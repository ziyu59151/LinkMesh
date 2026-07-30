# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **3.6**（本版依据 User 当前决定、实时仓库证据和 `docs/linkmesh/LinkMesh_Group_Delivery_and_SCOREC_Helper_Deployment_Analysis.md`，固化本地开发与服务器验证分工、四类环境、发布可追溯性、LinkMesh SCOREC helper 一次性命名迁移、Python 正式安装、native 构建安装、个人发布候选和组内版本化共享 release 契约；同步更新 EAST `array_file` 生成侧状态；本版仅更新正式文档，不实施 helper 重命名，不修改 Python、C++、CMake、测试、依赖、构建产物或部署脚本，不改变 Mesh2D、TRIMEG HDF5、M3D-C1 TXT、SMB schema v1、classification、PUMI 生命周期或 OFT/Triangle 契约）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`；本轮输入层调查参考见 `docs/linkmesh/LinkMesh_Boundary_Input_Architecture_Analysis.md`，该文件保存 EAST 文件调查、R-Z 几何验证、边界输入分层分析、`array_file` 架构建议及 `flux_surface` 概念与证据边界，但不是第二份蓝图，与本文冲突时以本文为准；M4-0 前置侦察逐轮证据见 `report.md`、`m4_0d_report.md`、`m4_0d1_report.md`、`m4_0d2_report.md`；OFT Region 重采样接口冲突只读核对见 `m3_complete11a_report.md`
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION / NOT IMPLEMENTED】为已批准正式契约但尚未实现的功能；【P0 禁止】为当前阶段严格禁止引入的功能；【实现候选】为已有源码调用点线索但须目标版本与最小运行验证确认、不得写成固定接口的路线；【版本锁定兼容接口】为 User 已批准、绑定特定 OFT 版本、范围受控、失败即停止的私有依赖，不是通用稳定公共 API
- 修改前置条件：任何对本文档接口、字段、格式、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位、范围与当前状态

### 1.1 项目定位

LinkMesh 是一个独立命令行程序（CLI），用于打通：

```text
等离子体平衡文件 GFile/EQDSK
  → 二维非结构三角网格
  → 目标求解器静态网格文件
```

唯一网格生成底座是 OFT/TokaMaker 封装方式调用的 Triangle，OFT 内部经
`liboft_triangle` 完成。LinkMesh 不维护第二种网格引擎。

SCOREC/PUMI 不是第二剖分器。LinkMesh 使用目标 PUMI 软件包提供的 APF、MDS、
GMI、PCU 与 PUMI 接口，将既有 `Mesh2D` 和 `M3DC1ModelSpec` 转换为 classified
APF/MDS mesh，并调用官方 `writeNative()` 生成 SMB。PUMI/APF/MDS 不重新生成
三角剖分。

### 1.2 总体数据流

```text
GFile/EQDSK
  → Reader
  → OFT Adapter
  → Mesh2D
      ├── TRIMEG HDF5 Writer → HDF5
      ├── M3DC1 model Adapter → M3DC1ModelSpec
      │     ├── TXT Writer → <base>.txt
      │     └── SMB Writer → native helper → rank-0 native SMB
      └── Plotter → PNG
```

M3D-C1 P0 正式生产链：

```text
GFile
  → OFT/Triangle
  → Mesh2D
  → single-face M3DC1 model Adapter
  → M3DC1ModelSpec
      ├── LinkMesh TXT model Writer
      └── LinkMesh SCOREC/PUMI Adapter
            → classified APF/MDS mesh
            → 目标版本官方 writeNative()
            → 分区前串行 native SMB
```

TXT Writer 与 SCOREC/PUMI Adapter 必须由同一个 `M3DC1ModelSpec` 驱动，共享
geometric vertex tags、geometric edge tags、loop tags、face tags、edge endpoint
order、face↔loop topology 与 geometric classification 语义。禁止两条输出路径独立
编号。

### 1.3 P0 范围

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；`array_file` counted R-Z boundary text 为已批准、待实现契约 | LinkMesh 手写 GFile 解析；复杂 CAD；多维输入；Python ndarray 公共边界 API；CSV、表头、注释或多轮廓边界格式 |
| 网格生成 | OFT `gs_Domain` / `build_mesh()` 调用 Triangle | 第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；维护 OFT 分支 |
| 分区 | LinkMesh 不涉及；终点为分区前串行 native SMB | `split_smb`、`part*.smb`、`**1.smb`～`**16.smb`、环向或并行分区 |
| 输出 | TRIMEG HDF5；M3D-C1 analytic model TXT + 分区前串行 PUMI native SMB | Simmetrix、`make_model`、`.smd`、`.sms` 正式依赖；手写、解析、修改、拼接、模板复制或逆向 SMB 字节 |
| 可视化 | matplotlib PNG 自检 | 交互式或三维渲染 |
| 配置 | `linkmesh.in` + CLI + `EffectiveConfig` | 通用配置 DSL、任意 N 区域语言、插件系统 |

### 1.4 事实环境边界

- 本地 LinkMesh 仓库是开发和蓝图维护工作区。
- `/data/liuchang/east_fishbone_1/`、`/opt/spack` 与 `/data/liuchang` 属于服务器
  外部环境，不是本地运行时依赖，不得由本地开发流程访问、创建或假定存在。
- `east.txt` 的 1 loop、104 geometric vertices、104 geometric edges、闭合末边和
  1 face 只辅证 `save_model`/`save_multi_rgn_model` ↔ `load_model` 契约。104、
  固定坐标、文件大小与摘要都不是格式常量。
- 服务器日志确认旧流程使用 Simmetrix 创建 geometric model、写 `.smd`、生成并写
  `.sms` 后重新加载；现有证据未确认 `.sms` 到 `.smb` 的具体命令。
- LinkMesh M4-1B probe 和 M4-2 helper 已在目标 PUMI 环境完成构建和生成侧运行。
- 正式 TXT+SMB 已由真实 M3D-C1/SCOREC 环境成功加载并完成初始化。
- 成功加载与初始化不表示时间推进、稳定性或物理正确性已经通过。

### 1.5 当前权威状态表

| 阶段或能力 | 状态 |
|---|---|
| M1 Reader | **PASSED** |
| M2 默认 `nested_three_region + artificial_outer` | **PASSED** |
| DIII-D GFile 单区域网格生成 | **PASSED** |
| M3 core | **PASSED** |
| M3 complete-11 | **PASSED** |
| TRIMEG 标准 MATLAB 消费端 A/B 验收 | **PASSED** |
| M4-0 只读侦察与架构契约 | **已完成** |
| M4-1A ModelSpec + TXT Writer + Level 1 | **PASSED** |
| M4-1B 实现入口 probe | **COMPLETED / PASSED** |
| M4-2 TXT Writer | **PASSED** |
| M4-2 SMB Writer/helper 生成侧 | **IMPLEMENTED / PASSED** |
| M5 第一条 `single_region + lcfs` M3DC1 CLI | **PASSED** |
| M5 PNG 人工检查 | **PASSED** |
| M3D-C1 配套 TXT+SMB 加载 | **PASSED** |
| M3D-C1 初始化 | **PASSED** |
| M3D-C1 时间推进主循环 | **PENDING** |
| M3D-C1 中等或长时运行稳定性 | **PENDING** |
| M3D-C1 物理结果正确性 | **PENDING** |
| EAST 文件结构调查 | **PASSED** |
| EAST R-Z 列顺序、单位与基础几何验证 | **PASSED** |
| EAST 物理构造算法及其与 LCFS、第一壁、磁轴、X-point 的精确关系 | **PENDING** |
| `single_region + array_file` 正式输入契约与实现 | **IMPLEMENTED / PASSED** |
| EAST counted R-Z 读取、单区域 OFT/Triangle、Mesh2D 与 PNG | **PASSED** |
| EAST TXT+SMB+PNG 生成侧 | **PASSED** |
| EAST M3D-C1 加载与初始化回归 | **PENDING** |
| EAST M3D-C1 时间推进 | **PENDING** |
| TCV 参考边界调查 | **PENDING** |
| TCV/TRIMEG 实际消费 | **PENDING** |
| `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED；未开放** |
| `single_region + array_file` | **IMPLEMENTED / PASSED；EAST 生成侧已验收** |
| `single_region + flux_surface` | **实现候选 / NOT IMPLEMENTED；需 OFT 26.6 只读侦察，未开放** |
| 多区域、多 face、三维、自适应网格和并行分区 | **OUT OF P0 / 未开放** |

### 1.6 下一阶段摘要

EAST 已确认为通过无扩展名纯文本文件提供的独立二维计算边界；文件结构、R-Z 列顺序、
单位和基础几何验证已通过。其具体物理构造算法及其与 LCFS、第一壁、磁轴和 X-point
的精确关系仍待确认，不阻塞读取研究人员已经确认的最终计算边界，也不得据此把该边界
标记为 LCFS、第一壁或内部磁面。

当前 EAST 生成侧链路为：

```text
counted R-Z boundary text
  → single_region + array_file
  → OFT/Triangle
  → Mesh2D
  → TXT + rank-0 SMB + PNG
```

该链路已通过生成侧验收：输入边界 104 点，OFT 输出 185 个节点、329 个三角形和
1 个区域；PNG 已由 User 完成人工几何检查。TXT、SMB 和 PNG 是通过当前旧环境变量
`LINKMESH_M3DC1_SMB_HELPER` 指向既有开发构建产物后生成。该证据不表示 EAST
M3D-C1 加载、初始化、时间推进、长期稳定性或物理正确性已经通过。

当前后续主线为：

```text
交付蓝图与命名迁移准备
  → helper 全量命名迁移与正式安装能力
  → 个人发布候选环境
  → EAST M3D-C1 加载和初始化回归
  → EAST M3D-C1 时间推进主循环
  → 组内版本化共享发布
```

TCV/TRIMEG 是并行的第二条真实消费验证路线。既有 M3D-C1 TXT+SMB 加载与初始化
继续保持 PASSED；时间推进、中等或长时稳定性及物理正确性继续保持 PENDING。

---

## 2. 总体架构与模块职责

### 2.1 允许依赖方向

```text
cli
  → config
  → readers
  → mesher
  → writers
  → utils

