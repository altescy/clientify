from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ..ir import MediaTypeIR, OperationIR, ParameterIR, RequestBodyIR, ResponseIR
from ..openapi import SchemaObject
from .emitter import TypeEmitter
from .profile import GenerationProfile


@dataclass
class ClientOutput:
    code: str


@dataclass
class ClientContext:
    profile: GenerationProfile
    emitter: TypeEmitter
    typing_imports: set[str] = field(default_factory=set)
    typing_extensions_imports: set[str] = field(default_factory=set)
    uses_iterator: bool = False


def generate_client(
    operations: list[OperationIR],
    schemas: list[str],
    profile: GenerationProfile,
) -> ClientOutput:
    emitter = TypeEmitter(profile)
    ctx = ClientContext(profile=profile, emitter=emitter)
    lines: list[str] = []
    lines.append("# ruff: noqa: F401")
    if profile.use_future_annotations:
        lines.append("from __future__ import annotations")

    ctx.typing_imports.add("TYPE_CHECKING")
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
    lines.append("from collections.abc import AsyncIterator, Iterable, Iterator, Mapping")
    if schemas:
        lines.append("from .models import (")
        for name in sorted(set(schemas)):
            lines.append(f"    {name},")
        lines.append(")")
    lines.append("from .types import SuccessResponse, ErrorResponse, JsonValue")
    lines.append("")

    lines.append("RequestUrl = str")
    lines.append("RequestHeaders = Mapping[str, str] | None")
    lines.append("RequestContent = str | bytes | Iterable[bytes] | None")
    lines.append("TimeoutType = float | None")
    lines.append("")

    lines.extend(_emit_backend_protocols(ctx))
    lines.extend(_emit_client_errors())

    for operation in operations:
        lines.extend(_emit_param_types(operation, ctx))

    uses_stream = _uses_streaming(operations)
    if uses_stream:
        pass

    lines.extend(_emit_response_aliases(operations, ctx))
    lines.extend(_emit_expected_statuses_map(operations))
    lines.extend(_emit_accept_types_map(operations))
    lines.extend(_emit_request_content_types_map(operations))

    lines.append("class SyncClient:")
    if not operations:
        lines.append("    pass")
    else:
        lines.extend(_emit_client_init(sync=True))
        lines.append("    if TYPE_CHECKING:")
        for operation in operations:
            lines.extend(_indent_lines(_emit_sync_overload(operation, ctx)))
        lines.extend(_emit_method_impls(operations, ctx, sync=True))
    lines.append("")

    lines.append("class AsyncClient:")
    if not operations:
        lines.append("    pass")
    else:
        lines.extend(_emit_client_init(sync=False))
        lines.append("    if TYPE_CHECKING:")
        for operation in operations:
            lines.extend(_indent_lines(_emit_async_overload(operation, ctx)))
        lines.extend(_emit_method_impls(operations, ctx, sync=False))
    lines.append("")

    lines.extend(_emit_create_helper(ctx))

    typing_imports = sorted(ctx.typing_imports | emitter.imports)
    if ctx.uses_iterator:
        typing_imports.append("Iterator")
    insert_at = _import_insert_index(lines)
    if ctx.typing_extensions_imports:
        lines.insert(
            insert_at,
            f"from typing_extensions import {', '.join(sorted(ctx.typing_extensions_imports))}",
        )
        insert_at += 1

    if typing_imports:
        lines.insert(insert_at, f"from typing import {', '.join(sorted(set(typing_imports)))}")

    return ClientOutput(code="\n".join(lines).rstrip() + "\n")


