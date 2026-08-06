# LinkMesh 项目目录树与使用导读

- 文档主受众：Human-facing
- 知识库用途：人类导读
- 文档状态：当前有效（对应技术蓝图 v4.4；初版 Linux 可移动 Release 构建系统为 IMPLEMENTED / STATICALLY CHECKED，Linux 生成、结构检查与外部验证仍为 NOT RUN / PENDING）
- 最高依据：根目录 `LinkMesh_Architecture_Plan.md`
- 事实边界：本文档是面向组内研究人员的轻量仓库地图，不定义正式接口、字段契约或验收标准。遇到目录职责、数据结构、文件格式、模块接口或阶段状态争议时，以 `LinkMesh_Architecture_Plan.md` 为最终裁决依据；详细运行证据与测试记录见 `History.md`。
- 主要用途：帮助首次接触 LinkMesh 的研究人员快速理解项目用途、当前能力、源码布局、最短运行方式、原生 helper 的位置以及后续查证入口。

> AI 代理执行开发任务时，应先阅读 `CONTEXT.md` 和 `LinkMesh_Architecture_Plan.md`。本文件不是第二份技术蓝图，也不能替代正式技术契约。

---

## 1. LinkMesh 是什么

LinkMesh 是一个轻量级命令行网格转换工具。

它从 GFile/EQDSK 或 counted R-Z 二维边界文件取得计算域边界，通过
OFT/TokaMaker 调用 Triangle 生成二维非结构化三角网格，再把统一的 `Mesh2D`
翻译为目标求解器所需的静态网格文件。

当前主数据流是：

```text
GFile/EQDSK 或 counted R-Z boundary
  → Reader
  → OFT/Triangle
  → Mesh2D
      ├── TRIMEG HDF5
      ├── M3D-C1 analytic model TXT + PUMI native SMB
      └── PNG 几何自检
```

OFT/Triangle 是 LinkMesh 唯一的二维三角剖分底座。PUMI 不重新生成三角网格，只负责建立目标几何分类、构造 APF/MDS 网格并调用官方接口写出 native SMB。

LinkMesh 当前不建设 M3D-C1 消费端、SMB loader、SMB validator、多区域 M3D-C1 模型、三维网格或并行分区工具。

---

## 2. 当前状态速览

| 项目 | 当前状态 |
|---|---|
| GFile Reader | 已实现并通过既有验收 |
| OFT/Triangle 二维网格生成 | 已实现；默认嵌套区域路径和单区域 LCFS 路径均有真实运行证据 |
| `Mesh2D` 统一网格对象 | 已实现 |
| TRIMEG HDF5 Writer | 已实现并通过既有 Python、h5py 和 MATLAB 消费验收 |
| M3D-C1 analytic model TXT Writer | PASSED |
| PUMI native SMB Writer 与 C++ helper | 生成侧 PASSED |
| 第一条真实 M3D-C1 CLI | PASSED |
| PNG 人工检查 | PASSED |
| M3D-C1 TXT+SMB 加载 | PASSED |
| M3D-C1 初始化 | PASSED |
| M3D-C1 时间推进主循环 | PENDING |
| M3D-C1 中等或长时运行稳定性 | PENDING |
| M3D-C1 物理结果正确性 | PENDING |
| counted R-Z Boundary Reader | 已实现 |
| `single_region + array_file` | 已实现；EAST 生成侧 PASSED |
| `array_file + 可选 GFile LCFS PNG 参考` | DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED |
| `--plot-lcfs` 与 `[output].plot_lcfs` | 已批准设计，尚未实现 |
| Release 构建脚本、launcher、bootstrap 与分层检查器 | IMPLEMENTED / STATICALLY CHECKED |
| Linux 可移动 Release 目录与 tar.gz | GENERATED: NOT RUN；STRUCTURALLY CHECKED: PENDING；EXTERNAL SERVER VALIDATION: PENDING |
| EAST M3D-C1 后续运行 | 已交付，加载、初始化、时间推进结果 PENDING |
| 最新 TRIMEG HDF5 | 已生成并交付卢老师测试，反馈 PENDING |
| `single_region + first_wall` | 未实现 |
| `single_region + flux_surface` | 未实现 |
| OFT 单区域空间变网格密度 | 待调查，未实现 |
| OFT 多区域拓扑 | 待调查 |
| M3D-C1 多区域、多 geometric face 与 C1 兼容性 | 待调查，未开放 |
| 动态自适应、磁面对齐、三维和并行分区 | 当前未开放 |
| 正式共享部署 | 方案已讨论，实施 PENDING |

当前最准确的结论是：

```text
LinkMesh 单区域生成侧最小闭环：PASSED
TXT、rank-0 SMB、PNG：已生成
PNG 人工检查：PASSED
TXT+SMB 加载：PASSED
M3D-C1 初始化：PASSED
M3D-C1 时间推进、稳定性和物理正确性：PENDING

array_file + 可选 GFile LCFS PNG 参考：
DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED

普通用户 Release 构建源码：
IMPLEMENTED / STATICALLY CHECKED

Linux Release：
GENERATED: NOT RUN
STRUCTURALLY CHECKED: PENDING
EXTERNAL SERVER VALIDATION: PENDING
TRIMEG REAL RUN: PENDING
M3D-C1 REAL RUN: PENDING
```

