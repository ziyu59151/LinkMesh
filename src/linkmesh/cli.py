"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse），标记用户显式输入
    - 调用 config.load_effective_config() 完成「内建默认值 < linkmesh.in < 显式 CLI」合并
    - 按 boundary_source 选择唯一实际边界，调用 reader → single-region mesher
      → writer → plotter
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑（Domain/区域/边界/种子/数组转换）
    - 不得直接解析 TOML（交给 config.py）
    - 不得自行维护第二套配置默认值（默认值集中在 config.py）
    - 不得把 boundary-source 判断放入 Reader 或 Writer
    - 未实现来源不得回退

数据流（v2.3 输入层 I/II 正式路径）：
    CLI 参数 → CliOverrides（仅显式输入）→ load_effective_config() → EffectiveConfig
         → Reader 取得唯一实际边界
         → oft_adapter.generate_mesh(boundary, mesh_dx=...) → Mesh2D
         → target=trimeg：write_hdf5()（且未 --no-hdf5）
         → target=m3dc1：build_single_face_model_spec() →
           write_m3dc1_model() + write_smb()（SMB 除非 --no-smb）
         → plot_mesh()（若配置 plot_path）

根命令只提供 --mesh-dx，表示唯一单 Region 的目标网格尺度（单位 m）。
多区域尺度和 transition 参数只存在于 regions generate 子命令。
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from linkmesh import config as config_mod
from linkmesh.config import CliOverrides, ConfigError, UNSET


