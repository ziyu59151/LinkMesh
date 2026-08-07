#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

die() {
    printf 'build_release.sh: %s\n' "$*" >&2
    exit 1
}

require_value() {
    local option=$1
    local value=${2-}
    [[ -n "$value" && "$value" != --* ]] ||
        die "$option requires a non-empty value"
}

SCRIPT_DIR=$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOURCE_ROOT=$(cd -P "$SCRIPT_DIR/../.." && pwd)

OUTPUT_DIR=
VERSION=
PYTHON_EXECUTABLE=
HELPER_PATH=
SOURCE_COMMIT=
SOURCE_ARCHIVE=
SOURCE_ARCHIVE_SHA256=

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            require_value "$1" "${2-}"
            OUTPUT_DIR=$2
            shift 2
            ;;
        --version)
            require_value "$1" "${2-}"
            VERSION=$2
            shift 2
            ;;
        --python)
            require_value "$1" "${2-}"
            PYTHON_EXECUTABLE=$2
            shift 2
            ;;
        --helper)
            require_value "$1" "${2-}"
            HELPER_PATH=$2
            shift 2
            ;;
        --source-commit)
            require_value "$1" "${2-}"
            SOURCE_COMMIT=$2
            shift 2
            ;;
        --source-archive)
            require_value "$1" "${2-}"
            SOURCE_ARCHIVE=$2
            shift 2
            ;;
        --source-archive-sha256)
            require_value "$1" "${2-}"
            SOURCE_ARCHIVE_SHA256=$2
            shift 2
            ;;
        --help|-h)
            cat <<'USAGE'
Usage:
  build_release.sh \
    --output DIR \
    --version VERSION \
    --python PATH \
    --helper PATH \
    --source-commit HASH \
    --source-archive NAME \
    --source-archive-sha256 HASH
USAGE
            exit 0
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
done

for variable_name in \
    OUTPUT_DIR VERSION PYTHON_EXECUTABLE HELPER_PATH SOURCE_COMMIT \
    SOURCE_ARCHIVE SOURCE_ARCHIVE_SHA256
do
    [[ -n "${!variable_name}" ]] ||
        die "missing required option for $variable_name"
done