mesher.oft_adapter → mesh
writers → mesh
utils.plotter → mesh
readers.boundary_reader → mesh
utils.plotter → readers（仅用于可选的 GFileData 类型信息，不读取业务文件）
```

`config` 不依赖 Reader、Mesher、Writer 或 Plotter。`mesh.py` 不依赖任何后端、
Writer、CLI、Plotter 或 config。

### 2.2 模块职责

| 模块 | 职责 | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 参数解析和业务逻辑 |
| `src/linkmesh/cli.py` | 收集显式 CLI 参数；拦截历史参数；调用配置合并；编排 Reader → Mesher → Writer → Plotter | 几何、区域、种子、Triangle、dx 换算、配置默认值合并、SMB rank 改写、helper 环境变量解析 |
| `src/linkmesh/config.py` | 定义冻结的 `EffectiveConfig`；严格读取 TOML；执行默认值、配置文件、CLI 合并；验证兼容矩阵和 required fields | 读取业务文件；创建 OFT Domain；调用 Writer；通用 DSL、插件或任意 N 区域语言 |
| `src/linkmesh/readers/gfile_reader.py` | 调用 OFT `GEQDSKEquilibrium` 并输出 `GFileData` | 手写 GFile 解析；调用 Triangle；写文件 |
| `src/linkmesh/readers/boundary_reader.py` | 实现 `read_boundary_file(filepath: str \| Path) -> np.ndarray`；严格读取 counted R-Z boundary text，返回独立 `(N,2) float64` 米制边界，并复用统一边界几何验证与方向规范化 | 创建 `Mesh2D` 或 OFT Domain；调用 OFT/Triangle；读取 GFile；判断物理语义；平滑、重采样、排序、全局去重或缩放；使用 pandas |
| `src/linkmesh/mesh.py` | 定义统一 `Mesh2D`、统计属性和 `outer_boundary` 集中验证 | 依赖后端或目标格式；读取 OFT 私有属性 |
| `src/linkmesh/mesher/oft_adapter.py` | 构造 OFT Domain；调用唯一 Triangle 底座；规范化 OFT 输出；受控读取 outer Region 回写边界 | 配置解析；复制 OFT 算法；读取禁止的 OFT 私有结构；写文件 |
| `src/linkmesh/m3dc1_model.py` | 定义 `M3DC1ModelSpec` 并从 `Mesh2D.outer_boundary` 构造 single-face model | PUMI、MPI、Simmetrix 依赖；保存 PUMI 句柄；固定 104 点 |
| `src/linkmesh/writers/hdf5_writer.py` | 按 TRIMEG 11 数据集契约写出 | 修改输入；写 `region_ids`；转置；网格生成 |
| `src/linkmesh/writers/m3dc1_model_writer.py` | 按 M3D-C1 analytic model 契约写 TXT | 复制样例坐标；调用 Simmetrix；独立分配 tags |
| `src/linkmesh/writers/smb_writer.py` | 验证输入；生成 classification 和交换文件；调用 helper；确认 rank-0 SMB | 创建 APF/MDS entity；读写 SMB 字节；硬编码 PUMI 路径 |
| `native/m3dc1_smb_helper/main.cc` | 读取交换文件；管理 MPI/PCU/GMI/APF/MDS；创建 classified mesh；调用官方 `writeNative()` | 网格剖分；配置；TXT Writer；loader/validator；多区域、多 face、三维或分区 |
| `native/m3dc1_smb_helper/CMakeLists.txt` | 构建唯一 helper target | 通用 native/plugin 框架；Python 扩展；运行时编译；硬编码安装前缀 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`；待最小调整的 `plot_mesh()` 以 `Mesh2D` 及实际计算边界完成基础 PNG，自愿接收 `GFileData` 叠加 LCFS、第一壁和磁轴参考 | 修改数据对象；要求所有路径必须提供 GFile；把外部边界伪装成 LCFS |

---

## 3. 核心数据契约

### 3.1 `GFileData`

坐标单位为 m，R 为大半径，Z 为垂直方向。字段由 OFT
`GEQDSKEquilibrium` 属性提取。

| 字段 | 类型/shape | 来源 | 说明 |
|---|---|---|---|
| `lcfs_r` / `lcfs_z` | `np.ndarray (N_lcfs,)` | `boundary_R` / `boundary_Z` | LCFS [m] |
| `rmaxis` / `zmaxis` | `float` | `R_mag` / `Z_mag` | 磁轴 [m] |
| `wall_r` / `wall_z` | `Optional[np.ndarray (N_wall,)]` | `limiter_R` / `limiter_Z` | 第一壁；无可用轮廓时为 `None` 或空 |
| `rcentr` | `Optional[float]` | `R_center` | R0 [m] |
| `bcentr` | `Optional[float]` | `B_center` | B0 [T] |
| `current` | `Optional[float]` | `Ip` | 等离子体电流 [A]，不缩放 |

### 3.2 `Mesh2D`

`Mesh2D` 是 LinkMesh 面向 TRIMEG、M3D-C1/PUMI 等下游的统一、持久、
求解器无关中间对象。

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | `[R,Z]`，单位 m |
| `triangles` | `(T,3)` | 整数，实测 `int32` | 内部 0-based |
| `region_ids` | `(T,)` | 整数，实测 `int32` | OFT 区域编号原样保留，不重编号、排序、压缩或 `+1` |
| `boundary_segments` | `(0,2)` 默认 | `int32` | 兼容字段 |
| `boundary_markers` | `(0,)` 默认 | `int32` | 兼容字段 |
| `node_markers` | `(0,)` 默认 | `int32` | 兼容字段 |
| `outer_boundary` | `Optional[(B,2)]` | `float64` | Triangle 输入前的有序最外层计算域边界 |

只读统计属性：`n_nodes`、`n_triangles`、`n_boundary_segments`。

由 `triangles` 可确定性派生的边和邻接关系默认不重复存储。P0 不保存 C1 自由度、
高阶节点、PUMI 句柄、MPI ownership、运行时 field 或求解器私有对象。

### 3.3 `outer_boundary`

| 属性 | 契约 |
|---|---|
| shape/dtype | `(B,2)` / `float64` |
| 列与单位 | 第 0 列 R，第 1 列 Z；m |
| 语义 | 进入 Triangle 前的有序最外层计算域几何边界 |
| 闭合 | 末尾不重复首点，最后一点到第一点隐式闭合 |
| 方向 | 顺时针；带符号闭合面积严格为负 |
| 几何 | 至少 3 个互异有限点；无相邻重复、零长度闭合边、退化面积或非相邻边自交 |
| 所有权 | `Mesh2D` 持有独立 `float64` 副本，不共享输入内存 |
| 必选性 | TRIMEG 必须提供；其他 target 按自身契约，可为 `None` |
| Steiner 点 | 不包含 Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑边界节点集合 |
| 起点 | 不规定固定起点；反向时保持原起点 |

统一验证入口 `_validate_outer_boundary` 必须检查 shape、dtype、有限性、点数、
相邻重复、闭合、方向、面积和完整非相邻边自交，包括严格交叉、端点接触和共线重叠；
不得误判相邻边、首末相邻边、合法凹多边形或区间分离的共线边。坐标容差和 orientation
叉积容差必须分别使用长度和长度平方量纲。

`outer_boundary` 不是人工矩形四角、`Region.get_resampled_points()`、最终
`idxevert`、Triangle 插入的所有边界点、最终 `pts/lc` 反推点列或 LinkMesh 自行
重采样点列。

### 3.4 `EffectiveConfig`

`EffectiveConfig` 是 `@dataclass(frozen=True)`，是默认值、配置文件和显式 CLI
合并、类型校验、路径解析、兼容矩阵及 required-fields 校验后的唯一配置对象。

| 字段 | 类型 |
|---|---|
| `schema_version` | `int`，固定 `1` |
| `config_path` | `Optional[Path]` |
| `target` | `Literal["mesh_only","trimeg","m3dc1"]` |
| `profile` | `Literal["single_region","nested_three_region"]` |
| `boundary_source` | `Literal["lcfs","first_wall","array_file","artificial_outer","flux_surface"]` |
| `gfile_path` | `Optional[Path]` |
| `array_file_path` | `Optional[Path]` |
| `plasma_dx` | `float` |
| `vacuum_dx` | `float` |
| `outer_dx` | `float` |
| `hdf5_path` | `Optional[Path]` |
| `plot_path` | `Optional[Path]` |
| `model_path` | `Optional[Path]` |
| `smb_path` | `Optional[Path]` |
| `verbose` | `bool` |

所有非 `None` 路径在构造前解析为绝对路径。对象不保存来源字典、NumPy 数组、
`Mesh2D`、`GFileData`、PUMI 句柄、Writer、argparse Namespace 或可变业务状态。

### 3.5 `M3DC1ModelSpec`

`M3DC1ModelSpec` 表达 P0 single-region、single-face、single-loop analytic model：

- geometric vertices：唯一 tag 和 `[R,Z,0]`；
- directed geometric edges：唯一 tag、begin/end vertex tag、`LIN=1`；
- geometric loop：唯一 tag 和有序 edge tags；
- geometric face：唯一 tag 和 loop tags；
- special loop tags：`separatrix_loop`、`inner_wall_loop`、`outer_wall_loop`、
  `vacuum_loop`。

Adapter 从 `Mesh2D.outer_boundary` 动态构造全部实体。不得固定点数，不得把
`region_ids` 自动当作 geometric face tag，不得保存 PUMI/SCOREC 句柄。

---

## 4. 网格生成与物理约定

### 4.1 坐标、单位和索引

- 坐标为 `[R,Z]`，使用 SI：m、T、A。
- `Mesh2D.triangles` 内部为 0-based。
- 目标格式偏置由 Writer 完成。
- `region_id` 与节点索引无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- 三角形不得有重复顶点、越界索引或绝对面积不大于 `1e-12`。

### 4.2 OFT/Triangle 与区域语义

OFT 输出契约：

- `pts (N,2) float64`；
- `lc (T,3)` 0-based 整数，满足 `0 <= lc < N`；
- `reg (T,)` 正整数；
- `reg` 与 `domain.region_info` 最终 ID 一一对应。

`mesh_from_oft_domain()` 必须在 `build_mesh()` 后读取最终 `region_info`，验证：

1. 至少一个区域；
2. `reg` 全为有限正整数；
3. `len(reg) == T`；
4. 输出 ID 集合与最终 `region_info` 一致；
5. 每个区域至少有一个三角形；
6. 不重编号、排序、压缩或 `+1`。

默认 nested 策略：

- 有有效第一壁：PLASMA + VACUUM + OUTER；
- 无有效第一壁：PLASMA + OUTER；
- 输入使用 GFile LCFS、可选 limiter/第一壁和 LinkMesh 固定策略构造的
  `artificial_outer`；
- 该生成路径已实现，并已有真实 DIII-D 与 fixed-boundary CLI、HDF5 和 PNG
  的 LinkMesh 生成侧验收证据；
- 该结论不开放 M3D-C1 多区域或多 face，不表示支持任意区域拓扑、三维、自适应
  网格或并行分区。

single-region 的 LCFS、first wall、array file 和 flux surface 只在边界获取阶段
不同；合法边界进入 Mesher 前统一为 `(B,2)` 的二维闭合轮廓，并复用同一
single-region OFT Domain 和 OFT/Triangle 核心。`Mesh2D` 与 Writer 不按来源分叉。
具体策略见第 5.10 节。

### 4.3 `merge_thresh` 与边界方向

- OFT 26.6 `build_mesh()` 使用锁定默认 `merge_thresh=1e-4 m`。
- P0 不将 `merge_thresh` 暴露为 CLI 或配置字段。
- single-region polygon 相邻近重复过滤阈值必须与该值同步。
- 若显式改变 `build_mesh()` 的 `merge_thresh`，必须先更新蓝图、规范化阈值和测试。
- `outer_boundary` 最终必须顺时针；逆时针转换使用
  `[p0, p_(B-1), …, p1]`，不得使用改变起点的裸 `pts[::-1]`。

### 4.4 OFT 26.6 私有兼容接口

【已确认事实】OFT 26.6 没有公共方法返回指定 Region 对应的 Triangle 输入前有序
离散边界。`Region.get_resampled_points()` 使用独立重采样路径，不是 Triangle
输入来源，禁止作为 `outer_boundary` 来源。

`Mesh.__init__()` 完成边界重采样、共享边界处理、点合并、全局重编号和 segment
方向处理，并将有序区域点列写入 `region._resampled_points`。`Mesh.get_mesh()`
将 `Mesh._resampled_points` 传给 Triangle。

受控数据链：

```text
边界来源
  → single-region 相邻近重复规范化
  → 策略层创建 outer Region 并保存引用
  → domain.build_mesh()
  → 读取同一个 outer_region._resampled_points
  → float64 独立副本
  → 删除一个普通显式闭合重复末点
  → 验证并规范化为顺时针
  → Mesh2D.outer_boundary
```

唯一允许读取的 OFT 私有属性是策略层已捕获 Region 的
`outer_region._resampled_points`。

禁止读取或解析：

- `domain.mesh._reg_seg_map`
- `domain.mesh._resampled_segments`
- `domain.mesh._resampled_points`

Region 输入和回写语义：

- `Region.__init__()` 仅在首末距离小于 `dx/1000` 时删除显式闭合末点。
- 相邻边小于 `dx_curve/1000` 时可能警告但不删除控制点。
- 全局点距离严格小于 `1e-4 m` 时映射到同一全局点。
- Region 回写点列按有向 segment 拓扑重建，可能重复引用合并后的坐标。
- OFT warning 不等同于 Triangle 失败。
- LinkMesh 不得放宽 `Mesh2D` 契约接纳回写重复坐标。

