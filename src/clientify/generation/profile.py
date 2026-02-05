from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationProfile:
    use_future_annotations: bool
    use_pep604: bool
    use_required: bool
    use_typing_extensions: bool

    @classmethod
    def from_version(cls, target_version: str | tuple[int, int]) -> "GenerationProfile":
        if isinstance(target_version, str):
            parts = target_version.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
        else:
            major, minor = target_version
        if (major, minor) <= (3, 8):
            return cls(
                use_future_annotations=True,
                use_pep604=False,
                use_required=True,
                use_typing_extensions=True,
            )
        if (major, minor) == (3, 9):
            return cls(
                use_future_annotations=True,
                use_pep604=False,
                use_required=True,
                use_typing_extensions=True,
            )
        if (major, minor) == (3, 10):
            return cls(
                use_future_annotations=True,
                use_pep604=True,
                use_required=True,
                use_typing_extensions=True,
            )
        return cls(
            use_future_annotations=True,
            use_pep604=True,
            use_required=True,
            use_typing_extensions=False,
        )
