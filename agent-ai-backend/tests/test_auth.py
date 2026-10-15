import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.app import create_app
from src.auth.deps import is_admin
from src.auth.firebase import FirebaseVerifier, InvalidToken
from src.channels.web import WebChannel
from src.core.config import AuthConfig, CorsConfig, load_tenant_config
from tests.helpers import PROJECT, make_token, make_verifier, wrong_key_token

ADMIN_EMAIL = "admin@example.com"


def make_app(cors=None, channels=None, **auth_over):
    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.auth = AuthConfig(mode="firebase", firebase_project_id=PROJECT, admin_emails=[ADMIN_EMAIL], **auth_over)
    if cors:
        cfg.cors = CorsConfig(allowed_origins=cors)
    return create_app(cfg, "sqlite:///:memory:", auth_verifier=make_verifier(), channels=channels)


@pytest.fixture
def client():
    return TestClient(make_app())


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- config ----------
def test_config_validation():
    with pytest.raises(ValidationError):
        AuthConfig(mode="firebase")  # falta project id
    assert AuthConfig(mode="firebase", firebase_project_id="p", admin_emails=[" A@X.com "]).admin_emails == ["a@x.com"]
    with pytest.raises(ValidationError):
        CorsConfig(allowed_origins=["*"])
    assert CorsConfig(allowed_origins=["http://a.test/"]).allowed_origins == ["http://a.test"]


def test_auth_block_is_required():
    import yaml
    from src.core.config import TenantConfig

    raw = yaml.safe_load(open("config/tenant.example.yaml", encoding="utf-8"))
    del raw["auth"]
    with pytest.raises(ValidationError):
        TenantConfig.model_validate(raw)


def test_disabled_mode_fails_closed_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("ALLOW_INSECURE_AUTH")
    with pytest.raises(RuntimeError, match="ALLOW_INSECURE_AUTH"):
        create_app(load_tenant_config("config/tenant.example.yaml"), "sqlite:///:memory:")


def test_disabled_mode_with_opt_in_is_open():
    app = create_app(load_tenant_config("config/tenant.example.yaml"), "sqlite:///:memory:")
    assert TestClient(app).get("/knowledge-blocks").status_code == 200


# ---------- verificador ----------
def test_verifier_accepts_valid_token():
    assert make_verifier().verify(make_token())["email"] == ADMIN_EMAIL


@pytest.mark.parametrize("token", [
    make_token(exp=int(time.time()) - 3600),                      # expirado
    make_token(aud="otro-proyecto"),                              # audiencia ajena
    make_token(iss="https://securetoken.google.com/otro"),        # emisor ajeno
    make_token(sub=None),                                         # sin sub
    make_token(sub=""),                                           # sub vacío
    wrong_key_token(),                                            # firmado con otra clave
    "no.es.un.jwt",
    "",
])
def test_verifier_rejects_bad_tokens(token):
    with pytest.raises(InvalidToken):
        make_verifier().verify(token)


def test_verifier_rejects_unsigned_and_hs256_tokens():
    import jwt

    now = int(time.time())
    claims = {"iss": f"https://securetoken.google.com/{PROJECT}", "aud": PROJECT, "sub": "x", "iat": now, "exp": now + 99}
    unsigned = jwt.encode(claims, None, algorithm="none")
    hs = jwt.encode(claims, "secreto-compartido-de-32-bytes-minimo!", algorithm="HS256")
    for t in (unsigned, hs):
        with pytest.raises(InvalidToken):
            make_verifier().verify(t)


def test_verifier_key_lookup_failure_is_invalid_token():
    def boom(token):
        raise RuntimeError("sin red")

    with pytest.raises(InvalidToken):
        FirebaseVerifier(PROJECT, key_resolver=boom).verify(make_token())


