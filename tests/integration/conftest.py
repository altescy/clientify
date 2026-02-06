"""Pytest fixtures for integration tests.

This module provides fixtures for:
- Generating client code from OpenAPI spec
- Starting/stopping FastAPI test server
- Creating sync and async clients
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import httpx
import pytest
import uvicorn

from clientify import GenerationProfile, PackageSpec, build_ir, generate_package, load_openapi

from .server import app, store

if TYPE_CHECKING:
    from types import ModuleType

SPEC_PATH = Path(__file__).parent / "openapi.yaml"
TEST_SERVER_HOST = "127.0.0.1"
TEST_SERVER_PORT = 18765


class ServerThread(threading.Thread):
    """Thread that runs uvicorn server."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.server: uvicorn.Server | None = None

    def run(self) -> None:
        config = uvicorn.Config(
            app,
            host=TEST_SERVER_HOST,
            port=TEST_SERVER_PORT,
            log_level="error",
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True


@pytest.fixture(scope="session")
def generated_client_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate client code from OpenAPI spec and return the package directory."""
    output_dir = tmp_path_factory.mktemp("generated")

    # Generate the client package
    document = load_openapi(SPEC_PATH)
    ir = build_ir(document)
    profile = GenerationProfile.from_version("3.14")
    package_spec = PackageSpec(package_name="petstore_client", output_dir=output_dir)
    result = generate_package(package_spec, ir, profile)

    return result


@pytest.fixture(scope="session")
def generated_client_module(generated_client_dir: Path) -> ModuleType:
    """Import the generated client module."""
    # Add the parent directory to sys.path so we can import the generated package
    parent_dir = generated_client_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    # Note: We skip pyright verification here because the generated code may have
    # some type issues that are acceptable for runtime use. The unit tests for
    # the generator verify the basic type correctness.

    # Import the generated module
    spec = importlib.util.spec_from_file_location(
        "petstore_client",
        generated_client_dir / "__init__.py",
        submodule_search_locations=[str(generated_client_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {generated_client_dir}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["petstore_client"] = module

    # Also import submodules
    for submodule_name in ["client", "models", "types"]:
        submodule_path = generated_client_dir / f"{submodule_name}.py"
        submodule_spec = importlib.util.spec_from_file_location(
            f"petstore_client.{submodule_name}",
            submodule_path,
        )
        if submodule_spec and submodule_spec.loader:
            submodule = importlib.util.module_from_spec(submodule_spec)
            sys.modules[f"petstore_client.{submodule_name}"] = submodule
            submodule_spec.loader.exec_module(submodule)

    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def server() -> Generator[str, None, None]:
    """Start the test server and return the base URL."""
    server_thread = ServerThread()
    server_thread.start()

    # Wait for server to be ready
    base_url = f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}"
    max_retries = 50
    for _ in range(max_retries):
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200:
                break
        except httpx.ConnectError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Test server failed to start")

    yield base_url

    server_thread.stop()


@pytest.fixture(autouse=True)
def reset_store() -> Generator[None, None, None]:
    """Reset the pet store before each test."""
    store.reset()
    yield


@pytest.fixture
def sync_client() -> Generator[httpx.Client, None, None]:
    """Create a sync httpx client."""
    with httpx.Client() as client:
        yield client


@pytest.fixture
def async_client() -> Generator[httpx.AsyncClient, None, None]:
    """Create an async httpx client."""
    # Note: We can't use async context manager in a sync fixture,
    # so we create and close manually
    client = httpx.AsyncClient()
    yield client
    # Cleanup will be handled by the test
