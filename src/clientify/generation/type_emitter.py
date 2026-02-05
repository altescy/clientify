from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ..openapi_types import SchemaObject
from .profile import GenerationProfile


@dataclass
class TypeEmitter:
    profile: GenerationProfile
    quote_refs: bool = False
    imports: set[str] = field(default_factory=set)

    def emit(self, schema: SchemaObject | None) -> str:
        if schema is None:
            return "object"
        if "$ref" in schema:
            ref = schema["$ref"]
            name = self._ref_name(ref)
            return f"{name!r}" if self.quote_refs else name
        schema_name = schema.get("x-clientify-schema-name")
        if isinstance(schema_name, str) and schema_name:
            return f"{schema_name!r}" if self.quote_refs else schema_name

        one_of = schema.get("oneOf")
        if one_of:
            return self._emit_union(one_of)
        any_of = schema.get("anyOf")
        if any_of:
            return self._emit_union(any_of)
        all_of = schema.get("allOf")
        if all_of:
            return self._emit_all_of(all_of)

        enum_values = schema.get("enum")
        if enum_values:
            self._ensure_literal()
            literals = ", ".join(repr(value) for value in enum_values)
            return f"Literal[{literals}]"

        schema_type = schema.get("type")
        if schema_type == "string":
            return "str"
        if schema_type == "integer":
            return "int"
        if schema_type == "number":
            return "float"
        if schema_type == "boolean":
            return "bool"
        if schema_type == "array":
            items_schema = schema.get("items")
            if isinstance(items_schema, dict):
                item_type = self.emit(cast(SchemaObject, items_schema))
            else:
                item_type = "object"
            return f"list[{item_type}]"
        if schema_type == "object":
            additional = schema.get("additionalProperties")
            if isinstance(additional, dict):
                value_type = self.emit(cast(SchemaObject, additional))
                return f"dict[str, {value_type}]"
            if additional is True:
                return "dict[str, object]"
            return "dict[str, object]"
        return "object"

    def apply_nullable(self, base: str, schema: SchemaObject | None) -> str:
        if not schema or not schema.get("nullable"):
            return base
        if self.profile.use_pep604:
            return f"{base} | None"
        self.imports.add("Optional")
        return f"Optional[{base}]"

    def _ensure_literal(self) -> None:
        self.imports.add("Literal")

    @staticmethod
    def _ref_name(ref: str) -> str:
        if "#/" in ref:
            return ref.split("/")[-1]
        return ref.split("/")[-1]

    def _emit_union(self, items: list[SchemaObject]) -> str:
        types = [self.emit(item) for item in items]
        unique = [item for item in dict.fromkeys(types)]
        if not unique:
            return "object"
        if len(unique) == 1:
            return unique[0]
        if self.profile.use_pep604:
            return " | ".join(unique)
        self.imports.add("Union")
        return f"Union[{', '.join(unique)}]"

    def _emit_all_of(self, items: list[SchemaObject]) -> str:
        object_items = [item for item in items if item.get("type") == "object"]
        if not object_items:
            return self._emit_union(items)
        # NOTE: allOf lacks a direct intersection type; use a safe object fallback for now.
        return "dict[str, object]"
