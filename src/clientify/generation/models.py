from __future__ import annotations

from dataclasses import dataclass

from ..ir import SchemaIR
from ..openapi import SchemaObject
from .emitter import TypeEmitter
from .profile import GenerationProfile


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

    needs_json_value = False
    schema_lines: list[str] = []
    for schema in schemas:
        schema_output = _emit_schema(schema, emitter, profile)
        schema_lines.extend(schema_output)
        if any("JsonValue" in line for line in schema_output):
            needs_json_value = True

    imports = _render_imports(emitter)
    if imports:
        insert_at = 1 if lines and lines[0].startswith("from __future__") else 0
        lines.insert(insert_at, imports)

    if needs_json_value:
        lines.append("from .types import JsonValue")

    lines.extend(schema_lines)
    return ModelOutput(code="\n".join(lines).rstrip() + "\n")


def _emit_schema(
    schema_ir: SchemaIR,
    emitter: TypeEmitter,
    profile: GenerationProfile,
) -> list[str]:
    schema = schema_ir.schema
    name = schema_ir.name

    # Handle boolean schemas (JSON Schema allows true/false as schemas)
    if isinstance(schema, bool):
        if schema:
            # true schema accepts anything
            alias = f"{name} = JsonValue"
        else:
            # false schema accepts nothing (never type, but we use JsonValue as fallback)
            alias = f"{name} = JsonValue"
        return [alias, ""]

    # Handle allOf with object merge
    all_of = schema.get("allOf")
    if all_of and isinstance(all_of, list):
        merged_schema = _merge_all_of(all_of)
        if merged_schema and merged_schema.get("type") == "object" and merged_schema.get("properties"):
            return _emit_typed_dict(name, merged_schema, emitter, profile)

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

    # Check if additionalProperties is explicitly false
    additional_properties = schema.get("additionalProperties")
    closed = additional_properties is False

    items = _typed_dict_items(properties, required_set, emitter)
    lines = [f"{name} = TypedDict(", f"    {name!r},", "    {"]
    if items:
        lines.extend(items)

    # If additionalProperties is false and all properties are required, use total=True
    # Otherwise use total=False for flexibility
    if closed and len(required_set) == len(properties):
        lines.extend(["    },", "    total=True,", ")", ""])
    else:
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
    base = _replace_object_with_json_value(base)
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
        prop_type = _replace_object_with_json_value(prop_type)
        if prop_name in required_set:
            prop_type = f"Required[{prop_type}]"
        items.append(f"        {prop_name!r}: {prop_type},")
    return items


def _replace_object_with_json_value(type_str: str) -> str:
    """Replace 'object' with 'JsonValue' in type annotations.

    OpenAPI schemas are JSON-based, so 'object' should be 'JsonValue'.
    This handles cases like:
    - "object" -> "JsonValue"
    - "dict[str, object]" -> "dict[str, JsonValue]"
    - "list[object]" -> "list[JsonValue]"
    """
    if type_str == "object":
        return "JsonValue"
    import re

    return re.sub(r"\bobject\b", "JsonValue", type_str)


def _merge_all_of(schemas: list[SchemaObject]) -> SchemaObject | None:
    """Merge allOf schemas into a single schema.

    This is a simplified merge that combines properties from all object schemas.
    Only handles object types with properties.

    Args:
        schemas: List of schemas to merge

    Returns:
        Merged schema, or None if merging is not possible
    """
    merged_properties: dict[str, SchemaObject] = {}
    merged_required: list[str] = []
    additional_properties: object | None = None

    for schema in schemas:
        if not isinstance(schema, dict):
            return None

        # Skip non-object schemas
        if schema.get("type") not in ("object", None):
            return None

        # Merge properties
        properties = schema.get("properties")
        if isinstance(properties, dict):
            merged_properties.update(properties)

        # Merge required fields
        required = schema.get("required")
        if isinstance(required, list):
            merged_required.extend(required)

        # Track additionalProperties (use most restrictive)
        schema_additional = schema.get("additionalProperties")
        if schema_additional is False:
            additional_properties = False
        elif additional_properties is None and schema_additional is not None:
            additional_properties = schema_additional

    if not merged_properties:
        return None

    result: SchemaObject = {
        "type": "object",
        "properties": merged_properties,
    }

    if merged_required:
        result["required"] = list(set(merged_required))

    if additional_properties is not None:
        result["additionalProperties"] = additional_properties

    return result
