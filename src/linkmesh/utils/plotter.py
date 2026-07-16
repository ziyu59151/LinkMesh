"""
plotter.py —— matplotlib 可视化自检工具。

职责：
    - 绘制 LCFS 边界与生成三角网格的叠加图
    - 输出 .png 自检图，供人眼快速判断网格质量

禁止事项：
    - 不得修改任何数据对象（GFileData、Mesh2D）

参考规范：
    LinkMesh_Architecture_Plan.md 第 10 节
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from linkmesh.readers.gfile_reader import GFileData
    from linkmesh.mesher.triangle_wrapper import Mesh2D


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
        show_boundary_markers: 是否用不同颜色标注边界标记类型
        show_region_ids:       是否用不同颜色填充不同区域

    实现要点：
        1. 使用 matplotlib.tri.Triangulation 绘制三角网格
        2. 叠加绘制 LCFS 边界曲线（红色实线）
        3. 若有第一壁数据，叠加绘制第一壁曲线（蓝色虚线）
        4. 标注磁轴位置（红色叉号）
        5. 设置坐标轴标签：xlabel='R [m]', ylabel='Z [m]'
        6. 设置标题：'LinkMesh 网格自检图'
        7. 保持纵横比相等（aspect='equal'）
        8. 保存为 PNG 文件，dpi=150
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
    except ImportError as e:
        raise ImportError(
            "无法导入 matplotlib。请运行：pip install matplotlib"
            f"\n原始错误：{e}"
        ) from e

    fig, ax = plt.subplots(figsize=(6, 8))

    # --- 绘制三角网格 ---
    R = mesh.nodes[:, 0]
    Z = mesh.nodes[:, 1]
    triang = mtri.Triangulation(R, Z, mesh.triangles)

    if show_region_ids and mesh.region_ids is not None and len(mesh.region_ids) > 0:
        # 按区域 ID 着色填充
        unique_regions = sorted(set(mesh.region_ids.tolist()))
        region_colors = {1: "#AED6F1", 2: "#A9DFBF", 3: "#F9E79F"}  # plasma/vacuum/wall
        region_labels = {1: "plasma", 2: "vacuum", 3: "wall"}
        for rid in unique_regions:
            mask = (mesh.region_ids == rid)
            color = region_colors.get(rid, "#D5D8DC")
            label = region_labels.get(rid, f"region {rid}")
            # 用 tripcolor 填充对应区域
            ax.tripcolor(
                triang,
                facecolors=mask.astype(float),
                cmap="Blues",
                alpha=0.3,
            )
        # 叠加网格线
        ax.triplot(triang, color="#555555", linewidth=0.3, alpha=0.6)
    else:
        # 仅绘制网格线
        ax.triplot(triang, color="#555555", linewidth=0.3, alpha=0.8)

    # --- 叠加绘制 LCFS 边界曲线（红色实线）---
    ax.plot(
        gfile_data.lcfs_r,
        gfile_data.lcfs_z,
        color="red",
        linewidth=1.5,
        label="LCFS",
        zorder=3,
    )

    # --- 若有第一壁数据，叠加绘制第一壁曲线（蓝色虚线）---
    if gfile_data.wall_r is not None and gfile_data.wall_z is not None:
        ax.plot(
            gfile_data.wall_r,
            gfile_data.wall_z,
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

    # --- 若 show_boundary_markers，用不同颜色标注边界线段 ---
    if show_boundary_markers and mesh.n_boundary_segments > 0:
        marker_colors = {1: "red", 2: "blue", 3: "green"}
        marker_labels = {1: "LCFS 边界", 2: "第一壁边界", 3: "外边界"}
        plotted_markers: set = set()
        for i in range(mesh.n_boundary_segments):
            seg = mesh.boundary_segments[i]
            marker = int(mesh.boundary_markers[i]) if len(mesh.boundary_markers) > i else 0
            if marker == 0:
                continue
            color = marker_colors.get(marker, "gray")
            label = marker_labels.get(marker, f"边界 {marker}") if marker not in plotted_markers else None
            plotted_markers.add(marker)
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
    ax.legend(loc="upper right", fontsize=8, framealpha=0.8)

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
    """仅绘制 LCFS 边界曲线（M1 里程碑最小可用版本）。

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

    # 绘制 LCFS 边界曲线（红色实线）
    ax.plot(
        gfile_data.lcfs_r,
        gfile_data.lcfs_z,
        color="red",
        linewidth=1.5,
        label="LCFS",
    )

    # 若有第一壁数据，叠加绘制（蓝色虚线）
    if gfile_data.wall_r is not None and gfile_data.wall_z is not None:
        ax.plot(
            gfile_data.wall_r,
            gfile_data.wall_z,
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
