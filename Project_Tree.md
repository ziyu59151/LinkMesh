# LinkMesh 项目目录树

- 文档主受众：Human-facing
- 知识库用途：人类导读
- 文档状态：当前有效
- 最高依据：LinkMesh_Architecture_Plan.md
- 事实边界：本文档是面向人类主管和研究员的轻量导读，不承载任何正式技术蓝图或接口定义。目录结构与职责描述以 `LinkMesh_Architecture_Plan.md` 为最终裁决依据，本文档仅作快速定向参考。
- 主要用途：帮助人类主管和初学者研究员快速理解 LinkMesh 仓库的目录布局、各模块的直观职责，以及应该去哪里找什么。

> 如果你是 Aider 或 AI 代理，请优先阅读 `CONTEXT.md` 和 `LinkMesh_Architecture_Plan.md`，本文档不是你的执行依据。

---

## 1. 这个项目是什么？

LinkMesh 是一个**轻量级独立命令行工具**，它的角色是一个**翻译官**。

网格生成底座**有且仅有** TokaMaker（底层为开源 Triangle 库）。LinkMesh 不包含多余的生成引擎，它的全部核心职责就是：

1. 从托卡马克平衡文件（GFile/EQDSK）中读取等离子体边界——通过调用 OFT `GEQDSKEquilibrium` API，**不手动解析 GFile 文本**；
2. 调用 TokaMaker/Triangle 生成二维非结构化三角网格；
3. 将算好的网格数据，准确翻译为两大目标物理求解器能直接读取的文件格式。

整个工具链路如下：

```text
GFile/EQDSK 平衡文件
        ↓  调用 OFT GEQDSKEquilibrium API 读取边界（薄 Adapter，不手动解析文本）
readers/gfile_reader.py
        ↓  生成二维三角网格（唯一底座，TokaMaker alpha/beta 字典风格）
mesher/triangle_wrapper.py  (TokaMaker / Triangle)
        ↓  统一内存网格对象 Mesh2D
        │
        ├──→ [第一战役] writers/hdf5_writer.py  ← 已完整实现
        │     → TRIMEG 求解器消费的 HDF5 静态网格
        │
        └──→ [第二战役] writers/smb_writer.py   ← 占位，待 M4 实现
              → M3DC1 求解器消费的 .smb 二进制静态网格
```

---

## 2. 两阶段战略：先易后难

LinkMesh 的开发顺序严格遵循"先易后难"原则，分两个阶段攻克两大输出格式：

### 第一战役：TRIMEG HDF5 模块（快速打通）

HDF5 是通用开放格式，TRIMEG 侧已有现成的 MATLAB 读取脚本（`loadfemmesh_h5.m`）和真实样例文件作为对照标尺，格式完全透明。

**目标**：把 TokaMaker 生成的网格数组，按照 `loadfemmesh_h5.m` 脚本期望的数据集路径和形状，格式化写入 HDF5 文件，快速实现打通与验证。

**验证方式**：用 MATLAB 运行 `loadfemmesh_h5.m` 读取生成的 `mesh.h5`，确认网格几何物理质量完全合格。

**当前状态**：`writers/hdf5_writer.py` 中的 `write_hdf5()` 函数已**完整实现**，等待 M2（网格生成）完成后进行端到端验收。

### 第二战役：M3DC1 .smb 模块（逆向攻坚）

`.smb` 是开源 `SCOREC/PUMI` 库的二进制网格格式。我们通过只读分析项目中已引入的 `m3dc1_scorec` 和 `scorec/pumi` 开源 C++ 源码，逆向推导出其二进制字节流协议，再用 Python `struct` 模块打包生成对齐的二进制文件。

**目标**：生成能被 M3DC1 的 `pumi_mesh_load` 顺畅读取的 `.smb` 静态网格文件。

**开发顺序铁律**：必须在第一战役完全验收通过、网格质量确认合格后，才能开始第二战役。

---

## 3. 顶层目录结构

