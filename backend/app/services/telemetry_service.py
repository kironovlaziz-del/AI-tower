from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_telemetry_event import AITelemetryEvent
from app.schemas.incident import IncidentCreate
from app.schemas.shadow_ai import ShadowSightingCreate
from app.schemas.telemetry import (
    DOMAIN_EVENT_TYPE,
    LOCAL_SIGNAL_EVENT_TYPES,
    TelemetryEventIn,
    TelemetryIngestResponse,
)
from app.services import notification_service
from app.services.domain_catalog_service import DomainCatalogService
from app.services.incident_service import IncidentService
from app.services.shadow_ai_service import ShadowAIService


class TelemetryService:
    """
    Shadow AI Monitor ingestion pipeline for the real, already-deployed
    producers: the Go endpoint agent (agent/) and the browser extension
    (extension/). Two genuinely different kinds of signal arrive on the
    same batch endpoint:

    1. "domain_visit" (from the browser extension today; a future
       network-level collector could add more) - a real outbound domain,
       classified against the org's domain catalog exactly as designed
       in Shadow AI Monitor stage 1: blocked -> sighting + incident,
       unknown -> sighting, allowed -> logged only.

    2. "process_detected" / "network_conn" / "local_model_found" (from
       the endpoint agent) - a local AI tool was found running or
       installed on one specific machine. There is no domain to classify
       here (domain_catalog has no concept of "is Ollama allowed"), so
       these always raise a sighting - but see the per-agent dedup note
       on _local_signal_identity below, since collapsing these across
       different people's machines the way domain dedup works would
       hide exactly the fact that matters (how many people are running
       this, not just whether anyone is).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.catalog = DomainCatalogService(db)
        self.shadow_ai = ShadowAIService(db)
        self.incidents = IncidentService(db)

    async def ingest_events(
        self, org_id: int, ingestion_source_id: int, events: List[TelemetryEventIn]
    ) -> TelemetryIngestResponse:
        counts = {"allowed": 0, "unknown": 0, "blocked": 0}
        local_signals = 0
        sightings_created = 0
        incidents_created = 0

        for event in events:
            if event.event_type == DOMAIN_EVENT_TYPE:
                policy_status, sighting_delta, incident_delta = await self._handle_domain_visit(
                    org_id, ingestion_source_id, event
                )
                counts[policy_status] += 1
                sightings_created += sighting_delta
                incidents_created += incident_delta
            elif event.event_type in LOCAL_SIGNAL_EVENT_TYPES:
                local_signals += 1
                sightings_created += await self._handle_local_signal(
                    org_id, ingestion_source_id, event
                )
            else:
                # An event_type we don't recognize yet (a newer agent
                # version, or a typo) is still logged for the record,
                # just not acted on - better than silently dropping it
                # or rejecting the whole batch over one unknown type.
                self._log_raw_event(org_id, ingestion_source_id, event, matched_policy_status=None)

        await self.db.commit()

        return TelemetryIngestResponse(
            received=len(events),
            allowed=counts["allowed"],
            unknown=counts["unknown"],
            blocked=counts["blocked"],
            local_signals=local_signals,
            sightings_created=sightings_created,
            incidents_created=incidents_created,
        )

    def _log_raw_event(
        self,
        org_id: int,
        ingestion_source_id: int,
        event: TelemetryEventIn,
        matched_policy_status: Optional[str],
    ) -> None:
        self.db.add(
            AITelemetryEvent(
                org_id=org_id,
                ingestion_source_id=ingestion_source_id,
                event_type=event.event_type,
                domain=event.domain,
                agent_id=event.agent_id,
                user_hint=event.user_id,
                risk_score=event.risk_score,
                action_taken=event.action_taken,
                occurred_at=event.timestamp or datetime.now(timezone.utc),
                matched_policy_status=matched_policy_status,
                metadata_json=event.payload,
            )
        )

    async def _handle_domain_visit(
        self, org_id: int, ingestion_source_id: int, event: TelemetryEventIn
    ) -> Tuple[str, int, int]:
        domain = event.domain or "unknown"
        match = await self.catalog.match_domain(org_id, domain)
        self._log_raw_event(org_id, ingestion_source_id, event, matched_policy_status=match.policy_status)

        if match.policy_status == "allowed":
            return "allowed", 0, 0

        existing = await self.shadow_ai.find_open_sighting_by_domain(org_id, domain)
        if existing:
            # Already flagged and still unresolved - the raw event is
            # still logged above, but instead of a new sighting we bump
            # the repeat counter so the UI shows it's ongoing.
            await self.shadow_ai.record_repeat_sighting(existing)
            return match.policy_status, 0, 0

        # A payload-supplied tool_name (the extension already knows this
        # from its own domain catalog) beats the org catalog's hint,
        # which in turn beats the bare domain string.
        payload = event.payload or {}
        payload_tool_name = payload.get("tool_name")
        display_meta = {
            "kind": "domain",
            "domain": domain,
            "category": payload.get("category") or match.category,
            "url": payload.get("url"),
            "agent_id": event.agent_id,
        }
        sighting = await self.shadow_ai.create_sighting(
            org_id,
            reported_by=None,
            data=ShadowSightingCreate(
                tool_name=payload_tool_name or match.tool_name or domain,
                domain=domain,
                detected_via=event.event_type,
                user_hint=event.user_id,
                display_meta=display_meta,
                notes=(
                    f"Auto-detected via telemetry ingestion "
                    f"(category: {payload.get('category') or match.category or 'unclassified'})."
                ),
            ),
        )

        if match.policy_status == "blocked":
            incident = await self.incidents.create_incident(
                org_id,
                IncidentCreate(
                    severity="high",
                    category="shadow_ai",
                    summary=(
                        f"Blocked AI domain detected: {domain}"
                        + (f" (user: {event.user_id})" if event.user_id else "")
                    ),
                    impact=(
                        "Traffic to a domain explicitly marked 'blocked' in this "
                        "organization's AI domain catalog was observed."
                    ),
                ),
            )
            await notification_service.notify(
                self.db,
                org_id,
                "shadow_ai_blocked_domain",
                f"Заблокированный AI-домен обнаружен: {domain}",
                f"Инцидент #{incident.id} создан автоматически. "
                f"Sighting #{sighting.id} в Shadow AI Monitor.",
                {"sighting_id": sighting.id, "incident_id": incident.id},
            )
            return "blocked", 1, 1

        await notification_service.notify(
            self.db,
            org_id,
            "shadow_ai_reported",
            f"Замечено несанкционированное использование AI: {sighting.tool_name}",
            f"Обнаружено автоматически через {event.event_type}. "
            f"Требует разбора в Shadow AI Monitor.",
            {"sighting_id": sighting.id},
        )
        return "unknown", 1, 0

    @staticmethod
    def _local_signal_identity(event: TelemetryEventIn) -> Tuple[str, str]:
        """
        Returns (dedup_key, tool_name). The dedup key is stored in
        ShadowAISighting.domain (reusing the existing dedup mechanism
        rather than inventing a parallel one) and is deliberately scoped
        per agent_id: two different people independently running Ollama
        are two separate facts worth knowing, not one. Domain-visit
        dedup is intentionally org-wide instead (see _handle_domain_visit)
        because that's about a policy violation existing at all, not
        about who specifically triggered it.
        """
        payload = event.payload or {}
        agent = event.agent_id or "unknown-agent"

        if event.event_type == "process_detected":
            name = payload.get("process_name") or payload.get("ai_tool") or "unknown-process"
            return f"local:{agent}:process:{name}", payload.get("ai_tool") or name

        if event.event_type == "network_conn":
            port = payload.get("port", "unknown-port")
            service = payload.get("service") or f"port {port}"
            return f"local:{agent}:port:{port}", service

        # local_model_found
        path = payload.get("file_path") or "unknown-file"
        name = payload.get("file_name") or path
        key = f"local:{agent}:model:{path}"
        # Column is String(255); a long absolute path could overflow it,
        # so fall back to just the filename for the dedup key in that
        # case - collisions across identically-named files in different
        # directories on the same machine are an acceptable trade for
        # never hitting a DB length error on a legitimate long path.
        if len(key) > 255:
            key = f"local:{agent}:model:{name}"[:255]
        return key, name

    @staticmethod
    def _local_display_meta(event: TelemetryEventIn) -> dict:
        """Human-readable specifics the UI can render, extracted per
        event type from the collector's payload (see the Go agent's
        collectors/*.go). Kept separate from the raw dedup key so the
        UI never has to show 'local:host:port:8000' to a person."""
        payload = event.payload or {}
        base = {"agent_id": event.agent_id}
        if event.event_type == "process_detected":
            return {
                **base,
                "kind": "process",
                "process_name": payload.get("process_name"),
                "pid": payload.get("pid"),
                "ai_tool": payload.get("ai_tool"),
            }
        if event.event_type == "network_conn":
            return {
                **base,
                "kind": "network",
                "port": payload.get("port"),
                "service": payload.get("service"),
                "target_host": payload.get("target_host"),
            }
        # local_model_found
        return {
            **base,
            "kind": "model_file",
            "file_name": payload.get("file_name"),
            "file_path": payload.get("file_path"),
            "size_mb": payload.get("size_mb"),
            "extension": payload.get("extension"),
        }

    async def _handle_local_signal(
        self, org_id: int, ingestion_source_id: int, event: TelemetryEventIn
    ) -> int:
        self._log_raw_event(org_id, ingestion_source_id, event, matched_policy_status=None)

        dedup_key, tool_name = self._local_signal_identity(event)
        existing = await self.shadow_ai.find_open_sighting_by_domain(org_id, dedup_key)
        if existing:
            await self.shadow_ai.record_repeat_sighting(existing)
            return 0

        sighting = await self.shadow_ai.create_sighting(
            org_id,
            reported_by=None,
            data=ShadowSightingCreate(
                tool_name=tool_name,
                domain=dedup_key,
                detected_via=event.event_type,
                user_hint=event.user_id,
                display_meta=self._local_display_meta(event),
                notes=f"Auto-detected on endpoint '{event.agent_id or 'unknown'}' via {event.event_type}.",
            ),
        )
        await notification_service.notify(
            self.db,
            org_id,
            "shadow_ai_reported",
            f"Обнаружен локальный AI-инструмент: {sighting.tool_name}",
            f"Найдено на устройстве '{event.agent_id or 'неизвестно'}' через {event.event_type}. "
            f"Требует разбора в Shadow AI Monitor.",
            {"sighting_id": sighting.id},
        )
        return 1
