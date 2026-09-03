from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("SecurePass1!")
    assert verify_password("SecurePass1!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    import uuid

    uid = uuid.uuid4()
    token = create_access_token(uid, "family_owner")
    payload = decode_token(token, "access")
    assert payload["sub"] == str(uid)
    assert payload["role"] == "family_owner"
