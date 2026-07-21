"""
tests/test_hdf5_writer.py —— M3 HDF5 Writer 验收测试（v1.11 契约）。

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布 M3 验收通过。最终真实回读与 MATLAB
消费验收在 Linux 服务器执行。

测试原则（v1.11）：
    - Mesh2D 从 linkmesh.mesh 导入（唯一正式定义）；
    - 使用 pytest tmp_path、真实 h5py 临时写入与回读、小型受控 NumPy 网格；
    - 不调用 OFT、Triangle、matplotlib 或真实 GFile；
    - 不读取或修改真实 HDF5 样例；
    - 不 mock h5py，不访问 Writer 私有实现绕过公开接口。

v1.11 核心契约（8 核心数据集，均 float64）：
    nvert/ntria/nvert_in/nvert_ex : (1,1)
    vert                          : (N,2)，不转置
    tria                          : (T,3)，1-based，无第四列，无 region_ids
    idxivert                      : (1,nvert_in)，1-based，升序（拓扑内部节点补集）
    idxevert                      : (1,nvert_ex)，1-based，升序（拓扑外边界节点）
    默认不写 nbcRZ/Rbc/Zbc。
"""

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Mesh2D 从唯一正式定义模块导入（v1.11 M2.5 解耦后）
# ---------------------------------------------------------------------------
from linkmesh.mesh import Mesh2D
from linkmesh.writers.hdf5_writer import write_hdf5


# ---------------------------------------------------------------------------
# 测试辅助：构造受控合法网格
# ---------------------------------------------------------------------------

def _make_center_mesh() -> Mesh2D:
    """网格 A：一个中心节点 + 一圈外边界节点。

    几何：
        - 外圈 4 个节点构成正方形的角点（0..3）；
        - 中心节点 4；
        - 4 个三角形以中心节点为公共顶点扇形铺满正方形。

    拓扑期望：
        - 外圈边 (0,1)(1,2)(2,3)(3,0) 各出现一次 → 外边界边；
        - 辐条边 (0,4)(1,4)(2,4)(3,4) 各出现两次 → 内部共享边；
        - 外边界节点 = {0,1,2,3}（1-based: {1,2,3,4}）；
        - 内部节点 = {4}（1-based: {5}）。

    坐标故意非对称，避免错误转置偶然通过。
    region_ids 使用与节点编号无关的值（7、9），证明 Writer 不写也不依赖它。
    """
    nodes = np.array([
        [0.10, 0.20],   # 0 外圈
        [2.30, 0.15],   # 1 外圈
        [2.45, 1.90],   # 2 外圈
        [0.05, 1.75],   # 3 外圈
        [1.20, 0.95],   # 4 中心（内部）
    ], dtype=np.float64)

    triangles = np.array([
        [0, 1, 4],
        [1, 2, 4],
        [2, 3, 4],
        [3, 0, 4],
    ], dtype=np.int32)

    # region_ids 与节点编号无关，且不是 {1,2,3}
    region_ids = np.array([7, 7, 9, 9], dtype=np.int32)

    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
    )


def _make_single_triangle_mesh() -> Mesh2D:
    """网格 B：单三角形，三个节点均为外边界。

    拓扑期望：
        - 三条边各出现一次 → 全部外边界边；
        - 外边界节点 = {0,1,2}（1-based: {1,2,3}）；
        - 内部节点为空；
        - nvert_in == 0，idxivert.shape == (1,0)。
    """
    nodes = np.array([
        [0.30, 0.10],
        [1.70, 0.20],
        [0.90, 1.40],
    ], dtype=np.float64)

    triangles = np.array([
        [0, 1, 2],
    ], dtype=np.int32)

    region_ids = np.array([5], dtype=np.int32)

    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
    )


def _copy_core_arrays(mesh: Mesh2D) -> dict:
    """复制 Mesh2D 核心与兼容数组，用于不可变性检查。"""
    return {
        "nodes": mesh.nodes.copy(),
        "triangles": mesh.triangles.copy(),
        "region_ids": mesh.region_ids.copy(),
        "boundary_segments": mesh.boundary_segments.copy(),
        "boundary_markers": mesh.boundary_markers.copy(),
        "node_markers": mesh.node_markers.copy(),
    }


# ===========================================================================
# M3-1：核心数据集完整性与可选数据集缺失
# ===========================================================================

