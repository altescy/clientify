from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class HttpxResponseProtocol(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes


class HttpxClientProtocol(Protocol):
    def request(self, method: str, url: str, **kwargs: object) -> HttpxResponseProtocol: ...


class HttpxAsyncClientProtocol(Protocol):
    async def request(self, method: str, url: str, **kwargs: object) -> HttpxResponseProtocol: ...


class HttpxBackend:
    def __init__(self, client: HttpxClientProtocol) -> None:
        self._client = client

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        body: bytes | None,
        timeout: float | None,
    ) -> tuple[int, dict[str, str], bytes]:
        response = self._client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            timeout=timeout,
        )
        return response.status_code, {str(k): str(v) for k, v in response.headers.items()}, response.content


class HttpxAsyncBackend:
    def __init__(self, client: HttpxAsyncClientProtocol) -> None:
        self._client = client

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        body: bytes | None,
        timeout: float | None,
    ) -> tuple[int, dict[str, str], bytes]:
        response = await self._client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            timeout=timeout,
        )
        return response.status_code, {str(k): str(v) for k, v in response.headers.items()}, response.content
