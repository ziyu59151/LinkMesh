"""
config.py —— LinkMesh 两层输入架构：EffectiveConfig 与 linkmesh.in 读取/校验/合并。

职责（严格对齐 LinkMesh_Architecture_Plan.md v2.3 第 6A 节）：
    - 定义只读/不可变 EffectiveConfig（@dataclass(frozen=True)，字段逐项匹配第 6A.2 节）；
    - 使用标准库 tomllib 读取 linkmesh.in（v1 schema）；
    - 严格校验 schema_version、允许的 section、允许的键、值类型与枚举；
    - 配置文件发现（--config / --no-config / 当前目录自动发现）；
    - 合并「内建默认值 < linkmesh.in < 用户显式 CLI」；
    - 按配置目录 / 当前工作目录两套基准解析路径，全部规范化为绝对路径；
    - 校验 target/profile/boundary_source 兼容矩阵与 required fields；
    - 输出已完成路径解析与类型验证的 EffectiveConfig。

禁止事项（第 2 节表 / 第 6A 节）：
    - 不导入 OFT、h5py；
    - 不读取 GFile 内容、不读取 array CSV 内容；
    - 不构造 Mesh2D、不构造 OFT Domain；
    - 不调用 Mesher/Writer/Plotter；
    - 不保存值来源字典、NumPy 数组、Mesh2D、GFileData、PUMI 句柄、Writer 实例、
      argparse Namespace；
    - 不建设通用配置 DSL、插件系统、注册表、抽象基类或任意 N 区域语言。

内建默认值集中在本模块（第 6A.3 节），CLI 只负责收集用户显式输入。

CLI 依赖契约（供 cli.py 导入）：
    - 序列枚举：TARGETS / PROFILES / BOUNDARY_SOURCES；
    - 哨兵：UNSET；
    - 可变输入载体：CliOverrides；
    - 异常：ConfigError；
    - 合并入口：load_effective_config(overrides, config_arg=..., no_config=...)；
    - 只读结果：EffectiveConfig（17 字段）。

键名约定（重要）：
    - CliOverrides 使用 CLI 短键名：gfile/array_file/hdf5/plot/model/smb（与 argparse
      dest 一致）；
    - _load_toml 输出与 EffectiveConfig 字段名一致的长键名：gfile_path/array_file_path/
      hdf5_path/plot_path/model_path/smb_path；
    - 因此路径合并时必须分别用「CLI 键」查 CliOverrides、用「EffectiveConfig 键」查
      TOML 映射，二者不可混用同一名称（标量字段两侧键名恰好相同，不受影响）。

参考规范：
    LinkMesh_Architecture_Plan.md v2.3 第 6A.1–6A.13 节
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping, Optional


# --------------------------------------------------------------------------- #
# 枚举与内建默认值（正式唯一来源，第 6A.2 / 6A.3 节）                           #
# --------------------------------------------------------------------------- #

SCHEMA_VERSION = 1

TARGETS = ("mesh_only", "trimeg", "m3dc1")
PROFILES = ("single_region", "nested_three_region")
BOUNDARY_SOURCES = (
    "lcfs",
    "first_wall",
    "array_file",
    "artificial_outer",
    "flux_surface",
)

# 内建默认值（第 6A.3 节）。无配置文件、无新增显式 CLI 时保持旧 CLI 行为。
DEFAULT_TARGET = "trimeg"
DEFAULT_PROFILE = "nested_three_region"
DEFAULT_BOUNDARY_SOURCE = "artificial_outer"
DEFAULT_MESH_DX = 0.08
DEFAULT_PLASMA_DX = 0.08
DEFAULT_VACUUM_DX = 0.10
DEFAULT_OUTER_DX = 0.15
DEFAULT_VERBOSE = False
DEFAULT_PLOT_LCFS = False

# 路径默认值（第 6A.3 节，经只读核对实时 cli.py）：
#   - hdf5 默认 mesh.h5（仅当 target=trimeg 需要时作为默认输出）；
#   - plot 默认 None（不生成 PNG）；
#   - model/smb 不制造尚未存在的可执行默认路径（首批 None）。
DEFAULT_HDF5_NAME = "mesh.h5"

# 允许的 TOML section 与逐 section 键（第 6A.4 节）。
_ALLOWED_TOP_LEVEL_KEYS = {"schema_version"}
_ALLOWED_SECTIONS = {"task", "input", "domain", "mesh", "output", "runtime"}
_ALLOWED_SECTION_KEYS = {
    "task": {"target"},
    "input": {"gfile", "array_file"},
    "domain": {"profile", "boundary_source"},
    "mesh": {"mesh_dx", "plasma_dx", "vacuum_dx", "outer_dx"},
    "output": {"hdf5", "plot", "model", "smb", "plot_lcfs"},
    "runtime": {"verbose"},
}


# --------------------------------------------------------------------------- #
# 异常                                                                          #
# --------------------------------------------------------------------------- #

class ConfigError(ValueError):
    """配置读取、校验或合并阶段的错误（ValueError 子类，便于 CLI 统一捕获）。"""


# --------------------------------------------------------------------------- #
# EffectiveConfig（frozen dataclass，17 字段）                                 #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EffectiveConfig:
    """LinkMesh 只读/不可变有效配置（合并「默认 < TOML < 显式 CLI」的最终结果）。

    字段逐项对齐当前蓝图字段表（共 17 字段）。所有非 None Path
    均为规范化绝对路径。不保存值来源字典、NumPy 数组、句柄或 Namespace。
    """

    schema_version: int
    config_path: Optional[Path]
    target: Literal["mesh_only", "trimeg", "m3dc1"]
    profile: Literal["single_region", "nested_three_region"]
    boundary_source: Literal[
        "lcfs", "first_wall", "array_file", "artificial_outer", "flux_surface"
    ]
    gfile_path: Optional[Path]
    array_file_path: Optional[Path]
    mesh_dx: float
    plasma_dx: float
    vacuum_dx: float
    outer_dx: float
    hdf5_path: Optional[Path]
    plot_path: Optional[Path]
    model_path: Optional[Path]
    smb_path: Optional[Path]
    verbose: bool
    plot_lcfs: bool


# --------------------------------------------------------------------------- #
# CLI 覆盖载体（内部 sentinel：未提供的字段保持缺省，不进入最终对象）          #
# --------------------------------------------------------------------------- #

class _Unset:
    """哨兵：表示某 CLI 字段未由用户显式提供。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - 仅调试
        return "UNSET"


