# M3DC1 全景宏观架构与数据流白皮书

- 文档主受众：LinkMesh 开发团队
- 知识库用途：侦察证据
- 文档状态：当前有效
- 最高依据：当前仓库的 CONTEXT.md (LinkMesh 敏捷开发工作流规范)
- 事实边界：本文档是基于 M3DC1 官方说明书、编译指南、教程文档与文件路径索引形成的参考工程白皮书。本文档中的所有底层物理与接口调研情报，在当前阶段【仅服务于 LinkMesh 独立命令行程序具体解析与写入脚本的编写】，不涉及任何通用抽象中间件或插件体系设计。本文档不等价于 M3DC1 完整源码级调用图，不承载 LinkMesh 的正式组件接口定义，也不得替代 `LinkMesh_Architecture_Plan.md` 中关于 LinkMesh 各模块边界的最高技术蓝图。
- 主要用途：帮助 LinkMesh 开发团队理解 M3DC1 作为目标输出格式消费者的工程结构，指导后续只读侦察 M3DC1 网格消费链路，为编写 `writers/smb_writer.py` 和 `writers/hdf5_writer.py` 提供稳定上下文。
- 修改前置条件：如需把本文档中的架构启示转化为 LinkMesh 代码实现，必须先完成对应方案审阅，并同步更新 `LinkMesh_Architecture_Plan.md`。
- 验收标准：本文档必须明确区分已确认事实、文件结构证据、架构推断和待源码确认事项；不得诱导修改 M3DC1 官方源码，不得把 M3DC1 私有语义写入 LinkMesh 的通用读写模块。

## 0. 文档定位、依据范围与使用边界

#### 本节摘要

本文档是 LinkMesh 项目中面向 M3DC1 参考工程的白皮书。它服务于 LinkMesh 开发团队：通过它建立 M3DC1 的宏观架构认知，约束后续只读源码侦察路径，并为编写 `writers/smb_writer.py` 提供 M3DC1 网格消费链路的上下文。本文档的证据基础来自 M3DC1 官方说明书、编译指南、教程文档和文件路径索引，不等价于完整源码级调用图。凡涉及 LinkMesh 的正式接口、目录职责、模块边界，必须以 `LinkMesh_Architecture_Plan.md` 为最高依据。

#### 依据范围

本文档依据以下材料形成：

| 证据来源 | 事实层级 | 在本文档中的用途 |
|---|---|---|
| `M3DC1/m3d_c1_mhd_simulation_code_intro.md` | 官方说明书级事实 | 确认 M3DC1 的物理模型、数值方法、时间推进、有限元特征和求解器生态。 |
| `M3DC1/M3D-C1 Compilation Guide.md` | 官方编译流程事实 | 确认 M3DC1 与 `m3dc1_scorec`、PETSc、SCOREC/PUMI 等依赖之间的工程关系。 |
| `M3DC1/M3D-C1 Tutorials.md` | 官方教程级事实 | 确认典型输入文件、任务流程、网格适配流程和输出诊断方式。 |
| `docs/m3dc1/m3dc1_reference_map.txt` | 文件路径索引证据 | 辅助定位 M3DC1 目录结构、skeleton 主程序骨架、`m3dc1_scorec` 网格相关模块和有限元装配相关文件。 |

#### 事实边界

- 【已确认】M3DC1 是面向磁约束聚变等离子体的高阶有限元 MHD 模拟程序，使用隐式或半隐式时间推进、Krylov 线性求解、PETSc 生态和 SCOREC/PUMI 网格基础设施。
- 【已确认】`m3dc1_scorec` 是 M3DC1 中与并行非结构网格、几何模型、场变量、矩阵接口、线性系统、网格适配和解转移密切相关的 C++ 支撑库。
- 【已确认】M3DC1 使用极向面非结构三角网格，与 LinkMesh P0 目标（二维三角网格）直接对应。
- 【已确认】M3DC1 的 C1 有限元使用 reduced quintic 三角单元，每个节点有 12 个自由度，这对 LinkMesh `writers/smb_writer.py` 的高阶节点处理有直接影响。
- 【已确认】M3DC1 使用多区域模型（plasma/vacuum/resistive wall），LinkMesh 必须在输出文件中正确写入区域标记。
- 【文件结构证据】文件路径索引显示存在 `skeleton` 主控骨架、`m3dc1_scorec` API、mesh、model、field、matrix、ls、adapt、sizeField 和 slnTransfer 等模块。
- 【待源码确认】`.smb` 二进制文件的精确字节流格式，仍需通过只读侦察 `m3dc1_mesh.cc` 和 PUMI 源码逆向推导。
- 【禁止误用】本文档不得被当成 M3DC1 官方源码修改方案，不得诱导修改 `M3DC1/` 目录下任何文件。

