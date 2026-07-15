# SideTask_Step1_Source_Investigation_Checklist

- 文档主受众：LinkMesh 开发团队
- 执行用途：为 Step 2 源码只读侦察生成优先级清单
- 人类阅读用途：帮助主管理解导师支线任务需要先查哪些源码区域
- 当前任务：导师支线任务 Step 1：文献驱动生成源码调研清单（路径已基于真实地图强制锚定，白皮书交叉核验完成）
- 当前状态：Step 1 最终版 v2 / 路径已对齐真实 reference_map / 白皮书交叉核验补全 / 待主管审阅后进入 Step 2
- 最高依据：当前仓库的 CONTEXT.md (LinkMesh 敏捷开发工作流规范)
- 事实边界：本报告只规划后续源码调研入口，不构成源码事实确认，不构成主线开发完成。本文档中的所有调研情报，在当前阶段【仅服务于 LinkMesh 独立命令行程序具体解析与写入脚本的编写】，不涉及任何通用抽象中间件设计。
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
- 触碰任何场外架构师专用上下文文件。

---

## 2. 文献与资料依据清单

| 编号 | 资料/文献/说明材料 | 资料类型 | 提供的关键信息 | 用于推导哪些源码调研方向 | 事实状态 |
|---|---|---|---|---|---|
| R1 | `docs/tokamaker/TOKAMAKER_Architecture_Whitepaper.md` | 架构白皮书 | TokaMaker/OFT 网格生成链路全景：`gs_Domain.build_mesh()` → `Mesh` 类 → `run_triangle()` → ctypes → `liboft_triangle.so` → `triangle.c`；Triangle 输入结构 `vertices/segments/regions`；`regions` 字段含义 `[x, y, region_id, max_area]`；Triangle 集成规范 | Triangle 输入格式解析入口；Python 封装层；ctypes 绑定；C 层 `triangulate()` 入口；区域标签处理路径 | [资料已读，本轮交叉核验完成] |
| R2 | `docs/m3dc1/M3DC1_Architecture_Whitepaper.md` | 架构白皮书 | M3DC1 使用高阶 C1 有限元、隐式时间推进、PETSc/Krylov；`m3dc1_scorec` 承担网格读取、几何模型绑定、场变量、矩阵、线性系统、适配、解转移；网格消费链路需要区域标记、边界标记、高阶自由度布局、几何拓扑一致性和并行分区信息 | `m3dc1_scorec` API 层；mesh/model/field/matrix/ls 模块；Fortran 主程序骨架；单元积分与矩阵装配；适配与解转移链路 | [资料已读，本轮交叉核验完成] |
| R3 | `docs/m3dc1/m3dc1_reference_map.txt` | 文件路径索引 | M3DC1 完整文件路径列表，包括 `m3dc1_scorec/api/`、`m3dc1_scorec/include/`、`m3dc1_scorec/src/`、`skeleton/` 下各 Fortran 骨架文件 | 为 Step 2 提供具体可调研文件路径候选；确认 M3DC1 侧哪些文件与网格消费直接相关 | [路径索引证据] |
| R4 | `TOKAMAKER/oft-meshing-architecture/SKILL.md` | 技术技能文档 | OFT 网格生成 Python 层完整调用链；`meshing.py` 中 `gs_Domain`、`Mesh` 类详细职责；`_interface.py` ctypes 绑定方式；`src/ext_libs/triangle.c` C 层入口；`triangle_struct` Python 侧结构体字段；`alpha` 字典 `{vertices, segments, regions}` 构造逻辑 | TokaMaker 侧网格生成源码调研入口；Python 层数据转换逻辑；C 层函数入口 | [资料已读] |
| R5 | `TOKAMAKER/triangle-library-integration/SKILL.md` | 技术技能文档 | Triangle 编译宏；`triangulateio` 结构体完整字段；`"pqaAzQ"` 控制字符串各开关含义；Python/Fortran/C 三种集成方式对比 | Triangle C 层数据结构完整字段；`triangulateio` 输入输出字段分析；Fortran 直接集成方案参考 | [资料已读] |
| R6 | `CONTEXT.md` | 项目开发上下文规范 | LinkMesh P0 作用域限制、只读隔离区定义、渐进式侦察纪律、支线任务协议 | 约束本报告的执行边界；确认哪些内容属于 LinkMesh 当前 MVP 范围 | [资料已读] |

