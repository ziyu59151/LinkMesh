"""
tests/test_triangle_wrapper.py —— M2 Triangle Wrapper 验收测试

本文件包含两类测试：
    1. 受控 mock 契约测试（TestTriangleContractMock）：
       使用 mock 替换 triangle.triangulate，验证 alpha/beta 字典契约和 Mesh2D 字段映射。
       可在任何环境中运行。
    2. 真实 Triangle 集成测试（TestTriangleRealIntegration）：
       不 mock triangle.triangulate，调用真实 generate_mesh。
       需要 User 人工审查后在 Linux 服务器上运行，本轮 Aider 编辑期间未执行。

注意：本文件的编辑完成不等同于 M2 验收通过。M2 验收需要 User 在服务器上
实际运行测试并确认结果，详见 LinkMesh_Architecture_Plan.md 第 12 节。
"""

import math
import re
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


def _make_minimal_mesh2d() -> Mesh2D:
    """构造受控合成 Mesh2D，用于 mock 输出验证。

    使用可区分的边界标记（1, 2, 3）和节点标记（0, 1, 2）以便检测
    清零、偏置、错序或读取错误字段等问题。
    区域编号使用蓝图允许的物理值（1=plasma）。
    """
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

    # 使用可区分的边界标记值（1=LCFS, 2=first_wall, 3=outer_boundary）
    boundary_markers = np.array([1, 2, 3, 1], dtype=np.int32)

    # 使用可区分的节点标记值（0=内部, 1/2=边界）
    node_markers = np.array([1, 2, 1, 2, 0, 0], dtype=np.int32)

    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=boundary_segments,
        boundary_markers=boundary_markers,
        node_markers=node_markers,
    )


# ---------------------------------------------------------------------------
# 测试辅助：构造受控 Triangle 输出字典（beta）
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# M2-1：Triangle alpha/beta 契约映射测试（mock）
# ---------------------------------------------------------------------------

