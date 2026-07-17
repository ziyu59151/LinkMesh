# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 v1.4
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源（Single Source of Truth）。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认事实】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
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
| 输入端 | 通过 OFT `GEQDSKEquilibrium` 或 `read_eqdsk` 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | **在 LinkMesh 侧手动执行复杂文本 I/O 与字符串切分解析 GFile**；复杂 CAD 输入；多区域高维输入 |
| 网格生成底座 | **唯一底座**：调用 `triangle` Python 包（TokaMaker `alpha`/`beta` 字典封装风格）生成二维非结构化三角网格 | 引入任何第二种网格生成引擎；三维棱柱/四面体生成；自适应网格细化算法 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 PUMI `.smb` 静态二进制网格文件 | 三维网格输出；其他求解器格式 |
| 可视化 | 基于 `matplotlib` 的简易画图自检 | 交互式可视化；三维渲染 |

---

## 1. MVP 物理目录树与职责矩阵

### 1.1 顶层目录结构

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。以下目录树为正式目录结构，所有模块路径均以此为准。

```text
LinkMesh/
├── pyproject.toml                     # 标准 Python 包安装元数据与控制台入口（见第 14 节）
├── cli.py                             # 【已废弃占位，实际入口在 src/linkmesh/cli.py】
├── CONTEXT.md                         # 敏捷开发纪律规范（只读）
├── LinkMesh_Architecture_Plan.md      # 本文档（单事实真理源）
├── History.md                         # 战术战果归档
├── requirements.txt                   # 服务器部署用直接依赖清单（见第 14.4 节）
├── .venv/                             # 独立虚拟环境（不入版本控制）
│
├── src/
│   └── linkmesh/                      # 正式 Python 包根目录
│       ├── __init__.py
│       ├── __main__.py                # python -m linkmesh 入口（仅调用 cli.main）
│       ├── cli.py                     # CLI 参数解析与主流程控制
│       │
│       ├── readers/
│       │   ├── __init__.py
│       │   └── gfile_reader.py        # GFile/EQDSK 读取 Adapter：薄封装 OFT GEQDSKEquilibrium
│       │
│       ├── mesher/
│       │   ├── __init__.py
│       │   └── triangle_wrapper.py    # TokaMaker/Triangle 唯一底座封装：生成二维三角网格
│       │
│       ├── writers/
│       │   ├── __init__.py
│       │   ├── hdf5_writer.py         # 第一战役：TRIMEG HDF5 静态网格写出器
│       │   └── smb_writer.py          # 第二战役：M3DC1 PUMI .smb 静态二进制网格写出器
│       │
│       └── utils/
│           ├── __init__.py
│           └── plotter.py             # matplotlib 可视化自检工具
│
├── tests/                             # 单元测试目录（M1～M3 验收测试）
│   ├── test_gfile_reader.py           # M1 验收测试：GFile 读取与 GFileData 字段验证
│   ├── test_triangle_wrapper.py       # M2 验收测试：Triangle 网格生成与 Mesh2D 字段验证
│   └── test_hdf5_writer.py            # M3 验收测试：HDF5 文件结构、索引与数据集验证
│
└── examples/
    ├── sample.geqdsk                  # 示例 GFile 平衡文件
    └── run_example.sh                 # 示例运行脚本
```

**注意**：
- `tests/` 目录当前尚不存在，需按 M1～M3 验收要求新建（见第 13 节）。
- 本轮不新增 `tests/test_smb_writer.py`，M4 开始前不创建该文件。
- 根目录下的 `cli.py` 为历史遗留占位文件，实际 CLI 入口为 `src/linkmesh/cli.py`。

### 1.2 模块职责矩阵

| 模块文件 | 核心职责 | 输入 | 输出 | 禁止事项 |
|---|---|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口：仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑 | `sys.argv`（透传） | 无（副作用：调用 `cli.main`） | 不得包含任何业务逻辑；不得直接操作文件；不得重复定义参数解析 |
| `src/linkmesh/cli.py` | 解析命令行参数；按顺序调用 reader → mesher → writer；捕获异常并打印友好错误信息 | `sys.argv` | 无（副作用：调用各模块） | 不得包含任何业务逻辑；不得直接操作文件 |
| `src/linkmesh/readers/gfile_reader.py` | **薄 Adapter（接线员）**：调用 OFT `GEQDSKEquilibrium` 读取 GFile，从返回对象属性中提取 LCFS 边界坐标、磁轴坐标、第一壁点集等，封装为 `GFileData` 对象 | GFile 文件路径（`str`） | `GFileData` dataclass | **绝对禁止**在 LinkMesh 侧手动执行任何原始 GFile 文本 I/O 与字符串切分；不得调用 Triangle；不得写文件 |
| `src/linkmesh/mesher/triangle_wrapper.py` | **唯一网格生成底座**：接收 `BoundaryConfig`；按 TokaMaker 风格构造 `alpha` 字典；调用 `triangle` Python 包生成二维三角网格；从 `beta` 字典提取输出；返回 `Mesh2D` 对象 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑；不得引入第二种生成引擎 |
| `src/linkmesh/writers/hdf5_writer.py` | **第一战役**：接收 `Mesh2D` 对象；严格对照 `docs/trimeg/loadfemmesh_h5.m` 黄金标尺，按 TRIMEG HDF5 规范写出 `.h5` 文件 | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑 |
| `src/linkmesh/writers/smb_writer.py` | **第二战役**：接收 `Mesh2D` 对象；通过逆向分析 SCOREC/PUMI 开源 C++ 源码的二进制字节流协议，用 Python `struct` 打包写出 M3DC1 可消费的 `.smb` 文件 | `Mesh2D` 对象，输出路径 | `.smb` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；未完成侦察前不得实现 |
| `src/linkmesh/utils/plotter.py` | 绘制 LCFS 边界与生成三角网格的叠加图；输出 `.png` 自检图；提供 `plot_lcfs_only()`（M1 最小可用版）和 `plot_mesh()`（M2 完整版）两个函数 | `GFileData`，`Mesh2D`，输出路径 | `.png` 文件（副作用） | 不得修改任何数据对象 |

---

## 2. 核心内存数据结构定义

### 2.1 `GFileData`：GFile 读取结果（OFT Adapter 输出）

【已确认事实】`GFileData` 是 `src/linkmesh/readers/gfile_reader.py` 这个薄 Adapter 的输出对象。其字段值**全部来自对 OFT `GEQDSKEquilibrium` 对象属性的直接提取**，LinkMesh 侧不执行任何原始文本解析。

相比旧草案，`GFileData` 已大幅精简，移除了 `nw`、`nh`、`rdim`、`zdim`、`rleft`、`zmid`、`simag`、`sibry`、`psi_grid`、`r_grid`、`z_grid`、`fpol`、`pres`、`qpsi` 等 14 个字段——这些字段由 OFT 内部管理，LinkMesh 无需重复存储。

【已确认事实】`current` 字段单位为安培（A），来源为 OFT `GEQDSKEquilibrium.Ip`，后者直接读取 EQDSK 文件中的 `CURRENT` 字段，全程不进行任何单位缩放。以 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 为例，服务器冒烟测试实测值为约 `1.56e7 A`（即约 15.6 MA），Python 类型为 `float`。

