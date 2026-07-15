# UniMesh 项目目录树

> 本文档面向人类用户，用于快速查看 UniMesh 仓库的目录结构和各目录职责。  
> 详细架构原则、模块边界、网格生成核心和 AI 开发约束请阅读 `docs/UniMesh_Architecture_Plan.md`。

## 1. 顶层目录结构

```text
UniMesh/
│
├── .venv/
├── .vscode/
│
├── CONTEXT.md
├── STUDIO_CONTEXT.md
├── UniMesh_Architecture_Plan.md
├── Project_Tree.md
│
├── src/
│   ├── main.cc
│   ├── core/
│   ├── generation/
│   ├── drivers/
│   └── utils/
│
├── docs/
│   ├── trimeg/
│   ├── tokamaker/
|   ├── m3dc1/
│   └── unimesh/
│
├── M3DC1/
├── TRIMEG/
└── TOKAMAKER/
```

## 2. 顶层目录说明

| 路径 | 用途 |
|---|---|
| `.venv/` | Python 虚拟环境目录，通常不提交到 Git。 |
| `.vscode/` | VS Code 本地编辑器配置目录。 |
| `CONTEXT.md` | 项目开发上下文与 AI 协作约束。 |
| `STUDIO_CONTEXT.md` | 场外架构协作与数物对齐相关上下文。 |
| `UniMesh_Architecture_Plan.md` | UniMesh 架构规划书，主要供 AI 后续开发使用。 |
| `Project_Tree.md` | UniMesh 项目目录树，主要供人类用户快速查看。 |
| `src/` | UniMesh 主体源码目录。 |
| `docs/` | 项目文档与外部代码分析报告目录。 |
| `M3DC1/` | M3DC1 官方源码与本地参考库，只读隔离。 |
| `TRIMEG/` | TRIMEG 或相关上游网格生成代码参考库，只读隔离。 |
| `TOKAMAKER/` | TokaMaker 或相关上游网格生成代码参考库，只读隔离。 |

## 3. `src/` 源码目录结构

```text
src/
│
├── main.cc
│
├── core/
│   ├── unimesh.h
│   ├── mesh.h
│   ├── mesh.cc
│   ├── mesh_entity.h
│   ├── mesh_entity.cc
│   ├── geometry.h
│   ├── geometry.cc
│   ├── topology.h
│   ├── topology.cc
│   ├── connectivity.h
│   ├── connectivity.cc
│   ├── attribute.h
│   ├── attribute.cc
│   ├── marker.h
│   ├── marker.cc
│   ├── metadata.h
│   ├── metadata.cc
│   ├── dof_layout.h
│   ├── dof_layout.cc
│   ├── partition.h
│   ├── partition.cc
│   ├── validation.h
│   ├── validation.cc
│   ├── io_mesh.h
│   └── io_mesh.cc
│
├── generation/
│   ├── generation.h
│   ├── geometric_domain.h
│   ├── geometric_domain.cc
│   ├── boundary_curve.h
│   ├── boundary_curve.cc
│   ├── region_decomposition.h
│   ├── region_decomposition.cc
│   ├── size_field.h
│   ├── size_field.cc
│   ├── point_seeding.h
│   ├── point_seeding.cc
│   ├── constrained_triangulation.h
│   ├── constrained_triangulation.cc
│   ├── boundary_recovery.h
│   ├── boundary_recovery.cc
│   ├── mesh_quality.h
│   ├── mesh_quality.cc
│   ├── mesh_optimizer.h
│   ├── mesh_optimizer.cc
│   ├── topology_builder.h
│   ├── topology_builder.cc
│   ├── mesh_generator.h
│   └── mesh_generator.cc
│
├── drivers/
│   ├── driver.h
│   ├── driver_options.h
│   ├── driver_options.cc
│   ├── driver_registry.h
│   ├── driver_registry.cc
│   │
│   ├── generic/
│   │   ├── driver_generic.h
│   │   ├── driver_generic.cc
│   │   ├── generic_schema.h
│   │   ├── generic_schema.cc
│   │   ├── generic_translator.h
│   │   ├── generic_translator.cc
│   │   ├── generic_writer.h
│   │   ├── generic_writer.cc
│   │   ├── generic_validation.h
│   │   └── generic_validation.cc
│   │
│   └── m3dc1/
│       ├── driver_m3dc1.h
│       ├── driver_m3dc1.cc
│       ├── m3dc1_schema.h
│       ├── m3dc1_schema.cc
│       ├── m3dc1_mesh_translator.h
│       ├── m3dc1_mesh_translator.cc
│       ├── m3dc1_model_translator.h
│       ├── m3dc1_model_translator.cc
│       ├── m3dc1_field_translator.h
│       ├── m3dc1_field_translator.cc
│       ├── m3dc1_matrix_metadata.h
│       ├── m3dc1_matrix_metadata.cc
│       ├── m3dc1_writer.h
│       ├── m3dc1_writer.cc
│       ├── m3dc1_validation.h
│       └── m3dc1_validation.cc
│
└── utils/
    ├── logging.h
    ├── logging.cc
    ├── error.h
    └── error.cc
```

## 4. `src/` 子目录说明

| 路径 | 用途 |
|---|---|
| `src/main.cc` | UniMesh 命令行入口，负责参数解析、几何输入、网格生成流程、驱动选择和导出流程编排。 |
| `src/core/` | 通用网格元模型，管理几何、拓扑、连接表、属性、标记、自由度和分区信息。 |
| `src/generation/` | 通用非结构化网格生成核心，负责几何域、边界曲线、区域划分、尺寸场、三角剖分、边界恢复、质量评估和拓扑构建。 |
| `src/drivers/` | 外部模拟软件适配层，负责把 UniMesh 通用网格数据翻译为目标求解器可消费的结构或文件格式。 |
| `src/drivers/generic/` | GenericSim 参考驱动，用于验证核心层与生成层抽象是否足够通用。 |
| `src/drivers/m3dc1/` | M3DC1 专属驱动，用于对接第一个真实下游高阶有限元 MHD 模拟程序。 |
| `src/utils/` | 通用工程辅助模块，例如日志、错误处理和诊断信息。 |

