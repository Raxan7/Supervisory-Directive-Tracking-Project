from datetime import timedelta
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    encoded=hash_password("a-secure-password")
    assert verify_password("a-secure-password",encoded)
    assert not verify_password("wrong-password",encoded)


def test_signed_token_round_trip():
    token=create_access_token("7","admin","secret-for-test",timedelta(minutes=5))
    payload=decode_access_token(token,"secret-for-test")
    assert payload["sub"]=="7" and payload["role"]=="admin"

