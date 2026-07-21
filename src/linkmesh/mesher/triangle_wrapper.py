"""
triangle_wrapper.py —— TokaMaker/Triangle 唯一底座封装（历史/过渡实现）。

职责：
    - 接收 BoundaryConfig（边界点集与区域配置）
    - 按 TokaMaker 风格构造 alpha 字典（键名：vertices, segments, segment_markers, regions）
    - 调用 triangle Python 包生成二维非结构化三角网格
    - 从 beta 字典提取输出字段（键名：vertices, triangles, triangle_attributes 等）
    - 返回统一内存网格对象 Mesh2D

v1.11 M2.5 解耦说明：
    Mesh2D 的唯一正式定义已迁出本模块到 src/linkmesh/mesh.py。
    本模块不再定义第二份同名数据类，而从 linkmesh.mesh 重新导出同一个类，
    以兼容历史导入：
        from linkmesh.mesher.triangle_wrapper import Mesh2D
    必须保证：
        linkmesh.mesh.Mesh2D is linkmesh.mesher.triangle_wrapper.Mesh2D
    BoundaryConfig 与历史 generate_mesh() 仍保留于本模块，暂不删除。

禁止事项：
    - 不得读取 GFile 或任何文件
    - 不得写文件
    - 不得引入三维网格逻辑
    - 不得引入第二种网格生成引擎
    - 不得在本模块重新定义第二份 Mesh2D

调用风格参考（只读）：
    TOKAMAKER/.../TokaMaker/meshing.py 中 run_triangle 函数与 Mesh.get_mesh 方法
    alpha = dict(vertices=..., segments=..., regions=...)  [TokaMaker 风格]
    beta  = run_triangle(alpha)
    beta['vertices'], beta['triangles'], beta['triangle_attributes']

参考规范：
    LinkMesh_Architecture_Plan.md 第 7 节、第 16.1 节（Mesh2D 解耦）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

# Mesh2D 唯一正式定义位于 linkmesh.mesh；此处重新导出以兼容历史导入。
# 不得在本模块重新定义第二份同名数据类。
from linkmesh.mesh import Mesh2D

__all__ = ["BoundaryConfig", "Mesh2D", "generate_mesh"]


# --------------------------------------------------------------------------- #
# 输入数据结构                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class BoundaryConfig:
    """Triangle 网格生成的输入配置。

    该对象由 cli.py 根据 GFileData 和用户参数构造，
    传递给 mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）。

    字段命名与 TokaMaker OFT meshing.py 中 alpha 字典的键名保持一致：
        alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)
    """

    # 边界点集（分段线性复合体 PLC 的顶点）
    # 对应 TokaMaker alpha 字典的 'vertices' 键
    vertices: np.ndarray          # shape=(N, 2)，所有边界点 [R, Z] 坐标，dtype=float64

    # 边界线段连接表（PLC 的边）
    # 对应 TokaMaker alpha 字典的 'segments' 键
    segments: np.ndarray          # shape=(M, 2)，线段端点索引对，dtype=int32

    # 区域标记点（Triangle regions 输入）
    # 对应 TokaMaker alpha 字典的 'regions' 键
    # 每行格式：[R, Z, region_id, max_area]
    # region_id 约定：1=plasma, 2=vacuum, 3=wall
    regions: np.ndarray           # shape=(K, 4)，dtype=float64

    # 边界标记（对应 segments 的整数标记，与 segments 逐项对应）
    # 对应 TokaMaker alpha 字典的 'segment_markers' 键
    # 标记约定：1=LCFS, 2=first_wall, 3=outer_boundary
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: Optional[float] = None  # 全局最大三角形面积约束（m²），None 表示不限制


# --------------------------------------------------------------------------- #
# 公开接口                                                                      #
# --------------------------------------------------------------------------- #

def generate_mesh(config: BoundaryConfig) -> Mesh2D:
    """调用 Triangle（TokaMaker/Triangle 唯一底座）生成二维非结构化三角网格。

    调用风格严格对齐 TokaMaker OFT meshing.py 的 run_triangle / Mesh.get_mesh：
        alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)
        beta  = tr.triangulate(alpha, opts)
        提取 beta['vertices'], beta['triangles'], beta['triangle_attributes'] 等

    参数：
        config: BoundaryConfig 对象，包含边界点、线段、区域标记和质量参数

    返回：
        Mesh2D 对象，包含节点坐标、三角形连接表、区域标记和边界标记

    异常：
        ImportError: triangle 包未安装
        ValueError: Triangle 生成失败（节点数或三角形数为 0）
    """
    try:
        import triangle as tr
    except ImportError as e:
        raise ImportError(
            "无法导入 triangle 包。请运行：pip install triangle"
            f"\n原始错误：{e}"
        ) from e

    # Step 1：按 TokaMaker 风格构造 alpha 字典
    # 参考：meshing.py:1077 alpha = dict(vertices=..., segments=..., regions=...)
    alpha = {
        "vertices":        np.ascontiguousarray(config.vertices, dtype=np.float64),
        "segments":        np.ascontiguousarray(config.segments, dtype=np.int32),
        "segment_markers": np.ascontiguousarray(config.segment_markers, dtype=np.int32),
        "regions":         np.ascontiguousarray(config.regions, dtype=np.float64),
    }

    # Step 2：生成 Triangle 控制字符串
    # 参考：meshing.py:74 setting_string = c_char_p(b'pqaAzQ')
    opts = _build_triangle_opts(config)

    # Step 3：调用 tr.triangulate，得到 beta 字典
    # 参考：meshing.py:1078 beta = run_triangle(alpha)
    beta = tr.triangulate(alpha, opts)

    # Step 4：验证输出合法性
    if len(beta.get("vertices", [])) == 0:
        raise ValueError("Triangle 生成失败：输出节点数为 0。请检查 BoundaryConfig 输入。")
    if len(beta.get("triangles", [])) == 0:
        raise ValueError("Triangle 生成失败：输出三角形数为 0。请检查 BoundaryConfig 输入。")

    # Step 5：从 beta 字典提取各字段，构造 Mesh2D 对象
    # 字段对应关系（参考 meshing.py:78-81 与 TokaMaker run_triangle 返回值）：
    #   beta['vertices']            → nodes
    #   beta['triangles']           → triangles
    #   beta['triangle_attributes'] → region_ids
    #   beta['segments']            → boundary_segments
    #   beta['segment_markers']     → boundary_markers
    #   beta['vertex_markers']      → node_markers
    #
    # 一维 shape 契约（v1.5）：使用 reshape(-1) 而非 squeeze()，
    # 保证即使 T==1、S==1 或 N==1 时仍得到一维数组，而非零维数组。
    nodes = beta["vertices"].astype(np.float64)
    triangles = beta["triangles"].astype(np.int32)
    region_ids = np.asarray(beta["triangle_attributes"], dtype=np.int32).reshape(-1)

    # boundary_segments / boundary_markers / node_markers：
    # Python triangle 包在使用 'p' 标志时会输出这些字段
    boundary_segments = np.asarray(
        beta.get("segments", np.zeros((0, 2), dtype=np.int32)),
        dtype=np.int32,
    )

    boundary_markers = np.asarray(
        beta.get("segment_markers", np.zeros((0,), dtype=np.int32)),
        dtype=np.int32,
    ).reshape(-1)

    node_markers = np.asarray(
        beta.get("vertex_markers", np.zeros((nodes.shape[0],), dtype=np.int32)),
        dtype=np.int32,
    ).reshape(-1)

    mesh = Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=boundary_segments,
        boundary_markers=boundary_markers,
        node_markers=node_markers,
    )

    # Step 6：打印统计信息（参考 meshing.py:1080-1082）
    print(f"  节点数: {mesh.n_nodes}")
    print(f"  三角形数: {mesh.n_triangles}")
    print(f"  边界线段数: {mesh.n_boundary_segments}")

    return mesh


# --------------------------------------------------------------------------- #
# 内部辅助函数                                                                  #
# --------------------------------------------------------------------------- #

def _build_triangle_opts(config: BoundaryConfig) -> str:
    """构造 Triangle 控制字符串。

    控制字符含义（参考 TokaMaker meshing.py 中 run_triangle 使用的 b'pqaAzQ'）：
        p  - 使用分段线性复合体（PLC）输入模式
        q  - 质量网格生成（最小角约束）
        a  - 面积约束（小写，仅当 max_area 不为 None 时加入）
        A  - 将区域属性写入三角形（生成 triangle_attributes，大写）
        z  - 节点索引从 0 开始（Python 友好，保证 Mesh2D 中所有索引为 0-based）
        Q  - 静默模式（不打印 Triangle 内部日志）

    示例：
        min_angle=20, max_area=0.001 → "pq20.0a0.001AzQ"
        min_angle=20, max_area=None  → "pq20.0AzQ"

    参数：
        config: BoundaryConfig 对象

    返回：
        Triangle 控制字符串
    """
    opts = "p"
    opts += f"q{config.min_angle:.1f}"
    if config.max_area is not None:
        opts += f"a{config.max_area:.6g}"
    opts += "AzQ"
    return opts