def _emit_sync_overload(operation: OperationIR, ctx: ClientContext) -> list[str]:
    op_name = _operation_name(operation.method, operation.path)
    params_type = f"{op_name}Params"
    url_literal = f"Literal[{operation.path!r}]"
    params_annotation = _optional_type(params_type, ctx.profile)
    response_alias = _operation_response_alias(operation, sync=True)
    body_annotation = _request_body_annotation(operation, ctx)
    content_type_annotation = _request_content_type_annotation(operation, ctx)
    expected_annotation = _expected_statuses_annotation()
    body_part, content_type_part = _request_param_parts(
        operation.request_body,
        body_annotation,
        content_type_annotation,
        ctx.profile,
    )
    param_parts = [f"url: {url_literal}", "*", f"params: {params_annotation} = ..."]
    param_parts.append(body_part)
    param_parts.append(content_type_part)
    param_parts.append(f"expected_statuses: {expected_annotation} = ...")
    param_parts.append("timeout: float | None = ...")

    signature = ", ".join(param_parts)
    return [
        "    @overload",
        f"    def {operation.method}(self, {signature}) -> {response_alias}:",
        "        ...",
        "",
    ]


def _emit_async_overload(operation: OperationIR, ctx: ClientContext) -> list[str]:
    op_name = _operation_name(operation.method, operation.path)
    params_type = f"{op_name}Params"
    url_literal = f"Literal[{operation.path!r}]"
    params_annotation = _optional_type(params_type, ctx.profile)
    response_alias = _operation_response_alias(operation, sync=False)
    body_annotation = _request_body_annotation(operation, ctx)
    content_type_annotation = _request_content_type_annotation(operation, ctx)
    expected_annotation = _expected_statuses_annotation()
    body_part, content_type_part = _request_param_parts(
        operation.request_body,
        body_annotation,
        content_type_annotation,
        ctx.profile,
    )
    param_parts = [f"url: {url_literal}", "*", f"params: {params_annotation} = ..."]
    param_parts.append(body_part)
    param_parts.append(content_type_part)
    param_parts.append(f"expected_statuses: {expected_annotation} = ...")
    param_parts.append("timeout: float | None = ...")

    signature = ", ".join(param_parts)
    return [
        "    @overload",
        f"    async def {operation.method}(self, {signature}) -> {response_alias}:",
        "        ...",
        "",
    ]


def _emit_param_types(operation: OperationIR, ctx: ClientContext) -> list[str]:
    op_name = _operation_name(operation.method, operation.path)
    by_location: dict[str, list[ParameterIR]] = {"path": [], "query": [], "header": [], "cookie": []}
    for param in operation.parameters:
        if param.location in by_location:
            by_location[param.location].append(param)

    accept_literals = _accept_literals(operation)
    if accept_literals:
        by_location["header"].append(
            ParameterIR(
                name="accept",
                location="header",
                required=False,
                schema=None,
                content=[],
                style=None,
                explode=None,
                default=None,
            )
        )

    lines: list[str] = []
    for location, params in by_location.items():
        class_name = f"{op_name}{location.title()}Params"
        lines.extend(_emit_location_params(class_name, params, ctx, accept_literals))

    params_class = f"{op_name}Params"
    lines.append(f"class {params_class}(TypedDict, total=False):")
    for location in ("path", "query", "header", "cookie"):
        lines.append(f"    {location}: {op_name}{location.title()}Params")
    lines.append("")
    return lines


def _emit_location_params(
    class_name: str,
    params: list[ParameterIR],
    ctx: ClientContext,
    accept_literals: list[str] | None = None,
) -> list[str]:
    items: list[str] = []
    for param in params:
        param_type = _param_type(param, ctx, accept_literals)
        if _is_required(param):
            param_type = f"Required[{param_type}]"
        items.append(f"        {param.name!r}: {param_type},")

    lines = [f"{class_name} = TypedDict(", f"    {class_name!r},", "    {"]
    if items:
        lines.extend(items)
    lines.extend(["    },", "    total=False,", ")", ""])
    return lines


def _param_type(
    param: ParameterIR,
    ctx: ClientContext,
    accept_literals: list[str] | None = None,
) -> str:
    if param.name == "accept" and accept_literals:
        ctx.typing_imports.add("Literal")
        literals = ", ".join(repr(value) for value in accept_literals)
        return f"Literal[{literals}]"
    schema = param.schema
    if schema is None and param.content:
        schema = param.content[0].schema
    if schema is None:
        return "JsonValue"
    if not isinstance(schema, dict):
        return "JsonValue"
    base = ctx.emitter.emit(cast(SchemaObject, schema))
    return ctx.emitter.apply_nullable(base, cast(SchemaObject, schema))


