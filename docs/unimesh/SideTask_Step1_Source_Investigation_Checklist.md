# SideTask_Step1_Source_Investigation_Checklist

- 文档主受众：Hybrid-Control
- Aider 执行用途：为 Step 2 源码只读侦察生成优先级清单
- 人类阅读用途：帮助主管理解导师支线任务需要先查哪些源码区域
- 场外架构师检索用途：后续通过知识库召回本支线任务的源码侦察入口、事实边界和待确认点
- 当前任务：导师支线任务 Step 1：文献驱动生成源码调研清单（路径已基于真实地图强制锚定，白皮书交叉核验完成）
- 当前状态：Step 1 最终版 v2 / 路径已对齐真实 reference_map / 白皮书交叉核验补全 / 待主管审阅后进入 Step 2
- 最高依据：主管本轮授权 + 已提供文献和参考资料 + tokamaker_reference_map.txt + m3dc1_reference_map.txt
- 事实边界：本报告只规划后续源码调研入口，不构成源码事实确认，不构成主线开发完成
- 当前禁止事项：不得修改源码；不得进入 Step 2 源码细读；不得把推断写成已确认源码事实

---

## 1. Step 1 任务识别

本轮任务是主管授权的【支线任务 Step 1】，来源于主管与导师讨论后的临时调研需求。

本轮只做文献/资料驱动的源码调研清单规划，具体包括：
- 阅读主管已提供的参考工程说明文档、架构白皮书、路径索引文件和只读参考资料；
- 分析不同程序网格数据格式之间的差别；
- 评估从网格生成/描述链路转换到物理求解/数据消费链路时缺失哪些信息；
- 生成后续 Step 2 必须调研的源码文件、目录、模块、函数入口或数据结构入口清单。

本轮严格禁止：
- 修改任何源码、构建脚本、测试、示例或配置文件；
- 进入具体源码逐行分析；
- 把文献推断写成源码已确认事实；
- 推进 UniMesh 主线 Layer 状态；
- 触碰 STUDIO_CONTEXT.md 或任何场外架构师专用上下文文件。

---

## 2. 文献与资料依据清单

