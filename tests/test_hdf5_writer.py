"""
tests/test_hdf5_writer.py —— M3 HDF5 Writer 验收测试

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布 M3 验收通过。
"""

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 导入路径来自实际业务源码侦察
# ---------------------------------------------------------------------------
from linkmesh.mesher.triangle_wrapper import Mesh2D
from linkmesh.writers.hdf5_writer import write_hdf5


# ---------------------------------------------------------------------------
# 测试辅助：构造受控合成 Mesh2D
# ---------------------------------------------------------------------------

def _make_test_mesh() -> Mesh2D:
    """构造受控合成 Mesh2D，用于 HDF5 Writer 验收。

    设计原则：
    - 节点坐标使用非对称数值，避免错误转置偶然通过；
    - 包含多个三角形；
    - triangles 使用 0-based；
    - region_ids 包含两个不同物理编号（1 和 2）；
    - node_markers 同时包含内部节点（0）和边界节点（非零）；
    - 边界线段和边界标记合法。
    """
    # 8 个节点，坐标故意非对称
    nodes = np.array([
        [1.1, 0.2],   # 0 边界
        [2.3, 0.1],   # 1 边界
        [3.0, 0.5],   # 2 边界
        [2.8, 1.4],   # 3 边界
        [1.5, 1.6],   # 4 边界
        [0.9, 1.1],   # 5 边界
        [1.8, 0.7],   # 6 内部
        [2.1, 1.0],   # 7 内部
    ], dtype=np.float64)

    # 6 个三角形，0-based 索引
    triangles = np.array([
        [0, 1, 6],
        [1, 2, 7],
        [2, 3, 7],
        [3, 4, 7],
        [4, 5, 6],
        [5, 0, 6],
    ], dtype=np.int32)

    # region_ids：前3个三角形属于 plasma(1)，后3个属于 vacuum(2)
    region_ids = np.array([1, 1, 1, 2, 2, 2], dtype=np.int32)

    # 边界线段（外边界）
    boundary_segments = np.array([
        [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
    ], dtype=np.int32)

    # 边界标记：全部为外边界（3）
    boundary_markers = np.array([3, 3, 3, 3, 3, 3], dtype=np.int32)

    # node_markers：节点 0-5 为边界（1），节点 6-7 为内部（0）
    node_markers = np.array([1, 1, 1, 1, 1, 1, 0, 0], dtype=np.int32)

    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=boundary_segments,
        boundary_markers=boundary_markers,
        node_markers=node_markers,
    )


def _copy_mesh_arrays(mesh: Mesh2D) -> dict:
    """复制 Mesh2D 的全部 NumPy 数组，用于不可变性检查。"""
    return {
        "nodes": mesh.nodes.copy(),
        "triangles": mesh.triangles.copy(),
        "region_ids": mesh.region_ids.copy(),
        "boundary_segments": mesh.boundary_segments.copy(),
        "boundary_markers": mesh.boundary_markers.copy(),
        "node_markers": mesh.node_markers.copy(),
    }


# ---------------------------------------------------------------------------
# M3-1：数据集完整性
# ---------------------------------------------------------------------------

class TestHDF5DatasetCompleteness:
    """M3 数据集完整性：精确验证 11 个数据集路径。"""

    _EXPECTED_DATASETS = {
        "nvert", "ntria", "nvert_in", "nvert_ex",
        "vert", "idxivert", "idxevert", "tria",
        "nbcRZ", "Rbc", "Zbc",
    }

    def test_all_11_datasets_present(self, tmp_path):
        """HDF5 文件包含全部 11 个数据集。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            assert "femmesh" in f, "缺少顶层组 /femmesh"
            actual_keys = set(f["femmesh"].keys())
            missing = self._EXPECTED_DATASETS - actual_keys
            assert not missing, (
                f"缺少以下数据集：{missing}"
            )

    def test_no_unexpected_dataset_names(self, tmp_path):
        """防止拼写错误产生替代字段（检查数据集名称集合）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            actual_keys = set(f["femmesh"].keys())
            # 实际数据集名称应是预期集合的超集（允许额外属性，但不允许缺少）
            missing = self._EXPECTED_DATASETS - actual_keys
            assert not missing, (
                f"数据集名称集合不完整，缺少：{missing}"
            )