def _is_required(param: ParameterIR) -> bool:
    if param.default is not None:
        return False
    if param.schema and isinstance(param.schema, dict) and "default" in param.schema:
        return False
    return param.required


def _operation_return_type(
    operation: OperationIR,
    ctx: ClientContext,
    stream_iterator: str,
) -> str:
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
        _union_types(success_types, ctx),
        _union_types(error_types, ctx),
        ctx,
    )


def _expected_statuses_annotation() -> str:
    return "set[str] | None"


def _ensure_optional(value: str, profile: GenerationProfile) -> str:
    if "None" in value:
        return value
    if profile.use_pep604:
        return f"{value} | None"
    return f"Union[{value}, None]"


def _request_param_parts(
    request_body: RequestBodyIR | None,
    body_annotation: str | None,
    content_type_annotation: str | None,
    profile: GenerationProfile,
) -> tuple[str, str]:
    if request_body is None:
        return "body: None = ...", "content_type: str | None = ..."

    if body_annotation is None:
        body_type = "None"
    elif request_body.required:
        body_type = body_annotation
    else:
        body_type = _ensure_optional(body_annotation, profile)

    body_default = "" if request_body.required else " = ..."
    body_part = f"body: {body_type}{body_default}"

    if content_type_annotation is None:
        return body_part, "content_type: str | None = ..."

    content_default = "" if request_body.required else " = ..."
    content_part = f"content_type: {content_type_annotation}{content_default}"
    return body_part, content_part


def _emit_response_aliases(operations: list[OperationIR], ctx: ClientContext) -> list[str]:
    lines: list[str] = []
    for operation in operations:
        sync_alias = _operation_response_alias(operation, sync=True)
        async_alias = _operation_response_alias(operation, sync=False)
        sync_value = _operation_return_type(operation, ctx, "Iterator[str]")
        async_value = _operation_return_type(operation, ctx, "AsyncIterator[str]")
        lines.append(f"{sync_alias} = {sync_value}")
        lines.append(f"{async_alias} = {async_value}")
    if lines:
        lines.append("")
    return lines


def _operation_response_alias(operation: OperationIR, sync: bool) -> str:
    op_name = _operation_name(operation.method, operation.path)
    suffix = "Response" if sync else "AsyncResponse"
    return f"{op_name}{suffix}"


def _request_body_annotation(operation: OperationIR, ctx: ClientContext) -> str | None:
    request_body = operation.request_body
    if request_body is None:
        return None
    body_type = _request_body_union(request_body, ctx)
    if request_body.required:
        return body_type
    return _optional_type(body_type, ctx.profile)


def _request_content_type_annotation(
    operation: OperationIR,
    ctx: ClientContext,
) -> str | None:
    request_body = operation.request_body
    if request_body is None:
        return None
    content_types = [media.content_type for media in request_body.content]
    if len(content_types) <= 1:
        return None
    ctx.typing_imports.add("Literal")
    literals = ", ".join(repr(value) for value in sorted(content_types))
    return f"Literal[{literals}]"


def _request_body_union(request_body: RequestBodyIR, ctx: ClientContext) -> str:
    content = request_body.content
    if not content:
        return "JsonValue"
    body_types = [_media_type_body(media, ctx, "Iterator[str]") for media in content]
    return _union_types(body_types, ctx)


def _known_statuses(operation: OperationIR) -> list[str]:
    statuses: list[str] = []
    for response in operation.responses:
        if response.status == "default":
            return []
        if response.status.isdigit():
            statuses.append(response.status)
    unique = [item for item in dict.fromkeys(statuses)]
    return [repr(item) for item in unique]


def _response_body_union(
    response: ResponseIR,
    ctx: ClientContext,
    stream_iterator: str,
) -> str:
    if not response.content:
        return "None"
    media_items = _filter_empty_json_media(response.content)
    body_types = [_media_type_body(media, ctx, stream_iterator) for media in media_items]
    return _union_types(body_types, ctx)


