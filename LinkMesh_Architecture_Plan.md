# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **3.4**（本版仅整理章节结构，将既有正式内容归类为连续的第 1 至第 10 节，并统一旧 CLI 重复说明与 `EffectiveConfig`、三层配置合并及 required-fields 权威契约；不新增或改变字段、接口、编号约定、HDF5 契约、SMB 交换契约、CLI 参数、实现状态或验收结论）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`；M4-0 前置侦察逐轮证据见 `report.md`、`m4_0d_report.md`、`m4_0d1_report.md`、`m4_0d2_report.md`；OFT Region 重采样接口冲突只读核对见 `m3_complete11a_report.md`
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
| 输入 | OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；`array_file` 两列 CSV 边界为已批准但未实现契约 | LinkMesh 手写 GFile 解析；复杂 CAD；多维输入；Python ndarray 公共边界 API |
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
| EAST 样例边界调查 | **NEXT** |
| EAST 细密单区域网格生成 | **PENDING** |
| TCV 参考边界调查 | **PENDING** |
| TCV/TRIMEG 实际消费 | **PENDING** |
| `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED；未开放** |
| `single_region + array_file` | **PLANNED / NOT IMPLEMENTED；未开放** |
| `single_region + flux_surface` | **NOT IMPLEMENTED；未开放** |
| 多区域、多 face、三维、自适应网格和并行分区 | **OUT OF P0 / 未开放** |

### 1.6 下一阶段摘要

下一阶段先调查老师提供的 EAST 边界真实类型，再决定：

1. 若为 LCFS，复用 `single_region + lcfs`；
2. 若为 GFile 第一壁，评估 `single_region + first_wall`；
3. 若为独立二维闭合轮廓，先更新蓝图并实施 `single_region + array_file`。

随后生成细密单区域网格，验证 M3D-C1 时间推进。TCV/TRIMEG 是并行的第二条真实
消费验证路线。不得替 User 决定边界类型，不得自动构造人工边界。

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
| `src/linkmesh/readers/boundary_reader.py` | 计划读取两列 CSV 并复用统一边界验证 | 创建 `Mesh2D`；调用 OFT；读取 GFile；使用 pandas；当前未实现 |
| `src/linkmesh/mesh.py` | 定义统一 `Mesh2D`、统计属性和 `outer_boundary` 集中验证 | 依赖后端或目标格式；读取 OFT 私有属性 |
| `src/linkmesh/mesher/oft_adapter.py` | 构造 OFT Domain；调用唯一 Triangle 底座；规范化 OFT 输出；受控读取 outer Region 回写边界 | 配置解析；复制 OFT 算法；读取禁止的 OFT 私有结构；写文件 |
| `src/linkmesh/m3dc1_model.py` | 定义 `M3DC1ModelSpec` 并从 `Mesh2D.outer_boundary` 构造 single-face model | PUMI、MPI、Simmetrix 依赖；保存 PUMI 句柄；固定 104 点 |
| `src/linkmesh/writers/hdf5_writer.py` | 按 TRIMEG 11 数据集契约写出 | 修改输入；写 `region_ids`；转置；网格生成 |
| `src/linkmesh/writers/m3dc1_model_writer.py` | 按 M3D-C1 analytic model 契约写 TXT | 复制样例坐标；调用 Simmetrix；独立分配 tags |
| `src/linkmesh/writers/smb_writer.py` | 验证输入；生成 classification 和交换文件；调用 helper；确认 rank-0 SMB | 创建 APF/MDS entity；读写 SMB 字节；硬编码 PUMI 路径 |
| `native/m3dc1_smb_helper/main.cc` | 读取交换文件；管理 MPI/PCU/GMI/APF/MDS；创建 classified mesh；调用官方 `writeNative()` | 网格剖分；配置；TXT Writer；loader/validator；多区域、多 face、三维或分区 |
| `native/m3dc1_smb_helper/CMakeLists.txt` | 构建唯一 helper target | 通用 native/plugin 框架；Python 扩展；运行时编译；硬编码安装前缀 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()` PNG 自检 | 修改数据对象 |

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
- 无有效第一壁：PLASMA + OUTER。

single-region 策略见第 5.10 节。

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
- `src/linkmesh/readers/boundary_reader.py`：计划中的 CSV Reader；
- `src/linkmesh/cli.py`：显式参数收集与业务编排；
- `src/linkmesh/mesher/oft_adapter.py`：边界来源对应的 OFT 策略；
- 不新增 `inputs/`、抽象基类、注册表、插件或任意 N 区域语言。

### 5.2 内建默认值

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

### 5.3 `linkmesh.in` TOML v1

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

### 5.4 CLI 参数与 `UNSET`

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

### 5.5 配置发现和三层合并

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

### 5.6 `array_file` v1 契约

当前状态为 **PLANNED / NOT IMPLEMENTED**。

