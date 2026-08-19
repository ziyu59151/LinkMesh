# LinkMesh 项目目录树与使用导读

- 文档主受众：Human-facing
- 知识库用途：人类导读
- 文档状态：当前有效（对应技术蓝图 v5.8；根命令及 legacy nested 源码收口已经完成，
  `regions inspect/generate` 是唯一多区域入口；全局 `transition_width`、
  `transition_gradient` 及根/regions R-Z point local refinement 均已实现并完成
  生成侧真实验收；Triangle shape quality Q plot 已获批准，源码实现仍 PENDING）
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

LinkMesh 当前不建设 M3D-C1 消费端、SMB loader、SMB validator、三维网格或并行
分区工具。多区域 M3D-C1 生成侧已实现，消费验证继续按独立层级记录。

---

## 2. 当前状态速览

| 项目 | 当前状态 |
|---|---|
| GFile Reader | 已实现并通过既有验收 |
| 根命令 OFT/Triangle 二维网格生成 | 当前产品契约仅单区域；历史 nested 路径曾有真实运行证据，现已 RETIRED，源码删除 PENDING |
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
| `array_file + 可选 GFile LCFS PNG 参考` | IMPLEMENTED |
| `--plot-lcfs` 与 `[output].plot_lcfs` | IMPLEMENTED |
| Release 构建、launcher、bootstrap 与分层检查基础设施 | IMPLEMENTED |
| 初版 Release | 已发送同门和老师，当前反馈可正常使用 |
| EAST M3D-C1 后续运行 | 已交付，加载、初始化、时间推进结果 PENDING |
| 最新 TRIMEG HDF5 | 已生成并交付卢老师测试，反馈 PENDING |
| `single_region + first_wall` | 未实现 |
| `single_region + flux_surface` | 未实现 |
| `boundary_source=multi_array_file` | IMPLEMENTED；只通过独立 `regions` 命令族进入 |
| `linkmesh regions inspect/generate` | IMPLEMENTED；唯一正式多区域入口；two-level/four-level 真实 OFT/Triangle 生成已通过 |
| regions map | IMPLEMENTED；inspect 输出、generate 必须读取的 TOML 用户产物 |
| 多区域 N-region `Mesh2D` | STRUCTURALLY CHECKED |
| 多区域 mesh PNG | GENERATED；已由 User 人工复核 |
| `regions generate --target mesh_only` | IMPLEMENTED；默认行为 |
| `regions generate --target trimeg` | IMPLEMENTED；真实 HDF5 GENERATED，User 确认自动测试和实际检测通过；标准 MATLAB/TRIMEG 加载 PENDING |
| OFT 多 Region与分 Region常数 dx | 运行探针确认 |
| OFT Region 编号主逻辑 | setup、fresh rebuild、dx change 已由运行探针确认 |
| OFT 无 plasma technical role | OFT 26.6 主动拒绝，准确异常已确认 |
| synthetic plasma compatibility role | IMPLEMENTED；仅服务 regions OFT 兼容，不表达用户物理语义 |
| OFT 自动包含树 | 未提供 |
| LinkMesh 轻量包含推导 | IMPLEMENTED |
| OFT multi-array 最小探针程序 | 调查完成，无需继续扩展当前探针 |
| OFT 五类合成案例 | 全部 PASS；GENERATED / STRUCTURALLY CHECKED |
| M3D-C1 求解器多区域模拟能力 | User 根据同门实际展示确认 |
| M3D-C1 多区域输入契约调查 | COMPLETED |
| 教程三 face 拓扑 | CONFIRMED |
| exchange 多 face record 表达能力 | CONFIRMED |
| 原始 curve corner exact-match | REJECTED BY DIRECT PROBE |
| topology-driven classification | IMPLEMENTED |
| schema v2 | IMPLEMENTED |
| multi-face ModelSpec / build result | IMPLEMENTED |
| helper 多 face 支持 | IMPLEMENTED；支持 schema v1/v2 |
| `regions generate target=m3dc1` | IMPLEMENTED |
| LinkMesh 多区域 TXT+SMB | `case_002` GENERATED / DELIVERED |
| LinkMesh 多区域 M3D-C1 消费验证 | PENDING |
| OFT/Triangle transition refinement | IMPLEMENTED；真实 `rpqazQ` 已在目标服务器运行 |
| 全局 `transition_width` | IMPLEMENTED / PRESERVED；所有不同 dx interfaces 共享同一 W |
| 全局 `transition_gradient` | IMPLEMENTED；真实 G=10 案例 GENERATED / USER-CHECKED PASSED |
| global G → per-interface Wi 与 gradient diagnostics | IMPLEMENTED / CHECKED |
| M3D-C1 gradient-refined mesh 消费 | PENDING |
| R-Z point local refinement | IMPLEMENTED；root 与 regions generate 均已真实生成并由 User 检查 |
| 可重复 `--local-refinement R,Z,DX,W` | IMPLEMENTED；根与 regions 使用不同严格 TOML 路径，CLI 列表整体覆盖 TOML 列表 |
| 复杂合成 transition 压力案例 | GENERATED；PNG USER-CHECKED PASSED |
| final `Mesh2D` verbose 数值质量报告 | IMPLEMENTED / USER ACCEPTED |
| Triangle shape quality Q plot | IMPLEMENTED / USER-ACCEPTED；root 与 regions generate 使用独立 `quality_plot` |
| fixed red-blue-green Q colormap | IMPLEMENTED / USER-ACCEPTED；颜色范围固定为 `[0,1]` |
| refined mesh 的 M3D-C1 消费 | PENDING |
| OFT 单区域空间变网格密度 | 待调查，未实现 |
| OFT 多区域拓扑 | 生成与共享 mesh topology 已调查；M3D-C1 interface classification 对应仍待确认 |
| M3D-C1 多区域、多 geometric face 与 C1 兼容性 | 输入契约调查完成；实现与 native/消费验证未开放 |
| 动态自适应、磁面对齐、三维和并行分区 | 当前未开放 |
| 正式共享部署 | 方案已讨论，实施 PENDING |

