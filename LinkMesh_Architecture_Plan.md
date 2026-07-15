# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Hybrid-Control
- 知识库用途：参考架构
- 文档状态：正式版 v1.0
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
- 主要用途：指导 Aider 编写 LinkMesh 各模块的具体 Python 代码，约束 MVP P0 边界，提供数据流转管道的精确接口定义。
- 场外架构师检索用途：当场外架构师需要判断 LinkMesh 某模块的职责边界、某数据结构的字段定义、某输出格式的对齐标准，或某开发阶段的验收条件时，应优先召回本文档。

---

## 0. LinkMesh 项目定位与 MVP P0 边界

### 0.1 项目定位

LinkMesh 是一个**独立命令行程序（CLI）**，专注于打通从**等离子体平衡文件（GFile/EQDSK）**提取边界，到基于**开源 Triangle 库**生成二维非结构三角网格，再到输出**目标物理求解器静态网格文件**的完整工具链路。

LinkMesh 不是通用网格中间件，不是插件框架，不是抽象适配层。它是一个能快速跑通、能被导师团队验收的独立命令行转换工具。

### 0.2 MVP P0 硬边界（铁律，不得突破）

| 维度 | P0 允许 | P0 禁止 |
|---|---|---|
| 输入端 | 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | 复杂 CAD 输入；多区域高维输入 |
| 网格生成 | 调用 `triangle` Python 包生成二维非结构化三角网格 | 三维棱柱/四面体生成；自适应网格细化算法 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 `.smb` 静态二进制网格文件 | 三维网格输出；其他求解器格式 |
| 可视化 | 基于 `matplotlib` 的简易画图自检 | 交互式可视化；三维渲染 |

---

## 1. MVP 物理目录树与职责矩阵

### 1.1 顶层目录结构

```text
LinkMesh/
├── cli.py                         # CLI 入口：参数解析与主流程控制
├── CONTEXT.md                     # 敏捷开发纪律规范（只读）
├── LinkMesh_Architecture_Plan.md  # 本文档（单事实真理源）
├── History.md                     # 战术战果归档
├── requirements.txt               # Python 依赖清单
├── .venv/                         # 独立虚拟环境（不入版本控制）
│
├── readers/
│   ├── __init__.py
│   └── gfile_reader.py            # GFile/EQDSK 平衡文件读取器
│
├── mesher/
│   ├── __init__.py
│   └── triangle_wrapper.py        # Triangle 库封装：生成二维三角网格
│
├── writers/
│   ├── __init__.py
│   ├── hdf5_writer.py             # TRIMEG 标准 HDF5 静态网格写出器
│   └── smb_writer.py              # M3DC1 PUMI .smb 静态二进制网格写出器
│
├── utils/
│   ├── __init__.py
│   └── plotter.py                 # matplotlib 可视化自检工具
│
├── tests/
│   ├── test_gfile_reader.py
│   ├── test_triangle_wrapper.py
│   ├── test_hdf5_writer.py
│   └── test_smb_writer.py
│
└── examples/
    ├── sample.geqdsk               # 示例 GFile 平衡文件
    └── run_example.sh              # 示例运行脚本
```

### 1.2 模块职责矩阵

| 模块文件 | 核心职责 | 输入 | 输出 | 禁止事项 |
|---|---|---|---|---|
| `cli.py` | 解析命令行参数；按顺序调用 reader → mesher → writer；捕获异常并打印友好错误信息 | `sys.argv` | 无（副作用：调用各模块） | 不得包含任何业务逻辑；不得直接操作文件 |
| `readers/gfile_reader.py` | 读取 EQDSK/GFile 文件；提取 LCFS 边界坐标、磁轴坐标、第一壁点集、基本平衡参数 | GFile 文件路径（`str`） | `GFileData` dataclass | 不得调用 Triangle；不得写文件 |
| `mesher/triangle_wrapper.py` | 接收边界点集和区域配置；调用 `triangle` Python 包生成二维三角网格；返回内存网格对象 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑 |
| `writers/hdf5_writer.py` | 接收 `Mesh2D` 对象；按 TRIMEG HDF5 规范写出 `.h5` 文件 | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑 |
| `writers/smb_writer.py` | 接收 `Mesh2D` 对象；按 PUMI `.smb` 二进制协议写出静态网格文件 | `Mesh2D` 对象，输出路径 | `.smb` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑 |
| `utils/plotter.py` | 绘制 LCFS 边界与生成三角网格的叠加图；输出 `.png` 自检图 | `GFileData`，`Mesh2D`，输出路径 | `.png` 文件（副作用） | 不得修改任何数据对象 |

