# TOKAMAKER 网格生成链路与 UniMesh 架构对齐白皮书

## 1. 文档定位

本文档记录 UniMesh 项目在外部参考代码宏观哨探阶段，对 TOKAMAKER / OpenFUSION Toolkit 网格生成链路与 Triangle 库集成方式的第一层结构化分析。

本轮分析严格基于以下只读技术资产：

- `TOKAMAKER/oft-meshing-architecture/SKILL.md`
- `TOKAMAKER/triangle-library-integration/SKILL.md`
- `UniMesh_Architecture_Plan.md`
- `CONTEXT.md`

本文档不直接分析尚未加载的外部源码文件，不对未读取的实现细节进行推测。本文的作用是：

1. 从宏观层面对齐 TOKAMAKER 的二维三角网格生成事实与 UniMesh 的通用网格内核规划；
2. 评估当前 `src/core/` 抽象是否足以覆盖 Triangle 风格的二维非结构化网格拓扑事实；
3. 明确下一轮 BFS 第二层源码侦察所需物理拉取清单；
4. 为后续是否引入独立网格生成层提供架构观察点。

---

## 2. 宏观调用链路概览

根据 `TOKAMAKER/oft-meshing-architecture/SKILL.md`，TOKAMAKER / OFT 的三角网格生成链路可以抽象为以下分层结构：

```text
Python 用户层
gs_Domain.build_mesh()
    - 管理几何区域
    - 定义 plasma / vacuum / boundary / conductor / coil 等区域语义
    - 调用 Mesh 类生成网格

        ↓

Python 中间层
Mesh 类
    - 点合并
    - 边界段合并与拆分
    - 共享边界处理
    - 边界重采样
    - 区域标记点生成
    - 构造 Triangle 输入字典

        ↓

Python 封装层
run_triangle(alpha)
    - 将 Python dict 转换为 C 风格 triangle_struct
    - 通过 ctypes 调用 oft_triangulate
    - 将 Triangle 输出转换为 NumPy 数组

        ↓

Python ctypes 接口层
_interface.py
    - 动态加载 liboft_triangle
    - 绑定 triangulate 函数签名

        ↓

共享库层
liboft_triangle.so / liboft_triangle.dylib / liboft_triangle.dll
    - 导出 triangulate 符号

        ↓

C 源码层
src/ext_libs/triangle.c
    - triangulate()
    - intern_triangulate()
    - Delaunay 三角化与质量优化
```

该链路体现了科学计算软件中常见的混合语言分层模式：

```text
高层几何与区域建模
        ↓
中层拓扑清洗与离散化预处理
        ↓
跨语言封装
        ↓
底层 C 语言网格生成算法内核
```

---

## 3. TOKAMAKER / Triangle 暴露的核心网格事实

当前 Skill 文本明确提到，TOKAMAKER 在调用 Triangle 前会构造类似如下输入结构：

```python
alpha = {
    "vertices": self._resampled_points,
    "segments": resampled_flat,
    "regions": self._reg_defs,
}
```

这些对象可解释为：

| 名称 | 形态 | 网格含义 |
|---|---|---|
| `vertices` | `[N, 2]` | 二维边界点坐标表 |
| `segments` | `[M, 2]` | 边界线段连接表 |
| `regions` | `[K, 4]` | 区域内部标记点、区域 ID 与最大面积约束 |

其中 `regions` 通常具有如下逻辑结构：

```text
[x, y, region_id, max_area]
```

含义分别是：

| 字段 | 含义 |
|---|---|
| `x` | 区域内部标记点的第一坐标 |
| `y` | 区域内部标记点的第二坐标 |
| `region_id` | 区域编号或区域属性 |
| `max_area` | 该区域允许的最大三角形面积约束 |

从高阶网格事实角度看，这些对象并不是某个下游求解器的私有有限元语义，而是二维分段线性复合体与三角剖分前处理中的通用事实。

---

## 4. 与 UniMesh 核心层规划的抽象能力对齐

根据 `UniMesh_Architecture_Plan.md`，UniMesh 当前 `src/core/` 规划包含以下中立组件：

```text
Mesh
Geometry
ConnectivityTable
TopologyGraph
Marker
Attribute
Metadata
DofLayout
PartitionInfo
ValidationReport
```

