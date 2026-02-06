# Clientify

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Generate type-safe HTTP clients from OpenAPI specifications.

Clientify produces both synchronous and asynchronous Python client code with full type annotations, enabling IDE autocompletion and static type checking with tools like pyright and mypy.

## Features

- **Type-Safe**: Full type annotations for request parameters, bodies, and responses
- **Sync & Async**: Generates both synchronous and asynchronous client classes
- **Backend Agnostic**: Works with any HTTP library that implements the simple Backend protocol (httpx, requests, aiohttp, etc.)
- **Overloaded Methods**: Path-specific type hints via `@overload` for precise return types
- **Model Generation**: Pydantic-style dataclasses for request/response schemas
- **Python 3.10+**: Modern Python syntax with union types (`X | Y`) and other features

## Quick Start

### 1. Generate a Client

Run clientify using `uvx` (no installation required):

```bash
uvx --from git+https://github.com/altescy/clientify clientify openapi.yaml -n myapi -o ./generated
```

This creates a Python package with:

```
generated/
└── myapi/
    ├── __init__.py    # Public exports
    ├── client.py      # SyncClient and AsyncClient classes
    ├── models.py      # Dataclass models for schemas
    └── types.py       # Response type definitions
```

### 2. Use the Generated Client

```python
import httpx
from myapi import SyncClient, AsyncClient

# Synchronous client
with httpx.Client() as backend:
    client = SyncClient(base_url="https://api.example.com", backend=backend)

    # Type-safe API calls
    response = client.get("/users")
    users = response.body  # Fully typed based on OpenAPI spec

    # With parameters
    response = client.post(
        "/users",
        body={"name": "Alice", "email": "alice@example.com"},
        content_type="application/json",
    )

# Asynchronous client
async with httpx.AsyncClient() as backend:
    client = AsyncClient(base_url="https://api.example.com", backend=backend)

    response = await client.get("/users/{user_id}", params={"path": {"user_id": 123}})
    user = response.body
```

## CLI Usage

```bash
clientify <spec> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `spec` | Path or URL to OpenAPI spec file (YAML or JSON) |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--package-name`, `-n` | Name of the generated package | `client` |
| `--output-dir`, `-o` | Output directory | `.` |
| `--python-version` | Target Python version | `3.10` |

### Examples

```bash
# Basic usage
clientify api.yaml -n myapi -o ./src

# Target specific Python version
clientify api.yaml -n myapi --python-version 3.12

# From URL
clientify https://api.example.com/openapi.json -n myapi

# Using uvx (no installation required)
uvx --from git+https://github.com/altescy/clientify clientify api.yaml -n myapi

# Using uvx with a specific branch or tag
uvx --from git+https://github.com/altescy/clientify@main clientify api.yaml -n myapi
```

## Backend Protocol

The generated clients accept any backend that implements a simple protocol:

```python
from typing import Protocol, Iterator

class SyncBackend(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response: ...

class AsyncBackend(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response: ...
```

### Using with httpx (Recommended)

[httpx](https://www.python-httpx.org/) clients directly satisfy the Backend protocol:

```python
import httpx
from myapi import SyncClient, AsyncClient

# httpx.Client works directly as SyncBackend
client = SyncClient(base_url="https://api.example.com", backend=httpx.Client())

# httpx.AsyncClient works directly as AsyncBackend
async_client = AsyncClient(base_url="https://api.example.com", backend=httpx.AsyncClient())
```

### Using with requests

For `requests`, create a simple wrapper:

```python
import requests
from myapi import SyncClient

class RequestsBackend:
    def __init__(self) -> None:
        self.session = requests.Session()

    def request(self, method: str, url: str, *, content=None, headers=None, timeout=None):
        response = self.session.request(
            method=method,
            url=url,
            data=content,
            headers=headers,
            timeout=timeout,
        )
        return response

client = SyncClient(base_url="https://api.example.com", backend=RequestsBackend())
```

## Generated Code Structure

### Client Classes

```python
class SyncClient:
    def __init__(
        self,
        base_url: str,
        backend: SyncBackend,
        headers: Mapping[str, str] | None = None,
        raise_on_unexpected_status: bool = True,
    ) -> None: ...

    # HTTP methods with overloads for each endpoint
    @overload
    def get(self, url: Literal["/users"], ...) -> GetUsersResponse: ...
    @overload
    def get(self, url: Literal["/users/{user_id}"], ...) -> GetUserResponse: ...
    def get(self, url: str, ...) -> Response: ...

    def post(self, url: str, *, body: object, ...) -> Response: ...
    def put(self, url: str, *, body: object, ...) -> Response: ...
    def delete(self, url: str, ...) -> Response: ...
    def patch(self, url: str, *, body: object, ...) -> Response: ...
```

### Response Types

```python
from myapi.types import SuccessResponse, ErrorResponse

response = client.get("/users")

if isinstance(response, SuccessResponse):
    print(response.status)   # int (200-299)
    print(response.headers)  # dict[str, str]
    print(response.body)     # Typed based on OpenAPI response schema
```

### Parameter Types

Parameters are passed via the `params` dict with typed sub-dicts:

```python
response = client.get(
    "/users/{user_id}/posts",
    params={
        "path": {"user_id": 123},           # Path parameters
        "query": {"limit": 10, "offset": 0}, # Query parameters
        "header": {"X-Request-ID": "abc"},   # Header parameters
    },
)
```

## Python Version Support

Clientify supports Python 3.10 and above. The generated code adapts to the target Python version:

| Python Version | Features Used |
|---------------|---------------|
| 3.10+ | `X \| Y` union syntax, `match` statements |
| 3.11+ | `Self` type, `ExceptionGroup` |
| 3.12+ | Type parameter syntax (`class Foo[T]:`) |

Specify the target version:

```bash
clientify api.yaml -n myapi --python-version 3.12
```

## Development

### Setup

```bash
git clone https://github.com/altescy/clientify.git
cd clientify
uv sync
```

### Commands

```bash
# Run all checks (format, lint, test)
make all

# Individual commands
make format  # Format code with ruff
make lint    # Run ruff and pyright
make test    # Run pytest
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/generation/test_client.py -v

# Integration tests only
uv run pytest tests/integration/ -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run `make all` to ensure tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request
