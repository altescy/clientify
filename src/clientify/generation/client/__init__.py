"""Client code generation module.

This module provides the generate_client() function that generates
type-safe synchronous and asynchronous HTTP client code from OpenAPI
operations.

The generated code includes:
- Backend Protocol definitions for dependency injection
- TypedDict classes for request parameters
- Response type aliases with proper generic types
- SyncClient and AsyncClient classes with typed HTTP methods
- A create() helper function for backend auto-detection
"""

from __future__ import annotations

from ...ir import OperationIR
from ..emitter import TypeEmitter
from ..profile import GenerationProfile
from .context import ClientContext, ClientOutput
from .helpers import group_operations, import_insert_index, method_counts, uses_streaming
from .maps import emit_accept_types_map, emit_expected_statuses_map, emit_request_content_types_map
from .methods import (
    emit_async_overload,
    emit_create_helper,
    emit_method_call,
    emit_sync_overload,
    emit_typed_method_impl,
)
from .params import emit_param_types
from .protocols import emit_backend_protocols, emit_client_errors
from .response import emit_response_aliases
from .templates import emit_client_init, emit_request_impl

__all__ = [
    "generate_client",
    "ClientOutput",
    "ClientContext",
]


def generate_client(
    operations: list[OperationIR],
    schemas: list[str],
    profile: GenerationProfile,
) -> ClientOutput:
    """Generate client code from OpenAPI operations.

    Args:
        operations: List of parsed OpenAPI operations
        schemas: List of schema names used in operations
        profile: Generation profile controlling Python version features

    Returns:
        ClientOutput containing the generated client code
    """
    emitter = TypeEmitter(profile)
    ctx = ClientContext(profile=profile, emitter=emitter)
    counts = method_counts(operations)
    lines: list[str] = []
    lines.append("# ruff: noqa: F401")
    if profile.use_future_annotations:
        lines.append("from __future__ import annotations")

    ctx.typing_imports.add("overload")
    ctx.typing_imports.add("cast")
    ctx.typing_imports.add("Protocol")
    ctx.typing_imports.add("Literal")
    if not profile.use_pep604:
        ctx.typing_imports.add("Union")

    if profile.use_typing_extensions:
        ctx.typing_extensions_imports.update({"TypedDict", "Required"})
    else:
        ctx.typing_imports.update({"TypedDict", "Required"})

    lines.append("import inspect")
    lines.append("import json")
    lines.append("from urllib.parse import urlencode")
    lines.append("from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator, Mapping")
    if schemas:
        lines.append("from .models import (")
        for name in sorted(set(schemas)):
            lines.append(f"    {name},")
        lines.append(")")
    lines.append("from .types import SuccessResponse, ErrorResponse, JsonValue")
    lines.append("")

    lines.append("RequestUrl = str")
    lines.append("RequestHeaders = Mapping[str, str] | None")
    lines.append("RequestContent = str | bytes | Iterable[bytes] | AsyncIterable[bytes]")
    lines.append("TimeoutType = float | None")
    lines.append("")

    lines.extend(emit_backend_protocols(ctx))
    lines.extend(emit_client_errors())

    for operation in operations:
        lines.extend(emit_param_types(operation, ctx))

    _uses_stream = uses_streaming(operations)
    if _uses_stream:
        pass  # Reserved for future streaming configuration

    lines.extend(emit_response_aliases(operations, ctx))
    lines.extend(emit_expected_statuses_map(operations))
    lines.extend(emit_accept_types_map(operations))
    lines.extend(emit_request_content_types_map(operations))

    lines.append("class SyncClient:")
    if not operations:
        lines.append("    pass")
    else:
        lines.extend(emit_client_init(sync=True))
        lines.extend(emit_request_impl(sync=True))
        for method, method_ops in group_operations(operations).items():
            if counts.get(method, 0) == 1:
                lines.extend(emit_typed_method_impl(method_ops[0], ctx, sync=True))
            else:
                for operation in method_ops:
                    lines.extend(emit_sync_overload(operation, ctx))
                lines.extend(emit_method_call(method, sync=True))
    lines.append("")

    lines.append("class AsyncClient:")
    if not operations:
        lines.append("    pass")
    else:
        lines.extend(emit_client_init(sync=False))
        lines.extend(emit_request_impl(sync=False))
        for method, method_ops in group_operations(operations).items():
            if counts.get(method, 0) == 1:
                lines.extend(emit_typed_method_impl(method_ops[0], ctx, sync=False))
            else:
                for operation in method_ops:
                    lines.extend(emit_async_overload(operation, ctx))
                lines.extend(emit_method_call(method, sync=False))
    lines.append("")

    lines.extend(emit_create_helper(ctx))

    typing_imports = sorted(ctx.typing_imports | emitter.imports)
    if ctx.uses_iterator:
        typing_imports.append("Iterator")
    insert_at = import_insert_index(lines)
    if ctx.typing_extensions_imports:
        lines.insert(
            insert_at,
            f"from typing_extensions import {', '.join(sorted(ctx.typing_extensions_imports))}",
        )
        insert_at += 1

    if typing_imports:
        lines.insert(insert_at, f"from typing import {', '.join(sorted(set(typing_imports)))}")

    return ClientOutput(code="\n".join(lines).rstrip() + "\n")
