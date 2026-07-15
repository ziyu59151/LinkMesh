# M3DC1 全景宏观架构与数据流白皮书

- 文档主受众：Hybrid-Control
- 知识库用途：侦察证据
- 文档状态：当前有效
- 最高依据：UniMesh_Architecture_Plan.md
- 事实边界：本文档是基于 M3DC1 官方说明书、编译指南、教程文档与文件路径索引形成的参考工程白皮书和阶段性架构控制文档。本文档用于解释 M3DC1 的宏观架构、数据流、网格生态位与 UniMesh 适配启示；本文档不等价于 M3DC1 完整源码级调用图，不承载 UniMesh 的正式组件接口定义，也不得替代 `UniMesh_Architecture_Plan.md` 中关于 UniMesh 核心层、生成层和驱动层边界的最高技术蓝图。
- 主要用途：帮助人类主管理解 M3DC1 作为第一个真实下游验证对象的工程结构，指导 Aider 后续只读侦察 M3DC1 网格消费链路，并为场外架构师通过知识库召回 M3DC1 与 UniMesh 适配关系提供稳定上下文。
- 场外架构师检索用途：当场外架构师需要判断 M3DC1 在 UniMesh 项目中的定位、M3DC1 对网格拓扑与高阶有限元元数据的需求、`m3dc1_scorec` 的战略生态位、以及哪些内容属于已确认说明书事实或待源码确认事项时，应优先召回本文档。
- Aider 执行用途：后续 Aider 对 M3DC1 进行源码侦察或驱动层方案设计时，必须把本文档作为宏观地图使用；任何具体接口、目录职责、公共数据结构和驱动层实现方案仍必须回到 `UniMesh_Architecture_Plan.md` 对齐。
- 修改前置条件：如需把本文档中的架构启示转化为 UniMesh 代码实现，必须先完成对应方案审阅，并同步更新 `UniMesh_Architecture_Plan.md`。
- 验收标准：本文档必须保持 Hybrid-Control 结构，明确区分已确认事实、文件结构证据、架构推断和待源码确认事项；不得诱导修改 M3DC1 官方源码，不得把 M3DC1 私有语义上浮到 UniMesh 核心层。

## 0. 文档定位、依据范围与使用边界

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 文档定位、依据范围与使用边界  
> **Aider 执行用途**：约束 Aider 在后续 M3DC1 侦察中只能把本文档作为宏观地图，不得把说明书级归纳直接当作源码级事实。  
> **人类阅读用途**：帮助人类主管理解本文档为什么存在、依据什么材料、能回答什么问题、不能被如何误用。  
> **场外架构师检索用途**：帮助场外架构师快速判断本文档的事实等级、证据来源和与 UniMesh 总蓝图之间的关系。  
> **触发问题**：M3DC1 白皮书依据什么材料？本文档是源码事实还是架构导读？本文档能否替代 UniMesh 总蓝图？  
> **事实状态**：已确认事实与解释性说明并存；源码级调用链仍待后续只读侦察确认。  
> **使用限制**：不得将本文档中的架构解释直接改写为 UniMesh 已实现功能；不得据此修改 M3DC1 官方源码。

#### 本节摘要

本文档是 UniMesh 项目中面向 M3DC1 参考工程的 Hybrid-Control 白皮书。它同时服务三类对象：人类主管通过它建立 M3DC1 的宏观架构认知，Aider 通过它约束后续只读源码侦察路径，场外架构师通过它在 RAG 检索中恢复 M3DC1 与 UniMesh 之间的适配上下文。本文档的证据基础来自 M3DC1 官方说明书、编译指南、教程文档和文件路径索引，不等价于完整源码级调用图。凡涉及 UniMesh 的正式接口、目录职责、核心层允许或禁止概念、驱动层实现细则，必须以 `UniMesh_Architecture_Plan.md` 为最高依据。

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
- 【文件结构证据】文件路径索引显示存在 `skeleton` 主控骨架、`m3dc1_scorec` API、mesh、model、field、matrix、ls、adapt、sizeField 和 slnTransfer 等模块。
- 【待源码确认】主时间推进、Newton-Krylov 非线性控制、矩阵装配和 `m3dc1_scorec` API 之间的精确函数调用链，仍需后续只读阅读完整源码确认。
- 【禁止误用】本文档不得被当成 M3DC1 官方源码修改方案，不得诱导 Aider 修改 `M3DC1/` 目录下任何文件。

## 1. M3DC1 总体定位：高阶有限元隐式 MHD 大型模拟程序

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / M3DC1 总体定位  
> **Aider 执行用途**：为后续侦察建立 M3DC1 的物理模型、数值方法和软件生态坐标，避免把 M3DC1 简化为普通网格格式消费者。  
> **人类阅读用途**：帮助人类主管快速把握 M3DC1 是什么类型的软件，以及为什么它对网格适配层提出高阶要求。  
> **场外架构师检索用途**：召回 M3DC1 的物理目标、有限元特征、并行依赖和对 UniMesh 的战略压力。  
> **触发问题**：M3DC1 是什么？M3DC1 为什么不是普通网格消费者？M3DC1 对 UniMesh 有什么高阶约束？  
> **事实状态**：官方说明书级已确认事实与面向 UniMesh 的解释性说明。  
> **使用限制**：不得把本节解释性说明视为 UniMesh 核心层接口定义。