| 编号 | 资料/文献/说明材料 | 资料类型 | 提供的关键信息 | 用于推导哪些源码调研方向 | 事实状态 |
|---|---|---|---|---|---|
| R1 | `docs/tokamaker/TOKAMAKER_Architecture_Whitepaper.md` | 架构白皮书 | TokaMaker/OFT 网格生成链路全景：`gs_Domain.build_mesh()` → `Mesh` 类 → `run_triangle()` → ctypes → `liboft_triangle.so` → `triangle.c`；Triangle 输入结构 `vertices/segments/regions`；`regions` 字段含义 `[x, y, region_id, max_area]`；BFS 第二层源码侦察清单（第9节）；多后端生成工厂架构草案（第7节）；Triangle 集成规范（第8节） | Triangle 输入格式解析入口；Python 封装层；ctypes 绑定；C 层 `triangulate()` 入口；区域标签处理路径；格式转换工具侦察方向；基函数侦察方向 | [资料已读，本轮交叉核验完成] |
| R2 | `docs/m3dc1/M3DC1_Architecture_Whitepaper.md` | 架构白皮书 | M3DC1 使用高阶 C1 有限元、隐式时间推进、PETSc/Krylov；`m3dc1_scorec` 承担网格读取、几何模型绑定、场变量、矩阵、线性系统、适配、解转移；网格消费链路需要区域标记、边界标记、高阶自由度布局、几何拓扑一致性和并行分区信息；速度场与磁矢势以标量势变量 `U/omega/chi/psi/f` 表示；后续只读侦察清单（第7节）；`m3dc1_scorec` 内部模块结构（第4.2节）含 `ReducedQuintic`/`BSpline`/`Expression` 基函数模块 | `m3dc1_scorec` API 层；mesh/model/field/matrix/ls 模块；Fortran 主程序骨架；单元积分与矩阵装配；适配与解转移链路；高阶 DOF 绑定；基函数与表达式模块 | [资料已读，本轮交叉核验完成] |
| R3 | `docs/m3dc1/m3dc1_reference_map.txt` | 文件路径索引 | M3DC1 完整文件路径列表，包括 `m3dc1_scorec/api/`、`m3dc1_scorec/include/`、`m3dc1_scorec/src/`、`skeleton/` 下各 Fortran 骨架文件；`fortran/c1_12_element.F90`、`explicit_element.F90`、`explicit_element_interface.F90`；`include/ReducedQuintic.h`、`include/ReducedQuinticImplicit.h`、`include/BSpline.h`、`include/Expression.h`、`include/slntransferUtil.h`、`include/PolyNomial.h` | 为 Step 2 提供具体可调研文件路径候选；确认 M3DC1 侧哪些文件与网格消费直接相关；确认基函数与表达式模块的完整路径 | [路径索引证据] |
| R4 | `TOKAMAKER/oft-meshing-architecture/SKILL.md` | 技术技能文档（已加入对话） | OFT 网格生成 Python 层完整调用链；`meshing.py` 中 `gs_Domain`、`Mesh` 类详细职责（点合并、边界段合并/拆分、边界重采样、区域标记点生成）；`_interface.py` ctypes 绑定方式；`src/ext_libs/triangle.c` 第 14903 行 C 层入口；`triangle_struct` Python 侧结构体字段；`alpha` 字典 `{vertices, segments, regions}` 构造逻辑；`run_triangle()` 输入输出流程 | TokaMaker 侧网格生成源码调研入口；Python 层数据转换逻辑；C 层函数入口行号；`Mesh` 类预处理步骤 | [资料已读] |
| R5 | `TOKAMAKER/triangle-library-integration/SKILL.md` | 技术技能文档（已加入对话） | Triangle 编译宏 `TRILIBRARY/ANSI_DECLARATORS/NO_TIMER/REAL=double/VOID=void`；`triangulateio` 结构体完整字段（含输入字段 `pointlist/segmentlist/regionlist/holelist` 和输出字段 `trianglelist/neighborlist/edgelist/triangleattributelist/pointmarkerlist/segmentmarkerlist`）；`"pqaAzQ"` 控制字符串各开关含义；Python/Fortran/C 三种集成方式对比；Fortran `ISO_C_BINDING` 集成示例；针对 Fortran/C 混合程序推荐直接集成 C 源码 | Triangle C 层数据结构完整字段；`triangulateio` 输入输出字段与 UniMesh 核心层对齐分析；Fortran 直接集成方案参考；M3DC1 可能的 Triangle 集成路径 | [资料已读] |
| R6 | `UniMesh_Architecture_Plan.md` | 项目总蓝图（摘要，只读） | UniMesh `src/core/` 规划组件：`Mesh/Geometry/ConnectivityTable/TopologyGraph/Marker/Attribute/Metadata/DofLayout/PartitionInfo/ValidationReport`；驱动层 `src/drivers/m3dc1/` 封锁 M3DC1 私有语义；`src/generation/` 候选多后端生成工厂 | UniMesh 中间适配层候选能力边界；哪些信息可进入 core，哪些必须留在 driver；生成层与核心层隔离红线 | [路径索引证据] |
| R7 | `CONTEXT.md` | 项目开发上下文规范 | 作用域限制、只读隔离区定义、渐进式侦察纪律、支线任务协议；禁止把下游私有语义上浮到 `src/core/` | 约束本报告的执行边界；确认哪些内容属于驱动层私有语义 | [资料已读] |
| R8 | `docs/tokamaker/tokamaker_reference_map.txt` | 文件路径索引 | TokaMaker/OFT 完整文件路径列表，包括 `meshing.py`、`_interface.py`、`_core.py`、`convert_gmsh.py`、`convert_cubit.py`、`lagrange.py`、`nedelec.py`、`triangle.c`、`triangle.h`、`metis_bridge.c` 等 | 为 Step 2 提供 TokaMaker 侧具体可调研文件路径候选；确认 OFT 侧哪些文件与网格生成、格式转换、基函数定义直接相关 | [路径索引证据] |

---

## 3. 导师问题拆解为源码调研问题

