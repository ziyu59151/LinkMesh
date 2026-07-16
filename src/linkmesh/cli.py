"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse）
    - 按顺序调用 reader → mesher → writer
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑
    - 不得直接操作文件

数据流：
    GFile → read_gfile() → GFileData
         → 构造 BoundaryConfig
         → generate_mesh() → Mesh2D
         → write_hdf5()（除非 --no-hdf5）
         → write_smb()（除非 --no-smb）
         → plot_mesh() / plot_lcfs_only()（若指定 --plot）
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    """构造 LinkMesh CLI 参数解析器。

    返回：
        argparse.ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        prog="linkmesh",
        description=(
            "LinkMesh：从 GFile/EQDSK 平衡文件生成二维三角网格，"
            "并导出为 TRIMEG HDF5 或 M3DC1 PUMI .smb 静态网格文件。"
        ),
    )

    # 必选参数
    parser.add_argument(
        "--gfile",
        required=True,
        metavar="PATH",
        help="GFile/EQDSK 平衡文件路径（必选）",
    )

    # 可选输出参数
    parser.add_argument(
        "--output",
        default="mesh.h5",
        metavar="PATH",
        help="TRIMEG HDF5 输出路径（默认：mesh.h5）",
    )
    parser.add_argument(
        "--smb",
        default="mesh.smb",
        metavar="PATH",
        help="PUMI .smb 输出路径（默认：mesh.smb）",
    )
    parser.add_argument(
        "--plot",
        default=None,
        metavar="PATH",
        help="可视化自检图输出路径（默认：不生成）",
    )

    # Triangle 质量控制参数
    parser.add_argument(
        "--min-angle",
        type=float,
        default=20.0,
        metavar="FLOAT",
        help="Triangle 最小内角约束（度，默认：20.0）",
    )
    parser.add_argument(
        "--max-area",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Triangle 最大三角形面积约束（m²，默认：不限制）",
    )

    # 跳过开关
    parser.add_argument(
        "--no-smb",
        action="store_true",
        help="跳过 .smb 文件生成（仅生成 HDF5）",
    )
    parser.add_argument(
        "--no-hdf5",
        action="store_true",
        help="跳过 HDF5 文件生成（仅生成 .smb）",
    )

    # 详细日志
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印详细日志（节点数、三角形数、写入状态）",
    )

    return parser


def main() -> None:
    """LinkMesh CLI 主入口函数。

    执行顺序：
        1. 解析命令行参数
        2. 调用 readers.gfile_reader.read_gfile() → GFileData（OFT Adapter）
        3. 构造 BoundaryConfig（从 GFileData 提取 LCFS 边界点集与区域配置）
        4. 调用 mesher.triangle_wrapper.generate_mesh() → Mesh2D
        5. 调用 writers.hdf5_writer.write_hdf5()（除非 --no-hdf5）
        6. 调用 writers.smb_writer.write_smb()（除非 --no-smb）
        7. 调用 utils.plotter.plot_mesh() 或 plot_lcfs_only()（若指定 --plot）

    里程碑说明：
        M1：Step 1-2 + plot_lcfs_only() 可用
        M2：Step 1-4 + plot_mesh() 可用
        M3：Step 1-5 可用（第一战役闭环）
        M4：Step 1-6 可用（第二战役闭环）
        M5：完整端到端链路
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        _run(args)
    except NotImplementedError as e:
        print(f"[LinkMesh] 该功能尚未实现（当前里程碑限制）：\n  {e}", file=sys.stderr)
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


