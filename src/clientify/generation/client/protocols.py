from __future__ import annotations

from .context import ClientContext


def emit_backend_protocols(ctx: ClientContext) -> list[str]:
    """Generate Protocol classes for backend abstraction.

    This generates the Response, SyncResponse, AsyncResponse,
    SyncBackend, and AsyncBackend Protocol classes that allow
    dependency injection of HTTP backends.
    """
    return [
        "class Response(Protocol):",
        "    status_code: int",
        "",
        "    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:",
        "        ...",
        "",
        "    def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:",
        "        ...",
        "",
        "class SyncResponse(Response, Protocol):",
        "    ...",
        "",
        "class AsyncResponse(Response, Protocol):",
        "    ...",
        "",
        "class SyncBackend(Protocol):",
        "    def request(",
        "        self,",
        "        method: str,",
        "        url: RequestUrl,",
        "        *,",
        "        content: RequestContent | None = None,",
        "        headers: RequestHeaders = None,",
        "        timeout: TimeoutType = None,",
        "    ) -> SyncResponse:",
        "        ...",
        "",
        "class AsyncBackend(Protocol):",
        "    async def request(",
        "        self,",
        "        method: str,",
        "        url: RequestUrl,",
        "        *,",
        "        content: RequestContent | None = None,",
        "        headers: RequestHeaders = None,",
        "        timeout: TimeoutType = None,",
        "    ) -> AsyncResponse:",
        "        ...",
        "",
    ]


def emit_client_errors() -> list[str]:
    """Generate client error classes.

    This generates ClientError, TransportError, and DecodeError
    exception classes for error handling in generated clients.
    """
    return [
        "class ClientError(Exception):",
        "    pass",
        "",
        "class TransportError(ClientError):",
        "    pass",
        "",
        "class DecodeError(ClientError):",
        "    pass",
        "",
    ]
