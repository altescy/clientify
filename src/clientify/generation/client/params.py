from __future__ import annotations

from typing import cast

from ...ir import OperationIR, ParameterIR
from ...openapi import SchemaObject
from .context import ClientContext
from .helpers import operation_name


def emit_param_types(operation: OperationIR, ctx: ClientContext) -> list[str]:
    """Generate TypedDict classes for operation parameters.

    This generates parameter type classes for path, query, header, and cookie
    parameters, as well as a combined Params class for each operation.
    """
    op_name = operation_name(operation.method, operation.path)
    by_location: dict[str, list[ParameterIR]] = {"path": [], "query": [], "header": [], "cookie": []}
    for param in operation.parameters:
        if param.location in by_location:
            by_location[param.location].append(param)

    accept_literals = _accept_literals(operation)
    if accept_literals:
        by_location["header"].append(
            ParameterIR(
                name="accept",
                location="header",
                required=False,
                schema=None,
                content=[],
                style=None,
                explode=None,
                default=None,
            )
        )

    lines: list[str] = []
    for location, params in by_location.items():
        class_name = f"{op_name}{location.title()}Params"
        lines.extend(_emit_location_params(class_name, params, ctx, accept_literals))

    params_class = f"{op_name}Params"
    lines.append(f"class {params_class}(TypedDict, total=False):")
    for location in ("path", "query", "header", "cookie"):
        lines.append(f"    {location}: {op_name}{location.title()}Params")
    lines.append("")
    return lines


def _emit_location_params(
    class_name: str,
    params: list[ParameterIR],
    ctx: ClientContext,
    accept_literals: list[str] | None = None,
) -> list[str]:
    """Generate a TypedDict class for parameters at a specific location."""
    items: list[str] = []
    for param in params:
        param_type = _param_type(param, ctx, accept_literals)
        if _is_required(param):
            param_type = f"Required[{param_type}]"
        items.append(f"        {param.name!r}: {param_type},")

    lines = [f"{class_name} = TypedDict(", f"    {class_name!r},", "    {"]
    if items:
        lines.extend(items)
    lines.extend(["    },", "    total=False,", ")", ""])
    return lines


def _param_type(
    param: ParameterIR,
    ctx: ClientContext,
    accept_literals: list[str] | None = None,
) -> str:
    """Get the Python type annotation for a parameter."""
    if param.name == "accept" and accept_literals:
        ctx.typing_imports.add("Literal")
        literals = ", ".join(repr(value) for value in accept_literals)
        return f"Literal[{literals}]"
    schema = param.schema
    if schema is None and param.content:
        schema = param.content[0].schema
    if schema is None:
        return "JsonValue"
    if not isinstance(schema, dict):
        return "JsonValue"
    base = ctx.emitter.emit(cast(SchemaObject, schema))
    return ctx.emitter.apply_nullable(base, cast(SchemaObject, schema))


def _is_required(param: ParameterIR) -> bool:
    """Check if a parameter is required."""
    if param.default is not None:
        return False
    if param.schema and isinstance(param.schema, dict) and "default" in param.schema:
        return False
    return param.required


def _accept_literals(operation: OperationIR) -> list[str] | None:
    """Get the list of Accept header literals for an operation."""
    content_types: set[str] = set()
    for response in operation.responses:
        for media in response.content:
            content_types.add(media.content_type)
    if len(content_types) <= 1:
        return None
    return sorted(content_types)
