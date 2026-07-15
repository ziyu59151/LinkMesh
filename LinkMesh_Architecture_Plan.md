# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 v1.1
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源（Single Source of Truth）。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
- 主要用途：本文档为 LinkMesh 项目的单事实真理源（Single Source of Truth），不作为人类泛读材料，专门用于指导 Aider 自动化编码、RAG 知识库精准检索以及下游模块的硬核参数对齐。凡 Aider 在执行编码、新建文件、修改具体业务代码前，必须查阅并严格对齐本文档。
- 场外架构师检索用途：当场外架构师需要判断 LinkMesh 某模块的职责边界、某数据结构的字段定义、某输出格式的对齐标准，或某开发阶段的验收条件时，应优先召回本文档。
- Aider 执行用途：Aider 必须以本文档为最高技术权威。编写任何 `.py` 业务源码前，必须先核对本文档对应章节的接口定义、数据结构字段和验收标准。如发现实际需求与本文档不符，必须先在对话中提出蓝图迭代建议，待主管确认并更新本文档后，方可动手编写代码。
- 修改前置条件：任何对本文档的修改，必须由人类主管在对话中明确确认后方可执行。Aider 严禁自发修改本文档中的接口定义、数据结构、验收标准或禁止事项。

---

## 0. LinkMesh 项目定位与 MVP P0 边界

### 0.1 项目定位

LinkMesh 是一个**独立命令行程序（CLI）**，专注于打通从**等离子体平衡文件（GFile/EQDSK）**提取边界，到基于**TokaMaker/Triangle 唯一底座**生成二维非结构三角网格，再将统一内存网格对象顺次翻译输出为**两大目标物理求解器静态网格文件**的完整工具链路。

LinkMesh 的网格生成底座**有且仅有** TokaMaker（底层为开源 Triangle 库），不存在多种生成引擎并存的情况。LinkMesh 的核心职责是作为"翻译官"：将 TokaMaker/Triangle 生成的统一 `Mesh2D` 内存对象，准确翻译为两种目标格式：

1. **TRIMEG 消费的 HDF5 静态网格**（第一阶段战役，先易后难）
2. **M3DC1 消费的 PUMI `.smb` 静态二进制网格**（第二阶段战役，逆向攻坚）

LinkMesh 不是通用网格中间件，不是插件框架，不是抽象适配层。它是一个能快速跑通、能被导师团队验收的独立命令行转换工具。

### 0.2 MVP P0 硬边界（铁律，不得突破）

| 维度 | P0 允许 | P0 禁止 |
|---|---|---|
| 输入端 | 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | 复杂 CAD 输入；多区域高维输入 |
| 网格生成底座 | **唯一底座**：调用 `triangle` Python 包（TokaMaker 封装风格）生成二维非结构化三角网格 | 引入任何第二种网格生成引擎；三维棱柱/四面体生成；自适应网格细化算法 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 PUMI `.smb` 静态二进制网格文件 | 三维网格输出；其他求解器格式 |
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
│   └── triangle_wrapper.py        # TokaMaker/Triangle 唯一底座封装：生成二维三角网格
│
├── writers/
│   ├── __init__.py
│   ├── hdf5_writer.py             # 第一战役：TRIMEG HDF5 静态网格写出器
│   └── smb_writer.py              # 第二战役：M3DC1 PUMI .smb 静态二进制网格写出器
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
| `mesher/triangle_wrapper.py` | **唯一网格生成底座**：接收边界点集和区域配置；调用 `triangle` Python 包（TokaMaker 封装风格）生成二维三角网格；返回统一内存网格对象 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑；不得引入第二种生成引擎 |
| `writers/hdf5_writer.py` | **第一战役**：接收 `Mesh2D` 对象；对照 `loadfemmesh_h5.m` 与真实 `.h5` 样例，按 TRIMEG HDF5 规范写出 `.h5` 文件 | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑 |
| `writers/smb_writer.py` | **第二战役**：接收 `Mesh2D` 对象；通过逆向分析 SCOREC/PUMI 开源 C++ 源码的二进制字节流协议，用 Python `struct` 打包写出 M3DC1 可消费的 `.smb` 文件 | `Mesh2D` 对象，输出路径 | `.smb` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；未完成侦察前不得实现 |
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
    传递给 mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）。
    """
    # 边界点集（分段线性复合体 PLC 的顶点）
    vertices: np.ndarray          # shape=(N, 2)，所有边界点 [R, Z] 坐标，dtype=float64

    # 边界线段连接表（PLC 的边）
    segments: np.ndarray          # shape=(M, 2)，线段端点索引对，dtype=int32

    # 区域标记点（Triangle regions 输入）
    # 每行格式：[R, Z, region_id, max_area]
    # region_id 约定：1=plasma, 2=vacuum, 3=wall（见第 5 节）
    regions: np.ndarray           # shape=(K, 4)，dtype=float64

    # 边界标记（对应 segments 的整数标记）
    # 标记约定：1=LCFS, 2=first_wall, 3=outer_boundary（见第 5 节）
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: float | None = None # 全局最大三角形面积约束（m²），None 表示不限制
```

### 2.3 `Mesh2D`：内存二维三角网格对象（唯一核心数据结构）

```python
@dataclass
class Mesh2D:
    """LinkMesh 核心内存网格对象。

    该对象是 mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）的输出，
    同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py 的共同输入。
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

