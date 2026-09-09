"""
Credential encryption for Connections.

Provider API keys are encrypted at rest with Fernet (symmetric,
authenticated encryption) using settings.ENCRYPTION_KEY. The key must be a
generated Fernet key - see app/core/config.py for the generation command.

If ENCRYPTION_KEY is unset (e.g. a fresh dev install that hasn't configured
it yet), encryption falls back to a fixed local-only key so the app doesn't
crash - but this is NOT safe for production and a warning is raised.
"""

import warnings
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_DEV_FALLBACK_KEY = b"KyU3v0Q8yv8dGtj9mZ1cQvV1r7hFZQyq5W3f9pTz9pk="  # local dev only


@lru_cache
def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.strip()
    if not key:
        warnings.warn(
            "ENCRYPTION_KEY is not set - falling back to an insecure "
            "development key. Set ENCRYPTION_KEY in .env before storing "
            "any real provider API keys.",
            stacklevel=2,
        )
        return Fernet(_DEV_FALLBACK_KEY)
    return Fernet(key.encode())


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Could not decrypt stored credential - ENCRYPTION_KEY may have "
            "changed since it was saved."
        ) from exc
