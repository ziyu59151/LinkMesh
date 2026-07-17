# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 v1.6（M2 区域简化批准 + 真实验收结果记录 + 区域传递契约建立）
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源（Single Source of Truth）。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认事实】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【计划新增】的内容为蓝图已批准、但尚未在仓库中创建的文件或目录；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
- 主要用途：本文档为 LinkMesh 项目的单事实真理源（Single Source of Truth），不作为人类泛读材料，专门用于指导 Aider 自动化编码、RAG 知识库精准检索以及下游模块的硬核参数对齐。凡 Aider 在执行编码、新建文件、修改具体业务代码前，必须查阅并严格对齐本文档。
- 场外架构师检索用途：当场外架构师需要判断 LinkMesh 某模块的职责边界、某数据结构的字段定义、某输出格式的对齐标准，或某开发阶段的验收条件时，应优先召回本文档。
- Aider 执行用途：Aider 必须以本文档为最高技术权威。编写任何 `.py` 业务源码前，必须先核对本文档对应章节的接口定义、数据结构字段和验收标准。如发现实际需求与本文档不符，必须先在对话中提出蓝图迭代建议，待主管确认并更新本文档后，方可动手编写代码。
- 修改前置条件：任何对本文档的修改，必须由人类主管在对话中明确确认后方可执行。Aider 严禁自发修改本文档中的接口定义、数据结构、验收标准或禁止事项。

### 修订记录

| 版本 | 修订摘要 |
|---|---|
| v1.5 | M1 验收写入；M2 契约校正（reshape(-1) 替代 squeeze()；mock 目标修正） |
| v1.6 | 批准含第一壁 DIII-D P0 默认三区域简化方案（region_id=1/2/3）；明确无可用壁轮廓降级两区域方案（region_id=1/2）；建立轻量的按表区域传递契约（Wrapper/Writer 不写死区域数）；补充区域种子几何条件与失败原则；记录 M2 自动测试 36/36 通过但真实 region_id=0 阻塞 M2 总体验收；保留 M4 Multi Region 侦察空间 |

---

## 0. LinkMesh 项目定位与 MVP P0 边界

### 0.1 项目定位

LinkMesh 是一个**独立命令行程序（CLI）**，专注于打通从**等离子体平衡文件（GFile/EQDSK）**提取边界，到基于**TokaMaker/Triangle 唯一底座**生成二维非结构三角网格，再将统一内存网格对象顺次翻译输出为**两大目标物理求解器静态网格文件**的完整工具链路。

LinkMesh 的网格生成底座**有且仅有**以下组合：TokaMaker/OFT 的封装思路（只读参考）+ Python `triangle` 包（运行时直接调用）+ Triangle 二维非结构化三角剖分算法。LinkMesh 当前运行时直接调用的是 Python `triangle` 包，而不是完整运行 TokaMaker 网格程序。`TOKAMAKER/` 继续作为封装方法和接口的只读参考源码，不是最终运行时网格生成依赖。

LinkMesh 的核心职责是作为"翻译官"：将 Python `triangle` 包生成的统一 `Mesh2D` 内存对象，准确翻译为两种目标格式：

1. **TRIMEG 消费的 HDF5 静态网格**（第一阶段战役，先易后难）
2. **M3DC1 消费的 PUMI `.smb` 静态二进制网格**（第二阶段战役，逆向攻坚，M3 完整验收后开始）

LinkMesh 不是通用网格中间件，不是插件框架，不是抽象适配层。它是一个能快速跑通、能被导师团队验收的独立命令行转换工具。

### 0.2 MVP P0 硬边界（铁律，不得突破）

| 维度 | P0 允许 | P0 禁止 |
|---|---|---|
| 输入端 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | **在 LinkMesh 侧手动执行复杂文本 I/O 与字符串切分解析 GFile**；复杂 CAD 输入；多区域高维输入 |
| 网格生成底座 | **唯一底座**：调用 Python `triangle` 包（对齐 TokaMaker `alpha`/`beta` 字典封装风格）生成二维非结构化三角网格 | 引入任何第二种网格生成引擎；三维棱柱/四面体生成；自适应网格细化算法 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 PUMI `.smb` 静态二进制网格文件（M4 阶段） | 三维网格输出；其他求解器格式 |
| 可视化 | 基于 `matplotlib` 的简易画图自检 | 交互式可视化；三维渲染 |

---

## 1. MVP 物理目录树与职责矩阵

### 1.1 当前仓库与本阶段目标目录结构

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。以下目录树区分了当前已存在的文件与蓝图批准但尚待实施的计划项。

```text
LinkMesh/
├── pyproject.toml                     # 【计划新增】标准 Python 包安装元数据与控制台入口（见第 14 节）
├── CONTEXT.md                         # 敏捷开发纪律规范（只读）
├── LinkMesh_Architecture_Plan.md      # 本文档（单事实真理源）
├── History.md                         # 战术战果归档
├── requirements.txt                   # 服务器部署用直接依赖清单（见第 14.4 节）
├── .venv/                             # 独立虚拟环境（不入版本控制）
│
├── src/
│   └── linkmesh/                      # 正式 Python 包根目录
│       ├── __init__.py
│       ├── __main__.py                # 已新建（git: 1fc04f8）：python -m linkmesh 入口（仅调用 cli.main）
│       ├── cli.py                     # CLI 参数解析与主流程控制
│       │
│       ├── readers/
│       │   ├── __init__.py
│       │   └── gfile_reader.py        # GFile/EQDSK 读取 Adapter：薄封装 OFT GEQDSKEquilibrium
│       │
│       ├── mesher/
│       │   ├── __init__.py
│       │   └── triangle_wrapper.py    # Python triangle 包唯一底座封装：生成二维三角网格
│       │
│       ├── writers/
│       │   ├── __init__.py
│       │   ├── hdf5_writer.py         # 第一战役：TRIMEG HDF5 静态网格写出器
│       │   └── smb_writer.py          # 第二战役占位：M3 验收后按侦察结果实现
│       │
│       └── utils/
│           ├── __init__.py
│           └── plotter.py             # matplotlib 可视化自检工具
│
├── tests/                             # 单元测试目录（M1～M3 验收测试）
│   ├── test_gfile_reader.py           # M1 验收测试（已通过，git: f52a75f）
│   ├── test_triangle_wrapper.py       # M2 验收测试（自动测试 36/36 通过；真实区域编号 BLOCKED，待修复）
│   └── test_hdf5_writer.py            # 【计划新增】M3 验收测试
│
└── examples/                          # 【计划新增】示例文件目录
    ├── sample.geqdsk                  # 【计划新增，待许可确认】示例 GFile 平衡文件
    └── run_example.sh                 # 【计划新增】示例运行脚本
```

**注意**：
- `examples/` 目录当前尚不存在，其中的 `sample.geqdsk` 来源和许可证待确认（见第 13.2 节）。
- `pyproject.toml` 当前尚不存在，待主管批准后创建（见第 14.1 节）。
- 本轮不新增 `tests/test_smb_writer.py`，M4 开始前不创建该文件。

### 1.2 模块职责矩阵

| 模块文件 | 核心职责 | 输入 | 输出 | 禁止事项 |
|---|---|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口：仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑 | `sys.argv`（透传） | 无（副作用：调用 `cli.main`） | 不得包含任何业务逻辑；不得直接操作文件；不得重复定义参数解析 |
| `src/linkmesh/cli.py` | 解析命令行参数；按顺序调用 reader → mesher → writer；捕获异常并打印友好错误信息 | `sys.argv` | 无（副作用：调用各模块） | 不得包含任何业务逻辑；不得直接操作文件 |
| `src/linkmesh/readers/gfile_reader.py` | **薄 Adapter（接线员）**：调用 OFT `GEQDSKEquilibrium` 读取 GFile，从返回对象属性中提取 LCFS 边界坐标、磁轴坐标、第一壁点集等，封装为 `GFileData` 对象 | GFile 文件路径（`str`） | `GFileData` dataclass | **绝对禁止**在 LinkMesh 侧手动执行任何原始 GFile 文本 I/O 与字符串切分；不得调用 Triangle；不得写文件 |
| `src/linkmesh/mesher/triangle_wrapper.py` | **唯一网格生成底座**：接收 `BoundaryConfig`；按 TokaMaker 风格构造 `alpha` 字典；调用 Python `triangle` 包生成二维三角网格；从 `beta` 字典提取输出；返回 `Mesh2D` 对象 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑；不得引入第二种生成引擎；**不得写死区域数量**；不得推断区域物理含义 |
| `src/linkmesh/writers/hdf5_writer.py` | **第一战役**：接收 `Mesh2D` 对象；严格对照 `docs/trimeg/loadfemmesh_h5.m` 黄金标尺，按 TRIMEG HDF5 规范写出 `.h5` 文件 | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；**不得重编号、偏置、压缩或排序 `region_ids`**；不得推断区域物理含义 |
| `src/linkmesh/writers/smb_writer.py` | **第二战役占位模块**：在 M3 完整验收及 SCOREC/PUMI/M3DC1 只读侦察完成后，按主管确认的实现路线将 `Mesh2D` 转换为 M3DC1 可消费的 `.smb`；当前不得锁定具体序列化方式；保持 `NotImplementedError` 占位 | `Mesh2D` 对象，输出路径 | `.smb` 文件（副作用，M4 实现后） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；M3 验收前不得实现任何字节流逻辑 |
| `src/linkmesh/utils/plotter.py` | 绘制 LCFS 边界与生成三角网格的叠加图；输出 `.png` 自检图；提供 `plot_lcfs_only()`（M1 最小可用版）和 `plot_mesh()`（M2 完整版）两个函数 | `GFileData`，`Mesh2D`，输出路径 | `.png` 文件（副作用） | 不得修改任何数据对象 |

