# LinkMesh 项目目录树与使用导读

- 文档主受众：Human-facing
- 知识库用途：人类导读
- 文档状态：当前有效
- 最高依据：`LinkMesh_Architecture_Plan.md`
- 事实边界：本文档是面向组内研究人员的轻量仓库地图，不定义正式接口、字段契约或验收标准。遇到目录职责、数据结构、文件格式、模块接口或阶段状态争议时，以 `LinkMesh_Architecture_Plan.md` 为最终裁决依据；详细运行证据与测试记录见 `History.md`。
- 主要用途：帮助首次接触 LinkMesh 的研究人员快速理解项目用途、当前能力、源码布局、最短运行方式、原生 helper 的位置以及后续查证入口。

> AI 代理执行开发任务时，应先阅读 `CONTEXT.md` 和 `LinkMesh_Architecture_Plan.md`。本文件不是第二份技术蓝图，也不能替代正式技术契约。

---

## 1. LinkMesh 是什么

LinkMesh 是一个轻量级命令行网格转换工具。

它从 GFile/EQDSK 平衡文件读取托卡马克边界，通过 OFT/TokaMaker 调用 Triangle 生成二维非结构化三角网格，再把统一的 `Mesh2D` 翻译为目标求解器所需的静态网格文件。

当前已经跑通的最小用户链路是：

```text
GFile/EQDSK
  → 读取 LCFS
  → OFT/Triangle 单区域二维三角网格
  → Mesh2D
  → 配套 M3D-C1 analytic model TXT
  → PUMI native SMB
  → PNG 人工检查
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
| M3D-C1 analytic model TXT Writer | 已实现 |
| PUMI native SMB Writer 与 C++ helper | LinkMesh 生成侧已实现并在锁定的服务器 PUMI 环境运行通过 |
| 单区域真实 GFile M3D-C1 CLI | 已跑通，成功生成 TXT、rank-0 SMB 和 PNG |
| PNG 人工检查 | 已通过，未观察到明显孔洞、越界、折叠或显著异常单元 |
| 真实 M3D-C1/SCOREC 外部消费 | 待同门反馈；当前不能写成已通过 |
| 多区域、多 face、三维和并行分区 | 当前未开放 |

当前最准确的结论是：

```text
LinkMesh 单区域生成侧最小闭环：已跑通
TXT、rank-0 SMB、PNG：已生成
PNG 人工检查：已通过
真实 M3D-C1/SCOREC 外部消费验收：待同门完成
```

外部消费尚待验证，不表示 LinkMesh 生成失败；同样，生成侧运行成功和 PNG 检查通过也不能替代真实 M3D-C1/SCOREC 消费验收。

---

## 3. 当前仓库结构

以下目录树只展示理解项目所需的主要源码、文档和测试入口。大型外部参考源码不展开内部细节，缓存、临时运行目录、编辑器目录和构建垃圾不列入正式结构。

```text
LinkMesh/
├── CONTEXT.md
├── LinkMesh_Architecture_Plan.md
├── Project_Tree.md
├── History.md
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
│   └── m3dc1_smb_helper/
│       ├── CMakeLists.txt
│       └── main.cc
│
├── tests/
│   ├── test_gfile_reader.py
│   ├── test_mesh.py
│   ├── test_oft_adapter.py
│   ├── test_hdf5_writer.py
│   ├── test_m3dc1_model_writer.py
│   └── test_smb_writer.py
│
├── docs/
│   ├── linkmesh/
│   │   ├── plan.md
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

- LinkMesh 自有 Python 业务源码位于 `src/linkmesh/`。
- M3D-C1 native SMB helper 的正式源码位于 `native/m3dc1_smb_helper/`。
- `M3DC1/` 和 `TOKAMAKER/` 是外部参考源码区域，不是 LinkMesh 自有业务模块。
- `docs/trimeg/` 中的 MATLAB 读取脚本和真实样例是 TRIMEG 文件契约的只读证据。
- `docs/linkmesh/LinkMesh_Architecture_Plan_v1.13.md` 是历史版本参考，不得覆盖根目录当前 `LinkMesh_Architecture_Plan.md` 的正式裁决。
- 当前不把计划中的示例、安装元数据或配置模板画入实际仓库树。不存在或尚未确认存在的文件，不应被当成当前仓库组成。
- 编译 native helper 时产生的 `build/` 目录属于构建产物，不是正式源码目录，也不应作为 Git 源码提交。