#### 本节摘要

M3D-C1 是面向磁约束聚变等离子体的大型高阶有限元 MHD 模拟程序。它同时涉及复杂物理模型、高阶 C1 有限元、隐式或半隐式时间推进、Krylov 线性求解和并行非结构网格基础设施。对 UniMesh 来说，M3DC1 的价值不在于提供一个简单文件格式目标，而在于提供一个真实、高强度、带物理语义和求解器约束的下游验证对象。UniMesh 必须通过驱动层吸收 M3DC1 私有语义，同时保持核心层中立。

M3D-C1 的核心特征可以概括为：

| 维度 | M3DC1 的技术选择 | 数值或物理意义 |
|---|---|---|
| 物理模型 | 非线性 MHD、双流体扩展、自由边界、多区域模型 | 支持等离子体区、真空区、阻性壁区等复杂磁约束聚变问题。 |
| 空间离散 | 高阶 C1 有限元 | 使场变量及一阶导数具备连续性，适合电流、磁场、压力梯度和高阶算子计算。 |
| 几何网格 | 极向面非结构三角网格与环向结构化方向结合 | 兼顾托卡马克截面几何适应性和环向方向数值结构。 |
| 时间推进 | 隐式或半隐式时间推进 | 缓解快 MHD 波导致的显式 CFL 限制。 |
| 线性代数 | Krylov 迭代、PETSc、MUMPS 或 SuperLU_DIST | 支撑大规模稀疏线性系统求解。 |
| 网格生态 | SCOREC/PUMI、Zoltan、并行网格适配 | 支持并行非结构网格、重分区、适配和解转移。 |

从 UniMesh 的角度看，M3DC1 不是单纯的“读取节点和三角形”的程序。M3DC1 消费的是带有区域语义、边界语义、高阶自由度布局、几何拓扑一致性和并行分区信息的数值网格对象。错误的边界标记、区域标记或自由度布局可能直接影响有限元弱形式装配、矩阵结构、预条件器行为和非线性收敛。

## 2. 主控流与主循环：说明书级事实与待确认调用链

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 主控流与主循环  
> **Aider 执行用途**：提示后续源码侦察应优先定位 Fortran 主程序、时间推进控制层、矩阵装配层与 PETSc/Krylov 调用边界。  
> **人类阅读用途**：帮助人类主管理解 M3DC1 从输入、初始化、有限元装配到求解器更新的宏观执行流程。  
> **场外架构师检索用途**：召回 M3DC1 主程序入口候选、时间推进逻辑和 Newton-Krylov 待确认边界。  
> **触发问题**：M3DC1 主程序入口在哪里？时间推进在哪里？Newton-Krylov 总控函数是否已确认？  
> **事实状态**：文件结构证据已确认主控骨架位置；精确生产版调用链待源码确认。  
> **使用限制**：不得把 skeleton 文件路径直接断言为完整生产版唯一入口；不得把本文档抽象流程当成源码函数调用图。

#### 本节摘要

M3DC1 的用户入口表现为运行编译后的 `m3dc1` 可执行程序，并通过 `C1input.*` 输入文件选择不同任务。文件路径索引显示，M3DC1 在 `skeleton` 目录下包含多个 Fortran 主程序骨架和 OpenMP/OpenACC 变体，这些文件反映了主控组织方式。说明书能够确认 M3DC1 使用隐式或半隐式时间推进和 Krylov 线性求解，但尚不能仅凭说明书确认 Newton-Krylov 总控函数的精确源码位置。后续 Aider 只读侦察应围绕主程序、时间推进、矩阵装配和 PETSc/KSP 接口建立更细的调用链地图。

### 2.1 主程序入口候选

根据文件路径索引，M3DC1 的 Fortran 主程序入口骨架主要出现在以下位置：

| 候选入口文件 | 所属目录 | 已确认意义 |
|---|---|---|
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/main.F90` | OpenMP skeleton | 反映 CPU/OpenMP 版本主控骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/main_omp.F90` | OpenMP skeleton | 反映 OpenMP 主控变体。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90` | OpenACC skeleton | 反映 GPU/OpenACC 版本主控骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main_acc.F90` | OpenACC skeleton | 反映 OpenACC 主控变体。 |

当前可确认的结论是：M3DC1 的生产主控由 Fortran 侧驱动，`m3dc1_scorec` 是 C++ 网格、几何、适配和线性代数支撑库，不是顶层物理时间推进入口。

### 2.2 教程级任务流

M3DC1 教程展示了通过不同输入文件驱动不同任务流程：