读取时机固定为：

1. 规范化 single-region polygon 控制点；
2. 创建 outer Region；
3. 立即保存该对象引用；
4. 执行 `domain.build_mesh()`；
5. build 后读取保存对象的 `_resampled_points`；
6. 创建独立 `float64` 副本；
7. 删除可能存在的一个普通显式闭合重复末点；
8. 验证 shape、有限性、点数、简单闭环和自交；
9. 规范化为顺时针并保持起点；
10. 写入 `Mesh2D.outer_boundary`。

以下情况必须失败：

- OFT 版本不是 26.6；
- Region 未捕获或属性缺失、为 `None`；
- shape 不是 `(B,2)`；
- 存在 NaN/Inf；
- 点数不足；
- 规范化后相邻重复、首尾重复、自交或面积退化；
- 无法证明该 Region 是策略层创建的最外边界；
- OFT 私有接口与已核对数据流不一致。

禁止回退到人工四角、原始 LCFS、`Region.get_resampled_points()`、`idxevert`、
最终 `pts/lc` 反推、LinkMesh 自行重采样或对 TRIMEG 静默设置
`outer_boundary=None`。

### 4.5 OFT 升级纪律

OFT 私有接口是版本锁定、范围受控、失败即停止的兼容接口。升级 OFT 时必须重新核对：

- `Region` 创建及捕获方式；
- `_resampled_points` 写回时机和语义；
- `build_mesh()` 默认 `merge_thresh`；
- Triangle 输入数据流；
- 真实 GFile、HDF5、PNG 和相邻回归。

不得把 OFT 26.6 私有实现假定为跨版本公共 API。

---

## 5. 输入、配置与 CLI 契约

### 5.1 权威性和模块落点

配置契约的唯一权威是：

1. `EffectiveConfig` 字段级契约；
2. 三层合并算法；
3. compatibility matrix；
4. required-fields。

模块落点：

- `src/linkmesh/config.py`：配置读取、严格校验、合并和阶段闸门；
- `src/linkmesh/readers/boundary_reader.py`：计划中的 counted R-Z boundary text Reader；
- `src/linkmesh/cli.py`：显式参数收集与业务编排；
- `src/linkmesh/mesher/oft_adapter.py`：边界来源对应的 OFT 策略；
- 不新增 `inputs/`、抽象基类、注册表、插件或任意 N 区域语言。

### 5.2 边界输入分层

边界输入必须分别描述以下三个层次：

| 层次 | 当前正式类别 |
|---|---|
| 输入载体 | GFile/EQDSK；外部二维边界纯文本 |
| 边界物理语义 | LCFS；limiter/第一壁相关轮廓；内部闭合磁面；外部提供的计算边界 |
| 边界构造方法 | GFile 直接读取；从 GFile 磁通场提取；外部程序构造；研究人员直接提供；LinkMesh 固定策略构造 `artificial_outer` |

输入载体、物理语义和构造方法不得互相替代或互相推断。`array_file` 只表示边界通过
外部二维文件进入 LinkMesh，不表示 CSV、NumPy 文件或特定扩展名，也不自动表示
LCFS、第一壁或磁通面。

不同来源必须先归一为统一二维闭合计算边界，再进入 single-region OFT Domain。
Reader 负责获取边界，Mesher 负责构造 Domain，Writer 只消费 `Mesh2D`，不得跨层
猜测来源或物理语义。

### 5.3 内建默认值

| 字段 | 内建默认值 |
|---|---|
| `schema_version` | `1` |
| `target` | `"trimeg"` |
| `profile` | `"nested_three_region"` |
| `boundary_source` | `"artificial_outer"` |
| `plasma_dx` | `0.08` |
| `vacuum_dx` | `0.10` |
| `outer_dx` | `0.15` |
| `verbose` | `False` |
| `gfile_path` | `None` |
| `array_file_path` | `None` |
| `hdf5_path` | target 为 `trimeg` 时为当前工作目录下 `mesh.h5` |
| `plot_path` | `None` |
| `model_path` | `None` |
| `smb_path` | `None` |

裁决规则：

- `mesh.h5` 是配置合并后的 target 条件默认值，不是 `--output` 的 argparse 默认值。
- `smb_path` 不存在 `mesh.smb` 隐式默认值。`target=m3dc1` 时必须通过配置文件或
  显式 CLI 提供。
- `gfile_path=None`。是否必需由 `boundary_source` 和 required-fields 决定。
- `outer_padding` 和 `merge_thresh` 不是配置字段。
- 默认行为保持 `trimeg + nested_three_region + artificial_outer`。

### 5.4 `linkmesh.in` TOML v1

顶层必须包含：

```toml
schema_version = 1
```

只允许：

```text
顶层：
  schema_version

[task]
  target

[input]
  gfile
  array_file

[domain]
  profile
  boundary_source

[mesh]
  plasma_dx
  vacuum_dx
  outer_dx

[output]
  hdf5
  plot
  model
  smb

[runtime]
  verbose
```

| TOML 键 | 类型 | 映射 |
|---|---|---|
| `schema_version` | 非布尔整数，必须为 `1` | `schema_version` |
| `[task].target` | 枚举字符串 | `target` |
| `[input].gfile` | 非空字符串 | `gfile_path` |
| `[input].array_file` | 非空字符串 | `array_file_path` |
| `[domain].profile` | 枚举字符串 | `profile` |
| `[domain].boundary_source` | 枚举字符串 | `boundary_source` |
| `[mesh].plasma_dx` | 有限正数 | `plasma_dx` |
| `[mesh].vacuum_dx` | 有限正数 | `vacuum_dx` |
| `[mesh].outer_dx` | 有限正数 | `outer_dx` |
| `[output].hdf5` | 非空字符串 | `hdf5_path` |
| `[output].plot` | 非空字符串 | `plot_path` |
| `[output].model` | 非空字符串 | `model_path` |
| `[output].smb` | 非空字符串 | `smb_path` |
| `[runtime].verbose` | TOML bool | `verbose` |

严格规则：

1. 未知顶层键、section 或 section 内键立即报 `ConfigError`。
2. section 必须为 table。
3. 路径必须为非空字符串。
4. dx 接受整数或浮点数，拒绝 bool、NaN、Inf、零和负数。
5. `verbose` 只接受 TOML bool。
6. TOML 语法、读取和 schema 错误必须包含文件路径和字段位置。
7. 配置层不读取业务文件，不创建目录。
8. `examples/m3dc1_single_region/linkmesh.in.example` 已存在；示例不产生新规则，
   也不开放未实现组合。

### 5.5 CLI 参数与 `UNSET`

| CLI 参数 | argparse 目标 | 合并语义 |
|---|---|---|
| `--config PATH` | `config` | 指定唯一配置文件 |
| `--no-config` | `no_config` | 禁止自动发现 |
| `--target VALUE` | `target` | 覆盖 `[task].target` |
| `--profile VALUE` | `profile` | 覆盖 `[domain].profile` |
| `--boundary-source VALUE` | `boundary_source` | 覆盖 `[domain].boundary_source` |
| `--gfile PATH` | `gfile` | 覆盖 `[input].gfile` |
| `--array-file PATH` | `array_file` | 覆盖 `[input].array_file` |
| `--plasma-dx FLOAT` | `plasma_dx` | 覆盖 `[mesh].plasma_dx` |
| `--vacuum-dx FLOAT` | `vacuum_dx` | 覆盖 `[mesh].vacuum_dx` |
| `--outer-dx FLOAT` | `outer_dx` | 覆盖 `[mesh].outer_dx` |
| `--output PATH` | `hdf5` | 覆盖 `[output].hdf5` |
| `--plot PATH` | `plot` | 覆盖 `[output].plot` |
| `--model PATH` | `model` | 覆盖 `[output].model` |
| `--smb PATH` | `smb` | 覆盖 `[output].smb`，表示未插 rank 的基础路径 |
| `--verbose` | `verbose` | 显式出现时覆盖为 `True` |

参与合并的 CLI 参数必须使用 `UNSET` 区分未提供与显式提供。CLI 层不得通过业务默认
值覆盖 TOML。

附加规则：

- `--config` 与 `--no-config` 互斥。
- `--verbose` 未出现时保持 `UNSET`。
- `--no-hdf5` 和 `--no-smb` 是执行期开关，不进入 `EffectiveConfig`，不取消
  required-fields。
- `--min-angle` 默认 `20.0`；非默认值在读取配置或调用 OFT 前拒绝。
- `--max-area` 默认 `None`；一旦提供立即拒绝。
- CLI 不将 `--smb` 改写为 rank-0 文件名。
- CLI 不解析 `LINKMESH_M3DC1_SMB_HELPER`。
- CLI 不硬编码 PUMI 安装路径。

### 5.6 配置发现和三层合并

发现顺序：

1. 同时提供 `--config` 和 `--no-config`：失败。
2. 提供 `--config PATH`：只读取该文件；不存在或非普通文件时失败。
3. 提供 `--no-config`：不加载配置。
4. 均未提供：只检查当前工作目录的 `linkmesh.in`。
5. 不递归父目录，不搜索主目录或仓库根，不从环境变量发现配置。

优先级：

```text
内建默认值 < linkmesh.in < 用户显式 CLI
```

算法：

1. 发现并严格解析 TOML。
2. TOML 相对路径以配置文件目录为基准。
3. CLI 相对路径以进程当前工作目录为基准。
4. 标量先取显式 CLI，否则 TOML，否则内建默认值。
5. 路径键映射：
   `gfile→gfile_path`、`array_file→array_file_path`、
   `hdf5→hdf5_path`、`plot→plot_path`、`model→model_path`、
   `smb→smb_path`。
6. 路径使用 `Path.resolve(strict=False)` 等价语义，不展开 `~` 或环境变量。
7. 合并后再次校验枚举、数值和 bool。
8. 构造冻结的 `EffectiveConfig`。
9. 执行兼容矩阵、required-fields 和阶段闸门。
10. 全部通过后才进入 Reader、OFT、Writer 或 Plotter。

配置层不要求输出文件已经存在，不创建父目录。输入业务文件存在性由 Reader 报告。
helper 定位不属于 `EffectiveConfig`。

### 5.7 `array_file` v1：counted R-Z boundary text

状态为 **IMPLEMENTED / PASSED**。正式语法为：

```text
N
R_1 Z_1
R_2 Z_2
...
R_N Z_N
```

| 项目 | 正式契约 |
|---|---|
| 文件 | 纯文本；扩展名不参与格式判断，无扩展名合法 |
| 计数头 | 第一行只包含一个十进制整数 `N`，且 `N >= 3` |
| 数据行数 | 计数头后必须恰好有 `N` 行，不得少、多或包含额外数据 |
| 坐标行 | 每行恰好两个有限浮点数，以一个或多个空白字符分隔 |
| 列与单位 | 第一列 R，第二列 Z；单位 m |
| 输出 | 独立 `(N,2) float64` 数组 |
| 闭合 | 输入隐式闭合；首末点不得重复；最后一点由 LinkMesh 连接回第一点 |
| 几何 | 至少 3 个互异节点；无相邻重复、零长度闭合边、零面积或自交；P0 只允许一条简单闭环 |
| 方向 | 输入可顺时针或逆时针；进入 `Mesh2D.outer_boundary` 前规范为顺时针并保持起点 |

P0 明确不支持 CSV 逗号分隔、表头、注释、索引列、额外列、空数据行或多条轮廓。
不得根据文件名或内容猜测其他格式，不得自动排序、重采样、全局去重、平滑、缩放、
投影或最近距离修补，也不得把外部边界自动解释为 LCFS、第一壁或磁通面。EAST
原始点序为逆时针不改变 `Mesh2D.outer_boundary` 的全局顺时针契约。

已实现接口为：