## 1. M3DC1 总体定位：高阶有限元隐式 MHD 大型模拟程序

#### 本节摘要

M3D-C1 是面向磁约束聚变等离子体的大型高阶有限元 MHD 模拟程序。对 LinkMesh 来说，M3DC1 的价值在于提供一个真实的目标网格消费者：LinkMesh 的 `writers/smb_writer.py` 必须输出能被 M3DC1 的 `pumi_mesh_load` 顺畅读取的 `.smb` 静态二进制网格文件，内含顶点坐标、三角连接索引及 MultiRegion 逻辑区域标注。

M3D-C1 的核心特征可以概括为：

| 维度 | M3DC1 的技术选择 | 对 LinkMesh Writer 的影响 |
|---|---|---|
| 物理模型 | 非线性 MHD、双流体扩展、自由边界、多区域模型 | Writer 必须正确写入 plasma/vacuum/wall 区域标记。 |
| 空间离散 | 高阶 C1 有限元（reduced quintic 三角单元，12 DOF/节点） | Writer 可能需要生成边中点（高阶节点）。 |
| 几何网格 | 极向面非结构三角网格 | Writer 输出二维三角网格，与 LinkMesh P0 目标一致。 |
| 时间推进 | 隐式或半隐式时间推进 | 对 LinkMesh 静态网格输出无直接影响。 |
| 网格生态 | SCOREC/PUMI、并行网格适配 | Writer 必须按 PUMI `.smb` 二进制协议写出。 |

## 2. M3DC1 的 C1 有限元与网格需求

#### 本节摘要

M3DC1 使用 C1 连续的 reduced quintic 三角单元，每个节点存储 12 个自由度（函数值、一阶导数、二阶导数的组合）。这意味着 LinkMesh 生成的网格不仅需要提供三角形的三个顶点坐标，还可能需要提供边中点坐标（高阶节点）。这是 Triangle 输出与 M3DC1 输入之间最关键的潜在缺口（缺口 G1）。

### 2.1 C1 有限元的物理意义

C1 连续性意味着：
- 场变量（如磁通 psi、速度势 U）在单元边界处连续；
- 场变量的一阶导数（如磁场分量 B_R, B_Z）在单元边界处也连续；
- 这对于计算电流密度 J = ∇×B 等需要高阶导数的物理量至关重要。

### 2.2 12 DOF 节点的含义

根据 M3DC1 官方说明书（Jardin et al. 2012），每个节点的 12 个自由度包括：

```text
对于标量场 u(R, Z)，每个节点存储：
  u          函数值
  ∂u/∂R      R 方向一阶导数
  ∂u/∂Z      Z 方向一阶导数
  ∂²u/∂R²   R 方向二阶导数（部分实现）
  ∂²u/∂R∂Z  混合二阶导数（部分实现）
  ∂²u/∂Z²   Z 方向二阶导数（部分实现）
```

具体的 12 DOF 定义需要通过只读侦察 `c1_12_element.F90` 确认。

### 2.3 对 LinkMesh smb_writer 的影响

【待源码确认】：需要通过侦察 `m3dc1_field.cc` 确认：
1. M3DC1 是否在读取 `.smb` 文件后自行生成边中点，还是要求 `.smb` 文件中已包含边中点；
2. 如果需要边中点，LinkMesh `writers/smb_writer.py` 需要在写出前对每条三角形边生成中点坐标。

## 3. 主控流与主循环

#### 本节摘要

M3DC1 的用户入口表现为运行编译后的 `m3dc1` 可执行程序，并通过 `C1input.*` 输入文件选择不同任务。文件路径索引显示，M3DC1 在 `skeleton` 目录下包含多个 Fortran 主程序骨架。

### 3.1 主程序入口候选

根据文件路径索引，M3DC1 的 Fortran 主程序入口骨架主要出现在以下位置：

