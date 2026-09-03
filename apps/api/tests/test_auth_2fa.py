"""M1 polish: 2FA enroll/confirm smoke + handle immutability."""

import pytest
from httpx import AsyncClient

from tests.helpers_auth import register_verified


@pytest.mark.asyncio
async def test_2fa_enroll_and_confirm_flow(client: AsyncClient):
    login = await register_verified(
        client, email="tfa@example.com", handle="tfa_user", full_name="TFA User"
    )
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    enroll = await client.post("/api/v1/auth/2fa/enroll", headers=headers)
    assert enroll.status_code == 200, enroll.text
    assert "secret" in enroll.json()
    assert "otpauth_url" in enroll.json()

    # Confirm with an invalid code should fail (proves endpoint is live)
    bad = await client.post(
        "/api/v1/auth/2fa/confirm",
        headers=headers,
        json={"code": "000000"},
    )
    assert bad.status_code in (400, 401, 422)


@pytest.mark.asyncio
async def test_me_exposes_handle_but_no_public_mutation(client: AsyncClient):
    login = await register_verified(
        client, email="handlelock@example.com", handle="locked_handle", full_name="Lock"
    )
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["handle"] == "locked_handle"
    # No PATCH /auth/me or handle update route should exist
    patch = await client.patch("/api/v1/auth/me", headers=headers, json={"handle": "hijacked"})
    assert patch.status_code in (404, 405, 422)