| 教程阶段 | 输入文件示例 | 物理或数值任务 |
|---|---|---|
| EFIT 插值 | `C1input.interpolate` | 将 EFIT 平衡数据插值到 M3DC1 网格。 |
| 平衡修正 | `C1input.refine` | 使用 Grad-Shafranov 求解器修正平衡。 |
| 网格自适应 | `C1input.adapt` | 根据物理场或误差指标触发网格适配。 |
| 新网格验证 | `C1input.test` | 检查适配后网格与平衡兼容性。 |
| 线性稳定性 | 线性稳定性算例输入 | 求解线性扰动增长率与本征函数。 |
| 线性 RMP 响应 | RMP 算例输入 | 计算非轴对称外场响应。 |

### 2.3 主时间推进抽象流程

说明书级别能够确认的主时间推进抽象如下：

```text
读取输入参数、网格、几何模型与物理配置
        ↓
初始化物理场、平衡、边界条件和区域标记
        ↓
进入时间步循环或线性响应任务
        ↓
构造非线性残量或半隐式线性化算子
        ↓
执行有限元弱形式积分与矩阵装配
        ↓
调用 Krylov 线性求解器与预条件器
        ↓
更新 MHD 场变量
        ↓
输出诊断、HDF5 数据、网格状态或适配结果
        ↓
必要时触发网格适配、重分区或解转移
```

该流程是说明书级架构抽象，不是源码函数调用图。后续需要通过只读源码侦察确认具体函数、模块和调用顺序。

### 2.4 Newton-Krylov 与线性代数待确认边界

说明书可以确认 M3DC1 使用 Krylov 方法和 PETSc 生态，但没有在当前证据范围内明确给出 Newton-Krylov 总控函数的精确位置。文件结构上，与矩阵装配和线性系统强相关的候选文件包括：

| 文件 | 文件结构层面的推断职责 | 事实边界 |
|---|---|---|
| `M3DC1/m3dc1_scorec/include/m3dc1_matrix.h` | C++ 侧矩阵接口声明 | 文件名与模块命名证据；具体 API 待源码阅读。 |
| `M3DC1/m3dc1_scorec/src/m3dc1_matrix.cc` | C++ 侧矩阵实现 | 文件名与模块命名证据；具体装配边界待确认。 |
| `M3DC1/m3dc1_scorec/include/m3dc1_ls.h` | 线性系统接口声明 | `ls` 可理解为 linear system；具体求解器调用待确认。 |
| `M3DC1/m3dc1_scorec/src/m3dc1_ls.cc` | 线性系统实现 | 可能与 PETSc/Krylov 对接；需源码确认。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/matdef.F90` | Fortran 矩阵定义或物理项装配骨架 | 文件名证据；具体物理项需源码确认。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/nintegrate.F90` | 数值积分或弱形式积分骨架 | 文件名证据；具体积分流程需源码确认。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/element.F90` | 单元级有限元计算骨架 | 文件名证据；具体单元自由度布局需源码确认。 |

## 3. 核心物理与数值模块划分

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 核心物理与数值模块划分  
> **Aider 执行用途**：为后续源码侦察建立模块清单，避免只盯住网格文件格式而忽略平衡、物理场、有限元、矩阵和求解器耦合。  
> **人类阅读用途**：用结构化方式帮助人类主管理解 M3DC1 的核心模块如何协同。  
> **场外架构师检索用途**：召回 M3DC1 物理模块、有限元模块、网格模块和求解器模块之间的关系。  
> **触发问题**：M3DC1 包含哪些核心模块？网格模块和物理模块如何耦合？  
> **事实状态**：说明书级事实、文件结构证据与架构解释并存。  
> **使用限制**：模块划分是白皮书级架构归纳，不应被当作完整源码包层级定义。

#### 本节摘要

M3DC1 可以从软件架构上划分为输入与任务控制、平衡与初始条件、高阶 MHD 物理场、C1 有限元、网格与几何拓扑、弱形式积分与矩阵装配、线性求解、网格适配与解转移、输出诊断等模块。对 UniMesh 最关键的是：网格模块不是孤立存在的，它服务于高阶有限元、区域方程选择、边界条件施加、矩阵稀疏结构和解转移流程。UniMesh 驱动层适配 M3DC1 时，必须把这些耦合关系作为输入约束，而不是只输出裸节点表和三角形表。

### 3.1 顶层模块图

```text
M3DC1 顶层物理模拟程序
│
├── 输入与任务控制模块
│   ├── C1input.*
│   ├── batchjob.*
│   └── interpolate / refine / adapt / test / linear / RMP 等任务流
│
├── 平衡与初始条件模块
│   ├── EFIT geqdsk 读取与插值
│   ├── Grad-Shafranov 平衡修正
│   ├── kinetic profiles 读取
│   └── coil / wall / region 几何定义
│
├── 高阶有限元物理场模块
│   ├── C1 标量场表示
│   ├── 速度势变量 U, omega, chi
│   ├── 磁通或矢势变量 psi, f
│   └── 压力、密度、温度、电流等派生场
│
├── 网格与几何拓扑模块：m3dc1_scorec
│   ├── mesh
│   ├── model
│   ├── entity
│   ├── field
│   ├── matrix
│   ├── ls
│   ├── sizeField
│   └── slnTransfer
│
├── 弱形式积分与矩阵装配模块
│   ├── element
│   ├── explicit_element
│   ├── nintegrate
│   ├── matdef
│   └── matrix
│
├── 非线性与线性求解模块
│   ├── PETSc KSP
│   ├── Krylov / GMRES
│   ├── block-Jacobi 预条件
│   └── MUMPS / SuperLU_DIST 块求解
│
├── 网格自适应与解转移模块
│   ├── adapt
│   ├── sizeField
│   ├── slnTransfer
│   └── collapse / partition mesh
│
└── 输出与后处理模块
    ├── C1.h5
    ├── mesh0.smb
    ├── ts0-adapted*.smb
    └── IDL plot_field / plot_mesh / plot_scalar / plot_br