---

## 3. 导师问题拆解为源码调研问题

> **重要说明**：以下所有调研问题，其最终目的均为服务 LinkMesh 独立命令行程序中具体 Reader/Mesher/Writer 脚本的编写，不涉及任何通用抽象中间件或插件体系设计。

| 调研问题编号 | 人类问题 | 转化后的源码问题 | 后续需要确认的源码信息 | 优先级 |
|---|---|---|---|---|
| Q1 | Triangle/TokaMaker 网格生成端实际输出哪些数据字段？ | `run_triangle()` 返回什么 NumPy 数组？`triangulateio` 输出字段中哪些被 OFT 实际使用？Python 层如何把 C 输出转换为可用对象？ | `meshing.py` 中 `run_triangle()` 返回值结构；`_interface.py` 中输出字段绑定；`triangulateio` 的 `trianglelist/pointlist/neighborlist/edgelist/segmentlist/triangleattributelist/pointmarkerlist` 等输出字段的实际使用情况 | P0 |
| Q2 | M3DC1 物理求解端读取网格时需要哪些数据？ | `m3dc1_scorec` 的 mesh 模块如何读取网格文件？读取后构造什么数据结构？哪些字段是必须的？`.smb` 文件格式包含哪些信息？ | `m3dc1_mesh.h/cc` 中网格读取函数签名；`.smb` 文件格式解析逻辑；节点坐标、单元连接、边界实体、区域标记如何进入 mesh object | P0 |
| Q3 | M3DC1 的几何模型层需要哪些额外信息？ | `m3dc1_model` 如何绑定几何区域和边界语义？区域标记（plasma/vacuum/wall）如何从文件进入 model object？model `.txt` 文件格式是什么？ | `m3dc1_model.h/cc` 中区域定义接口；model `.txt` 文件格式与解析逻辑；区域 ID 如何映射到物理方程选择 | P0 |
| Q4 | M3DC1 的高阶自由度布局如何与网格绑定？ | `m3dc1_field` 如何在网格实体上分配 C1 高阶自由度？DOF 编号如何与单元连接表对应？C1 reduced quintic 单元有多少个自由度？ | `m3dc1_field.h/cc` 中 field 初始化接口；C1 reduced quintic 基函数与节点/边/面自由度的对应关系；`c1_12_element.F90` 中单元自由度定义（12 DOF 含义） | P0 |
| Q5 | Triangle 输出与 M3DC1 输入之间缺失哪些信息？ | Triangle 输出的 `trianglelist/pointlist/segmentlist/triangleattributelist` 能否直接满足 `m3dc1_scorec` mesh 初始化所需的全部字段？哪些字段在 Triangle 输出中不存在或语义不匹配？ | 对比 `triangulateio` 输出字段与 `m3dc1_mesh` 读取所需字段；确认区域语义（plasma/vacuum）是否可从 `triangleattributelist` 中的 `region_id` 直接映射；确认 `.smb` 格式与 Triangle 输出格式的结构差异 | P0 |
| Q6 | M3DC1 的矩阵装配如何消费网格数据？ | `m3dc1_matrix` 如何从 mesh/field 获取单元连接和自由度编号？局部矩阵如何散射到全局 PETSc 矩阵？ | `m3dc1_matrix.h/cc` 中装配接口；`matdef.F90` 中物理项定义；`nintegrate.F90` 中积分点循环与 mesh 数据消费 | P1 |
| Q7 | M3DC1 的边界条件如何从网格标记进入求解器？ | 边界标记（wall/outer boundary/interface）如何从 model 层进入弱形式装配？边界条件施加在哪个层次完成？ | `m3dc1_model.h/cc` 中边界实体接口；`element.F90` 或 `matdef.F90` 中边界项处理；Fortran 主程序中边界条件初始化调用 | P1 |
| Q8 | TokaMaker 的 Python 网格生成层如何处理共享边界和区域种子点？ | `Mesh` 类中点合并、边界段合并、共享边界处理、边界重采样、区域标记点生成的具体逻辑是什么？ | `meshing.py` 中 `Mesh.__init__` 方法；`_resampled_points`、`resampled_flat`、`_reg_defs` 的构造逻辑；共享边界处理后的 segment 结构 | P1 |