这些组件的设计目标是表达求解器无关、物理模型无关、格式无关的通用网格事实。

### 4.1 `vertices` 与 UniMesh 几何层对齐

TOKAMAKER / Triangle 的 `vertices` 本质是节点坐标矩阵。它可以自然映射到 UniMesh 的：

```text
Geometry
CoordinateTable
Mesh
```

对应关系如下：

| TOKAMAKER / Triangle | UniMesh core | 是否自然匹配 |
|---|---|---|
| `vertices` | `Geometry` / `CoordinateTable` | 是 |
| 点坐标 `[x, y]` | 坐标矩阵中的一行 | 是 |
| 二维坐标维度 | `Geometry` 的坐标维度元信息 | 是 |

因此，`vertices` 不要求 UniMesh 核心层引入新概念。

### 4.2 `segments` 与 UniMesh 连接表和拓扑层对齐

TOKAMAKER / Triangle 的 `segments` 是边界线段连接表，通常每一行包含两个顶点索引。

它可以自然映射到 UniMesh 的：

```text
MeshEntity
ConnectivityTable
TopologyGraph
```

对应关系如下：

| TOKAMAKER / Triangle | UniMesh core | 是否自然匹配 |
|---|---|---|
| `segments` | Edge 实体连接表 | 是 |
| 线段端点索引 | `ConnectivityTable` 中 Edge 到 Vertex 的连接关系 | 是 |
| 边界段集合 | `Marker` 或实体集合 | 是 |
| 共享边界处理后的边 | `TopologyGraph` 可表达的实体邻接事实 | 是 |

因此，`segments` 也不要求 UniMesh 核心层引入 Triangle 专属结构。

### 4.3 `regions` 与 UniMesh Marker / Attribute 对齐

`regions` 是本轮最需要谨慎处理的对象，因为它同时包含两类不同性质的信息：

1. 区域标识信息；
2. 网格生成约束信息。

其中 `region_id` 可以自然映射到 UniMesh 的：

```text
Marker
Attribute
```

但 `max_area` 更接近网格生成阶段的尺寸约束，不应被误认为最终网格的基本拓扑事实。

对应关系如下：

| `regions` 字段 | UniMesh 中的合理表达 | 是否自然匹配 | 备注 |
|---|---|---:|---|
| 区域内部点坐标 | `Attribute` 或未来生成层输入结构 | 基本匹配 | 它是生成器输入种子点，不一定是最终网格实体。 |
| `region_id` | `Marker` / `Attribute` | 是 | 可表达区域编号或区域归属。 |
| `max_area` | 未来网格生成层约束参数，或临时 Attribute | 需谨慎 | 不建议固化为 `src/core/` 的专用字段。 |

因此，`regions` 中的区域编号属于通用标记能力，而区域面积约束更适合放在未来的生成层或后端输入适配层。

---

## 5. 核心结论：当前 UniMesh 内核抽象是否足够

本轮宏观比对结论如下：

```text
UniMesh 当前 src/core/ 规划已经能够覆盖 TOKAMAKER / Triangle 暴露的二维非结构化网格基本拓扑事实。
```

具体理由包括：

1. `vertices` 可以由 `Geometry` / `CoordinateTable` 表达；
2. `segments` 可以由 `ConnectivityTable` / `MeshEntity` / `TopologyGraph` 表达；
3. `region_id` 可以由 `Marker` / `Attribute` 表达；
4. 区域附加信息可以通过 `Attribute` 或 `Metadata` 辅助表达；
5. Triangle 的 C API、switch 字符串和 `triangulateio` 结构不应进入 `src/core/`。

因此，本轮不建议修改 `UniMesh_Architecture_Plan.md` 中关于 `src/core/` 的基础抽象规划。

---

## 6. 关键架构边界：生成输入不等于核心网格事实

本轮最重要的架构边界是：

```text
Triangle 的输入 PLC 数据结构
        ≠
UniMesh core 的最终通用网格内核
```

二者存在交集，但职责不同。

### 6.1 Triangle / TOKAMAKER 输入更接近生成前描述

Triangle 所需的 `vertices`、`segments`、`regions` 更接近：

```text
几何边界定义
边界离散采样
区域种子点
局部网格尺寸约束
Triangle 后端输入
```

