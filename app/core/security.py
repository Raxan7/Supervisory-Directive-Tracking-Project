import base64
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    algorithm, rounds, salt, expected = encoded.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
    return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(subject: str, role: str, secret: str, expires: timedelta) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": subject, "role": role, "exp": int(time.time() + expires.total_seconds())}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str, secret: str) -> dict:
    header, payload, signature = token.split(".")
    signing_input = f"{header}.{payload}".encode()
    expected = _b64(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid signature")
    data = json.loads(_unb64(payload))
    if data["exp"] < int(time.time()):
        raise ValueError("Token expired")
    return data