---

## 2. 核心内存数据结构定义

### 2.1 `GFileData`：GFile 读取结果（OFT Adapter 输出）

【已确认事实】`GFileData` 是 `src/linkmesh/readers/gfile_reader.py` 这个薄 Adapter 的输出对象。其字段值**全部来自对 OFT `GEQDSKEquilibrium` 对象属性的直接提取**，LinkMesh 侧不执行任何原始文本解析。

相比旧草案，`GFileData` 已大幅精简，移除了 `nw`、`nh`、`rdim`、`zdim`、`rleft`、`zmid`、`simag`、`sibry`、`psi_grid`、`r_grid`、`z_grid`、`fpol`、`pres`、`qpsi` 等 14 个字段——这些字段由 OFT 内部管理，LinkMesh 无需重复存储。

【已确认事实】`current` 字段单位为安培（A），来源为 OFT `GEQDSKEquilibrium.Ip`，后者直接读取 EQDSK 文件中的 `CURRENT` 字段，全程不进行任何单位缩放。以 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 为例，服务器冒烟测试实测值为约 `1.56e7 A`（即约 15.6 MA），Python 类型为 `float`。以 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 为例，M1 正式验收实测值为 `493324.5 A`（约 0.49 MA），Python 类型为 `float`。

**关于 `wall_r` / `wall_z` 字段的物理含义说明**：

`GFileData.wall_r` 和 `wall_z` 为可选字段，表示输入 GFile 是否提供了可供 LinkMesh 使用的 limiter/第一壁二维轮廓。字段为 `None` 或空数组只表示"输入文件未提供可用壁轮廓"，**不表示物理装置不存在第一壁**。LinkMesh 不得在缺少壁几何时凭空推断真实壁形状。

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

    # LCFS 边界坐标（最后闭合磁面，plasma-vacuum interface）
    lcfs_r: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 R 坐标 [m]
    lcfs_z: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 Z 坐标 [m]

    # 磁轴坐标
    rmaxis: float                    # 磁轴 R 坐标 [m]
    zmaxis: float                    # 磁轴 Z 坐标 [m]

    # 第一壁/limiter 点集（可选）
    # 若 GFile 提供了可用壁轮廓则为数组，否则为 None
    # 字段为 None 只表示"输入文件未提供可用壁轮廓"，不表示物理装置不存在第一壁
    wall_r: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 R 坐标 [m]
    wall_z: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 Z 坐标 [m]

    # 基本平衡参数（可选，用于后续物理验证与可视化）
    rcentr: Optional[float] = None   # 参考大半径 R0 [m]
    bcentr: Optional[float] = None   # 参考磁场强度 B0 [T]
    current: Optional[float] = None  # 等离子体电流 Ip [A]，来源 eq.Ip，不缩放
                                     # ITER 样例实测值约 1.56e7 A（约 15.6 MA）
                                     # DIII-D 样例实测值约 4.93e5 A（约 0.49 MA）