### 6.2 UniMesh core 应表达生成后或导入后的通用网格事实

UniMesh `src/core/` 应主要表达：

```text
节点坐标
实体连接
拓扑邻接
实体标记
实体属性
网格元数据
自由度布局
并行分区信息
```

### 6.3 不应上浮到 core 的内容

以下内容不应进入 UniMesh `src/core/`：

```text
Triangle switch 字符串
triangulateio C 结构体
ctypes 调用细节
pqaAzQ 控制参数
Triangle 特定内存释放规则
OFT 专属 region_info 语义
plasma / vacuum / conductor / coil 等具体物理区域角色
```

这些内容如果未来需要进入 UniMesh，应被隔离在生成层、工具层或具体后端适配层，而不是通用核心层。

---

## 7. 未来架构观察点：多后端可插拔网格生成工厂

本节是基于 TOKAMAKER / Triangle 宏观链路得到的专项架构观察，不直接修改全局蓝图文件。  
在未完成卢志鑫与唐成曜两位研究员网格代码的全量源码交叉比对之前，本节仅提出生成层演进方向、隔离原则与蓝图升级草案，供后续正式审查使用。

### 7.1 从单一生成层升级为多后端可插拔工厂

原先对未来 `src/generation/` 的设想，是在 UniMesh 中增加一个独立网格生成层，用于表达生成前的边界、区域和尺寸约束，并将 Triangle 这类第三方算法后端的输出转换为 `src/core/` 可消费的中立网格事实。

经过对 TOKAMAKER / Triangle 调用链路的宏观比对后，更合理的长期定位应升级为：

```text
src/generation/
    多后端可插拔网格生成工厂
    Multi-backend Pluggable Mesh Generation Factory
```

该层不应被设计成单一 Triangle 包装器，也不应被设计成某一个研究代码的专属入口。它应当成为一个可容纳多个网格生成引擎并行存在的抽象工厂层，通过统一接口把不同来源、不同语言、不同算法取向的生成器隔离在 UniMesh 通用内核之外。

其长期目标可以概括为：

```text
统一生成请求
        ↓
选择具体生成后端
        ↓
执行后端私有网格生成流程
        ↓
清洗与标准化输出
        ↓
构造 UniMesh core::Mesh 中立对象
```

### 7.2 多后端并存的工程动机

未来 UniMesh 面向的网格生成需求可能并不只有一种。不同上游网格生成代码可能在以下方面存在明显差异：

| 维度 | 快型生成后端 | 质型生成后端 |
|---|---|---|
| 主要目标 | 极限生成速度、快速参数扫描、批量样例生产 | 高质量网格、复杂几何适应、高阶有限元友好 |
| 拓扑优化倾向 | 倾向快速构造可用三角化或四边形化结果 | 倾向更强的局部质量控制、边界贴合和自适应调整 |
| 典型适用场景 | 大量扫描、前期测试、几何粗筛 | 高阶有限元、强梯度区域、精细物理计算 |
| 对 UniMesh 的要求 | 快速转换为中立坐标与连接表 | 保留更多质量指标、生成约束与局部自适应元数据 |
| 后端隔离重点 | 防止速度优化代码污染核心抽象 | 防止复杂质量控制策略上浮为核心私有语义 |

因此，`src/generation/` 应支持多个候选生成引擎同时存在。例如：

```text
generation factory
├── TriangleBackend
├── ResearcherA_FastBackend
├── ResearcherB_QualityBackend
└── FutureBackend
```

其中，卢志鑫与唐成曜两位研究员的网格代码可以作为首批候选生成引擎进入后续侦察范围。  
但在完成其源码目录结构、输入输出格式、语言边界、内存模型、几何约束表达方式和网格质量策略的全量交叉比对之前，不能预先裁定：

1. 它们分别应归入快型后端还是质型后端；
2. 它们是否适合直接编译进 UniMesh；
3. 它们是否应通过文件接口、库接口、进程接口或脚本接口调用；
4. 它们的最终模块名、类名、调用栈和目录位置；
5. 它们是否需要共享一套几何预处理前端。

因此，本白皮书仅将两者定位为：

```text
首批候选生成后端
```

而不是已经确定的正式架构组件。

### 7.3 生成层的统一抽象边界