| 调研问题编号 | 人类问题 | 转化后的源码问题 | 后续需要确认的源码信息 | 优先级 |
|---|---|---|---|---|
| Q1 | Triangle/TokaMaker 网格生成端实际输出哪些数据字段？ | `run_triangle()` 返回什么 NumPy 数组？`triangulateio` 输出字段中哪些被 OFT 实际使用？Python 层如何把 C 输出转换为可用对象？ | `meshing.py` 中 `run_triangle()` 返回值结构；`_interface.py` 中输出字段绑定；`triangulateio` 的 `trianglelist/pointlist/neighborlist/edgelist/segmentlist/triangleattributelist/pointmarkerlist` 等输出字段的实际使用情况 | P0 |
| Q2 | M3DC1 物理求解端读取网格时需要哪些数据？ | `m3dc1_scorec` 的 mesh 模块如何读取网格文件？读取后构造什么数据结构？哪些字段是必须的？`.smb` 文件格式包含哪些信息？ | `m3dc1_mesh.h/cc` 中网格读取函数签名；`.smb` 文件格式解析逻辑；节点坐标、单元连接、边界实体、区域标记如何进入 mesh object | P0 |
| Q3 | M3DC1 的几何模型层需要哪些额外信息？ | `m3dc1_model` 如何绑定几何区域和边界语义？区域标记（plasma/vacuum/wall）如何从文件进入 model object？model `.txt` 文件格式是什么？ | `m3dc1_model.h/cc` 中区域定义接口；model `.txt` 文件格式与解析逻辑；区域 ID 如何映射到物理方程选择 | P0 |
| Q4 | M3DC1 的高阶自由度布局如何与网格绑定？ | `m3dc1_field` 如何在网格实体上分配 C1 高阶自由度？DOF 编号如何与单元连接表对应？C1 reduced quintic 单元有多少个自由度？ | `m3dc1_field.h/cc` 中 field 初始化接口；C1 reduced quintic 基函数与节点/边/面自由度的对应关系；`c1_12_element.F90` 中单元自由度定义（12 DOF 含义） | P0 |
| Q5 | Triangle 输出与 M3DC1 输入之间缺失哪些信息？ | Triangle 输出的 `trianglelist/pointlist/segmentlist/triangleattributelist` 能否直接满足 `m3dc1_scorec` mesh 初始化所需的全部字段？哪些字段在 Triangle 输出中不存在或语义不匹配？ | 对比 `triangulateio` 输出字段与 `m3dc1_mesh` 读取所需字段；确认区域语义（plasma/vacuum）是否可从 `triangleattributelist` 中的 `region_id` 直接映射；确认高阶节点（边中点）是否需要额外生成；确认 `.smb` 格式与 Triangle 输出格式的结构差异 | P0 |
| Q6 | M3DC1 的矩阵装配如何消费网格数据？ | `m3dc1_matrix` 如何从 mesh/field 获取单元连接和自由度编号？局部矩阵如何散射到全局 PETSc 矩阵？ | `m3dc1_matrix.h/cc` 中装配接口；`matdef.F90` 中物理项定义；`nintegrate.F90` 中积分点循环与 mesh 数据消费 | P1 |
| Q7 | M3DC1 的边界条件如何从网格标记进入求解器？ | 边界标记（wall/outer boundary/interface）如何从 model 层进入弱形式装配？边界条件施加在哪个层次完成？ | `m3dc1_model.h/cc` 中边界实体接口；`element.F90` 或 `matdef.F90` 中边界项处理；Fortran 主程序中边界条件初始化调用 | P1 |
| Q8 | TokaMaker 的 Python 网格生成层如何处理共享边界和区域种子点？ | `Mesh` 类中点合并、边界段合并、共享边界处理、边界重采样、区域标记点生成的具体逻辑是什么？这些预处理步骤输出什么？ | `meshing.py` 中 `Mesh.__init__` 方法；`_resampled_points`、`resampled_flat`、`_reg_defs` 的构造逻辑；共享边界处理后的 segment 结构；`get_mesh()` 方法返回值 | P1 |
| Q9 | UniMesh 中间层可以承载哪些信息？ | UniMesh `src/core/` 的 `Geometry/ConnectivityTable/Marker/Attribute/DofLayout` 能否覆盖 Triangle 输出到 M3DC1 输入之间的信息缺口？哪些缺口必须由 driver 层补全？ | 对比 UniMesh core 组件与 Q5 确认的缺失信息；确认 `DofLayout` 是否足以表达 C1 高阶自由度需求；确认 `Marker` 是否足以表达 plasma/vacuum/wall 区域语义 | P1 |
| Q10 | M3DC1 的网格适配和解转移如何消费网格数据？ | `m3dc1_adapt/sizeField/slnTransfer` 如何读取旧网格、生成新网格、转移场变量？这些操作对网格数据结构有哪些额外要求？ | `m3dc1_adapt.cc`、`m3dc1_sizeField.h/cc`、`m3dc1_slnTransfer.h/cc` 中适配与解转移接口；旧网格与新网格之间的拓扑映射机制 | P2 |
| Q11 | OFT 的网格格式转换工具如何处理外部网格格式？ | `convert_gmsh.py` 和 `convert_cubit.py` 如何将外部网格格式转换为 OFT 内部格式？转换后输出哪些字段？这些字段与 Triangle 输出字段有何异同？ | `convert_gmsh.py` 和 `convert_cubit.py` 中的解析逻辑；输出数据结构；与 `meshing.py` 输出格式的对比 | P1 |
| Q12 | OFT 的有限元基函数定义如何与网格拓扑绑定？ | `lagrange.py` 和 `nedelec.py` 中的基函数定义如何与网格节点/边/面编号对应？这些基函数定义对 UniMesh DOF 布局设计有何参考价值？ | `lagrange.py` 中拉格朗日基函数节点编号约定；`nedelec.py` 中 Nédélec 基函数边编号约定；与 M3DC1 C1 reduced quintic 基函数的对比 | P1 |
| Q13 | OFT 的 METIS 分区桥接如何消费网格数据？ | `metis_bridge.c` 如何从 OFT 内部网格数据结构提取分区所需信息？分区结果如何写回网格？这对 UniMesh `PartitionInfo` 组件设计有何参考价值？ | `metis_bridge.c` 中分区接口；输入的单元连接表格式；输出的分区标记格式 | P2 |
| Q14 | M3DC1 的高阶基函数（ReducedQuintic/BSpline/PolyNomial）如何支撑 C1 连续性？ | `ReducedQuintic.h`、`ReducedQuinticImplicit.h`、`BSpline.h`、`PolyNomial.h` 中的基函数定义如何与网格实体绑定？这些基函数如何保证跨单元 C1 连续性？ | `ReducedQuintic.h` 中基函数接口声明；`BSpline.h` 中样条基函数定义；`PolyNomial.h` 中多项式基函数定义；与 `c1_12_element.F90` 中 12 DOF 定义的对应关系 | P1 |
| Q15 | M3DC1 的解转移工具函数如何辅助场变量插值？ | `slntransferUtil.h/cc` 中的工具函数如何支撑 `m3dc1_slnTransfer` 的场变量插值？这些工具函数对 UniMesh 解转移能力设计有何参考价值？ | `slntransferUtil.h` 中工具函数接口声明；`slntransferUtil.cc` 中插值逻辑实现；与 `m3dc1_slnTransfer.cc` 的调用关系 | P2 |