def build_parser() -> argparse.ArgumentParser:
    """构造 LinkMesh CLI 参数解析器。

    返回：
        argparse.ArgumentParser 对象

    合并语义要点：
        - 需要区分「用户显式提供」与「未提供」的字段，其 argparse default 设为
          config.UNSET 哨兵，使 config 合并时 argparse 默认值不覆盖 TOML；
        - --no-hdf5/--no-smb/--verbose 等既有开关保持原默认（store_true），
          用于旧 CLI 行为兼容；verbose 的最终值由 config 合并（CLI 显式 True 覆盖 TOML）。
    """
    parser = argparse.ArgumentParser(
        prog="linkmesh",
        usage=(
            "%(prog)s [standard mesh options]\n"
            "       %(prog)s regions {inspect,generate} ..."
        ),
        description=(
            "LinkMesh 用于生成二维 R-Z 非结构三角网格，并输出 TRIMEG 或 "
            "M3D-C1 所需文件。\n\n"
            "工作流：\n"
            "  单区域网格\n"
            "    适用于 GFile/EQDSK 或单轮廓边界，使用 linkmesh [options]。\n"
            "  多区域网格\n"
            "    适用于包含多个 counted R-Z blocks 的输入，先执行\n"
            "    linkmesh regions inspect，再执行 linkmesh regions generate。\n"
            "    使用 linkmesh regions -h 查看多区域工作流。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    configuration_group = parser.add_argument_group("Configuration")
    task_group = parser.add_argument_group("Task")
    input_group = parser.add_argument_group("Input")
    mesh_group = parser.add_argument_group("Mesh Resolution")
    output_group = parser.add_argument_group("Output")
    runtime_group = parser.add_argument_group("Runtime")

    # ------------------------------------------------------------------ #
    # 配置发现                                                            #
    # ------------------------------------------------------------------ #
    config_group = configuration_group.add_mutually_exclusive_group()
    config_group.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="仅加载指定配置文件；文件不存在时失败；与 --no-config 互斥",
    )
    config_group.add_argument(
        "--no-config",
        action="store_true",
        help="禁用配置文件自动发现；与 --config 互斥",
    )

    # ------------------------------------------------------------------ #
    # 根命令任务、边界来源与输入                                            #
    # 默认值交给 config.py；此处 default=UNSET 表示未显式提供。            #
    # ------------------------------------------------------------------ #
    task_group.add_argument(
        "--target",
        default=UNSET,
        choices=list(config_mod.TARGETS),
        help="选择输出目标；覆盖配置文件中的值",
    )
    task_group.add_argument(
        "--boundary-source",
        dest="boundary_source",
        default=UNSET,
        choices=list(config_mod.BOUNDARY_SOURCES),
        help="选择计算域边界来源；覆盖配置文件中的值",
    )
    # ------------------------------------------------------------------ #
    # 既有：GFile 输入                                                     #
    # ------------------------------------------------------------------ #
    input_group.add_argument(
        "--gfile",
        default=UNSET,
        metavar="PATH",
        help=(
            "GFile/EQDSK 路径；用于网格输入，或在 array_file + "
            "--plot-lcfs 时仅提供 LCFS 参考线"
        ),
    )
    input_group.add_argument(
        "--array-file",
        dest="array_file",
        default=UNSET,
        metavar="PATH",
        help="counted R-Z 单轮廓边界文件（boundary_source=array_file）",
    )

    # ------------------------------------------------------------------ #
    # 既有：输出路径参数（default=UNSET 交给 config 合并）                  #
    # ------------------------------------------------------------------ #
    output_group.add_argument(
        "--hdf5",
        "--h5",
        dest="hdf5",
        default=UNSET,
        metavar="PATH",
        help="TRIMEG HDF5 输出路径；仅 target=trimeg 时使用（默认：mesh.h5）",
    )
    input_group.add_argument(
        "--plot-lcfs",
        action="store_true",
        help=(
            "仅用于 boundary_source=array_file：在 PNG 中叠加 LCFS 参考线，"
            "不改变实际网格边界"
        ),
    )
    output_group.add_argument(
        "--model",
        default=UNSET,
        metavar="PATH",
        help="M3D-C1 model TXT 输出路径；仅 target=m3dc1 时使用",
    )
    output_group.add_argument(
        "--smb",
        default=UNSET,
        metavar="PATH",
        help="PUMI SMB 输出路径；仅 target=m3dc1 时使用",
    )
    output_group.add_argument(
        "--plot",
        default=UNSET,
        metavar="PATH",
        help="可选的网格自检 PNG 输出路径",
    )

    # ------------------------------------------------------------------ #
    # 网格尺度（default=UNSET，合并、校验和 profile 适用性由 config 负责）  #
    # ------------------------------------------------------------------ #
    mesh_group.add_argument(
        "--mesh-dx",
        dest="mesh_dx",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help="唯一单 Region 的目标网格尺度，单位 m（默认：0.08）",
    )

    # ------------------------------------------------------------------ #
    # 既有：跳过开关（保持旧行为）                                          #
    # ------------------------------------------------------------------ #
    output_group.add_argument(
        "--no-hdf5",
        action="store_true",
        help="跳过 HDF5 文件生成",
    )
    output_group.add_argument(
        "--no-smb",
        action="store_true",
        help="跳过 .smb 文件生成",
    )

    # ------------------------------------------------------------------ #
    # 既有：详细日志（store_true；显式 True 时覆盖 TOML verbose）           #
    # ------------------------------------------------------------------ #
    runtime_group.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "打印配置、网格规模和写入状态；regions generate 还会打印 "
            "final Mesh2D 质量摘要"
        ),
    )

    command_parsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        title="Multi-region workflow",
        description="使用 regions inspect/generate 处理多轮廓 Region 网格。",
    )
    regions_parser = command_parsers.add_parser(
        "regions",
        usage="linkmesh regions {inspect,generate} ...",
        help="检查多轮廓 Region 或生成多区域网格",
        description=(
            "多区域工作流处理包含多个 counted R-Z 闭合轮廓的输入：\n\n"
            "  1. inspect\n"
            "     推导包含关系，通过 OFT setup-only 取得最终 Region ID，并生成\n"
            "     regions map；不生成完整 Triangle 网格。\n"
            "  2. generate\n"
            "     读取同一输入和经用户确认的 regions map，应用分区域尺度并生成\n"
            "     最终网格。提供相应 --plot 路径时可生成 PNG。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    regions_actions = regions_parser.add_subparsers(
        dest="regions_action",
        metavar="ACTION",
        required=True,
    )
    inspect_parser = regions_actions.add_parser(
        "inspect",
        usage="linkmesh regions inspect [options]",
        help="推导 Region 并生成供 generate 使用的 regions map",
        description=(
            "读取重复 counted R-Z blocks，推导 Region 包含关系，并通过 OFT "
            "setup-only 取得最终 Region ID。输出 regions map，可选输出 "
            "inspection PNG；不生成完整 Triangle 网格。"
        ),
    )
    inspect_configuration_group = inspect_parser.add_argument_group(
        "Configuration"
    )
    inspect_input_group = inspect_parser.add_argument_group("Input")
    inspect_output_group = inspect_parser.add_argument_group("Output")
    inspect_runtime_group = inspect_parser.add_argument_group("Runtime")

    inspect_configuration_group.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="仅加载指定的 regions inspect 配置文件",
    )
    inspect_input_group.add_argument(
        "--multi-array-file",
        dest="multi_array_file",
        default=UNSET,
        metavar="PATH",
        help="包含多个重复 counted R-Z 闭合轮廓的输入文件",
    )
    inspect_output_group.add_argument(
        "--regions-map",
        dest="regions_map",
        default=UNSET,
        metavar="PATH",
        help="供 generate 使用的 TOML regions map 输出路径",
    )
    inspect_output_group.add_argument(
        "--plot",
        default=UNSET,
        metavar="PATH",
        help="可选的 inspection PNG 输出路径",
    )
    inspect_runtime_group.add_argument(
        "--verbose",
        action="store_true",
        help="打印 inspect 过程摘要",
    )

    generate_parser = regions_actions.add_parser(
        "generate",
        usage="linkmesh regions generate [options]",
        help="应用分区域尺度并生成最终多区域网格",
        description=(
            "读取 multi-array 输入和经用户确认的 regions map，应用全局默认尺度与 "
            "Region 覆盖，可选执行 transition refinement，生成一个最终多区域 "
            "Triangle 网格，并按 target 写出目标格式。"
        ),
        epilog=(
            "尺度规则：--mesh-dx 提供默认值，--region-dx ID=DX 可重复并覆盖对应的"
            "最终 Region ID；未提供 --mesh-dx 时，--region-dx 必须覆盖所有最终 "
            "Region。单位均为 m。transition width 对所有不同尺度的内部 Region "
            "界面统一生效，变化层自动位于粗侧。"
        ),
    )
    generate_configuration_group = generate_parser.add_argument_group(
        "Configuration"
    )
    generate_task_group = generate_parser.add_argument_group("Task")
    generate_input_group = generate_parser.add_argument_group("Input")
    generate_mesh_group = generate_parser.add_argument_group(
        "Mesh Resolution"
    )
    generate_output_group = generate_parser.add_argument_group("Output")
    generate_runtime_group = generate_parser.add_argument_group("Runtime")

    generate_configuration_group.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="仅加载指定的 regions generate 配置文件",
    )
    generate_task_group.add_argument(
        "--target",
        default=UNSET,
        choices=("mesh_only", "trimeg", "m3dc1"),
        help=(
            "选择输出目标（默认：mesh_only）：mesh_only 不写求解器格式，"
            "trimeg 写 HDF5，m3dc1 写 model TXT 和 SMB"
        ),
    )
    generate_input_group.add_argument(
        "--multi-array-file",
        dest="multi_array_file",
        default=UNSET,
        metavar="PATH",
        help="与 inspect 使用相同的重复 counted R-Z blocks 输入文件",
    )
    generate_input_group.add_argument(
        "--regions-map",
        dest="regions_map",
        default=UNSET,
        metavar="PATH",
        help="由 inspect 生成并经用户确认的 TOML regions map",
    )
    generate_mesh_group.add_argument(
        "--mesh-dx",
        dest="mesh_dx",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help="全部最终 Region 的默认目标网格尺度，单位 m",
    )
    generate_mesh_group.add_argument(
        "--region-dx",
        dest="region_dx",
        action="append",
        default=None,
        metavar="ID=DX",
        help="按最终 Region ID 覆盖尺度；格式 ID=DX，可重复提供，单位 m",
    )
    generate_mesh_group.add_argument(
        "--transition-width",
        dest="transition_width",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help=(
            "不同网格尺度的内部 Region 界面在粗侧使用的统一变化层厚度，"
            "单位 m；0 表示关闭"
        ),
    )
    generate_output_group.add_argument(
        "--hdf5",
        default=UNSET,
        metavar="PATH",
        help="TRIMEG HDF5 输出路径；仅 target=trimeg 时需要",
    )
    generate_output_group.add_argument(
        "--model",
        default=UNSET,
        metavar="PATH",
        help="M3D-C1 model TXT 输出路径；仅 target=m3dc1 时需要",
    )
    generate_output_group.add_argument(
        "--smb",
        default=UNSET,
        metavar="PATH",
        help="PUMI SMB 基础输出路径；仅 target=m3dc1 时需要",
    )
    generate_output_group.add_argument(
        "--plot",
        default=UNSET,
        metavar="PATH",
        help="可选的最终网格 PNG 输出路径",
    )
    generate_runtime_group.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "打印 Region 与网格规模、final Mesh2D 数值质量；启用 transition "
            "且存在不同尺度界面时还打印 transition 质量摘要"
        ),
    )

    return parser


