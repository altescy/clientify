from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, cast

from .openapi_types import (
    ComponentsObject,
    MediaTypeObject,
    OpenAPIDocument,
    OperationObject,
    ParameterObject,
    PathItemObject,
    RequestBodyObject,
    ResponseObject,
    SchemaObject,
)


@dataclass(frozen=True)
class SchemaIR:
    name: str
    schema: SchemaObject


@dataclass(frozen=True)
class MediaTypeIR:
    content_type: str
    schema: SchemaObject | None


@dataclass(frozen=True)
class ResponseIR:
    status: str
    description: str | None
    content: list[MediaTypeIR]


@dataclass(frozen=True)
class RequestBodyIR:
    required: bool
    content: list[MediaTypeIR]


@dataclass(frozen=True)
class ParameterIR:
    name: str
    location: str
    required: bool
    schema: SchemaObject | None
    content: list[MediaTypeIR]
    style: str | None
    explode: bool | None
    default: object | None


@dataclass(frozen=True)
class OperationIR:
    method: str
    path: str
    operation_id: str | None
    parameters: list[ParameterIR]
    request_body: RequestBodyIR | None
    responses: list[ResponseIR]
    extensions: dict[str, object]


@dataclass(frozen=True)
class IRDocument:
    schemas: list[SchemaIR]
    operations: list[OperationIR]


def build_ir(document: OpenAPIDocument) -> IRDocument:
    components = cast(ComponentsObject, document.get("components", {}))
    schemas: list[SchemaIR] = []
    for name, schema in components.get("schemas", {}).items():
        schemas.append(SchemaIR(name=name, schema=schema))

    operations: list[OperationIR] = []
    for path, item in cast(dict[str, PathItemObject], document.get("paths", {})).items():
        operations.extend(_build_path_operations(path, item))
    return IRDocument(schemas=schemas, operations=operations)


def _build_path_operations(path: str, item: PathItemObject) -> Iterable[OperationIR]:
    common_params = cast(list[ParameterObject], item.get("parameters", []))
    for method in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
        operation = cast(OperationObject | None, item.get(method))
        if not operation:
            continue
        parameters = _merge_parameters(
            common_params,
            cast(list[ParameterObject], operation.get("parameters", [])),
        )
        request_body = _build_request_body(cast(RequestBodyObject | None, operation.get("requestBody")))
        responses = _build_responses(cast(dict[str, ResponseObject], operation.get("responses", {})))
        extensions = _extract_extensions(operation)
        yield OperationIR(
            method=method,
            path=path,
            operation_id=operation.get("operationId"),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            extensions=extensions,
        )


def _merge_parameters(
    common: list[ParameterObject],
    specific: list[ParameterObject],
) -> list[ParameterIR]:
    merged: dict[tuple[str, str], ParameterObject] = {}
    for param in common + specific:
        name = param.get("name")
        location = param.get("in")
        if not name or not location:
            continue
        merged[(name, location)] = param
    return [_build_parameter(param) for param in merged.values()]


def _build_parameter(param: ParameterObject) -> ParameterIR:
    content = _build_media_types(param.get("content", {}))
    schema = param.get("schema")
    return ParameterIR(
        name=param.get("name", ""),
        location=param.get("in", ""),
        required=bool(param.get("required", False)),
        schema=schema,
        content=content,
        style=param.get("style"),
        explode=param.get("explode"),
        default=param.get("default"),
    )


def _build_request_body(request_body: RequestBodyObject | None) -> RequestBodyIR | None:
    if not request_body:
        return None
    return RequestBodyIR(
        required=bool(request_body.get("required", False)),
        content=_build_media_types(request_body.get("content", {})),
    )


def _build_responses(responses: dict[str, ResponseObject]) -> list[ResponseIR]:
    result: list[ResponseIR] = []
    for status, response in responses.items():
        result.append(
            ResponseIR(
                status=status,
                description=response.get("description"),
                content=_build_media_types(response.get("content", {})),
            )
        )
    return result


def _build_media_types(content: dict[str, MediaTypeObject]) -> list[MediaTypeIR]:
    result: list[MediaTypeIR] = []
    for content_type, media_type in content.items():
        result.append(
            MediaTypeIR(
                content_type=content_type,
                schema=media_type.get("schema"),
            )
        )
    return result


def _extract_extensions(operation: OperationObject) -> dict[str, object]:
    return {key: value for key, value in operation.items() if key.startswith("x-clientify-")}