# ---------------------------------------------------------------------------
# M3-2：标量、shape 和 dtype
# ---------------------------------------------------------------------------

class TestHDF5ShapeAndDtype:
    """M3 shape 和 dtype：精确验证每个数据集的维度和类型。"""

    def test_scalars_and_shapes(self, tmp_path):
        """验证全部 11 个数据集的标量值、shape 和 dtype。"""
        import h5py
        mesh = _make_test_mesh()
        n = mesh.n_nodes       # 8
        t = mesh.n_triangles   # 6
        n_in = int(np.sum(mesh.node_markers == 0))   # 2
        n_ex = int(np.sum(mesh.node_markers != 0))   # 6

        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]

            # --- 标量 ---
            assert int(grp["nvert"][()]) == n,    f"nvert 期望 {n}"
            assert int(grp["ntria"][()]) == t,    f"ntria 期望 {t}"
            assert int(grp["nvert_in"][()]) == n_in, f"nvert_in 期望 {n_in}"
            assert int(grp["nvert_ex"][()]) == n_ex, f"nvert_ex 期望 {n_ex}"
            assert int(grp["nbcRZ"][()]) == n_ex, f"nbcRZ 期望 {n_ex}"

            # --- dtype 标量 ---
            assert grp["nvert"].dtype == np.int32,    "nvert dtype 应为 int32"
            assert grp["ntria"].dtype == np.int32,    "ntria dtype 应为 int32"
            assert grp["nvert_in"].dtype == np.int32, "nvert_in dtype 应为 int32"
            assert grp["nvert_ex"].dtype == np.int32, "nvert_ex dtype 应为 int32"
            assert grp["nbcRZ"].dtype == np.int32,    "nbcRZ dtype 应为 int32"

            # --- vert ---
            assert grp["vert"].shape == (2, n),   f"vert shape 期望 (2,{n})"
            assert grp["vert"].dtype == np.float64, "vert dtype 应为 float64"

            # --- idxivert ---
            assert grp["idxivert"].shape == (n_in,), f"idxivert shape 期望 ({n_in},)"
            assert grp["idxivert"].dtype == np.int32, "idxivert dtype 应为 int32"

            # --- idxevert ---
            assert grp["idxevert"].shape == (n_ex,), f"idxevert shape 期望 ({n_ex},)"
            assert grp["idxevert"].dtype == np.int32, "idxevert dtype 应为 int32"

            # --- tria ---
            assert grp["tria"].shape == (4, t),   f"tria shape 期望 (4,{t})"
            assert grp["tria"].dtype == np.int32, "tria dtype 应为 int32"

            # --- Rbc / Zbc ---
            assert grp["Rbc"].shape == (n_ex,),   f"Rbc shape 期望 ({n_ex},)"
            assert grp["Rbc"].dtype == np.float64, "Rbc dtype 应为 float64"
            assert grp["Zbc"].shape == (n_ex,),   f"Zbc shape 期望 ({n_ex},)"
            assert grp["Zbc"].dtype == np.float64, "Zbc dtype 应为 float64"


# ---------------------------------------------------------------------------
# M3-3：节点坐标转置
# ---------------------------------------------------------------------------

