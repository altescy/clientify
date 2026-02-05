from __future__ import annotations

from clientify.generation.profile import GenerationProfile
from clientify.generation.types import generate_types


class TestGenerateTypes:
    def test_generates_success_error_responses(self) -> None:
        output = generate_types(GenerationProfile.from_version("3.14")).code
        assert "class SuccessResponse" in output
        assert "class ErrorResponse" in output

    def test_body_type_union_matches_profile(self) -> None:
        output = generate_types(GenerationProfile.from_version("3.9")).code
        assert "BodyType = Union[object, Iterator[str]]" in output
        output = generate_types(GenerationProfile.from_version("3.14")).code
        assert "BodyType = object | Iterator[str]" in output

    def test_json_value_uses_recursive_types(self) -> None:
        output = generate_types(GenerationProfile.from_version("3.9")).code
        assert "JsonValue = Union[bool, int, str, None, Sequence['JsonValue'], Mapping[str, 'JsonValue']]" in output
        output = generate_types(GenerationProfile.from_version("3.14")).code
        assert "JsonValue = bool | int | str | None | Sequence['JsonValue'] | Mapping[str, 'JsonValue']" in output

    def test_generates_common_aliases(self) -> None:
        output = generate_types(GenerationProfile.from_version("3.14")).code
        assert "Headers = Mapping[str, str]" in output
        assert "QueryParams = Mapping[str, JsonValue]" in output