当前最准确的结论是：

```text
根命令：
SINGLE-REGION WORKFLOW / CURRENT
ROOT MESH_DX = 唯一单 Region 尺度
NESTED_THREE_REGION = RETIRED / SOURCE REMOVAL COMPLETED
--PROFILE / --PLASMA-DX / --VACUUM-DX / --OUTER-DX = REMOVED
ARTIFICIAL_OUTER NESTED CONSTRUCTION = REMOVED

LinkMesh 单区域生成侧最小闭环：PASSED
TXT、rank-0 SMB、PNG：已生成
PNG 人工检查：PASSED
TXT+SMB 加载：PASSED
M3D-C1 初始化：PASSED
M3D-C1 时间推进、稳定性和物理正确性：PENDING

array_file + 可选 GFile LCFS PNG 参考：
IMPLEMENTED

初版 Release：
DELIVERED TO COLLEAGUES AND TEACHERS
CURRENT FEEDBACK: USABLE

multi_array_file / regions inspect/generate / TOML regions map：
IMPLEMENTED / ONLY MULTI-REGION PRODUCT ENTRY
REGIONS MESH_DX = 全部最终 Regions 默认尺度
REGION_DX = 按最终 Region ID 覆盖
REAL TWO-LEVEL / FOUR-LEVEL OFT MESHES GENERATED
N-REGION MESH2D STRUCTURALLY CHECKED
MESH PNG GENERATED / USER-REVIEWED

regions generate 多区域 TRIMEG：
WIRING IMPLEMENTED
REAL HDF5: GENERATED
AUTOMATED TESTS / ACTUAL CHECK: USER-CONFIRMED PASSED
EXACT PASSED COUNT / FULL CHECK DETAILS: NOT PROVIDED
MATLAB/TRIMEG LOAD: PENDING

OFT 多 Region与分 Region常数 dx：
PROBE-CONFIRMED
FIVE CASES GENERATED / STRUCTURALLY CHECKED

OFT Region 编号主逻辑：
PROBE-CONFIRMED
SETUP / FRESH REBUILD / DX CHANGE CONSISTENT

OFT 无 plasma technical role：
PROBE-CONFIRMED UNSUPPORTED
VALUEERROR: NO PLASMA REGION SPECIFIED

synthetic plasma compatibility role：
IMPLEMENTED
ADAPTER COMPATIBILITY ONLY

OFT 任意无序曲线自动包含树：
NOT PROVIDED

OFT multi-array 最小探针：
FIVE SYNTHETIC CASES PASS
GENERATED / STRUCTURALLY CHECKED
INVESTIGATION COMPLETED

M3D-C1 本身能够进行多区域模拟：
USER-CONFIRMED SOLVER CAPABILITY

M3D-C1 多区域输入契约调查：
COMPLETED
TUTORIAL THREE-FACE TOPOLOGY: CONFIRMED
EXCHANGE MULTI-FACE RECORD CAPABILITY: CONFIRMED

LinkMesh 多区域 M3D-C1：
ORIGINAL-CORNER EXACT MATCH: REJECTED BY DIRECT PROBE
TOPOLOGY-DRIVEN CLASSIFICATION: IMPLEMENTED
SCHEMA V2: IMPLEMENTED
MULTI-FACE MODELSPEC / BUILD RESULT: IMPLEMENTED
HELPER V1/V2 MULTI-FACE SUPPORT: IMPLEMENTED
REGIONS TARGET=M3DC1: IMPLEMENTED
CASE_002 TXT+SMB+PNG: GENERATED
TXT+SMB: DELIVERED
CONSUMER VALIDATION: PENDING
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
│       ├── mesh_quality.py
│       ├── m3dc1_model.py
│       │
│       ├── readers/
│       │   ├── __init__.py
│       │   ├── boundary_reader.py
│       │   └── gfile_reader.py
│       │
│       ├── mesher/
│       │   ├── __init__.py
│       │   ├── oft_adapter.py
│       │   └── triangle_refinement.py
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
├── scripts/
│   ├── probe_oft_multi_array_regions.py
│   ├── probe_oft_no_plasma.py
│   ├── probe_m3dc1_interface_mapping.py
│   └── probe_scorec_multi_face/
│       ├── CMakeLists.txt
│       └── main.cc
│
├── native/
│   └── linkmesh_scorec_helper/
│       ├── CMakeLists.txt
│       └── main.cc
│
├── packaging/
│   └── release/
│       ├── README.md
│       ├── build_release.sh
│       ├── linkmesh-launcher
│       ├── linkmesh-bootstrap.py
│       └── linkmesh-check
│
├── tests/
│   ├── test_configuration_contract.py
│   ├── test_geometry_and_readers.py
│   ├── test_oft_adapter_contract.py
│   ├── test_format_contracts.py
│   ├── test_cli_contract.py
│   ├── test_plotter_contract.py
│   └── test_release_packaging.py
│
├── docs/
│   ├── linkmesh/
│   │   ├── work_plan_1.md
│   │   ├── work_plan_2.md
│   │   ├── multi_array_regions_investigation_report.md
│   │   ├── m3dc1_multi_region_model_topology_evidence.md
│   │   ├── m3dc1_multi_region_pumi_api_evidence.md
│   │   ├── m3dc1_multi_region_pumi_input_contract_report.md
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
- `docs/linkmesh/` 下的 work plan 是人类阶段记事本，不是 Aider 技术依据、字段契约
  或第二份技术蓝图。
- `scripts/probe_oft_multi_array_regions.py` 是 OFT 26.6 多区域生成、基本结构、
  setup 编号、fresh rebuild、dx change 和输入重排影响的独立调查工具；五类案例已
  全部 PASS。
- `scripts/probe_oft_no_plasma.py` 是 root=boundary、内部=vacuum 且无 plasma 的
  对照调查工具；真实运行确认 setup-only 和完整 build 均被 OFT 主动拒绝。
- 两个 probe 都不是 `src/linkmesh` 业务模块，也不实现 `regions` CLI；相关调查已经
  完成，无需继续扩展当前探针。
- `docs/linkmesh/multi_array_regions_investigation_report.md` 记录多轮廓、多 Region、
  包含树、分区域常数 dx、OFT/Triangle 能力和 `regions` 工作流的调查依据。
- `docs/linkmesh/oft_triangle_transition_refinement_investigation.md` 记录 transition
  refinement 的 Triangle 1.6 源码、ABI、ownership、真实 `rpqazQ` 运行和当前实现
  收口证据；详细质量指标与失败边界以根蓝图为准。
- `docs/linkmesh/m3dc1_multi_region_model_topology_evidence.md` 记录教程和生成侧
  vertices、edges、loops、faces、tags、共享界面与 orientation 的字段级证据。
- `docs/linkmesh/m3dc1_multi_region_pumi_api_evidence.md` 记录当前 exchange、
  classification、SCOREC/PUMI 2.2.9 API 与 helper single-face 限制的字段级证据。
- `docs/linkmesh/m3dc1_multi_region_pumi_input_contract_report.md` 综合前两份证据及
  最新 probes，定义从最终 `Mesh2D` topology 自动派生 model/classification 的正式
  设计、不可变 build result、schema v2、helper、CLI、验收和停止条件；它不表示
  schema v2、multi-face ModelSpec/helper 或任意 N-region M3D-C1 已经实现。
- `scripts/probe_m3dc1_interface_mapping.py` 已直接否证原始 curve corner
  exact-match 候选，停止维护；其失败不否定最终 topology interface 提取。
- `scripts/probe_scorec_multi_face/` 因 PIE/static `libmds.a` 链接不兼容未产生
  executable 或 runtime 结论，停止维护；不得解释为正式 helper 或 PUMI 失败。
- `docs/linkmesh/LinkMesh_Architecture_Plan_v3.7.md` 是进入 v4.0 前的完整 3.x 历史快照。
- `docs/linkmesh/LinkMesh_Architecture_Plan_v1.13.md` 是更早的历史版本参考。
- 根目录当前 `LinkMesh_Architecture_Plan.md` 是唯一有效技术蓝图；历史快照和专题报告不得覆盖其正式裁决。
- `packaging/release/README.md` 是唯一最终用户 Release README 来源；构建器只把它
  复制到外部交付目录，不把 README 放入 tar.gz。
- `packaging/release/build_release.sh` 组装内部可移动 Release，并生成外部 README、
  tar.gz 和 tar.gz.sha256 三文件交付目录。
- launcher、bootstrap 和检查器分别负责可移动入口、Release 包路径优先加载和
  `core/trimeg/plot/m3dc1/all` 分层环境诊断。
- `tests/test_release_packaging.py` 只保护发布结构和脚本静态契约，不证明 OFT、
  SMB、TRIMEG 或 M3D-C1 外部消费。
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
| `docs/linkmesh/` 下的 work plan | 查询人类阶段记事时阅读；它们不是字段或技术契约依据。 |
| `docs/linkmesh/multi_array_regions_investigation_report.md` | 查询 multi-array 格式、OFT N-region 数据流、几何算法、包含树、Region ID/dx、两阶段 CLI 和风险时阅读。 |
| `docs/linkmesh/m3dc1_multi_region_model_topology_evidence.md` | 查询教程三 face、共享 loops/edges、TXT 拓扑、tags 与 orientation 证据时阅读。 |
| `docs/linkmesh/m3dc1_multi_region_pumi_api_evidence.md` | 查询 exchange records、classification、PUMI 2.2.9 API、ownership 与 helper 限制时阅读。 |
| `docs/linkmesh/m3dc1_multi_region_pumi_input_contract_report.md` | 查询多区域 M3D-C1 实施级候选、schema v1/v2 裁决、测试矩阵、停止条件和消费边界时阅读。 |
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

已批准但尚未实现的 multi-array 数据流是：

```text
重复 counted R-Z blocks
  → 未来多轮廓 Reader 和基础检查
  → 未来基于 OFT Region 基础能力的轻量包含推导
  → OFT 最终 attribute Region ID
  → regions map + inspection PNG + 人工确认
  → 显式 Region ID/dx
  → OFT/Triangle
  → Mesh2D + mesh PNG
