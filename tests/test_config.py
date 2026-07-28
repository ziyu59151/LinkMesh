"""
tests/test_config.py —— LinkMesh 输入层 I/II：config.py（EffectiveConfig + linkmesh.in）验收测试。

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布输入层验收通过。最终真实回归在
Linux 服务器执行。

测试原则（蓝图 v2.3 第 6A 节）：
    - 只测试配置层（linkmesh.config）：EffectiveConfig 定义、TOML 严格读取、
      配置发现、三层合并、路径解析、required fields、兼容矩阵、当前阶段边界；
    - 不导入 OFT/h5py，不读取 GFile/CSV 内容，不构造 Mesh2D/Domain；
    - 使用 tmp_path，不写真实用户目录，不修改仓库配置文件；
    - 通过公开 API load_effective_config / discover_config / EffectiveConfig / CliOverrides。

输入层 II 状态变化：
    - single_region + lcfs（mesh_only / trimeg）现已实现，合法通过；
    - m3dc1 仅允许 single_region + lcfs；
    - single_region + first_wall/array_file、flux_surface 仍未实现。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from linkmesh import config as cfgmod
from linkmesh.config import (
    CliOverrides,
    ConfigError,
    EffectiveConfig,
    UNSET,
    discover_config,
    load_effective_config,
)


# --------------------------------------------------------------------------- #
# 辅助                                                                          #
# --------------------------------------------------------------------------- #

def _write_toml(dir_path: Path, text: str, name: str = "linkmesh.in") -> Path:
    p = dir_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _overrides(**kw) -> CliOverrides:
    """构造 CliOverrides；未在 kw 中提供的字段保持正式 UNSET sentinel。

    CliOverrides 每个字段默认即为 config.UNSET（表示“CLI 未显式提供”），
    因此仅把 kw 中显式给出的字段设值即可；不得把未提供字段设为 None，
    否则会被生产合并逻辑误判为“用户显式提供”，从而覆盖 TOML 值。

    键名使用 CLI 短名（gfile/array_file/hdf5/plot/model/smb），与生产
    CliOverrides 字段名一致，绝不能用 EffectiveConfig 长名（gfile_path 等）。
    """
    return CliOverrides(**kw)


_MINIMAL_GFILE_OVR = dict(
    profile="nested_three_region",
    boundary_source="artificial_outer",
    gfile="g.eqdsk",
)


# --------------------------------------------------------------------------- #
# 0. sentinel 契约（固定 _overrides gfile 键与 config.UNSET 身份，防再次分叉） #
# --------------------------------------------------------------------------- #

class TestOverridesSentinelContract:
    def test_overrides_gfile_key_defaults_to_config_unset(self):
        # 未提供 gfile 时，CliOverrides.gfile 必须是同一个 config.UNSET 对象。
        ovr = _overrides()
        assert ovr.gfile is UNSET
        assert ovr.gfile is cfgmod.UNSET

    def test_overrides_uses_cli_short_key_gfile(self):
        # 生产 CLI 载体字段名是短名 gfile（非 gfile_path）。
        ovr = _overrides(gfile="x.eqdsk")
        assert ovr.gfile == "x.eqdsk"
        assert not hasattr(ovr, "gfile_path")

    def test_all_path_fields_default_unset(self):
        ovr = _overrides()
        for key in ("gfile", "array_file", "hdf5", "plot", "model", "smb"):
            assert getattr(ovr, key) is UNSET


# --------------------------------------------------------------------------- #
# 1. EffectiveConfig 结构                                                       #
# --------------------------------------------------------------------------- #

class TestEffectiveConfigStructure:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(EffectiveConfig)
        params = getattr(EffectiveConfig, "__dataclass_params__")
        assert params.frozen is True

    def test_has_exactly_blueprint_fields(self):
        # 蓝图 v2.3 第 6A.2 节：15 字段。
        names = [f.name for f in dataclasses.fields(EffectiveConfig)]
        expected = [
            "schema_version", "config_path", "target", "profile",
            "boundary_source", "gfile_path", "array_file_path",
            "plasma_dx", "vacuum_dx", "outer_dx",
            "hdf5_path", "plot_path", "model_path", "smb_path", "verbose",
        ]
        assert names == expected
        assert len(names) == 15

    def test_frozen_instance_immutable(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.plasma_dx = 0.5  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# 2. 内建默认值                                                                 #
# --------------------------------------------------------------------------- #

class TestBuiltinDefaults:
    def test_no_config_uses_defaults(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.schema_version == 1
        assert cfg.target == "trimeg"
        assert cfg.profile == "nested_three_region"
        assert cfg.boundary_source == "artificial_outer"
        assert cfg.plasma_dx == 0.08
        assert cfg.vacuum_dx == 0.10
        assert cfg.outer_dx == 0.15
        assert cfg.verbose is False

    def test_default_hdf5_path_for_trimeg(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.hdf5_path is not None
        assert cfg.hdf5_path.name == "mesh.h5"
        assert cfg.hdf5_path.is_absolute()

    def test_default_plot_and_m4_paths_none(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.plot_path is None
        assert cfg.model_path is None
        assert cfg.smb_path is None

    def test_config_path_none_when_no_config(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.config_path is None


# --------------------------------------------------------------------------- #
# 3. 配置发现                                                                   #
# --------------------------------------------------------------------------- #

class TestDiscovery:
    def test_auto_discover_current_dir(self, tmp_path):
        p = _write_toml(tmp_path, "schema_version = 1\n")
        found = discover_config(config_arg=None, no_config=False, cwd=tmp_path)
        assert found == p.resolve()

    def test_no_config_disables_discovery(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n")
        found = discover_config(config_arg=None, no_config=True, cwd=tmp_path)
        assert found is None

    def test_explicit_config_only(self, tmp_path):
        sub = tmp_path / "cfg"
        sub.mkdir()
        p = _write_toml(sub, "schema_version = 1\n", name="custom.in")
        found = discover_config(
            config_arg=str(p), no_config=False, cwd=tmp_path
        )
        assert found == p.resolve()

    def test_explicit_config_missing_fails(self, tmp_path):
        with pytest.raises(ConfigError):
            discover_config(
                config_arg=str(tmp_path / "nope.in"), no_config=False, cwd=tmp_path
            )

    def test_config_and_no_config_conflict(self, tmp_path):
        p = _write_toml(tmp_path, "schema_version = 1\n")
        with pytest.raises(ConfigError):
            discover_config(config_arg=str(p), no_config=True, cwd=tmp_path)

    def test_no_recursion_to_parent(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n")
        child = tmp_path / "child"
        child.mkdir()
        found = discover_config(config_arg=None, no_config=False, cwd=child)
        assert found is None


# --------------------------------------------------------------------------- #
# 4. TOML 严格校验                                                              #
# --------------------------------------------------------------------------- #

class TestTomlStrict:
    def _load(self, tmp_path, text, overrides=None):
        _write_toml(tmp_path, text)
        ovr = overrides if overrides is not None else _overrides(**_MINIMAL_GFILE_OVR)
        return load_effective_config(ovr, no_config=False, cwd=tmp_path)

    def test_syntax_error_fails(self, tmp_path):
        with pytest.raises(ConfigError):
            self._load(tmp_path, "schema_version = = 1\n")

    def test_missing_schema_version_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="schema_version"):
            self._load(tmp_path, "[mesh]\nplasma_dx = 0.08\n")

    def test_schema_version_not_1_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="schema_version"):
            self._load(tmp_path, "schema_version = 2\n")

    def test_schema_version_bool_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="schema_version"):
            self._load(tmp_path, "schema_version = true\n")

    def test_unknown_top_level_key_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="未知顶层键"):
            self._load(tmp_path, "schema_version = 1\nfoo = 1\n")

    def test_unknown_section_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="未知 section"):
            self._load(tmp_path, "schema_version = 1\n[bogus]\nk = 1\n")

    def test_unknown_key_in_task(self, tmp_path):
        with pytest.raises(ConfigError, match="未知键"):
            self._load(tmp_path, "schema_version = 1\n[task]\nbogus = 1\n")

    def test_unknown_key_in_mesh(self, tmp_path):
        with pytest.raises(ConfigError, match="未知键"):
            self._load(tmp_path, "schema_version = 1\n[mesh]\nbogus = 1\n")

    def test_unknown_key_in_output(self, tmp_path):
        with pytest.raises(ConfigError, match="未知键"):
            self._load(tmp_path, "schema_version = 1\n[output]\nbogus = 'x'\n")

    def test_bad_dx_type_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="plasma_dx"):
            self._load(
                tmp_path,
                "schema_version = 1\n[mesh]\nplasma_dx = 'big'\n",
            )

    def test_negative_dx_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="plasma_dx"):
            self._load(
                tmp_path,
                "schema_version = 1\n[mesh]\nplasma_dx = -0.1\n",
            )

    def test_bad_target_enum_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="target"):
            self._load(tmp_path, "schema_version = 1\n[task]\ntarget = 'nope'\n")

    def test_bad_profile_enum_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="profile"):
            self._load(
                tmp_path, "schema_version = 1\n[domain]\nprofile = 'nope'\n"
            )

    def test_bad_boundary_source_enum_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="boundary_source"):
            self._load(
                tmp_path,
                "schema_version = 1\n[domain]\nboundary_source = 'nope'\n",
            )

    def test_bad_verbose_type_fails(self, tmp_path):
        with pytest.raises(ConfigError, match="verbose"):
            self._load(
                tmp_path, "schema_version = 1\n[runtime]\nverbose = 'yes'\n"
            )

    def test_error_message_contains_config_path(self, tmp_path):
        p = _write_toml(tmp_path, "schema_version = 1\nfoo = 1\n")
        with pytest.raises(ConfigError) as ei:
            load_effective_config(
                _overrides(**_MINIMAL_GFILE_OVR), no_config=False, cwd=tmp_path
            )
        assert str(p.resolve()) in str(ei.value)


# --------------------------------------------------------------------------- #
# 5. 三层合并                                                                   #
# --------------------------------------------------------------------------- #

class TestMerge:
    def test_toml_overrides_default(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n[mesh]\nplasma_dx = 0.03\n")
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=False, cwd=tmp_path
        )
        assert cfg.plasma_dx == 0.03
        assert cfg.vacuum_dx == 0.10  # 未在 TOML 出现 → 默认

    def test_cli_overrides_toml(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n[mesh]\nplasma_dx = 0.03\n")
        ovr = _overrides(plasma_dx=0.07, **_MINIMAL_GFILE_OVR)
        cfg = load_effective_config(ovr, no_config=False, cwd=tmp_path)
        assert cfg.plasma_dx == 0.07

    def test_unset_cli_does_not_override_toml(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n[mesh]\nvacuum_dx = 0.22\n")
        # 不提供 vacuum_dx（保持 UNSET）
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=False, cwd=tmp_path
        )
        assert cfg.vacuum_dx == 0.22

    def test_cli_target_overrides_toml(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n[task]\ntarget = 'trimeg'\n")
        ovr = _overrides(target="mesh_only", **_MINIMAL_GFILE_OVR)
        cfg = load_effective_config(ovr, no_config=False, cwd=tmp_path)
        assert cfg.target == "mesh_only"

    def test_toml_profile_boundary_used(self, tmp_path):
        # TOML 提供 domain 与 input.gfile；CLI 全部未显式提供（保持 UNSET），
        # 因此 profile/boundary_source/gfile 均应采用 TOML 值。
        _write_toml(
            tmp_path,
            "schema_version = 1\n[domain]\nprofile = 'nested_three_region'\n"
            "boundary_source = 'artificial_outer'\n[input]\ngfile = 'g.eqdsk'\n",
        )
        cfg = load_effective_config(_overrides(), no_config=False, cwd=tmp_path)
        assert cfg.profile == "nested_three_region"
        assert cfg.boundary_source == "artificial_outer"
        # TOML 中的 gfile 被采用（相对配置目录解析为绝对路径）
        assert cfg.gfile_path == (tmp_path / "g.eqdsk").resolve()

    def test_toml_gfile_used_when_cli_gfile_unset(self, tmp_path):
        # CLI gfile 保持 UNSET → 采用 TOML [input].gfile。
        _write_toml(
            tmp_path,
            "schema_version = 1\n[input]\ngfile = 'from_toml.eqdsk'\n",
        )
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer"),
            no_config=False, cwd=tmp_path,
        )
        assert cfg.gfile_path == (tmp_path / "from_toml.eqdsk").resolve()

    def test_cli_gfile_overrides_toml_with_cwd_base(self, tmp_path):
        # CLI 显式 gfile 覆盖 TOML，且相对路径以 cwd 为基准。
        _write_toml(
            tmp_path,
            "schema_version = 1\n[input]\ngfile = 'from_toml.eqdsk'\n",
        )
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer",
                       gfile="from_cli.eqdsk"),
            no_config=False, cwd=tmp_path,
        )
        assert cfg.gfile_path == (tmp_path / "from_cli.eqdsk").resolve()
        assert cfg.gfile_path != (tmp_path / "from_toml.eqdsk").resolve()

    def test_toml_selects_single_region_lcfs(self, tmp_path):
        # 输入层 II：配置文件可选择 single_region + lcfs。
        _write_toml(
            tmp_path,
            "schema_version = 1\n[task]\ntarget = 'trimeg'\n"
            "[domain]\nprofile = 'single_region'\nboundary_source = 'lcfs'\n"
            "[input]\ngfile = 'g.eqdsk'\n",
        )
        cfg = load_effective_config(_overrides(), no_config=False, cwd=tmp_path)
        assert cfg.profile == "single_region"
        assert cfg.boundary_source == "lcfs"
        assert cfg.gfile_path == (tmp_path / "g.eqdsk").resolve()


# --------------------------------------------------------------------------- #
# 6. 路径解析                                                                   #
# --------------------------------------------------------------------------- #

class TestPathResolution:
    def test_toml_relative_path_based_on_config_dir(self, tmp_path):
        sub = tmp_path / "cfg"
        sub.mkdir()
        _write_toml(
            sub,
            "schema_version = 1\n[input]\ngfile = 'eq.gfile'\n",
            name="custom.in",
        )
        # CLI 不显式提供 gfile（保持 UNSET），使 TOML 的相对 gfile 生效；
        # 该相对路径应相对配置文件所在目录（sub）解析，而非 cwd（tmp_path）。
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer"),
            config_arg=str(sub / "custom.in"),
            no_config=False,
            cwd=tmp_path,
        )
        assert cfg.gfile_path == (sub / "eq.gfile").resolve()
        # 明确不是相对 cwd 解析
        assert cfg.gfile_path != (tmp_path / "eq.gfile").resolve()

    def test_cli_relative_path_based_on_cwd(self, tmp_path):
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer",
                       gfile="eq.gfile"),
            no_config=True,
            cwd=tmp_path,
        )
        assert cfg.gfile_path == (tmp_path / "eq.gfile").resolve()

    def test_cli_overrides_toml_path_with_cwd_base(self, tmp_path):
        sub = tmp_path / "cfg"
        sub.mkdir()
        _write_toml(
            sub,
            "schema_version = 1\n[input]\ngfile = 'toml.gfile'\n",
            name="custom.in",
        )
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer",
                       gfile="cli.gfile"),
            config_arg=str(sub / "custom.in"),
            no_config=False,
            cwd=tmp_path,
        )
        # CLI 显式路径基于 cwd，覆盖 TOML 路径
        assert cfg.gfile_path == (tmp_path / "cli.gfile").resolve()

    def test_paths_are_absolute(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.gfile_path.is_absolute()
        assert cfg.hdf5_path.is_absolute()

    def test_config_path_absolute(self, tmp_path):
        _write_toml(tmp_path, "schema_version = 1\n")
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=False, cwd=tmp_path
        )
        assert cfg.config_path is not None
        assert cfg.config_path.is_absolute()

    def test_toml_output_hdf5_relative_to_config_dir(self, tmp_path):
        # 覆盖路径字段键名映射：TOML [output].hdf5 → hdf5_path，相对配置目录。
        sub = tmp_path / "cfg"
        sub.mkdir()
        _write_toml(
            sub,
            "schema_version = 1\n[input]\ngfile = 'eq.gfile'\n"
            "[output]\nhdf5 = 'out.h5'\n",
            name="custom.in",
        )
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer"),
            config_arg=str(sub / "custom.in"),
            no_config=False,
            cwd=tmp_path,
        )
        assert cfg.hdf5_path == (sub / "out.h5").resolve()

    def test_no_env_expansion(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LINKMESH_TEST_VAR", "should_not_expand")
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer",
                       gfile="$LINKMESH_TEST_VAR/eq.gfile"),
            no_config=True,
            cwd=tmp_path,
        )
        # 环境变量未展开：字面量 $LINKMESH_TEST_VAR 仍在路径中
        assert "$LINKMESH_TEST_VAR" in str(cfg.gfile_path)
        assert "should_not_expand" not in str(cfg.gfile_path)

    def test_no_tilde_expansion(self, tmp_path):
        cfg = load_effective_config(
            _overrides(profile="nested_three_region",
                       boundary_source="artificial_outer",
                       gfile="~/eq.gfile"),
            no_config=True,
            cwd=tmp_path,
        )
        # ~ 未展开为主目录：字面量 ~ 仍在路径中
        assert "~" in str(cfg.gfile_path)


# --------------------------------------------------------------------------- #
# 7. required fields                                                            #
# --------------------------------------------------------------------------- #

class TestRequiredFields:
    def test_lcfs_requires_gfile(self, tmp_path):
        # single_region + lcfs 现已实现；缺 gfile 应报 required 错误（先于业务）。
        with pytest.raises(ConfigError, match="gfile"):
            load_effective_config(
                _overrides(profile="single_region", boundary_source="lcfs"),
                no_config=True, cwd=tmp_path,
            )

    def test_lcfs_forbids_array_file(self, tmp_path):
        with pytest.raises(ConfigError):
            load_effective_config(
                _overrides(profile="single_region", boundary_source="lcfs",
                           gfile="g.eqdsk", array_file="b.csv"),
                no_config=True, cwd=tmp_path,
            )

    def test_array_file_requires_array_file(self, tmp_path):
        with pytest.raises(ConfigError, match="array_file"):
            load_effective_config(
                _overrides(profile="single_region", boundary_source="array_file"),
                no_config=True, cwd=tmp_path,
            )

    def test_array_file_forbids_gfile(self, tmp_path):
        with pytest.raises(ConfigError):
            load_effective_config(
                _overrides(profile="single_region", boundary_source="array_file",
                           array_file="b.csv", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_artificial_outer_requires_gfile(self, tmp_path):
        with pytest.raises(ConfigError, match="gfile"):
            load_effective_config(
                _overrides(profile="nested_three_region",
                           boundary_source="artificial_outer"),
                no_config=True, cwd=tmp_path,
            )

    def test_first_wall_requires_gfile(self, tmp_path):
        with pytest.raises(ConfigError, match="gfile"):
            load_effective_config(
                _overrides(profile="single_region", boundary_source="first_wall"),
                no_config=True, cwd=tmp_path,
            )


# --------------------------------------------------------------------------- #
# 8. 兼容矩阵                                                                   #
# --------------------------------------------------------------------------- #

class TestCompatibility:
    def test_valid_trimeg_nested_artificial(self, tmp_path):
        cfg = load_effective_config(
            _overrides(**_MINIMAL_GFILE_OVR), no_config=True, cwd=tmp_path
        )
        assert cfg.target == "trimeg"
        assert cfg.profile == "nested_three_region"
        assert cfg.boundary_source == "artificial_outer"

    def test_m3dc1_nested_forbidden(self, tmp_path):
        with pytest.raises(ConfigError, match="m3dc1"):
            load_effective_config(
                _overrides(target="m3dc1", profile="nested_three_region",
                           boundary_source="artificial_outer", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_nested_lcfs_forbidden(self, tmp_path):
        with pytest.raises(ConfigError, match="不匹配"):
            load_effective_config(
                _overrides(profile="nested_three_region",
                           boundary_source="lcfs", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_nested_first_wall_forbidden(self, tmp_path):
        with pytest.raises(ConfigError):
            load_effective_config(
                _overrides(profile="nested_three_region",
                           boundary_source="first_wall", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_nested_array_file_forbidden(self, tmp_path):
        with pytest.raises(ConfigError):
            load_effective_config(
                _overrides(profile="nested_three_region",
                           boundary_source="array_file", array_file="b.csv"),
                no_config=True, cwd=tmp_path,
            )

    def test_single_region_artificial_outer_forbidden(self, tmp_path):
        with pytest.raises(ConfigError, match="artificial_outer"):
            load_effective_config(
                _overrides(profile="single_region",
                           boundary_source="artificial_outer", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )


# --------------------------------------------------------------------------- #
# 9. 当前阶段实现边界                                                           #
# --------------------------------------------------------------------------- #

class TestCurrentStage:
    def test_flux_surface_not_implemented(self, tmp_path):
        with pytest.raises(NotImplementedError, match="flux_surface"):
            load_effective_config(
                _overrides(profile="single_region",
                           boundary_source="flux_surface", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_m3dc1_single_region_lcfs_allowed(self, tmp_path):
        cfg = load_effective_config(
            _overrides(
                target="m3dc1",
                profile="single_region",
                boundary_source="lcfs",
                gfile="g.eqdsk",
                model="model.txt",
                smb="mesh.smb",
            ),
            no_config=True,
            cwd=tmp_path,
        )
        assert cfg.target == "m3dc1"
        assert cfg.profile == "single_region"
        assert cfg.boundary_source == "lcfs"
        assert cfg.model_path == (tmp_path / "model.txt").resolve()
        assert cfg.smb_path == (tmp_path / "mesh.smb").resolve()

    def test_m3dc1_requires_model_and_smb_paths(self, tmp_path):
        with pytest.raises(ConfigError, match="model_path"):
            load_effective_config(
                _overrides(
                    target="m3dc1",
                    profile="single_region",
                    boundary_source="lcfs",
                    gfile="g.eqdsk",
                    smb="mesh.smb",
                ),
                no_config=True,
                cwd=tmp_path,
            )

    def test_m3dc1_nested_forbidden(self, tmp_path):
        with pytest.raises(ConfigError, match="m3dc1"):
            load_effective_config(
                _overrides(
                    target="m3dc1",
                    profile="nested_three_region",
                    boundary_source="artificial_outer",
                    gfile="g.eqdsk",
                    model="model.txt",
                    smb="mesh.smb",
                ),
                no_config=True,
                cwd=tmp_path,
            )

    def test_m3dc1_non_lcfs_forbidden(self, tmp_path):
        with pytest.raises(ConfigError, match="single_region"):
            load_effective_config(
                _overrides(
                    target="m3dc1",
                    profile="single_region",
                    boundary_source="first_wall",
                    gfile="g.eqdsk",
                    model="model.txt",
                    smb="mesh.smb",
                ),
                no_config=True,
                cwd=tmp_path,
            )

    def test_single_region_first_wall_not_implemented(self, tmp_path):
        with pytest.raises(NotImplementedError, match="single_region"):
            load_effective_config(
                _overrides(profile="single_region",
                           boundary_source="first_wall", gfile="g.eqdsk"),
                no_config=True, cwd=tmp_path,
            )

    def test_single_region_array_file_not_implemented(self, tmp_path):
        with pytest.raises(NotImplementedError, match="single_region"):
            load_effective_config(
                _overrides(profile="single_region",
                           boundary_source="array_file", array_file="b.csv"),
                no_config=True, cwd=tmp_path,
            )

    def test_mesh_only_nested_artificial_allowed(self, tmp_path):
        # mesh_only + nested_three_region + artificial_outer 属首批目标，允许通过。
        cfg = load_effective_config(
            _overrides(target="mesh_only", profile="nested_three_region",
                       boundary_source="artificial_outer", gfile="g.eqdsk"),
            no_config=True, cwd=tmp_path,
        )
        assert cfg.target == "mesh_only"
        # mesh_only 不强制 hdf5，hdf5_path 默认 None
        assert cfg.hdf5_path is None


# --------------------------------------------------------------------------- #
# 9b. 输入层 II：single_region + lcfs 现在合法                                  #
# --------------------------------------------------------------------------- #

class TestSingleRegionLcfsImplemented:
    def test_mesh_only_single_region_lcfs_allowed(self, tmp_path):
        cfg = load_effective_config(
            _overrides(target="mesh_only", profile="single_region",
                       boundary_source="lcfs", gfile="g.eqdsk"),
            no_config=True, cwd=tmp_path,
        )
        assert cfg.target == "mesh_only"
        assert cfg.profile == "single_region"
        assert cfg.boundary_source == "lcfs"
        assert cfg.gfile_path == (tmp_path / "g.eqdsk").resolve()
        # mesh_only 不强制 hdf5
        assert cfg.hdf5_path is None

    def test_trimeg_single_region_lcfs_allowed(self, tmp_path):
        cfg = load_effective_config(
            _overrides(target="trimeg", profile="single_region",
                       boundary_source="lcfs", gfile="g.eqdsk"),
            no_config=True, cwd=tmp_path,
        )
        assert cfg.target == "trimeg"
        assert cfg.profile == "single_region"
        assert cfg.boundary_source == "lcfs"
        # trimeg 需要 hdf5_path（默认 mesh.h5）
        assert cfg.hdf5_path is not None
        assert cfg.hdf5_path.name == "mesh.h5"

    def test_single_region_lcfs_requires_gfile(self, tmp_path):
        with pytest.raises(ConfigError, match="gfile"):
            load_effective_config(
                _overrides(target="trimeg", profile="single_region",
                           boundary_source="lcfs"),
                no_config=True, cwd=tmp_path,
            )

    def test_single_region_lcfs_forbids_array_file(self, tmp_path):
        with pytest.raises(ConfigError):
            load_effective_config(
                _overrides(target="trimeg", profile="single_region",
                           boundary_source="lcfs",
                           gfile="g.eqdsk", array_file="b.csv"),
                no_config=True, cwd=tmp_path,
            )


# --------------------------------------------------------------------------- #
# 10. 模块边界（不导入 OFT/h5py）                                               #
# --------------------------------------------------------------------------- #

class TestModuleBoundaries:
    def test_config_module_does_not_hold_oft_or_h5py(self):
        # config 模块命名空间不应直接持有 oft/h5py 符号
        assert not hasattr(cfgmod, "h5py")
        assert not hasattr(cfgmod, "gs_Domain")

    def test_enums_exposed(self):
        assert cfgmod.TARGETS == ("mesh_only", "trimeg", "m3dc1")
        assert cfgmod.PROFILES == ("single_region", "nested_three_region")
        assert "artificial_outer" in cfgmod.BOUNDARY_SOURCES
        assert "flux_surface" in cfgmod.BOUNDARY_SOURCES