---

## 2. 核心内存数据结构定义

### 2.1 `GFileData`：GFile 读取结果

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class GFileData:
    """GFile/EQDSK 平衡文件读取结果。

    所有坐标单位均为米（SI 单位制）。
    R 为大半径方向，Z 为垂直方向（托卡马克柱坐标系）。
    """
    # 网格维度
    nw: int                      # R 方向网格点数
    nh: int                      # Z 方向网格点数

    # 基本平衡参数
    rdim: float                  # 计算域 R 方向宽度 [m]
    zdim: float                  # 计算域 Z 方向高度 [m]
    rcentr: float                # 参考大半径 R0 [m]
    rleft: float                 # 计算域左边界 R 坐标 [m]
    zmid: float                  # 计算域 Z 方向中心 [m]
    rmaxis: float                # 磁轴 R 坐标 [m]
    zmaxis: float                # 磁轴 Z 坐标 [m]
    simag: float                 # 磁轴处归一化磁通 psi_axis [Wb]
    sibry: float                 # LCFS 处归一化磁通 psi_bry [Wb]
    bcentr: float                # 参考磁场强度 B0 [T]
    current: float               # 等离子体电流 Ip [A]

    # LCFS 边界坐标（最后闭合磁面）
    lcfs_r: np.ndarray           # shape=(N_lcfs,)，LCFS 上各点 R 坐标 [m]
    lcfs_z: np.ndarray           # shape=(N_lcfs,)，LCFS 上各点 Z 坐标 [m]

    # 第一壁点集（可选，若 GFile 不含则为 None）
    wall_r: np.ndarray | None    # shape=(N_wall,)，第一壁 R 坐标 [m]
    wall_z: np.ndarray | None    # shape=(N_wall,)，第一壁 Z 坐标 [m]

    # 磁通函数网格（用于可视化，非网格生成必需）
    psi_grid: np.ndarray | None  # shape=(nh, nw)，归一化磁通分布
    r_grid: np.ndarray | None    # shape=(nw,)，R 方向网格坐标
    z_grid: np.ndarray | None    # shape=(nh,)，Z 方向网格坐标

    # 剖面数组（可选，用于后续物理验证）
    fpol: np.ndarray | None      # shape=(nw,)，极向磁通函数 F(psi)
    pres: np.ndarray | None      # shape=(nw,)，压力剖面 P(psi)
    qpsi: np.ndarray | None      # shape=(nw,)，安全因子 q(psi)
