# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 v1.8（固化 M2-0 OFT 通过证据；新增正式 mesher/oft_adapter.py 模块；Triangle Wrapper 降级为历史/过渡路径；明确轻量 Mesh2D 核心三数组；明确 OFT 区域编号与元数据规则；授权下一轮最小 M2 Adapter 实现）
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源（Single Source of Truth）。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认事实】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【待运行验证】的内容为需要在真实 OFT 环境中实际运行后方可确认的事项；标注【计划新增】的内容为蓝图已批准、但尚未在仓库中创建的文件或目录；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
- 主要用途：本文档为 LinkMesh 项目的单事实真理源（Single Source of Truth），不作为人类泛读材料，专门用于指导 Aider 自动化编码、RAG 知识库精准检索以及下游模块的硬核参数对齐。凡 Aider 在执行编码、新建文件、修改具体业务代码前，必须查阅并严格对齐本文档。
- 场外架构师检索用途：当场外架构师需要判断 LinkMesh 某模块的职责边界、某数据结构的字段定义、某输出格式的对齐标准，或某开发阶段的验收条件时，应优先召回本文档。
- Aider 执行用途：Aider 必须以本文档为最高技术权威。编写任何 `.py` 业务源码前，必须先核对本文档对应章节的接口定义、数据结构字段和验收标准。如发现实际需求与本文档不符，必须先在对话中提出蓝图迭代建议，待主管确认并更新本文档后，方可动手编写代码。
- 修改前置条件：任何对本文档的修改，必须由人类主管在对话中明确确认后方可执行。Aider 严禁自发修改本文档中的接口定义、数据结构、验收标准或禁止事项。

### 修订记录

| 版本 | 修订摘要 |
|---|---|
| v1.5 | M1 验收写入；M2 契约校正（reshape(-1) 替代 squeeze()；mock 目标修正） |
| v1.6 | 批准含第一壁 DIII-D P0 默认三区域简化方案（region_id=1/2/3）；明确无可用壁轮廓降级两区域方案（region_id=1/2）；建立轻量的按表区域传递契约（Wrapper/Writer 不写死区域数）；补充区域种子几何条件与失败原则；记录 M2 自动测试 36/36 通过但真实 region_id=0 阻塞 M2 总体验收；保留 M4 Multi Region 侦察空间 |
| v1.7 | 优先复用 OFT 完成 M1 读取、M2 区域/网格生成和可选静态中间输出；LinkMesh 最小化为输入编排、统一对象适配、目标格式翻译和 CLI；两区域/三区域改为 OFT Multi Region 的特殊验收实例，删除 LinkMesh 固定区域编号和固定区域数量的全局表述；根据 `loadfemmesh_h5.m` 修正 TRIMEG HDF5 直接消费契约（明确 boundary_segments/boundary_markers/node_markers 非 TRIMEG 直接消费字段，/femmesh/tria 第四列含义标注为待真实样例核对）；Mesh2D 重新定义为轻量统一网格对象，boundary_segments/boundary_markers/node_markers 降级为可选内部/适配字段；增加 M2-0 OFT 可行性验证里程碑；明确不修改、不维护 OFT 分支；保留 M4 对 M3DC1 特有要求的 LinkMesh 侧适配空间 |
| v1.8 | 固化 M2-0 OFT 环境、合成两/三区域和真实 DIII-D 通过证据（Linux x86_64 / Python 3.12.13 / OpenFUSIONToolkit 26.6 正式 Conda 环境）；新增正式 `mesher/oft_adapter.py` 模块作为 M2 正式网格生成适配层；将 Python Triangle Wrapper 降级为历史/过渡路径（不再作为 M2 正式主路径）；明确轻量 Mesh2D 核心三数组（nodes/triangles/region_ids）；明确 OFT 区域编号原样保存与元数据从 domain.region_info 获取的规则；约束 LinkMesh 不复制 OFT 通用几何算法；授权进入 M2 Adapter 实现，但不表述为 M2/M3/M4 已通过 |

---

## 0. LinkMesh 项目定位与 MVP P0 边界

### 0.1 项目定位

LinkMesh 是一个**独立命令行程序（CLI）**，专注于打通从**等离子体平衡文件（GFile/EQDSK）**提取边界，到基于**OFT（OpenFUSIONToolkit）已有模块**完成区域组织、边界处理、区域种子和网格生成，再将统一内存网格对象顺次翻译输出为**两大目标物理求解器静态网格文件**的完整工具链路。

**【v1.7 架构决定】LinkMesh 的优先开发路线**：尽量直接调用 OFT 已有模块完成 GFile/EQDSK 读取、区域组织、边界处理、区域种子、网格生成和可选中间静态网格输出；LinkMesh 只负责最小输入编排、必要字段翻译、目标格式输出和 CLI 编排。

**【P0 禁止】** 不得复制 OFT 已实现的通用网格拓扑、区域管理、边界重采样、点合并或 Triangle 调用逻辑。不得修改、补丁化、重新编译或维护新的 OFT 分支。

**关于历史实验代码**：当前 LinkMesh 自有 Triangle/几何代码（`triangle_wrapper.py` 中的 `BoundaryConfig`、`_build_boundary_config()` 等）视为历史实验或过渡候选，不再作为必须保留的正式架构核心。在 M2-0 OFT 可行性验证通过后，将由 OFT `gs_Domain` 路线（`mesher/oft_adapter.py`）替代。

**正式目标数据流（v1.8）**：

```text
GFile/EQDSK
  → OFT GEQDSKEquilibrium（M1，已通过）
  → GFileData（LinkMesh 薄字段适配器）
  → mesher/oft_adapter.py（M2 正式网格生成适配层）
      → OFT gs_Domain / define_region / add_polygon / add_annulus / add_rectangle / add_enclosed / build_mesh
      → OFT Mesh / liboft_triangle
  → OFT 网格结果（pts, lc, reg）
  → LinkMesh 最小适配（轻量 Mesh2D 统一对象）
  → TRIMEG HDF5（M3）/ M3DC1 .smb（M4）
```

**M2 正式核心数据流（v1.8）**：

```text
GFileData → oft_adapter → OFT gs_Domain/Mesh/build_mesh → pts/lc/reg → 轻量 Mesh2D
```

**完整项目数据流（v1.8）**：

```text
GFile/EQDSK → OFT GEQDSKEquilibrium → GFileData → OFT Adapter → Mesh2D → TRIMEG HDF5 / M3DC1 .smb
```

**关于 OFT 网格后端**：OFT 当前 `run_triangle()` 通过 `ctypes` 调用 OFT 自己的 `liboft_triangle`（见 `meshing.py` 中 `oft_triangulate`），LinkMesh 不需要直接维护该底层实现。LinkMesh 通过调用 OFT 公开接口（`gs_Domain.build_mesh()`）获得网格结果，不直接操作 `liboft_triangle`。

**关于 OFT 适配验证**：不得把"调用 OFT 一定无需任何适配"写成已确认事实。LinkMesh 仍需验证 OFT 输出与目标文件契约之间的字段映射。如当前 OFT 公开接口无法满足某个目标字段，记录为适配验证项；在未确认前不得伪造字段或静默填充。

### 0.2 MVP P0 硬边界（铁律，不得突破）

| 维度 | P0 允许 | P0 禁止 |
|---|---|---|
| 输入端 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | **在 LinkMesh 侧手动执行复杂文本 I/O 与字符串切分解析 GFile**；复杂 CAD 输入；多区域高维输入 |
| 网格生成底座 | **优先调用 OFT `gs_Domain` / `build_mesh()`（经 `mesher/oft_adapter.py`）**；OFT 内部通过 `liboft_triangle` 完成 Triangle 调用 | 复制 OFT 已实现的通用网格拓扑、区域管理、边界重采样、点合并逻辑；引入任何第二种网格生成引擎；三维棱柱/四面体生成；自适应网格细化算法；修改或维护 OFT 分支 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 PUMI `.smb` 静态二进制网格文件（M4 阶段） | 三维网格输出；其他求解器格式 |
| 可视化 | 基于 `matplotlib` 的简易画图自检 | 交互式可视化；三维渲染 |
| OFT 治理 | 调用 OFT 已提供的公开接口 | 修改 OFT 源码；修改 Conda 安装目录；维护 OFT fork；把 OFT 私有字段固化为长期公共 API |

### 0.3 OFT 已确认能力（来自只读源码侦察与 M2-0 运行验证）

【已确认事实】以下 OFT 能力已通过只读侦察 `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` 确认，并已在 M2-0 中通过正式 Conda 环境运行验证（见第 13 节 M2-0）：

| OFT 接口 | 能力描述 |
|---|---|
| `gs_Domain` | 支持多个命名区域和区域类型，包括 plasma、vacuum、boundary、conductor、coil |
| `define_region(name, dx, reg_type, ...)` | 定义命名区域及其属性（类型、分辨率、电阻率、匝数等） |
| `add_polygon(contour, name, parent_name, ...)` | 添加多边形几何，定义区域边界 |
| `add_annulus(inner_contour, inner_name, outer_contour, annulus_name, ...)` | 添加环形几何，定义嵌套区域边界 |
| `add_rectangle(rc, zc, w, h, name, parent_name, ...)` | 添加矩形几何 |
| `add_enclosed(in_point, name)` | 添加区域内部种子点 |
| `build_mesh(debug, merge_thresh, require_boundary, setup_only, cubit_path, ...)` | 执行网格生成，返回 `(pts[np,2], lc[nc,3], reg[nc])` |
| `Mesh` | 已实现区域边界组织、点合并、共享边界处理、边界重采样、区域定义和 Triangle 输入构造 |
| `Region` | OFT 区域对象；提供区域名称、类型和最终 ID 等元数据 |
| `run_triangle` | OFT Triangle 调用封装（内部通过 `liboft_triangle.so`） |
| `get_coils()` | 获取线圈区域字典 |
| `get_conductors()` | 获取导体区域字典 |
| `save_gs_mesh()` / `load_gs_mesh()` | 可选静态中间网格文件保存/加载（OFT 自有格式，**不是 TRIMEG HDF5 格式，也不是 M3DC1 `.smb` 格式**） |