def _media_type_body(media: MediaTypeIR, ctx: ClientContext, stream_iterator: str) -> str:
    if media.content_type == "application/octet-stream":
        return "bytes"
    if media.content_type == "text/event-stream":
        return stream_iterator
    if media.schema is None:
        return "JsonValue"
    if not isinstance(media.schema, dict):
        return "JsonValue"
    if media.content_type.startswith("application/json") and media.schema == {}:
        return "JsonValue"
    if media.schema.get("format") in {"binary", "byte"}:
        return "bytes"
    base = ctx.emitter.emit(cast(SchemaObject, media.schema))
    return ctx.emitter.apply_nullable(base, cast(SchemaObject, media.schema))


def _union_types(types: list[str], ctx: ClientContext) -> str:
    unique = [item for item in dict.fromkeys(types)]
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    if ctx.profile.use_pep604:
        return " | ".join(unique)
    return f"Union[{', '.join(unique)}]"


def _filter_empty_json_media(media: list[MediaTypeIR]) -> list[MediaTypeIR]:
    if len(media) <= 1:
        return media
    filtered: list[MediaTypeIR] = []
    for item in media:
        if item.content_type == "application/json" and item.schema == {}:
            continue
        filtered.append(item)
    return filtered or media


def _response_union(success: str, error: str, ctx: ClientContext) -> str:
    if success and error:
        return _union_types([success, error], ctx)
    if success:
        return success
    return error


def _optional_type(base: str, profile: GenerationProfile) -> str:
    if profile.use_pep604:
        return f"{base} | None"
    return f"Union[{base}, None]"


def _is_success_status(status: str) -> bool:
    return status.startswith("2")


def _operation_name(method: str, path: str) -> str:
    raw = f"{method}_{path}"
    cleaned = []
    prev_underscore = False
    for ch in raw:
        if ch.isalnum():
            cleaned.append(ch.lower())
            prev_underscore = False
        else:
            if not prev_underscore:
                cleaned.append("_")
                prev_underscore = True
    name = "".join(cleaned).strip("_")
    name = name.replace("_", " ").title().replace(" ", "")
    return name


def _accept_literals(operation: OperationIR) -> list[str] | None:
    content_types: set[str] = set()
    for response in operation.responses:
        for media in response.content:
            content_types.add(media.content_type)
    if len(content_types) <= 1:
        return None
    return sorted(content_types)


def _emit_backend_protocols(ctx: ClientContext) -> list[str]:
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
        "        content: RequestContent = None,",
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
        "        content: RequestContent = None,",
        "        headers: RequestHeaders = None,",
        "        timeout: TimeoutType = None,",
        "    ) -> AsyncResponse:",
        "        ...",
        "",
    ]


def _emit_client_errors() -> list[str]:
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


