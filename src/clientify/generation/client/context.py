from __future__ import annotations

from dataclasses import dataclass, field

from ..emitter import TypeEmitter
from ..profile import GenerationProfile


@dataclass
class ClientOutput:
    """Output of client code generation."""

    code: str


@dataclass
class ClientContext:
    """Context for client code generation.

    This class holds the state needed during client code generation,
    including the generation profile, type emitter, and collected imports.

    Note:
        The typing_imports and typing_extensions_imports sets are mutated
        during code generation to track required imports.
    """

    profile: GenerationProfile
    emitter: TypeEmitter
    typing_imports: set[str] = field(default_factory=set)
    typing_extensions_imports: set[str] = field(default_factory=set)
    uses_iterator: bool = False