---

## 4. 顶层文档导航

| 文档 | 应该什么时候读 |
|---|---|
| `Project_Tree.md` | 第一次接触项目时阅读，用于快速了解仓库、数据流和使用入口。 |
| `CONTEXT.md` | 开始开发或让 AI 修改项目之前阅读，了解行为规范、只读边界和开发纪律。 |
| `LinkMesh_Architecture_Plan.md` | 查询正式模块职责、数据结构、文件格式、接口、阶段状态和验收边界时阅读。它是唯一技术蓝图。 |
| `History.md` | 查询某项功能何时完成、运行过哪些命令、测试结果、真实样例和阶段证据时阅读。 |
| `docs/linkmesh/plan.md` | 查询组内 Case 管理、日常使用和部署建议时阅读。 |

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

当前单区域 M3D-C1 用户链路可按以下方式理解：

```text
CLI / linkmesh.in
  │
  ↓
src/linkmesh/config.py
  │  合并内建默认值、配置文件和显式 CLI 参数
  ↓
src/linkmesh/readers/gfile_reader.py
  │  通过 OFT GEQDSKEquilibrium 读取 GFile
  ↓
src/linkmesh/mesher/oft_adapter.py
  │  调用 OFT/TokaMaker/Triangle 生成二维三角网格
  ↓
src/linkmesh/mesh.py :: Mesh2D
  │
  ├──→ src/linkmesh/m3dc1_model.py
  │       │  从有序计算域外边界构造共享 M3DC1ModelSpec
  │       ├──→ writers/m3dc1_model_writer.py → analytic model TXT
  │       └──→ writers/smb_writer.py
  │               ↓
  │             native/m3dc1_smb_helper/
  │               ↓  SCOREC/PUMI APF/MDS + writeNative()
  │             rank-0 native SMB
  │
  ├──→ writers/hdf5_writer.py → TRIMEG HDF5
  │
  └──→ utils/plotter.py → PNG 人工检查图
```

TXT Writer 和 SMB Writer 使用同一个 `M3DC1ModelSpec`，以保持 geometric vertices、edges、loop、face 和分类标签一致。

---

## 6. Python 模块导读

### `src/linkmesh/cli.py`

- **输入**：命令行参数。
- **职责**：调用配置合并，编排 Reader、Mesher、Writer 和 Plotter。
- **输出**：按目标生成 HDF5，或生成配套 TXT、SMB 和 PNG。
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
- **职责**：调用 OFT `GEQDSKEquilibrium`，提取 LCFS、第一壁、磁轴和基本平衡信息。
- **输出**：`GFileData`。
- **不负责**：手写 GFile 文本解析、网格生成或文件写出。

### `src/linkmesh/mesher/oft_adapter.py`

- **输入**：`GFileData`、区域策略和网格尺度。
- **职责**：构造 OFT Domain，调用 OFT/TokaMaker/Triangle，并把结果规范化为 `Mesh2D`。
- **输出**：二维非结构化三角网格。
- **不负责**：第二种剖分后端、PUMI 网格生成、TRIMEG/M3D-C1 文件写出或配置文件解析。

当前正式单区域 M3D-C1 路径使用：

```text
profile=single_region
boundary_source=lcfs
```

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

- **输入**：包含有效外边界的 `Mesh2D`。
- **职责**：写出 TRIMEG 标准 HDF5 静态网格。
- **输出**：TRIMEG MATLAB 消费端可读取的 HDF5。
- **不负责**：生成网格、推断区域物理含义或修改输入对象。

字段级 HDF5 数据集、shape、dtype 和索引规则请直接查阅当前技术蓝图，不在本导读重复。

