from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .generation import GenerationProfile, generate_client, generate_models, generate_types
from .ir import IRDocument


@dataclass(frozen=True)
class PackageSpec:
    package_name: str
    output_dir: Path


def generate_package(
    spec: PackageSpec,
    ir: IRDocument,
    profile: GenerationProfile,
) -> Path:
    package_dir = spec.output_dir / spec.package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    models_code = generate_models(ir.schemas, profile).code
    types_code = generate_types(profile).code
    schema_names = [schema.name for schema in ir.schemas]
    client_code = generate_client(ir.operations, schema_names, profile).code

    (package_dir / "models.py").write_text(models_code, encoding="utf-8")
    (package_dir / "types.py").write_text(types_code, encoding="utf-8")
    (package_dir / "client.py").write_text(client_code, encoding="utf-8")
    (package_dir / "__init__.py").write_text(_init_content(), encoding="utf-8")

    return package_dir


def _init_content() -> str:
    lines = [
        "from .client import (",
        "    AsyncClient,",
        "    ClientError,",
        "    DecodeError,",
        "    SyncClient,",
        "    TransportError,",
        "    create,",
        ")",
        "from .models import *  # noqa: F403",
        "from .types import (",
        "    CookieParams,",
        "    ErrorResponse,",
        "    HeaderParams,",
        "    Headers,",
        "    JsonValue,",
        "    PathParams,",
        "    QueryParams,",
        "    SuccessResponse,",
        ")",
        "",
        "__all__ = [",
        "    'SyncClient',",
        "    'AsyncClient',",
        "    'create',",
        "    'SuccessResponse',",
        "    'ErrorResponse',",
        "    'JsonValue',",
        "    'Headers',",
        "    'QueryParams',",
        "    'PathParams',",
        "    'HeaderParams',",
        "    'CookieParams',",
        "    'ClientError',",
        "    'TransportError',",
        "    'DecodeError',",
        "]",
        "",
    ]
    return "\n".join(lines)
