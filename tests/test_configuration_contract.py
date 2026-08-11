from __future__ import annotations

from pathlib import Path

import pytest

from linkmesh.config import (
    CliOverrides,
    ConfigError,
    RegionsInspectOverrides,
    load_effective_config,
    load_regions_inspect_config,
)


def _load(tmp_path: Path, **overrides):
    return load_effective_config(
        CliOverrides(**overrides),
        no_config=True,
        cwd=tmp_path,
    )


def test_regions_inspect_config_is_isolated_and_cli_overrides_toml(tmp_path):
    config_dir = tmp_path / "regions-config"
    config_dir.mkdir()
    config_path = config_dir / "regions.toml"
    config_path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'inspect'\n"
        "multi_array_file = 'input.rz'\n"
        "regions_map = 'map.toml'\n"
        "plot = 'toml.png'\n"
        "[runtime]\nverbose = true\n",
        encoding="utf-8",
    )

    config = load_regions_inspect_config(
        RegionsInspectOverrides(plot="cli.png"),
        config_arg=str(config_path),
        cwd=tmp_path,
    )

    assert config.mode == "inspect"
    assert config.multi_array_file_path == (config_dir / "input.rz").resolve()
    assert config.regions_map_path == (config_dir / "map.toml").resolve()
    assert config.plot_path == (tmp_path / "cli.png").resolve()
    assert config.verbose is True


def test_regions_inspect_config_rejects_unknown_key_and_missing_required(
    tmp_path,
):
    path = tmp_path / "regions.toml"
    path.write_text(
        "schema_version = 1\n"
        "[regions]\nmode = 'inspect'\nunknown = true\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="未知键"):
        load_regions_inspect_config(
            RegionsInspectOverrides(),
            config_arg=str(path),
            cwd=tmp_path,
        )

    with pytest.raises(ConfigError, match="multi-array-file"):
        load_regions_inspect_config(
            RegionsInspectOverrides(),
            cwd=tmp_path,
        )


def test_builtin_defaults_and_target_conditional_output(tmp_path):
    config = _load(
        tmp_path,
        profile="nested_three_region",
        boundary_source="artificial_outer",
        gfile="eq.gfile",
    )

    assert config.target == "trimeg"
    assert config.profile == "nested_three_region"
    assert config.boundary_source == "artificial_outer"
    assert (config.mesh_dx, config.plasma_dx, config.vacuum_dx, config.outer_dx) == (
        0.08,
        0.08,
        0.10,
        0.15,
    )
    assert config.hdf5_path == (tmp_path / "mesh.h5").resolve()
    assert config.plot_path is None
    assert config.verbose is False
    assert config.plot_lcfs is False


def test_toml_cli_priority_and_distinct_path_bases(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "linkmesh.in"
    config_path.write_text(
        "schema_version = 1\n"
        "[task]\ntarget = 'trimeg'\n"
        "[input]\ngfile = 'toml.gfile'\n"
        "[domain]\nprofile = 'nested_three_region'\n"
        "boundary_source = 'artificial_outer'\n"
        "[mesh]\nplasma_dx = 0.04\n"
        "[output]\nhdf5 = 'toml.h5'\n",
        encoding="utf-8",
    )

    config = load_effective_config(
        CliOverrides(gfile="cli.gfile", plasma_dx=0.06),
        config_arg=str(config_path),
        cwd=tmp_path,
    )

    assert config.gfile_path == (tmp_path / "cli.gfile").resolve()
    assert config.hdf5_path == (config_dir / "toml.h5").resolve()
    assert config.plasma_dx == 0.06


@pytest.mark.parametrize(
    "text, message",
    [
        ("[mesh]\nmesh_dx = 0.1\n", "schema_version"),
        ("schema_version = 2\n", "schema_version"),
        ("schema_version = 1\nunknown = 1\n", "未知顶层键"),
        ("schema_version = 1\n[mesh]\nmesh_dx = true\n", "mesh_dx"),
        ("schema_version = 1\n[output]\nplot_lcfs = 'yes'\n", "plot_lcfs"),
    ],
)
def test_strict_toml_rejects_distinct_schema_failures(tmp_path, text, message):
    path = tmp_path / "linkmesh.in"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_effective_config(
            CliOverrides(
                profile="nested_three_region",
                boundary_source="artificial_outer",
                gfile="eq.gfile",
            ),
            cwd=tmp_path,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "target": "mesh_only",
            "profile": "single_region",
            "boundary_source": "lcfs",
            "gfile": "eq.gfile",
        },
        {
            "target": "trimeg",
            "profile": "single_region",
            "boundary_source": "array_file",
            "array_file": "boundary",
        },
        {
            "target": "m3dc1",
            "profile": "single_region",
            "boundary_source": "array_file",
            "array_file": "boundary",
            "model": "model.txt",
            "smb": "mesh.smb",
        },
    ],
)
def test_current_legal_workflows(tmp_path, overrides):
    config = _load(tmp_path, **overrides)
    assert config.profile == "single_region"


@pytest.mark.parametrize(
    "overrides, exception",
    [
        (
            {
                "profile": "nested_three_region",
                "boundary_source": "lcfs",
                "gfile": "eq.gfile",
            },
            ConfigError,
        ),
        (
            {
                "profile": "single_region",
                "boundary_source": "artificial_outer",
                "gfile": "eq.gfile",
            },
            ConfigError,
        ),
        (
            {
                "target": "m3dc1",
                "profile": "nested_three_region",
                "boundary_source": "artificial_outer",
                "gfile": "eq.gfile",
                "model": "model.txt",
                "smb": "mesh.smb",
            },
            ConfigError,
        ),
        (
            {
                "profile": "single_region",
                "boundary_source": "first_wall",
                "gfile": "eq.gfile",
            },
            NotImplementedError,
        ),
    ],
)
def test_forbidden_and_unimplemented_combinations(
    tmp_path,
    overrides,
    exception,
):
    with pytest.raises(exception):
        _load(tmp_path, **overrides)


@pytest.mark.parametrize(
    "overrides, message",
    [
        (
            {
                "profile": "single_region",
                "boundary_source": "lcfs",
            },
            "gfile",
        ),
        (
            {
                "profile": "single_region",
                "boundary_source": "array_file",
            },
            "array_file",
        ),
        (
            {
                "target": "m3dc1",
                "profile": "single_region",
                "boundary_source": "lcfs",
                "gfile": "eq.gfile",
                "smb": "mesh.smb",
            },
            "model_path",
        ),
        (
            {
                "target": "mesh_only",
                "profile": "single_region",
                "boundary_source": "array_file",
                "array_file": "boundary",
                "plot_lcfs": True,
                "plot": "mesh.png",
            },
            "gfile_path",
        ),
    ],
)
def test_required_fields(tmp_path, overrides, message):
    with pytest.raises(ConfigError, match=message):
        _load(tmp_path, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "target": "mesh_only",
            "profile": "single_region",
            "boundary_source": "lcfs",
            "gfile": "eq.gfile",
            "plasma_dx": 0.03,
        },
        {
            "profile": "nested_three_region",
            "boundary_source": "artificial_outer",
            "gfile": "eq.gfile",
            "mesh_dx": 0.03,
        },
        {
            "profile": "nested_three_region",
            "boundary_source": "artificial_outer",
            "gfile": "eq.gfile",
            "outer_dx": float("inf"),
        },
    ],
)
def test_mesh_scale_applicability_and_finite_positive_values(
    tmp_path,
    overrides,
):
    with pytest.raises(ConfigError):
        _load(tmp_path, **overrides)
