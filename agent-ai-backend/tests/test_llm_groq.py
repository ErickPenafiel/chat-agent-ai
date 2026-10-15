import json

import httpx
import pytest

from src.core.config import LLMConfig
from src.llm.base import LLMError
from src.llm.factory import build_llm
from src.llm.groq import GroqLLM


def _llm(handler):
    return GroqLLM("K", "llama-x", client=httpx.Client(transport=httpx.MockTransport(handler)))


def _ok(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_complete_ok():
    seen = {}

    def handler(req):
        seen["req"] = req
        return _ok(" hola ")

    assert _llm(handler).complete("sys", "usr") == "hola"
    req = seen["req"]
    assert str(req.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer K"
    body = json.loads(req.content)
    assert body["model"] == "llama-x"
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert "response_format" not in body


def test_json_mode():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return _ok("{}")

    _llm(handler).complete("s", "u", json_mode=True)
    assert seen["body"]["response_format"] == {"type": "json_object"}


def test_timeout_maps_to_llm_error():
    def handler(req):
        raise httpx.ReadTimeout("t", request=req)

    with pytest.raises(LLMError):
        _llm(handler).complete("s", "u")


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_errors(status):
    with pytest.raises(LLMError):
        _llm(lambda r: httpx.Response(status, json={"error": {}})).complete("s", "u")


def test_malformed_response():
    with pytest.raises(LLMError):
        _llm(lambda r: httpx.Response(200, json={"choices": []})).complete("s", "u")


def test_stream_chunks():
    sse = "".join(
        f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n" for c in ["Ho", "la"]
    ) + "data: [DONE]\n\n"
    llm = _llm(lambda r: httpx.Response(200, text=sse))
    assert list(llm.stream("s", "u")) == ["Ho", "la"]


def test_stream_http_error():
    with pytest.raises(LLMError):
        list(_llm(lambda r: httpx.Response(429)).stream("s", "u"))


def test_factory_builds_groq():
    llm = build_llm(LLMConfig(provider="groq", model="m"), {"GROQ_API_KEY": "K"})
    assert isinstance(llm, GroqLLM)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        build_llm(LLMConfig(provider="groq", model="m"), {})