```text
LinkMesh/
├── CONTEXT.md                       # [最高行为宪法] 敏捷开发工作流与纪律规范
├── LinkMesh_Architecture_Plan.md    # [最高技术蓝图] AI 单事实真理源与实操图纸
├── Project_Tree.md                  # [当前文件] 项目全局目录树与人类导读
├── History.md                       # [记忆沉淀] MVP 战术战果单向追加归档
├── requirements.txt                 # Python 依赖清单（pip install -r 安装）
├── .venv/                           # Python 虚拟环境（不提交到 Git）
│
├── readers/                         # 平衡数据读取（OFT Adapter，不手动解析 GFile 文本）
│   ├── __init__.py
│   └── gfile_reader.py              # 薄 Adapter：调用 OFT GEQDSKEquilibrium 读取 GFile
│
├── mesher/                          # 2D 网格底座封装（唯一底座：TokaMaker / Triangle）
│   ├── __init__.py
│   └── triangle_wrapper.py          # alpha/beta 字典风格，对齐 TokaMaker meshing.py
│
├── writers/                         # 静态网格翻译导出（两阶段战役核心）
│   ├── __init__.py
│   ├── hdf5_writer.py               # 第一战役：TRIMEG HDF5 格式映射【已完整实现】
│   └── smb_writer.py                # 第二战役：M3DC1 PUMI .smb 二进制逆向【占位】
│
├── utils/                           # 辅助自检工具（基于 matplotlib 的网格画图）
│   ├── __init__.py
│   └── plotter.py                   # plot_lcfs_only()（M1）+ plot_mesh()（M2）
│
├── cli.py                           # 命令行参数解析与转换执行流水线入口
│
├── tests/                           # 单元测试
│   ├── test_gfile_reader.py
│   ├── test_triangle_wrapper.py
│   ├── test_hdf5_writer.py
│   └── test_smb_writer.py
│
├── examples/                        # 示例文件与运行脚本
│   ├── sample.geqdsk
│   └── run_example.sh
│
├── docs/                            # [技术情报区] 调研报告与 RAG 规范文档
│   ├── linkmesh/                    # 本地前哨开发清单与 RAG 规范
│   ├── m3dc1/                       # M3DC1 调研报告与 .smb 接口参考事实
│   ├── trimeg/                      # TRIMEG HDF5 读取脚本与样例（loadfemmesh_h5.m）
│   └── tokamaker/                   # TokaMaker 封装架构与三角剖分参考（oft_reference_map.txt）
│
├── M3DC1/                           # [绝对只读参考区] M3DC1 官方/Scorec 接口源码
└── TOKAMAKER/                       # [绝对只读参考区] TokaMaker 及其核心源码
```

---

## 4. 各模块直观职责说明

### 控制文档（根目录）

| 文件 | 一句话说明 |
|---|---|
| `CONTEXT.md` | 项目最高行为宪法。规定了 Aider 的角色、开发纪律、禁止事项和协作规范。 |
| `LinkMesh_Architecture_Plan.md` | 项目最高技术蓝图。所有模块接口、数据结构、输出格式和验收标准都在这里定义。 |
| `History.md` | 战术战果归档。每攻克一个里程碑，就在这里追加一条记录。 |
| `requirements.txt` | Python 依赖清单。运行 `pip install -r requirements.txt` 安装所有依赖。 |

### `readers/`：GFile 读取 Adapter（薄封装 OFT API，不手动解析文本）

- **`gfile_reader.py`**：这是一个**薄 Adapter（接线员）**，而不是手动文本解析器。它直接调用 TokaMaker/OFT 提供的 `GEQDSKEquilibrium` 类来读取 GFile，然后从 OFT 返回对象的属性中提取 LinkMesh 所需的字段（`eq.boundary_R`/`eq.boundary_Z` 提取 LCFS 坐标、`eq.R_mag`/`eq.Z_mag` 提取磁轴位置、`eq.limiter_R`/`eq.limiter_Z` 提取第一壁坐标等），封装为精简的 `GFileData` 数据对象（9 个字段）。**绝对禁止**在这里手动执行任何 GFile 文本解析。

### `mesher/`：TokaMaker/Triangle 唯一网格生成底座

- **`triangle_wrapper.py`**：封装 `triangle` Python 包，调用风格严格对齐 TokaMaker/OFT 的 `meshing.py`。输入以 `alpha = dict(vertices=..., segments=..., regions=...)` 字典形式组织（TokaMaker 风格），输出从 `beta` 字典中提取（键名：`vertices`、`triangles`、`triangle_attributes`），最终封装为 `Mesh2D` 数据对象。这是 LinkMesh 唯一的网格生成引擎，不存在第二种。

### `writers/`：两阶段战役核心——翻译导出

这是 LinkMesh 最核心的攻坚方向，负责把统一的 `Mesh2D` 对象翻译为两种目标格式：

- **`hdf5_writer.py`**（第一战役）：对照 `loadfemmesh_h5.m` 脚本，将 `Mesh2D` 字段格式化写入 HDF5 文件，供 TRIMEG 求解器消费。**`write_hdf5()` 函数已完整实现**，包含转置写入（`vert`/`tria`）、1-based 索引偏置（节点索引 +1）等全部关键转换。
- **`smb_writer.py`**（第二战役）：通过逆向分析 SCOREC/PUMI 开源 C++ 源码，用 Python `struct` 打包写出 M3DC1 可消费的 `.smb` 二进制文件。当前为**占位实现**（`raise NotImplementedError`），必须在第一战役验收通过后才能开始。

### `utils/`：辅助自检工具

- **`plotter.py`**：已实现两个函数：
  - `plot_lcfs_only(gfile_data, filepath)`：M1 最小可用版，仅绘制 LCFS 边界与磁轴；
  - `plot_mesh(gfile_data, mesh, filepath, ...)`：M2 完整版，绘制 LCFS + 三角网格叠加图，支持区域着色和边界标记着色。

