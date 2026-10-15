import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from src.auth.firebase import FirebaseVerifier

PROJECT = "test-project"
_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)  # clave que Google NO publicó


def make_verifier() -> FirebaseVerifier:
    return FirebaseVerifier(PROJECT, key_resolver=lambda token: _PRIVATE.public_key())


def make_token(key=None, algorithm="RS256", **overrides) -> str:
    """ID token con la forma de Firebase. overrides pisa claims; un valor None elimina el claim."""
    now = int(time.time())
    claims = {
        "iss": f"https://securetoken.google.com/{PROJECT}", "aud": PROJECT, "sub": "uid-1",
        "iat": now, "exp": now + 3600, "email": "admin@example.com", "email_verified": True,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key or _PRIVATE, algorithm=algorithm)


def wrong_key_token(**overrides) -> str:
    return make_token(key=_OTHER, **overrides)


def authed_client(app) -> TestClient:
    """TestClient para los tests de funcionalidad: si la app usa Firebase, añade un token de admin válido."""
    client = TestClient(app)
    if hasattr(app.state, "auth_verifier"):
        client.headers["Authorization"] = f"Bearer {make_token()}"
    return client