多后端生成工厂的关键不是统一所有算法内部细节，而是统一它们对 UniMesh 暴露的最小公共契约。

该契约至少应包括三类对象：

```text
MeshGenerationRequest
MeshGenerationOptions
MeshGenerationResult
```

其职责可描述为：

| 抽象对象 | 职责 |
|---|---|
| `MeshGenerationRequest` | 表达生成前的中立几何输入，例如边界点、边界段、区域种子、几何环和约束集合。 |
| `MeshGenerationOptions` | 表达后端无关或可降级解释的生成选项，例如目标尺寸、质量阈值、调试输出、严格校验模式。 |
| `MeshGenerationResult` | 表达生成后的中立网格结果，包括坐标、单元连接、边界实体、区域标记、质量诊断和后端运行报告。 |

这些对象不应直接暴露任何后端的原生数据结构。  
例如，对于 Triangle 后端，`MeshGenerationRequest` 可以被后端适配器转换为 `triangulateio`；但 `triangulateio` 本身不能成为 `MeshGenerationRequest` 的字段，也不能被 `src/core/` 依赖。

从层次上看，合理边界应是：

```text
UniMesh generation abstract API
        ↓
TriangleBackend adapter
        ↓
triangle_struct / triangulateio / triangulate()
```

而不是：

```text
UniMesh core::Mesh
        ↓
triangulateio
        ↓
triangulate()
```

后一种设计会把后端 C API 直接绑定到核心内核，是应当明确禁止的架构反模式。

### 7.4 生成层的隔离壁垒

`src/generation/` 的首要工程职责，是阻断上游生成算法的私有实现细节向 UniMesh 核心层扩散。

对于 Triangle 这类 C 库后端，需要隔离的内容包括：

```text
C API 函数签名
原生指针
ctypes 或 FFI 绑定细节
triangulateio / triangle_struct
switch 字符串
后端专属编译宏
后端专属内存释放规则
后端专属错误码
后端专属控制参数
```

对于未来卢志鑫与唐成曜两位研究员的网格代码，也应采用同样隔离原则。无论其代码最终采用 C、C++、Fortran、Python 还是混合语言实现，以下内容都不应越过生成层进入 UniMesh 核心：

```text
研究代码内部数组布局
私有几何对象
私有拓扑清洗策略
私有质量优化参数名
私有文件中间格式
私有内存管理约定
私有并行划分假设
私有调试输出格式
```

生成层应将这些后端私有细节统一翻译为：

```text
core::Mesh
core::Geometry
core::ConnectivityTable
core::Marker
core::Attribute
core::Metadata
core::ValidationReport
```

换言之，UniMesh 核心层只接收“生成结果形成的中立网格事实”，不接收“生成算法内部如何得到这些事实”的过程细节。

### 7.5 后端替换不应改变核心层事实模型

多后端工厂设计必须满足一个基本可替换性条件：

```text
更换生成后端
        ≠
修改 core::Mesh 数据模型
```

例如，Triangle 后端、快速研究后端和高质量自适应研究后端都可能生成二维三角网格，但它们的内部路径完全不同：

```text
TriangleBackend
    PLC 输入
    triangulateio
    triangulate()
    输出三角形网格

ResearchFastBackend
    私有快速几何离散流程
    私有拓扑构造流程
    输出三角形或混合网格

ResearchQualityBackend
    私有质量优化流程
    私有自适应调整流程
    输出高质量三角形或混合网格
```

这些后端最终都必须收敛到同一类中立结果：

```text
节点坐标矩阵
单元连接表
边界实体集合
区域或材料标记
可选质量指标
可选生成过程元数据
```

其中，质量指标与生成过程元数据应以通用 `Attribute` 或 `Metadata` 形式进入 UniMesh，而不应作为某个后端名称绑定的核心字段。

### 7.6 对卢志鑫与唐成曜代码的战略悬空处理

由于当前阶段尚未读取两位研究员代码的真实源码，本白皮书对其只作如下克制定位：

1. 它们是未来 `src/generation/` 多后端工厂的首批候选后端；
2. 它们可能分别代表不同的生成速度、质量优化和高阶有限元适配取向；
3. 它们的最终封装方式必须等待源码级交叉比对后决定；
4. 在完成比对前，不应把任何一个研究代码的私有术语写入 UniMesh 核心层；
5. 不应把任何一个研究代码的目录结构、函数名、参数名或文件格式预先固化到全局蓝图中。

