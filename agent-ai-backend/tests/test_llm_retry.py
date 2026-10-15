import httpx

from src.llm.retry import RetryTransport


class _Flaky(httpx.BaseTransport):
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def handle_request(self, request):
        self.calls += 1
        return httpx.Response(self.statuses.pop(0), request=request)


def _client(statuses):
    inner = _Flaky(statuses)
    return httpx.Client(transport=RetryTransport(backoff=0, inner=inner)), inner


def test_reintenta_429_y_503_hasta_exito():
    client, inner = _client([429, 503, 200])
    assert client.get("http://x").status_code == 200
    assert inner.calls == 3


def test_no_reintenta_errores_de_cliente():
    client, inner = _client([401])
    assert client.get("http://x").status_code == 401
    assert inner.calls == 1


def test_devuelve_el_ultimo_error_si_se_agotan_reintentos():
    client, inner = _client([503, 503, 503])
    assert client.get("http://x").status_code == 503
    assert inner.calls == 3