UNSET = _Unset()


@dataclass
class RegionsInspectOverrides:
    """Explicit CLI values for the isolated regions-inspect configuration."""

    multi_array_file: Any = UNSET
    regions_map: Any = UNSET
    plot: Any = UNSET
    verbose: Any = UNSET


@dataclass(frozen=True)
class RegionsInspectConfig:
    """Resolved configuration for ``linkmesh regions inspect`` only."""

    schema_version: int
    config_path: Optional[Path]
    mode: Literal["inspect"]
    multi_array_file_path: Path
    regions_map_path: Path
    plot_path: Path
    verbose: bool


@dataclass
class RegionsGenerateOverrides:
    """Explicit CLI values for the isolated regions-generate configuration."""

    target: Any = UNSET
    multi_array_file: Any = UNSET
    regions_map: Any = UNSET
    plot: Any = UNSET
    hdf5: Any = UNSET
    model: Any = UNSET
    smb: Any = UNSET
    mesh_dx: Any = UNSET
    region_dx: Any = UNSET
    verbose: Any = UNSET


@dataclass(frozen=True)
class RegionsGenerateConfig:
    """Resolved configuration for ``linkmesh regions generate`` only."""

    schema_version: int
    config_path: Optional[Path]
    mode: Literal["generate"]
    target: Literal["mesh_only", "trimeg", "m3dc1"]
    multi_array_file_path: Path
    regions_map_path: Path
    plot_path: Path
    hdf5_path: Optional[Path]
    model_path: Optional[Path]
    smb_path: Optional[Path]
    mesh_dx: Optional[float]
    region_dx: Mapping[int, float]
    verbose: bool


@dataclass
class CliOverrides:
    """CLI 收集的用户显式输入（未提供者保持 UNSET）。

    该对象是合并输入，不是最终配置；仅传给 load_effective_config。
    路径字段以字符串保存（相对进程当前工作目录解析）。

    注意：cli.py 会在构造后对 verbose 字段赋值（overrides.verbose = True），
    因此本类必须为可变 dataclass（不加 frozen）。

    路径字段键名使用 CLI 短名（gfile/array_file/hdf5/plot/model/smb），与
    EffectiveConfig 的长名（gfile_path 等）不同，合并逻辑需分别映射。
    """

    target: Any = UNSET
    profile: Any = UNSET
    boundary_source: Any = UNSET
    gfile: Any = UNSET
    array_file: Any = UNSET
    mesh_dx: Any = UNSET
    plasma_dx: Any = UNSET
    vacuum_dx: Any = UNSET
    outer_dx: Any = UNSET
    hdf5: Any = UNSET
    plot: Any = UNSET
    model: Any = UNSET
    smb: Any = UNSET
    verbose: Any = UNSET
    plot_lcfs: Any = UNSET


# --------------------------------------------------------------------------- #
# 内部辅助：类型/枚举校验                                                       #
# --------------------------------------------------------------------------- #

def _fail(config_path: Optional[Path], where: str, msg: str) -> None:
    prefix = f"[配置文件 {config_path}] " if config_path is not None else ""
    raise ConfigError(f"{prefix}{where}：{msg}")


def _check_enum(value: Any, allowed: tuple, name: str,
                config_path: Optional[Path]) -> str:
    if not isinstance(value, str) or value not in allowed:
        _fail(
            config_path, name,
            f"取值非法，实际={value!r}，允许={list(allowed)}",
        )
    return value


def _check_positive_float(value: Any, name: str,
                          config_path: Optional[Path]) -> float:
    # TOML 中数值可能被解析为 int 或 float；bool 是 int 子类，需排除。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(config_path, name, f"必须是数值，实际类型={type(value).__name__}")
    v = float(value)
    if not (math.isfinite(v) and v > 0.0):
        _fail(config_path, name, f"必须是有限正数，实际={value}")
    return v


def _check_bool(value: Any, name: str, config_path: Optional[Path]) -> bool:
    if not isinstance(value, bool):
        _fail(config_path, name, f"必须是布尔值，实际类型={type(value).__name__}")
    return value


def _check_str_path(value: Any, name: str, config_path: Optional[Path]) -> str:
    if not isinstance(value, str) or value == "":
        _fail(config_path, name, f"必须是非空字符串路径，实际={value!r}")
    return value


# --------------------------------------------------------------------------- #
# TOML 读取与严格 schema 校验（第 6A.4 节）                                     #
# --------------------------------------------------------------------------- #

