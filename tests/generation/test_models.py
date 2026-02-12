from __future__ import annotations

from clientify.generation.models import generate_models
from clientify.generation.profile import GenerationProfile
from clientify.ir import SchemaIR


class TestGenerateModels:
    def test_generates_typed_dict_with_required(self) -> None:
        schemas = [
            SchemaIR(
                name="User",
                schema={
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                    "required": ["id"],
                },
            )
        ]
        profile = GenerationProfile.from_version("3.14")
        output = generate_models(schemas, profile).code
        assert "User = TypedDict(" in output
        assert "'id': Required[int]" in output
        assert "'name': str" in output

    def test_generates_required_and_optional_classes(self) -> None:
        schemas = [
            SchemaIR(
                name="Item",
                schema={
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "note": {"type": "string"}},
                    "required": ["id"],
                },
            )
        ]
        profile = GenerationProfile.from_version("3.9")
        output = generate_models(schemas, profile).code
        assert "Item = TypedDict(" in output
        assert "'id': Required[int]" in output
        assert "'note': str" in output

    def test_generates_alias_for_non_object(self) -> None:
        schemas = [
            SchemaIR(name="UserId", schema={"type": "integer"}),
        ]
        profile = GenerationProfile.from_version("3.14")
        output = generate_models(schemas, profile).code
        assert "UserId = int" in output

    def test_nested_object_uses_json_value(self) -> None:
        schemas = [
            SchemaIR(
                name="User",
                schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string"},
                            },
                        },
                        "metadata": {"type": "object"},
                    },
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "from .types import JsonValue" in output.code
        assert "'address': dict[str, JsonValue]" in output.code
        assert "'metadata': dict[str, JsonValue]" in output.code

    def test_anyof_with_null_uses_none(self) -> None:
        schemas = [
            SchemaIR(
                name="NullableString",
                schema={
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ]
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "NullableString = Union[str, None]" in output.code

    def test_nested_anyof_with_null_in_typed_dict(self) -> None:
        schemas = [
            SchemaIR(
                name="User",
                schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ]
                        },
                    },
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "'name': Union[str, None]" in output.code

    def test_deeply_nested_object_uses_json_value(self) -> None:
        schemas = [
            SchemaIR(
                name="DeepNested",
                schema={
                    "type": "object",
                    "properties": {
                        "level1": {
                            "type": "object",
                            "properties": {
                                "level2": {
                                    "type": "object",
                                    "properties": {
                                        "level3": {"type": "object"},
                                    },
                                },
                            },
                        },
                    },
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "from .types import JsonValue" in output.code
        assert "dict[str, JsonValue]" in output.code

    def test_array_without_items_uses_json_value(self) -> None:
        schemas = [
            SchemaIR(
                name="UntypedArray",
                schema={
                    "type": "array",
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "from .types import JsonValue" in output.code
        assert "UntypedArray = list[JsonValue]" in output.code

    def test_object_in_anyof_uses_json_value(self) -> None:
        schemas = [
            SchemaIR(
                name="FlexibleType",
                schema={
                    "anyOf": [
                        {"type": "string"},
                        {"type": "object"},
                    ]
                },
            )
        ]
        output = generate_models(schemas, GenerationProfile.from_version("3.14"))
        assert "from .types import JsonValue" in output.code
        assert "FlexibleType = Union[str, dict[str, JsonValue]]" in output.code
