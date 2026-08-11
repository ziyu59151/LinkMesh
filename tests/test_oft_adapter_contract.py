from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from linkmesh.mesher import oft_adapter
from linkmesh.mesher.oft_adapter import (
    _OUTER_REGION_ATTR,
    build_oft_domain_from_gfile,
    build_single_region_domain_from_boundary,
    generate_multi_region_mesh,
    inspect_multi_region_ids,
    mesh_from_oft_domain,
)
from linkmesh.regions import build_region_plan


def _mesh_arrays():
    nodes = np.array(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=np.float64,
    )
    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    return nodes, triangles


class _Region:
    def __init__(self):
        self._resampled_points = None


class _Domain:
    def __init__(self, *, replace_region=False):
        self.nodes, self.triangles = _mesh_arrays()
        self.region_info = {"temporary": {"id": 9}}
        self.original_region = _Region()
        self.replacement_region = _Region()
        self.replace_region = replace_region
        setattr(self, _OUTER_REGION_ATTR, self.original_region)

    def build_mesh(self):
        self.region_info = {"final": {"id": 1}}
        self.original_region._resampled_points = np.array(
            [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
            dtype=np.float64,
        )
        if self.replace_region:
            self.replacement_region._resampled_points = np.array(
                [[0.0, 0.0], [0.0, 2.0], [2.0, 0.0]],
                dtype=np.float64,
            )
            setattr(self, _OUTER_REGION_ATTR, self.replacement_region)
        return (
            self.nodes,
            self.triangles,
            np.array([1, 1], dtype=np.int32),
        )


def test_build_mesh_output_uses_final_region_ids_and_owned_boundary(monkeypatch):
    monkeypatch.setattr(
        oft_adapter,
        "_get_installed_oft_version",
        lambda: "26.6",
    )
    domain = _Domain(replace_region=True)

    mesh = mesh_from_oft_domain(domain)

    assert mesh.nodes.shape == (4, 2)
    assert mesh.nodes.dtype == np.float64
    assert mesh.triangles.shape == (2, 3)
    assert mesh.triangles.dtype == np.int32
    assert mesh.region_ids.tolist() == [1, 1]
    assert mesh.outer_boundary.shape == (4, 2)
    assert mesh.outer_boundary[1, 1] == 1.0
    assert not np.shares_memory(
        mesh.outer_boundary,
        domain.original_region._resampled_points,
    )


@pytest.mark.parametrize(
    "triangles, regions, message",
    [
        (
            np.array([[0, 1, 9], [0, 2, 3]], dtype=np.int32),
            np.array([1, 1], dtype=np.int32),
            "越界",
        ),
        (
            np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32),
            np.array([1, 2], dtype=np.int32),
            "区域 ID 集合",
        ),
        (
            np.array([[0, 1, 1], [0, 2, 3]], dtype=np.int32),
            np.array([1, 1], dtype=np.int32),
            "重复顶点",
        ),
    ],
)
def test_adapter_rejects_distinct_mesh_contract_failures(
    monkeypatch,
    triangles,
    regions,
    message,
):
    monkeypatch.setattr(
        oft_adapter,
        "_get_installed_oft_version",
        lambda: "26.6",
    )
    domain = _Domain()
    domain.triangles = triangles

    def build_mesh():
        domain.original_region._resampled_points = np.array(
            [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]
        )
        domain.region_info = {"final": {"id": 1}}
        return domain.nodes, domain.triangles, regions

    domain.build_mesh = build_mesh

    with pytest.raises(ValueError, match=message):
        mesh_from_oft_domain(domain)


def test_outer_region_readback_is_version_locked(monkeypatch):
    monkeypatch.setattr(
        oft_adapter,
        "_get_installed_oft_version",
        lambda: "27.0",
    )

    with pytest.raises(ValueError, match="openfusiontoolkit"):
        mesh_from_oft_domain(_Domain())


class _SingleRegionDomain:
    def __init__(self):
        self.regions = []
        self.define_region = MagicMock()

    def add_polygon(self, *_args, **_kwargs):
        self.regions.append(_Region())