def _load_toml(config_path: Path) -> dict:
    """读取并严格校验 linkmesh.in，返回已按 EffectiveConfig 字段名归一的原始值字典。

    返回的字典只包含 TOML 中实际出现的键（映射到 EffectiveConfig 字段名，
    路径字段用长名 gfile_path/array_file_path/hdf5_path/plot_path/model_path/smb_path），
    未出现的键不放入（表示未提供）。路径值保持字符串（相对配置目录解析在后续步骤）。
    """
    try:
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(
            f"[配置文件 {config_path}] TOML 语法错误：{e}"
        ) from e
    except OSError as e:
        raise ConfigError(
            f"[配置文件 {config_path}] 无法读取：{e}"
        ) from e

    if not isinstance(raw, dict):
        _fail(config_path, "顶层", "TOML 顶层必须是表（键值映射）")

    # 顶层：schema_version 必须存在且为整数 1；其余顶层非 section 键立即失败。
    if "schema_version" not in raw:
        _fail(config_path, "schema_version", "缺失，v1 schema 要求顶层 schema_version = 1")

    sv = raw["schema_version"]
    if isinstance(sv, bool) or not isinstance(sv, int) or sv != SCHEMA_VERSION:
        _fail(
            config_path, "schema_version",
            f"必须是整数 {SCHEMA_VERSION}，实际={sv!r}",
        )

    # 分离 section 与非 section 顶层键。
    for key, val in raw.items():
        if key in _ALLOWED_TOP_LEVEL_KEYS:
            continue
        # 允许的 section 是表；其余顶层键（无论是否为表）都视为未知。
        if key in _ALLOWED_SECTIONS:
            if not isinstance(val, dict):
                _fail(config_path, f"[{key}]", "必须是 TOML 表（section）")
            continue
        if isinstance(val, dict):
            _fail(config_path, f"[{key}]", "未知 section，不被 v1 schema 允许")
        _fail(config_path, key, "未知顶层键，不被 v1 schema 允许")

    # 逐 section 校验未知键。
    for section, allowed_keys in _ALLOWED_SECTION_KEYS.items():
        if section not in raw:
            continue
        body = raw[section]
        for k in body.keys():
            if k not in allowed_keys:
                _fail(
                    config_path, f"[{section}].{k}",
                    f"未知键，[{section}] 只允许 {sorted(allowed_keys)}",
                )

    # 抽取并类型校验，映射到 EffectiveConfig 字段名。
    out: dict = {"schema_version": SCHEMA_VERSION}

    task = raw.get("task", {})
    if "target" in task:
        out["target"] = _check_enum(task["target"], TARGETS, "[task].target", config_path)

    inp = raw.get("input", {})
    if "gfile" in inp:
        out["gfile_path"] = _check_str_path(inp["gfile"], "[input].gfile", config_path)
    if "array_file" in inp:
        out["array_file_path"] = _check_str_path(
            inp["array_file"], "[input].array_file", config_path
        )

    dom = raw.get("domain", {})
    if "profile" in dom:
        out["profile"] = _check_enum(
            dom["profile"], PROFILES, "[domain].profile", config_path
        )
    if "boundary_source" in dom:
        out["boundary_source"] = _check_enum(
            dom["boundary_source"], BOUNDARY_SOURCES,
            "[domain].boundary_source", config_path,
        )

    mesh = raw.get("mesh", {})
    if "mesh_dx" in mesh:
        out["mesh_dx"] = _check_positive_float(
            mesh["mesh_dx"], "[mesh].mesh_dx", config_path
        )
    if "plasma_dx" in mesh:
        out["plasma_dx"] = _check_positive_float(
            mesh["plasma_dx"], "[mesh].plasma_dx", config_path
        )
    if "vacuum_dx" in mesh:
        out["vacuum_dx"] = _check_positive_float(
            mesh["vacuum_dx"], "[mesh].vacuum_dx", config_path
        )
    if "outer_dx" in mesh:
        out["outer_dx"] = _check_positive_float(
            mesh["outer_dx"], "[mesh].outer_dx", config_path
        )

    output = raw.get("output", {})
    if "hdf5" in output:
        out["hdf5_path"] = _check_str_path(output["hdf5"], "[output].hdf5", config_path)
    if "plot" in output:
        out["plot_path"] = _check_str_path(output["plot"], "[output].plot", config_path)
    if "model" in output:
        out["model_path"] = _check_str_path(
            output["model"], "[output].model", config_path
        )
    if "smb" in output:
        out["smb_path"] = _check_str_path(output["smb"], "[output].smb", config_path)
    if "plot_lcfs" in output:
        out["plot_lcfs"] = _check_bool(
            output["plot_lcfs"], "[output].plot_lcfs", config_path
        )

    runtime = raw.get("runtime", {})
    if "verbose" in runtime:
        out["verbose"] = _check_bool(
            runtime["verbose"], "[runtime].verbose", config_path
        )

    return out


# --------------------------------------------------------------------------- #
# regions inspect 独立配置模型                                                 #
# --------------------------------------------------------------------------- #

def _load_regions_inspect_toml(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open("rb") as file_object:
            raw = tomllib.load(file_object)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"[配置文件 {config_path}] TOML 语法错误：{exc}"
        ) from exc
    except OSError as exc:
        raise ConfigError(
            f"[配置文件 {config_path}] 无法读取：{exc}"
        ) from exc

    if set(raw) - {"schema_version", "regions", "runtime"}:
        unknown = sorted(set(raw) - {"schema_version", "regions", "runtime"})
        _fail(config_path, "顶层", f"未知 section 或键：{unknown}")
    if raw.get("schema_version") != SCHEMA_VERSION or isinstance(
        raw.get("schema_version"), bool
    ):
        _fail(config_path, "schema_version", "必须是整数 1")

    regions = raw.get("regions", {})
    runtime = raw.get("runtime", {})
    if not isinstance(regions, dict):
        _fail(config_path, "[regions]", "必须是 TOML table")
    if not isinstance(runtime, dict):
        _fail(config_path, "[runtime]", "必须是 TOML table")

    allowed_regions = {"mode", "multi_array_file", "regions_map", "plot"}
    unknown_regions = set(regions) - allowed_regions
    if unknown_regions:
        _fail(
            config_path,
            "[regions]",
            f"未知键：{sorted(unknown_regions)}",
        )
    unknown_runtime = set(runtime) - {"verbose"}
    if unknown_runtime:
        _fail(
            config_path,
            "[runtime]",
            f"未知键：{sorted(unknown_runtime)}",
        )

    values: dict[str, Any] = {}
    if "mode" in regions:
        if regions["mode"] != "inspect":
            _fail(
                config_path,
                "[regions].mode",
                "regions inspect 配置必须为字符串 \"inspect\"",
            )
        values["mode"] = "inspect"
    for key in ("multi_array_file", "regions_map", "plot"):
        if key in regions:
            values[key] = _check_str_path(
                regions[key],
                f"[regions].{key}",
                config_path,
            )
    if "verbose" in runtime:
        values["verbose"] = _check_bool(
            runtime["verbose"],
            "[runtime].verbose",
            config_path,
        )
    return values