---

## 4. Step 2 源码调研总表（路径已基于真实 reference_map 强制锚定，白皮书交叉核验补全）

### 4.1 TokaMaker / OFT 侧（字典 A：tokamaker_reference_map.txt）

| 优先级 | 文件路径（已在字典 A 中确认） | 调研目标 | 关联调研问题 | 当前事实边界 |
|---|---|---|---|---|
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` | `run_triangle()` 返回值结构；`Mesh.__init__` 预处理步骤；`get_mesh()` 输出字段；`gs_Domain.build_mesh()` 调用链；`_resampled_points`/`resampled_flat`/`_reg_defs` 构造逻辑；共享边界处理后 segment 结构 | Q1, Q8 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_interface.py` | ctypes 绑定方式；`oft_triangulate` 函数签名；`triangle_struct` 结构体字段定义；输出字段绑定逻辑 | Q1 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c` | C 层 `triangulate()` 函数入口（第 14903 行）；`triangulateio` 输出字段实际填充逻辑；`triangleattributelist` 区域标记写入时机 | Q1, Q5 | [SKILL文档指引，待源码核实] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h` | `triangulateio` 结构体完整字段定义；`REAL`/`VOID` 宏定义；函数原型声明 | Q1, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_core.py` | TokaMaker Python 核心层数据结构；网格对象在 Python 层的表示形式；与 `meshing.py` 的数据交换接口 | Q1, Q8 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/utilities/convert_gmsh.py` | 外部 Gmsh 格式解析逻辑；输出数据结构字段；与 Triangle 输出格式的异同；区域标记和边界标记的处理方式 | Q11 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/utilities/convert_cubit.py` | 外部 Cubit 格式解析逻辑；输出数据结构字段；与 Triangle 输出格式的异同；区域标记和边界标记的处理方式 | Q11 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/utilities/basis_functions/lagrange.py` | 拉格朗日基函数节点编号约定；基函数与网格节点/边/面的绑定方式；对 UniMesh DOF 布局设计的参考价值 | Q12 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/utilities/basis_functions/nedelec.py` | Nédélec 矢量基函数边编号约定；基函数与网格边的绑定方式；与 M3DC1 C1 基函数的对比参考 | Q12 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `TOKAMAKER/OpenFUSIONToolkit/src/grid/metis_bridge.c` | METIS 分区接口；输入单元连接表格式；输出分区标记格式；对 UniMesh `PartitionInfo` 组件设计的参考价值 | Q13 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/_interface.py` | OFT 顶层 ctypes 接口层；动态库加载方式；与 TokaMaker 子模块接口的关系 | Q1 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/_core.py` | OFT 顶层核心数据结构；网格对象基类定义 | Q1, Q9 | [路径已确认，内容待 Step 2 读源码验证] |

### 4.2 M3DC1 侧（字典 B：m3dc1_reference_map.txt）

| 优先级 | 文件路径（已在字典 B 中确认） | 调研目标 | 关联调研问题 | 当前事实边界 |
|---|---|---|---|---|
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_mesh.h` | 网格读取函数签名；mesh object 数据结构定义；节点坐标/单元连接/边界实体/区域标记字段声明；`.smb` 文件格式读取接口 | Q2, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` | 网格读取函数实现；`.smb` 文件格式解析逻辑；节点坐标/单元连接/边界实体/区域标记如何进入 mesh object；与 SCOREC/PUMI 接口的调用方式 | Q2, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_model.h` | 几何模型层接口声明；区域定义接口；边界实体接口；区域 ID 到物理方程选择的映射声明 | Q3, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` | 几何模型层实现；区域标记（plasma/vacuum/wall）从文件进入 model object 的逻辑；model `.txt` 文件格式解析；区域 ID 映射实现 | Q3, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_field.h` | field 初始化接口声明；C1 高阶自由度分配接口；DOF 编号与单元连接表对应关系声明 | Q4, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_field.cc` | field 初始化实现；C1 reduced quintic 自由度在网格实体（节点/边/面）上的分配逻辑；DOF 编号生成机制 | Q4, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/fortran/c1_12_element.F90` | C1 reduced quintic 单元 12 DOF 定义；基函数与节点/边自由度的对应关系；单元刚度矩阵局部装配逻辑 | Q4, Q5, Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/api/m3dc1_scorec.h` | M3DC1-SCOREC 公共 API 头文件；网格/模型/场/矩阵/线性系统的顶层接口声明；供 Fortran 主程序调用的 C 接口 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/api/m3dc1_scorec.cc` | M3DC1-SCOREC 公共 API 实现；顶层接口的调用链；Fortran-C 互操作层 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/m3dc1_matrix.h` | 矩阵装配接口声明；从 mesh/field 获取单元连接和 DOF 编号的接口；PETSc 矩阵散射接口 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/src/m3dc1_matrix.cc` | 矩阵装配实现；局部矩阵到全局 PETSc 矩阵的散射逻辑；单元连接表消费方式 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/fortran/explicit_element.F90` | 显式单元积分实现；积分点循环与 mesh 数据消费；物理项定义 | Q6, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/fortran/explicit_element_interface.F90` | 显式单元接口定义；Fortran 模块接口声明；与 C 层的互操作接口 | Q6, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/mesh.F90` | Fortran 主程序骨架中的网格初始化调用；网格数据在 Fortran 层的表示；与 `m3dc1_scorec` API 的调用关系 | Q2, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/field.F90` | Fortran 主程序骨架中的场变量初始化；场变量与网格 DOF 的绑定方式；标量势变量 `U/omega/chi/psi/f` 的定义 | Q4, Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/matdef.F90` | 物理项矩阵定义；弱形式各项的 Fortran 实现；边界条件项处理 | Q6, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/nintegrate.F90` | 数值积分循环；积分点与网格单元的对应；mesh 数据消费方式 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90` | Fortran 主程序入口；初始化调用顺序；网格/模型/场/矩阵的初始化链路 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/element.F90` | 单元级计算；单元数据结构；与网格拓扑的绑定方式 | Q4, Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/src/m3dc1_entity.cc` | 网格实体（节点/边/面/单元）的底层表示；实体标记机制；与 SCOREC/PUMI 实体接口的对应 | Q2, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/api/name_convert.h` | M3DC1 内部命名约定；区域/边界/场变量名称映射；供 UniMesh driver 层命名对齐参考 | Q3, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/ReducedQuintic.h` | C1 reduced quintic 基函数接口声明；基函数与网格实体的绑定方式；C1 连续性保证机制 | Q4, Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/ReducedQuinticImplicit.h` | C1 reduced quintic 隐式基函数接口声明；与显式版本的差异；隐式基函数在弱形式装配中的角色 | Q4, Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/BSpline.h` | B 样条基函数接口声明；样条基函数与网格实体的绑定方式；在几何或场插值中的角色 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/PolyNomial.h` | 多项式基函数接口声明；多项式基函数与 C1 单元的关系；在积分点求值中的角色 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/Expression.h` | 表达式接口声明；几何或场表达式的抽象层；在 `CMODGeoExpression` 和基函数求值中的角色 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/src/Expression.cc` | 表达式接口实现；几何或场表达式的具体求值逻辑 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/CMODGeoExpression.h` | CMOD 几何表达式接口声明；几何边界或区域的解析表达式定义；与 model 层的关联 | Q3, Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/src/CMODGeoExpression.cc` | CMOD 几何表达式实现；几何边界解析逻辑；与 `m3dc1_model` 的调用关系 | Q3, Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/include/m3dc1_ls.h` | 线性系统接口声明；PETSc KSP/PC 配置接口；与矩阵/场的连接 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/m3dc1_ls.cc` | 线性系统实现；PETSc 求解器配置；收敛判据 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/m3dc1_adapt.cc` | 网格适配实现；旧网格到新网格的拓扑映射；适配触发条件 | Q10 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/include/m3dc1_sizeField.h` | 尺寸场接口声明；适配驱动的尺寸场定义 | Q10 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/m3dc1_sizeField.cc` | 尺寸场实现；基于物理量的网格尺寸控制逻辑 | Q10 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/include/m3dc1_slnTransfer.h` | 解转移接口声明；旧网格场变量到新网格的插值接口 | Q10, Q15 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/m3dc1_slnTransfer.cc` | 解转移实现；场变量插值逻辑；与 mesh/field 的数据交换 | Q10, Q15 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/include/slntransferUtil.h` | 解转移工具函数接口声明；辅助插值函数定义 | Q15 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/slntransferUtil.cc` | 解转移工具函数实现；插值逻辑细节；与 `m3dc1_slnTransfer.cc` 的调用关系 | Q15 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/ReducedQuinticImplicit.cc` | C1 reduced quintic 隐式基函数实现；隐式基函数求值逻辑 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/BSpline.cc` | B 样条基函数实现；样条求值逻辑 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/m3dc1_scorec/src/PolyNomial.cc` | 多项式基函数实现；多项式求值逻辑 | Q14 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/m3dc1_data.F90` | Fortran 全局数据模块；网格/场/矩阵数据的 Fortran 侧存储结构 | Q2, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P2 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/init_conds.F90` | 初始条件设置；场变量初始化与网格 DOF 的对应 | Q4 | [路径已确认，内容待 Step 2 读源码验证] |

