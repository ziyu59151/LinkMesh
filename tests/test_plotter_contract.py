from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

from linkmesh.mesh import Mesh2D
from linkmesh.regions import (
    assign_final_region_ids,
    build_region_plan,
    region_map_entries,
)
from linkmesh.utils.plotter import plot_mesh, plot_regions_inspection


def _mesh() -> Mesh2D:
    return Mesh2D(
        nodes=np.array(
            [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
            dtype=np.float64,
        ),
        triangles=np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32),
        region_ids=np.array([1, 1], dtype=np.int32),
        outer_boundary=np.array(
            [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
            dtype=np.float64,
        ),
    )


def test_plotter_generates_nonempty_png_without_gfile(tmp_path):
    output = tmp_path / "mesh.png"

    plot_mesh(None, _mesh(), str(output), show_region_ids=True)

    assert output.is_file()
    assert output.stat().st_size > 0


def test_regions_inspection_generates_png_with_map_colors(tmp_path):
    outer = np.array([[0, 0], [0, 3], [3, 3], [3, 0]], dtype=float)
    inner = np.array([[1, 1], [1, 2], [2, 2], [2, 1]], dtype=float)
    plan = build_region_plan((outer, inner))
    numbered = assign_final_region_ids(plan, {1: 2, 2: 1})
    records = region_map_entries(numbered)
    snapshots = [entry.points.copy() for entry in numbered.entries]
    output = tmp_path / "regions.png"

    plot_regions_inspection(numbered, records, str(output))

    assert output.is_file()
    assert output.stat().st_size > 0
    assert {record.color for record in records} == {
        entry.color for entry in numbered.entries
    }
    for entry, snapshot in zip(numbered.entries, snapshots):
        np.testing.assert_array_equal(entry.points, snapshot)


def test_reference_only_mode_selects_lcfs_and_preserves_inputs(
    tmp_path,
    monkeypatch,
):
    class GFile:
        lcfs_r = np.array([0.1, 0.9, 0.9, 0.1])
        lcfs_z = np.array([0.1, 0.1, 0.9, 0.9])
        wall_r = np.array([-0.1, 1.1, 1.1, -0.1])
        wall_z = np.array([-0.1, -0.1, 1.1, 1.1])
        rmaxis = 0.5
        zmaxis = 0.5

    import matplotlib.axes

    labels = []
    original_plot = matplotlib.axes.Axes.plot

    def recording_plot(self, *args, **kwargs):
        if kwargs.get("label") is not None:
            labels.append(kwargs["label"])
        return original_plot(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "plot", recording_plot)

    mesh = _mesh()
    gfile = GFile()
    boundary_before = mesh.outer_boundary.copy()
    lcfs_before = gfile.lcfs_r.copy()
    output = tmp_path / "reference.png"

    plot_mesh(
        gfile,
        mesh,
        str(output),
        show_region_ids=True,
        lcfs_reference_only=True,
    )

    assert output.stat().st_size > 0
    assert "Mesh boundary" in labels
    assert "LCFS reference" in labels
    assert "First wall" not in labels
    assert not any(label.startswith("Magnetic axis") for label in labels)
    np.testing.assert_array_equal(mesh.outer_boundary, boundary_before)
    np.testing.assert_array_equal(gfile.lcfs_r, lcfs_before)