```

### 2.2 `BoundaryConfig`：Triangle 输入配置

```python
@dataclass
class BoundaryConfig:
    """Triangle 网格生成的输入配置。

    该对象由 cli.py 根据 GFileData 和用户参数构造，
    传递给 mesher/triangle_wrapper.py。
    """
    # 边界点集（分段线性复合体 PLC 的顶点）
    vertices: np.ndarray          # shape=(N, 2)，所有边界点 [R, Z] 坐标，dtype=float64

    # 边界线段连接表（PLC 的边）
    segments: np.ndarray          # shape=(M, 2)，线段端点索引对，dtype=int32

    # 区域标记点（Triangle regions 输入）
    # 每行格式：[R, Z, region_id, max_area]
    # region_id 约定：1=plasma, 2=vacuum, 3=wall（见第 4 节）
    regions: np.ndarray           # shape=(K, 4)，dtype=float64

    # 边界标记（对应 segments 的整数标记）
    # 标记约定：1=LCFS, 2=first_wall, 3=outer_boundary（见第 4 节）
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: float | None = None # 全局最大三角形面积约束（m²），None 表示不限制
```

### 2.3 `Mesh2D`：内存二维三角网格对象

```python
@dataclass
class Mesh2D:
    """LinkMesh 核心内存网格对象。

    该对象是 mesher/triangle_wrapper.py 的输出，
    也是 writers/hdf5_writer.py 和 writers/smb_writer.py 的输入。
    所有索引均从 0 开始（Python 约定）。
    写出时各 writer 负责按目标格式约定进行索引转换。
    """
    # 节点坐标
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64

    # 三角形连接表（三角形顶点索引，逆时针方向）
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，dtype=int32

    # 三角形区域标记（来自 Triangle triangleattributelist）
    # 约定：1=plasma, 2=vacuum, 3=wall
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，dtype=int32

    # 边界线段连接表
    boundary_segments: np.ndarray    # shape=(S, 2)，边界线段端点节点索引，dtype=int32

    # 边界线段标记（来自 Triangle segmentmarkerlist）
    # 约定：1=LCFS, 2=first_wall, 3=outer_boundary
    boundary_markers: np.ndarray     # shape=(S,)，每条边界线段的标记，dtype=int32

    # 节点边界标记（来自 Triangle pointmarkerlist）
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
```

---

## 3. 数据流转架构

### 3.1 完整数据管道

```text
用户命令行输入
│
│  linkmesh --gfile sample.geqdsk \
│           --output mesh.h5 \
│           --smb mesh.smb \
│           --min-angle 20 \
│           --max-area 0.001 \
│           --plot mesh_check.png
│
↓
cli.py
│  解析参数
│  调用 readers.gfile_reader.read_gfile(gfile_path) → GFileData
│  根据 GFileData 和用户参数构造 BoundaryConfig
│  调用 mesher.triangle_wrapper.generate_mesh(config) → Mesh2D
│  调用 writers.hdf5_writer.write_hdf5(mesh, output_path)
│  调用 writers.smb_writer.write_smb(mesh, smb_path)
│  调用 utils.plotter.plot_mesh(gfile_data, mesh, plot_path)（可选）
│
↓
readers/gfile_reader.py
│  读取 EQDSK 文件（纯文本，Fortran e16.9 格式）
│  提取 LCFS 坐标（lcfs_r, lcfs_z）
│  提取第一壁坐标（wall_r, wall_z，可选）
│  提取磁轴坐标（rmaxis, zmaxis）
│  提取磁通网格（psi_grid，用于可视化）
│  返回 GFileData 对象
│
↓
mesher/triangle_wrapper.py
│  将 BoundaryConfig 转换为 triangle 包输入字典
│  构造 Triangle 控制字符串（如 "pq20.0a0.001AzQ"）
│  调用 triangle.triangulate(input_dict, opts)
│  从输出字典提取各字段，构造 Mesh2D 对象
│  返回 Mesh2D 对象
│
├──→ writers/hdf5_writer.py
│     按 TRIMEG HDF5 规范写出 mesh.h5
│     节点索引转换：0-based → 1-based（+1）
│
├──→ writers/smb_writer.py
│     按 PUMI .smb 二进制协议写出 mesh.smb
│     【待源码确认】具体字节流格式
│
└──→ utils/plotter.py（可选）
      绘制 LCFS + 三角网格叠加图
      输出 mesh_check.png
```

### 3.2 CLI 参数规范

```text
用法：linkmesh [选项]

必选参数：
  --gfile PATH          GFile/EQDSK 平衡文件路径

可选参数：
  --output PATH         TRIMEG HDF5 输出路径（默认：mesh.h5）
  --smb PATH            PUMI .smb 输出路径（默认：mesh.smb）
  --min-angle FLOAT     Triangle 最小内角约束（度，默认：20.0）
  --max-area FLOAT      Triangle 最大三角形面积约束（m²，默认：不限制）
  --plot PATH           可视化自检图输出路径（默认：不生成）
  --no-smb              跳过 .smb 文件生成（仅生成 HDF5）
  --no-hdf5             跳过 HDF5 文件生成（仅生成 .smb）
  --verbose             打印详细日志（节点数、三角形数、写入状态）
  -h, --help            显示帮助信息
