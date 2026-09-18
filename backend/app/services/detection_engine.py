import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_domain_catalog import AIDomainCatalog
from app.schemas.telemetry import TelemetryEventIn

KNOWN_AI_PORTS = {
    11434: ("Ollama", "high"),
    1234: ("LM Studio", "medium"),
    5000: ("LocalAI / Flask Model API", "medium"),
    8080: ("llama.cpp server", "medium"),
    7860: ("Gradio / Text Generation WebUI", "medium"),
    8000: ("vLLM / Triton Inference", "medium"),
}

KNOWN_AI_PROCESSES = {
    "ollama": ("Ollama Local LLM", "high"),
    "lm studio": ("LM Studio", "medium"),
    "jan": ("Jan AI Assistant", "medium"),
    "text-generation-webui": ("oobabooga WebUI", "medium"),
    "localai": ("LocalAI", "medium"),
    "llama-server": ("llama.cpp Server", "medium"),
}

AI_DOMAIN_KEYWORDS = re.compile(
    r"(?:^|[\.-])(ai|llm|gpt|claude|openai|anthropic|cohere|mistral|replicate|midjourney)(?:[\.-]|$)",
    re.IGNORECASE,
)

@dataclass
class DetectionResult:
    detected: bool
    confidence: float
    source: str
    category: str = "unclassified"
    tool_name: Optional[str] = None
    policy_status: str = "unknown"
    risk: str = "low"
    reasons: List[str] = field(default_factory=list)

class DetectionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_event(self, org_id: int, event: TelemetryEventIn) -> DetectionResult:
        if event.domain:
            cat_result = await self._check_catalog(org_id, event.domain)
            if cat_result:
                return cat_result

        behavioral_result = self._check_behavioral(event)
        if behavioral_result.detected:
            return behavioral_result

        fingerprint_result = self._check_fingerprint(event)
        if fingerprint_result.detected:
            return fingerprint_result

        return DetectionResult(detected=False, confidence=0.0, source="none", policy_status="unknown", risk="low")

    async def _check_catalog(self, org_id: int, domain: str) -> Optional[DetectionResult]:
        clean = domain.lower().strip()
        stmt = select(AIDomainCatalog).where(
            AIDomainCatalog.org_id == org_id,
            (AIDomainCatalog.domain == clean) | (clean.endswith("." + AIDomainCatalog.domain)),
        )
        res = await self.db.execute(stmt)
        entry = res.scalars().first()

        if entry:
            risk = "low" if entry.policy_status == "allowed" else ("high" if entry.policy_status == "blocked" else "medium")
            return DetectionResult(
                detected=True,
                confidence=1.0,
                source="catalog",
                category=entry.category or "llm",
                tool_name=entry.tool_name or domain,
                policy_status=entry.policy_status,
                risk=risk,
                reasons=[f"Domain catalog match: policy_status={entry.policy_status}"],
            )
        return None

    def _check_behavioral(self, event: TelemetryEventIn) -> DetectionResult:
        payload = event.payload or {}

        if event.event_type == "pii_paste_attempt":
            pii_types = payload.get("findings", [])
            return DetectionResult(
                detected=True,
                confidence=1.0,
                source="behavioral",
                category="data_leak",
                tool_name=event.domain or "AI Web Form",
                policy_status="blocked",
                risk="critical",
                reasons=[f"PII paste attempt ({', '.join(pii_types)}) towards {event.domain}"],
            )

        proc_name = (payload.get("process_name") or "").lower()
        cmdline = (payload.get("cmdline") or "").lower()
        for key, (name, risk) in KNOWN_AI_PROCESSES.items():
            if key in proc_name or key in cmdline:
                return DetectionResult(
                    detected=True,
                    confidence=0.95,
                    source="behavioral",
                    category="local_llm",
                    tool_name=name,
                    policy_status="unknown",
                    risk=risk,
                    reasons=[f"Known AI process detected: {name}"],
                )

        local_port = payload.get("local_port") or payload.get("port")
        if local_port and str(local_port).isdigit() and int(local_port) in KNOWN_AI_PORTS:
            name, risk = KNOWN_AI_PORTS[int(local_port)]
            return DetectionResult(
                detected=True,
                confidence=0.9,
                source="behavioral",
                category="local_server",
                tool_name=name,
                policy_status="unknown",
                risk=risk,
                reasons=[f"Local AI server port active: {local_port} ({name})"],
            )

        if event.domain and AI_DOMAIN_KEYWORDS.search(event.domain):
            return DetectionResult(
                detected=True,
                confidence=0.75,
                source="behavioral",
                category="suspicious_domain",
                tool_name=event.domain,
                policy_status="unknown",
                risk="medium",
                reasons=[f"Domain {event.domain} matches AI keyword heuristics"],
            )

        return DetectionResult(detected=False, confidence=0.0, source="none")

    def _check_fingerprint(self, event: TelemetryEventIn) -> DetectionResult:
        payload = event.payload or {}
        headers = {k.lower(): v for k, v in (payload.get("headers") or {}).items()}
        reasons = []

        if any(h.startswith("x-openai-") for h in headers) or "anthropic-version" in headers:
            reasons.append("Provider-specific AI API headers present (OpenAI/Anthropic)")

        ua = headers.get("user-agent", "").lower()
        if any(marker in ua for marker in ("open-webui", "ollama", "langchain")):
            reasons.append(f"AI client User-Agent: {ua}")

        url_path = payload.get("path", "")
        if "/v1/chat/completions" in url_path or "/v1/messages" in url_path:
            reasons.append(f"LLM API endpoint called: {url_path}")

        if reasons:
            return DetectionResult(
                detected=True,
                confidence=0.85,
                source="fingerprint",
                category="api_access",
                tool_name=event.domain or "Shadow AI API Client",
                policy_status="unknown",
                risk="high",
                reasons=reasons,
            )

        return DetectionResult(detected=False, confidence=0.0, source="none")