后续交叉比对时，建议至少从以下维度建立对照表：

| 比对维度 | 需要确认的问题 |
|---|---|
| 输入几何表达 | 使用点线段、曲线、隐式边界、CAD 几何，还是私有格式？ |
| 输出网格类型 | 三角形、四边形、混合单元，还是高阶曲边单元？ |
| 网格质量控制 | 是否支持最小角、最大面积、边长场、各向异性尺寸场？ |
| 拓扑清洗策略 | 是否合并重复点、拆分共享边、修复小边和退化单元？ |
| 语言与构建方式 | C、C++、Fortran、Python 或混合语言？ |
| 调用方式 | 库调用、文件交换、命令行子进程，还是脚本 API？ |
| 内存模型 | 调用方分配、被调用方分配，还是内部缓存？ |
| 错误处理 | 返回码、异常、日志文件，还是标准输出？ |
| 并行能力 | 单进程、OpenMP、MPI，还是 GPU 加速？ |
| 与高阶 FEM 的关系 | 是否支持曲边、边界贴合、自适应细化或高阶节点？ |

只有在这些事实被实际源码和文档确认之后，才允许决定它们在 `src/generation/` 中的正式模块命名和调用栈。

### 7.7 蓝图升级提案权与正式审查红线

基于上述分析，当前 `UniMesh_Architecture_Plan.md` 的主线架构已经很好地定义了 `src/core/` 与 `src/drivers/`，但尚未正式纳入 `src/generation/` 这一多后端网格生成工厂层。

这并不构成当前核心层设计错误，但从长期架构看，若 UniMesh 需要同时吸收 Triangle、卢志鑫研究代码、唐成曜研究代码以及未来更多生成器，则全局蓝图应在正式审查后补充生成层章节。

本白皮书在此提出蓝图升级草案，但不直接修改 `UniMesh_Architecture_Plan.md`。  
在主管正式审查并授权前，任何工具都不应自动改写全局蓝图文件。

### 7.8 提交给主管审查的蓝图升级草案

以下是建议提交给人类主管进行正式审查的 `UniMesh_Architecture_Plan.md` 扩展草案。

#### 7.8.1 总体架构描述建议

建议将 UniMesh 总体结构从：

```text
core/
drivers/
utils/
```

扩展为：

```text
generation/
core/
drivers/
utils/
```

其职责分工为：

| 层级 | 职责 |
|---|---|
| `src/generation/` | 多后端可插拔网格生成工厂，封装 Triangle、研究代码和未来生成器，将生成结果转换为 UniMesh 中立网格对象。 |
| `src/core/` | 通用非结构化网格内核，只表达生成后或导入后的中立网格事实。 |
| `src/drivers/` | 下游模拟软件驱动层，将 UniMesh 中立网格对象翻译为外部求解器可消费格式。 |
| `src/utils/` | 通用工程辅助模块。 |

#### 7.8.2 建议新增目录树草案

建议在正式蓝图中增加如下候选目录结构：

```text
src/
├── generation/
│   ├── mesh_generator.h
│   ├── mesh_generator.cc
│   ├── generation_request.h
│   ├── generation_request.cc
│   ├── generation_options.h
│   ├── generation_options.cc
│   ├── generation_result.h
│   ├── generation_result.cc
│   ├── generation_registry.h
│   ├── generation_registry.cc
│   │
│   ├── triangle/
│   │   ├── triangle_backend.h
│   │   ├── triangle_backend.cc
│   │   ├── triangle_adapter.h
│   │   └── triangle_adapter.cc
│   │
│   └── research/
│       ├── README.md
│       └── candidate_backends.md
```

其中 `research/` 在早期只用于记录候选后端侦察结果，不应在源码未确认前固化卢志鑫或唐成曜代码的具体模块名。

#### 7.8.3 建议新增公共接口语义草案

建议在蓝图中描述如下抽象接口：

```cpp
class MeshGenerator {
public:
  virtual ~MeshGenerator() = default;

  virtual std::string name() const = 0;

  virtual GenerationCapabilities capabilities() const = 0;

  virtual GenerationResult generate(const GenerationRequest& request,
                                    const GenerationOptions& options) const = 0;
};
```

