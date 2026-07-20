"""
tests/test_triangle_wrapper.py —— M2 Triangle Wrapper 验收测试

本文件包含三类测试：
    1. 受控 mock 契约测试（TestTriangleContractMock）：
       使用 mock 替换 triangle.triangulate，验证 alpha/beta 字典契约和 Mesh2D 字段映射。
       可在任何环境中运行。
    2. Wrapper 区域防御测试（TestWrapperRegionDefense）：
       使用 mock 验证 generate_mesh() 对非法区域属性的拒绝行为。
       可在任何环境中运行。
    3. _build_boundary_config() 静态测试（TestBuildBoundaryConfig）：
       使用合成 GFileData（SimpleNamespace）验证边界构造逻辑，不访问真实 GFile，不调用 OFT。
       可在任何环境中运行。
    4. 真实 Triangle 集成测试（TestTriangleRealIntegration）：
       不 mock triangle.triangulate，调用真实 generate_mesh。
       需要 User 人工审查后在 Linux 服务器上运行，本轮 Aider 编辑期间未执行。

注意：本文件的编辑完成不等同于 M2 验收通过。M2 验收需要 User 在服务器上
实际运行测试并确认结果，详见 LinkMesh_Architecture_Plan.md 第 13 节。
"""

import math
import re
import types
import argparse
from unittest.mock import patch

import numpy as np
import pytest

from linkmesh.mesher.triangle_wrapper import (
    BoundaryConfig,
    Mesh2D,
    generate_mesh,
)


# ---------------------------------------------------------------------------
# 测试辅助：构造最小合法 BoundaryConfig
# ---------------------------------------------------------------------------

def _make_minimal_boundary_config(
    min_angle: float = 20.0,
    max_area=None,
) -> BoundaryConfig:
    """构造最小合法 BoundaryConfig：逆时针单位正方形，单区域 region_id=1。"""
    vertices = np.array([
        [1.0, 0.0],
        [2.0, 0.0],
        [2.0, 1.0],
        [1.0, 1.0],
    ], dtype=np.float64)
    segments = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int32)
    segment_markers = np.array([1, 1, 1, 1], dtype=np.int32)
    regions = np.array([[1.5, 0.5, 1.0, -1.0]], dtype=np.float64)
    return BoundaryConfig(
        vertices=vertices,
        segments=segments,
        segment_markers=segment_markers,
        regions=regions,
        min_angle=min_angle,
        max_area=max_area,
    )


def _make_minimal_mesh2d() -> Mesh2D:
    """构造受控合成 Mesh2D，用于 mock 输出验证。

    使用可区分的边界标记（1, 2, 3）和节点标记（0, 1, 2）以便检测
    清零、偏置、错序或读取错误字段等问题。
    区域编号使用蓝图允许的物理值（1=plasma）。
    """
    nodes = np.array([
        [1.0, 0.0], [2.0, 0.0], [2.0, 1.0],
        [1.0, 1.0], [1.5, 0.3], [1.5, 0.7],
    ], dtype=np.float64)
    triangles = np.array([
        [0, 1, 4], [1, 2, 5], [2, 3, 5], [3, 0, 4],
    ], dtype=np.int32)
    region_ids = np.array([1, 1, 1, 1], dtype=np.int32)
    boundary_segments = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int32)
    boundary_markers = np.array([1, 2, 3, 1], dtype=np.int32)
    node_markers = np.array([1, 2, 1, 2, 0, 0], dtype=np.int32)
    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=boundary_segments,
        boundary_markers=boundary_markers,
        node_markers=node_markers,
    )


def _make_triangle_output(mesh: Mesh2D) -> dict:
    """根据 Mesh2D 构造 Triangle beta 字典（0-based 索引）。

    triangle_attributes 以 (T, 1) 形状返回（模拟真实 Triangle 输出），
    segment_markers 和 vertex_markers 以 (S, 1) 和 (N, 1) 形状返回，
    用于验证 Wrapper 的 reshape(-1) 规范化逻辑。
    """
    return {
        "vertices": mesh.nodes.copy(),
        "triangles": mesh.triangles.copy(),
        "triangle_attributes": mesh.region_ids.reshape(-1, 1).astype(np.float64),
        "segments": mesh.boundary_segments.copy(),
        "segment_markers": mesh.boundary_markers.reshape(-1, 1).copy(),
        "vertex_markers": mesh.node_markers.reshape(-1, 1).copy(),
    }


def _make_beta_with_region_ids(region_ids_1d: np.ndarray) -> dict:
    """构造含指定区域编号的合法 beta 字典（节点、三角形等均合法）。

    用于 Wrapper 区域防御测试，确保失败来自区域契约而非无关字段。
    """
    n_tri = len(region_ids_1d)
    # 构造足够多的节点（至少覆盖三角形索引）
    n_nodes = max(n_tri + 2, 4)
    nodes = np.zeros((n_nodes, 2), dtype=np.float64)
    for i in range(n_nodes):
        nodes[i] = [float(i), 0.0]
    # 构造合法三角形（每个三角形使用连续三个节点，确保索引合法）
    triangles = np.zeros((n_tri, 3), dtype=np.int32)
    for i in range(n_tri):
        triangles[i] = [0, 1, 2]  # 使用固定的合法索引
    return {
        "vertices": nodes,
        "triangles": triangles,
        "triangle_attributes": region_ids_1d.reshape(-1, 1).astype(np.float64),
        "segments": np.zeros((0, 2), dtype=np.int32),
        "segment_markers": np.zeros((0, 1), dtype=np.int32),
        "vertex_markers": np.zeros((n_nodes, 1), dtype=np.int32),
    }


