"""
tests/test_oft_adapter.py —— M2 OFT Adapter 验收测试
（v1.9 三层接口，v2.2 outer boundary 私有兼容接口修正，
v2.3 输入层 II single_region + lcfs 追加测试）。

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
        Steiner 点不进入 outer_boundary、超过 4 点证明旧四角失败；
        含近似重复闭合末点删除真实回归）
    B. build_oft_domain_from_gfile()：默认 GFile 区域策略
       （含 outer Region 引用捕获、regions 长度差异、有壁/无壁一致）
    C. generate_mesh()：便利入口只组合两层
    D. build_single_region_domain_from_lcfs()：LCFS 单区域来源策略层
       （v2.3 输入层 II：单 polygon Region、不 rectangle/annulus、plasma_dx、
        回写点列非原始 LCFS、防御性失败、版本锁定）
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
    _normalize_single_region_polygon,
    _signed_area_closed,
    build_oft_domain_from_gfile,
    build_single_region_domain_from_lcfs,
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

    可选在 build_mesh() 时把 domain 上的 _OUTER_REGION_ATTR 替换为另一个
    Region（replace_attr_on_build），用于验证 Adapter 使用 build 前保存的
    原对象、而非替换对象。
    """

    def __init__(self, pts, lc, reg, region_info,
                 outer_region=None, resampled_on_build=None,
                 replace_attr_on_build=None):
        self._pts = pts
        self._lc = lc
        self._reg = reg
        self.region_info = region_info
        self.build_mesh_call_count = 0
        self._resampled_on_build = resampled_on_build
        self._outer_region = outer_region
        self._replace_attr_on_build = replace_attr_on_build
        if outer_region is not None:
            setattr(self, _OUTER_REGION_ATTR, outer_region)

    def build_mesh(self):
        self.build_mesh_call_count += 1
        # 模拟 OFT 在 Mesh.__init__() 期间回写 region._resampled_points
        if self._outer_region is not None and self._resampled_on_build is not None:
            self._outer_region._resampled_points = self._resampled_on_build
        # 模拟极端情况：build 过程中把 domain 上的私有属性替换为另一个 Region
        if self._replace_attr_on_build is not None:
            setattr(self, _OUTER_REGION_ATTR, self._replace_attr_on_build)
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

    def test_generic_domain_without_oft_installed_does_not_check_version(self, monkeypatch):
        # 通用 domain 无 outer Region 时，即使版本读取返回 None 也不应因版本检查失败
        monkeypatch.setattr(adapter, "_get_installed_oft_version", lambda: None)
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        domain = FakeDomain(pts, lc, reg, _region_info([1, 2]))
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary is None


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

    def test_counterclockwise_readback_normalized_to_clockwise(self, force_oft_version_266):
        # OFT 回写逆时针点列时，规范化为顺时针后注入
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ccw = _cw_rect_points_6()[::-1].copy()  # 逆时针
        assert _signed_area_closed(ccw) > 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ccw,
        )
        mesh = mesh_from_oft_domain(domain)
        assert _signed_area_closed(mesh.outer_boundary) < 0

    def test_clockwise_input_keeps_order_and_start(self, force_oft_version_266):
        """合法顺时针点列保持原值、原起点、原点序不变。"""
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        expected = ob.copy()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        np.testing.assert_array_equal(mesh.outer_boundary, expected)

    def test_ccw_normalization_preserves_start_point(self, force_oft_version_266):
        """逆时针转顺时针后，输出点 0 等于输入点 0，后续为输入后续反向。

        输入逆时针 [q0, q1, ..., q_(B-1)]，
        规范化后应为 [q0, q_(B-1), q_(B-2), ..., q1]（不是裸 pts[::-1]）。
        """
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ccw = _cw_rect_points_6()[::-1].copy()  # 逆时针输入
        assert _signed_area_closed(ccw) > 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ccw,
        )
        mesh = mesh_from_oft_domain(domain)
        ob = mesh.outer_boundary
        # 输出点 0 == 输入点 0
        np.testing.assert_array_equal(ob[0], ccw[0])
        # 后续点序 == 输入后续点反向：ob[1:] == ccw[:0:-1]
        np.testing.assert_array_equal(ob[1:], ccw[:0:-1])
        # 且结果顺时针
        assert _signed_area_closed(ob) < 0

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

    def test_near_duplicate_closing_point_removed_realistic(self, force_oft_version_266):
        """真实 DIII-D 回归：首末点在 Mesh2D 正式坐标尺度容差内近似重复但不逐位相等。

        真实故障（服务器 openfusiontoolkit==26.6，DIII-D g192185.02440，
        mesh_only + single_region + lcfs）：OFT 回写的 outer Region
        _resampled_points 末点与首点在 Mesh2D 正式坐标尺度容差内重复，但不逐位
        完全相等；旧实现（Adapter 容差比 Mesh2D 窄/尺度语义不同）保留了该末点，
        导致 Mesh2D 报「首点与末点相同」。

        本用例构造首末点差值小于 Mesh2D 正式坐标容差
        （coordinate_tol = 1e-12 * max(1.0, 跨度, 坐标绝对量级)）、但大于 0 的
        回写点列，断言修复后只删除一个末点、保留 >=3 点、独立副本、点 0 不变，
        且 Mesh2D 构造成功。使用 DIII-D 量级坐标（R≈1–2.3），使 abs_mag 项主导
        length_scale，从而暴露旧 Adapter 尺度差异。
        """
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()

        # DIII-D 量级顺时针 6 点边界（不重复首点）
        base = np.array([
            [1.0, -1.2],
            [1.0, 0.0],
            [1.0, 1.2],
            [2.3, 1.2],
            [2.3, 0.0],
            [2.3, -1.2],
        ], dtype=np.float64)
        # 追加一个与首点“近似重复”的显式闭合末点：
        # 差值远小于 Mesh2D coordinate_tol = 1e-12 * max(1.0, 跨度≈2.4, abs_mag≈2.3)
        # ≈ 2.4e-12，取 5e-13 保证 gap <= coordinate_tol 且 gap > 0。
        near_first = base[0] + np.array([5e-13, -5e-13], dtype=np.float64)
        ob_near_closed = np.vstack([base, near_first])
        assert not np.array_equal(ob_near_closed[0], ob_near_closed[-1])  # 不逐位相等
        gap = float(np.hypot(
            ob_near_closed[0, 0] - ob_near_closed[-1, 0],
            ob_near_closed[0, 1] - ob_near_closed[-1, 1],
        ))
        assert gap > 0.0

        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob_near_closed,
        )
        mesh = mesh_from_oft_domain(domain)

        # 只删除一个末点：7 → 6
        assert mesh.outer_boundary.shape[0] == 6
        assert mesh.outer_boundary.shape[0] >= 3
        # (B,2) float64
        assert mesh.outer_boundary.ndim == 2
        assert mesh.outer_boundary.shape[1] == 2
        assert mesh.outer_boundary.dtype == np.float64
        # 输出点 0 保持不变（等于原首点）
        np.testing.assert_array_equal(mesh.outer_boundary[0], base[0])
        # 独立副本：不与 Region 回写数组共享内存
        assert not np.shares_memory(mesh.outer_boundary, region._resampled_points)
        # 删除后首末点不再逐位相等（Mesh2D 已成功构造，未抛异常）
        assert not np.array_equal(
            mesh.outer_boundary[0], mesh.outer_boundary[-1]
        )

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
        assert mesh.outer_boundary is not region._resampled_points
        assert not np.shares_memory(mesh.outer_boundary, region._resampled_points)

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

    def test_steiner_points_not_in_outer_boundary(self, force_oft_version_266):
        """模拟最终 Triangle 输出含额外 Steiner 点：不进入 outer_boundary。

        build_mesh 返回的 pts 含一个额外内部节点（模拟 Steiner），
        但 outer Region 回写点列只有 6 个原始边界重采样点，
        outer_boundary 必须只含这 6 点，不含 Steiner 坐标。
        """
        pts = np.array([
            [0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0],
            [1.0, 1.0],   # 模拟 Steiner/内部节点
        ], dtype=np.float64)
        lc = np.array([
            [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4],
        ], dtype=np.int32)
        reg = np.array([1, 1, 1, 1], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()  # 不含 (1,1)
        domain = FakeDomain(
            pts, lc, reg, _region_info([1]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)
        steiner = np.array([1.0, 1.0], dtype=np.float64)
        contains = np.any(np.all(mesh.outer_boundary == steiner, axis=1))
        assert not contains

    def test_boundary_steiner_point_isolation_realistic(self, force_oft_version_266):
        """真实模拟 boundary Steiner point 隔离（本轮任务十三）。

        Region 回写点列描述 Triangle 输入前外边界（顺时针四角）：
            (0,0),(0,2),(2,2),(2,0)
        最终 pts 在底部外边界边上增加中点 (1,0)（模拟 Triangle 输出后新增的
        boundary Steiner point），并增加中心点 (1,1)。
        最终三角连接沿有序边界节点
            (0,0)->(0,2)->(2,2)->(2,0)->(1,0)->(0,0)
        形成以中心点 (1,1) 为公共顶点的扇形，使 (1,0) 参与两条只出现一次的
        拓扑外边界边。

        断言：
            - outer_boundary 只含四角，不含 (1,0)；
            - nodes 仍含 (1,0)。
        """
        # 有序外边界节点（顺时针）：
        #   0:(0,0) 1:(0,2) 2:(2,2) 3:(2,0) 4:(1,0)  中心 5:(1,1)
        pts = np.array([
            [0.0, 0.0],   # 0
            [0.0, 2.0],   # 1
            [2.0, 2.0],   # 2
            [2.0, 0.0],   # 3
            [1.0, 0.0],   # 4  底部外边界边上的 Steiner 中点
            [1.0, 1.0],   # 5  中心点
        ], dtype=np.float64)
        # 扇形三角：沿有序边界环 0->1->2->3->4->0，公共顶点 5
        lc = np.array([
            [0, 1, 5],
            [1, 2, 5],
            [2, 3, 5],
            [3, 4, 5],
            [4, 0, 5],
        ], dtype=np.int32)
        reg = np.array([1, 1, 1, 1, 1], dtype=np.int32)

        region = FakeRegion()
        # Triangle 输入前外边界（四角，顺时针），不含 (1,0)
        ob = np.array([
            [0.0, 0.0],
            [0.0, 2.0],
            [2.0, 2.0],
            [2.0, 0.0],
        ], dtype=np.float64)
        assert _signed_area_closed(ob) < 0
        domain = FakeDomain(
            pts, lc, reg, _region_info([1]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh = mesh_from_oft_domain(domain)

        steiner = np.array([1.0, 0.0], dtype=np.float64)
        # outer_boundary 不含 (1,0)
        in_ob = np.any(np.all(mesh.outer_boundary == steiner, axis=1))
        assert not in_ob
        assert mesh.outer_boundary.shape[0] == 4
        # nodes 仍含 (1,0)
        in_nodes = np.any(np.all(mesh.nodes == steiner, axis=1))
        assert in_nodes

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


class TestMeshFromOftDomainOuterRegionSavedBeforeBuild:
    """build 前保存 outer Region 局部引用，build 后读取同一个原对象。"""

    def test_reads_original_region_not_replaced_one(self, force_oft_version_266):
        """build_mesh 期间 domain 上的私有属性被替换，仍读原对象点列。"""
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)

        # 原 outer Region：build 时被回写合法点列
        original = FakeRegion()
        ob_original = _cw_rect_points_6()

        # 替换 Region：带错误/不同点列（若被误读则测试值会不同）
        replacement = FakeRegion()
        replacement._resampled_points = _cw_rect_points_4()  # 仅 4 点，明显不同

        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=original, resampled_on_build=ob_original,
            replace_attr_on_build=replacement,
        )
        mesh = mesh_from_oft_domain(domain)
        # 必须读原对象（6 点），而非替换对象（4 点）
        assert mesh.outer_boundary.shape[0] == 6
        np.testing.assert_array_equal(mesh.outer_boundary, ob_original)
        # 确认 domain 上的属性确实已被替换为 4 点 Region
        current = getattr(domain, _OUTER_REGION_ATTR)
        assert current is replacement
        assert current._resampled_points.shape[0] == 4

    def test_replacement_region_none_still_reads_original(self, force_oft_version_266):
        """替换对象即使 _resampled_points 为 None，也不影响读原对象。"""
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        original = FakeRegion()
        ob_original = _cw_rect_points_6()
        replacement = FakeRegion()  # _resampled_points 保持 None
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=original, resampled_on_build=ob_original,
            replace_attr_on_build=replacement,
        )
        mesh = mesh_from_oft_domain(domain)
        assert mesh.outer_boundary.shape[0] == 6
        np.testing.assert_array_equal(mesh.outer_boundary, ob_original)

    def test_build_mesh_called_once_with_outer_region(self, force_oft_version_266):
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        ob = _cw_rect_points_6()
        domain = FakeDomain(
            pts, lc, reg, _region_info([1, 2]),
            outer_region=region, resampled_on_build=ob,
        )
        mesh_from_oft_domain(domain)
        assert domain.build_mesh_call_count == 1


class TestMeshFromOftDomainOuterBoundaryFailures:
    """outer Region 私有接口失败即停（不回退四角/idxevert/自行重采样）。"""

    def test_missing_resampled_points_attr_fails(self, force_oft_version_266):
        # 捕获的 outer Region 缺少 _resampled_points 属性
        class NoAttrRegion:
            __slots__ = ()  # 明确不允许有 _resampled_points

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

    def test_resampled_points_too_few_after_dedup_fails(self, force_oft_version_266):
        # 4 点里末点重复首点 → 删 1 后 3 点合法；此处构造删后仅 2 点失败
        pts, lc = _square_two_triangles()
        reg = np.array([1, 2], dtype=np.int32)
        region = FakeRegion()
        # 3 点，末点重复首点 → 删后 2 点 → 失败
        bad = np.array([[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]], dtype=np.float64)
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
        - define_region / add_polygon / add_annulus 记录调用；
        - add_rectangle 调用时向 regions 追加一个 Region 对象（模拟 OFT 行为）。
    不虚构任何公共边界 API。
    """

    def __init__(self):
        self.define_region = MagicMock()
        self.add_polygon = MagicMock()
        self.add_annulus = MagicMock()
        self.regions = []
        # add_rectangle 追加一个 Region 到 regions
        self.add_rectangle = MagicMock(side_effect=self._add_rectangle)

    def _add_rectangle(self, *args, **kwargs):
        self.regions.append(FakeRegion())


class TestBuildOftDomainWithWall:
    """有第一壁：三区域 OUTER/PLASMA/VACUUM，annulus + rectangle，不 build_mesh。"""

    def test_three_regions_annulus_rectangle_no_build_mesh(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)

        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            result = build_oft_domain_from_gfile(gfile)

        assert result is holder
        define_names = [c.args[0] for c in holder.define_region.call_args_list]
        assert "outer" in define_names
        assert "plasma" in define_names
        assert "vacuum" in define_names
        assert holder.add_annulus.called
        assert holder.add_rectangle.called
        # 不调用 build_mesh（DomainHolder 无 build_mesh 属性）
        assert not hasattr(holder, "build_mesh_called")

    def test_wall_uses_rectangle_named_outer(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_oft_domain_from_gfile(gfile)

        _, kwargs = holder.add_rectangle.call_args
        assert kwargs.get("name") == "outer"

    def test_wall_outer_region_captured(self):
        """有壁路径同样捕获 outer Region 引用（regions[-1]）。"""
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_oft_domain_from_gfile(gfile)

        outer_region = getattr(domain, _OUTER_REGION_ATTR, None)
        assert outer_region is not None
        # 捕获的是 regions 最后一个（add_rectangle 追加的那个）
        assert outer_region is holder.regions[-1]


class TestBuildOftDomainNoWall:
    """无第一壁：两区域 OUTER/PLASMA，polygon + rectangle，不 build_mesh。"""

    def test_two_regions_polygon_rectangle_no_build_mesh(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            result = build_oft_domain_from_gfile(gfile)

        assert result is holder
        define_names = [c.args[0] for c in holder.define_region.call_args_list]
        assert "outer" in define_names
        assert "plasma" in define_names
        assert "vacuum" not in define_names
        assert holder.add_polygon.called
        assert holder.add_rectangle.called
        assert not holder.add_annulus.called

    def test_nowall_outer_region_captured(self):
        """无壁路径捕获 outer Region 引用（与有壁同一逻辑）。"""
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_oft_domain_from_gfile(gfile)

        outer_region = getattr(domain, _OUTER_REGION_ATTR, None)
        assert outer_region is not None
        assert outer_region is holder.regions[-1]


class TestBuildOftDomainOuterRegionCapture:
    """outer Region 捕获细节：捕获对象引用而非四角数组。"""

    def test_captured_attr_is_region_object_not_array(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_oft_domain_from_gfile(gfile)

        captured = getattr(domain, _OUTER_REGION_ATTR)
        # 捕获的是 Region 对象（具 _resampled_points 属性），不是 ndarray 四角
        assert not isinstance(captured, np.ndarray)
        assert hasattr(captured, "_resampled_points")

    def test_regions_increment_exactly_one(self):
        """add_rectangle 后 regions 恰好新增一个 Region。"""
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_oft_domain_from_gfile(gfile)

        # DomainHolder 只在 add_rectangle 时追加一个 Region
        assert len(holder.regions) == 1

    def test_missing_regions_container_fails(self):
        """domain 无 regions 容器时捕获失败即停。"""
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class NoRegionsDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.add_polygon = MagicMock()
                self.add_annulus = MagicMock()
                self.add_rectangle = MagicMock()
                # 无 regions 属性

        holder = NoRegionsDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="regions"):
                build_oft_domain_from_gfile(gfile)

    def test_regions_not_incremented_fails(self):
        """add_rectangle 未使 regions 增加一个时失败即停。"""
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class NoIncrementDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.add_polygon = MagicMock()
                self.add_annulus = MagicMock()
                self.regions = []
                # add_rectangle 不向 regions 追加
                self.add_rectangle = MagicMock()

        holder = NoIncrementDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="新增一个 Region|regions"):
                build_oft_domain_from_gfile(gfile)

    def test_regions_incremented_more_than_one_fails(self):
        """add_rectangle 新增超过一个 Region 时失败即停。"""
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class MultiIncrementDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.add_polygon = MagicMock()
                self.add_annulus = MagicMock()
                self.regions = []
                self.add_rectangle = MagicMock(side_effect=self._add_two)

            def _add_two(self, *args, **kwargs):
                # 追加两个 Region，破坏“恰好新增一个”不变式
                self.regions.append(FakeRegion())
                self.regions.append(FakeRegion())

        holder = MultiIncrementDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="新增一个 Region|regions"):
                build_oft_domain_from_gfile(gfile)

    def test_cannot_attach_private_attr_fails_with_cause(self):
        """domain 拒绝附加 _linkmesh_outer_region 时立即失败并保留异常链。

        使用真实的 __setattr__ 机制显式拒绝该私有属性（不依赖 MagicMock 偶然
        行为），同时保留策略层需要的其他接口（define_region/add_polygon/
        add_annulus/add_rectangle/regions）。
        """
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class RejectingDomain:
            def __init__(self):
                # 用 object.__setattr__ 绕过自定义拒绝逻辑设置内部字段
                object.__setattr__(self, "define_region", MagicMock())
                object.__setattr__(self, "add_polygon", MagicMock())
                object.__setattr__(self, "add_annulus", MagicMock())
                object.__setattr__(self, "regions", [])
                object.__setattr__(
                    self, "add_rectangle", MagicMock(side_effect=self._add_rectangle)
                )

            def _add_rectangle(self, *args, **kwargs):
                self.regions.append(FakeRegion())

            def __setattr__(self, name, value):
                if name == _OUTER_REGION_ATTR:
                    raise AttributeError(
                        f"该 domain 明确拒绝附加私有属性 {name}"
                    )
                object.__setattr__(self, name, value)

        holder = RejectingDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(RuntimeError) as ei:
                build_oft_domain_from_gfile(gfile)

        # 保留原始异常链
        assert ei.value.__cause__ is not None
        assert isinstance(ei.value.__cause__, AttributeError)
        # 错误信息含私有属性名，明确未静默 pass
        assert _OUTER_REGION_ATTR in str(ei.value)


class TestBuildOftDomainNormalization:
    """轮廓薄规范化行为。"""

    def test_duplicate_closing_point_removed_only_last(self):
        # LCFS 首尾重复：正方形 + 追加首点
        r = np.array([0.0, 1.0, 1.0, 0.0, 0.0], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0, 1.0, 0.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)

        holder = DomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_oft_domain_from_gfile(gfile)

        # add_polygon 收到的 LCFS 应删除末尾重复点，剩 4 点
        contour = holder.add_polygon.call_args.args[0]
        assert contour.shape == (4, 2)


class TestBuildOftDomainInputFailures:
    """输入非法失败（不依赖 OFT，参数/轮廓校验先行）。"""

    def test_wall_r_only_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, None)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_wall_length_mismatch_fails(self):
        # 第一壁 R/Z 同时存在但长度不一致，应在 _load_gs_domain_class 前失败
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5], dtype=np.float64)  # 长度 3 != 4
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_wall_nan_fails(self):
        # 第一壁含 NaN，应在 _load_gs_domain_class 前失败
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, np.nan], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_wall_inf_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, np.inf], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)
        with pytest.raises(ValueError):
            build_oft_domain_from_gfile(gfile)

    def test_wall_too_few_points_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)
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

    def test_generate_mesh_single_region_lcfs_dispatch(self):
        # profile=single_region + boundary_source=lcfs 走 single-region 策略层。
        sentinel_domain = object()
        sentinel_mesh = object()
        gfile = FakeGFileData(*_square_contour(), None, None)

        with patch(
            "linkmesh.mesher.oft_adapter.build_single_region_domain_from_lcfs",
            return_value=sentinel_domain,
        ) as m_build_sr, patch(
            "linkmesh.mesher.oft_adapter.mesh_from_oft_domain",
            return_value=sentinel_mesh,
        ) as m_mesh, patch(
            "linkmesh.mesher.oft_adapter.build_oft_domain_from_gfile",
        ) as m_build_nested:
            result = generate_mesh(
                gfile,
                plasma_dx=0.07,
                profile="single_region",
                boundary_source="lcfs",
            )

        # 走 single-region 策略层，不走 nested 策略层
        m_build_sr.assert_called_once()
        _, kwargs = m_build_sr.call_args
        assert kwargs["plasma_dx"] == 0.07
        assert not m_build_nested.called
        m_mesh.assert_called_once_with(sentinel_domain)
        assert result is sentinel_mesh

    def test_generate_mesh_unimplemented_combo_raises(self):
        # 未实现的 profile/source 组合应抛 NotImplementedError（不回退 nested）。
        gfile = FakeGFileData(*_square_contour(), None, None)
        with pytest.raises(NotImplementedError):
            generate_mesh(
                gfile,
                profile="single_region",
                boundary_source="first_wall",
            )


# ==========================================================================
# D. build_single_region_domain_from_lcfs()：LCFS 单区域来源策略层
#    （v2.3 输入层 II）
# ==========================================================================

class SingleRegionDomainHolder:
    """LCFS 单区域来源策略层专用假 domain。

    模拟服务器已确认关系：
        - define_region 记录调用；
        - add_polygon 调用时向 regions 追加恰好一个 Region（模拟 OFT 行为）；
        - 不提供 add_rectangle / add_annulus，若被误调用会 AttributeError。
    LCFS 单区域来源策略层不应调用 add_rectangle / add_annulus。
    """

    def __init__(self):
        self.define_region = MagicMock()
        self.regions = []
        self.add_polygon = MagicMock(side_effect=self._add_polygon)

    def _add_polygon(self, *args, **kwargs):
        self.regions.append(FakeRegion())


class TestSingleRegionPolygonNormalization:
    """single-region polygon 相邻近重复控制点的稳定过滤。"""

    def test_removes_realistic_near_duplicate_and_preserves_input(self):
        original = np.array([
            [1.0, 0.0],
            [1.0 + 3e-9, 0.0],
            [2.0, 0.0],
            [2.0, 1.0],
            [1.0, 1.0],
        ], dtype=np.float64)
        snapshot = original.copy()

        result = _normalize_single_region_polygon(original)

        expected = np.array([
            [1.0, 0.0],
            [2.0, 0.0],
            [2.0, 1.0],
            [1.0, 1.0],
        ], dtype=np.float64)
        np.testing.assert_array_equal(result, expected)
        np.testing.assert_array_equal(original, snapshot)
        assert result.shape[0] == original.shape[0] - 1
        assert result.dtype == np.float64
        assert not np.shares_memory(result, original)

    def test_threshold_is_strict_and_not_numpy_allclose(self):
        # 5e-5 m 大于 Mesh2D 的 1e-12 尺度容差，但小于 OFT merge_thresh，
        # 因此必须删除。
        below = np.array([
            [1.0, 0.0],
            [1.0 + 5e-5, 0.0],
            [2.0, 0.0],
            [2.0, 1.0],
            [1.0, 1.0],
        ], dtype=np.float64)
        below_result = _normalize_single_region_polygon(below)
        assert below_result.shape[0] == 4
        np.testing.assert_array_equal(below_result[0], below[0])
        np.testing.assert_array_equal(below_result[1], below[2])

        # 坐标绝对量级很大时 np.allclose 默认相对容差会把相距 1e-4 m 的点
        # 判断为接近；正式规则使用显式欧氏距离且仅删除严格小于阈值的点。
        at_threshold = np.array([
            [1.0e6, 0.0],
            [1.0e6 + 1e-4, 0.0],
            [1.0e6 + 1.0, 0.0],
            [1.0e6 + 1.0, 1.0],
            [1.0e6, 1.0],
        ], dtype=np.float64)
        assert np.allclose(at_threshold[0], at_threshold[1])
        threshold_result = _normalize_single_region_polygon(at_threshold)
        assert threshold_result.shape[0] == at_threshold.shape[0]
        np.testing.assert_array_equal(threshold_result, at_threshold)

    def test_stable_filter_uses_last_accepted_and_not_global_dedup(self):
        points = np.array([
            [0.0, 0.0],
            [3e-9, 0.0],
            [6e-9, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [1.0, 0.0],  # 与较早的非相邻点重复，helper 不做全局去重
        ], dtype=np.float64)

        result = _normalize_single_region_polygon(points)

        expected = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [1.0, 0.0],
        ], dtype=np.float64)
        np.testing.assert_array_equal(result, expected)

    def test_fails_when_fewer_than_three_points_remain(self):
        points = np.array([
            [0.0, 0.0],
            [3e-9, 0.0],
            [6e-9, 0.0],
            [1.0, 0.0],
        ], dtype=np.float64)
        with pytest.raises(ValueError, match="不足 3 个点"):
            _normalize_single_region_polygon(points)

    def test_fails_when_filter_leaves_near_duplicate_closing_edge(self):
        points = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 5e-5],
        ], dtype=np.float64)
        with pytest.raises(ValueError, match="首末点距离"):
            _normalize_single_region_polygon(points)

    @pytest.mark.parametrize(
        "bad",
        [
            np.array([0.0, 1.0, 2.0], dtype=np.float64),
            np.array([[0.0, 0.0], [1.0, np.nan], [1.0, 1.0]], dtype=np.float64),
            np.array([[0.0, 0.0], [1.0, np.inf], [1.0, 1.0]], dtype=np.float64),
        ],
    )
    def test_rejects_invalid_shape_or_non_finite_input(self, bad):
        with pytest.raises(ValueError):
            _normalize_single_region_polygon(bad)


class TestBuildSingleRegionDomainFromLcfs:
    """LCFS 单区域来源策略层：单 polygon、不 rectangle/annulus、plasma_dx。"""

    def test_single_polygon_region_created(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            result = build_single_region_domain_from_lcfs(gfile)

        assert result is holder
        # add_polygon 恰好调用一次
        assert holder.add_polygon.call_count == 1
        # Domain 只有一个 Region
        assert len(holder.regions) == 1

    def test_no_rectangle_no_annulus(self):
        # LCFS 单区域来源策略层不创建人工矩形、不创建 annulus。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_single_region_domain_from_lcfs(gfile)

        # holder 不提供 add_rectangle / add_annulus，若被调用会立即 AttributeError。
        # 显式断言这两个属性未被生产代码添加/调用。
        assert not hasattr(holder, "add_rectangle")
        assert not hasattr(holder, "add_annulus")

    def test_does_not_use_first_wall(self):
        # 即便 GFile 提供第一壁，LCFS 单区域来源也不消费第一壁。
        lcfs_r, lcfs_z = _square_contour()
        wall_r = np.array([-0.5, 1.5, 1.5, -0.5], dtype=np.float64)
        wall_z = np.array([-0.5, -0.5, 1.5, 1.5], dtype=np.float64)
        gfile = FakeGFileData(lcfs_r, lcfs_z, wall_r, wall_z)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_single_region_domain_from_lcfs(gfile)

        # 只有一个 Region（未因第一壁额外建区）
        assert len(holder.regions) == 1
        # add_polygon 收到的轮廓是 LCFS（四点），不是 wall
        contour = holder.add_polygon.call_args.args[0]
        assert contour.shape == (4, 2)
        # 轮廓 R 范围与 LCFS 一致（[0,1]），不含 wall 的 -0.5/1.5
        assert contour[:, 0].min() == 0.0
        assert contour[:, 0].max() == 1.0

    def test_uses_plasma_dx_as_mesh_scale(self):
        # single-region 网格尺度使用 plasma_dx，经 define_region 传入。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_single_region_domain_from_lcfs(gfile, plasma_dx=0.055)

        # define_region 至少被调用一次，且 dx 参数为 plasma_dx（第二个位置参数）
        assert holder.define_region.call_count >= 1
        found_dx = False
        for call in holder.define_region.call_args_list:
            args = call.args
            if len(args) >= 2 and args[1] == 0.055:
                found_dx = True
        assert found_dx

    def test_captures_added_polygon_region(self):
        # 捕获的是 add_polygon 新增的 Region 对象（regions[-1]），不写死 ID。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)

        captured = getattr(domain, _OUTER_REGION_ATTR, None)
        assert captured is not None
        assert captured is holder.regions[-1]
        # 捕获的是 Region 对象（具 _resampled_points），不是 ndarray
        assert not isinstance(captured, np.ndarray)
        assert hasattr(captured, "_resampled_points")

    def test_does_not_call_build_mesh(self):
        # Domain 构造阶段不调用 build_mesh（holder 无 build_mesh 属性即证明）。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_single_region_domain_from_lcfs(gfile)

        assert not hasattr(holder, "build_mesh")

    def test_near_duplicate_control_point_removed_before_add_polygon(self):
        # 复现真实根因：point 1 与 point 0 相距约 3e-9 m，会被 OFT 默认
        # merge_thresh=1e-4 m 合并。策略层必须保留 point 0、删除 point 1。
        r = np.array([1.0, 1.0 + 3e-9, 2.0, 2.0, 1.0], dtype=np.float64)
        z = np.array([0.0, 0.0, 0.0, 1.0, 1.0], dtype=np.float64)
        r_snapshot = r.copy()
        z_snapshot = z.copy()
        gfile = FakeGFileData(r, z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(
                gfile, plasma_dx=0.055
            )

        assert holder.add_polygon.call_count == 1
        contour = holder.add_polygon.call_args.args[0]
        expected = np.array([
            [1.0, 0.0],
            [2.0, 0.0],
            [2.0, 1.0],
            [1.0, 1.0],
        ], dtype=np.float64)
        np.testing.assert_array_equal(contour, expected)
        np.testing.assert_array_equal(r, r_snapshot)
        np.testing.assert_array_equal(z, z_snapshot)
        assert contour.dtype == np.float64
        assert getattr(domain, _OUTER_REGION_ATTR) is holder.regions[-1]
        define_call = holder.define_region.call_args
        assert define_call.args[1] == 0.055
        assert not hasattr(holder, "add_rectangle")
        assert not hasattr(holder, "add_annulus")
        assert not hasattr(holder, "build_mesh")

    def test_duplicate_closing_point_removed_only_last(self):
        # LCFS 首尾重复：add_polygon 收到删除末尾重复点后的 4 点轮廓。
        r = np.array([0.0, 1.0, 1.0, 0.0, 0.0], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0, 1.0, 0.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)

        holder = SingleRegionDomainHolder()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            build_single_region_domain_from_lcfs(gfile)

        contour = holder.add_polygon.call_args.args[0]
        assert contour.shape == (4, 2)


class TestBuildSingleRegionDomainInputFailures:
    """LCFS 单区域来源策略层输入非法失败（LCFS/参数校验先于 OFT）。"""

    def test_lcfs_length_mismatch_fails(self):
        r = np.array([0.0, 1.0, 0.5], dtype=np.float64)
        z = np.array([0.0, 0.0], dtype=np.float64)  # 长度不一致
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile)

    def test_lcfs_too_few_points_fails(self):
        r = np.array([0.0, 1.0], dtype=np.float64)
        z = np.array([0.0, 0.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile)

    def test_lcfs_nan_fails(self):
        r = np.array([0.0, 1.0, np.nan], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile)

    def test_lcfs_inf_fails(self):
        r = np.array([0.0, 1.0, np.inf], dtype=np.float64)
        z = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        gfile = FakeGFileData(r, z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile)

    def test_plasma_dx_non_positive_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile, plasma_dx=0.0)

    def test_plasma_dx_non_finite_fails(self):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        with pytest.raises(ValueError):
            build_single_region_domain_from_lcfs(gfile, plasma_dx=np.inf)

    def test_missing_regions_container_fails(self):
        # domain 无 regions 容器时捕获失败即停。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class NoRegionsDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.add_polygon = MagicMock()
                # 无 regions 属性

        holder = NoRegionsDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="regions"):
                build_single_region_domain_from_lcfs(gfile)

    def test_add_polygon_not_incremented_fails(self):
        # add_polygon 未使 regions 增加一个时失败即停。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class NoIncrementDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.regions = []
                # add_polygon 不向 regions 追加
                self.add_polygon = MagicMock()

        holder = NoIncrementDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="新增一个 Region|regions"):
                build_single_region_domain_from_lcfs(gfile)

    def test_add_polygon_incremented_more_than_one_fails(self):
        # add_polygon 新增超过一个 Region 时失败即停。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class MultiIncrementDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.regions = []
                self.add_polygon = MagicMock(side_effect=self._add_two)

            def _add_two(self, *args, **kwargs):
                self.regions.append(FakeRegion())
                self.regions.append(FakeRegion())

        holder = MultiIncrementDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(ValueError, match="新增一个 Region|regions"):
                build_single_region_domain_from_lcfs(gfile)

    def test_cannot_attach_private_attr_fails_with_cause(self):
        # domain 拒绝附加 _linkmesh_outer_region 时立即失败并保留异常链。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        class RejectingDomain:
            def __init__(self):
                object.__setattr__(self, "define_region", MagicMock())
                object.__setattr__(self, "regions", [])
                object.__setattr__(
                    self, "add_polygon", MagicMock(side_effect=self._add_polygon)
                )

            def _add_polygon(self, *args, **kwargs):
                self.regions.append(FakeRegion())

            def __setattr__(self, name, value):
                if name == _OUTER_REGION_ATTR:
                    raise AttributeError(
                        f"该 domain 明确拒绝附加私有属性 {name}"
                    )
                object.__setattr__(self, name, value)

        holder = RejectingDomain()
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            with pytest.raises(RuntimeError) as ei:
                build_single_region_domain_from_lcfs(gfile)

        assert ei.value.__cause__ is not None
        assert isinstance(ei.value.__cause__, AttributeError)
        assert _OUTER_REGION_ATTR in str(ei.value)


class TestSingleRegionLcfsEndToEndWithMesh:
    """LCFS 单区域来源策略层 + mesh_from_oft_domain 端到端边界回写（版本锁定隔离）。

    使用 SingleRegionBuildDomain：既能被 build_single_region_domain_from_lcfs
    捕获 Region，又能在 build_mesh 后回写点列，验证完整数据链：
        LCFS → add_polygon 捕获 Region → build_mesh 回写 _resampled_points
             → Mesh2D.outer_boundary（非原始 LCFS 控制点）。
    """

    def _make_single_region_domain(self, resampled_on_build,
                                    replace_attr_on_build=None):
        """构造一个 single-region 假 domain，支持被策略层捕获并在 build 回写。"""
        pts, lc = _square_two_triangles()
        reg = np.array([1, 1], dtype=np.int32)

        class SingleRegionBuildDomain:
            def __init__(self):
                self.define_region = MagicMock()
                self.regions = []
                self.add_polygon = MagicMock(side_effect=self._add_polygon)
                self.region_info = _region_info([1])
                self.build_mesh_call_count = 0
                self._resampled_on_build = resampled_on_build
                self._replace = replace_attr_on_build
                self._captured_region = None

            def _add_polygon(self, *args, **kwargs):
                r = FakeRegion()
                self._captured_region = r
                self.regions.append(r)

            def build_mesh(self):
                self.build_mesh_call_count += 1
                if self._captured_region is not None:
                    self._captured_region._resampled_points = self._resampled_on_build
                if self._replace is not None:
                    setattr(self, _OUTER_REGION_ATTR, self._replace)
                return pts, lc, reg

        return SingleRegionBuildDomain()

    def test_outer_boundary_from_readback_not_raw_lcfs(self, force_oft_version_266):
        # LCFS 控制点为正方形（4 点，[0,1]×[0,1]）；OFT 回写点列为 6 点、坐标不同。
        # outer_boundary 必须来自回写点列，与原始 LCFS 明显不同。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        ob = _cw_rect_points_6()  # 6 点，[0,2]×[0,2]
        holder = self._make_single_region_domain(resampled_on_build=ob)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)

        mesh = mesh_from_oft_domain(domain)

        # build_mesh 只调用一次
        assert holder.build_mesh_call_count == 1
        # outer_boundary 来自回写点列（6 点），非原始 LCFS 控制点（4 点）
        assert mesh.outer_boundary.shape == (6, 2)
        assert mesh.outer_boundary.dtype == np.float64
        # 与原始 LCFS 控制点明显不同：LCFS R 范围 [0,1]，回写 R 范围 [0,2]
        raw_lcfs = np.column_stack([lcfs_r, lcfs_z])
        assert mesh.outer_boundary.shape[0] != raw_lcfs.shape[0]
        assert mesh.outer_boundary[:, 0].max() == 2.0
        # 精确等于回写点列（顺时针未反转）
        np.testing.assert_array_equal(mesh.outer_boundary, ob)

    def test_outer_boundary_independent_of_region_array(self, force_oft_version_266):
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        ob = _cw_rect_points_6()
        holder = self._make_single_region_domain(resampled_on_build=ob)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        mesh = mesh_from_oft_domain(domain)

        captured = getattr(domain, _OUTER_REGION_ATTR)
        # 修改 Region 回写源数组不影响已注入 Mesh2D 副本；不共享内存
        captured._resampled_points[0, 0] = 999.0
        assert mesh.outer_boundary[0, 0] != 999.0
        assert not np.shares_memory(
            mesh.outer_boundary, captured._resampled_points
        )

    def test_ccw_readback_normalized_keeps_start_point(self, force_oft_version_266):
        # 逆时针回写点列转顺时针时保持点 0。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        ccw = _cw_rect_points_6()[::-1].copy()
        assert _signed_area_closed(ccw) > 0
        holder = self._make_single_region_domain(resampled_on_build=ccw)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        mesh = mesh_from_oft_domain(domain)

        ob = mesh.outer_boundary
        # 顺时针
        assert _signed_area_closed(ob) < 0
        # 输出点 0 == 输入点 0
        np.testing.assert_array_equal(ob[0], ccw[0])

    def test_near_duplicate_closing_point_removed_end_to_end(self, force_oft_version_266):
        """端到端真实回归：LCFS 单区域 build 回写近似重复闭合末点被删除。

        直接复现服务器真实故障链
        （build_single_region_domain_from_lcfs → mesh_from_oft_domain → Mesh2D）：
        OFT 回写点列末点与首点在 Mesh2D 正式坐标尺度容差内近似重复但不逐位相等。
        修复后 Mesh2D 构造成功，只删除一个末点、保留点 0、独立副本。
        """
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)

        base = np.array([
            [1.0, -1.2],
            [1.0, 0.0],
            [1.0, 1.2],
            [2.3, 1.2],
            [2.3, 0.0],
            [2.3, -1.2],
        ], dtype=np.float64)
        near_first = base[0] + np.array([5e-13, -5e-13], dtype=np.float64)
        ob_near_closed = np.vstack([base, near_first])
        assert not np.array_equal(ob_near_closed[0], ob_near_closed[-1])

        holder = self._make_single_region_domain(resampled_on_build=ob_near_closed)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        mesh = mesh_from_oft_domain(domain)

        # 只删除一个末点：7 → 6，且 Mesh2D 构造成功
        assert mesh.outer_boundary.shape[0] == 6
        assert mesh.outer_boundary.shape[0] >= 3
        assert mesh.outer_boundary.dtype == np.float64
        np.testing.assert_array_equal(mesh.outer_boundary[0], base[0])
        assert not np.array_equal(
            mesh.outer_boundary[0], mesh.outer_boundary[-1]
        )

    def test_reads_original_region_when_replaced_during_build(self, force_oft_version_266):
        # build 中替换 domain 上保存的 Region 引用时，仍读 build 前保存的原对象。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        ob_original = _cw_rect_points_6()
        replacement = FakeRegion()
        replacement._resampled_points = _cw_rect_points_4()  # 4 点，明显不同
        holder = self._make_single_region_domain(
            resampled_on_build=ob_original,
            replace_attr_on_build=replacement,
        )
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        mesh = mesh_from_oft_domain(domain)

        # 读原对象（6 点），非替换对象（4 点）
        assert mesh.outer_boundary.shape[0] == 6
        np.testing.assert_array_equal(mesh.outer_boundary, ob_original)

    def test_resampled_none_after_build_fails(self, force_oft_version_266):
        # build 后原 Region 未回写（_resampled_points 仍 None）→ 失败即停。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        holder = self._make_single_region_domain(resampled_on_build=None)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        with pytest.raises(ValueError, match="None"):
            mesh_from_oft_domain(domain)

    def test_resampled_bad_shape_fails(self, force_oft_version_266):
        # 回写点列 shape 非法 → 失败即停。
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        bad = np.array([1.0, 2.0, 3.0], dtype=np.float64)  # 一维
        holder = self._make_single_region_domain(resampled_on_build=bad)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        with pytest.raises(ValueError):
            mesh_from_oft_domain(domain)

    def test_version_mismatch_fails_when_reading(self, monkeypatch):
        # OFT 版本不为 26.6 时，读取回写点列前明确失败。
        monkeypatch.setattr(adapter, "_get_installed_oft_version", lambda: "27.0")
        lcfs_r, lcfs_z = _square_contour()
        gfile = FakeGFileData(lcfs_r, lcfs_z, None, None)
        ob = _cw_rect_points_6()
        holder = self._make_single_region_domain(resampled_on_build=ob)
        fake_gs_domain_cls = MagicMock(return_value=holder)
        with patch(
            "linkmesh.mesher.oft_adapter._load_gs_domain_class",
            return_value=fake_gs_domain_cls,
        ):
            domain = build_single_region_domain_from_lcfs(gfile)
        with pytest.raises(ValueError, match="openfusiontoolkit"):
            mesh_from_oft_domain(domain)
