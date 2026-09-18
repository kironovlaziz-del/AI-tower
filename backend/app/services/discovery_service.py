from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovered_service import DiscoveredService
from app.schemas.discovery import (
    DiscoveredServiceIn,
    ServiceConnectRequest,
)


class DiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- ingestion from the discovery layer -------------------------------

    async def report_services(
        self, org_id: int, services: List[DiscoveredServiceIn]
    ) -> Tuple[int, int]:
        """
        Upsert discovered services. Re-discovering the same
        (service_type, host) bumps last_seen_at and refreshes details
        rather than creating a duplicate - discovery runs repeatedly, and
        the admin cares about "what's on my network now", not a log of
        every scan. Returns (new_count, updated_count).

        Crucially this ONLY records observations - it never initiates any
        connection. connect_status stays "discovered" until an admin acts.
        """
        new_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc)

        for svc in services:
            result = await self.db.execute(
                select(DiscoveredService).where(
                    DiscoveredService.org_id == org_id,
                    DiscoveredService.service_type == svc.service_type,
                    DiscoveredService.host == svc.host,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.last_seen_at = now
                existing.port = svc.port if svc.port is not None else existing.port
                if svc.details:
                    existing.details = svc.details
                existing.discovered_via = svc.discovered_via
                updated_count += 1
            else:
                self.db.add(
                    DiscoveredService(
                        org_id=org_id,
                        service_type=svc.service_type,
                        host=svc.host,
                        port=svc.port,
                        discovered_via=svc.discovered_via,
                        details=svc.details,
                        connect_status="discovered",
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                new_count += 1

        await self.db.commit()
        return new_count, updated_count

    # ---- listing ----------------------------------------------------------

    async def list_services(
        self, org_id: int, status_filter: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[DiscoveredService], int]:
        base = select(DiscoveredService).where(DiscoveredService.org_id == org_id)
        if status_filter:
            base = base.where(DiscoveredService.connect_status == status_filter)
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(DiscoveredService.last_seen_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def _get(self, service_id: int, org_id: int) -> DiscoveredService:
        result = await self.db.execute(
            select(DiscoveredService).where(
                DiscoveredService.id == service_id, DiscoveredService.org_id == org_id
            )
        )
        svc = result.scalar_one_or_none()
        if not svc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Discovered service not found"
            )
        return svc

    # ---- explicit connect / ignore ---------------------------------------

    async def ignore_service(
        self, service_id: int, org_id: int, reason: Optional[str]
    ) -> DiscoveredService:
        svc = await self._get(service_id, org_id)
        svc.connect_status = "ignored"
        if reason:
            svc.connect_error = None
            details = dict(svc.details or {})
            details["ignore_reason"] = reason
            svc.details = details
        await self.db.commit()
        await self.db.refresh(svc)
        return svc

    async def connect_service(
        self, service_id: int, org_id: int, connected_by: int, creds: ServiceConnectRequest
    ) -> DiscoveredService:
        """
        Attempt to connect ONE discovered service using credentials the
        admin explicitly supplied. This is the ONLY path that ever
        establishes a real connection to a discovered service - there is
        no anonymous/automatic attach anywhere in the system.

        The actual per-service connection logic (LDAP bind for AD, zone
        read for DNS, API auth for a firewall) is delegated to a
        type-specific handler. Until those handlers land in the discovery
        track, connecting records the admin's intent and the supplied
        credential *reference*, marks the service, and returns - it does
        NOT fabricate a fake "connected" success. A service whose handler
        isn't implemented yet is marked "needs_credentials" with a clear
        message rather than pretending it worked.
        """
        svc = await self._get(service_id, org_id)

        handler = _CONNECT_HANDLERS.get(svc.service_type)
        if handler is None:
            svc.connect_status = "needs_credentials"
            svc.connect_error = (
                f"Connecting '{svc.service_type}' services is not implemented yet. "
                "The credentials were not used or stored."
            )
            await self.db.commit()
            await self.db.refresh(svc)
            return svc

        # A handler exists: run it. Handlers must NEVER auto-connect on
        # their own - they only run because we reached here from an
        # explicit admin action with supplied credentials.
        try:
            ref_type, ref_id = await handler(self.db, org_id, svc, creds)
            svc.connect_status = "connected"
            svc.connect_error = None
            svc.connected_ref_type = ref_type
            svc.connected_ref_id = ref_id
            svc.connected_by = connected_by
            svc.connected_at = datetime.now(timezone.utc)
        except ServiceConnectError as exc:
            svc.connect_status = "error"
            svc.connect_error = str(exc)[:500]

        await self.db.commit()
        await self.db.refresh(svc)
        return svc


class ServiceConnectError(Exception):
    """Raised by a connect handler when the supplied credentials don't
    work or the target refuses the connection - surfaced to the admin as
    connect_error, not swallowed."""


# Per-service-type connect handlers. Each takes (db, org_id, service,
# creds) and returns (connected_ref_type, connected_ref_id) on success,
# or raises ServiceConnectError. Empty for now: the real LDAP/DNS/DHCP
# handlers belong to the discovery track and will register here. Keeping
# this as an explicit, initially-empty registry (rather than a stub that
# fakes success) is what guarantees the system never claims to have
# connected to something it hasn't.
_CONNECT_HANDLERS = {}
