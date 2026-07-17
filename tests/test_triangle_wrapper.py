"""
tests/test_triangle_wrapper.py —— M2 Triangle Wrapper 验收测试

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布 M2 验收通过。
"""

import math
from unittest.mock import patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 导入路径来自实际业务源码侦察
# ---------------------------------------------------------------------------
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
    """构造最小合法 BoundaryConfig：逆时针单位正方形。

    顶点（0-based 索引）：
        0: (1.0, 0.0)
        1: (2.0, 0.0)
        2: (2.0, 1.0)
        3: (1.0, 1.0)
    线段：0→1, 1→2, 2→3, 3→0（闭合环）
    区域种子：(1.5, 0.5)，region_id=1
    """
    vertices = np.array([
        [1.0, 0.0],
        [2.0, 0.0],
        [2.0, 1.0],
        [1.0, 1.0],
    ], dtype=np.float64)

    segments = np.array([
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
    ], dtype=np.int32)

    segment_markers = np.array([1, 1, 1, 1], dtype=np.int32)

    # regions 格式：[R, Z, region_id, max_area_hint]
    regions = np.array([[1.5, 0.5, 1.0, -1.0]], dtype=np.float64)

    return BoundaryConfig(
        vertices=vertices,
        segments=segments,
        segment_markers=segment_markers,
        regions=regions,
        min_angle=min_angle,
        max_area=max_area,
    )


def _make_minimal_mesh2d(n_nodes=6, n_tria=4, n_seg=4) -> Mesh2D:
    """构造受控合成 Mesh2D，用于 mock 输出验证。"""
    nodes = np.array([
        [1.0, 0.0],
        [2.0, 0.0],
        [2.0, 1.0],
        [1.0, 1.0],
        [1.5, 0.3],
        [1.5, 0.7],
    ], dtype=np.float64)

    triangles = np.array([
        [0, 1, 4],
        [1, 2, 5],
        [2, 3, 5],
        [3, 0, 4],
    ], dtype=np.int32)

    region_ids = np.array([1, 1, 1, 1], dtype=np.int32)

    boundary_segments = np.array([
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
    ], dtype=np.int32)

    boundary_markers = np.array([1, 1, 1, 1], dtype=np.int32)

    node_markers = np.array([1, 1, 1, 1, 0, 0], dtype=np.int32)

    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=boundary_segments,
        boundary_markers=boundary_markers,
        node_markers=node_markers,
    )


# ---------------------------------------------------------------------------
# 测试辅助：构造受控 Triangle 输出字典
# ---------------------------------------------------------------------------

def _make_triangle_output(mesh: Mesh2D) -> dict:
    """根据 Mesh2D 构造 Triangle beta 字典（0-based 索引）。"""
    return {
        "vertices": mesh.nodes.copy(),
        "triangles": mesh.triangles.copy(),
        "triangle_attributes": mesh.region_ids.reshape(-1, 1).astype(np.float64),
        "segments": mesh.boundary_segments.copy(),
        "segment_markers": mesh.boundary_markers.reshape(-1, 1).copy(),
        "vertex_markers": mesh.node_markers.reshape(-1, 1).copy(),
    }


# ---------------------------------------------------------------------------
# M2-1：Triangle alpha/beta 契约映射测试（mock）
# ---------------------------------------------------------------------------

