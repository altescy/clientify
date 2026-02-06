from __future__ import annotations

from ...ir import OperationIR
from .context import ClientContext
from .helpers import operation_name
from .response import (
    expected_statuses_annotation,
    operation_response_alias,
    optional_type,
    request_body_annotation,
    request_content_type_annotation,
    request_param_parts,
)


def emit_sync_overload(
    operation: OperationIR,
    ctx: ClientContext,
) -> list[str]:
    """Generate a sync method overload for an operation."""
    signature, response_alias = build_method_signature(
        operation,
        ctx,
        literal_url=True,
        sync=True,
        optional_default="...",
    )
    return [
        "    @overload",
        f"    def {operation.method}(self, {signature}) -> {response_alias}:",
        "        ...",
        "",
    ]


def emit_async_overload(
    operation: OperationIR,
    ctx: ClientContext,
) -> list[str]:
    """Generate an async method overload for an operation."""
    signature, response_alias = build_method_signature(
        operation,
        ctx,
        literal_url=True,
        sync=False,
        optional_default="...",
    )
    return [
        "    @overload",
        f"    async def {operation.method}(self, {signature}) -> {response_alias}:",
        "        ...",
        "",
    ]


def build_method_signature(
    operation: OperationIR,
    ctx: ClientContext,
    literal_url: bool,
    sync: bool,
    optional_default: str,
) -> tuple[str, str]:
    """Build the method signature for an operation."""
    op_name = operation_name(operation.method, operation.path)
    params_type = f"{op_name}Params"
    url_part = f"Literal[{operation.path!r}]" if literal_url else "str"
    params_annotation = optional_type(params_type, ctx.profile)
    response_alias = operation_response_alias(operation, sync=sync)
    body_annotation = request_body_annotation(operation, ctx)
    content_type_annotation = request_content_type_annotation(operation, ctx)
    expected_annotation = expected_statuses_annotation()
    body_part, content_type_part = request_param_parts(
        operation.request_body,
        body_annotation,
        content_type_annotation,
        ctx.profile,
        optional_default,
    )
    param_parts = [
        f"url: {url_part}",
        "*",
        f"params: {params_annotation} = {optional_default}",
    ]
    param_parts.append(body_part)
    param_parts.append(content_type_part)
    param_parts.append(f"expected_statuses: {expected_annotation} = {optional_default}")
    param_parts.append(f"timeout: float | None = {optional_default}")
    signature = ", ".join(param_parts)
    return signature, response_alias


def emit_typed_method_impl(
    operation: OperationIR,
    ctx: ClientContext,
    sync: bool,
) -> list[str]:
    """Generate a typed method implementation for an operation."""
    signature, response_alias = build_method_signature(
        operation,
        ctx,
        literal_url=True,
        sync=sync,
        optional_default="None",
    )
    method = operation.method
    if sync:
        return [
            f"    def {method}(self, {signature}) -> {response_alias}:",
            "        return cast(",
            f"            {response_alias},",
            "            self.request(",
            f"            '{method.upper()}',",
            "            url,",
            "            params=params,",
            "            body=body,",
            "            content_type=content_type,",
            "            expected_statuses=expected_statuses,",
            "            timeout=timeout,",
            "            ),",
            "        )",
            "",
        ]
    return [
        f"    async def {method}(self, {signature}) -> {response_alias}:",
        "        return cast(",
        f"            {response_alias},",
        "            await self.request(",
        f"            '{method.upper()}',",
        "            url,",
        "            params=params,",
        "            body=body,",
        "            content_type=content_type,",
        "            expected_statuses=expected_statuses,",
        "            timeout=timeout,",
        "            ),",
        "        )",
        "",
    ]


def emit_method_call(method: str, sync: bool) -> list[str]:
    """Generate a generic method implementation for multiple endpoints."""
    if sync:
        return [
            f"    def {method}(",
            "        self,",
            "        url: str,",
            "        *,",
            "        params: object | None = None,",
            "        body: object | None = None,",
            "        content_type: str | None = None,",
            "        expected_statuses: set[str] | None = None,",
            "        timeout: float | None = None,",
            "    ) -> SuccessResponse[object] | ErrorResponse[object]:",
            "        return self.request(",
            f"            '{method.upper()}',",
            "            url,",
            "            params=params,",
            "            body=body,",
            "            content_type=content_type,",
            "            expected_statuses=expected_statuses,",
            "            timeout=timeout,",
            "        )",
            "",
        ]
    return [
        f"    async def {method}(",
        "        self,",
        "        url: str,",
        "        *,",
        "        params: object | None = None,",
        "        body: object | None = None,",
        "        content_type: str | None = None,",
        "        expected_statuses: set[str] | None = None,",
        "        timeout: float | None = None,",
        "    ) -> SuccessResponse[object] | ErrorResponse[object]:",
        "        return await self.request(",
        f"            '{method.upper()}',",
        "            url,",
        "            params=params,",
        "            body=body,",
        "            content_type=content_type,",
        "            expected_statuses=expected_statuses,",
        "            timeout=timeout,",
        "        )",
        "",
    ]


def emit_create_helper(ctx: ClientContext) -> list[str]:
    """Generate the create() helper function."""
    return [
        "@overload",
        "def create(",
        "    base_url: str,",
        "    backend: SyncBackend,",
        "    headers: Mapping[str, str] | None = None,",
        "    raise_on_unexpected_status: bool = True,",
        ") -> SyncClient:",
        "    ...",
        "",
        "@overload",
        "def create(",
        "    base_url: str,",
        "    backend: AsyncBackend,",
        "    headers: Mapping[str, str] | None = None,",
        "    raise_on_unexpected_status: bool = True,",
        ") -> AsyncClient:",
        "    ...",
        "",
        "def create(",
        "    base_url: str,",
        "    backend: SyncBackend | AsyncBackend,",
        "    headers: Mapping[str, str] | None = None,",
        "    raise_on_unexpected_status: bool = True,",
        ") -> SyncClient | AsyncClient:",
        "    request = getattr(backend, 'request', None)",
        "    if request and inspect.iscoroutinefunction(request):",
        "        return AsyncClient(",
        "            base_url=base_url,",
        "            backend=cast(AsyncBackend, backend),",
        "            headers=headers,",
        "            raise_on_unexpected_status=raise_on_unexpected_status,",
        "        )",
        "    if request:",
        "        return SyncClient(",
        "            base_url=base_url,",
        "            backend=cast(SyncBackend, backend),",
        "            headers=headers,",
        "            raise_on_unexpected_status=raise_on_unexpected_status,",
        "        )",
        "    raise TypeError('backend must implement SyncBackend or AsyncBackend')",
        "",
    ]
