"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse），标记用户显式输入
    - 调用 config.load_effective_config() 完成「内建默认值 < linkmesh.in < 显式 CLI」合并
    - 按 profile/boundary_source 选择已实现路径，调用 reader → mesher（OFT Adapter）
      → writer → plotter
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑（Domain/区域/边界/种子/数组转换）
    - 不得直接解析 TOML（交给 config.py）
    - 不得自行维护第二套配置默认值（默认值集中在 config.py）
    - 不得把 profile/source 判断放入 Reader 或 Writer
    - 未实现组合不得回退到 nested_three_region

数据流（v2.3 输入层 I/II 正式路径）：
    CLI 参数 → CliOverrides（仅显式输入）→ load_effective_config() → EffectiveConfig
         → read_gfile() → GFileData
         → oft_adapter.generate_mesh(..., profile=, boundary_source=) → Mesh2D
         → target=trimeg：write_hdf5()（且未 --no-hdf5）
         → target=m3dc1：build_single_face_model_spec() →
           write_m3dc1_model() + write_smb()（SMB 除非 --no-smb）
         → plot_mesh()（若配置 plot_path）

CLI 分区域网格密度参数（v1.13 契约）：
    --plasma-dx / --vacuum-dx / --outer-dx 三个目标区域网格长度尺度参数（单位 m）。
    CLI 只负责解析、标记显式输入并把值交给 config 合并；有限正数校验集中在 config.py，
    合并后 EffectiveConfig 的 dx 已保证为有限正数。

输入层 I（v2.3）新增参数（蓝图第 6A.5 节）：
    --config / --no-config（互斥）、--target、--profile、--boundary-source、--array-file。
    旧参数全部保留，旧命令无配置时行为不变。

输入层 II（v2.3）新增业务分派：
    - nested_three_region + artificial_outer：原路径（有壁三区域 / 无壁两区域）；
    - single_region + lcfs：单 polygon Region，LCFS 为唯一计算域边界，
      single-region 网格尺度用 plasma_dx；不消费 vacuum_dx/outer_dx。

