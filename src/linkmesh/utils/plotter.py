"""
plotter.py —— matplotlib 可视化自检工具。

职责：
    - 绘制 LCFS 边界与生成三角网格的叠加图
    - 输出 .png 自检图，供人眼快速判断网格质量

禁止事项：
    - 不得修改任何数据对象（GFileData、Mesh2D）

v1.9 M2 说明：
    - plot_mesh() 主网格只依赖 mesh.nodes / mesh.triangles；
    - 区域着色只使用实际 mesh.region_ids，不使用固定 {1:plasma,2:vacuum,3:wall} 文本映射；
    - LCFS/第一壁来自 GFileData，绘制时若首尾不同则临时追加首点用于显示闭合（不修改 GFileData）；
    - boundary_segments/boundary_markers 为空时跳过旧边界段绘制。

参考规范：
    LinkMesh_Architecture_Plan.md v1.9 第 11 节
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from linkmesh.readers.gfile_reader import GFileData
    from linkmesh.mesher.triangle_wrapper import Mesh2D


def _closed_for_display(r, z):
    """返回用于显示闭合的坐标副本：若首尾不同则临时追加首点。

    仅用于绘图显示，绝不修改传入的底层数据对象。

    参数：
        r: R 坐标（array-like）
        z: Z 坐标（array-like）

    返回：
        (r_disp, z_disp) numpy 数组副本，保证首尾闭合
    """
    r_arr = np.asarray(r, dtype=np.float64).reshape(-1)
    z_arr = np.asarray(z, dtype=np.float64).reshape(-1)
    if len(r_arr) < 2:
        return r_arr, z_arr
    if not (np.isclose(r_arr[0], r_arr[-1]) and np.isclose(z_arr[0], z_arr[-1])):
        r_arr = np.append(r_arr, r_arr[0])
        z_arr = np.append(z_arr, z_arr[0])
    return r_arr, z_arr


def plot_mesh(
    gfile_data: "GFileData",
    mesh: "Mesh2D",
    filepath: str,
    show_boundary_markers: bool = True,
    show_region_ids: bool = False,
) -> None:
    """绘制 LCFS 边界与生成三角网格的叠加图，输出 PNG 自检图。

    参数：
        gfile_data:            GFileData 对象，提供 LCFS 和磁轴坐标
        mesh:                  Mesh2D 对象，提供三角网格数据
        filepath:              输出 .png 文件路径
        show_boundary_markers: 是否用不同颜色标注边界标记类型（仅当存在边界段时）
        show_region_ids:       是否按实际 region_ids 着色填充

    实现要点（v1.9 M2）：
        1. 使用 matplotlib.tri.Triangulation 绘制三角网格（仅依赖 nodes/triangles）
        2. 区域着色只使用实际 region_ids，标签为 "OFT region <id>"
        3. 叠加绘制 LCFS 边界曲线（红色实线，显示闭合）
        4. 若有第一壁数据，叠加绘制第一壁曲线（蓝色虚线，显示闭合）
        5. 标注磁轴位置（红色叉号）
        6. 保持纵横比相等（aspect='equal'），保存为 PNG，dpi=150
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
        from matplotlib import cm
    except ImportError as e:
        raise ImportError(
            "无法导入 matplotlib。请运行：pip install matplotlib"
            f"\n原始错误：{e}"
        ) from e

    fig, ax = plt.subplots(figsize=(6, 8))

    # --- 绘制三角网格（仅依赖 nodes/triangles）---
    R = mesh.nodes[:, 0]
    Z = mesh.nodes[:, 1]
    triang = mtri.Triangulation(R, Z, mesh.triangles)

    if show_region_ids and mesh.region_ids is not None and len(mesh.region_ids) > 0:
        # 按排序后的实际 region ID 生成通用离散颜色
        unique_regions = sorted(set(int(x) for x in mesh.region_ids.tolist()))
        n_reg = len(unique_regions)
        cmap = cm.get_cmap("tab10", max(n_reg, 1))
        id_to_color = {rid: cmap(i) for i, rid in enumerate(unique_regions)}

        # 每个三角形按其 region ID 上色（facecolors 使用 region 索引映射）
        reg_index = np.array(
            [unique_regions.index(int(r)) for r in mesh.region_ids],
            dtype=np.float64,
        )
        ax.tripcolor(
            triang,
            facecolors=reg_index,
            cmap=cmap,
            alpha=0.35,
            edgecolors="none",
        )
        # 图例代理（通用 OFT region 标签）
        from matplotlib.patches import Patch
        legend_handles = [
            Patch(facecolor=id_to_color[rid], alpha=0.35, label=f"OFT region {rid}")
            for rid in unique_regions
        ]
        # 叠加网格线
        ax.triplot(triang, color="#555555", linewidth=0.3, alpha=0.6)
    else:
        legend_handles = []
        # 仅绘制网格线
        ax.triplot(triang, color="#555555", linewidth=0.3, alpha=0.8)

    # --- 叠加绘制 LCFS 边界曲线（红色实线，显示闭合）---
    lcfs_r_disp, lcfs_z_disp = _closed_for_display(gfile_data.lcfs_r, gfile_data.lcfs_z)
    ax.plot(
        lcfs_r_disp,
        lcfs_z_disp,
        color="red",
        linewidth=1.5,
        label="LCFS",
        zorder=3,
    )

    # --- 若有第一壁数据，叠加绘制第一壁曲线（蓝色虚线，显示闭合）---
    if gfile_data.wall_r is not None and gfile_data.wall_z is not None:
        wall_r_disp, wall_z_disp = _closed_for_display(gfile_data.wall_r, gfile_data.wall_z)
        ax.plot(
            wall_r_disp,
            wall_z_disp,
            color="blue",
            linewidth=1.2,
            linestyle="--",
            label="第一壁",
            zorder=3,
        )

    # --- 标注磁轴位置（红色叉号）---
    ax.plot(
        gfile_data.rmaxis,
        gfile_data.zmaxis,
        marker="x",
        color="red",
        markersize=8,
        markeredgewidth=2,
        label=f"磁轴 ({gfile_data.rmaxis:.3f}, {gfile_data.zmaxis:.3f})",
        zorder=4,
    )

    # --- 旧边界段绘制：仅当 boundary_segments/boundary_markers 非空时 ---
    has_boundary = (
        show_boundary_markers
        and mesh.boundary_segments is not None
        and mesh.boundary_markers is not None
        and mesh.n_boundary_segments > 0
        and len(mesh.boundary_markers) > 0
    )
    if has_boundary:
        # 通用着色：按实际 marker 值分配颜色，不使用固定语义文本
        unique_markers = sorted(set(int(m) for m in mesh.boundary_markers.tolist()))
        from matplotlib import cm as _cm
        mcmap = _cm.get_cmap("Set1", max(len(unique_markers), 1))
        marker_to_color = {mk: mcmap(i) for i, mk in enumerate(unique_markers)}
        plotted: set = set()
        for i in range(mesh.n_boundary_segments):
            seg = mesh.boundary_segments[i]
            marker = int(mesh.boundary_markers[i]) if len(mesh.boundary_markers) > i else 0
            if marker == 0:
                continue
            color = marker_to_color.get(marker, "gray")
            label = f"边界 marker {marker}" if marker not in plotted else None
            plotted.add(marker)
            p0 = mesh.nodes[seg[0]]
            p1 = mesh.nodes[seg[1]]
            ax.plot(
                [p0[0], p1[0]],
                [p0[1], p1[1]],
                color=color,
                linewidth=1.0,
                label=label,
                zorder=2,
            )

    # --- 格式设置 ---
    ax.set_xlabel("R [m]", fontsize=11)
    ax.set_ylabel("Z [m]", fontsize=11)
    ax.set_title("LinkMesh 网格自检图", fontsize=13)
    ax.set_aspect("equal")

    # 合并图例（区域填充代理 + 曲线/磁轴自动图例）
    handles, labels = ax.get_legend_handles_labels()
    if legend_handles:
        handles = list(handles) + legend_handles
        labels = list(labels) + [h.get_label() for h in legend_handles]
    if handles:
        ax.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.8)

    # --- 统计信息文本框 ---
    info_text = (
        f"节点数: {mesh.n_nodes}\n"
        f"三角形数: {mesh.n_triangles}\n"
        f"边界线段数: {mesh.n_boundary_segments}"
    )
    ax.text(
        0.02, 0.02, info_text,
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
    )

    fig.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"自检图已保存：{filepath}")