```text
src/linkmesh/readers/boundary_reader.py
read_boundary_file(filepath: str | Path) -> np.ndarray
```

职责与错误边界：

1. Reader 只读取并验证 counted R-Z boundary text，返回独立 `(N,2) float64`。
2. 文件不存在或不可读取沿用 `FileNotFoundError`/`OSError`。
3. 文件语法错误与数值词法错误使用 `BoundaryFormatError(ValueError)`，错误信息包含
   路径、行号和原因。
4. 成功解析后先按现有方向约定规范化并保持起点，再复用 `mesh.py` 的统一
   `_validate_outer_boundary`；几何非法沿用 `ValueError`。
5. Reader 不解析 GFile，不构造 OFT Domain 或 `Mesh2D`，不生成网格，不判断物理
   来源，不执行平滑、重采样、排序、全局去重或缩放，不使用 pandas。
6. CLI 只调用 Reader 并编排后续流程，不自行读取或验证文件内容。

EAST 直接证据：

- 路径 `/data/liuchang/east_fishbone_1/EAST`；
- 无扩展名纯文本，`N=104`，随后恰好 104 行 R-Z 米制坐标；
- shape 为 `(104,2)`，首末不重复，隐式闭合，输入逆时针且无自交；
- R 约为 `1.465..2.269 m`，Z 约为 `-0.627..0.563 m`；
- 面积约 `0.7211 m²`，周长约 `3.1574 m`；
- 图形和量级符合 EAST 二维极向截面的工程预期；
- 它是与 EQDSK、M3D-C1 TXT 和 SMB 分离的外部二维计算边界；
- 具体物理构造算法及其与 LCFS、第一壁、磁轴和 X-point 的精确关系仍为
  PENDING，但不阻塞读取已由研究人员确认的最终边界。

### 5.8 `boundary_source`

| 来源 | 正式来源 | 状态 | 规则 |
|---|---|---|---|
| `lcfs` | `GFileData.lcfs_r/lcfs_z` | 已实现 | single-region 唯一边界；不使用第一壁或人工外框 |
| `first_wall` | `GFileData.wall_r/wall_z` | 未实现 | 需要有效第一壁；首版 single-region |
| `array_file` | counted R-Z boundary text | 已实现并通过 EAST 生成侧验收 | 首版 single-region；EAST 主线；v1 与 GFile 互斥 |
| `artificial_outer` | LCFS/第一壁包围盒加固定 padding | 已实现并完成生成侧真实验收 | 当前只配 nested；四角不直接作为 `outer_boundary` |
| `flux_surface` | 从 GFile 二维极向磁通场提取指定内部闭合磁通等值线 | 实现候选，未实现，待 OFT 26.6 只读侦察 | 只用于 single-region 核心或内部等离子体计算域；禁止缩放 LCFS 伪造 |

共同规则：

- 每次任务只有一个计算域外边界来源。
- `lcfs`、`first_wall`、`artificial_outer` 需要 GFile。
- `array_file` v1 需要 array file，并禁止 GFile；未来若允许额外 GFile，只能作为
  蓝图明确批准的可选平衡参考，且不得改变实际计算边界，本版不开放该能力。
- `flux_surface` 不是文件格式或第二网格生成器，不能替代需要包含 X-point 或其附近
  区域的 EAST 外部边界。本轮不批准其业务实现；后续必须先只读确认 OFT 26.6
  的磁通场、归一化磁通、轮廓提取、多轮廓选择、闭合和方向接口。
- 未实现来源不得回退。
- 已实现来源必须走 Region 捕获、build 后回写和统一验证。

### 5.9 兼容矩阵

| target | profile | boundary_source | 状态 |
|---|---|---|---|
| `mesh_only` | `nested_three_region` | `artificial_outer` | 已实现 |
| `trimeg` | `nested_three_region` | `artificial_outer` | 已实现并验收 |
| `mesh_only` | `single_region` | `lcfs` | 已实现 |
| `trimeg` | `single_region` | `lcfs` | 已实现并验收 |
| `m3dc1` | `single_region` | `lcfs` | 已实现；加载和初始化通过 |
| `mesh_only` / `trimeg` | `single_region` | `first_wall` | 规划有效，未实现 |
| `mesh_only` | `single_region` | `array_file` | 已实现 |
| `trimeg` | `single_region` | `array_file` | 已实现；不改变 HDF5 契约 |
| `m3dc1` | `single_region` | `array_file` | 已实现；EAST 生成侧通过，外部消费待验收 |
| 任意 | `single_region` | `flux_surface` | 实现候选，未实现，待 OFT 26.6 只读侦察 |
| `m3dc1` | `single_region` | `first_wall` / `flux_surface` | 未开放 |
| `m3dc1` | `nested_three_region` | 任意 | 禁止 |
| 任意 | `nested_three_region` | `lcfs` / `first_wall` / `array_file` | 禁止 |
| 任意 | `single_region` | `artificial_outer` | 禁止 |

禁止组合使用 `ConfigError`。架构可表达但未实现的组合使用
`NotImplementedError`。旧测试若期待不同异常类型，应更新测试，不得放行组合。

### 5.10 required-fields

按边界来源：

| 来源 | 必需 | 禁止同时提供 |
|---|---|---|
| `lcfs` | `gfile_path` | `array_file_path` |
| `first_wall` | `gfile_path` | `array_file_path` |
| `artificial_outer` | `gfile_path` | `array_file_path` |
| `array_file` | `array_file_path` | `gfile_path`（v1 不开放可选平衡参考） |
| `flux_surface` | 未定义，阶段闸门报未实现 | 不得猜测 |

按 target：

| target | 必需输出 | 行为 |
|---|---|---|
| `mesh_only` | 无 | 不写 HDF5、TXT、SMB |
| `trimeg` | `hdf5_path` | 未使用 `--no-hdf5` 时写 HDF5 |
| `m3dc1` | `model_path`、`smb_path` | 总写 TXT；未使用 `--no-smb` 时写 SMB |

`--no-smb` 不使 `smb_path` 可选；`--no-hdf5` 不改变有效配置结构。配置层只验证字段
存在和组合，不读取业务内容。

### 5.11 `single_region` 构造

#### 5.11.1 `single_region + lcfs`

1. 读取 `GFileData.lcfs_r/lcfs_z`。
2. 检查 shape、长度、有限性和最低点数，处理普通显式闭合末点。
3. 调用 `add_polygon()` 前稳定过滤相邻近重复点：
   - 保留第一点；
   - 按原顺序遍历；
   - 与最后一个已接受点距离严格小于 `1e-4 m` 时删除候选；
   - 否则保留；
   - 不排序、循环移位、插值、重采样、全局去重或改变保留坐标。
4. 过滤后至少 3 点。
5. 若首末距离仍小于 `1e-4 m`，失败。
6. 定义唯一 `plasma` region，尺度为 `plasma_dx`。
7. 调用一次 `add_polygon(lcfs, "plasma")`，无 parent。
8. 不使用第一壁，不创建 vacuum、annulus 或 artificial outer。
9. 通过 `domain.regions` 长度差捕获唯一新增 Region。
10. build 后读取同一 Region 的 `_resampled_points`。
11. 规范化并验证 `outer_boundary`。
12. `vacuum_dx`、`outer_dx`、`outer_padding` 不参与。
13. 不缩放 LCFS，不从最终拓扑反推边界。

#### 5.11.2 `single_region + first_wall`

当前未实现。规划契约：

- 使用有效 `wall_r/wall_z` 作为唯一 polygon；
- 首版尺度为 `plasma_dx`；
- 不创建 LCFS 内部界面、vacuum 或 artificial outer；
- 缺壁、点数不足、非有限、退化或非简单闭环时失败；
- 必须走 Region 捕获、build 后回写和统一验证；
- CLI 当前不得放行。

#### 5.11.3 `single_region + array_file`

正式契约已实现并通过 EAST 生成侧验收：

1. 调用 `read_boundary_file()` 获取经验证和方向规范化的唯一 `(N,2)` 计算边界。
2. v1 不读取 GFile；边界物理语义保持“外部提供的计算边界”。
3. 使用现有单区域尺度 `plasma_dx`，不新增同义尺度字段。
4. 复用统一 single-region OFT Domain 构造，调用一次
   `add_polygon(boundary, "plasma")` 创建唯一 Region。
5. 不创建 LCFS interface、first-wall interface、vacuum annulus 或
   `artificial_outer`。
6. 复用现有 OFT/Triangle 网格生成核心，不复制 Triangle、重采样、点合并或种子逻辑。
7. 必须通过 `domain.regions` 长度差捕获唯一 Region，build 后读取同一对象的
   `_resampled_points`，并执行统一 `outer_boundary` 验证。
8. `Mesh2D.outer_boundary` 表达实际 EAST 计算域外边界；`Mesh2D`、Writer 和
   native helper 不感知边界来源。
9. 不自动推断 X-point 附近目标磁拓扑，不改变用户轮廓，不引入插件、抽象基类体系
   或通用区域配置语言。

#### 5.11.4 `single_region + flux_surface`

状态为 **实现候选 / NOT IMPLEMENTED / 需要 OFT 26.6 只读侦察**，本轮不批准业务
实现。它不是文件格式或第二网格生成器，而是从 GFile 二维极向磁通场提取指定内部闭合
磁通等值线，并作为 single-region 唯一边界，适用于核心或内部等离子体计算域。

该能力不能替代需要包含 X-point 或其附近区域的 EAST 外部边界。实现前必须确认
OFT 26.6 的磁通场数据、归一化磁通定义、轮廓提取接口、多轮廓选择规则、闭合和方向
约定及失败行为。禁止径向缩放、中心缩放或任意几何插值伪造内部磁面。

#### 5.11.5 Plotter 的 array-file 最小调整

1. 基础 `plot_mesh()` 以 `Mesh2D` 及其实际计算边界作为必需数据。
2. `GFileData` 改为可选平衡参考；存在时可叠加 LCFS、limiter/第一壁和磁轴。
3. 无 GFile 的 `array_file` 路径必须仍能绘制实际计算边界和三角网格。
4. 不得为兼容 Plotter 把外部边界伪装成 LCFS。
5. 坐标轴继续明确为 R、Z，单位 m。
6. PNG 仅用于几何检查，不替代 M3D-C1 或 TRIMEG 消费验收。

### 5.12 输入层实施拆分