```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class GFileData:
    """GFile/EQDSK 平衡文件读取结果（OFT Adapter 输出）。

    所有字段均由 src/linkmesh/readers/gfile_reader.py 从 OFT GEQDSKEquilibrium 对象属性
    中直接提取，LinkMesh 侧不执行任何原始文本解析。

    所有坐标单位均为米（SI 单位制）。
    R 为大半径方向，Z 为垂直方向（托卡马克柱坐标系）。

    字段来源（对应 GEQDSKEquilibrium 属性名，来自 eqdsk.py 只读侦察）：
        lcfs_r   ← eq.boundary_R   (eqdsk.py 属性 boundary_R)
        lcfs_z   ← eq.boundary_Z   (eqdsk.py 属性 boundary_Z)
        rmaxis   ← eq.R_mag        (eqdsk.py 属性 R_mag)
        zmaxis   ← eq.Z_mag        (eqdsk.py 属性 Z_mag)
        wall_r   ← eq.limiter_R    (eqdsk.py 属性 limiter_R)，若为空则 None
        wall_z   ← eq.limiter_Z    (eqdsk.py 属性 limiter_Z)，若为空则 None
        rcentr   ← eq.R_center     (eqdsk.py 属性 R_center)
        bcentr   ← eq.B_center     (eqdsk.py 属性 B_center)
        current  ← eq.Ip           (eqdsk.py 属性 Ip)，单位 A，不缩放
    """

    # LCFS 边界坐标（最后闭合磁面）
    lcfs_r: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 R 坐标 [m]
    lcfs_z: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 Z 坐标 [m]

    # 磁轴坐标
    rmaxis: float                    # 磁轴 R 坐标 [m]
    zmaxis: float                    # 磁轴 Z 坐标 [m]

    # 第一壁点集（可选，若 GFile 不含则为 None）
    wall_r: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 R 坐标 [m]
    wall_z: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 Z 坐标 [m]

    # 基本平衡参数（可选，用于后续物理验证与可视化）
    rcentr: Optional[float] = None   # 参考大半径 R0 [m]
    bcentr: Optional[float] = None   # 参考磁场强度 B0 [T]
    current: Optional[float] = None  # 等离子体电流 Ip [A]，来源 eq.Ip，不缩放
                                     # ITER 样例实测值约 1.56e7 A（约 15.6 MA）
```

### 2.2 `BoundaryConfig`：Triangle 输入配置

【已确认事实】字段命名与 TokaMaker OFT `meshing.py` 中 `alpha` 字典的键名保持一致（`vertices`、`segments`、`regions`），这是 `src/linkmesh/mesher/triangle_wrapper.py` 构造 `alpha` 字典的直接来源。

```python
@dataclass
class BoundaryConfig:
    """Triangle 网格生成的输入配置。

    该对象由 src/linkmesh/cli.py 根据 GFileData 和用户参数构造，
    传递给 src/linkmesh/mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）。

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
    # region_id 约定：1=plasma, 2=vacuum, 3=wall（见第 5 节）
    regions: np.ndarray           # shape=(K, 4)，dtype=float64

    # 边界标记（对应 segments 的整数标记）
    # 标记约定：1=LCFS, 2=first_wall, 3=outer_boundary（见第 5 节）
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: Optional[float] = None  # 全局最大三角形面积约束（m²），None 表示不限制
```

### 2.3 `Mesh2D`：内存二维三角网格对象（唯一核心数据结构）

【已确认事实】`Mesh2D` 的字段命名与 TokaMaker `run_triangle` 函数返回字典的键名直接对应，已通过只读侦察 `TOKAMAKER/.../TokaMaker/meshing.py` 确认：

```python
@dataclass
class Mesh2D:
    """LinkMesh 核心内存网格对象。

    该对象是 src/linkmesh/mesher/triangle_wrapper.py（TokaMaker/Triangle 唯一底座）的输出，
    同时也是 src/linkmesh/writers/hdf5_writer.py 和 src/linkmesh/writers/smb_writer.py 的共同输入。
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
```

---

## 3. 数据流转架构（TokaMaker/Triangle 唯一底座 → 双向翻译分发）

### 3.1 完整数据管道

LinkMesh 的数据流是以 `src/linkmesh/mesher/triangle_wrapper.py`（TokaMaker/Triangle）为绝对核心的**单向分发映射结构**：上游唯一，下游双轨。

```text
GFile 平衡文本
  │
  ↓ [薄 Adapter：调用 OFT GEQDSKEquilibrium，提取边界坐标，绝不手动解析文本]
src/linkmesh/readers/gfile_reader.py
  │  ← from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium
  │  ← eq = GEQDSKEquilibrium(filepath)
  │  ← 提取 eq.boundary_R / eq.boundary_Z / eq.R_mag / eq.Z_mag 等属性
  │
  ↓ [封装为 GFileData，传递给 cli.py 构造 BoundaryConfig]
GFileData
  │
  ↓ [构造 alpha 字典，调用 Triangle 唯一底座]
src/linkmesh/mesher/triangle_wrapper.py
  │  ← alpha = dict(vertices=..., segments=..., regions=...)  [TokaMaker 风格]
  │  ← beta  = tr.triangulate(alpha, opts)
  │  ← 提取 beta['vertices'], beta['triangles'], beta['triangle_attributes'] 等
  │
  ↓ [生成统一内存网格对象]
Mesh2D  (内存核心数据结构，所有索引 0-based)
  │
  ├──→ [第一阶段战役：HDF5 映射对齐]
  │      src/linkmesh/writers/hdf5_writer.py
  │      (严格对照 docs/trimeg/loadfemmesh_h5.m 黄金标尺)
  │        │
  │        ↓
  │      TRIMEG 求解器消费的 HDF5 静态网格
  │
  └──→ [第二阶段战役：二进制字节流逆向]
         src/linkmesh/writers/smb_writer.py
         (逆向分析 scorec/pumi 开源 C++ 底层解析规范)
           │
           ↓
         M3DC1 求解器消费的 .smb 静态二进制网格
```

### 3.2 CLI 参数规范与调用方式

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数：

```text
# 方式 A：通过 python -m linkmesh（依赖 src/linkmesh/__main__.py）
python -m linkmesh [选项]

# 方式 B：通过控制台命令（依赖 pyproject.toml 中的 console_scripts 入口）
linkmesh [选项]
```

两种方式的参数规范完全相同：

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

本节是 LinkMesh 两大 Writer 模块的核心实现方法论，Aider 在编写 `src/linkmesh/writers/` 下任何代码前必须完整阅读本节。

### 4.1 第一战役：TokaMaker → TRIMEG HDF5 格式映射

**【已确认事实】战役定性**：HDF5 是通用开放格式，TRIMEG 侧已有现成的 MATLAB 读取脚本 `docs/trimeg/loadfemmesh_h5.m` 作为黄金对照标尺，格式完全透明可读。以下所有规范均直接从该脚本逐行逆向提取，无任何推断成分。

#### 4.1.1 转置规律（核心机制，必须理解）

