from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class RequestsResponseProtocol(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes


class RequestsSessionProtocol(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        data: bytes | None,
        timeout: float | None,
    ) -> RequestsResponseProtocol: ...


class RequestsBackend:
    def __init__(self, session: RequestsSessionProtocol) -> None:
        self._session = session

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        body: bytes | None,
        timeout: float | None,
    ) -> tuple[int, dict[str, str], bytes]:
        response = self._session.request(
            method=method,
            url=url,
            headers=headers,
            data=body,
            timeout=timeout,
        )
        return response.status_code, {str(k): str(v) for k, v in response.headers.items()}, response.content
