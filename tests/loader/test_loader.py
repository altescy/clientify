from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from clientify.errors import SpecError
from clientify.loader import RefResolver, _is_url, load_openapi, resolve_refs
from clientify.openapi import OpenAPIDocument


class TestLoadOpenAPI:
    @pytest.mark.parametrize(
        "document",
        [
            pytest.param({}, id="missing-openapi"),
            pytest.param({"openapi": None}, id="openapi-null"),
        ],
    )
    def test_missing_openapi_field_raises(self, document: dict[str, object]) -> None:
        with pytest.raises(SpecError):
            load_openapi(document)

    def test_loads_json_file(self, tmp_path: Path) -> None:
        path = tmp_path / "spec.json"
        data = {"openapi": "3.0.3", "info": {"title": "t", "version": "1"}, "paths": {}}
        path.write_text(json.dumps(data), encoding="utf-8")
        loaded = load_openapi(path)
        assert loaded.get("openapi") == "3.0.3"

    def test_loads_yaml_file(self, tmp_path: Path) -> None:
        yaml = pytest.importorskip("yaml")
        path = tmp_path / "spec.yaml"
        data = {"openapi": "3.0.3", "info": {"title": "t", "version": "1"}, "paths": {}}
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        loaded = load_openapi(path)
        info = loaded.get("info", {})
        assert info.get("title") == "t"


class TestLoadFromURL:
    """Tests for loading OpenAPI specs from URLs."""

    def test_is_url_detects_http(self) -> None:
        assert _is_url("http://example.com/spec.json") is True
        assert _is_url("https://example.com/spec.yaml") is True
        assert _is_url("./local/spec.json") is False
        assert _is_url("/absolute/path/spec.yaml") is False
        assert _is_url("spec.json") is False

    def test_loads_json_from_url(self) -> None:
        data = {"openapi": "3.0.3", "info": {"title": "API", "version": "1"}, "paths": {}}
        json_content = json.dumps(data)

        with patch("clientify.loader._fetch_url", return_value=json_content):
            loaded = load_openapi("https://example.com/openapi.json")

        assert loaded.get("openapi") == "3.0.3"
        assert cast(dict[str, object], loaded.get("info", {})).get("title") == "API"

    def test_loads_yaml_from_url(self) -> None:
        yaml = pytest.importorskip("yaml")
        data = {"openapi": "3.0.3", "info": {"title": "YAML API", "version": "1"}, "paths": {}}
        yaml_content = yaml.safe_dump(data)

        with patch("clientify.loader._fetch_url", return_value=yaml_content):
            loaded = load_openapi("https://example.com/openapi.yaml")

        assert loaded.get("openapi") == "3.0.3"
        assert cast(dict[str, object], loaded.get("info", {})).get("title") == "YAML API"

    def test_loads_yml_extension_from_url(self) -> None:
        yaml = pytest.importorskip("yaml")
        data = {"openapi": "3.0.3", "info": {"title": "YML API", "version": "1"}, "paths": {}}
        yaml_content = yaml.safe_dump(data)

        with patch("clientify.loader._fetch_url", return_value=yaml_content):
            loaded = load_openapi("https://example.com/api/spec.yml")

        assert loaded.get("openapi") == "3.0.3"

    def test_url_without_extension_tries_json_first(self) -> None:
        data = {"openapi": "3.0.3", "info": {"title": "No Ext", "version": "1"}, "paths": {}}
        json_content = json.dumps(data)

        with patch("clientify.loader._fetch_url", return_value=json_content):
            loaded = load_openapi("https://example.com/openapi")

        assert loaded.get("openapi") == "3.0.3"

    def test_url_fetch_failure_raises_spec_error(self) -> None:
        with patch("clientify.loader._fetch_url", side_effect=SpecError("Failed to fetch URL: test")):
            with pytest.raises(SpecError, match="Failed to fetch URL"):
                load_openapi("https://example.com/spec.json")

    def test_url_returns_non_object_raises_spec_error(self) -> None:
        with patch("clientify.loader._fetch_url", return_value='"just a string"'):
            with pytest.raises(SpecError, match="must be an object"):
                load_openapi("https://example.com/spec.json")


