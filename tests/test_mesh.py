"""
tests/test_mesh.py —— M2.5 Mesh2D 独立数据模型验收测试（v2.0 扩充 outer_boundary）。

测试原则：
    - 只针对 linkmesh.mesh.Mesh2D 数据模型；
    - 不调用 OFT、Triangle、matplotlib、h5py；
    - 不写文件；
    - 不运行网格生成；
    - 使用小型 NumPy 数组。

覆盖：
    1. 从 linkmesh.mesh 导入 Mesh2D 成功；
    2. 仅提供 nodes/triangles/region_ids 可构造对象；
    3. 三个兼容字段自动得到正确空 shape 和 dtype；
    4. n_nodes / n_triangles / n_boundary_segments 返回正确值；
    5-7. 两个分别构造的实例不共享兼容默认数组；
    8. 显式传入兼容数组时旧构造方式仍可用；
    9. outer_boundary 默认 None（未提供）；
    10. 合法顺时针 outer_boundary 构造与 (B,2)/float64/数值不被意外修改；
    11. 末尾不重复首点；
    12. 逆时针被拒绝；少于 3 点被拒绝；非 (B,2) 被拒绝；NaN/Inf 被拒绝；
        相邻重复点被拒绝；首尾重复点被拒绝；零面积/共线被拒绝；
    13. 不同实例不共享 outer_boundary 数组。

v1.12 历史 Python Triangle 路径删除说明：
    旧 Wrapper（linkmesh.mesher.triangle_wrapper）已删除，其重导出身份断言
    随之移除。Mesh2D 唯一正式定义位于 linkmesh.mesh，唯一导入路径为
    `from linkmesh.mesh import Mesh2D`。

最终真实回归在 Linux 服务器执行，本文件仅静态编辑，不宣称已通过。
"""

from __future__ import annotations

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# 测试辅助：构造最小核心三数组                                                  #
# --------------------------------------------------------------------------- #

def _core_arrays():
    """构造最小核心三数组：4 节点、2 三角形（单位正方形）。"""
    nodes = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ], dtype=np.float64)
    triangles = np.array([
        [0, 1, 2],
        [0, 2, 3],
    ], dtype=np.int32)
    region_ids = np.array([1, 2], dtype=np.int32)
    return nodes, triangles, region_ids


def _cw_boundary():
    """构造合法顺时针、隐式闭合（末尾不重复首点）的 (4,2) outer boundary。

    顺时针顺序（R 向右、Z 向上）：
        (0,0) → (0,1) → (1,1) → (1,0)
    带符号闭合面积为负（顺时针）。
    """
    return np.array([
        [0.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
    ], dtype=np.float64)


def _ccw_boundary():
    """构造逆时针（带符号面积为正）的 (4,2) 轮廓，用于拒绝测试。"""
    return np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ], dtype=np.float64)


# --------------------------------------------------------------------------- #
# 1. 导入成功                                                                   #
# --------------------------------------------------------------------------- #

class TestMeshImport:
    def test_import_from_linkmesh_mesh(self):
        from linkmesh.mesh import Mesh2D
        assert Mesh2D is not None


# --------------------------------------------------------------------------- #
# 2-3. 核心构造与兼容字段默认值                                                 #
# --------------------------------------------------------------------------- #

