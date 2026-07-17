"""
tests/test_gfile_reader.py —— M1 GFile Reader 自动测试

本文件定义 M1 Reader 自动测试，结果以实际 pytest 输出和正式验收记录为准，
本文件本身不声明 M1 已通过。
"""

import ast
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from linkmesh.readers.gfile_reader import GFileData, read_gfile


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------

def _make_fake_eq(
    boundary_R=None,
    boundary_Z=None,
    R_mag=6.3624,
    Z_mag=0.5328,
    limiter_R=None,
    limiter_Z=None,
    R_center=6.2,
    B_center=5.3,
    Ip=15_599_996.7,
):
    """构造受控假 GEQDSKEquilibrium 对象。"""
    if boundary_R is None:
        boundary_R = np.array([1.0, 2.0, 2.0, 1.0, 1.0])
        boundary_Z = np.array([0.0, 0.0, 1.0, 1.0, 0.0])

    return SimpleNamespace(
        boundary_R=np.asarray(boundary_R, dtype=np.float64),
        boundary_Z=np.asarray(boundary_Z, dtype=np.float64),
        R_mag=float(R_mag),
        Z_mag=float(Z_mag),
        limiter_R=(
            np.asarray(limiter_R, dtype=np.float64)
            if limiter_R is not None
            else np.array([], dtype=np.float64)
        ),
        limiter_Z=(
            np.asarray(limiter_Z, dtype=np.float64)
            if limiter_Z is not None
            else np.array([], dtype=np.float64)
        ),
        R_center=float(R_center),
        B_center=float(B_center),
        Ip=float(Ip),
    )


def _signed_area(r, z):
    """使用鞋带公式计算有向面积，正值表示逆时针。"""
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    if len(r) >= 2 and np.allclose(
        [r[0], z[0]],
        [r[-1], z[-1]],
        rtol=0.0,
        atol=1e-12,
    ):
        r = r[:-1]
        z = z[:-1]

    area = 0.0
    for index in range(len(r)):
        next_index = (index + 1) % len(r)
        area += r[index] * z[next_index]
        area -= r[next_index] * z[index]

    return area / 2.0


def _assert_closed(r, z):
    """断言首尾坐标在严格浮点容差内重合。"""
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    assert r.ndim == 1
    assert z.ndim == 1
    assert len(r) == len(z)
    assert len(r) >= 2

    np.testing.assert_allclose(
        r[0],
        r[-1],
        rtol=0.0,
        atol=1e-12,
        err_msg=f"LCFS 首尾 R 不重合：r[0]={r[0]}, r[-1]={r[-1]}",
    )
    np.testing.assert_allclose(
        z[0],
        z[-1],
        rtol=0.0,
        atol=1e-12,
        err_msg=f"LCFS 首尾 Z 不重合：z[0]={z[0]}, z[-1]={z[-1]}",
    )


def _sorted_open_vertices(r, z):
    """移除重复闭合末点，并按 (R, Z) 排序后返回几何顶点。"""
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    assert r.ndim == 1
    assert z.ndim == 1
    assert len(r) == len(z)

    if len(r) >= 2 and np.allclose(
        [r[0], z[0]],
        [r[-1], z[-1]],
        rtol=0.0,
        atol=1e-12,
    ):
        r = r[:-1]
        z = z[:-1]

    points = np.column_stack([r, z])
    order = np.lexsort((points[:, 1], points[:, 0]))
    return points[order]


def _run_with_fake(tmp_path, fake_eq):
    """创建占位文件，隔离 OFT，并调用 read_gfile。"""
    dummy = tmp_path / "dummy.eqdsk"
    dummy.write_text("", encoding="utf-8")

    with patch(
        "OpenFUSIONToolkit.TokaMaker.eqdsk.GEQDSKEquilibrium",
        return_value=fake_eq,
    ):
        return read_gfile(str(dummy))


# ---------------------------------------------------------------------------
# M1-1：OFT Adapter 正常路径
# ---------------------------------------------------------------------------