## 5. `src/core/` 文件说明

| 文件 | 用途 |
|---|---|
| `unimesh.h` | 核心层统一公共头文件。 |
| `mesh.h` / `mesh.cc` | 通用网格主容器。 |
| `mesh_entity.h` / `mesh_entity.cc` | 顶点、边、面、单元等网格实体抽象。 |
| `geometry.h` / `geometry.cc` | 节点坐标矩阵和几何查询。 |
| `topology.h` / `topology.cc` | 实体邻接、包含、方向和边界关系。 |
| `connectivity.h` / `connectivity.cc` | 单元连接表和局部拓扑模板。 |
| `attribute.h` / `attribute.cc` | 泛化属性系统。 |
| `marker.h` / `marker.cc` | 区域、边界、集合等通用标记系统。 |
| `metadata.h` / `metadata.cc` | 网格级元数据容器。 |
| `dof_layout.h` / `dof_layout.cc` | 泛化自由度布局。 |
| `partition.h` / `partition.cc` | 并行分区、所有权和 ghost 实体信息。 |
| `validation.h` / `validation.cc` | 通用网格合法性与一致性检查。 |
| `io_mesh.h` / `io_mesh.cc` | 求解器无关的基础网格读写接口。 |

## 6. `src/generation/` 文件说明

| 文件 | 用途 |
|---|---|
| `generation.h` | 生成层统一公共头文件。 |
| `geometric_domain.h` / `geometric_domain.cc` | 几何域、坐标空间、外边界、内边界、孔洞和约束几何对象。 |
| `boundary_curve.h` / `boundary_curve.cc` | 边界曲线、折线边界、参数化边界和边界采样。 |
| `region_decomposition.h` / `region_decomposition.cc` | 区域划分、子域标签、区域邻接和区域-边界关联关系。 |
| `size_field.h` / `size_field.cc` | 通用尺寸场，用于描述不同位置的目标网格尺度。 |
| `point_seeding.h` / `point_seeding.cc` | 初始点云生成，包括边界点、内部点和区域约束点。 |
| `constrained_triangulation.h` / `constrained_triangulation.cc` | 约束三角剖分，从点集与约束边生成初始非结构三角网格。 |
| `boundary_recovery.h` / `boundary_recovery.cc` | 边界恢复，确保外边界、内部界面和区域分隔线被网格边准确表达。 |
| `mesh_quality.h` / `mesh_quality.cc` | 网格质量指标，例如面积、长宽比、最小角、最大角和尺寸场偏差。 |
| `mesh_optimizer.h` / `mesh_optimizer.cc` | 网格质量优化，例如点平滑、边翻转、局部重构和尺寸场一致化。 |
| `topology_builder.h` / `topology_builder.cc` | 从剖分结果构建 UniMesh 拓扑连接表、实体邻接图和 Marker 绑定。 |
| `mesh_generator.h` / `mesh_generator.cc` | 网格生成器门面，串联几何域、尺寸场、点采样、三角化、边界恢复、优化和拓扑构建。 |

## 7. `src/drivers/generic/` 文件说明

| 文件 | 用途 |
|---|---|
| `driver_generic.h` / `driver_generic.cc` | GenericSim 驱动主类和导出流程编排。 |
| `generic_schema.h` / `generic_schema.cc` | GenericSim 抽象 schema 定义与检查。 |
| `generic_translator.h` / `generic_translator.cc` | UniMesh 通用网格到 GenericSim 中间结构的转换。 |
| `generic_writer.h` / `generic_writer.cc` | GenericSim 调试或参考格式写出。 |
| `generic_validation.h` / `generic_validation.cc` | GenericSim 最低限度输入检查。 |

## 8. `src/drivers/m3dc1/` 文件说明

| 文件 | 用途 |
|---|---|
| `driver_m3dc1.h` / `driver_m3dc1.cc` | M3DC1 驱动主类和导出流程编排。 |
| `m3dc1_schema.h` / `m3dc1_schema.cc` | M3DC1 专属标签、属性键和导出规则。 |
| `m3dc1_mesh_translator.h` / `m3dc1_mesh_translator.cc` | UniMesh 几何拓扑到 M3DC1 mesh 层的转换。 |
| `m3dc1_model_translator.h` / `m3dc1_model_translator.cc` | UniMesh Marker/Attribute 到 M3DC1 model 层的转换。 |
| `m3dc1_field_translator.h` / `m3dc1_field_translator.cc` | UniMesh 泛化 DOF 到 M3DC1 field 层的转换。 |
| `m3dc1_matrix_metadata.h` / `m3dc1_matrix_metadata.cc` | M3DC1 矩阵装配和线性求解器元数据映射。 |
| `m3dc1_writer.h` / `m3dc1_writer.cc` | M3DC1 目标格式写出。 |
| `m3dc1_validation.h` / `m3dc1_validation.cc` | M3DC1 专属输入前检查。 |

## 9. 阅读建议

如果你是人类用户，建议优先阅读（优先级由高到低排列）：

```text
Project_Tree.md
CONTEXT.md
UniMesh_Architecture_Plan.md
```

如果你是后续 AI 开发代理，建议优先阅读（优先级由高到低排列）：

```text
CONTEXT.md
UniMesh_Architecture_Plan.md
Project_Tree.md
```

## 10. 蓝图驱动开发协议

UniMesh 研发采用严格的微循环迭代机制。每一层级的开发（Layer N）都必须遵循：

```text
调研
  ↓
技术文档
  ↓
强制升级总蓝图
  ↓
实现与验收代码
```

`UniMesh_Architecture_Plan.md` 是 UniMesh 架构与代码实现的唯一事实真理。  
任何架构调整必须先落实到总蓝图，并经主管确认后，方可进入对应代码实现。