### `cli.py`：命令行入口

整个工具的入口。解析用户输入的命令行参数，按顺序调用 reader → mesher → writer，完成从平衡文件到网格文件的完整转换。

**当前实现状态**：
- 参数解析框架已完整实现（`build_parser()`）；
- `_run()` 主执行逻辑已按里程碑顺序组织（Step 1~7）；
- M1 路径（`--no-hdf5 --no-smb --plot`）可触发 `plot_lcfs_only()`；
- **`_build_boundary_config()` 已完整实现**（git: 994c415）：从 `GFileData.lcfs_r/lcfs_z` 等弧长重采样，构造 LCFS 线段、外边界矩形、可选第一壁线段，设置 plasma/vacuum 区域标记点，封装为 `BoundaryConfig`。

典型用法：

```bash
# M1 验收：仅读取 GFile 并可视化 LCFS
linkmesh --gfile sample.geqdsk --no-hdf5 --no-smb --plot lcfs_check.png

# M2/M3 验收：生成网格并写出 HDF5
linkmesh --gfile sample.geqdsk --output mesh.h5 --no-smb --plot mesh_check.png

# M5 完整链路
linkmesh \
  --gfile sample.geqdsk \
  --output mesh.h5 \
  --smb mesh.smb \
  --min-angle 20 \
  --max-area 0.001 \
  --plot mesh_check.png \
  --verbose
```

### `docs/`：技术情报区

| 子目录 | 内容 |
|---|---|
| `docs/linkmesh/` | LinkMesh 本地开发清单、RAG 友好化文档规范等。 |
| `docs/trimeg/` | TRIMEG HDF5 读取脚本（`loadfemmesh_h5.m`）与真实样例文件——第一战役的黄金标尺。 |
| `docs/m3dc1/` | M3DC1 宏观架构白皮书、`.smb` 接口调研报告、源码侦察清单等。 |
| `docs/tokamaker/` | TokaMaker/OFT 网格生成链路白皮书、Triangle 集成规范、OFT API 参考映射表（`oft_reference_map.txt`）等。 |

### `M3DC1/` 和 `TOKAMAKER/`：只读参考区

**绝对只读，严禁修改任何文件。**

- **`M3DC1/`**：M3DC1 官方源码与 `m3dc1_scorec` 接口库。第二战役通过只读侦察这里的 C++ 代码来逆向推导 `.smb` 字节流格式。
- **`TOKAMAKER/`**：TokaMaker/OpenFUSION Toolkit 源码。`readers/gfile_reader.py` 通过调用这里的 OFT Python API（`GEQDSKEquilibrium`，位于 `TOKAMAKER/.../TokaMaker/eqdsk.py`）读取 GFile；`mesher/triangle_wrapper.py` 的封装风格参考这里的 `meshing.py` 实现（`alpha` 字典输入、`beta` 字典输出）。

---

## 5. MVP 开发里程碑（当前进度参考）

| 里程碑 | 目标 | 核心模块 | 当前状态 |
|---|---|---|---|
| M1 | 通过 OFT Adapter 从 GFile 提取 LCFS 边界并可视化 | `readers/gfile_reader.py`（OFT Adapter），`utils/plotter.py`（`plot_lcfs_only`） | 代码已实现，待真实 GFile 验收 |
| M2 | 调用 TokaMaker/Triangle 生成二维三角网格并可视化 | `mesher/triangle_wrapper.py`，`utils/plotter.py`（`plot_mesh`），`cli.py`（`_build_boundary_config`） | **全部代码已实现**（git: 994c415），待端到端验收 |
| M3 | 写出 TRIMEG HDF5 文件并用 `loadfemmesh_h5.m` 验证 | `writers/hdf5_writer.py` | **`write_hdf5()` 已完整实现**，待端到端验收 |
| M4 | 逆向写出 M3DC1 可消费的 `.smb` 文件 | `writers/smb_writer.py` | 占位实现，待 M3 验收后开始 |
| M5 | 一条命令完成完整端到端转换链路 | `cli.py` + 全部模块 | 待 M4 完成后验收 |

详细验收标准请查阅 `LinkMesh_Architecture_Plan.md` 第 12 节。

---

## 6. 阅读建议

如果你是**人类主管或研究员**，建议按以下顺序阅读：

```text
Project_Tree.md（当前文件，快速定向）
        ↓
CONTEXT.md（了解项目纪律与协作规范）
        ↓
LinkMesh_Architecture_Plan.md（深入理解技术蓝图与接口定义）
```

如果你是 **Aider 或 AI 代理**，请直接跳转：

```text
CONTEXT.md → LinkMesh_Architecture_Plan.md
```

本文档（`Project_Tree.md`）不是 Aider 的执行依据，仅供人类快速定向使用。
