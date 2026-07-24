# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **2.5**（归档 M1–M3 最新真实 CLI、TRIMEG HDF5 与 MATLAB 标准消费端验收：`nested_three_region + artificial_outer` 的 DIII-D/gNT 两条真实链路及 `single_region + lcfs` 的 DIII-D 真实链路均退出码 0，三份 HDF5 均包含完整 11 个 `/femmesh` 数据集；老师原始 `loadfemmesh_h5.m` 已完成标准样例与 LinkMesh LCFS 单区域输出的 A/B 读取和绘图验收，确认两者在“单一闭合计算域内部网格化”的拓扑形态上相容。`single_region + lcfs` 状态更新为真实 CLI 与 TRIMEG MATLAB 消费验收 PASSED；`single_region + first_wall`、`array_file`、`flux_surface` 保留正式规划但后置，不再阻塞 M4。两层输入架构保持不变，本阶段暂不创建面向用户的标准 `linkmesh.in` 示例，待 TRIMEG 与未来 M3DC1 TXT+SMB 均通过真实消费端验收后再形成双下游示例。项目主线获 User 授权切换至 M4 业务实现；M4 仍为 NOT IMPLEMENTED / NOT PASSED，既有目标版本 API、classification、单进程与 Level 1–3 验收门槛以及禁止手写 SMB 规则全部保持）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`；M4-0 前置侦察逐轮证据见 `report.md`、`m4_0d_report.md`、`m4_0d1_report.md`、`m4_0d2_report.md`；OFT Region 重采样接口冲突只读核对见 `m3_complete11a_report.md`（阶段证据，非本蓝图正文的长期正式依赖，蓝图正文自包含）
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION / NOT IMPLEMENTED】为已批准正式契约但尚未实现的功能；【P0 禁止】为当前阶段严格禁止引入的功能；【实现候选】为已有源码调用点线索但须目标版本与最小运行验证确认、不得写成固定接口的路线；【版本锁定兼容接口】为 User 已批准、绑定特定 OFT 版本、范围受控、失败即停止的私有依赖，不是通用稳定公共 API
- 修改前置条件：任何对本文档接口、字段、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位与范围

LinkMesh 是一个**独立命令行程序（CLI）**，用于打通「等离子体平衡文件 GFile/EQDSK → 二维非结构三角网格 → 目标求解器静态网格文件」的转换链路。

**唯一网格生成底座**：OFT/TokaMaker 封装方式调用的 Triangle（OFT 内部经 `liboft_triangle` 完成）。LinkMesh 不维护第二种网格引擎。

**SCOREC/PUMI 架构位置（M4 相关，非第二剖分引擎）**：M4 引入的 SCOREC/PUMI 技术栈**不是第二个三角剖分引擎**。其中 GMI 负责 geometric model 接口、APF 负责网格与 field 抽象、MDS 负责底层 mesh 表示、PCU 负责并行通信支持，PUMI 是 M3D-C1 使用的接口/封装层。M4 中 LinkMesh 的作用是把 `Mesh2D` 与 `M3DC1ModelSpec` 转换为 classified APF/MDS 网格，并调用官方 API 输出 `.smb`；Triangle 仍是唯一剖分底座。

**正式数据流**：

```text
GFile/EQDSK → Reader → OFT Adapter → Mesh2D → TRIMEG HDF5 / M3DC1 TXT model + PUMI SMB → PNG
```

**当前阶段状态（v2.5）**：

| 阶段 | 状态 |
|---|---|
| M1 Reader | **PASSED** |
| M2 默认 `nested_three_region + artificial_outer` | **PASSED** |
| M2 `single_region + lcfs` 真实 CLI | **PASSED** |
| M3 core | **PASSED** |
| M3 complete-11 | **PASSED** |
| TRIMEG 标准 MATLAB 消费端 A/B 验收 | **PASSED** |
| M4-0 只读侦察与架构契约 | **已完成** |
| M4 业务实现 | **获 User 授权开始；NOT IMPLEMENTED / NOT PASSED** |

项目当前主线正式切换到 M4 业务实现。M4 P0 使用已经验收的
`single_region + lcfs` `Mesh2D` 作为第一份真实输入，限定 single-region +
single-face；该阶段切换只表示允许开始实现，不表示 TXT model、SMB、PUMI 加载或
M3D-C1 验收已经通过。

**P0 范围**：

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；`array_file` 两列 CSV 边界（PLANNED） | 在 LinkMesh 侧手写 GFile 文本解析；复杂 CAD；多维输入；Python ndarray 公共边界 API |
| 网格生成 | 调用 OFT `gs_Domain` / `build_mesh()` | 引入第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；修改/维护 OFT 分支 |
| 并行切分 | 不涉及 | 生成 `**1.smb`~`**16.smb` 并行分区 |
| 输出 | TRIMEG HDF5；M3DC1 配套 TXT model file + PUMI .smb（M4，经 PUMI/APF/MDS 官方 API） | 三维输出；手写、拼接、修改或逆向 `.smb` 二进制字节流 |
| 可视化 | matplotlib 自检 PNG | 交互式/三维渲染 |
| 配置 | 当前 CLI 参数；两层输入架构（`linkmesh.in` + CLI，见第 6A 节，PLANNED） | 通用配置 DSL / 任意 N 区域语言 / 插件系统 |

---

## 2. 当前架构与模块职责

允许依赖方向：`cli → config / readers / mesher / writers / utils`；`mesher.oft_adapter → mesh`；`writers → mesh`；`utils.plotter → mesh`；`config` 不依赖 Reader/Mesher/Writer/Plotter；`readers.boundary_reader → mesh`（仅复用统一边界验证）。`mesh.py` 不依赖任何后端、Writer、CLI、Plotter 或 config。