### `src/linkmesh/utils/plotter.py`

- **输入**：`GFileData` 和 `Mesh2D`。
- **职责**：绘制 LCFS、第一壁、磁轴、三角网格和可选区域着色。
- **输出**：PNG 人工检查图。
- **不负责**：修改网格、判断 SMB 是否可被 M3D-C1 消费或替代数值验收。

---

## 7. 原生 helper：源码与编译产物

原生 helper 的正式源码目录是：

```text
native/m3dc1_smb_helper/
├── CMakeLists.txt
└── main.cc
```

两者的关系是：

```text
main.cc + CMakeLists.txt
  → 在具有相容 SCOREC/PUMI 和 MPI 的环境中编译
  → linkmesh-m3dc1-smb-helper 可执行文件
  → 运行时由 Python smb_writer.py 调用
  → PUMI writeNative()
  → rank-0 native SMB
```

需要明确区分：

1. `main.cc` 是 helper 的 C++ 源码。
2. `CMakeLists.txt` 是构建规则。
3. 编译后产生的 `linkmesh-m3dc1-smb-helper` 是运行时可执行文件。
4. 源码和可执行文件不是两个不同的 helper，而是同一组件的源代码与构建结果。
5. helper 是 LinkMesh M3D-C1 输出链的正式组成部分，不是临时 probe。
6. helper 不重新剖分网格；它只根据 Python 提供的节点、连接关系、几何模型和分类信息构造 APF/MDS 网格，并调用 SCOREC/PUMI 官方接口写出 native SMB。
7. 常见 `build/` 目录只是 CMake 生成的构建产物目录，不是正式源码，不应作为 Git 源码提交。
8. 普通用户不需要理解内部交换文件；该内容仅属于 Python Writer 与 helper 的内部实现契约。

当前仓库尚未完成让所有用户在任意目录无条件调用 helper 的统一安装。运行时仍需保证：

- LinkMesh Python 包能被当前 Python/Conda 环境找到；
- 正确版本的 OFT 可用；
- 编译后的 helper 可由 SMB Writer 按正式定位规则找到；
- helper 所依赖的 SCOREC/PUMI 与 MPI 环境相容。

helper 的构建依赖、目标 PUMI 版本和定位优先级请查阅当前技术蓝图。

---

## 8. 测试与证据导读

测试目录按模块组织，主要覆盖：

| 测试文件 | 主要关注内容 |
|---|---|
| `tests/test_gfile_reader.py` | GFile Reader 字段提取、LCFS 后处理和薄 Adapter 边界。 |
| `tests/test_mesh.py` | `Mesh2D` 数据对象及有序外边界验证。 |
| `tests/test_oft_adapter.py` | OFT Adapter 输出转换、区域校验、策略分派和外边界传递。 |
| `tests/test_hdf5_writer.py` | TRIMEG HDF5 写出、拓扑边界和非法输入拒绝。 |
| `tests/test_m3dc1_model_writer.py` | M3D-C1 ModelSpec 与 TXT model 序列化契约。 |
| `tests/test_smb_writer.py` | Python SMB Writer 输入校验、helper 调用边界和输出确认。 |

测试文件只能说明测试意图和覆盖范围。某个测试文件存在，不等于它已在当前环境运行通过；正式测试结果应查阅 `History.md` 和当前技术蓝图。

当前记录需要保留以下边界：

- 真实 DIII-D GFile 的单区域 M3D-C1 CLI 最小闭环已经成功。
- TXT、rank-0 SMB 和 PNG 已实际生成。
- PNG 已由 User 人工检查通过。
- 最近记录的服务器配置与 CLI 专项测试仍有两项旧预期不一致，不能表述为“自动测试全部通过”。
- 其中一项旧测试对未开放组合的异常类型预期过时；另一项仍期待 TRIMEG target 调用 SMB Writer，与当前 target 分派不一致。
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
native/m3dc1_smb_helper/
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
7. 阅读 `native/m3dc1_smb_helper/main.cc` 和对应 `CMakeLists.txt`，理解 Python 与 SCOREC/PUMI 的边界。
8. 最后按需要查阅 `History.md`、测试文件、TRIMEG 参考资料以及外部只读源码。