```

---

## 4. 区域标记与边界标记约定

### 4.1 区域标记（region_id）约定

LinkMesh 在当前 P0 阶段使用以下整数区域标记约定，该约定必须在 `BoundaryConfig.regions`、`Mesh2D.region_ids`、`writers/hdf5_writer.py` 和 `writers/smb_writer.py` 中保持一致：

| region_id | 物理含义 | 对应 M3DC1 语义 | 对应 TRIMEG 语义 |
|---|---|---|---|
| 1 | 等离子体区（plasma） | plasma region | plasma zone |
| 2 | 真空区（vacuum） | vacuum region | vacuum zone |
| 3 | 第一壁/导体区（wall/conductor） | resistive wall region | wall zone |

**注意**：当 GFile 不含第一壁信息时，LinkMesh 只生成 plasma 区（region_id=1）和 vacuum 区（region_id=2）。

### 4.2 边界标记（boundary_marker）约定

LinkMesh 在当前 P0 阶段使用以下整数边界标记约定，该约定必须在 `BoundaryConfig.segment_markers`、`Mesh2D.boundary_markers`、`writers/hdf5_writer.py` 和 `writers/smb_writer.py` 中保持一致：

| boundary_marker | 物理含义 | 对应 M3DC1 语义 |
|---|---|---|
| 1 | 最后闭合磁面（LCFS） | plasma-vacuum interface |
| 2 | 第一壁内表面 | wall inner surface |
| 3 | 外边界（计算域边界） | outer boundary |
| 0 | 内部节点（非边界） | — |

---

## 5. readers/gfile_reader.py 实现规范

### 5.1 EQDSK/GFile 文件格式说明

EQDSK（G-EQDSK）是托卡马克平衡文件的标准格式，由 EFIT 代码生成。文件结构如下：

```text
第 1 行：标题行（任意文本）+ 3 个整数（idum, nw, nh）
         nw = R 方向网格点数
         nh = Z 方向网格点数

第 2 行起（5 个 float 一行，Fortran e16.9 格式）：
  rdim, zdim, rcentr, rleft, zmid       # 计算域几何参数
  rmaxis, zmaxis, simag, sibry, bcentr  # 磁轴与磁通参数
  current, simag, xdum, rmaxis, xdum    # 电流与冗余参数
  zmaxis, xdum, sibry, xdum, xdum       # 冗余参数

接下来的数组（均为 nw 或 nh 个元素，5 个 float 一行）：
  fpol[nw]      # 极向磁通函数 F(psi)
  pres[nw]      # 压力剖面 P(psi)
  ffprim[nw]    # F*dF/dpsi
  pprime[nw]    # dP/dpsi
  psirz[nh,nw]  # 二维磁通分布（行优先，nh 行 nw 列）
  qpsi[nw]      # 安全因子 q(psi)

接下来：
  nbbbs, limitr                          # LCFS 点数，第一壁点数
  rbbbs[nbbbs], zbbbs[nbbbs]             # LCFS 坐标（R,Z 交替排列）
  rlim[limitr], zlim[limitr]             # 第一壁坐标（R,Z 交替排列）
```

### 5.2 `read_gfile()` 函数接口

```python
def read_gfile(filepath: str) -> GFileData:
    """读取 EQDSK/GFile 平衡文件，提取 LinkMesh 所需的边界信息。

    参数：
        filepath: GFile 文件路径（字符串）

    返回：
        GFileData 对象，包含 LCFS 坐标、第一壁坐标、磁轴坐标和基本平衡参数

    异常：
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不符合 EQDSK 规范

    实现要点：
        1. 使用 Python 标准文件 I/O 逐行读取，不依赖 Fortran 格式化 I/O
        2. 第 1 行解析：取最后 3 个 token 作为 idum, nw, nh
        3. 后续数值块使用 numpy.fromstring 或逐行 split 解析
        4. LCFS 坐标从 rbbbs/zbbbs 数组提取，确保闭合（首尾点相同）
        5. 第一壁坐标从 rlim/zlim 数组提取，若 limitr=0 则 wall_r=wall_z=None
        6. psirz 数组按 (nh, nw) 形状重塑，用于可视化（非网格生成必需）
        7. 构造 r_grid 和 z_grid：
               r_grid = np.linspace(rleft, rleft + rdim, nw)
               z_grid = np.linspace(zmid - zdim/2, zmid + zdim/2, nh)
    """
```

### 5.3 LCFS 边界预处理

从 GFile 提取的 LCFS 坐标可能存在以下问题，`gfile_reader.py` 必须处理：

1. **闭合性**：确保 LCFS 首尾点相同（若不同则追加首点到末尾）；
2. **方向性**：确保 LCFS 点按逆时针方向排列（若顺时针则反转）；
3. **重采样**：LCFS 点数可能过多或过少，`mesher/triangle_wrapper.py` 在调用 Triangle 前负责重采样。

---

## 6. mesher/triangle_wrapper.py 实现规范

### 6.1 Triangle Python 包调用方式

LinkMesh 通过 `triangle` Python 包调用 Triangle 算法，不直接调用 C API。

```python
import triangle as tr