【已确认事实】`build_mesh()` 最终返回：
- `pts`：节点坐标数组，shape `(np, 2)`，dtype `float64`
- `lc`：三角形连接表，shape `(nc, 3)`，整数 dtype（M2-0 实测为 `int32`），**0-based 索引**
- `reg`：三角形区域编号数组，shape `(nc,)`，整数 dtype（M2-0 实测为 `int32`）

【已确认事实，M2-0 运行验证】OFT 26.6 在 M2-0 真实运行中：
- `lc` 返回合法 **0-based** 连接表，索引范围为 `0..N-1`；Adapter 应验证 `0 <= lc < N`，无需无依据地再次偏置。
- `reg` 返回的区域编号为正整数，与 `gs_Domain.region_info` 中定义区域的最终 ID 一一对应。非正区域编号（如 0）表示未认领或非法区域，不是"无物理方程"的合法标签。

---

## 1. MVP 物理目录树与职责矩阵

### 1.1 当前仓库与本阶段目标目录结构

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。以下目录树区分了当前已存在的文件与蓝图批准但尚待实施的计划项。

```text
LinkMesh/
├── pyproject.toml                     # 【计划新增】标准 Python 包安装元数据与控制台入口（见第 15 节）
├── CONTEXT.md                         # 敏捷开发纪律规范（只读）
├── LinkMesh_Architecture_Plan.md      # 本文档（单事实真理源）
├── History.md                         # 战术战果归档
├── requirements.txt                   # 服务器部署用直接依赖清单（见第 15.4 节）
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
│       │   ├── oft_adapter.py         # 【计划新增，M2 正式主路径】OFT gs_Domain 网格生成适配层：
│       │   │                          # 接收 GFileData + 网格尺度参数，调用 OFT gs_Domain/build_mesh，
│       │   │                          # 将 pts/lc/reg 规范化为轻量 Mesh2D；不复制 OFT 通用几何算法
│       │   └── triangle_wrapper.py    # 【历史/过渡实现，非 M2 正式主路径】Python triangle 包底座封装；
│       │                              # 已被 oft_adapter.py 替代为正式路线；
│       │                              # 当前保持文件不动，禁止继续扩展其区域拓扑与通用几何能力
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
│   ├── test_triangle_wrapper.py       # 【历史/过渡测试】Python triangle 路线自动测试 36/36 通过；
│   │                                  # 作为历史证据保留；不能作为 OFT Adapter 正式验收的替代；
│   │                                  # 当前保持文件不动，暂不删除、不扩展
│   ├── test_oft_adapter.py            # 【计划新增，M2 正式验收测试】OFT Adapter 专用测试；
│   │                                  # 验证 pts/lc/reg → Mesh2D 规范化、shape/dtype/索引范围/区域编号契约
│   └── test_hdf5_writer.py            # 【计划新增】M3 验收测试
│
└── examples/                          # 【计划新增】示例文件目录
    ├── sample.geqdsk                  # 【计划新增，待许可确认】示例 GFile 平衡文件
    └── run_example.sh                 # 【计划新增】示例运行脚本
```

**注意**：
- `examples/` 目录当前尚不存在，其中的 `sample.geqdsk` 来源和许可证待确认（见第 14.2 节）。
- `pyproject.toml` 当前尚不存在，待主管批准后创建（见第 15.1 节）。
- `mesher/oft_adapter.py` 当前尚不存在，为下一轮 M2 实现允许新建的正式模块（见第 7 节与第 13 节 M2）。
- `tests/test_oft_adapter.py` 当前尚不存在，为下一轮 M2 实现允许新建的正式验收测试（建议路径；若与目录规则冲突见第 14.1 节说明）。
- 本轮不新增 `tests/test_smb_writer.py`，M4 开始前不创建该文件。
- `mesher/triangle_wrapper.py` 与 `tests/test_triangle_wrapper.py` 保留为历史/过渡实现，本轮及下一轮 M2 任务均保持文件不动，暂不删除、不扩展；是否以后删除不在本轮裁决。

### 1.2 模块职责矩阵

| 模块文件 | 核心职责 | 输入 | 输出 | 禁止事项 |
|---|---|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口：仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑 | `sys.argv`（透传） | 无（副作用：调用 `cli.main`） | 不得包含任何业务逻辑；不得直接操作文件；不得重复定义参数解析 |
| `src/linkmesh/cli.py` | 解析命令行参数；调用 reader → `mesher/oft_adapter.py`（M2 正式路径）→ writer；捕获异常并打印友好错误信息 | `sys.argv` | 无（副作用：调用各模块） | 不得包含任何业务逻辑；不得直接操作文件；**不得在 CLI 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换**；不得复制 OFT 通用几何逻辑 |
| `src/linkmesh/readers/gfile_reader.py` | **薄 Adapter（接线员）**：调用 OFT `GEQDSKEquilibrium` 读取 GFile，从返回对象属性中提取 LCFS 边界坐标、磁轴坐标、第一壁点集等，封装为 `GFileData` 对象 | GFile 文件路径（`str`） | `GFileData` dataclass | **绝对禁止**在 LinkMesh 侧手动执行任何原始 GFile 文本 I/O 与字符串切分；不得调用 Triangle；不得写文件 |
| `src/linkmesh/mesher/oft_adapter.py` | **【M2 正式网格生成适配层】** 接收 `GFileData` 和必要网格尺度参数；使用正式安装的 OFT `gs_Domain`，调用 `define_region()`/`add_polygon()`/`add_annulus()`/`add_rectangle()`/必要时 `add_enclosed()`/`build_mesh()`；由 OFT 完成区域组织、边界处理、点合并、边界重采样、区域种子、Triangle 输入构造和三角网格生成；将 `pts`/`lc`/`reg` 规范化为轻量 `Mesh2D`；检查 shape、dtype、有限值、索引范围、区域属性长度、非正区域编号和退化三角形 | `GFileData` 对象，网格尺度参数 | `Mesh2D` 对象 | **不得复制 OFT 通用几何、区域拓扑、种子搜索、重采样或 Triangle 调用算法**；不得修改 OFT 源码；不得读取或改写 OFT 安装目录；不得维护 OFT fork；不得依赖仓库 `TOKAMAKER/` 快照作为运行时包；不得写死区域数量；不得根据整数编号推断区域物理语义；不得对合法 0-based 连接表无依据地再次偏置 |
| `src/linkmesh/mesher/triangle_wrapper.py` | 【历史/过渡实现，非 M2 正式主路径】原 Python triangle 包底座封装；已被 `oft_adapter.py` 替代 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑；不得引入第二种生成引擎；**不得写死区域数量**；不得推断区域物理含义；**禁止为保存旧实现继续扩展其区域拓扑与通用几何能力** |
| `src/linkmesh/writers/hdf5_writer.py` | **第一战役**：接收 `Mesh2D` 对象；严格对照 `docs/trimeg/loadfemmesh_h5.m` 黄金标尺，按 TRIMEG HDF5 规范写出 `.h5` 文件 | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；**不得重编号、偏置、压缩或排序 `region_ids`**；不得推断区域物理含义；不得根据整数编号猜测区域语义 |
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

### 2.2 `Mesh2D`：LinkMesh 轻量统一网格对象（v1.8 明确核心三数组）

【v1.8 明确】`Mesh2D` 是 LinkMesh 目标格式之间的**轻量统一网格表示**，而不是 Python Triangle 专属对象。其 M2 正式核心数据收缩为三个数组，全部来自 OFT `build_mesh()` 返回值：

| 字段 | 来源 | 期望 shape | 期望 dtype |
|---|---|---|---|
| `nodes` | OFT `pts` | `(N, 2)` | `float64` |
| `triangles` | OFT `lc` | `(T, 3)` | 整数 dtype（M2-0 实测 `int32`） |
| `region_ids` | OFT `reg` | `(T,)` | 整数 dtype（M2-0 实测 `int32`） |

**索引基准原则（v1.8）**：内部节点索引基准以 M2-0 实际证据为准。当前 OFT 26.6 已确认返回合法 **0-based** 连接表；Adapter 应验证 `0 <= lc < N`，**无需无依据地再次偏置**。任何后续偏置（如写入 TRIMEG HDF5 时的 `+1`）由目标 Writer 按其格式契约在写出阶段执行，不在 `Mesh2D` 阶段处理。

**区域编号原则（v1.8）**：`region_ids` **原样保存 OFT 返回的三角形区域编号**，不重编号、不压缩、不排序、不执行 `+1`。LinkMesh、`Mesh2D`、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义。区域语义应从 OFT `domain.region_info` 的区域名称、类型和最终 ID 获得。区域数量由 OFT 当前区域模型决定，不在 `Mesh2D` 中写死。