| 阶段 | 内容 | 状态 |
|---|---|---|
| 输入层 I | `EffectiveConfig`、TOML、发现、合并、矩阵、required-fields、CLI 参数 | **IMPLEMENTED** |
| 输入层 II | `single_region + lcfs`、近重复规范化、真实验收 | **PASSED** |
| 输入层 III | `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED** |
| 输入层 IV | counted R-Z Boundary Reader 与 `single_region + array_file` | **IMPLEMENTED / PASSED** |
| 输入层 V | 真实 `flux_surface` | **实现候选 / NOT IMPLEMENTED / 待 OFT 26.6 只读侦察** |
| M5 第一条 | M3D-C1 TXT+SMB+PNG CLI | **PASSED；时间推进 PENDING** |

输入层 IV 的 Reader、几何验证、配置放行、CLI 编排、single-region OFT Domain、
无 GFile Plotter 以及 EAST `Mesh2D`、TXT、SMB、PNG 生成侧均已完成。EAST
M3D-C1 加载、初始化和时间推进仍必须分别验收，不得由生成侧结果替代。

后续新增来源仍必须先更新蓝图，再修改最小源码和测试；不得一次实现全部来源或建设
插件体系。

### 5.13 输入与 CLI 验收矩阵

必须覆盖：

- schema 缺失、类型错误和版本错误；
- 未知键、section 和 section 内键；
- 非法枚举、dx、bool；
- `--config`/`--no-config` 互斥和发现规则；
- 默认 < TOML < 显式 CLI；
- TOML 与 CLI 两套路径基准；
- 路径不展开；
- `EffectiveConfig` 冻结且恰为 15 字段；
- 已实现、禁止和未实现组合的异常类型；
- boundary source 和 target required-fields；
- `mesh_only` 不调用 Writer；
- `trimeg` 不调用 SMB Writer；
- single-region LCFS 唯一 polygon、近重复过滤和 Region 回写；
- `array_file` counted R-Z boundary text 契约；
- EAST 无扩展名文件正确读取 `N=104`、恰好 104 点、shape `(104,2)`、第一列 R、
  第二列 Z、单位 m；
- 缺计数头、非法整数 N、行数与 N 不一致、列数不是 2、非数字、NaN/Inf、少于
  3 个互异点、首尾重复、相邻重复、零长度闭合边、零面积、自交、多轮廓及额外数据
  必须严格失败；
- `single_region + array_file` 只生成一个区域和合法 `Mesh2D`，不创建嵌套区域
  interface、vacuum annulus 或 artificial outer；
- EAST `outer_boundary` 必须表达实际计算边界并满足正式顺时针约定，Writer 不感知来源；
- 无 GFile 时仍可生成显示实际边界和三角网格的 R-Z 米制 PNG；
- EAST TXT、rank-0 SMB 和 PNG 生成、PNG 人工检查、M3D-C1 加载、初始化与时间推进
  必须分层记录，时间推进不得由前述结果替代；
- first wall 缺失不得回退；
- M3D-C1 只构造一次 `M3DC1ModelSpec`；
- SMB 基础路径不插 rank；
- helper 定位由 SMB Writer 管理；
- 默认 nested TRIMEG 行为不变；
- PNG 不替代加载、初始化、时间推进、稳定性或物理正确性验收。

---

## 6. TRIMEG HDF5 输出契约

### 6.1 完整 11 数据集

黄金标尺是 `docs/trimeg/loadfemmesh_h5.m` 和两个真实样例。所有数据集位于
`/femmesh/`，磁盘 dtype 全部为 `float64`。

| 路径 | shape | 语义 |
|---|---|---|
| `/femmesh/nvert` | `(1,1)` | 节点数 N |
| `/femmesh/ntria` | `(1,1)` | 三角形数 T |
| `/femmesh/nvert_in` | `(1,1)` | 内部节点数 |
| `/femmesh/nvert_ex` | `(1,1)` | 拓扑外边界节点数 |
| `/femmesh/vert` | `(N,2)` | 每行 `[R,Z]`，不转置 |
| `/femmesh/idxivert` | `(1,nvert_in)` | 内部节点 1-based 升序索引 |
| `/femmesh/idxevert` | `(1,nvert_ex)` | 外边界节点 1-based 升序索引 |
| `/femmesh/tria` | `(T,3)` | `triangles+1`，无第四列，不转置 |
| `/femmesh/nbcRZ` | `(1,1)` | 有序外边界点数 B |
| `/femmesh/Rbc` | `(B,1)` | `outer_boundary[:,0]` |
| `/femmesh/Zbc` | `(B,1)` | `outer_boundary[:,1]` |

任何数据集不得遗漏、改名、合并或转置。

### 6.2 索引、拓扑和边界映射

- `triangles` 内存为 0-based；`tria`、`idxivert`、`idxevert` 文件端为 1-based。
- `region_ids` 不写入 HDF5，也不得偏置。
- `idxevert` 是只被一个三角形使用的无向边所含节点集合。
- 无向边出现超过两次时在打开文件前拒绝。
- 没有拓扑外边界边时拒绝。
- `idxivert = {1..N} \ idxevert`。
- `nvert_in + nvert_ex = nvert`，两集合互斥且覆盖全部节点。
- `Rbc/Zbc` 只能来自有序 `mesh.outer_boundary`。
- 禁止从升序 `idxevert` 反推 `Rbc/Zbc`。
- `nbcRZ` 不要求等于 `nvert_ex`。
- TRIMEG target 缺少 `outer_boundary` 时在打开文件前失败。
- Writer 必须在打开文件前完成所有 shape、有限性、整数、索引、面积、非流形和边界
  验证，并不得修改输入。

### 6.3 真实 CLI 和 MATLAB 验收

| 链路 | 结果 |
|---|---|
| DIII-D `g192185.02440`，nested artificial outer | 972 节点、1872 三角形、3 区域、902 内部、70 外部、70 boundary points；HDF5/PNG 成功 |
| fixed-boundary `gNT_example`，nested artificial outer | 3412 节点、6692 三角形、3 区域、3282 内部、130 外部、130 boundary points；HDF5/PNG 成功 |
| DIII-D `g192185.02440`，single-region LCFS，`plasma_dx=0.08` | 344 节点、631 三角形、1 区域、289 内部、55 外部、55 boundary points；HDF5/PNG 成功 |

三份文件均含完整 11 数据集，保持 `(N,2)`、`(T,3)`、1-based 文件索引、无第四列、
不写 `region_ids`。

MATLAB 标准消费端 A/B 验收为 **PASSED**：

- 原始 `loadfemmesh_h5.m` 成功读取标准样例和 LinkMesh HDF5；
- 标准样例约 981 节点、1847 三角形；
- LinkMesh 样例 344 节点、631 三角形、`nbcRZ=55`；
- 未发现索引、布局或明显跨域连线问题；
- 验证不证明计算边界永久固定为 LCFS。

参考样例确认：

- `Rbc/Zbc` 是有序边界几何；
- `idxevert` 是最终拓扑外边界节点；
- `Rbc/Zbc` 不必包含 Triangle 后插入的边界点；
- `nbcRZ` 可等于或小于 `nvert_ex`；
- 样例不证明固定起点规则。

---

## 7. M3D-C1 TXT、SMB 与 native helper 契约

### 7.1 TXT 与 SMB 配套关系

`build_single_face_model_spec(mesh)` 必须只调用一次。TXT Writer 和 SMB Writer
必须接收同一个 `M3DC1ModelSpec` 对象。

TXT Writer 必须：

- 写完整 5 整数头部；
- 写 geometric vertex ID 和 `x/y/z`；
- 写 edge ID、begin/end vertex ID、curve type；
- 写 loop ID、edge 数及有序 edge tags；
- 写完整 `numFaces>0` face 段；
- 保证 ID 唯一、引用存在、endpoint order 正确和 loop 闭合；
- 不输出两列 CSV，不固定 104 点，不调用 Simmetrix。

### 7.2 目标 SCOREC/PUMI 环境

首要兼容目标：

- PUMI 2.2.9；
- Git commit `f87525cae7597322edfb2ccf1c7d4437402d948`；
- Spack hash `333b2ut`；
- GCC 13.3.0；
- Open MPI 4.1.6；
- Zoltan 3.901；
- `/usr/bin/mpicxx`；
- Release；
- variants：
  `~fortran ~int64 ~ipo ~shared +simmodsuite_version_check ~testing +zoltan`，
  `simmodsuite=none`。

调查实例前缀：

```text
/opt/spack/opt/spack/linux-zen4/pumi-2.2.9-333b2utt2vneffaporuf7kaenhpow7x5
```

该路径只标识外部调查实例，不得硬编码。

CMake 必须使用：

- `find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED ...)`；
- `SCOREC::mds`；
- `SCOREC::apf`；
- `SCOREC::gmi`；
- `SCOREC::pcu`；
- 相容 MPI C++ imported target。

不得使用不存在的 `SCOREC_INCLUDE_DIRS` 或 `SCOREC_LIBRARIES`。

已确认 API：

- `apf::makeEmptyMdsMesh(model, 2, false)`；
- `Mesh2::createVertex(ModelEntity*, Vector3 const&, Vector3 const&)`；
- `Mesh2::createEntity(int type, ModelEntity*, MeshEntity** down)`；
- `acceptChanges()`；
- `verify()`；
- `writeNative()`。

目标版本中传入 `<base>.smb` 时，rank 0 实际文件为 `<base>0.smb`。该规则不自动
外推到其他版本。

### 7.3 Python SMB Writer

公开接口：

```text
write_smb(
    mesh: Mesh2D,
    spec: M3DC1ModelSpec,
    filepath: str | os.PathLike[str],
    *,
    helper_path: str | os.PathLike[str] | None = None,
) -> None
```

职责：

1. 验证类型、shape、dtype、有限性、0-based 索引、退化 triangle、single-region、
   single-face、输出目录和路径冲突。
2. 不修改 `Mesh2D` 或 NumPy 数组。
3. 确定性构造 mesh entity classification。
4. 创建、flush、fsync 并关闭唯一隐藏交换文件。
5. 独立子进程调用 helper，捕获退出码、stdout、stderr。
6. 根据目标版本确认 `<base>0.smb` 是非空普通文件。
7. 成功删除交换文件。
8. Python 校验、子进程、helper 或输出确认失败时保留交换文件，并在异常中报告路径。
9. 不创建 GMI/APF/MDS entity，不读取或修改 SMB 字节。
10. 不硬编码 PUMI 前缀，不实现 loader/validator。

### 7.4 Classification

classification 的唯一责任层是 Python Writer。C++ helper 只执行交换契约，不猜测。

规则：

1. 从 triangles 生成 `(min(node0,node1), max(node0,node1))` 无向边，去重后按字典序。
2. 边出现一次为边界，出现两次为内部，超过两次失败。
3. 外边界必须形成唯一简单环；每个 boundary node degree 为 2，一次遍历覆盖全部边。
4. 每个 geometric vertex 坐标必须与恰好一个 boundary node 逐分量精确相等。
5. 以 directed geometric edge 起点 corner 顺序确定唯一边界方向。
6. corner vertex 分类为 `(dim=0, vertex.tag)`。
7. 相邻 corner 间非 corner boundary vertices 分类为对应
   `(dim=1, edge.tag)`。
8. boundary mesh edges 分类为对应 geometric edge。
9. interior vertices、interior edges、全部 triangles 分类为唯一 face。
10. 不从 `region_ids` 推导 face tag。
11. 禁止最近距离、容差最近邻、投影或启发式 classification。

无法满足精确映射时必须停止并先更新上游数据契约，不得静默改为容差匹配。

### 7.5 Schema v1 内部交换格式

交换文件名称为 `LinkMesh M4 Exchange`，schema version 为 `1`。编码是单个
little-endian 二进制文件。整数使用明确宽度，字符串使用 UTF-8，浮点使用
IEEE-754 binary64。

字段顺序固定为：

1. 8 字节 magic：ASCII `LM4XCHG` 后跟 NUL。
2. `uint32 schema_version`，值 `1`。
3. `uint32 endian_marker`，值 `0x01020304`。
4. `uint64 N`、`T`、`E`、`GV`、`GE`、`GL`、`GF`。
5. 四个 `int32`：
   `separatrix_loop`、`inner_wall_loop`、`outer_wall_loop`、`vacuum_loop`。
6. 输出 SMB 基础路径：`uint64 byte_length` + 不含 NUL 的 UTF-8 字节。
7. `nodes`：`N×2 float64`，C-order，每行 `[R,Z]`，m。
8. `triangles`：`T×3 uint64`，C-order，Python 0-based。
9. geometric vertices：每条
   `int32 tag + float64 r + float64 z + float64 y`。
10. geometric edges：每条
    `int32 tag + int32 begin_vertex_tag + int32 end_vertex_tag +
    int32 curve_type`。
11. geometric loops：每条
    `int32 tag + uint64 edge_count + edge_count×int32 edge_tag`。
12. geometric faces：每条
    `int32 tag + uint64 loop_count + loop_count×int32 loop_tag`。
13. mesh vertex classification：N 条
    `int32 geometric_dimension + int32 geometric_tag`。
14. mesh edges：E 条
    `uint64 node0 + uint64 node1 + int32 geometric_dimension +
    int32 geometric_tag`。
15. triangle classification：T 条
    `int32 geometric_dimension + int32 geometric_tag`。
16. 文件在最后记录后立即结束，不允许截断或尾随字节。

Schema v1 限制：

- `GL=1`；
- `GF=1`；
- curve 仅 `LIN=1`；
- triangle 全部分类到唯一 face；
- node/edge 索引 0-based；
- mesh edge 满足 `node0 < node1` 且按端点字典序；
- Python 和 helper 分别验证计数、溢出、引用、tag、dimension、索引和文件长度；
- 不承载 PUMI 指针、SMB 字节、MPI ownership、C1 field、高阶节点、field、
  numbering、partition、residence 或 ghost 信息。

当前实时实现的 helper 调用：

```text
linkmesh-m3dc1-smb-helper --input <exchange-file>
```

已批准但尚未实施的一次性命名迁移完成后，正式调用改为：

```text
linkmesh-scorec-helper --input <exchange-file>
```

成功 stdout：

```text
LINKMESH_M4_OK base=<base-path> rank0=<actual-rank0-path>
```

失败 stderr：

```text
LINKMESH_M4_ERROR stage=<stage> message=<summary>
```

不得依赖任意 PUMI 日志判断成功。

### 7.6 C++ helper 生命周期

helper 必须：

1. 初始化 MPI、PCU、GMI。
2. 严格读取 schema v1。
3. 建立完整 geometric vertices、directed edges、loop、face。
4. 查找并验证 classification entities。
5. 调用 `apf::makeEmptyMdsMesh(model, 2, false)`。
6. 按 node index 创建 classified vertices。
7. 按交换顺序创建 classified edges。
8. 按 triangle index 创建 classified triangles，并规范 orientation。
9. 只设置目标版本必需的串行 residence/ownership。
10. 调用 `acceptChanges()`、`verify()`、`writeNative()`。
11. 记录基础路径和实际 rank-0 路径。
12. 按唯一顺序清理：
    - callback data 在 model 使用期间保持有效；
    - `apf::disownMdsModel(mesh)`；
    - `mesh->destroyNative()`；
    - `apf::destroyMesh(mesh)`；
    - `gmi_destroy(model)` 恰好一次；
    - 释放 PCU；
    - MPI Finalize。
13. 任意失败以非零退出码和结构化错误报告。

禁止依靠进程退出泄漏、重复销毁 model、跳过 `disownMdsModel`、跳过 mesh 销毁或以
异常终止掩盖生命周期错误。

### 7.7 helper 当前定位与正式命名迁移

当前实时实现使用：

- 源码目录：`native/m3dc1_smb_helper/`；
- CMake target 和可执行文件：`linkmesh-m3dc1-smb-helper`；
- 环境变量：`LINKMESH_M3DC1_SMB_HELPER`；
- 定位顺序：
  `helper_path` → `LINKMESH_M3DC1_SMB_HELPER` →
  `PATH` 中的 `linkmesh-m3dc1-smb-helper` → 明确失败。

当前服务器开发构建产物为：

```text
/home/lxzeng/LinkMesh_runs/m4_2_helper_build/linkmesh-m3dc1-smb-helper
```

已批准但尚未实施的正式名称为：

| 层次 | 目标名称 |
|---|---|
| 文档组件名 | LinkMesh SCOREC helper |
| Git 源码目录 | `native/linkmesh_scorec_helper/` |
| CMake target | `linkmesh-scorec-helper` |
| Linux 可执行文件 | `linkmesh-scorec-helper` |
| 环境变量 | `LINKMESH_SCOREC_HELPER` |
| 推荐开发构建根目录 | `$HOME/LinkMesh_build/linkmesh_scorec_helper/` |
| 个人候选安装位置 | `$CONDA_PREFIX/bin/linkmesh-scorec-helper` |
| 共享安装位置 | `<GROUP_SOFTWARE_ROOT>/linkmesh/releases/<version>/env/bin/linkmesh-scorec-helper` |

源码目录使用下划线；Unix 可执行文件和 CMake target 使用连字符；环境变量使用大写
下划线。名称变宽只说明它连接 LinkMesh Python 与 SCOREC/PUMI native 环境，不扩大
当前 M3D-C1 native SMB 写出职责。

项目处于组内正式交付前阶段，采用一次性强制迁移。迁移完成后唯一定位顺序为：

1. Python API 显式 `helper_path`；
2. `LINKMESH_SCOREC_HELPER`；
3. `PATH` 中的 `linkmesh-scorec-helper`；
4. 全部失败时明确报错并停止。

不保留旧环境变量或旧可执行文件兼容分支，不创建旧名称符号链接，不增加长期兼容
警告。高优先级候选已提供但无效时不得静默回退。Python Writer 不猜测仓库 build、
`LinkMesh_runs`、用户主目录、服务器固定路径或 Python 包同目录 helper。

迁移实施必须同步修改源码目录、CMake target、输出文件名、Writer、测试、README、
示例、部署说明和受控文档。服务器旧构建目录不是 Git 重命名对象；必须从新命名的空
构建目录重新配置，禁止复用旧 `CMakeCache.txt`。本版只批准迁移，不执行迁移。

更换 PUMI、编译器或 MPI ABI 时必须重新执行 probe、生成侧验收和外部消费验收。

### 7.8 LinkMesh SCOREC helper 职责边界

helper 是 LinkMesh 自有 native Adapter，连接 Python SMB Writer 与服务器
SCOREC/PUMI C++ 环境。它接收 Python Writer 按正式内部交换 schema 产生的数据，
负责 GMI/APF/MDS mesh 构造、classification 应用、PUMI 生命周期管理和 native SMB
写出。

helper 不读取 GFile、EAST 或其他边界文件；不调用 OFT/Triangle；不重新剖分；不决定
计算边界来源；不承担 M3D-C1 消费端职责；当前不是通用 SCOREC 工具，只服务于
LinkMesh 的 M3D-C1 native SMB 写出。LCFS、`array_file`、未来 `first_wall` 或
`flux_surface` 只要在 Writer 前形成相同合法的 `Mesh2D` 和 `M3DC1ModelSpec`，
通常不需要修改 helper。

需要修改 helper 或至少重新构建的触发条件包括：

- Python/C++ 内部交换 schema 变化；
- classification 或 `M3DC1ModelSpec` 拓扑契约变化；
- 多 face、多 loop、孔洞或多区域能力正式获批；
- SCOREC/PUMI API 或版本变化；
- MPI 实现或 ABI 变化；
- 编译器或 C++ ABI 变化；
- 服务器或 CPU 架构变化；
- helper 自身缺陷修复。

普通 Boundary Reader、Plotter 或网格尺度变化不得自动触发 helper 重构。

### 7.9 当前 helper 二进制事实

当前 helper 是 Linux x86-64 动态链接 ELF，包含 `debug_info` 且尚未 strip。这是
开发/验证构建特征，不表示程序错误。当前已观察到系统路径的 `libmpi.so.40` 和
`libstdc++.so.6`；筛选后的 `ldd` 输出未出现 `not found`。

筛选输出未显示 SCOREC/PUMI 动态库，不能据此声称 helper 不依赖 SCOREC/PUMI。
相关库可能静态链接或以其他名称参与链接。发布前必须审计完整 `ldd`、`readelf -d`、
CMake 配置摘要、编译命令和链接命令。把 helper 安装到 Conda `bin` 只解决安装与
定位，不自动解决 MPI、SCOREC/PUMI、系统 C++ 库或 ABI 兼容。

### 7.10 M4 验收边界

- M4-1A TXT/Level 1：**PASSED**；
- M4-1B probe：**COMPLETED / PASSED**；
- M4-2 LinkMesh 生成侧：**IMPLEMENTED / PASSED**；
- 正式 TXT+SMB 外部加载：**PASSED**；
- M3D-C1 初始化：**PASSED**；
- 时间推进、稳定性和物理正确性：**PENDING**。

319 字节 probe、955 bytes synthetic SMB、173 bytes TXT、真实运行文件大小和
SHA-256 只用于运行追踪，不是格式常量或测试期望。LinkMesh 不建设 SMB loader、
validator 或 M3D-C1 消费端。

---

## 8. 真实场景、使用与部署路线

### 8.1 Case 组织与部署

1. 当前不进行需要 `sudo` 的全局安装。
2. 一份 LinkMesh 源码可与 `100`、`200` 等 Case 系列同层。
3. 每个 Case 保存配置、GFile、M3D-C1 输入、TXT、SMB、PNG 和日志。
4. `100`、`200` 可代表源码版本；`101`、`102` 等复用源码并修改输入。
5. 进入 Case 后通过 CLI 指定配置；临时覆盖使用显式 CLI。
6. 网格预处理与正式求解作业分离。
7. 推荐“生成 → PNG 检查 → 提交求解”，不在每次 `sbatch` 中无条件覆盖网格。
8. 登录节点不允许时可提交独立轻量预处理作业。
9. 只改求解参数可复用网格；改 GFile、边界策略或尺度必须重生成。
10. 后续推荐用户级 Conda 安装 Python 包和 helper。
11. PNG 只做几何检查，不替代消费端验收。

### 8.2 EAST 主线

EAST 已确认为无扩展名 counted R-Z boundary text 提供的独立二维计算边界，文件结构、
列顺序、单位和基础几何验证已通过。其物理构造算法及其与 LCFS、第一壁、磁轴和
X-point 的精确关系仍待确认，不阻塞读取最终边界，也不得被擅自补写。

```text
蓝图 counted R-Z 契约确认
  → single_region + array_file 实现
  → OFT/Triangle 细密二维网格
  → Mesh2D + TXT + rank-0 SMB + PNG
  → PNG 几何检查
  → M3D-C1 加载
  → 初始化回归
  → 时间推进主循环
  → 短时运行
  → 中等时长运行
