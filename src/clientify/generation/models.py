from __future__ import annotations

from dataclasses import dataclass

from ..ir import SchemaIR
from ..openapi import SchemaObject
from .profile import GenerationProfile
from .emitter import TypeEmitter


@dataclass
class ModelOutput:
    code: str


def generate_models(
    schemas: list[SchemaIR],
    profile: GenerationProfile,
) -> ModelOutput:
    model_profile = GenerationProfile(
        use_future_annotations=profile.use_future_annotations,
        use_pep604=False,
        use_required=True,
        use_typing_extensions=profile.use_typing_extensions,
    )
    emitter = TypeEmitter(model_profile, quote_refs=True)
    lines: list[str] = []

    if model_profile.use_future_annotations:
        lines.append("from __future__ import annotations")

    if model_profile.use_typing_extensions:
        lines.append("from typing_extensions import Required, TypedDict")
    else:
        lines.append("from typing import Required, TypedDict")

    for schema in schemas:
        lines.extend(_emit_schema(schema, emitter, profile))

    imports = _render_imports(emitter)
    if imports:
        insert_at = 1 if lines and lines[0].startswith("from __future__") else 0
        lines.insert(insert_at, imports)

    return ModelOutput(code="\n".join(lines).rstrip() + "\n")


def _emit_schema(
    schema_ir: SchemaIR,
    emitter: TypeEmitter,
    profile: GenerationProfile,
) -> list[str]:
    schema = schema_ir.schema
    name = schema_ir.name

    schema_type = schema.get("type")
    if schema_type == "object" and schema.get("properties"):
        return _emit_typed_dict(name, schema, emitter, profile)
    alias = _emit_alias(name, schema, emitter, profile)
    return [alias, ""]


def _emit_typed_dict(
    name: str,
    schema: SchemaObject,
    emitter: TypeEmitter,
    profile: GenerationProfile,
) -> list[str]:
    properties = schema.get("properties", {})
    required_set = set(schema.get("required", []))
    for prop_name, prop_schema in properties.items():
        if isinstance(prop_schema, dict) and "default" in prop_schema:
            required_set.discard(prop_name)

    items = _typed_dict_items(properties, required_set, emitter)
    lines = [f"{name} = TypedDict(", f"    {name!r},", "    {"]
    if items:
        lines.extend(items)
    lines.extend(["    },", "    total=False,", ")", ""])
    return lines


def _emit_alias(
    name: str,
    schema: SchemaObject,
    emitter: TypeEmitter,
    profile: GenerationProfile,
) -> str:
    base = emitter.emit(schema)
    base = emitter.apply_nullable(base, schema)
    return f"{name} = {base}"


def _render_imports(emitter: TypeEmitter) -> str:
    if not emitter.imports:
        return ""
    imports = ", ".join(sorted(emitter.imports))
    return f"from typing import {imports}"


def _typed_dict_items(
    properties: dict[str, SchemaObject],
    required_set: set[str],
    emitter: TypeEmitter,
) -> list[str]:
    items: list[str] = []
    for prop_name, prop_schema in properties.items():
        prop_type = emitter.emit(prop_schema)
        prop_type = emitter.apply_nullable(prop_type, prop_schema)
        if prop_name in required_set:
            prop_type = f"Required[{prop_type}]"
        items.append(f"        {prop_name!r}: {prop_type},")
    return items