```

### 3.2 平衡模块

M3DC1 教程展示的典型平衡准备流程包括 EFIT 数据读取、线圈与电流输入、动理学剖面读取、网格插值、Grad-Shafranov 平衡修正和后处理验证。

| 阶段 | 输入或输出 | 作用 |
|---|---|---|
| 读取 EFIT | `geqdsk` | 提供实验平衡磁通、边界和剖面信息。 |
| 线圈定义 | `coil.dat`、`current.dat` | 定义外部线圈几何和电流。 |
| 动理学剖面 | `profile_ne`、`profile_te`、`profile_omega` | 提供密度、温度和旋转等径向剖面。 |
| 网格插值 | `C1input.interpolate` | 将 EFIT 平衡插值到 M3DC1 网格。 |
| 平衡修正 | `C1input.refine` | 通过 Grad-Shafranov 求解器生成自洽平衡。 |
| 平衡验证 | IDL 后处理命令 | 检查电流密度、LCFS、边界和热力学量。 |

对 UniMesh 的启示是：M3DC1 所需网格不仅是几何离散对象，还承载物理区域、边界角色和与 EFIT 坐标体系兼容的几何信息。

### 3.3 MHD 场变量与高阶自由度需求

说明书中一个关键事实是：M3DC1 并不是简单地把速度和磁场存成普通三维向量分量，而是使用适合柱坐标和 MHD 投影的标量势变量。

速度场可表示为：

```text
V = R^2 grad(U) × grad(phi)
  + omega R^2 grad(phi)
  + R^(-2) grad_perp(chi)
```

磁矢势可表示为：

```text
A = R^2 grad(phi) × grad(f)
  + psi grad(phi)
  - F0 ln(R) Z_hat
```

这些表示方式的含义是：

| 变量 | 主要角色 | 对网格和自由度的影响 |
|---|---|---|
| `U` | 极向流或流函数型变量 | 与剪切 Alfvén 动力学相关，需要高阶空间导数支撑。 |
| `omega` | 环向速度变量 | 与慢磁声波动力学相关，需要与其他标量场耦合。 |
| `chi` | 压缩流或势流型变量 | 与快磁声波和半隐式稳定化相关。 |
| `psi` | 磁通相关变量 | 与 Grad-Shafranov 结构和极向磁场相关。 |
| `f` | 三维环向磁场修正变量 | 支持非轴对称扰动。 |

C1 高阶有限元的意义在于使函数值和一阶导数在单元间具备连续性，从而支持磁场、电流、涡量、压力梯度和半隐式高阶算子的稳定计算。

### 3.4 弱形式积分与矩阵装配

文件路径索引显示，有限元弱形式矩阵组装相关候选文件包括：

| 文件 | 架构职责 |
|---|---|
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/element.F90` | 单元级物理或有限元计算骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/element_acc.F90` | GPU/OpenACC 单元计算骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/nintegrate.F90` | 数值积分骨架。 |
| `M3DC1/skeleton/m3dc1_skeleton_big_spec_omp/matdef.F90` | 矩阵项定义骨架。 |
| `M3DC1/m3dc1_scorec/fortran/c1_12_element.F90` | C1 12 自由度单元相关接口候选。 |
| `M3DC1/m3dc1_scorec/fortran/explicit_element.F90` | 显式单元计算接口候选。 |
| `M3DC1/m3dc1_scorec/fortran/explicit_element_interface.F90` | Fortran/C++ 单元接口层候选。 |

弱形式装配的数据链路可抽象为：

```text
单元拓扑连接表
        ↓
局部节点坐标与几何 Jacobian
        ↓
C1 高阶基函数与导数
        ↓
物理变量在积分点重构
        ↓
残量项、质量项、刚度项、半隐式稳定化项
        ↓
局部单元矩阵与右端项
        ↓
散射装配到全局 PETSc 矩阵
```

