from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class DiscoveredService(Base):
    """
    A network service (DNS, DHCP, Active Directory/LDAP, etc.) that
    passive discovery found on the org's network - see the sniffer/agent
    discovery track. This row is a READ-ONLY OBSERVATION: finding a
    service here does NOT mean the system connected to it or read
    anything from it. Connection only happens when an admin explicitly
    supplies credentials via the connect wizard (see connect_status).

    This separation is deliberate and is the whole point of the
    "explicit-connect" design: discovery is passive and safe (just
    listening to broadcast traffic / SRV records the network already
    advertises), while anything that actually touches another system -
    an LDAP bind, a DNS zone read - requires a human to authorize that
    specific connection with real credentials. We never anonymously
    auto-attach.

    Dedup: (org_id, service_type, host) is unique - re-discovering the
    same service updates last_seen_at rather than piling up duplicates.
    """

    __tablename__ = "discovered_services"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # What kind of service: "dns", "dhcp", "active_directory", "ldap",
    # "kerberos", "firewall", "unknown". Free-form string rather than an
    # enum so the discovery layer can report new types without a schema
    # change / migration.
    service_type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=False)  # IP or hostname as discovered
    port = Column(Integer)
    # How it was found: "mdns", "dns_srv", "dhcp_broadcast", "llmnr",
    # "arp_scan", "manual" - provenance matters for an admin deciding
    # whether to trust/act on a discovered service.
    discovered_via = Column(String(50), nullable=False)
    # Anything extra the discovery layer learned (AD domain name, DNS
    # server vendor, etc.) - display-only, shaped by the discoverer.
    details = Column(JSONB)

    # Connection lifecycle, driven by the admin wizard - NOT by discovery:
    #   "discovered"     - found, nothing done (default)
    #   "needs_credentials" - admin started connecting, service requires
    #                         credentials that haven't been supplied yet
    #   "connected"      - admin supplied working credentials; a real
    #                      connection was established and verified
    #   "ignored"        - admin dismissed it; keep the record but stop
    #                      surfacing it as actionable
    #   "error"          - a connection attempt was made and failed
    connect_status = Column(String(30), nullable=False, default="discovered")
    connect_error = Column(String(500))
    # FK to whatever connection object a successful connect produced
    # (e.g. an AIProvider or a future credentialed-connection row). Null
    # until connected. Kept as a plain int + label rather than a hard FK
    # so different service types can point at different target tables.
    connected_ref_type = Column(String(50))
    connected_ref_id = Column(Integer)

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    connected_by = Column(Integer, ForeignKey("users.id"))
    connected_at = Column(DateTime(timezone=True))