```

正式 CLI 设计为：

```text
linkmesh regions inspect ...
linkmesh regions generate ...
```

OFT 官方多 Region 和分 Region常数 dx 能力已经确认；五类探针全部 PASS，编号和
no-plasma 调查已经结束。OFT 不会从任意无序曲线自动建立包含树。首版不建设通用
鲁棒计算几何系统，inspection PNG 不是数学证明。多轮廓 Reader、轻量包含逻辑、
regions parser 和 TOML regions map Writer 均不是当前已存在业务文件；下一步是第一批
inspect 源码实现。

已经实现的 LCFS 参考绘图工作流包含两条独立支路：

```text
实际网格支路：
array file → Boundary Reader → OFT/Triangle → Mesh2D ─┐
                                                      ├→ Plotter → PNG
参考几何支路：                                        │
GFile → GFile Reader → GFileData/LCFS ────────────────┘
```

array file 是唯一实际计算域边界。GFile LCFS 只在 Plotter 中作为参考曲线，两条
Reader 不互相调用。参考 `GFileData` 不进入 Mesher、`Mesh2D`、TRIMEG Writer、
M3D-C1 Writer 或 native helper，因此不会改变网格或求解器输出。该能力当前为
**IMPLEMENTED**。

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
- **职责**：根命令编排单区域 Reader、Mesher、Writer 和 Plotter；`regions
  inspect/generate` 是作用域隔离的唯一多区域入口。legacy nested 参数和分支已经
  删除；四层 CLI help 提供严格 TOML 路径提示和 `schema_version = 1` 入口说明。
  下一轮将仅在 root 与 regions generate 接入独立 `--quality-plot`，并确保它消费
  refinement 后的 final `Mesh2D`；当前尚未实现。
- **输出**：标准工作流按目标生成 HDF5 或配套 TXT/SMB/PNG；多区域 generate 默认
  输出 mesh PNG，选择 `target=trimeg` 时把同一个 N-region `Mesh2D` 交给既有 HDF5
  Writer 并继续输出 PNG。
- **TRIMEG HDF5 路径参数**：正式参数为 `--hdf5 PATH`，`--h5 PATH` 是完全同义别名；
  二者最终形成同一个 `EffectiveConfig.hdf5_path`。旧 `--output` 已从当前接口删除。
- **不负责**：网格算法、边界重采样、几何分类、SMB 字节实现或 helper 生命周期。

`src/linkmesh/__main__.py` 只负责让以下命令进入同一个 CLI 主入口：

```bash
python -m linkmesh
```

### `src/linkmesh/config.py`

- **输入**：内建默认值、`linkmesh.in` 和显式 CLI 覆盖。
- **职责**：读取并严格校验根命令单区域配置及独立 regions 配置，是当前严格 TOML
  schema、允许 section/key 和路径映射的唯一实现位置。profile 和三个 legacy 区域
  dx 已从正式契约及实时源码删除；下一轮将分别增加 root
  `[output].quality_plot` 与 generate `[regions].quality_plot`，inspect 继续拒绝；
  当前尚未实现。详细配置示例见 `docs/linkmesh/plan.md`，技术契约见蓝图。
- **输出**：不可变的标准有效配置对象或独立 regions 配置对象。
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

- **输入**：根命令的单个实际计算边界，或 regions 已验证的 Region plan。
- **职责**：根命令构造 single-region OFT Domain；regions 构造 N-region Domain；
  调用 OFT/TokaMaker/Triangle 并规范化为 `Mesh2D`。nested/artificial-outer 专用
  分支已经删除。
- **输出**：二维非结构化三角网格。
- **候选工作流边界**：`array_file` 路径只接收 array boundary，不接收参考
  `GFileData`，也不感知 `--plot-lcfs`。
- **不负责**：第二种剖分后端、参考 GFile 绘图、PUMI 网格生成、
  TRIMEG/M3D-C1 文件写出或配置文件解析。

当前根命令天然是单区域，不再要求用户选择 profile。正式来源包括已实现的 `lcfs`
和 `array_file`，并保留尚未实现的 `first_wall` 单区域规划。根命令唯一尺度参数为
`mesh_dx`。

`multi_array_file` 不属于旧单曲线入口，只允许通过 `regions` 命令族进入。生产路径
已经完成基础几何检查、唯一根包含树、setup-only 最终 Region ID、map 核对和显式 dx
映射，并能生成 N-region `Mesh2D`；two-level/four-level 真实 OFT/Triangle 网格已
生成并完成结构检查。该结果不开放异常 polygon、M3D-C1 多区域或多 face。

`lcfs` 来源读取 GFile；`array_file` 来源读取 counted R-Z boundary，并且 v1 契约下
不同时读取 GFile。

### `src/linkmesh/mesh.py`

- **输入**：节点、三角形连接表、区域编号和可选有序外边界。
- **职责**：定义唯一正式统一网格对象 `Mesh2D`，供所有下游 Writer 和 Plotter 使用。
- **输出**：求解器无关的内存网格表示。
- **不负责**：调用 OFT、PUMI、h5py、CLI 或任何 Writer。

### `src/linkmesh/mesher/triangle_refinement.py`

- **状态**：IMPLEMENTED；真实 `rpqazQ` 和 global-gradient 案例已在目标服务器运行。
- **职责**：自动提取 transition interfaces、判断粗细侧、计算指数 profile 和逐
  triangle 面积约束、管理 native ownership、执行有限 refinement并返回 final
  `Mesh2D`。
- **产品语义**：width 模式使用一个全局 W；gradient 模式使用一个全局对数尺度梯度，
  并为每条 interface 派生不同的 W。R-Z point sources 与 interface constraints
  共享 combined Amax 和同一 refinement 循环；root 与 regions local refinement
  均已实现并完成生成侧验收。详细契约见当前技术蓝图。
- **不负责**：CLI 打印、Writer、Plotter、PUMI 或把诊断保存到 `Mesh2D`。

### `src/linkmesh/mesh_quality.py`

- **状态**：数值报告 IMPLEMENTED / USER ACCEPTED；quality plot 共享逐 triangle
  Q 接口 IMPLEMENTED / USER ACCEPTED。
- **职责**：只读计算 final `Mesh2D` 通用数值质量，并合并 transition 与 local
  refinement diagnostics，形成现有 `--verbose` 人类可读摘要；下一轮继续作为 Q
  数学的唯一来源，为数值汇总和 Plotter 提供同一逐 triangle Q。
- **不负责**：修改 mesh、依赖 Matplotlib、调用 Triangle、定义新质量失败阈值。
- 详细 Q 公式、颜色映射、数据流和验收边界统一查阅当前技术蓝图。

### `src/linkmesh/m3dc1_model.py`

- **输入**：当前正式路径接收单区域 `Mesh2D` 及其有序外边界。
- **职责**：当前构造 single-loop、single-face 的 `M3DC1ModelSpec`。
- **输出**：TXT Writer 和 SMB Writer 共同使用的 analytic geometric model。
- **多区域状态**：topology-driven multi-face build result 已实现，并统一携带
  ModelSpec、mappings 和 classifications 供 TXT/SMB Writers 使用。
- **不负责**：调用 PUMI、生成 SMB、读取固定外部 TXT 模板或当前处理 multi-face
  model。

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

- **输入**：作为实际网格和实际边界来源的 `Mesh2D`，以及现有 geometry plot 可选的
  参考 `GFileData`。
- **职责**：现有 geometry plot 继续绘制三角网格、actual mesh boundary、Region 和
  可选 LCFS reference，行为保持不变；下一轮新增接收 final `Mesh2D` 与已计算逐
  triangle Q 的独立 quality PNG，当前尚未实现。
- **输出**：相互独立的 geometry PNG；未来可选 Triangle shape quality Q PNG。
- **不负责**：重新计算 Q、把 quality plot 变成第二份完整 geometry plot、把 array
  boundary 标为 LCFS、把 LCFS 标为 mesh boundary、修改网格，或判断 SMB/HDF5
  是否可被求解器消费或替代数值验收。

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
6. helper 不重新剖分网格；它只根据 Python 提供的节点、连接关系、几何模型和分类信息构造 APF/MDS 网格，并调用 SCOREC/PUMI 官方接口写出 native SMB。当前 helper 的正式 contract 仍为 schema v1 single-loop/single-face；多 face 支持只是设计候选，等待 schema v2 User 裁决和目标环境 native probe。
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

## 8. Release 基础设施导读

仓库内发布源码位于：

```text
packaging/release/
├── README.md
├── build_release.sh
├── linkmesh-launcher
├── linkmesh-bootstrap.py
└── linkmesh-check
```

各文件职责：

| 文件 | 职责 |
|---|---|
| `README.md` | 唯一最终用户 Release README 来源；构建时原样复制到外部交付目录 |
| `build_release.sh` | 校验输入和依赖、组装内部 Release、生成内部 manifest、tar.gz 和外部 SHA-256 |
| `linkmesh-launcher` | 按自身真实路径定位 Release、选择 Python、定位包内 helper 并透传参数和退出状态 |
| `linkmesh-bootstrap.py` | 将 Release 的 `python/site-packages` 放到 `sys.path` 首位并启动 `linkmesh.__main__` |
| `linkmesh-check` | 提供 `core`、`trimeg`、`plot`、`m3dc1`、`all` 分层环境检查 |

构建器的正式外部输出是：

```text
LinkMesh-<version>-linux-x86_64-release/
├── README.md
├── linkmesh-release-<version>-linux-x86_64.tar.gz
└── linkmesh-release-<version>-linux-x86_64.tar.gz.sha256
```

tar.gz 解压后是：

```text
linkmesh-release-<version>-linux-x86_64/
├── bin/
├── manifest/
└── python/
```

tar.gz 内不含 README。`manifest/SHA256SUMS` 只校验内部普通文件；外部
tar.gz.sha256 只校验最终归档。外部 README 不进入内部 manifest，README 内容变化也
不会单独改变 tar.gz。

`packaging/release/` 中的脚本和 README 是 Git 源码。外部交付目录、解压目录、
tar.gz、tar.gz.sha256、helper 二进制、CMake 缓存和服务器验证输出都是生成物，不得
提交到 Git。

本轮只在源码层实施该基础设施，尚未基于本轮 master 生成 Linux Release，也未完成
内部 manifest、外部 SHA-256、ABI、真实文件生成或普通用户验收。

## 8A. multi-array 专项调查导读

专项报告：

```text
docs/linkmesh/multi_array_regions_investigation_report.md
```

报告基于 OFT 26.6 `meshing.py`、OFT 携带的 `triangle.h`、真实探针结果和当前
LinkMesh 业务源码，说明：

- OFT Region、segment、seed、dx、dx_curve 和最终 attribute 的真实数据流；
- OFT 当前缺少的严格 polygon 和 containment 验证；
- Triangle regionlist、holelist、segment 和 area 数据接口与 OFT wrapper 实际使用的
  区别；
- 成熟计算几何算法与 Shapely/GEOS 候选；
- 重复 counted block 格式；
- 唯一根包含树和 Region 差集定义；
- curve_id、OFT 最终 Region attribute/Region ID 和 dx；
- 正式 `regions inspect/generate` 二级子命令；
- regions map、inspection PNG、轻量包含推导、OFT 最小探针和停止条件。

当前职责边界：

| 职责 | 作用 | 当前状态 |
|---|---|---|
| 多轮廓 Reader | 严格读取重复 counted blocks并保留顺序 | 已实现；旧单 block Reader 契约未放宽 |
| 轻量包含推导 | 基础检查、parent/children 和唯一 root | 已实现；不是通用鲁棒几何验证器 |
| regions config/CLI | inspect/generate、配置覆盖、Region ID/dx 和 generate target/HDF5 路径 | 已实现；与旧入口作用域隔离 |
| regions map | 展示 curve、parent/children、最终 Region ID 和颜色 | 已实现 TOML schema v1 |
| OFT Adapter 扩展 | 消费 Region plan，构造多 Region Domain | 已实现；真实 two-level/four-level 生成通过 |
| Plotter 扩展 | inspection 关系图和 generate 网格图 | 已实现；PNG 不是数学证明 |
| TRIMEG 分派 | 将同一个 N-region `Mesh2D` 交给既有 complete-11 Writer | 接线已实现；真实文件分层验收待执行 |

独立调查工具 `scripts/probe_oft_multi_array_regions.py` 已在真实 OFT 26.6 环境完成
修正后重跑。两层、四层、单父双 sibling、混合树和重排输入五类案例的 generation、
mesh structure、numbering 和 overall 全部 PASS，状态为 GENERATED /
STRUCTURALLY CHECKED。`scripts/probe_oft_no_plasma.py` 进一步确认 OFT 强制至少一个
plasma technical role；无 plasma 时准确抛出
`ValueError: No plasma region specified`。

User 已批准 synthetic plasma compatibility role：root 使用 boundary；最大深度
leaf 使用 plasma，深度并列取最小 curve_id；其他内部 Region 使用 vacuum。该规则
仅属于 Adapter 兼容性，不表达用户物理语义。regions map 的 `physical_label` 可选、
默认空且不阻塞建网。

两个脚本都不是业务模块，也不得由 `src/linkmesh` 导入。调查阶段已经结束；正式
multi-array Reader、轻量包含树、deterministic synthetic role plan、OFT setup-only
编号、`regions inspect/generate`、TOML regions map、inspection PNG 和 N-region
`Mesh2D` 均已实现。

根命令 legacy nested 分支已经从实时源码删除；历史运行证据继续保留，不恢复兼容
入口。当前 transition gradient 的实施范围和验收标准只查阅当前技术蓝图。

## 9. 测试与证据导读

`tests/` 是小型内部契约回归集，按稳定契约组织：

| 测试文件 | 主要关注内容 |
|---|---|
| `tests/test_configuration_contract.py` | 配置默认值、合并优先级、路径基准、required-fields 和兼容矩阵。 |
| `tests/test_geometry_and_readers.py` | `Mesh2D.outer_boundary`、counted R-Z Reader 和最小 GFile Adapter 契约。 |
| `tests/test_oft_adapter_contract.py` | OFT 三数组转换、最终区域 ID、outer Region 时序、版本锁定和最小策略。 |
| `tests/test_format_contracts.py` | TRIMEG HDF5 Writer complete-11 数据集、M3D-C1 TXT、exchange schema 及 helper 子进程边界。 |
| `tests/test_cli_contract.py` | mesh-only、TRIMEG、M3D-C1、array reference 和配置提前失败的最小编排。 |
| `tests/test_plotter_contract.py` | 非空 PNG、reference 选择语义和输入不可变性。 |

测试优先直接检查返回值、真实临时文本、HDF5、TXT、交换文件和 PNG。mock 只用于
OFT、CLI 外部副作用和 native helper 等不可避免边界，不复制第三方内部算法，也不
把 mock 结果提升为外部消费证据。自动测试不能替代真实 OFT、TRIMEG、
M3D-C1/SCOREC/PUMI 加载、初始化、时间推进或物理验收。

当前正式测试树仅包含上表所列七个测试模块；仓库中不存在
`tests/test_hdf5_writer.py`，TRIMEG Writer 契约由 `tests/test_format_contracts.py`
保护。本轮实现前服务器精简基线为 96 passed；本轮修改后的最终数量必须以实际服务器
输出为准，未运行时不得猜测。

当前记录需要保留以下边界：

- User 最新直接证据确认 legacy nested 源码收口完成后服务器 pytest 全部通过，
  根单区域和 regions 功能运行验收通过；未提供精确 passed 数，不得猜测，也不得将
  较早不含 release packaging 测试的 123 passed 记录冒充当前完整数量。
- transition refinement、自动 interface/粗细侧和真实 `rpqazQ` 已实现并运行；
  gradient 真实案例的公式、diagnostics、final area constraints 和结构质量已检查，
  PNG 已由 User 人工检查通过。
- R-Z point local refinement 已实现；服务器自动测试为 160 passed，root 与 regions
  真实生成侧案例及 PNG 已由 User 检查。该证据不等于外部消费或物理验证。
- `case_002` 与复杂合成压力案例 PNG 已由 User 人工检查通过，但定量数值质量报告
  尚未实现，refined mesh 的 M3D-C1 消费仍为 PENDING。
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

## 10. 外部参考源码与只读区域

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

## 11. 新成员建议阅读顺序

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

## 12. 开发、验证与发布环境导读

正式源码在本地 Windows Git Bash 仓库维护；本地负责源码、文档和 Git 审查，不运行
测试、OFT/Triangle、native 构建或消费端验证。当前服务器源码由 User 从本地直接
上传，不采用服务器 `git pull` 工作流。Linux 服务器负责创建环境、编译 helper、
运行测试、生成产物和执行 M3D-C1/TRIMEG 验收。

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

## 13. 普通用户最短使用路径

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

这里的 `0.05` 单位为米，是本次运行对配置文件网格尺度的临时覆盖，不会自动修改 `linkmesh.in`。

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

## 14. Case 100/101/200 系列管理建议

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

## 15. 生成网格与提交作业

当前推荐流程是：

```text
进入 Case
  → 单区域使用根命令；多区域先 regions inspect 再 regions generate
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