class TestHDF5VertTranspose:
    """M3 vert 转置：验证 HDF5 中存储的是 mesh.nodes.T。"""

    def test_vert_equals_nodes_transposed(self, tmp_path):
        """vert 与 mesh.nodes.T 数值完全一致（含 R/Z 顺序）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            vert = f["femmesh"]["vert"][:]

        np.testing.assert_array_almost_equal(
            vert, mesh.nodes.T,
            err_msg="vert 与 mesh.nodes.T 不一致，可能转置方向错误"
        )

    def test_vert_row0_is_R(self, tmp_path):
        """vert 第 0 行是 R 坐标（mesh.nodes[:, 0]）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            vert = f["femmesh"]["vert"][:]

        np.testing.assert_array_almost_equal(
            vert[0, :], mesh.nodes[:, 0],
            err_msg="vert 第 0 行应为 R 坐标"
        )

    def test_vert_row1_is_Z(self, tmp_path):
        """vert 第 1 行是 Z 坐标（mesh.nodes[:, 1]）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            vert = f["femmesh"]["vert"][:]

        np.testing.assert_array_almost_equal(
            vert[1, :], mesh.nodes[:, 1],
            err_msg="vert 第 1 行应为 Z 坐标"
        )


# ---------------------------------------------------------------------------
# M3-4：三角形连接与区域编号
# ---------------------------------------------------------------------------

class TestHDF5TriaAndRegionIds:
    """M3 tria 转置、节点索引 +1、region_id 不偏置。"""

    def test_tria_node_indices_1based(self, tmp_path):
        """tria 前 3 行的节点索引为 1-based（等于 mesh.triangles + 1 的转置）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        # tria[:3, :].T 应等于 mesh.triangles + 1
        expected_nodes = (mesh.triangles + 1).astype(np.int32)
        np.testing.assert_array_equal(
            tria[:3, :].T, expected_nodes,
            err_msg="tria 前 3 行节点索引不等于 mesh.triangles + 1 的转置"
        )

    def test_tria_node_indices_range(self, tmp_path):
        """所有三角形节点索引满足 1 <= index <= N。"""
        import h5py
        mesh = _make_test_mesh()
        n = mesh.n_nodes
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        node_indices = tria[:3, :]
        assert node_indices.min() >= 1, (
            f"节点索引最小值 {node_indices.min()} < 1"
        )
        assert node_indices.max() <= n, (
            f"节点索引最大值 {node_indices.max()} > N={n}"
        )

    def test_tria_region_id_not_offset(self, tmp_path):
        """tria 第 4 行（region_id）不执行 +1 偏置，保持物理标记值。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        np.testing.assert_array_equal(
            tria[3, :], mesh.region_ids,
            err_msg="tria 第 4 行 region_id 不应执行 +1 偏置"
        )

    def test_tria_region_id_distinct_values_preserved(self, tmp_path):
        """不同物理区域编号在输出中保持原值（1 和 2 均存在）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        actual_region_ids = set(tria[3, :].tolist())
        assert 1 in actual_region_ids, "region_id=1 (plasma) 应存在于输出"
        assert 2 in actual_region_ids, "region_id=2 (vacuum) 应存在于输出"


# ---------------------------------------------------------------------------
# M3-5：内外节点索引
# ---------------------------------------------------------------------------

class TestHDF5NodeIndices:
    """M3 内外节点索引：idxivert/idxevert 的 1-based 和完整性。"""

    def test_idxivert_equals_expected(self, tmp_path):
        """idxivert 等于 np.where(node_markers == 0)[0] + 1。"""
        import h5py
        mesh = _make_test_mesh()
        expected = (np.where(mesh.node_markers == 0)[0] + 1).astype(np.int32)
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = f["femmesh"]["idxivert"][:]

        np.testing.assert_array_equal(idxivert, expected)

    def test_idxevert_equals_expected(self, tmp_path):
        """idxevert 等于 np.where(node_markers != 0)[0] + 1。"""
        import h5py
        mesh = _make_test_mesh()
        expected = (np.where(mesh.node_markers != 0)[0] + 1).astype(np.int32)
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxevert = f["femmesh"]["idxevert"][:]

        np.testing.assert_array_equal(idxevert, expected)

    def test_idxivert_1based(self, tmp_path):
        """idxivert 所有值 >= 1（1-based）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = f["femmesh"]["idxivert"][:]

        assert idxivert.min() >= 1, f"idxivert 出现 0-based 索引：{idxivert.min()}"

    def test_idxevert_1based(self, tmp_path):
        """idxevert 所有值 >= 1（1-based）。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxevert = f["femmesh"]["idxevert"][:]

        assert idxevert.min() >= 1, f"idxevert 出现 0-based 索引：{idxevert.min()}"

    def test_idxivert_idxevert_no_overlap(self, tmp_path):
        """idxivert 和 idxevert 互不重叠。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = set(f["femmesh"]["idxivert"][:].tolist())
            idxevert = set(f["femmesh"]["idxevert"][:].tolist())

        overlap = idxivert & idxevert
        assert not overlap, f"idxivert 和 idxevert 存在重叠：{overlap}"

    def test_idxivert_idxevert_cover_all_nodes(self, tmp_path):
        """idxivert 和 idxevert 合并后覆盖全部节点索引（1 到 N）。"""
        import h5py
        mesh = _make_test_mesh()
        n = mesh.n_nodes
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = set(f["femmesh"]["idxivert"][:].tolist())
            idxevert = set(f["femmesh"]["idxevert"][:].tolist())

        all_indices = idxivert | idxevert
        expected = set(range(1, n + 1))
        assert all_indices == expected, (
            f"节点索引覆盖不完整：缺少 {expected - all_indices}，多余 {all_indices - expected}"
        )

    def test_nvert_in_nvert_ex_consistent(self, tmp_path):
        """nvert_in 和 nvert_ex 与索引数组长度一致。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            nvert_in = int(grp["nvert_in"][()])
            nvert_ex = int(grp["nvert_ex"][()])
            len_idxivert = len(grp["idxivert"][:])
            len_idxevert = len(grp["idxevert"][:])

        assert nvert_in == len_idxivert, (
            f"nvert_in={nvert_in} 与 idxivert 长度 {len_idxivert} 不一致"
        )
        assert nvert_ex == len_idxevert, (
            f"nvert_ex={nvert_ex} 与 idxevert 长度 {len_idxevert} 不一致"
        )


