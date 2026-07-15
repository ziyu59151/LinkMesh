"""
plotter.py —— matplotlib 可视化自检工具。

职责：
    - 绘制 LCFS 边界与生成三角网格的叠加图
    - 输出 .png 自检图，供人眼快速判断网格质量

禁止事项：
    - 不得修改任何数据对象（GFileData、Mesh2D）

参考规范：
    LinkMesh_Architecture_Plan.md 第 10 节

# TODO: 待在 M1~M2 里程碑阶段结合真实数据实测，进行绘图细节的最终对齐
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
        gfile_data: GFileData 对象，提供 LCFS 和磁轴坐标
        mesh: Mesh2D 对象，提供三角网格数据
        filepath: 输出 .png 文件路径
        show_boundary_markers: 是否用不同颜色标注边界标记类型
        show_region_ids: 是否用不同颜色填充不同区域

    实现要点（待 M1~M2 里程碑实现）：
        1. 使用 matplotlib.tri.Triangulation 绘制三角网格
        2. 叠加绘制 LCFS 边界曲线（红色实线）
        3. 若有第一壁数据，叠加绘制第一壁曲线（蓝色虚线）
        4. 标注磁轴位置（红色叉号）
        5. 设置坐标轴标签：xlabel='R [m]', ylabel='Z [m]'
        6. 设置标题：'LinkMesh 网格自检图'
        7. 保持纵横比相等（aspect='equal'）
        8. 保存为 PNG 文件，dpi=150

    # TODO: 待在 M1~M2 里程碑阶段结合真实数据实测，进行绘图细节的最终对齐
    """
    raise NotImplementedError(
        "plot_mesh() 将在 M1~M2 里程碑阶段实现。"
        "请参考 LinkMesh_Architecture_Plan.md 第 10 节。"
    )


def plot_lcfs_only(
    gfile_data: "GFileData",
    filepath: str,
) -> None:
    """仅绘制 LCFS 边界曲线（M1 里程碑最小可用版本）。

    参数：
        gfile_data: GFileData 对象，提供 LCFS 和磁轴坐标
        filepath: 输出 .png 文件路径

    实现要点（待 M1 里程碑实现）：
        1. 绘制 LCFS 边界曲线（红色实线）
        2. 标注磁轴位置（红色叉号）
        3. 设置坐标轴标签与标题
        4. 保持纵横比相等，保存为 PNG，dpi=150

    # TODO: 待 M1 里程碑实现
    """
    raise NotImplementedError(
        "该模块逻辑将在对应里程碑阶段结合源码实测验证后实现"
    )