## 16. 当前能力边界

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

- 根命令多区域或 legacy `nested_three_region`；
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

多区域只通过 `regions inspect/generate` 进入；根命令不得作为第二条多区域入口。
三维和并行分区不能从当前二维闭环外推为已经支持。

---

## 17. 下一步

multi-array OFT 前置调查、inspect/generate 生产链和多区域 TRIMEG 文件生成均已完成。
User 已确认自动测试和实际检测通过；标准 MATLAB/TRIMEG consumer 加载仍待直接证据。

M3D-C1 多区域生成侧已经实现：LinkMesh 从 final `Mesh2D` topology 自动派生
interfaces 和 cycles，以不可变 `M3DC1BuildResult` 统一驱动 TXT/SMB，并通过
schema v2 和正式 helper 写出 multi-face 产物。`case_002` TXT、rank-0 SMB 和 PNG
已生成，TXT+SMB 已交付同门；加载、初始化、时间推进、稳定性和物理结果必须继续
分别取得消费端直接证据，`writeNative()` 成功不能替代这些验收。

M3D-C1 本身能够进行多区域模拟，是 User 根据同门实际展示确认的能力；该事实不表示
LinkMesh 当前已生成或验证新多区域网格。

既有 v4.1 产品化路线继续包括：

1. 保持现有 `array_file`、GFile、TRIMEG 和 M3D-C1 可用入口稳定。
2. 实施已批准的 `array_file + 可选 GFile LCFS PNG reference` 工作流；array file
   继续是唯一实际计算域边界，两条 Reader 只在 Plotter 汇合。
