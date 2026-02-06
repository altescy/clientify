from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Mapping, cast
from urllib.parse import urldefrag

from .errors import SpecError
from .openapi import OpenAPIDocument

OpenAPISource = str | Path | Mapping[str, object]


def load_openapi(source: OpenAPISource, base_path: Path | None = None) -> OpenAPIDocument:
    document, resolved_base = _read_source(source, base_path)
    if not isinstance(document, dict):
        raise SpecError("OpenAPI document must be an object")
    openapi_version = document.get("openapi")
    if not isinstance(openapi_version, str):
        raise SpecError("Missing or invalid 'openapi' field in document")
    resolved = resolve_refs(document, resolved_base)
    return resolved


def resolve_refs(document: OpenAPIDocument, base_path: Path | None) -> OpenAPIDocument:
    cache: dict[str, object] = {}
    doc_cache: dict[Path, OpenAPIDocument] = {}
    base_path = base_path or Path.cwd()

    def _resolve(obj: object, current_base: Path) -> object:
        if isinstance(obj, list):
            return [_resolve(item, current_base) for item in obj]
        if not isinstance(obj, dict):
            return obj
        obj_dict = cast(dict[str, object], obj)
        if "$ref" in obj_dict:
            ref = obj_dict["$ref"]
            if not isinstance(ref, str):
                raise SpecError("$ref must be a string")
            resolved = _resolve_ref(ref, current_base)
            if len(obj_dict) == 1:
                return resolved
            if not isinstance(resolved, dict):
                raise SpecError("$ref target must be an object when merged")
            merged = deepcopy(cast(dict[str, object], resolved))
            for key, value in obj_dict.items():
                if key == "$ref":
                    continue
                merged[key] = _resolve(value, current_base)
            return merged
        return {key: _resolve(value, current_base) for key, value in obj_dict.items()}

    def _resolve_ref(ref: str, current_base: Path) -> object:
        if ref in cache:
            return deepcopy(cache[ref])
        path_part, frag = urldefrag(ref)
        if path_part:
            target_path = (current_base / path_part).resolve()
            target_doc = _load_doc(target_path, doc_cache)
            base_for_ref = target_path.parent
        else:
            target_doc = document
            base_for_ref = current_base
        if frag and not frag.startswith("/"):
            raise SpecError(f"Unsupported $ref fragment: {frag}")
        resolved = _resolve_pointer(target_doc, frag)
        if ref.startswith("#/components/schemas/") and isinstance(resolved, dict):
            name = ref.split("/")[-1]
            resolved = dict(resolved)
            resolved.setdefault("x-clientify-schema-name", name)
        cache[ref] = deepcopy(resolved)
        return _resolve(resolved, base_for_ref)

    return cast(OpenAPIDocument, _resolve(document, base_path))


def _read_source(source: OpenAPISource, base_path: Path | None) -> tuple[OpenAPIDocument, Path | None]:
    if isinstance(source, Mapping):
        if base_path is None:
            return cast(OpenAPIDocument, dict(source)), None
        return cast(OpenAPIDocument, dict(source)), base_path
    path = Path(source)
    base_path = path.parent
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = _load_yaml(text)
    else:
        data = _load_json_or_yaml(text)
    if not isinstance(data, dict):
        raise SpecError("OpenAPI document must be an object")
    return cast(OpenAPIDocument, data), base_path


def _load_json_or_yaml(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _load_yaml(text)


def _load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise SpecError("PyYAML is required to load YAML specs") from exc
    return yaml.safe_load(text)


def _load_doc(path: Path, cache: dict[Path, OpenAPIDocument]) -> OpenAPIDocument:
    if path in cache:
        return cache[path]
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = _load_yaml(text)
    else:
        data = _load_json_or_yaml(text)
    if not isinstance(data, dict):
        raise SpecError(f"Referenced document must be an object: {path}")
    cache[path] = cast(OpenAPIDocument, data)
    return cache[path]


def _resolve_pointer(document: OpenAPIDocument, fragment: str) -> object:
    if fragment in {"", "#"}:
        return document
    pointer = fragment[1:] if fragment.startswith("/") else fragment
    current: object = document
    for part in pointer.split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise SpecError(f"Unresolvable $ref pointer: #{fragment}")
    return current