```python
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class Mesh2D:
    """LinkMesh 轻量统一网格对象（v1.8 明确核心三数组）。

    该对象是 OFT build_mesh() 返回结果经 LinkMesh 最小适配后的统一表示，
    同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py 的共同输入。

    M2 正式核心字段来源（OFT build_mesh() 返回值）：
        nodes      ← pts[np, 2]，OFT 返回的节点坐标，期望 dtype float64
        triangles  ← lc[nc, 3]，OFT 返回的三角形连接表，期望整数 dtype，0-based
        region_ids ← reg[nc]，OFT 返回的三角形区域编号，期望整数 dtype

    索引约定（M2-0 已确认）：
        OFT 26.6 build_mesh() 返回合法 0-based lc 连接表，索引范围 0..N-1。
        Adapter 应验证 0 <= lc < N，无需无依据地再次偏置。
        任何针对目标格式的偏置（如 TRIMEG HDF5 的 +1）由目标 Writer 在写出阶段执行。

    区域编号约定（v1.8）：
        region_ids 原样保存 OFT 返回的三角形区域编号，不重编号、不压缩、不排序、不执行 +1。
        LinkMesh、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义。
        区域语义应从 OFT domain.region_info 的区域名称、类型和最终 ID 获得。
        区域数量由 OFT 当前区域模型决定，不在 Mesh2D 中写死。
        非正区域编号表示未认领或非法区域，不是"无物理方程"的合法标签。
    """
    # ------------------------------------------------------------------ #
    # M2 正式核心字段（来自 OFT build_mesh() 返回值）                       #
    # ------------------------------------------------------------------ #

    # 节点坐标（来自 OFT pts）
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64

    # 三角形连接表（来自 OFT lc），0-based（M2-0 确认）
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，整数 dtype

    # 三角形区域编号（来自 OFT reg）
    # 原样保存 OFT 返回值，不重编号、不压缩、不排序、不执行 +1
    # 不得根据整数值推断区域物理语义
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，整数 dtype

    # ------------------------------------------------------------------ #
    # 非核心、可选、兼容字段（v1.8 保持降级状态）                            #
    # 这些字段不是 TRIMEG HDF5 loadfemmesh_h5.m 的直接消费数据集，          #
    # 也不是 M2 正式核心三数组。是否需要由目标格式直接证据和 M4 侦察          #
    # 结果决定。当前保留字段定义以维持与现有过渡代码的兼容性，               #
    # 但不得将其描述为 TRIMEG 核心消费字段或无条件必填字段。                 #
    #                                                                     #
    # 本轮不为了删除这些字段而扩大重构；后续 OFT Adapter 首次实现            #
    # 也不得为了填充这些旧字段而重新建设边界恢复算法。若现有构造函数         #
    # 强制要求它们，应在后续源码任务中采用最小兼容处理并报告，               #
    # 不得伪造物理语义。                                                    #
    # ------------------------------------------------------------------ #

    # 边界线段连接表（可选兼容字段）
    boundary_segments: Optional[np.ndarray] = None  # shape=(S, 2)，dtype=int32

    # 边界线段标记（可选兼容字段）
    boundary_markers: Optional[np.ndarray] = None   # shape=(S,)，dtype=int32

    # 节点边界标记（可选兼容/适配字段）
    # 用于区分内部节点（0）和边界节点（非零），供 TRIMEG HDF5 idxivert/idxevert 计算使用
    # 【待运行验证】OFT build_mesh() 是否直接提供等价信息，待 M3 适配阶段确认
    # 若 OFT 不直接提供，LinkMesh 需要在 HDF5 Writer 适配层中从网格拓扑推导
    node_markers: Optional[np.ndarray] = None       # shape=(N,)，dtype=int32
                                                    # 0=内部节点，非零=边界节点

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
        """边界线段总数（若 boundary_segments 为 None 则返回 0）。"""
        if self.boundary_segments is None:
            return 0
        return self.boundary_segments.shape[0]
```

**关于 `node_markers` 与 TRIMEG HDF5 的关系**：

`loadfemmesh_h5.m` 读取 `/femmesh/idxivert`（内部节点全局索引）和 `/femmesh/idxevert`（边界节点全局索引）。这两个数据集需要区分内部节点和边界节点。`node_markers` 是 LinkMesh 内部用于计算这两个索引集合的辅助字段。

【待运行验证】OFT `build_mesh()` 是否直接提供等价的内外节点区分信息，需要在 M3 适配阶段验证。若 OFT 不直接提供，LinkMesh 需要在 HDF5 Writer 适配层中从网格拓扑（边界边）推导节点边界标记。**本轮及下一轮 M2 Adapter 首次实现不得为了填充该字段而重新建设边界恢复算法。**

### 2.3 `BoundaryConfig`（历史/过渡候选，非 M2 正式主路径）

【v1.8 状态】`BoundaryConfig` 是历史/过渡候选数据结构，原用于向 Python `triangle` 包传递输入。M2 正式主路径已由 `mesher/oft_adapter.py` 的 OFT `gs_Domain` 调用替代。

当前保留其定义以维持与现有过渡代码（`triangle_wrapper.py`、`cli.py` 中 `_build_boundary_config()`）的兼容性，但不得将其作为 M2 正式架构的核心数据结构进行扩展。

---

## 3. 数据流转架构（OFT 优先，LinkMesh 最小适配）

### 3.1 正式目标数据管道（v1.8）

LinkMesh 的数据流以 OFT 为核心网格生成后端，LinkMesh 只负责最小输入编排、统一对象适配、目标格式翻译和 CLI 编排。

```text
GFile 平衡文本
  │
  ↓ [薄 Adapter：调用 OFT GEQDSKEquilibrium，提取边界坐标，绝不手动解析文本]
src/linkmesh/readers/gfile_reader.py
  │  ← from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium
  │  ← eq = GEQDSKEquilibrium(filepath)
  │  ← 提取 eq.boundary_R / eq.boundary_Z / eq.R_mag / eq.Z_mag 等属性
  │
  ↓ [封装为 GFileData，传递给 CLI 编排层]
GFileData
  │
  ↓ [M2 正式网格生成适配层：src/linkmesh/mesher/oft_adapter.py]
  │  [接收 GFileData + 网格尺度参数]
  │  [极薄接口规范化：坐标转 (N,2) float64、删首尾重复闭合点、验证最低点数、构造 outer 包围范围]
  │  [调用 OFT gs_Domain.define_region() / add_polygon() / add_annulus() / add_rectangle() / add_enclosed()]
  │  [调用 OFT gs_Domain.build_mesh() 完成区域组织、边界处理、点合并、重采样、种子和网格生成]
  │  [OFT 内部通过 liboft_triangle 完成 Triangle 调用，LinkMesh 不直接维护]
  │  [区域编号由 OFT 区域模型决定，LinkMesh 原样接收]
  │
  ↓ [OFT build_mesh() 返回 (pts[np,2], lc[nc,3], reg[nc])，lc 为 0-based]
  │  [可选：OFT save_gs_mesh() 写出静态中间网格（OFT 自有格式，非 TRIMEG HDF5）]
  │
  ↓ [oft_adapter.py 最小适配：规范化并检查 shape/dtype/有限值/索引范围/区域编号/退化三角形]
  │  [封装为轻量 Mesh2D 统一对象；原样保存 OFT 返回的区域编号，不重编号]
Mesh2D  (轻量统一网格对象，v1.8 核心三数组 nodes/triangles/region_ids)
  │
  ├──→ [第一阶段战役：HDF5 映射对齐]
  │      src/linkmesh/writers/hdf5_writer.py
  │      (严格对照 docs/trimeg/loadfemmesh_h5.m 黄金标尺)
  │      (Writer 不重编号、偏置、压缩或排序 region_ids)
  │      (节点索引 0-based → 1-based 偏置由 Writer 在写出阶段执行)
  │      (不根据整数编号猜测区域物理语义)
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

**关于可选静态中间网格**：

OFT 已有 `save_gs_mesh()` / `load_gs_mesh()` 能力，可将网格结果保存为 HDF5 或 JSON 格式。这是 OFT 自有格式，**不是 TRIMEG HDF5 格式，也不是 M3DC1 `.smb` 格式**。可将其用于调试、归档和诊断，但正式生产链优先使用内存结果（`OFT build_mesh() → oft_adapter 最小适配 → HDF5/.smb`），不强制增加"OFT 写文件 → LinkMesh 再读文件"的中间步骤。

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

**【v1.8 编排约束】** `cli.py` 只负责参数解析和调用 `mesher/oft_adapter.py`，不得在 CLI 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换。这些逻辑由 OFT `gs_Domain` 内部处理。

---

## 4. 数据格式对齐规范（两阶段战役核心方法论）

本节是 LinkMesh 两大 Writer 模块的核心实现方法论，Aider 在编写 `src/linkmesh/writers/` 下任何代码前必须完整阅读本节。**本轮 v1.8 不修改 M3 HDF5 字段契约，本节内容保持 v1.7 不变。**

### 4.1 第一战役：TRIMEG HDF5 格式映射

**【已确认事实】战役定性**：HDF5 是通用开放格式，TRIMEG 侧已有现成的 MATLAB 读取脚本 `docs/trimeg/loadfemmesh_h5.m` 作为黄金对照标尺，格式完全透明可读。以下所有规范均直接从该脚本逐行逆向提取，无任何推断成分。

#### 4.1.1 `loadfemmesh_h5.m` 直接消费的数据集（已确认事实）

【已确认事实】以下数据集路径和读取方式直接来自 `docs/trimeg/loadfemmesh_h5.m` 逐行解析：

**必须写出的数据集（MATLAB 无条件读取）**：

| HDF5 路径 | MATLAB 读取方式 | 说明 |
|---|---|---|
| `/femmesh/nvert` | `h5read(h5file,'/femmesh/nvert')` | 节点总数，标量 |
| `/femmesh/ntria` | `h5read(h5file,'/femmesh/ntria')` | 三角形总数，标量 |
| `/femmesh/nvert_in` | `h5read(h5file,'/femmesh/nvert_in')` | 内部节点数，标量 |
| `/femmesh/nvert_ex` | `h5read(h5file,'/femmesh/nvert_ex')` | 边界节点数，标量 |
| `/femmesh/vert` | `h5read(h5file,'/femmesh/vert').'` | 节点坐标，末尾有 `.'`（转置） |
| `/femmesh/idxivert` | `h5read(h5file,'/femmesh/idxivert')` | 内部节点全局索引 |
| `/femmesh/idxevert` | `h5read(h5file,'/femmesh/idxevert')` | 边界节点全局索引 |
| `/femmesh/tria` | `h5read(h5file,'/femmesh/tria').'` | 三角形数据，末尾有 `.'`（转置） |

**可选数据集（MATLAB 在 try...catch 块中读取，失败时仅打印 warning）**：

| HDF5 路径 | MATLAB 读取方式 | 说明 |
|---|---|---|
| `/femmesh/nbcRZ` | `h5read(h5file,'/femmesh/nbcRZ')` | 边界节点坐标点数，标量 |
| `/femmesh/Rbc` | `h5read(h5file,'/femmesh/Rbc')` | 边界节点 R 坐标 |
| `/femmesh/Zbc` | `h5read(h5file,'/femmesh/Zbc')` | 边界节点 Z 坐标 |

**【重要澄清】** `loadfemmesh_h5.m` 中**没有**读取以下数据集：`boundary_segments`、`boundary_markers`、`node_markers`。这些字段是 LinkMesh 内部字段，不是 TRIMEG MATLAB 直接消费的数据集，不得将其写入 TRIMEG HDF5 文件并声称为 TRIMEG 消费字段。

#### 4.1.2 转置规律（核心机制，必须理解）

【已确认事实】`loadfemmesh_h5.m` 中凡是末尾带 `.'`（非共轭转置运算符）的 `h5read` 调用，均说明该数组在 HDF5 文件中以 **Fortran 列优先（column-major）顺序**存储。