3. 在 Linux 基于已实施的 Release 基础设施生成外部三文件交付目录，并验证内部
   manifest、外部 SHA-256、可移动入口和运行时依赖。
4. 将通过验证的发布候选交给 M3D-C1 和 TRIMEG 使用者，分别取得初期使用报告。
5. 根据真实反馈修正 CLI、诊断、文档、打包和运行时定位。
6. 在老师确认共享根目录、权限和 module 能力后继续推进版本化共享 release。

OFT 单区域空间变密度、Triangle refinement、多区域拓扑以及 M3D-C1 C1 与多
geometric face 调查继续保留，但降为后续 P2 工作。动态自适应、磁面对齐、
M3D-C1 多区域、多 face、三维和并行分区仍未开放。

文档中的“统一用户入口命令”“可移动发布目录”和“物理意义上的单文件可执行程序”
是三个不同概念。打包与 ABI 探针完成前，不得宣称真正单文件已经实现。发布候选仍需
验证 OFT 26.6、`linkmesh-scorec-helper`、SCOREC/PUMI、MPI、C++ runtime 和 ABI，
不得预设未经验证的相对布局、RPATH 或系统库兼容性。

初版 Release 已经发送给同门和老师，当前反馈为可以正常使用。该状态不自动证明
M3D-C1 时间推进、长期稳定性或物理结果正确性。