def plot_lcfs_only(
    gfile_data: "GFileData",
    filepath: str,
) -> None:
    """仅绘制 LCFS 边界曲线（M1 里程碑最小可用版本，历史保留）。

    参数：
        gfile_data: GFileData 对象，提供 LCFS 和磁轴坐标
        filepath:   输出 .png 文件路径
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "无法导入 matplotlib。请运行：pip install matplotlib"
            f"\n原始错误：{e}"
        ) from e

    fig, ax = plt.subplots(figsize=(6, 8))

    # 绘制 LCFS 边界曲线（红色实线，显示闭合）
    lcfs_r_disp, lcfs_z_disp = _closed_for_display(gfile_data.lcfs_r, gfile_data.lcfs_z)
    ax.plot(
        lcfs_r_disp,
        lcfs_z_disp,
        color="red",
        linewidth=1.5,
        label="LCFS",
    )

    # 若有第一壁数据，叠加绘制（蓝色虚线，显示闭合）
    if gfile_data.wall_r is not None and gfile_data.wall_z is not None:
        wall_r_disp, wall_z_disp = _closed_for_display(gfile_data.wall_r, gfile_data.wall_z)
        ax.plot(
            wall_r_disp,
            wall_z_disp,
            color="blue",
            linewidth=1.2,
            linestyle="--",
            label="第一壁",
        )

    # 标注磁轴位置（红色叉号）
    ax.plot(
        gfile_data.rmaxis,
        gfile_data.zmaxis,
        marker="x",
        color="red",
        markersize=8,
        markeredgewidth=2,
        label=f"磁轴 ({gfile_data.rmaxis:.3f}, {gfile_data.zmaxis:.3f})",
    )

    ax.set_xlabel("R [m]", fontsize=11)
    ax.set_ylabel("Z [m]", fontsize=11)
    ax.set_title("LinkMesh LCFS 边界自检图", fontsize=13)
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=9)

    # 统计信息
    info_text = (
        f"LCFS 点数: {len(gfile_data.lcfs_r)}\n"
        f"磁轴: R={gfile_data.rmaxis:.4f} m, Z={gfile_data.zmaxis:.4f} m"
    )
    ax.text(
        0.02, 0.02, info_text,
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
    )

    fig.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"LCFS 自检图已保存：{filepath}")
    print(f"LCFS 点数: {len(gfile_data.lcfs_r)}，磁轴: (R={gfile_data.rmaxis:.4f}, Z={gfile_data.zmaxis:.4f})")