既有 TXT+SMB 已完成 M3D-C1 加载和初始化；后续交付给组内同学的网格仍在继续运行。
最新 TRIMEG HDF5 已交付卢老师测试。交付不等于外部加载、初始化、时间推进、稳定性
或物理正确性已经通过，尚未返回的结果继续标记为 `PENDING`。

---

## 3. 当前仓库结构

以下目录树只展示理解项目所需的主要源码、文档和测试入口。大型外部参考源码不展开内部细节，缓存、临时运行目录、编辑器目录和构建垃圾不列入正式结构。

```text
LinkMesh/
├── CONTEXT.md
├── LinkMesh_Architecture_Plan.md
├── Project_Tree.md
├── History.md
├── examples/
│   └── m3dc1_single_region/
│       └── linkmesh.in.example
│
├── src/
│   └── linkmesh/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── mesh.py
│       ├── m3dc1_model.py
│       │
│       ├── readers/
│       │   ├── __init__.py
│       │   ├── boundary_reader.py
│       │   └── gfile_reader.py
│       │
│       ├── mesher/
│       │   ├── __init__.py
│       │   └── oft_adapter.py
│       │
│       ├── writers/
│       │   ├── __init__.py
│       │   ├── hdf5_writer.py
│       │   ├── m3dc1_model_writer.py
│       │   └── smb_writer.py
│       │
│       └── utils/
│           ├── __init__.py
│           └── plotter.py
│
├── native/
│   └── linkmesh_scorec_helper/
│       ├── CMakeLists.txt
│       └── main.cc
│
├── packaging/
│   └── release/
│       ├── build_release.sh
│       ├── linkmesh-launcher
│       ├── linkmesh-bootstrap.py
│       ├── linkmesh-check
│       └── README.md
│
├── tests/
│   ├── test_configuration_contract.py
│   ├── test_geometry_and_readers.py
│   ├── test_oft_adapter_contract.py
│   ├── test_format_contracts.py
│   ├── test_cli_contract.py
│   └── test_plotter_contract.py
│
├── docs/
│   ├── linkmesh/
│   │   ├── work_plan.md
│   │   ├── plan.md
│   │   ├── LinkMesh_Architecture_Plan_v3.7.md
│   │   └── LinkMesh_Architecture_Plan_v1.13.md
│   └── trimeg/
│       ├── loadfemmesh_h5.m
│       └── TRIMEG HDF5 参考样例
│
├── M3DC1/
│   └── m3dc1_scorec/ 与 unstructured/ 等外部参考源码
│
└── TOKAMAKER/
    └── OpenFUSIONToolkit/ 外部参考源码
```

需要注意：

- `examples/m3dc1_single_region/linkmesh.in.example` 是供用户复制到 Case 并改名为 `linkmesh.in` 的标准配置示例；它不定义新的技术契约，正式配置规则仍以根目录技术蓝图为准。
- LinkMesh 自有 Python 业务源码位于 `src/linkmesh/`。
- LinkMesh SCOREC helper 的当前正式源码位于 `native/linkmesh_scorec_helper/`。
- helper 的当前构建目标和可执行文件名为 `linkmesh-scorec-helper`，显式定位变量为
  `LINKMESH_SCOREC_HELPER`。
- `M3DC1/` 和 `TOKAMAKER/` 是外部参考源码区域，不是 LinkMesh 自有业务模块。
- `docs/trimeg/` 中的 MATLAB 读取脚本和真实样例是 TRIMEG 文件契约的只读证据。
- `docs/linkmesh/work_plan.md` 承载下一阶段 OFT 高级网格能力侦察的执行拆解，但不是第二份技术蓝图。
- `docs/linkmesh/LinkMesh_Architecture_Plan_v3.7.md` 是进入 v4.0 前的完整 3.x 历史快照。
- `docs/linkmesh/LinkMesh_Architecture_Plan_v1.13.md` 是更早的历史版本参考。
- 根目录当前 `LinkMesh_Architecture_Plan.md` 是唯一有效技术蓝图；历史快照和专题报告不得覆盖其正式裁决。
- `packaging/release/` 由 Windows 本地 Git 仓库维护；其中 `build_release.sh` 只在
  Linux 服务器对上传源码归档执行。
- Release 目录和同名 tar.gz 是 Linux 服务器生成物，不提交 Git。
- Linux 服务器不承担 LinkMesh 源码 Git 管理；真实构建和验证结果返回本地后再按
  直接证据归档。
- `build/` 是 native helper 的构建产物目录，不是正式源码目录，也不应作为 Git 源码提交。
- 当前仓库树只列出已经存在且属于当前导读范围的文件；不存在或尚未确认存在的文件，不应被当成当前仓库组成。
- 编译 native helper 时产生的 `build/` 目录属于构建产物，不是正式源码目录，也不应作为 Git 源码提交。