【已确认事实】`loadfemmesh_h5.m` 中凡是末尾带 `.'`（非共轭转置运算符）的 `h5read` 调用，均说明该数组在 HDF5 文件中以 **Fortran 列优先（column-major）顺序**存储。

- MATLAB `h5read` 读取 HDF5 时，会将 C 行优先的存储顺序自动解释为 Fortran 列优先，因此读出的矩阵维度与 HDF5 中存储的维度**行列互换**。
- Python `h5py` 写入时，若要让 MATLAB 读取后得到 `(nvert, 2)` 的矩阵，必须在 HDF5 中存储 `(2, nvert)` 的数组。
- **实现公式**：`h5file.create_dataset(key, data=array.T)` —— 即写入前先转置。

涉及转置的字段：`/femmesh/vert`（需转置）、`/femmesh/tria`（需转置）。
不涉及转置的字段：所有标量、所有一维数组（`idxivert`、`idxevert`、`Rbc`、`Zbc` 等）。

#### 4.1.2 索引偏置规律（核心机制，必须理解）

【已确认事实】MATLAB 使用 1-based 索引，`Mesh2D` 内部使用 0-based 索引（Python 约定）。

凡是写入 HDF5 的**节点索引**字段，必须执行 `+1` 偏置转换：

- `mesh.triangles`（0-based）→ 写入 `/femmesh/tria` 前三行时 `+1` → 1-based
- `mesh.node_markers` 中内部节点的全局位置索引 → 写入 `/femmesh/idxivert` 时 `+1` → 1-based
- `mesh.node_markers` 中边界节点的全局位置索引 → 写入 `/femmesh/idxevert` 时 `+1` → 1-based

`region_id`（`/femmesh/tria` 第4行）**不需要** `+1`，它是物理标记值而非节点索引。

#### 4.1.3 完整字段映射契约（Field Mapping Contract）

以下表格是 `src/linkmesh/writers/hdf5_writer.py` 的唯一实现依据，每一行均为【已确认事实】，直接来自 `docs/trimeg/loadfemmesh_h5.m` 逐行解析。

| HDF5 数据集路径 | HDF5 中存储的 shape | MATLAB 读取后 shape | dtype | 数据来源（Python `Mesh2D` 字段） | 转换公式 |
|---|---|---|---|---|---|
| `/femmesh/nvert` | 标量 | 标量 | int32 | `mesh.n_nodes` | 无转换 |
| `/femmesh/ntria` | 标量 | 标量 | int32 | `mesh.n_triangles` | 无转换 |
| `/femmesh/nvert_in` | 标量 | 标量 | int32 | `np.sum(mesh.node_markers == 0)` | 无转换 |
| `/femmesh/nvert_ex` | 标量 | 标量 | int32 | `np.sum(mesh.node_markers != 0)` | 无转换 |
| `/femmesh/vert` | `(2, nvert)` | `(nvert, 2)` | float64 | `mesh.nodes`，列顺序 `[R, Z]` | **转置写入**：`mesh.nodes.T` |
| `/femmesh/idxivert` | `(nvert_in,)` | `(nvert_in,)` | int32 | 满足 `mesh.node_markers == 0` 的节点全局位置（0-based 下标） | **+1 偏置**：`np.where(mesh.node_markers == 0)[0] + 1` |
| `/femmesh/idxevert` | `(nvert_ex,)` | `(nvert_ex,)` | int32 | 满足 `mesh.node_markers != 0` 的节点全局位置（0-based 下标） | **+1 偏置**：`np.where(mesh.node_markers != 0)[0] + 1` |
| `/femmesh/tria` | `(4, ntria)` | `(ntria, 4)` | int32 | 前3行：`mesh.triangles`（节点索引）；第4行：`mesh.region_ids` | **前3行 +1 偏置 + 整体转置写入**：见下方详细说明 |
| `/femmesh/nbcRZ` | 标量 | 标量 | int32 | `np.sum(mesh.node_markers != 0)`（与 `nvert_ex` 相同） | 无转换 |
| `/femmesh/Rbc` | `(nbcRZ,)` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 0]`（边界节点的 R 坐标） | 无转换 |
| `/femmesh/Zbc` | `(nbcRZ,)` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 1]`（边界节点的 Z 坐标） | 无转换 |

#### 4.1.4 `/femmesh/tria` 的精确构造公式

【已确认事实】`/femmesh/tria` 是最复杂的字段，需要同时处理多列拼接、索引偏置和转置。精确构造步骤如下：

```python
# Step 1：将三角形连接表从 0-based 转换为 1-based
tria_nodes_1based = (mesh.triangles + 1).astype(np.int32)   # shape=(T, 3)

# Step 2：将 region_ids 扩展为列向量
region_col = mesh.region_ids.reshape(-1, 1).astype(np.int32)  # shape=(T, 1)

# Step 3：水平拼接，构造 (T, 4) 矩阵
# 列顺序：[node0_1based, node1_1based, node2_1based, region_id]
tria_4col = np.hstack([tria_nodes_1based, region_col])  # shape=(T, 4)

# Step 4：转置后写入 HDF5，使 HDF5 中存储为 (4, T)
# MATLAB h5read 后自动转置得到 (T, 4)，与 loadfemmesh_h5.m 期望一致
h5file.create_dataset('/femmesh/tria', data=tria_4col.T.astype(np.int32))
```

#### 4.1.5 可选字段处理规范

【已确认事实】`loadfemmesh_h5.m` 中 `nbcRZ`、`Rbc`、`Zbc` 三个字段被包裹在 `try...catch` 块中，读取失败时仅打印 warning 而不报错。这说明这三个字段在 TRIMEG 中是**可选字段**。

`src/linkmesh/writers/hdf5_writer.py` 的处理策略：**始终写出这三个字段**（因为 `Mesh2D` 中 `node_markers` 始终存在，边界节点坐标可以直接提取），不需要做条件判断。

### 4.2 第二战役：TokaMaker → M3DC1 PUMI .smb 二进制格式逆向

**【已确认事实】战役定性**：`.smb` 并非商业公司私有保密格式，而是开源 `SCOREC/PUMI` 库的通用二进制网格格式。这意味着我们可以通过只读侦察项目中已引入的 `m3dc1_scorec` 和 `scorec/pumi` 开源 C++ 源码，完整逆向推导出其二进制字节流协议。

**逆向方法**：