| 项目 | 契约 |
|---|---|
| 编码 | UTF-8 |
| 列 | 恰好两列 `R,Z` |
| 单位 | m |
| 数值 | 有限 `float64` |
| header | 不允许 |
| 注释 | 不定义 |
| 空行 | 可忽略纯空白行；数据行不得有空字段 |
| 分隔符 | 逗号 |
| shape | `(B,2)` |
| 点数 | 至少 3 |
| 闭合 | 末尾不重复首点；隐式闭合 |
| 方向 | 输入任意；进入 `Mesh2D` 前规范为顺时针并保持起点 |
| 几何 | 单一简单闭环；无重复、退化、自交、端点接触或共线重叠 |

计划中的 `boundary_reader.py`：

1. 读取 CSV 并生成独立 `(B,2) float64`；
2. 报告读取、列数、空字段、非数字、NaN/Inf 和点数错误；
3. 复用 `mesh.py` 的统一边界验证；
4. 不创建 `Mesh2D`，不调用 OFT，不读取 GFile，不用 pandas；
5. 不自动闭合、重采样、平滑、排序、投影或最近距离修补；
6. 不从文件名或坐标范围推断物理语义。

### 5.7 `boundary_source`

| 来源 | 正式来源 | 状态 | 规则 |
|---|---|---|---|
| `lcfs` | `GFileData.lcfs_r/lcfs_z` | 已实现 | single-region 唯一边界；不使用第一壁或人工外框 |
| `first_wall` | `GFileData.wall_r/wall_z` | 未实现 | 需要有效第一壁；首版 single-region |
| `array_file` | 两列 CSV | 未实现 | 首版 single-region；与 GFile 互斥 |
| `artificial_outer` | LCFS/第一壁包围盒加固定 padding | 已实现 | 当前只配 nested；四角不直接作为 `outer_boundary` |
| `flux_surface` | 真实平衡磁通面 | 未实现 | 禁止缩放 LCFS 伪造 |

共同规则：

- 每次任务只有一个计算域外边界来源。
- `lcfs`、`first_wall`、`artificial_outer` 需要 GFile。
- `array_file` 需要 array file，并禁止 GFile。
- 未实现来源不得回退。
- 已实现来源必须走 Region 捕获、build 后回写和统一验证。

### 5.8 兼容矩阵

| target | profile | boundary_source | 状态 |
|---|---|---|---|
| `mesh_only` | `nested_three_region` | `artificial_outer` | 已实现 |
| `trimeg` | `nested_three_region` | `artificial_outer` | 已实现并验收 |
| `mesh_only` | `single_region` | `lcfs` | 已实现 |
| `trimeg` | `single_region` | `lcfs` | 已实现并验收 |
| `m3dc1` | `single_region` | `lcfs` | 已实现；加载和初始化通过 |
| `mesh_only` / `trimeg` | `single_region` | `first_wall` | 规划有效，未实现 |
| `mesh_only` / `trimeg` | `single_region` | `array_file` | 规划有效，未实现 |
| 任意 | `single_region` | `flux_surface` | 未实现 |
| `m3dc1` | `single_region` | `first_wall` / `array_file` / `flux_surface` | 未开放 |
| `m3dc1` | `nested_three_region` | 任意 | 禁止 |
| 任意 | `nested_three_region` | `lcfs` / `first_wall` / `array_file` | 禁止 |
| 任意 | `single_region` | `artificial_outer` | 禁止 |

禁止组合使用 `ConfigError`。架构可表达但未实现的组合使用
`NotImplementedError`。旧测试若期待不同异常类型，应更新测试，不得放行组合。

### 5.9 required-fields

按边界来源：

| 来源 | 必需 | 禁止同时提供 |
|---|---|---|
| `lcfs` | `gfile_path` | `array_file_path` |
| `first_wall` | `gfile_path` | `array_file_path` |
| `artificial_outer` | `gfile_path` | `array_file_path` |
| `array_file` | `array_file_path` | `gfile_path` |
| `flux_surface` | 未定义，阶段闸门报未实现 | 不得猜测 |

按 target：

| target | 必需输出 | 行为 |
|---|---|---|
| `mesh_only` | 无 | 不写 HDF5、TXT、SMB |
| `trimeg` | `hdf5_path` | 未使用 `--no-hdf5` 时写 HDF5 |
| `m3dc1` | `model_path`、`smb_path` | 总写 TXT；未使用 `--no-smb` 时写 SMB |

`--no-smb` 不使 `smb_path` 可选；`--no-hdf5` 不改变有效配置结构。配置层只验证字段
存在和组合，不读取业务内容。

### 5.10 `single_region` 构造

#### 5.10.1 `single_region + lcfs`

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

#### 5.10.2 `single_region + first_wall`

当前未实现。规划契约：

- 使用有效 `wall_r/wall_z` 作为唯一 polygon；
- 首版尺度为 `plasma_dx`；
- 不创建 LCFS 内部界面、vacuum 或 artificial outer；
- 缺壁、点数不足、非有限、退化或非简单闭环时失败；
- 必须走 Region 捕获、build 后回写和统一验证；
- CLI 当前不得放行。