| 模块 | 职责（一段式） | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 任何业务逻辑或参数解析 |
| `src/linkmesh/cli.py` | 解析/验证用户显式 CLI 参数（含三个区域 `dx` 与规划中的 `--config/--no-config/--target/--profile/--boundary-source/--array-file`），拦截历史 `--min-angle/--max-area`，调用配置合并（见 `config.py`）得到 `EffectiveConfig`，按顺序编排 Reader → `generate_mesh()` → Writer → Plotter | 实现区域/几何/种子/Triangle 算法或任何 dx 换算；自行合并三套默认值/文件/CLI（合并交给 `config.py`）；恢复已删除历史边界构造代码；解析 TOML |
| `src/linkmesh/config.py`（PLANNED，未实现） | 定义只读/不可变 `EffectiveConfig`；用标准库 `tomllib` 读取并严格校验 `linkmesh.in`；合并「内建默认值 < 配置文件 < 用户显式 CLI」；按配置目录/当前工作目录两套基准解析路径；校验 `target/profile/boundary_source` 兼容矩阵与 required fields；输出已完成路径解析与类型验证的 `EffectiveConfig` | 读取 GFile；读取 array boundary 数据；构造 OFT Domain；调用 Mesher/Writer/Plotter；建设通用配置 DSL、插件系统或任意 N 区域语言；保存值来源字典/ndarray/句柄/argparse Namespace |
| `src/linkmesh/mesh.py` | 定义 `Mesh2D`（唯一正式统一网格对象）与只读统计属性；对 `outer_boundary`（若提供）执行集中式验证（含完整非相邻边自交检查，见第 3.2 节） | 依赖 OFT/Triangle/HDF5/PUMI/CLI/Plotter/config；共享可变默认数组；读取任何 OFT 私有属性 |
| `src/linkmesh/readers/gfile_reader.py` | 薄 Adapter：调用 OFT `GEQDSKEquilibrium`，提取字段封装为 `GFileData`；仅允许 LCFS 闭合/方向后处理 | 手写文本解析；调用 Triangle；写文件 |
| `src/linkmesh/readers/boundary_reader.py`（PLANNED，未实现） | 轻量边界输入：读取 `array_file`（两列 CSV），输出 `(B,2) float64` 边界点列，执行文件语法/shape/有限性/基础点列检查，完整简单闭环几何验证委托 `mesh.py` 统一边界验证入口 | 创建 `Mesh2D`；调用 OFT；读取 GFile；引入 pandas |
| `src/linkmesh/mesher/oft_adapter.py` | 三层接口：`mesh_from_oft_domain(domain)` 通用 N 区域核心（含 N=1）、`build_oft_domain_from_gfile(gfile_data, plasma_dx, vacuum_dx, outer_dx, ...)` 默认策略层、`generate_mesh(...)` 便利入口；single-region polygon 来源在进入 `add_polygon()` 前按第 6A.11 节执行稳定相邻近重复点规范化；将 `pts/lc/reg` 规范化为 `Mesh2D`；在锁定的 OFT 26.6 环境中，由策略层受控捕获 outer Region 引用并于 `build_mesh()` 后读取 `outer_region._resampled_points` 得到 `outer_boundary`（版本锁定兼容接口，见第 3.2A 节）。所有 OFT 私有属性依赖集中封装于本模块内 | 解析 TOML；复制 OFT 通用几何/种子/重采样/segment 拼接/方向/全局重编号/Triangle 算法；写死区域数量/名称/类型/ID；无依据再次偏置 0-based 连接表；解析 `_reg_seg_map`/`_resampled_segments`/`Mesh._resampled_points`；调用 `Region.get_resampled_points()` 作为 `outer_boundary` 来源；回退四角/`idxevert`/最终 `pts/lc` 反推/自行重采样；把 OFT 私有依赖泄漏到 `Mesh2D`/Writer/CLI/Plotter；修改 OFT 源码或依赖 `TOKAMAKER/` 快照；把 OFT `merge_thresh` 暴露为 P0 公共配置 |
| `src/linkmesh/writers/hdf5_writer.py` | 接收 `Mesh2D`，按 TRIMEG HDF5 契约写出（见第 5 节） | 修改 `Mesh2D`；写 `region_ids`；转置 `vert/tria`；给 `tria` 加第四列；从 `idxevert` 反推 `Rbc/Zbc`；网格生成逻辑；判断配置来源 |
| `src/linkmesh/writers/smb_writer.py` | M4 占位；侦察与蓝图确认前保持 `NotImplementedError`；未来经 PUMI/APF/MDS 官方 API 输出 | 手写/拼接/修改/逆向 `.smb` 字节流 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()`（支持区域着色、LCFS/第一壁闭合显示） | 修改任何数据对象 |

M4 规划新增模块（PLANNED，本轮不建源码）：M3DC1 目标专用对象 `M3DC1ModelSpec`（第 7 节）、TXT model Writer 与 PUMI/APF/MDS Adapter（第 7 节）。

**M4 当前授权与实施入口（v2.5）**：

1. 先实现或固化 `M3DC1ModelSpec` 与 TXT geometric model Writer。
2. 在目标环境核对 SCOREC/PUMI/APF/MDS 精确版本、头文件、库、构建方式和官方 API。
3. 实现 `Mesh2D + M3DC1ModelSpec` 到 classified APF/MDS mesh 的最小转换。
4. 调用目标版本官方 `writeNative` 或等价官方接口输出 `.smb`。
5. 完成 Level 1 TXT 静态验收、Level 2 SMB 轻量加载与 Level 3 TXT+SMB 配套加载；
   三者全部通过后 M4 方可标记 PASSED。Level 4 完整 M3D-C1 属后续或导师验收。

M4 P0 使用已验收的 `single_region + lcfs` `Mesh2D`，限定 single-region +
single-face，输出必须是配套 TXT geometric model + PUMI `.smb`。Triangle 仍是唯一
网格剖分底座；PUMI/APF/MDS 只承担目标格式构造与输出，不是第二网格生成器。禁止
手写、拼接、修改、模板复制或逆向 `.smb` 字节流；`region_ids` 不自动等同于
M3DC1 geometric face tag；C1 field、高阶节点、运行时 field 与
adaptation/restart metadata 不属于初始静态网格输出要求。

以下事项继续作为实现停止条件：

- 目标版本的 `makeEmptyMdsMesh`、`createVertex`、`createEntity`、
  `acceptChanges`、`verify`、`writeNative` 等精确签名与调用顺序未确认；
- classification 本地判定未确认；
- 单进程 residence、文件命名或 triangle 方向未确认；
- TXT model 与 SMB geometric classification 无法证明相容；
- 目标环境无法使用所需 PUMI/APF/MDS 官方库。

现有调用点只属于【实现候选】，不得写成跨版本固定事实。User 授权开始 M4 不等于
M4 已实现或已通过；当前准确状态仍为 **NOT IMPLEMENTED / NOT PASSED**。

**不得规划**：`inputs/` 插件包；抽象基类；source 注册表；通用 source plugin 系统。

---

## 3. 核心数据契约

### 3.1 `GFileData`（Reader 输出）

坐标单位 m，R 为大半径方向，Z 为垂直方向。字段全部由 OFT `GEQDSKEquilibrium` 属性提取，无手写解析。

| 字段 | 类型/shape | 来源属性 | 说明 |
|---|---|---|---|
| `lcfs_r` / `lcfs_z` | `np.ndarray (N_lcfs,)` | `boundary_R` / `boundary_Z` | LCFS 边界坐标 [m] |
| `rmaxis` / `zmaxis` | `float` | `R_mag` / `Z_mag` | 磁轴坐标 [m] |
| `wall_r` / `wall_z` | `Optional[np.ndarray (N_wall,)]` | `limiter_R` / `limiter_Z` | 第一壁；`None`/空表示输入未提供可用壁轮廓，不代表物理无壁 |
| `rcentr` | `Optional[float]` | `R_center` | 参考大半径 R0 [m] |
| `bcentr` | `Optional[float]` | `B_center` | 参考磁场 B0 [T] |
| `current` | `Optional[float]` | `Ip` | 等离子体电流 [A]，不缩放 |

### 3.2 `Mesh2D`（LinkMesh 统一中间网格对象）

**正式定位（v2.0，v2.1/v2.2/v2.3/v2.4 保持）**：`Mesh2D` 是 LinkMesh 面向多个下游模拟代码（TRIMEG、M3DC1/PUMI 等）的**统一、持久、求解器无关**中间网格对象。

原则：

- 保存下游共同需要、且在网格生成后**无法可靠反推**的规范几何、拓扑、物理标记与必要分类信息；
- 目标格式的索引、转置、dtype、布局转换由各 Writer 完成；不得把 TRIMEG/M3DC1/PUMI 的文件布局搬进 `Mesh2D` 内存布局；
- 可从 `triangles` 无损、确定性派生的边集合与邻接关系，**默认不重复存储**，除非 M4 直接证据证明必须持久保存；
- 不因追求"最完备"而提前加入未经证据确认的 C1 自由度、高阶节点、PUMI 私有句柄、MPI ownership、M3DC1 私有数组或求解器运行时对象；
- `Mesh2D` **不读取任何 OFT 私有属性**；所有 OFT 私有依赖集中在 OFT Adapter，`Mesh2D` 只接收已规范化、已验证的 `outer_boundary` 独立副本。

**核心字段（来自 OFT `build_mesh()`，内部索引 0-based）**：

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | 线性二维节点 `[R,Z]` [m] |
| `triangles` | `(T,3)` | 整数（实测 `int32`） | 三顶点节点索引，**内部 0-based** |
| `region_ids` | `(T,)` | 整数（实测 `int32`） | OFT 最终区域编号，**原样保留**（不重编号/排序/压缩/+1）；LinkMesh 物理区域标签，**不等同于** M3DC1 geometric face tag |

**兼容字段（现存于 `mesh.py`，均安全空数组默认值，不参与 TRIMEG 契约）**：`boundary_segments (0,2) int32`、`boundary_markers (0,) int32`、`node_markers (0,) int32`。这三个字段**与下文 `outer_boundary` 不同义、不同名、语义不同**；不得改名或删除既有字段。

**`outer_boundary` 字段（正式定义，已实现并验收）**

`Mesh2D.outer_boundary` 表示当前 `Mesh2D` 所代表计算域**在进入 Triangle 前**的有序离散外边界。

| 属性 | 规定 |
|---|---|
| 类型 / shape / dtype | `Optional[np.ndarray]` / `(B,2)` / `float64` |
| 列含义 / 单位 | 第 0 列 R，第 1 列 Z / m |
| 语义 | 传入网格生成器的、有序、最外层计算域几何边界点；一条**单一简单闭合轮廓** |
| 闭合 | 末尾**不重复首点**，最后一点与第一点隐式闭合 |
| 方向 | 顺时针（带符号闭合面积严格为负） |
| 约束 | 至少 3 个互异有限点；无相邻重复点；无零长度闭合边；无退化面积；**单一简单闭环，禁止非相邻边自交**；P0 只允许一条最外层闭合轮廓 |
| 所有权 | 数组由 `Mesh2D` **独立持有**（构造期规范化为 float64 独立副本，即使输入已是 float64 ndarray 也不复用其内存、不修改输入），不与外部可变输入或 OFT 私有数组共享所有权 |
| 必选性 | **TRIMEG target 必须提供**；`mesh_only` 与 M3DC1 target 按各自目标契约处理，可为 `None`（不得把 TRIMEG 必填性扩大为所有目标全局必填） |
| 与 Steiner 点 | **不包含** OFT/Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑外边界节点集合；因生成器插点，`B` 可小于最终 `nvert_ex` |
| 性质 | 求解器无关的计算域几何，**不是**按节点编号升序生成的 `idxevert` 坐标表 |

**验证实现状态（已完成）**：`Mesh2D.__post_init__`（经统一验证入口 `_validate_outer_boundary`）对 shape、dtype、有限性、点数、相邻重复点、隐式闭合语义、方向、退化面积**以及完整非相邻边自交检查**（非相邻边严格交叉、端点接触、共线重叠；不误判相邻边、首末相邻边、合法顺时针凹多边形、共线但区间分离边）执行验证，并区分坐标容差（长度量纲）与 orientation 叉积容差（长度平方量纲）。HDF5 Writer 复用同一统一验证入口作为打开文件前的二次防线，不复制自交算法。该完整自交验证已由第一轮 `mesh.py`/`tests/test_mesh.py` 服务器专项测试通过。

`outer_boundary` **不是**：人工矩形四个控制角点；`Region.get_resampled_points()` 的返回值；最终按节点编号排序的 `idxevert`；Triangle 后续插入的全部 boundary Steiner points；由最终 `pts/lc` 反推的点；LinkMesh 自行重采样的点列；永久固定的 LCFS；永久固定的 first wall；永久固定的 artificial outer。

正确数据链：

```text
控制几何 / 边界来源
  → single-region polygon 来源按第 6A.11 节稳定规范化相邻近重复控制点
  → 策略层创建 outer Region 并捕获引用
  → domain.build_mesh()（OFT 内部完成重采样、共享边界处理、点合并、全局重编号、segment 方向处理，并回写 region._resampled_points）
  → 受控读取 outer_region._resampled_points（OFT/Triangle 输入前的真实有序离散点列）
  → 删除可能的普通显式闭合重复末点 + 验证 + 顺时针规范化 + float64 独立副本
  → Mesh2D.outer_boundary
  → TRIMEG Rbc/Zbc
