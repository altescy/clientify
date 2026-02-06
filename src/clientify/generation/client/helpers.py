from __future__ import annotations

from ...ir import OperationIR


def operation_name(method: str, path: str) -> str:
    """Convert an operation method and path to a PascalCase name.

    Example:
        >>> operation_name("get", "/users/{id}")
        'GetUsersId'
    """
    raw = f"{method}_{path}"
    cleaned = []
    prev_underscore = False
    for ch in raw:
        if ch.isalnum():
            cleaned.append(ch.lower())
            prev_underscore = False
        else:
            if not prev_underscore:
                cleaned.append("_")
                prev_underscore = True
    name = "".join(cleaned).strip("_")
    name = name.replace("_", " ").title().replace(" ", "")
    return name


def group_operations(operations: list[OperationIR]) -> dict[str, list[OperationIR]]:
    """Group operations by HTTP method."""
    grouped: dict[str, list[OperationIR]] = {}
    for operation in operations:
        grouped.setdefault(operation.method, []).append(operation)
    return grouped


def method_counts(operations: list[OperationIR]) -> dict[str, int]:
    """Count operations by HTTP method."""
    counts: dict[str, int] = {}
    for operation in operations:
        counts[operation.method] = counts.get(operation.method, 0) + 1
    return counts


def uses_streaming(operations: list[OperationIR]) -> bool:
    """Check if any operation uses streaming responses."""
    for operation in operations:
        for response in operation.responses:
            for media in response.content:
                if media.content_type == "text/event-stream":
                    return True
    return False


def known_statuses(operation: OperationIR) -> list[str]:
    """Get the known status codes for an operation."""
    statuses: list[str] = []
    for response in operation.responses:
        if response.status == "default":
            return []
        if response.status.isdigit():
            statuses.append(response.status)
    unique = [item for item in dict.fromkeys(statuses)]
    return [repr(item) for item in unique]


def import_insert_index(lines: list[str]) -> int:
    """Find the index where typing imports should be inserted."""
    for index, line in enumerate(lines):
        if line.startswith("from __future__ import"):
            return index + 1
    if lines and lines[0].startswith("# ruff:"):
        return 1
    return 0