| 候选入口文件 | 所属目录 | 已确认意义 |
|---|---|---|
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/main.F90` | OpenMP skeleton | 反映 CPU/OpenMP 版本主控骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90` | OpenACC skeleton | 反映 GPU/OpenACC 版本主控骨架。 |

当前可确认的结论是：M3DC1 的生产主控由 Fortran 侧驱动，`m3dc1_scorec` 是 C++ 网格、几何、适配和线性代数支撑库，不是顶层物理时间推进入口。

### 3.2 教程级任务流

M3DC1 教程展示了通过不同输入文件驱动不同任务流程：

| 教程阶段 | 输入文件示例 | 物理或数值任务 |
|---|---|---|
| EFIT 插值 | `C1input.interpolate` | 将 EFIT 平衡数据插值到 M3DC1 网格。 |
| 平衡修正 | `C1input.refine` | 使用 Grad-Shafranov 求解器修正平衡。 |
| 网格自适应 | `C1input.adapt` | 根据物理场或误差指标触发网格适配。 |
| 新网格验证 | `C1input.test` | 检查适配后网格与平衡兼容性。 |

### 3.3 主时间推进抽象流程

```text
读取输入参数、网格（*.smb）、几何模型（*.txt）与物理配置（C1input.*）
        ↓
m3dc1_scorec 读取或绑定网格与几何模型
        ↓
建立区域标记（plasma/vacuum/wall）、边界标记和网格实体拓扑
        ↓
初始化有限元场变量（U, omega, chi, psi, f）
        ↓
EFIT / profile / coil 数据插值到网格场
        ↓
进入时间步循环或线性响应任务
        ↓
执行有限元弱形式积分与矩阵装配
        ↓
调用 Krylov 线性求解器（PETSc KSP）
        ↓
更新 MHD 场变量
        ↓
输出诊断（C1.h5）、网格状态（mesh0.smb）
```

## 4. `m3dc1_scorec` 的战略生态位

#### 本节摘要

`m3dc1_scorec` 不是 M3DC1 的顶层物理主程序，而是 M3DC1 与 SCOREC/PUMI 并行非结构网格生态之间的关键支撑库。对 LinkMesh 来说，`m3dc1_scorec` 是理解 M3DC1 如何实际消费网格的第一优先级入口，也是逆向推导 `.smb` 二进制格式的核心侦察对象。

### 4.1 层级关系

```text
M3DC1 Fortran 物理主程序
        ↓ 调用或链接
m3dc1_scorec C++ 网格与有限元基础库
        ↓ 依赖
PUMI / SCOREC / Zoltan / PETSc 等第三方 HPC 库
```

### 4.2 内部模块结构

根据文件路径索引，`m3dc1_scorec` 可被初步划分为以下模块：

| 子模块 | 代表文件 | 白皮书级职责 | 对 LinkMesh 的价值 |
|---|---|---|---|
| API 层 | `api/m3dc1_scorec.h`、`api/m3dc1_scorec.cc` | 对外暴露 C/C++ 或 Fortran 可调用接口。 | 确认 `pumi_mesh_load` 等函数的调用约定。 |
| 网格模块 | `include/m3dc1_mesh.h`、`src/m3dc1_mesh.cc` | 网格读取、实体遍历、拓扑连接。 | 逆向推导 `.smb` 二进制格式，指导 `writers/smb_writer.py`。 |
| 几何模型模块 | `include/m3dc1_model.h`、`src/m3dc1_model.cc` | 几何模型、区域、边界语义。 | 确认 model `.txt` 文件格式，指导 `writers/model_writer.py`。 |
| 实体模块 | `src/m3dc1_entity.cc` | 顶点、边、面、单元等实体操作。 | 理解 PUMI 实体句柄结构。 |
| 场模块 | `include/m3dc1_field.h`、`src/m3dc1_field.cc` | 有限元场变量存储与访问。 | 确认高阶节点需求，决定 `writers/smb_writer.py` 是否需要生成边中点。 |
| 矩阵模块 | `include/m3dc1_matrix.h`、`src/m3dc1_matrix.cc` | 全局矩阵接口与装配支撑。 | 理解 M3DC1 对网格质量的隐式要求。 |
| 线性系统模块 | `include/m3dc1_ls.h`、`src/m3dc1_ls.cc` | 线性系统与求解器接口。 | 对 LinkMesh 静态网格输出无直接影响。 |

