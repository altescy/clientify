from __future__ import annotations

from clientify.generation.emitter import TypeEmitter
from clientify.generation.profile import GenerationProfile


class TestTypeEmitter:
    def test_emits_scalar_types(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        assert emitter.emit({"type": "string"}) == "str"
        assert emitter.emit({"type": "integer"}) == "int"
        assert emitter.emit({"type": "number"}) == "float"
        assert emitter.emit({"type": "boolean"}) == "bool"

    def test_emits_enum_literal(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        assert emitter.emit({"enum": ["a", "b"]}) == "Literal['a', 'b']"
        assert "Literal" in emitter.imports

    def test_emits_array_and_object(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        assert emitter.emit({"type": "array", "items": {"type": "string"}}) == "list[str]"
        assert emitter.emit({"type": "object"}) == "dict[str, object]"

    def test_applies_nullable(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        base = emitter.emit({"type": "string"})
        assert emitter.apply_nullable(base, {"nullable": True}) == "str | None"

    def test_emits_ref_name(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        assert emitter.emit({"$ref": "#/components/schemas/User"}) == "User"

    def test_emits_one_of_union(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        result = emitter.emit({"oneOf": [{"type": "string"}, {"type": "integer"}]})
        assert result == "str | int"

    def test_emits_any_of_union(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.9"))
        result = emitter.emit({"anyOf": [{"type": "string"}, {"type": "integer"}]})
        assert result == "Union[str, int]"

    def test_emits_all_of_fallback(self) -> None:
        emitter = TypeEmitter(GenerationProfile.from_version("3.14"))
        result = emitter.emit({"allOf": [{"type": "object"}, {"type": "object"}]})
        assert result == "dict[str, object]"

    def test_emits_null_type(self) -> None:
        profile = GenerationProfile.from_version("3.14")
        emitter = TypeEmitter(profile)
        result = emitter.emit({"type": "null"})
        assert result == "None"

    def test_emits_anyof_with_null(self) -> None:
        profile = GenerationProfile.from_version("3.14")
        emitter = TypeEmitter(profile)
        result = emitter.emit(
            {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ]
            }
        )
        assert result == "str | None"
