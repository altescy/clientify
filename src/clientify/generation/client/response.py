from __future__ import annotations

from typing import cast

from ...ir import MediaTypeIR, OperationIR, RequestBodyIR, ResponseIR
from ...openapi import SchemaObject
from ..profile import GenerationProfile
from .context import ClientContext
from .helpers import operation_name


def emit_response_aliases(operations: list[OperationIR], ctx: ClientContext) -> list[str]:
    """Generate type aliases for operation responses."""
    lines: list[str] = []
    for operation in operations:
        sync_alias = operation_response_alias(operation, sync=True)
        async_alias = operation_response_alias(operation, sync=False)
        sync_value = _operation_return_type(operation, ctx, "Iterator[str]")
        async_value = _operation_return_type(operation, ctx, "AsyncIterator[str]")
        lines.append(f"{sync_alias} = {sync_value}")
        lines.append(f"{async_alias} = {async_value}")
    if lines:
        lines.append("")
    return lines


def operation_response_alias(operation: OperationIR, sync: bool) -> str:
    """Get the response type alias name for an operation."""
    op_name = operation_name(operation.method, operation.path)
    suffix = "Response" if sync else "AsyncResponse"
    return f"{op_name}{suffix}"


def request_body_annotation(operation: OperationIR, ctx: ClientContext) -> str | None:
    """Get the type annotation for a request body."""
    request_body = operation.request_body
    if request_body is None:
        return None
    body_type = _request_body_union(request_body, ctx)
    if request_body.required:
        return body_type
    return optional_type(body_type, ctx.profile)


def request_content_type_annotation(
    operation: OperationIR,
    ctx: ClientContext,
) -> str | None:
    """Get the Literal type annotation for content types."""
    request_body = operation.request_body
    if request_body is None:
        return None
    content_types = [media.content_type for media in request_body.content]
    if len(content_types) <= 1:
        return None
    ctx.typing_imports.add("Literal")
    literals = ", ".join(repr(value) for value in sorted(content_types))
    return f"Literal[{literals}]"


def _operation_return_type(
    operation: OperationIR,
    ctx: ClientContext,
    stream_iterator: str,
) -> str:
    """Get the full return type for an operation."""
    success_types: list[str] = []
    error_types: list[str] = []
    if not operation.responses:
        return _response_union("SuccessResponse[object]", "ErrorResponse[object]", ctx)
    for response in operation.responses:
        response_type = _response_body_union(response, ctx, stream_iterator)
        wrapper = (
            f"SuccessResponse[{response_type}]"
            if _is_success_status(response.status)
            else f"ErrorResponse[{response_type}]"
        )
        if _is_success_status(response.status):
            success_types.append(wrapper)
        else:
            error_types.append(wrapper)

    return _response_union(
        union_types(success_types, ctx),
        union_types(error_types, ctx),
        ctx,
    )


def _request_body_union(request_body: RequestBodyIR, ctx: ClientContext) -> str:
    """Get the union type for request body content types."""
    content = request_body.content
    if not content:
        return "JsonValue"
    body_types = [_media_type_body(media, ctx, "Iterator[str]") for media in content]
    return union_types(body_types, ctx)


def _response_body_union(
    response: ResponseIR,
    ctx: ClientContext,
    stream_iterator: str,
) -> str:
    """Get the union type for response body content types."""
    if not response.content:
        return "None"
    media_items = _filter_empty_json_media(response.content)
    body_types = [_media_type_body(media, ctx, stream_iterator) for media in media_items]
    return union_types(body_types, ctx)


