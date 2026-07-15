"""
gfile_reader.py —— GFile/EQDSK 平衡文件读取器。

职责：
    - 读取 EQDSK/GFile 文件（纯文本，Fortran e16.9 格式）
    - 提取 LCFS 边界坐标（lcfs_r, lcfs_z）
    - 提取第一壁坐标（wall_r, wall_z，可选）
    - 提取磁轴坐标（rmaxis, zmaxis）
    - 提取磁通网格（psi_grid，用于可视化）
    - 返回 GFileData 对象

禁止事项：
    - 不得调用 Triangle 或任何网格生成逻辑
    - 不得写文件

参考规范：
    LinkMesh_Architecture_Plan.md 第 6 节

# TODO: 待在 M1 里程碑阶段结合真实 GFile 样例实测，进行确切字段与索引约定的最终对齐
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# --------------------------------------------------------------------------- #
# 核心数据结构                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class GFileData:
    """GFile/EQDSK 平衡文件读取结果。

    所有坐标单位均为米（SI 单位制）。
    R 为大半径方向，Z 为垂直方向（托卡马克柱坐标系）。

    # TODO: 待在 M1 里程碑阶段结合真实源码实测，进行确切字段与索引约定的最终对齐
    """

    # 网格维度
    nw: int                              # R 方向网格点数
    nh: int                              # Z 方向网格点数

    # 基本平衡参数
    rdim: float                          # 计算域 R 方向宽度 [m]
    zdim: float                          # 计算域 Z 方向高度 [m]
    rcentr: float                        # 参考大半径 R0 [m]
    rleft: float                         # 计算域左边界 R 坐标 [m]
    zmid: float                          # 计算域 Z 方向中心 [m]
    rmaxis: float                        # 磁轴 R 坐标 [m]
    zmaxis: float                        # 磁轴 Z 坐标 [m]
    simag: float                         # 磁轴处归一化磁通 psi_axis [Wb]
    sibry: float                         # LCFS 处归一化磁通 psi_bry [Wb]
    bcentr: float                        # 参考磁场强度 B0 [T]
    current: float                       # 等离子体电流 Ip [A]

    # LCFS 边界坐标（最后闭合磁面）
    lcfs_r: np.ndarray                   # shape=(N_lcfs,)，LCFS 上各点 R 坐标 [m]
    lcfs_z: np.ndarray                   # shape=(N_lcfs,)，LCFS 上各点 Z 坐标 [m]

    # 第一壁点集（可选，若 GFile 不含则为 None）
    wall_r: Optional[np.ndarray]         # shape=(N_wall,)，第一壁 R 坐标 [m]
    wall_z: Optional[np.ndarray]         # shape=(N_wall,)，第一壁 Z 坐标 [m]

    # 磁通函数网格（用于可视化，非网格生成必需）
    # TODO: psirz 的行列顺序（nh×nw 还是 nw×nh）待 M1 实测确认
    psi_grid: Optional[np.ndarray]       # shape=(nh, nw)，归一化磁通分布
    r_grid: Optional[np.ndarray]         # shape=(nw,)，R 方向网格坐标
    z_grid: Optional[np.ndarray]         # shape=(nh,)，Z 方向网格坐标

    # 剖面数组（可选，用于后续物理验证）
    fpol: Optional[np.ndarray]           # shape=(nw,)，极向磁通函数 F(psi)
    pres: Optional[np.ndarray]           # shape=(nw,)，压力剖面 P(psi)
    qpsi: Optional[np.ndarray]           # shape=(nw,)，安全因子 q(psi)


# --------------------------------------------------------------------------- #
# 公开接口                                                                      #
# --------------------------------------------------------------------------- #

def read_gfile(filepath: str) -> GFileData:
    """读取 EQDSK/GFile 平衡文件，提取 LinkMesh 所需的边界信息。

    参数：
        filepath: GFile 文件路径（字符串）

    返回：
        GFileData 对象，包含 LCFS 坐标、第一壁坐标、磁轴坐标和基本平衡参数

    异常：
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不符合 EQDSK 规范

    实现要点（待 M1 里程碑实现）：
        1. 使用 Python 标准文件 I/O 逐行读取，不依赖 Fortran 格式化 I/O
        2. 第 1 行解析：取最后 3 个 token 作为 idum, nw, nh
        3. 后续数值块使用 numpy.fromstring 或逐行 split 解析
        4. LCFS 坐标从 rbbbs/zbbbs 数组提取，确保闭合（首尾点相同）
        5. 第一壁坐标从 rlim/zlim 数组提取，若 limitr=0 则 wall_r=wall_z=None
        6. psirz 数组按 (nh, nw) 形状重塑，用于可视化（非网格生成必需）
        7. 构造 r_grid 和 z_grid：
               r_grid = np.linspace(rleft, rleft + rdim, nw)
               z_grid = np.linspace(zmid - zdim/2, zmid + zdim/2, nh)

    # TODO: 待在 M1 里程碑阶段结合真实 GFile 样例实测，进行确切字段与索引约定的最终对齐
    """
    raise NotImplementedError(
        "read_gfile() 将在 M1 里程碑阶段实现。"
        "请参考 LinkMesh_Architecture_Plan.md 第 6 节。"
    )


def _ensure_lcfs_closed(r: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """确保 LCFS 边界首尾闭合。

    若首尾点不同，则追加首点到末尾。

    # TODO: 待 M1 里程碑实测验证
    """
    raise NotImplementedError(
        "该模块逻辑将在对应里程碑阶段结合源码实测验证后实现"
    )


def _ensure_lcfs_ccw(r: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """确保 LCFS 边界点按逆时针方向排列。

    若为顺时针则反转数组。
    判断方法：计算多边形有向面积（Shoelace 公式），若为负则反转。

    # TODO: 待 M1 里程碑实测验证
    """
    raise NotImplementedError(
        "该模块逻辑将在对应里程碑阶段结合源码实测验证后实现"
    )
