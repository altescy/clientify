"""Type emission utilities for code generation.

This module provides the TypeEmitter class which converts OpenAPI schema
objects into Python type annotation strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ..openapi import SchemaObject
from .profile import GenerationProfile


@dataclass
class TypeEmitter:
    """Converts OpenAPI schemas to Python type annotation strings.

    This class is responsible for transforming OpenAPI schema definitions
    into valid Python type annotations that can be used in generated code.

    Attributes:
        profile: Generation profile controlling Python version features
        quote_refs: Whether to quote reference type names (for forward refs)
        imports: Set of typing imports required by emitted types

    Note:
        The emit() method has side effects: it updates self.imports with
        any typing module imports required by the emitted type. When using
        the same TypeEmitter instance for multiple schemas, imports will
        accumulate across all emit() calls.

    Example:
        >>> profile = GenerationProfile(use_pep604=True)
        >>> emitter = TypeEmitter(profile)
        >>> emitter.emit({"type": "string"})
        'str'
        >>> emitter.emit({"type": "array", "items": {"type": "integer"}})
        'list[int]'
        >>> emitter.emit({"oneOf": [{"type": "string"}, {"type": "integer"}]})
        'str | int'
    """

    profile: GenerationProfile
    quote_refs: bool = False
    imports: set[str] = field(default_factory=set)

    def emit(self, schema: SchemaObject | None) -> str:
        """Convert an OpenAPI schema to a Python type annotation string.

        This method handles various OpenAPI schema types including:
        - Primitive types (string, integer, number, boolean)
        - Arrays with typed items
        - Objects with additionalProperties
        - References ($ref)
        - Unions (oneOf, anyOf)
        - Intersections (allOf) - simplified to dict[str, object]
        - Enums (converted to Literal types)

        Args:
            schema: The OpenAPI schema object to convert, or None

        Returns:
            A string representing the Python type annotation

        Side Effects:
            Updates self.imports with required typing imports (e.g., Literal, Union)
        """
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
        if schema_type == "null":
            return "None"
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
        """Apply nullable modifier to a type annotation if needed.

        Args:
            base: The base type annotation string
            schema: The schema to check for nullable flag

        Returns:
            The type annotation, optionally wrapped with None union
        """
        if not schema or not schema.get("nullable"):
            return base
        if self.profile.use_pep604:
            return f"{base} | None"
        self.imports.add("Optional")
        return f"Optional[{base}]"

    def _ensure_literal(self) -> None:
        """Ensure Literal is added to imports."""
        self.imports.add("Literal")

    @staticmethod
    def _ref_name(ref: str) -> str:
        """Extract the type name from a $ref string.

        Args:
            ref: A JSON reference string (e.g., "#/components/schemas/User")

        Returns:
            The final component of the reference path (e.g., "User")
        """
        if "#/" in ref:
            return ref.split("/")[-1]
        return ref.split("/")[-1]

    def _emit_union(self, items: list[SchemaObject]) -> str:
        """Emit a union type from oneOf or anyOf schemas.

        Args:
            items: List of schema objects to union

        Returns:
            A union type annotation (e.g., "str | int" or "Union[str, int]")
        """
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
        """Emit a type for allOf schemas.

        Note:
            Python doesn't have a direct intersection type, so allOf schemas
            with object types are simplified to dict[str, object]. Non-object
            allOf schemas fall back to union behavior.

        Args:
            items: List of schema objects to intersect

        Returns:
            A type annotation representing the intersection
        """
        object_items = [item for item in items if item.get("type") == "object"]
        if not object_items:
            return self._emit_union(items)
        # NOTE: allOf lacks a direct intersection type; use a safe object fallback for now.
        return "dict[str, object]"
