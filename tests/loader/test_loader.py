from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from clientify.errors import SpecError
from clientify.loader import load_openapi, resolve_refs
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