class TestReadGfileNormalPath:
    """使用受控 OFT 对象验证 GFileData 字段契约。"""

    def test_returns_gfiledata(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert isinstance(result, GFileData)

    def test_lcfs_r_z_are_1d_numpy_arrays(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert isinstance(result.lcfs_r, np.ndarray)
        assert isinstance(result.lcfs_z, np.ndarray)
        assert result.lcfs_r.ndim == 1
        assert result.lcfs_z.ndim == 1

    def test_lcfs_r_z_same_length(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert len(result.lcfs_r) == len(result.lcfs_z)

    def test_lcfs_strictly_closed(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        _assert_closed(result.lcfs_r, result.lcfs_z)

    def test_lcfs_minimum_points(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert len(result.lcfs_r) >= 4

    def test_lcfs_all_finite(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert np.all(np.isfinite(result.lcfs_r))
        assert np.all(np.isfinite(result.lcfs_z))

    def test_lcfs_counterclockwise(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())
        area = _signed_area(result.lcfs_r, result.lcfs_z)

        assert area > 0, (
            f"LCFS 方向不是逆时针，有向面积={area:.6g}"
        )

    def test_magnetic_axis_finite(self, tmp_path):
        result = _run_with_fake(tmp_path, _make_fake_eq())

        assert math.isfinite(result.rmaxis)
        assert math.isfinite(result.zmaxis)

    def test_magnetic_axis_values(self, tmp_path):
        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(R_mag=6.3624, Z_mag=0.5328),
        )

        assert result.rmaxis == pytest.approx(6.3624)
        assert result.zmaxis == pytest.approx(0.5328)

    def test_wall_present_arrays(self, tmp_path):
        wall_r = [4.0, 5.0, 5.0, 4.0, 4.0]
        wall_z = [-1.0, -1.0, 1.0, 1.0, -1.0]

        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(limiter_R=wall_r, limiter_Z=wall_z),
        )

        assert result.wall_r is not None
        assert result.wall_z is not None
        assert isinstance(result.wall_r, np.ndarray)
        assert isinstance(result.wall_z, np.ndarray)
        assert result.wall_r.ndim == 1
        assert result.wall_z.ndim == 1
        assert len(result.wall_r) == len(result.wall_z)

    def test_wall_coordinates_match_limiter_no_swap_no_scale(self, tmp_path):
        wall_r = [4.0, 5.0, 5.0, 4.0, 4.0]
        wall_z = [-1.0, -1.0, 1.0, 1.0, -1.0]

        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(limiter_R=wall_r, limiter_Z=wall_z),
        )

        np.testing.assert_allclose(
            result.wall_r,
            np.asarray(wall_r, dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
            err_msg=(
                "wall_r 与 limiter_R 不一致，"
                "疑似 R/Z 交换或坐标缩放"
            ),
        )
        np.testing.assert_allclose(
            result.wall_z,
            np.asarray(wall_z, dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
            err_msg=(
                "wall_z 与 limiter_Z 不一致，"
                "疑似 R/Z 交换或坐标缩放"
            ),
        )

    def test_rcentr_bcentr_current_match_fake(self, tmp_path):
        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(
                R_center=6.2,
                B_center=5.3,
                Ip=15_599_996.7,
            ),
        )

        assert result.rcentr == pytest.approx(6.2)
        assert result.bcentr == pytest.approx(5.3)
        assert result.current == pytest.approx(15_599_996.7)

    def test_current_unit_ampere_no_scaling(self, tmp_path):
        ip_ampere = 15_599_996.7
        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(Ip=ip_ampere),
        )

        assert result.current == pytest.approx(ip_ampere, rel=1e-6), (
            f"current 疑似被缩放："
            f"期望 {ip_ampere}，实际 {result.current}"
        )


# ---------------------------------------------------------------------------
# M1-2：LCFS 闭合规范化
# ---------------------------------------------------------------------------

class TestLCFSClosure:
    """验证 Reader 输出的 LCFS 首尾闭合。"""

    def test_already_closed_input_stays_closed(self, tmp_path):
        r_in = np.array(
            [1.0, 2.0, 2.0, 1.0, 1.0],
            dtype=np.float64,
        )
        z_in = np.array(
            [0.0, 0.0, 1.0, 1.0, 0.0],
            dtype=np.float64,
        )

        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(boundary_R=r_in, boundary_Z=z_in),
        )

        _assert_closed(result.lcfs_r, result.lcfs_z)

    def test_unclosed_input_becomes_closed_with_same_geometry(
        self,
        tmp_path,
    ):
        """未闭合输入应变为闭合、逆时针且几何点集不变。"""
        r_in = np.array(
            [1.0, 2.0, 2.0, 1.0],
            dtype=np.float64,
        )
        z_in = np.array(
            [0.0, 0.0, 1.0, 1.0],
            dtype=np.float64,
        )

        assert not np.allclose(
            [r_in[0], z_in[0]],
            [r_in[-1], z_in[-1]],
            rtol=0.0,
            atol=1e-12,
        ), "测试前提：输入应首尾不重复"
        assert _signed_area(r_in, z_in) > 0, (
            "测试前提：输入应为逆时针"
        )

        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(boundary_R=r_in, boundary_Z=z_in),
        )

        _assert_closed(result.lcfs_r, result.lcfs_z)

        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"闭合规范化后的 LCFS 不是逆时针，"
            f"有向面积={area:.6g}"
        )

        points_in = _sorted_open_vertices(r_in, z_in)
        points_out = _sorted_open_vertices(
            result.lcfs_r,
            result.lcfs_z,
        )

        assert points_out.shape == points_in.shape, (
            "闭合规范化改变了几何顶点数量："
            f"输入 {points_in.shape[0]}，"
            f"输出 {points_out.shape[0]}"
        )
        np.testing.assert_allclose(
            points_out,
            points_in,
            rtol=0.0,
            atol=1e-12,
            err_msg="闭合规范化改变了 LCFS 几何点集",
        )