#### 5.10.3 `single_region + array_file`

当前未实现。规划契约：

- 使用经物理人员确认的唯一二维闭合边界；
- 不同时读取 GFile；
- 首版尺度为 `plasma_dx`；
- 使用 `add_polygon()` 创建唯一 Region；
- 必须走 Region 捕获、build 后回写和统一验证；
- 不自动推断 X-point 附近目标磁拓扑边界；
- 实施前必须由真实 EAST/TCV 样例确认文件契约。

#### 5.10.4 `single_region + flux_surface`

当前未实现。必须先确认真实磁通面提取字段、输入参数、轮廓选择和验收依据。禁止径向
缩放、中心缩放或任意几何插值伪造磁通面。

### 5.11 输入层实施拆分

| 阶段 | 内容 | 状态 |
|---|---|---|
| 输入层 I | `EffectiveConfig`、TOML、发现、合并、矩阵、required-fields、CLI 参数 | **IMPLEMENTED** |
| 输入层 II | `single_region + lcfs`、近重复规范化、真实验收 | **PASSED** |
| 输入层 III | `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED** |
| 输入层 IV | `boundary_reader.py` 与 `array_file` | **PLANNED / NOT IMPLEMENTED** |
| 输入层 V | 真实 `flux_surface` | **NOT IMPLEMENTED** |
| M5 第一条 | M3D-C1 TXT+SMB+PNG CLI | **PASSED；时间推进 PENDING** |

每阶段必须先更新蓝图，再修改最小源码和测试。不得一次实现全部来源或建设插件体系。

### 5.12 输入与 CLI 验收矩阵

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
- `array_file` CSV 契约；
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

helper 调用：

```text
linkmesh-m3dc1-smb-helper --input <exchange-file>
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

### 7.7 helper 定位

唯一优先级：

1. `helper_path=...`；
2. `LINKMESH_M3DC1_SMB_HELPER`；
3. `PATH` 中的 `linkmesh-m3dc1-smb-helper`。

首个指定或找到的候选必须为可执行普通文件。显式参数或环境变量无效时不得降级。
不得猜测仓库 build 目录或服务器路径。

更换 PUMI、编译器或 MPI ABI 时必须重新执行 probe、生成侧验收和外部消费验收。

### 7.8 M4 验收边界

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

```text
EAST 边界与输入
  → 调查边界类型和文件契约
  → OFT/Triangle 细密二维网格
  → TXT + SMB + PNG
  → PNG 检查
  → M3D-C1 加载
  → 初始化
  → 时间推进
  → 短时运行
  → 中等时长运行
```

边界类型闸门：

- 若为 LCFS：复用现有 `single_region + lcfs`；
- 若为 GFile 第一壁：逐点确认后评估 `single_region + first_wall`；
- 若为独立闭合轮廓：归入 `single_region + array_file`，先更新蓝图再编码。

不得因“包含 X-point”推断必须多区域。`single_region` 描述区域数，不等于 LCFS。
不得替 User 选择边界来源。

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
- first wall：未实现；
- array file：未实现；
- flux surface：未实现。

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

- EAST 边界调查：**NEXT**；
- EAST 细密网格：**PENDING**；
- M3D-C1 EAST 时间推进：**PENDING**；
- TCV 边界调查：**PENDING**；
- TCV/TRIMEG 实际消费：**PENDING**。

任何状态更新必须有对应直接证据，不得由 PNG、加载或初始化向后续层级外推。

---

## 10. 变更纪律、停止条件与待决事项

### 10.1 蓝图先行纪律

以下变化必须先修改本蓝图并经 User 确认：

- 新字段、CLI 参数、TOML key 或用户格式；
- 新 target/profile/boundary-source 组合；
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

- `array_file` 需要改变两列 R/Z、单位 m、隐式闭合或简单闭环契约；
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

1. EAST 边界究竟是 LCFS、第一壁还是独立闭合轮廓；
2. EAST 网格尺度与时间推进需求；
3. `single_region + first_wall` 是否由真实需求启动；
4. `single_region + array_file` 是否由 EAST/TCV 证据启动；
5. TCV 参考边界与真实 TRIMEG 消费结果；
6. M3D-C1 时间推进、稳定性和物理正确性；
7. 真实场景是否证明全局 dx 不足。

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

当前准确结论：M1–M3 和既有 TRIMEG 消费验收已通过；M4 LinkMesh 生成侧已通过；
M5 第一条 `m3dc1 + single_region + lcfs` 真实 CLI、PNG、TXT+SMB 加载和
M3D-C1 初始化已通过；时间推进主循环、中等或长时稳定性及物理结果正确性仍为
PENDING。下一阶段先调查 EAST 边界真实类型；TCV/TRIMEG 是并行的第二条真实消费
路线。`single_region + first_wall`、`single_region + array_file` 和
`flux_surface` 均未实现；多 face、三维、自适应网格和并行分区均未开放。