def _run(args: argparse.Namespace) -> None:
    """LinkMesh 主执行逻辑（由 main() 调用，异常由 main() 统一捕获）。"""

    # ------------------------------------------------------------------ #
    # Step 1：读取 GFile（M1 里程碑）                                      #
    # ------------------------------------------------------------------ #
    from linkmesh.readers.gfile_reader import read_gfile

    if args.verbose:
        print(f"[LinkMesh] 读取 GFile：{args.gfile}")

    gfile_data = read_gfile(args.gfile)

    if args.verbose:
        print(f"  LCFS 点数: {len(gfile_data.lcfs_r)}")
        print(f"  磁轴: (R={gfile_data.rmaxis:.4f} m, Z={gfile_data.zmaxis:.4f} m)")
        if gfile_data.wall_r is not None:
            print(f"  第一壁点数: {len(gfile_data.wall_r)}")
        else:
            print("  第一壁: 无（GFile 不含 limiter 数据）")

    # ------------------------------------------------------------------ #
    # Step 2：若仅需 LCFS 可视化（M1 里程碑），在网格生成前先出图           #
    # ------------------------------------------------------------------ #
    # 注意：若 --no-hdf5 且 --no-smb 且指定了 --plot，则仅绘制 LCFS 图
    mesh_needed = not (args.no_hdf5 and args.no_smb)

    if args.plot and not mesh_needed:
        from linkmesh.utils.plotter import plot_lcfs_only
        plot_lcfs_only(gfile_data, args.plot)
        return

    # ------------------------------------------------------------------ #
    # Step 3：构造 BoundaryConfig（M2 里程碑）                             #
    # ------------------------------------------------------------------ #
    # TODO: 待 M2 里程碑实现：从 GFileData 提取 LCFS 边界点集，
    #       构造 BoundaryConfig（vertices, segments, regions, segment_markers）
    # 当前占位：直接抛出 NotImplementedError，触发 M2 里程碑实现
    from linkmesh.mesher.triangle_wrapper import BoundaryConfig, generate_mesh

    config = _build_boundary_config(gfile_data, args)

    # ------------------------------------------------------------------ #
    # Step 4：生成网格（M2 里程碑）                                         #
    # ------------------------------------------------------------------ #
    if args.verbose:
        print("[LinkMesh] 调用 Triangle 生成二维三角网格...")

    mesh = generate_mesh(config)

    if args.verbose:
        print(f"  节点数: {mesh.n_nodes}")
        print(f"  三角形数: {mesh.n_triangles}")
        print(f"  边界线段数: {mesh.n_boundary_segments}")

    # ------------------------------------------------------------------ #
    # Step 5：写出 HDF5（M3 里程碑）                                        #
    # ------------------------------------------------------------------ #
    if not args.no_hdf5:
        from linkmesh.writers.hdf5_writer import write_hdf5
        if args.verbose:
            print(f"[LinkMesh] 写出 TRIMEG HDF5：{args.output}")
        write_hdf5(mesh, args.output, verbose=args.verbose)

    # ------------------------------------------------------------------ #
    # Step 6：写出 .smb（M4 里程碑）                                        #
    # ------------------------------------------------------------------ #
    if not args.no_smb:
        from linkmesh.writers.smb_writer import write_smb
        if args.verbose:
            print(f"[LinkMesh] 写出 PUMI .smb：{args.smb}")
        write_smb(mesh, args.smb)

    # ------------------------------------------------------------------ #
    # Step 7：可视化自检（M2 里程碑）                                        #
    # ------------------------------------------------------------------ #
    if args.plot:
        from linkmesh.utils.plotter import plot_mesh
        if args.verbose:
            print(f"[LinkMesh] 生成网格自检图：{args.plot}")
        plot_mesh(gfile_data, mesh, args.plot)


def _build_boundary_config(
    gfile_data: "object",
    args: argparse.Namespace,
) -> "object":
    """从 GFileData 构造 BoundaryConfig。

    当前为占位实现，待 M2 里程碑完整实现。

    实现要点（M2 里程碑）：
        1. 将 gfile_data.lcfs_r / lcfs_z 重采样为适合 Triangle 的点密度
        2. 构造 LCFS 闭合线段连接表（segments）
        3. 若有第一壁数据，构造第一壁线段连接表
        4. 构造外边界矩形（计算域边界）
        5. 设置区域标记点（regions）：plasma 区内一点、vacuum 区内一点
        6. 设置边界标记（segment_markers）：1=LCFS, 2=first_wall, 3=outer_boundary
        7. 封装为 BoundaryConfig 对象

    参数：
        gfile_data: GFileData 对象
        args:       CLI 参数（含 min_angle, max_area）

    返回：
        BoundaryConfig 对象
    """
    raise NotImplementedError(
        "_build_boundary_config() 将在 M2 里程碑阶段实现。\n"
        "需要从 GFileData.lcfs_r/lcfs_z 构造 Triangle 输入的 "
        "vertices、segments、regions、segment_markers 字段。\n"
        "请参考 LinkMesh_Architecture_Plan.md 第 7 节。"
    )


if __name__ == "__main__":
    main()
