from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from linkmesh import cli
from linkmesh.config import ConfigError


def _parse(*arguments):
    return cli.build_parser().parse_args(list(arguments))


def _install_boundaries(monkeypatch):
    gfile = SimpleNamespace(
        lcfs_r=np.array([0.0, 1.0, 0.0]),
        lcfs_z=np.array([0.0, 0.0, 1.0]),
        wall_r=None,
        wall_z=None,
        rmaxis=0.5,
        zmaxis=0.5,
    )
    boundary = np.array(
        [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]
    )
    mesh = SimpleNamespace(n_nodes=4, n_triangles=2)

    mocks = {
        "read_gfile": MagicMock(return_value=gfile),
        "read_boundary": MagicMock(return_value=boundary),
        "generate": MagicMock(return_value=mesh),
        "hdf5": MagicMock(),
        "build_spec": MagicMock(return_value=object()),
        "model": MagicMock(),
        "smb": MagicMock(),
        "plot": MagicMock(),
    }
    monkeypatch.setattr(
        "linkmesh.readers.gfile_reader.read_gfile",
        mocks["read_gfile"],
    )
    monkeypatch.setattr(
        "linkmesh.readers.boundary_reader.read_boundary_file",
        mocks["read_boundary"],
    )
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.generate_mesh",
        mocks["generate"],
    )
    monkeypatch.setattr(
        "linkmesh.writers.hdf5_writer.write_hdf5",
        mocks["hdf5"],
    )
    monkeypatch.setattr(
        "linkmesh.m3dc1_model.build_single_face_model_spec",
        mocks["build_spec"],
    )
    monkeypatch.setattr(
        "linkmesh.writers.m3dc1_model_writer.write_m3dc1_model",
        mocks["model"],
    )
    monkeypatch.setattr(
        "linkmesh.writers.smb_writer.write_smb",
        mocks["smb"],
    )
    monkeypatch.setattr(
        "linkmesh.utils.plotter.plot_mesh",
        mocks["plot"],
    )
    mocks.update(gfile=gfile, boundary=boundary, mesh=mesh)
    return mocks


def test_mesh_only_selects_mesher_without_writers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    mocks = _install_boundaries(monkeypatch)

    cli._run(
        _parse(
            "--no-config",
            "--target",
            "mesh_only",
            "--profile",
            "single_region",
            "--boundary-source",
            "lcfs",
            "--gfile",
            "eq.gfile",
        )
    )

    assert mocks["generate"].call_args.args[0] is mocks["gfile"]
    assert mocks["hdf5"].call_count == 0
    assert mocks["model"].call_count == 0
    assert mocks["smb"].call_count == 0


def test_trimeg_passes_same_mesh_to_hdf5_only(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    mocks = _install_boundaries(monkeypatch)

    cli._run(
        _parse(
            "--no-config",
            "--target",
            "trimeg",
            "--profile",
            "single_region",
            "--boundary-source",
            "lcfs",
            "--gfile",
            "eq.gfile",
            "--hdf5",
            "mesh.h5",
        )
    )

    assert mocks["hdf5"].call_args.args[0] is mocks["mesh"]
    assert mocks["build_spec"].call_count == 0
    assert mocks["smb"].call_count == 0


def test_m3dc1_reuses_one_model_spec_and_skips_hdf5(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    mocks = _install_boundaries(monkeypatch)

    cli._run(
        _parse(
            "--no-config",
            "--target",
            "m3dc1",
            "--profile",
            "single_region",
            "--boundary-source",
            "lcfs",
            "--gfile",
            "eq.gfile",
            "--model",
            "model.txt",
            "--smb",
            "mesh.smb",
        )
    )

    spec = mocks["build_spec"].return_value
    assert mocks["build_spec"].call_args.args[0] is mocks["mesh"]
    assert mocks["model"].call_args.args[0] is spec
    assert mocks["smb"].call_args.args[:2] == (mocks["mesh"], spec)
    assert mocks["hdf5"].call_count == 0


def test_array_lcfs_reference_never_enters_mesher_or_writer(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    mocks = _install_boundaries(monkeypatch)

    cli._run(
        _parse(
            "--no-config",
            "--target",
            "trimeg",
            "--profile",
            "single_region",
            "--boundary-source",
            "array_file",
            "--array-file",
            "boundary",
            "--plot-lcfs",
            "--gfile",
            "eq.gfile",
            "--plot",
            "mesh.png",
            "--hdf5",
            "mesh.h5",
        )
    )

    assert mocks["generate"].call_args.args[0] is mocks["boundary"]
    assert mocks["generate"].call_args.args[0] is not mocks["gfile"]
    assert mocks["hdf5"].call_args.args[0] is mocks["mesh"]
    assert mocks["plot"].call_args.args[:2] == (
        mocks["gfile"],
        mocks["mesh"],
    )
    assert mocks["plot"].call_args.kwargs["lcfs_reference_only"] is True


def test_configuration_failure_precedes_reader_and_mesher(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    mocks = _install_boundaries(monkeypatch)
    arguments = _parse(
        "--no-config",
        "--target",
        "mesh_only",
        "--profile",
        "single_region",
        "--boundary-source",
        "array_file",
        "--array-file",
        "boundary",
        "--plot-lcfs",
        "--plot",
        "mesh.png",
    )

    with pytest.raises(ConfigError, match="gfile_path"):
        cli._run(arguments)

    assert mocks["read_boundary"].call_count == 0
    assert mocks["read_gfile"].call_count == 0
    assert mocks["generate"].call_count == 0