---

## 4. 顶层文档导航

| 文档 | 应该什么时候读 |
|---|---|
| `Project_Tree.md` | 第一次接触项目时阅读，用于快速了解仓库、数据流和使用入口。 |
| `CONTEXT.md` | 开始开发或让 AI 修改项目之前阅读，了解行为规范、只读边界和开发纪律。 |
| `LinkMesh_Architecture_Plan.md` | 查询正式模块职责、数据结构、文件格式、接口、阶段状态和验收边界时阅读。它是唯一技术蓝图。 |
| `History.md` | 查询某项功能何时完成、运行过哪些命令、测试结果、真实样例和阶段证据时阅读。 |
| `docs/linkmesh/work_plan.md` | 查询下一阶段 OFT 空间变密度、多区域拓扑和 M3D-C1 C1 兼容性调查的执行拆解时阅读。 |
| `docs/linkmesh/plan.md` | 查询组内 Case 管理和日常使用建议时阅读。 |
| `docs/linkmesh/LinkMesh_Architecture_Plan_v3.7.md` | 查询进入 v4.0 前的完整 3.x 技术蓝图时阅读；它是只读历史快照。 |

如果文档之间出现不一致，应按以下顺序处理：

```text
User 当前明确决定
  → 根目录当前 LinkMesh_Architecture_Plan.md
  → History.md 中的运行与验收记录
  → 实时源码和仓库结构
  → 其他导读或历史文档
```

`Project_Tree.md` 只负责导航，不得用它修改或推翻正式技术契约。

---

## 5. 核心数据流

已批准但尚未实现的 LCFS 参考绘图工作流包含两条独立支路：

```text
实际网格支路：
array file → Boundary Reader → OFT/Triangle → Mesh2D ─┐
                                                      ├→ Plotter → PNG
参考几何支路：                                        │
GFile → GFile Reader → GFileData/LCFS ────────────────┘
```

array file 是唯一实际计算域边界。GFile LCFS 只在 Plotter 中作为参考曲线，两条
Reader 不互相调用。参考 `GFileData` 不进入 Mesher、`Mesh2D`、TRIMEG Writer、
M3D-C1 Writer 或 native helper，因此不会改变网格或求解器输出。该能力当前仅为
**DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED**。

TRIMEG 路径：

```text
GFile/EQDSK 或 counted R-Z boundary
  → 对应 Reader
  → OFT/Triangle
  → Mesh2D
  → HDF5 Writer
  → TRIMEG HDF5
  → MATLAB/TRIMEG 消费
```

M3D-C1 路径：

```text
linkmesh.in / CLI
  → Config
  → GFile Reader
  → OFT/Triangle
  → Mesh2D
  → 共享 M3DC1ModelSpec
  → TXT Writer + SMB Writer/native helper
  → TXT + rank-0 SMB
  → M3D-C1 加载和初始化
```

TXT Writer 和 SMB Writer 使用同一个 `M3DC1ModelSpec`，以保持 geometric vertices、edges、loop、face 和分类标签一致。SMB 是由 PUMI 写出的 native 二进制文件。当前 TXT+SMB 已完成 M3D-C1 加载和初始化；时间推进仍待验证。

---

## 6. Python 模块导读

### `src/linkmesh/cli.py`

- **输入**：命令行参数。
- **职责**：调用配置合并，编排 Reader、Mesher、Writer 和 Plotter。
- **输出**：按目标生成 HDF5，或生成配套 TXT、SMB 和 PNG。
- **TRIMEG HDF5 路径参数**：正式参数为 `--hdf5 PATH`，`--h5 PATH` 是完全同义别名；
  二者最终形成同一个 `EffectiveConfig.hdf5_path`。旧 `--output` 已从当前接口删除。
- **不负责**：网格算法、边界重采样、几何分类、SMB 字节实现或 helper 生命周期。

`src/linkmesh/__main__.py` 只负责让以下命令进入同一个 CLI 主入口：

```bash
python -m linkmesh
```

### `src/linkmesh/config.py`

- **输入**：内建默认值、`linkmesh.in` 和显式 CLI 覆盖。
- **职责**：读取并严格校验配置，解析路径，检查当前允许的 target/profile/boundary 组合。
- **输出**：不可变的有效配置对象。
- **不负责**：读取 GFile、生成网格或写出任何目标文件。

配置优先级固定为：

```text
内建默认值 < linkmesh.in < 显式 CLI 参数
```

### `src/linkmesh/readers/gfile_reader.py`

- **输入**：GFile/EQDSK 文件路径。
- **职责**：作为独立薄 Adapter 调用 OFT `GEQDSKEquilibrium`，提取 LCFS、第一壁、
  磁轴和基本平衡信息。
- **输出**：`GFileData`。
- **不负责**：读取 array file、调用 Boundary Reader、决定实际网格边界、手写 GFile
  文本解析、网格生成、绘图或文件写出。
- **候选参考用途**：在已批准但尚未实现的 `array_file + plot_lcfs` 工作流中，只为
  Plotter 提供 LCFS reference。

