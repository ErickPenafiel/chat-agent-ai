import json

import httpx
import pytest

from src.core.config import LLMConfig
from src.llm.base import LLMError
from src.llm.factory import build_llm
from src.llm.openrouter import OpenRouterLLM, audio_part, image_part, video_part


def _llm(handler):
    return OpenRouterLLM("K", "google/gemini-2.5-flash-lite", client=httpx.Client(transport=httpx.MockTransport(handler)))


def _ok(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_complete_ok():
    seen = {}

    def handler(req):
        seen["req"] = req
        return _ok(" hola ")

    assert _llm(handler).complete("sys", "usr") == "hola"
    req = seen["req"]
    assert str(req.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer K"
    body = json.loads(req.content)
    assert body["model"] == "google/gemini-2.5-flash-lite"
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert "response_format" not in body and "stream" not in body


def test_json_mode():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return _ok("{}")

    _llm(handler).complete("s", "u", json_mode=True)
    assert seen["body"]["response_format"] == {"type": "json_object"}


def test_media_parts_follow_the_text():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return _ok("ok")

    media = [image_part("https://x/y.jpg"), audio_part("QUJD", "wav"), video_part("https://x/v.mp4")]
    _llm(handler).complete("s", "¿Qué ves?", media=media)
    assert seen["body"]["messages"][1]["content"] == [
        {"type": "text", "text": "¿Qué ves?"},
        {"type": "image_url", "image_url": {"url": "https://x/y.jpg"}},
        {"type": "input_audio", "input_audio": {"data": "QUJD", "format": "wav"}},
        {"type": "video_url", "video_url": {"url": "https://x/v.mp4"}},
    ]


def test_timeout_maps_to_llm_error():
    def handler(req):
        raise httpx.ReadTimeout("t", request=req)

    with pytest.raises(LLMError):
        _llm(handler).complete("s", "u")


@pytest.mark.parametrize("status", [401, 402, 429, 500])
def test_http_errors(status):
    with pytest.raises(LLMError):
        _llm(lambda r: httpx.Response(status, json={"error": {}})).complete("s", "u")


def test_malformed_response():
    with pytest.raises(LLMError):
        _llm(lambda r: httpx.Response(200, json={"choices": []})).complete("s", "u")


def test_stream_chunks_skip_keepalive_comments():
    events = "".join(
        f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n" for c in ["Ho", "la"]
    )
    sse = ": OPENROUTER PROCESSING\n\n" + events + "data: [DONE]\n\n"
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, text=sse)

    assert list(_llm(handler).stream("s", "u")) == ["Ho", "la"]
    assert seen["body"]["stream"] is True


def test_stream_http_error():
    with pytest.raises(LLMError):
        list(_llm(lambda r: httpx.Response(429)).stream("s", "u"))


def test_factory_builds_openrouter():
    cfg = LLMConfig(provider="openrouter", model="google/gemini-2.5-flash-lite")
    assert isinstance(build_llm(cfg, {"OPENROUTER_API_KEY": "K"}), OpenRouterLLM)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        build_llm(cfg, {})