---

## 5. 分组侦察路线（Step 2 执行顺序建议）

### 路线 A：Triangle 输出格式完整解析（P0 优先）

**目标**：完整确认 Triangle 生成端实际输出哪些字段，为后续缺口分析提供事实基础。

**执行顺序**：

1. `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h`
   - 确认 `triangulateio` 结构体完整字段定义
   - 确认 `REAL`/`VOID` 宏定义
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c`
   - 定位第 14903 行 `triangulate()` 函数入口
   - 确认 `triangleattributelist` 区域标记写入时机
   - 确认 `pointmarkerlist`/`segmentmarkerlist` 边界标记写入逻辑
   - 事实边界：[SKILL文档指引，待源码核实]

3. `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_interface.py`
   - 确认 `triangle_struct` Python 侧结构体字段与 C 侧 `triangulateio` 的对应
   - 确认 `oft_triangulate` ctypes 函数签名
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
   - 确认 `run_triangle()` 从输出结构体中提取哪些字段
   - 确认 `get_mesh()` 返回值结构
   - 确认 `Mesh.__init__` 中 `_resampled_points`/`resampled_flat`/`_reg_defs` 构造逻辑
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 B：M3DC1 网格消费链路解析（P0 优先）

**目标**：完整确认 M3DC1 读取网格时需要哪些字段，为缺口分析提供事实基础。

**执行顺序**：

1. `M3DC1/m3dc1_scorec/api/m3dc1_scorec.h`
   - 确认顶层公共 API 接口声明
   - 确认网格/模型/场/矩阵/线性系统的接口层次
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `M3DC1/m3dc1_scorec/include/m3dc1_mesh.h`
   - 确认网格读取函数签名
   - 确认 mesh object 数据结构字段声明
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

3. `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`
   - 确认 `.smb` 文件格式解析逻辑
   - 确认节点坐标/单元连接/边界实体/区域标记进入 mesh object 的方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `M3DC1/m3dc1_scorec/include/m3dc1_model.h`
   - 确认区域定义接口
   - 确认边界实体接口
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

5. `M3DC1/m3dc1_scorec/src/m3dc1_model.cc`
   - 确认区域标记（plasma/vacuum/wall）从文件进入 model object 的逻辑
   - 确认 model `.txt` 文件格式解析
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

6. `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90`
   - 确认 Fortran 主程序初始化调用顺序
   - 确认网格/模型/场/矩阵的初始化链路
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 C：M3DC1 高阶 DOF 布局与基函数解析（P0/P1）

**目标**：确认 C1 reduced quintic 单元的自由度定义及其支撑基函数体系，为 Triangle 输出与 M3DC1 输入的缺口分析提供 DOF 维度的事实基础。

**执行顺序**：

1. `M3DC1/m3dc1_scorec/fortran/c1_12_element.F90`（P0）
   - 确认 C1 reduced quintic 单元 12 DOF 的具体定义
   - 确认基函数与节点/边自由度的对应关系
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `M3DC1/m3dc1_scorec/include/m3dc1_field.h`（P0）
   - 确认 field 初始化接口声明
   - 确认 C1 高阶自由度分配接口
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

3. `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`（P0）
   - 确认 C1 reduced quintic 自由度在网格实体上的分配逻辑
   - 确认 DOF 编号生成机制
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `M3DC1/m3dc1_scorec/include/ReducedQuintic.h`（P1）
   - 确认 C1 reduced quintic 基函数接口声明
   - 确认基函数与网格实体的绑定方式
   - 确认 C1 连续性保证机制
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

5. `M3DC1/m3dc1_scorec/include/ReducedQuinticImplicit.h`（P1）
   - 确认隐式版本与显式版本的差异
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

6. `M3DC1/m3dc1_scorec/include/BSpline.h`（P1）
   - 确认 B 样条基函数接口声明
   - 确认在几何或场插值中的角色
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

7. `M3DC1/m3dc1_scorec/include/PolyNomial.h`（P1）
   - 确认多项式基函数接口声明
   - 确认在积分点求值中的角色
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

8. `M3DC1/m3dc1_scorec/include/Expression.h`（P1）
   - 确认表达式抽象层接口声明
   - 确认在基函数求值中的角色
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

9. `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/field.F90`（P1）
   - 确认标量势变量 `U/omega/chi/psi/f` 的定义
   - 确认场变量与网格 DOF 的绑定方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 D：格式转换工具与基函数参考（P1）

**目标**：通过 OFT 的格式转换工具和基函数定义，为 UniMesh 的格式适配层和 DOF 布局设计提供参考。

**执行顺序**：

1. `TOKAMAKER/OpenFUSIONToolkit/src/utilities/convert_gmsh.py`
   - 确认 Gmsh 格式解析逻辑
   - 确认输出数据结构字段
   - 确认区域标记和边界标记的处理方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `TOKAMAKER/OpenFUSIONToolkit/src/utilities/convert_cubit.py`
   - 确认 Cubit 格式解析逻辑
   - 确认输出数据结构字段
   - 确认区域标记和边界标记的处理方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

3. `TOKAMAKER/OpenFUSIONToolkit/src/utilities/basis_functions/lagrange.py`
   - 确认拉格朗日基函数节点编号约定
   - 确认基函数与网格节点/边/面的绑定方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `TOKAMAKER/OpenFUSIONToolkit/src/utilities/basis_functions/nedelec.py`
   - 确认 Nédélec 矢量基函数边编号约定
   - 确认基函数与网格边的绑定方式
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 E：M3DC1 矩阵装配与边界条件（P1）

**目标**：确认 M3DC1 矩阵装配如何消费网格数据，边界条件如何从网格标记进入求解器。

**执行顺序**：

1. `M3DC1/m3dc1_scorec/include/m3dc1_matrix.h`
   - 确认矩阵装配接口声明
   - 确认从 mesh/field 获取单元连接和 DOF 编号的接口
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `M3DC1/m3dc1_scorec/src/m3dc1_matrix.cc`
   - 确认局部矩阵到全局 PETSc 矩阵的散射逻辑
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

3. `M3DC1/m3dc1_scorec/fortran/explicit_element.F90`
   - 确认显式单元积分实现
   - 确认积分点循环与 mesh 数据消费
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/matdef.F90`
   - 确认物理项矩阵定义
   - 确认边界条件项处理
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

