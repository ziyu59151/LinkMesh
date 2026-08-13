from __future__ import annotations

from pathlib import Path

import pytest

from linkmesh.config import (
    CliOverrides,
    ConfigError,
    RegionsGenerateOverrides,
    RegionsInspectOverrides,
    load_effective_config,
    load_regions_generate_config,
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


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "multi_array_file": "shared",
            "regions_map": "shared",
            "plot": "plot.png",
        },
        {
            "multi_array_file": "shared",
            "regions_map": "regions.toml",
            "plot": "shared",
        },
        {
            "multi_array_file": "input.rz",
            "regions_map": "shared",
            "plot": "shared",
        },
    ],
)
def test_regions_inspect_config_rejects_each_path_collision(
    tmp_path,
    overrides,
):
    with pytest.raises(ConfigError, match="路径冲突"):
        load_regions_inspect_config(
            RegionsInspectOverrides(**overrides),
            cwd=tmp_path,
        )


def test_regions_inspect_config_accepts_distinct_normalized_paths(tmp_path):
    config = load_regions_inspect_config(
        RegionsInspectOverrides(
            multi_array_file="input.rz",
            regions_map="regions.toml",
            plot="regions.png",
        ),
        cwd=tmp_path,
    )

    assert len(
        {
            config.multi_array_file_path,
            config.regions_map_path,
            config.plot_path,
        }
    ) == 3


def test_regions_inspect_config_rejects_normalized_toml_cli_collision(
    tmp_path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    shared_path = (config_dir / "shared").resolve()
    config_path = config_dir / "regions.toml"
    config_path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'inspect'\n"
        "multi_array_file = 'shared'\n"
        "regions_map = 'map.toml'\n"
        "plot = 'plot.png'\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="multi_array_file.*regions_map"):
        load_regions_inspect_config(
            RegionsInspectOverrides(
                regions_map=str(shared_path),
            ),
            config_arg=str(config_path),
            cwd=tmp_path,
        )


def test_regions_generate_config_merges_toml_and_cli_region_dx(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "regions.toml"
    config_path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'generate'\n"
        "multi_array_file = 'multi.rz'\n"
        "regions_map = 'regions-map.toml'\n"
        "plot = 'toml.png'\n"
        "[regions.mesh]\n"
        "mesh_dx = 0.08\n"
        "[regions.mesh.region_dx]\n"
        "1 = 0.03\n"
        "2 = 0.05\n",
        encoding="utf-8",
    )

    config = load_regions_generate_config(
        RegionsGenerateOverrides(
            target="trimeg",
            plot="cli.png",
            hdf5="cli.h5",
            mesh_dx=0.10,
            region_dx=["2=0.04", "3=0.02"],
        ),
        config_arg=str(config_path),
        cwd=tmp_path,
    )

    assert config.multi_array_file_path == (config_dir / "multi.rz").resolve()
    assert config.regions_map_path == (
        config_dir / "regions-map.toml"
    ).resolve()
    assert config.target == "trimeg"
    assert config.plot_path == (tmp_path / "cli.png").resolve()
    assert config.hdf5_path == (tmp_path / "cli.h5").resolve()
    assert config.mesh_dx == 0.10
    assert dict(config.region_dx) == {1: 0.03, 2: 0.04, 3: 0.02}
    assert config.transition_width == 0.0


def test_regions_generate_transition_width_merges_and_validates(tmp_path):
    config_path = tmp_path / "regions.toml"
    config_path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'generate'\n"
        "multi_array_file = 'multi.rz'\n"
        "regions_map = 'regions-map.toml'\n"
        "plot = 'mesh.png'\n"
        "[regions.mesh]\n"
        "mesh_dx = 0.08\n"
        "transition_width = 0.12\n",
        encoding="utf-8",
    )

    toml_config = load_regions_generate_config(
        RegionsGenerateOverrides(),
        config_arg=str(config_path),
        cwd=tmp_path,
    )
    assert toml_config.transition_width == 0.12

    cli_config = load_regions_generate_config(
        RegionsGenerateOverrides(transition_width=0.2),
        config_arg=str(config_path),
        cwd=tmp_path,
    )
    assert cli_config.transition_width == 0.2

    zero_config = load_regions_generate_config(
        RegionsGenerateOverrides(
            multi_array_file="multi.rz",
            regions_map="regions.toml",
            plot="mesh.png",
            mesh_dx=0.08,
            transition_width=0.0,
        ),
        cwd=tmp_path,
    )
    assert zero_config.transition_width == 0.0

    for invalid in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ConfigError, match="transition_width"):
            load_regions_generate_config(
                RegionsGenerateOverrides(
                    multi_array_file="multi.rz",
                    regions_map="regions.toml",
                    plot="mesh.png",
                    mesh_dx=0.08,
                    transition_width=invalid,
                ),
                cwd=tmp_path,
            )


def test_regions_inspect_rejects_transition_width_toml_key(tmp_path):
    path = tmp_path / "regions.toml"
    path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'inspect'\n"
        "multi_array_file = 'multi.rz'\n"
        "regions_map = 'regions-map.toml'\n"
        "plot = 'mesh.png'\n"
        "[regions.mesh]\n"
        "transition_width = 0.1\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="未知"):
        load_regions_inspect_config(
            RegionsInspectOverrides(),
            config_arg=str(path),
            cwd=tmp_path,
        )