## 3. 数据流转架构（TokaMaker/Triangle 唯一底座 → 双向翻译分发）

### 3.1 完整数据管道

LinkMesh 的数据流是以 `mesher/triangle_wrapper.py`（TokaMaker/Triangle）为绝对核心的**单向分发映射结构**：上游唯一，下游双轨。

```text
GFile 平衡文本
  │
  ↓ [读取与提取边界]
readers/gfile_reader.py
  │
  ↓ [边界点集与区域打标 config]
mesher/triangle_wrapper.py  (TokaMaker / Triangle 唯一底座)
  │
  ↓ [生成统一内存网格对象]
Mesh2D  (内存核心数据结构)
  │
  ├──→ [第一阶段战役：HDF5 映射对齐]
  │      writers/hdf5_writer.py
  │      (对照 loadfemmesh_h5.m 与真实 .h5 样例)
  │        │
  │        ↓
  │      TRIMEG 求解器消费的 HDF5 静态网格
  │
  └──→ [第二阶段战役：二进制字节流逆向]
         writers/smb_writer.py
         (逆向分析 scorec/pumi 开源 C++ 底层解析规范)
           │
           ↓
         M3DC1 求解器消费的 .smb 静态二进制网格
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

## 4. 数据格式对齐规范（两阶段战役核心方法论）

本节是 LinkMesh 两大 Writer 模块的核心实现方法论，Aider 在编写 `writers/` 下任何代码前必须完整阅读本节。

### 4.1 第一战役：TokaMaker → TRIMEG HDF5 格式映射

**【已确认】战役定性**：这是两场战役中相对容易的一场。HDF5 是通用开放格式，TRIMEG 侧已有现成的 MATLAB 读取脚本 `loadfemmesh_h5.m` 和真实 `.h5` 样例文件作为黄金对照标尺，格式完全透明可读。

**对齐方法**：

1. **黄金标尺**：以卢志鑫老师提供的 `docs/trimeg/loadfemmesh_h5.m` 脚本为唯一权威参考。该脚本明确列出了 TRIMEG 读取 HDF5 时期望的所有数据集路径与形状。
2. **字段逐一映射**：`writers/hdf5_writer.py` 的任务就是把 `Mesh2D` 对象的各字段，按照 `loadfemmesh_h5.m` 中 `h5read` 调用的路径名和形状，逐一写入 HDF5 文件。
3. **关键索引转换**：`Mesh2D` 内部所有索引均为 0-based（Python 约定）。写出 HDF5 时，三角形连接表 `triangles` 和边界线段连接表 `boundary_segments` 中的节点索引必须 **+1 转换为 1-based**（Fortran/MATLAB 约定），以匹配 TRIMEG 读取侧的期望。
4. **Fortran 列优先转置**：`loadfemmesh_h5.m` 中注释明确指出 `vert` 在 Fortran 中为 `(2, nvert)` 但在 MATLAB 中读取后为 `(nvert, 2)`（`.`转置）。`writers/hdf5_writer.py` 写出坐标时，必须按 HDF5 实际存储的列优先顺序处理，确保 MATLAB 读取后形状正确。

**`loadfemmesh_h5.m` 揭示的 TRIMEG HDF5 数据集清单**：

| HDF5 数据集路径 | MATLAB 读取后形状 | 对应 `Mesh2D` 字段 | 索引约定 |
|---|---|---|---|
| `/femmesh/nvert` | 标量 | `mesh.n_nodes` | — |
| `/femmesh/ntria` | 标量 | `mesh.n_triangles` | — |
| `/femmesh/nvert_in` | 标量 | 内部节点数（`node_markers==0` 的计数） | — |
| `/femmesh/nvert_ex` | 标量 | 边界节点数（`node_markers!=0` 的计数） | — |
| `/femmesh/vert` | `(nvert, 2)`（MATLAB 转置后） | `mesh.nodes`，列顺序 `[R, Z]` | — |
| `/femmesh/idxivert` | `(nvert_in,)` | 内部节点的全局索引列表 | **1-based** |
| `/femmesh/idxevert` | `(nvert_ex,)` | 边界节点的全局索引列表 | **1-based** |
| `/femmesh/tria` | `(ntria, 4)`（MATLAB 转置后） | `mesh.triangles`（前3列）+ `mesh.region_ids`（第4列） | **1-based**（节点索引列） |
| `/femmesh/nbcRZ` | 标量 | `mesh.n_boundary_segments` | — |
| `/femmesh/Rbc` | `(nbcRZ,)` | 边界节点 R 坐标（从 `mesh.nodes` 按边界标记提取） | — |
| `/femmesh/Zbc` | `(nbcRZ,)` | 边界节点 Z 坐标（从 `mesh.nodes` 按边界标记提取） | — |

**【重要】`/femmesh/tria` 的列结构**：根据 `loadfemmesh_h5.m` 中 `femmesh.tria=h5read(...).′` 的用法，`tria` 在 HDF5 中存储为 `(4, ntria)`（Fortran 列优先），MATLAB 转置后得到 `(ntria, 4)`，其中前 3 列为三角形三顶点节点索引（1-based），第 4 列为区域标记 `region_id`。

### 4.2 第二战役：TokaMaker → M3DC1 PUMI .smb 二进制格式逆向

**【已确认】战役定性**：`.smb` 并非商业公司私有保密格式，而是开源 `SCOREC/PUMI` 库的通用二进制网格格式。这意味着我们可以通过只读侦察项目中已引入的 `m3dc1_scorec` 和 `scorec/pumi` 开源 C++ 源码，完整逆向推导出其二进制字节流协议。

**逆向方法**：

1. **侦察入口**：重点只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` 中读取 `.smb` 文件的 C++ 实现，以及 `scorec/pumi` 库中 `pumi_mesh_load` 的底层字节流解析逻辑。
2. **逆向目标**：从 C++ 读取代码中提取以下关键信息：
   - 文件头格式（魔数、版本号、维度、节点数、单元数等元数据的字节布局）
   - 字节序（Endianness：大端 vs 小端）
   - 数值精度（节点坐标 float32 vs float64；索引 int32 vs int64）
   - 拓扑排列顺序（节点坐标块、三角形连接块、区域标记块、边界标记块的先后顺序）
   - 索引约定（0-based vs 1-based）