class TestResolveRefs:
    def test_resolves_local_file_ref(self, tmp_path: Path) -> None:
        component_path = tmp_path / "components.json"
        component_path.write_text(
            json.dumps({"components": {"schemas": {"User": {"type": "object"}}}}),
            encoding="utf-8",
        )
        document = {
            "openapi": "3.0.3",
            "paths": {},
            "components": {"schemas": {"User": {"$ref": "components.json#/components/schemas/User"}}},
        }
        resolved = resolve_refs(cast(OpenAPIDocument, document), tmp_path)
        components = cast(dict[str, object], resolved.get("components", {}))
        schemas = cast(dict[str, object], components.get("schemas", {}))
        user = cast(dict[str, object], schemas.get("User", {}))
        assert user.get("type") == "object"

    def test_ref_merge_preserves_siblings(self, tmp_path: Path) -> None:
        component_path = tmp_path / "components.json"
        component_path.write_text(
            json.dumps({"components": {"schemas": {"User": {"type": "object"}}}}),
            encoding="utf-8",
        )
        document = {
            "openapi": "3.0.3",
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "$ref": "components.json#/components/schemas/User",
                        "description": "merged",
                    }
                }
            },
        }
        resolved = resolve_refs(cast(OpenAPIDocument, document), tmp_path)
        components = cast(dict[str, object], resolved.get("components", {}))
        schemas = cast(dict[str, object], components.get("schemas", {}))
        user = cast(dict[str, object], schemas.get("User", {}))
        assert user.get("type") == "object"
        assert user.get("description") == "merged"


class TestRefResolver:
    """Tests for the RefResolver class."""

    def test_resolves_local_ref(self) -> None:
        """Test that local #/components/schemas/ refs are resolved."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {
                    "/users": {
                        "get": {
                            "responses": {
                                "200": {
                                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}
                                }
                            }
                        }
                    }
                },
                "components": {"schemas": {"User": {"type": "object"}}},
            },
        )
        resolver = RefResolver(document, None)
        resolved = resolver.resolve()
        paths = resolved.get("paths", {})
        users_path = cast(dict[str, object], paths.get("/users", {}))
        get_op = cast(dict[str, object], users_path.get("get", {}))
        responses = cast(dict[str, object], get_op.get("responses", {}))
        response_200 = cast(dict[str, object], responses.get("200", {}))
        content = cast(dict[str, object], response_200.get("content", {}))
        json_content = cast(dict[str, object], content.get("application/json", {}))
        schema = cast(dict[str, object], json_content.get("schema", {}))
        assert schema.get("type") == "object"
        assert schema.get("x-clientify-schema-name") == "User"

    def test_resolves_nested_refs(self) -> None:
        """Test that nested refs are resolved recursively."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "properties": {"address": {"$ref": "#/components/schemas/Address"}},
                        },
                        "Address": {"type": "object"},
                    }
                },
            },
        )
        resolver = RefResolver(document, None)
        resolved = resolver.resolve()
        components = cast(dict[str, object], resolved.get("components", {}))
        schemas = cast(dict[str, object], components.get("schemas", {}))
        user = cast(dict[str, object], schemas.get("User", {}))
        properties = cast(dict[str, object], user.get("properties", {}))
        address = cast(dict[str, object], properties.get("address", {}))
        assert address.get("type") == "object"

    def test_invalid_ref_fragment_raises(self) -> None:
        """Test that invalid $ref fragment format raises SpecError."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {
                    "schemas": {
                        # Fragment that doesn't start with /
                        "User": {"$ref": "#invalid-fragment"}
                    }
                },
            },
        )
        resolver = RefResolver(document, None)
        with pytest.raises(SpecError, match="Unsupported"):
            resolver.resolve()

    def test_unresolvable_pointer_raises(self) -> None:
        """Test that unresolvable pointer raises SpecError."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {"schemas": {"User": {"$ref": "#/components/schemas/NonExistent"}}},
            },
        )
        resolver = RefResolver(document, None)
        with pytest.raises(SpecError, match="Unresolvable"):
            resolver.resolve()

    def test_caches_resolved_refs(self) -> None:
        """Test that resolved refs are cached for reuse."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {
                    "schemas": {
                        "User": {"type": "object"},
                        "UserList": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"},
                        },
                        "UserResponse": {
                            "type": "object",
                            "properties": {"user": {"$ref": "#/components/schemas/User"}},
                        },
                    }
                },
            },
        )
        resolver = RefResolver(document, None)
        resolver.resolve()
        # Cache should contain the User schema
        assert "#/components/schemas/User" in resolver._cache

    def test_non_string_ref_raises(self) -> None:
        """Test that non-string $ref raises SpecError."""
        document: OpenAPIDocument = cast(
            OpenAPIDocument,
            {
                "openapi": "3.0.3",
                "paths": {},
                "components": {
                    "schemas": {
                        "User": {"$ref": 123}  # Invalid: should be string
                    }
                },
            },
        )
        resolver = RefResolver(document, None)
        with pytest.raises(SpecError, match="must be a string"):
            resolver.resolve()