## 4. `m3dc1_scorec` 的战略生态位

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / `m3dc1_scorec` 的战略生态位  
> **Aider 执行用途**：指导后续优先只读侦察 `m3dc1_scorec` 的 API、mesh、model、field、matrix、ls、adapt、sizeField 和 slnTransfer 模块。  
> **人类阅读用途**：解释为什么 `m3dc1_scorec` 是 UniMesh 对接 M3DC1 的第一优先级参考对象。  
> **场外架构师检索用途**：召回 `m3dc1_scorec` 在 M3DC1 与 SCOREC/PUMI、PETSc、Fortran 物理内核之间的桥梁位置。  
> **触发问题**：`m3dc1_scorec` 是主程序吗？它负责什么？UniMesh 为什么要优先研究它？  
> **事实状态**：编译指南和文件结构证据支持；具体 API 细节待源码确认。  
> **使用限制**：不得把 `m3dc1_scorec` 的私有概念直接上浮到 UniMesh `src/core/`。

#### 本节摘要

`m3dc1_scorec` 不是 M3DC1 的顶层物理主程序，而是 M3DC1 与 SCOREC/PUMI 并行非结构网格生态之间的关键支撑库。它承担网格读取、几何模型绑定、实体遍历、场变量访问、矩阵接口、线性系统、网格适配、尺寸场和解转移等职责。对 UniMesh 来说，`m3dc1_scorec` 是理解 M3DC1 如何实际消费网格的第一优先级入口。UniMesh 应通过 `src/drivers/m3dc1/` 消化这些 M3DC1 私有需求，而不是把其私有语义写入通用核心层。

### 4.1 层级关系

编译指南显示，`m3dc1_scorec` 是需要单独编译并被 M3DC1 主程序链接使用的 C++ 库。其层级关系可理解为：

```text
M3DC1 Fortran 物理主程序
        ↓ 调用或链接
m3dc1_scorec C++ 网格与有限元基础库
        ↓ 依赖
PUMI / SCOREC / Zoltan / PETSc 等第三方 HPC 库
```

因此，`m3dc1_scorec` 的战略生态位是为 M3DC1 的高阶有限元 MHD 求解提供并行非结构网格、几何模型、场数据、网格适配、解转移、矩阵和线性系统接口。

### 4.2 内部模块结构

根据文件路径索引，`m3dc1_scorec` 可被初步划分为以下模块：

| 子模块 | 代表文件 | 白皮书级职责 |
|---|---|---|
| API 层 | `api/m3dc1_scorec.h`、`api/m3dc1_scorec.cc` | 对外暴露 C/C++ 或 Fortran 可调用接口。 |
| 名称转换 | `api/name_convert.h` | 处理 Fortran/C++ 符号命名兼容。 |
| 网格模块 | `include/m3dc1_mesh.h`、`src/m3dc1_mesh.cc` | 网格读取、实体遍历、拓扑连接。 |
| 几何模型模块 | `include/m3dc1_model.h`、`src/m3dc1_model.cc` | 几何模型、区域、边界语义。 |
| 实体模块 | `src/m3dc1_entity.cc` | 顶点、边、面、单元等实体操作。 |
| 场模块 | `include/m3dc1_field.h`、`src/m3dc1_field.cc` | 有限元场变量存储与访问。 |
| 矩阵模块 | `include/m3dc1_matrix.h`、`src/m3dc1_matrix.cc` | 全局矩阵接口与装配支撑。 |
| 线性系统模块 | `include/m3dc1_ls.h`、`src/m3dc1_ls.cc` | 线性系统与求解器接口。 |
| 尺寸场模块 | `include/m3dc1_sizeField.h`、`src/m3dc1_sizeField.cc` | 网格适配尺度控制。 |
| 解转移模块 | `include/m3dc1_slnTransfer.h`、`src/m3dc1_slnTransfer.cc` | 旧网格到新网格的场投影或插值。 |
| 基函数与表达式模块 | `include/ReducedQuintic.h`、`include/BSpline.h`、`include/Expression.h` | 高阶基函数、表达式和几何或场插值支撑。 |

### 4.3 初始化阶段数据流

M3DC1 初始化阶段可抽象为：

```text
用户准备输入
│
├── first_wall.pts
├── geqdsk
├── coil.dat / current.dat
├── profile_ne / profile_te / profile_omega
├── mesh *.smb
├── model *.txt
└── C1input.*
        ↓
M3DC1 主程序读取输入参数
        ↓
m3dc1_scorec 读取或绑定网格与几何模型
        ↓
建立区域标记、边界标记和网格实体拓扑
        ↓
初始化有限元场变量
        ↓
EFIT / profile / coil 数据插值到网格场
        ↓
进入平衡修正、时间推进或线性响应任务
```

`.smb` 与 `.txt` 是教程中反复出现的关键网格和模型输入。UniMesh 面向 M3DC1 的驱动层输出，不应只关注 `.smb` 文件，而应关注 M3DC1 如何把网格拓扑、几何模型、区域边界标记和场自由度整体消费。