5. `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/nintegrate.F90`
   - 确认数值积分循环
   - 确认积分点与网格单元的对应
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

6. `M3DC1/m3dc1_scorec/include/CMODGeoExpression.h`
   - 确认 CMOD 几何表达式接口声明
   - 确认几何边界或区域的解析表达式定义
   - 确认与 model 层的关联
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 F：网格适配、解转移与工具函数（P2，可延后）

**目标**：确认 M3DC1 网格适配和解转移对网格数据结构的额外要求，以及解转移工具函数的辅助角色。

**执行顺序**：

1. `M3DC1/m3dc1_scorec/src/m3dc1_adapt.cc`
2. `M3DC1/m3dc1_scorec/include/m3dc1_sizeField.h`
3. `M3DC1/m3dc1_scorec/src/m3dc1_sizeField.cc`
4. `M3DC1/m3dc1_scorec/include/m3dc1_slnTransfer.h`
5. `M3DC1/m3dc1_scorec/src/m3dc1_slnTransfer.cc`
6. `M3DC1/m3dc1_scorec/include/slntransferUtil.h`
7. `M3DC1/m3dc1_scorec/src/slntransferUtil.cc`

所有文件事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

## 6. 预期信息缺口假设（待 Step 2 验证）

以下为基于文献推断的预期缺口，**不构成源码已确认事实**，仅作为 Step 2 侦察的重点关注方向：

