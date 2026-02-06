from __future__ import annotations

from ...ir import OperationIR
from .helpers import known_statuses


def emit_expected_statuses_map(operations: list[OperationIR]) -> list[str]:
    """Generate the EXPECTED_STATUSES constant mapping.

    This creates a dict mapping (method, path) tuples to sets of expected
    status codes for each operation.
    """
    entries: list[str] = []
    for operation in operations:
        statuses = known_statuses(operation)
        if not statuses:
            continue
        method = operation.method.upper()
        path = operation.path
        status_set = "{" + ", ".join(statuses) + "}"
        entries.append(f"    ({method!r}, {path!r}): {status_set},")
    if not entries:
        return ["EXPECTED_STATUSES: dict[tuple[str, str], set[str]] = {}", ""]
    return [
        "EXPECTED_STATUSES: dict[tuple[str, str], set[str]] = {",
        *entries,
        "}",
        "",
    ]


def emit_accept_types_map(operations: list[OperationIR]) -> list[str]:
    """Generate the ACCEPT_TYPES constant mapping.

    This creates a dict mapping (method, path) tuples to lists of
    acceptable content types for each operation's responses.
    """
    entries: list[str] = []
    for operation in operations:
        content_types: set[str] = set()
        for response in operation.responses:
            for media in response.content:
                content_types.add(media.content_type)
        if not content_types:
            continue
        method = operation.method.upper()
        path = operation.path
        types_list = "[" + ", ".join(repr(t) for t in sorted(content_types)) + "]"
        entries.append(f"    ({method!r}, {path!r}): {types_list},")
    if not entries:
        return ["ACCEPT_TYPES: dict[tuple[str, str], list[str]] = {}", ""]
    return [
        "ACCEPT_TYPES: dict[tuple[str, str], list[str]] = {",
        *entries,
        "}",
        "",
    ]


def emit_request_content_types_map(operations: list[OperationIR]) -> list[str]:
    """Generate the REQUEST_CONTENT_TYPES constant mapping.

    This creates a dict mapping (method, path) tuples to lists of
    acceptable request content types for each operation's request body.
    """
    entries: list[str] = []
    for operation in operations:
        request_body = operation.request_body
        if request_body is None:
            continue
        content_types = [media.content_type for media in request_body.content]
        if not content_types:
            continue
        method = operation.method.upper()
        path = operation.path
        types_list = "[" + ", ".join(repr(t) for t in sorted(content_types)) + "]"
        entries.append(f"    ({method!r}, {path!r}): {types_list},")
    if not entries:
        return ["REQUEST_CONTENT_TYPES: dict[tuple[str, str], list[str]] = {}", ""]
    return [
        "REQUEST_CONTENT_TYPES: dict[tuple[str, str], list[str]] = {",
        *entries,
        "}",
        "",
    ]