def _parse_region_dx_key(
    raw_region_id: Any,
    name: str,
    config_path: Optional[Path],
) -> int:
    if isinstance(raw_region_id, bool):
        _fail(config_path, name, "Region ID 必须是正整数")
    token = str(raw_region_id)
    if not token.isdecimal():
        _fail(config_path, name, f"Region ID 必须是正整数，实际={token!r}")
    region_id = int(token, 10)
    if region_id <= 0:
        _fail(config_path, name, f"Region ID 必须是正整数，实际={token!r}")
    return region_id


def _parse_region_dx_tokens(
    tokens: Any,
    config_path: Optional[Path],
) -> dict[int, float]:
    if tokens is UNSET or tokens is None:
        return {}
    if not isinstance(tokens, (list, tuple)):
        _fail(config_path, "--region-dx", "内部值必须是 token 序列")

    parsed: dict[int, float] = {}
    for token in tokens:
        if not isinstance(token, str) or token.count("=") != 1:
            _fail(
                config_path,
                "--region-dx",
                f"必须使用 ID=DX 格式，实际={token!r}",
            )
        raw_region_id, raw_dx = token.split("=", 1)
        region_id = _parse_region_dx_key(
            raw_region_id,
            "--region-dx",
            config_path,
        )
        if region_id in parsed:
            _fail(
                config_path,
                "--region-dx",
                f"重复提供 Region ID {region_id}",
            )
        try:
            dx_value: Any = float(raw_dx)
        except ValueError as exc:
            raise ConfigError(
                f"--region-dx：Region ID {region_id} 的 DX 必须是有限正数，"
                f"实际={raw_dx!r}"
            ) from exc
        parsed[region_id] = _check_positive_float(
            dx_value,
            f"--region-dx {region_id}",
            config_path,
        )
    return parsed


def _load_regions_generate_toml(
    config_path: Path,
) -> dict[str, Any]:
    try:
        with config_path.open("rb") as file_object:
            raw = tomllib.load(file_object)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"[配置文件 {config_path}] TOML 语法错误：{exc}"
        ) from exc
    except OSError as exc:
        raise ConfigError(
            f"[配置文件 {config_path}] 无法读取：{exc}"
        ) from exc

    allowed_top = {"schema_version", "regions", "runtime"}
    unknown_top = set(raw) - allowed_top
    if unknown_top:
        _fail(
            config_path,
            "顶层",
            f"未知 section 或键：{sorted(unknown_top)}",
        )
    schema_version = raw.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or schema_version != SCHEMA_VERSION
    ):
        _fail(config_path, "schema_version", "必须是整数 1")

    regions = raw.get("regions", {})
    runtime = raw.get("runtime", {})
    if not isinstance(regions, dict):
        _fail(config_path, "[regions]", "必须是 TOML table")
    if not isinstance(runtime, dict):
        _fail(config_path, "[runtime]", "必须是 TOML table")

    allowed_regions = {
        "mode",
        "target",
        "multi_array_file",
        "regions_map",
        "plot",
        "hdf5",
        "model",
        "smb",
        "mesh",
    }
    unknown_regions = set(regions) - allowed_regions
    if unknown_regions:
        _fail(
            config_path,
            "[regions]",
            f"未知键：{sorted(unknown_regions)}",
        )
    unknown_runtime = set(runtime) - {"verbose"}
    if unknown_runtime:
        _fail(
            config_path,
            "[runtime]",
            f"未知键：{sorted(unknown_runtime)}",
        )

    if regions.get("mode") != "generate":
        _fail(
            config_path,
            "[regions].mode",
            'regions generate 配置必须为字符串 "generate"',
        )

    values: dict[str, Any] = {"mode": "generate"}
    if "target" in regions:
        values["target"] = _check_enum(
            regions["target"],
            ("mesh_only", "trimeg", "m3dc1"),
            "[regions].target",
            config_path,
        )
    for key in (
        "multi_array_file",
        "regions_map",
        "plot",
        "hdf5",
        "model",
        "smb",
    ):
        if key in regions:
            values[key] = _check_str_path(
                regions[key],
                f"[regions].{key}",
                config_path,
            )

    mesh = regions.get("mesh", {})
    if not isinstance(mesh, dict):
        _fail(config_path, "[regions.mesh]", "必须是 TOML table")
    unknown_mesh = set(mesh) - {"mesh_dx", "region_dx"}
    if unknown_mesh:
        _fail(
            config_path,
            "[regions.mesh]",
            f"未知键：{sorted(unknown_mesh)}",
        )
    if "mesh_dx" in mesh:
        values["mesh_dx"] = _check_positive_float(
            mesh["mesh_dx"],
            "[regions.mesh].mesh_dx",
            config_path,
        )

    raw_region_dx = mesh.get("region_dx", {})
    if not isinstance(raw_region_dx, dict):
        _fail(
            config_path,
            "[regions.mesh.region_dx]",
            "必须是 TOML table",
        )
    normalized_region_dx: dict[int, float] = {}
    for raw_region_id, raw_dx in raw_region_dx.items():
        region_id = _parse_region_dx_key(
            raw_region_id,
            "[regions.mesh.region_dx]",
            config_path,
        )
        if region_id in normalized_region_dx:
            _fail(
                config_path,
                "[regions.mesh.region_dx]",
                f"规范化后重复 Region ID {region_id}",
            )
        normalized_region_dx[region_id] = _check_positive_float(
            raw_dx,
            f"[regions.mesh.region_dx].{raw_region_id}",
            config_path,
        )
    values["region_dx"] = normalized_region_dx

    if "verbose" in runtime:
        values["verbose"] = _check_bool(
            runtime["verbose"],
            "[runtime].verbose",
            config_path,
        )
    return values