- MATLAB `h5read` 读取 HDF5 时，会将 C 行优先的存储顺序自动解释为 Fortran 列优先，因此读出的矩阵维度与 HDF5 中存储的维度**行列互换**。
- Python `h5py` 写入时，若要让 MATLAB 读取后得到 `(nvert, 2)` 的矩阵，必须在 HDF5 中存储 `(2, nvert)` 的数组。
- **实现公式**：`h5file.create_dataset(key, data=array.T)` —— 即写入前先转置。

涉及转置的字段：`/femmesh/vert`（需转置）、`/femmesh/tria`（需转置）。
不涉及转置的字段：所有标量、所有一维数组（`idxivert`、`idxevert`、`Rbc`、`Zbc` 等）。

#### 4.1.3 索引偏置规律（核心机制，必须理解）

【已确认事实】MATLAB 使用 1-based 索引。

凡是写入 HDF5 的**节点索引**字段，必须执行 `+1` 偏置转换（前提：LinkMesh 内部使用 0-based 索引；M2-0 已确认 OFT 返回 0-based 连接表）：

- `mesh.triangles`（0-based）→ 写入 `/femmesh/tria` 前三列时 `+1` → 1-based
- 内部节点的全局位置索引 → 写入 `/femmesh/idxivert` 时 `+1` → 1-based
- 边界节点的全局位置索引 → 写入 `/femmesh/idxevert` 时 `+1` → 1-based

`region_id`（若写入 `/femmesh/tria` 第4列）**不需要** `+1`，它是物理标记值而非节点索引。

【已确认事实，M2-0】OFT `build_mesh()` 返回的 `lc` 数组为 **0-based**。因此写入 HDF5 时需要 `+1` 偏置。该偏置由 HDF5 Writer 在写出阶段执行，不在 `Mesh2D` 或 `oft_adapter.py` 阶段处理。

#### 4.1.4 关于 `idxivert` 和 `idxevert` 的含义

【已确认事实】`loadfemmesh_h5.m` 读取 `idxivert`（内部节点全局索引）和 `idxevert`（边界节点全局索引）。根据 User 对真实样例的核对：`nvert_in + nvert_ex == nvert`，两组索引分别表示内、外节点集合，不重叠。

【待运行验证】如何从 OFT `build_mesh()` 返回结果中区分内部节点和边界节点，需要在 M3 适配阶段验证。可能的方式包括：
1. OFT 直接提供节点边界标记信息；
2. 从 OFT 返回的边界线段信息推导；
3. 从网格拓扑（边界边）推导。

#### 4.1.5 关于 `/femmesh/tria` 第四列的含义

【待确认】`loadfemmesh_h5.m` 读取 `femmesh.tria` 后 shape 为 `(T, 4)`（转置后），但脚本本身没有显式说明第四列的含义。

现有 `hdf5_writer.py` 将 `region_ids` 写入第四列。这一做法需要与实际 TRIMEG 样例和 TRIMEG 完整源码联合核对后方可确认。

**当前处理原则**：
- 保留现有 `hdf5_writer.py` 中将 `region_ids` 写入第四列的实现；
- 在 M3 验收时，必须通过真实 TRIMEG 样例核对第四列的实际含义和期望值；
- 在获得直接证据前，不得将"第四列为 region_id"声称为已确认事实。

#### 4.1.6 完整字段映射契约（Field Mapping Contract）

以下表格是 `src/linkmesh/writers/hdf5_writer.py` 的实现依据，每一行均标注事实状态。

| HDF5 数据集路径 | HDF5 中存储的 shape | MATLAB 读取后 shape | dtype | 数据来源（Python `Mesh2D` 字段） | 转换公式 | 状态 |
|---|---|---|---|---|---|---|
| `/femmesh/nvert` | 标量 | 标量 | int32 | `mesh.n_nodes` | 无转换 | 已确认 |
| `/femmesh/ntria` | 标量 | 标量 | int32 | `mesh.n_triangles` | 无转换 | 已确认 |
| `/femmesh/nvert_in` | 标量 | 标量 | int32 | 内部节点数（计算方式待 M3 适配确认） | 无转换 | 已确认（计算方式待确认） |
| `/femmesh/nvert_ex` | 标量 | 标量 | int32 | 边界节点数（计算方式待 M3 适配确认） | 无转换 | 已确认（计算方式待确认） |
| `/femmesh/vert` | `(2, nvert)` | `(nvert, 2)` | float64 | `mesh.nodes`，列顺序 `[R, Z]` | **转置写入**：`mesh.nodes.T` | 已确认 |
| `/femmesh/idxivert` | `(nvert_in,)` | `(nvert_in,)` | int32 | 内部节点全局位置 | **+1 偏置**（LinkMesh 内部 0-based，M2-0 已确认） | 已确认 |
| `/femmesh/idxevert` | `(nvert_ex,)` | `(nvert_ex,)` | int32 | 边界节点全局位置 | **+1 偏置**（LinkMesh 内部 0-based，M2-0 已确认） | 已确认 |
| `/femmesh/tria` | `(4, ntria)` | `(ntria, 4)` | int32 | 前3列：`mesh.triangles`；第4列：`mesh.region_ids`（待确认） | **前3列 +1 偏置（0-based）+ 整体转置写入；第4列原样写出** | 前3列已确认；第4列含义待真实样例核对 |
| `/femmesh/nbcRZ` | 标量 | 标量 | int32 | 边界节点数（与 `nvert_ex` 相同） | 无转换 | 已确认（可选字段） |
| `/femmesh/Rbc` | `(nbcRZ,)` | `(nbcRZ,)` | float64 | 边界节点的 R 坐标 | 无转换 | 已确认（可选字段） |
| `/femmesh/Zbc` | `(nbcRZ,)` | `(nbcRZ,)` | float64 | 边界节点的 Z 坐标 | 无转换 | 已确认（可选字段） |

#### 4.1.7 `/femmesh/tria` 的精确构造公式（当前实现，待 M3 真实样例核对）

当前 `hdf5_writer.py` 中的实现：

```python
# Step 1：将三角形连接表从 0-based 转换为 1-based（M2-0 已确认 OFT 返回 0-based）
tria_nodes_1based = (mesh.triangles + 1).astype(np.int32)   # shape=(T, 3)

# Step 2：将 region_ids 扩展为列向量（原样写出，不执行 +1，不根据整数值推断区域语义）
# 【待确认】第四列是否为 region_id，需要真实 TRIMEG 样例核对
region_col = mesh.region_ids.reshape(-1, 1).astype(np.int32)  # shape=(T, 1)

# Step 3：水平拼接，构造 (T, 4) 矩阵
tria_4col = np.hstack([tria_nodes_1based, region_col])  # shape=(T, 4)

# Step 4：转置后写入 HDF5，使 HDF5 中存储为 (4, T)
# MATLAB h5read 后自动转置得到 (T, 4)，与 loadfemmesh_h5.m 期望一致
h5file.create_dataset('/femmesh/tria', data=tria_4col.T.astype(np.int32))
```