```

### 2.2 `BoundaryConfig`：Triangle 输入配置

【已确认事实】字段命名与 TokaMaker OFT `meshing.py` 中 `alpha` 字典的键名保持一致（`vertices`、`segments`、`regions`），这是 `src/linkmesh/mesher/triangle_wrapper.py` 构造 `alpha` 字典的直接来源。`segment_markers` 字段用于保留 LCFS、第一壁和外边界的物理标签，与 `segments` 逐项对应，是 `alpha` 字典的必要组成部分（见第 7.2 节）。

**区域数量说明**：`BoundaryConfig.regions` 的行数由 `_build_boundary_config()` 根据输入是否提供有效壁轮廓动态决定（含壁时 3 行，无壁时 2 行），不在 Triangle Wrapper 或 Writer 中写死。

```python
@dataclass
class BoundaryConfig:
    """Triangle 网格生成的输入配置。

    该对象由 src/linkmesh/cli.py 根据 GFileData 和用户参数构造，
    传递给 src/linkmesh/mesher/triangle_wrapper.py（Python triangle 包唯一底座）。

    字段命名与 TokaMaker OFT meshing.py 中 alpha 字典的键名保持一致：
        alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)
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
    # region_id 约定：1=plasma, 2=vacuum, 3=equivalent outer/wall-conductor（见第 5 节）
    # max_area_hint=-1 表示不限制该区域面积（使用全局 max_area 约束）
    # 行数由 _build_boundary_config() 根据输入动态决定，不写死
    regions: np.ndarray           # shape=(K, 4)，dtype=float64，K 由输入决定

    # 边界标记（对应 segments 的整数标记，与 segments 逐项对应）
    # 对应 Triangle alpha 字典的 'segment_markers' 键
    # 标记约定：1=LCFS, 2=first_wall/limiter, 3=outer_boundary（见第 5 节）
    segment_markers: np.ndarray   # shape=(M,)，dtype=int32

    # Triangle 质量控制参数
    min_angle: float = 20.0       # 最小三角形内角（度），默认 20°
    max_area: Optional[float] = None  # 全局最大三角形面积约束（m²），None 表示不限制
```

### 2.3 `Mesh2D`：内存二维三角网格对象（唯一核心数据结构）

【已确认事实】`Mesh2D` 的字段命名与 TokaMaker `run_triangle` 函数返回字典的键名直接对应，已通过只读侦察 `TOKAMAKER/.../TokaMaker/meshing.py` 确认。

**一维数组 shape 契约**（v1.5 校正）：`region_ids`、`boundary_markers`、`node_markers` 均为严格一维数组。提取时使用 `.reshape(-1)` 而非 `.squeeze()`，以保证即使 `T==1`、`S==1` 或 `N==1` 时仍得到 shape `(T,)`、`(S,)`、`(N,)` 的一维数组，而非 shape `()` 的零维数组。

```python
@dataclass
class Mesh2D:
    """LinkMesh 核心内存网格对象。

    该对象是 src/linkmesh/mesher/triangle_wrapper.py（Python triangle 包唯一底座）的输出，
    同时也是 src/linkmesh/writers/hdf5_writer.py 和 src/linkmesh/writers/smb_writer.py 的共同输入。
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
    """
    # 节点坐标
    # 来源：beta['vertices']，shape=(N, 2)
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64

    # 三角形连接表（三角形顶点索引，逆时针方向）
    # 来源：beta['triangles']，shape=(T, 3)
    # 索引为 0-based（Triangle 'z' 标志保证）
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，dtype=int32

    # 三角形区域标记（来自 Triangle triangleattributelist / beta['triangle_attributes']）
    # 约定：1=plasma, 2=vacuum, 3=equivalent outer/wall-conductor（见第 5 节）
    # 提取：np.asarray(beta['triangle_attributes'], dtype=np.int32).reshape(-1)
    # 全局区域传递契约：编号必须全部来自 BoundaryConfig.regions[:,2] 显式配置的非零物理编号
    # 不得出现 region_id=0（Triangle 默认属性，不是合法 P0 物理区域）
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，dtype=int32

    # 边界线段连接表
    # 来源：beta['segments']，shape=(S, 2)
    # 索引为 0-based（Triangle 'z' 标志保证）
    boundary_segments: np.ndarray    # shape=(S, 2)，边界线段端点节点索引，dtype=int32

    # 边界线段标记（来自 Triangle segmentmarkerlist / beta['segment_markers']）
    # 约定：1=LCFS, 2=first_wall/limiter, 3=outer_boundary
    # 提取：np.asarray(beta['segment_markers'], dtype=np.int32).reshape(-1)
    boundary_markers: np.ndarray     # shape=(S,)，每条边界线段的标记，dtype=int32

    # 节点边界标记（来自 Triangle pointmarkerlist / beta['vertex_markers']）
    # 0=内部节点，非零=边界节点
    # 提取：np.asarray(beta['vertex_markers'], dtype=np.int32).reshape(-1)
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

## 3. 数据流转架构（Python triangle 包唯一底座 → 双向翻译分发）

### 3.1 完整数据管道

LinkMesh 的数据流是以 `src/linkmesh/mesher/triangle_wrapper.py`（Python `triangle` 包，对齐 TokaMaker 封装风格）为绝对核心的**单向分发映射结构**：上游唯一，下游双轨。

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
  ↓ [构造 alpha 字典，调用 Python triangle 包唯一底座]
  │  [_build_boundary_config() 根据是否有可用壁轮廓动态决定区域数（2 或 3）]
  │  [区域种子必须通过点在闭合多边形内外关系检查，不满足则停止并报错]
src/linkmesh/mesher/triangle_wrapper.py
  │  ← alpha = dict(vertices=..., segments=..., segment_markers=..., regions=...)
  │  ← beta  = tr.triangulate(alpha, opts)
  │  ← 提取 beta['vertices'], beta['triangles'], beta['triangle_attributes'] 等
  │  ← Wrapper 按契约传递区域，不推断区域物理含义，不写死区域数
  │
  ↓ [生成统一内存网格对象]
Mesh2D  (内存核心数据结构，所有索引 0-based，region_ids 不得含 0)
  │
  ├──→ [第一阶段战役：HDF5 映射对齐]
  │      src/linkmesh/writers/hdf5_writer.py
  │      (严格对照 docs/trimeg/loadfemmesh_h5.m 黄金标尺)
  │      (Writer 不重编号、偏置、压缩或排序 region_ids)
  │        │
  │        ↓
  │      TRIMEG 求解器消费的 HDF5 静态网格
  │
  └──→ [第二阶段战役：M3 验收后按侦察结果实现]
         src/linkmesh/writers/smb_writer.py
         (M3 完整验收后，只读侦察 SCOREC/PUMI/M3DC1 源码，
          按主管确认的实现路线转换；当前保持 NotImplementedError 占位)
           │
           ↓
         M3DC1 求解器消费的 .smb 静态二进制网格
```

### 3.2 CLI 参数规范与调用方式

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数：

```text
# 方式 A：通过 python -m linkmesh（依赖 src/linkmesh/__main__.py，已新建 git: 1fc04f8）
python -m linkmesh [选项]

# 方式 B：通过控制台命令（依赖 pyproject.toml 中的 console_scripts 入口，pyproject.toml 计划新增）
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

# Step 2：将 region_ids 扩展为列向量（不需要偏置，region_id 是物理标记非节点索引）
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

### 4.2 第二战役：M3DC1 `.smb` 格式——M3 验收后侦察确定实现路线

**【已确认事实】战役定性**：`.smb` 并非商业公司私有保密格式，而是开源 `SCOREC/PUMI` 库的通用二进制网格格式。这意味着我们可以通过只读侦察项目中已引入的 `m3dc1_scorec` 和 `scorec/pumi` 开源 C++ 源码，完整逆向推导出其格式协议。

**【铁律】M3 完整验收通过后，才能开始 M4 侦察与实现。在侦察完成并经主管确认前，`write_smb()` 保持 `NotImplementedError` 占位，不得锁定任何具体序列化方式。**

**侦察目标（M3 验收后执行）**：

1. **侦察入口**：重点只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` 中读取 `.smb` 文件的 C++ 实现，以及 `scorec/pumi` 库中 `pumi_mesh_load` 的底层解析逻辑。
2. **侦察目标**：从 C++ 读取代码中提取以下关键信息：
   - 文件头格式（魔数、版本号、维度、节点数、单元数等元数据的字节布局）
   - 字节序（Endianness：大端 vs 小端）
   - 数值精度（节点坐标 float32 vs float64；索引 int32 vs int64）
   - 拓扑排列顺序（节点坐标块、三角形连接块、区域标记块、边界标记块的先后顺序）
   - 索引约定（0-based vs 1-based）
   - MeshFile 与 ModelFile 的配对关系（见第 4.2.1 节）
3. **实现路线**：由侦察结果和主管确认决定，可能包括但不限于：
   - Python 二进制写出；
   - 调用 SCOREC/PUMI 官方 API；
   - 调用经确认的官方转换程序；
   - 其他由直接证据确认的方式。
4. **前置条件**：`src/linkmesh/writers/smb_writer.py` 的具体实现**必须等待** M3 完整验收通过、只读侦察任务完成并经主管确认后方可开始编写。

#### 4.2.1 M4 侦察线索（组内交流，非直接源码证据）

以下内容来自组内交流，记录为 M4 侦察线索，不得升级为已确认格式事实：

- M3DC1 可能存在 Multi Region 网格，区域数可能依装置、算例和 ModelFile 而变化；
- MeshFile 可能保存离散网格，ModelFile 可能保存边界/模型信息；
- 导体和线圈的完整含时物理功能可能有限。

M4 仍必须在 M3 完整通过后，对 MCD7 样例、官方文档、ModelFile、MeshFile 和 M3DC1/SCOREC/PUMI 源码进行只读侦察，确认区域数量、D1B、几何分类、索引、文件配对和 `.smb` 契约；不得据此提前实现 `.smb`。P0 默认三区域方案不得被外推为 M3DC1 永久固定三区域。

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
| 序列化方式 | Python 二进制写出或其他 | 【待侦察后由主管确认】 |
| MeshFile/ModelFile 配对 | 区域数量和 ModelFile 格式 | 【待源码确认，见 M4 侦察线索】 |

---

## 5. 区域标记与边界标记约定

### 5.1 P0 区域方案总览

LinkMesh P0 阶段采用**轻量的按表区域传递契约**：区域由 `BoundaryConfig.regions` 中的显式种子定义，Triangle 将每个三角形的区域属性写入 `Mesh2D.region_ids`，Wrapper 和 Writer 只按契约传递区域，不负责推断区域物理含义，不写死区域数量。

**P0 当前支持两种方案**，由 `_build_boundary_config()` 根据输入动态选择：

#### 方案 A：含有效第一壁轮廓的默认三区域方案（当前 DIII-D P0 验收方案）

当 GFile 提供有效、闭合且满足嵌套关系的第一壁/limiter 轮廓时，P0 默认计算域从内到外定义为：

| region_id | 物理含义 | 几何范围 | 对应 M3DC1 语义 | 对应 TRIMEG 语义 |
|---|---|---|---|---|
| 1 | plasma | LCFS 内部 | plasma region | plasma zone |
| 2 | vacuum | LCFS 外且第一壁内 | vacuum region | vacuum zone |
| 3 | equivalent outer/wall-conductor computational region | 第一壁外且人工 outer boundary 内 | 待 M4 侦察确认 | wall zone |

**重要说明**：`region_id=3` 是 P0 等效计算区域，只用于完成多区域网格翻译和接口验收，不代表真实导体厚度、材料、线圈或电路模型。人工 outer boundary 是 LinkMesh 构造的数值截断边界，不是 GFile 提供的真实装置外表面，不得将其解释成真实装置外壁。

#### 方案 B：无可用第一壁轮廓的降级两区域方案

若 GFile 未提供可用第一壁轮廓（`GFileData.wall_r` 为 `None` 或空），则 P0 降级为：

| region_id | 物理含义 | 几何范围 |
|---|---|---|
| 1 | plasma | LCFS 内部 |
| 2 | vacuum | LCFS 外且人工 outer boundary 内 |

**重要说明**：不生成 `region_id=3`，因为 LinkMesh 没有壁几何依据。该方案的含义只是"输入缺少可用壁轮廓"，不得写成"物理装置没有第一壁"。

### 5.2 区域标记（region_id）约定

| region_id | 物理含义 | 方案 A（含壁） | 方案 B（无壁） |
|---|---|---|---|
| 1 | plasma | ✅ | ✅ |
| 2 | vacuum | ✅ | ✅ |
| 3 | equivalent outer/wall-conductor computational region | ✅ | 不生成 |

**注意**：`region_id` 是物理标签，不得执行索引式 `+1` 偏置。`region_id=0` 是 Triangle 默认属性，不是合法 P0 物理区域，最终 `Mesh2D` 中不得出现。

### 5.3 边界标记（boundary_marker）约定

| boundary_marker | 物理含义 | 几何含义 |
|---|---|---|
| 1 | LCFS | plasma-vacuum interface；区域 1 与区域 2 的界面 |
| 2 | first wall/limiter | vacuum 与 P0 等效区域 3 的界面（仅方案 A） |
| 3 | outer boundary | LinkMesh 构造的人工数值截断边界；P0 计算域的数值外边界 |
| 0 | 内部节点（非边界） | — |

**注意**：`boundary_markers` 不得被清零、偏置或改写；Wrapper 规范化 shape/dtype 后必须保持原始物理编号。边界标记和区域编号不是一一对应的数组索引关系：`segment_markers` 标记几何曲线或界面，`region_ids` 标记二维三角形所属的计算区域，两者均为物理/几何标签。

### 5.4 全局区域传递契约

以下规则作为稳定契约，不把所有网格永久锁死为三区域：

1. `BoundaryConfig.regions` 每行仍为 `[R, Z, region_id, max_area_hint]`；
2. 本次区域方案中的每个区域必须由显式种子定义；
3. 最终 `Mesh2D.region_ids` 中的编号必须全部来自本次 `BoundaryConfig.regions[:,2]` 显式配置的非零物理编号；
4. Triangle 默认属性 `region_id=0` 不是合法 P0 物理区域，最终 `Mesh2D` 中不得出现；
5. 每个显式配置的区域编号必须至少对应一个三角形；
6. 输出区域编号集合应与本次区域方案配置的区域编号集合一致；
7. `len(mesh.region_ids) == mesh.n_triangles`；
8. 不得在 Triangle 输出后通过将 `0` 批量替换为某个编号来掩盖缺失种子，必须在 `BoundaryConfig.regions` 构造阶段正确配置区域；
9. 当前 DIII-D 含第一壁的 P0 默认方案期望 `{1,2,3}`；
10. 无可用第一壁轮廓的降级方案期望 `{1,2}`；
11. 上述集合是具体 P0 区域方案的验收条件，不是对未来所有 M3DC1 Multi Region 网格永久写死区域数；
12. Triangle Wrapper 和 Writer 不得写死区域数量，不得推断区域物理含义，不得重编号、压缩、排序或自行推断区域。

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

**【绝对禁止】** 将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境的 `PYTHONPATH`。该路径下的 OFT 源码快照**不包含编译后的 `liboftpy.so`**，若加入 PYTHONPATH 会遮蔽 `site-packages` 中带有 `liboftpy.so` 的正式安装包，导致 OFT 导入失败，并最终抛出 `FileNotFoundError: Unable to load OFT shared library`。

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

【已确认事实】以下两个 OFT API 均已通过只读侦察 `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/eqdsk.py` 确认存在于源码中：

#### 方案 A：`read_geqdsk`（轻量字典接口）

```python
# 来源：TOKAMAKER/.../TokaMaker/eqdsk.py 底部 read_geqdsk 便捷函数
# 注意：正确函数名为 read_geqdsk，不是 read_eqdsk
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

**事实等级**：`read_geqdsk` 已通过只读源码侦察确认存在；当前没有服务器直接执行 `read_geqdsk` 的运行验证证据，不得声称其已通过服务器验证。

#### 方案 B：`GEQDSKEquilibrium`（高级对象接口，属性更丰富）【当前正式采用】

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

**事实等级**：`GEQDSKEquilibrium` 已通过只读源码侦察确认存在，且已在服务器（liustation，`openfusiontoolkit==26.6`）上实际运行验证，成功读取 `ITER_test.eqdsk` 和 `DIIID/g192185.02440` 并提取全部所需字段。

**当前正式采用方案 B**（`GEQDSKEquilibrium`），因为其属性命名语义清晰，且已提供 `boundary_R`/`boundary_Z`、`limiter_R`/`limiter_Z`、`R_mag`/`Z_mag` 等 LinkMesh 直接需要的字段，并已通过服务器运行验证。

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
        FileNotFoundError: 文件不存在（由 GEQDSKEquilibrium 内部抛出）；
                           或 OFT 共享库缺失时抛出
                           "FileNotFoundError: Unable to load OFT shared library"
        ValueError: 文件格式不符合 EQDSK 规范（由 GEQDSKEquilibrium 内部抛出）
        ImportError: OFT Python 包本身未安装或不在 PYTHONPATH 中
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

## 7. src/linkmesh/mesher/triangle_wrapper.py 实现规范（Python triangle 包唯一底座）

### 7.1 Python triangle 包调用方式与 TokaMaker 风格对齐

【已确认事实】LinkMesh 通过 Python `triangle` 包调用 Triangle 算法。封装风格**严格参考** TokaMaker/OFT 的 `meshing.py` 中 `run_triangle` 函数与 `Mesh.get_mesh` 方法的实现模式（只读侦察 `meshing.py` 确认）。

**重要说明**：
- LinkMesh 当前运行时直接调用的是 Python `triangle` 包（`tr.triangulate`），而不是完整运行 TokaMaker 网格程序。
- `TOKAMAKER/` 仅作为封装方法和接口的只读参考源码，不是最终运行时网格生成依赖。
- 不得因此引入第二个网格生成引擎，也不得改变现有 `BoundaryConfig`、`Mesh2D` 或 `triangle_wrapper.py` 接口。

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

### 7.2 Triangle 输入字典构造（alpha 字典正式契约）

【已确认事实】以下为 `alpha` 字典的正式字段契约，Wrapper 必须严格按此构造：

| 字段名 | shape | dtype | 语义 |
|---|---|---|---|
| `vertices` | `(N, 2)` | float64 | 所有边界点 [R, Z] 坐标，来自 `config.vertices` |
| `segments` | `(M, 2)` | int32 | 线段端点索引对，0-based，来自 `config.segments` |
| `segment_markers` | `(M,)` | int32 | 与 `segments` 逐项对应的边界标记，来自 `config.segment_markers` |
| `regions` | `(K, 4)` | float64 | 每行 `[R, Z, region_id, max_area_hint]`，来自 `config.regions`；K 由输入决定，不写死 |

**物理语义保证**：
- `vertices` 不交换 R/Z、不缩放；
- `segments` 节点索引保持 0-based，不提前转换为 1-based；
- `segment_markers` 保持原始物理编号（1=LCFS, 2=first_wall/limiter, 3=outer_boundary），不清零、不偏置；
- `regions` 中的 `region_id` 是物理标签（1=plasma, 2=vacuum, 3=equivalent outer/wall-conductor），不执行 `+1`；
- Wrapper 不写死区域数量，不推断区域物理含义。

```python
# Triangle 输入字典格式（正式契约）
alpha = {
    "vertices":        np.ascontiguousarray(config.vertices, dtype=np.float64),
    "segments":        np.ascontiguousarray(config.segments, dtype=np.int32),
    "segment_markers": np.ascontiguousarray(config.segment_markers, dtype=np.int32),
    "regions":         np.ascontiguousarray(config.regions, dtype=np.float64),
}
```

### 7.3 Triangle 控制字符串（`_build_triangle_opts` 正式契约）

【已确认事实】控制字符串参考 TokaMaker `meshing.py` 中的 `b'pqaAzQ'`，已实现的 `_build_triangle_opts` 函数。各控制字符的正式语义如下：

| 字符 | 语义 | 条件 |
|---|---|---|
| `p` | PLC/segments 输入模式 | 始终包含 |
| `q<min_angle>` | 质量约束与最小内角（数值语义：角度值，单位度） | 始终包含；`min_angle` 为数值，不强制要求特定字符串格式 |
| `a<max_area>` | 全局最大面积约束（小写 `a`） | 仅当 `max_area is not None` 时加入 |
| `A` | 输出区域属性 `triangle_attributes`（大写 `A`） | 始终包含 |
| `z` | 0-based 节点索引 | 始终包含 |
| `Q` | 静默 Triangle 内部日志 | 始终包含 |

**注意**：小写 `a` 和大写 `A` 语义不同，不得混淆。`_build_triangle_opts` 当前实现的精确字符串格式为：

```python
def _build_triangle_opts(config: BoundaryConfig) -> str:
    opts = "p"
    opts += f"q{config.min_angle:.1f}"   # 数值格式为 .1f，如 "20.0"
    if config.max_area is not None:
        opts += f"a{config.max_area:.6g}"
    opts += "AzQ"
    return opts
# 示例：min_angle=20, max_area=0.001 → "pq20.0a0.001AzQ"
# 示例：min_angle=20, max_area=None  → "pq20.0AzQ"
```

### 7.4 Triangle 输出字段提取（beta 字典到 Mesh2D 的正式映射契约）

【已确认事实】以下为 beta 字典六个字段到 `Mesh2D` 的正式映射契约，Wrapper 必须严格按此提取：

| `Mesh2D` 字段 | beta 字典键 | 提取方式 | shape 契约 | dtype | 物理语义保证 |
|---|---|---|---|---|---|
| `nodes` | `beta["vertices"]` | `.astype(np.float64)` | `(N, 2)` | float64 | R/Z 不交换、不缩放 |
| `triangles` | `beta["triangles"]` | `.astype(np.int32)` | `(T, 3)` | int32 | 保持 0-based，不转 1-based |
| `region_ids` | `beta["triangle_attributes"]` | `np.asarray(..., dtype=np.int32).reshape(-1)` | `(T,)` | int32 | 不执行 `+1`；T==1 时仍为一维；不得含 0 |
| `boundary_segments` | `beta["segments"]` | `.astype(np.int32)` | `(S, 2)` | int32 | 保持 0-based，不转 1-based |
| `boundary_markers` | `beta["segment_markers"]` | `np.asarray(..., dtype=np.int32).reshape(-1)` | `(S,)` | int32 | 不清零、不偏置；S==1 时仍为一维 |
| `node_markers` | `beta["vertex_markers"]` | `np.asarray(..., dtype=np.int32).reshape(-1)` | `(N,)` | int32 | 不清零、不偏置；N==1 时仍为一维 |

**一维 shape 契约（v1.5 校正）**：`region_ids`、`boundary_markers`、`node_markers` 使用 `.reshape(-1)` 而非 `.squeeze()`，保证即使 `T==1`、`S==1` 或 `N==1` 时仍得到一维数组，而非零维数组。

**缺失字段处理**：`boundary_segments`、`boundary_markers`、`node_markers` 使用 `beta.get(key, fallback)` 提供默认值。若 beta 字典缺少必要字段（`vertices`、`triangles`、`triangle_attributes`），Wrapper 应抛出异常；缺失必要字段时的精确异常类型待 User 裁决（见第 7.5 节）。

```python
# 正式提取方式（v1.5 校正，使用 reshape(-1) 替代 squeeze()）
nodes = beta["vertices"].astype(np.float64)
triangles = beta["triangles"].astype(np.int32)
region_ids = np.asarray(beta["triangle_attributes"], dtype=np.int32).reshape(-1)

boundary_segments = np.asarray(
    beta.get("segments", np.zeros((0, 2), dtype=np.int32)),
    dtype=np.int32
)
boundary_markers = np.asarray(
    beta.get("segment_markers", np.zeros((0,), dtype=np.int32)),
    dtype=np.int32
).reshape(-1)
node_markers = np.asarray(
    beta.get("vertex_markers", np.zeros((len(beta["vertices"]),), dtype=np.int32)),
    dtype=np.int32
).reshape(-1)
```

### 7.5 待 User 裁决事项

以下事项当前蓝图未明确规定，不得自行发明，待 User 确认后写入蓝图：

- **缺失必要 beta 字段的异常类型**：当 `beta` 字典缺少 `vertices`、`triangles` 或 `triangle_attributes` 时，Wrapper 应抛出何种异常（`ValueError`、`KeyError` 或其他）？当前实现抛出 `ValueError`（节点数或三角形数为 0），但未覆盖键缺失场景。

---

## 8. src/linkmesh/cli.py 中 `_build_boundary_config()` 实现规范

### 8.1 职责与区域方案选择

`_build_boundary_config()` 是 M2 里程碑的核心胶水代码，负责将 `GFileData` 中的 LCFS 边界坐标转换为 Triangle 所需的分段线性复合体（PLC）描述格式，并根据输入是否提供有效壁轮廓动态选择区域方案：

- **含有效第一壁轮廓**：构造三区域方案（region_id=1/2/3），生成 3 行 `regions`；
- **无可用第一壁轮廓**：构造两区域方案（region_id=1/2），生成 2 行 `regions`。

### 8.2 区域种子几何契约（正式规范）

`_build_boundary_config()` 必须满足以下区域种子几何条件：

1. **plasma seed（region_id=1）**：必须严格位于 LCFS 内；
2. **vacuum seed（region_id=2）**：
   - 含第一壁时：必须严格位于 LCFS 外且第一壁内；
   - 无第一壁时：必须严格位于 LCFS 外且人工 outer boundary 内；
3. **region 3 seed（region_id=3，仅含第一壁时）**：必须严格位于第一壁外且人工 outer boundary 内；
4. 种子不得落在 LCFS、第一壁或人工 outer boundary 的线段上；
5. 不能继续无条件使用"LCFS 最右端与人工 outer boundary 最右端的中点"作为 vacuum seed，因为真实 DIII-D 证据表明该公式不能保证种子位于 LCFS 与第一壁之间；
6. 种子必须经过确定性的点在闭合多边形内外关系检查（用于验证种子位于哪个几何环带；不能替代边界闭合、自交、嵌套和最终网格质量验收）；
7. 边界必须满足 P0 预期嵌套关系：
   - 含第一壁：LCFS 位于第一壁内，第一壁位于人工 outer boundary 内；
   - 无第一壁：LCFS 位于人工 outer boundary 内；
8. 若边界不闭合、发生不允许的相交、不满足嵌套关系或无法找到合法种子，`_build_boundary_config()` 必须停止并抛出明确错误，不得继续生成可能含 `region_id=0` 的网格；
9. 本蓝图规定几何条件、失败原则和确定性要求，不锁定未经实现审查的具体种子搜索算法。

### 8.3 三条 P0 几何边界的含义

| 边界 | 来源 | 含义 |
|---|---|---|
| LCFS | GFile/OFT | plasma-vacuum interface |
| first wall/limiter | GFile/OFT 的可用壁轮廓（可选） | vacuum 与 P0 等效外部区域之间的内部界面 |
| outer boundary | LinkMesh 构造的人工数值截断边界 | P0 计算域的数值外边界，不是 GFile 提供的真实装置外表面 |

### 8.4 实现步骤概要（已实现，待修复区域种子部分）

【已确认事实】`_build_boundary_config()` 已在 `src/linkmesh/cli.py` 中实现（git: 994c415），当前实现步骤：

1. LCFS 点集重采样（等弧长插值）；
2. 构造人工 outer boundary 矩形；
3. 组装顶点列表与线段连接表（LCFS + outer boundary + 第一壁（若有））；
4. 设置区域标记点（regions）——**此步骤存在 region_id=0 缺陷，待修复**；
5. 封装为 `BoundaryConfig` 对象。

**当前已知缺陷**：vacuum seed 使用"LCFS 最右端与 outer boundary 最右端的中点"公式，真实 DIII-D 验收证明该公式不能保证种子位于 LCFS 与第一壁之间，导致 245 个三角形出现 `region_id=0`。修复必须引入确定性的点在闭合多边形内外关系检查，并满足第 8.2 节的全部几何条件。

---

## 9. src/linkmesh/writers/hdf5_writer.py 实现规范（第一战役：TRIMEG HDF5 格式映射）

### 9.1 实现依据与黄金标尺

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 的唯一实现依据是 `docs/trimeg/loadfemmesh_h5.m`。该脚本是 TRIMEG 求解器读取网格 HDF5 文件的 MATLAB 实现，其每一行 `h5read` 调用直接揭示了 TRIMEG 对 HDF5 文件结构的期望。所有数据集路径名、存储形状、数据类型和索引约定均以该脚本为最终裁决依据，不得凭推断自行补充。

### 9.2 TRIMEG HDF5 物理文件结构树

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
    │                                          #         列3=region_id（无偏置，原样写出）
    │
    ├── nbcRZ        [标量, int32]      # 边界节点坐标点数（等于 nvert_ex）
    ├── Rbc          [shape=(nbcRZ,), float64]  # 边界节点 R 坐标 [m]（始终写出）
    └── Zbc          [shape=(nbcRZ,), float64]  # 边界节点 Z 坐标 [m]（始终写出）
```

### 9.3 精确字段映射契约（Field Mapping Contract）

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
| `/femmesh/tria` | `(4, T)` | int32 | 见 §9.4 精确构造公式 | **+1 偏置（节点列）+ 转置；region_id 列原样写出** |
| `/femmesh/nbcRZ` | 标量 | int32 | `np.int32(np.sum(mesh.node_markers != 0))` | 无转换（等于 nvert_ex） |
| `/femmesh/Rbc` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 0].astype(np.float64)` | 无转换，提取边界节点 R 列 |
| `/femmesh/Zbc` | `(nbcRZ,)` | float64 | `mesh.nodes[mesh.node_markers != 0, 1].astype(np.float64)` | 无转换，提取边界节点 Z 列 |

### 9.4 `/femmesh/tria` 精确构造公式

【已确认事实】已在 `write_hdf5()` 中完整实现：

```python
# Step 1：节点索引从 0-based 转换为 1-based
tria_nodes_1based = (mesh.triangles + 1).astype(np.int32)      # shape=(T, 3)

# Step 2：region_ids 扩展为列向量（不需要偏置，region_id 是物理标记非节点索引，原样写出）
region_col = mesh.region_ids.reshape(-1, 1).astype(np.int32)   # shape=(T, 1)

# Step 3：水平拼接为 (T, 4) 矩阵
tria_4col = np.hstack([tria_nodes_1based, region_col])          # shape=(T, 4)

# Step 4：转置后写入 HDF5，HDF5 中存储为 (4, T)
grp.create_dataset("tria", data=tria_4col.T.astype(np.int32))
```

### 9.5 `write_hdf5()` 实现状态与 M3 前置条件

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 中的 `write_hdf5(mesh, filepath, verbose=True)` 函数已**完整实现**（非占位），按 §9.3 映射契约逐一写出全部 11 个数据集。

**M3 前置条件**：M3 真实验收必须基于已经通过 M2 的无 `region_id=0` 网格。在 M2 区域种子修复并通过验收之前，不得进入 M3 验收。

---

## 10. src/linkmesh/writers/smb_writer.py 实现规范（第二战役：M3 验收后侦察确定实现路线）

### 10.1 实现依据与前置条件

`src/linkmesh/writers/smb_writer.py` 的实现依赖对 `SCOREC/PUMI` 开源 C++ 源码的只读侦察结果，以及主管对实现路线的确认。**在 M3 完整验收通过、侦察任务完成并经主管确认前，本模块保持 `NotImplementedError` 占位实现，严禁提前编写任何字节流或序列化逻辑。**

侦察目标文件（只读，严禁修改，M3 验收后执行）：
- `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`：`.smb` 文件读取的 C++ 实现入口
- `M3DC1/m3dc1_scorec/include/m3dc1_model.h`：model `.txt` 配套文件格式
- `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`：高阶节点需求确认

### 10.2 `write_smb()` 函数接口（占位，待 M4 里程碑实现）

【已确认事实】当前 `write_smb()` 保持 `raise NotImplementedError` 占位实现，同时定义了 `_write_model_txt()` 内部函数占位（同样为 `raise NotImplementedError`）。实现路线（包括但不限于 Python 二进制写出、调用官方 API 或其他方式）必须由侦察结果和主管确认决定，不得提前锁定。

```python
def write_smb(mesh: Mesh2D, filepath: str) -> None:
    """将 Mesh2D 对象写出为 M3DC1 可消费的 .smb 静态网格文件。

    【重要】：本函数的具体实现必须等待以下条件全部满足后方可编写：
        1. M3 里程碑完整验收通过；
        2. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc；
        3. 只读侦察 M3DC1/m3dc1_scorec/include/m3dc1_model.h；
        4. 只读侦察 M3DC1/m3dc1_scorec/src/m3dc1_field.cc；
        5. 侦察结果经主管确认，实现路线确定。
    实现路线（序列化方式）由侦察结果决定，当前不得锁定。
    """
    raise NotImplementedError(...)
```

### 10.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。`src/linkmesh/writers/smb_writer.py` 在写出 `.smb` 文件时，应同时写出配套的 model `.txt` 文件。

**【待源码确认】**：model `.txt` 文件的具体格式需通过只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` 中 `load_model` 函数确认。从已侦察的 `m3dc1_model.cc` 可知，文件头格式为：

```text
numL separatrixLoop innerWallLoop outerWallLoop vacuumLoop
```

后续每个 loop 的顶点与边的详细格式待进一步侦察确认。

---

## 11. src/linkmesh/utils/plotter.py 实现规范

### 11.1 已实现的两个函数

【已确认事实】`src/linkmesh/utils/plotter.py` 已完整实现以下两个函数：

#### `plot_lcfs_only(gfile_data, filepath)`（M1 最小可用版本）

仅绘制 LCFS 边界曲线，用于 M1 里程碑验收。功能：
- 绘制 LCFS 边界曲线（红色实线）
- 若有第一壁数据，叠加绘制（蓝色虚线）
- 标注磁轴位置（红色叉号）
- 输出统计信息文本框（LCFS 点数、磁轴坐标）
- 保存为 PNG 文件，dpi=150

**已知非阻塞问题**：matplotlib 默认字体 `DejaVu Sans` 缺少中文字形，使用中文标签时会产生 `Glyph missing` 警告。该警告不影响 PNG 生成和物理验收，当前不要求修改业务源码。

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

## 12. 依赖清单

### 12.1 核心运行依赖

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
- `pyproject.toml`（计划新增）和 `requirements.txt` 的核心运行依赖和版本约束必须保持一致（见第 15 节）。

### 12.2 开发与测试依赖（可选）

```text
pytest>=7.0.0
```

---

## 13. 敏捷渐进里程碑（MVP 开发阶段）

**【铁律】开发时序严格锁死：先完成 M3（TRIMEG HDF5 闭环验证），确认网格几何物理质量完全合格后，再进军 M4（`.smb` 侦察与实现）。严禁跳序。**

### 里程碑 M1：GFile 读取验收（P0 第一步）

**当前状态**：【M1 已通过，允许进入 M2】

【已确认事实】M1 全部验收项均已通过，具体证据如下：

**自动测试**：`tests/test_gfile_reader.py` 运行结果 `19 passed in 0.61s`，退出码 `0`（git: f52a75f）。临时日志路径 `/tmp/m1_reader_test.log`，该路径不保证长期保存。

**真实 GFile 验收**：
- 样例文件：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 调用链：DIII-D GFile → 正式安装的 OFT `GEQDSKEquilibrium`（`openfusiontoolkit==26.6`）→ LinkMesh `read_gfile` → `GFileData`，未使用 mock
- 实测结果：LCFS 81 点；第一壁 88 点；磁轴 `R=1.78029311 m`、`Z=-0.0421587565 m`；等离子体电流 `493324.5 A`
- CLI 路径：`--no-hdf5 --no-smb --plot` 进入 M1 专用路径，不调用 M2 Triangle、M3 HDF5 或 M4 SMB
- PNG 临时路径：`/tmp/linkmesh_diiid_m1.png`，该路径不保证长期保存

**人工几何检查**（User 已确认）：
- LCFS 闭合连续，无明显跳点或自交
- 第一壁整体包围 LCFS
- 磁轴位于 LCFS 内
- R/Z 方向和尺度合理
- DIII-D 极向截面形状正常

**非阻塞问题**：matplotlib `DejaVu Sans` 缺少中文字形，产生 `Glyph missing` 警告，不影响物理验收，当前不要求修改业务源码。

**M1 验收标准逐项确认**：
1. ✅ `python -m linkmesh --gfile ... --no-hdf5 --no-smb --plot lcfs_check.png` 能够运行
2. ✅ 生成的 PNG 中 LCFS 边界曲线闭合、方向正确
3. ✅ 终端打印 LCFS 点数、磁轴坐标
4. ✅ `GFileData` 对象所有必填字段均已正确填充
5. ✅ `gfile_reader.py` 中不存在任何手动文本解析逻辑（AST 测试通过）
6. ✅ `tests/test_gfile_reader.py` 中的 M1 自动测试全部通过（19 passed）

**涉及模块**：`src/linkmesh/__main__.py`（已新建，git: 1fc04f8），`src/linkmesh/readers/gfile_reader.py`（OFT Adapter），`src/linkmesh/utils/plotter.py`（`plot_lcfs_only` 函数），`tests/test_gfile_reader.py`（已通过，git: f52a75f）

---

### 里程碑 M2：Triangle 网格生成验收（P0 第二步）

**当前状态**：【BLOCKED——自动测试 36/36 通过、几何与质量检查通过、PNG 人工检查通过，但真实 region_id=0 阻塞，不得进入 M3】

#### M2 已确认结果（本轮真实验收直接证据）

**自动测试**：
- 运行环境：Linux、Python 3.12.13、pytest 9.1.1
- 结果：`36 passed in 0.19s`，退出码 0
- 其中 27 项受控 mock 契约测试和 9 项真实 Triangle 最小集成测试全部通过
- 临时日志：`/tmp/m2_triangle_wrapper_test.log`，不保证长期保存

**真实 DIII-D 链路验收**：
- 真实 GFile：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 真实链路：`DIII-D GFile → read_gfile → GFileData → _build_boundary_config → generate_mesh → Mesh2D → plot_mesh`
- 输入 `BoundaryConfig`：`vertices (171,2) float64`，`segments (171,2) int32`，`segment_markers (171,) int32`，`regions (2,4) float64`
- 输入边界标记计数：`{1:80, 2:87, 3:4}`（LCFS 80 条、第一壁 87 条、outer boundary 4 条）
- 输出 `Mesh2D`：308 个节点、574 个三角形、207 条边界线段
- 输出边界标记计数：`{1:80, 2:87, 3:40}`（outer boundary 的 4 条输入边被 Triangle 合法细分为 40 条输出边界线段，不作为失败）
- 三角形和边界索引合法；重复顶点三角形为 0；面积不大于 `1e-12 m²` 的三角形为 0；非正有向面积三角形为 0
- 实际最小内角：`20.01391400°`，满足 `20.0° - 0.01°` 的验收下限
- PNG：`/tmp/linkmesh_diiid_m2.png` 已生成
- User 人工确认：网格覆盖、LCFS、第一壁、人工 outer boundary、磁轴位置及三角形几何外观基本正常
- matplotlib 中文 `Glyph missing` 警告：非阻塞显示问题

**区域编号验收失败（阻塞 M2）**：
- 输出区域计数：`{0:245, 1:176, 2:153}`
- 245 个三角形出现不允许的 `region_id=0`（Triangle 默认属性，不是合法 P0 物理区域）
- 当前确认：三条闭合边界、两个区域种子（regions 行数为 2）、245 个默认区域 0 三角形
- 不确认：`region_id=0` 具体位于哪一个几何环带（不作为已确认事实）
- 根本原因：`_build_boundary_config()` 中 vacuum seed 使用"LCFS 最右端与 outer boundary 最右端的中点"公式，不能保证种子位于 LCFS 与第一壁之间；且当前 `regions` 只有 2 行（缺少 region_id=3 的种子），不符合含第一壁三区域方案

#### M2 目标：修复后验收标准

**区域编号验收**：
- 含有效第一壁的当前 DIII-D P0 默认方案，`Mesh2D.region_ids` 集合必须精确为 `{1,2,3}`；
- 无可用第一壁轮廓的降级方案，集合必须精确为 `{1,2}`；
- 任何 P0 方案都不得出现 `0` 或未配置编号；
- 每个配置区域必须至少包含一个三角形；
- 通过三角形质心相对 LCFS、第一壁和人工 outer boundary 的内外关系，验证区域编号与几何环带一致；
- 数值区域统计负责验证区域编号，默认不按区域着色的 PNG 不能替代该检查。

**几何与质量验收（继续检查）**：
- 节点与边界索引合法（0-based，范围内）
- 数组 shape/dtype 正确
- 重复顶点三角形为 0
- 近零面积三角形为 0（面积 > 1e-12）
- 非正有向面积三角形为 0
- 实际最小内角满足 `actual_min_angle >= min_angle - 0.01°`

**测试要求**：
- 修复后必须重跑现有 `tests/test_triangle_wrapper.py`（36 项）；
- 必须新增或扩展 `_build_boundary_config()` 的测试，至少覆盖：
  - 含第一壁三区域方案（region_ids 集合为 `{1,2,3}`）
  - 无第一壁两区域方案（region_ids 集合为 `{1,2}`）
  - 种子内外关系（plasma seed 在 LCFS 内，vacuum seed 在正确环带内，region 3 seed 在第一壁外）
  - 非法嵌套时停止并报错
  - 无法找到合法种子时停止并报错
  - 不得出现未配置区域（不得出现 `region_id=0`）
- 必须重跑真实 DIII-D 链路并重新生成 PNG；
- 只有上述全部通过并由 User 确认后，M2 才能改为 `PASSED` 并进入 M3。

**M2 验收标准完整列表**（修复后逐项确认）：
1. `python -m linkmesh --gfile sample.geqdsk --no-smb --plot mesh_check.png` 能够运行
2. 生成的 `mesh_check.png` 中三角网格覆盖 LCFS 内部区域，无明显退化三角形
3. 终端打印：`节点数: N，三角形数: T，边界线段数: S`
4. `Mesh2D` 对象的所有字段均已正确填充
5. 计算生成网格中全部三角形的真实内角，记录实际最小角 `actual_min_angle`，验证：`actual_min_angle >= min_angle - angle_tolerance`（`angle_tolerance` 约为 0.01°，仅用于浮点误差）；若真实网格明显低于 `min_angle`，测试必须失败并输出最小角及对应三角形
6. `triangle_wrapper.py` 中 `alpha` 字典包含 `vertices`、`segments`、`segment_markers`、`regions` 四个字段（对齐正式契约），`beta` 字典提取键名为 `vertices`、`triangles`、`triangle_attributes`、`segments`、`segment_markers`、`vertex_markers`
7. `cli.py` 中 `_build_boundary_config()` 已完整实现（git: 994c415），区域种子修复后满足第 8.2 节全部几何条件
8. 含第一壁时 `Mesh2D.region_ids` 集合精确为 `{1,2,3}`，无第一壁时精确为 `{1,2}`，任何方案不得出现 `0`
9. `tests/test_triangle_wrapper.py` 中的 M2 自动测试全部通过（修复后重跑）
10. `_build_boundary_config()` 的新增测试全部通过

**涉及模块**：`src/linkmesh/mesher/triangle_wrapper.py`，`src/linkmesh/utils/plotter.py`（`plot_mesh` 函数），`src/linkmesh/cli.py`（`_build_boundary_config` 函数，待修复区域种子），`tests/test_triangle_wrapper.py`（已 36/36 通过，修复后重跑）

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步，第一战役闭环）

**当前状态**：【占位，待 M2 完整验收通过后开始；M3 真实验收必须基于无 region_id=0 的网格】

**目标**：将 Python `triangle` 包生成的三角网格写出为 TRIMEG 可消费的 HDF5 文件，并通过 `loadfemmesh_h5.m` 读取验证，确认网格几何物理质量完全合格。

**M3 边界**：
- Writer 不推断区域物理含义；
- Writer 不重编号、偏置、压缩或排序 `region_ids`；
- 节点连接表按契约从 0-based 转为 1-based；
- `region_id` 原样写出，不执行 `+1`；
- 本轮不得宣称 M3 已开始或通过。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --output mesh.h5 --no-smb` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开；
3. `h5py` 读取验证：`/femmesh/vert` shape=`(2,N)`，`/femmesh/tria` shape=`(4,T)`，`/femmesh/nvert`=N，`/femmesh/ntria`=T；
4. 使用 `loadfemmesh_h5.m` 在 MATLAB 中读取 `mesh.h5`，`femmesh.vert` shape=`(N,2)`，`femmesh.tria` shape=`(T,4)`，无报错；
5. 节点索引合法性验证：`femmesh.tria(:,1:3)` 中所有节点索引均为整数，且满足 `1 <= index <= N`；
6. `region_id` 列（`femmesh.tria(:,4)`）无 `+1` 偏置，取值为物理标记值（1=plasma, 2=vacuum, 3=equivalent outer/wall-conductor），不得含 0；
7. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`；
8. `tests/test_hdf5_writer.py` 中的 M3 自动测试全部通过（测试文件计划新增）。

**涉及模块**：`src/linkmesh/writers/hdf5_writer.py`（已完整实现），`tests/test_hdf5_writer.py`（计划新增）

---

### 里程碑 M4：`.smb` 输出验收（P0 第四步，第二战役攻坚）

**当前状态**：【占位，待 M3 验收通过后开始侦察】

**目标**：在 M3 完全验收通过、网格质量确认合格后，完成 SCOREC/PUMI/M3DC1 只读侦察，由主管确认实现路线，将同一 `Mesh2D` 对象写出为 M3DC1 可消费的 `.smb` 静态网格文件。

**M4 侦察范围**：M4 必须在 M3 完整通过后，对 MCD7 样例、官方文档、ModelFile、MeshFile 和 M3DC1/SCOREC/PUMI 源码进行只读侦察，确认区域数量、D1B、几何分类、索引、文件配对和 `.smb` 契约。P0 默认三区域方案不得被外推为 M3DC1 永久固定三区域；M3DC1 实际区域数量和 ModelFile 格式待侦察确认。

**前置条件**：
1. M3 里程碑已完全验收通过；
2. 已完成对 `m3dc1_mesh.cc`、`m3dc1_model.cc`、`m3dc1_field.cc` 的只读侦察；
3. 侦察结果已经主管确认，`.smb` 格式事实已从【待源码确认】转为【已确认事实】，实现路线已确定。

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
2. 生成 `mesh.smb`（M3DC1 格式，通过 M4 验收标准）；
3. 生成 `mesh_check.png`（LCFS + 三角网格叠加图）；
4. 终端打印完整统计信息，无报错，无警告。

---

## 14. 测试目录规划（M1～M3 验收测试）

### 14.1 测试文件职责

| 测试文件 | 服务里程碑 | 状态 | 核心验收内容 |
|---|---|---|---|
| `tests/test_gfile_reader.py` | M1 | 已通过（19 passed，git: f52a75f） | 验证 `read_gfile()` 能正确读取 EQDSK 文件；`GFileData` 所有字段类型与形状正确；LCFS 首尾闭合；LCFS 方向为逆时针；`current` 单位为 A（不缩放）；`gfile_reader.py` 中无手动文本解析逻辑 |
| `tests/test_triangle_wrapper.py` | M2 | 自动测试 36/36 通过；真实区域编号 BLOCKED，待修复后重跑 | 验证 `generate_mesh()` 能从合法 `BoundaryConfig` 生成 `Mesh2D`；alpha 四字段契约；beta 六字段映射；`Mesh2D` 所有字段类型与形状正确；三角形索引为 0-based；`region_ids` 取值在约定范围内；最小内角满足约束；单元素 shape 为一维；修复后新增 `_build_boundary_config()` 区域种子测试 |
| `tests/test_hdf5_writer.py` | M3 | 【计划新增】 | 验证 `write_hdf5()` 写出的 HDF5 文件包含全部 11 个数据集；`/femmesh/vert` shape=`(2,N)`；`/femmesh/tria` shape=`(4,T)`；节点索引满足 `1 <= index <= N`；`region_id` 列无偏置、不含 0；`nvert`/`ntria` 标量值正确 |

### 14.2 测试数据来源与许可证边界

**测试分层原则**：

| 测试层次 | 数据来源 | 依赖范围 | 说明 |
|---|---|---|---|
| 单元测试 | 受控合成对象或 mock | 不依赖 `TOKAMAKER/` 源码树 | 验证 Adapter 后处理逻辑（闭合性、方向性等），不需要真实 GFile |
| 集成测试（开发期） | 只读访问 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 或 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` | 依赖 `TOKAMAKER/` 源码树（只读） | 验证 OFT 真实读取链路；仅在开发环境中使用，不得打包进最终交付物 |
| 交付测试 | LinkMesh 自有、来源明确、许可允许分发的样例 GFile | 不依赖 `TOKAMAKER/` 源码树 | 【计划新增，待许可确认】 |

**许可证说明**：

`TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 和 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 均受 `TOKAMAKER/OpenFUSIONToolkit/LICENSE`（GNU LGPL v3.0）约束。在未经主管和法务确认这些 EQDSK 样例可单独复制和再分发之前：

- 这些文件**不得**被复制到 `tests/data/` 或 `examples/` 目录。
- 这些文件**不得**作为 LinkMesh 正式自动测试或交付测试的唯一数据来源。
- 开发期集成测试可以通过只读路径访问这些文件，但必须在测试代码中明确标注为"开发期集成测试，不打包进交付物"。

**计划新增的自有样例**（待许可确认后实施）：

- `examples/sample.geqdsk`：LinkMesh 自有、来源明确、许可允许分发的示例 GFile，用于交付测试和用户示例。来源和许可证状态：【待许可确认】，本轮不创建。

**测试依赖**：
- 测试框架：`pytest>=7.0.0`
- M2/M3 单元测试可使用最小合成 `BoundaryConfig`/`Mesh2D` 进行，不依赖真实 GFile。

---

## 15. 包安装与运行环境规范

### 15.1 src 布局与标准安装

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。仓库根目录需要 `pyproject.toml` 来支持标准 Python 包安装。**`pyproject.toml` 当前尚不存在，为计划新增文件，待主管批准后创建。**

**`pyproject.toml` 的职责**：
1. 声明标准 Python 包元数据（名称、版本、描述、作者等）
2. 配置 src 布局的包发现（`packages = {find = {where = ["src"]}}`）
3. 声明控制台入口：`linkmesh = "linkmesh.cli:main"`
4. 声明正式运行依赖（与 `requirements.txt` 核心依赖保持一致）

**`pyproject.toml` 规划示例**（待实施时创建，本轮不创建）：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

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

### 15.2 `src/linkmesh/__main__.py` 规范

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

### 15.3 两种调用方式的等价性

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数，行为完全等价：

| 调用方式 | 依赖条件 | 入口路径 |
|---|---|---|
| `python -m linkmesh` | `src/linkmesh/__main__.py` 存在（已完成，git: 1fc04f8）；`src/` 在 PYTHONPATH 中或已安装 | `__main__.py` → `linkmesh.cli.main` |
| `linkmesh`（控制台命令） | `pyproject.toml` 中 `console_scripts` 已配置（计划新增）；包已通过 `pip install` 安装 | `linkmesh.cli:main` 直接调用 |

### 15.4 `pyproject.toml` 与 `requirements.txt` 的关系

- **`pyproject.toml`**（计划新增）：正式安装元数据与运行依赖依据。通过 `pip install .` 或 `pip install -e .` 安装时使用。
- **`requirements.txt`**：服务器部署用的直接依赖清单，适合 `pip install -r requirements.txt` 快速部署。
- **一致性要求**：两者的核心运行依赖和版本约束必须保持一致。当 `openfusiontoolkit` 版本约束更新时，两个文件必须同步修改。

### 15.5 PYTHONPATH 与安装规则汇总

【已确认事实】以下规则来自服务器冒烟测试实际故障排查，为铁律：

| 场景 | 规则 |
|---|---|
| 标准安装后（`pip install .`） | 最终用户不应依靠手动设置 PYTHONPATH 来发现 LinkMesh；`linkmesh` 控制台命令直接可用 |
| 开发期未安装时 | 可临时将仓库 `src/` 加入 PYTHONPATH：`export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH` |
| OFT 源码路径 | **绝对禁止**将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入任何运行环境的 PYTHONPATH；该路径下的源码快照不含 `liboftpy.so`，会遮蔽正式安装包，导致 OFT 导入失败并抛出 `FileNotFoundError: Unable to load OFT shared library` |
| OFT 运行依赖 | 通过 `pip install openfusiontoolkit==26.6` 获取官方 manylinux wheel；不依赖 `TOKAMAKER/` 源码树 |
| `TOKAMAKER/` 目录 | 继续作为开发期绝对只读参考区；不参与运行时依赖；不得修改其中任何文件 |

---

## 16. 蓝图更新纪律

本文档是 LinkMesh 项目的单事实真理源。以下情况必须先更新本文档，再进入代码实现：

1. 新增或删除任何模块文件；
2. 修改任何数据结构的字段定义（`GFileData`、`BoundaryConfig`、`Mesh2D`）；
3. 修改区域标记或边界标记的整数约定；
4. 修改 HDF5 文件结构或数据集路径名；
5. 确认 `.smb` 格式的任何细节（将【待源码确认】转为【已确认事实】）或确认实现路线；
6. 新增任何 CLI 参数；
7. 调整任何里程碑的验收标准；
8. **修改 OFT API 的调用方式（如从 `GEQDSKEquilibrium` 切换到 `read_geqdsk` 或反之，或新增/移除 OFT 依赖）**；
9. **修改 `openfusiontoolkit` 版本约束**（需同步更新 `pyproject.toml` 和 `requirements.txt`）；
10. **修改 `src/linkmesh/__main__.py` 的职责或内容**；
11. **修改 `pyproject.toml` 中的控制台入口或包发现配置**；
12. **修改 P0 区域方案（含壁三区域 / 无壁两区域）或全局区域传递契约**；
13. **修改区域种子几何条件或失败原则**。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
