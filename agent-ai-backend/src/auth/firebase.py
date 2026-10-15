"""Verificación de ID tokens de Firebase Auth (JWT RS256 firmado por Google)."""

from collections.abc import Callable

import jwt
from jwt import PyJWKClient

JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"


class InvalidToken(Exception):
    pass


class FirebaseVerifier:
    def __init__(
        self,
        project_id: str,
        key_resolver: Callable[[str], object] | None = None,
        leeway_seconds: int = 10,
    ) -> None:
        self._project = project_id
        self._leeway = leeway_seconds
        if key_resolver is None:
            client = PyJWKClient(JWKS_URL, cache_keys=True)  # cachea las claves públicas en memoria
            key_resolver = lambda token: client.get_signing_key_from_jwt(token).key
        self._resolve = key_resolver

    def verify(self, token: str) -> dict:
        """Devuelve los claims o lanza InvalidToken. Solo RS256: bloquea alg=none y confusión HS256."""
        try:
            claims = jwt.decode(
                token,
                self._resolve(token),
                algorithms=["RS256"],
                audience=self._project,
                issuer=f"https://securetoken.google.com/{self._project}",
                leeway=self._leeway,
                options={"require": ["exp", "iat", "aud", "iss", "sub"]},
            )
        except Exception as e:  # firma, expiración, audiencia, emisor, formato o clave no encontrada
            raise InvalidToken(type(e).__name__) from e
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise InvalidToken("sub vacío")
        return claims
