#!/usr/bin/env python3
"""Start LinkMesh with the bundled release packages taking precedence."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    bin_directory = Path(__file__).resolve().parent
    site_packages = (
        bin_directory.parent / "python" / "site-packages"
    ).resolve()

    if not site_packages.is_dir():
        raise SystemExit(
            f"LinkMesh release site-packages is missing: {site_packages}"
        )

    site_packages_text = str(site_packages)
    sys.path[:] = [
        site_packages_text,
        *(entry for entry in sys.path if entry != site_packages_text),
    ]

    runpy.run_module("linkmesh.__main__", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