### 4.3 初始化阶段数据流

```text
用户准备输入
│
├── first_wall.pts          ← LinkMesh 可从 GFile 提取第一壁坐标
├── geqdsk                  ← LinkMesh readers/gfile_reader.py 读取
├── coil.dat / current.dat  ← 非 LinkMesh 职责
├── profile_ne / profile_te ← 非 LinkMesh 职责
├── mesh *.smb              ← LinkMesh writers/smb_writer.py 生成
├── model *.txt             ← LinkMesh writers/smb_writer.py 配套生成
└── C1input.*               ← 非 LinkMesh 职责
        ↓
M3DC1 主程序读取输入参数
        ↓
m3dc1_scorec 读取或绑定网格与几何模型
        ↓
建立区域标记、边界标记和网格实体拓扑
        ↓
初始化有限元场变量
```

`.smb` 与 `.txt` 是 LinkMesh 必须生成的两个关键输出文件。

### 4.4 弱形式矩阵组装阶段数据流

M3DC1 的弱形式有限元矩阵组装需要 `m3dc1_scorec` 提供以下基础信息：

| 数据类型 | 可能来源模块 | 被消费位置 | 用途 | LinkMesh 是否需要提供 |
|---|---|---|---|---|
| 节点坐标 `(R,Z)` | mesh / entity | element / nintegrate | 几何映射、Jacobian、积分权重。 | 是，写入 `.smb` |
| 单元拓扑连接表 | mesh | element / matdef | 局部自由度编号和局部矩阵生成。 | 是，写入 `.smb` |
| 边界实体标记 | model / mesh | matdef / boundary terms | 施加边界条件、壁、真空和外边界处理。 | 是，写入 `.smb` 和 `.txt` |
| 区域标记 | model / mesh | physics residual | 区分 plasma、vacuum、resistive wall 等区域方程。 | 是，写入 `.smb` 和 `.txt` |
| 场自由度 | field | element / nintegrate | 在积分点重构 `U`、`omega`、`chi`、`psi`、`f` 等变量。 | 否，由 M3DC1 自行初始化 |

## 5. LinkMesh Writer 适配要点

#### 本节摘要

M3DC1 对 LinkMesh 的关键启示是：`writers/smb_writer.py` 不能只是简单地把节点坐标和三角形连接表写成二进制文件，而要能正确表达节点坐标、单元连接、边界实体、区域标记等 M3DC1 消费所需的全部信息。这些 M3DC1 私有语义必须封锁在 `writers/` 模块内，不得污染 `readers/` 或 `mesher/` 模块。

### 5.1 LinkMesh writers/ 模块必须处理的 M3DC1 需求

| M3DC1 需求 | 对应 LinkMesh writers/ 实现要点 | 事实状态 |
|---|---|---|
| 节点坐标 `(R,Z)` | 按 PUMI `.smb` 协议写出二维坐标 | 【待源码确认】`.smb` 字节流格式 |
| 单元拓扑连接表 | 按 PUMI `.smb` 协议写出三角形连接索引 | 【待源码确认】索引约定（0-based vs 1-based） |
| 边界实体标记 | 按 M3DC1 model 层约定写出边界标记整数 ID | 【待源码确认】model `.txt` 格式 |
| 区域标记 | 按 M3DC1 model 层约定写出 plasma/vacuum/wall 区域 ID | 【待源码确认】区域 ID 映射规则 |
| TRIMEG HDF5 格式 | 按卢志鑫老师 TRIMEG 标准写出顶点坐标、三角连接拓扑、边界标注 | 【待源码确认】HDF5 数据集名称和结构 |

### 5.2 必须留在 writers/ 模块的私有语义

| 私有语义类别 | 示例 | 必须封锁位置 |
|---|---|---|
| M3DC1 区域角色语义 | plasma、vacuum、resistive wall 的具体物理解释 | `writers/smb_writer.py` |
| M3DC1 文件格式语义 | `.smb`、model `.txt` 的目标写出规则 | `writers/smb_writer.py` |
| TRIMEG HDF5 格式语义 | 数据集名称、组织结构、数据类型 | `writers/hdf5_writer.py` |