def main() -> None:
    """LinkMesh CLI 主入口函数。

    执行顺序（v2.3 输入层 I/II）：
        0. 解析 CLI，拦截历史参数
        1. 收集用户显式输入 → CliOverrides
        2. load_effective_config()（发现/读取/校验/合并 linkmesh.in 与 CLI）
        3. Reader 取得唯一实际计算域边界
        4. oft_adapter.generate_mesh(boundary, mesh_dx=...) → Mesh2D
        5. target=trimeg 时写出 HDF5
        6. target=m3dc1 时构造一次 M3DC1ModelSpec，并写出 TXT 与可选 SMB
        7. plot_mesh()（若配置 plot_path）
    """
    parser = build_parser()
    args = parser.parse_args()

    from linkmesh.regions import RegionsError

    try:
        _run(args)
    except NotImplementedError as e:
        print(f"[LinkMesh] 该功能尚未实现（当前阶段限制）：\n  {e}", file=sys.stderr)
        sys.exit(1)
    except ConfigError as e:
        print(f"[LinkMesh] 配置错误：{e}", file=sys.stderr)
        sys.exit(1)
    except RegionsError as e:
        print(f"[LinkMesh] Region 工作流错误：\n  {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"[LinkMesh] 文件未找到：{e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"[LinkMesh] 依赖缺失：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[LinkMesh] 运行时错误：{e}", file=sys.stderr)
        raise



def _build_overrides(args: argparse.Namespace) -> CliOverrides:
    """把 argparse Namespace 中用户显式提供的字段收集为 CliOverrides。

    未显式提供的字段保持 UNSET（default=UNSET）。
    --verbose 是 store_true：仅当为 True 时视为显式提供（旧行为兼容，
    显式 --verbose 覆盖 TOML；未加时不覆盖 TOML）。
    """
    overrides = CliOverrides(
        target=args.target,
        boundary_source=args.boundary_source,
        gfile=args.gfile,
        array_file=args.array_file,
        mesh_dx=args.mesh_dx,
        hdf5=args.hdf5,
        plot=args.plot,
        model=args.model,
        smb=args.smb,
    )
    # store_true 配置项仅在显式为 True 时覆盖，否则保持 UNSET，不覆盖 TOML。
    if args.verbose:
        overrides.verbose = True
    if args.plot_lcfs:
        overrides.plot_lcfs = True
    return overrides


def _run(args: argparse.Namespace) -> None:
    """LinkMesh 主执行逻辑（由 main() 调用，异常由 main() 统一捕获）。"""
    if getattr(args, "command", None) == "regions":
        if args.regions_action == "inspect":
            _run_regions_inspect(args)
        elif args.regions_action == "generate":
            _run_regions_generate(args)
        else:
            raise NotImplementedError(
                f"regions action 尚未实现：{args.regions_action}"
            )
        return

    # ------------------------------------------------------------------ #
    # Step 1：收集显式 CLI 输入并合并配置                                   #
    # 默认值、TOML 读取、严格校验、合并、兼容矩阵、required、当前阶段边界    #
    # 全部集中在 config.py；CLI 不解析 TOML、不维护第二套默认值。           #
    # ------------------------------------------------------------------ #
    overrides = _build_overrides(args)

    config_arg = None if args.config is UNSET else args.config
    cfg = config_mod.load_effective_config(
        overrides,
        config_arg=config_arg,
        no_config=args.no_config,
    )

    verbose = cfg.verbose

    if verbose:
        if cfg.config_path is not None:
            print(f"[LinkMesh] 已加载配置文件：{cfg.config_path}")
        else:
            print("[LinkMesh] 未加载配置文件（使用内建默认值与 CLI 显式参数）")
        print(
            f"[LinkMesh] 有效配置：target={cfg.target}, "
            f"boundary_source={cfg.boundary_source}"
        )

    # ------------------------------------------------------------------ #
    # Step 2：按 boundary_source 读取唯一网格输入。                           #
    # lcfs/artificial_outer 读取一次 GFile 作为网格输入；array_file 读取一次  #
    # counted R-Z boundary text。plot_lcfs 启用时额外读取一次 GFile，但该     #
    # GFileData 只供 Plotter 使用，不进入 Mesher、Mesh2D 或 Writer。          #
    # ------------------------------------------------------------------ #
    gfile_data = None
    if cfg.boundary_source == "array_file":
        from linkmesh.readers.boundary_reader import read_boundary_file

        boundary_path = str(cfg.array_file_path)
        if verbose:
            print(f"[LinkMesh] 读取外部计算边界：{boundary_path}")
        mesh_input = read_boundary_file(boundary_path)
        if verbose:
            print(f"  计算边界点数: {mesh_input.shape[0]}")

        if cfg.plot_lcfs:
            from linkmesh.readers.gfile_reader import read_gfile

            reference_path = str(cfg.gfile_path)
            if verbose:
                print(
                    "[LinkMesh] 读取 GFile LCFS reference（仅用于 PNG）："
                    f"{reference_path}"
                )
            gfile_data = read_gfile(reference_path)
            if verbose:
                print(f"  LCFS reference 点数: {len(gfile_data.lcfs_r)}")
    else:
        from linkmesh.readers.gfile_reader import read_gfile

        gfile_path = str(cfg.gfile_path)
        if verbose:
            print(f"[LinkMesh] 读取 GFile：{gfile_path}")

        gfile_data = read_gfile(gfile_path)
        mesh_input = np.column_stack(
            (gfile_data.lcfs_r, gfile_data.lcfs_z)
        )

        if verbose:
            print(f"  LCFS 点数: {len(gfile_data.lcfs_r)}")
            print(
                f"  磁轴: (R={gfile_data.rmaxis:.4f} m, "
                f"Z={gfile_data.zmaxis:.4f} m)"
            )
            if gfile_data.wall_r is not None:
                print(f"  第一壁点数: {len(gfile_data.wall_r)}")
            else:
                print("  第一壁: 无（GFile 不含 limiter 数据）")

    # ------------------------------------------------------------------ #
    # Step 3：使用唯一实际边界生成单区域网格                                #
    # ------------------------------------------------------------------ #
    from linkmesh.mesher.oft_adapter import generate_mesh

    if verbose:
        print(
            "[LinkMesh] 调用 OFT gs_Domain 生成 single-region "
            f"{cfg.boundary_source} 二维三角网格..."
        )
        print(f"  网格尺度: mesh_dx={cfg.mesh_dx} m")

    mesh = generate_mesh(mesh_input, mesh_dx=cfg.mesh_dx)

    if verbose:
        print(f"  节点数: {mesh.n_nodes}")
        print(f"  三角形数: {mesh.n_triangles}")
    else:
        print(f"节点数: {mesh.n_nodes}，三角形数: {mesh.n_triangles}")

    # ------------------------------------------------------------------ #
    # Step 4：写出 HDF5（M3；target=trimeg 且未 --no-hdf5）                 #
    # mesh_only 不写 HDF5（第 6A.10 节：mesh_only 不强制 HDF5）。            #
    # ------------------------------------------------------------------ #
    if cfg.target == "trimeg" and not args.no_hdf5:
        from linkmesh.writers.hdf5_writer import write_hdf5
        hdf5_str = str(cfg.hdf5_path)
        if verbose:
            print(f"[LinkMesh] 写出 TRIMEG HDF5：{hdf5_str}")
        write_hdf5(mesh, hdf5_str, verbose=verbose)

    # ------------------------------------------------------------------ #
    # Step 5：按 target 分派 M3DC1 输出                                     #
    # ------------------------------------------------------------------ #
    if cfg.target == "m3dc1":
        from linkmesh.m3dc1_model import build_single_face_model_spec
        from linkmesh.writers.m3dc1_model_writer import write_m3dc1_model

        spec = build_single_face_model_spec(mesh)
        model_str = str(cfg.model_path)
        if verbose:
            print(f"[LinkMesh] 写出 M3D-C1 model TXT：{model_str}")
        write_m3dc1_model(spec, model_str)

        if not args.no_smb:
            from linkmesh.writers.smb_writer import write_smb

            smb_str = str(cfg.smb_path)
            if verbose:
                print(
                    f"[LinkMesh] 写出 PUMI SMB 基础路径：{smb_str}"
                )
                print(
                    "[LinkMesh] PUMI 实际 rank-0 SMB 文件名由 "
                    "SMB Writer/helper 管理"
                )
            write_smb(mesh, spec, smb_str)

    # ------------------------------------------------------------------ #
    # Step 6：可视化自检（若配置 plot_path）                                 #
    # ------------------------------------------------------------------ #
    if cfg.plot_path is not None:
        from linkmesh.utils.plotter import plot_mesh
        plot_str = str(cfg.plot_path)
        if verbose:
            print(f"[LinkMesh] 生成网格自检图：{plot_str}")
        plot_mesh(
            gfile_data,
            mesh,
            plot_str,
            show_region_ids=True,
            lcfs_reference_only=(
                cfg.boundary_source == "array_file" and cfg.plot_lcfs
            ),
        )
        if verbose:
            print(f"[LinkMesh] PNG 路径：{plot_str}")


def _format_optional_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6g}"


