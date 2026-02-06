"""Integration tests for generated clientify clients.

These tests verify that:
1. Client code is correctly generated from OpenAPI spec
2. Generated code passes type checking
3. Sync and async clients work correctly with a real FastAPI server
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest


class TestClientGeneration:
    """Tests for client code generation."""

    def test_generates_client_files(self, generated_client_dir: Path) -> None:
        """Verify all expected files are generated."""
        assert (generated_client_dir / "__init__.py").exists()
        assert (generated_client_dir / "client.py").exists()
        assert (generated_client_dir / "models.py").exists()
        assert (generated_client_dir / "types.py").exists()

    def test_generated_code_is_valid_python(self, generated_client_module: ModuleType) -> None:
        """Verify generated code can be imported."""
        assert hasattr(generated_client_module, "SyncClient")
        assert hasattr(generated_client_module, "AsyncClient")
        assert hasattr(generated_client_module, "create")

    def test_generated_models_exist(self, generated_client_module: ModuleType) -> None:
        """Verify expected model classes are generated."""
        # Check that Pet model exists
        assert hasattr(generated_client_module, "Pet")
        assert hasattr(generated_client_module, "CreatePetRequest")
        assert hasattr(generated_client_module, "UpdatePetRequest")
        assert hasattr(generated_client_module, "ErrorResponse")
        assert hasattr(generated_client_module, "HealthResponse")


class TestSyncClient:
    """Tests for the synchronous client."""

    def test_health_check(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test health check endpoint."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
        )
        response = client.get("/health")
        assert response.status == 200
        assert response.body["status"] == "ok"

    def test_create_and_get_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test creating and retrieving a pet."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
        )

        # Create a pet
        create_response = client.post(
            "/pets",
            body={"name": "Fluffy", "species": "cat", "age": 3},
            content_type="application/json",
        )
        assert create_response.status == 201
        pet_data: dict[str, Any] = create_response.body
        assert pet_data["name"] == "Fluffy"
        assert pet_data["species"] == "cat"
        assert pet_data["age"] == 3
        pet_id = pet_data["id"]

        # Get the pet
        get_response = client.get(f"/pets/{pet_id}")
        assert get_response.status == 200
        assert get_response.body["id"] == pet_id
        assert get_response.body["name"] == "Fluffy"

    def test_list_pets(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test listing pets with pagination."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
        )

        # Create multiple pets
        for i in range(5):
            client.post(
                "/pets",
                body={"name": f"Pet{i}", "species": "dog"},
                content_type="application/json",
            )

        # List all pets
        response = client.get("/pets")
        assert response.status == 200
        pets: list[dict[str, Any]] = response.body
        assert len(pets) == 5

        # List with limit
        response = client.get("/pets", params={"query": {"limit": 2}})
        assert response.status == 200
        pets = response.body
        assert len(pets) == 2

        # List with offset
        response = client.get("/pets", params={"query": {"offset": 3}})
        assert response.status == 200
        pets = response.body
        assert len(pets) == 2

    def test_update_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test updating a pet."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
        )

        # Create a pet
        create_response = client.post(
            "/pets",
            body={"name": "Buddy", "species": "dog"},
            content_type="application/json",
        )
        pet_id = create_response.body["id"]

        # Update the pet
        update_response = client.put(
            f"/pets/{pet_id}",
            body={"name": "Max", "age": 5},
            content_type="application/json",
        )
        assert update_response.status == 200
        assert update_response.body["name"] == "Max"
        assert update_response.body["age"] == 5

    def test_delete_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test deleting a pet."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
        )

        # Create a pet
        create_response = client.post(
            "/pets",
            body={"name": "ToDelete", "species": "hamster"},
            content_type="application/json",
        )
        pet_id = create_response.body["id"]

        # Delete the pet
        delete_response = client.delete(f"/pets/{pet_id}")
        assert delete_response.status == 204

        # Verify pet is gone
        get_response = client.get(f"/pets/{pet_id}")
        assert get_response.status == 404

    def test_not_found_error(
        self,
        server: str,
        generated_client_module: ModuleType,
        sync_client: httpx.Client,
    ) -> None:
        """Test 404 response handling."""
        client = generated_client_module.SyncClient(
            base_url=server,
            backend=sync_client,
            raise_on_unexpected_status=False,
        )

        response = client.get("/pets/99999")
        assert response.status == 404


class TestAsyncClient:
    """Tests for the asynchronous client."""

    @pytest.mark.anyio
    async def test_health_check(
        self,
        server: str,
        generated_client_module: ModuleType,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Test health check endpoint with async client."""
        client = generated_client_module.AsyncClient(
            base_url=server,
            backend=async_client,
        )
        response = await client.get("/health")
        assert response.status == 200
        assert response.body["status"] == "ok"

    @pytest.mark.anyio
    async def test_create_and_get_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Test creating and retrieving a pet with async client."""
        client = generated_client_module.AsyncClient(
            base_url=server,
            backend=async_client,
        )

        # Create a pet
        create_response = await client.post(
            "/pets",
            body={"name": "AsyncPet", "species": "bird", "age": 2},
            content_type="application/json",
        )
        assert create_response.status == 201
        pet_data: dict[str, Any] = create_response.body
        assert pet_data["name"] == "AsyncPet"
        pet_id = pet_data["id"]

        # Get the pet
        get_response = await client.get(f"/pets/{pet_id}")
        assert get_response.status == 200
        assert get_response.body["name"] == "AsyncPet"

    @pytest.mark.anyio
    async def test_list_pets(
        self,
        server: str,
        generated_client_module: ModuleType,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Test listing pets with async client."""
        client = generated_client_module.AsyncClient(
            base_url=server,
            backend=async_client,
        )

        # Create multiple pets
        for i in range(3):
            await client.post(
                "/pets",
                body={"name": f"AsyncPet{i}", "species": "fish"},
                content_type="application/json",
            )

        # List all pets
        response = await client.get("/pets")
        assert response.status == 200
        pets: list[dict[str, Any]] = response.body
        assert len(pets) == 3

    @pytest.mark.anyio
    async def test_update_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Test updating a pet with async client."""
        client = generated_client_module.AsyncClient(
            base_url=server,
            backend=async_client,
        )

        # Create a pet
        create_response = await client.post(
            "/pets",
            body={"name": "AsyncBuddy", "species": "rabbit"},
            content_type="application/json",
        )
        pet_id = create_response.body["id"]

        # Update the pet
        update_response = await client.put(
            f"/pets/{pet_id}",
            body={"name": "AsyncMax"},
            content_type="application/json",
        )
        assert update_response.status == 200
        assert update_response.body["name"] == "AsyncMax"

    @pytest.mark.anyio
    async def test_delete_pet(
        self,
        server: str,
        generated_client_module: ModuleType,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Test deleting a pet with async client."""
        client = generated_client_module.AsyncClient(
            base_url=server,
            backend=async_client,
        )

        # Create a pet
        create_response = await client.post(
            "/pets",
            body={"name": "AsyncToDelete", "species": "turtle"},
            content_type="application/json",
        )
        pet_id = create_response.body["id"]

        # Delete the pet
        delete_response = await client.delete(f"/pets/{pet_id}")
        assert delete_response.status == 204

        # Verify pet is gone
        get_response = await client.get(f"/pets/{pet_id}")
        assert get_response.status == 404
