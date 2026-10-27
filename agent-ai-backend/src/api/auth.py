from fastapi import APIRouter, Depends

from src.auth.deps import AuthUser, require_admin

__all__ = ["require_admin", "router"]

router = APIRouter(tags=["auth"])


@router.get("/auth/me")
def me(user: AuthUser = Depends(require_admin)):
    """Para que el frontend confirme que su token de Firebase es válido y el usuario es admin."""
    return {"uid": user.uid, "email": user.email}


@router.get("/health")
def health():
    return {"status": "ok"}