def _emit_client_init(sync: bool) -> list[str]:
    backend_type = "SyncBackend" if sync else "AsyncBackend"
    return [
        "    def __init__(",
        "        self,",
        "        base_url: str,",
        f"        backend: {backend_type},",
        "        headers: Mapping[str, str] | None = None,",
        "        raise_on_unexpected_status: bool = True,",
        "    ) -> None:",
        "        self._base_url = base_url.rstrip('/')",
        "        self._backend = backend",
        "        self._headers = dict(headers or {})",
        "        self._raise_on_unexpected_status = raise_on_unexpected_status",
        "        self._expected_statuses = EXPECTED_STATUSES",
        "        self._accept_types = ACCEPT_TYPES",
        "        self._request_content_types = REQUEST_CONTENT_TYPES",
        "",
        "    def _build_url(",
        "        self,",
        "        path: str,",
        "        path_params: Mapping[str, JsonValue] | None,",
        "        query_params: Mapping[str, JsonValue] | None,",
        "    ) -> str:",
        '        url = f"{self._base_url}{path}"',
        "        if path_params:",
        "            for key, value in path_params.items():",
        "                url = url.replace(f'{{{key}}}', str(value))",
        "        if query_params:",
        "            query = urlencode(query_params, doseq=True)",
        "            if query:",
        '                url = f"{url}?{query}"',
        "        return url",
        "",
        "    def _encode_body(self, body: object | None, content_type: str | None) -> bytes | None:",
        "        if body is None:",
        "            return None",
        "        if isinstance(body, bytes):",
        "            return body",
        "        if content_type and content_type.startswith('text/plain'):",
        "            return str(body).encode('utf-8')",
        "        if content_type and content_type.startswith('application/json'):",
        "            return json.dumps(body).encode('utf-8')",
        "        return json.dumps(body).encode('utf-8')",
        "",
        "    def _decode_body(self, content_type: str, data: bytes) -> object:",
        "        if not content_type:",
        "            return data",
        "        if content_type.startswith('application/json'):",
        "            try:",
        "                return json.loads(data)",
        "            except json.JSONDecodeError as exc:",
        "                raise DecodeError('Failed to decode JSON') from exc",
        "        if content_type.startswith('text/plain'):",
        "            return data.decode('utf-8')",
        "        if content_type.startswith('text/event-stream'):",
        "            return iter(data.decode('utf-8').splitlines())",
        "        return data",
        "",
        "    def _iter_event_stream_lines(self, response: SyncResponse) -> Iterator[str]:",
        "        try:",
        "            iterator = response.iter_bytes()",
        "        except Exception:",
        "            return iter(())",
        "        buffer = ''",
        "        for chunk in iterator:",
        "            buffer += chunk.decode('utf-8')",
        "            while '\\n\\n' in buffer:",
        "                part, buffer = buffer.split('\\n\\n', 1)",
        "                for line in part.splitlines():",
        "                    yield line",
        "        if buffer:",
        "            for line in buffer.splitlines():",
        "                yield line",
        "",
        "    async def _aiter_event_stream_lines(self, response: AsyncResponse) -> AsyncIterator[str]:",
        "        buffer = ''",
        "        async for chunk in response.aiter_bytes():",
        "            buffer += chunk.decode('utf-8')",
        "            while '\\n\\n' in buffer:",
        "                part, buffer = buffer.split('\\n\\n', 1)",
        "                for line in part.splitlines():",
        "                    yield line",
        "        if buffer:",
        "            for line in buffer.splitlines():",
        "                yield line",
        "",
    ]


