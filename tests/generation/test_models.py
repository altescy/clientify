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