class TestTriangleContractMock:
    """M2 契约映射：mock triangle.triangulate，验证输入输出字典契约。

    mock 目标为 triangle.triangulate，因为 generate_mesh() 内部使用
    局部 import（import triangle as tr），tr 不是模块属性。
    """

    def _run_with_mock(self, config: BoundaryConfig, fake_mesh: Mesh2D):
        """执行 generate_mesh，捕获 Triangle 调用参数。"""
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
        """alpha 字典包含正式契约规定的四个字段。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha = captured["alpha"]
        for key in ("vertices", "segments", "segment_markers", "regions"):
            assert key in alpha, f"alpha 字典缺少字段：{key}"

    def test_alpha_vertices_content_and_dtype(self):
        """alpha['vertices'] 内容等于 BoundaryConfig.vertices，dtype=float64。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_v = captured["alpha"]["vertices"]
        np.testing.assert_array_almost_equal(alpha_v, config.vertices)
        assert alpha_v.dtype == np.float64, f"vertices dtype 应为 float64，实际为 {alpha_v.dtype}"
        assert alpha_v.shape == (4, 2), f"vertices shape 应为 (4,2)，实际为 {alpha_v.shape}"

    def test_alpha_segments_content_and_dtype(self):
        """alpha['segments'] 内容等于 BoundaryConfig.segments，dtype=int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_s = captured["alpha"]["segments"]
        np.testing.assert_array_equal(alpha_s, config.segments)
        assert alpha_s.dtype == np.int32, f"segments dtype 应为 int32，实际为 {alpha_s.dtype}"
        assert alpha_s.shape == (4, 2), f"segments shape 应为 (4,2)，实际为 {alpha_s.shape}"

    def test_alpha_segment_markers_content_and_dtype(self):
        """alpha['segment_markers'] 内容等于 BoundaryConfig.segment_markers，dtype=int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_sm = captured["alpha"]["segment_markers"]
        np.testing.assert_array_equal(alpha_sm, config.segment_markers)
        assert alpha_sm.dtype == np.int32, f"segment_markers dtype 应为 int32，实际为 {alpha_sm.dtype}"
        assert alpha_sm.shape == (4,), f"segment_markers shape 应为 (4,)，实际为 {alpha_sm.shape}"

    def test_alpha_regions_content_and_dtype(self):
        """alpha['regions'] 内容等于 BoundaryConfig.regions，dtype=float64。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        alpha_r = captured["alpha"]["regions"]
        np.testing.assert_array_almost_equal(alpha_r, config.regions)
        assert alpha_r.dtype == np.float64, f"regions dtype 应为 float64，实际为 {alpha_r.dtype}"
        assert alpha_r.shape == (1, 4), f"regions shape 应为 (1,4)，实际为 {alpha_r.shape}"

    def test_alpha_region_id_not_offset(self):
        """alpha['regions'] 中的 region_id（第3列）保持物理值，未执行 +1 偏置。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        region_ids_in_alpha = captured["alpha"]["regions"][:, 2]
        expected_ids = config.regions[:, 2]
        np.testing.assert_array_almost_equal(
            region_ids_in_alpha, expected_ids,
            err_msg=f"region_id 被偏置：期望 {expected_ids}，实际 {region_ids_in_alpha}"
        )

    # --- Triangle 选项字符串精确验证 ---

    def test_opts_exact_without_max_area(self):
        """max_area=None 时，选项字符串精确为 'pq20.0AzQ'。"""
        config = _make_minimal_boundary_config(min_angle=20.0, max_area=None)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert captured["opts"] == "pq20.0AzQ", (
            f"选项字符串不符合预期：期望 'pq20.0AzQ'，实际 '{captured['opts']}'"
        )

    def test_opts_exact_with_max_area(self):
        """max_area=0.1 时，选项字符串精确为 'pq20.0a0.1AzQ'。"""
        config = _make_minimal_boundary_config(min_angle=20.0, max_area=0.1)
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        assert captured["opts"] == "pq20.0a0.1AzQ", (
            f"选项字符串不符合预期：期望 'pq20.0a0.1AzQ'，实际 '{captured['opts']}'"
        )

    def test_opts_uppercase_A_always_present(self):
        """大写 'A'（输出区域属性）始终存在于选项字符串中。"""
        for max_area in (None, 0.05):
            config = _make_minimal_boundary_config(max_area=max_area)
            fake_mesh = _make_minimal_mesh2d()
            _, captured = self._run_with_mock(config, fake_mesh)
            assert "A" in captured["opts"], (
                f"选项字符串缺少大写 'A'：{captured['opts']}"
            )

    def test_opts_lowercase_a_only_when_max_area_set(self):
        """小写 'a'（面积约束）仅在 max_area 不为 None 时出现。"""
        # max_area=None：不应含小写 a 后跟数字
        config_none = _make_minimal_boundary_config(max_area=None)
        fake_mesh = _make_minimal_mesh2d()
        _, captured_none = self._run_with_mock(config_none, fake_mesh)
        assert not re.search(r"a\d", captured_none["opts"]), (
            f"max_area=None 时选项字符串不应含面积约束：{captured_none['opts']}"
        )

        # max_area=0.05：应含小写 a 后跟数字
        config_set = _make_minimal_boundary_config(max_area=0.05)
        _, captured_set = self._run_with_mock(config_set, fake_mesh)
        assert re.search(r"a\d", captured_set["opts"]), (
            f"max_area=0.05 时选项字符串应含面积约束：{captured_set['opts']}"
        )

    def test_opts_contains_p_q_z_Q(self):
        """选项字符串始终包含 p、q、z、Q。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        _, captured = self._run_with_mock(config, fake_mesh)
        opts = captured["opts"]
        for ch in ("p", "q", "z", "Q"):
            assert ch in opts, f"选项字符串缺少 '{ch}'：{opts}"

    # --- beta 六字段精确映射验证 ---

    def test_nodes_exact_content_and_shape_dtype(self):
        """result.nodes 精确等于 beta['vertices']，shape=(N,2)，dtype=float64。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.nodes, fake_mesh.nodes)
        assert result.nodes.shape == (6, 2), f"nodes shape 错误：{result.nodes.shape}"
        assert result.nodes.dtype == np.float64

    def test_triangles_exact_content_and_shape_dtype(self):
        """result.triangles 精确等于 beta['triangles']，shape=(T,3)，dtype=int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.triangles, fake_mesh.triangles)
        assert result.triangles.shape == (4, 3), f"triangles shape 错误：{result.triangles.shape}"
        assert result.triangles.dtype == np.int32

    def test_region_ids_exact_content_and_shape_dtype(self):
        """result.region_ids 精确等于 beta['triangle_attributes'] 规范化后的一维内容。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.region_ids, fake_mesh.region_ids)
        assert result.region_ids.shape == (4,), f"region_ids shape 错误：{result.region_ids.shape}"
        assert result.region_ids.dtype == np.int32

    def test_boundary_segments_exact_content_and_shape_dtype(self):
        """result.boundary_segments 精确等于 beta['segments']，shape=(S,2)，dtype=int32。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(result.boundary_segments, fake_mesh.boundary_segments)
        assert result.boundary_segments.shape == (4, 2), (
            f"boundary_segments shape 错误：{result.boundary_segments.shape}"
        )
        assert result.boundary_segments.dtype == np.int32

    def test_boundary_markers_exact_content_and_shape_dtype(self):
        """result.boundary_markers 精确等于 beta['segment_markers'] 规范化后的一维内容。

        使用可区分标记值 [1, 2, 3, 1]，验证未清零、未偏置、未改写。
        """
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(
            result.boundary_markers, fake_mesh.boundary_markers,
            err_msg=(
                f"boundary_markers 内容不匹配：\n"
                f"  期望 {fake_mesh.boundary_markers}\n"
                f"  实际 {result.boundary_markers}"
            )
        )
        assert result.boundary_markers.shape == (4,), (
            f"boundary_markers shape 错误：{result.boundary_markers.shape}"
        )
        assert result.boundary_markers.dtype == np.int32

    def test_node_markers_exact_content_and_shape_dtype(self):
        """result.node_markers 精确等于 beta['vertex_markers'] 规范化后的一维内容。

        使用可区分标记值 [1, 2, 1, 2, 0, 0]，验证未清零、未偏置、未改写。
        """
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(
            result.node_markers, fake_mesh.node_markers,
            err_msg=(
                f"node_markers 内容不匹配：\n"
                f"  期望 {fake_mesh.node_markers}\n"
                f"  实际 {result.node_markers}"
            )
        )
        assert result.node_markers.shape == (6,), (
            f"node_markers shape 错误：{result.node_markers.shape}"
        )
        assert result.node_markers.dtype == np.int32

    # --- 索引合法性验证 ---

    def test_triangles_zero_based_and_valid_range(self):
        """所有三角形索引满足 0 <= index < n_nodes（0-based，未提前 +1）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        n = result.n_nodes
        assert result.triangles.min() >= 0, (
            f"三角形索引出现负值：{result.triangles.min()}"
        )
        assert result.triangles.max() < n, (
            f"三角形索引超出节点范围：max={result.triangles.max()}, N={n}"
        )

    def test_boundary_segments_zero_based_and_valid_range(self):
        """所有边界线段端点索引满足 0 <= index < n_nodes（0-based，未提前 +1）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        n = result.n_nodes
        assert result.boundary_segments.min() >= 0, (
            f"边界线段索引出现负值：{result.boundary_segments.min()}"
        )
        assert result.boundary_segments.max() < n, (
            f"边界线段索引超出节点范围：max={result.boundary_segments.max()}, N={n}"
        )

    def test_triangles_not_offset_by_one(self):
        """验证 Wrapper 未对 triangles 提前执行 +1（与受控 beta 精确比较）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(
            result.triangles, fake_mesh.triangles,
            err_msg="triangles 与受控 beta 不一致，可能被提前 +1 偏置"
        )

    def test_region_ids_not_offset(self):
        """region_ids 保持物理编号（1=plasma），未执行索引式 +1 偏置。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        np.testing.assert_array_equal(
            result.region_ids, fake_mesh.region_ids,
            err_msg=(
                f"region_ids 被偏置：期望 {fake_mesh.region_ids}，实际 {result.region_ids}"
            )
        )

    def test_boundary_markers_valid_range(self):
        """边界标记取值在蓝图允许范围 {0,1,2,3} 内（补充值域测试，不替代精确映射测试）。"""
        config = _make_minimal_boundary_config()
        fake_mesh = _make_minimal_mesh2d()
        result, _ = self._run_with_mock(config, fake_mesh)
        valid_markers = {0, 1, 2, 3}
        actual_markers = set(result.boundary_markers.tolist())
        assert actual_markers.issubset(valid_markers), (
            f"边界标记超出蓝图范围：{actual_markers - valid_markers}"
        )

    # --- 单元素 shape 测试（验证 reshape(-1) 替代 squeeze() 的正确性）---

    def test_single_triangle_region_ids_shape_is_1d(self):
        """triangle_attributes.shape==(1,1) 时，result.region_ids.shape 必须为 (1,)。

        这是 shape 契约样例，不用于证明合成网格的物理合法性。
        """
        # 构造最小受控 beta：1个节点（实际不合法，但足以走完字段映射）
        # 使用 3 个节点 1 个三角形的最小几何
        minimal_nodes = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64)
        minimal_triangles = np.array([[0, 1, 2]], dtype=np.int32)
        minimal_region_attrs = np.array([[1.0]], dtype=np.float64)  # shape=(1,1)
        minimal_seg = np.zeros((0, 2), dtype=np.int32)
        minimal_seg_markers = np.zeros((0, 1), dtype=np.int32)
        minimal_vtx_markers = np.zeros((3, 1), dtype=np.int32)

        single_beta = {
            "vertices": minimal_nodes,
            "triangles": minimal_triangles,
            "triangle_attributes": minimal_region_attrs,
            "segments": minimal_seg,
            "segment_markers": minimal_seg_markers,
            "vertex_markers": minimal_vtx_markers,
        }

        config = _make_minimal_boundary_config()

        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)

        assert result.region_ids.ndim == 1, (
            f"region_ids 应为一维数组，实际 ndim={result.region_ids.ndim}"
        )
        assert result.region_ids.shape == (1,), (
            f"region_ids.shape 应为 (1,)，实际为 {result.region_ids.shape}"
        )
        assert result.region_ids[0] == 1

    def test_single_segment_boundary_markers_shape_is_1d(self):
        """segment_markers 只有一个元素时，result.boundary_markers.shape 必须为 (1,)。

        这是 shape 契约样例，不用于证明合成网格的物理合法性。
        """
        minimal_nodes = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64)
        minimal_triangles = np.array([[0, 1, 2]], dtype=np.int32)
        minimal_region_attrs = np.array([[1.0]], dtype=np.float64)
        minimal_seg = np.array([[0, 1]], dtype=np.int32)          # 1 条线段
        minimal_seg_markers = np.array([[2]], dtype=np.int32)     # shape=(1,1)
        minimal_vtx_markers = np.zeros((3, 1), dtype=np.int32)

        single_beta = {
            "vertices": minimal_nodes,
            "triangles": minimal_triangles,
            "triangle_attributes": minimal_region_attrs,
            "segments": minimal_seg,
            "segment_markers": minimal_seg_markers,
            "vertex_markers": minimal_vtx_markers,
        }

        config = _make_minimal_boundary_config()

        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)

        assert result.boundary_markers.ndim == 1, (
            f"boundary_markers 应为一维数组，实际 ndim={result.boundary_markers.ndim}"
        )
        assert result.boundary_markers.shape == (1,), (
            f"boundary_markers.shape 应为 (1,)，实际为 {result.boundary_markers.shape}"
        )
        assert result.boundary_markers[0] == 2

    def test_single_node_marker_shape_is_1d(self):
        """vertex_markers 只有一个元素时，result.node_markers.shape 必须为 (1,)。

        这是 shape 契约样例，不用于证明合成网格的物理合法性。
        使用 1 个节点的极端情况（几何上不合法，但足以验证 shape 规范化）。
        """
        # 构造 1 个节点的极端 beta（仅用于 shape 验证）
        single_node = np.array([[1.0, 0.0]], dtype=np.float64)
        # triangles 为空会触发 ValueError，所以给一个假三角形
        # 但 vertex_markers 只有 1 个元素
        # 为避免触发空检查，给 triangles 一个非空值
        fake_triangles = np.array([[0, 0, 0]], dtype=np.int32)
        fake_region_attrs = np.array([[1.0]], dtype=np.float64)
        fake_vtx_markers = np.array([[1]], dtype=np.int32)  # shape=(1,1)

        single_beta = {
            "vertices": single_node,
            "triangles": fake_triangles,
            "triangle_attributes": fake_region_attrs,
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": fake_vtx_markers,
        }

        config = _make_minimal_boundary_config()

        with patch("triangle.triangulate", return_value=single_beta):
            result = generate_mesh(config)

        assert result.node_markers.ndim == 1, (
            f"node_markers 应为一维数组，实际 ndim={result.node_markers.ndim}"
        )
        assert result.node_markers.shape == (1,), (
            f"node_markers.shape 应为 (1,)，实际为 {result.node_markers.shape}"
        )
        assert result.node_markers[0] == 1

    # --- 空输出异常测试 ---

    def test_empty_vertices_raises_value_error(self):
        """beta['vertices'] 为空时，Wrapper 抛出 ValueError，消息含'节点数为 0'。"""
        empty_vertices_beta = {
            "vertices": np.zeros((0, 2), dtype=np.float64),
            "triangles": np.zeros((0, 3), dtype=np.int32),
            "triangle_attributes": np.zeros((0, 1), dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((0, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()

        with patch("triangle.triangulate", return_value=empty_vertices_beta):
            with pytest.raises(ValueError, match="节点数为 0"):
                generate_mesh(config)

    def test_empty_triangles_raises_value_error(self):
        """beta['vertices'] 非空但 beta['triangles'] 为空时，Wrapper 抛出 ValueError，消息含'三角形数为 0'。"""
        empty_triangles_beta = {
            "vertices": np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            "triangles": np.zeros((0, 3), dtype=np.int32),
            "triangle_attributes": np.zeros((0, 1), dtype=np.float64),
            "segments": np.zeros((0, 2), dtype=np.int32),
            "segment_markers": np.zeros((0, 1), dtype=np.int32),
            "vertex_markers": np.zeros((3, 1), dtype=np.int32),
        }
        config = _make_minimal_boundary_config()

        with patch("triangle.triangulate", return_value=empty_triangles_beta):
            with pytest.raises(ValueError, match="三角形数为 0"):
                generate_mesh(config)


# ---------------------------------------------------------------------------
# M2-2：真实 Triangle 最小集成测试
# ---------------------------------------------------------------------------

class TestTriangleRealIntegration:
    """M2 真实 Triangle 集成测试。

    本类测试不 mock triangle.triangulate，调用真实 generate_mesh。
    需要 User 人工审查后在 Linux 服务器上运行，本轮 Aider 编辑期间未执行。
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
        """单区域样例的 region_ids 集合预期为 {1}。"""
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