参见 LinkMesh_Architecture_Plan.md v2.3 第 6、6A 节。
"""

from __future__ import annotations

import argparse
import sys

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
        description=(
            "LinkMesh：从 GFile/EQDSK 平衡文件生成二维三角网格，"
            "并导出为 TRIMEG HDF5 或 M3DC1 PUMI .smb 静态网格文件。"
        ),
    )

    # ------------------------------------------------------------------ #
    # 输入层 I 新增：配置发现                                              #
    # ------------------------------------------------------------------ #
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="只加载该 linkmesh.in 配置文件；不存在立即失败（与 --no-config 互斥）",
    )
    config_group.add_argument(
        "--no-config",
        action="store_true",
        help="禁用配置文件自动发现（与 --config 互斥）",
    )

    # ------------------------------------------------------------------ #
    # 输入层 I 新增：target / profile / boundary_source / array_file      #
    # 默认值交给 config.py；此处 default=UNSET 表示未显式提供。            #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--target",
        default=UNSET,
        choices=list(config_mod.TARGETS),
        help="目标输出族（mesh_only/trimeg/m3dc1）；覆盖配置文件",
    )
    parser.add_argument(
        "--profile",
        default=UNSET,
        choices=list(config_mod.PROFILES),
        help="区域策略（single_region/nested_three_region）；覆盖配置文件",
    )
    parser.add_argument(
        "--boundary-source",
        dest="boundary_source",
        default=UNSET,
        choices=list(config_mod.BOUNDARY_SOURCES),
        help="计算域外边界来源；覆盖配置文件",
    )
    parser.add_argument(
        "--array-file",
        dest="array_file",
        default=UNSET,
        metavar="PATH",
        help="array boundary CSV 路径（boundary_source=array_file 时使用）",
    )

    # ------------------------------------------------------------------ #
    # 既有：GFile 输入                                                     #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--gfile",
        default=UNSET,
        metavar="PATH",
        help="GFile/EQDSK 平衡文件路径",
    )

    # ------------------------------------------------------------------ #
    # 既有：输出路径参数（default=UNSET 交给 config 合并）                  #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--output",
        dest="hdf5",
        default=UNSET,
        metavar="PATH",
        help="TRIMEG HDF5 输出路径（默认：mesh.h5，target=trimeg 时生效）",
    )
    parser.add_argument(
        "--smb",
        default=UNSET,
        metavar="PATH",
        help="PUMI .smb 输出路径（M4；默认无可执行路径）",
    )
    parser.add_argument(
        "--plot",
        default=UNSET,
        metavar="PATH",
        help="可视化自检图输出路径（默认：不生成）",
    )
    parser.add_argument(
        "--model",
        default=UNSET,
        metavar="PATH",
        help="M3DC1 TXT model 输出路径（M4；默认无可执行路径）",
    )

    # ------------------------------------------------------------------ #
    # 既有：分区域网格密度参数（default=UNSET，合并/校验交给 config）        #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--plasma-dx",
        dest="plasma_dx",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help="target plasma-region mesh scale in meters (inside LCFS; default: 0.08)",
    )
    parser.add_argument(
        "--vacuum-dx",
        dest="vacuum_dx",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help=(
            "target vacuum-region mesh scale in meters "
            "(between LCFS and first wall; default: 0.10)"
        ),
    )
    parser.add_argument(
        "--outer-dx",
        dest="outer_dx",
        type=float,
        default=UNSET,
        metavar="FLOAT",
        help=(
            "target outer-region mesh scale in meters "
            "(between first wall and outer boundary; default: 0.15)"
        ),
    )

    # ------------------------------------------------------------------ #
    # 历史 Python Triangle 参数（OFT 正式路径不支持，非默认值报错）          #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--min-angle",
        dest="min_angle",
        type=float,
        default=20.0,
        metavar="FLOAT",
        help="[历史参数] Triangle 最小内角约束（度，默认：20.0）；OFT 正式路径暂不支持",
    )
    parser.add_argument(
        "--max-area",
        dest="max_area",
        type=float,
        default=None,
        metavar="FLOAT",
        help="[历史参数] Triangle 最大三角形面积约束（m²，默认：不限制）；OFT 正式路径暂不支持",
    )

    # ------------------------------------------------------------------ #
    # 既有：跳过开关（保持旧行为）                                          #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--no-smb",
        action="store_true",
        help="跳过 .smb 文件生成",
    )
    parser.add_argument(
        "--no-hdf5",
        action="store_true",
        help="跳过 HDF5 文件生成",
    )

    # ------------------------------------------------------------------ #
    # 既有：详细日志（store_true；显式 True 时覆盖 TOML verbose）           #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印详细日志（节点数、三角形数、写入状态、配置文件路径）",
    )

    return parser


def main() -> None:
    """LinkMesh CLI 主入口函数。

    执行顺序（v2.3 输入层 I/II）：
        0. 解析 CLI，拦截历史参数
        1. 收集用户显式输入 → CliOverrides
        2. load_effective_config()（发现/读取/校验/合并 linkmesh.in 与 CLI）
        3. read_gfile() → GFileData
        4. oft_adapter.generate_mesh(..., profile=, boundary_source=) → Mesh2D
        5. target=trimeg 时写出 HDF5
        6. target=m3dc1 时构造一次 M3DC1ModelSpec，并写出 TXT 与可选 SMB
        7. plot_mesh()（若配置 plot_path）
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        _run(args)
    except NotImplementedError as e:
        print(f"[LinkMesh] 该功能尚未实现（当前阶段限制）：\n  {e}", file=sys.stderr)
        sys.exit(1)
    except ConfigError as e:
        print(f"[LinkMesh] 配置错误：{e}", file=sys.stderr)
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


def _check_unsupported_legacy_params(args: argparse.Namespace) -> None:
    """检查历史 Triangle 参数：若用户给出非默认值则抛清晰错误。

    OFT 正式路径不支持 --min-angle / --max-area 这两个旧 Python Triangle 参数。
    不得静默忽略，也不得映射为 OFT dx。默认值不传给 OFT Adapter。
    """
    if args.min_angle != 20.0:
        raise ValueError(
            "OFT 正式网格生成路径暂不支持历史参数 --min-angle。"
            "该参数属于旧 Python Triangle 路线；OFT 网格尺度由 dx 参数控制。"
            "请去除 --min-angle 后重试。"
        )
    if args.max_area is not None:
        raise ValueError(
            "OFT 正式网格生成路径暂不支持历史参数 --max-area。"
            "该参数属于旧 Python Triangle 路线；OFT 网格尺度由 dx 参数控制。"
            "请去除 --max-area 后重试。"
        )