#### 4.1.8 可选字段处理规范

【已确认事实】`loadfemmesh_h5.m` 中 `nbcRZ`、`Rbc`、`Zbc` 三个字段被包裹在 `try...catch` 块中，读取失败时仅打印 warning 而不报错。这说明这三个字段在 TRIMEG 中是**可选字段**。

`src/linkmesh/writers/hdf5_writer.py` 的处理策略：**始终写出这三个字段**（因为边界节点坐标可以从 `mesh.nodes` 和节点边界标记中提取），不需要做条件判断。

【待运行验证】`Rbc`/`Zbc` 是否为 TRIMEG 求解必需字段，需要更多直接消费证据确认。当前策略（始终写出）是保守安全的做法。

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
   - M3DC1 特有的区域数量、几何分类、连续性要求（如 C1 连续性、高阶单元等）
3. **实现路线**：由侦察结果和主管确认决定，可能包括但不限于：
   - Python 二进制写出；
   - 调用 SCOREC/PUMI 官方 API；
   - 调用经确认的官方转换程序；
   - 其他由直接证据确认的方式。
4. **前置条件**：`src/linkmesh/writers/smb_writer.py` 的具体实现**必须等待** M3 完整验收通过、只读侦察任务完成并经主管确认后方可开始编写。
5. **M3DC1 特有适配原则**：若 M3DC1 有额外区域、边界实体、几何分类或连续性要求（如 C1 连续性、高阶单元等），只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。

#### 4.2.1 M4 侦察线索（组内交流，非直接源码证据）

以下内容来自组内交流，记录为 M4 侦察线索，不得升级为已确认格式事实：

- M3DC1 可能存在 Multi Region 网格，区域数可能依装置、算例和 ModelFile 而变化；
- MeshFile 可能保存离散网格，ModelFile 可能保存边界/模型信息；
- 导体和线圈的完整含时物理功能可能有限；
- M3DC1 可能有 C1 连续性要求或高阶单元需求，但这不是当前阻止 OFT 网格后端的事实，需要 M4 源码侦察确认。

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
| M3DC1 区域数量 | 不固定，依装置和算例而变化 | 【待源码确认，不得由 P0 两/三区域样例固定】 |

---

## 5. 区域标记与边界标记约定

### 5.1 区域编号总体原则（v1.8）

【v1.8 原则】LinkMesh 不维护全局固定的区域编号映射（如 `1=plasma、2=vacuum、3=wall`）。

**正式原则**：

1. **区域由 OFT `gs_Domain` 的命名区域和最终区域编号定义**；
2. **LinkMesh 原样保存 OFT 返回的三角形区域编号**，不重编号、不压缩、不排序、不执行 `+1`；
3. **LinkMesh、`Mesh2D`、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义**；
4. **区域语义应从 OFT `domain.region_info` 的区域名称、类型和最终 ID 获得**，不得从整数值推断；
5. **区域数量由 OFT 当前区域模型决定**，不在 LinkMesh 中写死；
6. **当前两区域 PLASMA/OUTER 与三区域 PLASMA/VACUUM/OUTER 只作为验收样例**，不是 LinkMesh 的全局固定架构；
7. **M3DC1 Multi Region 的区域数不得由这两个样例固定**；
8. **若某个物理区域不属于目标计算域，正确做法是构造不包含该区域的 OFT 区域模型，使其不生成三角形**；不得保留区域空间后将其编号设为 0。OFT 中非正区域编号表示未认领或非法区域，不是"无物理方程"的合法标签。

### 5.2 P0 验收样例（非全局固定架构）

以下两个样例仅用于 P0 阶段验证，不代表 LinkMesh 的全局固定区域编号约定。OFT 最终编号由 `build_mesh()` 决定。

#### 样例 A：三区域验收样例（当前真实 DIII-D 样例）

当 GFile 提供有效、闭合且满足嵌套关系的第一壁/limiter 轮廓时，P0 验收场景从内到外定义三个区域。**M2-0 真实运行已确认 OFT 最终区域编号如下**：

| OFT 区域名称 | OFT reg_type | OFT 最终 ID（M2-0 实测） |
|---|---|---|
| `PLASMA` | `plasma` | 1 |
| `OUTER` | `boundary` | 2 |
| `VACUUM` | `vacuum` | 3 |

**注意**：该编号只描述当前 OFT 区域模型下的实测结果，**不得外推为所有模型的固定编号表**。区域数量和最终 ID 由 OFT `build_mesh()` 决定。

#### 样例 B：两区域合成验收样例

两区域合成样例定义 `PLASMA` + `OUTER`。M2-0 合成两区域运行中区域统计为 `{1:83, 2:401}`（详见第 13 节 M2-0 证据）。

### 5.3 边界标记约定（历史/过渡代码，非 OFT 正式约定）

【历史/过渡】以下为历史过渡代码（Python triangle 路线）中使用的边界标记约定，仅供参考，不作为 OFT 路线的正式约定：

| boundary_marker | 历史含义 | 备注 |
|---|---|---|
| 1 | LCFS | 历史过渡代码约定 |
| 2 | first wall/limiter | 历史过渡代码约定 |
| 3 | outer boundary | 历史过渡代码约定 |
| 0 | 内部节点（非边界） | — |

【待运行验证】OFT `gs_Domain` 在 `build_mesh()` 后是否提供边界线段标记信息，以及标记的具体整数值约定，需要在 M3 适配阶段验证（`boundary_markers`/`boundary_segments` 为 `Mesh2D` 非核心可选字段）。

---

## 6. src/linkmesh/readers/gfile_reader.py 实现规范（OFT Adapter 模式）

### 6.1 设计原则：薄 Adapter，绝不重复造轮子

【已确认事实】`src/linkmesh/readers/gfile_reader.py` 的唯一职责是作为**薄 Adapter（接线员）**：

1. 调用 OFT（OpenFUSIONToolkit）提供的 `GEQDSKEquilibrium` 类读取 GFile；
2. 从 OFT 返回对象的属性中提取 LinkMesh 所需的字段；
3. 封装为 `GFileData` 对象返回。

**【绝对禁止】** 在 `src/linkmesh/readers/gfile_reader.py` 中手动执行任何原始 GFile 文本 I/O、字符串切分、Fortran 格式化数值解析或 EQDSK 格式字段手动提取。OFT 已经提供了完整、经过验证的 GFile 解析实现，LinkMesh 直接复用即可。

### 6.2 OFT 运行依赖（已确认事实）

【已确认事实】以下 OFT 版本已在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证；并已在 M2-0 中于正式 Conda 环境（Python 3.12.13）验证网格生成链路：

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

**事实等级**：`GEQDSKEquilibrium` 已通过只读源码侦察确认存在，且已在服务器（liustation，`openfusiontoolkit==26.6`）上实际运行验证，成功读取 `ITER_test.eqdsk` 和 `DIIID/g192185.02440` 并提取全部所需字段；M2-0 中进一步验证其输出可直接驱动 OFT `gs_Domain` 网格生成链路。

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
3. **重采样**：LCFS 点数可能过多或过少，OFT `gs_Domain` 在调用 `add_polygon()`/`add_annulus()` 时内部负责重采样（非 `gfile_reader.py` 职责）。

---

## 7. OFT gs_Domain 网格生成适配规范（M2 正式路线：mesher/oft_adapter.py）

### 7.1 oft_adapter.py 正式职责（M2 正式主路径）

【计划新增，M2 正式主路径】`src/linkmesh/mesher/oft_adapter.py` 是 M2 正式网格生成适配层。其职责严格限定为以下七点：

1. 接收 `GFileData` 和必要网格尺度参数；
2. 使用正式安装的 `OpenFUSIONToolkit.TokaMaker.meshing.gs_Domain`；
3. 调用 OFT 的 `define_region()`、`add_polygon()`、`add_annulus()`、`add_rectangle()`、必要时 `add_enclosed()` 和 `build_mesh()`；
4. 由 OFT 完成区域组织、边界处理、点合并、边界重采样、区域种子、Triangle 输入构造和三角网格生成；
5. 将 OFT `build_mesh()` 返回的 `pts`、`lc`、`reg` 规范化为 LinkMesh 的轻量统一内存网格对象（`Mesh2D`）；
6. 检查数组 shape、dtype、有限值、索引范围、区域属性长度、非正区域编号和退化三角形；
7. 不复制 OFT 的通用几何、区域拓扑、种子搜索、重采样或 Triangle 调用算法。

**【OFT 治理铁律】** 该模块只调用 Conda 环境中正式安装的 OFT：
- 不修改 OFT 源码；
- 不读取或改写 OFT 安装目录；
- 不维护 OFT fork；
- 不依赖仓库 `TOKAMAKER/` 快照作为运行时包。

### 7.2 OFT gs_Domain 调用方式（M2 正式路线，M2-0 已验证）

【已确认事实，来自只读侦察 `meshing.py` 与 M2-0 运行验证】OFT `gs_Domain` 提供完整的区域定义、边界组织、区域种子和网格生成能力。M2 正式路线通过 `oft_adapter.py` 调用 OFT `gs_Domain`，不复制 OFT 已实现的通用几何逻辑。

**OFT `gs_Domain` 调用流程（示意；具体参数由 oft_adapter.py 实现时按 M2-0 验证结果确定）**：