```

对于 `artificial_outer`：人工矩形控制几何 → OFT 按网格尺度重采样 → `region._resampled_points`（Triangle 输入前离散边界）→ `outer_boundary`。**四个矩形控制角点不得直接代替离散边界点列。**

起点规则：当前无足够证据，不规定固定起点（不强制从最小 R/最大 R/最小 Z 起）。只要求点序相邻正确、方向为顺时针、同一输入与配置产生确定顺序。逆时针输入规范化为顺时针时**保持原起点**（输出 `[p0, p_(B-1), …, p1]`，不使用裸 `pts[::-1]`）。

### 3.2A `outer_boundary` 的 OFT 26.6 私有兼容接口（版本锁定兼容接口，User 已批准，已实现并验收）

**背景事实（服务器正式安装版 `openfusiontoolkit==26.6` 只读 introspection 直接证据，见 `History.md` 第 18/19 条与 `m3_complete11a_report.md`）**：

- OFT 26.6 **没有公开方法**直接返回"指定 Region 对应的 Triangle 输入前有序离散边界"。
- `Region.get_resampled_points()` 在 OFT 26.6 中**存在**，但它走**独立**重采样路径，**不是** Triangle 输入 `alpha["vertices"]` 的来源，**禁止**作为 `outer_boundary` 来源。
- OFT 26.6 的 `Mesh.__init__()` 在内部完成实际的边界重采样、共享边界处理、点合并、全局重编号与 segment 方向处理，并把对应 Region 的有序离散点列**回写**到 `region._resampled_points`（`region._resampled_points = numpy.asarray(reg_points)`；组装 `reg_points` 时负 segment 通过反向遍历 `_resampled_segments` 处理方向）。
- `Mesh.get_mesh()` 使用 `alpha = dict(vertices=self._resampled_points, segments=..., regions=...)`，Triangle 经 `run_triangle(alpha)` 接收该输入；即 Triangle 输入 `vertices` 的权威来源是 `Mesh._resampled_points`，与各 Region 回写的 `region._resampled_points` 同源同批（同一 `Mesh.__init__` 重采样过程）。

**OFT 26.6 Region 输入、全局点合并与回写点列语义（v2.4 新增已确认事实）**：

- `Region.__init__()` 对输入首末点执行普通显式闭合检查：仅当首末点距离小于 `dx / 1000` 时删除一个末尾点。
- 对相邻控制点，`Region.__init__()` 在相邻边长度小于 `dx_curve / 1000` 时输出 `Repeated points detected` 警告并跳过该点对应的角点分析，但**不从** `Region._points` 或 `Region._segments` 删除该相邻控制点。
- OFT 26.6 `Mesh.__init__()` 的锁定默认参数为 `merge_thresh=1e-4 m`；`gs_Domain.build_mesh()` 当前默认使用同一值。构造全局点表时，局部点与已有全局点的欧氏距离严格小于 `merge_thresh`，即 `< 1e-4 m`，则映射到同一个全局点。
- `Mesh.__init__()` 先构造经过全局点合并和 segment 重采样的坐标与拓扑表示，再按照每个 Region 的有向 segment 顺序，通过 `_reg_seg_map` 与 `_resampled_segments` 重建 `reg_points`，最后写入 `region._resampled_points`。
- 因此，`Region._resampled_points` 是**按区域 segment 拓扑顺序重建**的有序区域边界点列，坐标来自经过全局点合并与 segment 重采样的坐标表；它不是原始输入控制点的直接副本，不是 Triangle 后续生成的全部边界节点，不是无序的全局唯一点集合，也不是仅按坐标去重后的简单数组。
- 多个局部控制点可能因 `merge_thresh` 映射到同一个全局点，但区域 segment 的有序重建仍可能在 `region._resampled_points` 中多次引用该合并坐标。因此，OFT 全局点合并可能表现为 **Region 回写点列中的重复坐标**。
- 术语必须区分：输入末点重复首点是“显式闭合末点”；两个相邻输入控制点距离小于 OFT `merge_thresh` 是“相邻近重复控制点”；多个局部点映射到同一全局点是“OFT 全局点合并”；区域 segment 重建后同一合并坐标在有序点列中出现多次是“Region 回写重复坐标”；LinkMesh 要求末尾不重复首点、最后一点隐式连接第一点是“隐式闭合”。
- OFT 的 `Repeated points` / `Small feature` 警告不表示 Triangle 失败。真实 DIII-D LCFS 单区域来源中，OFT 与 Triangle 已成功生成 344 个节点、631 个三角形和 1 个区域；失败发生在随后将含重复闭合坐标的回写点列转换为 `Mesh2D.outer_boundary` 时。
- `Region._resampled_points` 仍是 `outer_boundary` 的直接权威来源，但它是 OFT 私有拓扑表示，进入 `Mesh2D` 前必须规范化为 LinkMesh 的独立、顺时针、隐式闭合、单一简单闭环表示。不得通过放宽 `Mesh2D` 契约接纳 OFT 回写重复坐标。

**已实现并验收的受控依赖**：

- LinkMesh 在锁定的 `openfusiontoolkit==26.6` 环境中，在 OFT Adapter 内、由策略层明确捕获 outer `Region` 对象后，于 `domain.build_mesh()` 完成后受控读取该对象的私有属性 **`outer_region._resampled_points`**，作为 `outer_boundary` 的权威离散点列来源。
- 读取后创建 `float64` **独立副本**，按 `Mesh2D.outer_boundary` 契约验证并规范化（删除普通显式闭合重复末点、方向规范为顺时针并保持原起点）。
- 该受控读取链已由第二轮 `oft_adapter.py`/`tests/test_oft_adapter.py` 服务器专项测试通过，并经现有 `nested_three_region + artificial_outer` 两个真实 GFile 回归验证。LCFS 单区域来源暴露出的 OFT 点合并回写重复坐标问题仍处于代码修复和真实集成验收阶段，不得据此前既有验收将该新增路径标记为 PASSED。

**允许读取的 OFT 属性（唯一）**：

- 策略层已明确捕获的 `outer_region._resampled_points`。

**禁止读取或解析的 OFT 属性**：

- `domain.mesh._reg_seg_map`
- `domain.mesh._resampled_segments`
- `domain.mesh._resampled_points`（Mesh 级别聚合点列，禁止 LinkMesh 直接解析）

原因：OFT 已在 `Mesh.__init__` 内完成 Region 点列的方向与拼接并回写到 `region._resampled_points`；LinkMesh 只读取该回写结果，不再解释 OFT 私有 segment 语义、不复制 OFT 重采样/点合并/segment 拼接/方向/全局重编号算法，从而把版本耦合范围压到最小。第 6A.11 节规定的 single-region polygon 相邻近重复控制点预处理发生在调用 `add_polygon()` **之前**，仅用于避免已知输入控制点在 OFT 锁定默认 `merge_thresh` 下塌缩为同一全局点；它不解析上述私有属性，也不替代 build 后的 Region 回写读取。

**接口性质**：该私有依赖是**版本锁定、范围受控、失败即停止**的兼容接口（【版本锁定兼容接口】），**不是**一般稳定公共 API；只服务于获取 `outer_boundary`，不得扩展为 LinkMesh 对 OFT 私有结构的通用依赖。

**捕获与读取时机（固定）**：

1. single-region polygon 来源先按第 6A.11 节规范化相邻近重复控制点；nested 路径保持既有输入行为；
2. 策略层创建 outer Region；
3. 策略层**立即**保存该 Region 对象引用（不写死 region ID、不按名称猜测、不遍历私有 map），并在 `build_mesh()` 前保存到局部变量；
4. `domain.build_mesh()` 创建 OFT `Mesh` 并完成实际重采样、全局点合并及 Region 点列回写；
5. `build_mesh()` **完成后**读取 build 前保存的**同一个** outer Region 对象的 `outer_region._resampled_points`（即使 build 期间 domain 上私有属性被替换，也使用 build 前保存的原对象）；
6. 转换为独立 `float64` 副本；
7. 删除可能存在的一个普通显式闭合重复末点；
8. 验证 shape、有限性、点数、隐式闭合、简单闭环与非相邻边自交；
9. 规范化为顺时针（保持原起点）；
10. 写入 `Mesh2D.outer_boundary`；
11. HDF5 Writer 直接映射为 `nbcRZ/Rbc/Zbc`。

**不得**把读取时机写成 `build_mesh()` 之前——服务器证据已确认权威 Region 点列在 `Mesh.__init__()` 处理后才回写。通用 `mesh_from_oft_domain()` **不得**通过 region ID、名称猜测或遍历私有 map 推断 outer Region；outer Region 的选择与引用捕获属于**策略层**职责。

**防御性失败规则（任一条件必须明确失败）**：

- `openfusiontoolkit` 运行版本不是 26.6；
- outer Region 引用未捕获；
- `outer_region` 缺少 `_resampled_points`；
- 属性值为 `None`；
- shape 不是 `(B,2)`；
- 数据含 NaN 或 Inf；
- 点数不足；
- 显式闭合规范化后点数不足；
- single-region polygon 输入相邻近重复过滤后不足 3 点；
- single-region polygon 输入规范化后仍有相邻重复点或首尾重复点；
- Region 回写规范化后仍有相邻重复点、首尾重复点、自交、面积退化或不足 3 点；
- 轮廓退化；
- 方向或点序无法规范化；
- 非相邻边自交；
- 无法证明该 Region 是策略层创建的最外边界；
- OFT 内部接口与已核对签名或数据流不一致。

失败时**禁止**继续扩大静默修补，也禁止回退到：人工矩形四角；清理后的原始 LCFS 控制点；`Region.get_resampled_points()`；`idxevert`；最终 `pts/lc` 反推；LinkMesh 自行重采样；静默设置 `outer_boundary=None` 后继续 TRIMEG 输出。对不需要 `outer_boundary` 的目标仍按目标契约处理。

**禁止加入 `Mesh2D` 的数据（P0）**：triangle adjacency（由 triangles 派生）、geometric model handles、PUMI handles、geometric model tags、C1 field、edge orientation、boundary normal、boundary curvature、high-order nodes、MPI ownership。可确定性派生的数据默认由 Adapter、PUMI/MDS 或 M3D-C1 运行时生成。

**只读统计属性**：`n_nodes`、`n_triangles`、`n_boundary_segments`。

---

## 4. 网格与物理约定

- **坐标/单位**：`[R,Z]`，SI（m、T、A）。
- **内存索引**：`triangles` 内部 0-based；目标格式偏置（如 TRIMEG +1）由对应 Writer 在写出阶段完成。`region_id` 与节点索引转换无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- **OFT 输出契约**（已确认）：`pts (np,2) float64`、`lc (nc,3)` 0-based 整数（`0<=lc<N`）、`reg (nc,)` 正整数，与 `domain.region_info` 最终 ID 一一对应。
- **区域编号**：原样保留 OFT `reg`；区域语义只从 `domain.region_info` 名称/类型/最终 ID 获得，不由整数值推断；区域数量由 OFT 当前区域模型决定，不写死；合法单区域（N=1）满足契约。
- **区域校验**（`mesh_from_oft_domain`，在 `build_mesh()` 之后读取最终 `region_info`）：至少一个区域；`reg` 全为有限正整数；`len(reg)==T`；输出 ID 集合与最终 `region_info` 一致；每个区域至少一个三角形；不重编号/排序/压缩/+1。`build_mesh()` 会原地重排区域 ID，绝不能在其之前提取。
- **当前默认 GFile 区域策略**：有有效第一壁 → PLASMA+VACUUM+OUTER（`add_annulus`+`add_rectangle`）；无壁 → PLASMA+OUTER（`add_polygon`+`add_rectangle`）。这是当前 CLI 便利策略，非 Adapter 能力边界。single-region 策略见第 6A.11 节。
- **OFT 点合并参数（版本锁定）**：P0 继续调用 OFT 26.6 `build_mesh()` 的锁定默认 `merge_thresh=1e-4 m`，不新增公共参数，不向 CLI 或 `linkmesh.in` 暴露。single-region polygon 输入规范化阈值必须与该锁定默认值同步；未来若 LinkMesh 显式改变 `build_mesh()` 的 `merge_thresh`，必须先修订蓝图并同步更新规范化阈值和测试。
- **outer boundary 形状**：当前 `nested_three_region` 为 LCFS 与第一壁联合包围盒加 `outer_padding` 的**矩形**；`single_region` 首批直接使用 LCFS/第一壁/`array_file` 边界本身。`outer_boundary` 字段只保存实际计算域边界几何，不决定形状生成策略。放大 LCFS、D 形、椭圆、自定义多边形或线圈/导体包络仍待 User 与导师确认；未来更换形状沿用同一 `(B,2)` 字段，Writer 契约不随形状变化。
- **退化检查**：无重复顶点、无越界索引、绝对面积 > `1e-12`。
- **边界编号（历史/过渡约定，不参与 TRIMEG 契约）**：`1=LCFS`、`2=first wall`、`3=outer boundary`、`0=内部`。TRIMEG 内外节点区分由三角形拓扑推导，不依赖此表。

---

## 5. TRIMEG HDF5 契约（完整 11 数据集，已实现并验收）

黄金标尺：`docs/trimeg/loadfemmesh_h5.m` 与两个真实样例。所有数据集位于 `/femmesh/`，磁盘 dtype **全部 float64**。

完整 11 数据集：`nvert ntria nvert_in nvert_ex vert idxivert idxevert tria nbcRZ Rbc Zbc`

| 路径 | 磁盘 shape | 说明 |
|---|---|---|
| `nvert` | `(1,1)` | 节点总数 N（整数语义） |
| `ntria` | `(1,1)` | 三角形总数 T |
| `nvert_in` | `(1,1)` | 内部节点数 |
| `nvert_ex` | `(1,1)` | 拓扑外边界节点数 |
| `vert` | `(N,2)` | 节点坐标，每行 `[R,Z]`，**不转置** |
| `tria` | `(T,3)` | 连接表，**1-based**，无第四列（`triangles+1`） |
| `idxivert` | `(1,nvert_in)` | 内部节点全局索引，1-based 升序（`{1..N}` 补集） |
| `idxevert` | `(1,nvert_ex)` | 拓扑外边界节点全局索引，1-based 升序 |
| `nbcRZ` | `(1,1)` | 有序外边界点数 B（整数语义） |
| `Rbc` | `(B,1)` | `mesh.outer_boundary[:,0]` |
| `Zbc` | `(B,1)` | `mesh.outer_boundary[:,1]` |

规则要点：

- Mesh2D 内部 0-based；文件连接表与 `idxivert/idxevert` 为 1-based。
- `region_ids` **不写入** TRIMEG HDF5。
- `idxevert` 定义为三角形无向边中只出现一次的边所含节点集合（拓扑外边界）；非流形边（同一无向边被 >2 三角形共享）在打开目标文件前拒绝；无任何拓扑外边界边时拒绝。
- `idxivert = {1..N} \ idxevert`；`nvert_in+nvert_ex=nvert`；两集合互斥且覆盖全部节点。
- `nbcRZ = len(outer_boundary)`；`Rbc = outer_boundary[:,0]`；`Zbc = outer_boundary[:,1]`。
- `Rbc/Zbc` 来自有序 `mesh.outer_boundary`；**禁止**用升序 `idxevert` 反推 `Rbc/Zbc`；`Rbc/Zbc` 不含生成器后插入的 Steiner 边界点。
- `nbcRZ` **不要求**等于 `nvert_ex`。
- TRIMEG target 下 `outer_boundary` 缺失（`None`）时，Writer 在打开输出文件前失败；Writer 不负责猜测 boundary source、不从 `idxevert` 恢复点序、不做边界重采样。
- Writer 全部输入验证（shape/有限性/整数语义/索引范围/重复顶点/面积/非流形/`outer_boundary` 合法性含自交）在打开目标文件前完成，且不修改输入 `Mesh2D`；Writer 复用 `mesh.py` 统一 `_validate_outer_boundary`（含完整非相邻边自交检查）作为二次防线，不复制自交算法。

**v2.5 最新真实 CLI 与消费端证据**：

| 真实链路 | 结果 |
|---|---|
| DIII-D `g192185.02440`；`target=trimeg`、`profile=nested_three_region`、`boundary_source=artificial_outer` | CLI 退出码 0；972 节点、1872 三角形、3 区域、902 内部节点、70 拓扑外边界节点、`outer_boundary` 70 点；成功生成 HDF5、PNG 与运行日志 |
| fixed-boundary `gNT_example`；`target=trimeg`、`profile=nested_three_region`、`boundary_source=artificial_outer` | CLI 退出码 0；3412 节点、6692 三角形、3 区域、3282 内部节点、130 拓扑外边界节点、`outer_boundary` 130 点；成功生成 HDF5、PNG 与运行日志 |
| DIII-D `g192185.02440`；`target=trimeg`、`profile=single_region`、`boundary_source=lcfs`、`plasma_dx=0.08 m` | CLI 退出码 0；344 节点、631 三角形、1 区域、289 内部节点、55 拓扑外边界节点、`outer_boundary` 55 点；成功生成 HDF5、PNG 与运行日志；LCFS 相邻近重复控制点导致的 OFT 回写失败不再阻塞真实链路 |

三份 LinkMesh HDF5 经 `h5ls` 确认均包含完整 11 个 `/femmesh` 数据集：
`nvert`、`ntria`、`nvert_in`、`nvert_ex`、`vert`、`tria`、`idxivert`、
`idxevert`、`nbcRZ`、`Rbc`、`Zbc`。实际布局继续遵守本节正式契约：
`vert=(N,2)`、`tria=(T,3)`、文件端节点索引 1-based、无第四列、不写
`region_ids`，`Rbc/Zbc` 来自 `Mesh2D.outer_boundary`，且不要求
`nbcRZ == nvert_ex`。

OFT 的 `Repeated points`、`Sliver` 与 `Small feature` 信息仍作为诊断 warning
保留；上述 nested 网格、HDF5 与 PNG 均已成功生成，不得把这些 warning 表述为
Triangle 失败。

**MATLAB 标准消费端 A/B 验收（PASSED）**：使用老师原始
`docs/trimeg/loadfemmesh_h5.m` 读取并绘制标准样例
`femmesh_65402_t1_nr16core.h5` 与 LinkMesh `single_region + lcfs` 生成的
`mesh.h5`。两者均成功读取并通过基础网格检查；标准样例约 981 节点、1847
三角形，LinkMesh 文件为 344 节点、631 三角形且 `nbcRZ=55`。两幅 MATLAB
图均表现为单一闭合计算域内部三角剖分，未发现节点索引错误、明显跨域错误连线或
读取布局错误；验证脚本只读、检查并绘图，未修改、删除或写回 HDF5。

该 A/B 证据确认 TRIMEG 接受“单一闭合计算域内部网格化”的静态网格，并确认当前
`single_region + lcfs` 与标准样例在拓扑形态上相容；它不证明 TRIMEG 永久固定使用
LCFS，也不固定 `Rbc/Zbc` 的物理来源。`Rbc/Zbc` 表示任务选定的有序计算域外边界。
因此，`single_region + first_wall` 仍是有价值的后续来源，但“必须先实现第一壁内部
全域网格”不再是启动 M4 的前置条件。

**两个参考样例直接证据（User 提供，紧凑归档）**：

| 样例 | Rbc/Zbc | nbcRZ | nvert_ex | 匹配 | 连续点对为拓扑边 | 方向/闭合 |
|---|---|---|---|---|---|---|
| `femmesh_65402_t1_nr16core.h5` | `(112,1)` | 112 | 113 | 112 点全部精确匹配最终 `vert`/`idxevert`（最大距离 0） | 111/112；唯一额外外边界节点位于最后一点→首点的闭合边上，为生成后插入的边界点 | 顺时针、单闭环、末尾不重复首点 |
| `femmesh_65402_t1_nr16nout4edge.h5` | `(175,1)` | 175 | 175 | 175 点全部精确匹配 | 175/175 均为实际拓扑边界边 | 顺时针、单闭环、末尾不重复首点 |

由此确认：`Rbc/Zbc` 是有序边界几何（非升序坐标集合）；`idxevert` 描述最终拓扑外边界节点；`Rbc/Zbc` 不含生成器后插入点；`nbcRZ` 可等于或小于 `nvert_ex`。两样例均未证明固定起点规则，不得写成事实。

**M3 complete-11 真实验收证据（已 PASSED，见 `History.md` 第 19 条）**：`71fe09f` 早期把人工矩形四控制角点错误作为 `outer_boundary`，此错误已修正为受控读取 `outer_region._resampled_points`（见第 3.2A 节）。两个真实 GFile 结果：DIII-D `g192185.02440` → 972 节点/1872 三角形/3 区域/内部 902/外边界 70/`outer_boundary` 70、`signed_area` 顺时针、所有 `Rbc/Zbc` 与最终 `vert` 最大匹配距离 0、h5py 11 数据集通过、MATLAB `loadfemmesh_h5.m` 成功读取重建且与 Python Plotter 图人工一致、无缺三字段 warning；fixed_boundary `gNT_example` → 3412 节点/6692 三角形/3 区域/内部 3282/外边界 130/`outer_boundary` 130、h5py 11 数据集与 shape/dtype/索引/计数检查通过。第一样例 `nbcRZ==nvert_ex==70`、第二样例二者均 130，均为样例实际结果，**不表示**格式要求二者恒等。当前默认 `nested_three_region + artificial_outer` 下 `Rbc/Zbc` 表示人工矩形最外计算域、第一壁为内部界面（MATLAB 红色矩形与固定策略一致，非读取错误）。M3 complete-11、M3 完整闭环均 **PASSED**。

---

## 6. CLI 契约

必进入同一 `cli.main()`：`python -m linkmesh [选项]` 与控制台命令 `linkmesh [选项]`（后者依赖计划中的 `pyproject.toml`）。

**现有已实现参数**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--gfile PATH` | 必选（当前实现） | GFile/EQDSK 路径 |
| `--output PATH` | `mesh.h5` | TRIMEG HDF5 输出 |
| `--smb PATH` | `mesh.smb` | PUMI `.smb` 输出（M4） |
| `--plasma-dx FLOAT` | `0.08` | LCFS 内 plasma 区目标网格尺度（m） |
| `--vacuum-dx FLOAT` | `0.10` | LCFS 与第一壁间 vacuum 区目标网格尺度（m） |
| `--outer-dx FLOAT` | `0.15` | 第一壁与最外层边界间 outer 区目标网格尺度（m） |
| `--min-angle FLOAT` | `20.0` | 历史参数；非默认值直接报错拒绝 |
| `--max-area FLOAT` | `None` | 历史参数；给出即报错拒绝 |
| `--plot PATH` | `None` | 自检 PNG |
| `--no-smb` / `--no-hdf5` | `False` | 跳过对应输出 |
| `--verbose` | `False` | 详细日志 |

