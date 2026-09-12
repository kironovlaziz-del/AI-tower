"""
Rotate the Fernet key used for provider API keys.

Usage:
    1. Generate a new key:
         python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    2. Add it to backend/.env as ENCRYPTION_KEY_NEW, keeping the old
       ENCRYPTION_KEY in place.
    3. Run this script from the backend directory:
         python3 scripts/rotate_encryption_key.py
    4. Move the new value into ENCRYPTION_KEY and remove ENCRYPTION_KEY_NEW.
    5. Restart the backend.

The script re-encrypts every ai_providers.api_key_encrypted using the old
key to decrypt and the new key to encrypt. It is idempotent: rows already
encrypted with the new key are skipped.
"""

import sys
from pathlib import Path

# Allow "python scripts/rotate_encryption_key.py" from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography.fernet import Fernet, InvalidToken  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.sync_database import SyncSessionLocal  # noqa: E402
from app.models.ai_provider import AIProvider  # noqa: E402


def main() -> int:
    old_key = settings.ENCRYPTION_KEY.strip()
    new_key = settings.ENCRYPTION_KEY_NEW.strip()

    if not old_key:
        print("ERROR: ENCRYPTION_KEY is empty.", file=sys.stderr)
        return 1
    if not new_key:
        print(
            "ERROR: ENCRYPTION_KEY_NEW is empty. Set it in backend/.env "
            "before running this script.",
            file=sys.stderr,
        )
        return 1
    if old_key == new_key:
        print("ERROR: new key equals old key, nothing to do.", file=sys.stderr)
        return 1

    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())

    rotated = 0
    skipped_already_new = 0
    failed: list[tuple[int, str]] = []

    db = SyncSessionLocal()
    try:
        providers = db.execute(select(AIProvider)).scalars().all()
        for provider in providers:
            if not provider.api_key_encrypted:
                continue

            # Try old key first.
            try:
                plaintext = old_fernet.decrypt(provider.api_key_encrypted.encode()).decode()
            except InvalidToken:
                # Maybe already encrypted with the new key from a previous
                # partial run - try new key.
                try:
                    new_fernet.decrypt(provider.api_key_encrypted.encode())
                    skipped_already_new += 1
                    continue
                except InvalidToken:
                    failed.append((provider.id, "no key could decrypt it"))
                    continue

            provider.api_key_encrypted = new_fernet.encrypt(plaintext.encode()).decode()
            rotated += 1

        db.commit()
    finally:
        db.close()

    print(f"Rotated: {rotated}")
    print(f"Already on new key: {skipped_already_new}")
    if failed:
        print(f"Failed: {len(failed)}")
        for pid, reason in failed:
            print(f"  provider #{pid}: {reason}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