```

`single_region` 描述区域数，不等于 LCFS。不得因为边界可能包含 X-point 推断必须
多区域，不得把 EAST 外部计算边界改写为 LCFS、第一壁或内部磁面。

### 8.3 X-point 附近目标磁拓扑的工程边界

本蓝图只使用“X-point 附近具有特殊或分形特征的磁拓扑结构”描述背景，不定义
“分形面”的严格性质，也不推断形成机制。

LinkMesh 不计算、重建或分析该磁拓扑。输入是一条经物理人员确认、包含目标研究结构
的二维 R-Z 闭合计算边界。计算边界不等同于研究对象，也不必是 LCFS、第一壁或普通
磁通面。

禁止：

- 缩放 LCFS 伪造人工边界；
- 自动推断目标磁拓扑外边界；
- 扩展为磁拓扑分析程序；
- 在缺少数据和算法时自动判断 X-point、LCFS、第一壁和边界包含关系。

### 8.4 EAST 网格与时间推进记录

可比较 `plasma_dx=0.08 m`、`0.05 m`、`0.03 m`，但不是固定标准。每组记录：

- 边界点数、节点数、三角形数；
- 完整配置和 `plasma_dx`；
- TXT、rank-0 SMB、PNG；
- 加载与初始化结果；
- 是否进入时间推进；
- 实际步数；
- 首次错误或停止原因。

短时推进至少检查：

1. 执行若干时间步；
2. 无立即网格、connectivity 或 classification 错误；
3. 无明显 NaN、Inf、段错误或 MPI 异常；
4. 日志区分正常停止、求解器输入、网格和环境问题。

时间推进不报错不等于物理正确或精度充分。

### 8.5 TCV/TRIMEG 路线

调查应比较：

- EQDSK LCFS；
- EQDSK 第一壁；
- 参考 HDF5 `Rbc/Zbc`；
- 参考网格拓扑外边界；
- 磁轴、X-point 和指定研究区域。

真实消费路线：

```text
LinkMesh HDF5
  → 官方 MATLAB Reader
  → TRIMEG 实际读取和运行