三个 `dx` 契约：`dx` 是传给 OFT 的**目标区域尺度**，非硬边长约束；使用物理区域名映射到 `define_region(name, dx, reg_type)`，不依赖 `region_ids` 数值顺序。验证规则：可解析浮点、有限、严格大于 0；`0`/负数/`nan`/`±inf` 必须在调用 OFT 前失败，错误含参数名与"必须是有限正数"；非数字文本由 argparse 拒绝；不静默恢复默认、不取绝对值、不裁剪、不换算单位。CLI 只解析/验证/转发，原样按关键字传给 `generate_mesh(gfile_data, plasma_dx=..., vacuum_dx=..., outer_dx=...)`。用户不提供时行为与默认完全兼容。

两层输入架构（`linkmesh.in` + CLI + `EffectiveConfig`）契约见第 6A 节。`outer_padding` 在 v2.4 仍**不暴露**为正式配置或 CLI 字段，保持内部默认策略。OFT `merge_thresh` 同样不暴露为 CLI 或配置字段，继续锁定使用 OFT 26.6 默认 `1e-4 m`。自适应细化、全局 `--mesh-size`、计算域选择参数在 v2.4 未在源码暴露。

### 6.1 近期输入层优先级（v2.5 冻结）

1. 保持并维护已有真实运行证据的 `nested_three_region + artificial_outer`。
2. 保持并维护已通过真实 CLI 与 TRIMEG MATLAB 消费验收的
   `single_region + lcfs`。
