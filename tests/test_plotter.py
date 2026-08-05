from __future__ import annotations

import numpy as np
import pytest

from linkmesh.mesh import Mesh2D
from linkmesh.utils import plotter
from linkmesh.utils.plotter import plot_mesh


pytest.importorskip("matplotlib")


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


def test_plot_mesh_without_gfile_uses_computational_boundary(tmp_path):
    output = tmp_path / "array-boundary.png"

    plot_mesh(None, _mesh(), str(output), show_region_ids=True)

    assert output.is_file()
    assert output.stat().st_size > 0


def test_plot_mesh_with_gfile_keeps_reference_overlays(
    tmp_path, monkeypatch
):
    class GFile:
        lcfs_r = np.array([0.1, 0.9, 0.9, 0.1])
        lcfs_z = np.array([0.1, 0.1, 0.9, 0.9])
        wall_r = np.array([-0.1, 1.1, 1.1, -0.1])
        wall_z = np.array([-0.1, -0.1, 1.1, 1.1])
        rmaxis = 0.5
        zmaxis = 0.5

    mesh = _mesh()
    gfile = GFile()
    mesh_boundary_before = mesh.outer_boundary.copy()
    lcfs_r_before = gfile.lcfs_r.copy()
    lcfs_z_before = gfile.lcfs_z.copy()
    plotted_styles = {}

    import matplotlib.axes

    original_plot = matplotlib.axes.Axes.plot

    def recording_plot(self, *args, **kwargs):
        label = kwargs.get("label")
        if label in {"Mesh boundary", "LCFS reference"}:
            plotted_styles[label] = kwargs.get("linestyle", "-")
        return original_plot(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "plot", recording_plot)

    output = tmp_path / "gfile-overlay.png"
    plot_mesh(gfile, mesh, str(output), show_region_ids=True)

    assert output.is_file()
    assert output.stat().st_size > 0
    assert plotted_styles["Mesh boundary"] != plotted_styles["LCFS reference"]
    np.testing.assert_array_equal(mesh.outer_boundary, mesh_boundary_before)
    np.testing.assert_array_equal(gfile.lcfs_r, lcfs_r_before)
    np.testing.assert_array_equal(gfile.lcfs_z, lcfs_z_before)


def test_plot_mesh_warns_when_lcfs_reference_is_outside(
    tmp_path, capsys
):
    class GFile:
        lcfs_r = np.array([0.1, 1.2, 0.9, 0.1])
        lcfs_z = np.array([0.1, 0.1, 0.9, 0.9])
        wall_r = None
        wall_z = None
        rmaxis = 0.5
        zmaxis = 0.5

    output = tmp_path / "outside-reference.png"
    plot_mesh(GFile(), _mesh(), str(output))

    assert "WARNING: LCFS reference" in capsys.readouterr().out
    assert output.is_file()
    assert output.stat().st_size > 0