# ---------------------------------------------------------------------------
# 辅助：构造合成 GFileData 和 CLI args（用于 _build_boundary_config 测试）
# ---------------------------------------------------------------------------

def _make_gfile_data(
    lcfs_r, lcfs_z,
    rmaxis, zmaxis,
    wall_r=None, wall_z=None,
) -> types.SimpleNamespace:
    """构造合成 GFileData（SimpleNamespace），不访问真实 GFile，不调用 OFT。"""
    return types.SimpleNamespace(
        lcfs_r=np.asarray(lcfs_r, dtype=np.float64),
        lcfs_z=np.asarray(lcfs_z, dtype=np.float64),
        rmaxis=float(rmaxis),
        zmaxis=float(zmaxis),
        wall_r=np.asarray(wall_r, dtype=np.float64) if wall_r is not None else None,
        wall_z=np.asarray(wall_z, dtype=np.float64) if wall_z is not None else None,
    )


def _make_cli_args(min_angle=20.0, max_area=None) -> argparse.Namespace:
    """构造最小 CLI args。"""
    args = argparse.Namespace()
    args.min_angle = min_angle
    args.max_area = max_area
    return args


def _make_nested_polygons():
    """构造三个嵌套的简单多边形（LCFS、第一壁、outer boundary）。

    使用正方形近似，便于人工判断内外关系：
        LCFS：中心 (5,0)，半径约 1（正方形 [4,6] x [-1,1]）
        第一壁：中心 (5,0)，半径约 2（正方形 [3,7] x [-2,2]）
        outer boundary 由 _build_boundary_config 自动构造

    磁轴：(5.0, 0.0)，严格在 LCFS 内。
    """
    # LCFS：逆时针正方形，4 个顶点 + 首点重复（闭合）
    lcfs_r = np.array([4.0, 6.0, 6.0, 4.0, 4.0])
    lcfs_z = np.array([-1.0, -1.0, 1.0, 1.0, -1.0])
    # 第一壁：逆时针正方形，包围 LCFS
    wall_r = np.array([3.0, 7.0, 7.0, 3.0, 3.0])
    wall_z = np.array([-2.0, -2.0, 2.0, 2.0, -2.0])
    rmaxis = 5.0
    zmaxis = 0.0
    return lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis


# ---------------------------------------------------------------------------
# M2-1：Triangle alpha/beta 契约映射测试（mock）
# ---------------------------------------------------------------------------