### `src/linkmesh/readers/boundary_reader.py`

- **输入**：counted R-Z boundary text。
- **职责**：作为独立 Reader 严格读取计数头和 R-Z 米制坐标，验证并规范化单一闭合
  实际计算域边界。
- **输出**：独立的二维边界数组。
- **不负责**：读取 GFile、调用 GFile Reader、返回 `GFileData`、组合参考几何、
  调用 Plotter、调用 OFT/Triangle、判断边界物理来源或生成网格。

EAST `array_file` 生成侧已通过：104 个输入边界点生成 185 个节点、329 个三角形和
1 个区域，并成功生成 TXT、rank-0 SMB 和 PNG；M3D-C1 加载、初始化和时间推进仍待
分层验收。

### `src/linkmesh/mesher/oft_adapter.py`

- **输入**：按边界来源得到的实际计算边界、区域策略和网格尺度。
- **职责**：构造 OFT Domain，调用 OFT/TokaMaker/Triangle，并把结果规范化为 `Mesh2D`。
- **输出**：二维非结构化三角网格。
- **候选工作流边界**：`array_file` 路径只接收 array boundary，不接收参考
  `GFileData`，也不感知 `--plot-lcfs`。
- **不负责**：第二种剖分后端、参考 GFile 绘图、PUMI 网格生成、
  TRIMEG/M3D-C1 文件写出或配置文件解析。

当前正式 single-region 路径支持：

```text
profile=single_region
boundary_source=lcfs 或 array_file
```

`lcfs` 来源读取 GFile；`array_file` 来源读取 counted R-Z boundary，并且 v1 契约下
不同时读取 GFile。

### `src/linkmesh/mesh.py`

- **输入**：节点、三角形连接表、区域编号和可选有序外边界。
- **职责**：定义唯一正式统一网格对象 `Mesh2D`，供所有下游 Writer 和 Plotter 使用。
- **输出**：求解器无关的内存网格表示。
- **不负责**：调用 OFT、PUMI、h5py、CLI 或任何 Writer。

### `src/linkmesh/m3dc1_model.py`

- **输入**：单区域 `Mesh2D` 及其有序外边界。
- **职责**：构造 single-loop、single-face 的 `M3DC1ModelSpec`。
- **输出**：TXT Writer 和 SMB Writer 共同使用的 analytic geometric model。
- **不负责**：调用 PUMI、生成 SMB、读取固定外部 TXT 模板或处理多 face 模型。

### `src/linkmesh/writers/m3dc1_model_writer.py`

- **输入**：已经验证的 `M3DC1ModelSpec`。
- **职责**：写出 M3D-C1 analytic geometric model TXT。
- **输出**：与 SMB 配套使用的 TXT model 文件。
- **不负责**：生成网格、调用 PUMI、写 SMB 或自行分配另一套几何标签。

### `src/linkmesh/writers/smb_writer.py`

- **输入**：`Mesh2D`、同一个 `M3DC1ModelSpec`、SMB 基础路径。
- **职责**：验证输入、确定性建立网格实体分类、生成内部交换数据并调用独立 native helper。
- **输出**：由 helper 和 PUMI 写出的 rank-0 native SMB。
- **不负责**：在 Python 中实现 SMB 字节格式、加载或反向验证 SMB、运行 M3D-C1 求解器。

用户提供的 `mesh.smb` 是基础路径。锁定的 PUMI 目标版本在单进程 rank 0 下实际生成类似：

```text
mesh0.smb
```

rank 插入由 SMB Writer/helper 与 PUMI 管理，不由普通用户手工改写。

### `src/linkmesh/writers/hdf5_writer.py`

- **输入**：包含有效实际计算域外边界的 `Mesh2D`。
- **职责**：写出 TRIMEG 标准 HDF5 静态网格。
- **输出**：TRIMEG MATLAB 消费端可读取的 HDF5。
- **参考曲线边界**：当前授权的 Loader 与正式 11 数据集契约中没有独立 LCFS
  reference 输入位置；`Rbc/Zbc` 继续来自 `Mesh2D.outer_boundary`，候选工作流不
  新增 HDF5 dataset。
- **不负责**：读取参考 GFile、把 LCFS 写入 `Rbc/Zbc`、生成网格、推断区域物理
  含义或修改输入对象。

字段级 HDF5 数据集、shape、dtype 和索引规则请直接查阅当前技术蓝图，不在本导读重复。

### `src/linkmesh/utils/plotter.py`

- **输入**：作为实际网格和实际边界来源的 `Mesh2D`，以及可选参考 `GFileData`。
- **职责**：绘制三角网格、actual mesh boundary 和可选 LCFS reference，并在视觉和
  图例中明确区分；还可按既有路径叠加第一壁、磁轴和区域着色。
- **输出**：PNG 人工检查图。
- **不负责**：把 array boundary 标为 LCFS、把 LCFS 标为 mesh boundary、修改网格、
  判断 SMB/HDF5 是否可被求解器消费或替代数值验收。

---

## 7. 原生 helper：源码与编译产物

