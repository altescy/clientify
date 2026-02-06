from __future__ import annotations

from typing import TypedDict

# Type aliases for JSON-like values used in OpenAPI
JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]

# Type alias for enum values (OpenAPI enum can contain strings, numbers, or booleans)
EnumValue = str | int | float | bool | None

# Type alias for default values in schemas
DefaultValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]

# Header object (simplified - commonly used fields)
HeaderObject = TypedDict(
    "HeaderObject",
    {
        "description": str,
        "required": bool,
        "schema": "SchemaObject",
        "$ref": str,
    },
    total=False,
)

SchemaObject = TypedDict(
    "SchemaObject",
    {
        "type": str,
        "format": str,
        "properties": dict[str, "SchemaObject"],
        "items": "SchemaObject",
        "required": list[str],
        "nullable": bool,
        "enum": list[EnumValue],
        "oneOf": list["SchemaObject"],
        "anyOf": list["SchemaObject"],
        "allOf": list["SchemaObject"],
        # Note: additionalProperties can be bool or SchemaObject, but we use object
        # for compatibility with TypedDict's type annotation limitations
        "additionalProperties": object,
        "default": DefaultValue,
        "description": str,
        "title": str,
        "$ref": str,
        # Clientify extension field for tracking schema names
        "x-clientify-schema-name": str,
    },
    total=False,
)

MediaTypeObject = TypedDict(
    "MediaTypeObject",
    {
        "schema": SchemaObject,
    },
    total=False,
)

ResponseObject = TypedDict(
    "ResponseObject",
    {
        "description": str,
        "headers": dict[str, HeaderObject],
        "content": dict[str, MediaTypeObject],
        "$ref": str,
    },
    total=False,
)

RequestBodyObject = TypedDict(
    "RequestBodyObject",
    {
        "description": str,
        "content": dict[str, MediaTypeObject],
        "required": bool,
        "$ref": str,
    },
    total=False,
)

ParameterObject = TypedDict(
    "ParameterObject",
    {
        "name": str,
        "in": str,
        "required": bool,
        "schema": SchemaObject,
        "content": dict[str, MediaTypeObject],
        "style": str,
        "explode": bool,
        "allowReserved": bool,
        "default": DefaultValue,
        "$ref": str,
    },
    total=False,
)

OperationObject = TypedDict(
    "OperationObject",
    {
        "operationId": str,
        "summary": str,
        "description": str,
        "parameters": list[ParameterObject],
        "requestBody": RequestBodyObject,
        "responses": dict[str, ResponseObject],
        "security": list[dict[str, list[str]]],
    },
    total=False,
)

PathItemObject = TypedDict(
    "PathItemObject",
    {
        "parameters": list[ParameterObject],
        "get": OperationObject,
        "put": OperationObject,
        "post": OperationObject,
        "delete": OperationObject,
        "options": OperationObject,
        "head": OperationObject,
        "patch": OperationObject,
        "trace": OperationObject,
    },
    total=False,
)

ComponentsObject = TypedDict(
    "ComponentsObject",
    {
        "schemas": dict[str, SchemaObject],
    },
    total=False,
)

InfoObject = TypedDict(
    "InfoObject",
    {
        "title": str,
        "version": str,
    },
    total=False,
)

# Server variable object
ServerVariableObject = TypedDict(
    "ServerVariableObject",
    {
        "enum": list[str],
        "default": str,
        "description": str,
    },
    total=False,
)

# Server object with proper typing
ServerObject = TypedDict(
    "ServerObject",
    {
        "url": str,
        "description": str,
        "variables": dict[str, ServerVariableObject],
    },
    total=False,
)

OpenAPIDocument = TypedDict(
    "OpenAPIDocument",
    {
        "openapi": str,
        "info": InfoObject,
        "paths": dict[str, PathItemObject],
        "components": ComponentsObject,
        "servers": list[ServerObject],
    },
    total=False,
)
