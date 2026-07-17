"""
tests/test_gfile_reader.py —— M1 GFile Reader 自动测试

本文件定义 M1 Reader 自动测试，结果以实际 pytest 输出和正式验收记录为准，
本文件本身不声明 M1 已通过。
"""

import ast
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

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
    """构造受控假 GEQDSKEquilibrium 对象，属性名来自 eqdsk.py 只读侦察。"""
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
    """Shoelace 公式计算有向面积（正值=逆时针）。
    对首尾重复的闭合点列，去掉重复末点后计算。
    """
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    if len(r) >= 2 and np.allclose(r[0], r[-1]) and np.allclose(z[0], z[-1]):
        r = r[:-1]
        z = z[:-1]
    n = len(r)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += r[i] * z[j]
        area -= r[j] * z[i]
    return area / 2.0


def _assert_closed(r, z):
    """断言首尾点严格重合（浮点精度）。"""
    np.testing.assert_allclose(
        r[0], r[-1], rtol=0.0, atol=1e-12,
        err_msg=f"LCFS 首尾 R 不重合：r[0]={r[0]}, r[-1]={r[-1]}"
    )
    np.testing.assert_allclose(
        z[0], z[-1], rtol=0.0, atol=1e-12,
        err_msg=f"LCFS 首尾 Z 不重合：z[0]={z[0]}, z[-1]={z[-1]}"
    )


def _run_with_fake(tmp_path, fake_eq):
    """公共执行逻辑：创建占位文件，patch OFT，调用 read_gfile。"""
    dummy = tmp_path / "dummy.eqdsk"
    dummy.write_text("")
    with patch(
        "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
        return_value=fake_eq,
    ):
        return read_gfile(str(dummy))


# ---------------------------------------------------------------------------
# M1-1：OFT Adapter 正常路径（含第一壁）
# ---------------------------------------------------------------------------

