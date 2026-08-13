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
from linkmesh.mesh import Mesh2D
from linkmesh.mesher import triangle_refinement
from linkmesh.regions import build_region_plan


def _mesh_arrays():
    nodes = np.array(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=np.float64,
    )
    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    return nodes, triangles


def _two_region_mesh() -> Mesh2D:
    nodes = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [2.0, 1.0],
        ],
        dtype=np.float64,
    )
    triangles = np.array(
        [
            [0, 1, 4],
            [0, 4, 3],
            [1, 2, 5],
            [1, 5, 4],
        ],
        dtype=np.int32,
    )
    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=np.array([1, 1, 2, 2], dtype=np.int32),
    )


def test_transition_topology_profile_and_pslg_contract():
    mesh = _two_region_mesh()
    dx = {1: 0.25, 2: 1.0}

    topology = triangle_refinement._extract_edge_topology(mesh, dx)
    assert len(topology.interfaces) == 1
    interface = topology.interfaces[0]
    assert interface.coarse_region_id == 2
    assert interface.fine_region_id == 1
    assert interface.fine_dx == 0.25
    assert interface.coarse_dx == 1.0
    assert interface.segments.tolist() == [[1, 4]]

    pslg = {
        tuple(edge)
        for edge in topology.pslg_segments.tolist()
    }
    assert (1, 4) in pslg
    assert (0, 4) not in pslg
    assert (1, 5) not in pslg

    bounds = triangle_refinement._triangle_area_bounds(
        mesh,
        dx,
        1.0,
        topology,
    )
    assert bounds.shape == (4,)
    assert bounds.dtype == np.float64
    assert bounds.flags.c_contiguous
    assert np.all(np.isfinite(bounds))
    assert np.all(bounds > 0.0)
    assert bounds[2] < 0.5
    assert bounds[3] < 0.5


def test_centroid_to_segment_distance_is_euclidean():
    nodes = np.array([[0.0, 0.0], [0.0, 2.0]], dtype=np.float64)
    centroids = np.array([[1.0, 1.0], [2.0, 3.0]], dtype=np.float64)
    segments = np.array([[0, 1]], dtype=np.int32)

    distances = triangle_refinement._centroid_to_segments_distance(
        centroids,
        nodes,
        segments,
    )

    assert distances == pytest.approx([1.0, np.sqrt(5.0)])


def test_multiple_interfaces_use_strictest_size():
    nodes = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [2.0, 0.0],
            [2.0, 1.0],
        ],
        dtype=np.float64,
    )
    mesh = Mesh2D(
        nodes=nodes,
        triangles=np.array(
            [[0, 1, 2], [1, 3, 4], [1, 4, 2]],
            dtype=np.int32,
        ),
        region_ids=np.array([1, 2, 2], dtype=np.int32),
    )
    topology = triangle_refinement.EdgeTopology(
        edges=np.empty((0, 2), dtype=np.int32),
        incidences=(),
        pslg_segments=np.array([[1, 2]], dtype=np.int32),
        interfaces=(
            triangle_refinement.InterfaceConstraint(
                coarse_region_id=2,
                fine_region_id=1,
                fine_dx=0.2,
                coarse_dx=1.0,
                segments=np.array([[1, 2]], dtype=np.int32),
            ),
            triangle_refinement.InterfaceConstraint(
                coarse_region_id=2,
                fine_region_id=3,
                fine_dx=0.1,
                coarse_dx=1.0,
                segments=np.array([[3, 4]], dtype=np.int32),
            ),
        ),
    )

    bounds = triangle_refinement._triangle_area_bounds(
        mesh,
        {1: 0.2, 2: 1.0, 3: 0.1},
        10.0,
        topology,
    )

    assert np.all(bounds[1:] < 0.5)


def test_equal_dx_and_zero_width_do_not_call_native(monkeypatch):
    mesh = _two_region_mesh()
    native = MagicMock()
    monkeypatch.setattr(triangle_refinement, "_native_refine", native)

    equal_dx = triangle_refinement.refine_transition_mesh(
        mesh,
        {1: 0.5, 2: 0.5},
        0.2,
    )
    zero_width = triangle_refinement.refine_transition_mesh(
        mesh,
        {1: 0.25, 2: 1.0},
        0.0,
    )

    assert native.call_count == 0
    assert np.array_equal(equal_dx.nodes, mesh.nodes)
    assert np.array_equal(zero_width.triangles, mesh.triangles)
    assert not np.shares_memory(equal_dx.nodes, mesh.nodes)
    assert not np.shares_memory(zero_width.triangles, mesh.triangles)