def test_single_region_boundary_strategy_creates_one_region(monkeypatch):
    domain = _SingleRegionDomain()
    monkeypatch.setattr(
        oft_adapter,
        "_load_gs_domain_class",
        lambda: lambda: domain,
    )
    boundary = np.array(
        [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
        dtype=np.float64,
    )

    result = build_single_region_domain_from_boundary(
        boundary,
        plasma_dx=0.04,
    )

    assert result is domain
    assert len(domain.regions) == 1
    assert getattr(domain, _OUTER_REGION_ATTR) is domain.regions[0]
    domain.define_region.assert_called_once_with("plasma", 0.04, "plasma")


class _InspectDomain:
    last_instance = None

    def __init__(self):
        type(self).last_instance = self
        self.regions = []
        self.region_info = {}
        self.setup_only = None

    def define_region(self, name, _dx, role):
        self.region_info[name.upper()] = {
            "id": 99,
            "type": role,
        }

    def add_polygon(self, points, name, parent_name=None):
        self.regions.append(
            SimpleNamespace(
                points=np.array(points, copy=True),
                name=name,
                parent_name=parent_name,
            )
        )

    def build_mesh(self, *, setup_only=False):
        self.setup_only = setup_only
        # Deliberately differ from curve IDs and definition order.
        final_ids = {
            "LM_CURVE_1": 2,
            "LM_CURVE_2": 3,
            "LM_CURVE_3": 1,
        }
        for name, region_id in final_ids.items():
            if name in self.region_info:
                self.region_info[name]["id"] = region_id
        return None, None, None


def test_multi_region_inspect_uses_setup_only_and_final_ids(monkeypatch):
    root = np.array([[0, 0], [0, 4], [4, 4], [4, 0]], dtype=float)
    left = np.array([[0.5, 0.5], [0.5, 1.5], [1.5, 1.5], [1.5, 0.5]])
    right = np.array([[2.5, 0.5], [2.5, 1.5], [3.5, 1.5], [3.5, 0.5]])
    plan = build_region_plan((root, left, right))
    monkeypatch.setattr(
        oft_adapter,
        "_load_gs_domain_class",
        lambda: _InspectDomain,
    )

    mapping = inspect_multi_region_ids(plan)

    assert mapping == {1: 2, 2: 3, 3: 1}
    domain = _InspectDomain.last_instance
    assert domain.setup_only is True
    roles = {
        name: info["type"]
        for name, info in domain.region_info.items()
    }
    assert roles["LM_CURVE_1"] == "boundary"
    assert roles["LM_CURVE_2"] == "plasma"
    assert roles["LM_CURVE_3"] == "vacuum"


class _GenerateDomain:
    instances = []

    def __init__(self):
        type(self).instances.append(self)
        self.regions = []
        self.region_info = {}
        self.define_calls = []
        self.setup_only = None

    def define_region(self, name, dx, role):
        self.define_calls.append((name, dx, role))
        self.region_info[name.upper()] = {
            "id": 99,
            "type": role,
        }

    def add_polygon(self, points, name, parent_name=None):
        region = _Region()
        region.points = np.array(points, dtype=np.float64, copy=True)
        region.name = name
        region.parent_name = parent_name
        self.regions.append(region)

    def build_mesh(self, *, setup_only=False):
        self.setup_only = setup_only
        final_ids = {
            "LM_CURVE_1": 2,
            "LM_CURVE_2": 1,
            "LM_CURVE_3": 3,
        }
        for name, region_id in final_ids.items():
            self.region_info[name]["id"] = region_id

        if setup_only:
            return None, None, None

        self.regions[0]._resampled_points = np.array(
            [[0.0, 0.0], [0.0, 4.0], [4.0, 4.0], [4.0, 0.0]],
            dtype=np.float64,
        )
        nodes = np.array(
            [
                [0.0, 0.0],
                [4.0, 0.0],
                [4.0, 4.0],
                [0.0, 4.0],
                [2.0, 2.0],
            ],
            dtype=np.float64,
        )
        triangles = np.array(
            [[0, 1, 4], [1, 2, 4], [2, 3, 4]],
            dtype=np.int32,
        )
        attributes = np.array([2, 1, 3], dtype=np.int32)
        return nodes, triangles, attributes


def test_multi_region_full_build_uses_final_id_dx_and_fresh_domain(
    monkeypatch,
):
    _GenerateDomain.instances = []
    monkeypatch.setattr(
        oft_adapter,
        "_load_gs_domain_class",
        lambda: _GenerateDomain,
    )
    monkeypatch.setattr(
        oft_adapter,
        "_get_installed_oft_version",
        lambda: "26.6",
    )
    root = np.array([[0, 0], [0, 4], [4, 4], [4, 0]], dtype=float)
    left = np.array([[0.5, 0.5], [0.5, 1.5], [1.5, 1.5], [1.5, 0.5]])
    right = np.array([[2.5, 0.5], [2.5, 1.5], [3.5, 1.5], [3.5, 0.5]])
    plan = build_region_plan((root, left, right))

    setup_ids = inspect_multi_region_ids(plan)
    from linkmesh.regions import assign_final_region_ids

    numbered = assign_final_region_ids(plan, setup_ids)
    mesh = generate_multi_region_mesh(
        numbered,
        {1: 0.03, 2: 0.08, 3: 0.05},
    )

    assert len(_GenerateDomain.instances) == 2
    setup_domain, full_domain = _GenerateDomain.instances
    assert setup_domain is not full_domain
    assert setup_domain.setup_only is True
    assert full_domain.setup_only is False
    assert full_domain.define_calls == [
        ("LM_CURVE_1", 0.08, "boundary"),
        ("LM_CURVE_2", 0.03, "plasma"),
        ("LM_CURVE_3", 0.05, "vacuum"),
    ]
    assert mesh.region_ids.tolist() == [2, 1, 3]
    assert mesh.outer_boundary is not None
    assert set(mesh.region_ids.tolist()) == {1, 2, 3}


class _NestedDomain:
    def __init__(self):
        self.regions = []
        self.define_region = MagicMock()
        self.add_polygon = MagicMock()
        self.add_annulus = MagicMock()

    def add_rectangle(self, *_args, **_kwargs):
        self.regions.append(_Region())


def test_nested_strategy_captures_artificial_outer_region(monkeypatch):
    domain = _NestedDomain()
    monkeypatch.setattr(
        oft_adapter,
        "_load_gs_domain_class",
        lambda: lambda: domain,
    )
    gfile = SimpleNamespace(
        lcfs_r=np.array([0.0, 1.0, 1.0, 0.0]),
        lcfs_z=np.array([0.0, 0.0, 1.0, 1.0]),
        wall_r=None,
        wall_z=None,
    )

    result = build_oft_domain_from_gfile(gfile)

    assert result is domain
    assert len(domain.regions) == 1
    assert getattr(domain, _OUTER_REGION_ATTR) is domain.regions[0]
    assert domain.add_polygon.call_count == 1
