"""
triangle_wrapper.py —— TokaMaker/Triangle 唯一底座封装。

职责：
    - 接收 BoundaryConfig（边界点集与区域配置）
    - 按 TokaMaker 风格构造 alpha 字典（键名：vertices, segments, segment_markers, regions）
    - 调用 triangle Python 包生成二维非结构化三角网格
    - 从 beta 字典提取输出字段（键名：vertices, triangles, triangle_attributes 等）
    - 验证输出区域集合与配置区域集合完全一致（不写死区域数量）
    - 返回统一内存网格对象 Mesh2D

禁止事项：
    - 不得读取 GFile 或任何文件
    - 不得写文件
    - 不得引入三维网格逻辑
    - 不得引入第二种网格生成引擎
    - 不得写死区域数量（不得假设区域数为 2 或 3）
    - 不得推断区域物理含义

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
    传递给 mesher/triangle_wrapper.py（Python triangle 包唯一底座）。

    字段命名与 TokaMaker OFT meshing.py 中 alpha 字典的键名保持一致：
        alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)

    区域数量不在本类中写死，由 cli.py 的 _build_boundary_config() 根据输入动态决定。
    """

    # 边界点集（分段线性复合体 PLC 的顶点）
    # 对应 Triangle alpha 字典的 'vertices' 键
    vertices: np.ndarray          # shape=(N, 2)，所有边界点 [R, Z] 坐标，dtype=float64

    # 边界线段连接表（PLC 的边）
    # 对应 Triangle alpha 字典的 'segments' 键
    segments: np.ndarray          # shape=(M, 2)，线段端点索引对，dtype=int32，0-based

    # 区域标记点（Triangle regions 输入）
    # 对应 Triangle alpha 字典的 'regions' 键
    # 每行格式：[R, Z, region_id, max_area_hint]
    # region_id 约定：1=plasma, 2=vacuum, 3=P0 equivalent outer/wall-conductor（见蓝图第 5 节）
    # max_area_hint=-1 表示不限制该区域面积（使用全局 max_area 约束）
    # 行数由 _build_boundary_config() 根据输入动态决定，不写死
    regions: np.ndarray           # shape=(K, 4)，dtype=float64，K 由输入决定

    # 边界标记（对应 segments 的整数标记，与 segments 逐项对应）
    # 对应 Triangle alpha 字典的 'segment_markers' 键
    # 标记约定：1=LCFS, 2=first_wall/limiter, 3=outer_boundary（见蓝图第 5 节）
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

    该对象是 mesher/triangle_wrapper.py（Python triangle 包唯一底座）的输出，
    同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py 的共同输入。
    所有索引均从 0 开始（Python 约定，由 Triangle 'z' 控制字符保证）。
    写出时各 writer 负责按目标格式约定进行索引转换。

    字段来源（对应 TokaMaker run_triangle / tr.triangulate 返回字典键名）：
        nodes             ← beta['vertices']
        triangles         ← beta['triangles']
        region_ids        ← beta['triangle_attributes']，reshape(-1)，dtype=int32
        boundary_segments ← beta['segments']
        boundary_markers  ← beta['segment_markers']，reshape(-1)，dtype=int32
        node_markers      ← beta['vertex_markers']，reshape(-1)，dtype=int32

    一维 shape 契约（v1.5 校正）：
        region_ids.shape    == (T,)，即使 T==1 也保持一维
        boundary_markers.shape == (S,)，即使 S==1 也保持一维
        node_markers.shape  == (N,)，即使 N==1 也保持一维
        提取方式：np.asarray(..., dtype=np.int32).reshape(-1)，不使用 .squeeze()

    区域传递契约：
        region_ids 中的编号必须全部来自 BoundaryConfig.regions[:,2] 显式配置的非零物理编号。
        不得出现 region_id=0（Triangle 默认属性，不是合法 P0 物理区域）。
        输出区域集合必须与配置区域集合完全一致（不缺少，不多余）。
    """

    # 节点坐标
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64

    # 三角形连接表（三角形顶点索引，逆时针方向）
    # 索引为 0-based（Triangle 'z' 标志保证）
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，dtype=int32

    # 三角形区域标记
    # 约定：1=plasma, 2=vacuum, 3=P0 equivalent outer/wall-conductor
    # 提取：np.asarray(beta['triangle_attributes'], dtype=np.int32).reshape(-1)
    # 不得含 0；编号集合必须与 BoundaryConfig.regions[:,2] 完全一致
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，dtype=int32

    # 边界线段连接表
    # 索引为 0-based（Triangle 'z' 标志保证）
    boundary_segments: np.ndarray    # shape=(S, 2)，边界线段端点节点索引，dtype=int32

    # 边界线段标记
    # 约定：1=LCFS, 2=first_wall/limiter, 3=outer_boundary
    # 提取：np.asarray(beta['segment_markers'], dtype=np.int32).reshape(-1)
    boundary_markers: np.ndarray     # shape=(S,)，每条边界线段的标记，dtype=int32

    # 节点边界标记
    # 0=内部节点，非零=边界节点
    # 提取：np.asarray(beta['vertex_markers'], dtype=np.int32).reshape(-1)
    node_markers: np.ndarray         # shape=(N,)，每个节点的边界标记，dtype=int32

    @property
    def n_nodes(self) -> int:
        return self.nodes.shape[0]

    @property
    def n_triangles(self) -> int:
        return self.triangles.shape[0]

    @property
    def n_boundary_segments(self) -> int:
        return self.boundary_segments.shape[0]


# --------------------------------------------------------------------------- #
# 公开接口                                                                      #
# --------------------------------------------------------------------------- #

def generate_mesh(config: BoundaryConfig) -> Mesh2D:
    """调用 Triangle（Python triangle 包唯一底座）生成二维非结构化三角网格。

    调用风格严格对齐 TokaMaker OFT meshing.py 的 run_triangle / Mesh.get_mesh：
        alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)
        beta  = tr.triangulate(alpha, opts)
        提取 beta['vertices'], beta['triangles'], beta['triangle_attributes'] 等

    区域输出契约检查（不写死区域数量）：
        - 配置区域编号必须有限、具有整数语义且非零；
        - 配置区域编号不得重复；
        - 原始 Triangle 区域属性必须有限并具有整数语义（不静默截断小数）；
        - 输出区域编号不得包含 0；
        - 实际输出区域集合必须与配置集合完全一致（不缺少，不多余）；
        - 每个配置区域至少对应一个三角形。

    参数：
        config: BoundaryConfig 对象，包含边界点、线段、区域标记和质量参数

    返回：
        Mesh2D 对象，包含节点坐标、三角形连接表、区域标记和边界标记

    异常：
        ImportError: triangle 包未安装
        ValueError: Triangle 生成失败或区域契约检查不通过
    """
    try:
        import triangle as tr
    except ImportError as e:
        raise ImportError(
            "无法导入 triangle 包。请运行：pip install triangle"
            f"\n原始错误：{e}"
        ) from e

    # ------------------------------------------------------------------ #
    # Step 1：验证配置区域编号                                             #
    # ------------------------------------------------------------------ #
    _validate_config_regions(config.regions)

    # 提取配置区域编号集合（用于后续输出验证）
    configured_ids = set(int(x) for x in config.regions[:, 2])

    # ------------------------------------------------------------------ #
    # Step 2：按 TokaMaker 风格构造 alpha 字典                             #
    # ------------------------------------------------------------------ #
    alpha = {
        "vertices":        np.ascontiguousarray(config.vertices, dtype=np.float64),
        "segments":        np.ascontiguousarray(config.segments, dtype=np.int32),
        "segment_markers": np.ascontiguousarray(config.segment_markers, dtype=np.int32),
        "regions":         np.ascontiguousarray(config.regions, dtype=np.float64),
    }

    # ------------------------------------------------------------------ #
    # Step 3：生成 Triangle 控制字符串                                     #
    # ------------------------------------------------------------------ #
    opts = _build_triangle_opts(config)

    # ------------------------------------------------------------------ #
    # Step 4：调用 tr.triangulate                                          #
    # ------------------------------------------------------------------ #
    beta = tr.triangulate(alpha, opts)

    # ------------------------------------------------------------------ #
    # Step 5：验证基本输出合法性                                           #
    # ------------------------------------------------------------------ #
    if len(beta.get("vertices", [])) == 0:
        raise ValueError("Triangle 生成失败：输出节点数为 0。请检查 BoundaryConfig 输入。")
    if len(beta.get("triangles", [])) == 0:
        raise ValueError("Triangle 生成失败：输出三角形数为 0。请检查 BoundaryConfig 输入。")

    # ------------------------------------------------------------------ #
    # Step 6：提取并验证区域属性，然后构造 Mesh2D                          #
    # ------------------------------------------------------------------ #
    nodes = beta["vertices"].astype(np.float64)
    triangles = beta["triangles"].astype(np.int32)

    # 验证并规范化区域属性（在转换为 int32 之前检查有限性和整数语义）
    region_ids = _validate_and_normalize_region_ids(
        beta["triangle_attributes"], triangles.shape[0], configured_ids
    )

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

    # Step 7：打印统计信息
    print(f"  节点数: {mesh.n_nodes}")
    print(f"  三角形数: {mesh.n_triangles}")
    print(f"  边界线段数: {mesh.n_boundary_segments}")

    return mesh


# --------------------------------------------------------------------------- #
# 内部辅助函数                                                                  #
# --------------------------------------------------------------------------- #

def _validate_config_regions(regions: np.ndarray) -> None:
    """验证 BoundaryConfig.regions 中的区域编号合法性。

    检查项：
        - regions 至少有一行且有第 3 列（region_id 列）；
        - 所有区域编号有限；
        - 所有区域编号具有整数语义（不接受 1.5 等非整数值）；
        - 所有区域编号非零；
        - 区域编号不重复。

    异常：
        ValueError：任何检查不通过时抛出，消息区分具体问题。
    """
    if regions.ndim != 2 or regions.shape[1] < 3:
        raise ValueError(
            f"BoundaryConfig.regions 格式错误：期望 shape (K,4)，实际 shape {regions.shape}。"
        )
    raw_ids = regions[:, 2]

    if not np.all(np.isfinite(raw_ids)):
        bad = raw_ids[~np.isfinite(raw_ids)]
        raise ValueError(
            f"BoundaryConfig.regions 中区域编号含非有限值：{bad}。"
        )

    # 检查整数语义：与四舍五入后的值比较
    rounded = np.round(raw_ids)
    if not np.allclose(raw_ids, rounded, atol=1e-9):
        bad = raw_ids[~np.isclose(raw_ids, rounded, atol=1e-9)]
        raise ValueError(
            f"BoundaryConfig.regions 中区域编号不具有整数语义（含小数值）：{bad}。"
            f"区域编号必须为整数（如 1.0, 2.0, 3.0），不接受 1.5 等非整数值。"
        )

    int_ids = rounded.astype(np.int64)
    zero_mask = int_ids == 0
    if np.any(zero_mask):
        raise ValueError(
            f"BoundaryConfig.regions 中区域编号含 0：{int_ids[zero_mask]}。"
            f"region_id=0 是 Triangle 默认属性，不是合法 P0 物理区域。"
        )

    unique_ids, counts = np.unique(int_ids, return_counts=True)
    dup = unique_ids[counts > 1]
    if len(dup) > 0:
        raise ValueError(
            f"BoundaryConfig.regions 中区域编号重复：{dup.tolist()}。"
            f"每个区域编号只能出现一次。"
        )


def _validate_and_normalize_region_ids(
    raw_attrs,
    n_triangles: int,
    configured_ids: set,
) -> np.ndarray:
    """验证并规范化 Triangle 输出的区域属性，返回一维 int32 数组。

    检查项（按顺序，产生清晰错误消息）：
        1. 属性数组长度与三角形数一致；
        2. 所有属性值有限（不含 NaN/Inf）；
        3. 所有属性值具有整数语义（不静默截断小数）；
        4. 不含 0（Triangle 默认属性）；
        5. 输出区域集合与配置集合完全一致（不缺少，不多余）；
        6. 每个配置区域至少对应一个三角形。

    参数：
        raw_attrs:      beta['triangle_attributes']（原始 Triangle 输出）
        n_triangles:    三角形总数
        configured_ids: 配置区域编号集合（来自 BoundaryConfig.regions[:,2]）

    返回：
        shape=(T,) 的一维 int32 数组

    异常：
        ValueError：任何检查不通过时抛出，消息区分具体问题。
    """
    # 规范化为一维浮点数组（在整数转换之前）
    raw = np.asarray(raw_attrs, dtype=np.float64).reshape(-1)

    # 检查 1：长度与三角形数一致
    if len(raw) != n_triangles:
        raise ValueError(
            f"Triangle 区域属性长度 ({len(raw)}) 与三角形数 ({n_triangles}) 不一致。"
        )

    # 检查 2：有限性
    if not np.all(np.isfinite(raw)):
        n_bad = np.sum(~np.isfinite(raw))
        raise ValueError(
            f"Triangle 输出区域属性含 {n_bad} 个非有限值（NaN 或 Inf）。"
        )

    # 检查 3：整数语义（不静默截断小数）
    rounded = np.round(raw)
    if not np.allclose(raw, rounded, atol=1e-9):
        bad_vals = raw[~np.isclose(raw, rounded, atol=1e-9)]
        raise ValueError(
            f"Triangle 输出区域属性含非整数值：{bad_vals[:5]}（最多显示 5 个）。"
            f"区域属性必须为整数语义，不接受小数值。"
        )

    int_ids = rounded.astype(np.int32)

    # 检查 4：不含 0
    if np.any(int_ids == 0):
        n_zero = np.sum(int_ids == 0)
        raise ValueError(
            f"Triangle 输出区域属性含 {n_zero} 个 region_id=0。"
            f"region_id=0 是 Triangle 默认属性，不是合法 P0 物理区域。"
            f"请检查 BoundaryConfig.regions 中的区域种子是否正确覆盖所有几何区域。"
        )

    # 检查 5：输出集合与配置集合完全一致
    actual_ids = set(int_ids.tolist())
    missing = configured_ids - actual_ids
    extra = actual_ids - configured_ids

    if missing:
        raise ValueError(
            f"Triangle 输出缺少配置区域：{sorted(missing)}。"
            f"配置区域 {sorted(configured_ids)} 中有区域未被任何三角形覆盖。"
            f"请检查区域种子是否正确放置在对应几何区域内。"
        )
    if extra:
        raise ValueError(
            f"Triangle 输出含未配置区域：{sorted(extra)}。"
            f"配置区域为 {sorted(configured_ids)}，但输出出现了额外区域编号。"
        )

    # 检查 6：每个配置区域至少对应一个三角形（已由检查 5 保证，此处为显式确认）
    for cid in configured_ids:
        count = np.sum(int_ids == cid)
        if count == 0:
            raise ValueError(
                f"配置区域 {cid} 没有对应的三角形（0 个三角形）。"
            )

    return int_ids


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
    """
    opts = "p"
    opts += f"q{config.min_angle:.1f}"
    if config.max_area is not None:
        opts += f"a{config.max_area:.6g}"
    opts += "AzQ"
    return opts