1. **侦察入口**：重点只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` 中读取 `.smb` 文件的 C++ 实现，以及 `scorec/pumi` 库中 `pumi_mesh_load` 的底层字节流解析逻辑。
2. **逆向目标**：从 C++ 读取代码中提取以下关键信息：
   - 文件头格式（魔数、版本号、维度、节点数、单元数等元数据的字节布局）
   - 字节序（Endianness：大端 vs 小端）
   - 数值精度（节点坐标 float32 vs float64；索引 int32 vs int64）
   - 拓扑排列顺序（节点坐标块、三角形连接块、区域标记块、边界标记块的先后顺序）
   - 索引约定（0-based vs 1-based）
3. **Python 实现**：在 `src/linkmesh/writers/smb_writer.py` 中使用 Python `struct` 模块，按逆向得到的字节流协议，将 `Mesh2D` 对象的各字段打包为对齐的二进制字节流并写出。
4. **前置条件**：`src/linkmesh/writers/smb_writer.py` 的具体实现**必须等待**只读侦察任务完成并经主管确认后方可开始编写。在侦察完成前，`write_smb()` 函数保持占位实现（`raise NotImplementedError`）。

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

LinkMesh 在当前 P0 阶段使用以下整数区域标记约定，该约定必须在 `BoundaryConfig.regions`、`Mesh2D.region_ids`、`src/linkmesh/writers/hdf5_writer.py` 和 `src/linkmesh/writers/smb_writer.py` 中保持一致：

| region_id | 物理含义 | 对应 M3DC1 语义 | 对应 TRIMEG 语义 |
|---|---|---|---|
| 1 | 等离子体区（plasma） | plasma region | plasma zone |
| 2 | 真空区（vacuum） | vacuum region | vacuum zone |
| 3 | 第一壁/导体区（wall/conductor） | resistive wall region | wall zone |

**注意**：当 GFile 不含第一壁信息时，LinkMesh 只生成 plasma 区（region_id=1）和 vacuum 区（region_id=2）。

### 5.2 边界标记（boundary_marker）约定

LinkMesh 在当前 P0 阶段使用以下整数边界标记约定，该约定必须在 `BoundaryConfig.segment_markers`、`Mesh2D.boundary_markers`、`src/linkmesh/writers/hdf5_writer.py` 和 `src/linkmesh/writers/smb_writer.py` 中保持一致：

| boundary_marker | 物理含义 | 对应 M3DC1 语义 |
|---|---|---|
| 1 | 最后闭合磁面（LCFS） | plasma-vacuum interface |
| 2 | 第一壁内表面 | wall inner surface |
| 3 | 外边界（计算域边界） | outer boundary |
| 0 | 内部节点（非边界） | — |

---

## 6. src/linkmesh/readers/gfile_reader.py 实现规范（OFT Adapter 模式）

### 6.1 设计原则：薄 Adapter，绝不重复造轮子

【已确认事实】`src/linkmesh/readers/gfile_reader.py` 的唯一职责是作为**薄 Adapter（接线员）**：

1. 调用 OFT（OpenFUSIONToolkit）提供的 `GEQDSKEquilibrium` 类读取 GFile；
2. 从 OFT 返回对象的属性中提取 LinkMesh 所需的字段；
3. 封装为 `GFileData` 对象返回。

**【绝对禁止】** 在 `src/linkmesh/readers/gfile_reader.py` 中手动执行任何原始 GFile 文本 I/O、字符串切分、Fortran 格式化数值解析或 EQDSK 格式字段手动提取。OFT 已经提供了完整、经过验证的 GFile 解析实现，LinkMesh 直接复用即可。

### 6.2 OFT 运行依赖（已确认事实）

【已确认事实】以下 OFT 版本已在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证：

```text
openfusiontoolkit==26.6
```

**版本约定**：
- 当前记录的经过真实验证的版本为 `openfusiontoolkit==26.6`，不得写成 `>=26.6`，不得声称其他版本已经验证。
- 最终运行安装**不要求**携带整个 `TOKAMAKER/` 源码树；`TOKAMAKER/` 继续作为开发期绝对只读参考区，不参与运行时依赖。

### 6.3 PYTHONPATH 规则（已确认事实，铁律）

【已确认事实】以下 PYTHONPATH 规则来自服务器冒烟测试中的实际故障排查，必须严格遵守：

**【绝对禁止】** 将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境的 `PYTHONPATH`。该路径下的 OFT 源码快照**不包含编译后的 `liboftpy.so`**，若加入 PYTHONPATH 会遮蔽 `site-packages` 中带有 `liboftpy.so` 的正式安装包，导致 `ImportError`。

**开发期临时规则**：
- 标准安装完成后（`pip install -e .` 或 `pip install .`），最终用户**不应**依靠手动设置 PYTHONPATH 来发现 LinkMesh。
- 开发期尚未安装时，可以临时将仓库 `src/` 目录加入 PYTHONPATH（`export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH`），但**绝对不得**同时加入 `TOKAMAKER/OpenFUSIONToolkit/src/python`。

```bash
# 正确：开发期临时将 src/ 加入 PYTHONPATH
export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH

# 错误：绝对禁止将 OFT 源码路径加入 PYTHONPATH
# export PYTHONPATH=/path/to/TOKAMAKER/OpenFUSIONToolkit/src/python:$PYTHONPATH  # 禁止！
```

### 6.4 OFT 可用 API 清单（已确认事实）

【已确认事实】以下两个 OFT API 均可用于读取 GFile，来源为只读侦察 `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/eqdsk.py`，并已通过 `openfusiontoolkit==26.6` 官方 wheel 在服务器上验证可导入：

#### 方案 A：`read_eqdsk`（轻量字典接口）

```python
# 来源：TOKAMAKER/.../TokaMaker/eqdsk.py 底部 read_geqdsk 便捷函数
from OpenFUSIONToolkit.TokaMaker.eqdsk import read_geqdsk

g = read_geqdsk(filepath)
# g 是一个字典，已确认的键（来自 _read_geqdsk 函数）：
#   g['RBBBS']  → LCFS 边界 R 坐标数组 [m]
#   g['ZBBBS']  → LCFS 边界 Z 坐标数组 [m]
#   g['RMAXIS'] → 磁轴 R 坐标 [m]
#   g['ZMAXIS'] → 磁轴 Z 坐标 [m]
#   g['RLIM']   → 第一壁 R 坐标数组 [m]
#   g['ZLIM']   → 第一壁 Z 坐标数组 [m]
```

#### 方案 B：`GEQDSKEquilibrium`（高级对象接口，属性更丰富）【当前采用】

```python
# 来源：TOKAMAKER/.../TokaMaker/eqdsk.py，GEQDSKEquilibrium 类
from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium

eq = GEQDSKEquilibrium(filepath)
# 已确认的属性（来自 eqdsk.py GEQDSKEquilibrium 类属性定义，只读侦察确认）：
#   eq.boundary_R   → LCFS 边界 R 坐标数组 [m]（属性 boundary_R，来自 _raw['RBBBS']）
#   eq.boundary_Z   → LCFS 边界 Z 坐标数组 [m]（属性 boundary_Z，来自 _raw['ZBBBS']）
#   eq.R_mag        → 磁轴 R 坐标 [m]（属性 R_mag，来自 _raw['RMAXIS']）
#   eq.Z_mag        → 磁轴 Z 坐标 [m]（属性 Z_mag，来自 _raw['ZMAXIS']）
#   eq.limiter_R    → 第一壁 R 坐标数组 [m]（属性 limiter_R，来自 _raw['RLIM']）
#   eq.limiter_Z    → 第一壁 Z 坐标数组 [m]（属性 limiter_Z，来自 _raw['ZLIM']）
#   eq.R_center     → 参考大半径 R0 [m]（属性 R_center，来自 _raw['RCENTR']）
#   eq.B_center     → 参考磁场强度 B0 [T]（属性 B_center，来自 _raw['BCENTR']）
#   eq.Ip           → 等离子体电流 Ip [A]（属性 Ip，来自 _raw['CURRENT']，不缩放）
```

**当前采用方案 B**（`GEQDSKEquilibrium`），因为其属性命名语义清晰，且已提供 `boundary_R`/`boundary_Z`、`limiter_R`/`limiter_Z`、`R_mag`/`Z_mag` 等 LinkMesh 直接需要的字段，无需额外键名猜测。

### 6.5 `read_gfile()` 函数接口（已实现）

【已确认事实】以下为 `src/linkmesh/readers/gfile_reader.py` 中已实现的函数签名与核心逻辑：

```python
from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium
import numpy as np