### 4.4 弱形式矩阵组装阶段数据流

M3DC1 的弱形式有限元矩阵组装需要 `m3dc1_scorec` 提供以下基础信息：

| 数据类型 | 可能来源模块 | 被消费位置 | 用途 |
|---|---|---|---|
| 节点坐标 `(R,Z)` | mesh / entity | element / nintegrate | 几何映射、Jacobian、积分权重。 |
| 单元拓扑连接表 | mesh | element / matdef | 局部自由度编号和局部矩阵生成。 |
| 边界实体标记 | model / mesh | matdef / boundary terms | 施加边界条件、壁、真空和外边界处理。 |
| 区域标记 | model / mesh | physics residual | 区分 plasma、vacuum、resistive wall 等区域方程。 |
| 场自由度 | field | element / nintegrate | 在积分点重构 `U`、`omega`、`chi`、`psi`、`f` 等变量。 |
| 全局编号 | matrix / ls | PETSc matrix | 将局部矩阵散射到全局稀疏矩阵。 |
| 解向量 | field / ls | time advance | Krylov 解回填到物理场。 |
| 尺寸场 | sizeField | adapt | 控制局部网格加密或粗化。 |
| 解转移 | slnTransfer | adapt / restart | 适配后保持物理场连续性。 |

更直观的链路是：

```text
m3dc1_mesh 提供单元拓扑
        ↓
m3dc1_entity 提供实体坐标、邻接关系和边界归属
        ↓
C1 / reduced-quintic / Hermite 基函数在积分点求值
        ↓
m3dc1_field 提供当前物理场自由度
        ↓
Fortran element / nintegrate / matdef 计算局部弱形式项
        ↓
m3dc1_matrix 将局部贡献装配到全局矩阵
        ↓
m3dc1_ls / PETSc KSP 求解线性系统
        ↓
解向量回填到 m3dc1_field
```

## 5. 网格自适应、解转移与输出诊断

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 网格自适应、解转移与输出诊断  
> **Aider 执行用途**：提示后续研究 M3DC1 时不能只看初始网格读取，还要侦察 adapt、sizeField、slnTransfer 和 collapse 相关链路。  
> **人类阅读用途**：帮助人类主管理解 M3DC1 的网格生命周期不是一次性导入，而是包含适配和解转移的动态流程。  
> **场外架构师检索用途**：召回 M3DC1 网格适配流程和 UniMesh 未来可能需要预留的元数据能力。  
> **触发问题**：M3DC1 是否会修改网格？适配后场变量如何保持？UniMesh 是否需要考虑 solution transfer？  
> **事实状态**：教程级事实与文件结构证据。  
> **使用限制**：不得将 M3DC1 适配流程直接写成 UniMesh 已实现能力。

#### 本节摘要

M3DC1 教程展示了网格适配流程，说明 M3DC1 并非只在初始化时读取一次网格。它可以基于物理场或误差指标触发适配，生成适配后的 `.smb` 网格，并通过解转移机制保持场变量连续性。对 UniMesh 来说，这意味着长期设计不应只服务一次性网格导出，还应预留尺寸场、适配元数据、网格质量报告和解转移映射等能力。但这些能力是否进入核心层、生成层或驱动层，必须由 `UniMesh_Architecture_Plan.md` 决定。

教程级网格适配流程如下：

| 阶段 | 文件或输出 | 含义 |
|---|---|---|
| 运行 adapt 输入 | `C1input.adapt` | 根据物理场或误差指标触发适配。 |
| 并行适配输出 | `ts0-adapted#.smb` | 每个 MPI 任务产生分区适配网格。 |
| 网格合并 | `mesh0.smb` | collapse 工具生成合并网格。 |
| 验证 | `plot_mesh, /iso` | 检查新网格几何与物理区域。 |

文件结构中与适配直接相关的模块包括：

| 文件 | 白皮书级作用 |
|---|---|
| `M3DC1/m3dc1_scorec/src/m3dc1_adapt.cc` | 网格适配实现候选。 |
| `M3DC1/m3dc1_scorec/src/m3dc1_sizeField.cc` | 尺寸场或网格尺度控制实现候选。 |
| `M3DC1/m3dc1_scorec/src/m3dc1_slnTransfer.cc` | 解场从旧网格到新网格转移实现候选。 |
| `M3DC1/m3dc1_scorec/src/slntransferUtil.cc` | 解转移工具函数候选。 |

