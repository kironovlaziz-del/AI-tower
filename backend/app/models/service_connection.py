from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class ServiceConnection(Base):
    """
    A live, credentialed connection to a discovered network service that
    an admin explicitly connected (see DiscoveryService.connect_service).

    This is where the actual secrets live - the bind password for an
    LDAP/AD directory, encrypted at rest with the same Fernet key used
    for provider API keys (app/core/crypto.py). The DiscoveredService row
    only points here via connected_ref_id; it never holds the secret.

    A separate table (rather than reusing ai_providers) because an AD/DNS
    connection is not an LLM provider: it has bind_dn / base_dn, and its
    purpose is directory/infra integration, not prompt routing.

    last_verified_at / last_error record the most recent connectivity
    check so the UI can show whether the stored credentials still work
    without re-prompting the admin.
    """

    __tablename__ = "service_connections"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    discovered_service_id = Column(
        Integer, ForeignKey("discovered_services.id", ondelete="CASCADE"), nullable=False
    )
    service_type = Column(String(50), nullable=False)  # active_directory, ldap, ...
    host = Column(String(255), nullable=False)
    port = Column(Integer)

    # LDAP/AD connection parameters. bind_password is Fernet-encrypted;
    # the others are not secret.
    bind_dn = Column(String(500))
    base_dn = Column(String(500))
    username = Column(String(255))
    bind_password_encrypted = Column(Text)

    # Snapshot of what the one-time read after connecting found (e.g. AD
    # user count, naming contexts) - display-only, never secret.
    info = Column(JSONB)

    last_verified_at = Column(DateTime(timezone=True))
    last_error = Column(String(500))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