def read_gfile(filepath: str) -> GFileData:
    """读取 GFile/EQDSK 平衡文件，提取 LinkMesh 所需的边界信息。

    实现策略：薄 Adapter 模式。
    直接调用 OFT GEQDSKEquilibrium 读取 GFile，从其属性中提取字段，
    封装为 GFileData 对象。LinkMesh 侧不执行任何原始文本解析。

    参数：
        filepath: GFile 文件路径（字符串）

    返回：
        GFileData 对象

    异常：
        FileNotFoundError: 文件不存在（由 GEQDSKEquilibrium 内部抛出）
        ValueError: 文件格式不符合 EQDSK 规范（由 GEQDSKEquilibrium 内部抛出）
        ImportError: OFT 未安装或不在 PYTHONPATH 中
    """
    eq = GEQDSKEquilibrium(filepath)
    # 提取 LCFS 坐标 → 闭合性检查 → 逆时针方向检查 → 封装 GFileData
    ...
```

### 6.6 LCFS 边界后处理（LinkMesh 侧唯一允许的后处理）

从 OFT 提取的 LCFS 坐标可能存在以下问题，`src/linkmesh/readers/gfile_reader.py` 必须处理（这是 LinkMesh 侧唯一允许的后处理逻辑，不属于原始文本解析）：

1. **闭合性**（`_ensure_lcfs_closed`）：确保 LCFS 首尾点相同。使用相对容差（首尾点距离 < 总周长的 0.1%）判断，若不满足则追加首点到末尾。
2. **方向性**（`_ensure_lcfs_ccw`）：使用 Shoelace 公式计算有向面积，若为负值（顺时针）则反转数组为逆时针。
3. **重采样**：LCFS 点数可能过多或过少，`src/linkmesh/mesher/triangle_wrapper.py` 在调用 Triangle 前负责重采样（非 `gfile_reader.py` 职责）。

---

## 7. src/linkmesh/mesher/triangle_wrapper.py 实现规范（TokaMaker/Triangle 唯一底座）

### 7.1 Triangle Python 包调用方式与 TokaMaker 风格对齐

【已确认事实】LinkMesh 通过 `triangle` Python 包调用 Triangle 算法。封装风格**严格参考** TokaMaker/OFT 的 `meshing.py` 中 `run_triangle` 函数与 `Mesh.get_mesh` 方法的实现模式（只读侦察 `meshing.py` 确认）：

```python
# TokaMaker 原始调用模式（只读参考，不得修改）：
alpha = dict(vertices=self._resampled_points, segments=resampled_flat, regions=self._reg_defs)
beta = run_triangle(alpha)
regions = beta['triangle_attributes'].astype('int32').ravel()
# beta['vertices']  → 节点坐标
# beta['triangles'] → 三角形连接表
# beta['triangle_attributes'] → 三角形区域属性
```

LinkMesh 的 `triangle_wrapper.py` 使用 Python `triangle` 包（`tr.triangulate`）复现相同的调用模式，返回字典键名与 TokaMaker `run_triangle` 返回值一致。

### 7.2 Triangle 输入字典构造（TokaMaker alpha 字典风格）

【已确认事实】以下为已实现的 `alpha` 字典构造方式，键名严格对齐 TokaMaker `meshing.py`：

```python
# Triangle 输入字典格式（严格对齐 TokaMaker OFT meshing.py 的 alpha 字典）
alpha = {
    "vertices":        np.ascontiguousarray(config.vertices, dtype=np.float64),
    "segments":        np.ascontiguousarray(config.segments, dtype=np.int32),
    "segment_markers": np.ascontiguousarray(config.segment_markers, dtype=np.int32),
    "regions":         np.ascontiguousarray(config.regions, dtype=np.float64),
}
```

### 7.3 Triangle 控制字符串

【已确认事实】控制字符串参考 TokaMaker `meshing.py` 中的 `b'pqaAzQ'`，已实现的 `_build_triangle_opts` 函数：

```python
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
    """
    opts = "p"
    opts += f"q{config.min_angle:.1f}"
    if config.max_area is not None:
        opts += f"a{config.max_area:.6g}"
    opts += "AzQ"
    return opts
```

### 7.4 Triangle 输出字段提取（从 beta 字典到 Mesh2D）

【已确认事实】以下字段提取方式与 TokaMaker `run_triangle` 返回值的键名完全对齐，已在 `generate_mesh()` 中完整实现：

```python
beta = tr.triangulate(alpha, opts)

mesh = Mesh2D(
    nodes=beta["vertices"].astype(np.float64),
    triangles=beta["triangles"].astype(np.int32),
    region_ids=beta["triangle_attributes"].squeeze().astype(np.int32),
    boundary_segments=beta.get("segments", np.zeros((0, 2), dtype=np.int32)).astype(np.int32),
    boundary_markers=np.asarray(
        beta.get("segment_markers", np.zeros((0,), dtype=np.int32)),
        dtype=np.int32
    ).squeeze(),
    node_markers=np.asarray(
        beta.get("vertex_markers", np.zeros((len(beta["vertices"]),), dtype=np.int32)),
        dtype=np.int32
    ).squeeze(),
)
```

**注意**：Python `triangle` 包（`tr.triangulate`）的返回字典键名与 TokaMaker `run_triangle` 返回字典键名一致（`vertices`、`triangles`、`triangle_attributes`），这是选择该包的重要原因之一。

---

## 8. src/linkmesh/writers/hdf5_writer.py 实现规范（第一战役：TRIMEG HDF5 格式映射）

### 8.1 实现依据与黄金标尺

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 的唯一实现依据是 `docs/trimeg/loadfemmesh_h5.m`。该脚本是 TRIMEG 求解器读取网格 HDF5 文件的 MATLAB 实现，其每一行 `h5read` 调用直接揭示了 TRIMEG 对 HDF5 文件结构的期望。所有数据集路径名、存储形状、数据类型和索引约定均以该脚本为最终裁决依据，不得凭推断自行补充。

### 8.2 TRIMEG HDF5 物理文件结构树

【已确认事实】以下结构树直接来自 `loadfemmesh_h5.m` 逐行解析，所有字段均为已确认事实：

```text
mesh.h5
└── /femmesh/                          # 唯一顶层组，名称固定为 "femmesh"
    │
    ├── nvert        [标量, int32]      # 节点总数 N
    ├── ntria        [标量, int32]      # 三角形总数 T
    ├── nvert_in     [标量, int32]      # 内部节点数（node_markers == 0 的节点数）
    ├── nvert_ex     [标量, int32]      # 边界节点数（node_markers != 0 的节点数）
    │
    ├── vert         [shape=(2,N), float64]   # 节点坐标，HDF5 中存 (2,N)
    │                                          # MATLAB h5read 后转置得 (N,2)
    │                                          # 行顺序：第0行=R坐标，第1行=Z坐标
    │
    ├── idxivert     [shape=(nvert_in,), int32]  # 内部节点全局索引，1-based
    ├── idxevert     [shape=(nvert_ex,), int32]  # 边界节点全局索引，1-based
    │
    ├── tria         [shape=(4,T), int32]     # 三角形数据，HDF5 中存 (4,T)
    │                                          # MATLAB h5read 后转置得 (T,4)
    │                                          # 列顺序：列0-2=节点索引(1-based)
    │                                          #         列3=region_id（无偏置）
    │
    ├── nbcRZ        [标量, int32]      # 边界节点坐标点数（等于 nvert_ex）
    ├── Rbc          [shape=(nbcRZ,), float64]  # 边界节点 R 坐标 [m]（始终写出）
    └── Zbc          [shape=(nbcRZ,), float64]  # 边界节点 Z 坐标 [m]（始终写出）
```

### 8.3 精确字段映射契约（Field Mapping Contract）

【已确认事实】以下每一行均为从 `loadfemmesh_h5.m` 直接提取的确凿映射规则，`write_hdf5()` 已按此完整实现：

| HDF5 路径 | HDF5 存储 shape | dtype | Python 计算表达式 | 转换说明 |
|---|---|---|---|---|
| `/femmesh/nvert` | 标量 | int32 | `np.int32(mesh.n_nodes)` | 无转换 |
| `/femmesh/ntria` | 标量 | int32 | `np.int32(mesh.n_triangles)` | 无转换 |
| `/femmesh/nvert_in` | 标量 | int32 | `np.int32(np.sum(mesh.node_markers == 0))` | 无转换 |
| `/femmesh/nvert_ex` | 标量 | int32 | `np.int32(np.sum(mesh.node_markers != 0))` | 无转换 |
| `/femmesh/vert` | `(2, N)` | float64 | `mesh.nodes.T.astype(np.float64)` | **转置**：Python 中 `nodes` 为 `(N,2)`，转置后写入得 `(2,N)` |
| `/femmesh/idxivert` | `(nvert_in,)` | int32 | `(np.where(mesh.node_markers == 0)[0] + 1).astype(np.int32)` | **+1 偏置**：0-based 下标转 1-based 全局索引 |
| `/femmesh/idxevert` | `(nvert_ex,)` | int32 | `(np.where(mesh.node_markers != 0)[0] + 1).astype(np.int32)` | **+1 偏置**：0-based 下标转 1-based 全局索引 |
| `/femmesh/tria` | `(4, T)` | int32 | 见 §8.4 精确构造公式 | **+1 偏置（节点列）+ 转置** |
| `/femmesh/nbcRZ` | 标量 | int32 | `np.int32(np.sum(mesh.node_markers != 0))` | 无转换（等于 nvert_ex） |
| `/femmesh/Rbc` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 0].astype(np.float64)` | 无转换，提取边界节点 R 列 |
| `/femmesh/Zbc` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 1].astype(np.float64)` | 无转换，提取边界节点 Z 列 |

### 8.4 `/femmesh/tria` 精确构造公式

【已确认事实】已在 `write_hdf5()` 中完整实现：

```python
# Step 1：节点索引从 0-based 转换为 1-based
tria_nodes_1based = (mesh.triangles + 1).astype(np.int32)      # shape=(T, 3)

# Step 2：region_ids 扩展为列向量（不需要偏置，region_id 是物理标记非节点索引）
region_col = mesh.region_ids.reshape(-1, 1).astype(np.int32)   # shape=(T, 1)

# Step 3：水平拼接为 (T, 4) 矩阵
tria_4col = np.hstack([tria_nodes_1based, region_col])          # shape=(T, 4)

# Step 4：转置后写入 HDF5，HDF5 中存储为 (4, T)
grp.create_dataset("tria", data=tria_4col.T.astype(np.int32))
```

### 8.5 `write_hdf5()` 实现状态

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 中的 `write_hdf5(mesh, filepath, verbose=True)` 函数已**完整实现**（非占位），按 §8.3 映射契约逐一写出全部 11 个数据集，包括：

- 4 个标量元数据（`nvert`、`ntria`、`nvert_in`、`nvert_ex`）
- 转置写入的 `vert`（`mesh.nodes.T`）
- +1 偏置的 `idxivert`、`idxevert`
- +1 偏置 + 转置的 `tria`（`tria_4col.T`）
- 始终写出的 `nbcRZ`、`Rbc`、`Zbc`

函数签名：`write_hdf5(mesh: Mesh2D, filepath: str, verbose: bool = True) -> None`

---

## 9. src/linkmesh/writers/smb_writer.py 实现规范（第二战役：PUMI .smb 二进制逆向）

### 9.1 实现依据与前置条件

`src/linkmesh/writers/smb_writer.py` 的实现依赖对 `SCOREC/PUMI` 开源 C++ 源码的只读侦察结果。**在侦察任务完成并经主管确认前，本模块保持占位实现，严禁提前编写任何字节流打包逻辑。**

侦察目标文件（只读，严禁修改）：
- `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`：`.smb` 文件读取的 C++ 实现入口
- `M3DC1/m3dc1_scorec/include/m3dc1_model.h`：model `.txt` 配套文件格式
- `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`：高阶节点需求确认

### 9.2 `write_smb()` 函数接口（占位，待 M4 里程碑实现）

【已确认事实】当前 `write_smb()` 保持 `raise NotImplementedError` 占位实现，同时定义了 `_write_model_txt()` 内部函数占位（同样为 `raise NotImplementedError`）。

```python
def write_smb(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 PUMI .smb 静态二进制网格文件。

    【重要】：本函数的具体实现必须等待以下侦察任务完成后方可编写：
        1. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc
        2. 只读侦察 M3DC1/m3dc1_scorec/include/m3dc1_model.h
        3. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_field.cc
    前置条件：M3 里程碑必须先完全验收通过。
    """
    raise NotImplementedError(...)