def _print_mesh_quality_report(report) -> None:
    """Print one compact human-readable report without defining a wire format."""
    print("Mesh quality:")
    print(
        f"  nodes={report.node_count}, triangles={report.triangle_count}, "
        f"Regions={report.region_count}"
    )
    print(
        "  angle [degree]: "
        f"min={report.minimum_angle:.6g}, "
        f"P01={report.minimum_angle_p01:.6g}, "
        f"P05={report.minimum_angle_p05:.6g}, "
        f"max={report.maximum_angle:.6g}"
    )
    print(
        "  shape Q [-]: "
        f"min={report.minimum_shape_quality:.6g}, "
        f"P01={report.shape_quality_p01:.6g}, "
        f"P05={report.shape_quality_p05:.6g}, "
        f"median={report.median_shape_quality:.6g}"
    )
    print(
        "  equivalent size [m]: "
        f"min={report.minimum_equivalent_size:.6g}, "
        f"median={report.median_equivalent_size:.6g}, "
        f"max={report.maximum_equivalent_size:.6g}"
    )
    print(
        "  adjacent size ratio [-]: "
        f"max={_format_optional_metric(report.maximum_adjacent_size_ratio)}, "
        f"P95={_format_optional_metric(report.adjacent_size_ratio_p95)}, "
        f"P99={_format_optional_metric(report.adjacent_size_ratio_p99)}"
    )
    print(
        "  structure counts: "
        f"degenerate={report.degenerate_triangle_count}, "
        f"duplicate={report.duplicate_triangle_count}, "
        f"non-manifold={report.non_manifold_edge_count}"
    )

    diagnostics = report.refinement
    if (
        diagnostics is None
        or not diagnostics.enabled
        or diagnostics.transition_interface_count == 0
    ):
        return

    node_growth = (
        diagnostics.final_node_count / diagnostics.initial_node_count
    )
    triangle_growth = (
        diagnostics.final_triangle_count
        / diagnostics.initial_triangle_count
    )
    print("Transition quality:")
    print(
        f"  W [m]={diagnostics.transition_width:.6g}, "
        f"interfaces={diagnostics.transition_interface_count}, "
        f"iterations={diagnostics.iteration_count}"
    )
    print(
        "  mesh growth: "
        f"nodes={diagnostics.initial_node_count}"
        f"->{diagnostics.final_node_count} ({node_growth:.6g}x), "
        f"triangles={diagnostics.initial_triangle_count}"
        f"->{diagnostics.final_triangle_count} ({triangle_growth:.6g}x)"
    )
    print(
        f"  affected coarse triangles="
        f"{diagnostics.affected_coarse_triangle_count}, "
        f"maximum area excess="
        f"{diagnostics.final_maximum_area_excess:.6g}, "
        f"violations={diagnostics.final_violating_triangle_count}"
    )
    for interface in diagnostics.interfaces:
        print(
            f"  interface Regions={interface.region_ids}: "
            f"fine={interface.fine_region_id} "
            f"(hf={interface.fine_dx:.6g} m), "
            f"coarse={interface.coarse_region_id} "
            f"(hc={interface.coarse_dx:.6g} m), "
            f"W={interface.transition_width:.6g} m, "
            f"affected={interface.affected_coarse_triangle_count}, "
            f"maximum area excess={interface.maximum_area_excess:.6g}"
        )