原生 helper 的正式源码目录是：

```text
native/linkmesh_scorec_helper/
├── CMakeLists.txt
└── main.cc
```

两者的关系是：

```text
main.cc + CMakeLists.txt
  → 在具有相容 SCOREC/PUMI 和 MPI 的环境中编译
  → linkmesh-scorec-helper 可执行文件
  → 运行时由 Python smb_writer.py 调用
  → PUMI writeNative()
  → rank-0 native SMB
```

需要明确区分：

1. `main.cc` 是 helper 的 C++ 源码。
2. `CMakeLists.txt` 是构建规则。
3. 编译后产生的 `linkmesh-scorec-helper` 是运行时可执行文件。
4. 源码和可执行文件不是两个不同的 helper，而是同一组件的源代码与构建结果。
5. helper 是 LinkMesh M3D-C1 输出链的正式组成部分，不是临时 probe。
6. helper 不重新剖分网格；它只根据 Python 提供的节点、连接关系、几何模型和分类信息构造 APF/MDS 网格，并调用 SCOREC/PUMI 官方接口写出 native SMB。
7. helper 连接 Python SMB Writer 与 SCOREC/PUMI；它不读取 GFile 或边界文件，不调用
   OFT/Triangle，也不重新生成三角网格。
8. 常见 `build/` 目录只是 CMake 生成的构建产物目录，不是正式源码，不应作为 Git 源码提交。
9. 普通用户不需要理解内部交换文件；该内容仅属于 Python Writer 与 helper 的内部实现契约。

当前仓库尚未完成让所有用户在任意目录无条件调用 helper 的统一安装。运行时仍需保证：

- LinkMesh Python 包能被当前 Python/Conda 环境找到；
- 正确版本的 OFT 可用；
- 编译后的 helper 可由 SMB Writer 按正式定位规则找到；
- helper 所依赖的 SCOREC/PUMI 与 MPI 环境相容。

当前接口已经统一为：

```text
源码目录：native/linkmesh_scorec_helper/
构建目标和可执行文件：linkmesh-scorec-helper
显式定位变量：LINKMESH_SCOREC_HELPER
定位顺序：helper_path → LINKMESH_SCOREC_HELPER → PATH
```

服务器构建目录属于仓库外产物，不是 Git 源码。helper 的目标 SCOREC/PUMI 版本、
MPI/ABI 约束、交换契约和生命周期规则请查阅当前技术蓝图。

---

## 8. 测试与证据导读

`tests/` 是小型内部契约回归集，按稳定契约组织：

| 测试文件 | 主要关注内容 |
|---|---|
| `tests/test_configuration_contract.py` | 配置默认值、合并优先级、路径基准、required-fields 和兼容矩阵。 |
| `tests/test_geometry_and_readers.py` | `Mesh2D.outer_boundary`、counted R-Z Reader 和最小 GFile Adapter 契约。 |
| `tests/test_oft_adapter_contract.py` | OFT 三数组转换、最终区域 ID、outer Region 时序、版本锁定和最小策略。 |
| `tests/test_format_contracts.py` | TRIMEG 11 dataset、M3D-C1 TXT、exchange schema 及 helper 子进程边界。 |
| `tests/test_cli_contract.py` | mesh-only、TRIMEG、M3D-C1、array reference 和配置提前失败的最小编排。 |
| `tests/test_plotter_contract.py` | 非空 PNG、reference 选择语义和输入不可变性。 |

测试优先直接检查返回值、真实临时文本、HDF5、TXT、交换文件和 PNG。mock 只用于
OFT、CLI 外部副作用和 native helper 等不可避免边界，不复制第三方内部算法，也不
把 mock 结果提升为外部消费证据。自动测试不能替代真实 OFT、TRIMEG、
M3D-C1/SCOREC/PUMI 加载、初始化、时间推进或物理验收。

当前记录需要保留以下边界：

- 真实 DIII-D GFile 的单区域 M3D-C1 CLI 最小闭环已经成功。
- TXT、rank-0 SMB 和 PNG 已实际生成。
- PNG 已由 User 人工检查通过。
- 配套 TXT+SMB 已完成 M3D-C1 外部加载和初始化。
- M3D-C1 时间推进主循环、中等或长时运行稳定性以及物理结果正确性仍为 `PENDING`。
- 历史上对未开放组合异常类型的过时预期，以及要求 TRIMEG target 调用 SMB Writer
  的过时预期，均不属于当前正式测试契约；当前以蓝图兼容矩阵和 target 分派为准。
- 未实际执行的测试命令不能记录为通过或失败。
- 精确测试计数、运行环境和阶段证据统一查阅 `History.md`。

---

## 9. 外部参考源码与只读区域

### `TOKAMAKER/`

该目录保存 OpenFUSIONToolkit/TokaMaker 参考源码。

LinkMesh 通过正式安装的 OFT 包运行，而不是把仓库中的 OFT 源码快照当作 LinkMesh 自有模块。Reader 和 Mesher 的关键参考包括：