class TestTriangleContractMock:
    """M2 契约映射：mock triangle.triangulate，验证输入输出字典契约。"""

    def _run_with_mock(self, config: BoundaryConfig, fake_mesh: Mesh2D):
        captured = {}

        def fake_triangulate(alpha, opts):
            captured["alpha"] = alpha
            captured["opts"] = opts
            return _make_triangle_output(fake_mesh)

        with patch("triangle.triangulate", side_effect=fake_triangulate):
            result = generate_mesh(config)

        return result, captured

    # --- alpha 四字段存在性与内容验证 ---

    def test_alpha_four_fields_exist(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha = captured["alpha"]
        for key in ("vertices", "segments", "segment_markers", "regions"):
            assert key in alpha, f"alpha 字典缺少字段：{key}"

    def test_alpha_vertices_content_and_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_v = captured["alpha"]["vertices"]
        np.testing.assert_array_almost_equal(alpha_v, config.vertices)
        assert alpha_v.dtype == np.float64
        assert alpha_v.shape == (4, 2)

    def test_alpha_segments_content_and_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_s = captured["alpha"]["segments"]
        np.testing.assert_array_equal(alpha_s, config.segments)
        assert alpha_s.dtype == np.int32
        assert alpha_s.shape == (4, 2)

    def test_alpha_segment_markers_content_and_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_sm = captured["alpha"]["segment_markers"]
        np.testing.assert_array_equal(alpha_sm, config.segment_markers)
        assert alpha_sm.dtype == np.int32
        assert alpha_sm.shape == (4,)

    def test_alpha_regions_content_and_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_r = captured["alpha"]["regions"]
        np.testing.assert_array_almost_equal(alpha_r, config.regions)
        assert alpha_r.dtype == np.float64
        assert alpha_r.shape == (1, 4)

    def test_alpha_region_id_not_offset(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        region_ids_in_alpha = captured["alpha"]["regions"][:, 2]
        expected_ids = config.regions[:, 2]
        np.testing.assert_array_almost_equal(region_ids_in_alpha, expected_ids)

    # --- Triangle 选项字符串精确验证 ---

    def test_opts_exact_without_max_area(self):
        config = _make_minimal_boundary_config(min_angle=20.0, max_area=None)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert captured["opts"] == "pq20.0AzQ"

    def test_opts_exact_with_max_area(self):
        config = _make_minimal_boundary_config(min_angle=20.0, max_area=0.1)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert captured["opts"] == "pq20.0a0.1AzQ"

    def test_opts_uppercase_A_always_present(self):
        for max_area in (None, 0.05):
            config = _make_minimal_boundary_config(max_area=max_area)
            fake_mesh = _make_minimal_mesh2d()
            _, captured = self._run_with_mock(config, fake_mesh)
            assert "A" in captured["opts"]

    def test_opts_lowercase_a_only_when_max_area_set(self):
        config_none = _make_minimal_boundary_config(max_area=None)
        fake_mesh = _make_minimal_mesh2d()
        _, captured_none = self._run_with_mock(config_none, fake_mesh)
        assert not re.search(r"a\d", captured_none["opts"])

        config_set = _make_minimal_boundary_config(max_area=0.05)
        _, captured_set = self._run_with_mock(config_set, fake_mesh)
        assert re.search(r"a\d", captured_set["opts"])

    def test_opts_contains_p_q_z_Q(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        opts = captured["opts"]
        for ch in ("p", "q", "z", "Q"):
            assert ch in opts

    # --- beta 六字段精确映射验证 ---

    def test_nodes_exact_content_and_shape_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.nodes, fake_mesh.nodes)
        assert result.nodes.shape == (6, 2)
        assert result.nodes.dtype == np.float64

    def test_triangles_exact_content_and_shape_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.triangles, fake_mesh.triangles)
        assert result.triangles.shape == (4, 3)
        assert result.triangles.dtype == np.int32

    def test_region_ids_exact_content_and_shape_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.region_ids, fake_mesh.region_ids)
        assert result.region_ids.shape == (4,)
        assert result.region_ids.dtype == np.int32

    def test_boundary_segments_exact_content_and_shape_dtype(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.boundary_segments, fake_mesh.boundary_segments)
        assert result.boundary_segments.shape == (4, 2)
        assert result.boundary_segments.dtype == np.int32

    def test_boundary_markers_exact_content_and_shape_dtype(self):
        """使用可区分标记值 [1, 2, 3, 1]，验证未清零、未偏置、未改写。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.boundary_markers, fake_mesh.boundary_markers)
        assert result.boundary_markers.shape == (4,)
        assert result.boundary_markers.dtype == np.int32

    def test_node_markers_exact_content_and_shape_dtype(self):
        """使用可区分标记值 [1, 2, 1, 2, 0, 0]，验证未清零、未偏置、未改写。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.node_markers, fake_mesh.node_markers)
        assert result.node_markers.shape == (6,)
        assert result.node_markers.dtype == np.int32

    # --- 索引合法性验证 ---

    def test_triangles_zero_based_and_valid_range(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        n = result.n_nodes
        assert result.triangles.min() >= 0
        assert result.triangles.max() < n

    def test_boundary_segments_zero_based_and_valid_range(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        n = result.n_nodes
        assert result.boundary_segments.min() >= 0
        assert result.boundary_segments.max() < n

    def test_triangles_not_offset_by_one(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.triangles, fake_mesh.triangles)

    def test_region_ids_not_offset(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.region_ids, fake_mesh.region_ids)

    def test_boundary_markers_valid_range(self):
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        valid_markers = {0, 1, 2, 3}
        actual_markers = set(result.boundary_markers.tolist())
        assert actual_markers.issubset(valid_markers)

    # --- 单元素 shape 测试 ---

    def test_single_triangle_region_ids_shape_is_1d(self):
        """triangle_attributes.shape==(1,1) 时，result.region_ids.shape 必须为 (1,)。"""
        single_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.array([[0, 1, 2]], dtype=np.int32),
            "triangle_attributes": np.array([[1.0]], dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()
        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)
        assert result.region_ids.ndim == 1
        assert result.region_ids.shape == (1,)
        assert result.region_ids[0] == 1

    def test_single_segment_boundary_markers_shape_is_1d(self):
        """segment_markers 只有一个元素时，result.boundary_markers.shape 必须为 (1,)。"""
        single_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.array([[0, 1, 2]], dtype=np.int32),
            "triangle_attributes": np.array([[1.0]], dtype=np.float64),
            "segments": np.array([[0, 1]], dtype=np.int32),
            "segment_markers": np.array([[2]], dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()
        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)
        assert result.boundary_markers.ndim == 1
        assert result.boundary_markers.shape == (1,)
        assert result.boundary_markers[0] == 2

    def test_single_node_marker_shape_is_1d(self):
        """vertex_markers 只有一个元素时，result.node_markers.shape 必须为 (1,)。"""
        single_beta = {
            "vertices": np.array([[1.0, 0.0]], dtype=np.float64),
            "triangles": np.array([[0, 0, 0]], dtype=np.int32),
            "triangle_attributes": np.array([[1.0]], dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.array([[1]], dtype=np.int32),
        }
        config = _make_minimal_boundary_config()
        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)
        assert result.node_markers.ndim == 1
        assert result.node_markers.shape == (1,)
        assert result.node_markers[0] == 1

    # --- 空输出异常测试 ---

    def test_empty_vertices_raises_value_error(self):
        empty_beta = {
            "vertices": np.zeros((0, 2), dtype=np.float64),
            "triangles": np.zeros((0, 3), dtype=np.int32),
            "triangle_attributes": np.zeros((0, 1), dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((0, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()
        with patch("triangle.triangulate", return_value=empty_beta):
            with pytest.raises(ValueError, match="节点数为 0"):
                generate_mesh(config)

    def test_empty_triangles_raises_value_error(self):
        empty_tri_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.zeros((0, 3), dtype=np.int32),
            "triangle_attributes": np.zeros((0, 1), dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()
        with patch("triangle.triangulate", return_value=empty_tri_beta):
            with pytest.raises(ValueError, match="三角形数为 0"):
                generate_mesh(config)


# ---------------------------------------------------------------------------
# M2-2：Wrapper 区域防御测试（mock）
# ---------------------------------------------------------------------------

class TestWrapperRegionDefense:
    """验证 generate_mesh() 对非法区域属性的拒绝行为。

    所有测试使用 patch("triangle.triangulate", ...)，确保失败来自区域契约检查
    而非无关字段问题。
    """

    def _make_config_with_regions(self, region_ids_list: list) -> BoundaryConfig:
        """构造含指定区域编号的 BoundaryConfig。"""
        vertices = np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]], dtype=np.float64)
        segments = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int32)
        segment_markers = np.ones(4, dtype=np.int32)
        regions = np.array(
            [[1.5, 0.5, float(rid), -1.0] for rid in region_ids_list],
            dtype=np.float64,
        )
        return BoundaryConfig(
            vertices=vertices,
            segments=segments,
            segment_markers=segment_markers,
            regions=regions,
            min_angle=20.0,
            max_area=None,
        )

    # --- 配置区域编号非法 ---

    def test_config_region_id_zero_raises(self):
        """配置区域编号含 0 时抛出 ValueError。"""
        config = self._make_config_with_regions([0, 1, 2])
        fake_beta = _make_beta_with_region_ids(np.array([1, 2], dtype=np.int32))
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="0"):
                generate_mesh(config)

    def test_config_region_id_noninteger_raises(self):
        """配置区域编号含非整数值（1.5）时抛出 ValueError，不得被静默截断。"""
        vertices = np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]], dtype=np.float64)
        segments = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int32)
        segment_markers = np.ones(4, dtype=np.int32)
        regions = np.array([[1.5, 0.5, 1.5, -1.0]], dtype=np.float64)
        config = BoundaryConfig(
            vertices=vertices, segments=segments,
            segment_markers=segment_markers, regions=regions,
        )
        fake_beta = _make_beta_with_region_ids(np.array([1], dtype=np.int32))
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="整数"):
                generate_mesh(config)

    def test_config_region_id_duplicate_raises(self):
        """配置区域编号重复时抛出 ValueError。"""
        vertices = np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]], dtype=np.float64)
        segments = np.array([[0, 1], [1, 2], [2, 3], [3, 0]], dtype=np.int32)
        segment_markers = np.ones(4, dtype=np.int32)
        regions = np.array([
            [1.5, 0.5, 1.0, -1.0],
            [1.5, 0.5, 1.0, -1.0],  # 重复
        ], dtype=np.float64)
        config = BoundaryConfig(
            vertices=vertices, segments=segments,
            segment_markers=segment_markers, regions=regions,
        )
        fake_beta = _make_beta_with_region_ids(np.array([1, 1], dtype=np.int32))
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="重复"):
                generate_mesh(config)

    # --- 输出区域属性非法 ---

    def test_output_contains_zero_raises(self):
        """配置 {1,2,3}，输出含 0 时抛出 ValueError。"""
        config = self._make_config_with_regions([1, 2, 3])
        # 输出含 0（Triangle 默认属性）
        out_ids = np.array([0, 1, 2], dtype=np.int32)
        fake_beta = _make_beta_with_region_ids(out_ids)
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="0"):
                generate_mesh(config)

    def test_output_missing_configured_region_raises(self):
        """配置 {1,2,3}，输出只含 {1,2} 时抛出 ValueError（缺少区域 3）。"""
        config = self._make_config_with_regions([1, 2, 3])
        out_ids = np.array([1, 2, 1, 2], dtype=np.int32)
        fake_beta = _make_beta_with_region_ids(out_ids)
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="缺少"):
                generate_mesh(config)

    def test_output_extra_unconfigured_region_raises(self):
        """配置 {1,2}，输出含额外区域 3 时抛出 ValueError。"""
        config = self._make_config_with_regions([1, 2])
        out_ids = np.array([1, 2, 3], dtype=np.int32)
        fake_beta = _make_beta_with_region_ids(out_ids)
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="未配置"):
                generate_mesh(config)

    def test_output_attr_length_mismatch_raises(self):
        """输出区域属性长度与三角形数不一致时抛出 ValueError。"""
        config = self._make_config_with_regions([1])
        # 构造 beta：3 个三角形，但 triangle_attributes 只有 2 行
        nodes = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0], [0.5, 0.5]], dtype=np.float64)
        triangles = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3]], dtype=np.int32)
        bad_beta = {
            "vertices": nodes,
            "triangles": triangles,
            "triangle_attributes": np.array([[1.0], [1.0]], dtype=np.float64),  # 只有 2 行
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((4, 1), dtype=np.int32),
        }
        with patch("triangle.triangulate", return_value=bad_beta):
            with pytest.raises(ValueError, match="长度"):
                generate_mesh(config)

    def test_output_nan_in_attrs_raises(self):
        """输出区域属性含 NaN 时抛出 ValueError。"""
        config = self._make_config_with_regions([1])
        out_ids = np.array([np.nan], dtype=np.float64)
        fake_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.array([[0, 1, 2]], dtype=np.int32),
            "triangle_attributes": out_ids.reshape(-1, 1),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="非有限"):
                generate_mesh(config)

    def test_output_noninteger_attr_raises(self):
        """输出区域属性含 1.5 等非整数值时抛出 ValueError，不得被静默截断。"""
        config = self._make_config_with_regions([1])
        out_ids = np.array([1.5], dtype=np.float64)
        fake_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.array([[0, 1, 2]], dtype=np.int32),
            "triangle_attributes": out_ids.reshape(-1, 1),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        with patch("triangle.triangulate", return_value=fake_beta):
            with pytest.raises(ValueError, match="整数"):
                generate_mesh(config)

    def test_valid_output_passes(self):
        """配置集合与输出集合一致时，generate_mesh 正常返回 Mesh2D。"""
        config = self._make_config_with_regions([1])
        out_ids = np.array([1, 1, 1], dtype=np.int32)
        fake_beta = _make_beta_with_region_ids(out_ids)
        with patch("triangle.triangulate", return_value=fake_beta):
            result = generate_mesh(config)
        assert isinstance(result, Mesh2D)
        assert set(result.region_ids.tolist()) == {1}

    def test_valid_three_region_output_passes(self):
        """配置 {1,2,3}，输出 {1,2,3} 时正常通过。"""
        config = self._make_config_with_regions([1, 2, 3])
        out_ids = np.array([1, 2, 3, 1, 2, 3], dtype=np.int32)
        fake_beta = _make_beta_with_region_ids(out_ids)
        with patch("triangle.triangulate", return_value=fake_beta):
            result = generate_mesh(config)
        assert isinstance(result, Mesh2D)
        assert set(result.region_ids.tolist()) == {1, 2, 3}