3. **Python 实现**：在 `writers/smb_writer.py` 中使用 Python `struct` 模块，按逆向得到的字节流协议，将 `Mesh2D` 对象的各字段打包为对齐的二进制字节流并写出。
4. **前置条件**：`writers/smb_writer.py` 的具体实现**必须等待**只读侦察任务完成并经主管确认后方可开始编写。在侦察完成前，`write_smb()` 函数保持占位实现（`raise NotImplementedError`）。

**【待源码确认】当前推断的 `.smb` 格式关键事实**：

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

---

## 5. 区域标记与边界标记约定

### 5.1 区域标记（region_id）约定

LinkMesh 在当前 P0 阶段使用以下整数区域标记约定，该约定必须在 `BoundaryConfig.regions`、`Mesh2D.region_ids`、`writers/hdf5_writer.py` 和 `writers/smb_writer.py` 中保持一致：

| region_id | 物理含义 | 对应 M3DC1 语义 | 对应 TRIMEG 语义 |
|---|---|---|---|
| 1 | 等离子体区（plasma） | plasma region | plasma zone |
| 2 | 真空区（vacuum） | vacuum region | vacuum zone |
| 3 | 第一壁/导体区（wall/conductor） | resistive wall region | wall zone |

**注意**：当 GFile 不含第一壁信息时，LinkMesh 只生成 plasma 区（region_id=1）和 vacuum 区（region_id=2）。