def _build_overrides(args: argparse.Namespace) -> CliOverrides:
    """把 argparse Namespace 中用户显式提供的字段收集为 CliOverrides。

    未显式提供的字段保持 UNSET（default=UNSET）。
    --verbose 是 store_true：仅当为 True 时视为显式提供（旧行为兼容，
    显式 --verbose 覆盖 TOML；未加时不覆盖 TOML）。
    """
    overrides = CliOverrides(
        target=args.target,
        profile=args.profile,
        boundary_source=args.boundary_source,
        gfile=args.gfile,
        array_file=args.array_file,
        plasma_dx=args.plasma_dx,
        vacuum_dx=args.vacuum_dx,
        outer_dx=args.outer_dx,
        hdf5=args.hdf5,
        plot=args.plot,
        model=args.model,
        smb=args.smb,
    )
    # verbose：仅显式 True 覆盖，否则保持 UNSET 不覆盖 TOML。
    if args.verbose:
        overrides.verbose = True
    return overrides


def _run(args: argparse.Namespace) -> None:
    """LinkMesh 主执行逻辑（由 main() 调用，异常由 main() 统一捕获）。"""

    # ------------------------------------------------------------------ #
    # Step 0：历史参数拦截（在任何配置/网格生成之前）                       #
    # ------------------------------------------------------------------ #
    _check_unsupported_legacy_params(args)

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
            f"[LinkMesh] 有效配置：target={cfg.target}, profile={cfg.profile}, "
            f"boundary_source={cfg.boundary_source}"
        )

    # ------------------------------------------------------------------ #
    # Step 2：读取 GFile（M1）                                             #
    # 当前阶段进入业务执行的组合（config 已保证其余组合报未实现/失败）：      #
    #   - target ∈ {trimeg, mesh_only} + nested_three_region + artificial_outer #
    #   - target ∈ {trimeg, mesh_only} + single_region + lcfs（输入层 II） #
    # 上述两组均以 GFile 为输入，需要 gfile_path（required fields 已保证）。 #
    # GFile 只读取一次。                                                    #
    # ------------------------------------------------------------------ #
    from linkmesh.readers.gfile_reader import read_gfile

    gfile_str = str(cfg.gfile_path)
    if verbose:
        print(f"[LinkMesh] 读取 GFile：{gfile_str}")

    gfile_data = read_gfile(gfile_str)

    if verbose:
        print(f"  LCFS 点数: {len(gfile_data.lcfs_r)}")
        print(f"  磁轴: (R={gfile_data.rmaxis:.4f} m, Z={gfile_data.zmaxis:.4f} m)")
        if gfile_data.wall_r is not None:
            print(f"  第一壁点数: {len(gfile_data.wall_r)}")
        else:
            print("  第一壁: 无（GFile 不含 limiter 数据）")

    # ------------------------------------------------------------------ #
    # Step 3：生成网格（M2 正式路径：OFT Adapter）                          #
    # 按 profile/boundary_source 分派已实现路径；Adapter 自身也校验组合。    #
    # single_region + lcfs 只使用 plasma_dx；vacuum_dx/outer_dx 仍传入      #
    # （Adapter 在 single-region 分支忽略之），配置字段不删除。              #
    # ------------------------------------------------------------------ #
    from linkmesh.mesher.oft_adapter import generate_mesh

    if verbose:
        if cfg.profile == "single_region" and cfg.boundary_source == "lcfs":
            print("[LinkMesh] 调用 OFT gs_Domain 生成 single-region LCFS 二维三角网格...")
            print(f"  网格尺度: plasma_dx={cfg.plasma_dx} m（single-region 唯一尺度）")
        else:
            print("[LinkMesh] 调用 OFT gs_Domain 生成 nested-three-region 二维三角网格...")
            print(
                f"  网格尺度: plasma_dx={cfg.plasma_dx} m, "
                f"vacuum_dx={cfg.vacuum_dx} m, outer_dx={cfg.outer_dx} m"
            )

    mesh = generate_mesh(
        gfile_data,
        plasma_dx=cfg.plasma_dx,
        vacuum_dx=cfg.vacuum_dx,
        outer_dx=cfg.outer_dx,
        profile=cfg.profile,
        boundary_source=cfg.boundary_source,
    )

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
        plot_mesh(gfile_data, mesh, plot_str, show_region_ids=True)
        if verbose:
            print(f"[LinkMesh] PNG 路径：{plot_str}")


if __name__ == "__main__":
    main()