强制纪律如下：

1. 完成第 N 层调研后，必须先产出技术文档或设计方案；
2. 技术方案获批后，必须先更新 `UniMesh_Architecture_Plan.md`；
3. 总蓝图未更新、未确认前，严禁编写对应功能代码；
4. 如果代码实现与总蓝图冲突，必须优先修正蓝图或重构代码，不允许代码越界先行；
5. 每一层都执行同一套微循环，不允许把架构更新拖延到项目末端。

因此，UniMesh 的标准推进方式不是“先写大量代码，最后补蓝图”，而是：

```text
每推进一个具体层级
    ↓
先调研
    ↓
形成技术文档
    ↓
强制升级总蓝图
    ↓
再实现与验收代码
```

## 11. 项目研发演进图谱（BFS 广度优先搜索树）

本节面向人类用户，用一棵广度优先搜索树展示 UniMesh 当前研发路线。  
这里的 BFS 不是算法实现代码，而是一种工程侦察方法：先横向扫清多个外部参考源的宏观结构，再逐层向下进入源码细节、接口隔离、统一抽象和回归验证。

需要特别说明：本节是面向人类用户的研发图谱，不直接替代 `UniMesh_Architecture_Plan.md`。  
任何从本图谱推导出的架构调整，都必须进入“调研 -> 技术文档 -> 强制升级总蓝图 -> 实现与验收代码”的微循环。

```text
                                  [根节点：UniMesh 通用网格解耦底座]
                                                │
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     │                          │                          │
                     ▼                          ▼                          ▼
        [Layer 1：M3DC1 宏观哨探]   [Layer 1：TokaMaker 宏观哨探]   [Layer 1：TRIMEG 战术占位]
             状态：已完成                 状态：已完成                  状态：等待中
             关注：下游接收端             关注：上游生成链路              关注：候选生成算法
             产物：M3DC1 白皮书            产物：TokaMaker 白皮书          产物：TRIMEG 白皮书
                     │                          │                          │
                     │                          │                          │
                     ▼                          ▼                          ▼
        [Layer 2：M3DC1 源码逆向]   [Layer 2：TokaMaker API 隔离]   [Layer 2：TRIMEG 算法能力评估]
             │                          │                          │
             ├─ mesh/model/field         ├─ meshing.py 定点解剖       ├─ 输入几何表达确认
             │  数据消费链确认           ├─ _interface.py FFI 边界    ├─ 输出网格类型确认
             ├─ C1 高阶有限元 DOF        ├─ triangle.c C API 防线     ├─ 速度/质量取向评估
             │  需求拆解                 ├─ triangulateio 隔离        ├─ 内存模型与调用方式识别
             ├─ matrix/KSP 元数据         └─ region/max_area           └─ 并行与高阶适配潜力评估
             │  驱动内封装                  生成约束归位
             └─ M3DC1 私有语义
                禁止上浮 core
                     │                          │                          │
                     ▼                          ▼                          ▼
        [Layer 3：M3DC1 驱动层适配设计] [Layer 3：三源事实交叉比对] [Layer 3：生成层多引擎封装设计]
             │                          │                          │
             ├─ 高阶 DOF 映射骨架        ├─ 点坐标矩阵共性             ├─ MeshGenerationRequest
             ├─ 私有物理语义消化         ├─ 单元连接表共性             ├─ MeshGenerationOptions
             ├─ mesh/model/field          ├─ 边界/区域标记共性          ├─ MeshGenerationResult
             │  翻译器职责划分           ├─ 尺寸场/质量约束差异        ├─ TriangleBackend 候选封装
             ├─ PETSc/KSP 元数据          ├─ 高阶/导数 DOF 差异         ├─ ResearchFastBackend 候选封装
             │  驱动内装配               └─ 求解器私有元数据差异       ├─ ResearchQualityBackend 候选封装
             └─ validation/writer                                     └─ 后端注册表与路由策略
                闭环设计
                     │                          │                          │
                     └──────────────┬───────────┴───────────┬──────────────┘
                                    │                       │
                                    ▼                       ▼
                              [Layer 4：UniMesh 中立抽象收敛]
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                              ▼                    ▼                    ▼
                    [core 事实模型压力测试] [generation 工厂边界测试] [drivers 适配边界测试]
                              │                    │                    │
                              ├─ Geometry 是否足够  ├─ C 指针不越界      ├─ M3DC1 私有语义
                              ├─ Connectivity 是否足够 ├─ 后端结构体不外泄 │  只留在 m3dc1/
                              ├─ Marker/Attribute  ├─ 控制参数不上浮     ├─ GenericSim 不吸收
                              │  是否足够表达      ├─ 速度/质量策略可换  │  真实私有语义
                              └─ DofLayout 是否     └─ 生成结果统一转入  └─ 驱动导出流程可替换
                                 保持求解器中立        core::Mesh
                                                   │
                                                   ▼
                              [Layer 5：跨网格源验证与回归压力测试]
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                              ▼                    ▼                    ▼
                    [几何拓扑一致性回归] [质量与鲁棒性回归] [端到端适配回归]
                              │                    │                    │
                              ├─ 重复点检测         ├─ 最小角/长宽比      ├─ 生成后导入 core
                              ├─ 非法连接检测       ├─ 退化单元检测       ├─ core 导出 generic
                              ├─ 边界闭合检测       ├─ 尺寸场偏差检测     ├─ core 导出 m3dc1
                              ├─ 区域标记完整性     ├─ 后端失败诊断       └─ 多源样例持续集成
                              └─ 邻接图一致性       └─ 参数扰动稳定性
                                                   │
                                                   ▼
                              [Layer 6：三源接口基线对齐与原型交付]
                                                   │
                              ├─ 对齐 M3DC1、TOKAMAKER、TRIMEG 三源接口基线
                              ├─ 在总蓝图中固化 generation/core/drivers 三层边界
                              ├─ 确认 UniMesh 中间适配层核心架构
                              ├─ 交付最小可运行原型
                              ├─ 验证标准中间适配能力
                              └─ 进入面向各物理源的持续适配迭代循环
```

