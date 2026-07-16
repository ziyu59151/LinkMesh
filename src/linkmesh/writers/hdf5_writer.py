"""
hdf5_writer.py —— 第一战役：TRIMEG HDF5 静态网格写出器。

职责：
    - 接收 Mesh2D 对象
    - 严格对照 docs/trimeg/loadfemmesh_h5.m 黄金标尺
    - 按 TRIMEG HDF5 规范写出 .h5 文件

禁止事项：
    - 不得修改 Mesh2D 对象
    - 不得包含任何网格生成逻辑

关键实现约定（来自 loadfemmesh_h5.m 逐行解析，均为已确认事实）：
    1. 所有节点索引写入 HDF5 前必须 +1（0-based → 1-based，MATLAB 约定）
    2. /femmesh/vert 写出为 shape=(2, nvert)（转置），MATLAB h5read 后得 (nvert, 2)
    3. /femmesh/tria 写出为 shape=(4, ntria)（转置），MATLAB h5read 后得 (ntria, 4)
       前3列为节点索引（1-based），第4列为 region_id（不偏置）
    4. /femmesh/Rbc、Zbc 始终写出（不做条件判断）

参考规范：
    LinkMesh_Architecture_Plan.md 第 4.1 节、第 8 节
    docs/trimeg/loadfemmesh_h5.m（黄金标尺，只读）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from linkmesh.mesher.triangle_wrapper import Mesh2D


def write_hdf5(mesh: "Mesh2D", filepath: str, verbose: bool = True) -> None:
    """将 Mesh2D 对象写出为 TRIMEG 标准 HDF5 静态网格文件。

    黄金标尺：docs/trimeg/loadfemmesh_h5.m
    所有数据集路径、形状、dtype 和索引约定均以该脚本为唯一依据。

    参数：
        mesh:     Mesh2D 对象（内部索引全部为 0-based）
        filepath: 输出 .h5 文件路径（若已存在则覆盖）
        verbose:  是否打印写出完成信息（默认 True）

    写出的 HDF5 结构（来自 loadfemmesh_h5.m 逐行解析）：
        /femmesh/nvert      标量 int32   节点总数
        /femmesh/ntria      标量 int32   三角形总数
        /femmesh/nvert_in   标量 int32   内部节点数
        /femmesh/nvert_ex   标量 int32   边界节点数
        /femmesh/vert       (2,N) float64  节点坐标（转置存储）
        /femmesh/idxivert   (nvert_in,) int32  内部节点全局索引（1-based）
        /femmesh/idxevert   (nvert_ex,) int32  边界节点全局索引（1-based）
        /femmesh/tria       (4,T) int32   三角形数据（转置存储，节点索引1-based）
        /femmesh/nbcRZ      标量 int32   边界节点坐标点数
        /femmesh/Rbc        (nbcRZ,) float64  边界节点 R 坐标
        /femmesh/Zbc        (nbcRZ,) float64  边界节点 Z 坐标
    """
    try:
        import h5py
    except ImportError as e:
        raise ImportError(
            "无法导入 h5py。请运行：pip install h5py"
            f"\n原始错误：{e}"
        ) from e

    # ------------------------------------------------------------------ #
    # 预计算各统计量                                                        #
    # ------------------------------------------------------------------ #
    n_nodes = mesh.n_nodes
    n_triangles = mesh.n_triangles

    # 内部节点：node_markers == 0
    # 边界节点：node_markers != 0
    interior_mask = (mesh.node_markers == 0)
    boundary_mask = (mesh.node_markers != 0)

    nvert_in = int(np.sum(interior_mask))
    nvert_ex = int(np.sum(boundary_mask))

    # ------------------------------------------------------------------ #
    # 写出 HDF5 文件                                                        #
    # ------------------------------------------------------------------ #
    with h5py.File(filepath, "w") as f:
        grp = f.create_group("femmesh")

        # --- 标量元数据 ---
        # 来自 loadfemmesh_h5.m:
        #   femmesh.nvert    = h5read(h5file,'/femmesh/nvert');
        #   femmesh.ntria    = h5read(h5file,'/femmesh/ntria');
        #   femmesh.nvert_in = h5read(h5file,'/femmesh/nvert_in');
        #   femmesh.nvert_ex = h5read(h5file,'/femmesh/nvert_ex');
        grp.create_dataset("nvert",    data=np.int32(n_nodes))
        grp.create_dataset("ntria",    data=np.int32(n_triangles))
        grp.create_dataset("nvert_in", data=np.int32(nvert_in))
        grp.create_dataset("nvert_ex", data=np.int32(nvert_ex))

        # --- /femmesh/vert：转置写入 ---
        # 来自 loadfemmesh_h5.m:
        #   femmesh.vert = h5read(h5file,'/femmesh/vert').';
        # 说明：HDF5 中存储 (2, N)，MATLAB h5read 后转置得 (N, 2)
        # Python 中 mesh.nodes 为 (N, 2)，转置后写入得 (2, N)
        vert_data = mesh.nodes.T.astype(np.float64)   # shape=(2, N)
        grp.create_dataset("vert", data=vert_data)

        # --- /femmesh/idxivert：内部节点全局索引，1-based ---
        # 来自 loadfemmesh_h5.m:
        #   femmesh.idxivert = h5read(h5file,'/femmesh/idxivert');
        # 0-based 下标 +1 → 1-based 全局索引
        idxivert = (np.where(interior_mask)[0] + 1).astype(np.int32)
        grp.create_dataset("idxivert", data=idxivert)

        # --- /femmesh/idxevert：边界节点全局索引，1-based ---
        # 来自 loadfemmesh_h5.m:
        #   femmesh.idxevert = h5read(h5file,'/femmesh/idxevert');
        idxevert = (np.where(boundary_mask)[0] + 1).astype(np.int32)
        grp.create_dataset("idxevert", data=idxevert)

        # --- /femmesh/tria：+1 偏置（节点列）+ 转置写入 ---
        # 来自 loadfemmesh_h5.m:
        #   femmesh.tria = h5read(h5file,'/femmesh/tria').';
        # 说明：HDF5 中存储 (4, T)，MATLAB h5read 后转置得 (T, 4)
        #   列0-2：节点索引（1-based）
        #   列3：region_id（不偏置，物理标记值）
        #
        # Step 1：节点索引 0-based → 1-based
        tria_nodes_1based = (mesh.triangles + 1).astype(np.int32)   # shape=(T, 3)
        # Step 2：region_ids 扩展为列向量
        region_col = mesh.region_ids.reshape(-1, 1).astype(np.int32)  # shape=(T, 1)
        # Step 3：水平拼接为 (T, 4)
        tria_4col = np.hstack([tria_nodes_1based, region_col])         # shape=(T, 4)
        # Step 4：转置后写入，HDF5 中存储为 (4, T)
        grp.create_dataset("tria", data=tria_4col.T.astype(np.int32))

        # --- /femmesh/nbcRZ、Rbc、Zbc：边界节点坐标 ---
        # 来自 loadfemmesh_h5.m（try...catch 块，可选但始终写出）：
        #   femmesh.nbcRZ = h5read(h5file,'/femmesh/nbcRZ');
        #   femmesh.Rbc   = h5read(h5file,'/femmesh/Rbc');
        #   femmesh.Zbc   = h5read(h5file,'/femmesh/Zbc');
        nbcRZ = nvert_ex  # 等于边界节点数
        grp.create_dataset("nbcRZ", data=np.int32(nbcRZ))

        # 边界节点的 R 坐标（mesh.nodes 第0列）
        Rbc = mesh.nodes[boundary_mask, 0].astype(np.float64)
        grp.create_dataset("Rbc", data=Rbc)

        # 边界节点的 Z 坐标（mesh.nodes 第1列）
        Zbc = mesh.nodes[boundary_mask, 1].astype(np.float64)
        grp.create_dataset("Zbc", data=Zbc)

    if verbose:
        print(f"HDF5 写出完成：{filepath}，节点数: {n_nodes}，三角形数: {n_triangles}")