该接口应满足：

1. 不暴露 Triangle 的 `triangulateio`；
2. 不暴露任何研究代码私有数组布局；
3. 不要求调用方理解后端内部参数名；
4. 只返回可转换为 `core::Mesh` 的中立结果；
5. 通过注册表实现后端选择。

#### 7.8.4 建议新增隔离红线草案

建议在蓝图中明确加入如下禁止规则：

```text
src/core/ 禁止包含任何网格生成后端私有 API。
src/core/ 禁止包含 Triangle triangulateio、switch 字符串、C 指针绑定和后端编译宏。
src/core/ 禁止包含卢志鑫或唐成曜研究代码的私有数据结构、私有参数名和私有文件格式语义。
src/generation/ 可以封装后端私有逻辑，但必须将输出转换为 core 可表达的中立网格事实。
```

#### 7.8.5 建议新增开发顺序草案

考虑当前 UniMesh 已有主线，建议生成层不要立即打断核心层与 GenericSim 驱动开发。更稳妥的顺序是：

```text
第一阶段：完成 core 最小闭环
第二阶段：完成 generic 参考驱动
第三阶段：完成 DofLayout 泛化表达
第四阶段：建立 generation 抽象接口与 Triangle 原型后端
第五阶段：对卢志鑫与唐成曜代码进行交叉比对并决定是否接入
第六阶段：推进 M3DC1 真实驱动验收
```

如果工程目标需要优先验证上游生成能力，也可以在主管授权后将第四阶段提前为并行支线，但不应牺牲 `src/core/` 的中立性。

### 7.9 本节结论

本节形成如下架构判断：

1. `src/generation/` 不应只是 Triangle 的包装层，而应升级为多后端可插拔网格生成工厂；
2. Triangle、卢志鑫研究代码、唐成曜研究代码和未来生成器都应以候选后端方式接入；
3. 所有后端私有 C API、原生指针、结构体、控制参数和内部数组布局必须被隔离在生成层内部；
4. `src/core/` 只接收生成后的中立网格事实，不接收生成算法内部过程；
5. 当前白皮书仅提出 `UniMesh_Architecture_Plan.md` 的升级草案，是否落入全局蓝图需等待主管正式审查与授权。

---

## 8. Triangle 集成规范对 UniMesh 的工程启发

根据 `TOKAMAKER/triangle-library-integration/SKILL.md`，Triangle 集成有以下关键事实：

| 项目 | 工程含义 |
|---|---|
| `triangulate()` | Triangle C API 主入口 |
| `struct triangulateio` | C 侧输入输出结构体 |
| `TRILIBRARY` | 将 Triangle 编译为库而不是可执行程序 |
| `ANSI_DECLARATORS` | 使用 ANSI C 函数声明 |
| `NO_TIMER` | 禁用计时器依赖 |
| `REAL=double` | 使用双精度浮点数 |
| `VOID=void` | 定义返回类型 |
| `"pqaAzQ"` | OFT 当前使用的 Triangle 控制字符串 |
| `pointlist` | 点坐标列表 |
| `segmentlist` | 边界线段列表 |
| `regionlist` | 区域点、区域属性和最大面积约束 |

对 UniMesh 的工程启发是：

1. Triangle 应被视为可替换的网格生成后端；
2. Triangle 的数据结构不应成为 UniMesh 的核心数据结构；
3. UniMesh 应接收或输出中立网格事实，而不是直接暴露 Triangle 的 C 结构体；
4. 如果未来接入 Triangle，应通过隔离层完成后端调用与数据转换；
5. Python `ctypes` 集成经验可作为参考，但不应预设 UniMesh 必须采用 Python 作为调用层。

---

## 9. BFS 第二层源码侦察清单

本节清单仅基于当前 Skill 文本明确提及的组件路径。  
在实际源码文件被物理加入并读取之前，不对其内部实现进行任何主观推测。

### 9.1 TOKAMAKER / OFT Python 网格生成链路源码

