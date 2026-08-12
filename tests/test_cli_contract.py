from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from linkmesh import cli
from linkmesh.config import ConfigError
from linkmesh.regions import RegionsError


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


def _assert_group_order(help_text, *titles):
    positions = [help_text.index(f"{title}:") for title in titles]
    assert positions == sorted(positions)


def test_top_level_help_describes_both_workflows_and_group_order(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as captured:
        parser.parse_args(["--help"])

    assert captured.value.code == 0
    help_text = capsys.readouterr().out
    assert "标准网格工作流" in help_text
    assert "多区域工作流" in help_text
    assert "regions {inspect,generate}" in help_text
    assert "linkmesh mesh" not in help_text
    for option in (
        "--config",
        "--no-config",
        "--target",
        "--profile",
        "--boundary-source",
        "--gfile",
        "--array-file",
        "--plot-lcfs",
        "--mesh-dx",
        "--plasma-dx",
        "--vacuum-dx",
        "--outer-dx",
        "--hdf5",
        "--h5",
        "--model",
        "--smb",
        "--plot",
        "--no-hdf5",
        "--no-smb",
        "--verbose",
    ):
        assert option in help_text
    _assert_group_order(
        help_text,
        "Configuration",
        "Task",
        "Input",
        "Mesh Resolution",
        "Output",
        "Runtime",
    )


def test_regions_help_hierarchy_and_old_parser_scope(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as captured:
        parser.parse_args(["regions", "--help"])

    assert captured.value.code == 0
    help_text = capsys.readouterr().out
    assert "inspect" in help_text
    assert "generate" in help_text
    assert "setup-only" in help_text
    assert "完整多区域 Triangle 网格" in help_text
    assert "--gfile" not in help_text
    assert "--hdf5" not in help_text
    assert "--smb" not in help_text

    old = parser.parse_args(
        [
            "--no-config",
            "--target",
            "mesh_only",
            "--profile",
            "single_region",
            "--boundary-source",
            "lcfs",
            "--gfile",
            "eq.gfile",
        ]
    )
    assert old.command is None


def test_regions_inspect_help_is_scoped_and_grouped(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as captured:
        parser.parse_args(["regions", "inspect", "--help"])

    assert captured.value.code == 0
    help_text = capsys.readouterr().out
    for option in (
        "--config",
        "--multi-array-file",
        "--regions-map",
        "--plot",
        "--verbose",
    ):
        assert option in help_text
    assert "正式 TOML regions map" in help_text
    assert "inspection PNG" in help_text
    assert "--region-dx" not in help_text
    assert "--hdf5" not in help_text
    assert "--smb" not in help_text
    _assert_group_order(
        help_text,
        "Configuration",
        "Input",
        "Output",
        "Runtime",
    )


def test_regions_inspect_runs_setup_only_map_and_plot(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    blocks = (
        np.array([[0, 0], [0, 3], [3, 3], [3, 0]], dtype=float),
        np.array([[1, 1], [1, 2], [2, 2], [2, 1]], dtype=float),
    )
    read = MagicMock(return_value=blocks)
    setup = MagicMock(return_value={1: 2, 2: 1})
    plot = MagicMock()
    write_map = MagicMock()
    monkeypatch.setattr(
        "linkmesh.readers.boundary_reader.read_multi_boundary_file",
        read,
    )
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.inspect_multi_region_ids",
        setup,
    )
    monkeypatch.setattr(
        "linkmesh.utils.plotter.plot_regions_inspection",
        plot,
    )
    monkeypatch.setattr(
        "linkmesh.regions.write_regions_map",
        write_map,
    )

    cli._run(
        _parse(
            "regions",
            "inspect",
            "--multi-array-file",
            "multi.rz",
            "--regions-map",
            "regions.toml",
            "--plot",
            "regions.png",
        )
    )

    assert read.call_count == 1
    assert setup.call_count == 1
    assert plot.call_count == 1
    assert write_map.call_count == 1


def test_regions_generate_help_is_scoped(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as captured:
        parser.parse_args(["regions", "generate", "--help"])

    assert captured.value.code == 0
    help_text = capsys.readouterr().out
    for option in (
        "--config",
        "--target",
        "--multi-array-file",
        "--regions-map",
        "--mesh-dx",
        "--region-dx",
        "--hdf5",
        "--model",
        "--smb",
        "--plot",
        "--verbose",
    ):
        assert option in help_text
    assert "最终 Region ID" in help_text
    assert "可重复提供" in help_text
    assert "完整覆盖全部 Region" in help_text
    assert "{mesh_only,trimeg,m3dc1}" in help_text
    assert "--gfile" not in help_text
    assert "--no-hdf5" not in help_text
    assert "--no-smb" not in help_text
    _assert_group_order(
        help_text,
        "Configuration",
        "Task",
        "Input",
        "Mesh Resolution",
        "Output",
        "Runtime",
    )


def test_regions_error_is_reported_without_traceback(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        sys,
        "argv",
        ["linkmesh", "regions", "generate", "--help"],
    )
    monkeypatch.setattr(
        cli,
        "_run",
        MagicMock(side_effect=RegionsError("请重新执行 linkmesh regions inspect")),
    )
    monkeypatch.setattr(
        cli,
        "build_parser",
        MagicMock(
            return_value=SimpleNamespace(
                parse_args=MagicMock(return_value=SimpleNamespace())
            )
        ),
    )

    with pytest.raises(SystemExit) as captured:
        cli.main()

    assert captured.value.code != 0
    stderr = capsys.readouterr().err
    assert "[LinkMesh] Region 工作流错误：" in stderr
    assert "请重新执行 linkmesh regions inspect" in stderr
    assert "Traceback" not in stderr


def test_unknown_internal_exception_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(
        cli,
        "_run",
        MagicMock(side_effect=RuntimeError("internal failure")),
    )
    monkeypatch.setattr(
        cli,
        "build_parser",
        MagicMock(
            return_value=SimpleNamespace(
                parse_args=MagicMock(return_value=SimpleNamespace())
            )
        ),
    )

    with pytest.raises(RuntimeError, match="internal failure"):
        cli.main()


def test_regions_generate_rebuilds_validates_and_plots(
    monkeypatch,
    tmp_path,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    blocks = (
        np.array([[0, 0], [0, 3], [3, 3], [3, 0]], dtype=float),
        np.array([[1, 1], [1, 2], [2, 2], [2, 1]], dtype=float),
    )
    records = (
        SimpleNamespace(
            region_id=1,
            curve_id=2,
            parent_region_id=2,
            child_region_ids=(),
            color="#D55E00",
            physical_label="core",
        ),
        SimpleNamespace(
            region_id=2,
            curve_id=1,
            parent_region_id=0,
            child_region_ids=(1,),
            color="#0072B2",
            physical_label="",
        ),
    )
    plan = object()
    numbered_plan = object()
    mesh = SimpleNamespace(
        n_nodes=5,
        n_triangles=3,
        region_ids=np.array([1, 1, 2], dtype=np.int32),
    )

    read_map = MagicMock(return_value=records)
    read_blocks = MagicMock(return_value=blocks)
    build_plan = MagicMock(return_value=plan)
    setup = MagicMock(return_value={1: 2, 2: 1})
    assign = MagicMock(return_value=numbered_plan)
    validate = MagicMock()
    resolve = MagicMock(return_value={1: 0.03, 2: 0.08})
    generate = MagicMock(return_value=mesh)
    plot = MagicMock()
    hdf5 = MagicMock()

    monkeypatch.setattr("linkmesh.regions.read_regions_map", read_map)
    monkeypatch.setattr(
        "linkmesh.readers.boundary_reader.read_multi_boundary_file",
        read_blocks,
    )
    monkeypatch.setattr("linkmesh.regions.build_region_plan", build_plan)
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.inspect_multi_region_ids",
        setup,
    )
    monkeypatch.setattr(
        "linkmesh.regions.assign_final_region_ids",
        assign,
    )
    monkeypatch.setattr(
        "linkmesh.regions.validate_plan_against_map",
        validate,
    )
    monkeypatch.setattr("linkmesh.regions.resolve_region_dx", resolve)
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.generate_multi_region_mesh",
        generate,
    )
    monkeypatch.setattr(
        "linkmesh.utils.plotter.plot_regions_mesh",
        plot,
    )
    monkeypatch.setattr(
        "linkmesh.writers.hdf5_writer.write_hdf5",
        hdf5,
    )

    cli._run(
        _parse(
            "regions",
            "generate",
            "--multi-array-file",
            "multi.rz",
            "--regions-map",
            "regions.toml",
            "--plot",
            "mesh.png",
            "--mesh-dx",
            "0.08",
            "--region-dx",
            "1=0.03",
            "--verbose",
        )
    )

    validate.assert_called_once_with(numbered_plan, records)
    resolve.assert_called_once_with(records, 0.08, {1: 0.03})
    generate.assert_called_once_with(
        numbered_plan,
        {1: 0.03, 2: 0.08},
    )
    plot.assert_called_once_with(mesh, records, str((tmp_path / "mesh.png").resolve()))
    assert hdf5.call_count == 0
    output = capsys.readouterr().out
    assert "Region 1" in output
    assert "triangles=2" in output
    assert "Region 2" in output


def test_regions_generate_trimeg_reuses_mesh_and_calls_hdf5_once(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    blocks = (
        np.array([[0, 0], [0, 3], [3, 3], [3, 0]], dtype=float),
        np.array([[1, 1], [1, 2], [2, 2], [2, 1]], dtype=float),
    )
    records = (
        SimpleNamespace(
            region_id=1,
            curve_id=2,
            parent_region_id=2,
            child_region_ids=(),
            color="#D55E00",
            physical_label="",
        ),
        SimpleNamespace(
            region_id=2,
            curve_id=1,
            parent_region_id=0,
            child_region_ids=(1,),
            color="#0072B2",
            physical_label="",
        ),
    )
    mesh = SimpleNamespace(
        n_nodes=5,
        n_triangles=3,
        region_ids=np.array([1, 1, 2], dtype=np.int32),
    )
    generate = MagicMock(return_value=mesh)
    hdf5 = MagicMock()

    monkeypatch.setattr(
        "linkmesh.readers.boundary_reader.read_multi_boundary_file",
        MagicMock(return_value=blocks),
    )
    monkeypatch.setattr(
        "linkmesh.regions.read_regions_map",
        MagicMock(return_value=records),
    )
    monkeypatch.setattr(
        "linkmesh.regions.build_region_plan",
        MagicMock(return_value=object()),
    )
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.inspect_multi_region_ids",
        MagicMock(return_value={1: 2, 2: 1}),
    )
    monkeypatch.setattr(
        "linkmesh.regions.assign_final_region_ids",
        MagicMock(return_value=object()),
    )
    monkeypatch.setattr(
        "linkmesh.regions.validate_plan_against_map",
        MagicMock(),
    )
    monkeypatch.setattr(
        "linkmesh.regions.resolve_region_dx",
        MagicMock(return_value={1: 0.03, 2: 0.08}),
    )
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.generate_multi_region_mesh",
        generate,
    )
    monkeypatch.setattr(
        "linkmesh.writers.hdf5_writer.write_hdf5",
        hdf5,
    )
    monkeypatch.setattr(
        "linkmesh.utils.plotter.plot_regions_mesh",
        MagicMock(),
    )
    build_spec = MagicMock()
    model_writer = MagicMock()
    smb_writer = MagicMock()
    monkeypatch.setattr(
        "linkmesh.m3dc1_model.build_single_face_model_spec",
        build_spec,
    )
    monkeypatch.setattr(
        "linkmesh.writers.m3dc1_model_writer.write_m3dc1_model",
        model_writer,
    )
    monkeypatch.setattr(
        "linkmesh.writers.smb_writer.write_smb",
        smb_writer,
    )

    cli._run(
        _parse(
            "regions",
            "generate",
            "--target",
            "trimeg",
            "--multi-array-file",
            "multi.rz",
            "--regions-map",
            "regions.toml",
            "--plot",
            "mesh.png",
            "--mesh-dx",
            "0.08",
            "--hdf5",
            "mesh.h5",
        )
    )

    generate.assert_called_once()
    hdf5.assert_called_once_with(
        mesh,
        str((tmp_path / "mesh.h5").resolve()),
        verbose=False,
    )
    assert build_spec.call_count == 0
    assert model_writer.call_count == 0
    assert smb_writer.call_count == 0


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
