from __future__ import annotations

from typing import cast

import pytest

from clientify.backends.aiohttp_backend import AiohttpBackend, AiohttpSessionProtocol
from clientify.backends.httpx_backend import (
    HttpxAsyncBackend,
    HttpxAsyncClientProtocol,
    HttpxBackend,
    HttpxClientProtocol,
)
from clientify.backends.requests_backend import RequestsBackend, RequestsSessionProtocol


class DummyResponse:
    def __init__(self) -> None:
        self.status_code = 201
        self.headers = {"content-type": "application/json"}
        self.content = b"{}"


class DummyHttpxClient:
    def request(self, **_: object) -> DummyResponse:
        return DummyResponse()


class DummyHttpxAsyncClient:
    async def request(self, **_: object) -> DummyResponse:
        return DummyResponse()


class DummyRequestsSession:
    def request(self, **_: object) -> DummyResponse:
        return DummyResponse()


class DummyAiohttpResponse:
    status = 200
    headers = {"content-type": "text/plain"}

    async def read(self) -> bytes:
        return b"ok"

    async def __aenter__(self) -> "DummyAiohttpResponse":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class DummyAiohttpSession:
    def request(self, **_: object) -> DummyAiohttpResponse:
        return DummyAiohttpResponse()


class TestBackends:
    def test_httpx_backend(self) -> None:
        backend = HttpxBackend(cast(HttpxClientProtocol, DummyHttpxClient()))
        status, headers, body = backend.request("GET", "http://example", None, None, None)
        assert status == 201
        assert headers["content-type"] == "application/json"
        assert body == b"{}"

    def test_requests_backend(self) -> None:
        backend = RequestsBackend(cast(RequestsSessionProtocol, DummyRequestsSession()))
        status, headers, body = backend.request("GET", "http://example", None, None, None)
        assert status == 201
        assert headers["content-type"] == "application/json"
        assert body == b"{}"

    @pytest.mark.anyio
    async def test_aiohttp_backend(self) -> None:
        backend = AiohttpBackend(cast(AiohttpSessionProtocol, DummyAiohttpSession()))
        status, headers, body = await backend.request("GET", "http://example", None, None, None)
        assert status == 200
        assert headers["content-type"] == "text/plain"
        assert body == b"ok"

    @pytest.mark.anyio
    async def test_httpx_async_backend(self) -> None:
        backend = HttpxAsyncBackend(cast(HttpxAsyncClientProtocol, DummyHttpxAsyncClient()))
        status, headers, body = await backend.request("GET", "http://example", None, None, None)
        assert status == 201
        assert headers["content-type"] == "application/json"
        assert body == b"{}"