def _run_regions_inspect(args: argparse.Namespace) -> None:
    """Execute the first-batch inspect chain without Triangle generation."""
    overrides = config_mod.RegionsInspectOverrides(
        multi_array_file=args.multi_array_file,
        regions_map=args.regions_map,
        plot=args.plot,
        verbose=True if args.verbose else UNSET,
    )
    cfg = config_mod.load_regions_inspect_config(
        overrides,
        config_arg=args.config,
    )

    from linkmesh.mesher.oft_adapter import inspect_multi_region_ids
    from linkmesh.readers.boundary_reader import read_multi_boundary_file
    from linkmesh.regions import (
        assign_final_region_ids,
        build_region_plan,
        region_map_entries,
        write_regions_map,
    )
    from linkmesh.utils.plotter import plot_regions_inspection

    blocks = read_multi_boundary_file(cfg.multi_array_file_path)
    plan = build_region_plan(blocks)
    region_ids = inspect_multi_region_ids(plan)
    numbered_plan = assign_final_region_ids(plan, region_ids)
    records = region_map_entries(numbered_plan)

    # All parsing, tree, role, and OFT setup checks have succeeded before any
    # ordinary success artifact is created.
    plot_regions_inspection(
        numbered_plan,
        records,
        str(cfg.plot_path),
    )
    write_regions_map(records, cfg.regions_map_path)

    if cfg.verbose:
        print(f"[LinkMesh] multi-array curves: {len(blocks)}")
        print(f"[LinkMesh] regions map: {cfg.regions_map_path}")
        print(f"[LinkMesh] inspection PNG: {cfg.plot_path}")