| 缺口编号 | 预期缺口描述 | 缺口来源推断 | 需要 Step 2 验证的具体问题 | 对 UniMesh 设计的潜在影响 |
|---|---|---|---|---|
| G1 | Triangle 输出仅含线性节点（三角形三顶点），M3DC1 C1 单元需要边中点（高阶节点） | C1 reduced quintic 基函数需要边中点作为额外自由度载体；Triangle 默认输出线性三角形 | `c1_12_element.F90` 中是否需要边中点？`m3dc1_field.cc` 中如何生成边中点？Triangle 是否有高阶输出选项？ | UniMesh 生成层或驱动层需要提供高阶节点生成能力 |
| G2 | Triangle 的 `triangleattributelist` 中的 `region_id` 与 M3DC1 的物理区域语义（plasma/vacuum/wall）之间需要显式映射 | Triangle 只输出数值 ID；M3DC1 需要物理语义标签来选择方程 | `m3dc1_model.cc` 中 region_id 到物理方程的映射逻辑；映射是否通过 model `.txt` 文件完成 | UniMesh M3DC1 driver 层需要提供 region_id 到物理语义的映射表 |
| G3 | Triangle 输出的 `segmentmarkerlist` 边界标记与 M3DC1 的边界条件类型（Dirichlet/Neumann/interface）之间需要显式映射 | Triangle 边界标记是整数 ID；M3DC1 边界条件类型是物理语义 | `m3dc1_model.cc` 中边界标记到边界条件类型的映射；`matdef.F90` 中边界条件项如何识别边界类型 | UniMesh M3DC1 driver 层需要提供边界标记到边界条件类型的映射表 |
| G4 | Triangle 输出不包含并行分区信息，M3DC1 并行运行需要 METIS 分区 | Triangle 是串行网格生成器；M3DC1 使用 MPI 并行 | `m3dc1_mesh.cc` 中分区信息如何获取？是否通过 SCOREC/PUMI 的分区接口？ | UniMesh `PartitionInfo` 组件需要支持 METIS 分区结果的存储和传递 |
| G5 | Triangle 输出的拓扑连接表（`trianglelist`）使用全局节点编号，M3DC1 可能需要基于 SCOREC/PUMI 实体句柄的拓扑表示 | SCOREC/PUMI 使用面向对象的网格实体模型；Triangle 使用平坦数组索引 | `m3dc1_mesh.cc` 中如何将平坦数组索引转换为 SCOREC/PUMI 实体句柄？是否有中间转换层？ | UniMesh 核心层的 `ConnectivityTable` 需要支持从平坦索引到实体句柄的转换，或由 driver 层完成此转换 |
| G6 | M3DC1 的 C1 reduced quintic 基函数体系（`ReducedQuintic`/`BSpline`/`PolyNomial`）与 OFT 的拉格朗日/Nédélec 基函数体系在 DOF 布局约定上存在根本差异 | M3DC1 使用 C1 连续高阶基函数；OFT 使用标准 H1/H(curl) 基函数；两者对网格实体（节点/边/面）上的 DOF 数量和编号约定不同 | `ReducedQuintic.h` 中每条边上的 DOF 数量；`lagrange.py` 中每个节点上的 DOF 数量；两者是否可以用同一套 UniMesh `DofLayout` 抽象表达 | UniMesh `DofLayout` 组件需要足够通用，能同时表达 C1 高阶 DOF 和标准拉格朗日/Nédélec DOF |