`multi_array_file`、`regions inspect/generate`、TOML regions map、轻量包含推导、
synthetic role Adapter、分 Region dx 和生产 N-region `Mesh2D` 均已实现；
`regions inspect/generate` 是唯一多区域产品入口。OFT 五类合成案例已全部
**PASS / GENERATED / STRUCTURALLY CHECKED**；Region 编号主逻辑和 no-plasma 行为
已由运行探针确认。OFT 自动包含树未提供，复杂异常几何仍不属于当前承诺。

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
| 人类阶段记事如何拆解 | `docs/linkmesh/` 下的 work plan；不作为技术契约 |
| 日常 Case 如何组织 | `docs/linkmesh/plan.md` |
| TRIMEG 消费契约依据 | `docs/trimeg/` |
| OFT 或 M3D-C1 外部实现如何工作 | `TOKAMAKER/`、`M3DC1/`，仅限只读查证 |

---

## 18. 本文档的边界

本导读只回答“项目里有什么、如何找到、如何运行、当前做到哪里”。

它不重复以下内容：

- `Mesh2D` 字段级正式契约；
- TRIMEG HDF5 全部数据集布局；
- Python/C++ 内部交换文件字节结构；
- PUMI/APF/MDS 生命周期细节；
- 所有测试条目和运行计数；
- 多区域或未来功能设计。

这些内容分别由当前技术蓝图、业务源码、测试和历史归档承载。若本导读与它们不一致，应修正本导读，而不是用本导读改变项目技术事实。
