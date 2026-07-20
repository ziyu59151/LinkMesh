"""
tests/test_oft_adapter.py —— M2 OFT Adapter 验收测试（v1.9 三层接口）。

测试原则：
    - 只使用 mock / 受控假的 OFT Domain；
    - 不读取真实 GFile；
    - 不调用真实 OFT、Triangle、matplotlib；
    - 不写文件；
    - patch Adapter 实际查找的 `_load_gs_domain_class()`，不使用 create=True；
    - 测试文件不宣称尚未运行的测试已经通过。

最终真实运行与验收在 Linux 服务器正式 OFT 26.6 环境执行，本文件仅静态编辑，
Windows 本地可收集但不保证运行通过。

覆盖三组：
    A. mesh_from_oft_domain()：通用 N 区域核心转换与校验
    B. build_oft_domain_from_gfile()：默认 GFile 区域策略
    C. generate_mesh()：便利入口只组合两层
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from linkmesh.mesher.oft_adapter import (
    build_oft_domain_from_gfile,
    generate_mesh,
    mesh_from_oft_domain,
)


# --------------------------------------------------------------------------- #
# 受控假 OFT Domain                                                            #
# --------------------------------------------------------------------------- #

class FakeDomain:
    """受控假 OFT gs_Domain，用于 mesh_from_oft_domain 测试。

    build_mesh() 返回预置的 (pts, lc, reg)，并记录调用次数。
    region_info 为 {name: {'id': int}} 结构。
    """

    def __init__(self, pts, lc, reg, region_info):
        self._pts = pts
        self._lc = lc
        self._reg = reg
        self.region_info = region_info
        self.build_mesh_call_count = 0

    def build_mesh(self):
        self.build_mesh_call_count += 1
        return self._pts, self._lc, self._reg


def _square_two_triangles():
    """构造一个单位正方形（4 节点、2 三角形）的基础几何。

    节点：
        0:(0,0) 1:(1,0) 2:(1,1) 3:(0,1)
    三角形（逆时针，面积均为 0.5）：
        [0,1,2], [0,2,3]
    """
    pts = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ], dtype=np.float64)
    lc = np.array([
        [0, 1, 2],
        [0, 2, 3],
    ], dtype=np.int32)
    return pts, lc


def _region_info(ids):
    """构造 region_info：{f'r{ id }': {'id': id}}。"""
    return {f"r{i}": {"id": int(i)} for i in ids}


# ==========================================================================
# A. mesh_from_oft_domain()：通用 N 区域核心
# ==========================================================================

class TestMeshFromOftDomainValid:
    """合法输入通过，N=1/2/3/N>3 无特殊分支。"""

    def test_single_region_n1_passes(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        mesh = mesh_from_oft_domain(domain)
        assert mesh.n_nodes == 4
        assert mesh.n_triangles == 2
        assert set(mesh.region_ids.tolist()) == {1}
        assert domain.build_mesh_call_count == 1

    def test_two_regions_pass(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        assert set(mesh.region_ids.tolist()) == {1, 2}

    def test_three_regions_pass(self):
        # 4 三角形，区域 {1,2,3}
        pts = np.array([
            [0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [1.0, 1.0],
        ], dtype=np.float64)
        lc = np.array([
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4],
        ], dtype=np.int32)
        reg = np.array([1, 2, 3, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2, 3]))
        mesh = mesh_from_oft_domain(domain)
        assert set(mesh.region_ids.tolist()) == {1, 2, 3}

    def test_n_greater_than_3_passes_no_hardcoded_count(self):
        # 5 三角形，区域 {1,2,3,4,5}，证明未写死区域数量
        pts = np.array([
            [0.0, 0.0], [1.0, 0.0], [2.0, 0.0],
            [2.0, 1.0], [1.0, 1.0], [0.0, 1.0],
        ], dtype=np.float64)
        lc = np.array([
            [0, 1, 4],
            [1, 2, 3],
            [1, 3, 4],
            [0, 4, 5],
            [2, 4, 3],
        ], dtype=np.int32)
        # 保证每个三角形非退化、面积>1e-12
        reg = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2, 3, 4, 5]))
        mesh = mesh_from_oft_domain(domain)
        assert set(mesh.region_ids.tolist()) == {1, 2, 3, 4, 5}

    def test_shapes_and_dtypes(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        assert mesh.nodes.shape == (4, 2)
        assert mesh.nodes.dtype == np.float64
        assert mesh.triangles.shape == (2, 3)
        assert mesh.triangles.dtype == np.int32
        assert mesh.region_ids.shape == (2,)
        assert mesh.region_ids.dtype == np.int32

    def test_build_mesh_called_once(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh_from_oft_domain(domain)
        assert domain.build_mesh_call_count == 1

    def test_region_ids_not_reordered_or_offset(self):
        pts, lc = _square_two_triangles()
        reg = np.array([2, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        # 原样保存，不排序、不 +1
        np.testing.assert_array_equal(mesh.region_ids, np.array([2, 1], dtype=np.int32))

    def test_boundary_fields_are_empty_compat_arrays(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        assert mesh.boundary_segments.shape == (0, 2)
        assert mesh.boundary_markers.shape == (0,)
        assert mesh.node_markers.shape == (0,)


class TestMeshFromOftDomainNodeTriangleFailures:
    """节点/三角形非法输入失败。"""

    def test_empty_nodes_fails(self):
        pts = np.zeros((0, 2), dtype=np.float64)
        lc = np.zeros((0, 3), dtype=np.int32)
        reg = np.zeros((0,), dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_empty_triangles_fails(self):
        pts = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]], dtype=np.float64)
        lc = np.zeros((0, 3), dtype=np.int32)
        reg = np.zeros((0,), dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_non_finite_nodes_fails(self):
        pts = np.array([[0.0, 0.0], [1.0, 0.0], [np.nan, 1.0]], dtype=np.float64)
        lc = np.array([[0, 1, 2]], dtype=np.int32)
        reg = np.array([1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_non_integer_fails(self):
        pts, lc0 = _square_two_triangles()
        lc = np.array([[0.0, 1.0, 2.5], [0.0, 2.0, 3.0]], dtype=np.float64)
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_negative_fails(self):
        pts, _ = _square_two_triangles()
        lc = np.array([[-1, 1, 2], [0, 2, 3]], dtype=np.int32)
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_out_of_range_fails(self):
        pts, _ = _square_two_triangles()
        lc = np.array([[0, 1, 99], [0, 2, 3]], dtype=np.int32)
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_duplicate_node_fails(self):
        pts, _ = _square_two_triangles()
        lc = np.array([[0, 0, 2], [0, 2, 3]], dtype=np.int32)
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_zero_area_fails(self):
        # 三点共线，面积为 0
        pts = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [0.0, 1.0]], dtype=np.float64)
        lc = np.array([[0, 1, 2], [0, 1, 3]], dtype=np.int32)
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_lc_wrong_ncol_fails(self):
        pts, _ = _square_two_triangles()
        lc = np.array([[0, 1], [0, 2]], dtype=np.int32)  # 只有 2 列
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)


class TestMeshFromOftDomainRegionFailures:
    """区域编号非法失败。"""

    def test_reg_length_mismatch_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1], dtype=np.int32)  # 长度 1 != 2
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_reg_zero_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([0, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_reg_negative_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([-1, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_reg_nan_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1.0, np.nan], dtype=np.float64)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_reg_inf_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1.0, np.inf], dtype=np.float64)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_reg_non_integer_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1.0, 2.5], dtype=np.float64)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_missing_domain_region_fails(self):
        # region_info 声明 {1,2}，但输出只出现 {1}
        pts, lc = _square_two_triangles()
        reg = np.array([1, 1], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_extra_region_fails(self):
        # region_info 声明 {1}，但输出出现 {1,2}
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1]))
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)


class TestMeshFromOftDomainRegionInfoFailures:
    """domain.region_info 结构性失败。"""

    def test_empty_region_info_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, {})
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_region_info_duplicate_id_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        # 两个不同 name 映射到同一 ID
        region_info = {"a": {"id": 1}, "b": {"id": 1}}
        domain = FakeDomain(pts, lc, reg, region_info)
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_region_info_non_positive_id_fails(self):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region_info = {"a": {"id": 0}, "b": {"id": 1}}
        domain = FakeDomain(pts, lc, reg, region_info)
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_missing_build_mesh_raises_typeerror(self):
        class NoBuild:
            region_info = {"a": {"id": 1}}
        with pytest.raises(TypeError):
            mesh_from_oft_domain(NoBuild())

    def test_missing_region_info_raises_typeerror(self):
        class NoInfo:
            def build_mesh(self):
                return None
        with pytest.raises(TypeError):
            mesh_from_oft_domain(NoInfo())


# ==========================================================================
# B. build_oft_domain_from_gfile()：默认 GFile 区域策略
# ==========================================================================

class FakeGFileData:
    """受控假 GFileData，仅提供 Adapter 需要的字段。"""

    def __init__(self, lcfs_r, lcfs_z, wall_r=None, wall_z=None):
        self.lcfs_r = lcfs_r
        self.lcfs_z = lcfs_z
        self.wall_r = wall_r
        self.wall_z = wall_z
        self.rmaxis = 0.5
        self.zmaxis = 0.5


def _triangle_contour():
    """一个简单的三点轮廓（不闭合）。"""
    r = np.array([0.0, 1.0, 0.5], dtype=np.float64)
    z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    return r, z


def _square_contour():
    """一个正方形四点轮廓（不闭合）。"""
    r = np.array([0.0, 1.0, 1.0, 0.0], dtype=np.float64)
    z = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    return r, z


class TestBuildOftDomainWithWall:
    """有第一壁：三区域 OUTER/PLASMA/VACUUM，annulus + rectangle，不 build_mesh。"""

    def test_three_regions_annulus_rectangle_no_build_mesh(self):
        lcfs_r, lcfs_z = _square_contour()
        # 第一壁比 LCFS 更大的正方形
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        fake_domain = MagicMock()
        fake_gs_domain_cls = MagicMock(return_value=fake_domain)

        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            result = build_oft_domain_from_gfile(gfile)

        assert result is fake_domain
        # 定义了三个区域
        define_names = [c.args[0] for c in fake_domain.define_region.call_args_list]
        assert "outer" in define_names
        assert "plasma" in define_names
        assert "vacuum" in define_names
        # 使用 annulus + rectangle
        assert fake_domain.add_annulus.called
        assert fake_domain.add_rectangle.called
        # 不调用 build_mesh
        assert not fake_domain.build_mesh.called

    def test_wall_uses_rectangle_named_outer(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        fake_domain = MagicMock()
        fake_gs_domain_cls = MagicMock(return_value=fake_domain)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_oft_domain_from_gfile(gfile)

        # add_rectangle 使用 name="outer"
        _, kwargs = fake_domain.add_rectangle.call_args
        assert kwargs.get("name") == "outer"


class TestBuildOftDomainNoWall:
    """无第一壁：两区域 OUTER/PLASMA，polygon + rectangle，不 build_mesh。"""

    def test_two_regions_polygon_rectangle_no_build_mesh(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        fake_domain = MagicMock()
        fake_gs_domain_cls = MagicMock(return_value=fake_domain)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            result = build_oft_domain_from_gfile(gfile)

        assert result is fake_domain
        define_names = [c.args[0] for c in fake_domain.define_region.call_args_list]
        assert "outer" in define_names
        assert "plasma" in define_names
        assert "vacuum" not in define_names
        assert fake_domain.add_polygon.called
        assert fake_domain.add_rectangle.called
        assert not fake_domain.add_annulus.called
        assert not fake_domain.build_mesh.called


class TestBuildOftDomainNormalization:
    """轮廓薄规范化行为。"""

    def test_duplicate_closing_point_removed_only_last(self):
        # LCFS 首尾重复：正方形 + 追加首点
        r = np.array([0.0, 1.0, 1.0, 0.0, 0.0], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0, 1.0, 0.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)

        fake_domain = MagicMock()
        fake_gs_domain_cls = MagicMock(return_value=fake_domain)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_oft_domain_from_gfile(gfile)

        # add_polygon 收到的 LCFS 应删除末尾重复点，剩 4 点
        contour = fake_domain.add_polygon.call_args.args[0]
        assert contour.shape == (4, 2)


class TestBuildOftDomainInputFailures:
    """输入非法失败（不依赖 OFT，参数/轮廓校验先行）。"""

    def test_wall_r_only_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_lcfs_length_mismatch_fails(self):
        r = np.array([0.0, 1.0, 0.5], dtype=np.float64)
        z = np.array([0.0, 0.0], dtype=np.float64)  # 长度不一致
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_lcfs_too_few_points_fails(self):
        r = np.array([0.0, 1.0], dtype=np.float64)
        z = np.array([0.0, 0.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_lcfs_nan_fails(self):
        r = np.array([0.0, 1.0, np.nan], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_degenerate_range_fails(self):
        # 所有点共位，包围范围退化
        r = np.array([1.0, 1.0, 1.0], dtype=np.float64)
        z = np.array([1.0, 1.0, 1.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_plasma_dx_non_positive_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile, plasma_dx=0.0)

    def test_vacuum_dx_non_finite_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile, vacuum_dx=np.inf)

    def test_outer_dx_negative_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile, outer_dx=-0.1)

    def test_outer_padding_negative_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile, outer_padding=-0.1)

    def test_outer_padding_non_finite_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile, outer_padding=np.nan)


# ==========================================================================
# C. generate_mesh()：便利入口只组合两层
# ==========================================================================

class TestGenerateMeshComposition:
    """generate_mesh 只组合 build_oft_domain_from_gfile 与 mesh_from_oft_domain。"""

    def test_composition_passes_domain_and_returns_mesh(self):
        sentinel_domain = object()
        sentinel_mesh = object()
        gfile = FakeGFileData(*_square_contour(), None, None)

        with patch(
            "linkmesh.mesher.oft_adapter.build_oft_domain_from_gfile",
            return_value=sentinel_domain,
        ) as m_build, patch(
            "linkmesh.mesher.oft_adapter.mesh_from_oft_domain",
            return_value=sentinel_mesh,
        ) as m_mesh:
            result = generate_mesh(gfile)

        # 前者返回的 domain 原样传给后者
        m_build.assert_called_once()
        m_mesh.assert_called_once_with(sentinel_domain)
        # 结果原样返回
        assert result is sentinel_mesh

    def test_generate_mesh_forwards_scale_kwargs(self):
        sentinel_domain = object()
        sentinel_mesh = object()
        gfile = FakeGFileData(*_square_contour(), None, None)

        with patch(
            "linkmesh.mesher.oft_adapter.build_oft_domain_from_gfile",
            return_value=sentinel_domain,
        ) as m_build, patch(
            "linkmesh.mesher.oft_adapter.mesh_from_oft_domain",
            return_value=sentinel_mesh,
        ):
            generate_mesh(
                gfile,
                plasma_dx=0.05,
                vacuum_dx=0.06,
                outer_dx=0.20,
                outer_padding=0.30,
            )

        _, kwargs = m_build.call_args
        assert kwargs["plasma_dx"] == 0.05
        assert kwargs["vacuum_dx"] == 0.06
        assert kwargs["outer_dx"] == 0.20
        assert kwargs["outer_padding"] == 0.30

    def test_generate_mesh_no_second_build_mesh(self):
        # mesh_from_oft_domain 被 patch，则不会有真实 build_mesh 调用链；
        # 这里验证 generate_mesh 不自行调用 domain.build_mesh。
        fake_domain = MagicMock()
        sentinel_mesh = object()
        gfile = FakeGFileData(*_square_contour(), None, None)

        with patch(
            "linkmesh.mesher.oft_adapter.build_oft_domain_from_gfile",
            return_value=fake_domain,
        ), patch(
            "linkmesh.mesher.oft_adapter.mesh_from_oft_domain",
            return_value=sentinel_mesh,
        ):
            generate_mesh(gfile)

        # generate_mesh 自身不直接调用 build_mesh
        assert not fake_domain.build_mesh.called