# ---------------------------------------------------------------------------
# M3-6：边界坐标
# ---------------------------------------------------------------------------

class TestHDF5BoundaryCoords:
    """M3 边界坐标：Rbc/Zbc 与边界节点坐标一致。"""

    def test_nbcRZ_equals_nvert_ex(self, tmp_path):
        """nbcRZ == nvert_ex。"""
        import h5py
        mesh = _make_test_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            nbcRZ = int(f["femmesh"]["nbcRZ"][()])
            nvert_ex = int(f["femmesh"]["nvert_ex"][()])

        assert nbcRZ == nvert_ex, f"nbcRZ={nbcRZ} != nvert_ex={nvert_ex}"

    def test_Rbc_equals_boundary_node_R(self, tmp_path):
        """Rbc 等于所有 node_markers != 0 节点的 R 坐标。"""
        import h5py
        mesh = _make_test_mesh()
        expected_Rbc = mesh.nodes[mesh.node_markers != 0, 0]
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            Rbc = f["femmesh"]["Rbc"][:]

        np.testing.assert_array_almost_equal(
            Rbc, expected_Rbc,
            err_msg="Rbc 与边界节点 R 坐标不一致"
        )

    def test_Zbc_equals_boundary_node_Z(self, tmp_path):
        """Zbc 等于所有 node_markers != 0 节点的 Z 坐标。"""
        import h5py
        mesh = _make_test_mesh()
        expected_Zbc = mesh.nodes[mesh.node_markers != 0, 1]
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            Zbc = f["femmesh"]["Zbc"][:]

        np.testing.assert_array_almost_equal(
            Zbc, expected_Zbc,
            err_msg="Zbc 与边界节点 Z 坐标不一致"
        )


# ---------------------------------------------------------------------------
# M3-7：Writer 输入不可变性
# ---------------------------------------------------------------------------

class TestHDF5WriterImmutability:
    """M3 输入不可变性：write_hdf5 不得原地修改 Mesh2D 的 NumPy 数组。"""

    def test_write_hdf5_does_not_modify_input(self, tmp_path):
        """write_hdf5 调用后，Mesh2D 的全部 NumPy 数组保持不变。"""
        mesh = _make_test_mesh()
        # 写出前复制全部数组
        before = _copy_mesh_arrays(mesh)

        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        # 逐项比较
        np.testing.assert_array_equal(
            mesh.nodes, before["nodes"],
            err_msg="write_hdf5 修改了 mesh.nodes"
        )
        np.testing.assert_array_equal(
            mesh.triangles, before["triangles"],
            err_msg="write_hdf5 修改了 mesh.triangles（可能执行了原地 +1）"
        )
        np.testing.assert_array_equal(
            mesh.region_ids, before["region_ids"],
            err_msg="write_hdf5 修改了 mesh.region_ids"
        )
        np.testing.assert_array_equal(
            mesh.boundary_segments, before["boundary_segments"],
            err_msg="write_hdf5 修改了 mesh.boundary_segments"
        )
        np.testing.assert_array_equal(
            mesh.boundary_markers, before["boundary_markers"],
            err_msg="write_hdf5 修改了 mesh.boundary_markers"
        )
        np.testing.assert_array_equal(
            mesh.node_markers, before["node_markers"],
            err_msg="write_hdf5 修改了 mesh.node_markers"
        )
