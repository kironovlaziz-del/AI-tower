"""
AI Policy Evaluation Engine.
Evaluates telemetry events against active AI policies and registers incidents.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_policy import AIPolicy
from app.models.ai_incident import AIIncident
from app.services import notification_service


class PolicyEngine:
    """
    Evaluates incoming telemetry events against organizational AI policies.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_policies(self, org_id: int) -> List[AIPolicy]:
        """Fetch all active policies for the organization."""
        query = select(AIPolicy).where(
            AIPolicy.org_id == org_id,
            AIPolicy.is_active == True,
        )
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def evaluate_event(
        self,
        org_id: int,
        event: Dict[str, Any],
        source_id: Optional[int] = None,
    ) -> Optional[AIIncident]:
        """
        Evaluate a single telemetry event and register an incident if violations occur.
        """
        event_type = event.get("event_type")
        payload = event.get("payload") or {}
        user_identity = event.get("user_identity") or "unknown_user"
        hostname = event.get("hostname") or "unknown_host"

        incident: Optional[AIIncident] = None

        if event_type == "pii_paste_attempt":
            matches = payload.get("matches", [])
            domain = payload.get("domain", "external AI service")
            summary = f"Sensitive data paste attempt detected towards {domain}"
            impact = (
                f"User {user_identity} on host {hostname} attempted to send "
                f"potential credentials or PII: {matches[:5]}."
            )
            root_cause = "Browser extension PII guard triggered"

            incident = AIIncident(
                org_id=org_id,
                severity="critical" if any(m in ("api_key", "private_key") for m in matches) else "high",
                category="data_leak_prevention",
                summary=summary,
                impact=impact,
                root_cause=root_cause,
                status="open",
            )

        elif event_type in ("domain_visit", "api_call"):
            domain = payload.get("domain") or payload.get("host")
            if domain:
                policies = await self.get_active_policies(org_id)
                for pol in policies:
                    pattern = pol.rule_definition or ""
                    if pattern and pattern.lower() in domain.lower() and pol.enforcement_mode == "block":
                        incident = AIIncident(
                            org_id=org_id,
                            severity="medium",
                            category="unauthorized_ai_usage",
                            summary=f"Visit to blocked AI domain: {domain}",
                            impact=f"Access attempt by {user_identity} on {hostname} to restricted service.",
                            root_cause=f"Matched policy rule: {pol.name}",
                            status="open",
                        )
                        break

        elif event_type in ("process_detected", "port_active", "model_file_found"):
            tool_name = payload.get("tool_name") or payload.get("process_name") or "Local AI Model"
            incident = AIIncident(
                org_id=org_id,
                severity="medium" if event_type == "model_file_found" else "low",
                category="shadow_ai_endpoint",
                summary=f"Unapproved local AI asset detected: {tool_name}",
                impact=f"Host {hostname} has active shadow AI process or port: {payload}",
                root_cause="Go Endpoint Agent local discovery",
                status="open",
            )

        if incident:
            self.db.add(incident)
            await self.db.flush()

            try:
                await notification_service.notify_sync(
                    self.db,
                    org_id=org_id,
                    event_type="incident_created",
                    payload={
                        "incident_id": incident.id,
                        "summary": incident.summary,
                        "severity": incident.severity,
                        "category": incident.category,
                    },
                )
            except Exception:
                pass

        return incident