### 5.2 边界标记（boundary_marker）约定

LinkMesh 在当前 P0 阶段使用以下整数边界标记约定，该约定必须在 `BoundaryConfig.segment_markers`、`Mesh2D.boundary_markers`、`writers/hdf5_writer.py` 和 `writers/smb_writer.py` 中保持一致：

| boundary_marker | 物理含义 | 对应 M3DC1 语义 |
|---|---|---|
| 1 | 最后闭合磁面（LCFS） | plasma-vacuum interface |
| 2 | 第一壁内表面 | wall inner surface |
| 3 | 外边界（计算域边界） | outer boundary |
| 0 | 内部节点（非边界） | — |

---

## 6. readers/gfile_reader.py 实现规范

### 6.1 EQDSK/GFile 文件格式说明

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

### 6.2 `read_gfile()` 函数接口

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

### 6.3 LCFS 边界预处理

从 GFile 提取的 LCFS 坐标可能存在以下问题，`gfile_reader.py` 必须处理：

1. **闭合性**：确保 LCFS 首尾点相同（若不同则追加首点到末尾）；
2. **方向性**：确保 LCFS 点按逆时针方向排列（若顺时针则反转）；
3. **重采样**：LCFS 点数可能过多或过少，`mesher/triangle_wrapper.py` 在调用 Triangle 前负责重采样。

---

## 7. mesher/triangle_wrapper.py 实现规范（TokaMaker/Triangle 唯一底座）

### 7.1 Triangle Python 包调用方式

LinkMesh 通过 `triangle` Python 包调用 Triangle 算法，封装风格参考 TokaMaker/OFT 的 `meshing.py`，不直接调用 C API，不引入第二种网格生成引擎。

```python
import triangle as tr

def generate_mesh(config: BoundaryConfig) -> Mesh2D:
    """调用 Triangle（TokaMaker/Triangle 唯一底座）生成二维非结构化三角网格。

    参数：
        config: BoundaryConfig 对象，包含边界点、线段、区域标记和质量参数

    返回：
        Mesh2D 对象，包含节点坐标、三角形连接表、区域标记和边界标记

    实现要点：
        1. 构造 Triangle 输入字典（参考 TokaMaker OFT 的 alpha 字典结构）
        2. 生成 Triangle 控制字符串（参考 OFT 的 "pqaAzQ"）
        3. 调用 tr.triangulate(input_dict, opts)
        4. 从输出字典提取各字段，构造 Mesh2D 对象
        5. 验证输出合法性（节点数 > 0，三角形数 > 0）
        6. 打印统计信息（节点数、三角形数、边界线段数）
    """
```

### 7.2 Triangle 输入字典构造

```python
# Triangle 输入字典格式（参考 TokaMaker OFT meshing.py 的 alpha 字典）
input_dict = {
    "vertices":        config.vertices,          # np.ndarray shape=(N, 2)，float64
    "segments":        config.segments,          # np.ndarray shape=(M, 2)，int32
    "segment_markers": config.segment_markers,   # np.ndarray shape=(M,)，int32
    "regions":         config.regions,           # np.ndarray shape=(K, 4)，float64
                                                 # 每行：[R, Z, region_id, max_area]
}
```