def _run_regions_generate(args: argparse.Namespace) -> None:
    """Rebuild, validate, and generate a full OFT N-region mesh."""
    overrides = config_mod.RegionsGenerateOverrides(
        target=args.target,
        multi_array_file=args.multi_array_file,
        regions_map=args.regions_map,
        plot=args.plot,
        hdf5=args.hdf5,
        model=args.model,
        smb=args.smb,
        mesh_dx=args.mesh_dx,
        region_dx=(
            args.region_dx
            if args.region_dx is not None
            else UNSET
        ),
        transition_width=args.transition_width,
        verbose=True if args.verbose else UNSET,
    )
    cfg = config_mod.load_regions_generate_config(
        overrides,
        config_arg=args.config,
    )

    from linkmesh.mesher.oft_adapter import (
        generate_multi_region_mesh,
        inspect_multi_region_ids,
    )
    from linkmesh.readers.boundary_reader import read_multi_boundary_file
    from linkmesh.regions import (
        assign_final_region_ids,
        build_region_plan,
        read_regions_map,
        resolve_region_dx,
        validate_plan_against_map,
    )
    from linkmesh.utils.plotter import plot_regions_mesh

    records = read_regions_map(cfg.regions_map_path)
    blocks = read_multi_boundary_file(cfg.multi_array_file_path)
    plan = build_region_plan(blocks)
    region_ids = inspect_multi_region_ids(plan)
    numbered_plan = assign_final_region_ids(plan, region_ids)
    validate_plan_against_map(numbered_plan, records)
    resolved_dx = resolve_region_dx(
        records,
        cfg.mesh_dx,
        dict(cfg.region_dx),
    )

    initial_mesh = generate_multi_region_mesh(numbered_plan, resolved_dx)
    from linkmesh.mesher.triangle_refinement import refine_transition_mesh

    refinement_result = refine_transition_mesh(
        initial_mesh,
        resolved_dx,
        cfg.transition_width,
    )
    mesh = refinement_result.mesh

    counts = {
        region_id: int(np.count_nonzero(mesh.region_ids == region_id))
        for region_id in sorted(resolved_dx)
    }
    if any(count == 0 for count in counts.values()):
        raise ValueError("完整网格中至少一个 map Region 没有三角形")

    if cfg.verbose:
        from linkmesh.mesh_quality import calculate_mesh_quality

        quality_report = calculate_mesh_quality(
            mesh,
            refinement_result.diagnostics,
        )
        _print_mesh_quality_report(quality_report)

    if cfg.target == "trimeg":
        from linkmesh.writers.hdf5_writer import write_hdf5

        write_hdf5(mesh, str(cfg.hdf5_path), verbose=False)
    elif cfg.target == "m3dc1":
        from linkmesh.m3dc1_model import build_multi_face_model
        from linkmesh.writers.m3dc1_model_writer import write_m3dc1_model
        from linkmesh.writers.smb_writer import write_smb

        build_result = build_multi_face_model(mesh)
        write_m3dc1_model(build_result, str(cfg.model_path))
        write_smb(mesh, build_result, str(cfg.smb_path))

    plot_regions_mesh(mesh, records, str(cfg.plot_path))

    if cfg.verbose:
        record_by_id = {
            record.region_id: record
            for record in records
        }
        print(
            f"[LinkMesh] target={cfg.target}, nodes={mesh.n_nodes}, "
            f"triangles={mesh.n_triangles}, regions={len(counts)}"
        )
        for region_id in sorted(counts):
            record = record_by_id[region_id]
            label = (
                f", label={record.physical_label}"
                if record.physical_label
                else ""
            )
            print(
                f"[LinkMesh] Region {region_id}: "
                f"curve_id={record.curve_id}, triangles={counts[region_id]}"
                f"{label}"
            )
        if cfg.hdf5_path is not None:
            print(f"[LinkMesh] TRIMEG HDF5: {cfg.hdf5_path}")
        if cfg.model_path is not None:
            print(f"[LinkMesh] M3D-C1 model TXT: {cfg.model_path}")
        if cfg.smb_path is not None:
            print(f"[LinkMesh] PUMI SMB base: {cfg.smb_path}")
        print(f"[LinkMesh] mesh PNG: {cfg.plot_path}")
    else:
        print(
            f"节点数: {mesh.n_nodes}，三角形数: {mesh.n_triangles}，"
            f"Region 数: {len(counts)}"
        )


if __name__ == "__main__":
    main()
