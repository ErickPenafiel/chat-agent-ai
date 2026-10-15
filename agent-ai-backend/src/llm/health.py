"""Chequeo de arranque: detecta clave inválida o modelo inexistente antes del primer cliente."""

import logging

import httpx

from src.llm.base import LLMError, LLMProvider

log = logging.getLogger(__name__)

_HINTS = {
    401: "la API key fue rechazada; revisa la variable de entorno del proveedor",
    403: "la API key no tiene permiso para este modelo o proyecto",
    404: "el modelo no existe o ya no está disponible; revisa `llm.model` en tenant.yaml",
    429: "límite de uso alcanzado en el proveedor",
}


def verify_llm(llm: LLMProvider | None) -> bool:
    """Hace una llamada mínima. No detiene el arranque: deja un error claro en el log y devuelve False."""
    if llm is None:
        return True
    try:
        llm.complete("Responde solo: ok", "ok")
        return True
    except LLMError as e:
        cause = e.__cause__
        if isinstance(cause, httpx.HTTPStatusError):
            status = cause.response.status_code
            detail = f"HTTP {status}: {_HINTS.get(status, 'error del proveedor')}"
        else:
            detail = f"{type(cause).__name__ if cause else e}: sin conexión o respuesta inválida"
        log.error("El LLM configurado NO responde (%s). El agente contestará con el mensaje de respaldo.", detail)
        return False