# ---------- autorización ----------
def test_is_admin_rules():
    cfg = AuthConfig(mode="firebase", firebase_project_id="p", admin_emails=[ADMIN_EMAIL])
    assert is_admin(cfg, {"admin": True})
    assert is_admin(cfg, {"email": "ADMIN@example.com", "email_verified": True})
    assert not is_admin(cfg, {"email": ADMIN_EMAIL, "email_verified": False})
    assert not is_admin(cfg, {"email": "otro@example.com", "email_verified": True})
    assert not is_admin(cfg, {"admin": "true"})  # solo el booleano True
    assert not is_admin(cfg, {})
    relaxed = AuthConfig(mode="firebase", firebase_project_id="p", admin_emails=[ADMIN_EMAIL], require_email_verified=False)
    assert is_admin(relaxed, {"email": ADMIN_EMAIL})


# ---------- API ----------
ADMIN_ROUTES = ["/knowledge-blocks", "/knowledge-blocks/orphans", "/prompts", "/connectors",
                "/conversation-outcomes", "/improvement-proposals", "/auth/me", "/channels/web/outbox/u1"]


@pytest.mark.parametrize("path", ADMIN_ROUTES)
def test_admin_routes_require_token(client, path):
    r = client.get(path)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    assert client.get(path, headers=bearer("basura")).status_code == 401
    assert client.get(path, headers=bearer(wrong_key_token())).status_code == 401
    assert client.get(path, headers={"Authorization": f"Basic {make_token()}"}).status_code == 401


@pytest.mark.parametrize("path", ADMIN_ROUTES)
def test_admin_routes_accept_admin(client, path):
    assert client.get(path, headers=bearer(make_token())).status_code in (200, 404)  # 404 solo si el recurso no existe
    assert client.get("/auth/me", headers=bearer(make_token())).json() == {"uid": "uid-1", "email": ADMIN_EMAIL}


def test_valid_token_but_not_admin_is_403(client):
    for tok in (make_token(email="otro@example.com"), make_token(email_verified=False), make_token(email=None)):
        assert client.get("/knowledge-blocks", headers=bearer(tok)).status_code == 403


def test_admin_claim_grants_access(client):
    tok = make_token(email="otro@example.com", admin=True)
    assert client.get("/knowledge-blocks", headers=bearer(tok)).status_code == 200


def test_write_endpoints_protected(client):
    body = {"title": "t", "content": "c", "intents": ["chat"]}
    assert client.post("/knowledge-blocks", json=body).status_code == 401
    assert client.put("/prompts/tone", json={"text": "x"}).status_code == 401
    assert client.post("/improvement-proposals/1/approve").status_code == 401
    assert client.post("/knowledge-blocks", json=body, headers=bearer(make_token())).status_code == 201


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_mock_channel_webhook_needs_admin_but_real_channels_do_not():
    from tests.test_channels import _payload, _sign, _wa

    app = make_app(channels={"web": WebChannel(), "whatsapp_cloud_api": _wa()})
    c = TestClient(app)
    web = {"user_id": "u", "text": "hola"}
    assert c.post("/channels/web/webhook", json=web).status_code == 401  # consume LLM: no puede ser público
    assert c.post("/channels/web/webhook", json=web, headers=bearer(make_token())).status_code == 200
    body = _payload([{"from": "591700", "id": "m1", "type": "text", "text": {"body": "hola"}}])
    assert c.post("/channels/whatsapp_cloud_api/webhook", content=body, headers=_sign(body)).status_code == 200


# ---------- CORS ----------
ORIGIN = "http://localhost:5173"


def preflight(c, origin, path="/knowledge-blocks"):
    return c.options(path, headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                    "Access-Control-Request-Headers": "authorization,content-type"})


def test_cors_allows_configured_origin_only():
    c = TestClient(make_app(cors=[ORIGIN]))
    ok = preflight(c, ORIGIN)
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == ORIGIN
    assert "authorization" in ok.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in ok.headers
    bad = preflight(c, "http://evil.example")
    assert bad.status_code == 400 and "access-control-allow-origin" not in bad.headers
    r = c.get("/knowledge-blocks", headers={"Origin": ORIGIN, **bearer(make_token())})
    assert r.headers["access-control-allow-origin"] == ORIGIN


def test_no_cors_headers_when_not_configured(client):
    r = preflight(client, ORIGIN)
    assert "access-control-allow-origin" not in r.headers