| 优先级 | 建议拉取文件 | 来源依据 | 侦察目的 |
|---:|---|---|---|
| 1 | `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` | `oft-meshing-architecture/SKILL.md` 明确提及 | 读取 `gs_Domain`、`Mesh`、`run_triangle()` 的真实实现，确认点合并、边界段处理、区域标记点生成和 Triangle 输入构造逻辑。 |
| 2 | `src/python/OpenFUSIONToolkit/TokaMaker/_interface.py` | `oft-meshing-architecture/SKILL.md` 明确提及 | 读取 `ctypes` 动态库加载、Triangle 结构体绑定和 C 接口签名定义方式。 |

### 9.2 Triangle C 层源码与构建文件

| 优先级 | 建议拉取文件 | 来源依据 | 侦察目的 |
|---:|---|---|---|
| 3 | `src/ext_libs/triangle.c` | 两份 Skill 均明确提及 | 读取 `triangulate()`、`intern_triangulate()`、`triangulatepolygon()` 等入口附近实现，确认 OFT 编译集成的 C 入口。 |
| 4 | `src/ext_libs/CMakeLists.txt` | `oft-meshing-architecture/SKILL.md` 明确提及 | 确认 OFT 对 Triangle 的编译宏定义、共享库目标名和构建方式。 |
| 5 | `src/ext_libs/triangle.h` 或 OFT 中对应的 Triangle 头文件 | `triangle-library-integration/SKILL.md` 明确 Triangle 标准结构 | 如果 OFT 仓库中存在该头文件，应读取以核对 `triangulateio` 结构体字段顺序与跨语言绑定一致性。 |

### 9.3 构建产物和符号检查

| 优先级 | 建议查看对象 | 注意事项 | 侦察目的 |
|---:|---|---|---|
| 6 | `build_release/bin/liboft_triangle.*` | 构建产物，不应作为源码修改对象 | 仅用于验证动态库名称、路径和运行时加载方式。 |
| 7 | `nm` 或等价符号检查结果 | 不是源码文件 | 验证是否导出 `triangulate`、`intern_triangulate` 等符号。 |

### 9.4 下一轮建议加入聊天的最小源码批次

为了保持 BFS 第二层侦察克制，建议下一轮优先加入以下文件：

```text
src/python/OpenFUSIONToolkit/TokaMaker/meshing.py
src/python/OpenFUSIONToolkit/TokaMaker/_interface.py
src/ext_libs/triangle.c
src/ext_libs/CMakeLists.txt
```

如果仓库中存在 Triangle 头文件，再补充：

```text
src/ext_libs/triangle.h
```

---

## 10. 对 UniMesh 当前开发路线的建议

基于本轮宏观比对，建议 UniMesh 继续保持当前主线：

```text
先完成 src/core/ 中立网格内核
        ↓
再完成 drivers/generic/ 参考驱动
        ↓
再处理 DofLayout 泛化表达
        ↓
最后进入 drivers/m3dc1/ 真实下游适配
```

TOKAMAKER / Triangle 暂时不应改变当前主线优先级。它们当前更适合作为：

1. 二维三角网格生成链路参考；
2. 未来 mesh generation 层的设计输入；
3. Triangle 后端集成规范参考；
4. 外部网格生成器如何向 UniMesh core 提供坐标、连接表、标记和属性的样本。

---

## 11. 总结

本轮 TOKAMAKER 宏观哨探形成以下结论：

1. TOKAMAKER 的网格生成链路具有清晰的 Python 拓扑预处理到 C Triangle 后端的分层结构；
2. Triangle 输入中的 `vertices`、`segments`、`regions` 可被解释为二维非结构化网格生成前的通用几何拓扑事实；
3. UniMesh 当前 `src/core/` 规划已经能够表达生成后的点坐标、边界连接、区域标记和附加属性；
4. `max_area`、Triangle switch、`triangulateio` 等内容属于生成器约束或后端实现细节，不应进入通用核心层；
5. 当前不建议修改 `UniMesh_Architecture_Plan.md` 的核心层规划；
6. 未来如需接入网格生成能力，应考虑新增独立生成层，而不是污染 `src/core/`；
7. 下一步应物理拉取并只读分析 `meshing.py`、`_interface.py`、`triangle.c`、`CMakeLists.txt` 以及可选的 `triangle.h`。

本文件作为 TOKAMAKER 第一层宏观哨探成果归档，供后续 BFS 第二层源码逆向分析使用。