## 6. UniMesh 适配启示：M3DC1 需求应封锁在驱动层

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / UniMesh 适配启示  
> **Aider 执行用途**：约束后续设计时把 M3DC1 私有语义放入 `src/drivers/m3dc1/`，不得污染 `src/core/`。  
> **人类阅读用途**：把 M3DC1 的复杂需求翻译成 UniMesh 的架构设计注意事项。  
> **场外架构师检索用途**：召回 M3DC1 对 UniMesh 中立核心、驱动层适配和未来验证路径的影响。  
> **触发问题**：UniMesh 需要为 M3DC1 提供什么？哪些概念不能进入 core？M3DC1 驱动层应承担什么？  
> **事实状态**：基于 M3DC1 证据的架构解释；正式设计仍以 `UniMesh_Architecture_Plan.md` 为准。  
> **使用限制**：不得把本节列出的 M3DC1 专属需求直接写入 UniMesh 核心层公共接口。

#### 本节摘要

M3DC1 对 UniMesh 的关键启示是：网格适配层不能只是格式转换脚本，而要能表达节点坐标、单元连接、边界实体、区域标记、属性、自由度布局、分区信息、适配元数据和求解器相关元数据。然而，这些能力必须经过严格分层：通用网格事实可以进入 UniMesh 核心层，M3DC1 私有物理语义、文件格式语义、求解器配置和矩阵元数据必须封锁在 `src/drivers/m3dc1/`。GenericSim 应继续作为参考驱动，用于检查核心抽象是否保持中立。

### 6.1 可抽象为 UniMesh 通用能力的事实

| 通用事实 | 对应 M3DC1 需求 | 是否适合进入核心层 |
|---|---|---|
| 节点坐标表 | `(R,Z)` 节点坐标矩阵 | 可作为通用几何能力。 |
| 单元连接表 | 三角单元拓扑连接 | 可作为通用拓扑能力。 |
| 边界实体表 | wall、outer boundary、interface 等边界实体 | 可抽象为通用边界实体与 Marker。 |
| 区域标记 | plasma、vacuum、resistive wall 等区域角色 | 只能把“区域标记机制”抽象进核心；具体角色名应留在驱动层。 |
| 泛化属性系统 | 质量指标、来源信息、边界附加数据 | 可作为通用 Attribute 能力。 |
| 泛化自由度布局 | C1 高阶节点自由度需求 | 可抽象为求解器中立的 DofLayout；具体 M3DC1 DOF 解释留在驱动层。 |
| 分区元数据 | MPI 分区、所有权、ghost 信息 | 可作为通用 Partition / Metadata 能力。 |

### 6.2 必须留在 M3DC1 驱动层的私有语义

| 私有语义类别 | 示例 | 必须封锁位置 |
|---|---|---|
| M3DC1 区域角色语义 | plasma、vacuum、resistive wall 的具体物理解释 | `src/drivers/m3dc1/` |
| M3DC1 文件格式语义 | `.smb`、model `.txt` 的目标写出规则 | `src/drivers/m3dc1/` |
| M3DC1 场变量解释 | `U`、`omega`、`chi`、`psi`、`f` 的求解器含义 | `src/drivers/m3dc1/` |
| M3DC1 矩阵与求解器元数据 | PETSc/KSP、matrix id、block-Jacobi 配置 | `src/drivers/m3dc1/` |
| M3DC1 高阶有限元私有映射 | C1 reduced quintic / Hermite 的具体下游映射 | `src/drivers/m3dc1/` |

### 6.3 面向 UniMesh 的适配结论

UniMesh 面向 M3DC1 的驱动层应优先关注以下能力：

1. 将 UniMesh 的几何坐标与拓扑连接转换为 M3DC1 可消费的 mesh 层结构。
2. 将 UniMesh 的 Marker 与 Attribute 转换为 M3DC1 model 层所需的区域和边界描述。
3. 将 UniMesh 的泛化 DofLayout 映射为 M3DC1 field 层可解释的高阶自由度布局。
4. 将 M3DC1 的矩阵装配、KSP 配置和线性求解器元数据封装为驱动层私有 metadata。
5. 在 writer 前执行 M3DC1 专属 validation，阻断区域标记缺失、边界不闭合、连接表非法和自由度布局不匹配等问题。
6. 保持 `src/core/` 只表达中立网格事实，不解释任何具体 M3DC1 物理角色。

## 7. 后续只读侦察清单

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 后续只读侦察清单  
> **Aider 执行用途**：为后续 Aider 在用户授权下只读阅读 M3DC1 源码提供优先级清单和禁止事项。  
> **人类阅读用途**：帮助人类主管理解下一步如果要深入 M3DC1，应先看哪些模块。  
> **场外架构师检索用途**：召回 M3DC1 源码侦察路线和仍待确认的关键接口。  
> **触发问题**：下一步应该读 M3DC1 哪些源码？哪些调用链还没确认？  
> **事实状态**：当前任务建议与待源码确认事项。  
> **使用限制**：只读侦察清单不代表授权修改 M3DC1；任何外部源码仍处于只读隔离区。

#### 本节摘要

本文档目前已经建立 M3DC1 的宏观架构地图，但尚未完成源码级调用链确认。后续若人类主管要求继续推进，应按照“先宏观、再核心数据结构、最后具体数值语义”的顺序，只读侦察 M3DC1 的主程序、`m3dc1_scorec` API、mesh/model/field 数据链、matrix/ls 求解器边界、adapt/sizeField/slnTransfer 适配链路和 Fortran 单元积分骨架。所有侦察结果必须以文档形式反馈，不得修改 M3DC1 官方源码。

