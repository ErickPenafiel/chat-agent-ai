import base64
import shutil
import subprocess

import pytest

from src.core.config import load_tenant_config
from src.core.graph import build_graph
from src.llm.base import LLMError, LLMProvider
from src.nodes.media import make_media_node


class MediaLLM(LLMProvider):
    """Registra lo recibido y responde según el tipo de adjunto."""

    supports_media = True

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def complete(self, system, user, *, json_mode=False):
        return "ok"

    def complete_media(self, system, user, media):
        self.calls.append((system, media))
        if self.fail:
            raise LLMError("429")
        return "Quiero un café suave" if media[0]["type"] == "input_audio" else "Una bolsa de café"


def _url(mime, raw=b"datos"):
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _state(*media, text=""):
    return {"last_user_message": text, "media": [dict(m) for m in media]}


AUDIO = {"type": "audio", "url": _url("audio/wav")}
IMAGE = {"type": "image", "url": _url("image/png")}


def test_audio_becomes_transcript_and_media_is_dropped():
    llm = MediaLLM()
    out = make_media_node(llm)(_state(AUDIO))
    assert out == {"transcript": "Quiero un café suave", "media": []}
    part = llm.calls[0][1][0]
    assert part["input_audio"]["format"] == "wav" and part["input_audio"]["data"] == base64.b64encode(b"datos").decode()


def test_image_is_described_as_a_note():
    out = make_media_node(MediaLLM())(_state(IMAGE))
    assert out["transcript"] == "[El cliente envió una imagen: Una bolsa de café]"


def test_text_audio_and_image_are_combined():
    out = make_media_node(MediaLLM())(_state(AUDIO, IMAGE, text="Mira esto"))
    assert out["transcript"].splitlines() == [
        "Mira esto", "Quiero un café suave", "[El cliente envió una imagen: Una bolsa de café]"
    ]


def test_https_image_url_is_passed_through():
    llm = MediaLLM()
    make_media_node(llm)(_state({"type": "image", "url": "https://x.test/a.jpg"}))
    assert llm.calls[0][1][0]["image_url"]["url"] == "https://x.test/a.jpg"


@pytest.mark.parametrize("url", [
    "http://x.test/a.jpg", "file:///etc/passwd", "data:text/html;base64,PGI+", "data:image/png;base64,@@@", "",
])
def test_unsafe_or_invalid_image_urls_are_ignored(url):
    llm = MediaLLM()
    out = make_media_node(llm)(_state({"type": "image", "url": url}))
    assert out == {"transcript": None, "media": []} and not llm.calls


def test_oversized_attachment_is_ignored(monkeypatch):
    monkeypatch.setattr("src.nodes.media.MAX_BYTES", 4)
    llm = MediaLLM()
    out = make_media_node(llm)(_state(AUDIO))
    assert out["transcript"] is None and not llm.calls


def test_llm_error_keeps_the_text_and_never_raises():
    out = make_media_node(MediaLLM(fail=True))(_state(AUDIO, text="Hola"))
    assert out == {"transcript": None, "media": []}


def test_provider_without_media_support_is_skipped():
    class TextOnly(LLMProvider):
        def complete(self, system, user, *, json_mode=False):
            return "ok"

    assert make_media_node(TextOnly())(_state(AUDIO))["transcript"] is None
    assert make_media_node(None)(_state(AUDIO))["transcript"] is None
    with pytest.raises(LLMError):
        TextOnly().complete_media("s", "u", [])


def test_only_three_attachments_are_processed():
    llm = MediaLLM()
    make_media_node(llm)(_state(*[IMAGE] * 5))
    assert len(llm.calls[0][1]) == 3


def test_transcript_is_capped_to_max_chars():
    out = make_media_node(MediaLLM(), max_chars=10)(_state(AUDIO))
    assert out["transcript"] == "Quiero un "


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no está instalado")
def test_browser_audio_is_converted_to_wav():
    tone = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", "-f", "ogg", "pipe:1"],
        capture_output=True, check=True,
    ).stdout
    llm = MediaLLM()
    out = make_media_node(llm)(_state({"type": "audio", "url": _url("audio/ogg; codecs=opus", tone)}))
    assert out["transcript"]
    sent = llm.calls[0][1][0]["input_audio"]
    assert sent["format"] == "wav" and base64.b64decode(sent["data"])[:4] == b"RIFF"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no está instalado")
def test_undecodable_audio_is_ignored():
    llm = MediaLLM()
    out = make_media_node(llm)(_state({"type": "audio", "url": _url("audio/webm", b"no es audio")}))
    assert out["transcript"] is None and not llm.calls


def test_graph_uses_the_transcript_as_the_customer_message():
    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.media_enabled = True
    seen = []
    graph = build_graph(cfg, classifier=lambda m, e: seen.append(m) or "chat", llm=MediaLLM(), prompts=_Prompts())
    out = graph.invoke({"channel": "web", "user_id": "u", "last_user_message": "", "media": [dict(AUDIO)]})
    assert seen == ["Quiero un café suave"] and out["media"] == []


class _Prompts:
    """PromptStore mínimo: el nodo de respuesta pide plantillas por nombre."""

    def get(self, *a, **k):
        return "{}"

    def __getattr__(self, name):
        return lambda *a, **k: "{}"