def _media_type_body(media: MediaTypeIR, ctx: ClientContext, stream_iterator: str) -> str:
    """Get the Python type for a media type body.

    This function maps content types to their corresponding Python types based on
    how the runtime _decode_body() method processes them.
    """
    if media.content_type == "application/octet-stream":
        return "bytes"

    if media.content_type == "text/event-stream":
        return stream_iterator

    if media.content_type.startswith("application/x-ndjson") or media.content_type.startswith(
        "application/stream+json"
    ):
        if media.schema is not None and isinstance(media.schema, dict) and media.schema != {}:
            if media.schema.get("format") in {"binary", "byte"}:
                return "bytes"
            base = ctx.emitter.emit(cast(SchemaObject, media.schema))
            item_type = ctx.emitter.apply_nullable(base, cast(SchemaObject, media.schema))
            if item_type == "object":
                item_type = "JsonValue"
            return stream_iterator.replace("str", item_type)
        return stream_iterator.replace("str", "JsonValue")

    if media.content_type.startswith("text/plain"):
        return "str"
    if media.content_type.startswith("text/csv"):
        return "str"
    if media.content_type.startswith("application/x-www-form-urlencoded"):
        return "str"

    if media.content_type.startswith("application/json") or media.content_type.endswith("+json"):
        if media.schema is not None and isinstance(media.schema, dict) and media.schema != {}:
            if media.schema.get("format") in {"binary", "byte"}:
                return "bytes"
            base = ctx.emitter.emit(cast(SchemaObject, media.schema))
            nullable_base = ctx.emitter.apply_nullable(base, cast(SchemaObject, media.schema))
            if nullable_base == "object":
                return "JsonValue"
            return nullable_base
        return "JsonValue"

    if media.schema is not None and isinstance(media.schema, dict) and media.schema != {}:
        if media.schema.get("format") in {"binary", "byte"}:
            return "bytes"
        base = ctx.emitter.emit(cast(SchemaObject, media.schema))
        return ctx.emitter.apply_nullable(base, cast(SchemaObject, media.schema))

    return "object"


def union_types(types: list[str], ctx: ClientContext) -> str:
    """Create a union type from a list of types."""
    unique = [item for item in dict.fromkeys(types)]
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    if ctx.profile.use_pep604:
        return " | ".join(unique)
    return f"Union[{', '.join(unique)}]"


def _filter_empty_json_media(media: list[MediaTypeIR]) -> list[MediaTypeIR]:
    """Filter out empty JSON media types when other types exist."""
    if len(media) <= 1:
        return media
    filtered: list[MediaTypeIR] = []
    for item in media:
        if item.content_type == "application/json" and item.schema == {}:
            continue
        filtered.append(item)
    return filtered or media


def _response_union(success: str, error: str, ctx: ClientContext) -> str:
    """Create a union of success and error response types."""
    if success and error:
        return union_types([success, error], ctx)
    if success:
        return success
    return error


def optional_type(base: str, profile: GenerationProfile) -> str:
    """Create an optional type annotation."""
    if profile.use_pep604:
        return f"{base} | None"
    return f"Union[{base}, None]"


def _is_success_status(status: str) -> bool:
    """Check if a status code indicates success."""
    return status.startswith("2")


def expected_statuses_annotation() -> str:
    """Get the type annotation for expected_statuses parameter."""
    return "set[str] | None"


def ensure_optional(value: str, profile: GenerationProfile) -> str:
    """Ensure a type annotation includes None."""
    if "None" in value:
        return value
    if profile.use_pep604:
        return f"{value} | None"
    return f"Union[{value}, None]"


def request_param_parts(
    request_body: RequestBodyIR | None,
    body_annotation: str | None,
    content_type_annotation: str | None,
    profile: GenerationProfile,
    optional_default: str,
) -> tuple[str, str]:
    """Generate the body and content_type parameter parts for a method signature."""
    if request_body is None:
        return f"body: None = {optional_default}", f"content_type: str | None = {optional_default}"

    if body_annotation is None:
        body_type = "None"
    elif request_body.required:
        body_type = body_annotation
    else:
        body_type = ensure_optional(body_annotation, profile)

    body_default = "" if request_body.required else f" = {optional_default}"
    body_part = f"body: {body_type}{body_default}"

    if content_type_annotation is None:
        return body_part, f"content_type: str | None = {optional_default}"

    content_default = "" if request_body.required else f" = {optional_default}"
    content_part = f"content_type: {content_type_annotation}{content_default}"
    return body_part, content_part