class TestTriangleContractMock:
    """M2 契约映射：mock triangle.triangulate，验证输入输出字典契约。"""

    def _run_with_mock(self, config: BoundaryConfig, fake_mesh: Mesh2D):
        """执行 generate_mesh，捕获 Triangle 调用参数。"""
        captured = {}

        def fake_triangulate(alpha, opts):
            captured["alpha"] = alpha
            captured["opts"] = opts
            return _make_triangle_output(fake_mesh)

        with patch(
            "linkmesh.mesher.triangle_wrapper.tr.triangulate",
            side_effect=fake_triangulate,
        ):
            result = generate_mesh(config)

        return result, captured

    # --- 输入字典验证 ---

    def test_alpha_contains_vertices(self, tmp_path):
        """alpha 字典包含 vertices 键。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "vertices" in captured["alpha"]

    def test_alpha_contains_segments(self, tmp_path):
        """alpha 字典包含 segments 键。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "segments" in captured["alpha"]

    def test_alpha_contains_regions(self, tmp_path):
        """alpha 字典包含 regions 键。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "regions" in captured["alpha"]

    def test_alpha_vertices_match_config(self):
        """alpha['vertices'] 内容与 BoundaryConfig.vertices 对应。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_almost_equal(
            captured["alpha"]["vertices"], config.vertices
        )

    def test_alpha_segments_match_config(self):
        """alpha['segments'] 内容与 BoundaryConfig.segments 对应。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(
            captured["alpha"]["segments"], config.segments
        )

    def test_alpha_region_id_preserved(self):
        """alpha['regions'] 中的区域编号保持物理值（不偏置）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        region_ids_in_alpha = captured["alpha"]["regions"][:, 2]
        expected_ids = config.regions[:, 2]
        np.testing.assert_array_almost_equal(region_ids_in_alpha, expected_ids)

    # --- 选项字符串语义验证 ---

    def test_opts_contains_p_for_plc(self):
        """选项字符串包含 'p'（PLC/segments 模式）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "p" in captured["opts"], (
            f"选项字符串缺少 'p'：{captured['opts']}"
        )

    def test_opts_contains_A_for_region_attributes(self):
        """选项字符串包含 'A'（输出区域属性）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "A" in captured["opts"], (
            f"选项字符串缺少 'A'：{captured['opts']}"
        )

    def test_opts_contains_z_for_zero_based(self):
        """选项字符串包含 'z'（0-based 索引）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "z" in captured["opts"], (
            f"选项字符串缺少 'z'：{captured['opts']}"
        )

    def test_opts_contains_q_for_quality(self):
        """选项字符串包含 'q'（质量约束）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "q" in captured["opts"], (
            f"选项字符串缺少 'q'：{captured['opts']}"
        )

    def test_opts_contains_min_angle_value(self):
        """选项字符串包含 min_angle 数值。"""
        config = _make_minimal_boundary_config(min_angle=20.0)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "20.0" in captured["opts"], (
            f"选项字符串未包含 min_angle=20.0：{captured['opts']}"
        )

    def test_opts_contains_a_when_max_area_set(self):
        """max_area 不为 None 时，选项字符串包含 'a'（面积约束）。"""
        config = _make_minimal_boundary_config(max_area=0.1)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert "a" in captured["opts"], (
            f"max_area 设置时选项字符串缺少 'a'：{captured['opts']}"
        )

    def test_opts_no_a_when_max_area_none(self):
        """max_area 为 None 时，选项字符串不包含面积约束数值。"""
        config = _make_minimal_boundary_config(max_area=None)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        # 不应包含 'a' 后跟数字的面积约束
        import re
        assert not re.search(r"a\d", captured["opts"]), (
            f"max_area=None 时选项字符串不应含面积约束：{captured['opts']}"
        )

    # --- 输出 Mesh2D 验证 ---

    def test_returns_mesh2d(self):
        """generate_mesh 返回 Mesh2D 实例。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert isinstance(result, Mesh2D)

    def test_nodes_shape(self):
        """nodes.shape == (N, 2)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.nodes.ndim == 2
        assert result.nodes.shape[1] == 2

    def test_triangles_shape(self):
        """triangles.shape == (T, 3)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.triangles.ndim == 2
        assert result.triangles.shape[1] == 3

    def test_region_ids_shape(self):
        """region_ids.shape == (T,)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.region_ids.ndim == 1
        assert len(result.region_ids) == result.n_triangles

    def test_boundary_segments_shape(self):
        """boundary_segments.shape == (S, 2)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        if result.n_boundary_segments > 0:
            assert result.boundary_segments.ndim == 2
            assert result.boundary_segments.shape[1] == 2

    def test_boundary_markers_shape(self):
        """boundary_markers.shape == (S,)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.boundary_markers.ndim == 1
        assert len(result.boundary_markers) == result.n_boundary_segments

    def test_node_markers_shape(self):
        """node_markers.shape == (N,)。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.node_markers.ndim == 1
        assert len(result.node_markers) == result.n_nodes

    def test_nodes_dtype_float64(self):
        """nodes dtype 为 float64。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.nodes.dtype == np.float64

    def test_triangles_dtype_int32(self):
        """triangles dtype 为 int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.triangles.dtype == np.int32

    def test_region_ids_dtype_int32(self):
        """region_ids dtype 为 int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.region_ids.dtype == np.int32

    def test_triangles_zero_based(self):
        """三角形索引为 0-based（最小值 >= 0）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        assert result.triangles.min() >= 0, (
            f"三角形索引出现负值：{result.triangles.min()}"
        )

    def test_triangles_indices_valid(self):
        """所有三角形索引满足 0 <= index < N。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        n = result.n_nodes
        assert result.triangles.max() < n, (
            f"三角形索引超出节点范围：max={result.triangles.max()}, N={n}"
        )

    def test_region_ids_not_offset(self):
        """region_ids 保持物理编号，不执行索引式 +1 偏置。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        # 输入 region_id=1，输出应仍为 1，不应变成 2
        expected = fake_mesh.region_ids
        np.testing.assert_array_equal(result.region_ids, expected)

    def test_boundary_markers_preserved(self):
        """边界标记保持蓝图约定值（1=LCFS）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        if result.n_boundary_segments > 0:
            # 所有边界标记应在蓝图允许范围内
            valid_markers = {0, 1, 2, 3}
            actual_markers = set(result.boundary_markers.tolist())
            assert actual_markers.issubset(valid_markers), (
                f"边界标记超出蓝图范围：{actual_markers}"
            )