```

PNG、截图或 MATLAB 绘图不是 TRIMEG 实际消费通过证据。

### 8.6 OFT/Triangle 真实场景评估顺序

1. 几何：边界贴合、覆盖、孔洞、越界、X-point 包含关系；
2. 网格：节点、三角形、面积、最小角、长宽比、边长分布；
3. 消费端：
   - M3D-C1 加载、初始化、时间推进；
   - TRIMEG MATLAB 读取和实际运行。

在真实场景证明全局 dx 不足前，不开发 refinement、局部加密、磁面对齐或自适应网格。

### 8.7 本地开发、上传与服务器验证分工

正式源码在本地 Windows Git Bash 仓库中维护。本地负责阅读和修改文档、Python、
C++、CMake 与测试源码，使用 Aider 执行 User 授权的修改，审查 `git status`、
`git diff` 和提交记录，并创建经过确认的源码版本或发布归档。

本地不运行任何测试，不运行 OFT/Triangle，不编译 Linux native helper，不运行
SCOREC/PUMI、M3D-C1 或 TRIMEG 消费验证。本地未运行的测试必须记录为
**NOT RUN**，不得由静态阅读或服务器历史结果写成 PASSED。

Linux 服务器负责接收本地上传的已确认源码版本或发布包，创建和维护服务器环境，
编译 helper，运行 Python 自动测试和 OFT/Triangle，生成 `Mesh2D`、HDF5、TXT、
SMB、PNG，并执行 M3D-C1/TRIMEG 真实消费验收和保存命令、日志、环境及产物。

当前服务器源码目录为 `/home/lxzeng/LinkMesh_server`，源码由 User 从本地直接上传，
不是通过服务器 Git 拉取和管理。不得把 `git pull`、服务器 `git status` 或服务器
`git log` 写成当前既有工作流。Linux 服务器原则上不修改正式源码和文档；问题必须
携带直接证据返回本地修复。服务器构建目录、测试缓存、日志和 Case 输出不是正式源码。

正式闭环为：

```text
本地修改与提交
  → 确认源码版本
  → 上传源码版本或发布归档
  → 服务器构建与验证
  → 保存失败或成功证据
  → 如需修复则返回本地修改
  → 再次上传并回归
```

### 8.8 四类环境与当前开发状态

| 环境 | 定位 | 正式规则 |
|---|---|---|
| 本地源码开发环境 | Windows Git Bash 正式仓库 | 维护源码和 Git；测试、Linux 科学计算栈与 native 构建均 NOT RUN |
| Linux 个人开发验证环境 | 当前可变开发环境 | 允许测试依赖、`PYTHONPATH`、开发 helper 和临时环境变量；不向组员承诺稳定 |
| Linux 个人发布候选环境 | User 个人可写目录中的全新环境 | 不克隆当前开发环境作为发布证明；正式安装 LinkMesh 和 helper；不依赖 `PYTHONPATH` 或开发构建目录 |
| 组内共享稳定环境 | 导师批准共享根目录中的版本化 release | 普通用户只读执行；不依赖个人目录；不原地升级；含统一入口、版本清单和验证记录 |

当前个人开发验证环境直接事实：

- Conda 环境 `linkmesh`，路径 `/home/lxzeng/miniconda3/envs/linkmesh`；
- Python `/home/lxzeng/miniconda3/envs/linkmesh/bin/python`，版本 3.12.13；
- `PYTHONPATH=/home/lxzeng/LinkMesh_server/src`；
- LinkMesh 从 `/home/lxzeng/LinkMesh_server/src/linkmesh` 导入，尚未作为正式发布包
  安装到该环境 `site-packages`；
- OpenFUSIONToolkit 26.6 从 Conda 环境 `site-packages` 导入；
- 不得把 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行时 `PYTHONPATH`；
- 当前观察版本包括 NumPy 2.5.1、h5py 3.16.0、matplotlib 3.11.0、
  OpenFUSIONToolkit 26.6、pytest 9.1.1 和 triangle 20250106；
- 当前 helper 通过旧环境变量指向个人开发构建目录。

这些版本只是当前开发环境事实，不自动等于正式发布锁定版本。Python 3.12 和依赖
锁定范围必须由干净发布候选环境验收。当前个人 Conda 环境不得直接定义为组内共享环境。

### 8.9 发布可追溯性

服务器没有现行 Git 工作流，因此每个发布候选和共享 release 至少保存：

1. LinkMesh 发布版本号和对应本地 Git commit；
2. 上传或发布日期、上传者或维护者；
3. 源码归档文件名及 SHA-256，或其他明确源码标识；
4. Python 版本、直接运行依赖和关键版本；
5. OFT 版本及导入来源；
6. helper 源码版本、二进制 SHA-256、构建日期；
7. CMake 和编译器版本；
8. MPI 版本、来源和 ABI 信息；
9. SCOREC/PUMI 版本、来源和链接信息；
10. 验收日期、案例、测试摘要、日志位置；
11. 已通过和仍待确认的验收层级。

SHA-256 只标识某次具体源码归档或二进制构建，不是跨构建恒定黄金值。

### 8.10 源码、构建和安装分层

批准的目标分层为：

```text
Git 源码：
LinkMesh/native/linkmesh_scorec_helper/
  ├── C++ 正式源码
  ├── CMakeLists.txt
  └── README.md

Linux 开发构建：
$HOME/LinkMesh_build/linkmesh_scorec_helper/<toolchain-id>/

个人发布候选：
$CONDA_PREFIX/bin/linkmesh-scorec-helper
$CONDA_PREFIX/.../site-packages/linkmesh

组内共享 release：
<GROUP_SOFTWARE_ROOT>/linkmesh/releases/<version>/env/
```

Git 只保存 C++ 源码、CMake 和维护文档，不提交 helper 二进制、`CMakeCache.txt`、
`CMakeFiles`、Makefile、`cmake_install.cmake` 或构建日志。开发构建树位于仓库外，
可删除并从源码重建，可按 PUMI、MPI 和编译器组合区分 `<toolchain-id>`；Python
Writer 不猜测该路径，不再把长期构建树放在 `LinkMesh_runs`。

个人候选环境必须通过正式 Python 安装把 LinkMesh 放入 `site-packages`，并通过
CMake install 把 helper 放入 `bin`；不得依赖 `PYTHONPATH` 或开发构建目录。共享
release 中 Python LinkMesh 与 helper 属于同一版本组合，不依赖维护者个人目录。

native 构建后续实施要求：

- 保持已验证的 SCOREC/PUMI imported targets 和 MPI 发现方式，除非直接证据要求修改；
- target 更名为 `linkmesh-scorec-helper`；
- 添加或核对 `install(TARGETS ...)`；
- 支持 `cmake --install <build-dir> --prefix <install-prefix>`；
- 从空构建目录可复现配置和编译；
- 检查可执行权限、`file`、完整 `ldd`、`readelf -d`、CMake 配置摘要及编译链接命令；
- 不得出现 `not found`；
- 优先使用目标服务器正式软件栈、CMake RUNPATH/RPATH 或管理员确认环境；
- 不要求普通用户长期维护复杂 `LD_LIBRARY_PATH`；
- 不复制 SCOREC/PUMI 库进 Git，不以 `sudo` 全局安装为当前默认方案。

是否 strip 发布二进制留待后续裁决，但必须保留构建可追溯性和调试策略。

### 8.11 Python 正式安装与 triangle 验证

发布前必须建立可复现的正式 Python 安装方式。个人候选和共享 release 中 LinkMesh
必须安装到 `site-packages`，从源码目录外可以 `import linkmesh`、启动统一 CLI 并
运行批准的真实流程；发布运行不得依赖 `PYTHONPATH`。OFT 必须从发布环境
`site-packages` 导入，不得从 `TOKAMAKER` 参考源码导入。

当前交付侦察尚未确认仓库具备完整正式打包元数据和统一安装入口；若后续实时核对确认
缺少 `pyproject.toml` 或其他必要元数据，应作为独立实现缺口处理。本版不创建打包
文件，精确安装、命令入口和版本元数据另行设计和测试。

triangle 事实边界：

- 当前开发环境安装 triangle 20250106；
- 当前只读证据未发现 LinkMesh 正式源码直接导入 triangle；
- OpenFUSIONToolkit 26.6 包元数据未声明 triangle；
- `TOKAMAKER` 参考源码中的相关 import 是注释线索；
- 这些证据只支持“triangle 可能不是正式运行依赖”的候选判断，不批准删除依赖。

最终裁决必须来自不安装 triangle 的干净候选环境：正式安装 LinkMesh，运行自动测试、
真实 GFile 和 `array_file`、所有批准 profile，生成 HDF5/TXT/SMB/PNG，调用 helper
并完成相应真实消费验证。全部通过后才能修改正式依赖契约。

### 8.12 组内版本化共享发布

目标结构使用占位符，正式根目录仍待导师或服务器管理者确认：

```text
<GROUP_SOFTWARE_ROOT>/
└── linkmesh/
    ├── releases/
    │   ├── <version>/
    │   │   ├── env/
    │   │   ├── source-manifest/
    │   │   ├── validation/
    │   │   └── VERSION
    │   └── ...
    ├── current -> releases/<stable-version>
    ├── bin/
    │   └── linkmesh
    └── modulefiles/
        └── linkmesh