---

## 4. Step 2 源码调研总表（路径已基于真实 reference_map 强制锚定）

### 4.1 TokaMaker / OFT 侧

| 优先级 | 文件路径 | 调研目标 | 关联调研问题 | 当前事实边界 |
|---|---|---|---|---|
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` | `run_triangle()` 返回值结构；`Mesh.__init__` 预处理步骤；`get_mesh()` 输出字段；`gs_Domain.build_mesh()` 调用链 | Q1, Q8 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_interface.py` | ctypes 绑定方式；`oft_triangulate` 函数签名；`triangle_struct` 结构体字段定义 | Q1 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c` | C 层 `triangulate()` 函数入口；`triangulateio` 输出字段实际填充逻辑；`triangleattributelist` 区域标记写入时机 | Q1, Q5 | [SKILL文档指引，待源码核实] |
| P0 | `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h` | `triangulateio` 结构体完整字段定义；`REAL`/`VOID` 宏定义；函数原型声明 | Q1, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_core.py` | TokaMaker Python 核心层数据结构；网格对象在 Python 层的表示形式 | Q1, Q8 | [路径已确认，内容待 Step 2 读源码验证] |

### 4.2 M3DC1 侧

| 优先级 | 文件路径 | 调研目标 | 关联调研问题 | 当前事实边界 |
|---|---|---|---|---|
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_mesh.h` | 网格读取函数签名；mesh object 数据结构定义；节点坐标/单元连接/边界实体/区域标记字段声明；`.smb` 文件格式读取接口 | Q2, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` | 网格读取函数实现；`.smb` 文件格式解析逻辑；节点坐标/单元连接/边界实体/区域标记如何进入 mesh object | Q2, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_model.h` | 几何模型层接口声明；区域定义接口；边界实体接口 | Q3, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` | 几何模型层实现；区域标记（plasma/vacuum/wall）从文件进入 model object 的逻辑；model `.txt` 文件格式解析 | Q3, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/include/m3dc1_field.h` | field 初始化接口声明；C1 高阶自由度分配接口 | Q4, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/src/m3dc1_field.cc` | field 初始化实现；C1 reduced quintic 自由度在网格实体上的分配逻辑 | Q4, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/fortran/c1_12_element.F90` | C1 reduced quintic 单元 12 DOF 定义；基函数与节点/边自由度的对应关系 | Q4, Q5 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/api/m3dc1_scorec.h` | M3DC1-SCOREC 公共 API 头文件；网格/模型/场/矩阵/线性系统的顶层接口声明 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P0 | `M3DC1/m3dc1_scorec/api/m3dc1_scorec.cc` | M3DC1-SCOREC 公共 API 实现；顶层接口的调用链 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/include/m3dc1_matrix.h` | 矩阵装配接口声明 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/src/m3dc1_matrix.cc` | 矩阵装配实现；局部矩阵到全局 PETSc 矩阵的散射逻辑 | Q6 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/m3dc1_scorec/fortran/explicit_element.F90` | 显式单元积分实现；积分点循环与 mesh 数据消费 | Q6, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/mesh.F90` | Fortran 主程序骨架中的网格初始化调用 | Q2, Q7 | [路径已确认，内容待 Step 2 读源码验证] |
| P1 | `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90` | Fortran 主程序入口；初始化调用顺序 | Q2, Q3, Q4 | [路径已确认，内容待 Step 2 读源码验证] |

---

## 5. 分组侦察路线（Step 2 执行顺序建议）

### 路线 A：Triangle 输出格式完整解析（P0 优先）

**目标**：完整确认 Triangle 生成端实际输出哪些字段，为 LinkMesh `writers/` 模块编写提供事实基础。

**执行顺序**：

1. `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h`
   - 确认 `triangulateio` 结构体完整字段定义
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

2. `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c`
   - 定位 `triangulate()` 函数入口
   - 确认 `triangleattributelist` 区域标记写入时机
   - 事实边界：[SKILL文档指引，待源码核实]

3. `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/_interface.py`
   - 确认 `triangle_struct` Python 侧结构体字段与 C 侧 `triangulateio` 的对应
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

