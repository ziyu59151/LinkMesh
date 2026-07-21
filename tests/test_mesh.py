"""
tests/test_mesh.py —— M2.5 Mesh2D 独立数据模型验收测试。

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
    8. 显式传入兼容数组时旧构造方式仍可用。

v1.12 历史 Python Triangle 路径删除说明：
    旧 Wrapper（linkmesh.mesher.triangle_wrapper）已删除，其重导出身份断言
    随之移除。Mesh2D 唯一正式定义位于 linkmesh.mesh，唯一导入路径为
    `from linkmesh.mesh import Mesh2D`。

最终真实回归在 Linux 服务器执行，本文件仅静态编辑，不宣称已通过。
"""

from __future__ import annotations

import numpy as np


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