### 7.3 Triangle 控制字符串

```python
def _build_triangle_opts(config: BoundaryConfig) -> str:
    """构造 Triangle 控制字符串。

    控制字符含义（参考 TokaMaker triangle-library-integration/SKILL.md）：
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
    opts = "p"
    opts += f"q{config.min_angle:.1f}"
    if config.max_area is not None:
        opts += f"a{config.max_area}"
    opts += "AzQ"
    return opts
```

### 7.4 Triangle 输出字段提取

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

## 8. writers/hdf5_writer.py 实现规范（第一战役：TRIMEG HDF5 格式映射）

### 8.1 实现依据

`writers/hdf5_writer.py` 的实现以 `docs/trimeg/loadfemmesh_h5.m` 为唯一黄金标尺。所有 HDF5 数据集路径名、形状约定和索引转换规则，均以该脚本的 `h5read` 调用为准。详细字段清单见第 4.1 节。

### 8.2 `write_hdf5()` 函数接口

```python
import h5py
import numpy as np

def write_hdf5(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 TRIMEG 标准 HDF5 静态网格文件。

    以 docs/trimeg/loadfemmesh_h5.m 为黄金标尺，逐一对齐数据集路径与形状。

    参数：
        mesh: Mesh2D 对象（索引 0-based）
        filepath: 输出 .h5 文件路径

    实现要点：
        1. 使用 h5py 创建 HDF5 文件（mode='w'，覆盖已有文件）
        2. 写入 /femmesh/nvert、ntria、nvert_in、nvert_ex 标量
        3. 写入 /femmesh/vert：shape=(2, nvert)，Fortran 列优先存储
           （MATLAB h5read 后转置得到 (nvert, 2)）
        4. 写入 /femmesh/idxivert、idxevert：内部/边界节点全局索引，1-based
        5. 写入 /femmesh/tria：shape=(4, ntria)，Fortran 列优先存储
           前3行为三角形三顶点节点索引（1-based），第4行为 region_id
           （MATLAB h5read 后转置得到 (ntria, 4)）
        6. 写入 /femmesh/nbcRZ、Rbc、Zbc：边界节点坐标
        7. 写入完成后打印验证信息（节点数、三角形数）
    """
```

---

## 9. writers/smb_writer.py 实现规范（第二战役：PUMI .smb 二进制逆向）

### 9.1 实现依据与前置条件

`writers/smb_writer.py` 的实现依赖对 `SCOREC/PUMI` 开源 C++ 源码的只读侦察结果。**在侦察任务完成并经主管确认前，本模块保持占位实现，严禁提前编写任何字节流打包逻辑。**

侦察目标文件（只读，严禁修改）：
- `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`：`.smb` 文件读取的 C++ 实现入口
- `M3DC1/m3dc1_scorec/include/m3dc1_model.h`：model `.txt` 配套文件格式
- `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`：高阶节点需求确认

### 9.2 `write_smb()` 函数接口（占位规范）

```python
def write_smb(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 PUMI .smb 静态二进制网格文件。

    参数：
        mesh: Mesh2D 对象
        filepath: 输出 .smb 文件路径

    【重要】：本函数的具体实现必须等待以下侦察任务完成后方可编写：
        1. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc
           → 逆向推导 .smb 文件的完整二进制字节流格式
        2. 只读侦察 M3DC1/m3dc1_scorec/include/m3dc1_model.h
           → 确认 model .txt 文件格式（配套输出）
        3. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_field.cc
           → 确认是否需要在写出前生成边中点（高阶节点）

    侦察完成后，使用 Python struct 模块按逆向得到的字节流协议打包写出。

    当前占位实现：
        raise NotImplementedError(
            "smb_writer 尚待完成 PUMI .smb 格式逆向侦察后实现。"
            "请参考 LinkMesh_Architecture_Plan.md 第 4.2 节和第 9 节。"
        )
    """
```