- GFile/EQDSK 读取接口；
- `gs_Domain` 区域构造；
- Triangle 输入组织；
- OFT 网格结果与区域信息。

该目录是外部只读参考区，禁止由 LinkMesh 开发任务修改。

### `M3DC1/`

该目录保存 M3D-C1、`m3dc1_scorec` 和相关外部源码，用于理解 M3D-C1 如何加载模型、网格和场数据。

LinkMesh 不修改 M3D-C1/SCOREC/PUMI 消费端，也不把这些源码当作 LinkMesh 自有业务模块。该目录同样属于外部只读参考区。

### LinkMesh 自有源码

LinkMesh 自有 Python 业务源码位于：

```text
src/linkmesh/
```

LinkMesh 自有 native helper 源码位于：

```text
native/linkmesh_scorec_helper/
```

开发时必须清楚区分“LinkMesh 自有源码”和“外部参考源码”。

---

## 10. 新成员建议阅读顺序

建议按以下顺序了解项目，通常不需要一开始阅读全部实现细节：

1. 阅读 `Project_Tree.md`，理解项目用途、当前状态和目录布局。
2. 阅读 `LinkMesh_Architecture_Plan.md` 的项目定位、当前阶段状态和 M5 单区域 CLI 部分。
3. 阅读 `src/linkmesh/cli.py` 与 `src/linkmesh/config.py`，理解用户输入如何进入业务流程。
4. 阅读 `src/linkmesh/mesh.py`，理解统一的 `Mesh2D`。
5. 阅读 `src/linkmesh/readers/gfile_reader.py` 与 `src/linkmesh/mesher/oft_adapter.py`，理解 GFile 到二维网格的路径。
6. 阅读 `src/linkmesh/m3dc1_model.py`、`src/linkmesh/writers/m3dc1_model_writer.py` 和 `src/linkmesh/writers/smb_writer.py`，理解 TXT 与 SMB 如何共享模型语义。
7. 阅读 `native/linkmesh_scorec_helper/main.cc` 和对应 `CMakeLists.txt`，理解 Python 与 SCOREC/PUMI 的边界。
8. 最后按需要查阅 `History.md`、测试文件、TRIMEG 参考资料以及外部只读源码。

如果只想运行 LinkMesh，不需要先阅读 helper 的内部交换契约或 PUMI 生命周期细节。

---

## 11. 开发、验证与发布环境导读

正式源码在本地 Windows Git Bash 仓库维护；本地负责源码、文档、Git 审查、Release
构建脚本和发布版本，不运行测试、OFT/Triangle、native 构建或消费端验证。服务器只
接收本地 `git archive` 产生的源码归档，不采用服务器 Git 工作流。Linux 服务器负责
展开归档、执行 `packaging/release/build_release.sh`、创建环境、编译或选择已验证
helper、运行测试、生成 Release 目录与 tar.gz，并执行 M3D-C1/TRIMEG 验收。

初版 Release 是可移动目录，不是单文件程序。它携带 LinkMesh、OFT 26.6、helper、
启动器和 manifest，但不携带 Python、通用 Python 包、MPI、glibc、libstdc++ 或
PUMI 库。普通用户通过 `bin/linkmesh` 启动，不设置 `PYTHONPATH` 或 helper 环境
变量；通用 Python 包由选定的目标 Python 环境提供。

服务器环境分为：

| 环境 | 用途 |
|---|---|
| 个人开发验证环境 | 允许 `PYTHONPATH`、测试依赖、开发 helper 和临时环境变量，不向组员承诺稳定 |
| 个人发布候选环境 | 从零创建，正式安装 LinkMesh 与 helper，不依赖 `PYTHONPATH` 或开发构建目录 |
| 组内共享 release | 位于导师批准的共享根目录，按版本发布，普通用户只读执行，不依赖个人主目录 |

共享根目录尚待导师或服务器管理者确认，不得把 `/share` 等候选路径写成当前事实。
目标共享结构是版本化 `releases/<version>/env`、可切换的 `current`、统一包装入口和
可选 modulefile；详细契约及验收矩阵见正式技术蓝图。

普通用户目标体验是通过统一入口运行 LinkMesh，不自行安装 Conda、不编译 helper、
不设置个人 `PYTHONPATH` 或 helper 环境变量，也不进入维护者个人主目录。已确认的
网格可由后续 M3D-C1 作业重复使用，不需要每次时间推进前重新生成。

### Release 构建文件

`packaging/release/` 中各文件职责如下：

| 文件 | 职责 |
|---|---|
| `build_release.sh` | Linux 服务器构建入口；从上传源码根目录离线组装可移动目录、manifest、SHA-256 与 tar.gz |
| `linkmesh-launcher` | 最终用户入口模板；安装为 `bin/linkmesh`，定位 Release、目标 Python 和 Release 内 helper |
| `linkmesh-bootstrap.py` | Release Python 路径引导；将 Release site-packages 插入当前 Python 进程并启动 LinkMesh |
| `linkmesh-check` | 部署诊断入口；执行 core、TRIMEG、plot、M3D-C1 分层环境检查 |
| `README.md` | Release 构建和交付说明；面向维护者与物理模拟使用者 |

