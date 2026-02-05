from __future__ import annotations

from typing import TypedDict

SchemaObject = TypedDict(
    "SchemaObject",
    {
        "type": str,
        "format": str,
        "properties": dict[str, "SchemaObject"],
        "items": "SchemaObject",
        "required": list[str],
        "nullable": bool,
        "enum": list[object],
        "oneOf": list["SchemaObject"],
        "anyOf": list["SchemaObject"],
        "allOf": list["SchemaObject"],
        "additionalProperties": object,
        "default": object,
        "description": str,
        "title": str,
        "$ref": str,
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
        "headers": dict[str, object],
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
        "default": object,
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

OpenAPIDocument = TypedDict(
    "OpenAPIDocument",
    {
        "openapi": str,
        "info": InfoObject,
        "paths": dict[str, PathItemObject],
        "components": ComponentsObject,
        "servers": list[dict[str, object]],
    },
    total=False,
)
