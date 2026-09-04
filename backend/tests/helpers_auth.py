"""Shared helpers for auth-aware API tests."""

from app.core.config import settings


async def register_verified(client, *, email: str, password: str = "SecurePass1!", handle: str, full_name: str = "Test"):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "handle": handle,
            "full_name": full_name,
            "terms_version": "2026-09-01",
            "privacy_version": "2026-09-01",
            "medical_disclaimer_version": "2026-09-01",
        },
    )
    assert reg.status_code == 202, reg.text

    verify = await client.post(
        "/api/v1/auth/verify-registration",
        json={"email": email, "code": settings.otp_dev_code},
    )
    assert verify.status_code == 201, verify.text
    assert verify.json()["tokens"] is not None
    assert verify.json()["user"]["is_verified"] is True
    return verify