### 11.1 Layer 1：三大参考源的宏观哨探

Layer 1 的任务是先横向建立“外部世界地图”，避免 UniMesh 因单一参考源而过拟合。

| 节点 | 当前状态 | 战略意义 |
|---|---|---|
| M3DC1 宏观哨探 | 已完成 | 将 M3DC1 定位为第一个真实下游接收端，用于验证 UniMesh 能否服务高阶有限元 MHD 程序。 |
| TokaMaker 宏观哨探 | 已完成 | 将 TokaMaker / Triangle 链路定位为上游网格生成参考，用于观察二维三角网格生成过程如何进入中立网格事实。 |
| TRIMEG 战术占位 | 等待中 | 保留第三个参考源，用于校验生成层、多后端抽象和核心模型是否存在尚未暴露的盲区。 |

这一层的核心价值在于“先看全局，再进细节”。对于数值软件工程来说，这相当于在写核心数据结构前，先确认多个程序对网格事实的消费方式和生产方式，减少架构早熟和局部硬编码风险。

### 11.2 Layer 2：源码细节解剖与接口防线

Layer 2 开始进入外部代码的局部实现，但仍要坚持只读侦察和边界隔离。

#### M3DC1 方向

M3DC1 是下游接收端，重点不是如何生成网格，而是如何消费网格。需要确认：

1. mesh/model/field/matrix 数据链路如何读取坐标、连接表、区域和边界；
2. C1 高阶有限元与导数型自由度如何约束 UniMesh 的 `DofLayout`；
3. matrix/KSP 等求解器元数据如何被驱动层封装；
4. M3DC1 私有语义不得进入 `src/core/`。

它对 UniMesh 的反哺主要发生在驱动层：帮助确认 `drivers/m3dc1/` 需要哪些 translator、schema、writer 和 validation。

#### TokaMaker 方向

TokaMaker 是上游生成链路参考，重点是 API 隔离。需要确认：

1. `meshing.py` 如何组织点、边界段、区域标记和 Triangle 输入；
2. `_interface.py` 如何通过 FFI 或 `ctypes` 绑定底层 C 库；
3. `triangle.c` 暴露哪些 C API、结构体和内存约定；
4. `triangulateio`、switch 字符串、原生指针和后端控制参数必须被隔离在生成后端内部。

它对 UniMesh 的反哺主要发生在生成层：帮助确认未来多后端生成工厂如何阻断 C API 污染核心层。

#### TRIMEG 方向

TRIMEG 当前仍是战术占位。后续需要确认：

1. 输入几何是点线段、曲线、隐式边界还是其他形式；
2. 输出网格是三角形、四边形、混合网格还是高阶曲边单元；
3. 算法更偏速度、质量、自适应，还是并行扩展；
4. 调用方式是库接口、文件交换、命令行进程还是脚本 API；
5. 其能力是否能与 TokaMaker / Triangle 形成互补。

TRIMEG 的主要价值是避免 TokaMaker 单一来源决定生成层结构。TRIMEG 调研完成后，必须先产出技术文档，再将三源结论强制同步进 `UniMesh_Architecture_Plan.md`，随后才能进入对应实现与验收代码。

### 11.3 Layer 3：驱动适配设计、三源交叉比对与多引擎封装设计

Layer 3 是从“读懂外部代码”过渡到“抽象 UniMesh 自身能力”的关键层。

#### M3DC1 驱动层适配设计

M3DC1 驱动层适配设计节点承接 Layer 2 对 M3DC1 mesh/model/field/matrix 数据消费链的逆向解剖结论。  
它的任务不是修改 UniMesh 中立内核，而是设计一套位于 `src/drivers/m3dc1/` 内部的驱动适配器骨架，用于把 UniMesh 的中立网格事实转换为 M3DC1 可消费的私有结构。

该节点需要重点规划：

1. 如何将 UniMesh 的坐标、连接表、Marker、Attribute 和泛化 `DofLayout` 映射到 M3DC1 mesh/model/field 层；
2. 如何在驱动内部消化 M3DC1 私有物理语义，避免区域角色、求解器配置和专用标签上浮到 `src/core/`；
3. 如何处理高阶 DOF 与导数型自由度的驱动侧映射骨架；
4. 如何在 M3DC1 驱动内部装配 PETSc/KSP 等矩阵与线性求解器元数据；
5. 如何通过 `schema`、`translator`、`writer` 与 `validation` 形成可检查、可阻断、可回归的导出闭环。

因此，该节点是 M3DC1 方向从“源码读懂”走向“驱动设计”的过渡层。  
它与右侧的“三源事实交叉比对”和“生成层多引擎封装设计”并列，但职责更偏向下游适配边界，核心原则仍然是：M3DC1 私有语义只在驱动层内部解释，不能污染 UniMesh 中立核心层。

三源交叉比对需要把所有外部事实分成两类：

```text
可进入 UniMesh 中立模型的通用事实
不可进入 core 的私有实现细节
```

可进入中立模型的事实包括：

1. 节点坐标矩阵；
2. 单元连接表；
3. 边界实体；
4. 区域或材料标记；
5. 通用属性；
6. 可选质量指标；
7. 可选生成过程元数据；
8. 泛化自由度布局。

必须隔离的私有细节包括：

1. Triangle 的 `triangulateio`；
2. C API 原生指针；
3. 后端专属 switch 字符串；
4. 研究代码内部数组布局；
5. 私有质量优化参数名；
6. 下游求解器专属区域角色；
7. PETSc/KSP 等求解器私有配置。

这一层对应 TokaMaker 白皮书中“多后端可插拔网格生成工厂”的思想：未来 `src/generation/` 不应只是 Triangle 包装器，而应允许多个后端共存，例如速度优先型后端、质量优先型后端和未来高阶自适应后端。

