from __future__ import annotations

from pathlib import Path

from clientify.generation.profile import GenerationProfile
from clientify.generator import PackageSpec, generate_package
from clientify.ir import IRDocument, OperationIR


class TestGeneratePackage:
    def test_generates_package_files(self, tmp_path: Path) -> None:
        spec = PackageSpec(package_name="sample_client", output_dir=tmp_path)
        ir = IRDocument(
            schemas=[],
            operations=[
                OperationIR(
                    method="get",
                    path="/health",
                    operation_id=None,
                    parameters=[],
                    request_body=None,
                    responses=[],
                    extensions={},
                )
            ],
        )
        package_dir = generate_package(spec, ir, GenerationProfile.from_version("3.14"))

        init_contents = (package_dir / "__init__.py").read_text(encoding="utf-8")
        assert "create" in init_contents
        assert (package_dir / "client.py").exists()
        assert (package_dir / "models.py").exists()
        assert (package_dir / "types.py").exists()