```python
from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain

# Step 1：创建 gs_Domain 对象
domain = gs_Domain(...)

# Step 2：定义命名区域（区域类型、分辨率等）
domain.define_region('PLASMA', dx=..., reg_type='plasma')
domain.define_region('VACUUM', dx=..., reg_type='vacuum')
domain.define_region('OUTER', dx=..., reg_type='boundary')

# Step 3：添加几何边界（LCFS、第一壁、人工 outer boundary 等）
# 使用 add_polygon() / add_annulus() / add_rectangle() 添加区域边界
# 必要时使用 add_enclosed() 添加区域内部种子点

# Step 4：调用 build_mesh() 生成网格
pts, lc, reg = domain.build_mesh()
# pts: shape=(np, 2)，节点坐标，float64
# lc:  shape=(nc, 3)，三角形连接表，int32，0-based（M2-0 确认）
# reg: shape=(nc,)，三角形区域编号（来自 OFT 区域模型），int32
```

**【M2-0 已确认】** 以上调用链在 M2-0 真实运行中通过验证：
- `gs_Domain` 可以直接接受 GFile 提供的 LCFS 和第一壁轮廓（经极薄规范化）；
- `build_mesh()` 返回 `reg` 数组的区域编号为正整数，与 `domain.region_info` 中定义区域一一对应；
- `lc` 数组为 0-based，索引范围 `0..N-1`；
- `pts` 数组为 `(N, 2)` float64。

**【待 oft_adapter.py 实现时确定的接口细节】**：
- `define_region()` 的 `dx`、`reg_type` 等参数如何从 CLI 网格尺度参数映射；
- `add_polygon()` / `add_annulus()` / `add_rectangle()` / `add_enclosed()` 的具体调用组合；
- `gs_Domain(...)` 构造参数（如 padding）。

### 7.3 最小输入规范化（oft_adapter.py 允许的极薄预处理）

允许 `oft_adapter.py` 在调用 OFT 前做**极薄的接口规范化**：

1. 将 LCFS 和第一壁坐标转换为 shape `(N, 2)` 的有限 `float64` 数组；
2. 删除首尾近似重复的闭合点，避免 OFT 产生零长度闭合小段；
3. 验证点数满足 OFT 调用的最低要求；
4. 构造人工 outer boundary 所需的简单包围范围；
5. 把网格尺度参数传给 OFT。

**【严禁】** 不允许在 LinkMesh 中复制 OFT 的尖角处理、Sliver 处理、Small feature 处理、重采样、自交通用框架、共享边界拆分或区域种子搜索。第一壁尖角和短线段优先交给 OFT 处理；只有实际 OFT 运行失败且有直接证据时，才提出新的最小预处理建议。

【M2-0 证据】DIII-D 真实样例中，第一壁尖角和短线段触发 OFT `Repeated points`、`Sliver`、`Small feature` 警告，但最终网格质量通过（最小内角 `20.222°`，退化三角形 0）。这证明尖角和短线段交给 OFT 处理是可行的，无需 LinkMesh 侧额外预处理。

### 7.4 LinkMesh 最小适配层（OFT 输出 → Mesh2D）

OFT `build_mesh()` 返回 `(pts, lc, reg)` 后，`oft_adapter.py` 进行最小适配，规范化为 `Mesh2D` 轻量统一对象，并执行以下检查：

- `nodes`：`pts` 转为 `(N, 2)` float64；检查有限值；
- `triangles`：`lc` 转为 `(T, 3)` 整数；检查 `0 <= lc < N`（0-based，M2-0 确认，无需再次偏置）；
- `region_ids`：`reg` 转为 `(T,)` 整数；原样保存，不重编号；检查非正区域编号（正常应全部为正）；
- 退化三角形检查：重复顶点三角形数、非正/近零有向面积三角形数应为 0；
- 区域属性长度检查：`len(reg) == T`。

区域语义（名称、类型、ID）从 OFT `domain.region_info` 获得，不从整数值推断。

### 7.5 历史/过渡代码（Python triangle 包路线，非 M2 正式主路径）

【v1.8 状态】以下历史/过渡代码不再作为 M2 正式主路径，已被 `oft_adapter.py` 替代：

- `src/linkmesh/mesher/triangle_wrapper.py`：Python `triangle` 包底座封装；
- `src/linkmesh/cli.py` 中的 `_build_boundary_config()`：历史过渡胶水代码；
- `tests/test_triangle_wrapper.py`：历史过渡测试（36/36 通过，作为历史证据保留）。

**处置原则**：本轮及下一轮 M2 任务均保持这些文件不动，暂不删除、不扩展。**禁止为了保存旧实现继续扩展其区域拓扑和通用几何能力。** 是否以后删除旧模块和旧测试不在本轮裁决。旧 Triangle 的 36 项测试作为历史证据保留，**但不能作为 OFT Adapter 正式验收的替代**。

---

## 8. src/linkmesh/cli.py 编排规范（M2 OFT 路线）

### 8.1 职责与编排原则

`src/linkmesh/cli.py` 是 LinkMesh 的 CLI 编排层，负责：

1. 解析命令行参数；
2. 调用 `read_gfile()` 获取 `GFileData`；
3. 将 `GFileData` 和网格尺度参数传给 `mesher/oft_adapter.py`（最小输入编排）；
4. 由 `oft_adapter.py` 调用 OFT `gs_Domain.build_mesh()` 并返回 `Mesh2D`；
5. 调用 `write_hdf5()` 或 `write_smb()` 写出目标格式；
6. 调用 `plot_mesh()` 生成可视化自检图。

**【禁止】** 不得在 `cli.py` 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换。不得复制 OFT 通用几何逻辑（边界重采样、点合并、区域种子搜索等）。这些逻辑由 OFT `gs_Domain` 内部处理，或由 `oft_adapter.py` 编排。

### 8.2 M2 OFT 编排（下一轮实现）

【下一轮 M2 实现范围】`cli.py` 的 M2 正式路径应最小修改为调用 `mesher/oft_adapter.py`。具体编排入口的函数命名与签名由下一轮源码任务实现时确定，本轮不锁定实现细节。约束为：

- `cli.py` 只传递 `GFileData` 和网格尺度参数；
- 不在 `cli.py` 中实现任何几何/区域/种子/Triangle 算法；
- 区域编号原样从 `oft_adapter.py` 返回的 `Mesh2D` 获取，不在 `cli.py` 中重编号。

### 8.3 历史/过渡代码（`_build_boundary_config`）

【v1.8 状态】`cli.py` 中现有的 `_build_boundary_config()` 函数是历史/过渡胶水代码，不再作为 M2 正式架构的核心实现。M2 正式路径由调用 `oft_adapter.py` 替代。

当前保留 `_build_boundary_config()` 以维持与现有过渡代码的兼容性，但不得继续扩展其功能。下一轮 M2 任务对 `cli.py` 只做最小修改以接入 `oft_adapter.py`，不扩展 `_build_boundary_config()`。

---

## 9. src/linkmesh/writers/hdf5_writer.py 实现规范（第一战役：TRIMEG HDF5 格式映射）

**【本轮 v1.8 不修改 M3 HDF5 字段契约，本节内容保持 v1.7 不变。】**

### 9.1 实现依据与黄金标尺

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 的唯一实现依据是 `docs/trimeg/loadfemmesh_h5.m`。该脚本是 TRIMEG 求解器读取网格 HDF5 文件的 MATLAB 实现，其每一行 `h5read` 调用直接揭示了 TRIMEG 对 HDF5 文件结构的期望。所有数据集路径名、存储形状、数据类型和索引约定均以该脚本为最终裁决依据，不得凭推断自行补充。

### 9.2 TRIMEG HDF5 物理文件结构树

【已确认事实】以下结构树直接来自 `loadfemmesh_h5.m` 逐行解析（第四列含义标注为待确认）：

```text
mesh.h5
└── /femmesh/                          # 唯一顶层组，名称固定为 "femmesh"
    │
    ├── nvert        [标量, int32]      # 节点总数 N
    ├── ntria        [标量, int32]      # 三角形总数 T
    ├── nvert_in     [标量, int32]      # 内部节点数（计算方式待 M3 适配确认）
    ├── nvert_ex     [标量, int32]      # 边界节点数（计算方式待 M3 适配确认）
    │
    ├── vert         [shape=(2,N), float64]   # 节点坐标，HDF5 中存 (2,N)
    │                                          # MATLAB h5read 后转置得 (N,2)
    │                                          # 行顺序：第0行=R坐标，第1行=Z坐标
    │
    ├── idxivert     [shape=(nvert_in,), int32]  # 内部节点全局索引，1-based
    ├── idxevert     [shape=(nvert_ex,), int32]  # 边界节点全局索引，1-based
    │                                             # nvert_in + nvert_ex == nvert（已确认）
    │
    ├── tria         [shape=(4,T), int32]     # 三角形数据，HDF5 中存 (4,T)
    │                                          # MATLAB h5read 后转置得 (T,4)
    │                                          # 列0-2：节点索引（1-based）
    │                                          # 列3：【待确认】含义需真实样例核对
    │
    ├── nbcRZ        [标量, int32]      # 边界节点坐标点数（等于 nvert_ex）【可选字段】
    ├── Rbc          [shape=(nbcRZ,), float64]  # 边界节点 R 坐标 [m]【可选字段，始终写出】
    └── Zbc          [shape=(nbcRZ,), float64]  # 边界节点 Z 坐标 [m]【可选字段，始终写出】
```

**【重要说明】** `boundary_segments`、`boundary_markers`、`node_markers` 不是 TRIMEG HDF5 的直接消费数据集，不得写入 TRIMEG HDF5 文件并声称为 TRIMEG 消费字段。