这一层若进入实现，必须先完成：

```text
三源事实交叉比对文档
    ↓
生成层多引擎封装方案
    ↓
强制升级 UniMesh_Architecture_Plan.md
    ↓
实现 MeshGenerationRequest / Result 与后端注册表
```

### 11.4 Layer 4：UniMesh 中立抽象收敛

Layer 4 的任务是把多源事实压缩为可维护的 UniMesh 抽象。

#### core 事实模型压力测试

需要回答：

1. `Geometry` 是否足够表达二维、三维和未来曲边几何；
2. `ConnectivityTable` 是否足够表达三角形、四边形、混合单元和高阶局部拓扑；
3. `Marker` / `Attribute` 是否足够表达边界、区域、材料、质量指标和外部来源信息；
4. `DofLayout` 是否能在不吸收 M3DC1 私有有限元名称的前提下表达高阶与导数型自由度。

#### generation 工厂边界测试

需要回答：

1. 后端 C 指针是否完全不进入 `src/core/`；
2. 后端结构体是否只存在于后端 adapter 内部；
3. 后端控制参数是否通过通用 options 或后端私有 options 隔离；
4. 更换 Triangle、TRIMEG 或研究代码后端时，是否不需要修改 core 数据模型；
5. 生成结果是否最终统一收敛为 `core::Mesh`。

#### drivers 适配边界测试

需要回答：

1. M3DC1 私有语义是否只存在于 `drivers/m3dc1/`；
2. GenericSim 是否仍保持参考驱动定位，不吸收真实软件私有概念；
3. 不同下游程序是否可以通过独立 driver 消费同一个 core 网格对象；
4. 驱动导出失败是否能通过 validation 和 report 给出明确诊断。

这一层的战略意义是把“看起来能跑”的程序，提升为“结构上可长期扩展”的数值软件工程体系。  
任何 core、generation 或 drivers 边界调整，都必须先写入总蓝图，再进入代码实现。

### 11.5 Layer 5：跨网格源验证与回归压力测试

Layer 5 是将架构判断落到工程质量保证中的阶段。

#### 几何拓扑一致性回归

用于检查不同来源网格进入 core 后是否满足基本拓扑合法性：

1. 重复点检测；
2. 非法连接检测；
3. 退化单元检测；
4. 边界闭合检测；
5. 区域标记完整性；
6. 邻接图一致性。

#### 质量与鲁棒性回归

用于比较不同生成后端的数值网格质量：

1. 最小角；
2. 最大角；
3. 长宽比；
4. 面积分布；
5. 尺寸场偏差；
6. 参数扰动稳定性；
7. 后端失败诊断。

这里会遇到一个典型工程矛盾：速度优先后端可能适合大规模参数扫描，但网格质量可能不足；质量优先后端更适合高阶有限元和强梯度区域，但计算成本更高。UniMesh 不应在 core 中固化某一种策略，而应通过 generation 后端选择和 metadata/report 系统记录这种差异。

#### 端到端适配回归

用于验证完整链路：

```text
外部生成源或导入源
        ↓
UniMesh core::Mesh
        ↓
GenericSim 参考导出
        ↓
M3DC1 真实驱动导出
```

这可以确保 UniMesh 不是单点转换脚本，而是具有长期回归测试能力的通用适配层。

Layer 5 的测试与验收体系也必须遵循蓝图驱动开发协议：先明确测试设计与验收指标，强制同步到总蓝图，再实现自动化脚本和回归测试代码。

### 11.6 Layer 6：三源接口基线对齐与原型交付

Layer 6 是三源接口基线对齐节点，不是架构滞后补写阶段。  
本层标志着 UniMesh 作为中间适配层的核心架构已确立。

本层目标如下：

1. M3DC1、TOKAMAKER 与 TRIMEG 的接口基线需求在总蓝图中完成对齐；
2. `generation/`、`core/`、`drivers/` 三层职责完成稳定划分；
3. UniMesh 原型具备标准的中间适配能力；
4. 原型能够支撑后续针对不同物理源的映射与解耦验证；
5. 项目进入持续的、针对各源的适配迭代循环。

Layer 6 的交付链路应为：

```text
三源接口基线技术文档
    ↓
强制升级 UniMesh_Architecture_Plan.md
    ↓
最小可运行原型实现
    ↓
GenericSim 中立适配验证
    ↓
M3DC1 真实驱动预验证
    ↓
持续适配迭代循环
```

Layer 6 之后，UniMesh 的开发模式仍然保持微循环：

```text
新的物理源或新后端调研
    ↓
产出技术文档
    ↓
强制升级总蓝图
    ↓
实现与验收代码
```

### 11.7 黑箱 Bug 防御与量化验收指标

本节是对上方 6 层实态研发树的工程验收补强。  
其目标不是替代总蓝图，而是在未来进入源码实现前，把“写代码、编接口、测数据”的最低防线提前固定下来，防止底层实现变成难以追踪的黑箱。

核心原则如下：

```text
外部黑箱输入必须先消毒
        ↓
内部控制流必须有断言
        ↓
数值结果必须可检查
        ↓
中间状态必须可落盘
        ↓
端到端链路必须可回归
        ↓
集成阶段必须启用动态内存与未定义行为扫描
```

#### 11.7.1 Layer 1 & Layer 2：哨探与 FFI 隔离级防线

挂载节点：

```text
triangle.c C API 防线
triangulateio 隔离
M3DC1 私有语义禁止上浮
```

这些节点的主要风险来自外部源码、第三方 C 库、FFI 边界和下游私有语义。  
未来一旦实现 Triangle、TRIMEG 或其他研究代码后端，所有原生指针、外部数组和后端结构体必须被限制在隔离层内部，不允许越过边界进入 `src/core/`。