```

### 9.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。`src/linkmesh/writers/smb_writer.py` 在写出 `.smb` 文件时，应同时写出配套的 model `.txt` 文件。

**【待源码确认】**：model `.txt` 文件的具体格式需通过只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` 中 `load_model` 函数确认。从已侦察的 `m3dc1_model.cc` 可知，文件头格式为：

```text
numL separatrixLoop innerWallLoop outerWallLoop vacuumLoop
```

后续每个 loop 的顶点与边的详细格式待进一步侦察确认。

---

## 10. src/linkmesh/utils/plotter.py 实现规范

### 10.1 已实现的两个函数

【已确认事实】`src/linkmesh/utils/plotter.py` 已完整实现以下两个函数：

#### `plot_lcfs_only(gfile_data, filepath)`（M1 最小可用版本）

仅绘制 LCFS 边界曲线，用于 M1 里程碑验收。功能：
- 绘制 LCFS 边界曲线（红色实线）
- 若有第一壁数据，叠加绘制（蓝色虚线）
- 标注磁轴位置（红色叉号）
- 输出统计信息文本框（LCFS 点数、磁轴坐标）
- 保存为 PNG 文件，dpi=150

#### `plot_mesh(gfile_data, mesh, filepath, show_boundary_markers=True, show_region_ids=False)`（M2 完整版本）

