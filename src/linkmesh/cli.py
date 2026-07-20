"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse）
    - 按顺序调用 reader → mesher（OFT Adapter）→ writer
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑（除历史过渡函数 _build_boundary_config 外）
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

import numpy as np


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
    if args.plot:
        from linkmesh.utils.plotter import plot_mesh
        if args.verbose:
            print(f"[LinkMesh] 生成网格自检图：{args.plot}")
        plot_mesh(gfile_data, mesh, args.plot)


def _build_boundary_config(
    gfile_data: "object",
    args: argparse.Namespace,
) -> "object":
    """[历史/过渡函数，非 M2 正式路径] 从 GFileData 构造旧 Python Triangle BoundaryConfig。

    本函数是历史 Python Triangle 路线的胶水代码，已被 mesher/oft_adapter.py
    的 OFT gs_Domain 路线替代，不再由 CLI 正式调用。当前保留其定义以维持与
    历史过渡代码的兼容性，本轮不删除、不扩展。

    区域标记约定（历史 Python Triangle 路线）：
        region_id=1：等离子体区（plasma，LCFS 内部）
        region_id=2：真空区（vacuum，LCFS 与外边界之间）

    边界标记约定（历史 Python Triangle 路线）：
        boundary_marker=1：LCFS（最后闭合磁面）
        boundary_marker=2：第一壁内表面（若有）
        boundary_marker=3：外边界（计算域矩形边界）

    参数：
        gfile_data: GFileData 对象（来自 read_gfile()）
        args:       CLI 参数（含 min_angle, max_area）

    返回：
        BoundaryConfig 对象
    """
    from linkmesh.mesher.triangle_wrapper import BoundaryConfig

    # ------------------------------------------------------------------ #
    # Step A：LCFS 点集重采样                                              #
    # ------------------------------------------------------------------ #
    # 目标点数：取 LCFS 原始点数与 200 的较小值，但不少于 40 点
    # 重采样使用等弧长插值，保证 Triangle 输入点分布均匀
    lcfs_r_raw = gfile_data.lcfs_r
    lcfs_z_raw = gfile_data.lcfs_z

    n_lcfs_target = max(40, min(200, len(lcfs_r_raw)))
    lcfs_r, lcfs_z = _resample_closed_curve(lcfs_r_raw, lcfs_z_raw, n_lcfs_target)

    # 去掉重复的末尾点（Triangle 输入不需要首尾重复）
    # 注意：_ensure_lcfs_closed 已保证首尾相同，这里去掉最后一个重复点
    if len(lcfs_r) > 1 and np.isclose(lcfs_r[0], lcfs_r[-1]) and np.isclose(lcfs_z[0], lcfs_z[-1]):
        lcfs_r = lcfs_r[:-1]
        lcfs_z = lcfs_z[:-1]

    n_lcfs = len(lcfs_r)

    # ------------------------------------------------------------------ #
    # Step B：构造外边界矩形                                               #
    # ------------------------------------------------------------------ #
    # 外边界矩形比 LCFS 包络盒向外扩展 pad_factor 倍的余量
    pad_r = 0.15  # R 方向向外扩展 15%
    pad_z = 0.15  # Z 方向向外扩展 15%

    r_min_lcfs = np.min(lcfs_r)
    r_max_lcfs = np.max(lcfs_r)
    z_min_lcfs = np.min(lcfs_z)
    z_max_lcfs = np.max(lcfs_z)

    dr = r_max_lcfs - r_min_lcfs
    dz = z_max_lcfs - z_min_lcfs

    # 若有第一壁数据，外边界包含第一壁
    if gfile_data.wall_r is not None and len(gfile_data.wall_r) > 0:
        r_min_outer = min(r_min_lcfs - pad_r * dr, np.min(gfile_data.wall_r) - 0.05)
        r_max_outer = max(r_max_lcfs + pad_r * dr, np.max(gfile_data.wall_r) + 0.05)
        z_min_outer = min(z_min_lcfs - pad_z * dz, np.min(gfile_data.wall_z) - 0.05)
        z_max_outer = max(z_max_lcfs + pad_z * dz, np.max(gfile_data.wall_z) + 0.05)
    else:
        r_min_outer = r_min_lcfs - pad_r * dr
        r_max_outer = r_max_lcfs + pad_r * dr
        z_min_outer = z_min_lcfs - pad_z * dz
        z_max_outer = z_max_lcfs + pad_z * dz

    # 外边界矩形的 4 个顶点（逆时针方向）
    # 顶点顺序：左下 → 右下 → 右上 → 左上
    outer_rect = np.array([
        [r_min_outer, z_min_outer],  # 左下
        [r_max_outer, z_min_outer],  # 右下
        [r_max_outer, z_max_outer],  # 右上
        [r_min_outer, z_max_outer],  # 左上
    ], dtype=np.float64)
    n_outer = len(outer_rect)  # = 4

    # ------------------------------------------------------------------ #
    # Step C：组装顶点列表与线段连接表                                      #
    # ------------------------------------------------------------------ #
    # 顶点全局索引布局：
    #   [0 .. n_lcfs-1]                    → LCFS 顶点
    #   [n_lcfs .. n_lcfs+n_outer-1]       → 外边界矩形顶点
    #   [n_lcfs+n_outer .. ...]            → 第一壁顶点（若有）

    vertices_list = [
        np.column_stack([lcfs_r, lcfs_z]),  # LCFS 顶点，shape=(n_lcfs, 2)
        outer_rect,                          # 外边界矩形顶点，shape=(4, 2)
    ]
    segments_list = []
    seg_markers_list = []

    # LCFS 线段（闭合环，boundary_marker=1）
    lcfs_segs = np.column_stack([
        np.arange(n_lcfs, dtype=np.int32),
        np.roll(np.arange(n_lcfs, dtype=np.int32), -1),
    ])  # shape=(n_lcfs, 2)，每行 [i, i+1]，最后一行 [n_lcfs-1, 0]
    segments_list.append(lcfs_segs)
    seg_markers_list.append(np.ones(n_lcfs, dtype=np.int32))  # marker=1

    # 外边界矩形线段（闭合环，boundary_marker=3）
    outer_base = n_lcfs
    outer_segs = np.column_stack([
        outer_base + np.arange(n_outer, dtype=np.int32),
        outer_base + np.roll(np.arange(n_outer, dtype=np.int32), -1),
    ])  # shape=(4, 2)
    segments_list.append(outer_segs)
    seg_markers_list.append(3 * np.ones(n_outer, dtype=np.int32))  # marker=3

    # 第一壁线段（若有，boundary_marker=2）
    n_wall = 0
    if gfile_data.wall_r is not None and len(gfile_data.wall_r) > 0:
        wall_r_raw = gfile_data.wall_r
        wall_z_raw = gfile_data.wall_z

        # 第一壁重采样（目标点数：取原始点数与 150 的较小值，但不少于 20 点）
        n_wall_target = max(20, min(150, len(wall_r_raw)))
        wall_r, wall_z = _resample_closed_curve(wall_r_raw, wall_z_raw, n_wall_target)

        # 去掉重复末尾点
        if len(wall_r) > 1 and np.isclose(wall_r[0], wall_r[-1]) and np.isclose(wall_z[0], wall_z[-1]):
            wall_r = wall_r[:-1]
            wall_z = wall_z[:-1]

        n_wall = len(wall_r)
        vertices_list.append(np.column_stack([wall_r, wall_z]))

        wall_base = n_lcfs + n_outer
        wall_segs = np.column_stack([
            wall_base + np.arange(n_wall, dtype=np.int32),
            wall_base + np.roll(np.arange(n_wall, dtype=np.int32), -1),
        ])
        segments_list.append(wall_segs)
        seg_markers_list.append(2 * np.ones(n_wall, dtype=np.int32))  # marker=2

    # 合并所有顶点与线段
    vertices = np.vstack(vertices_list).astype(np.float64)
    segments = np.vstack(segments_list).astype(np.int32)
    segment_markers = np.concatenate(seg_markers_list).astype(np.int32)

    # ------------------------------------------------------------------ #
    # Step D：设置区域标记点（regions）                                     #
    # ------------------------------------------------------------------ #
    # Triangle regions 格式：每行 [R, Z, region_id, max_area]
    # max_area=-1 表示不限制该区域的三角形面积（使用全局 max_area 约束）
    #
    # plasma 区标记点：使用磁轴坐标（rmaxis, zmaxis），保证在 LCFS 内部
    # vacuum 区标记点：使用 LCFS 包络盒右侧中点，保证在 LCFS 外、外边界内
    #
    # 注意：max_area 字段在 Triangle 中仅当控制字符串含 'a' 时生效；
    # 这里统一填 -1（不限制），全局面积约束由 args.max_area 通过控制字符串传入。

    plasma_seed_r = float(gfile_data.rmaxis)
    plasma_seed_z = float(gfile_data.zmaxis)

    # vacuum 区种子点：取 LCFS 最右侧点与外边界右侧之间的中点
    vacuum_seed_r = 0.5 * (r_max_lcfs + r_max_outer)
    vacuum_seed_z = 0.5 * (z_min_lcfs + z_max_lcfs)  # Z 方向取 LCFS 中心高度

    regions_list = [
        [plasma_seed_r, plasma_seed_z, 1.0, -1.0],  # plasma，region_id=1
        [vacuum_seed_r, vacuum_seed_z, 2.0, -1.0],  # vacuum，region_id=2
    ]

    regions = np.array(regions_list, dtype=np.float64)

    # ------------------------------------------------------------------ #
    # Step E：封装为 BoundaryConfig                                        #
    # ------------------------------------------------------------------ #
    return BoundaryConfig(
        vertices=vertices,
        segments=segments,
        segment_markers=segment_markers,
        regions=regions,
        min_angle=args.min_angle,
        max_area=args.max_area,
    )