def test_transition_refinement_preserves_input_and_owned_final_mesh(monkeypatch):
    mesh = _two_region_mesh()
    original_nodes = mesh.nodes.copy()
    original_triangles = mesh.triangles.copy()
    original_regions = mesh.region_ids.copy()

    monkeypatch.setattr(
        triangle_refinement,
        "_area_violations",
        MagicMock(return_value=np.zeros(mesh.n_triangles, dtype=bool)),
    )
    native = MagicMock()
    monkeypatch.setattr(triangle_refinement, "_native_refine", native)

    result = triangle_refinement.refine_transition_mesh(
        mesh,
        {1: 0.25, 2: 1.0},
        0.5,
    )

    assert native.call_count == 0
    assert np.array_equal(mesh.nodes, original_nodes)
    assert np.array_equal(mesh.triangles, original_triangles)
    assert np.array_equal(mesh.region_ids, original_regions)
    assert not np.shares_memory(result.nodes, mesh.nodes)
    assert not np.shares_memory(result.triangles, mesh.triangles)
    assert not np.shares_memory(result.region_ids, mesh.region_ids)


def test_transition_topology_rejects_non_manifold_edge():
    mesh = Mesh2D(
        nodes=np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [0.0, 1.0],
                [0.0, -1.0],
                [1.0, 1.0],
            ],
            dtype=np.float64,
        ),
        triangles=np.array(
            [[0, 1, 2], [1, 0, 3], [0, 1, 4]],
            dtype=np.int32,
        ),
        region_ids=np.array([1, 1, 2], dtype=np.int32),
    )

    with pytest.raises(ValueError, match="non-manifold"):
        triangle_refinement._extract_edge_topology(mesh, {1: 0.2, 2: 0.4})


def test_transition_rejects_changed_or_noninteger_attributes(monkeypatch):
    mesh = _two_region_mesh()
    topology = triangle_refinement._extract_edge_topology(
        mesh,
        {1: 0.25, 2: 1.0},
    )
    monkeypatch.setattr(
        triangle_refinement,
        "_area_violations",
        MagicMock(return_value=np.ones(mesh.n_triangles, dtype=bool)),
    )

    def changed_attributes(_mesh, _bounds, _segments):
        return (
            mesh.nodes.copy(),
            mesh.triangles.copy(),
            np.array([1.0, 1.0, 2.0, 3.0]),
            topology.pslg_segments.copy(),
        )

    monkeypatch.setattr(
        triangle_refinement,
        "_native_refine",
        changed_attributes,
    )
    with pytest.raises(ValueError, match="Region ID 集合"):
        triangle_refinement.refine_transition_mesh(
            mesh,
            {1: 0.25, 2: 1.0},
            0.5,
        )

    with pytest.raises(ValueError, match="整数语义"):
        triangle_refinement._validate_mesh_arrays(
            Mesh2D(
                nodes=mesh.nodes,
                triangles=mesh.triangles,
                region_ids=np.array([1.0, 1.0, 2.0, 2.5]),
            )
        )


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


def test_multi_region_full_build_rejects_changed_final_mapping(
    monkeypatch,
):
    class ChangedDomain(_GenerateDomain):
        def build_mesh(self, *, setup_only=False):
            result = super().build_mesh(setup_only=setup_only)
            if not setup_only:
                self.region_info["LM_CURVE_2"]["id"] = 3
                self.region_info["LM_CURVE_3"]["id"] = 1
            return result

    _GenerateDomain.instances = []
    monkeypatch.setattr(
        oft_adapter,
        "_load_gs_domain_class",
        lambda: ChangedDomain,
    )
    monkeypatch.setattr(
        oft_adapter,
        "_get_installed_oft_version",
        lambda: "26.6",
    )
    root = np.array([[0, 0], [0, 4], [4, 4], [4, 0]], dtype=float)
    left = np.array([[0.5, 0.5], [0.5, 1.5], [1.5, 1.5], [1.5, 0.5]])
    right = np.array([[2.5, 0.5], [2.5, 1.5], [3.5, 1.5], [3.5, 0.5]])
    from linkmesh.regions import assign_final_region_ids

    numbered = assign_final_region_ids(
        build_region_plan((root, left, right)),
        {1: 2, 2: 1, 3: 3},
    )

    with pytest.raises(ValueError, match="setup-only/map"):
        generate_multi_region_mesh(
            numbered,
            {1: 0.03, 2: 0.08, 3: 0.05},
        )


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