def test_regions_generate_target_defaults_and_hdf5_contract(tmp_path):
    base = {
        "multi_array_file": "multi.rz",
        "regions_map": "regions.toml",
        "plot": "mesh.png",
        "mesh_dx": 0.08,
    }

    mesh_only = load_regions_generate_config(
        RegionsGenerateOverrides(**base),
        cwd=tmp_path,
    )
    assert mesh_only.target == "mesh_only"
    assert mesh_only.hdf5_path is None

    with pytest.raises(ConfigError, match="mesh_only.*禁止"):
        load_regions_generate_config(
            RegionsGenerateOverrides(**base, hdf5="mesh.h5"),
            cwd=tmp_path,
        )

    with pytest.raises(ConfigError, match="trimeg.*需要"):
        load_regions_generate_config(
            RegionsGenerateOverrides(**base, target="trimeg"),
            cwd=tmp_path,
        )

    trimeg = load_regions_generate_config(
        RegionsGenerateOverrides(
            **base,
            target="trimeg",
            hdf5="mesh.h5",
        ),
        cwd=tmp_path,
    )
    assert trimeg.target == "trimeg"
    assert trimeg.hdf5_path == (tmp_path / "mesh.h5").resolve()


@pytest.mark.parametrize("target", ["invalid", 1])
def test_regions_generate_rejects_unsupported_target(tmp_path, target):
    with pytest.raises(ConfigError, match="target"):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                target=target,
                multi_array_file="multi.rz",
                regions_map="regions.toml",
                plot="mesh.png",
                mesh_dx=0.08,
            ),
            cwd=tmp_path,
        )


def test_regions_generate_m3dc1_requires_model_and_smb(tmp_path):
    base = {
        "target": "m3dc1",
        "multi_array_file": "multi.rz",
        "regions_map": "regions.toml",
        "plot": "mesh.png",
        "mesh_dx": 0.08,
    }

    with pytest.raises(ConfigError, match="model.*smb"):
        load_regions_generate_config(
            RegionsGenerateOverrides(**base),
            cwd=tmp_path,
        )

    config = load_regions_generate_config(
        RegionsGenerateOverrides(
            **base,
            model="model.txt",
            smb="mesh.smb",
        ),
        cwd=tmp_path,
    )
    assert config.target == "m3dc1"
    assert config.model_path == (tmp_path / "model.txt").resolve()
    assert config.smb_path == (tmp_path / "mesh.smb").resolve()
    assert config.hdf5_path is None

    with pytest.raises(ConfigError, match="禁止.*hdf5"):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                **base,
                model="model.txt",
                smb="mesh.smb",
                hdf5="mesh.h5",
            ),
            cwd=tmp_path,
        )


def test_regions_generate_cli_overrides_toml_target_and_hdf5_bases(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "regions.toml"
    config_path.write_text(
        "schema_version = 1\n"
        "[regions]\n"
        "mode = 'generate'\n"
        "target = 'trimeg'\n"
        "multi_array_file = 'multi.rz'\n"
        "regions_map = 'regions-map.toml'\n"
        "plot = 'mesh.png'\n"
        "hdf5 = 'toml.h5'\n"
        "[regions.mesh]\n"
        "mesh_dx = 0.08\n",
        encoding="utf-8",
    )

    toml_config = load_regions_generate_config(
        RegionsGenerateOverrides(),
        config_arg=str(config_path),
        cwd=tmp_path,
    )
    assert toml_config.hdf5_path == (config_dir / "toml.h5").resolve()

    cli_config = load_regions_generate_config(
        RegionsGenerateOverrides(
            target="trimeg",
            hdf5="cli.h5",
        ),
        config_arg=str(config_path),
        cwd=tmp_path,
    )
    assert cli_config.target == "trimeg"
    assert cli_config.hdf5_path == (tmp_path / "cli.h5").resolve()


@pytest.mark.parametrize(
    "hdf5, message",
    [
        ("multi.rz", "multi_array_file.*hdf5"),
        ("regions.toml", "regions_map.*hdf5"),
        ("mesh.png", "plot.*hdf5"),
    ],
)
def test_regions_generate_rejects_hdf5_path_collisions(
    tmp_path,
    hdf5,
    message,
):
    with pytest.raises(ConfigError, match=message):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                target="trimeg",
                multi_array_file="multi.rz",
                regions_map="regions.toml",
                plot="mesh.png",
                hdf5=hdf5,
                mesh_dx=0.08,
            ),
            cwd=tmp_path,
        )


@pytest.mark.parametrize(
    "tokens, message",
    [
        (["1=0.03", "1=0.04"], "重复"),
        (["0=0.03"], "正整数"),
        (["1=nan"], "有限正数"),
        (["bad"], "ID=DX"),
    ],
)
def test_regions_generate_rejects_invalid_cli_region_dx(
    tmp_path,
    tokens,
    message,
):
    with pytest.raises(ConfigError, match=message):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                multi_array_file="multi.rz",
                regions_map="regions.toml",
                plot="mesh.png",
                region_dx=tokens,
            ),
            cwd=tmp_path,
        )


def test_regions_generate_rejects_path_collision_and_missing_resolution(
    tmp_path,
):
    with pytest.raises(ConfigError, match="路径冲突"):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                multi_array_file="shared",
                regions_map="regions.toml",
                plot="shared",
                mesh_dx=0.08,
            ),
            cwd=tmp_path,
        )

    with pytest.raises(ConfigError, match="mesh-dx|mesh_dx"):
        load_regions_generate_config(
            RegionsGenerateOverrides(
                multi_array_file="multi.rz",
                regions_map="regions.toml",
                plot="mesh.png",
            ),
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
