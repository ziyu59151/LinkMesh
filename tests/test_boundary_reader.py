from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from linkmesh.readers.boundary_reader import (
    BoundaryFormatError,
    read_boundary_file,
)


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _clockwise_square_lines() -> list[str]:
    return ["4", "0 0", "0 1", "1 1", "1 0"]


def _signed_area(points: np.ndarray) -> float:
    next_points = np.roll(points, -1, axis=0)
    return 0.5 * float(
        np.sum(
            points[:, 0] * next_points[:, 1]
            - next_points[:, 0] * points[:, 1]
        )
    )


def test_reads_extensionless_east_format_representative(tmp_path):
    angles = np.linspace(0.0, 2.0 * np.pi, 104, endpoint=False)
    points = np.column_stack(
        [1.85 + 0.4 * np.cos(angles), 0.6 * np.sin(angles)]
    )
    path = _write(
        tmp_path / "EAST",
        ["104", *(f"{r:.16g} {z:.16g}" for r, z in points)],
    )

    boundary = read_boundary_file(path)

    assert boundary.shape == (104, 2)
    assert boundary.dtype == np.float64
    assert boundary[0, 0] == pytest.approx(points[0, 0])
    assert boundary[0, 1] == pytest.approx(points[0, 1])
    assert _signed_area(boundary) < 0.0


def test_counterclockwise_input_reversed_without_changing_start(tmp_path):
    path = _write(
        tmp_path / "boundary",
        ["4", "0 0", "1 0", "1 1", "0 1"],
    )
    boundary = read_boundary_file(path)

    np.testing.assert_array_equal(boundary[0], [0.0, 0.0])
    np.testing.assert_array_equal(
        boundary,
        [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
    )
    assert _signed_area(boundary) < 0.0


def test_clockwise_input_order_preserved_and_result_owned(tmp_path):
    path = _write(tmp_path / "boundary", _clockwise_square_lines())
    first = read_boundary_file(path)
    snapshot = first.copy()
    second = read_boundary_file(path)

    np.testing.assert_array_equal(first, snapshot)
    np.testing.assert_array_equal(second, snapshot)
    assert not np.shares_memory(first, second)
    assert _signed_area(first) < 0.0


def test_missing_file_fails(tmp_path):
    with pytest.raises(FileNotFoundError, match="不存在"):
        read_boundary_file(tmp_path / "missing")


def test_non_regular_file_fails(tmp_path):
    directory = tmp_path / "boundary"
    directory.mkdir()
    with pytest.raises(IsADirectoryError, match="普通文件"):
        read_boundary_file(directory)


@pytest.mark.parametrize(
    "lines",
    [
        [],
        ["header", "0 0", "0 1", "1 0"],
        ["3.0", "0 0", "0 1", "1 0"],
        ["2", "0 0", "1 0"],
        ["+3", "0 0", "0 1", "1 0"],
    ],
)
def test_invalid_count_header_rejected(tmp_path, lines):
    path = _write(tmp_path / "boundary", lines)
    with pytest.raises(BoundaryFormatError, match="计数头|N 必须"):
        read_boundary_file(path)


@pytest.mark.parametrize(
    "lines",
    [
        ["4", "0 0", "0 1", "1 1"],
        ["3", "0 0", "0 1", "1 0", "2 2"],
        ["3", "0 0", "", "1 0"],
        ["3", "0 0", "0 1", "1 0", ""],
    ],
)
def test_data_line_count_must_match_header(tmp_path, lines):
    path = _write(tmp_path / "boundary", lines)
    with pytest.raises(BoundaryFormatError, match="数据行数|空数据行"):
        read_boundary_file(path)


@pytest.mark.parametrize(
    "bad_line",
    [
        "0,0",
        "R Z",
        "# comment",
        "0",
        "0 1 2",
        "index 0 1",
        "nan 0",
        "0 inf",
    ],
)
def test_invalid_coordinate_line_rejected(tmp_path, bad_line):
    path = _write(
        tmp_path / "boundary",
        ["3", "0 0", bad_line, "1 0"],
    )
    with pytest.raises(BoundaryFormatError):
        read_boundary_file(path)


@pytest.mark.parametrize(
    "lines,reason",
    [
        (
            ["5", "0 0", "0 1", "1 1", "1 0", "0 0"],
            "首点与末点",
        ),
        (
            ["5", "0 0", "0 1", "0 1", "1 1", "1 0"],
            "相邻重复",
        ),
        (
            ["4", "0 0", "0 1", "1 0", "0 1"],
            "互异点|自交",
        ),
        (
            ["3", "0 0", "1 0", "2 0"],
            "面积",
        ),
        (
            ["4", "0 0", "2 3", "0 2", "3 0"],
            "自交",
        ),
    ],
)
def test_invalid_geometry_rejected_with_path(tmp_path, lines, reason):
    path = _write(tmp_path / "boundary", lines)
    with pytest.raises(ValueError, match=reason) as exc_info:
        read_boundary_file(path)
    assert str(path) in str(exc_info.value)
