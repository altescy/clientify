"""Intermediate Representation (IR) for OpenAPI documents.

This module defines the IR data structures that represent OpenAPI specifications
in a simplified, code-generation-friendly format. The IR is built from parsed
OpenAPI documents and used by the generation modules to produce Python client code.

Key classes:
- IRDocument: Root container for schemas and operations
- OperationIR: Represents an HTTP operation (endpoint)
- SchemaIR: Represents a schema definition
- ResponseIR: Represents an HTTP response
- RequestBodyIR: Represents a request body
- ParameterIR: Represents a request parameter
- MediaTypeIR: Represents a media type with schema
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TypedDict, cast

from .openapi import (
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


class ClientifyExtensions(TypedDict, total=False):
    """TypedDict for x-clientify-* extension fields.

    This type defines the structure of Clientify-specific extension fields
    that can be added to OpenAPI operations. Currently, this is a placeholder
    for future extensions.

    Extension fields should follow the pattern: x-clientify-<name>

    Example future extensions:
        x-clientify-timeout: float  # Default timeout for the operation
        x-clientify-retry: bool     # Whether to enable retry logic
        x-clientify-deprecated: str # Custom deprecation message
    """

    pass


@dataclass(frozen=True)
class SchemaIR:
    """Intermediate representation of an OpenAPI schema.

    Attributes:
        name: The schema name (from components/schemas key)
        schema: The full OpenAPI schema object
    """

    name: str
    schema: SchemaObject


@dataclass(frozen=True)
class MediaTypeIR:
    """Intermediate representation of a media type.

    Attributes:
        content_type: The MIME type (e.g., "application/json")
        schema: The schema for the content, if specified
    """

    content_type: str
    schema: SchemaObject | None


@dataclass(frozen=True)
class ResponseIR:
    """Intermediate representation of an HTTP response.

    Attributes:
        status: The HTTP status code as a string (e.g., "200", "default")
        description: Human-readable description of the response
        content: List of possible response content types and their schemas
    """

    status: str
    description: str | None
    content: list[MediaTypeIR]


@dataclass(frozen=True)
class RequestBodyIR:
    """Intermediate representation of a request body.

    Attributes:
        required: Whether the request body is required
        content: List of possible request content types and their schemas
    """

    required: bool
    content: list[MediaTypeIR]


@dataclass(frozen=True)
class ParameterIR:
    """Intermediate representation of a request parameter.

    Attributes:
        name: The parameter name
        location: Where the parameter is sent ("path", "query", "header", "cookie")
        required: Whether the parameter is required
        schema: The parameter's schema, if specified directly
        content: Media type definitions if the parameter uses content encoding
        style: How the parameter value is serialized
        explode: Whether arrays/objects should be exploded
        default: Default value for the parameter
    """

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
    """Intermediate representation of an HTTP operation (endpoint).

    Attributes:
        method: The HTTP method (lowercase: "get", "post", etc.)
        path: The URL path template (e.g., "/users/{id}")
        operation_id: Unique operation identifier from the spec
        parameters: List of parameters for this operation
        request_body: The request body definition, if any
        responses: List of possible responses
        extensions: Clientify-specific extension fields (x-clientify-*)
    """

    method: str
    path: str
    operation_id: str | None
    parameters: list[ParameterIR]
    request_body: RequestBodyIR | None
    responses: list[ResponseIR]
    extensions: ClientifyExtensions


@dataclass(frozen=True)
class IRDocument:
    """Root container for the intermediate representation.

    This is the top-level structure produced by build_ir() and consumed
    by the code generation modules.

    Attributes:
        schemas: All schema definitions from components/schemas
        operations: All HTTP operations from paths
    """

    schemas: list[SchemaIR]
    operations: list[OperationIR]


def build_ir(document: OpenAPIDocument) -> IRDocument:
    """Build an intermediate representation from an OpenAPI document.

    This function transforms a parsed and resolved OpenAPI document into
    the IR format used by code generation.

    Args:
        document: A fully resolved OpenAPI document (all $refs expanded)

    Returns:
        An IRDocument containing schemas and operations
    """
    components = cast(ComponentsObject, document.get("components", {}))
    schemas: list[SchemaIR] = []
    for name, schema in components.get("schemas", {}).items():
        schemas.append(SchemaIR(name=name, schema=schema))

    operations: list[OperationIR] = []
    for path, item in cast(dict[str, PathItemObject], document.get("paths", {})).items():
        operations.extend(_build_path_operations(path, item))
    return IRDocument(schemas=schemas, operations=operations)


def _build_path_operations(path: str, item: PathItemObject) -> Iterable[OperationIR]:
    """Build OperationIR instances for all methods in a path item."""
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
    """Merge path-level and operation-level parameters.

    Operation-level parameters override path-level parameters with the
    same name and location.
    """
    merged: dict[tuple[str, str], ParameterObject] = {}
    for param in common + specific:
        name = param.get("name")
        location = param.get("in")
        if not name or not location:
            continue
        merged[(name, location)] = param
    return [_build_parameter(param) for param in merged.values()]


def _build_parameter(param: ParameterObject) -> ParameterIR:
    """Build a ParameterIR from an OpenAPI parameter object."""
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
    """Build a RequestBodyIR from an OpenAPI request body object."""
    if not request_body:
        return None
    return RequestBodyIR(
        required=bool(request_body.get("required", False)),
        content=_build_media_types(request_body.get("content", {})),
    )


def _build_responses(responses: dict[str, ResponseObject]) -> list[ResponseIR]:
    """Build ResponseIR instances from OpenAPI response objects."""
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
    """Build MediaTypeIR instances from OpenAPI content map."""
    result: list[MediaTypeIR] = []
    for content_type, media_type in content.items():
        result.append(
            MediaTypeIR(
                content_type=content_type,
                schema=media_type.get("schema"),
            )
        )
    return result


def _extract_extensions(operation: OperationObject) -> ClientifyExtensions:
    """Extract x-clientify-* extension fields from an operation.

    Returns:
        A ClientifyExtensions dict containing only Clientify-specific extensions
    """
    return cast(
        ClientifyExtensions,
        {key: value for key, value in operation.items() if key.startswith("x-clientify-")},
    )