def load_regions_inspect_config(
    overrides: RegionsInspectOverrides,
    *,
    config_arg: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> RegionsInspectConfig:
    """Resolve isolated inspect config using defaults < TOML < explicit CLI."""
    base_cwd = Path(cwd) if cwd is not None else Path.cwd()
    config_path: Optional[Path] = None
    values: dict[str, Any] = {}

    if config_arg is not None:
        config_path = _resolve_path(config_arg, base_cwd)
        if not config_path.is_file():
            raise ConfigError(
                f"--config 指定的 regions 配置文件不存在：{config_path}"
            )
        values = _load_regions_inspect_toml(config_path)

    config_dir = config_path.parent if config_path is not None else base_cwd

    def merged(name: str, default: Any = None) -> Any:
        explicit = getattr(overrides, name)
        if explicit is not UNSET:
            return explicit
        return values.get(name, default)

    def required_path(name: str) -> Path:
        explicit = getattr(overrides, name)
        value = merged(name)
        if value is None:
            option_name = name.replace("_", "-")
            raise ConfigError(
                "regions inspect 缺少必需路径："
                f"--{option_name} 或 [regions].{name}"
            )
        base = base_cwd if explicit is not UNSET else config_dir
        return _resolve_path(
            _check_str_path(value, name, config_path),
            base,
        )

    verbose = _check_bool(
        merged("verbose", False),
        "verbose",
        config_path,
    )
    multi_array_file_path = required_path("multi_array_file")
    regions_map_path = required_path("regions_map")
    plot_path = required_path("plot")

    resolved_paths = (
        ("multi_array_file", multi_array_file_path),
        ("regions_map", regions_map_path),
        ("plot", plot_path),
    )

    for index, (first_name, first_path) in enumerate(resolved_paths):
        for second_name, second_path in resolved_paths[index + 1:]:
            if first_path == second_path:
                raise ConfigError(
                    "regions inspect 路径冲突："
                    f"{first_name} 与 {second_name} 解析为同一路径 "
                    f"{first_path}"
                )

    return RegionsInspectConfig(
        schema_version=SCHEMA_VERSION,
        config_path=config_path,
        mode="inspect",
        multi_array_file_path=multi_array_file_path,
        regions_map_path=regions_map_path,
        plot_path=plot_path,
        verbose=verbose,
    )


def load_regions_generate_config(
    overrides: RegionsGenerateOverrides,
    *,
    config_arg: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> RegionsGenerateConfig:
    """Resolve isolated generate config using defaults < TOML < CLI."""
    base_cwd = Path(cwd) if cwd is not None else Path.cwd()
    config_path: Optional[Path] = None
    values: dict[str, Any] = {}

    if config_arg is not None:
        config_path = _resolve_path(config_arg, base_cwd)
        if not config_path.is_file():
            raise ConfigError(
                f"--config 指定的 regions 配置文件不存在：{config_path}"
            )
        values = _load_regions_generate_toml(config_path)

    config_dir = config_path.parent if config_path is not None else base_cwd

    def merged(name: str, default: Any = None) -> Any:
        explicit = getattr(overrides, name)
        if explicit is not UNSET:
            return explicit
        return values.get(name, default)

    def required_path(name: str) -> Path:
        explicit = getattr(overrides, name)
        value = merged(name)
        if value is None:
            option_name = name.replace("_", "-")
            raise ConfigError(
                "regions generate 缺少必需路径："
                f"--{option_name} 或 [regions].{name}"
            )
        base = base_cwd if explicit is not UNSET else config_dir
        return _resolve_path(
            _check_str_path(value, name, config_path),
            base,
        )

    target = _check_enum(
        merged("target", "mesh_only"),
        ("mesh_only", "trimeg", "m3dc1"),
        "regions target",
        config_path,
    )
    multi_array_file_path = required_path("multi_array_file")
    regions_map_path = required_path("regions_map")
    plot_path = required_path("plot")

    def optional_output_path(name: str) -> Optional[Path]:
        raw_value = merged(name)
        if raw_value is None:
            return None
        base = (
            base_cwd
            if getattr(overrides, name) is not UNSET
            else config_dir
        )
        return _resolve_path(
            _check_str_path(raw_value, name, config_path),
            base,
        )

    hdf5_path = optional_output_path("hdf5")
    model_path = optional_output_path("model")
    smb_path = optional_output_path("smb")

    if target == "mesh_only":
        if any(
            value is not None
            for value in (hdf5_path, model_path, smb_path)
        ):
            raise ConfigError(
                "regions generate target=mesh_only 禁止提供 hdf5、model 或 smb"
            )
    elif target == "trimeg":
        if hdf5_path is None:
            raise ConfigError(
                "regions generate target=trimeg 需要 hdf5，"
                "必须提供 --hdf5 或 [regions].hdf5"
            )
        if model_path is not None or smb_path is not None:
            raise ConfigError(
                "regions generate target=trimeg 禁止提供 model 或 smb"
            )
    else:
        if hdf5_path is not None:
            raise ConfigError(
                "regions generate target=m3dc1 禁止提供 hdf5"
            )
        if model_path is None or smb_path is None:
            raise ConfigError(
                "regions generate target=m3dc1 需要同时提供 model 和 smb"
            )

    resolved_paths = [
        ("multi_array_file", multi_array_file_path),
        ("regions_map", regions_map_path),
        ("plot", plot_path),
    ]
    for name, path in (
        ("hdf5", hdf5_path),
        ("model", model_path),
        ("smb", smb_path),
    ):
        if path is not None:
            resolved_paths.append((name, path))

    for index, (first_name, first_path) in enumerate(resolved_paths):
        for second_name, second_path in resolved_paths[index + 1:]:
            if first_path == second_path:
                raise ConfigError(
                    "regions generate 路径冲突："
                    f"{first_name} 与 {second_name} 解析为同一路径 "
                    f"{first_path}"
                )

    raw_mesh_dx = merged("mesh_dx")
    mesh_dx = (
        None
        if raw_mesh_dx is None
        else _check_positive_float(
            raw_mesh_dx,
            "regions mesh_dx",
            config_path,
        )
    )

    toml_region_dx = dict(values.get("region_dx", {}))
    cli_region_dx = _parse_region_dx_tokens(
        overrides.region_dx,
        config_path,
    )
    region_dx = {**toml_region_dx, **cli_region_dx}
    if mesh_dx is None and not region_dx:
        raise ConfigError(
            "regions generate 需要 --mesh-dx，或通过 --region-dx/"
            "[regions.mesh.region_dx] 提供完整 Region 覆盖"
        )

    verbose = _check_bool(
        merged("verbose", False),
        "verbose",
        config_path,
    )
    return RegionsGenerateConfig(
        schema_version=SCHEMA_VERSION,
        config_path=config_path,
        mode="generate",
        target=target,
        multi_array_file_path=multi_array_file_path,
        regions_map_path=regions_map_path,
        plot_path=plot_path,
        hdf5_path=hdf5_path,
        model_path=model_path,
        smb_path=smb_path,
        mesh_dx=mesh_dx,
        region_dx=MappingProxyType(dict(sorted(region_dx.items()))),
        verbose=verbose,
    )


# --------------------------------------------------------------------------- #
# 配置发现（第 6A.6 节）                                                        #
# --------------------------------------------------------------------------- #

def discover_config(
    *,
    config_arg: Optional[str],
    no_config: bool,
    cwd: Optional[Path] = None,
) -> Optional[Path]:
    """按第 6A.6 节发现配置文件，返回绝对路径或 None。

    - config_arg 与 no_config 互斥（由调用方保证；此处再次防御）；
    - config_arg 提供：只加载该路径，不存在立即失败；
    - no_config 提供：不自动发现；
    - 都未提供：只检查当前工作目录下 linkmesh.in；不递归父目录、不搜主目录。

    异常：
        ConfigError: --config 与 --no-config 同时提供；或 --config 指定文件不存在。
    """
    if config_arg is not None and no_config:
        raise ConfigError("--config 与 --no-config 互斥，不能同时提供")

    base = Path(cwd) if cwd is not None else Path.cwd()

    if config_arg is not None:
        p = Path(config_arg)
        if not p.is_absolute():
            p = base / p
        p = p.resolve()
        if not p.is_file():
            raise ConfigError(f"--config 指定的配置文件不存在：{p}")
        return p

    if no_config:
        return None

    candidate = (base / "linkmesh.in").resolve()
    if candidate.is_file():
        return candidate
    return None


# --------------------------------------------------------------------------- #
# 路径解析辅助                                                                  #
# --------------------------------------------------------------------------- #

def _resolve_path(value: str, base_dir: Path) -> Path:
    """把 value（可能相对）相对 base_dir 解析为规范化绝对路径。

    不展开 ~、不展开环境变量、不要求存在、不创建父目录。
    """
    p = Path(value)
    if not p.is_absolute():
        p = base_dir / p
    # resolve(strict=False)：规范化但不要求存在。
    return p.resolve()


# --------------------------------------------------------------------------- #
# 三层合并 + required fields + 兼容矩阵                                         #
# --------------------------------------------------------------------------- #

def load_effective_config(
    overrides: CliOverrides,
    *,
    config_arg: Optional[str] = None,
    no_config: bool = False,
    cwd: Optional[Path] = None,
) -> EffectiveConfig:
    """合并「内建默认值 < linkmesh.in < 用户显式 CLI」，返回冻结的 EffectiveConfig。

    路径解析基准：TOML 相对路径相对配置目录；CLI 相对路径相对进程当前工作目录。
    随后校验 required fields 与兼容矩阵（第 6A.9/6A.10 节）；当前阶段未实现的
    组合在此明确失败，不进入业务执行。

    参数：
        overrides: CLI 收集的用户显式输入（UNSET 表示未提供）。
        config_arg: --config 值或 None。
        no_config: --no-config 是否提供。
        cwd: 进程当前工作目录（测试可注入）；None 时用 Path.cwd()。

    返回：
        EffectiveConfig（frozen）。

    异常：
        ConfigError: 发现/读取/校验/合并/兼容矩阵任一环节失败。
        NotImplementedError: 当前阶段未实现的组合（single_region/flux_surface）。
    """
    base_cwd = Path(cwd) if cwd is not None else Path.cwd()

    # Step 1：发现配置文件。
    config_path = discover_config(
        config_arg=config_arg, no_config=no_config, cwd=base_cwd
    )

    # Step 2：加载 TOML（若有）。toml_values 使用 EffectiveConfig 字段名（长名）。
    toml_values: dict = {}
    if config_path is not None:
        toml_values = _load_toml(config_path)
        config_dir = config_path.parent
    else:
        config_dir = None

    def _explicit(cli_key: str) -> Any:
        """读取 CliOverrides 上的显式值；UNSET 归一为 None（表示未提供）。"""
        val = getattr(overrides, cli_key)
        return val if val is not UNSET else None

    # ------------------------------------------------------------------ #
    # 标量字段合并：默认 < TOML < 显式 CLI                                  #
    # 标量字段的 CLI 键名与 TOML/EffectiveConfig 键名相同，可共用一个名称。 #
    # ------------------------------------------------------------------ #
    def _merge_scalar(field: str, default: Any) -> Any:
        cli_val = _explicit(field)
        if cli_val is not None:
            return cli_val
        if field in toml_values:
            return toml_values[field]
        return default

    target = _merge_scalar("target", DEFAULT_TARGET)
    profile = _merge_scalar("profile", DEFAULT_PROFILE)
    boundary_source = _merge_scalar("boundary_source", DEFAULT_BOUNDARY_SOURCE)
    mesh_dx = _merge_scalar("mesh_dx", DEFAULT_MESH_DX)
    plasma_dx = _merge_scalar("plasma_dx", DEFAULT_PLASMA_DX)
    vacuum_dx = _merge_scalar("vacuum_dx", DEFAULT_VACUUM_DX)
    outer_dx = _merge_scalar("outer_dx", DEFAULT_OUTER_DX)
    verbose = _merge_scalar("verbose", DEFAULT_VERBOSE)
    plot_lcfs = _merge_scalar("plot_lcfs", DEFAULT_PLOT_LCFS)

    # 枚举/类型再校验（覆盖 CLI 直接注入的情况；TOML 侧已在 _load_toml 校验）。
    target = _check_enum(target, TARGETS, "target", config_path)
    profile = _check_enum(profile, PROFILES, "profile", config_path)
    boundary_source = _check_enum(
        boundary_source, BOUNDARY_SOURCES, "boundary_source", config_path
    )
    mesh_dx = _check_positive_float(mesh_dx, "mesh_dx", config_path)
    plasma_dx = _check_positive_float(plasma_dx, "plasma_dx", config_path)
    vacuum_dx = _check_positive_float(vacuum_dx, "vacuum_dx", config_path)
    outer_dx = _check_positive_float(outer_dx, "outer_dx", config_path)
    verbose = _check_bool(verbose, "verbose", config_path)
    plot_lcfs = _check_bool(plot_lcfs, "plot_lcfs", config_path)

    # ------------------------------------------------------------------ #
    # 路径字段合并 + 基准解析                                               #
    #   CLI 显式路径优先（相对 cwd）；否则 TOML 路径（相对配置目录）；        #
    #   否则内建默认（仅 hdf5 有默认名，且仅按需求处理）。                    #
    #                                                                      #
    # 关键：CLI 载体键名（cli_key，如 "gfile"）与 TOML/EffectiveConfig 键名  #
    # （toml_key，如 "gfile_path"）不同，必须分别查询，不能共用同一名称，    #
    # 否则 TOML 路径值会因 `cli_key in toml_values` 恒为 False 而被丢弃。    #
    # ------------------------------------------------------------------ #
    def _merge_path(cli_key: str, toml_key: str,
                    default_name: Optional[str]) -> Optional[Path]:
        cli_val = _explicit(cli_key)
        if cli_val is not None:
            return _resolve_path(str(cli_val), base_cwd)
        if toml_key in toml_values and config_dir is not None:
            return _resolve_path(str(toml_values[toml_key]), config_dir)
        if default_name is not None:
            # 内建默认路径相对当前工作目录。
            return _resolve_path(default_name, base_cwd)
        return None

    # gfile/array_file/plot/model/smb 无内建默认；hdf5 默认名仅在 target=trimeg
    # 时作为默认输出，其它 target 不制造默认可执行路径。
    gfile_path = _merge_path("gfile", "gfile_path", None)
    array_file_path = _merge_path("array_file", "array_file_path", None)
    plot_path = _merge_path("plot", "plot_path", None)
    model_path = _merge_path("model", "model_path", None)
    smb_path = _merge_path("smb", "smb_path", None)

    hdf5_default_name = DEFAULT_HDF5_NAME if target == "trimeg" else None
    hdf5_path = _merge_path("hdf5", "hdf5_path", hdf5_default_name)

    explicit_mesh_dx = (
        _explicit("mesh_dx") is not None or "mesh_dx" in toml_values
    )
    explicit_region_dx = tuple(
        name
        for name in ("plasma_dx", "vacuum_dx", "outer_dx")
        if _explicit(name) is not None or name in toml_values
    )
    _validate_mesh_resolution_inputs(
        profile,
        explicit_mesh_dx=explicit_mesh_dx,
        explicit_region_dx=explicit_region_dx,
    )

    cfg = EffectiveConfig(
        schema_version=SCHEMA_VERSION,
        config_path=config_path,
        target=target,
        profile=profile,
        boundary_source=boundary_source,
        gfile_path=gfile_path,
        array_file_path=array_file_path,
        mesh_dx=mesh_dx,
        plasma_dx=plasma_dx,
        vacuum_dx=vacuum_dx,
        outer_dx=outer_dx,
        hdf5_path=hdf5_path,
        plot_path=plot_path,
        model_path=model_path,
        smb_path=smb_path,
        verbose=verbose,
        plot_lcfs=plot_lcfs,
    )

    # required-field 校验发生在路径合并完成之后。
    _validate_compatibility(cfg)
    _validate_required_fields(cfg)
    _validate_current_stage(cfg)

    return cfg


# --------------------------------------------------------------------------- #
# 网格尺度适用性                                                                #
# --------------------------------------------------------------------------- #

def _validate_mesh_resolution_inputs(
    profile: str,
    *,
    explicit_mesh_dx: bool,
    explicit_region_dx: tuple[str, ...],
) -> None:
    """Reject explicitly supplied mesh scales that do not apply to profile."""
    if profile == "single_region" and explicit_region_dx:
        conflicts = ", ".join(explicit_region_dx)
        raise ConfigError(
            "profile=single_region 不接受显式多区域网格尺度 "
            f"{conflicts}；请使用 mesh_dx（--mesh-dx 或 [mesh].mesh_dx）"
        )
    if profile == "nested_three_region" and explicit_mesh_dx:
        raise ConfigError(
            "profile=nested_three_region 不接受显式 mesh_dx；请使用 "
            "plasma_dx、vacuum_dx、outer_dx"
        )


# --------------------------------------------------------------------------- #
# 兼容矩阵（第 6A.9 节）                                                        #
# --------------------------------------------------------------------------- #

def _combo(cfg: EffectiveConfig) -> str:
    return (
        f"target={cfg.target}, profile={cfg.profile}, "
        f"boundary_source={cfg.boundary_source}"
    )


def _validate_compatibility(cfg: EffectiveConfig) -> None:
    """校验 target/profile/boundary_source 兼容矩阵（第 6A.9 节明确禁止项）。"""
    t, p, b = cfg.target, cfg.profile, cfg.boundary_source

    # m3dc1 + nested_three_region 明确禁止。
    if t == "m3dc1" and p == "nested_three_region":
        raise ConfigError(
            f"禁止的组合（{_combo(cfg)}）：m3dc1 + nested_three_region "
            "多物理区域与界面语义未确认"
        )

    # nested_three_region 只允许 artificial_outer；配 lcfs/first_wall/array_file 禁止。
    if p == "nested_three_region" and b in ("lcfs", "first_wall", "array_file"):
        raise ConfigError(
            f"禁止的组合（{_combo(cfg)}）：nested_three_region 的 profile 与 "
            f"boundary_source={b} 不匹配"
        )

    # single_region 不使用人工外框。
    if p == "single_region" and b == "artificial_outer":
        raise ConfigError(
            f"禁止的组合（{_combo(cfg)}）：single_region 不使用 artificial_outer"
        )

    # LCFS reference 只适用于 array_file 实际计算域边界。
    if cfg.plot_lcfs and b != "array_file":
        raise ConfigError(
            f"禁止的组合（{_combo(cfg)}）：plot_lcfs 只适用于 "
            "boundary_source=array_file"
        )


# --------------------------------------------------------------------------- #
# required fields（第 6A.10 节）                                               #
# --------------------------------------------------------------------------- #

def _validate_required_fields(cfg: EffectiveConfig) -> None:
    """校验 required fields（第 6A.10 节）。

    仅校验字段存在/冲突关系；具体文件内容有效性（如第一壁是否有效）留待
    对应输入层实现阶段。array_file 内容读取本轮不实现。
    """
    b = cfg.boundary_source

    if b in ("lcfs", "first_wall", "artificial_outer"):
        if cfg.gfile_path is None:
            raise ConfigError(
                f"boundary_source={b} 需要 gfile_path（--gfile 或 [input].gfile）"
            )
        if cfg.array_file_path is not None:
            raise ConfigError(
                f"boundary_source={b} 禁止同时提供 array_file_path"
            )
    elif b == "array_file":
        if cfg.array_file_path is None:
            raise ConfigError(
                "boundary_source=array_file 需要 array_file_path"
                "（--array-file 或 [input].array_file）"
            )
        if cfg.plot_lcfs:
            if cfg.gfile_path is None:
                raise ConfigError(
                    "boundary_source=array_file 且 plot_lcfs=True 时需要 "
                    "gfile_path（--gfile 或 [input].gfile）"
                )
            if cfg.plot_path is None:
                raise ConfigError(
                    "boundary_source=array_file 且 plot_lcfs=True 时需要 "
                    "plot_path（--plot 或 [output].plot）"
                )
        elif cfg.gfile_path is not None:
            raise ConfigError(
                "boundary_source=array_file 仅在 plot_lcfs=True 时允许提供 "
                "gfile_path"
            )
    # flux_surface 的 required 判定由 _validate_current_stage 统一报未实现。

    # target=trimeg 需要 hdf5_path（默认已提供 mesh.h5）。
    if cfg.target == "trimeg" and cfg.hdf5_path is None:
        raise ConfigError("target=trimeg 需要 hdf5_path")

    # M5 第一条 M3DC1 CLI 闭环需要配套 TXT model 与 SMB 基础输出路径。
    if cfg.target == "m3dc1":
        if cfg.model_path is None:
            raise ConfigError(
                "target=m3dc1 需要 model_path（--model 或 [output].model）"
            )
        if cfg.smb_path is None:
            raise ConfigError(
                "target=m3dc1 需要 smb_path（--smb 或 [output].smb）"
            )


# --------------------------------------------------------------------------- #
# 当前阶段实现边界（输入层 I + 输入层 II）                                       #
# --------------------------------------------------------------------------- #

# 当前已实现的 single_region 来源：lcfs 与 array_file。
# first_wall/flux_surface 仍明确未实现。
_IMPLEMENTED_M3DC1_PROFILE = "single_region"
_IMPLEMENTED_M3DC1_SOURCES = ("lcfs", "array_file")
_IMPLEMENTED_SINGLE_REGION_SOURCES = ("lcfs", "array_file")


def _validate_current_stage(cfg: EffectiveConfig) -> None:
    """当前阶段（输入层 I + 输入层 II）业务能力边界校验。

    - flux_surface：首批明确未实现（第 6A.8 节，禁止缩放 LCFS 伪造磁面）；
    - target=m3dc1：允许 single_region + lcfs/array_file；
    - single_region：已实现 lcfs 与 array_file；
      first_wall 仍明确报未实现，不回退 artificial_outer。

    当前进入业务执行的组合：
        - target ∈ {trimeg, mesh_only} + nested_three_region + artificial_outer
          （已实现回归路径）；
        - target ∈ {trimeg, mesh_only} + single_region + lcfs/array_file；
        - target=m3dc1 + single_region + lcfs/array_file。
    """
    if cfg.boundary_source == "flux_surface":
        raise NotImplementedError(
            f"boundary_source=flux_surface 尚未实现（{_combo(cfg)}）："
            "真实磁通面提取未实现，禁止径向缩放 LCFS 伪造磁面"
        )

    if cfg.target == "m3dc1":
        if not (
            cfg.profile == _IMPLEMENTED_M3DC1_PROFILE
            and cfg.boundary_source in _IMPLEMENTED_M3DC1_SOURCES
        ):
            raise NotImplementedError(
                "target=m3dc1 当前仅支持 single_region + lcfs/array_file"
                f"（{_combo(cfg)}）"
            )
        return

    if cfg.profile == "single_region":
        if cfg.boundary_source not in _IMPLEMENTED_SINGLE_REGION_SOURCES:
            raise NotImplementedError(
                f"profile=single_region + boundary_source={cfg.boundary_source} "
                f"尚未实现（{_combo(cfg)}）："
                "single_region + first_wall 当前阶段未实现，"
                "不回退 artificial_outer"
            )