| 防线对象 | 验收方案 | 量化指标 | 黑箱 Bug 防御机制 |
|---|---|---|---|
| `triangle.c C API 防线` | 为后端 adapter 编写边界输入检查单元测试，覆盖空指针、空数组、负尺寸、超大尺寸和不一致尺寸。 | 所有 C API 入口包装函数必须在调用第三方库前完成 100% 参数预检查。 | 对传入原生指针执行 `NULL` 硬判定；对点、段、区域数组长度执行上限与下限检查；任何非法输入必须返回明确错误，不允许进入第三方 C 函数。 |
| `triangulateio 隔离` | 检查公共头文件，确认 `triangulateio` 或等价后端结构体不出现在 `src/core/`、`src/drivers/generic/` 和公共 API 中。 | 后端原生结构体在核心层出现次数必须为 0。 | 后端结构体只能存在于具体 adapter 的 `.cc` 或私有头文件中；转换结果必须落到中立的坐标表、连接表、Marker 和 Attribute。 |
| `M3DC1 私有语义禁止上浮` | 使用关键字扫描和代码评审检查 `src/core/` 是否出现 M3DC1、KSP、PETSc、matrix_id、plasma、vacuum 等私有概念。 | 核心层私有关键字命中数必须为 0。 | M3DC1 的区域角色、矩阵元数据和求解器配置只能在 `src/drivers/m3dc1/` 中解释；若核心层确需扩展，只允许提炼为通用 Marker、Attribute、Metadata 或 DofLayout 能力。 |

未来编码时，FFI 边界必须采用“先验证、再转换、后调用”的顺序：

```text
外部输入
    ↓
Boundary Sanitization
    - NULL 指针检查
    - 数组尺寸检查
    - 索引范围检查
    - 坐标有限性检查
    - 区域种子合法性检查
    ↓
后端私有结构体构造
    ↓
第三方库调用
    ↓
输出结果再验证
    ↓
转换为 core::Mesh
```

最低验收要求：

1. 任何来自第三方 C 库或研究代码的原生指针必须先检查是否为 `NULL`；
2. 顶点数组长度必须与坐标维度一致，例如二维点表应满足 `raw_coordinate_count == vertex_count * 2`；
3. 边界段数组必须满足每条段有两个合法端点索引；
4. 区域种子数组必须满足坐标有限、区域编号合法、可选尺寸约束为正；
5. 第三方后端返回的顶点数、单元数、边界段数必须重新检查，不能默认可信；
6. 一旦发现非法输入，必须在 UniMesh 边界层返回结构化错误，不能让崩溃发生在第三方库内部。

#### 11.7.2 Layer 3 & Layer 4：交叉比对与解耦工厂级防线

挂载节点：

```text
MeshGenerationRequest
MeshGenerationResult
core 事实模型压力测试
后端注册表与路由策略
```

这些节点的核心风险是：多个后端、多个转换器和多个驱动之间传递的网格对象表面类型正确，但内部几何拓扑已经悄悄损坏。  
因此未来实现必须把运行时不变性断言、数值健康监控和状态落盘作为基础能力，而不是调试阶段的临时补丁。

##### 运行时不变性断言（Runtime Invariants Assertion）

所有网格控制流代码内部必须密集布置条件检查。  
对于开发构建，可以使用 `assert`；对于生产构建，应使用明确的异常、错误码或 `ValidationReport`。

| 不变性对象 | 验收方案 | 量化指标 | 黑箱 Bug 防御机制 |
|---|---|---|---|
| `MeshGenerationRequest` | 构造请求后立即执行 `validate()`。 | 请求中的点、段、区域和尺寸场非法项必须全部被拦截。 | 节点索引不得为负；边界段端点必须落在点表范围内；区域 ID 必须处于合法范围；尺寸场值必须为正且有限。 |
| `MeshGenerationResult` | 后端返回后立即执行结果一致性检查。 | 任意非法连接、负索引、越界索引、空单元表必须触发失败。 | 不信任任何后端输出；每个单元连接必须逐项检查；三角形单元必须有 3 个不同顶点。 |
| `core 事实模型压力测试` | 对 `Geometry`、`ConnectivityTable`、`Marker`、`Attribute`、`DofLayout` 分别建立最小合法样例和非法样例测试。 | 合法样例通过率 100%，非法样例拦截率 100%。 | 将几何维度、实体数量、连接表长度、Marker 绑定范围作为核心断言。 |
| `后端注册表与路由策略` | 对未知后端名、重复注册、能力不匹配和选项缺失进行单元测试。 | 非法路由请求必须 100% 给出可读错误。 | 后端选择不得回退到隐式默认值；能力不满足时必须显式失败。 |

基础几何拓扑硬性规律必须被写成不变性检查：

1. 网格单元节点索引绝对禁止为负；
2. 任意连接表索引必须小于当前节点总数；
3. 三角形必须由三个互不相同的顶点组成；
4. 三角形面积不得低于退化阈值；
5. 边界线段必须由两个不同顶点组成；
6. Marker 绑定的实体 ID 必须存在；
7. Attribute 的长度必须与目标实体集合长度一致，或明确声明为网格级属性；
8. DofLayout 的实体维度、分量数和每实体自由度数必须为合法正值；
9. 后端路由结果必须与请求的能力条件一致；
10. 任意转换器输出给 `core::Mesh` 前必须通过基础 validation。

一旦上述硬性规律被破坏，程序必须立即失败，不能继续向下游驱动传播错误。

##### 数值健康监控（NaN/Inf Tracking）

数值软件中最危险的黑箱缺陷之一，是 `NaN` 或 `Inf` 悄悄穿过多个模块，最后在矩阵装配、插值或求解器阶段才爆炸。  
因此未来所有生成、转换和导出路径必须实施有限性检查。