3. `single_region + first_wall` 保留为有价值的后续边界来源，但不再阻塞 M4。
4. `single_region + array_file` 保留为后续轻量外部轮廓输入，当前不实施。
5. `single_region + flux_surface` 仍需真实磁面提取证据；禁止径向缩放 LCFS
   伪造磁面，当前不实施。
6. 不继续扩建大型 Fake OFT/Mock 测试体系。未来新增边界来源以少量关键单元测试，
   配合真实 GFile、OFT 26.6、CLI、PNG/HDF5 验收为主。

上述调整只冻结近期实施顺序，不删除未来 boundary source 的正式规划，也不表示
`first_wall`、`array_file` 或 `flux_surface` 已实现。

---

## 6A. 输入架构（两层输入 + EffectiveConfig，字段级契约）

以下为 User 已批准的字段级正式契约。保持轻量边界：不得建设通用配置 DSL、任意 N 区域语言或插件系统。

**标准 `linkmesh.in` 示例决策（v2.5）**：两层输入架构、TOML
`schema_version=1`、`EffectiveConfig`、优先级“内建默认值 < `linkmesh.in` <
用户显式 CLI”、未知键严格报错、`--config/--no-config` 互斥及
`target/profile/boundary_source` 兼容矩阵均保持正式有效。仓库当前尚无面向用户的
标准化 `linkmesh.in` 示例，本阶段不创建示例；缺少示例文件不表示配置架构未实现。
待 LinkMesh 的 TRIMEG HDF5 与未来 M3DC1 TXT+SMB 均通过各自真实消费端验收后，
再构造能够覆盖或清晰表达两个下游目标的标准示例，避免现在只围绕 TRIMEG 提前固化。

### 6A.1 模块落点

- `src/linkmesh/config.py`：`EffectiveConfig` 定义 + `linkmesh.in` 读取/校验/合并 + 兼容矩阵/required fields 校验（职责与禁止见第 2 节表）。
- `src/linkmesh/readers/boundary_reader.py`：`array_file` 两列 CSV → `(B,2) float64`（职责与禁止见第 2 节表）。
- `readers/gfile_reader.py`、`mesher/oft_adapter.py`、`cli.py`、`mesh.py`、
[Upstream error: stream_read_error]
