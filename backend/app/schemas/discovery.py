from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


# ---- Discovery ingestion (from the sniffer/agent discovery layer) ----

class DiscoveredServiceIn(BaseModel):
    service_type: str
    host: str
    port: Optional[int] = None
    discovered_via: str
    details: Optional[Dict[str, Any]] = None


class DiscoveryReportRequest(BaseModel):
    services: List[DiscoveredServiceIn]


class DiscoveryReportResponse(BaseModel):
    received: int
    new_services: int
    updated_services: int


# ---- Listing / display ----

class DiscoveredServiceOut(BaseModel):
    id: int
    org_id: int
    service_type: str
    host: str
    port: Optional[int]
    discovered_via: str
    details: Optional[Dict[str, Any]]
    connect_status: str
    connect_error: Optional[str]
    connected_ref_type: Optional[str]
    connected_ref_id: Optional[int]
    first_seen_at: datetime
    last_seen_at: datetime
    connected_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---- Connect wizard (admin supplies real credentials, explicitly) ----

class ServiceConnectRequest(BaseModel):
    """
    Credentials an admin explicitly provides to connect ONE discovered
    service. Which fields matter depends on service_type - e.g. LDAP/AD
    needs bind_dn + password, a firewall API needs api_token. All
    optional at the schema level; the service-specific connect handler
    validates what it actually requires.
    """
    username: Optional[str] = None
    password: Optional[str] = None
    bind_dn: Optional[str] = None
    base_dn: Optional[str] = None
    api_token: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ServiceIgnoreRequest(BaseModel):
    reason: Optional[str] = None
