from __future__ import annotations

from typing import cast

from clientify.ir import build_ir
from clientify.openapi import OpenAPIDocument


class TestBuildIR:
    def test_builds_schemas_and_operations(self) -> None:
        document = {
            "openapi": "3.0.3",
            "components": {"schemas": {"User": {"type": "object"}}},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }
        ir = build_ir(cast(OpenAPIDocument, document))
        assert len(ir.schemas) == 1
        assert ir.schemas[0].name == "User"
        assert len(ir.operations) == 1
        assert ir.operations[0].path == "/users/{id}"

    def test_merges_parameters_and_overrides(self) -> None:
        document = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "parameters": [{"name": "q", "in": "query", "required": False}],
                    "get": {
                        "parameters": [{"name": "q", "in": "query", "required": True}],
                        "responses": {"200": {"description": "ok"}},
                    },
                }
            },
        }
        ir = build_ir(cast(OpenAPIDocument, document))
        operation = ir.operations[0]
        assert len(operation.parameters) == 1
        assert operation.parameters[0].name == "q"
        assert operation.parameters[0].required is True

    def test_collects_request_body_and_responses(self) -> None:
        document = {
            "openapi": "3.0.3",
            "paths": {
                "/events": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                        "responses": {
                            "200": {
                                "description": "ok",
                                "content": {"text/plain": {"schema": {"type": "string"}}},
                            }
                        },
                    }
                }
            },
        }
        ir = build_ir(cast(OpenAPIDocument, document))
        operation = ir.operations[0]
        assert operation.request_body is not None
        assert operation.request_body.content[0].content_type == "application/json"
        assert operation.responses[0].content[0].content_type == "text/plain"

    def test_extracts_extensions(self) -> None:
        document = {
            "openapi": "3.0.3",
            "paths": {
                "/users": {
                    "get": {
                        "x-clientify-timeout": 10,
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }
        ir = build_ir(cast(OpenAPIDocument, document))
        assert ir.operations[0].extensions == {"x-clientify-timeout": 10}
