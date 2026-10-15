"""Cliente httpx con reintentos para errores transitorios (429, 5xx, red) de los proveedores de LLM."""

import time

import httpx

_RETRY_STATUS = {429, 500, 502, 503, 504}


class RetryTransport(httpx.BaseTransport):
    def __init__(self, retries: int = 2, backoff: float = 0.5, inner: httpx.BaseTransport | None = None) -> None:
        self._inner = inner or httpx.HTTPTransport()
        self._retries = retries
        self._backoff = backoff

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        for attempt in range(self._retries + 1):
            last = attempt == self._retries
            try:
                response = self._inner.handle_request(request)
            except (httpx.TransportError, httpx.TimeoutException):
                if last:
                    raise
            else:
                if response.status_code not in _RETRY_STATUS or last:
                    return response
                response.close()
            time.sleep(self._backoff * 2**attempt)
        raise AssertionError("inalcanzable")

    def close(self) -> None:
        self._inner.close()


def make_client(timeout: float) -> httpx.Client:
    return httpx.Client(timeout=timeout, transport=RetryTransport())