如果只想运行 LinkMesh，不需要先阅读 helper 的内部交换契约或 PUMI 生命周期细节。

---

## 11. 普通用户最短使用路径

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

进入 Case 后运行：

```bash
python -m linkmesh --config linkmesh.in
```

其中：

- `--config` 后面是该 Case 的配置文件路径；
- LinkMesh 按配置读取 GFile；
- 配置决定目标、区域策略、网格尺度以及 TXT、SMB、PNG 输出路径。

临时生成更细的单区域网格：

```bash
python -m linkmesh --config linkmesh.in --plasma-dx 0.05
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

## 12. Case 100/101/200 系列管理建议

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

## 13. 生成网格与提交作业

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

## 14. 当前能力边界

### 当前可用

- 通过 OFT 读取 GFile/EQDSK；
- 以 LCFS 为边界生成单区域二维三角网格；
- 生成统一 `Mesh2D`；
- 生成 single-loop、single-face M3D-C1 analytic model；
- 写出配套 TXT；
- 通过 SCOREC/PUMI helper 写出串行 rank-0 native SMB；
- 生成 PNG 人工检查图；
- 写出 TRIMEG HDF5；
- 通过配置文件和显式 CLI 参数编排当前已开放流程。

### 当前未开放

- M3D-C1 多区域；
- 多 geometric face；
- 三维网格；
- 环向切分；
- MPI 并行分区；
- `part*.smb` 或 `split_smb` 替代实现；
- M3D-C1 消费端；
- SMB loader 或 validator；
- 通用边界插件系统；
- Simmetrix、`.smd` 或 `.sms` 正式依赖。

多区域、三维和并行分区不能从当前单区域闭环外推为已经支持。

---

## 15. 下一步

当前真正有意义的短期工作是：

1. 等待同门完成配套 TXT+SMB 的真实 M3D-C1/SCOREC 外部消费并反馈结果。
2. 根据外部消费证据判断是否需要最小兼容性修正，不建设 LinkMesh 自有 loader 或 validator。
3. 在消费契约稳定后整理标准 `linkmesh.in` 配置模板和简明用户说明。
4. 建立无需 `sudo` 的个人 Conda 用户级安装，使 Python 包和 native helper 一起进入用户环境。
5. 清理开发阶段构建目录和命名，明确源码、构建产物与 Case 产物边界。
6. 工具稳定后再评估服务器统一安装。

遇到问题时：

| 问题 | 查证位置 |
|---|---|
| 正式接口、字段或格式是什么 | `LinkMesh_Architecture_Plan.md` |
| 某项功能是否实际验收过 | `History.md` |
| 当前 CLI 如何编排 | `src/linkmesh/cli.py` |
| 配置如何合并和限制组合 | `src/linkmesh/config.py` |
| `Mesh2D` 保存什么 | `src/linkmesh/mesh.py` |
| TXT 与 SMB 如何共享模型 | `src/linkmesh/m3dc1_model.py` |
| helper 源码在哪里 | `native/m3dc1_smb_helper/` |
| 日常 Case 如何组织 | `docs/linkmesh/plan.md` |
| TRIMEG 消费契约依据 | `docs/trimeg/` |
| OFT 或 M3D-C1 外部实现如何工作 | `TOKAMAKER/`、`M3DC1/`，仅限只读查证 |

---

## 16. 本文档的边界

本导读只回答“项目里有什么、如何找到、如何运行、当前做到哪里”。

它不重复以下内容：

- `Mesh2D` 字段级正式契约；
- TRIMEG HDF5 全部数据集布局；
- Python/C++ 内部交换文件字节结构；
- PUMI/APF/MDS 生命周期细节；
- 所有测试条目和运行计数；
- 多区域或未来功能设计。

这些内容分别由当前技术蓝图、业务源码、测试和历史归档承载。若本导读与它们不一致，应修正本导读，而不是用本导读改变项目技术事实。
