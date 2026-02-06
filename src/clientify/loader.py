from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Mapping, cast
from urllib.parse import urldefrag, urlparse

from .errors import SpecError
from .openapi import OpenAPIDocument

OpenAPISource = str | PathLike[str] | Mapping[str, object]


def load_openapi(
    source: OpenAPISource,
    base_path: str | PathLike[str] | None = None,
) -> OpenAPIDocument:
    """Load and resolve an OpenAPI document from various sources.

    Args:
        source: Can be a file path (str or PathLike), URL, or a dict-like object
        base_path: Base path for resolving relative $ref references

    Returns:
        Fully resolved OpenAPI document with all $refs expanded
    """
    resolved_base_path = Path(base_path) if base_path is not None else None
    document, resolved_base = _read_source(source, resolved_base_path)
    if not isinstance(document, dict):
        raise SpecError("OpenAPI document must be an object")
    openapi_version = document.get("openapi")
    if not isinstance(openapi_version, str):
        raise SpecError("Missing or invalid 'openapi' field in document")
    resolver = RefResolver(document, resolved_base)
    return resolver.resolve()


def resolve_refs(
    document: OpenAPIDocument,
    base_path: str | PathLike[str] | None,
) -> OpenAPIDocument:
    """Resolve all $ref references in an OpenAPI document.

    This function is kept for backwards compatibility.
    Use RefResolver directly for more control.
    """
    resolved_base_path = Path(base_path) if base_path is not None else None
    resolver = RefResolver(document, resolved_base_path)
    return resolver.resolve()


@dataclass
class RefResolver:
    """Resolves $ref references in OpenAPI documents.

    This class handles:
    - Local references (#/components/schemas/...)
    - External file references (./other-file.yaml#/...)
    - Circular reference detection via caching
    - Merging of sibling properties with $ref

    Example:
        >>> resolver = RefResolver(document, Path("./specs"))
        >>> resolved = resolver.resolve()
    """

    document: OpenAPIDocument
    base_path: Path | None
    _cache: dict[str, object] = field(default_factory=dict, init=False)
    _doc_cache: dict[Path, OpenAPIDocument] = field(default_factory=dict, init=False)

    def resolve(self) -> OpenAPIDocument:
        """Resolve all $refs in the document.

        Returns:
            A new OpenAPIDocument with all references resolved
        """
        effective_base = self.base_path or Path.cwd()
        return cast(OpenAPIDocument, self._resolve_object(self.document, effective_base))

    def _resolve_object(self, obj: object, current_base: Path) -> object:
        """Recursively resolve an object, expanding any $refs found.

        Args:
            obj: The object to resolve (can be dict, list, or primitive)
            current_base: The base path for resolving relative references

        Returns:
            The resolved object with all $refs expanded
        """
        if isinstance(obj, list):
            return [self._resolve_object(item, current_base) for item in obj]
        if not isinstance(obj, dict):
            return obj
        obj_dict = cast(dict[str, object], obj)
        if "$ref" in obj_dict:
            ref = obj_dict["$ref"]
            if not isinstance(ref, str):
                raise SpecError("$ref must be a string")
            resolved = self._resolve_ref(ref, current_base)
            if len(obj_dict) == 1:
                return resolved
            if not isinstance(resolved, dict):
                raise SpecError("$ref target must be an object when merged")
            merged = deepcopy(cast(dict[str, object], resolved))
            for key, value in obj_dict.items():
                if key == "$ref":
                    continue
                merged[key] = self._resolve_object(value, current_base)
            return merged
        return {key: self._resolve_object(value, current_base) for key, value in obj_dict.items()}

    def _resolve_ref(self, ref: str, current_base: Path) -> object:
        """Resolve a single $ref string to its target value.

        Args:
            ref: The $ref string (e.g., "#/components/schemas/User")
            current_base: The base path for resolving relative file references

        Returns:
            The resolved value (recursively resolved if it contains more $refs)
        """
        if ref in self._cache:
            return deepcopy(self._cache[ref])
        path_part, frag = urldefrag(ref)
        if path_part:
            target_path = (current_base / path_part).resolve()
            target_doc = _load_doc(target_path, self._doc_cache)
            base_for_ref = target_path.parent
        else:
            target_doc = self.document
            base_for_ref = current_base
        if frag and not frag.startswith("/"):
            raise SpecError(f"Unsupported $ref fragment: {frag}")
        resolved = _resolve_pointer(target_doc, frag)
        if ref.startswith("#/components/schemas/") and isinstance(resolved, dict):
            name = ref.split("/")[-1]
            resolved = dict(resolved)
            resolved.setdefault("x-clientify-schema-name", name)
        self._cache[ref] = deepcopy(resolved)
        return self._resolve_object(resolved, base_for_ref)