---

## 7. 待确认事项与主管决策点

| 编号 | 待确认事项 | 影响范围 | 建议决策方向 |
|---|---|---|---|
| D1 | Step 2 侦察是否按路线 A→B→C→D→E→F 的顺序串行执行，还是允许并行侦察多条路线？ | Step 2 执行计划 | 建议优先串行执行 A+B+C（P0 路线），再并行执行 D+E（P1 路线） |
| D2 | Step 2 侦察结果是否需要更新 `UniMesh_Architecture_Plan.md`？还是先形成独立的 Step 2 报告，再由主管决定是否触发蓝图更新？ | 主线蓝图更新触发条件 | 建议先形成独立 Step 2 报告，由主管确认后再决定是否触发蓝图更新 |
| D3 | 预期缺口 G1（高阶节点生成）是否需要在 UniMesh 生成层实现，还是由 M3DC1 driver 层在读取网格后自行生成？ | UniMesh 架构边界决策 | 需要 Step 2 确认 `m3dc1_field.cc` 中高阶节点生成逻辑后再决策 |
| D4 | 是否需要将 OFT 的 `convert_gmsh.py` 和 `convert_cubit.py` 的格式转换逻辑作为 UniMesh 格式适配层的参考实现？ | UniMesh 格式适配层设计 | 建议在 Step 2 读取这两个文件后，由主管决定是否纳入参考 |
| D5 | 预期缺口 G6（C1 基函数体系与标准基函数体系的 DOF 布局差异）是否意味着 UniMesh `DofLayout` 需要支持"每实体多 DOF"的泛化表达？ | UniMesh `DofLayout` 组件设计 | 需要 Step 2 确认 `ReducedQuintic.h` 和 `lagrange.py` 中的 DOF 数量约定后再决策 |
| D6 | M3DC1 的 `CMODGeoExpression` 模块是否意味着 M3DC1 使用解析几何边界（而非纯离散网格边界）？如果是，UniMesh driver 层是否需要支持解析几何边界的传递？ | UniMesh M3DC1 driver 层设计 | 需要 Step 2 确认 `CMODGeoExpression.h/cc` 和 `m3dc1_model.cc` 的关联后再决策 |
