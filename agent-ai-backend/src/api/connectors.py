from fastapi import APIRouter, Request

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("")
def list_connectors(request: Request):
    """Conectores activos en tenant.yaml y qué los dispara."""
    from src.connectors.registry import AVAILABLE

    return {
        "available": sorted(AVAILABLE),
        "active": [
            {"id": c.id, "intents": sorted(c.intents), "issues": sorted(c.issues), "prompt_key": c.prompt_key}
            for c in request.app.state.connectors
        ],
    }