[[ "$VERSION" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
    die "VERSION must match [A-Za-z0-9][A-Za-z0-9._-]*"
[[ "$SOURCE_COMMIT" =~ ^[0-9A-Fa-f]{7,64}$ ]] ||
    die "SOURCE_COMMIT must be a 7-64 character hexadecimal hash"
[[ "$SOURCE_ARCHIVE" != */* && "$SOURCE_ARCHIVE" != *\\* ]] ||
    die "SOURCE_ARCHIVE must be a filename, not a path"
[[ "$SOURCE_ARCHIVE_SHA256" =~ ^[0-9A-Fa-f]{64}$ ]] ||
    die "SOURCE_ARCHIVE_SHA256 must be a 64 character hexadecimal digest"

for required_command in \
    awk cp date file find grep hostname install ldd mktemp readelf readlink \
    sha256sum sort tar uname xargs
do
    command -v "$required_command" >/dev/null 2>&1 ||
        die "required command is missing: $required_command"
done

[[ -x "$PYTHON_EXECUTABLE" ]] ||
    die "selected Python is missing or not executable: $PYTHON_EXECUTABLE"
PYTHON_EXECUTABLE=$(readlink -f "$PYTHON_EXECUTABLE")
[[ -n "$PYTHON_EXECUTABLE" ]] ||
    die "cannot resolve selected Python executable"

[[ -f "$HELPER_PATH" ]] ||
    die "helper is not a regular file: $HELPER_PATH"
[[ -x "$HELPER_PATH" ]] ||
    die "helper is not executable: $HELPER_PATH"
HELPER_PATH=$(readlink -f "$HELPER_PATH")
[[ -n "$HELPER_PATH" ]] || die "cannot resolve helper path"

HELPER_FILE_SUMMARY=$(file -b "$HELPER_PATH")
grep -Fq 'ELF 64-bit LSB' <<<"$HELPER_FILE_SUMMARY" ||
    die "helper is not a 64-bit little-endian ELF: $HELPER_FILE_SUMMARY"
grep -Eq 'x86-64|x86_64' <<<"$HELPER_FILE_SUMMARY" ||
    die "helper is not Linux x86-64: $HELPER_FILE_SUMMARY"

if ! HELPER_LDD_SUMMARY=$(ldd "$HELPER_PATH" 2>&1); then
    printf '%s\n' "$HELPER_LDD_SUMMARY" >&2
    die "ldd failed for helper"
fi
if grep -Fq 'not found' <<<"$HELPER_LDD_SUMMARY"; then
    printf '%s\n' "$HELPER_LDD_SUMMARY" >&2
    die "helper has unresolved dynamic libraries"
fi

if ! HELPER_READELF_OUTPUT=$(readelf -d "$HELPER_PATH" 2>&1); then
    printf '%s\n' "$HELPER_READELF_OUTPUT" >&2
    die "readelf -d failed for helper"
fi
HELPER_READELF_SUMMARY=$(
    grep -E '\((NEEDED|RPATH|RUNPATH)\)' \
        <<<"$HELPER_READELF_OUTPUT" || true
)
if [[ -z "$HELPER_READELF_SUMMARY" ]]; then
    HELPER_READELF_SUMMARY="No NEEDED, RPATH or RUNPATH entries reported."
fi

mapfile -t OFT_LOCATION < <(
    "$PYTHON_EXECUTABLE" - <<'PY'
from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

distribution = importlib.metadata.distribution("OpenFUSIONToolkit")
version = distribution.version
if version != "26.6":
    raise SystemExit(
        f"OpenFUSIONToolkit==26.6 required; found {version}"
    )

spec = importlib.util.find_spec("OpenFUSIONToolkit")
if spec is None or not spec.submodule_search_locations:
    raise SystemExit("cannot locate OpenFUSIONToolkit package")

package_paths = list(spec.submodule_search_locations)
if len(package_paths) != 1:
    raise SystemExit(
        "OpenFUSIONToolkit package location is ambiguous: "
        f"{package_paths!r}"
    )
package_path = Path(package_paths[0]).resolve()
if not package_path.is_dir():
    raise SystemExit(
        f"OpenFUSIONToolkit package is not a directory: {package_path}"
    )

dist_info_roots = []
for entry in distribution.files or ():
    if entry.parts and entry.parts[0].endswith(".dist-info"):
        candidate = Path(distribution.locate_file(entry.parts[0])).resolve()
        if candidate not in dist_info_roots:
            dist_info_roots.append(candidate)

if len(dist_info_roots) != 1 or not dist_info_roots[0].is_dir():
    raise SystemExit(
        "cannot uniquely locate OpenFUSIONToolkit dist-info: "
        f"{dist_info_roots!r}"
    )

print(package_path)
print(dist_info_roots[0])
print(version)
PY
) || die "failed to locate OpenFUSIONToolkit 26.6"

[[ ${#OFT_LOCATION[@]} -eq 3 ]] ||
    die "unexpected OpenFUSIONToolkit location probe output"
OFT_PACKAGE=${OFT_LOCATION[0]}
OFT_DIST_INFO=${OFT_LOCATION[1]}
OFT_VERSION=${OFT_LOCATION[2]}
[[ "$OFT_VERSION" == "26.6" ]] ||
    die "OpenFUSIONToolkit version mismatch: $OFT_VERSION"

[[ -d "$SOURCE_ROOT/src/linkmesh" ]] ||
    die "LinkMesh package is missing: $SOURCE_ROOT/src/linkmesh"
for template in \
    linkmesh-launcher linkmesh-bootstrap.py linkmesh-check README.md
do
    [[ -f "$SCRIPT_DIR/$template" ]] ||
        die "release template is missing: $SCRIPT_DIR/$template"
done

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(cd -P "$OUTPUT_DIR" && pwd)
RELEASE_NAME="linkmesh-release-${VERSION}-linux-x86_64"
FINAL_DIR="$OUTPUT_DIR/$RELEASE_NAME"
FINAL_ARCHIVE="$OUTPUT_DIR/$RELEASE_NAME.tar.gz"
[[ ! -e "$FINAL_DIR" ]] ||
    die "target release directory already exists: $FINAL_DIR"
[[ ! -e "$FINAL_ARCHIVE" ]] ||
    die "target release archive already exists: $FINAL_ARCHIVE"

WORK_PARENT=$(mktemp -d "$OUTPUT_DIR/.${RELEASE_NAME}.build.XXXXXX")
WORK_RELEASE="$WORK_PARENT/$RELEASE_NAME"
ARCHIVE_TEMP="$WORK_PARENT/$RELEASE_NAME.tar.gz"

cleanup() {
    rm -rf "$WORK_PARENT"
}
trap cleanup EXIT

mkdir -p \
    "$WORK_RELEASE/bin" \
    "$WORK_RELEASE/python/site-packages" \
    "$WORK_RELEASE/manifest"

cp -a "$SOURCE_ROOT/src/linkmesh" \
    "$WORK_RELEASE/python/site-packages/linkmesh"
cp -a "$OFT_PACKAGE" \
    "$WORK_RELEASE/python/site-packages/OpenFUSIONToolkit"
cp -a "$OFT_DIST_INFO" \
    "$WORK_RELEASE/python/site-packages/$(basename "$OFT_DIST_INFO")"

install -m 0755 "$SCRIPT_DIR/linkmesh-launcher" \
    "$WORK_RELEASE/bin/linkmesh"
install -m 0755 "$SCRIPT_DIR/linkmesh-bootstrap.py" \
    "$WORK_RELEASE/bin/linkmesh-bootstrap.py"
install -m 0755 "$SCRIPT_DIR/linkmesh-check" \
    "$WORK_RELEASE/bin/linkmesh-check"
install -m 0755 "$HELPER_PATH" \
    "$WORK_RELEASE/bin/linkmesh-scorec-helper"
install -m 0644 "$SCRIPT_DIR/README.md" \
    "$WORK_RELEASE/README.md"

find "$WORK_RELEASE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$WORK_RELEASE" -type f -name '*.pyc' -delete

for forbidden_path in \
    tests examples TOKAMAKER M3DC1 native packaging
do
    [[ ! -e "$WORK_RELEASE/$forbidden_path" ]] ||
        die "forbidden source content was copied: $forbidden_path"
done

for forbidden_package in \
    numpy h5py matplotlib scipy netCDF4 pytest mpi4py pumi
do
    [[ ! -e "$WORK_RELEASE/python/site-packages/$forbidden_package" ]] ||
        die "forbidden generic package was copied: $forbidden_package"
done

HELPER_SHA256=$(sha256sum \
    "$WORK_RELEASE/bin/linkmesh-scorec-helper" | awk '{print $1}')
PYTHON_VERSION=$("$PYTHON_EXECUTABLE" -c \
    'import platform; print(platform.python_version())')
PYTHON_IMPLEMENTATION=$("$PYTHON_EXECUTABLE" -c \
    'import platform; print(platform.python_implementation())')
BUILD_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
BUILD_HOST=$(hostname)
BUILD_PLATFORM=$(uname -srm)

cat >"$WORK_RELEASE/manifest/build-info.txt" <<EOF
release_name=$RELEASE_NAME
release_version=$VERSION
source_commit=$SOURCE_COMMIT
source_archive=$SOURCE_ARCHIVE
source_archive_sha256=${SOURCE_ARCHIVE_SHA256,,}
build_date_utc=$BUILD_DATE
build_host=$BUILD_HOST
build_platform=$BUILD_PLATFORM
python_implementation=$PYTHON_IMPLEMENTATION
python_version=$PYTHON_VERSION
openfusiontoolkit_version=$OFT_VERSION
helper_sha256=$HELPER_SHA256

[helper file]
$HELPER_FILE_SUMMARY

[helper ldd]
$HELPER_LDD_SUMMARY

[helper readelf -d]
$HELPER_READELF_SUMMARY
EOF

"$PYTHON_EXECUTABLE" - > \
    "$WORK_RELEASE/manifest/python-requirements.txt" <<'PY'
from __future__ import annotations

import importlib.metadata
import platform

print(
    "Build interpreter: "
    f"{platform.python_implementation()} {platform.python_version()}"
)
print("Currently validated environment: CPython 3.12.13")
print("Other Python 3 versions require external validation.")
print("No unverified minimum Python version is declared by this release.")
print("Bundled:")
print("  LinkMesh source package")
print(
    "  OpenFUSIONToolkit=="
    + importlib.metadata.version("OpenFUSIONToolkit")
)
print("Provided by the selected target Python environment:")
for distribution in (
    "numpy",
    "h5py",
    "matplotlib",
    "scipy",
    "netCDF4",
):
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        version = "NOT INSTALLED IN BUILD ENVIRONMENT"
    print(f"  {distribution}: {version}")
print("Not bundled: pytest")
PY

cat >"$WORK_RELEASE/manifest/native-requirements.txt" <<EOF
Architecture: Linux x86-64
Bundled:
  linkmesh-scorec-helper
  OpenFUSIONToolkit 26.6 native libraries within its Python package
  PUMI 2.2.9 components statically linked into the helper:
    mds, apf, gmi, pcu, mth, lion
Not bundled:
  MPI runtime (helper requires a compatible libmpi.so.40)
  glibc
  libstdc++
  standalone PUMI .a or .so files
Native compatibility boundary:
  The bundled helper is an independent process, not a Python extension.
  MPI, glibc, libstdc++ and operating-system ABI compatibility require
  validation on the target Linux server.
TRIMEG note:
  The TRIMEG HDF5 path does not invoke the SCOREC helper and must not be
  blocked by helper or MPI availability.
EOF

if grep -R -n -E \
    '/home/lxzeng|LinkMesh_server|LinkMesh_build' \
    "$WORK_RELEASE" \
    --exclude='linkmesh-scorec-helper'
then
    die "release text contains a forbidden maintainer or development path"
fi

(
    cd "$WORK_RELEASE"
    find . -type f ! -path './manifest/SHA256SUMS' -print0 |
        LC_ALL=C sort -z |
        xargs -0 sha256sum >manifest/SHA256SUMS
)

(
    cd "$WORK_PARENT"
    tar -czf "$ARCHIVE_TEMP" "$RELEASE_NAME"
)

mv "$WORK_RELEASE" "$FINAL_DIR"
mv "$ARCHIVE_TEMP" "$FINAL_ARCHIVE"

printf 'Release directory: %s\n' "$FINAL_DIR"
printf 'Release archive:   %s\n' "$FINAL_ARCHIVE"
printf 'GENERATED: completed by build_release.sh\n'
printf 'STRUCTURALLY CHECKED: PENDING\n'
printf 'EXTERNAL SERVER VALIDATION: PENDING\n'
printf 'TRIMEG REAL RUN: PENDING\n'
printf 'M3D-C1 REAL RUN: PENDING\n'