| 检查对象 | 验收方案 | 量化指标 | 黑箱 Bug 防御机制 |
|---|---|---|---|
| 节点坐标 | 对所有坐标执行 `std::isfinite` 等价检查。 | `NaN` / `Inf` 允许数量为 0。 | 坐标表写入 `Geometry` 前必须检查有限性。 |
| 尺寸场与控制参数 | 对目标边长、最大面积、质量阈值等参数检查正值与有限性。 | 非正值、`NaN`、`Inf` 必须 100% 拦截。 | 参数进入后端前统一消毒，禁止后端自行解释非法值。 |
| 插值系数与局部坐标 | 对未来高阶或插值相关数据执行有限性检查。 | 非有限值允许数量为 0。 | 插值与高阶 DOF 元数据进入 driver 前必须再次验证。 |
| 网格质量指标 | 对面积、角度、长宽比、尺寸场偏差执行有限性检查。 | 所有质量指标必须为有限实数。 | 任何非有限质量指标都视为生成失败或转换失败。 |

最低验收要求：

```text
坐标 NaN/Inf 数量 = 0
尺寸参数 NaN/Inf 数量 = 0
质量指标 NaN/Inf 数量 = 0
连接索引 NaN/Inf 不适用，但必须全部为合法整数
```

##### 中间特征值显式落盘（State Dumping）

为了让人类物理学家无需阅读千行源码，也能判断底层网格流程是否正常，未来所有关键转换器必须预留结构清晰的文本或 CSV Dump 接口。

建议至少支持以下落盘文件：

| Dump 文件 | 内容 | 用途 |
|---|---|---|
| `mesh_summary.txt` | 节点数、边数、面数、单元数、边界段数、区域数、Marker 数量。 | 快速判断网格规模是否符合预期。 |
| `coordinates_sample.csv` | 前若干个节点坐标、坐标维度、坐标有限性标志。 | 检查坐标是否处于合理 R-Z 范围。 |
| `connectivity_sample.csv` | 前若干个单元连接表、索引范围检查结果。 | 检查连接表是否存在负索引或越界。 |
| `quality_metrics.csv` | 面积、最小角、最大角、长宽比、尺寸场偏差。 | 检查网格质量是否恶化。 |
| `marker_summary.csv` | Marker 名称、实体类型、绑定实体数量、合法性标志。 | 检查区域和边界标记是否丢失。 |
| `adjacency_summary.txt` | 邻接边数量、边界边数量、孤立实体数量。 | 检查拓扑邻接是否自洽。 |
| `backend_report.txt` | 后端名称、选项、运行状态、错误消息、耗时。 | 追踪不同后端的行为差异。 |

最低验收要求：

1. 每一次生成或转换流程必须能够输出摘要级 Dump；
2. Dump 文件必须是人类可读文本或 CSV，不应依赖专用二进制查看器；
3. Dump 中必须明确记录后端名称、输入规模、输出规模和 validation 状态；
4. 当 validation 失败时，Dump 仍应尽可能写出失败前的状态，方便定位；
5. Dump 路径必须由 options 控制，避免污染正常运行目录；
6. Dump 不得泄漏第三方后端的私有内存结构，只能输出中立统计特征和可审查样本。

#### 11.7.3 Layer 5：跨网格源验证与回归压力测试级防线

挂载节点：

```text
重复点检测
非法连接检测
退化单元检测
参数扰动稳定性
```

Layer 5 的目标是专门发现几何缺陷。  
未来必须通过自动化脚本，对同一托卡马克 R-Z 边界施加小幅参数扰动，并使用不同后端生成网格，再统一导入 `core::Mesh` 做差分回归测试。

推荐闭环如下：

```text
基准 R-Z 边界
    ↓
参数扰动样本生成
    ↓
Triangle 后端生成
    ↓
研究后端生成
    ↓
统一转换为 core::Mesh
    ↓
几何拓扑 validation
    ↓
质量指标统计
    ↓
GenericSim 导出
    ↓
可选 M3DC1 驱动预检查
    ↓
差分报告与失败日志
```

| 回归对象 | 验收方案 | 量化指标 | 黑箱 Bug 防御机制 |
|---|---|---|---|
| 重复点检测 | 对所有节点执行容差哈希或空间索引检查。 | 在标准测试样例中，未合并的重复点查出后必须被修复或显式报告；最终进入 `core::Mesh` 的非法重复点数量必须为 0。 | 如果重复点未被合并，必须记录点 ID、坐标、距离和来源后端。 |
| 非法连接检测 | 扫描所有单元连接表和边界段连接表。 | 负索引数量 = 0；越界索引数量 = 0；重复顶点单元数量 = 0。 | 任意非法连接必须阻断导出流程，并在日志中给出单元 ID 与非法索引。 |
| 退化单元检测 | 计算三角形面积、最小边长和最小角。 | 面积低于阈值的退化单元数量必须为 0；若出现必须触发失败。 | 退化单元必须输出单元 ID、三个顶点 ID、坐标、面积和来源后端。 |
| 参数扰动稳定性 | 对 R-Z 边界、尺寸场或区域种子施加小扰动，比较输出规模和质量指标变化。 | 节点数、单元数、最小角、长宽比等指标不得出现无解释的剧烈跳变；跳变超过阈值必须进入人工审查。 | 每组扰动必须保留输入参数、后端选项、输出摘要和质量统计，便于复现实验。 |

推荐的基础质量阈值应在未来由人类主管结合物理算例正式确定。  
在正式阈值确定前，至少需要预留以下可配置项：

```text
duplicate_point_tolerance
minimum_triangle_area
minimum_triangle_angle
maximum_aspect_ratio
maximum_size_field_deviation
maximum_allowed_orphan_entities
```

最低验收要求：

1. 自动化测试必须覆盖至少一个基准 R-Z 边界样例；
2. 每个样例必须同时输出 validation report 和 quality report；
3. 凡是出现退化单元，后端必须抛出可追踪的显式诊断日志；
4. 凡是出现非法连接，不允许继续导出到 GenericSim 或 M3DC1；
5. 差分测试必须记录不同后端的节点数、单元数、边界段数、区域标记数；
6. 参数扰动测试必须保留随机种子或扰动参数，保证失败可复现；
7. 回归脚本必须能够在持续集成或本地测试中一键运行。