# ---------------------------------------------------------------------------
# M1-3：LCFS 顺时针输入修正
# ---------------------------------------------------------------------------

class TestLCFSClockwiseCorrection:
    """验证 Reader 将顺时针 LCFS 规范为逆时针。"""

    def test_clockwise_input_becomes_ccw_with_same_geometry(
        self,
        tmp_path,
    ):
        cw_r = np.array(
            [1.0, 1.0, 2.0, 2.0, 1.0],
            dtype=np.float64,
        )
        cw_z = np.array(
            [0.0, 1.0, 1.0, 0.0, 0.0],
            dtype=np.float64,
        )

        assert _signed_area(cw_r, cw_z) < 0, (
            "测试前提：输入应为顺时针"
        )

        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(boundary_R=cw_r, boundary_Z=cw_z),
        )

        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"Reader 未将顺时针 LCFS 修正为逆时针，"
            f"有向面积={area:.6g}"
        )

        _assert_closed(result.lcfs_r, result.lcfs_z)

        points_in = _sorted_open_vertices(cw_r, cw_z)
        points_out = _sorted_open_vertices(
            result.lcfs_r,
            result.lcfs_z,
        )

        assert points_out.shape == points_in.shape, (
            "方向修正改变了几何顶点数量："
            f"输入 {points_in.shape[0]}，"
            f"输出 {points_out.shape[0]}"
        )
        np.testing.assert_allclose(
            points_out,
            points_in,
            rtol=0.0,
            atol=1e-12,
            err_msg=(
                "方向修正改变了 LCFS 几何点集，"
                "坐标可能被新增、丢失或替换"
            ),
        )


# ---------------------------------------------------------------------------
# M1-4：第一壁缺失
# ---------------------------------------------------------------------------

class TestWallMissing:
    """验证 OFT 返回双空数组时第一壁表示为缺失。"""

    def test_wall_missing_both_none(self, tmp_path):
        fake_eq = _make_fake_eq(limiter_R=[], limiter_Z=[])
        result = _run_with_fake(tmp_path, fake_eq)

        assert result.wall_r is None, (
            "第一壁缺失时 wall_r 应为 None，"
            f"实际为 {type(result.wall_r)}"
        )
        assert result.wall_z is None, (
            "第一壁缺失时 wall_z 应为 None，"
            f"实际为 {type(result.wall_z)}"
        )


# ---------------------------------------------------------------------------
# M1-5：路径错误
# ---------------------------------------------------------------------------

class TestReadGfileErrors:
    """验证 OFT 的 FileNotFoundError 由 Reader 传播。"""

    def test_oft_file_not_found_error_propagates(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist.eqdsk"

        assert not nonexistent.exists()

        mock_equilibrium = MagicMock(
            side_effect=FileNotFoundError("OFT: file not found")
        )

        with patch(
            "OpenFUSIONToolkit.TokaMaker.eqdsk.GEQDSKEquilibrium",
            mock_equilibrium,
        ):
            with pytest.raises(FileNotFoundError):
                read_gfile(str(nonexistent))

        mock_equilibrium.assert_called_once_with(str(nonexistent))


# ---------------------------------------------------------------------------
# M1-6：禁止手动解析的 AST 静态防线
# ---------------------------------------------------------------------------

class TestNoManualParsingAST:
    """验证 Reader 保持为薄 OFT Adapter。"""

    _FORBIDDEN_BARE_CALLS = frozenset({
        "open",
        "loadtxt",
        "genfromtxt",
    })

    _FORBIDDEN_ATTRIBUTE_CALLS = frozenset({
        "read_text",
        "read_bytes",
        "loadtxt",
        "genfromtxt",
    })

    def _get_reader_path(self):
        """从测试文件位置推导 Reader 源文件路径。"""
        repository_root = Path(__file__).resolve().parent.parent
        return (
            repository_root
            / "src"
            / "linkmesh"
            / "readers"
            / "gfile_reader.py"
        )

    def test_no_direct_open_or_numpy_parse(self):
        reader_path = self._get_reader_path()

        assert reader_path.exists(), (
            f"找不到 gfile_reader.py：{reader_path}"
        )

        source = reader_path.read_text(encoding="utf-8")
        syntax_tree = ast.parse(source, filename=str(reader_path))
        violations = []

        for node in ast.walk(syntax_tree):
            if not isinstance(node, ast.Call):
                continue

            function = node.func

            if (
                isinstance(function, ast.Name)
                and function.id in self._FORBIDDEN_BARE_CALLS
            ):
                violations.append(
                    f"第 {node.lineno} 行："
                    f"直接调用 {function.id}()"
                )

            if (
                isinstance(function, ast.Attribute)
                and function.attr in self._FORBIDDEN_ATTRIBUTE_CALLS
            ):
                violations.append(
                    f"第 {node.lineno} 行："
                    f"调用 .{function.attr}()"
                )

        assert not violations, (
            "gfile_reader.py 包含手动文件解析调用，"
            "违反薄 OFT Adapter 边界：\n"
            + "\n".join(violations)
        )