绘制 LCFS 边界与生成三角网格的叠加图。功能：
- 使用 `matplotlib.tri.Triangulation` 绘制三角网格线
- 若 `show_region_ids=True`，按区域 ID 着色填充（plasma=蓝、vacuum=绿、wall=黄）
- 叠加绘制 LCFS 边界曲线（红色实线）
- 若有第一壁数据，叠加绘制（蓝色虚线）
- 标注磁轴位置（红色叉号）
- 若 `show_boundary_markers=True`，用不同颜色标注边界线段类型
- 输出统计信息文本框（节点数、三角形数、边界线段数）
- 设置 `aspect='equal'`，保存为 PNG 文件，dpi=150

---

## 11. 依赖清单

### 11.1 核心运行依赖

```text
numpy>=1.24.0
triangle>=20230923
h5py>=3.8.0
matplotlib>=3.7.0
openfusiontoolkit==26.6
```

**说明**：
- `openfusiontoolkit==26.6` 为当前在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证的版本，不得写成 `>=26.6`，不得声称其他版本已经验证。
- OFT 通过 pip 安装官方 wheel 获取，**不依赖** `TOKAMAKER/` 源码树。
- `pyproject.toml` 和 `requirements.txt` 的核心运行依赖和版本约束必须保持一致（见第 14 节）。

### 11.2 开发与测试依赖（可选）

```text
pytest>=7.0.0
```

---

## 12. 敏捷渐进里程碑（MVP 开发阶段）

**【铁律】开发时序严格锁死：先完成 M3（TRIMEG HDF5 闭环验证），确认 TokaMaker 生成的网格几何物理质量完全合格后，再进军 M4（PUMI .smb 二进制逆向）。严禁跳序。**

### 里程碑 M1：GFile 读取验收（P0 第一步）

**当前状态**：【M1 Reader 核心链路冒烟测试成功，M1 正式验收尚未完成】

【已确认事实】服务器冒烟测试（liustation，`openfusiontoolkit==26.6`，`ITER_test.eqdsk`）已验证：
- 磁轴 R=6.3624 m，Z=0.5328 m
- LCFS 点数 64，首尾闭合
- 第一壁点数 153
- `current` ≈ 1.56e7 A（Python float，来源 `eq.Ip`，不缩放）

上述结果证明 M1 Reader 核心链路（`GEQDSKEquilibrium` 导入 + 字段提取）冒烟测试成功。**但 M1 正式验收尚未完成**，仍需完成以下项目：

**目标**：能够通过 OFT Adapter 从真实 GFile 文件中提取 LCFS 边界坐标并可视化。

**M1 正式验收标准**（尚未全部通过）：
1. `python -m linkmesh --gfile sample.geqdsk --no-hdf5 --no-smb --plot lcfs_check.png` 能够运行（需要 `src/linkmesh/__main__.py` 存在）；
2. 生成的 `lcfs_check.png` 中 LCFS 边界曲线闭合、方向正确；
3. 终端打印：`LCFS 点数: N，磁轴: (R=X.XX, Z=X.XX)`；
4. `GFileData` 对象的所有必填字段均已正确填充；
5. **`src/linkmesh/readers/gfile_reader.py` 中不存在任何手动文本解析逻辑，所有字段均来自 OFT `GEQDSKEquilibrium` 属性**；
6. `tests/test_gfile_reader.py` 中的 M1 自动测试全部通过。

**涉及模块**：`src/linkmesh/__main__.py`（已新建，git: 1fc04f8），`src/linkmesh/readers/gfile_reader.py`（OFT Adapter），`src/linkmesh/utils/plotter.py`（`plot_lcfs_only` 函数），`tests/test_gfile_reader.py`（需新建）

---

### 里程碑 M2：Triangle 网格生成验收（P0 第二步）

**当前状态**：【尚未完成服务器网格生成和质量验收】

**目标**：能够从 LCFS 边界调用 TokaMaker/Triangle 唯一底座生成二维三角网格并可视化。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --no-smb --plot mesh_check.png` 能够运行；
2. 生成的 `mesh_check.png` 中三角网格覆盖 LCFS 内部区域，无明显退化三角形；
3. 终端打印：`节点数: N，三角形数: T，边界线段数: S`；
4. `Mesh2D` 对象的所有字段均已正确填充；
5. 所有三角形的最小内角 ≥ 设定的 `min_angle` 参数值；
6. **`src/linkmesh/mesher/triangle_wrapper.py` 中 `alpha` 字典的键名为 `vertices`、`segments`、`regions`（TokaMaker 风格），`beta` 字典的提取键名为 `vertices`、`triangles`、`triangle_attributes`**；
7. **`src/linkmesh/cli.py` 中 `_build_boundary_config()` 已完整实现**（git: 994c415）：从 `GFileData.lcfs_r/lcfs_z` 等弧长重采样，构造 LCFS 线段、外边界矩形、可选第一壁线段，设置 plasma/vacuum 区域标记点，封装为 `BoundaryConfig`；
8. `tests/test_triangle_wrapper.py` 中的 M2 自动测试全部通过。

**涉及模块**：`src/linkmesh/mesher/triangle_wrapper.py`，`src/linkmesh/utils/plotter.py`（`plot_mesh` 函数），`src/linkmesh/cli.py`（`_build_boundary_config` 函数），`tests/test_triangle_wrapper.py`（需新建）

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步，第一战役闭环）

**当前状态**：【尚未完成 HDF5 结构、索引、11 个数据集和 MATLAB/TRIMEG 消费验证】

**目标**：将 TokaMaker/Triangle 生成的三角网格写出为 TRIMEG 可消费的 HDF5 文件，并通过 `loadfemmesh_h5.m` 读取验证，确认网格几何物理质量完全合格。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --output mesh.h5 --no-smb` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开；
3. `h5py` 读取验证：`/femmesh/vert` shape=`(2,N)`，`/femmesh/tria` shape=`(4,T)`，`/femmesh/nvert`=N，`/femmesh/ntria`=T；
4. 使用 `loadfemmesh_h5.m` 在 MATLAB 中读取 `mesh.h5`，`femmesh.vert` shape=`(N,2)`，`femmesh.tria` shape=`(T,4)`，无报错；
5. 节点索引为 1-based（`femmesh.tria(:,1:3)` 最小值为 1，最大值为 N）；
6. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`；
7. `tests/test_hdf5_writer.py` 中的 M3 自动测试全部通过。

**涉及模块**：`src/linkmesh/writers/hdf5_writer.py`（已完整实现），`tests/test_hdf5_writer.py`（需新建）

---

### 里程碑 M4：PUMI .smb 输出验收（P0 第四步，第二战役攻坚）

**当前状态**：【占位，待 M3 验收通过后开始】

**目标**：在 M3 完全验收通过、网格质量确认合格后，将同一 `Mesh2D` 对象写出为 M3DC1 可消费的 PUMI `.smb` 静态二进制网格文件。

**前置条件**：
1. M3 里程碑已完全验收通过；
2. 已完成对 `m3dc1_mesh.cc`、`m3dc1_model.cc`、`m3dc1_field.cc` 的只读侦察；
3. 侦察结果已经主管确认，`.smb` 字节流格式已从【待源码确认】转为【已确认事实】。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --smb mesh.smb --no-hdf5` 能够运行；
2. 生成的 `mesh.smb` 文件能被 M3DC1 的 `pumi_mesh_load` 顺畅读取（无报错）；
3. M3DC1 读取后能正确识别节点数、三角形数、区域标记和边界标记；
4. 终端打印：`.smb 写出完成：mesh.smb`。

