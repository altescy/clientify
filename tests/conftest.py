from __future__ import annotations

import pytest


@pytest.fixture()
def minimal_openapi_document() -> dict[str, object]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Example", "version": "1.0.0"},
        "paths": {},
    }
