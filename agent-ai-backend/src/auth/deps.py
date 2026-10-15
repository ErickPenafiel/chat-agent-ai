"""Autorización de la API de administración. `require_admin` sirve como dependencia de FastAPI
y también se puede llamar directo con la request (síncrono: en endpoints async usar run_in_threadpool)."""

import logging
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from src.auth.firebase import InvalidToken
from src.core.config import AuthConfig

log = logging.getLogger(__name__)


@dataclass
class AuthUser:
    uid: str
    email: str | None = None
    claims: dict = field(default_factory=dict)


def is_admin(cfg: AuthConfig, claims: dict) -> bool:
    if claims.get("admin") is True:
        return True
    email = (claims.get("email") or "").lower()
    if not email or email not in cfg.admin_emails:
        return False
    return claims.get("email_verified") is True or not cfg.require_email_verified


def _unauthorized() -> HTTPException:
    return HTTPException(401, "autenticación requerida", headers={"WWW-Authenticate": "Bearer"})


def _bearer(request: Request) -> str | None:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def require_admin(request: Request) -> AuthUser:
    cfg: AuthConfig = request.app.state.config.auth
    if cfg.mode == "disabled":
        return AuthUser(uid="dev")
    token = _bearer(request)
    if token is None:
        raise _unauthorized()
    try:
        claims = request.app.state.auth_verifier.verify(token)
    except InvalidToken as e:
        log.info("token rechazado: %s", e)  # el motivo exacto no se devuelve al cliente
        raise _unauthorized()
    if not is_admin(cfg, claims):
        raise HTTPException(403, "el usuario no tiene permisos de administrador")
    return AuthUser(uid=claims["sub"], email=claims.get("email"), claims=claims)