优先侦察清单如下：

| 优先级 | 目标模块 | 需要确认的问题 |
|---|---|---|
| P0 | `skeleton/.../main*.F90` | 主程序如何读取输入、初始化任务、调用时间推进或线性响应流程。 |
| P0 | `m3dc1_scorec/api/m3dc1_scorec.*` | Fortran 与 C++ 之间的公开 API 边界是什么。 |
| P0 | `m3dc1_scorec/include/m3dc1_mesh.h` 与 `src/m3dc1_mesh.cc` | M3DC1 如何读取、遍历和查询网格拓扑。 |
| P0 | `m3dc1_scorec/include/m3dc1_model.h` 与 `src/m3dc1_model.cc` | 区域、边界和几何模型语义如何进入有限元装配。 |
| P1 | `m3dc1_scorec/include/m3dc1_field.h` 与 `src/m3dc1_field.cc` | 场自由度如何存储、访问和回填。 |
| P1 | `m3dc1_scorec/include/m3dc1_matrix.h` 与 `src/m3dc1_matrix.cc` | 局部矩阵如何装配进全局矩阵。 |
| P1 | `m3dc1_scorec/include/m3dc1_ls.h` 与 `src/m3dc1_ls.cc` | 线性系统、PETSc KSP 和解向量如何组织。 |
| P1 | `m3dc1_scorec/src/m3dc1_adapt.cc`、`m3dc1_sizeField.cc`、`m3dc1_slnTransfer.cc` | 网格适配、尺寸场和解转移的实际数据流。 |
| P2 | `fortran/c1_12_element.F90` 与 skeleton 中的 `element.F90`、`nintegrate.F90`、`matdef.F90` | C1 高阶有限元、积分点重构和弱形式装配如何消费 mesh/field 数据。 |

后续只读侦察必须遵守以下纪律：

1. 不修改 `M3DC1/` 目录下任何源码。
2. 不把 M3DC1 私有变量名、区域角色或 PETSc/KSP 配置上浮到 UniMesh 核心层。
3. 先输出源码地图和数据流报告，再讨论是否需要更新 `UniMesh_Architecture_Plan.md`。
4. 涉及 UniMesh 实现方案时，必须先更新总蓝图，再进入代码。
5. 对未读源码的内容保持“待确认”标记，不把推断写成已确认事实。

## 8. 总结：M3DC1 对 UniMesh 的战略意义

> **章节坐标**：侦察证据 / `M3DC1_Architecture_Whitepaper.md` / 总结  
> **Aider 执行用途**：给后续开发代理提供 M3DC1 适配的高层红线和工作入口。  
> **人类阅读用途**：帮助人类主管用一句清晰的工程判断理解 M3DC1 对 UniMesh 的价值。  
> **场外架构师检索用途**：召回 M3DC1 与 UniMesh 之间最核心的适配结论。  
> **触发问题**：M3DC1 对 UniMesh 的最终启示是什么？UniMesh 为什么不能写成格式转换器？  
> **事实状态**：基于已确认材料的阶段性架构结论。  
> **使用限制**：本节是总结性判断，不替代具体蓝图和源码实现。

#### 本节摘要

M3DC1 是 UniMesh 的第一个真实下游验证对象，但它不是 UniMesh 核心层抽象的所有者。M3DC1 的高阶 C1 有限元、多区域物理语义、隐式矩阵装配、Krylov 求解和网格适配流程，证明 UniMesh 不能被设计成一次性格式转换脚本。UniMesh 应维护中立网格内核，通过 M3DC1 驱动层封装下游私有语义，并通过 GenericSim 等参考驱动持续检查核心层通用性。

可以把最终结论浓缩为：

```text
M3DC1 要求 UniMesh 理解的不只是“网格文件”，
而是“带几何拓扑、区域边界语义、高阶自由度、适配元数据和求解器约束的网格消费链”。

UniMesh 的正确架构回应不是污染 core，
而是在 core 保持中立事实模型，
在 drivers/m3dc1 中消化 M3DC1 私有语义，
并用 validation、writer、metadata 映射形成可检查的适配闭环。
```

对后续工程推进而言，最重要的红线是：

1. M3DC1 是真实验证对象，但不能反向定义 UniMesh 核心层。
2. `m3dc1_scorec` 是优先只读侦察对象，但其私有概念不得直接上浮到 `src/core/`。
3. M3DC1 的区域语义、场变量语义、文件格式语义和求解器配置必须封锁在 `src/drivers/m3dc1/`。
4. 任何 M3DC1 适配设计都必须先进入 `UniMesh_Architecture_Plan.md`，再进入代码实现。
5. 外部 M3DC1 官方源码始终是只读参考库，不得由 UniMesh 开发代理直接修改。
