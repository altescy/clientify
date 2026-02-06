# Clientify - Agent Guidelines

This document provides guidelines for AI coding agents working on the clientify codebase.

## Project Overview

Clientify generates type-safe HTTP clients from OpenAPI specifications, producing both synchronous and asynchronous Python client code with full type annotations.

## Repository Structure

```
src/clientify/           # Main source code
├── __init__.py          # Public API exports
├── __main__.py          # CLI entry point
├── errors.py            # Custom exception hierarchy
├── ir.py                # Intermediate representation for OpenAPI
├── loader.py            # OpenAPI spec loading and $ref resolution (RefResolver class)
├── openapi.py           # TypedDict definitions for OpenAPI types
├── generator.py         # Package generation orchestration
└── generation/          # Code generation modules
    ├── client/          # Client class generation (modular package)
    │   ├── __init__.py  # generate_client() entry point
    │   ├── context.py   # ClientContext, ClientOutput dataclasses
    │   ├── protocols.py # Backend protocols and client errors
    │   ├── helpers.py   # Utility functions (operation_name, group_operations)
    │   ├── params.py    # Parameter type generation
    │   ├── response.py  # Response type generation
    │   ├── methods.py   # HTTP method generation with overloads
    │   ├── templates.py # Client __init__ and request implementation
    │   └── maps.py      # Status/content-type mapping generation
    ├── emitter.py       # Type emission utilities
    ├── models.py        # Model class generation
    ├── profile.py       # Python version profiles
    └── types.py         # Type definitions generation
tests/                   # Test files mirror src structure
```

## Build, Lint, and Test Commands

This project uses `uv` as the package manager and task runner.

### Full Quality Check
```bash
make all        # Runs format, lint, and test
```

### Testing
```bash
# Run all tests
make test
# Or directly:
PYTHONPATH=$(pwd) uv run pytest

# Run a single test file
uv run pytest tests/generation/test_client.py -v

# Run a specific test class
uv run pytest tests/generation/test_client.py::TestGenerateClient -v

# Run a specific test method
uv run pytest tests/generation/test_client.py::TestGenerateClient::test_generates_sync_and_async -v

# Run tests with output
uv run pytest -v -s
```

### Linting
```bash
make lint       # Runs both ruff check and pyright
# Or separately:
PYTHONPATH=$(PWD) uv run ruff check
PYTHONPATH=$(PWD) uv run pyright
```

### Formatting
```bash
make format     # Sorts imports and formats code
# - uv run ruff check --select I --fix  (import sorting)
# - uv run ruff format                  (code formatting)
```

## Code Style Guidelines

### Python Version
- Minimum Python 3.10 required
- Target Python 3.14 for pyright type checking
- Use `from __future__ import annotations` in all files

### Formatting
- Line length: 120 characters (configured in pyproject.toml)
- Use ruff for formatting and linting
- Use pyright for static type checking

### Imports
Order imports as follows (ruff handles this with `--select I`):
1. `from __future__ import annotations` (always first)
2. Standard library imports
3. Third-party imports
4. Local imports (relative imports preferred within package)

### Type Annotations (Strict Type Hints)
- **Always** use type hints for function parameters and return types - no exceptions
- Use `TypedDict` for structured dictionaries (see `openapi.py` for examples)
- Use `cast()` when narrowing types from dict access
- Use union syntax `X | Y` for Python 3.10+ style unions
- Use `object` for truly dynamic values, **never use `Any`**
- All public APIs must have complete type annotations
- Pyright must pass with no errors before merging code

### Dataclasses
- Use `@dataclass(frozen=True)` for immutable data structures (preferred)
- Use `@dataclass` without frozen for mutable state when needed

### Naming Conventions
- **Classes**: PascalCase (e.g., `IRDocument`, `SchemaIR`)
- **Functions/Methods**: snake_case (e.g., `build_ir`, `load_openapi`)
- **Variables**: snake_case (e.g., `document`, `base_path`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `EXPECTED_STATUSES`)
- **Private functions**: prefix with underscore (e.g., `_resolve_ref`, `_build_parameter`)
- **Type aliases**: PascalCase (e.g., `OpenAPISource = str | Path | Mapping[str, object]`)

### Error Handling
- Define custom exceptions inheriting from `ClientifyError` base class
- Use specific exception types for different error categories (e.g., `SpecError`)
- Raise with descriptive messages

### Testing
- Use pytest as the test framework
- Organize tests in classes prefixed with `Test`
- Test methods prefixed with `test_`
- Use fixtures in `conftest.py` for shared test data
- Return type hints should be `-> None` for test methods

Example:
```python
class TestGenerateClient:
    def test_generates_sync_and_async(self) -> None:
        operations = [...]
        output = generate_client(operations, ["User"], profile).code
        assert "class SyncClient" in output
```

## Development Workflow

### Test-Driven Development
When implementing a new feature or fixing a bug:
1. Write corresponding tests first (or alongside the implementation)
2. Run `make lint` to check code style and type errors
3. Run `make test` to verify all tests pass
4. Never commit code without passing both lint and test

### Dependency Injection Pattern
- Avoid direct dependencies on specific libraries or frameworks
- Use Protocol classes to define abstract interfaces
- Inject dependencies through constructor parameters
- This enables easy testing and swapping implementations

Example from the codebase:
```python
# Protocol defines the interface (see generation/client/protocols.py)
class SyncBackend(Protocol):
    def request(self, method: str, url: str, ...) -> SyncResponse:
        ...

# Client accepts any backend that implements the Protocol
class SyncClient:
    def __init__(self, base_url: str, backend: SyncBackend, ...) -> None:
        self._backend = backend
```

### Code Generation Patterns
When generating Python code as strings:
- Build code as `list[str]` of lines
- Join with newlines at the end
- Ensure trailing newline in output
- Use ruff noqa comments when needed (e.g., `# ruff: noqa: F401`)

## Key Architectural Patterns

### IR (Intermediate Representation)
The codebase converts OpenAPI specs to an IR before code generation:
1. `loader.py`: Load and resolve $ref references
2. `ir.py`: Convert to simplified IR structures
3. `generation/`: Generate Python code from IR

### TypedDict for OpenAPI Types
OpenAPI structures are defined as TypedDict in `openapi.py` for type safety without runtime overhead.

### Generation Profiles
`GenerationProfile` adapts output for different Python versions, controlling features like PEP 604 union syntax and typing_extensions usage.

## CLI Usage
```bash
clientify spec.yaml --package-name myapi --output-dir ./generated
```
