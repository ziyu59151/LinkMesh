"""
tests/test_gfile_reader.py —— M1 GFile Reader 验收测试

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布 M1 验收通过。
"""

import ast
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 导入路径来自实际业务源码侦察
# ---------------------------------------------------------------------------
from linkmesh.readers.gfile_reader import GFileData, read_gfile


# ---------------------------------------------------------------------------
# 测试辅助：构造受控假 OFT 对象
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
    """构造受控假 GEQDSKEquilibrium 对象，属性名来自实际业务源码侦察。"""
    if boundary_R is None:
        # 逆时针单位正方形（5点，首尾重复）
        boundary_R = np.array([1.0, 2.0, 2.0, 1.0, 1.0])
        boundary_Z = np.array([0.0, 0.0, 1.0, 1.0, 0.0])
    obj = SimpleNamespace(
        boundary_R=np.asarray(boundary_R, dtype=np.float64),
        boundary_Z=np.asarray(boundary_Z, dtype=np.float64),
        R_mag=float(R_mag),
        Z_mag=float(Z_mag),
        limiter_R=np.asarray(limiter_R, dtype=np.float64) if limiter_R is not None else np.array([]),
        limiter_Z=np.asarray(limiter_Z, dtype=np.float64) if limiter_Z is not None else np.array([]),
        R_center=float(R_center),
        B_center=float(B_center),
        Ip=float(Ip),
    )
    return obj


def _signed_area(r, z):
    """鞋带公式计算有向面积（正值=逆时针）。
    对首尾重复的闭合点列，只取 [:-1] 避免重复末点。
    """
    if np.allclose(r[0], r[-1]) and np.allclose(z[0], z[-1]):
        r = r[:-1]
        z = z[:-1]
    n = len(r)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += r[i] * z[j]
        area -= r[j] * z[i]
    return area / 2.0


# ---------------------------------------------------------------------------
# M1-1：OFT Adapter 正常路径（含第一壁）
# ---------------------------------------------------------------------------

