"""FastAPI server for integration testing.

This module provides a simple Pet Store API that matches the OpenAPI spec
in openapi.yaml. It is used to test the generated client code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    species: str
    age: int | None = None


class CreatePetRequest(BaseModel):
    name: str
    species: str
    age: int | None = None


class UpdatePetRequest(BaseModel):
    name: str | None = None
    species: str | None = None
    age: int | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str


class HealthResponse(BaseModel):
    status: str


@dataclass
class PetStore:
    """In-memory pet store for testing."""

    pets: dict[int, Pet] = field(default_factory=dict)
    next_id: int = 1

    def reset(self) -> None:
        """Reset the store to initial state."""
        self.pets.clear()
        self.next_id = 1

    def list_pets(self, limit: int = 10, offset: int = 0) -> list[Pet]:
        """List pets with pagination."""
        all_pets = list(self.pets.values())
        return all_pets[offset : offset + limit]

    def get_pet(self, pet_id: int) -> Pet | None:
        """Get a pet by ID."""
        return self.pets.get(pet_id)

    def create_pet(self, request: CreatePetRequest) -> Pet:
        """Create a new pet."""
        pet = Pet(
            id=self.next_id,
            name=request.name,
            species=request.species,
            age=request.age,
        )
        self.pets[pet.id] = pet
        self.next_id += 1
        return pet

    def update_pet(self, pet_id: int, request: UpdatePetRequest) -> Pet | None:
        """Update an existing pet."""
        pet = self.pets.get(pet_id)
        if pet is None:
            return None
        if request.name is not None:
            pet = Pet(id=pet.id, name=request.name, species=pet.species, age=pet.age)
        if request.species is not None:
            pet = Pet(id=pet.id, name=pet.name, species=request.species, age=pet.age)
        if request.age is not None:
            pet = Pet(id=pet.id, name=pet.name, species=pet.species, age=request.age)
        self.pets[pet_id] = pet
        return pet

    def delete_pet(self, pet_id: int) -> bool:
        """Delete a pet. Returns True if deleted, False if not found."""
        if pet_id in self.pets:
            del self.pets[pet_id]
            return True
        return False


# Global store instance
store = PetStore()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Pet Store API", version="1.0.0")

    @app.get("/pets", response_model=list[Pet])
    def list_pets(
        limit: Annotated[int, Query()] = 10,
        offset: Annotated[int, Query()] = 0,
    ) -> list[Pet]:
        return store.list_pets(limit=limit, offset=offset)

    @app.post("/pets", response_model=Pet, status_code=201)
    def create_pet(request: CreatePetRequest) -> Pet:
        return store.create_pet(request)

    @app.get("/pets/{pet_id}", response_model=Pet)
    def get_pet(pet_id: Annotated[int, Path()]) -> Pet:
        pet = store.get_pet(pet_id)
        if pet is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="not_found", message=f"Pet with id {pet_id} not found").model_dump(),
            )
        return pet

    @app.put("/pets/{pet_id}", response_model=Pet)
    def update_pet(pet_id: Annotated[int, Path()], request: UpdatePetRequest) -> Pet:
        pet = store.update_pet(pet_id, request)
        if pet is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="not_found", message=f"Pet with id {pet_id} not found").model_dump(),
            )
        return pet

    @app.delete("/pets/{pet_id}", status_code=204)
    def delete_pet(pet_id: Annotated[int, Path()]) -> None:
        if not store.delete_pet(pet_id):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(error="not_found", message=f"Pet with id {pet_id} not found").model_dump(),
            )

    @app.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