## 6. 后续只读侦察清单

#### 本节摘要

本文档目前已经建立 M3DC1 的宏观架构地图，但尚未完成源码级调用链确认。后续若人类主管要求继续推进，应按照"先宏观、再核心数据结构、最后具体数值语义"的顺序，只读侦察 M3DC1 的主程序、`m3dc1_scorec` API、mesh/model/field 数据链。所有侦察结果必须以文档形式反馈，不得修改 M3DC1 官方源码。

优先侦察清单如下：

| 优先级 | 目标模块 | 需要确认的问题 | 对 LinkMesh 的价值 |
|---|---|---|---|
| P0 | `m3dc1_scorec/api/m3dc1_scorec.*` | Fortran 与 C++ 之间的公开 API 边界是什么。 | 确认 `pumi_mesh_load` 等函数的调用约定。 |
| P0 | `m3dc1_scorec/include/m3dc1_mesh.h` 与 `src/m3dc1_mesh.cc` | M3DC1 如何读取、遍历和查询网格拓扑。 | 逆向推导 `.smb` 二进制格式，指导 `writers/smb_writer.py`。 |
| P0 | `m3dc1_scorec/include/m3dc1_model.h` 与 `src/m3dc1_model.cc` | 区域、边界和几何模型语义如何进入有限元装配。 | 确认 model `.txt` 文件格式，指导 `writers/smb_writer.py` 配套输出。 |
| P1 | `m3dc1_scorec/include/m3dc1_field.h` 与 `src/m3dc1_field.cc` | 场自由度如何存储、访问和回填。 | 确认高阶节点需求，决定 `writers/smb_writer.py` 是否需要生成边中点。 |
| P2 | `fortran/c1_12_element.F90` 与 skeleton 中的 `element.F90`、`nintegrate.F90`、`matdef.F90` | C1 高阶有限元、积分点重构和弱形式装配如何消费 mesh/field 数据。 | 理解 M3DC1 对网格质量的隐式要求。 |

后续只读侦察必须遵守以下纪律：

1. 不修改 `M3DC1/` 目录下任何源码。
2. 不把 M3DC1 私有变量名、区域角色或 PETSc/KSP 配置写入 LinkMesh 的 `readers/` 或 `mesher/` 模块。
3. 先输出源码地图和数据流报告，再讨论是否需要更新 `LinkMesh_Architecture_Plan.md`。
4. 涉及 LinkMesh 实现方案时，必须先更新总蓝图，再进入代码。
5. 对未读源码的内容保持"待确认"标记，不把推断写成已确认事实。

## 7. 总结：M3DC1 对 LinkMesh 的战略意义

#### 本节摘要

M3DC1 是 LinkMesh 的第一个真实目标输出消费者。M3DC1 的高阶 C1 有限元、多区域物理语义、隐式矩阵装配、Krylov 求解和网格适配流程，证明 LinkMesh 的 `writers/smb_writer.py` 不能被设计成简单的二进制序列化脚本。LinkMesh 应通过 `writers/` 模块封装 M3DC1 私有语义，并通过 `utils/plotter.py` 提供可视化自检能力。

```text
M3DC1 要求 LinkMesh 理解的不只是"网格文件"，
而是"带几何拓扑、区域边界语义、高阶自由度、适配元数据和求解器约束的网格消费链"。

LinkMesh 的正确架构回应不是把 M3DC1 私有语义写入 readers/ 或 mesher/，
而是在 writers/smb_writer.py 中消化 M3DC1 私有语义，
并用 utils/plotter.py 提供可检查的可视化自检闭环。
```

对后续工程推进而言，最重要的红线是：

1. M3DC1 是真实验证对象，但不能反向定义 LinkMesh 的 `readers/` 或 `mesher/` 模块。
2. `m3dc1_scorec` 是优先只读侦察对象，但其私有概念不得直接写入 LinkMesh 的通用读写模块。
3. M3DC1 的区域语义、场变量语义、文件格式语义和求解器配置必须封锁在 `writers/smb_writer.py`。
4. 任何 M3DC1 适配设计都必须先进入 `LinkMesh_Architecture_Plan.md`，再进入代码实现。
5. 外部 M3DC1 官方源码始终是只读参考库，不得由 LinkMesh 开发团队直接修改。