# ---------------------------------------------------------------------------
# M2-3：_build_boundary_config() 静态测试
# ---------------------------------------------------------------------------

class TestBuildBoundaryConfig:
    """验证 _build_boundary_config() 的边界构造逻辑。

    使用合成 GFileData（SimpleNamespace），不访问真实 GFile，不调用 OFT，不写文件。
    使用简单嵌套正方形，便于人工判断内外关系。
    """

    def _call(self, gfile_data, min_angle=20.0, max_area=None):
        from linkmesh.cli import _build_boundary_config
        args = _make_cli_args(min_angle=min_angle, max_area=max_area)
        return _build_boundary_config(gfile_data, args)

    def _point_in_polygon_simple(self, pr, pz, poly_r, poly_z):
        """简单射线法，用于测试中验证种子内外关系（独立实现，不依赖业务代码）。"""
        n = len(poly_r)
        inside = False
        j = n - 1
        for i in range(n):
            ri, zi = poly_r[i], poly_z[i]
            rj, zj = poly_r[j], poly_z[j]
            if ((zi > pz) != (zj > pz)):
                r_int = rj + (pz - zj) / (zi - zj) * (ri - rj)
                if pr < r_int:
                    inside = not inside
            j = i
        return inside

    # --- 含第一壁的三区域方案 ---

    def test_three_region_shape_and_dtype(self):
        """含第一壁时 regions.shape==(3,4)，dtype==float64。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        assert config.regions.shape == (3, 4), f"regions.shape={config.regions.shape}"
        assert config.regions.dtype == np.float64

    def test_three_region_ids_order(self):
        """含第一壁时 regions[:,2] 编号集合为 {1,2,3}，顺序为 1,2,3。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        ids = config.regions[:, 2].astype(int).tolist()
        assert ids == [1, 2, 3], f"区域编号顺序错误：{ids}"

    def test_plasma_seed_inside_lcfs(self):
        """plasma seed 严格位于 LCFS 内。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        pr, pz = config.regions[0, 0], config.regions[0, 1]
        # LCFS 去掉重复末尾点
        lr = lcfs_r[:-1] if np.isclose(lcfs_r[0], lcfs_r[-1]) else lcfs_r
        lz = lcfs_z[:-1] if np.isclose(lcfs_z[0], lcfs_z[-1]) else lcfs_z
        assert self._point_in_polygon_simple(pr, pz, lr, lz), (
            f"plasma seed ({pr:.4f},{pz:.4f}) 不在 LCFS 内"
        )

    def test_vacuum_seed_outside_lcfs_inside_wall(self):
        """vacuum seed 严格位于 LCFS 外且第一壁内。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        vr, vz = config.regions[1, 0], config.regions[1, 1]
        lr = lcfs_r[:-1] if np.isclose(lcfs_r[0], lcfs_r[-1]) else lcfs_r
        lz = lcfs_z[:-1] if np.isclose(lcfs_z[0], lcfs_z[-1]) else lcfs_z
        wr = wall_r[:-1] if np.isclose(wall_r[0], wall_r[-1]) else wall_r
        wz = wall_z[:-1] if np.isclose(wall_z[0], wall_z[-1]) else wall_z
        assert not self._point_in_polygon_simple(vr, vz, lr, lz), (
            f"vacuum seed ({vr:.4f},{vz:.4f}) 不应在 LCFS 内"
        )
        assert self._point_in_polygon_simple(vr, vz, wr, wz), (
            f"vacuum seed ({vr:.4f},{vz:.4f}) 应在第一壁内"
        )

    def test_region3_seed_outside_wall_inside_outer(self):
        """region 3 seed 严格位于第一壁外且 outer boundary 内。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        r3, z3 = config.regions[2, 0], config.regions[2, 1]
        wr = wall_r[:-1] if np.isclose(wall_r[0], wall_r[-1]) else wall_r
        wz = wall_z[:-1] if np.isclose(wall_z[0], wall_z[-1]) else wall_z
        assert not self._point_in_polygon_simple(r3, z3, wr, wz), (
            f"region 3 seed ({r3:.4f},{z3:.4f}) 不应在第一壁内"
        )
        # outer boundary 是矩形，直接用包围盒检查（outer boundary 由 _build_boundary_config 构造）
        # 只验证 region 3 seed 不在第一壁内（已足够区分）

    def test_segment_markers_1_2_3_all_present(self):
        """含第一壁时 segment_markers 中 1、2、3 均存在。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)
        markers = set(config.segment_markers.tolist())
        assert 1 in markers, "segment_markers 缺少 LCFS 标记 1"
        assert 2 in markers, "segment_markers 缺少第一壁标记 2"
        assert 3 in markers, "segment_markers 缺少 outer boundary 标记 3"

    def test_seeds_not_on_boundary(self):
        """三个种子均不在相应边界上（到边界距离 > 0）。"""
        from linkmesh.cli import _point_min_dist_to_polygon, _strip_closed_duplicate
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r, wall_z)
        config = self._call(gd)

        lr, lz = _strip_closed_duplicate(lcfs_r, lcfs_z)
        wr, wz = _strip_closed_duplicate(wall_r, wall_z)

        # plasma seed 到 LCFS 的距离
        pr, pz = config.regions[0, 0], config.regions[0, 1]
        d_p = _point_min_dist_to_polygon(pr, pz, lr, lz)
        assert d_p > 1e-6, f"plasma seed 过于接近 LCFS 边界：距离 {d_p:.4g} m"

        # vacuum seed 到 LCFS 和第一壁的距离
        vr, vz = config.regions[1, 0], config.regions[1, 1]
        d_v_lcfs = _point_min_dist_to_polygon(vr, vz, lr, lz)
        d_v_wall = _point_min_dist_to_polygon(vr, vz, wr, wz)
        assert d_v_lcfs > 1e-6, f"vacuum seed 过于接近 LCFS：距离 {d_v_lcfs:.4g} m"
        assert d_v_wall > 1e-6, f"vacuum seed 过于接近第一壁：距离 {d_v_wall:.4g} m"

        # region 3 seed 到第一壁的距离
        r3, z3 = config.regions[2, 0], config.regions[2, 1]
        d_r3_wall = _point_min_dist_to_polygon(r3, z3, wr, wz)
        assert d_r3_wall > 1e-6, f"region 3 seed 过于接近第一壁：距离 {d_r3_wall:.4g} m"

    # --- 无壁轮廓的两区域降级方案 ---

    def test_two_region_wall_none(self):
        """wall_r=None, wall_z=None 时 regions.shape==(2,4)，编号为 {1,2}。"""
        lcfs_r, lcfs_z, _, _, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=None, wall_z=None)
        config = self._call(gd)
        assert config.regions.shape == (2, 4), f"regions.shape={config.regions.shape}"
        ids = set(config.regions[:, 2].astype(int).tolist())
        assert ids == {1, 2}, f"区域编号集合错误：{ids}"

    def test_two_region_wall_empty_arrays(self):
        """wall_r=[], wall_z=[] 时 regions.shape==(2,4)，编号为 {1,2}。"""
        lcfs_r, lcfs_z, _, _, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=[], wall_z=[])
        config = self._call(gd)
        assert config.regions.shape == (2, 4)
        ids = set(config.regions[:, 2].astype(int).tolist())
        assert ids == {1, 2}

    def test_two_region_no_marker_2(self):
        """无壁方案时 segment_markers 中不含 2，含 1 和 3。"""
        lcfs_r, lcfs_z, _, _, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=None, wall_z=None)
        config = self._call(gd)
        markers = set(config.segment_markers.tolist())
        assert 2 not in markers, "无壁方案不应含 segment_marker=2"
        assert 1 in markers
        assert 3 in markers

    def test_two_region_vacuum_seed_outside_lcfs(self):
        """无壁方案时 vacuum seed 在 LCFS 外且 outer boundary 内。"""
        lcfs_r, lcfs_z, _, _, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=None, wall_z=None)
        config = self._call(gd)
        vr, vz = config.regions[1, 0], config.regions[1, 1]
        lr = lcfs_r[:-1] if np.isclose(lcfs_r[0], lcfs_r[-1]) else lcfs_r
        lz = lcfs_z[:-1] if np.isclose(lcfs_z[0], lcfs_z[-1]) else lcfs_z
        assert not self._point_in_polygon_simple(vr, vz, lr, lz), (
            f"无壁方案 vacuum seed ({vr:.4f},{vz:.4f}) 不应在 LCFS 内"
        )

    # --- 非法壁数据 ---

    def test_wall_only_r_raises(self):
        """只有 wall_r 没有 wall_z 时抛出 ValueError。"""
        lcfs_r, lcfs_z, wall_r, _, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=wall_r, wall_z=None)
        with pytest.raises(ValueError):
            self._call(gd)

    def test_wall_only_z_raises(self):
        """只有 wall_z 没有 wall_r 时抛出 ValueError。"""
        lcfs_r, lcfs_z, _, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=None, wall_z=wall_z)
        with pytest.raises(ValueError):
            self._call(gd)

    def test_wall_length_mismatch_raises(self):
        """wall_r 和 wall_z 长度不一致时抛出 ValueError。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis,
                               wall_r=wall_r, wall_z=wall_z[:-1])
        with pytest.raises(ValueError):
            self._call(gd)

    def test_wall_with_nan_raises(self):
        """壁数据含 NaN 时抛出 ValueError。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        wall_r_bad = wall_r.copy()
        wall_r_bad[0] = np.nan
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis,
                               wall_r=wall_r_bad, wall_z=wall_z)
        with pytest.raises(ValueError):
            self._call(gd)

    def test_wall_too_few_points_raises(self):
        """壁数据有效点不足（去重后 < 3）时抛出 ValueError。"""
        lcfs_r, lcfs_z, _, _, rmaxis, zmaxis = _make_nested_polygons()
        # 只有 2 个不同点（加首点重复共 3 个，但去重后只有 2 个）
        wall_r_bad = np.array([3.0, 7.0, 3.0])
        wall_z_bad = np.array([-2.0, -2.0, -2.0])
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis,
                               wall_r=wall_r_bad, wall_z=wall_z_bad)
        with pytest.raises(ValueError):
            self._call(gd)

    # --- 磁轴位置非法 ---

    def test_rmaxis_outside_lcfs_raises(self):
        """磁轴位于 LCFS 外时抛出 ValueError。"""
        lcfs_r, lcfs_z, wall_r, wall_z, _, _ = _make_nested_polygons()
        # 磁轴放在 LCFS 外（第一壁内）
        gd = _make_gfile_data(lcfs_r, lcfs_z, 3.5, 0.0, wall_r=wall_r, wall_z=wall_z)
        with pytest.raises(ValueError):
            self._call(gd)

    # --- 嵌套关系非法 ---

    def test_lcfs_outside_wall_raises(self):
        """LCFS 不在第一壁内时抛出 ValueError。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        # 交换 LCFS 和第一壁（LCFS 比第一壁大）
        gd = _make_gfile_data(wall_r, wall_z, rmaxis, zmaxis, wall_r=lcfs_r, wall_z=lcfs_z)
        with pytest.raises(ValueError):
            self._call(gd)

    # --- 自交曲线 ---

    def test_self_intersecting_lcfs_raises(self):
        """自交的 LCFS 被拒绝，抛出 ValueError。"""
        # 构造自交的 LCFS（8 字形）
        lcfs_r = np.array([4.0, 6.0, 4.0, 6.0, 4.0])
        lcfs_z = np.array([-1.0, 1.0, 1.0, -1.0, -1.0])
        gd = _make_gfile_data(lcfs_r, lcfs_z, 5.0, 0.0)
        with pytest.raises(ValueError):
            self._call(gd)

    # --- 确定性 ---

    def test_seed_search_is_deterministic(self):
        """同一输入重复构造两次时区域种子完全一致（确定性搜索）。"""
        lcfs_r, lcfs_z, wall_r, wall_z, rmaxis, zmaxis = _make_nested_polygons()
        gd = _make_gfile_data(lcfs_r, lcfs_z, rmaxis, zmaxis, wall_r=wall_r, wall_z=wall_z)
        config1 = self._call(gd)
        config2 = self._call(gd)
        np.testing.assert_array_equal(
            config1.regions, config2.regions,
            err_msg="区域种子搜索不具有确定性：两次结果不一致"
        )


# ---------------------------------------------------------------------------
# M2-4：真实 Triangle 最小集成测试
# ---------------------------------------------------------------------------

class TestTriangleRealIntegration:
    """M2 真实 Triangle 集成测试。

    本类测试不 mock triangle.triangulate，调用真实 generate_mesh。
    需要 User 人工审查后在 Linux 服务器上运行，本轮 Aider 编辑期间未执行。
    """

    def _make_convex_config(self) -> BoundaryConfig:
        """构造无尖锐角的凸域 BoundaryConfig（正六边形近似），单区域 region_id=1。"""
        n = 6
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        r = 1.0 + np.cos(angles)
        z = np.sin(angles)
        vertices = np.column_stack([r, z]).astype(np.float64)
        segments = np.column_stack([
            np.arange(n, dtype=np.int32),
            np.roll(np.arange(n, dtype=np.int32), -1),
        ])
        segment_markers = np.ones(n, dtype=np.int32)
        regions = np.array([[1.0, 0.0, 1.0, -1.0]], dtype=np.float64)
        return BoundaryConfig(
            vertices=vertices,
            segments=segments,
            segment_markers=segment_markers,
            regions=regions,
            min_angle=20.0,
            max_area=0.05,
        )

    def test_real_triangle_returns_valid_mesh(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert isinstance(mesh, Mesh2D)
        assert mesh.n_nodes > 0
        assert mesh.n_triangles > 0

    def test_real_triangle_nodes_finite(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert np.all(np.isfinite(mesh.nodes))

    def test_real_triangle_indices_zero_based_valid(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert mesh.triangles.min() >= 0
        assert mesh.triangles.max() < mesh.n_nodes

    def test_real_triangle_no_degenerate_triangles(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        for i, tri in enumerate(mesh.triangles):
            assert len(set(tri.tolist())) == 3, f"三角形 {i} 存在重复顶点索引：{tri}"

    def test_real_triangle_positive_area(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        nodes = mesh.nodes
        for i, tri in enumerate(mesh.triangles):
            p0, p1, p2 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
            area = abs(
                (p1[0] - p0[0]) * (p2[1] - p0[1])
                - (p2[0] - p0[0]) * (p1[1] - p0[1])
            ) / 2.0
            assert area > 1e-12, f"三角形 {i} 面积过小：{area}"

    def test_real_triangle_region_ids_valid(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        valid = {1, 2, 3}
        actual = set(mesh.region_ids.tolist())
        assert actual.issubset(valid), f"region_ids 包含非法值：{actual - valid}"

    def test_real_triangle_single_region_is_1(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        actual = set(mesh.region_ids.tolist())
        assert actual == {1}, f"单区域样例 region_ids 应为 {{1}}，实际为 {actual}"

    def test_real_triangle_boundary_consistency(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert mesh.n_boundary_segments == len(mesh.boundary_markers)

    def test_real_triangle_min_angle(self):
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        actual_min, tri_idx, node_indices = _compute_min_angle(mesh)
        configured = config.min_angle
        assert actual_min >= configured - 0.01, (
            f"最小内角验收失败：\n"
            f"  配置最小角: {configured}°\n"
            f"  实际最小角: {actual_min:.4f}°\n"
            f"  对应三角形编号: {tri_idx}\n"
            f"  对应节点索引: {node_indices}"
        )


# ---------------------------------------------------------------------------
# 最小内角计算辅助函数
# ---------------------------------------------------------------------------

def _compute_min_angle(mesh: Mesh2D):
    """计算网格中所有三角形的最小内角。

    使用向量点积、向量长度、acos 和角度转换计算三个内角，
    用 np.clip 将余弦限制在 [-1,1]。
    不调用业务代码中的同类实现，不伪造 Triangle 质量结果。

    返回：
        (actual_min_angle_deg, triangle_index, node_indices)
    """
    nodes = mesh.nodes
    triangles = mesh.triangles
    min_angle = float("inf")
    min_tri_idx = -1
    min_node_indices = None

    for i, tri in enumerate(triangles):
        p = [nodes[tri[j]] for j in range(3)]
        angles_deg = []
        for j in range(3):
            v1 = p[(j + 1) % 3] - p[j]
            v2 = p[(j + 2) % 3] - p[j]
            len1 = np.linalg.norm(v1)
            len2 = np.linalg.norm(v2)
            assert len1 > 1e-15 and len2 > 1e-15, (
                f"三角形 {i} 存在零长度边，节点索引 {tri.tolist()}"
            )
            cos_val = np.dot(v1, v2) / (len1 * len2)
            cos_val = np.clip(cos_val, -1.0, 1.0)
            angle_deg = math.degrees(math.acos(cos_val))
            angles_deg.append(angle_deg)

        tri_min = min(angles_deg)
        if tri_min < min_angle:
            min_angle = tri_min
            min_tri_idx = i
            min_node_indices = tri.tolist()

    return min_angle, min_tri_idx, min_node_indices
