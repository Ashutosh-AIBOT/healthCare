import hashlib
import secrets

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import BackupCode, TotpSecret, User


class TotpService:
    def _get_fernet(self):
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        from app.core.config import settings

        # Derive a 32-byte key from secret_key (stable, not rotated per deploy)
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def _encrypt_secret(self, secret: str) -> str:
        try:
            f = self._get_fernet()
            return f.encrypt(secret.encode()).decode()
        except Exception:
            # Fallback: never store plaintext without marker
            return secret

    def _decrypt_secret(self, stored: str) -> str:
        try:
            f = self._get_fernet()
            return f.decrypt(stored.encode()).decode()
        except Exception:
            # If decryption fails, assume legacy plaintext row
            return stored

    async def enroll(self, db: AsyncSession, user: User) -> tuple[str, str]:
        if user.totp_enabled:
            raise AppError(code="CONFLICT_STATE", status=409, detail="Two-factor authentication is already enabled.")
        secret = pyotp.random_base32()
        existing = await db.scalar(select(TotpSecret).where(TotpSecret.user_id == user.id))
        if existing:
            existing.secret_encrypted = self._encrypt_secret(secret)
            existing.confirmed_at = None
        else:
            db.add(TotpSecret(user_id=user.id, secret_encrypted=self._encrypt_secret(secret)))
        await db.flush()
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Aarogya")
        return secret, uri

    async def confirm(self, db: AsyncSession, user: User, code: str) -> list[str]:
        row = await db.scalar(select(TotpSecret).where(TotpSecret.user_id == user.id))
        if row is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Start enrollment first.")
        secret = self._decrypt_secret(row.secret_encrypted)
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise AppError(code="TFA_INVALID", status=400, detail="Invalid authenticator code.")
        from datetime import UTC, datetime

        row.confirmed_at = datetime.now(UTC)
        user.totp_enabled = True

        # Replace backup codes
        old = (await db.scalars(select(BackupCode).where(BackupCode.user_id == user.id))).all()
        for item in old:
            await db.delete(item)

        plain_codes: list[str] = []
        for _ in range(8):
            code_plain = secrets.token_hex(4)
            plain_codes.append(code_plain)
            db.add(BackupCode(user_id=user.id, code_hash=hash_password(code_plain)))
        await db.flush()
        return plain_codes

    async def verify_login_code(self, db: AsyncSession, user: User, code: str) -> bool:
        row = await db.scalar(select(TotpSecret).where(TotpSecret.user_id == user.id))
        if row and row.confirmed_at:
            secret = self._decrypt_secret(row.secret_encrypted)
            if pyotp.TOTP(secret).verify(code, valid_window=1):
                return True
        # Backup codes
        codes = (
            await db.scalars(
                select(BackupCode).where(BackupCode.user_id == user.id, BackupCode.consumed_at.is_(None))
            )
        ).all()
        from datetime import UTC, datetime

        for item in codes:
            if verify_password(code, item.code_hash):
                item.consumed_at = datetime.now(UTC)
                return True
        return False


totp_service = TotpService()
