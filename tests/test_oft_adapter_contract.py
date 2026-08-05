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
    mesh_from_oft_domain,
)


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