这些文件在 Windows 本地维护和静态检查；Linux Release 构建、OFT 导入、helper、
MPI、TRIMEG 与 M3D-C1 运行状态只有服务器直接证据才能更新。生成的 Release 目录和
同名 tar.gz 是服务器构建产物，不是业务源码、Git 输入或技术依据。

当前已验证 Python 环境为 CPython 3.12.13。现有证据不建立 `Python >= 3.11` 或其他
通用最低版本；其他 Python 3 版本必须由实际导入和运行反馈确认。

## 12. 普通用户最短使用路径

### 推荐 Case 布局

当前推荐让一份个人维护的 LinkMesh 与各个 M3D-C1 Case 位于同一层，而不是把 LinkMesh 复制进每个 Case：

```text
work/
├── LinkMesh/
│
├── 100/
│   ├── GFile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   └── mesh/
│
├── 101/
│   ├── GFile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   └── mesh/
│
├── 200/
│   ├── GFile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   └── mesh/
│
└── 201/
    ├── GFile
    ├── m3dc1.in
    ├── linkmesh.in
    └── mesh/
```

每个 Case 应保存自己的：

- `linkmesh.in`；
- GFile；
- M3D-C1 输入文件；
- 生成的 TXT、SMB 和 PNG；
- 与该 Case 对应的求解设置。

配置文件中的相对路径按配置文件所在目录解析，因此适合随 Case 一起保存。

### 最简命令

标准配置示例位于 `examples/m3dc1_single_region/linkmesh.in.example`。用户可将其复制到 Case 目录并改名为 `linkmesh.in`，再进入 Case 运行：

```bash
python -m linkmesh --config linkmesh.in
```

其中：

- `--config` 后面是该 Case 的配置文件路径；
- LinkMesh 按配置读取 GFile；
- 配置决定目标、区域策略、网格尺度以及 TXT、SMB、PNG 输出路径。

临时生成更细的单区域网格：

```bash
python -m linkmesh --config linkmesh.in --mesh-dx 0.05
```

这里的 `0.05` 单位为米，是本次运行对配置文件 single-region 网格尺度的临时覆盖，
不会自动修改 `linkmesh.in`。

配置优先级为：

```text
内建默认值 < linkmesh.in < 显式 CLI 参数
```

因此，稳定科研设置应写入 `linkmesh.in`；CLI 参数适合临时改变网格尺度或输出路径。

### 当前运行环境说明

当前仓库尚未完成面向所有用户的统一安装。上述命令能否在任意 Case 目录执行，还取决于：

1. 当前 Python/Conda 环境能够找到 LinkMesh Python 包；
2. 正式 OFT 依赖可用；
3. M3D-C1 target 使用的 native helper 已编译；
4. SMB Writer 能按正式定位规则找到 helper；
5. helper 所需的 SCOREC/PUMI 与 MPI 环境正确。

不得把当前开发环境写成“任意目录无需配置即可运行”的已完成安装。后续计划建设无需 `sudo` 的个人 Conda 用户级安装。

---

## 13. Case 100/101/200 系列管理建议

组内 Case 编号可以同时表达 M3D-C1 源码版本和输入版本。例如：

```text
100/  完整保存某一版 M3D-C1 源码或编译结果
101/  复用 100 的源码版本，只修改输入或物理参数
102/  复用 100 的源码版本，只修改输入或物理参数

200/  完整保存更新后的 M3D-C1 源码或编译结果
201/  复用 200 的源码版本，只修改输入或物理参数
202/  复用 200 的源码版本，只修改输入或物理参数
```

建议遵循：

- LinkMesh 只维护一份，不复制到每个 Case。
- 每个 Case 保存自己的 `linkmesh.in` 和网格产物。
- 修改 GFile、计算域边界策略或网格尺度时，应重新生成网格。
- 只修改 M3D-C1 求解参数、且网格需求不变时，可以复用已确认的 TXT 和 SMB。
- TXT、SMB 和 PNG 应与产生它们的配置文件一起保存，便于复现。
- 临时 CLI 覆盖用于试验；需要长期保留的参数应写回该 Case 的配置文件。

---

## 14. 生成网格与提交作业

当前推荐流程是：

```text
进入 Case
  → 运行 LinkMesh
  → 生成 TXT、rank-0 SMB 和 PNG
  → 人工检查 PNG
  → 固化网格输入
  → 提交 M3D-C1 求解作业
```

暂不建议在每次 `sbatch` 中无条件执行 LinkMesh，原因包括：

- 会重复生成未变化的网格；
- 可能覆盖已经人工确认的 TXT、SMB 和 PNG；
- 新网格未经检查就直接进入求解；
- LinkMesh、OFT、PUMI、MPI 和 M3D-C1 的错误会混入同一份作业日志；
- 不利于追踪某次物理结果实际使用的网格版本。

如果服务器不允许在登录节点生成网格，可以使用独立的轻量网格预处理作业：

