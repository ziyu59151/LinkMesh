"""
cli.py —— LinkMesh 命令行入口。

职责：
    - 解析命令行参数（argparse）
    - 按顺序调用 reader → mesher → writer
    - 捕获异常并打印友好错误信息

禁止事项：
    - 不得包含任何业务逻辑（除 _build_boundary_config 的边界构造胶水代码外）
    - 不得直接操作文件

数据流：
    GFile → read_gfile() → GFileData
         → _build_boundary_config() → BoundaryConfig
         → generate_mesh() → Mesh2D
         → write_hdf5()（除非 --no-hdf5）
         → write_smb()（除非 --no-smb）
         → plot_mesh() / plot_lcfs_only()（若指定 --plot）
"""

from __future__ import annotations

import argparse
import sys

import numpy as np


def build_parser() -> argparse.ArgumentParser:
    """构造 LinkMesh CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="linkmesh",
        description=(
            "LinkMesh：从 GFile/EQDSK 平衡文件生成二维三角网格，"
            "并导出为 TRIMEG HDF5 或 M3DC1 PUMI .smb 静态网格文件。"
        ),
    )
    parser.add_argument("--gfile", required=True, metavar="PATH",
                        help="GFile/EQDSK 平衡文件路径（必选）")
    parser.add_argument("--output", default="mesh.h5", metavar="PATH",
                        help="TRIMEG HDF5 输出路径（默认：mesh.h5）")
    parser.add_argument("--smb", default="mesh.smb", metavar="PATH",
                        help="PUMI .smb 输出路径（默认：mesh.smb）")
    parser.add_argument("--plot", default=None, metavar="PATH",
                        help="可视化自检图输出路径（默认：不生成）")
    parser.add_argument("--min-angle", type=float, default=20.0, metavar="FLOAT",
                        help="Triangle 最小内角约束（度，默认：20.0）")
    parser.add_argument("--max-area", type=float, default=None, metavar="FLOAT",
                        help="Triangle 最大三角形面积约束（m²，默认：不限制）")
    parser.add_argument("--no-smb", action="store_true",
                        help="跳过 .smb 文件生成（仅生成 HDF5）")
    parser.add_argument("--no-hdf5", action="store_true",
                        help="跳过 HDF5 文件生成（仅生成 .smb）")
    parser.add_argument("--verbose", action="store_true",
                        help="打印详细日志（节点数、三角形数、写入状态）")
    return parser


def main() -> None:
    """LinkMesh CLI 主入口函数。"""
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

    # Step 1：读取 GFile（M1 里程碑）
    from linkmesh.readers.gfile_reader import read_gfile
    if args.verbose:
        print(f"[LinkMesh] 读取 GFile：{args.gfile}")
    gfile_data = read_gfile(args.gfile)
    if args.verbose:
        print(f"  LCFS 点数: {len(gfile_data.lcfs_r)}")
        print(f"  磁轴: (R={gfile_data.rmaxis:.4f} m, Z={gfile_data.zmaxis:.4f} m)")
        if gfile_data.wall_r is not None and len(gfile_data.wall_r) > 0:
            print(f"  第一壁点数: {len(gfile_data.wall_r)}")
        else:
            print("  第一壁: 无（GFile 不含可用 limiter 数据）")

    # Step 2：若仅需 LCFS 可视化（M1 里程碑），在网格生成前先出图
    mesh_needed = not (args.no_hdf5 and args.no_smb)
    if args.plot and not mesh_needed:
        from linkmesh.utils.plotter import plot_lcfs_only
        plot_lcfs_only(gfile_data, args.plot)
        return

    # Step 3：构造 BoundaryConfig（M2 里程碑）
    from linkmesh.mesher.triangle_wrapper import generate_mesh
    if args.verbose:
        print("[LinkMesh] 构造 Triangle 输入边界配置...")
    config = _build_boundary_config(gfile_data, args)
    if args.verbose:
        print(f"  边界顶点数: {len(config.vertices)}")
        print(f"  边界线段数: {len(config.segments)}")
        print(f"  区域标记点数: {len(config.regions)}")

    # Step 4：生成网格（M2 里程碑）
    if args.verbose:
        print("[LinkMesh] 调用 Triangle 生成二维三角网格...")
    mesh = generate_mesh(config)
    if args.verbose:
        print(f"  节点数: {mesh.n_nodes}")
        print(f"  三角形数: {mesh.n_triangles}")
        print(f"  边界线段数: {mesh.n_boundary_segments}")

    # Step 5：写出 HDF5（M3 里程碑）
    if not args.no_hdf5:
        from linkmesh.writers.hdf5_writer import write_hdf5
        if args.verbose:
            print(f"[LinkMesh] 写出 TRIMEG HDF5：{args.output}")
        write_hdf5(mesh, args.output, verbose=args.verbose)

    # Step 6：写出 .smb（M4 里程碑）
    if not args.no_smb:
        from linkmesh.writers.smb_writer import write_smb
        if args.verbose:
            print(f"[LinkMesh] 写出 PUMI .smb：{args.smb}")
        write_smb(mesh, args.smb)

    # Step 7：可视化自检（M2 里程碑）
    if args.plot:
        from linkmesh.utils.plotter import plot_mesh
        if args.verbose:
            print(f"[LinkMesh] 生成网格自检图：{args.plot}")
        plot_mesh(gfile_data, mesh, args.plot)


# ---------------------------------------------------------------------------
# 轻量几何辅助函数（仅供 _build_boundary_config 内部使用）
# ---------------------------------------------------------------------------

def _strip_closed_duplicate(r: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """去掉闭合曲线末尾与首点重复的点，返回不含重复末尾的点集。

    内部几何计算使用不含重复末尾的点集；构造 Triangle segments 时
    最后一条边由最后一点连回第一点，无需显式重复。
    """
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    if len(r) > 1 and np.isclose(r[0], r[-1]) and np.isclose(z[0], z[-1]):
        r = r[:-1]
        z = z[:-1]
    return r, z


def _polygon_area_signed(r: np.ndarray, z: np.ndarray) -> float:
    """用 Shoelace 公式计算多边形有向面积（不含重复末尾点）。

    正值表示逆时针，负值表示顺时针。
    """
    n = len(r)
    r_next = np.roll(r, -1)
    z_next = np.roll(z, -1)
    return 0.5 * float(np.sum(r * z_next - r_next * z))


def _is_degenerate(r: np.ndarray, z: np.ndarray, min_area: float = 1e-14) -> bool:
    """判断多边形是否退化（面积过小或点数不足）。"""
    if len(r) < 3:
        return True
    return abs(_polygon_area_signed(r, z)) < min_area


def _segments_intersect_proper(
    p1: np.ndarray, p2: np.ndarray,
    p3: np.ndarray, p4: np.ndarray,
    tol: float = 1e-12,
) -> bool:
    """判断线段 p1-p2 与 p3-p4 是否严格相交（不含共享端点的相邻边情况）。

    使用叉积参数化方法。返回 True 表示两线段在内部严格相交。
    """
    d1 = p2 - p1
    d2 = p4 - p3
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < tol:
        return False  # 平行或共线，不视为严格相交
    d3 = p3 - p1
    t = (d3[0] * d2[1] - d3[1] * d2[0]) / cross
    u = (d3[0] * d1[1] - d3[1] * d1[0]) / cross
    # 严格内部相交：t 和 u 均在 (0,1) 开区间内
    return (tol < t < 1.0 - tol) and (tol < u < 1.0 - tol)


def _polygon_has_self_intersection(r: np.ndarray, z: np.ndarray) -> bool:
    """检查多边形（不含重复末尾点）是否存在自交。

    排除相邻线段（共享端点）和首尾相邻线段，只检测真正的内部相交。
    """
    n = len(r)
    pts = np.column_stack([r, z])
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        for j in range(i + 2, n):
            # 跳过首尾相邻线段（i=0 与 j=n-1）
            if i == 0 and j == n - 1:
                continue
            p3 = pts[j]
            p4 = pts[(j + 1) % n]
            if _segments_intersect_proper(p1, p2, p3, p4):
                return True
    return False


def _point_in_polygon(pr: float, pz: float,
                      poly_r: np.ndarray, poly_z: np.ndarray) -> bool:
    """射线法判断点 (pr, pz) 是否严格位于多边形内部（不含重复末尾点）。

    使用向上射线（+Z 方向），正确处理水平边和顶点穿越情况。
    返回 True 表示点在多边形内部（不含边界）。
    """
    n = len(poly_r)
    inside = False
    j = n - 1
    for i in range(n):
        ri, zi = poly_r[i], poly_z[i]
        rj, zj = poly_r[j], poly_z[j]
        # 射线向右（+R 方向）穿越测试
        if ((zi > pz) != (zj > pz)):
            # 计算交点的 R 坐标
            r_intersect = rj + (pz - zj) / (zi - zj) * (ri - rj)
            if pr < r_intersect:
                inside = not inside
        j = i
    return inside


def _point_min_dist_to_polygon(pr: float, pz: float,
                                poly_r: np.ndarray, poly_z: np.ndarray) -> float:
    """计算点 (pr, pz) 到多边形各线段的最小距离（不含重复末尾点）。"""
    n = len(poly_r)
    min_dist = float("inf")
    for i in range(n):
        r1, z1 = poly_r[i], poly_z[i]
        r2, z2 = poly_r[(i + 1) % n], poly_z[(i + 1) % n]
        dr = r2 - r1
        dz = z2 - z1
        seg_len2 = dr * dr + dz * dz
        if seg_len2 < 1e-28:
            dist = np.hypot(pr - r1, pz - z1)
        else:
            t = ((pr - r1) * dr + (pz - z1) * dz) / seg_len2
            t = max(0.0, min(1.0, t))
            proj_r = r1 + t * dr
            proj_z = z1 + t * dz
            dist = np.hypot(pr - proj_r, pz - proj_z)
        if dist < min_dist:
            min_dist = dist
    return min_dist


def _polygons_intersect(r1: np.ndarray, z1: np.ndarray,
                        r2: np.ndarray, z2: np.ndarray) -> bool:
    """检查两条闭合多边形曲线是否存在线段相交（不含重复末尾点）。

    只检测边与边之间的严格相交，不检测包含关系。
    """
    n1 = len(r1)
    n2 = len(r2)
    pts1 = np.column_stack([r1, z1])
    pts2 = np.column_stack([r2, z2])
    for i in range(n1):
        p1 = pts1[i]
        p2 = pts1[(i + 1) % n1]
        for j in range(n2):
            p3 = pts2[j]
            p4 = pts2[(j + 1) % n2]
            if _segments_intersect_proper(p1, p2, p3, p4):
                return True
    return False


def _check_curve_valid(r: np.ndarray, z: np.ndarray,
                       name: str, min_points: int = 3) -> None:
    """验证曲线有效性：点数足够、坐标有限、非退化、无自交。

    参数：
        r, z:       不含重复末尾点的坐标数组
        name:       曲线名称（用于错误消息）
        min_points: 最少点数要求
    """
    if len(r) < min_points:
        raise ValueError(
            f"{name} 点数不足（{len(r)} < {min_points}），无法构成有效闭合曲线。"
        )
    if not (np.all(np.isfinite(r)) and np.all(np.isfinite(z))):
        raise ValueError(f"{name} 坐标含 NaN 或 Inf，无法使用。")
    if _is_degenerate(r, z):
        raise ValueError(f"{name} 退化（面积过小），无法构成有效计算域。")
    if _polygon_has_self_intersection(r, z):
        raise ValueError(f"{name} 存在自交，无法作为 Triangle PLC 输入。")


def _find_seed_in_annulus(
    inner_r: np.ndarray, inner_z: np.ndarray,
    outer_r: np.ndarray, outer_z: np.ndarray,
    min_margin: float,
    n_candidates: int = 200,
) -> tuple[float, float]:
    """在两条闭合多边形之间的环带区域内确定性寻找区域种子。

    策略：在外边界包围盒内生成固定规则网格候选点，筛选满足以下条件的点：
        1. 严格位于外多边形内部；
        2. 严格位于内多边形外部；
        3. 到内多边形的距离 >= min_margin；
        4. 到外多边形的距离 >= min_margin。
    在所有满足条件的候选点中，选取到内多边形距离最大的点（最远离内边界）。

    参数：
        inner_r, inner_z: 内边界多边形（不含重复末尾点）
        outer_r, outer_z: 外边界多边形（不含重复末尾点）
        min_margin:       到两条边界的最小距离要求
        n_candidates:     每个方向的候选点数（总候选点数为 n_candidates²）

    返回：
        (seed_r, seed_z)：满足条件的种子坐标

    异常：
        ValueError：找不到满足条件的候选点
    """
    r_min = np.min(outer_r)
    r_max = np.max(outer_r)
    z_min = np.min(outer_z)
    z_max = np.max(outer_z)

    # 生成规则网格候选点（固定顺序，确定性）
    rs = np.linspace(r_min, r_max, n_candidates + 2)[1:-1]
    zs = np.linspace(z_min, z_max, n_candidates + 2)[1:-1]

    best_r, best_z = None, None
    best_dist = -1.0

    for cr in rs:
        for cz in zs:
            # 必须在外边界内
            if not _point_in_polygon(cr, cz, outer_r, outer_z):
                continue
            # 必须在内边界外
            if _point_in_polygon(cr, cz, inner_r, inner_z):
                continue
            # 到内边界的距离
            d_inner = _point_min_dist_to_polygon(cr, cz, inner_r, inner_z)
            if d_inner < min_margin:
                continue
            # 到外边界的距离
            d_outer = _point_min_dist_to_polygon(cr, cz, outer_r, outer_z)
            if d_outer < min_margin:
                continue
            # 选取到内边界最远的点
            if d_inner > best_dist:
                best_dist = d_inner
                best_r = cr
                best_z = cz

    if best_r is None:
        raise ValueError(
            f"无法在环带区域内找到满足最小边界距离 {min_margin:.4g} m 的区域种子。"
            f"请检查边界嵌套关系或减小 min_margin。"
        )
    return float(best_r), float(best_z)


def _find_seed_inside_polygon(
    poly_r: np.ndarray, poly_z: np.ndarray,
    min_margin: float,
    n_candidates: int = 200,
) -> tuple[float, float]:
    """在单个闭合多边形内部确定性寻找区域种子。

    策略：在包围盒内生成固定规则网格候选点，筛选满足以下条件的点：
        1. 严格位于多边形内部；
        2. 到多边形边界的距离 >= min_margin。
    选取到边界距离最大的点（最靠近中心）。

    参数：
        poly_r, poly_z: 多边形（不含重复末尾点）
        min_margin:     到边界的最小距离要求
        n_candidates:   每个方向的候选点数

    返回：
        (seed_r, seed_z)

    异常：
        ValueError：找不到满足条件的候选点
    """
    r_min = np.min(poly_r)
    r_max = np.max(poly_r)
    z_min = np.min(poly_z)
    z_max = np.max(poly_z)

    rs = np.linspace(r_min, r_max, n_candidates + 2)[1:-1]
    zs = np.linspace(z_min, z_max, n_candidates + 2)[1:-1]

    best_r, best_z = None, None
    best_dist = -1.0

    for cr in rs:
        for cz in zs:
            if not _point_in_polygon(cr, cz, poly_r, poly_z):
                continue
            d = _point_min_dist_to_polygon(cr, cz, poly_r, poly_z)
            if d < min_margin:
                continue
            if d > best_dist:
                best_dist = d
                best_r = cr
                best_z = cz

    if best_r is None:
        raise ValueError(
            f"无法在多边形内部找到满足最小边界距离 {min_margin:.4g} m 的区域种子。"
            f"请检查多边形几何或减小 min_margin。"
        )
    return float(best_r), float(best_z)


# ---------------------------------------------------------------------------
# 壁数据状态判定
# ---------------------------------------------------------------------------

def _check_wall_data(wall_r, wall_z) -> bool:
    """判断壁数据是否可用，返回 True 表示有效壁数据，False 表示无壁数据。

    严格区分三种情况：
        - 二者均为 None 或均为空数组：无可用壁轮廓，返回 False；
        - 二者均存在且有效：返回 True；
        - 其他不一致情况：抛出 ValueError。

    "无可用壁轮廓"只表示 GFile 缺少可用壁几何，不表示物理装置没有第一壁。
    """
    r_none = wall_r is None
    z_none = wall_z is None
    r_empty = (not r_none) and (len(wall_r) == 0)
    z_empty = (not z_none) and (len(wall_z) == 0)

    # 二者均为 None
    if r_none and z_none:
        return False
    # 二者均为空数组
    if r_empty and z_empty:
        return False
    # 一个为 None 另一个不为 None
    if r_none != z_none:
        raise ValueError(
            "壁数据不一致：wall_r 和 wall_z 中只有一个为 None。"
            "请检查 GFile 读取结果。"
        )
    # 一个为空另一个不为空
    if r_empty != z_empty:
        raise ValueError(
            "壁数据不一致：wall_r 和 wall_z 中只有一个为空数组。"
            "请检查 GFile 读取结果。"
        )
    # 长度不一致
    if len(wall_r) != len(wall_z):
        raise ValueError(
            f"壁数据长度不一致：wall_r 有 {len(wall_r)} 个点，"
            f"wall_z 有 {len(wall_z)} 个点。"
        )
    # 含非有限值
    if not (np.all(np.isfinite(wall_r)) and np.all(np.isfinite(wall_z))):
        raise ValueError("壁数据含 NaN 或 Inf，无法使用。")
    # 有效点不足（去掉重复末尾后至少需要 3 点）
    wr, wz = _strip_closed_duplicate(
        np.asarray(wall_r, dtype=np.float64),
        np.asarray(wall_z, dtype=np.float64),
    )
    if len(wr) < 3:
        raise ValueError(
            f"壁数据有效点不足（去重后 {len(wr)} < 3），无法构成有效闭合曲线。"
        )
    return True


# ---------------------------------------------------------------------------
# 核心边界构造函数
# ---------------------------------------------------------------------------

def _build_boundary_config(
    gfile_data: "object",
    args: argparse.Namespace,
) -> "object":
    """从 GFileData 构造 BoundaryConfig，作为 Triangle 唯一底座的输入。

    本函数是 M2 里程碑的核心胶水代码，负责将 GFileData 中的 LCFS 边界坐标
    转换为 Triangle 所需的分段线性复合体（PLC）描述格式。

    区域方案（由输入是否提供有效壁轮廓动态决定）：
        含有效第一壁轮廓（三区域方案）：
            region_id=1：plasma（LCFS 内部）
            region_id=2：vacuum（LCFS 外且第一壁内）
            region_id=3：P0 等效 outer/wall-conductor 计算区域（第一壁外且人工 outer boundary 内）
                         注意：区域 3 只是 P0 等效计算区域，不代表真实导体厚度、材料、线圈或电路。
        无可用第一壁轮廓（两区域降级方案）：
            region_id=1：plasma（LCFS 内部）
            region_id=2：vacuum（LCFS 外且人工 outer boundary 内）
            "无可用壁轮廓"只表示 GFile 缺少可用壁几何，不表示物理装置没有第一壁。

    边界标记约定：
        boundary_marker=1：LCFS（最后闭合磁面，plasma-vacuum interface）
        boundary_marker=2：第一壁内表面（仅含壁方案，vacuum 与区域 3 的界面）
        boundary_marker=3：人工 outer boundary（LinkMesh 构造的数值截断边界）

    所有区域种子均经过确定性的点在闭合多边形内外关系检查和边界距离验证。
    若边界不闭合、退化、自交、不满足嵌套关系或无法找到合法种子，抛出 ValueError。

    参数：
        gfile_data: GFileData 对象（来自 read_gfile()）
        args:       CLI 参数（含 min_angle, max_area）

    返回：
        BoundaryConfig 对象，可直接传入 generate_mesh()
    """
    from linkmesh.mesher.triangle_wrapper import BoundaryConfig

    # ------------------------------------------------------------------ #
    # Step A：LCFS 点集重采样与验证                                        #
    # ------------------------------------------------------------------ #
    lcfs_r_raw = np.asarray(gfile_data.lcfs_r, dtype=np.float64)
    lcfs_z_raw = np.asarray(gfile_data.lcfs_z, dtype=np.float64)

    n_lcfs_target = max(40, min(200, len(lcfs_r_raw)))
    lcfs_r_rs, lcfs_z_rs = _resample_closed_curve(lcfs_r_raw, lcfs_z_raw, n_lcfs_target)
    # 去掉重复末尾点，用于几何计算和 Triangle 输入
    lcfs_r, lcfs_z = _strip_closed_duplicate(lcfs_r_rs, lcfs_z_rs)

    # 验证 LCFS 有效性
    _check_curve_valid(lcfs_r, lcfs_z, "LCFS")

    # ------------------------------------------------------------------ #
    # Step B：判断壁数据状态                                               #
    # ------------------------------------------------------------------ #
    has_wall = _check_wall_data(
        getattr(gfile_data, "wall_r", None),
        getattr(gfile_data, "wall_z", None),
    )

    # ------------------------------------------------------------------ #
    # Step C：若有壁数据，重采样并验证第一壁                               #
    # ------------------------------------------------------------------ #
    wall_r = None
    wall_z = None
    if has_wall:
        wall_r_raw = np.asarray(gfile_data.wall_r, dtype=np.float64)
        wall_z_raw = np.asarray(gfile_data.wall_z, dtype=np.float64)
        n_wall_target = max(20, min(150, len(wall_r_raw)))
        wall_r_rs, wall_z_rs = _resample_closed_curve(wall_r_raw, wall_z_raw, n_wall_target)
        wall_r, wall_z = _strip_closed_duplicate(wall_r_rs, wall_z_rs)
        _check_curve_valid(wall_r, wall_z, "第一壁")

    # ------------------------------------------------------------------ #
    # Step D：构造人工 outer boundary 矩形                                 #
    # ------------------------------------------------------------------ #
    pad_r = 0.15
    pad_z = 0.15

    r_min_lcfs = np.min(lcfs_r)
    r_max_lcfs = np.max(lcfs_r)
    z_min_lcfs = np.min(lcfs_z)
    z_max_lcfs = np.max(lcfs_z)
    dr = r_max_lcfs - r_min_lcfs
    dz = z_max_lcfs - z_min_lcfs

    if has_wall:
        r_min_outer = min(r_min_lcfs - pad_r * dr, np.min(wall_r) - 0.05)
        r_max_outer = max(r_max_lcfs + pad_r * dr, np.max(wall_r) + 0.05)
        z_min_outer = min(z_min_lcfs - pad_z * dz, np.min(wall_z) - 0.05)
        z_max_outer = max(z_max_lcfs + pad_z * dz, np.max(wall_z) + 0.05)
    else:
        r_min_outer = r_min_lcfs - pad_r * dr
        r_max_outer = r_max_lcfs + pad_r * dr
        z_min_outer = z_min_lcfs - pad_z * dz
        z_max_outer = z_max_lcfs + pad_z * dz

    # 外边界矩形顶点（逆时针：左下→右下→右上→左上）
    outer_r = np.array([r_min_outer, r_max_outer, r_max_outer, r_min_outer], dtype=np.float64)
    outer_z = np.array([z_min_outer, z_min_outer, z_max_outer, z_max_outer], dtype=np.float64)
    n_outer = 4

    # ------------------------------------------------------------------ #
    # Step E：嵌套关系与相交检查                                           #
    # ------------------------------------------------------------------ #
    # 计算合理的浮点容差（基于 LCFS 尺度）
    lcfs_scale = max(dr, dz, 0.01)
    margin = lcfs_scale * 1e-6  # 用于点在多边形内外判断的最小边界距离

    # 验证 LCFS 严格位于 outer boundary 内
    # 检查 LCFS 所有顶点均在 outer boundary 内
    for i in range(len(lcfs_r)):
        if not _point_in_polygon(lcfs_r[i], lcfs_z[i], outer_r, outer_z):
            raise ValueError(
                f"LCFS 顶点 ({lcfs_r[i]:.4f}, {lcfs_z[i]:.4f}) 不在人工 outer boundary 内，"
                f"请检查 outer boundary 构造逻辑。"
            )

    if has_wall:
        # 验证 LCFS 严格位于第一壁内（检查 LCFS 所有顶点）
        for i in range(len(lcfs_r)):
            if not _point_in_polygon(lcfs_r[i], lcfs_z[i], wall_r, wall_z):
                raise ValueError(
                    f"LCFS 顶点 ({lcfs_r[i]:.4f}, {lcfs_z[i]:.4f}) 不在第一壁内，"
                    f"不满足 LCFS ⊂ 第一壁 的嵌套关系。"
                )
        # 验证第一壁严格位于 outer boundary 内（检查第一壁所有顶点）
        for i in range(len(wall_r)):
            if not _point_in_polygon(wall_r[i], wall_z[i], outer_r, outer_z):
                raise ValueError(
                    f"第一壁顶点 ({wall_r[i]:.4f}, {wall_z[i]:.4f}) 不在人工 outer boundary 内，"
                    f"不满足 第一壁 ⊂ outer boundary 的嵌套关系。"
                )
        # 验证 LCFS 与第一壁不相交
        if _polygons_intersect(lcfs_r, lcfs_z, wall_r, wall_z):
            raise ValueError("LCFS 与第一壁存在线段相交，不满足嵌套关系。")
        # 验证第一壁与 outer boundary 不相交
        if _polygons_intersect(wall_r, wall_z, outer_r, outer_z):
            raise ValueError("第一壁与人工 outer boundary 存在线段相交，不满足嵌套关系。")
    else:
        # 无壁方案：验证 LCFS 与 outer boundary 不相交
        if _polygons_intersect(lcfs_r, lcfs_z, outer_r, outer_z):
            raise ValueError("LCFS 与人工 outer boundary 存在线段相交，不满足嵌套关系。")

    # ------------------------------------------------------------------ #
    # Step F：验证 plasma seed（磁轴）                                     #
    # ------------------------------------------------------------------ #
    plasma_seed_r = float(gfile_data.rmaxis)
    plasma_seed_z = float(gfile_data.zmaxis)

    if not (np.isfinite(plasma_seed_r) and np.isfinite(plasma_seed_z)):
        raise ValueError(
            f"磁轴坐标含非有限值：rmaxis={plasma_seed_r}, zmaxis={plasma_seed_z}。"
        )
    if not _point_in_polygon(plasma_seed_r, plasma_seed_z, lcfs_r, lcfs_z):
        raise ValueError(
            f"磁轴 ({plasma_seed_r:.4f}, {plasma_seed_z:.4f}) 不在 LCFS 内部，"
            f"无法作为 plasma 区域种子。请检查 GFile 数据。"
        )
    # 验证磁轴不在 LCFS 边界上（到边界距离必须大于 margin）
    d_plasma_to_lcfs = _point_min_dist_to_polygon(plasma_seed_r, plasma_seed_z, lcfs_r, lcfs_z)
    if d_plasma_to_lcfs < margin:
        raise ValueError(
            f"磁轴 ({plasma_seed_r:.4f}, {plasma_seed_z:.4f}) 过于接近 LCFS 边界"
            f"（距离 {d_plasma_to_lcfs:.4g} m < {margin:.4g} m），无法作为可靠的 plasma 种子。"
        )

    # ------------------------------------------------------------------ #
    # Step G：确定性搜索 vacuum seed 和（含壁时）region 3 seed             #
    # ------------------------------------------------------------------ #
    # 搜索用的最小边界距离：取 LCFS 尺度的 0.5%，但不小于 1e-4 m
    search_margin = max(lcfs_scale * 0.005, 1e-4)

    if has_wall:
        # vacuum seed：严格位于 LCFS 外且第一壁内
        vacuum_seed_r, vacuum_seed_z = _find_seed_in_annulus(
            inner_r=lcfs_r, inner_z=lcfs_z,
            outer_r=wall_r, outer_z=wall_z,
            min_margin=search_margin,
        )
        # region 3 seed：严格位于第一壁外且 outer boundary 内
        region3_seed_r, region3_seed_z = _find_seed_in_annulus(
            inner_r=wall_r, inner_z=wall_z,
            outer_r=outer_r, outer_z=outer_z,
            min_margin=search_margin,
        )
        regions = np.array([
            [plasma_seed_r,  plasma_seed_z,  1.0, -1.0],
            [vacuum_seed_r,  vacuum_seed_z,  2.0, -1.0],
            [region3_seed_r, region3_seed_z, 3.0, -1.0],
        ], dtype=np.float64)
    else:
        # vacuum seed：严格位于 LCFS 外且 outer boundary 内
        vacuum_seed_r, vacuum_seed_z = _find_seed_in_annulus(
            inner_r=lcfs_r, inner_z=lcfs_z,
            outer_r=outer_r, outer_z=outer_z,
            min_margin=search_margin,
        )
        regions = np.array([
            [plasma_seed_r, plasma_seed_z, 1.0, -1.0],
            [vacuum_seed_r, vacuum_seed_z, 2.0, -1.0],
        ], dtype=np.float64)

    # ------------------------------------------------------------------ #
    # Step H：组装顶点列表与线段连接表                                      #
    # ------------------------------------------------------------------ #
    n_lcfs = len(lcfs_r)

    vertices_list = [
        np.column_stack([lcfs_r, lcfs_z]),  # LCFS 顶点
        np.column_stack([outer_r, outer_z]),  # outer boundary 顶点
    ]
    segments_list = []
    seg_markers_list = []

    # LCFS 线段（闭合环，boundary_marker=1）
    lcfs_segs = np.column_stack([
        np.arange(n_lcfs, dtype=np.int32),
        np.roll(np.arange(n_lcfs, dtype=np.int32), -1),
    ])
    segments_list.append(lcfs_segs)
    seg_markers_list.append(np.ones(n_lcfs, dtype=np.int32))

    # outer boundary 线段（闭合环，boundary_marker=3）
    outer_base = n_lcfs
    outer_segs = np.column_stack([
        outer_base + np.arange(n_outer, dtype=np.int32),
        outer_base + np.roll(np.arange(n_outer, dtype=np.int32), -1),
    ])
    segments_list.append(outer_segs)
    seg_markers_list.append(3 * np.ones(n_outer, dtype=np.int32))

    # 第一壁线段（含壁方案，boundary_marker=2）
    if has_wall:
        n_wall = len(wall_r)
        vertices_list.append(np.column_stack([wall_r, wall_z]))
        wall_base = n_lcfs + n_outer
        wall_segs = np.column_stack([
            wall_base + np.arange(n_wall, dtype=np.int32),
            wall_base + np.roll(np.arange(n_wall, dtype=np.int32), -1),
        ])
        segments_list.append(wall_segs)
        seg_markers_list.append(2 * np.ones(n_wall, dtype=np.int32))

    vertices = np.vstack(vertices_list).astype(np.float64)
    segments = np.vstack(segments_list).astype(np.int32)
    segment_markers = np.concatenate(seg_markers_list).astype(np.int32)

    # ------------------------------------------------------------------ #
    # Step I：封装为 BoundaryConfig                                        #
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

    使用线性插值，适用于 LCFS 和第一壁的重采样。
    输入曲线应已闭合（首尾点相同或相近）。

    参数：
        r:        R 坐标数组
        z:        Z 坐标数组
        n_target: 目标点数（含末尾重复点）

    返回：
        (r_new, z_new)：重采样后的坐标数组，shape=(n_target,)
    """
    r = np.asarray(r, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    # 确保首尾闭合
    if not (np.isclose(r[0], r[-1]) and np.isclose(z[0], z[-1])):
        r = np.append(r, r[0])
        z = np.append(z, z[0])

    ds = np.sqrt(np.diff(r) ** 2 + np.diff(z) ** 2)
    s = np.concatenate([[0.0], np.cumsum(ds)])
    s_total = s[-1]

    if s_total < 1e-14:
        return r, z

    s_new = np.linspace(0.0, s_total, n_target)
    r_new = np.interp(s_new, s, r)
    z_new = np.interp(s_new, s, z)
    return r_new, z_new


if __name__ == "__main__":
    main()