def _emit_method_impls(
    operations: list[OperationIR],
    ctx: ClientContext,
    sync: bool,
) -> list[str]:
    methods = sorted({operation.method for operation in operations})
    lines: list[str] = []
    if sync:
        lines.extend(
            [
                "    def request(",
                "        self,",
                "        method: str,",
                "        url: str,",
                "        *,",
                "        params: object | None = None,",
                "        body: object | None = None,",
                "        content_type: str | None = None,",
                "        expected_statuses: set[str] | None = None,",
                "        timeout: float | None = None,",
                "    ) -> SuccessResponse[object] | ErrorResponse[object]:",
                "        params_map = params if isinstance(params, Mapping) else {}",
                "        path_params = params_map.get('path') if params_map else None",
                "        query_params = params_map.get('query') if params_map else None",
                "        header_params = params_map.get('header') if params_map else None",
                "        cookie_params = params_map.get('cookie') if params_map else None",
                "        headers = dict(self._headers)",
                "        if header_params:",
                "            headers.update({str(k): str(v) for k, v in header_params.items()})",
                "        if cookie_params:",
                "            cookie_header = '; '.join(",
                '                f"{key}={value}" for key, value in cookie_params.items()',
                "            )",
                "            if cookie_header:",
                "                if 'cookie' not in {k.lower() for k in headers.keys()}:",
                "                    headers['Cookie'] = cookie_header",
                "        if content_type is None:",
                "            content_types = self._request_content_types.get((method, url))",
                "            if content_types and len(content_types) == 1:",
                "                content_type = content_types[0]",
                "        if content_type:",
                "            headers['Content-Type'] = content_type",
                "        if 'accept' not in {k.lower() for k in headers.keys()}:",
                "            accept_types = self._accept_types.get((method, url))",
                "            if accept_types:",
                "                headers['Accept'] = ', '.join(accept_types)",
                "        url = self._build_url(url, path_params, query_params)",
                "        payload = self._encode_body(body, content_type)",
                "        try:",
                "            backend_response = self._backend.request(",
                "                method=method,",
                "                url=url,",
                "                headers=headers,",
                "                content=payload,",
                "                timeout=timeout,",
                "            )",
                "        except Exception as exc:",
                "            backend_name = type(self._backend).__name__",
                "            raise TransportError(f'Backend request failed: {backend_name}') from exc",
                "        response_headers = getattr(backend_response, 'headers', None) or {}",
                "        content_type_header = response_headers.get('content-type', '')",
                "        if content_type_header.startswith('text/event-stream'):",
                "            body_value = self._iter_event_stream_lines(backend_response)",
                "        else:",
                "            data = b''.join(backend_response.iter_bytes())",
                "            body_value = self._decode_body(content_type_header, data)",
                "        if expected_statuses is None:",
                "            expected_statuses = self._expected_statuses.get((method, url))",
                "        if 200 <= backend_response.status_code < 300:",
                "            api_response = SuccessResponse[object]()",
                "            api_response.status = backend_response.status_code",
                "            api_response.headers = response_headers",
                "            api_response.body = body_value",
                "            return api_response",
                "        if self._raise_on_unexpected_status:",
                "            expected = expected_statuses or set()",
                "            if expected and str(backend_response.status_code) not in expected:",
                "                raise ClientError(f'Unexpected status: {backend_response.status_code}')",
                "        api_response = ErrorResponse[object]()",
                "        api_response.status = backend_response.status_code",
                "        api_response.headers = response_headers",
                "        api_response.body = body_value",
                "        return api_response",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "    async def request(",
                "        self,",
                "        method: str,",
                "        url: str,",
                "        *,",
                "        params: object | None = None,",
                "        body: object | None = None,",
                "        content_type: str | None = None,",
                "        expected_statuses: set[str] | None = None,",
                "        timeout: float | None = None,",
                "    ) -> SuccessResponse[object] | ErrorResponse[object]:",
                "        params_map = params if isinstance(params, Mapping) else {}",
                "        path_params = params_map.get('path') if params_map else None",
                "        query_params = params_map.get('query') if params_map else None",
                "        header_params = params_map.get('header') if params_map else None",
                "        cookie_params = params_map.get('cookie') if params_map else None",
                "        headers = dict(self._headers)",
                "        if header_params:",
                "            headers.update({str(k): str(v) for k, v in header_params.items()})",
                "        if cookie_params:",
                "            cookie_header = '; '.join(",
                '                f"{key}={value}" for key, value in cookie_params.items()',
                "            )",
                "            if cookie_header:",
                "                if 'cookie' not in {k.lower() for k in headers.keys()}:",
                "                    headers['Cookie'] = cookie_header",
                "        if content_type is None:",
                "            content_types = self._request_content_types.get((method, url))",
                "            if content_types and len(content_types) == 1:",
                "                content_type = content_types[0]",
                "        if content_type:",
                "            headers['Content-Type'] = content_type",
                "        if 'accept' not in {k.lower() for k in headers.keys()}:",
                "            accept_types = self._accept_types.get((method, url))",
                "            if accept_types:",
                "                headers['Accept'] = ', '.join(accept_types)",
                "        url = self._build_url(url, path_params, query_params)",
                "        payload = self._encode_body(body, content_type)",
                "        try:",
                "            backend_response = await self._backend.request(",
                "                method=method,",
                "                url=url,",
                "                headers=headers,",
                "                content=payload,",
                "                timeout=timeout,",
                "            )",
                "        except Exception as exc:",
                "            backend_name = type(self._backend).__name__",
                "            raise TransportError(f'Backend request failed: {backend_name}') from exc",
                "        response_headers = getattr(backend_response, 'headers', None) or {}",
                "        content_type_header = response_headers.get('content-type', '')",
                "        if content_type_header.startswith('text/event-stream'):",
                "            body_value = self._aiter_event_stream_lines(backend_response)",
                "        else:",
                "            chunks: list[bytes] = []",
                "            async for chunk in backend_response.aiter_bytes():",
                "                chunks.append(chunk)",
                "            data = b''.join(chunks)",
                "            body_value = self._decode_body(content_type_header, data)",
                "        if expected_statuses is None:",
                "            expected_statuses = self._expected_statuses.get((method, url))",
                "        if 200 <= backend_response.status_code < 300:",
                "            api_response = SuccessResponse[object]()",
                "            api_response.status = backend_response.status_code",
                "            api_response.headers = response_headers",
                "            api_response.body = body_value",
                "            return api_response",
                "        if self._raise_on_unexpected_status:",
                "            expected = expected_statuses or set()",
                "            if expected and str(backend_response.status_code) not in expected:",
                "                raise ClientError(f'Unexpected status: {backend_response.status_code}')",
                "        api_response = ErrorResponse[object]()",
                "        api_response.status = backend_response.status_code",
                "        api_response.headers = response_headers",
                "        api_response.body = body_value",
                "        return api_response",
                "",
            ]
        )

    for method in methods:
        if sync:
            lines.extend(
                [
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
            )
        else:
            lines.extend(
                [
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
            )

    return lines


def _emit_create_helper(ctx: ClientContext) -> list[str]:
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


def _indent_lines(lines: list[str]) -> list[str]:
    return [f"    {line}" if line else "" for line in lines]


def _import_insert_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.startswith("from __future__ import"):
            return index + 1
    if lines and lines[0].startswith("# ruff:"):
        return 1
    return 0


def _uses_streaming(operations: list[OperationIR]) -> bool:
    for operation in operations:
        for response in operation.responses:
            for media in response.content:
                if media.content_type == "text/event-stream":
                    return True
    return False


def _emit_expected_statuses_map(operations: list[OperationIR]) -> list[str]:
    entries: list[str] = []
    for operation in operations:
        statuses = _known_statuses(operation)
        if not statuses:
            continue
        method = operation.method.upper()
        path = operation.path
        status_set = "{" + ", ".join(statuses) + "}"
        entries.append(f"    ({method!r}, {path!r}): {status_set},")
    if not entries:
        return ["EXPECTED_STATUSES: dict[tuple[str, str], set[str]] = {}", ""]
    return [
        "EXPECTED_STATUSES: dict[tuple[str, str], set[str]] = {",
        *entries,
        "}",
        "",
    ]


def _emit_accept_types_map(operations: list[OperationIR]) -> list[str]:
    entries: list[str] = []
    for operation in operations:
        content_types: set[str] = set()
        for response in operation.responses:
            for media in response.content:
                content_types.add(media.content_type)
        if not content_types:
            continue
        method = operation.method.upper()
        path = operation.path
        types_list = "[" + ", ".join(repr(t) for t in sorted(content_types)) + "]"
        entries.append(f"    ({method!r}, {path!r}): {types_list},")
    if not entries:
        return ["ACCEPT_TYPES: dict[tuple[str, str], list[str]] = {}", ""]
    return [
        "ACCEPT_TYPES: dict[tuple[str, str], list[str]] = {",
        *entries,
        "}",
        "",
    ]


def _emit_request_content_types_map(operations: list[OperationIR]) -> list[str]:
    entries: list[str] = []
    for operation in operations:
        request_body = operation.request_body
        if request_body is None:
            continue
        content_types = [media.content_type for media in request_body.content]
        if not content_types:
            continue
        method = operation.method.upper()
        path = operation.path
        types_list = "[" + ", ".join(repr(t) for t in sorted(content_types)) + "]"
        entries.append(f"    ({method!r}, {path!r}): {types_list},")
    if not entries:
        return ["REQUEST_CONTENT_TYPES: dict[tuple[str, str], list[str]] = {}", ""]
    return [
        "REQUEST_CONTENT_TYPES: dict[tuple[str, str], list[str]] = {",
        *entries,
        "}",
        "",
    ]