class TestReadGfileNormalPath:
    """M1 正常路径：mock OFT，验证 GFileData 字段契约。"""

    def test_returns_gfiledata(self, tmp_path):
        """返回值类型为 GFileData。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert isinstance(result, GFileData)

    def test_lcfs_r_z_are_1d_numpy_arrays(self, tmp_path):
        """LCFS R/Z 是一维 NumPy 数组。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert isinstance(result.lcfs_r, np.ndarray)
        assert isinstance(result.lcfs_z, np.ndarray)
        assert result.lcfs_r.ndim == 1
        assert result.lcfs_z.ndim == 1

    def test_lcfs_r_z_same_length(self, tmp_path):
        """LCFS R/Z 长度一致。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert len(result.lcfs_r) == len(result.lcfs_z)

    def test_lcfs_strictly_closed(self, tmp_path):
        """LCFS 首尾点严格重合（浮点精度）。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        _assert_closed(result.lcfs_r, result.lcfs_z)

    def test_lcfs_minimum_points(self, tmp_path):
        """LCFS 至少有 4 个点（构成有效闭合多边形所需最少点数）。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert len(result.lcfs_r) >= 4

    def test_lcfs_all_finite(self, tmp_path):
        """LCFS 坐标全部为有限数值。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert np.all(np.isfinite(result.lcfs_r))
        assert np.all(np.isfinite(result.lcfs_z))

    def test_lcfs_counterclockwise(self, tmp_path):
        """LCFS 方向为逆时针（有向面积 > 0）。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"LCFS 方向不是逆时针，有向面积={area:.6g}"
        )

    def test_magnetic_axis_finite(self, tmp_path):
        """磁轴坐标是有限数值。"""
        result = _run_with_fake(tmp_path, _make_fake_eq())
        assert math.isfinite(result.rmaxis)
        assert math.isfinite(result.zmaxis)

    def test_magnetic_axis_values(self, tmp_path):
        """磁轴坐标与受控假对象一致。"""
        result = _run_with_fake(tmp_path, _make_fake_eq(R_mag=6.3624, Z_mag=0.5328))
        assert result.rmaxis == pytest.approx(6.3624)
        assert result.zmaxis == pytest.approx(0.5328)

    def test_wall_present_arrays(self, tmp_path):
        """第一壁存在时，wall_r/wall_z 均为一维数组且长度一致。"""
        wall_r = [4.0, 5.0, 5.0, 4.0, 4.0]
        wall_z = [-1.0, -1.0, 1.0, 1.0, -1.0]
        result = _run_with_fake(tmp_path, _make_fake_eq(limiter_R=wall_r, limiter_Z=wall_z))
        assert result.wall_r is not None
        assert result.wall_z is not None
        assert isinstance(result.wall_r, np.ndarray)
        assert isinstance(result.wall_z, np.ndarray)
        assert result.wall_r.ndim == 1
        assert result.wall_z.ndim == 1
        assert len(result.wall_r) == len(result.wall_z)

    def test_wall_coordinates_match_limiter_no_swap_no_scale(self, tmp_path):
        """wall_r/wall_z 与 limiter_R/limiter_Z 数值完全对应，R/Z 未交换，坐标未缩放。

        蓝图未规定第一壁需要闭合/方向规范化，源码对第一壁无后处理，
        因此输出应与输入数值完全一致。
        """
        wall_r = [4.0, 5.0, 5.0, 4.0, 4.0]
        wall_z = [-1.0, -1.0, 1.0, 1.0, -1.0]
        result = _run_with_fake(tmp_path, _make_fake_eq(limiter_R=wall_r, limiter_Z=wall_z))
        np.testing.assert_allclose(
            result.wall_r, np.array(wall_r, dtype=np.float64),
            rtol=0.0, atol=1e-12,
            err_msg="wall_r 与 limiter_R 不一致，疑似 R/Z 交换或坐标缩放"
        )
        np.testing.assert_allclose(
            result.wall_z, np.array(wall_z, dtype=np.float64),
            rtol=0.0, atol=1e-12,
            err_msg="wall_z 与 limiter_Z 不一致，疑似 R/Z 交换或坐标缩放"
        )

    def test_rcentr_bcentr_current_match_fake(self, tmp_path):
        """rcentr、bcentr、current 与受控假对象对应数据一致。"""
        result = _run_with_fake(
            tmp_path,
            _make_fake_eq(R_center=6.2, B_center=5.3, Ip=15_599_996.7),
        )
        assert result.rcentr == pytest.approx(6.2)
        assert result.bcentr == pytest.approx(5.3)
        assert result.current == pytest.approx(15_599_996.7)

    def test_current_unit_ampere_no_scaling(self, tmp_path):
        """current 保持安培值，Reader 不执行 1e6 或 1e-6 等单位缩放。

        验证方式：受控输入值与输出值精确比较。
        若 Reader 错误地除以 1e6，current 会变成约 15.6；
        若 Reader 错误地乘以 1e6，current 会变成约 1.56e13。
        """
        ip_ampere = 15_599_996.7
        result = _run_with_fake(tmp_path, _make_fake_eq(Ip=ip_ampere))
        assert result.current == pytest.approx(ip_ampere, rel=1e-6), (
            f"current 疑似被缩放：期望 {ip_ampere}，实际 {result.current}"
        )


# ---------------------------------------------------------------------------
# M1-2：LCFS 闭合规范化
# ---------------------------------------------------------------------------

class TestLCFSClosure:
    """M1 LCFS 闭合规范化：Reader 负责确保 LCFS 首尾点重合。"""

    def test_already_closed_input_stays_closed(self, tmp_path):
        """已闭合输入（首尾重复）经 Reader 处理后仍严格闭合。"""
        # 逆时针正方形，首尾已重复
        r_in = np.array([1.0, 2.0, 2.0, 1.0, 1.0])
        z_in = np.array([0.0, 0.0, 1.0, 1.0, 0.0])
        result = _run_with_fake(tmp_path, _make_fake_eq(boundary_R=r_in, boundary_Z=z_in))
        _assert_closed(result.lcfs_r, result.lcfs_z)

    def test_unclosed_input_gets_closing_point(self, tmp_path):
        """首尾不重复的逆时针输入被规范为闭合输出（追加首点到末尾）。

        验证：
        - 输出严格闭合
        - 原始几何顶点未被替换（输出前 N 个点与输入完全一致）
        - 只增加了必要的闭合末点（输出长度 = 输入长度 + 1）
        """
        # 逆时针正方形，首尾不重复（4点）
        r_in = np.array([1.0, 2.0, 2.0, 1.0])
        z_in = np.array([0.0, 0.0, 1.0, 1.0])
        # 验证输入确实未闭合
        assert not (np.isclose(r_in[0], r_in[-1]) and np.isclose(z_in[0], z_in[-1])), \
            "测试前提：输入应首尾不重复"

        result = _run_with_fake(tmp_path, _make_fake_eq(boundary_R=r_in, boundary_Z=z_in))

        # 输出严格闭合
        _assert_closed(result.lcfs_r, result.lcfs_z)

        # 输出长度 = 输入长度 + 1（只追加了一个闭合点）
        assert len(result.lcfs_r) == len(r_in) + 1, (
            f"期望输出长度 {len(r_in) + 1}，实际 {len(result.lcfs_r)}"
        )

        # 原始几何顶点未被替换（前 N 个点与输入完全一致）
        np.testing.assert_allclose(
            result.lcfs_r[:len(r_in)], r_in,
            rtol=0.0, atol=1e-12,
            err_msg="原始 R 顶点被替换"
        )
        np.testing.assert_allclose(
            result.lcfs_z[:len(z_in)], z_in,
            rtol=0.0, atol=1e-12,
            err_msg="原始 Z 顶点被替换"
        )


# ---------------------------------------------------------------------------
# M1-3：LCFS 顺时针输入修正
# ---------------------------------------------------------------------------

class TestLCFSClockwiseCorrection:
    """M1 LCFS 方向修正：Reader 应将顺时针输入规范为逆时针。"""

    def test_clockwise_input_becomes_ccw(self, tmp_path):
        """顺时针 LCFS 输入经 Reader 处理后变为逆时针，且几何点集不变。

        验证：
        - 输出方向为逆时针（有向面积 > 0）
        - 输出严格闭合
        - 去掉重复末点后，输入与输出的几何点集完全一致
          （允许顺序反转、循环起点变化，不允许坐标被新增、丢失或替换）
        """
        # 顺时针正方形（5点，首尾重复）
        cw_r = np.array([1.0, 1.0, 2.0, 2.0, 1.0])
        cw_z = np.array([0.0, 1.0, 1.0, 0.0, 0.0])
        assert _signed_area(cw_r, cw_z) < 0, "测试前提：输入应为顺时针"

        result = _run_with_fake(tmp_path, _make_fake_eq(boundary_R=cw_r, boundary_Z=cw_z))

        # 输出方向为逆时针
        area = _signed_area(result.lcfs_r, result.lcfs_z)
        assert area > 0, (
            f"Reader 未将顺时针 LCFS 修正为逆时针，有向面积={area:.6g}"
        )

        # 输出严格闭合
        _assert_closed(result.lcfs_r, result.lcfs_z)

        # 去掉重复末点，提取唯一几何顶点
        def _unique_vertices(r, z):
            """去掉首尾重复末点，返回 (N, 2) 点数组。"""
            r = np.asarray(r, dtype=np.float64)
            z = np.asarray(z, dtype=np.float64)
            if len(r) >= 2 and np.allclose(r[0], r[-1]) and np.allclose(z[0], z[-1]):
                r = r[:-1]
                z = z[:-1]
            return np.column_stack([r, z])

        pts_in = _unique_vertices(cw_r, cw_z)
        pts_out = _unique_vertices(result.lcfs_r, result.lcfs_z)

        # 点数必须相同
        assert pts_in.shape[0] == pts_out.shape[0], (
            f"几何顶点数变化：输入 {pts_in.shape[0]}，输出 {pts_out.shape[0]}"
        )

        # 按 (R, Z) 稳定排序后比较，允许顺序反转和循环起点变化
        def _sort_pts(pts):
            idx = np.lexsort((pts[:, 1], pts[:, 0]))
            return pts[idx]

        sorted_in = _sort_pts(pts_in)
        sorted_out = _sort_pts(pts_out)

        np.testing.assert_allclose(
            sorted_out, sorted_in,
            rtol=0.0, atol=1e-12,
            err_msg="顺时针修正后几何点集发生变化（坐标被新增、丢失或替换）"
        )


# ---------------------------------------------------------------------------
# M1-4：第一壁缺失
# ---------------------------------------------------------------------------

class TestWallMissing:
    """M1 第一壁缺失：OFT 返回空数组时，wall_r/wall_z 应为 None。"""

    def test_wall_missing_both_none(self, tmp_path):
        """第一壁缺失（双空数组）时，wall_r 和 wall_z 同时为 None。"""
        fake_eq = _make_fake_eq(limiter_R=[], limiter_Z=[])
        result = _run_with_fake(tmp_path, fake_eq)

        assert result.wall_r is None, (
            f"第一壁缺失时 wall_r 应为 None，实际为 {type(result.wall_r)}"
        )
        assert result.wall_z is None, (
            f"第一壁缺失时 wall_z 应为 None，实际为 {type(result.wall_z)}"
        )

    # 注：蓝图未规定半缺失（R空/Z非空 或 R非空/Z空）行为，
    # 源码仅检查 lim_r 是否为空，不单独检查 lim_z。
    # 建议主管在蓝图中明确半缺失契约后再补充对应测试。


# ---------------------------------------------------------------------------
# M1-5：路径错误
# ---------------------------------------------------------------------------

class TestReadGfileErrors:
    """M1 路径错误：OFT 内部抛出 FileNotFoundError 时，Reader 应传播该异常。

    蓝图第 6.5 节：FileNotFoundError 由 GEQDSKEquilibrium 内部抛出。
    源码中 read_gfile 在调用 GEQDSKEquilibrium 前无路径存在性检查，
    因此让 mock 明确抛出 FileNotFoundError，验证异常传播。
    """

    def test_oft_raises_fnf_propagates(self, tmp_path):
        """OFT 抛出 FileNotFoundError 时，read_gfile 应将其传播给调用方。"""
        nonexistent = tmp_path / "does_not_exist.eqdsk"
        assert not nonexistent.exists()

        mock_cls = MagicMock(side_effect=FileNotFoundError("OFT: file not found"))

        with patch(
            "linkmesh.readers.gfile_reader.GEQDSKEquilibrium",
            mock_cls,
        ):
            with pytest.raises(FileNotFoundError):
                read_gfile(str(nonexistent))

        # 确认 mock 被调用了一次（Reader 确实将路径传给了 OFT）
        mock_cls.assert_called_once_with(str(nonexistent))


# ---------------------------------------------------------------------------
# M1-6：禁止手动解析的 AST 静态防线
# ---------------------------------------------------------------------------

class TestNoManualParsingAST:
    """M1 静态防线：gfile_reader.py 不得直接调用手动文件解析入口。"""

    # 禁止的裸函数名调用
    _FORBIDDEN_BARE_CALLS = frozenset({
        "open",
        "loadtxt",
        "genfromtxt",
    })

    # 禁止的属性方法调用（obj.method 中的 method）
    # 注意：不包含 exists/is_file，避免误报路径检查
    _FORBIDDEN_ATTR_CALLS = frozenset({
        "read_text",
        "read_bytes",
        "loadtxt",
        "genfromtxt",
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
            if isinstance(node, ast.Call):
                func = node.func
                # 裸函数名：open(...)
                if isinstance(func, ast.Name):
                    if func.id in self._FORBIDDEN_BARE_CALLS:
                        violations.append(
                            f"第 {node.lineno} 行：直接调用 {func.id}()"
                        )
                # 属性调用：xxx.read_text(...)、xxx.loadtxt(...) 等
                elif isinstance(func, ast.Attribute):
                    if func.attr in self._FORBIDDEN_ATTR_CALLS:
                        violations.append(
                            f"第 {node.lineno} 行：调用 .{func.attr}()"
                        )

        assert not violations, (
            "gfile_reader.py 包含手动文件解析调用，违反薄 OFT Adapter 边界：\n"
            + "\n".join(violations)
        )