def _resample_closed_curve(
    r: np.ndarray,
    z: np.ndarray,
    n_target: int,
) -> tuple[np.ndarray, np.ndarray]:
    """将闭合曲线重采样为 n_target 个等弧长间距的点（含末尾重复点）。

    [历史/过渡辅助函数] 仅供 _build_boundary_config 使用。

    使用线性插值（不引入额外依赖），适用于 LCFS 和第一壁的重采样。
    输入曲线应已闭合（首尾点相同或相近）。

    参数：
        r:        R 坐标数组（闭合曲线，首尾点相同）
        z:        Z 坐标数组（闭合曲线，首尾点相同）
        n_target: 目标点数（含末尾重复点，即输出 n_target 个点，
                  其中第 0 个和第 n_target-1 个相同）

    返回：
        (r_new, z_new)：重采样后的坐标数组，shape=(n_target,)
    """
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    # 确保首尾闭合
    if not (np.isclose(r[0], r[-1]) and np.isclose(z[0], z[-1])):
        r = np.append(r, r[0])
        z = np.append(z, z[0])

    # 计算累积弧长
    ds = np.sqrt(np.diff(r) ** 2 + np.diff(z) ** 2)
    s = np.concatenate([[0.0], np.cumsum(ds)])
    s_total = s[-1]

    if s_total < 1e-14:
        # 退化曲线，直接返回原始点
        return r, z

    # 等弧长采样点（含首尾重复点）
    s_new = np.linspace(0.0, s_total, n_target)

    # 线性插值
    r_new = np.interp(s_new, s, r)
    z_new = np.interp(s_new, s, z)

    return r_new, z_new


if __name__ == "__main__":
    main()