def generate_mesh(config: BoundaryConfig) -> Mesh2D:
    """调用 Triangle 生成二维非结构化三角网格。

    参数：
        config: BoundaryConfig 对象，包含边界点、线段、区域标记和质量参数

    返回：
        Mesh2D 对象，包含节点坐标、三角形连接表、区域标记和边界标记

    实现要点：
        1. 构造 Triangle 输入字典（参考 OFT 的 alpha 字典结构）
        2. 生成 Triangle 控制字符串（参考 OFT 的 "pqaAzQ"）
        3. 调用 tr.triangulate(input_dict, opts)
        4. 从输出字典提取各字段，构造 Mesh2D 对象
        5. 验证输出合法性（节点数 > 0，三角形数 > 0）
        6. 打印统计信息（节点数、三角形数、边界线段数）
    """
```

### 6.2 Triangle 输入字典构造

```python
# Triangle 输入字典格式（参考 OFT meshing.py 的 alpha 字典）
input_dict = {
    "vertices":        config.vertices,          # np.ndarray shape=(N, 2)，float64
    "segments":        config.segments,          # np.ndarray shape=(M, 2)，int32
    "segment_markers": config.segment_markers,   # np.ndarray shape=(M,)，int32
    "regions":         config.regions,           # np.ndarray shape=(K, 4)，float64
                                                 # 每行：[R, Z, region_id, max_area]
}
```

### 6.3 Triangle 控制字符串

```python
def _build_triangle_opts(config: BoundaryConfig) -> str:
    """构造 Triangle 控制字符串。

    控制字符含义（参考 triangle-library-integration/SKILL.md）：
        p  - 使用分段线性复合体（PLC）输入模式
        q  - 质量网格生成（最小角约束）
        a  - 面积约束
        A  - 将区域属性写入三角形（生成 triangleattributelist）
        z  - 节点索引从 0 开始（Python 友好）
        Q  - 静默模式（不打印 Triangle 内部日志）

    示例：
        min_angle=20, max_area=0.001 → "pq20.0a0.001AzQ"
        min_angle=20, max_area=None  → "pq20.0AzQ"
    """
    opts = "p"                             # PLC 输入模式
    opts += f"q{config.min_angle:.1f}"    # 质量约束
    if config.max_area is not None:
        opts += f"a{config.max_area}"     # 面积约束
    opts += "AzQ"                         # 区域属性 + 0索引 + 静默
    return opts
```

### 6.4 Triangle 输出字段提取

```python
# Triangle 输出字典字段提取（参考 triangulateio 结构体）
output = tr.triangulate(input_dict, opts)

mesh = Mesh2D(
    nodes=output["vertices"].astype(np.float64),
    triangles=output["triangles"].astype(np.int32),
    region_ids=(
        output["triangle_attributes"]
        .squeeze()
        .astype(np.int32)
    ),
    boundary_segments=output["segments"].astype(np.int32),
    boundary_markers=(
        output["segment_markers"]
        .squeeze()
        .astype(np.int32)
    ),
    node_markers=(
        output["vertex_markers"]
        .squeeze()
        .astype(np.int32)
    ),
)
```

---

## 7. writers/hdf5_writer.py 实现规范（TRIMEG HDF5 格式）

### 7.1 TRIMEG HDF5 文件结构

TRIMEG 标准 HDF5 静态网格格式（基于卢志鑫老师规范，【待源码确认】后可能调整）：

```text
mesh.h5
├── /coordinates          # 节点坐标，shape=(N, 2)，dtype=float64
│                         # 列顺序：[R, Z]，单位：米
├── /connectivity         # 三角形连接表，shape=(T, 3)，dtype=int32
│                         # 节点索引从 1 开始（Fortran 约定，写出时 +1）
├── /region_ids           # 三角形区域标记，shape=(T,)，dtype=int32
│                         # 1=plasma, 2=vacuum, 3=wall
├── /boundary_segments    # 边界线段连接表，shape=(S, 2)，dtype=int32
│                         # 节点索引从 1 开始（Fortran 约定，写出时 +1）
├── /boundary_markers     # 边界线段标记，shape=(S,)，dtype=int32
│                         # 1=LCFS, 2=first_wall, 3=outer_boundary
└── /metadata             # 元数据组
    ├── n_nodes           # 节点总数，标量 int32
    ├── n_triangles       # 三角形总数，标量 int32
    ├── n_boundary_segs   # 边界线段总数，标量 int32
    ├── generator         # 字符串："LinkMesh v1.0"
    └── format_version    # 字符串："TRIMEG-HDF5-v1"