def _is_url(source: str) -> bool:
    """Check if the source string is a URL."""
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"}


def _fetch_url(url: str) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        The response text content

    Raises:
        SpecError: If the URL cannot be fetched
    """
    try:
        from urllib.request import Request, urlopen
    except ImportError as exc:  # pragma: no cover
        raise SpecError("urllib is required to fetch URLs") from exc

    try:
        request = Request(url, headers={"User-Agent": "clientify"})
        with urlopen(request, timeout=30) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except Exception as exc:
        raise SpecError(f"Failed to fetch URL: {url}") from exc


def _get_url_extension(url: str) -> str:
    """Extract file extension from URL path."""
    parsed = urlparse(url)
    path = parsed.path
    if "." in path:
        return "." + path.rsplit(".", 1)[-1].lower()
    return ""


def _read_source(
    source: OpenAPISource,
    base_path: Path | None,
) -> tuple[OpenAPIDocument, Path | None]:
    """Read an OpenAPI document from various source types.

    Args:
        source: Can be a file path (str or PathLike), URL, or a dict-like object
        base_path: Optional base path override

    Returns:
        Tuple of (document, resolved_base_path)
    """
    if isinstance(source, Mapping):
        if base_path is None:
            return cast(OpenAPIDocument, dict(source)), None
        return cast(OpenAPIDocument, dict(source)), base_path

    source_str = str(source) if isinstance(source, PathLike) else source

    # Handle URL sources
    if _is_url(source_str):
        text = _fetch_url(source_str)
        ext = _get_url_extension(source_str)
        if ext in {".yaml", ".yml"}:
            data = _load_yaml(text)
        else:
            data = _load_json_or_yaml(text)
        if not isinstance(data, dict):
            raise SpecError("OpenAPI document must be an object")
        # For URL sources, we don't support relative $ref resolution to other URLs
        # The base_path remains None or the provided override
        return cast(OpenAPIDocument, data), base_path

    # Handle file path sources
    path = Path(source_str)
    resolved_base = path.parent
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = _load_yaml(text)
    else:
        data = _load_json_or_yaml(text)
    if not isinstance(data, dict):
        raise SpecError("OpenAPI document must be an object")
    return cast(OpenAPIDocument, data), resolved_base


def _load_json_or_yaml(text: str) -> object:
    """Try to load as JSON, fall back to YAML if that fails."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _load_yaml(text)


def _load_yaml(text: str) -> object:
    """Load YAML text, requiring PyYAML to be installed."""
    try:
        import yaml  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise SpecError("PyYAML is required to load YAML specs") from exc
    return yaml.safe_load(text)


def _load_doc(path: Path, cache: dict[Path, OpenAPIDocument]) -> OpenAPIDocument:
    """Load an external document, caching the result.

    Args:
        path: Path to the document file
        cache: Cache dict to store loaded documents

    Returns:
        The loaded OpenAPI document
    """
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
    """Resolve a JSON pointer fragment within a document.

    Args:
        document: The document to resolve within
        fragment: The JSON pointer (e.g., "/components/schemas/User")

    Returns:
        The value at the pointer location

    Raises:
        SpecError: If the pointer cannot be resolved
    """
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