```text
提交网格预处理作业
  → 生成 TXT、SMB、PNG
  → 人工检查 PNG
  → 再提交正式 M3D-C1 作业
```

正式求解脚本可以检查 TXT 和 rank-0 SMB 是否存在，但不应默认重新生成并覆盖它们。

---

## 15. 当前能力边界

### 当前可用

- 通过 OFT 读取 GFile/EQDSK；
- 以 LCFS 为边界生成单区域二维三角网格；
- 生成统一 `Mesh2D`；
- 生成 single-loop、single-face M3D-C1 analytic model；
- 写出配套 TXT；
- 通过 SCOREC/PUMI helper 写出串行 rank-0 native SMB；
- 生成 PNG 人工检查图；
- 写出 TRIMEG HDF5；
- 通过配置文件和显式 CLI 参数编排当前已开放流程；
- 通过 TXT+SMB 完成 M3D-C1 加载和初始化。

### 当前未开放

- M3D-C1 多区域；
- 多 geometric face；
- 三维网格；
- 环向切分；
- MPI 并行分区；
- `part*.smb` 或 `split_smb` 替代实现；
- M3D-C1 时间推进主循环；
- M3D-C1 中等或长时运行稳定性；
- M3D-C1 物理结果正确性；
- SMB loader 或 validator；
- 通用边界插件系统；
- Simmetrix、`.smd` 或 `.sms` 正式依赖。

多区域、三维和并行分区不能从当前单区域闭环外推为已经支持。

---

## 16. 下一步

v4.1 主线优先完成老师和初期使用者需要的产品化收口：

1. 保持现有 `array_file`、GFile、TRIMEG 和 M3D-C1 可用入口稳定。
2. 验证已实现的 `array_file + 可选 GFile LCFS PNG reference` 工作流；array file
   继续是唯一实际计算域边界，两条 Reader 只在 Plotter 汇合。
3. 在 Linux 服务器首次生成并结构检查不依赖个人 `PYTHONPATH`、开发构建目录或
   维护者主目录的普通用户 Release。
4. 将发布候选交给 M3D-C1 和 TRIMEG 使用者，分别取得初期使用报告。
5. 根据真实反馈修正 CLI、诊断、文档、打包和运行时定位。
6. 在老师确认共享根目录、权限和 module 能力后继续推进版本化共享 release。

OFT 单区域空间变密度、Triangle refinement、多区域拓扑以及 M3D-C1 C1 与多
geometric face 调查继续保留，但降为后续 P2 工作。动态自适应、磁面对齐、
M3D-C1 多区域、多 face、三维和并行分区仍未开放。

文档中的“统一用户入口命令”“可移动发布目录”和“物理意义上的单文件可执行程序”
是三个不同概念。打包与 ABI 探针完成前，不得宣称真正单文件已经实现。发布候选仍需
验证 OFT 26.6、`linkmesh-scorec-helper`、SCOREC/PUMI、MPI、C++ runtime 和 ABI，
不得预设未经验证的相对布局、RPATH 或系统库兼容性。

本轮 Release 构建系统在授权文件内完成独立修订，本地状态为
**IMPLEMENTED / STATICALLY CHECKED**。未修改业务源码、native helper、CMake、
tests、requirements、History 或权限范围外文件。

Linux Release 状态必须继续分层记录：

```text
GENERATED: NOT RUN
STRUCTURALLY CHECKED: PENDING
EXTERNAL SERVER VALIDATION: PENDING
TRIMEG REAL RUN: PENDING
M3D-C1 REAL RUN: PENDING
```

遇到问题时：

| 问题 | 查证位置 |
|---|---|
| 正式接口、字段或格式是什么 | `LinkMesh_Architecture_Plan.md` |
| 某项功能是否实际验收过 | `History.md` |
| 当前 CLI 如何编排 | `src/linkmesh/cli.py` |
| 配置如何合并和限制组合 | `src/linkmesh/config.py` |
| `Mesh2D` 保存什么 | `src/linkmesh/mesh.py` |
| TXT 与 SMB 如何共享模型 | `src/linkmesh/m3dc1_model.py` |
| helper 源码在哪里 | `native/linkmesh_scorec_helper/` |
| 下一阶段调查如何拆解 | `docs/linkmesh/work_plan.md` |
| 日常 Case 如何组织 | `docs/linkmesh/plan.md` |
| TRIMEG 消费契约依据 | `docs/trimeg/` |
| OFT 或 M3D-C1 外部实现如何工作 | `TOKAMAKER/`、`M3DC1/`，仅限只读查证 |

---

## 17. 本文档的边界

本导读只回答“项目里有什么、如何找到、如何运行、当前做到哪里”。

它不重复以下内容：

- `Mesh2D` 字段级正式契约；
- TRIMEG HDF5 全部数据集布局；
- Python/C++ 内部交换文件字节结构；
- PUMI/APF/MDS 生命周期细节；
- 所有测试条目和运行计数；
- 多区域或未来功能设计。

这些内容分别由当前技术蓝图、业务源码、测试和历史归档承载。若本导读与它们不一致，应修正本导读，而不是用本导读改变项目技术事实。