class TestReadGfileNormalPath:
    """M1 正常路径：mock OFT，验证 GFileData 字段契约。"""

    def _run(self, tmp_path, fake_eq):
        """公共执行逻辑：创建占位文件，patch OFT，调用 read_gfile。"""
        dummy = tmp_path / "dummy.eqdsk"
        dummy.write_text("")  # 占位文件，不写入 EQDSK 内容

        with patch(
            "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
            return_value=fake_eq,
        ):
            return read_gfile(str(dummy))

    def test_returns_gfiledata(self, tmp_path):
        """返回值类型为 GFileData。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert isinstance(result, GFileData)

    def test_lcfs_r_z_are_1d_numpy_arrays(self, tmp_path):
        """LCFS R/Z 是一维 NumPy 数组。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert isinstance(result.lcfs_r, np.ndarray)
        assert isinstance(result.lcfs_z, np.ndarray)
        assert result.lcfs_r.ndim == 1
        assert result.lcfs_z.ndim == 1

    def test_lcfs_r_z_same_length(self, tmp_path):
        """LCFS R/Z 长度一致。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert len(result.lcfs_r) == len(result.lcfs_z)

    def test_lcfs_closed(self, tmp_path):
        """LCFS 首尾坐标闭合（欧氏距离 < 总周长的 0.1%）。"""
        result = self._run(tmp_path, _make_fake_eq())
        r, z = result.lcfs_r, result.lcfs_z
        gap = math.hypot(r[0] - r[-1], z[0] - z[-1])
        perimeter = float(np.sum(np.sqrt(np.diff(r) ** 2 + np.diff(z) ** 2)))
        assert perimeter > 0
        assert gap <= 1e-3 * perimeter or gap < 1e-10, (
            f"LCFS 未闭合：gap={gap:.6g}, perimeter={perimeter:.6g}"
        )

    def test_lcfs_minimum_points(self, tmp_path):
        """LCFS 至少有 4 个点（构成有效闭合多边形所需最少点数）。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert len(result.lcfs_r) >= 4

    def test_lcfs_all_finite(self, tmp_path):
        """LCFS 坐标全部为有限数值。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert np.all(np.isfinite(result.lcfs_r))
        assert np.all(np.isfinite(result.lcfs_z))

    def test_lcfs_counterclockwise(self, tmp_path):
        """LCFS 方向为逆时针（有向面积 > 0）。"""
        result = self._run(tmp_path, _make_fake_eq())
        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"LCFS 方向不是逆时针，有向面积={area:.6g}"
        )

    def test_magnetic_axis_finite(self, tmp_path):
        """磁轴坐标是有限数值。"""
        result = self._run(tmp_path, _make_fake_eq())
        assert math.isfinite(result.rmaxis)
        assert math.isfinite(result.zmaxis)

    def test_magnetic_axis_values(self, tmp_path):
        """磁轴坐标与受控假对象一致。"""
        result = self._run(tmp_path, _make_fake_eq(R_mag=6.3624, Z_mag=0.5328))
        assert result.rmaxis == pytest.approx(6.3624)
        assert result.zmaxis == pytest.approx(0.5328)

    def test_wall_present_arrays(self, tmp_path):
        """第一壁存在时，wall_r/wall_z 均为一维数组且长度一致。"""
        wall_r = [4.0, 5.0, 5.0, 4.0, 4.0]
        wall_z = [-1.0, -1.0, 1.0, 1.0, -1.0]
        result = self._run(tmp_path, _make_fake_eq(limiter_R=wall_r, limiter_Z=wall_z))
        assert result.wall_r is not None
        assert result.wall_z is not None
        assert isinstance(result.wall_r, np.ndarray)
        assert isinstance(result.wall_z, np.ndarray)
        assert result.wall_r.ndim == 1
        assert result.wall_z.ndim == 1
        assert len(result.wall_r) == len(result.wall_z)

    def test_rcentr_bcentr_current_match_fake(self, tmp_path):
        """rcentr、bcentr、current 与受控假对象对应数据一致。"""
        result = self._run(
            tmp_path,
            _make_fake_eq(R_center=6.2, B_center=5.3, Ip=15_599_996.7),
        )
        assert result.rcentr == pytest.approx(6.2)
        assert result.bcentr == pytest.approx(5.3)
        assert result.current == pytest.approx(15_599_996.7)

    def test_current_unit_ampere_no_scaling(self, tmp_path):
        """current 保持安培值，Reader 不执行 1e6 或 1e-6 等单位缩放。"""
        ip_ampere = 15_599_996.7
        result = self._run(tmp_path, _make_fake_eq(Ip=ip_ampere))
        # 若 Reader 错误地除以 1e6，current 会变成约 15.6
        # 若 Reader 错误地乘以 1e6，current 会变成约 1.56e13
        assert result.current == pytest.approx(ip_ampere, rel=1e-6), (
            f"current 疑似被缩放：期望 {ip_ampere}，实际 {result.current}"
        )
        # 额外防线：确保量级在 MA 范围（1e6 ~ 1e8 A）
        assert 1e6 < abs(result.current) < 1e8, (
            f"current 量级异常，疑似单位错误：{result.current}"
        )


# ---------------------------------------------------------------------------
# M1-2：LCFS 顺时针输入修正
# ---------------------------------------------------------------------------

class TestLCFSClockwiseCorrection:
    """M1 LCFS 方向修正：Reader 应将顺时针输入规范为逆时针。"""

    def test_clockwise_input_becomes_ccw(self, tmp_path):
        """顺时针 LCFS 输入经 Reader 处理后变为逆时针。"""
        # 顺时针单位正方形（5点，首尾重复）
        cw_r = np.array([1.0, 1.0, 2.0, 2.0, 1.0])
        cw_z = np.array([0.0, 1.0, 1.0, 0.0, 0.0])
        # 验证输入确实是顺时针
        assert _signed_area(cw_r, cw_z) < 0, "测试前提：输入应为顺时针"

        dummy = tmp_path / "dummy.eqdsk"
        dummy.write_text("")
        fake_eq = _make_fake_eq(boundary_R=cw_r, boundary_Z=cw_z)

        with patch(
            "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
            return_value=fake_eq,
        ):
            result = read_gfile(str(dummy))

        # 输出应为逆时针
        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"Reader 未将顺时针 LCFS 修正为逆时针，有向面积={area:.6g}"
        )

        # 输出仍应闭合
        r, z = result.lcfs_r, result.lcfs_z
        gap = math.hypot(r[0] - r[-1], z[0] - z[-1])
        perimeter = float(np.sum(np.sqrt(np.diff(r) ** 2 + np.diff(z) ** 2)))
        assert gap <= 1e-3 * perimeter or gap < 1e-10

        # 点集数量不应无故增减（允许首尾规范化导致 ±1）
        n_in = len(cw_r)
        n_out = len(result.lcfs_r)
        assert abs(n_out - n_in) <= 1, (
            f"LCFS 点数异常变化：输入 {n_in}，输出 {n_out}"
        )


# ---------------------------------------------------------------------------
# M1-3：第一壁缺失
# ---------------------------------------------------------------------------

class TestWallMissing:
    """M1 第一壁缺失：OFT 返回空数组时，wall_r/wall_z 应为 None。"""

    def test_wall_missing_both_none(self, tmp_path):
        """第一壁缺失时，wall_r 和 wall_z 同时为 None。"""
        dummy = tmp_path / "dummy.eqdsk"
        dummy.write_text("")
        # limiter_R/Z 为空数组，模拟 GFile 不含第一壁
        fake_eq = _make_fake_eq(limiter_R=[], limiter_Z=[])

        with patch(
            "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
            return_value=fake_eq,
        ):
            result = read_gfile(str(dummy))

        assert result.wall_r is None, (
            f"第一壁缺失时 wall_r 应为 None，实际为 {type(result.wall_r)}"
        )
        assert result.wall_z is None, (
            f"第一壁缺失时 wall_z 应为 None，实际为 {type(result.wall_z)}"
        )

    def test_wall_missing_no_inconsistency(self, tmp_path):
        """wall_r 和 wall_z 不允许出现一个 None 一个数组的不一致状态。"""
        dummy = tmp_path / "dummy.eqdsk"
        dummy.write_text("")
        fake_eq = _make_fake_eq(limiter_R=[], limiter_Z=[])

        with patch(
            "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
            return_value=fake_eq,
        ):
            result = read_gfile(str(dummy))

        wall_r_is_none = result.wall_r is None
        wall_z_is_none = result.wall_z is None
        assert wall_r_is_none == wall_z_is_none, (
            "wall_r 和 wall_z 的 None 状态不一致"
        )


# ---------------------------------------------------------------------------
# M1-4：输入错误
# ---------------------------------------------------------------------------

class TestReadGfileErrors:
    """M1 输入错误：不存在路径应抛出契约规定的异常。"""

    def test_nonexistent_path_raises(self, tmp_path):
        """不存在的路径应抛出 FileNotFoundError 或 OSError。

        蓝图规定：FileNotFoundError（文件不存在或 OFT 共享库缺失）。
        实际 GEQDSKEquilibrium 在文件不存在时由 OFT 内部抛出。
        此处不 mock OFT，让真实 OFT 或 gfile_reader 的路径校验触发异常。
        """
        nonexistent = tmp_path / "does_not_exist.eqdsk"
        assert not nonexistent.exists()

        with pytest.raises((FileNotFoundError, OSError)):
            read_gfile(str(nonexistent))


# ---------------------------------------------------------------------------
# M1-5：禁止手动解析的 AST 静态防线
# ---------------------------------------------------------------------------

class TestNoManualParsingAST:
    """M1 静态防线：gfile_reader.py 不得直接调用手动文件解析入口。"""

    # 禁止的调用模式（函数名）
    _FORBIDDEN_CALLS = frozenset({
        "open",
        "loadtxt",
        "genfromtxt",
    })

    # 禁止的属性访问模式（obj.method 中的 method）
    _FORBIDDEN_ATTR_CALLS = frozenset({
        "read_text",
        "read_bytes",
    })

    def _get_reader_path(self) -> Path:
        """从当前测试文件位置推导仓库根目录，不依赖当前工作目录。"""
        # tests/test_gfile_reader.py → 仓库根 → src/linkmesh/readers/gfile_reader.py
        repo_root = Path(__file__).resolve().parent.parent
        return repo_root / "src" / "linkmesh" / "readers" / "gfile_reader.py"

    def test_no_direct_open_or_numpy_parse(self):
        """gfile_reader.py 不得直接调用 open/loadtxt/genfromtxt/read_text/read_bytes。"""
        reader_path = self._get_reader_path()
        assert reader_path.exists(), (
            f"找不到 gfile_reader.py：{reader_path}"
        )

        source = reader_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(reader_path))

        violations = []

        for node in ast.walk(tree):
            # 检查直接函数调用：open(...)、np.loadtxt(...)、np.genfromtxt(...)
            if isinstance(node, ast.Call):
                func = node.func
                # 裸函数名：open(...)
                if isinstance(func, ast.Name):
                    if func.id in self._FORBIDDEN_CALLS:
                        violations.append(
                            f"第 {node.lineno} 行：直接调用 {func.id}()"
                        )
                # 属性调用：xxx.read_text(...)、xxx.read_bytes(...)、
                #           np.loadtxt(...)、np.genfromtxt(...)
                elif isinstance(func, ast.Attribute):
                    if func.attr in self._FORBIDDEN_CALLS:
                        violations.append(
                            f"第 {node.lineno} 行：调用 .{func.attr}()"
                        )
                    if func.attr in self._FORBIDDEN_ATTR_CALLS:
                        violations.append(
                            f"第 {node.lineno} 行：调用 .{func.attr}()"
                        )

        assert not violations, (
            "gfile_reader.py 包含手动文件解析调用，违反薄 OFT Adapter 边界：\n"
            + "\n".join(violations)
        )