class TestMeshCoreConstruction:
    def test_construct_with_core_arrays_only(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.nodes is nodes
        assert mesh.triangles is triangles
        assert mesh.region_ids is region_ids

    def test_default_boundary_segments_empty_shape_dtype(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.boundary_segments.shape == (0, 2)
        assert mesh.boundary_segments.dtype == np.int32

    def test_default_boundary_markers_empty_shape_dtype(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.boundary_markers.shape == (0,)
        assert mesh.boundary_markers.dtype == np.int32

    def test_default_node_markers_empty_shape_dtype(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.node_markers.shape == (0,)
        assert mesh.node_markers.dtype == np.int32


# --------------------------------------------------------------------------- #
# 4. 只读统计属性                                                               #
# --------------------------------------------------------------------------- #

class TestMeshStatProperties:
    def test_n_nodes(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.n_nodes == 4

    def test_n_triangles(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.n_triangles == 2

    def test_n_boundary_segments_default_zero(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.n_boundary_segments == 0

    def test_n_boundary_segments_with_explicit_segments(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        segs = np.array([[0, 1], [1, 2], [2, 3]], dtype=np.int32)
        mesh = Mesh2D(
            nodes=nodes,
            triangles=triangles,
            region_ids=region_ids,
            boundary_segments=segs,
        )
        assert mesh.n_boundary_segments == 3


# --------------------------------------------------------------------------- #
# 5-7. 兼容默认数组不共享（每个实例独立）                                       #
# --------------------------------------------------------------------------- #

class TestMeshDefaultArraysNotShared:
    def test_boundary_segments_not_shared(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        m1 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        m2 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert m1.boundary_segments is not m2.boundary_segments

    def test_boundary_markers_not_shared(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        m1 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        m2 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert m1.boundary_markers is not m2.boundary_markers

    def test_node_markers_not_shared(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        m1 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        m2 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert m1.node_markers is not m2.node_markers


# --------------------------------------------------------------------------- #
# 8. 显式传入兼容数组的旧构造方式仍可用                                          #
# --------------------------------------------------------------------------- #

class TestMeshExplicitCompatConstruction:
    def test_explicit_six_field_construction(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        boundary_segments = np.array([[0, 1], [1, 2]], dtype=np.int32)
        boundary_markers = np.array([1, 2], dtype=np.int32)
        node_markers = np.array([1, 1, 0, 0], dtype=np.int32)
        mesh = Mesh2D(
            nodes=nodes,
            triangles=triangles,
            region_ids=region_ids,
            boundary_segments=boundary_segments,
            boundary_markers=boundary_markers,
            node_markers=node_markers,
        )
        assert mesh.boundary_segments is boundary_segments
        assert mesh.boundary_markers is boundary_markers
        assert mesh.node_markers is node_markers
        assert mesh.n_boundary_segments == 2


# --------------------------------------------------------------------------- #
# 9. outer_boundary 默认与合法构造                                              #
# --------------------------------------------------------------------------- #

class TestMeshOuterBoundaryDefaultAndValid:
    def test_outer_boundary_default_none(self):
        """不提供 outer_boundary 时默认 None（未提供，不作为合法几何）。"""
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        mesh = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        assert mesh.outer_boundary is None

    def test_valid_clockwise_boundary_accepted(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        ob = _cw_boundary()
        mesh = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=ob,
        )
        assert mesh.outer_boundary is not None
        assert mesh.outer_boundary.ndim == 2
        assert mesh.outer_boundary.shape == (4, 2)

    def test_outer_boundary_dtype_float64(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        # 传入整数轮廓，构造后应规范化为 float64
        ob_int = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=np.int64)
        mesh = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=ob_int,
        )
        assert mesh.outer_boundary.dtype == np.float64

    def test_outer_boundary_values_preserved(self):
        """数值不被意外修改（顺序与坐标保持）。"""
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        ob = _cw_boundary()
        expected = ob.copy()
        mesh = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=ob,
        )
        np.testing.assert_array_equal(mesh.outer_boundary, expected)

    def test_outer_boundary_last_not_equal_first(self):
        """末尾不重复首点（合法输入本就不重复，验证保持）。"""
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        ob = _cw_boundary()
        mesh = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=ob,
        )
        assert not np.array_equal(
            mesh.outer_boundary[0], mesh.outer_boundary[-1]
        )


# --------------------------------------------------------------------------- #
# 10. outer_boundary 非法输入被拒绝                                             #
# --------------------------------------------------------------------------- #

class TestMeshOuterBoundaryRejections:
    def _construct(self, ob):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        return Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=ob,
        )

    def test_counterclockwise_rejected(self):
        with pytest.raises(ValueError, match="顺时针"):
            self._construct(_ccw_boundary())

    def test_fewer_than_three_points_rejected(self):
        ob = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float64)
        with pytest.raises(ValueError, match="3"):
            self._construct(ob)

    def test_not_bx2_rejected(self):
        ob = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]],
                      dtype=np.float64)
        with pytest.raises(ValueError, match=r"\(B,2\)"):
            self._construct(ob)

    def test_one_dimensional_rejected(self):
        ob = np.array([0.0, 1.0, 2.0], dtype=np.float64)
        with pytest.raises(ValueError, match="二维"):
            self._construct(ob)

    def test_nan_rejected(self):
        ob = _cw_boundary().copy()
        ob[1, 0] = np.nan
        with pytest.raises(ValueError, match="有限"):
            self._construct(ob)

    def test_inf_rejected(self):
        ob = _cw_boundary().copy()
        ob[2, 1] = np.inf
        with pytest.raises(ValueError, match="有限"):
            self._construct(ob)

    def test_adjacent_duplicate_point_rejected(self):
        # 在顺时针轮廓中插入相邻重复点（零长度边）
        ob = np.array([
            [0.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],  # 与上一点重复
            [1.0, 1.0],
            [1.0, 0.0],
        ], dtype=np.float64)
        with pytest.raises(ValueError, match="相邻重复点"):
            self._construct(ob)

    def test_first_last_duplicate_rejected(self):
        # 首尾重复（末尾复制首点）应被拒绝
        ob = np.array([
            [0.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [1.0, 0.0],
            [0.0, 0.0],  # 重复首点
        ], dtype=np.float64)
        with pytest.raises(ValueError, match="首点与末点相同"):
            self._construct(ob)

    def test_collinear_zero_area_rejected(self):
        # 三点共线，面积退化
        ob = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
        ], dtype=np.float64)
        with pytest.raises(ValueError, match="面积"):
            self._construct(ob)


# --------------------------------------------------------------------------- #
# 11. outer_boundary 不共享                                                     #
# --------------------------------------------------------------------------- #

class TestMeshOuterBoundaryNotShared:
    def test_two_instances_do_not_share_array(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        m1 = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=_cw_boundary(),
        )
        m2 = Mesh2D(
            nodes=nodes, triangles=triangles, region_ids=region_ids,
            outer_boundary=_cw_boundary(),
        )
        assert m1.outer_boundary is not m2.outer_boundary

    def test_default_none_instances_independent(self):
        from linkmesh.mesh import Mesh2D
        nodes, triangles, region_ids = _core_arrays()
        m1 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        m2 = Mesh2D(nodes=nodes, triangles=triangles, region_ids=region_ids)
        # 默认均为 None，互不影响
        assert m1.outer_boundary is None
        assert m2.outer_boundary is None
