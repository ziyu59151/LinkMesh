"""Static and structural contracts for the portable Release infrastructure."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "packaging" / "release"


def _read(name: str) -> str:
    return (RELEASE_DIR / name).read_text(encoding="utf-8")


def _case_branch(script: str, mode: str) -> str:
    match = re.search(
        rf"\n        {re.escape(mode)}\)\n(?P<body>.*?)\n            ;;",
        script,
        flags=re.DOTALL,
    )
    assert match is not None, f"missing {mode!r} check mode"
    return match.group("body")


def test_user_readme_matches_single_region_resolution_contract() -> None:
    readme = _read("README.md")

    assert "[mesh]\nmesh_dx =" in readme
    assert "[mesh]\nplasma_dx =" not in readme
    assert "--mesh-dx " in readme


def test_user_readme_describes_external_and_internal_layouts() -> None:
    readme = _read("README.md")

    assert "README.md" in readme
    assert "linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz" in readme
    assert (
        "linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz.sha256"
        in readme
    )

    extracted_layout = re.search(
        r"解压后得到：\s*```text(?P<layout>.*?)```",
        readme,
        flags=re.DOTALL,
    )
    assert extracted_layout is not None
    layout = extracted_layout.group("layout")
    assert "├── bin/" in layout
    assert "├── manifest/" in layout
    assert "└── python/" in layout
    assert "README.md" not in layout


def test_builder_defines_exact_external_delivery_contract() -> None:
    script = _read("build_release.sh")

    assert 'DELIVERY_NAME="LinkMesh-${VERSION}-linux-x86_64-release"' in script
    assert 'ARCHIVE_NAME="$RELEASE_NAME.tar.gz"' in script
    assert 'CHECKSUM_NAME="$ARCHIVE_NAME.sha256"' in script
    assert (
        'install -m 0644 "$SCRIPT_DIR/README.md" \\\n'
        '    "$WORK_DELIVERY/README.md"'
    ) in script
    assert '"$WORK_RELEASE/README.md"' not in script
    assert "delivery directory must contain only README, archive and checksum" in script
    assert 'mv "$WORK_DELIVERY" "$FINAL_DELIVERY"' in script


def test_builder_rejects_existing_delivery_and_uses_temporary_workspace() -> None:
    script = _read("build_release.sh")

    reject_index = script.index('[[ ! -e "$FINAL_DELIVERY" ]]')
    temporary_index = script.index("WORK_PARENT=$(mktemp")
    publish_index = script.index('mv "$WORK_DELIVERY" "$FINAL_DELIVERY"')

    assert reject_index < temporary_index < publish_index
    assert "target delivery directory already exists" in script
    assert "trap cleanup EXIT" in script


def test_builder_separates_internal_manifest_from_archive_checksum() -> None:
    script = _read("build_release.sh")

    cache_cleanup_index = script.index(
        'find "$WORK_RELEASE" -type f -name \'*.pyc\' -delete'
    )
    manifest_index = script.index("xargs -0 sha256sum >manifest/SHA256SUMS")
    archive_index = script.index(
        'tar -czf "$WORK_DELIVERY/$ARCHIVE_NAME" "$RELEASE_NAME"'
    )
    checksum_index = script.index(
        'sha256sum "$ARCHIVE_NAME" >"$CHECKSUM_NAME"'
    )

    assert cache_cleanup_index < manifest_index < archive_index < checksum_index
    assert "! -path './manifest/SHA256SUMS'" in script
    assert "internal release root must contain only bin, manifest and python" in script
    assert "README.md" in script.split("for forbidden_path in", 1)[1]


def test_builder_records_reproducibility_and_native_audit() -> None:
    script = _read("build_release.sh")

    for required_text in (
        "source_commit=$SOURCE_COMMIT",
        "source_archive_sha256=${SOURCE_ARCHIVE_SHA256,,}",
        "helper_sha256=$HELPER_SHA256",
        "OpenFUSIONToolkit==26.6 required",
        "ldd",
        "readelf -d",
        "ELF 64-bit LSB",
        "manifest/python-requirements.txt",
        "manifest/native-requirements.txt",
    ):
        assert required_text in script


def test_launcher_uses_portable_python_and_helper_lookup() -> None:
    launcher = _read("linkmesh-launcher")

    explicit = launcher.index('if [[ -n "${LINKMESH_PYTHON:-}" ]]')
    python3 = launcher.index("command -v python3")
    python = launcher.index("command -v python 2>/dev/null")
    assert explicit < python3 < python

    assert 'HELPER="$BIN_DIR/linkmesh-scorec-helper"' in launcher
    assert 'export LINKMESH_SCOREC_HELPER="$HELPER"' in launcher
    assert 'exec "$PYTHON_EXECUTABLE" "$BOOTSTRAP" "$@"' in launcher


def test_bootstrap_prioritizes_bundled_site_packages() -> None:
    bootstrap = _read("linkmesh-bootstrap.py")

    assert 'bin_directory.parent / "python" / "site-packages"' in bootstrap
    assert "sys.path[:] = [" in bootstrap
    assert "site_packages_text," in bootstrap
    assert 'runpy.run_module("linkmesh.__main__"' in bootstrap


@pytest.mark.parametrize("mode", ("core", "trimeg", "plot", "m3dc1"))
def test_check_script_defines_each_task_mode(mode: str) -> None:
    checker = _read("linkmesh-check")
    assert _case_branch(checker, mode)


def test_check_script_keeps_python_only_modes_independent_of_native_helper() -> None:
    checker = _read("linkmesh-check")

    trimeg = _case_branch(checker, "trimeg")
    plot = _case_branch(checker, "plot")
    m3dc1 = _case_branch(checker, "m3dc1")

    assert "check_m3dc1_native" not in trimeg
    assert "check_m3dc1_native" not in plot
    assert "check_m3dc1_native" in m3dc1
    assert "for mode in core trimeg plot m3dc1" in checker
    assert "SMB writing and M3D-C1 loading were not executed" in checker


def test_release_runtime_scripts_do_not_depend_on_development_paths() -> None:
    scripts = "\n".join(
        _read(name)
        for name in (
            "build_release.sh",
            "linkmesh-launcher",
            "linkmesh-bootstrap.py",
            "linkmesh-check",
        )
    )

    for forbidden_text in (
        "/home/lxzeng",
        "LinkMesh_server",
        "LinkMesh_build",
        "LinkMesh_runs",
        "PYTHONPATH",
    ):
        assert forbidden_text not in scripts