# ---------------------------------------------------------------------------
# M2-2：真实 Triangle 最小集成测试（本轮严禁执行）
# ---------------------------------------------------------------------------

class TestTriangleRealIntegration:
    """M2 真实 Triangle 集成测试。

    本类测试不 mock triangle.triangulate，调用真实 generate_mesh。
    本轮严禁执行，供主管在 Linux 服务器手动运行。
    """

    def _make_convex_config(self) -> BoundaryConfig:
        """构造无尖锐角的凸域 BoundaryConfig（正六边形近似）。"""
        n = 6
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        r = 1.0 + np.cos(angles)  # 中心在 (1,0)，半径 1
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
        """真实 Triangle 调用返回合法 Mesh2D。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)

        assert isinstance(mesh, Mesh2D)
        assert mesh.n_nodes > 0
        assert mesh.n_triangles > 0

    def test_real_triangle_nodes_finite(self):
        """所有节点坐标有限。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert np.all(np.isfinite(mesh.nodes))

    def test_real_triangle_indices_zero_based_valid(self):
        """所有三角形索引合法且为 0-based。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert mesh.triangles.min() >= 0
        assert mesh.triangles.max() < mesh.n_nodes

    def test_real_triangle_no_degenerate_triangles(self):
        """每个三角形的三个顶点索引互不相同（无退化单元）。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        for i, tri in enumerate(mesh.triangles):
            assert len(set(tri.tolist())) == 3, (
                f"三角形 {i} 存在重复顶点索引：{tri}"
            )

    def test_real_triangle_positive_area(self):
        """每个三角形面积严格大于 1e-12。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        nodes = mesh.nodes
        for i, tri in enumerate(mesh.triangles):
            p0, p1, p2 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
            area = abs(
                (p1[0] - p0[0]) * (p2[1] - p0[1])
                - (p2[0] - p0[0]) * (p1[1] - p0[1])
            ) / 2.0
            assert area > 1e-12, (
                f"三角形 {i} 面积过小：{area}"
            )

    def test_real_triangle_region_ids_valid(self):
        """region_ids 只包含蓝图允许的 {1, 2, 3}。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        valid = {1, 2, 3}
        actual = set(mesh.region_ids.tolist())
        assert actual.issubset(valid), (
            f"region_ids 包含非法值：{actual - valid}"
        )

    def test_real_triangle_single_region_is_1(self):
        """单区域样例的 region_ids 集合预期为 {{1}}。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        actual = set(mesh.region_ids.tolist())
        assert actual == {1}, (
            f"单区域样例 region_ids 应为 {{1}}，实际为 {actual}"
        )

    def test_real_triangle_boundary_consistency(self):
        """边界线段数与边界标记数一致。"""
        config = self._make_convex_config()
        mesh = generate_mesh(config)
        assert mesh.n_boundary_segments == len(mesh.boundary_markers)

    def test_real_triangle_min_angle(self):
        """实际最小内角满足 min_angle - 0.01° 容差。"""
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
# M2-3：最小内角计算辅助函数
# ---------------------------------------------------------------------------

def _compute_min_angle(mesh: Mesh2D):
    """计算网格中所有三角形的最小内角。

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
            # 以顶点 j 为顶点，计算夹角
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