```

**【待源码确认】**：上述 HDF5 结构基于白皮书推断，需在获取卢志鑫老师 TRIMEG 代码后对齐实际读取接口。节点索引约定（0-based vs 1-based）需特别确认。

### 7.2 `write_hdf5()` 函数接口

```python
import h5py

def write_hdf5(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 TRIMEG 标准 HDF5 静态网格文件。

    参数：
        mesh: Mesh2D 对象
        filepath: 输出 .h5 文件路径

    实现要点：
        1. 使用 h5py 创建 HDF5 文件（mode='w'，覆盖已有文件）
        2. 节点索引转换：Mesh2D 内部使用 0-based，写出时转换为 1-based（+1）
        3. 坐标数据使用 float64 精度
        4. 连接表和标记使用 int32 类型
        5. 写入 /metadata 组记录生成信息
        6. 写入完成后打印验证信息（节点数、三角形数）
    """
```

---

## 8. writers/smb_writer.py 实现规范（PUMI .smb 格式）

### 8.1 PUMI .smb 格式逆向分析现状

**【重要说明】**：`.smb` 格式是 SCOREC/PUMI 库的私有二进制格式。以下规范基于对 `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` 和 PUMI 源码的逆向分析推断，**所有内容均标注为【待源码确认】**，在完成 Step 2 只读侦察并经主管确认后方可转为已确认事实并进入代码实现。

当前已知的 PUMI `.smb` 格式关键事实（来自 M3DC1 白皮书推断）：

| 信息类别 | 当前推断 | 事实状态 |
|---|---|---|
| 文件类型 | 小端序二进制文件 | 【待源码确认】 |
| 文件头 | 包含版本号、维度、节点数、单元数等元数据 | 【待源码确认】 |
| 节点坐标 | 按节点顺序存储 (R, Z) 坐标，float64 | 【待源码确认】 |
| 三角形连接表 | 按三角形顺序存储三顶点节点索引，int32 | 【待源码确认】 |
| 区域标记 | 每个三角形对应一个整数区域 ID | 【待源码确认】 |
| 边界标记 | 每条边界线段对应一个整数边界标记 | 【待源码确认】 |
| 索引约定 | 1-based（Fortran/PUMI 约定） | 【待源码确认】 |
| 高阶节点 | 是否需要边中点（C1 单元需求） | 【待源码确认，见缺口 G1】 |

### 8.2 `write_smb()` 函数接口（占位规范）

```python
def write_smb(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 PUMI .smb 静态二进制网格文件。

    参数：
        mesh: Mesh2D 对象
        filepath: 输出 .smb 文件路径

    【重要】：本函数的具体实现必须等待以下侦察任务完成后方可编写：
        1. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc
           → 确认 .smb 文件的二进制字节流格式
        2. 只读侦察 M3DC1/m3dc1_scorec/include/m3dc1_model.h
           → 确认 model .txt 文件格式（配套输出）
        3. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_field.cc
           → 确认是否需要在写出前生成边中点（高阶节点）

    当前占位实现：
        raise NotImplementedError(
            "smb_writer 尚待完成 PUMI .smb 格式逆向侦察后实现。"
            "请参考 LinkMesh_Architecture_Plan.md 第 8 节和"
            "docs/m3dc1/M3DC1_Architecture_Whitepaper.md 第 6 节。"
        )
    """
```

### 8.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。LinkMesh 的 `writers/smb_writer.py` 在写出 `.smb` 文件时，应同时写出配套的 model `.txt` 文件。

**【待源码确认】**：model `.txt` 文件的具体格式需通过只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` 确认。

---

## 9. utils/plotter.py 实现规范

### 9.1 `plot_mesh()` 函数接口

```python
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

def plot_mesh(
    gfile_data: GFileData,
    mesh: Mesh2D,
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
```

---

## 10. requirements.txt 依赖清单

```text
# LinkMesh Python 依赖清单
# 使用 pip install -r requirements.txt 安装

# 核心科学计算
numpy>=1.24.0

# Triangle 网格生成
triangle>=20230923

# HDF5 文件读写
h5py>=3.8.0

# 可视化自检
matplotlib>=3.7.0

# 开发与测试（可选）
pytest>=7.0.0
```

---

## 11. 敏捷渐进里程碑（MVP 开发阶段）

### 里程碑 M1：GFile 读取验收（P0 第一步）

**目标**：能够从真实 GFile 文件中提取 LCFS 边界坐标并可视化。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --plot lcfs_check.png` 能够运行；
2. 生成的 `lcfs_check.png` 中 LCFS 边界曲线闭合、方向正确；
3. 终端打印：`LCFS 点数: N，磁轴: (R=X.XX, Z=X.XX)`；
4. `GFileData` 对象的所有必填字段均已正确填充。

**涉及模块**：`readers/gfile_reader.py`，`utils/plotter.py`（仅 LCFS 绘制部分）

---

### 里程碑 M2：Triangle 网格生成验收（P0 第二步）

**目标**：能够从 LCFS 边界生成二维三角网格并可视化。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --plot mesh_check.png` 能够运行；
2. 生成的 `mesh_check.png` 中三角网格覆盖 LCFS 内部区域，无明显退化三角形；
3. 终端打印：`节点数: N，三角形数: T，边界线段数: S`；
4. `Mesh2D` 对象的所有字段均已正确填充；
5. 所有三角形的最小内角 ≥ 设定的 `min_angle` 参数值。

**涉及模块**：`mesher/triangle_wrapper.py`，`utils/plotter.py`（完整版）

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步）

**目标**：能够将三角网格写出为 TRIMEG 标准 HDF5 文件。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --output mesh.h5` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开；
3. `h5py` 读取验证：`/coordinates` shape=(N,2)，`/connectivity` shape=(T,3)，`/region_ids` shape=(T,)；
4. 节点索引为 1-based（最小值为 1，最大值为 N）；
5. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`。

**涉及模块**：`writers/hdf5_writer.py`

---

### 里程碑 M4：PUMI .smb 输出验收（P0 第四步，最高难度）

**目标**：能够将三角网格写出为 M3DC1 可消费的 PUMI `.smb` 静态二进制网格文件。

**前置条件**：必须完成 Step 2 只读侦察（`m3dc1_mesh.cc`、`m3dc1_model.cc`、`m3dc1_field.cc`），并经主管确认侦察结果后，方可开始编写 `writers/smb_writer.py`。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --smb mesh.smb` 能够运行；
2. 生成的 `mesh.smb` 文件能被 M3DC1 的 `pumi_mesh_load` 顺畅读取（无报错）；
3. M3DC1 读取后能正确识别节点数、三角形数、区域标记和边界标记；
4. 终端打印：`.smb 写出完成：mesh.smb`。

**涉及模块**：`writers/smb_writer.py`

---

### 里程碑 M5：完整 CLI 端到端验收（P0 完成）

**目标**：一条命令完成从 GFile 到 HDF5 + .smb + PNG 的完整转换链路。

**验收标准**：
```bash
linkmesh \
  --gfile sample.geqdsk \
  --output mesh.h5 \
  --smb mesh.smb \
  --min-angle 20 \
  --max-area 0.001 \
  --plot mesh_check.png \
  --verbose
```
运行后：
1. 生成 `mesh.h5`（TRIMEG HDF5 格式，通过 M3 验收标准）；
2. 生成 `mesh.smb`（PUMI .smb 格式，通过 M4 验收标准）；
3. 生成 `mesh_check.png`（LCFS + 三角网格叠加图）；
4. 终端打印完整统计信息，无报错，无警告。

---

## 12. 蓝图更新纪律

本文档是 LinkMesh 项目的单事实真理源。以下情况必须先更新本文档，再进入代码实现：

1. 新增或删除任何模块文件；
2. 修改任何数据结构的字段定义（`GFileData`、`BoundaryConfig`、`Mesh2D`）；
3. 修改区域标记或边界标记的整数约定；
4. 修改 HDF5 文件结构或数据集名称；
5. 确认 `.smb` 二进制格式的任何细节（将【待源码确认】转为【已确认】）；
6. 新增任何 CLI 参数；
7. 调整任何里程碑的验收标准。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