#### 11.7.4 Layer 6：三源接口基线对齐与自动化集成防线

挂载节点：

```text
建立最小可运行原型
长期架构收敛
```

Layer 6 的风险不再只是单个模块错误，而是多个模块集成后发生内存泄漏、空指针解引用、未定义行为或隐式架构污染。  
因此未来最小可运行原型建立后，必须在自调测阶段启用动态扫描工具。

| 集成对象 | 验收方案 | 量化指标 | 黑箱 Bug 防御机制 |
|---|---|---|---|
| 最小可运行原型 | 构造从样例输入到 `core::Mesh`，再到 GenericSim 导出的最短链路。 | 样例链路必须稳定运行，validation 必须通过，Dump 必须生成。 | 任何一步失败都必须返回结构化错误，不允许静默跳过。 |
| AddressSanitizer (ASan) | 在 Debug 或 Sanitizer 构建中运行核心测试与端到端样例。 | 堆越界、栈越界、use-after-free、double-free 报告数量必须为 0。 | 一旦 ASan 报错，相关变更不得进入主线。 |
| UndefinedBehaviorSanitizer (UBSan) | 对整数溢出、非法转换、未对齐访问等执行动态检测。 | UBSan 未定义行为报告数量必须为 0。 | 一旦 UBSan 报错，必须先修复再继续功能开发。 |
| 长期架构收敛 | 在每轮蓝图升级前执行目录边界和关键字扫描。 | `src/core/` 中后端私有 API 与下游私有语义命中数必须为 0。 | 防止为了跑通样例而把 Triangle、M3DC1 或研究代码私有概念写入核心层。 |

未来建议在构建系统中预留类似如下构建模式：

```text
Debug
Release
RelWithDebInfo
Sanitizer
```

其中 `Sanitizer` 构建至少应启用：

```text
AddressSanitizer
UndefinedBehaviorSanitizer
```

在条件允许时，可进一步考虑：

```text
LeakSanitizer
ThreadSanitizer
```

最低验收要求：

1. Sanitizer 构建必须能覆盖核心层基础单元测试；
2. Sanitizer 构建必须能覆盖至少一个端到端样例；
3. ASan 报告的内存错误数量必须为 0；
4. UBSan 报告的未定义行为数量必须为 0；
5. 空指针解引用数量必须为 0；
6. 未释放的长期堆内存泄漏必须为 0；
7. 若未来引入多线程或并行生成后端，必须增加线程竞争检测策略；
8. 每轮蓝图升级前必须重新运行边界扫描、validation 测试和端到端回归。

#### 11.7.5 总体验收矩阵

下表将 6 层研发树中的关键防线压缩为一张总体验收矩阵，供后续编码阶段逐项打钩。

| BFS 层级 | 关键节点 | 必须实现的验收动作 | 硬性指标 |
|---|---|---|---|
| Layer 1 | 三源宏观哨探 | 不因单一参考源修改核心蓝图。 | 每轮蓝图升级必须基于已完成的调研与技术文档。 |
| Layer 2 | FFI 与下游私有语义隔离 | 原生指针、后端结构体、下游私有概念全部隔离。 | `src/core/` 私有关键字命中数 = 0；非法指针进入第三方库数量 = 0。 |
| Layer 3 | 生成请求、结果与后端路由 | 请求、结果、路由全部执行 validation。 | 非法请求拦截率 100%；未知后端静默回退次数 = 0。 |
| Layer 4 | core/generation/drivers 边界测试 | 运行时不变性断言、NaN/Inf 检查、Dump 接口。 | 非法索引数量 = 0；NaN/Inf 数量 = 0；关键流程可生成 Dump。 |
| Layer 5 | 跨源回归与几何缺陷检测 | 差分回归、质量阈值、端到端闭环测试。 | 退化单元数量 = 0；负索引数量 = 0；越界索引数量 = 0。 |
| Layer 6 | 三源接口基线对齐与原型交付 | 三源接口基线入蓝图、最小原型、ASan、UBSan、端到端验证。 | 内存错误 = 0；未定义行为 = 0；空指针解引用 = 0。 |

#### 11.7.6 对未来编码代理的强制执行提示

后续任何 AI 或人类开发者在实现相关模块时，应把本节视为测试与防御清单，而不是附属说明。  
尤其需要遵守以下工程纪律：

1. 先写数据边界检查，再写后端调用；
2. 先写 validation，再写 writer；
3. 先保证 Dump 可读，再追求性能优化；
4. 先用 GenericSim 验证中立性，再进入 M3DC1 私有适配；
5. 先用 Sanitizer 清零底层错误，再扩大样例规模；
6. 任何失败都必须可定位、可复现、可解释；
7. 任何私有语义都必须留在对应隔离层内；
8. 任何不能通过 validation 的网格都不允许进入下游求解器；
9. 任何功能代码实现前，都必须先完成对应调研、技术文档和总蓝图升级。

这样做的目的，是把 UniMesh 从“能生成结果的脚本”提升为“能承受多后端、多驱动、多阶段回归压力的数值软件工程系统”。

### 11.8 对人类研究员的直观理解

可以把 UniMesh 的长期路线理解为三条输入输出链路的统一：

```text
上游生成器：TokaMaker / TRIMEG / 研究代码
        ↓
UniMesh core：中立网格事实
        ↓
下游求解器：GenericSim / M3DC1 / 未来程序
```

其中：

- 生成器负责“网格怎么产生”；
- core 负责“网格作为数学对象是什么”；
- driver 负责“网格如何交给某个具体求解器使用”。

BFS 研发图谱的目的，就是保证我们每走一步都知道自己处在哪一层，不把生成算法、核心事实和下游私有语义混在一起。

更直白地说：

```text
先调研清楚
    ↓
写成技术文档
    ↓
改总蓝图
    ↓
再写代码
```

这条顺序不能反过来。