### 9.3 精确字段映射契约（Field Mapping Contract）

见第 4.1.6 节完整字段映射契约表格。

### 9.4 `/femmesh/tria` 精确构造公式

见第 4.1.7 节。

### 9.5 `write_hdf5()` 实现状态与 M3 前置条件

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 中的 `write_hdf5(mesh, filepath, verbose=True)` 函数已**完整实现**（非占位），按第 4.1.6 节映射契约逐一写出全部 11 个数据集。

**M3 前置条件**：M3 真实验收必须基于已经通过 M2 的 OFT 网格结果（`oft_adapter.py` 输出的 `Mesh2D`）。在 M2 通过验收之前，不得进入 M3 验收。

---

## 10. src/linkmesh/writers/smb_writer.py 实现规范（第二战役：M3 验收后侦察确定实现路线）

### 10.1 实现依据与前置条件

`src/linkmesh/writers/smb_writer.py` 的实现依赖对 `SCOREC/PUMI` 开源 C++ 源码的只读侦察结果，以及主管对实现路线的确认。**在 M3 完整验收通过、侦察任务完成并经主管确认前，本模块保持 `NotImplementedError` 占位实现，严禁提前编写任何字节流或序列化逻辑。**

侦察目标文件（只读，严禁修改，M3 验收后执行）：
- `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`：`.smb` 文件读取的 C++ 实现入口
- `M3DC1/m3dc1_scorec/include/m3dc1_model.h`：model `.txt` 配套文件格式
- `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`：高阶节点需求确认

### 10.2 `write_smb()` 函数接口（占位，待 M4 里程碑实现）

【已确认事实】当前 `write_smb()` 保持 `raise NotImplementedError` 占位实现。实现路线（包括但不限于 Python 二进制写出、调用官方 API 或其他方式）必须由侦察结果和主管确认决定，不得提前锁定。若 M3DC1 有额外区域、边界实体、几何分类或连续性要求，只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。

### 10.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。

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
- 若 `show_region_ids=True`，按区域 ID 着色填充（颜色方案不依赖固定区域编号语义，按实际区域 ID 集合动态分配颜色）
- 叠加绘制 LCFS 边界曲线（红色实线）
- 若有第一壁数据，叠加绘制（蓝色虚线）
- 标注磁轴位置（红色叉号）
- 若 `show_boundary_markers=True` 且 `mesh.boundary_markers` 不为 None，用不同颜色标注边界线段类型
- 输出统计信息文本框（节点数、三角形数、边界线段数）
- 设置 `aspect='equal'`，保存为 PNG 文件，dpi=150

### 11.2 LCFS 显示闭合注意事项（M2-0 观察）

【M2-0 观察】M2-0 临时验收绘图脚本中，删除 LCFS 重复末点后未重新连接首尾，造成 LCFS 红线局部显示缺口。这是**显示问题，不是 OFT 几何或网格缺口**。

【下一轮 plotter 最小修改要点】正式 `plotter.py` 或临时验收绘图应在绘制 LCFS 显示曲线时显式闭合首尾（例如在绘图前追加首点到末尾，仅用于显示，不修改底层数据对象）。下一轮 M2 任务允许对 `plotter.py` 做此最小修改，使其基于 `nodes`/`triangles`/`region_ids` 绘图并闭合显示 LCFS。

---

## 12. 依赖清单

### 12.1 核心运行依赖

```text
numpy>=1.24.0
h5py>=3.8.0
matplotlib>=3.7.0
openfusiontoolkit==26.6
```

**说明**：
- `openfusiontoolkit==26.6` 为当前在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证、并在 M2-0 中于正式 Conda 环境（Python 3.12.13）验证网格生成链路的版本，不得写成 `>=26.6`，不得声称其他版本已经验证。
- OFT 通过 pip 安装官方 wheel 获取，**不依赖** `TOKAMAKER/` 源码树。
- OFT 内部通过 `liboft_triangle` 完成 Triangle 调用，LinkMesh 不需要单独安装 Python `triangle` 包。
- 【历史/过渡】`triangle>=20230923`：历史过渡代码依赖，M2 正式路线（`oft_adapter.py`）不需要该依赖；是否从依赖清单移除由主管在后续裁决。
- `pyproject.toml`（计划新增）和 `requirements.txt` 的核心运行依赖和版本约束必须保持一致（见第 15 节）。

### 12.2 开发与测试依赖（可选）

```text
pytest>=7.0.0
```

---

## 13. 敏捷渐进里程碑（MVP 开发阶段）

**【铁律】开发时序严格锁死：先完成 M2-0（OFT 可行性验证，已通过），再完成 M2（OFT 网格生成验收），再完成 M3（TRIMEG HDF5 闭环验证），确认网格几何物理质量完全合格后，再进军 M4（`.smb` 侦察与实现）。严禁跳序。**

### 里程碑 M1：GFile 读取验收（P0 第一步）

**当前状态**：【M1 已通过，允许进入 M2-0】

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

### 里程碑 M2-0：OFT gs_Domain 可行性验证（P0 第一点五步）

**当前状态**：【已通过，授权进入 M2 Adapter 实现；不得表述为 M2/M3/M4 已通过】

**目标**：在正式 Linux OFT 环境中验证 OFT `gs_Domain`、`Mesh`、`build_mesh()` 的最小调用链，确认 OFT 网格生成路线的可行性，为 M2 正式实现提供直接运行证据。

#### M2-0 已确认环境证据

【已确认事实】M2-0 运行环境：
- 操作系统：Linux x86_64；
- Python：3.12.13；
- OFT：正式 Conda 环境中的 `OpenFUSIONToolkit 26.6`；
- OFT 包路径：`/home/lxzeng/miniconda3/envs/linkmesh/lib/python3.12/site-packages/OpenFUSIONToolkit`；
- `gs_Domain`、`Mesh`、`Region`、`run_triangle` 均存在且可调用；
- `liboft_triangle.so` 已找到并成功加载；
- LinkMesh 从 `/home/lxzeng/LinkMesh_server/src/linkmesh` 导入。

#### M2-0 合成网格证据

【已确认事实，直接运行结果】

- **两区域合成网格**：267 个节点、484 个三角形；`pts (267,2) float64`、`lc (484,3) int32`、`reg (484,) int32`；索引范围 `0..266`；区域统计 `{1:83, 2:401}`；零面积三角形 0；**通过**。
- **三区域合成网格**：302 个节点、554 个三角形；`pts (302,2) float64`、`lc (554,3) int32`、`reg (554,) int32`；索引范围 `0..301`；区域统计 `{1:83, 2:291, 3:180}`；零面积三角形 0；**通过**。

#### M2-0 真实 DIII-D 证据

【已确认事实，直接运行结果】

- 真实样例：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 实际链路：`真实 GFile → LinkMesh read_gfile/OFT GEQDSKEquilibrium → GFileData → OFT gs_Domain → OFT Mesh/build_mesh → liboft_triangle → pts/lc/reg`

**输入**：
- LCFS 80 个不重复闭合输入点；
- 第一壁 87 个不重复闭合输入点；
- 磁轴 `(R=1.78029311 m, Z=-0.0421587565 m)`。

**输出**：
- 972 个节点；
- 1872 个三角形；
- `pts (972,2) float64`；
- `lc (1872,3) int32`；
- `reg (1872,) int32`；
- 索引范围 `0..971`；
- 区域统计 `{1:633, 2:678, 3:561}`；
- 区域元数据：`PLASMA id=1 type=plasma`、`OUTER id=2 type=boundary`、`VACUUM id=3 type=vacuum`；
- 最小面积 `3.0697138006999725e-06 m²`；
- 最大面积 `0.01121952731171436 m²`；
- 重复顶点三角形 0；
- 面积不大于 `1e-12 m²` 的三角形 0；
- 非正有向面积三角形 0；
- 实际最小内角 `20.222037126210235°`；
- PNG `/tmp/m2_0_oft_diiid.png` 已生成；
- 最终退出码 0。

**人工检查**：
- 三个区域网格覆盖与 LCFS、第一壁、人工 outer boundary 的位置关系正常；
- 第一壁尖角和短线段触发 OFT `Repeated points`、`Sliver`、`Small feature` 警告，但最终网格质量通过；
- LCFS 红线局部缺口由临时绘图脚本删除重复末点后未重新连接首尾造成，是显示问题，不是 OFT 几何或网格缺口；
- 正式 Plotter 或临时验收绘图应显式闭合 LCFS 显示曲线（见第 11.2 节）。

#### M2-0 结论

| 验证项 | 状态 |
|---|---|
| OFT 环境与动态库验证 | PASSED |
| 合成两区域网格 | PASSED |
| 合成三区域网格 | PASSED |
| 真实 DIII-D 三区域网格 | PASSED |
| OFT `pts/lc/reg` 最小契约 | PASSED |
| M2 正式 OFT Adapter | 尚未实现 |
| M2 总体 | 尚未正式 PASSED |
| M3 | 尚未按 OFT 路线开始正式验收 |
| M4 | 禁止开始 |

**M2-0 授权**：M2-0 的通过授权进入 M2 Adapter 实现，但**不能被表述为 M2、M3 或 M4 已通过**。

**涉及模块**：OFT `gs_Domain`（只读参考），`src/linkmesh/mesher/oft_adapter.py`（下一轮 M2 新建）

---

### 里程碑 M2：OFT 网格生成验收（P0 第二步）

