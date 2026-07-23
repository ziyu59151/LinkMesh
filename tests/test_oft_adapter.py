"""
tests/test_oft_adapter.py —— M2 OFT Adapter 验收测试
（v1.9 三层接口，v2.2 outer boundary 私有兼容接口修正 + 静态修正）。

测试原则：
    - 只使用 mock / 受控假的 OFT Domain / Region；
    - Fake Domain/Region 只模拟服务器已确认的真实关系：
        * domain.regions（列表容器）；
        * outer Region 对象；
        * domain.build_mesh() 后回写 outer_region._resampled_points；
        * domain.build_mesh() 返回现有假网格输出 (pts, lc, reg)；
      不虚构 OFT 不存在的公共边界 API（不使用 get_resampled_points 作为来源，
      不构造 _reg_seg_map/_resampled_segments/Mesh._resampled_points 读取路径）；
    - 不读取真实 GFile；
    - 不调用真实 OFT、Triangle、matplotlib；
    - 不写文件；
    - patch Adapter 实际查找的 `_load_gs_domain_class()`，不使用 create=True；
    - monkeypatch 版本读取以隔离 OFT 版本锁定检查；
    - 测试文件不宣称尚未运行的测试已经通过。

最终真实运行与验收在 Linux 服务器正式 OFT 26.6 环境执行，本文件仅静态编辑，
Windows 本地可收集但不保证运行通过。

覆盖三组：
    A. mesh_from_oft_domain()：通用 N 区域核心转换与校验
       （含 build_mesh 后 OFT 最终区域 ID 时序回归测试；
        含 build_mesh 后读取 outer Region 回写点列、版本锁定、失败即停、
        方向反转保持原起点、build 前保存引用、边界 Steiner 隔离、超过 4 点证伪四角）
    B. build_oft_domain_from_gfile()：默认 GFile 区域策略
       （含 outer Region 引用捕获、regions 长度差异、有壁/无壁一致、
        引用保存失败立即抛错）
    C. generate_mesh()：便利入口只组合两层
    另含 _load_gs_domain_class() 导入失败异常链测试与版本检查测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from linkmesh.mesher import oft_adapter as adapter
from linkmesh.mesher.oft_adapter import (
    _OUTER_REGION_ATTR,
    _REQUIRED_OFT_VERSION,
    _check_oft_version_locked,
    _load_gs_domain_class,
    _signed_area_closed,
    build_oft_domain_from_gfile,
    generate_mesh,
    mesh_from_oft_domain,
)


# --------------------------------------------------------------------------- #
# 版本锁定隔离辅助：monkeypatch 版本读取，避免依赖真实安装版                     #
# --------------------------------------------------------------------------- #

@pytest.fixture
def force_oft_version_266(monkeypatch):
    """强制版本检查读取到 26.6，使私有属性读取路径可在无 OFT 环境测试。"""
    monkeypatch.setattr(
        adapter, "_get_installed_oft_version", lambda: _REQUIRED_OFT_VERSION
    )


# --------------------------------------------------------------------------- #
# 受控假 OFT Region / Domain                                                    #
# --------------------------------------------------------------------------- #

class FakeRegion:
    """受控假 OFT Region：仅承载 build_mesh 后回写的 _resampled_points。

    初始 _resampled_points 为 None（build_mesh 前 OFT 尚未回写）。
    只提供 _resampled_points 属性，不提供 get_resampled_points（避免被误用为来源）。
    """

    def __init__(self):
        self._resampled_points = None


class FakeDomain:
    """受控假 OFT gs_Domain，用于 mesh_from_oft_domain 测试。

    build_mesh() 返回预置的 (pts, lc, reg)，并记录调用次数。
    region_info 为 {name: {'id': int}} 结构。

    可选携带一个 outer Region 对象（通过 _OUTER_REGION_ATTR 附加），
    并在 build_mesh() 时模拟 OFT 把有序离散点列回写到该 Region 的
    _resampled_points（resampled_on_build 提供回写值）。

    swap_region_on_build：若提供，build_mesh() 时把 domain 上的
    _OUTER_REGION_ATTR 替换成另一个对象（模拟 build 过程改写属性），
    用于验证 Adapter 使用 build 前保存的原对象。
    """

    def __init__(self, pts, lc, reg, region_info,
                 outer_region=None, resampled_on_build=None,
                 swap_region_on_build=None):
        self._pts = pts
        self._lc = lc
        self._reg = reg
        self.region_info = region_info
        self.build_mesh_call_count = 0
        self._resampled_on_build = resampled_on_build
        self._outer_region = outer_region
        self._swap_region_on_build = swap_region_on_build
        if outer_region is not None:
            setattr(self, _OUTER_REGION_ATTR, outer_region)

    def build_mesh(self):
        self.build_mesh_call_count += 1
        # 模拟 OFT 在 Mesh.__init__() 期间回写原 outer Region 的 _resampled_points
        if self._outer_region is not None and self._resampled_on_build is not None:
            self._outer_region._resampled_points = self._resampled_on_build
        # 模拟 build 过程改写 domain 上的 LinkMesh 附加属性为另一对象
        if self._swap_region_on_build is not None:
            setattr(self, _OUTER_REGION_ATTR, self._swap_region_on_build)
        return self._pts, self._lc, self._reg


class RelabelDomain:
    """受控假 OFT gs_Domain：模拟 build_mesh() 原地重排最终区域 ID。

    调用 build_mesh() 前，region_info 使用临时 ID（例如 {10,20}）；
    调用 build_mesh() 时，把 region_info 原地更新为最终 ID（例如 {1,2}），
    并返回与最终 ID 对应的 (pts, lc, reg)。

    该假对象证明 Adapter 必须在 build_mesh() 之后读取最终区域 ID。
    """

    def __init__(self, pts, lc, reg, initial_region_info, final_region_info):
        self._pts = pts
        self._lc = lc
        self._reg = reg
        # 调用前使用临时 ID
        self.region_info = dict(initial_region_info)
        self._final_region_info = dict(final_region_info)
        self.build_mesh_call_count = 0

    def build_mesh(self):
        self.build_mesh_call_count += 1
        # 原地更新为 OFT 最终 ID
        self.region_info = dict(self._final_region_info)
        return self._pts, self._lc, self._reg


def _cw_rect_points_6():
    """合法顺时针、隐式闭合（不重复首点）的 6 点离散边界（>4 点）。

    用于证明旧四角实现不能通过：真实回写点列包含比四角更多的重采样中点。
    顺时针：带符号闭合面积为负。
    """
    return np.array([
        [0.0, 0.0],
        [0.0, 1.0],
        [0.0, 2.0],   # 左边中点（重采样插入）
        [2.0, 2.0],
        [2.0, 1.0],   # 右边中点（重采样插入）
        [2.0, 0.0],
    ], dtype=np.float64)


def _cw_rect_points_4():
    """合法顺时针 4 点边界（不重复首点）。"""
    return np.array([
        [0.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
    ], dtype=np.float64)


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
# 版本锁定检查
# ==========================================================================

class TestOftVersionLock:
    """OFT 版本锁定检查：非 26.6 或读取失败明确失败。"""

    def test_version_266_passes(self, monkeypatch):
        monkeypatch.setattr(adapter, "_get_installed_oft_version",
                            lambda: _REQUIRED_OFT_VERSION)
        # 不抛异常
        _check_oft_version_locked()

    def test_version_mismatch_fails(self, monkeypatch):
        monkeypatch.setattr(adapter, "_get_installed_oft_version",
                            lambda: "27.0")
        with pytest.raises(ValueError) as ei:
            _check_oft_version_locked()
        msg = str(ei.value)
        assert "openfusiontoolkit" in msg
        assert "27.0" in msg
        assert _REQUIRED_OFT_VERSION in msg

    def test_version_unavailable_fails(self, monkeypatch):
        monkeypatch.setattr(adapter, "_get_installed_oft_version",
                            lambda: None)
        with pytest.raises(ValueError) as ei:
            _check_oft_version_locked()
        msg = str(ei.value)
        assert "openfusiontoolkit" in msg
        assert _REQUIRED_OFT_VERSION in msg


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

    def test_outer_boundary_none_when_no_outer_region_captured(self):
        # 通用 domain 未携带 outer Region 引用 → Mesh2D.outer_boundary 为 None
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary is None

    def test_generic_domain_does_not_guess_outer_region(self):
        # 携带 region_info 但不携带 outer Region 引用时，不猜测、不读私有 map
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        # 不附加 _OUTER_REGION_ATTR
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary is None
        assert not hasattr(domain, "mesh")  # 未构造/访问 domain.mesh 私有结构


class TestMeshFromOftDomainOuterBoundaryReadback:
    """build_mesh 后从 outer Region 回写点列读取 outer_boundary（版本锁定隔离）。"""

    def test_resampled_points_none_before_build(self):
        # build_mesh 前 outer Region 的 _resampled_points 为 None
        region = FakeRegion()
        assert region._resampled_points is None

    def test_outer_boundary_read_after_build(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()  # >4 点
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary is not None
        assert mesh.outer_boundary.shape == (6, 2)
        assert mesh.outer_boundary.dtype == np.float64

    def test_more_than_four_points_defeats_four_corner_impl(self, force_oft_version_266):
        # 回写点列 6 点：旧四角实现只会给 4 点，本用例证明真实来源多于四角。
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary.shape[0] == 6
        assert mesh.outer_boundary.shape[0] > 4

    def test_outer_boundary_clockwise(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        assert _signed_area_closed(ob) < 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert _signed_area_closed(mesh.outer_boundary) < 0

    def test_counterclockwise_readback_normalized_to_clockwise_keeps_start(self, force_oft_version_266):
        """OFT 回写逆时针点列时，规范化为顺时针，且保持原起点 0。

        输入逆时针点列首点应等于输出首点；输出后续点序为保持首点的反向。
        """
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ccw = _cw_rect_points_6()[::-1].copy()  # 逆时针
        assert _signed_area_closed(ccw) > 0
        input_first = ccw[0].copy()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ccw,
        )
        mesh = mesh_from_oft_domain(domain)
        ob_out = mesh.outer_boundary
        # 顺时针
        assert _signed_area_closed(ob_out) < 0
        # 起点保持
        np.testing.assert_array_equal(ob_out[0], input_first)
        # 后续点序为保持首点的反向：[p0, p_{B-1}, p_{B-2}, ..., p1]
        b = ccw.shape[0]
        expected = np.concatenate([ccw[:1], ccw[1:][::-1]], axis=0)
        np.testing.assert_array_equal(ob_out, expected)

    def test_clockwise_input_order_unchanged(self, force_oft_version_266):
        """输入已顺时针时点序不变（不反转、不循环移位）。"""
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        assert _signed_area_closed(ob) < 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        np.testing.assert_array_equal(mesh.outer_boundary, ob)

    def test_no_duplicate_first_point(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert not np.array_equal(mesh.outer_boundary[0], mesh.outer_boundary[-1])

    def test_explicit_closing_duplicate_removed(self, force_oft_version_266):
        # 回写点列若显式重复首点（末尾），规范化后删除且仍合法
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        ob_closed = np.vstack([ob, ob[0]])  # 末尾重复首点
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob_closed,
        )
        mesh = mesh_from_oft_domain(domain)
        # 删除重复末点后仍是 6 点
        assert mesh.outer_boundary.shape[0] == 6
        assert not np.array_equal(mesh.outer_boundary[0], mesh.outer_boundary[-1])

    def test_output_bx2_float64(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary.ndim == 2
        assert mesh.outer_boundary.shape[1] == 2
        assert mesh.outer_boundary.dtype == np.float64

    def test_outer_boundary_independent_copy(self, force_oft_version_266):
        # 修改 Region 回写数组，不影响已注入 Mesh2D 的副本；不共享内存
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        # 修改 Region 上的回写源数组
        region._resampled_points[0, 0] = 999.0
        assert mesh.outer_boundary[0, 0] != 999.0
        assert not np.shares_memory(mesh.outer_boundary, region._resampled_points)

    def test_uses_prebuild_saved_region_even_if_domain_attr_swapped(self, force_oft_version_266):
        """build 过程改写 domain 上的引用属性，Adapter 仍用 build 前保存的原对象。

        原 outer Region 在 build 中被回写正确点列；domain 上的
        _OUTER_REGION_ATTR 被替换为另一个（其 _resampled_points 为错误值）。
        Adapter 必须读取 build 前保存的原对象。
        """
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        original_region = FakeRegion()
        ob_correct = _cw_rect_points_6()

        # 被换上的另一个对象携带错误点列
        swapped_region = FakeRegion()
        swapped_region._resampled_points = np.array([
            [100.0, 100.0], [100.0, 101.0], [101.0, 100.0],
        ], dtype=np.float64)

        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=original_region, resampled_on_build=ob_correct,
            swap_region_on_build=swapped_region,
        )
        mesh = mesh_from_oft_domain(domain)
        # 读取的是 build 前保存的 original_region 回写点列，而非 swapped_region
        np.testing.assert_array_equal(mesh.outer_boundary, ob_correct)
        assert mesh.outer_boundary.shape[0] == 6

    def test_not_from_final_pts(self, force_oft_version_266):
        """outer boundary 来自 Region 回写点列，不来自 build_mesh 后 pts/lc。"""
        # 网格 pts 使用较大坐标；回写点列使用单位矩形，两者完全不同
        pts = np.array([
            [10.0, 10.0], [11.0, 10.0], [11.0, 11.0], [10.0, 11.0],
        ], dtype=np.float64)
        lc = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()  # 与 pts 完全不同
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        assert not np.array_equal(mesh.outer_boundary, pts)
        # 与回写点列一致（顺时针未反转，因为 ob 已顺时针）
        np.testing.assert_array_equal(mesh.outer_boundary, ob)

    def test_boundary_steiner_point_not_in_outer_boundary(self, force_oft_version_266):
        """真实边界 Steiner 点隔离：最终网格外边界含额外中点，但不进入 outer_boundary。

        构造受控二维网格：
            - Region 回写点列为矩形四角（Triangle 输入前离散边界，顺时针）：
                (0,0)->(0,2)->(2,2)->(2,0)
            - 最终 pts 在底边 (0,0)-(2,0) 上额外含中点 (1,0)（模拟边界 Steiner 点）；
            - 三角连接使 (1,0) 成为真正的拓扑外边界节点：
                它参与两条只出现一次的外边界边 (0,0)-(1,0) 与 (1,0)-(2,0)。
        断言 outer_boundary 不含 (1,0)。
        """
        # 最终节点：四角 + 底边中点 + 内部中心点
        pts = np.array([
            [0.0, 0.0],   # 0 角
            [1.0, 0.0],   # 1 底边 Steiner 中点（外边界节点）
            [2.0, 0.0],   # 2 角
            [2.0, 2.0],   # 3 角
            [0.0, 2.0],   # 4 角
            [1.0, 1.0],   # 5 内部中心
        ], dtype=np.float64)
        # 三角剖分（扇形 + 底边分两段）：使底边 (0,0)-(1,0)-(2,0) 为外边界边
        lc = np.array([
            [0, 1, 5],   # (0,0)-(1,0)-中心
            [1, 2, 5],   # (1,0)-(2,0)-中心
            [2, 3, 5],   # (2,0)-(2,2)-中心
            [3, 4, 5],   # (2,2)-(0,2)-中心
            [4, 0, 5],   # (0,2)-(0,0)-中心
        ], dtype=np.int32)
        reg = np.array([1, 1, 1, 1, 1], dtype=np.int32)

        region = FakeRegion()
        # Triangle 输入前离散边界：矩形四角（顺时针，不含底边中点 (1,0)）
        ob_corners = np.array([
            [0.0, 0.0],
            [0.0, 2.0],
            [2.0, 2.0],
            [2.0, 0.0],
        ], dtype=np.float64)
        assert _signed_area_closed(ob_corners) < 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1]),
            outer_region=region, resampled_on_build=ob_corners,
        )
        mesh = mesh_from_oft_domain(domain)

        # outer_boundary 不含底边 Steiner 点 (1,0)
        steiner = np.array([1.0, 0.0], dtype=np.float64)
        contains = np.any(np.all(mesh.outer_boundary == steiner, axis=1))
        assert not contains
        # outer_boundary 就是四角
        np.testing.assert_array_equal(mesh.outer_boundary, ob_corners)

    def test_nodes_triangles_regions_unchanged_by_outer_boundary(self, force_oft_version_266):
        # 注入 outer_boundary 不改变 nodes/triangles/region_ids
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        np.testing.assert_array_equal(mesh.nodes, pts)
        np.testing.assert_array_equal(mesh.triangles, lc)
        np.testing.assert_array_equal(mesh.region_ids, reg)


class TestMeshFromOftDomainOuterBoundaryFailures:
    """outer Region 私有接口失败即停（不回退四角/idxevert/自行重采样）。"""

    def test_missing_resampled_points_attr_fails(self, force_oft_version_266):
        # 捕获的 outer Region 缺少 _resampled_points 属性
        class NoAttrRegion:
            pass
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = NoAttrRegion()
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]), outer_region=region)
        with pytest.raises(ValueError, match="_resampled_points"):
            mesh_from_oft_domain(domain)

    def test_resampled_points_none_after_build_fails(self, force_oft_version_266):
        # build_mesh 后 Region._resampled_points 仍为 None（未回写）
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()  # 保持 None，且 domain 不回写
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=None,
        )
        with pytest.raises(ValueError, match="None"):
            mesh_from_oft_domain(domain)

    def test_resampled_points_bad_shape_fails(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        bad = np.array([1.0, 2.0, 3.0], dtype=np.float64)  # 一维
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=bad,
        )
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_resampled_points_nan_fails(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        bad = _cw_rect_points_6().copy()
        bad[0, 0] = np.nan
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=bad,
        )
        with pytest.raises(ValueError, match="有限|NaN|Inf"):
            mesh_from_oft_domain(domain)

    def test_resampled_points_too_few_fails(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        bad = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)  # 2 点
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=bad,
        )
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_version_mismatch_fails_when_reading_outer_region(self, monkeypatch):
        # 版本非 26.6 且存在 outer Region 时，读取前明确失败
        monkeypatch.setattr(adapter, "_get_installed_oft_version", lambda: "27.0")
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        with pytest.raises(ValueError, match="openfusiontoolkit"):
            mesh_from_oft_domain(domain)

    def test_version_unavailable_fails_when_reading_outer_region(self, monkeypatch):
        monkeypatch.setattr(adapter, "_get_installed_oft_version", lambda: None)
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        with pytest.raises(ValueError, match="openfusiontoolkit"):
            mesh_from_oft_domain(domain)


class TestMeshFromOftDomainFinalRegionIdTiming:
    """区域 ID 时序回归测试：校验使用 build_mesh 后的 OFT 最终区域 ID。"""

    def test_relabel_final_ids_accepted(self):
        # 调用前临时 ID {10,20}；build_mesh 后最终 ID {1,2}；输出 reg=[1,2]。
        # 旧实现（build_mesh 前提取 {10,20}）会错误拒绝；修复后必须通过。
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = RelabelDomain(
            pts, lc, reg,
            initial_region_info=_region_info([10, 20]),
            final_region_info=_region_info([1, 2]),
        )
        mesh = mesh_from_oft_domain(domain)
        # 断言结果区域 ID 原样为 [1,2]（不重编号、不 +1）
        np.testing.assert_array_equal(
            mesh.region_ids, np.array([1, 2], dtype=np.int32)
        )
        # build_mesh 只调用一次
        assert domain.build_mesh_call_count == 1

    def test_output_matching_stale_ids_rejected(self):
        # 调用前临时 ID {10,20}；build_mesh 后最终 ID {1,2}；
        # 但输出 reg 仍为旧 {10,20}（含未配置 ID）。
        # Adapter 必须依据最终集合 {1,2} 拒绝。
        pts, lc = _square_two_triangles()
        reg = np.array([10, 20], dtype=np.int32)
        domain = RelabelDomain(
            pts, lc, reg,
            initial_region_info=_region_info([10, 20]),
            final_region_info=_region_info([1, 2]),
        )
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)
        assert domain.build_mesh_call_count == 1


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
    """domain.region_info 结构性失败（build_mesh 后读取最终 region_info）。"""

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

    def test_region_info_none_after_build_mesh_raises_typeerror(self):
        # build_mesh 后 region_info 变为 None，应抛 TypeError
        class NoneAfterBuild:
            def __init__(self):
                self.region_info = {"a": {"id": 1}}

            def build_mesh(self):
                self.region_info = None
                pts, lc = _square_two_triangles()
                reg = np.array([1, 1], dtype=np.int32)
                return pts, lc, reg

        with pytest.raises(TypeError):
            mesh_from_oft_domain(NoneAfterBuild())


# ==========================================================================
# _load_gs_domain_class()：OFT 导入失败异常链
# ==========================================================================

class TestLoadGsDomainClassImportFailure:
    """OFT 导入失败时抛 ImportError 并保留原始异常链（__cause__）。"""

    def test_import_failure_raises_importerror_with_cause(self):
        # 通过 patch 内建 __import__ 制造导入失败，模拟 Windows 下
        # OFT 平台检查 / 共享库加载异常。不使用 create=True，不真实导入 OFT。
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("OpenFUSIONToolkit"):
                raise OSError("模拟：liboft_triangle.so 无法在当前平台加载")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ImportError) as excinfo:
                _load_gs_domain_class()

        # 保留原始异常链
        assert excinfo.value.__cause__ is not None
        assert isinstance(excinfo.value.__cause__, OSError)
        # 消息指出正式运行环境是 Linux Conda linkmesh 与正式安装的 OFT
        msg = str(excinfo.value)
        assert "Linux" in msg
        assert "linkmesh" in msg
        assert "openfusiontoolkit" in msg


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


def _square_contour():
    """一个正方形四点轮廓（不闭合）。"""
    r = np.array([0.0, 1.0, 1.0, 0.0], dtype=np.float64)
    z = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    return r, z


class DomainHolder:
    """允许附加任意属性、并模拟 domain.regions 列表的轻量假 domain。

    只模拟服务器已确认的真实关系：
        - define_region / add_pol