```

不得把 `/share`、`/shared` 或其他候选路径写成当前事实。每个版本使用独立环境前缀；
不得在稳定 release 上原地执行 `conda update`、`pip install` 或替换 helper。新版本
在新 release 中安装和验收，通过后才切换 `current`，旧版本保留用于回退和复现实验。
普通用户只读和执行；维护者创建、验证和发布。`source-manifest` 保存源码与构建来源，
`validation` 保存测试摘要、真实案例、native 软件栈和消费结果。

### 8.13 普通用户入口与权限边界

普通组员原则上不需要自行安装 Conda，不编译 helper，不设置 `PYTHONPATH`，不手工
设置 `LINKMESH_SCOREC_HELPER`，不进入 `/home/lxzeng`，也不需要知道源码或构建目录。
用户只在生成或更新网格时运行 LinkMesh；已确认网格可供后续 M3D-C1 作业重复使用。

统一入口优先级：

1. 第一阶段共享包装命令；
2. 条件允许时 `module load linkmesh`；
3. 最低可用回退为共享 release 中的绝对命令路径。

首版包装入口负责定位 `current`、准备 release `PATH`，必要时设置
`LINKMESH_SCOREC_HELPER`，仅在直接证据要求时准备动态库环境，调用 release 中的
LinkMesh，原样传递参数并保留退出状态。不得硬编码 `/home/lxzeng`、修改用户 Case、
隐藏失败退出码，或在完整审计前凭经验加入复杂 `LD_LIBRARY_PATH`。modulefile 是
条件性长期入口，其支持、位置和维护权限仍待确认。本版不创建包装脚本或 modulefile。

当前权限直接事实：

- User 属于 `lxzeng`、`users` 和 `m3dc1`；
- `/home/lxzeng` 权限约为 `750`，父目录权限使个人主目录不能作为可靠共享软件位置；
- 当前 shell 显示 `No modules loaded`，不能据此证明 module 系统不存在。

以下事项保持 PENDING：共享软件根目录、User 发布维护写权限、普通组员是否统一属于
`m3dc1`、该组是否承担 release 读执行权限、共享目录是否允许执行 ELF、modulefile
支持、正式 MPI 来源、SCOREC/PUMI 正式位置和版本、系统库与 ABI 管理、备份、配额及
清理策略。

### 8.14 发布阶段顺序

后续交付工作必须作为独立阶段实施，不得因当前个人环境可运行而跳过候选环境：

1. 文档与蓝图更新；
2. helper 全量命名迁移；
3. Python 正式打包和安装能力；
4. native CMake install 与构建目录整理；
5. 个人干净发布候选环境；
6. triangle 非依赖候选验证；
7. helper 完整二进制和动态库审计；
8. 发布候选端到端测试；
9. 导师确认共享根目录、组权限和 module 能力；
10. 创建第一个版本化共享 release；
11. 创建共享包装入口；
12. 条件允许时创建 modulefile；
13. 使用普通用户或等价权限验收；
14. 发布、切换 `current` 并保留回退版本。

---

## 9. 里程碑、测试与验收

### 9.1 M1–M3 和 TRIMEG

- M1 Reader：**PASSED**；
- M2 nested 默认链：**PASSED**；
- M3 core：**PASSED**；
- M3 complete-11：**PASSED**；
- TRIMEG 11 数据集写出：**PASSED**；
- MATLAB 标准消费 A/B：**PASSED**。

### 9.2 M4

- M4-0 只读侦察：完成；
- M4-1A ModelSpec + TXT：**PASSED**；
- M4-1B API/CMake probe：**PASSED**；
- M4-2 Python Writer/helper 生成侧：**PASSED**；
- Python SMB Writer 专项：17 passed；
- M4 相邻回归：170 passed；
- helper 目标环境构建、`verify()`、`writeNative()` 和生命周期：通过。

### 9.3 M5 和 M3D-C1 分层验收

真实 DIII-D 最小闭环：

- LCFS 原始 81 点；
- 第一壁 88 点；
- `outer_boundary` 55 点；
- 344 节点；
- 631 三角形；
- 1 区域；
- TXT 2275 bytes；
- rank-0 SMB 44823 bytes；
- PNG 235388 bytes。

计数和大小不是格式常量。

分层状态：

| 层级 | 状态 |
|---|---|
| LinkMesh CLI 生成 TXT+SMB+PNG | **PASSED** |
| PNG 人工检查 | **PASSED** |
| TXT+SMB 加载 | **PASSED** |
| M3D-C1 初始化 | **PASSED** |
| 时间推进主循环 | **PENDING** |
| 中等或长时稳定性 | **PENDING** |
| 物理结果正确性 | **PENDING** |

### 9.4 输入层

- 输入层 I：**IMPLEMENTED**；
- 输入层 II：**PASSED**；
- first wall：**PLANNED / NOT IMPLEMENTED**；
- EAST 文件结构、R-Z 列顺序、单位与基础几何调查：**PASSED**；
- array file counted R-Z Reader、配置、CLI、OFT 与生成侧：**IMPLEMENTED / PASSED**；
- EAST 生成侧结果：104 个输入边界点、185 个节点、329 个三角形、1 个区域；
- EAST PNG 人工几何检查：**PASSED**；
- EAST TXT+SMB+PNG 生成：**PASSED**；
- EAST M3D-C1 加载、初始化和时间推进：**PENDING**；
- flux surface：**实现候选 / NOT IMPLEMENTED / 待 OFT 26.6 只读侦察**。

新增来源以少量关键单元测试和真实 OFT/GFile/CLI/PNG/HDF5 验收为主，不扩建大型
Fake OFT。

### 9.5 自动测试事实边界

已记录的配置与 CLI 专项结果是 **145 passed、2 failed**，不得表述为全套通过：

1. 一项旧测试期待 `ConfigError`，实际未实现组合正确抛出
   `NotImplementedError`；
2. 一项旧测试错误期待默认 TRIMEG 调用 SMB Writer，当前正式分派规定 TRIMEG
   只调用 HDF5 Writer。

另有相邻回归命令引用不存在的 Plotter 测试路径，因此未执行。上述测试债务不否定真实
CLI 闭环，也不证明未运行测试通过。

### 9.6 EAST 和 TCV

- EAST 文件结构调查：**PASSED**；
- EAST R-Z 列顺序、单位和基础几何验证：**PASSED**；
- EAST 边界物理构造算法及其与 LCFS、第一壁、磁轴、X-point 的精确关系：
  **PENDING**；
- `single_region + array_file`：**IMPLEMENTED / PASSED**；
- EAST Mesh2D 与 TXT+SMB+PNG 生成侧：**PASSED**；
- EAST PNG 人工几何检查：**PASSED**；
- EAST M3D-C1 加载和初始化回归：**PENDING**；
- EAST M3D-C1 时间推进：**PENDING**；
- TCV 边界调查：**PENDING**；
- TCV/TRIMEG 实际消费：**PENDING**。

任何状态更新必须有对应直接证据，不得由 PNG、生成、加载或初始化向后续层级外推。

### 9.7 组内发布与部署验收

以下验收当前均为 **PENDING / NOT RUN**，不得写成 PASSED。

**Python 安装**

- LinkMesh 安装到 release `site-packages`；
- 不设置 `PYTHONPATH` 也可导入；
- 从源码目录外可启动；
- OFT 从 release `site-packages` 导入；
- 不使用 `TOKAMAKER` 源码路径。

**CLI**

- 统一入口可运行；
- 参数原样传递；
- 错误退出码保留；
- 普通用户不依赖个人目录。

**helper**

- 正式名称为 `linkmesh-scorec-helper`；
- 安装到 release `env/bin`；
- Writer 按正式定位规则找到；
- 可执行权限和 `file` 正确；
- 完整 `ldd` 无 `not found`；
- MPI、PUMI、编译器及链接信息已记录；
- 能生成真实 SMB；
- 普通用户无需编译或设置环境变量。

**多用户权限**

- `m3dc1` 普通成员或等价测试用户可进入共享目录；
- 可执行 LinkMesh 和 helper，读取 Python 包及所需库；
- 不能修改稳定 release；
- 维护者可创建新 release；
- `current` 可切换和回退。

**真实消费**

- 通过正式共享入口运行真实案例；
- 输出可被目标 M3D-C1/SCOREC/PUMI 软件栈加载；
- 不依赖开发者个人目录、`PYTHONPATH` 或开发 helper；
- 验收记录保存到 release `validation`。

**并发与稳定性**

- 多个普通用户可只读并发调用发布环境；
- 并发验证不修改共享 release；
- 每个用户把 Case 输出写入自己的可写工作目录。

---

## 10. 变更纪律、停止条件与待决事项

### 10.1 蓝图先行纪律

以下变化必须先修改本蓝图并经 User 确认：

- 新字段、CLI 参数、TOML key 或用户格式；
- 新 target/profile/boundary-source 组合；
- helper 名称、定位、构建、安装或兼容策略变化；
- Python 打包、共享 release、包装入口或 modulefile 契约变化；
- shape、dtype、索引、单位或 Writer 契约变化；
- OFT 版本或私有接口变化；
- PUMI 版本、API、编译器或 MPI ABI 变化；
- 多区域、多 face、三维、自适应或并行能力；
- 验收标准或阶段状态变化。

不得先修改业务代码再补蓝图。

### 10.2 PUMI/API 停止条件

遇到任一情况必须停止：

- `Mesh2D` 与 `M3DC1ModelSpec` 无法无歧义映射；
- classification 依赖最近距离、容差吸附或投影猜测；
- 必须修改核心字段才能继续；
- 需要新增用户格式或 CLI，但蓝图未定义；
- 官方 API 与已确认契约冲突；
- 只能手写 SMB 字节；
- 必须引入多 face、多区域、Simmetrix、三维或并行分区；
- 交换格式无法严格验证；
- 无法链接锁定 imported targets；
- helper、编译器、PUMI 或 MPI ABI 无法确认相容；
- 无法明确 mesh/model/PCU/MPI 所有权和释放顺序。

### 10.3 输入层停止条件

遇到任一情况必须停止：

- `array_file` 需要改变 counted R-Z 计数头、空白分隔双列 R/Z、单位 m、严格 N 行、
  隐式闭合或简单闭环契约；
- 需要多轮廓、孔洞、种子或任意 N 区域语言；
- 必须修改 `Mesh2D` 表示首版边界；
- GFile 与 array boundary 语义无法无歧义拒绝；
- 必须复制 OFT 重采样、点合并、segment、种子或 Triangle 算法；
- 无法可靠捕获唯一 outer Region；
- 必须从最终拓扑或最近距离猜测有序边界；
- 必须放宽 `outer_boundary` 简单闭环契约；
- 新来源缺少真实输入、物理语义或验收证据。

### 10.4 P0 禁止事项

- 第二网格引擎；
- 三维网格；
- 多 face；
- 多区域 M3D-C1；
- 自适应网格；
- 局部加密；
- 磁面对齐；
- 环向或并行分区；
- `split_smb` 或 `part*.smb`；
- loader 或 validator；
- 手写、解析、修改、拼接或模板化 SMB；
- Simmetrix、`make_model`、`.smd`、`.sms` 正式依赖；
- 自动人工边界构造；
- 通用插件、注册表或区域 DSL；
- 修改 M3D-C1、TokaMaker 或 SCOREC/PUMI 只读参考源码。

### 10.5 当前待决事项

1. EAST 边界的具体物理构造算法，以及它与 LCFS、第一壁、磁轴和 X-point 的精确关系；
2. EAST 网格尺度、M3D-C1 加载、初始化和时间推进需求；
3. `single_region + first_wall` 是否由真实需求启动；
4. TCV 参考边界与真实 TRIMEG 消费结果；
5. M3D-C1 时间推进、稳定性和物理正确性；
6. 真实场景是否证明全局 dx 不足；
7. helper 实际重命名、Writer 新定位协议和 native CMake install；
8. Python 正式打包、命令入口和版本元数据；
9. Python 3.12 及正式依赖锁定范围；
10. 不安装 triangle 的发布候选端到端验证；
11. helper 完整动态库、链接和 ABI 审计；
12. 个人发布候选环境与第一个共享 release；
13. 正式共享根目录、权限、modulefile 和管理员接口；
14. 包装入口、普通用户并发和回退验收。

待决事项不得写成已确认事实或自动转化为技术规划。

### 10.6 文档完整性纪律

- 本文档保持第 1 至第 10 节连续结构。
- 不恢复截断事故前的历史旧章节。
- 不通过重复章节保存过期状态。
- 字段表、格式表、算法步骤、停止条件和验收矩阵应作为完整语义块维护。
- 完全等价重复只保留一处；包含额外约束的内容必须保留其额外约束。
- 内部引用必须指向当前章节，不得引用旧第 6A 节。
- `History.md` 保存完成阶段的详细过程和证据；本文只保存当前权威契约与必要证据边界。
- `examples/m3dc1_single_region/linkmesh.in.example` 的存在不产生新契约。
- 状态更新必须有直接证据，并保持加载、初始化、时间推进、稳定性和物理正确性分层。
- 多 face、三维、自适应网格和并行分区继续未开放。

当前准确结论：M1–M3 和既有 TRIMEG 消费验收已通过；nested-three-region 已完成
真实 DIII-D 与 fixed-boundary 的 LinkMesh 生成侧验收；M4 LinkMesh 生成侧已通过；
M5 第一条 `m3dc1 + single_region + lcfs` 真实 CLI、PNG、TXT+SMB 加载和
M3D-C1 初始化已通过。EAST counted R-Z 文件结构、Reader、`single_region +
array_file`、OFT/Triangle、Mesh2D、TXT+SMB+PNG 生成侧和 PNG 人工几何检查已通过；
本次结果为 104 个输入边界点、185 个节点、329 个三角形和 1 个区域。EAST
M3D-C1 加载、初始化回归和时间推进仍为 PENDING；其物理构造算法及其与 LCFS、
第一壁、磁轴和 X-point 的精确关系仍为 PENDING。

当前实时实现仍使用 `native/m3dc1_smb_helper/`、`linkmesh-m3dc1-smb-helper` 和
`LINKMESH_M3DC1_SMB_HELPER`。新名称、Python 正式安装、CMake install、个人发布
候选、triangle 非依赖验证、完整二进制审计、共享根目录、包装入口、modulefile、
第一个共享 release 和普通用户验收均为已批准目标或 PENDING，不得写成已实施。
本版文档更新未运行任何本地测试，状态为 **NOT RUN**。

既有 M3D-C1 时间推进主循环、中等或长时稳定性及物理结果正确性仍为 PENDING；
TCV/TRIMEG 是并行的第二条真实消费路线。`single_region + first_wall` 未实现；
`flux_surface` 保持实现候选、未实现并等待 OFT 26.6 只读侦察；多 face、三维、
自适应网格和并行分区均未开放。
