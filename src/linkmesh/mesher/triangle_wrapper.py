"""
triangle_wrapper.py —— TokaMaker/Triangle 唯一底座封装。

职责：
    - 接收 BoundaryConfig（边界点集与区域配置）
    - 按 TokaMaker 风格构造 alpha 字典（键名：vertices, segments, regions）
    - 调用 triangle Python 包生成二维非结构化三角网格
    - 从 beta 字典提取输出字段（键名：vertices, triangles, triangle_attributes 等）
    - 返回统一内存网格对象 Mesh2D

禁止事项：
    - 不得读取 GFile 或任何文件
    - 不得写文件
    - 不得引入三维网格逻辑
    - 不得引入第二种网格生成引擎

调用风格参考（只读）：
    TOKAMAKER/.../TokaMaker/meshing.py 中 run_triangle 函数与 Mesh.get_mesh 方法
    alpha = dict(vertices=..., segments=..., regions=...)  [TokaMaker 风格]
    beta  = run_triangle(alpha)
    beta['vertices'], beta['triangles'], beta['triangle_attributes']

参考规范：
    LinkMesh_Architecture_Plan.md 第 7 节
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# --------------------------------------------------------------------------- #
# 输入数据结构                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class BoundaryConfig:
    """Triangle 网格生成的输入配置。

    该对象由 cli.py 根据 GFileData 和用户参数构造，
    传递给 mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）。

    字段命名与 TokaMaker OFT meshing.py 中 alpha 字典的键名保持一致：
        alpha = dict(vertices=..., segments=..., regions=...)
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

    # 边界标记（对应 segments 的整数标记）
    # 标记约定：1=LCFS, 2=first_wall, 3=outer_boundary
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: Optional[float] = None  # 全局最大三角形面积约束（m²），None 表示不限制


# --------------------------------------------------------------------------- #
# 输出数据结构                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class Mesh2D:
    """LinkMesh 核心内存网格对象。

    该对象是 mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）的输出，
    同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py 的共同输入。
    所有索引均从 0 开始（Python 约定，由 Triangle 'z' 控制字符保证）。
    写出时各 writer 负责按目标格式约定进行索引转换。

    字段来源（对应 TokaMaker run_triangle / tr.triangulate 返回字典键名）：
        nodes             ← beta['vertices']
        triangles         ← beta['triangles']
        region_ids        ← beta['triangle_attributes'].squeeze().astype(int32)
        boundary_segments ← beta['segments']
        boundary_markers  ← beta['segment_markers'].squeeze()
        node_markers      ← beta['vertex_markers'].squeeze()
    """

    # 节点坐标
    # 来源：beta['vertices']，shape=(N, 2)
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64

    # 三角形连接表（三角形顶点索引，逆时针方向）
    # 来源：beta['triangles']，shape=(T, 3)
    # 索引为 0-based（Triangle 'z' 标志保证）
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，dtype=int32

    # 三角形区域标记（来自 Triangle triangleattributelist / beta['triangle_attributes']）
    # 约定：1=plasma, 2=vacuum, 3=wall
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，dtype=int32

    # 边界线段连接表
    # 来源：beta['segments']，shape=(S, 2)
    # 索引为 0-based（Triangle 'z' 标志保证）
    boundary_segments: np.ndarray    # shape=(S, 2)，边界线段端点节点索引，dtype=int32

    # 边界线段标记（来自 Triangle segmentmarkerlist / beta['segment_markers']）
    # 约定：1=LCFS, 2=first_wall, 3=outer_boundary
    boundary_markers: np.ndarray     # shape=(S,)，每条边界线段的标记，dtype=int32

    # 节点边界标记（来自 Triangle pointmarkerlist / beta['vertex_markers']）
    # 0=内部节点，非零=边界节点
    node_markers: np.ndarray         # shape=(N,)，每个节点的边界标记，dtype=int32

    @property
    def n_nodes(self) -> int:
        """节点总数。"""
        return self.nodes.shape[0]

    @property
    def n_triangles(self) -> int:
        """三角形总数。"""
        return self.triangles.shape[0]

    @property
    def n_boundary_segments(self) -> int:
        """边界线段总数。"""
        return self.boundary_segments.shape[0]


# --------------------------------------------------------------------------- #
# 公开接口                                                                      #
# --------------------------------------------------------------------------- #

def generate_mesh(config: BoundaryConfig) -> Mesh2D:
    """调用 Triangle（TokaMaker/Triangle 唯一底座）生成二维非结构化三角网格。

    调用风格严格对齐 TokaMaker OFT meshing.py 的 run_triangle / Mesh.get_mesh：
        alpha = dict(vertices=..., segments=..., regions=...)
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
    nodes = beta["vertices"].astype(np.float64)
    triangles = beta["triangles"].astype(np.int32)
    region_ids = beta["triangle_attributes"].squeeze().astype(np.int32)

    # boundary_segments / boundary_markers / node_markers：
    # Python triangle 包在使用 'p' 标志时会输出这些字段
    boundary_segments = beta.get("segments", np.zeros((0, 2), dtype=np.int32))
    boundary_segments = np.asarray(boundary_segments, dtype=np.int32)

    raw_seg_markers = beta.get("segment_markers", np.zeros((0,), dtype=np.int32))
    boundary_markers = np.asarray(raw_seg_markers, dtype=np.int32).squeeze()

    raw_vtx_markers = beta.get("vertex_markers", np.zeros((nodes.shape[0],), dtype=np.int32))
    node_markers = np.asarray(raw_vtx_markers, dtype=np.int32).squeeze()

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
        a  - 面积约束
        A  - 将区域属性写入三角形（生成 triangle_attributes）
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