class TestHDF5DatasetSet:
    """精确验证 8 个核心数据集存在、3 个可选数据集不存在。"""

    _CORE = {
        "nvert", "ntria", "nvert_in", "nvert_ex",
        "vert", "idxivert", "idxevert", "tria",
    }
    _OPTIONAL = {"nbcRZ", "Rbc", "Zbc"}

    def test_exactly_eight_core_datasets(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            assert "femmesh" in f, "缺少顶层组 /femmesh"
            keys = set(f["femmesh"].keys())
            assert keys == self._CORE, (
                f"数据集集合与 8 核心不一致：多余={keys - self._CORE}，"
                f"缺失={self._CORE - keys}"
            )

    def test_optional_datasets_absent(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            keys = set(f["femmesh"].keys())
            present = self._OPTIONAL & keys
            assert not present, f"不应写出可选数据集：{present}"

    def test_no_region_ids_dataset(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            keys = set(f["femmesh"].keys())
            assert "region_ids" not in keys, "不得写出 region_ids 数据集"
            assert "region_id" not in keys, "不得写出 region_id 数据集"


# ===========================================================================
# M3-2：dtype 与 shape
# ===========================================================================

class TestHDF5ShapeAndDtype:
    """全部 8 核心 dtype 为 float64；shape 精确符合 v1.11。"""

    def test_all_core_dtype_float64(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            for name in ("nvert", "ntria", "nvert_in", "nvert_ex",
                         "vert", "idxivert", "idxevert", "tria"):
                assert grp[name].dtype == np.float64, (
                    f"{name} dtype 应为 float64，实际 {grp[name].dtype}"
                )

    def test_count_shapes_are_1x1(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            for name in ("nvert", "ntria", "nvert_in", "nvert_ex"):
                assert grp[name].shape == (1, 1), (
                    f"{name} shape 应为 (1,1)，实际 {grp[name].shape}"
                )

    def test_vert_tria_idx_shapes(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        n = mesh.n_nodes       # 5
        t = mesh.n_triangles   # 4
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            assert grp["vert"].shape == (n, 2), f"vert shape 期望 ({n},2)"
            assert grp["tria"].shape == (t, 3), f"tria shape 期望 ({t},3)"

            nvert_in = int(round(float(grp["nvert_in"][()][0, 0])))
            nvert_ex = int(round(float(grp["nvert_ex"][()][0, 0])))
            assert grp["idxivert"].shape == (1, nvert_in), (
                f"idxivert shape 期望 (1,{nvert_in})"
            )
            assert grp["idxevert"].shape == (1, nvert_ex), (
                f"idxevert shape 期望 (1,{nvert_ex})"
            )

    def test_count_values(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            assert int(round(float(grp["nvert"][()][0, 0]))) == 5
            assert int(round(float(grp["ntria"][()][0, 0]))) == 4
            assert int(round(float(grp["nvert_in"][()][0, 0]))) == 1
            assert int(round(float(grp["nvert_ex"][()][0, 0]))) == 4


# ===========================================================================
# M3-3：vert 内容（不转置）
# ===========================================================================

class TestHDF5Vert:
    """vert 磁盘 (N,2)，内容等于 nodes，不转置。"""

    def test_vert_equals_nodes(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            vert = f["femmesh"]["vert"][:]

        assert vert.shape == mesh.nodes.shape, (
            f"vert shape {vert.shape} 应等于 nodes shape {mesh.nodes.shape}"
        )
        np.testing.assert_array_almost_equal(
            vert, mesh.nodes,
            err_msg="vert 与 mesh.nodes 不一致（可能被错误转置）"
        )

    def test_vert_col0_is_R_col1_is_Z(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            vert = f["femmesh"]["vert"][:]

        np.testing.assert_array_almost_equal(vert[:, 0], mesh.nodes[:, 0])
        np.testing.assert_array_almost_equal(vert[:, 1], mesh.nodes[:, 1])


# ===========================================================================
# M3-4：tria 内容（1-based，无第四列，不转置，不写 region_ids）
# ===========================================================================

class TestHDF5Tria:
    """tria 磁盘 (T,3)，等于 triangles.astype(float64)+1。"""

    def test_tria_equals_triangles_plus_one(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        expected = mesh.triangles.astype(np.float64) + 1.0
        assert tria.shape == expected.shape, (
            f"tria shape {tria.shape} 应等于 (T,3) {expected.shape}"
        )
        np.testing.assert_array_almost_equal(
            tria, expected,
            err_msg="tria 应等于 triangles.astype(float64)+1（1-based，不转置，无第四列）"
        )

    def test_tria_has_three_columns_only(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        assert tria.shape[1] == 3, f"tria 不得含第四列，实际列数={tria.shape[1]}"

    def test_tria_node_indices_1based_range(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        n = mesh.n_nodes
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        assert tria.min() >= 1.0, f"tria 最小值 {tria.min()} < 1（应为 1-based）"
        assert tria.max() <= float(n), f"tria 最大值 {tria.max()} > N={n}"

    def test_region_ids_not_in_tria(self, tmp_path):
        """tria 中不包含 region_ids（列数为 3，且不存在 region_id 列）。"""
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            tria = f["femmesh"]["tria"][:]

        # region_ids 为 {7,9}，若被错误拼接为第四列会使列数为 4
        assert tria.shape[1] == 3, "tria 含额外列，疑似写入了 region_ids"


# ===========================================================================
# M3-5：idxevert / idxivert 拓扑分类
# ===========================================================================

class TestHDF5BoundaryTopology:
    """idxevert/idxivert 的 1-based、升序、拓扑正确性与集合关系。"""

    def test_center_mesh_classification(self, tmp_path):
        """中心节点属于内部；外圈 4 节点属于外边界。"""
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = f["femmesh"]["idxivert"][:]
            idxevert = f["femmesh"]["idxevert"][:]

        # 1-based：外圈节点 0..3 → {1,2,3,4}；中心节点 4 → {5}
        np.testing.assert_array_equal(
            idxevert.reshape(-1).astype(np.int64),
            np.array([1, 2, 3, 4], dtype=np.int64),
        )
        np.testing.assert_array_equal(
            idxivert.reshape(-1).astype(np.int64),
            np.array([5], dtype=np.int64),
        )

    def test_idxevert_1based_sorted(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxevert = f["femmesh"]["idxevert"][:].reshape(-1)

        assert idxevert.min() >= 1.0, "idxevert 应为 1-based"
        assert np.all(np.diff(idxevert) > 0), "idxevert 应严格升序"

    def test_idxivert_1based_sorted(self, tmp_path):
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            idxivert = f["femmesh"]["idxivert"][:].reshape(-1)

        if idxivert.size > 0:
            assert idxivert.min() >= 1.0, "idxivert 应为 1-based"
        if idxivert.size > 1:
            assert np.all(np.diff(idxivert) > 0), "idxivert 应严格升序"

    def test_single_triangle_no_interior(self, tmp_path):
        """单三角形：nvert_in=0，idxivert.shape==(1,0)，外边界为 {1,2,3}。"""
        import h5py
        mesh = _make_single_triangle_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            idxivert = grp["idxivert"][:]
            idxevert = grp["idxevert"][:]
            nvert_in = int(round(float(grp["nvert_in"][()][0, 0])))
            nvert_ex = int(round(float(grp["nvert_ex"][()][0, 0])))

        assert nvert_in == 0, "单三角形内部节点数应为 0"
        assert nvert_ex == 3, "单三角形外边界节点数应为 3"
        assert idxivert.shape == (1, 0), (
            f"nvert_in==0 时 idxivert.shape 应为 (1,0)，实际 {idxivert.shape}"
        )
        np.testing.assert_array_equal(
            idxevert.reshape(-1).astype(np.int64),
            np.array([1, 2, 3], dtype=np.int64),
        )

    def test_sets_unique_disjoint_cover(self, tmp_path):
        """idxivert 与 idxevert 唯一、互斥并覆盖 1..N。"""
        import h5py
        mesh = _make_center_mesh()
        n = mesh.n_nodes
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            iv = set(int(round(x)) for x in f["femmesh"]["idxivert"][:].reshape(-1).tolist())
            ev = set(int(round(x)) for x in f["femmesh"]["idxevert"][:].reshape(-1).tolist())

        assert not (iv & ev), f"idxivert 与 idxevert 存在重叠：{iv & ev}"
        assert (iv | ev) == set(range(1, n + 1)), (
            f"并集未覆盖 1..{n}：实际 {sorted(iv | ev)}"
        )

    def test_count_matches_index_lengths(self, tmp_path):
        """nvert_in/nvert_ex 与索引数组长度一致，且和为 nvert。"""
        import h5py
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            grp = f["femmesh"]
            nvert = int(round(float(grp["nvert"][()][0, 0])))
            nvert_in = int(round(float(grp["nvert_in"][()][0, 0])))
            nvert_ex = int(round(float(grp["nvert_ex"][()][0, 0])))
            len_iv = grp["idxivert"].shape[1]
            len_ev = grp["idxevert"].shape[1]

        assert nvert_in == len_iv, f"nvert_in={nvert_in} 与 idxivert 长度 {len_iv} 不一致"
        assert nvert_ex == len_ev, f"nvert_ex={nvert_ex} 与 idxevert 长度 {len_ev} 不一致"
        assert nvert_in + nvert_ex == nvert, (
            f"nvert_in+nvert_ex={nvert_in + nvert_ex} != nvert={nvert}"
        )


# ===========================================================================
# M3-6：Writer 输入不可变性与不依赖兼容字段
# ===========================================================================

class TestHDF5WriterImmutability:
    """write_hdf5 不得原地修改 Mesh2D 的任何 NumPy 数组。"""

    def test_write_does_not_modify_input(self, tmp_path):
        mesh = _make_center_mesh()
        before = _copy_core_arrays(mesh)

        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

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

    def test_does_not_depend_on_compat_arrays(self, tmp_path):
        """兼容字段为默认空数组时仍能正确写出（不依赖 node_markers 等）。"""
        import h5py
        mesh = _make_center_mesh()
        # 默认构造下 boundary_segments/boundary_markers/node_markers 均为空
        assert mesh.node_markers.shape == (0,)
        assert mesh.boundary_segments.shape == (0, 2)

        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)

        with h5py.File(str(h5_path), "r") as f:
            # 分类仍来自三角形拓扑：中心 {5} 为内部，外圈 {1,2,3,4} 为外边界
            idxivert = f["femmesh"]["idxivert"][:].reshape(-1).astype(np.int64)
            idxevert = f["femmesh"]["idxevert"][:].reshape(-1).astype(np.int64)

        np.testing.assert_array_equal(idxivert, np.array([5], dtype=np.int64))
        np.testing.assert_array_equal(idxevert, np.array([1, 2, 3, 4], dtype=np.int64))


# ===========================================================================
# M3-7：verbose 行为
# ===========================================================================

class TestHDF5Verbose:
    """verbose=False 不打印完成信息；verbose=True 打印且不宣称写出可选数据集。"""

    def test_verbose_false_silent(self, tmp_path, capsys):
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=False)
        captured = capsys.readouterr()
        assert captured.out == "", "verbose=False 不应打印任何完成信息"

    def test_verbose_true_prints_summary(self, tmp_path, capsys):
        mesh = _make_center_mesh()
        h5_path = tmp_path / "mesh.h5"
        write_hdf5(mesh, str(h5_path), verbose=True)
        captured = capsys.readouterr()
        out = captured.out
        assert str(h5_path) in out, "verbose 完成信息应包含输出路径"
        assert "节点数" in out
        assert "三角形数" in out
        assert "内部节点数" in out
        assert "外边界节点数" in out
        # 不得声称写出可选数据集
        assert "nbcRZ" not in out
        assert "Rbc" not in out
        assert "Zbc" not in out


# ===========================================================================
# M3-8：输入失败测试（失败前不得创建/截断目标文件）
# ===========================================================================

class TestHDF5InputFailures:
    """非法输入必须抛 ValueError，且失败前若文件不存在则失败后仍不存在。"""

    def _assert_fail_no_file(self, mesh, tmp_path, match):
        h5_path = tmp_path / "should_not_exist.h5"
        assert not h5_path.exists()
        with pytest.raises(ValueError, match=match):
            write_hdf5(mesh, str(h5_path), verbose=False)
        assert not h5_path.exists(), (
            "验证失败时不得创建或截断目标文件"
        )

    def test_nodes_not_2d(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            triangles=np.array([[0, 1, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="二维")

    def test_nodes_not_Nx2(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [2.0, 2.0, 2.0]],
                           dtype=np.float64),
            triangles=np.array([[0, 1, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match=r"\(N,2\)")

    def test_empty_nodes(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.zeros((0, 2), dtype=np.float64),
            triangles=np.zeros((0, 3), dtype=np.int32),
            region_ids=np.zeros((0,), dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="空")

    def test_nodes_nan(self, tmp_path):
        mesh = _make_single_triangle_mesh()
        bad = mesh.nodes.copy()
        bad[0, 0] = np.nan
        mesh2 = Mesh2D(nodes=bad, triangles=mesh.triangles.copy(),
                       region_ids=mesh.region_ids.copy())
        self._assert_fail_no_file(mesh2, tmp_path, match="有限")

    def test_nodes_inf(self, tmp_path):
        mesh = _make_single_triangle_mesh()
        bad = mesh.nodes.copy()
        bad[1, 1] = np.inf
        mesh2 = Mesh2D(nodes=bad, triangles=mesh.triangles.copy(),
                       region_ids=mesh.region_ids.copy())
        self._assert_fail_no_file(mesh2, tmp_path, match="有限")

    def test_triangles_not_2d(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([0, 1, 2], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="二维")

    def test_triangles_not_Tx3(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[0, 1]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match=r"\(T,3\)")

    def test_empty_triangles(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.zeros((0, 3), dtype=np.int32),
            region_ids=np.zeros((0,), dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="空")

    def test_triangles_nan(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[0.0, 1.0, np.nan]], dtype=np.float64),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="有限|整数")

    def test_triangles_inf(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[0.0, 1.0, np.inf]], dtype=np.float64),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="有限|整数")

    def test_triangles_non_integer(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0], [0.0, 1.0]],
                           dtype=np.float64),
            triangles=np.array([[0.0, 1.0, 2.5]], dtype=np.float64),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="整数")

    def test_triangles_negative_index(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[-1, 1, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="越界")

    def test_triangles_out_of_range(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[0, 1, 99]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="越界")

    def test_triangles_duplicate_node(self, tmp_path):
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64),
            triangles=np.array([[0, 0, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="重复顶点")

    def test_triangles_collinear_zero_area(self, tmp_path):
        """三个不同但共线的节点：面积为 0，应失败。"""
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [0.0, 1.0]],
                           dtype=np.float64),
            triangles=np.array([[0, 1, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="面积")

    def test_triangles_tiny_area(self, tmp_path):
        """面积不大于 1e-12：应失败。"""
        eps = 1e-9  # 底约 1，高约 1e-9 → 面积约 5e-10？调小到不大于 1e-12
        mesh = Mesh2D(
            nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1e-13]], dtype=np.float64),
            triangles=np.array([[0, 1, 2]], dtype=np.int32),
            region_ids=np.array([1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="面积")

    def test_non_manifold_edge(self, tmp_path):
        """三个及以上非退化三角形共享同一无向边 (0,1)，应在打开文件前拒绝。"""
        # 节点 0,1 为公共边；节点 2,3,4 分别在不同侧构成三个三角形，均非退化。
        nodes = np.array([
            [0.0, 0.0],   # 0
            [2.0, 0.0],   # 1
            [1.0, 1.0],   # 2
            [1.0, -1.0],  # 3
            [1.0, 2.0],   # 4
        ], dtype=np.float64)
        triangles = np.array([
            [0, 1, 2],
            [0, 1, 3],
            [0, 1, 4],
        ], dtype=np.int32)
        mesh = Mesh2D(
            nodes=nodes,
            triangles=triangles,
            region_ids=np.array([1, 1, 1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="非流形")

    def test_no_topological_boundary(self, tmp_path):
        """无任何拓扑外边界边（每条无向边都出现两次）时应拒绝。

        构造一个闭合曲面（四面体的三角面拓扑映射到平面节点集）：
        4 个节点，4 个三角形覆盖，使每条无向边恰好被两个三角形共享。
        节点使用非共面平面坐标即可（拓扑判定只看边计数，与几何无关；
        但需保证每个三角形面积非零以通过面积检查）。
        """
        # 四面体的 4 个面：{0,1,2},{0,1,3},{0,2,3},{1,2,3}
        # 每条无向边被恰好两个面共享 → 无外边界边。
        nodes = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ], dtype=np.float64)
        triangles = np.array([
            [0, 1, 2],
            [0, 1, 3],
            [0, 2, 3],
            [1, 2, 3],
        ], dtype=np.int32)
        mesh = Mesh2D(
            nodes=nodes,
            triangles=triangles,
            region_ids=np.array([1, 1, 1, 1], dtype=np.int32),
        )
        self._assert_fail_no_file(mesh, tmp_path, match="外边界")
