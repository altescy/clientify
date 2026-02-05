from __future__ import annotations

from dataclasses import dataclass

from .profile import GenerationProfile


@dataclass
class TypesOutput:
    code: str


def generate_types(profile: GenerationProfile) -> TypesOutput:
    lines: list[str] = []

    if profile.use_future_annotations:
        lines.append("from __future__ import annotations")

    typing_imports = ["TypeVar", "Generic", "Iterator", "Sequence"]
    if not profile.use_pep604:
        typing_imports.append("Union")
    lines.append(f"from typing import {', '.join(sorted(set(typing_imports)))}")

    lines.append("from collections.abc import Mapping")

    lines.append("")
    if profile.use_pep604:
        lines.append("JsonValue = bool | int | str | None | Sequence['JsonValue'] | Mapping[str, 'JsonValue']")
    else:
        lines.append("JsonValue = Union[bool, int, str, None, Sequence['JsonValue'], Mapping[str, 'JsonValue']]")
    lines.append("")
    lines.append("Headers = Mapping[str, str]")
    lines.append("QueryParams = Mapping[str, JsonValue]")
    lines.append("PathParams = Mapping[str, JsonValue]")
    lines.append("HeaderParams = Mapping[str, JsonValue]")
    lines.append("CookieParams = Mapping[str, JsonValue]")
    lines.append("")
    lines.append("T = TypeVar('T', covariant=True)")
    lines.append("E = TypeVar('E', covariant=True)")
    lines.append("")
    lines.append("class SuccessResponse(Generic[T]):")
    lines.append("    status: int")
    lines.append("    headers: Mapping[str, str]")
    lines.append("    body: T")
    lines.append("")
    lines.append("class ErrorResponse(Generic[E]):")
    lines.append("    status: int")
    lines.append("    headers: Mapping[str, str]")
    lines.append("    body: E")
    lines.append("")
    if profile.use_pep604:
        lines.append("BodyType = object | Iterator[str]")
    else:
        lines.append("BodyType = Union[object, Iterator[str]]")
    lines.append("")

    return TypesOutput(code="\n".join(lines).rstrip() + "\n")
