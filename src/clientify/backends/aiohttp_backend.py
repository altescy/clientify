from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class AiohttpResponseProtocol(Protocol):
    status: int
    headers: Mapping[str, str]

    async def read(self) -> bytes: ...

    async def __aenter__(self) -> "AiohttpResponseProtocol": ...

    async def __aexit__(self, *_: object) -> None: ...


class AiohttpSessionProtocol(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        data: bytes | None,
        timeout: float | None,
    ) -> AiohttpResponseProtocol: ...


class AiohttpBackend:
    def __init__(self, session: AiohttpSessionProtocol) -> None:
        self._session = session

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        body: bytes | None,
        timeout: float | None,
    ) -> tuple[int, dict[str, str], bytes]:
        async with self._session.request(
            method=method,
            url=url,
            headers=headers,
            data=body,
            timeout=timeout,
        ) as response:
            data = await response.read()
            return response.status, {str(k): str(v) for k, v in response.headers.items()}, data
