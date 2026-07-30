"""Strict reader for counted R-Z boundary text files."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from linkmesh.mesh import (
    _signed_area_closed,
    _validate_outer_boundary as _mesh_validate_outer_boundary,
)


_COUNT_PATTERN = re.compile(r"[0-9]+")


class BoundaryFormatError(ValueError):
    """Raised when a boundary file violates the counted R-Z text syntax."""


def _format_error(path: Path, line_number: int, reason: str) -> BoundaryFormatError:
    return BoundaryFormatError(f"[边界文件 {path}] 第 {line_number} 行：{reason}")


def _normalize_clockwise(boundary: np.ndarray) -> np.ndarray:
    """Return a clockwise copy while preserving the original starting point."""
    normalized = np.array(boundary, dtype=np.float64, copy=True)
    if _signed_area_closed(normalized) > 0.0:
        normalized = np.concatenate(
            (normalized[:1], normalized[:0:-1]),
            axis=0,
        )
    return normalized


def read_boundary_file(filepath: str | Path) -> np.ndarray:
    """Read a strict counted R-Z boundary text file.

    The accepted format is one decimal point count followed by exactly that
    many non-empty lines, each containing exactly two whitespace-separated
    finite floating-point values in R, Z order and SI metres.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"边界文件不存在：{path}")
    if not path.is_file():
        raise IsADirectoryError(f"边界路径不是普通文件：{path}")

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise BoundaryFormatError(
            f"[边界文件 {path}] 无法按 UTF-8 文本解码：{exc}"
        ) from exc

    lines = text.splitlines()
    if not lines:
        raise _format_error(path, 1, "缺少计数头 N")

    count_token = lines[0]
    if _COUNT_PATTERN.fullmatch(count_token) is None:
        raise _format_error(
            path,
            1,
            "计数头必须只包含一个十进制整数 N",
        )

    count = int(count_token, 10)
    if count < 3:
        raise _format_error(path, 1, f"N 必须不小于 3，实际 N={count}")

    actual_data_lines = len(lines) - 1
    if actual_data_lines != count:
        raise BoundaryFormatError(
            f"[边界文件 {path}] 计数头声明 N={count}，"
            f"但实际数据行数={actual_data_lines}；必须恰好包含 N 行"
        )

    boundary = np.empty((count, 2), dtype=np.float64)
    for index, line in enumerate(lines[1:], start=2):
        if not line.strip():
            raise _format_error(path, index, "不允许空数据行")

        fields = line.split()
        if len(fields) != 2:
            raise _format_error(
                path,
                index,
                f"坐标行必须恰好包含两个空白分隔字段，实际字段数={len(fields)}",
            )

        try:
            r_value = float(fields[0])
            z_value = float(fields[1])
        except ValueError as exc:
            raise _format_error(
                path,
                index,
                "R、Z 必须是合法浮点数",
            ) from exc

        if not (np.isfinite(r_value) and np.isfinite(z_value)):
            raise _format_error(path, index, "R、Z 必须是有限浮点数，禁止 NaN/Inf")

        boundary[index - 2] = (r_value, z_value)

    normalized = _normalize_clockwise(boundary)
    try:
        validated = _mesh_validate_outer_boundary(normalized)
    except ValueError as exc:
        raise ValueError(f"[边界文件 {path}] 边界几何非法：{exc}") from exc

    return np.array(validated, dtype=np.float64, copy=True)
