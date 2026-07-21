"""
mesh.py —— LinkMesh 唯一正式内存网格对象模块。

职责：
    - 定义轻量统一内存网格对象 Mesh2D，作为 LinkMesh 各目标格式之间的
      统一表示（OFT build_mesh 输出经 Adapter 适配后的统一对象，也是各
      Writer 的共同输入）。

设计约束（v1.11 M2.5）：
    - Mesh2D 是 LinkMesh 唯一正式内存网格对象；
    - 它与具体网格生成后端（OFT / Python Triangle 等）和目标文件格式
      （TRIMEG HDF5 / M3DC1 .smb）均无关；
    - 内部三角形索引保持 0-based；任何针对目标格式的偏置（如 TRIMEG HDF5
      的 +1）由目标 Writer 在写出阶段自行完成；
    - region_ids 原样保存 OFT 最终区域编号，不重编号、不排序、不压缩、不 +1。

模块依赖边界（铁律）：
    本模块不得依赖 OFT、Python Triangle、h5py、PUMI、CLI、Plotter、Reader
    或任何 Writer，也不得引入任何网格生成后端。仅依赖 numpy 与标准库。

参考规范：
    LinkMesh_Architecture_Plan.md v1.11 第 2.2 节、第 16 节 M2.5
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _empty_segments() -> np.ndarray:
    """构造空的边界线段数组，shape=(0,2)、dtype=int32。

    每次调用返回独立数组，避免不同 Mesh2D 实例共享同一可变默认数组。
    """
    return np.empty((0, 2), dtype=np.int32)


def _empty_markers() -> np.ndarray:
    """构造空的一维标记数组，shape=(0,)、dtype=int32。

    每次调用返回独立数组，避免不同 Mesh2D 实例共享同一可变默认数组。
    """
    return np.empty((0,), dtype=np.int32)


@dataclass
class Mesh2D:
    """LinkMesh 轻量统一内存网格对象（唯一正式定义，v1.11 迁入独立模块）。

    与网格后端无关的统一表示。该对象是 OFT build_mesh() 返回结果经 LinkMesh
    最小适配后的统一表示，同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py
    的共同输入。本模块不依赖 OFT / Python Triangle / HDF5 / PUMI / CLI / Plotter。

    M2 正式核心字段来源（OFT build_mesh() 返回值）：
        nodes      ← pts[np, 2]，OFT 返回的节点坐标，期望 dtype float64
        triangles  ← lc[nc, 3]，OFT 返回的三角形连接表，期望整数 dtype，内部 0-based
        region_ids ← reg[nc]，OFT 返回的三角形区域编号，期望整数 dtype

    索引约定（M2-0 / M2 已确认）：
        OFT 26.6 build_mesh() 返回合法 0-based lc 连接表，索引范围 0..N-1。
        Adapter 应验证 0 <= lc < N，无需无依据地再次偏置。
        任何针对目标格式的偏置（如 TRIMEG HDF5 的 +1）由目标 Writer 在写出阶段执行。

    区域编号约定（v1.8，v1.11 保持）：
        region_ids 原样保存 OFT 返回的三角形区域编号，不重编号、不压缩、不排序、不执行 +1。
        LinkMesh、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义。
        region_ids 不写入 TRIMEG HDF5（v1.11 契约），继续保留在内存对象中供
        Plotter 与 M4 使用。

    兼容字段说明（v1.8 降级；v1.11 提供安全空数组默认值）：
        boundary_segments/boundary_markers/node_markers 不是 TRIMEG HDF5
        loadfemmesh_h5.m 的直接消费数据集，也不是 M2 正式核心三数组，且不
        参与 v1.11 M3 HDF5 契约。保留字段定义以维持与现有过渡代码的兼容性。
        使用 default_factory 避免不同实例共享同一可变 NumPy 默认数组。

    本数据类不在构造时复制、重排、转换或校验输入数组；边界校验分别由
    OFT Adapter 和各 Writer 承担。
    """

    # M2 正式核心字段（来自 OFT build_mesh() 返回值）
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，整数 dtype，内部 0-based
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，整数 dtype，原样保留

    # 非核心、可选、兼容字段（v1.11 提供安全空数组默认值）
    # 使用 default_factory 避免共享可变 NumPy 默认数组。
    boundary_segments: np.ndarray = field(default_factory=_empty_segments)  # shape=(0,2) int32
    boundary_markers: np.ndarray = field(default_factory=_empty_markers)    # shape=(0,) int32
    node_markers: np.ndarray = field(default_factory=_empty_markers)        # shape=(0,) int32

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