**当前状态**：【M2-0 已通过，授权进入 M2 Adapter 实现；M2 总体尚未正式 PASSED】

**目标**：新建 `src/linkmesh/mesher/oft_adapter.py` 正式网格生成适配层，并最小修改 `cli.py` 接入该适配层，使 OFT 网格结果能够进入 LinkMesh 轻量统一对象（`Mesh2D`）并完成真实样例和 PNG/统计验收。

**实现原则**：
- 不得复制 OFT 通用几何逻辑（边界重采样、点合并、区域种子搜索等）；
- 区域编号原样保存 OFT 返回值，不重编号；
- `Mesh2D` 作为轻量统一对象，核心三数组（`nodes`/`triangles`/`region_ids`）首要数据来自 OFT 返回值；
- OFT 返回 0-based `lc`，Adapter 验证 `0 <= lc < N`，不再无依据偏置；
- OFT Adapter 首次实现不得为了填充 `boundary_segments`/`boundary_markers`/`node_markers` 旧字段而重新建设边界恢复算法。

**M2 验收标准**：
1. `python -m linkmesh --gfile <真实 DIII-D 样例> --no-smb --no-hdf5 --plot mesh_check.png` 能够运行；
2. 生成的 `mesh_check.png` 中三角网格覆盖 LCFS 内部及相应区域，无明显退化三角形，LCFS 显示曲线闭合；
3. 终端打印：`节点数: N，三角形数: T`；
4. `Mesh2D` 对象的核心字段（`nodes`、`triangles`、`region_ids`）均已正确填充，shape/dtype 符合第 2.2 节契约；
5. 网格质量验收（`0 <= lc < N` 合法索引、无退化单元、最小内角满足约束）；
6. `Mesh2D.region_ids` 集合与 OFT `domain.region_info` 区域模型一致，不含非正值；
7. `tests/test_oft_adapter.py`（新建）中的 M2 正式验收测试全部通过；
8. 只有上述全部通过并由 User 确认后，M2 才能改为 `PASSED` 并进入 M3。

**涉及模块**：`src/linkmesh/mesher/oft_adapter.py`（新建），`src/linkmesh/cli.py`（最小修改接入 Adapter），`src/linkmesh/utils/plotter.py`（`plot_mesh` 最小修改，闭合 LCFS 显示曲线），`tests/test_oft_adapter.py`（新建）

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步，第一战役闭环）

**当前状态**：【占位，待 M2 完整验收通过后开始；M3 真实验收必须基于通过 M2 的 OFT 网格结果】

**目标**：将 OFT 生成的三角网格（经 `oft_adapter.py` 最小适配后的 `Mesh2D`）写出为 TRIMEG 可消费的 HDF5 文件，并通过 `loadfemmesh_h5.m` 读取验证，确认网格几何物理质量完全合格。

**M3 边界**：
- Writer 不推断区域物理含义；
- Writer 不重编号、偏置、压缩或排序 `region_ids`；
- 节点连接表按契约从 0-based 转为 1-based（OFT 返回 0-based，M2-0 已确认）；
- `region_id` 原样写出，不执行 `+1`；
- 本轮不得宣称 M3 已开始或通过。

**验收标准**：
1. `python -m linkmesh --gfile <真实 DIII-D 样例> --output mesh.h5 --no-smb` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开；
3. `h5py` 读取验证：`/femmesh/vert` shape=`(2,N)`，`/femmesh/tria` shape=`(4,T)`，`/femmesh/nvert`=N，`/femmesh/ntria`=T；
4. 使用 `loadfemmesh_h5.m` 在 MATLAB 中读取 `mesh.h5`，`femmesh.vert` shape=`(N,2)`，`femmesh.tria` shape=`(T,4)`，无报错；
5. 节点索引合法性验证：`femmesh.tria(:,1:3)` 中所有节点索引均为整数，且满足 `1 <= index <= N`；
6. `/femmesh/tria` 第四列的含义通过真实 TRIMEG 样例核对确认（M3 验收时必须完成此核对）；
7. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`；
8. `tests/test_hdf5_writer.py` 中的 M3 自动测试全部通过（测试文件计划新增）。

**涉及模块**：`src/linkmesh/writers/hdf5_writer.py`（已完整实现），`tests/test_hdf5_writer.py`（计划新增）

---

### 里程碑 M4：`.smb` 输出验收（P0 第四步，第二战役攻坚）

**当前状态**：【占位，禁止开始；待 M3 验收通过后开始侦察】

**目标**：在 M3 完全验收通过、网格质量确认合格后，完成 SCOREC/PUMI/M3DC1 只读侦察，由主管确认实现路线，将同一 `Mesh2D` 对象写出为 M3DC1 可消费的 `.smb` 静态网格文件。

**M4 侦察范围**：M4 必须在 M3 完整通过后，对 MCD7 样例、官方文档、ModelFile、MeshFile 和 M3DC1/SCOREC/PUMI 源码进行只读侦察，确认区域数量、D1B、几何分类、索引、文件配对和 `.smb` 契约。P0 默认三区域方案不得被外推为 M3DC1 永久固定三区域；M3DC1 实际区域数量和 ModelFile 格式待侦察确认。

**M4 适配原则**：若 M3DC1 有额外区域、边界实体、几何分类或连续性要求（如 C1 连续性、高阶单元等），只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。

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
| `tests/test_oft_adapter.py` | M2（正式） | 【计划新增】 | 验证 `oft_adapter.py` 将 OFT `pts/lc/reg` 规范化为 `Mesh2D`；`nodes` shape=`(N,2)` float64；`triangles` shape=`(T,3)` 整数、`0 <= lc < N`；`region_ids` shape=`(T,)` 整数、原样保存无重编号、无非正值；退化三角形检查；区域编号集合与 OFT `domain.region_info` 一致 |
| `tests/test_triangle_wrapper.py` | M2（历史/过渡） | 历史证据保留（自动测试 36/36 通过；不能作为 OFT Adapter 正式验收替代） | 历史过渡测试，验证 Python triangle 包路线；当前保持文件不动，暂不删除、不扩展 |
| `tests/test_hdf5_writer.py` | M3 | 【计划新增】 | 验证 `write_hdf5()` 写出的 HDF5 文件包含全部必须数据集；`/femmesh/vert` shape=`(2,N)`；`/femmesh/tria` shape=`(4,T)`；节点索引满足 `1 <= index <= N`；`region_id` 列无偏置；`nvert`/`ntria` 标量值正确 |

**关于 `tests/test_oft_adapter.py` 路径**：建议路径为 `tests/test_oft_adapter.py`，与现有测试目录 `tests/` 布局一致，无冲突。若下一轮实现时发现与 `Mesh2D` 定义位置或其他目录规则产生冲突，应在下一轮蓝图更新中明确最终位置，不得整体停机。

**关于 `Mesh2D` 定义位置**：当前 `Mesh2D` 定义于 `src/linkmesh/mesher/triangle_wrapper.py`。下一轮 M2 任务若需最小调整 `Mesh2D` 的定义位置或构造方式，允许在不建设通用网格框架的前提下进行；若调整定义位置，需在下一轮蓝图更新中明确最终位置。本轮不裁决 `Mesh2D` 是否迁移出 `triangle_wrapper.py`。

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
- M2/M3 单元测试可使用最小合成 `Mesh2D` 或合成 OFT 返回值（`pts/lc/reg`）进行，不依赖真实 GFile。

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

## 16. 下一轮源码任务允许范围（M2 Adapter 实现，本轮不实施）

本轮 v1.8 仅更新蓝图，不实施任何源码。以下为下一轮允许的源码实施范围（授权来源：M2-0 已通过）：

1. **新建 `src/linkmesh/mesher/oft_adapter.py`**（M2 正式网格生成适配层，职责见第 7.1 节）；
2. **最小修改 `src/linkmesh/cli.py`**，使正式 M2 路径调用 OFT Adapter（见第 8.2 节）；
3. **必要时最小调整 `Mesh2D` 的定义位置或构造方式**，但不得建设通用网格框架（见第 14.1 节）；
4. **最小修改 `src/linkmesh/utils/plotter.py`**，使其基于 `nodes/triangles/region_ids` 绘图并闭合显示 LCFS（见第 11.2 节）；
5. **新增 OFT Adapter 专用测试文件**，建议路径 `tests/test_oft_adapter.py`（见第 14.1 节）；
6. **不在后续 M2 任务中修改 HDF5 Writer、SMB Writer 或 M3/M4 测试**；
7. **旧 `triangle_wrapper.py` 和 `tests/test_triangle_wrapper.py` 暂不删除、不扩展**。

若新增测试路径或 `Mesh2D` 定义位置与当前蓝图目录规则冲突，应在后续蓝图更新中明确最终位置；若无法确认，跳过该具体位置并在报告中列为待 User 裁决，不得整体停机。

---

## 17. 蓝图更新纪律

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
12. **修改 P0 区域方案或全局区域传递契约**；
13. **修改区域种子几何条件或失败原则**；
14. **将任何【待运行验证】事项更新为【已确认事实】**（必须有直接运行证据和 User 确认）；
15. **修改 OFT 网格生成路线（如从历史/过渡代码切换到 OFT gs_Domain 路线，或决定废弃历史/过渡代码）**；
16. **修改 `mesher/oft_adapter.py` 的职责边界或最小适配契约**；
17. **迁移 `Mesh2D` 定义位置或修改其核心三数组契约**。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
