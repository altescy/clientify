from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ClientifyError
from .generation import GenerationProfile
from .generator import PackageSpec, generate_package
from .ir import build_ir
from .loader import load_openapi


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clientify", description="Generate Python client from OpenAPI spec.")
    parser.add_argument("spec", type=Path, help="Path to OpenAPI spec (JSON/YAML)")
    parser.add_argument("-n", "--package-name", required=True, help="Generated package name")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."), help="Output directory")
    parser.add_argument("--python-version", default="3.10", help="Target Python version (e.g. 3.10)")

    args = parser.parse_args(argv)

    try:
        document = load_openapi(args.spec)
        ir = build_ir(document)
        profile = GenerationProfile.from_version(args.python_version)
        package = PackageSpec(package_name=args.package_name, output_dir=args.output_dir)
        generate_package(package, ir, profile)
    except ClientifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
