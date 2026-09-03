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
    assert reg.status_code == 201, reg.text
    assert reg.json()["tokens"] is None

    verify = await client.post(
        "/api/v1/otp/verify",
        json={"email": email, "code": settings.otp_dev_code, "purpose": "verify_email"},
    )
    assert verify.status_code == 200, verify.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login