4. `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
   - 确认 `run_triangle()` 从输出结构体中提取哪些字段
   - 事实边界：[路径已确认，内容待 Step 2 读源码验证]

---

### 路线 B：M3DC1 网格消费链路解析（P0 优先）

**目标**：完整确认 M3DC1 读取网格时需要哪些字段，为 LinkMesh `writers/smb_writer.py` 编写提供事实基础。

**执行顺序**：

1. `M3DC1/m3dc1_scorec/api/m3dc1_scorec.h`
2. `M3DC1/m3dc1_scorec/include/m3dc1_mesh.h`
3. `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`
4. `M3DC1/m3dc1_scorec/include/m3dc1_model.h`
5. `M3DC1/m3dc1_scorec/src/m3dc1_model.cc`
6. `M3DC1/skeleton/m3dc1_skeleton_big_spec_acc/main.F90`

---

## 6. 预期信息缺口假设（待 Step 2 验证）

以下为基于文献推断的预期缺口，**不构成源码已确认事实**，仅作为 Step 2 侦察的重点关注方向，最终目的是指导 LinkMesh `writers/smb_writer.py` 的具体实现：

| 缺口编号 | 预期缺口描述 | 缺口来源推断 | 需要 Step 2 验证的具体问题 | 对 LinkMesh Writer 的潜在影响 |
|---|---|---|---|---|
| G1 | Triangle 输出仅含线性节点（三角形三顶点），M3DC1 C1 单元需要边中点（高阶节点） | C1 reduced quintic 基函数需要边中点作为额外自由度载体 | `c1_12_element.F90` 中是否需要边中点？`m3dc1_field.cc` 中如何生成边中点？ | LinkMesh `writers/smb_writer.py` 可能需要在写出前生成边中点 |
| G2 | Triangle 的 `triangleattributelist` 中的 `region_id` 与 M3DC1 的物理区域语义（plasma/vacuum/wall）之间需要显式映射 | Triangle 只输出数值 ID；M3DC1 需要物理语义标签来选择方程 | `m3dc1_model.cc` 中 region_id 到物理方程的映射逻辑 | LinkMesh `writers/smb_writer.py` 需要写入正确的区域语义标记 |
| G3 | Triangle 输出的 `segmentmarkerlist` 边界标记与 M3DC1 的边界条件类型之间需要显式映射 | Triangle 边界标记是整数 ID；M3DC1 边界条件类型是物理语义 | `m3dc1_model.cc` 中边界标记到边界条件类型的映射 | LinkMesh `writers/smb_writer.py` 需要写入正确的边界标记 |
| G4 | Triangle 输出的拓扑连接表使用全局节点编号，M3DC1 可能需要基于 SCOREC/PUMI 实体句柄的拓扑表示 | SCOREC/PUMI 使用面向对象的网格实体模型；Triangle 使用平坦数组索引 | `m3dc1_mesh.cc` 中如何将平坦数组索引转换为 SCOREC/PUMI 实体句柄？ | LinkMesh `writers/smb_writer.py` 需要按 PUMI `.smb` 二进制协议写出正确的实体句柄结构 |

---

## 7. 待确认事项与主管决策点

| 编号 | 待确认事项 | 影响范围 | 建议决策方向 |
|---|---|---|---|
| D1 | Step 2 侦察是否按路线 A→B 的顺序串行执行？ | Step 2 执行计划 | 建议优先串行执行 A+B（P0 路线） |
| D2 | Step 2 侦察结果是否需要更新 `LinkMesh_Architecture_Plan.md`？ | 主线蓝图更新触发条件 | 建议先形成独立 Step 2 报告，由主管确认后再决定是否触发蓝图更新 |
| D3 | 预期缺口 G1（高阶节点生成）是否需要在 LinkMesh `writers/smb_writer.py` 中实现？ | LinkMesh Writer 实现边界 | 需要 Step 2 确认 `m3dc1_field.cc` 中高阶节点生成逻辑后再决策 |
| D4 | 预期缺口 G4（PUMI 实体句柄结构）的 `.smb` 二进制协议是否已有足够的逆向证据？ | LinkMesh `writers/smb_writer.py` 实现 | 需要 Step 2 读取 `m3dc1_mesh.cc` 后确认 |
