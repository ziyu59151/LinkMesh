"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse）
    - 按顺序调用 reader → mesher（OFT Adapter）→ writer
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑
    - 不得直接操作文件
    - 不得在 CLI 中构造 OFT Domain、区域、边界、种子或转换数组

数据流（v1.9 M2 正式路径）：
    GFile → read_gfile() → GFileData
         → oft_adapter.generate_mesh() → Mesh2D
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

    # Triangle 质量控制参数（历史 Python Triangle 参数，OFT 正式路径暂不支持）
    parser.add_argument(
        "--min-angle",
        type=float,
        default=20.0,
        metavar="FLOAT",
        help="[历史参数] Triangle 最小内角约束（度，默认：20.0）；OFT 正式路径暂不支持",
    )
    parser.add_argument(
        "--max-area",
        type=float,
        default=None,
        metavar="FLOAT",
        help="[历史参数] Triangle 最大三角形面积约束（m²，默认：不限制）；OFT 正式路径暂不支持",
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

    执行顺序（v1.9 M2 正式路径）：
        1. 解析命令行参数
        2. 调用 readers.gfile_reader.read_gfile() → GFileData（OFT Adapter）
        3. 调用 mesher.oft_adapter.generate_mesh() → Mesh2D（OFT gs_Domain 路线）
        4. 调用 writers.hdf5_writer.write_hdf5()（除非 --no-hdf5）
        5. 调用 writers.smb_writer.write_smb()（除非 --no-smb）
        6. 调用 utils.plotter.plot_mesh()（若指定 --plot）

    历史参数约束：
        --min-angle 与 --max-area 属于旧 Python Triangle 参数，OFT 正式路径暂不支持。
        若用户给出非默认值，CLI 抛出清晰错误，不静默忽略。默认值不传给 OFT Adapter。
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


def _check_unsupported_legacy_params(args: argparse.Namespace) -> None:
    """检查历史 Triangle 参数：若用户给出非默认值则抛清晰错误。

    OFT 正式路径不支持 --min-angle / --max-area 这两个旧 Python Triangle 参数。
    不得将它们静默忽略，也不得映射为 OFT dx。默认值不传给 OFT Adapter。
    """
    if args.min_angle != 20.0:
        raise ValueError(
            "OFT 正式网格生成路径（M2）暂不支持历史参数 --min-angle。"
            "该参数属于旧 Python Triangle 路线；OFT 网格尺度由 Adapter 默认值控制。"
            "请去除 --min-angle 后重试。"
        )
    if args.max_area is not None:
        raise ValueError(
            "OFT 正式网格生成路径（M2）暂不支持历史参数 --max-area。"
            "该参数属于旧 Python Triangle 路线；OFT 网格尺度由 Adapter 默认值控制。"
            "请去除 --max-area 后重试。"
        )


def _run(args: argparse.Namespace) -> None:
    """LinkMesh 主执行逻辑（由 main() 调用，异常由 main() 统一捕获）。"""

    # ------------------------------------------------------------------ #
    # Step 0：历史 Triangle 参数拦截                                        #
    # ------------------------------------------------------------------ #
    _check_unsupported_legacy_params(args)

    # ------------------------------------------------------------------ #
    # Step 1：读取 GFile（M1 里程碑，保持不变）                             #
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
    # Step 2：生成网格（M2 正式路径：OFT Adapter）                          #
    # ------------------------------------------------------------------ #
    from linkmesh.mesher.oft_adapter import generate_mesh

    if args.verbose:
        print("[LinkMesh] 调用 OFT gs_Domain 生成二维三角网格...")

    # 使用 OFT Adapter 已验证默认尺度（不传入历史 Triangle 参数）
    mesh = generate_mesh(gfile_data)

    if args.verbose:
        print(f"  节点数: {mesh.n_nodes}")
        print(f"  三角形数: {mesh.n_triangles}")
    else:
        print(f"节点数: {mesh.n_nodes}，三角形数: {mesh.n_triangles}")

    # ------------------------------------------------------------------ #
    # Step 3：写出 HDF5（M3 里程碑）                                        #
    # ------------------------------------------------------------------ #
    if not args.no_hdf5:
        from linkmesh.writers.hdf5_writer import write_hdf5
        if args.verbose:
            print(f"[LinkMesh] 写出 TRIMEG HDF5：{args.output}")
        write_hdf5(mesh, args.output, verbose=args.verbose)

    # ------------------------------------------------------------------ #
    # Step 4：写出 .smb（M4 里程碑）                                        #
    # ------------------------------------------------------------------ #
    if not args.no_smb:
        from linkmesh.writers.smb_writer import write_smb
        if args.verbose:
            print(f"[LinkMesh] 写出 PUMI .smb：{args.smb}")
        write_smb(mesh, args.smb)

    # ------------------------------------------------------------------ #
    # Step 5：可视化自检（M2 完整版）                                        #
    # ------------------------------------------------------------------ #
    # 显式启用 OFT 区域填色（show_region_ids=True），使正式 M2 PNG 默认显示
    # 各 OFT 区域的离散颜色。不修改 plot_mesh() 的全局默认参数，其他调用方
    # 仍可只画网格线。
    if args.plot:
        from linkmesh.utils.plotter import plot_mesh
        if args.verbose:
            print(f"[LinkMesh] 生成网格自检图：{args.plot}")
        plot_mesh(gfile_data, mesh, args.plot, show_region_ids=True)


if __name__ == "__main__":
    main()
