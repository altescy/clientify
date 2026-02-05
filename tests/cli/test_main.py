from __future__ import annotations

from pathlib import Path

import pytest

from clientify.__main__ import main


class TestCLI:
    def test_generates_package(self, tmp_path: Path) -> None:
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(
            '{"openapi": "3.0.3", "info": {"title": "t", "version": "1"}, "paths": {}}',
            encoding="utf-8",
        )
        output_dir = tmp_path / "out"
        result = main(
            [
                str(spec_path),
                "--package-name",
                "sample_client",
                "--output-dir",
                str(output_dir),
                "--python-version",
                "3.14",
            ]
        )
        assert result == 0
        package_dir = output_dir / "sample_client"
        assert (package_dir / "client.py").exists()
        assert (package_dir / "models.py").exists()
        assert (package_dir / "types.py").exists()

    @pytest.mark.parametrize(
        "spec_contents",
        [
            pytest.param("{}", id="missing-openapi"),
            pytest.param("[]", id="non-object"),
        ],
    )
    def test_invalid_spec_returns_error(self, tmp_path: Path, spec_contents: str) -> None:
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(spec_contents, encoding="utf-8")
        result = main(
            [
                str(spec_path),
                "--package-name",
                "sample_client",
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        assert result == 1