**涉及模块**：`src/linkmesh/writers/smb_writer.py`（当前为占位实现）

---

### 里程碑 M5：完整 CLI 端到端验收（P0 完成）

**当前状态**：【占位，待 M4 验收通过后开始】

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

## 13. 测试目录规划（M1～M3 验收测试）

【已确认事实】实际仓库当前不存在 `tests/` 目录，需按以下规划新建。本轮不新增 `tests/test_smb_writer.py`，M4 开始前不创建该文件。

### 13.1 测试文件职责

| 测试文件 | 服务里程碑 | 核心验收内容 |
|---|---|---|
| `tests/test_gfile_reader.py` | M1 | 验证 `read_gfile()` 能正确读取 EQDSK 文件；`GFileData` 所有字段类型与形状正确；LCFS 首尾闭合；LCFS 方向为逆时针；`current` 单位为 A（不缩放）；`gfile_reader.py` 中无手动文本解析逻辑 |
| `tests/test_triangle_wrapper.py` | M2 | 验证 `generate_mesh()` 能从合法 `BoundaryConfig` 生成 `Mesh2D`；`Mesh2D` 所有字段类型与形状正确；三角形索引为 0-based；`region_ids` 取值在约定范围内；最小内角满足约束 |
| `tests/test_hdf5_writer.py` | M3 | 验证 `write_hdf5()` 写出的 HDF5 文件包含全部 11 个数据集；`/femmesh/vert` shape=`(2,N)`；`/femmesh/tria` shape=`(4,T)`；节点索引为 1-based；`region_id` 列无偏置；`nvert`/`ntria` 标量值正确 |

### 13.2 测试依赖

- 测试框架：`pytest>=7.0.0`
- M1 测试需要访问 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 作为测试 fixture（只读）
- M2/M3 测试可使用 M1 测试生成的 `GFileData` 作为上游 fixture，或使用最小合成 `BoundaryConfig`/`Mesh2D` 进行单元测试

---

## 14. 包安装与运行环境规范

### 14.1 src 布局与标准安装

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。仓库根目录需要 `pyproject.toml` 来支持标准 Python 包安装。

**`pyproject.toml` 的职责**：
1. 声明标准 Python 包元数据（名称、版本、描述、作者等）
2. 配置 src 布局的包发现（`packages = {find = {where = ["src"]}}`）
3. 声明控制台入口：`linkmesh = "linkmesh.cli:main"`
4. 声明正式运行依赖（与 `requirements.txt` 核心依赖保持一致）

**`pyproject.toml` 规划示例**（待实施时创建，本轮不创建）：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "linkmesh"
version = "0.1.0"
description = "轻量级托卡马克二维非结构网格转换命令行工具"
requires-python = ">=3.9"
dependencies = [
    "numpy>=1.24.0",
    "triangle>=20230923",
    "h5py>=3.8.0",
    "matplotlib>=3.7.0",
    "openfusiontoolkit==26.6",
]

[project.scripts]
linkmesh = "linkmesh.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### 14.2 `src/linkmesh/__main__.py` 规范

【已确认事实】`src/linkmesh/__main__.py` 已新建（git: 1fc04f8）。其唯一职责是使 `python -m linkmesh` 调用进入 `linkmesh.cli.main`。

**规范**：
- 文件内容极简，仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑
- 不得在 `__main__.py` 中重复定义 `argparse` 参数或任何业务函数

```python
# src/linkmesh/__main__.py
from linkmesh.cli import main

if __name__ == "__main__":
    main()
```

### 14.3 两种调用方式的等价性

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数，行为完全等价：

| 调用方式 | 依赖条件 | 入口路径 |
|---|---|---|
| `python -m linkmesh` | `src/linkmesh/__main__.py` 存在（已完成）；`src/` 在 PYTHONPATH 中或已安装 | `__main__.py` → `linkmesh.cli.main` |
| `linkmesh`（控制台命令） | `pyproject.toml` 中 `console_scripts` 已配置；包已通过 `pip install` 安装 | `linkmesh.cli:main` 直接调用 |

### 14.4 `pyproject.toml` 与 `requirements.txt` 的关系

- **`pyproject.toml`**：正式安装元数据与运行依赖依据。通过 `pip install .` 或 `pip install -e .` 安装时使用。
- **`requirements.txt`**：服务器部署用的直接依赖清单，适合 `pip install -r requirements.txt` 快速部署。
- **一致性要求**：两者的核心运行依赖和版本约束必须保持一致。当 `openfusiontoolkit` 版本约束更新时，两个文件必须同步修改。

### 14.5 PYTHONPATH 与安装规则汇总

【已确认事实】以下规则来自服务器冒烟测试实际故障排查，为铁律：

| 场景 | 规则 |
|---|---|
| 标准安装后（`pip install .`） | 最终用户不应依靠手动设置 PYTHONPATH 来发现 LinkMesh；`linkmesh` 控制台命令直接可用 |
| 开发期未安装时 | 可临时将仓库 `src/` 加入 PYTHONPATH：`export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH` |
| OFT 源码路径 | **绝对禁止**将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入任何运行环境的 PYTHONPATH；该路径下的源码快照不含 `liboftpy.so`，会遮蔽正式安装包导致 `ImportError` |
| OFT 运行依赖 | 通过 `pip install openfusiontoolkit==26.6` 获取官方 manylinux wheel；不依赖 `TOKAMAKER/` 源码树 |
| `TOKAMAKER/` 目录 | 继续作为开发期绝对只读参考区；不参与运行时依赖；不得修改其中任何文件 |

---

## 15. 蓝图更新纪律

本文档是 LinkMesh 项目的单事实真理源。以下情况必须先更新本文档，再进入代码实现：

1. 新增或删除任何模块文件；
2. 修改任何数据结构的字段定义（`GFileData`、`BoundaryConfig`、`Mesh2D`）；
3. 修改区域标记或边界标记的整数约定；
4. 修改 HDF5 文件结构或数据集路径名；
5. 确认 `.smb` 二进制格式的任何细节（将【待源码确认】转为【已确认事实】）；
6. 新增任何 CLI 参数；
7. 调整任何里程碑的验收标准；
8. **修改 OFT API 的调用方式（如从 `GEQDSKEquilibrium` 切换到 `read_eqdsk` 或反之，或新增/移除 OFT 依赖）**；
9. **修改 `openfusiontoolkit` 版本约束**（需同步更新 `pyproject.toml` 和 `requirements.txt`）；
10. **修改 `src/linkmesh/__main__.py` 的职责或内容**；
11. **修改 `pyproject.toml` 中的控制台入口或包发现配置**。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
