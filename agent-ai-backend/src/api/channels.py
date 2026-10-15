import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from src.api.auth import require_admin
from src.channels.base import InvalidWebhook
from src.channels.web import WebChannel
from src.core.dispatcher import handle_event, handle_event_with_trace

router = APIRouter(prefix="/channels", tags=["channels"])


def _channel(request: Request, name: str):
    channel = request.app.state.channels.get(name)
    if channel is None:
        raise HTTPException(404, f"canal {name!r} no está activo en tenant.yaml")
    return channel


@router.get("/{name}/webhook")
def verify(name: str, request: Request):
    """Handshake de suscripción (Meta). Canales que no lo usan responden 404."""
    channel = _channel(request, name)
    try:
        challenge = channel.verify_subscription(dict(request.query_params))
    except InvalidWebhook:
        raise HTTPException(403, "verificación rechazada")
    if challenge is None:
        raise HTTPException(404, "este canal no usa verificación")
    return Response(challenge, media_type="text/plain")


@router.post("/{name}/webhook")
async def webhook(name: str, request: Request):
    channel = _channel(request, name)
    if not channel.is_real:  # canal mock/de pruebas: consume LLM, no puede ser público
        await run_in_threadpool(require_admin, request)  # puede consultar claves públicas de Google (bloqueante)
    body = await request.body()
    try:
        events = channel.receive(body, dict(request.headers))
    except InvalidWebhook as e:
        raise HTTPException(400 if name == "web" else 403, str(e))
    state = request.app.state
    replies = []
    actions = []
    for event in events:
        reply, trace = await run_in_threadpool(
            handle_event_with_trace, state.graph, channel, event, state.deduper, state.recorder,
            state.config.max_input_chars,
        )
        if reply is not None:
            replies.append(reply)
            if trace:
                trace["provider"] = state.config.llm.provider if state.config.llm else None
                trace["model"] = state.config.llm.model if state.config.llm else None
                actions.append(trace)
    return {"processed": len(events), "replies": replies, "actions": actions}



@router.get("/web/outbox/{user_id}", dependencies=[Depends(require_admin)])
def outbox(user_id: str, request: Request):
    """Solo para pruebas con el adapter mock: lo que el agente le envió a ese usuario."""
    channel = _channel(request, "web")
    assert isinstance(channel, WebChannel)
    return channel.outbox.get(user_id, [])


@router.get("/web/stream", dependencies=[Depends(require_admin)])
async def stream(user_id: str, text: str, request: Request):
    """SSE: procesa un turno por el grafo y emite la respuesta en eventos `message`, cerrando con `done`."""
    channel = _channel(request, "web")
    assert isinstance(channel, WebChannel)
    body = json.dumps({"user_id": user_id, "text": text}).encode()
    try:
        events = channel.receive(body, {})
    except InvalidWebhook as e:
        raise HTTPException(400, str(e))
    state = request.app.state

    async def gen():
        for event in events:
            reply = await run_in_threadpool(handle_event, state.graph, channel, event, state.deduper, state.recorder,
                                        state.config.max_input_chars)
            if reply is not None:
                yield f"event: message\ndata: {json.dumps(reply, ensure_ascii=False, default=str)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