### 9.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。`writers/smb_writer.py` 在写出 `.smb` 文件时，应同时写出配套的 model `.txt` 文件。

**【待源码确认】**：model `.txt` 文件的具体格式需通过只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` 确认。

---

## 10. utils/plotter.py 实现规范

### 10.1 `plot_mesh()` 函数接口

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

## 11. requirements.txt 依赖清单

```text
# LinkMesh Python 依赖清单
# 使用 pip install -r requirements.txt 安装

# 核心科学计算
numpy>=1.24.0

# Triangle 网格生成（TokaMaker/Triangle 唯一底座）
triangle>=20230923

# HDF5 文件读写（第一战役：TRIMEG HDF5 格式映射）
h5py>=3.8.0

# 可视化自检
matplotlib>=3.7.0

# 开发与测试（可选）
pytest>=7.0.0
```

---

## 12. 敏捷渐进里程碑（MVP 开发阶段）

**【铁律】开发时序严格锁死：先完成 M3（TRIMEG HDF5 闭环验证），确认 TokaMaker 生成的网格几何物理质量完全合格后，再进军 M4（PUMI .smb 二进制逆向）。严禁跳序。**

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

**目标**：能够从 LCFS 边界调用 TokaMaker/Triangle 唯一底座生成二维三角网格并可视化。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --plot mesh_check.png` 能够运行；
2. 生成的 `mesh_check.png` 中三角网格覆盖 LCFS 内部区域，无明显退化三角形；
3. 终端打印：`节点数: N，三角形数: T，边界线段数: S`；
4. `Mesh2D` 对象的所有字段均已正确填充；
5. 所有三角形的最小内角 ≥ 设定的 `min_angle` 参数值。

**涉及模块**：`mesher/triangle_wrapper.py`，`utils/plotter.py`（完整版）

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步，第一战役闭环）

**目标**：将 TokaMaker/Triangle 生成的三角网格写出为 TRIMEG 可消费的 HDF5 文件，并通过 `loadfemmesh_h5.m` 读取验证，确认网格几何物理质量完全合格。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --output mesh.h5` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开；
3. `h5py` 读取验证：`/femmesh/vert` shape=(2,N)，`/femmesh/tria` shape=(4,T)，`/femmesh/nvert`=N，`/femmesh/ntria`=T；
4. 使用 `loadfemmesh_h5.m` 在 MATLAB 中读取 `mesh.h5`，`femmesh.vert` shape=(N,2)，`femmesh.tria` shape=(T,4)，无报错；
5. 节点索引为 1-based（`femmesh.tria` 前3列最小值为 1，最大值为 N）；
6. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`。

**涉及模块**：`writers/hdf5_writer.py`

---

### 里程碑 M4：PUMI .smb 输出验收（P0 第四步，第二战役攻坚）

**目标**：在 M3 完全验收通过、网格质量确认合格后，将同一 `Mesh2D` 对象写出为 M3DC1 可消费的 PUMI `.smb` 静态二进制网格文件。

**前置条件**：
1. M3 里程碑已完全验收通过；
2. 已完成对 `m3dc1_mesh.cc`、`m3dc1_model.cc`、`m3dc1_field.cc` 的只读侦察；
3. 侦察结果已经主管确认，`.smb` 字节流格式已从【待源码确认】转为【已确认】。

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

## 13. 蓝图更新纪律

本文档是 LinkMesh 项目的单事实真理源。以下情况必须先更新本文档，再进入代码实现：

1. 新增或删除任何模块文件；
2. 修改任何数据结构的字段定义（`GFileData`、`BoundaryConfig`、`Mesh2D`）；
3. 修改区域标记或边界标记的整数约定；
4. 修改 HDF5 文件结构或数据集路径名；
5. 确认 `.smb` 二进制格式的任何细节（将【待源码确认】转为【已确认】）；
6. 新增任何 CLI 参数；
7. 调整任何里程碑的验收标准。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
