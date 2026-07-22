# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **2.1**（在 v2.0 基线上固化 M4-0 侦察成果：写入 User 已批准的两层输入架构与 `target/profile/boundary_source` 分层、`M3DC1ModelSpec` 目标专用对象、M3DC1 双文件输出契约（TXT model + SMB，SMB 经 PUMI/APF/MDS 官方 API 生成，禁止手写字节流）、C1 初始静态网格边界、M4 实现停止条件与 Level 1–4 验收；收紧 `outer_boundary` 与 `Rbc/Zbc/nbcRZ` 正式定义并记录 `71fe09f` 数据来源错误；补充 M4-0A..0E 子里程碑与后续严格顺序。本轮为文档固化，未修改任何业务源码或测试，M3 complete-11 与 M4 均未标 PASSED）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`；M4-0 前置侦察逐轮证据见 `report.md`、`m4_0d_report.md`、`m4_0d1_report.md`、`m4_0d2_report.md`（阶段证据，非本蓝图正文的长期正式依赖，蓝图正文自包含）
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION / PENDING CORRECTION AND VALIDATION】为已批准正式契约但尚未实现、或已有实现尝试但尚未通过验收的功能；【P0 禁止】为当前阶段严格禁止引入的功能；【实现候选】为已有源码调用点线索但须目标版本与最小运行验证确认、不得写成固定接口的路线
- 修改前置条件：任何对本文档接口、字段、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位与范围

LinkMesh 是一个**独立命令行程序（CLI）**，用于打通「等离子体平衡文件 GFile/EQDSK → 二维非结构三角网格 → 目标求解器静态网格文件」的转换链路。

**唯一网格生成底座**：OFT/TokaMaker 封装方式调用的 Triangle（OFT 内部经 `liboft_triangle` 完成）。LinkMesh 不维护第二种网格引擎。

**SCOREC/PUMI 架构位置（M4 相关，非第二剖分引擎）**：M4 引入的 SCOREC/PUMI 技术栈**不是第二个三角剖分引擎**。其中 GMI 负责 geometric model 接口、APF 负责网格与 field 抽象、MDS 负责底层 mesh 表示、PCU 负责并行通信支持，PUMI 是 M3D-C1 使用的接口/封装层。M4 中 LinkMesh 的作用是把 `Mesh2D` 与 `M3DC1ModelSpec` 转换为 classified APF/MDS 网格，并调用官方 API 输出 `.smb`；Triangle 仍是唯一剖分底座。

**正式数据流**：

```text
GFile/EQDSK → Reader → OFT Adapter → Mesh2D → TRIMEG HDF5 / future PUMI API output → PNG
```

**P0 范围**：

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile | 在 LinkMesh 侧手写 GFile 文本解析；复杂 CAD；多维输入 |
| 网格生成 | 调用 OFT `gs_Domain` / `build_mesh()` | 引入第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；修改/维护 OFT 分支 |
| 并行切分 | 不涉及 | 生成 `**1.smb`~`**16.smb` 并行分区 |
| 输出 | TRIMEG HDF5；M3DC1 PUMI `.smb`（M4，经 PUMI/APF/MDS 官方 API） | 三维输出；手写、拼接、修改或逆向 `.smb` 二进制字节流 |
| 可视化 | matplotlib 自检 PNG | 交互式/三维渲染 |
| 配置 | 当前 CLI 参数；两层输入架构（`linkmesh.in` + CLI，见第 6A 节，PLANNED） | 通用配置 DSL / 任意 N 区域语言 / 插件系统 |

---

## 2. 当前架构与模块职责

允许依赖方向：`cli → readers / mesher / writers / utils`；`mesher.oft_adapter → mesh`；`writers → mesh`；`utils.plotter → mesh`。`mesh.py` 不依赖任何后端、Writer、CLI 或 Plotter。

| 模块 | 职责（一段式） | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 任何业务逻辑或参数解析 |
| `src/linkmesh/cli.py` | 解析/验证参数（含三个区域 `dx`），拦截历史 `--min-angle/--max-area`，按顺序调用 Reader → `generate_mesh()` → Writer → Plotter，原样按关键字转发 `dx` | 实现区域/几何/种子/Triangle 算法或任何 dx 换算；恢复已删除历史边界构造代码 |
| `src/linkmesh/mesh.py` | 定义 `Mesh2D`（唯一正式统一网格对象）与只读统计属性 | 依赖 OFT/Triangle/HDF5/PUMI/CLI/Plotter；共享可变默认数组 |
| `src/linkmesh/readers/gfile_reader.py` | 薄 Adapter：调用 OFT `GEQDSKEquilibrium`，提取字段封装为 `GFileData`；仅允许 LCFS 闭合/方向后处理 | 手写文本解析；调用 Triangle；写文件 |
| `src/linkmesh/mesher/oft_adapter.py` | 三层接口：`mesh_from_oft_domain(domain)` 通用 N 区域核心（含 N=1）、`build_oft_domain_from_gfile(gfile_data, plasma_dx, vacuum_dx, outer_dx, ...)` 默认策略层、`generate_mesh(...)` 便利入口；将 `pts/lc/reg` 规范化为 `Mesh2D` | 复制 OFT 通用几何/种子/重采样/Triangle 算法；写死区域数量/名称/类型/ID；无依据再次偏置 0-based 连接表；修改 OFT 源码或依赖 `TOKAMAKER/` 快照 |
| `src/linkmesh/writers/hdf5_writer.py` | 接收 `Mesh2D`，按 TRIMEG HDF5 契约写出（见第 5 节） | 修改 `Mesh2D`；写 `region_ids`；转置 `vert/tria`；给 `tria` 加第四列；网格生成逻辑 |
| `src/linkmesh/writers/smb_writer.py` | M4 占位；侦察与蓝图确认前保持 `NotImplementedError`；未来经 PUMI/APF/MDS 官方 API 输出 | 手写/拼接/修改/逆向 `.smb` 字节流 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()`（支持区域着色、LCFS/第一壁闭合显示） | 修改任何数据对象 |

M4 规划新增模块（PLANNED，本轮不建源码）：M3DC1 目标专用对象 `M3DC1ModelSpec`（第 7 节）、TXT model Writer 与 PUMI/APF/MDS Adapter（第 7 节）、两层输入配置与 `EffectiveConfig`（第 6A 节）。

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

**正式定位（v2.0，v2.1 保持）**：`Mesh2D` 是 LinkMesh 面向多个下游模拟代码（TRIMEG、M3DC1/PUMI 等）的**统一、持久、求解器无关**中间网格对象。

原则：

- 保存下游共同需要、且在网格生成后**无法可靠反推**的规范几何、拓扑、物理标记与必要分类信息；
- 目标格式的索引、转置、dtype、布局转换由各 Writer 完成；不得把 TRIMEG/M3DC1/PUMI 的文件布局搬进 `Mesh2D` 内存布局；
- 可从 `triangles` 无损、确定性派生的边集合与邻接关系，**默认不重复存储**，除非 M4 直接证据证明必须持久保存；
- 不因追求"最完备"而提前加入未经证据确认的 C1 自由度、高阶节点、PUMI 私有句柄、MPI ownership、M3DC1 私有数组或求解器运行时对象。

**核心字段（来自 OFT `build_mesh()`，内部索引 0-based）**：

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | 线性二维节点 `[R,Z]` [m] |
| `triangles` | `(T,3)` | 整数（实测 `int32`） | 三顶点节点索引，**内部 0-based** |
| `region_ids` | `(T,)` | 整数（实测 `int32`） | OFT 最终区域编号，**原样保留**（不重编号/排序/压缩/+1）；LinkMesh 物理区域标签，**不等同于** M3DC1 geometric face tag |

**兼容字段（现存于 `mesh.py`，均安全空数组默认值，不参与 TRIMEG 契约）**：`boundary_segments (0,2) int32`、`boundary_markers (0,) int32`、`node_markers (0,) int32`。这三个字段**与下文 `outer_boundary` 不同义、不同名、语义不同**；不得改名或删除既有字段。

**`outer_boundary` 字段（正式定义，实时 `mesh.py` 已含该可选字段并在 `__post_init__` 中执行部分验证；提交 `71fe09f` 已有实现尝试，但 OFT Adapter 传入的数据来源错误，处于 PENDING CORRECTION AND VALIDATION）**

`Mesh2D.outer_boundary` 表示当前 `Mesh2D` 所代表计算域**在进入 Triangle 前**的有序离散外边界。

| 属性 | 规定 |
|---|---|
| 类型 / shape / dtype | `Optional[np.ndarray]` / `(B,2)` / `float64` |
| 列含义 / 单位 | 第 0 列 R，第 1 列 Z / m |
| 语义 | 传入网格生成器的、有序、最外层计算域几何边界点；一条**单一简单闭合轮廓** |
| 闭合 | 末尾**不重复首点**，最后一点与第一点隐式闭合 |
| 方向 | 顺时针（带符号闭合面积严格为负） |
| 约束 | 至少 3 个互异有限点；无相邻重复点；无零长度闭合边；无退化面积；**单一简单闭环，禁止非相邻边自交**；P0 只允许一条最外层闭合轮廓 |
| 所有权 | 数组由 `Mesh2D` **独立持有**（构造期规范化为 float64 独立副本），不与外部可变输入共享所有权 |
| 必选性 | **TRIMEG target 必须提供**；`mesh_only` 与 M3DC1 target 按各自目标契约处理，可为 `None` |
| 与 Steiner 点 | **不包含** OFT/Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑外边界节点集合；因生成器插点，`B` 可小于最终 `nvert_ex` |
| 性质 | 求解器无关的计算域几何，**不是**按节点编号升序生成的 `idxevert` 坐标表 |

**验证实现状态（重要）**：`Mesh2D.__post_init__` 当前对 shape、dtype、有限性、点数、相邻重复点、隐式闭合语义、方向、退化面积执行验证；**尚未完整实现非相邻边自交检查**。完整自交验证及其测试列入返回 M3 complete-11 时**必须核对并补齐**的事项（见第 5 节 M3 complete-11 验收条件与第 10.3 节）。不得宣称当前 `__post_init__` 已完整实现全部自交检查。

`outer_boundary` **不是**：人工矩形四个控制角点；最终按节点编号排序的 `idxevert`；Triangle 后续插入的全部 boundary Steiner points；永久固定的 LCFS；永久固定的 first wall；永久固定的 artificial outer。

正确数据链：

```text
控制几何 / 边界来源
  → 边界验证与方向规范化
  → OFT/Triangle 输入前的真实有序离散点列
  → Mesh2D.outer_boundary
  → TRIMEG Rbc/Zbc
```

对于 `artificial_outer`：人工矩形控制几何 → 按网格尺度或 OFT 策略重采样 → Triangle 输入前离散边界 → `outer_boundary`。**四个矩形控制角点不得直接代替离散边界点列。**

起点规则：当前无足够证据，不规定固定起点（不强制从最小 R/最大 R/最小 Z 起）。只要求点序相邻正确、方向为顺时针、同一输入与配置产生确定顺序。

**禁止加入 `Mesh2D` 的数据（P0）**：triangle adjacency（由 triangles 派生）、geometric model handles、PUMI handles、geometric model tags、C1 field、edge orientation、boundary normal、boundary curvature、high-order nodes、MPI ownership。可确定性派生的数据默认由 Adapter、PUMI/MDS 或 M3D-C1 运行时生成。

**只读统计属性**：`n_nodes`、`n_triangles`、`n_boundary_segments`。

---

## 4. 网格与物理约定

- **坐标/单位**：`[R,Z]`，SI（m、T、A）。
- **内存索引**：`triangles` 内部 0-based；目标格式偏置（如 TRIMEG +1）由对应 Writer 在写出阶段完成。`region_id` 与节点索引转换无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- **OFT 输出契约**（已确认）：`pts (np,2) float64`、`lc (nc,3)` 0-based 整数（`0<=lc<N`）、`reg (nc,)` 正整数，与 `domain.region_info` 最终 ID 一一对应。
- **区域编号**：原样保留 OFT `reg`；区域语义只从 `domain.region_info` 名称/类型/最终 ID 获得，不由整数值推断；区域数量由 OFT 当前区域模型决定，不写死；合法单区域（N=1）满足契约。
- **区域校验**（`mesh_from_oft_domain`，在 `build_mesh()` 之后读取最终 `region_info`）：至少一个区域；`reg` 全为有限正整数；`len(reg)==T`；输出 ID 集合与最终 `region_info` 一致；每个区域至少一个三角形；不重编号/排序/压缩/+1。`build_mesh()` 会原地重排区域 ID，绝不能在其之前提取。
- **当前默认 GFile 区域策略**：有有效第一壁 → PLASMA+VACUUM+OUTER（`add_annulus`+`add_rectangle`）；无壁 → PLASMA+OUTER（`add_polygon`+`add_rectangle`）。这是当前 CLI 便利策略，非 Adapter 能力边界。
- **outer boundary 形状**：当前为 LCFS 与第一壁联合包围盒加 `outer_padding` 的**矩形**。`outer_boundary` 字段只保存实际计算域边界几何，不决定形状生成策略。放大 LCFS、D 形、椭圆、自定义多边形或线圈/导体包络仍待 User 与导师确认；未来更换形状沿用同一 `(B,2)` 字段，Writer 契约不随形状变化。
- **退化检查**：无重复顶点、无越界索引、绝对面积 > `1e-12`。
- **边界编号（历史/过渡约定，不参与 TRIMEG 契约）**：`1=LCFS`、`2=first wall`、`3=outer boundary`、`0=内部`。TRIMEG 内外节点区分由三角形拓扑推导，不依赖此表。

---

## 5. TRIMEG HDF5 契约（完整 11 数据集）

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
- Writer 全部输入验证（shape/有限性/整数语义/索引范围/重复顶点/面积/非流形/`outer_boundary` 合法性）在打开目标文件前完成，且不修改输入 `Mesh2D`。

**两个样例直接证据（User 提供，紧凑归档）**：

| 样例 | Rbc/Zbc | nbcRZ | nvert_ex | 匹配 | 连续点对为拓扑边 | 方向/闭合 |
|---|---|---|---|---|---|---|
| `femmesh_65402_t1_nr16core.h5` | `(112,1)` | 112 | 113 | 112 点全部精确匹配最终 `vert`/`idxevert`（最大距离 0） | 111/112；唯一额外外边界节点位于最后一点→首点的闭合边上，为生成后插入的边界点 | 顺时针、单闭环、末尾不重复首点 |
| `femmesh_65402_t1_nr16nout4edge.h5` | `(175,1)` | 175 | 175 | 175 点全部精确匹配 | 175/175 均为实际拓扑边界边 | 顺时针、单闭环、末尾不重复首点 |

由此确认：`Rbc/Zbc` 是有序边界几何（非升序坐标集合）；`idxevert` 描述最终拓扑外边界节点；`Rbc/Zbc` 不含生成器后插入点；`nbcRZ` 可等于或小于 `nvert_ex`。两样例均未证明固定起点规则，不得写成事实。

**提交 `71fe09f` 状态（M3 complete-11 PENDING CORRECTION AND VALIDATION）**：`71fe09f` 已存在 `Mesh2D.outer_boundary` 字段、11 数据集 Writer 映射与相关测试的**实现尝试**，但 OFT Adapter 将**人工矩形四个控制角点**错误作为 `outer_boundary`，未经过 Triangle 输入前的真实重采样离散点列。该实现尝试**尚未通过**架构、真实 GFile、`h5py` 与 MATLAB/Octave 完整验收，处于 **PENDING CORRECTION AND VALIDATION**。M4-0E 文档固化后必须先返回 M3 complete-11 修正该数据来源并完成验收；不得把当前尝试标记为通过。

**M3 complete-11 验收条件**：精确 11 数据集（path/shape/dtype 见上表）；`nbcRZ` 数值正确；`Rbc/Zbc` 来自 `outer_boundary`、不从 `idxevert` 反推、不要求 `nbcRZ==nvert_ex`、Steiner 点隔离；`outer_boundary` 完整自交验证（单一简单闭环、禁止非相邻边自交）在 `Mesh2D.__post_init__` 或等效统一验证层补齐并有测试覆盖；`h5py` 回读验证；MATLAB 或 Octave 用 `loadfemmesh_h5.m` 验证（不再出现缺三字段 warning）；两个真实 GFile 回归；PNG 或等效几何检查；并有测试证明人工控制角点不能错误代替离散边界点列。

---

## 6. CLI 契约

必进入同一 `cli.main()`：`python -m linkmesh [选项]` 与控制台命令 `linkmesh [选项]`（后者依赖计划中的 `pyproject.toml`）。

| 参数 | 默认 | 说明 |
|---|---|---|
| `--gfile PATH` | 必选 | GFile/EQDSK 路径 |
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

配置文件参数（`--config` / `--no-config`）与 `outer_padding`、全局 `--mesh-size`、自适应细化、计算域选择参数在 v2.1 尚未在源码暴露；两层输入架构契约见第 6A 节（PLANNED），实现前不建源码。

---

## 6A. 输入架构（两层输入 + EffectiveConfig，PLANNED）

以下为 User 已批准的正式架构契约，本轮只写蓝图，不建源码文件或字段实现。保持轻量边界：不得建设通用配置 DSL、任意 N 区域语言或插件系统。

### 6A.1 配置文件 `linkmesh.in`

- 文件名：`linkmesh.in`；格式：TOML；编码：UTF-8；`schema_version = 1`。
- Python 3.12 使用标准库 `tomllib` 读取。
- 未知 section 与未知键**严格报错**。
- 不执行 Python 表达式；不执行 Shell 命令；不自动展开环境变量。
- 配置文件中的相对路径相对于**配置文件所在目录**；CLI 中的相对路径相对于**当前工作目录**；CLI 覆盖配置路径时使用 CLI 路径解析规则。

配置发现规则：

1. 显式 `--config PATH`：只加载该文件；文件不存在立即失败。
2. 未指定 `--config` 且未指定 `--no-config`：检查当前目录的 `linkmesh.in`。
3. `--no-config`：禁用自动发现。
4. `--config` 与 `--no-config` **互斥**。
5. verbose 模式打印实际加载的配置绝对路径。

### 6A.2 EffectiveConfig 与优先级

规划只读/不可变语义的 `EffectiveConfig`，表示合并后的有效任务配置。优先级：

```text
程序内建默认值 < linkmesh.in < 用户显式提供的 CLI 参数
```

**只有用户实际输入的 CLI 字段**才能覆盖配置文件值；argparse 解析器默认值**不得**无条件覆盖配置值。

### 6A.3 配置层次

至少规划 section：`[task]`、`[input]`、`[domain]`、`[mesh]`、`[output]`、`[runtime]`。核心语义：

- target：`mesh_only` / `trimeg` / `m3dc1`（决定输出与 Writer）。
- profile：`single_region` / `nested_three_region`（决定区域策略）。
- boundary source：`lcfs` / `flux_surface` / `first_wall` / `array_file` / `artificial_outer`（决定计算域外边界来源）。
- mesh resolution：`plasma_dx` / `vacuum_dx` / `outer_dx`（现有）及 M3DC1 per-loop/face 尺度。
- output paths：HDF5 / `.smb` / model `.txt` / PNG 路径。
- runtime flags：`verbose` / `no_hdf5` / `no_smb` 等。

### 6A.4 boundary source 正式契约

- `lcfs`：使用 GFile/EQDSK 提取的 LCFS，进入 Mesher 前归一化为有序闭合边界点列；是否允许用于特定 target/profile 由兼容矩阵裁决。
- `flux_surface`：使用归一化磁通 `(psi - psi_axis) / (psi_lcfs - psi_axis)`，合法候选范围 `0 < normalized_flux < 1`；必须从平衡磁通提取真实闭合等磁通轮廓；**禁止**通过径向缩放 LCFS 伪造磁面；轮廓提取接口尚未实现，属后续任务；TRIMEG 首批实现不因其未完成被阻塞。
- `first_wall`：使用 GFile 第一壁/limiter 轮廓，归一化为有序闭合边界点列；是否允许由兼容矩阵决定。
- `array_file`：文本文件，候选两列 CSV；内存形状 `(B,2)`，第 0 列 R、第 1 列 Z，单位 m；至少 3 个互异有限点；不允许相邻重复点、零长度边、退化面积、自交；单一简单闭环；文件末尾不重复首点（隐式闭合）；允许在保持起点前提下统一为蓝图规定方向；大型点列不得直接内嵌 TOML。
- `artificial_outer`：仅用于当前 `nested_three_region` 演示/内部策略；人工矩形控制几何本身不是最终 `outer_boundary`，必须经实际重采样得到进入 Triangle 前的有序离散点列，该离散点列才进入 `Mesh2D.outer_boundary`。

### 6A.5 target/profile/boundary_source 兼容矩阵

| 组合 | 状态 |
|---|---|
| `mesh_only + nested_three_region + artificial_outer` | 当前已确认可执行 |
| `trimeg + single_region + lcfs` | 首批支持目标 |
| `trimeg + single_region + first_wall` | 首批支持目标 |
| `trimeg + single_region + array_file` | 首批支持目标 |
| `trimeg + single_region + flux_surface` | 架构允许，等待真实磁通轮廓提取实现 |
| `m3dc1 + single_region + lcfs` | P0 候选，待实现后 Level 1–3 验收 |
| `m3dc1 + single_region + first_wall` | P0 候选，待实现后 Level 1–3 验收 |
| `m3dc1 + single_region + array_file` | P0 候选，待实现后 Level 1–3 验收 |
| `m3dc1 + single_region + flux_surface` | 等待真实轮廓提取和 M3DC1 验收 |
| `m3dc1 + nested_three_region` | 当前禁止（多物理区域与界面语义未确认前不得开放） |

不得把"技术上可构造"写成"已经实现"或"已通过消费端验证"。不得把多 geometric face 直接等同 plasma/vacuum/wall 多物理方程区域。

---

## 7. M3DC1 / PUMI 输出契约（M4，PLANNED / 部分待实现阶段确认）

M4 面向 M3D-C1 消费端，产出**配套双文件**：TXT model file + SMB mesh file。SMB 经 PUMI/APF/MDS 官方 API 生成。以下含【刘老师会议确认的 A 级事实】、【生成端与消费端双向源码确认】、【架构正式定义】、【实现候选】与【实现阶段停止条件】。

### 7.1 双文件输出契约

**TXT model file**（M3D-C1 geometric model 文本，非 CSV 点表）：

- 至少包含边界点 ID、坐标以及恢复 geometric model 所需的 loop、edge、curve、face 信息。
- 字段顺序与拓扑契约以生成端 `save_model()`/`save_multi_rgn_model()` 与消费端 `load_model()` 的**双向源码**为黄金标尺，不得缩减为边界坐标 CSV。
- P0 应输出完整 `numFaces > 0` 的 face 段，不依赖旧格式兼容回退分支。
- P0 single-face model 可使用源码已证明的**单闭合 periodic edge + one loop + one face** 路径；具体曲线实现（BSpline 控制点拟合等）仍需实现阶段验证。
- TXT Writer 必须单独可测试（Level 1）。

**SMB mesh file**（PUMI native 网格）：

- 由 PUMI/APF/MDS **官方 C/C++ API** 生成；LinkMesh **不定义、不实现、不手写、不拼接、不修改、不逆向** SMB 字节布局【会议 A 级事实】。
- LinkMesh 将网格顶点、三角形及形成合法 classified mesh 所需信息录入 PUMI 内存网格，由 PUMI 自动生成 SMB。
- SMB 至少承载全量 mesh vertices 与 mesh triangles；不得据此缩减为"SMB 只含顶点和三角形"——SMB 还必须形成可由 PUMI/APF/MDS 加载、且与配套 TXT geometric model 相容的 **classified mesh**。
- geometric classification 在 mesh entity 创建时或正式 API 规定阶段建立；最终保存通过 `writeNative()` 或目标版本正式等效 API【实现候选，签名待版本确认】。
- `.dmg` **不属于** P0 必需输出（延后确认）。

### 7.2 配套一致性

- geometric model 必须**先于** mesh 加载。
- TXT 中的 geometric vertex/edge/face tag 必须能解释 SMB 中的 mesh entity classification。
- TXT 单独可读、SMB 单独可加载都**不足以**证明双文件整体通过。
- 两文件 classification 不相容时，M4 验收失败。
- 文件是否强制共享 base name、单进程 rank 后缀（源码字符串处理显示 `foo.smb` 查 `foo0.smb`）等细节保留为**实现阶段验证项**，不提前写死。

### 7.3 `M3DC1ModelSpec`（M3DC1 目标专用对象，PLANNED）

采用 `M3DC1ModelSpec`（除非现有命名冲突），与通用 `Mesh2D` **分离**。候选职责（P0 最小、轻量）：

- geometric vertices；geometric edges；edge endpoint order；loops；face-to-loop topology；stable model tags；
- separatrix loop / inner wall loop / outer wall loop / vacuum loop 标签；
- curve representation；model edge segmentation；
- 单 face P0 的 geometric face；
- TXT model Writer 所需的拓扑与曲线数据。

**不得存储**：PUMI/GMI/APF/MDS 运行时句柄；`.smb` 字节数据；C1 physical field；high-order mesh nodes；MPI ownership；adaptation metadata。

约束：P0 只要求 single-region、single-face；多 face 字段最多保留最小可扩展语义，不得开放普通用户任意配置；`Mesh2D.region_ids` **不自动映射**为 geometric face tag，face tag 由 M3DC1 Adapter 按目标专用模型显式分配。

### 7.4 C1 与初始静态网格边界（消费端源码确认）

- 当前直接路径中 `C1TRIDOFNODE = 6` 表示每 mesh vertex 的数值场分量，**不是**六个几何节点。
- 初始 mesh load 后删除已有 field/numbering，仅保留可选 `norm_curv` tag。
- C1 field 在 mesh load **后**由运行时创建；初始 SMB **不需要**预存 C1 physical field。
- 主路径不要求 LinkMesh 提供额外高阶几何节点。
- C1 edge orientation 与法向符号由三角形连接与坐标在**运行时派生**。
- boundary normal/curvature 可由 geometric model 计算；`norm_curv` 当前为可选，非 P0 强制输出。
- adaptation/restart 的 field/tag **不得**升级为初始静态网格要求。
- 限定：12-DOF C1 单元源码存在，但不得据此要求 LinkMesh 初始 SMB 预存 edge DOF；多 face 物理界面处理仍未确认；P0 通过 single-face 避开未确认的跨 face 物理问题。

### 7.5 M4 实现停止条件

在以下事实确认前，**不得擅自完成 M4 实现**：

1. 目标环境 SCOREC/PUMI 版本、commit 或兼容来源（当前**版本未确认**，不得默认 GitHub 最新版）。
2. `makeEmptyMdsMesh` 或等效 API 的准确签名及参数语义（如第三参 matched/partitioned）。
3. `createVertex`、`createEntity`、`ModelEntity` 转换与所有权。
4. geometric classification 的**本地判定与分配规则**（corner→gvtx / boundary→gedge / interior→gface）。
5. `acceptChanges`、`verify`、`writeNative` 的准确调用顺序与必需性。
6. 单进程 residence/remotes/barrier 是否可省略。
7. 二维 triangle orientation 要求。
8. 单进程文件命名与 rank 后缀的实际行为（`foo.smb` 是否展开为 `foo0.smb`、已带 `0` 名是否变 `foo00.smb`）。
9. 唐同学 loader 与生成环境使用兼容的 PUMI/APF/MDS 版本。

蓝图可记录当前源码候选调用链（`createVertex`/`createEntity`/`acceptChanges`/`writeNative`；`makeEmptyMdsMesh(model,2,false)`；analytic model `gmi_add_analytic`+`make_edge_topo`+`make_face_topo`），但必须标注为【实现候选，待目标版本与最小运行验证确认】，不得写成固定函数接口契约。

`smb_writer.py` 在侦察完成、User 确认并更新蓝图前保持 `NotImplementedError`。当前**禁止**凭推测给 `Mesh2D` 增加 C1 导数自由度、高阶边节点、PUMI 句柄、MPI ownership、M3DC1 私有数组或运行时场。

---

## 7A. M4 四级验收（Level 1–4）

| 等级 | 内容（至少） | 责任 |
|---|---|---|
| Level 1 TXT 静态结构 | Writer 字段顺序与 Reader `fscanf` 顺序一致；ID 引用存在；计数一致；坐标有限；loop/edge/face 拓扑合法；TXT model loader 可读取 | LinkMesh 测试与源码对照 |
| Level 2 SMB 轻量加载 | PUMI/APF/MDS 成功加载；mesh dimension=2；vertex/edge/triangle 数与生成报告一致；坐标有限；topology 合法；geometric classification 可读取；verify 或等效校验通过；可输出可视化网格；可视化无明显孔洞/折叠/断裂/边界错误 | 唐同学（主要） |
| Level 3 TXT+SMB 配套 | geometric model 先加载、SMB 后加载；TXT tag 与 SMB classification 相容；geometric vertex/edge/face 能解释对应 mesh entity；两文件形成完整初始网格输入 | 唐同学尽力；轻量工具无法覆盖时由等效消费端补齐 |
| Level 4 完整 M3D-C1 | 正式 M3D-C1 环境加载；后续初始化接受；物理程序接受 | 后续完整求解器对接或 M5/导师验收，**不由轻量 loader 替代** |

状态要求：M4 P0 Writer **至少通过 Level 1+2+3** 才可标记 PASSED；唐同学当前**尚未执行** Level 2/3，不得在蓝图状态写成已通过；验证工具**不是** LinkMesh 运行时依赖。

---

## 8. 里程碑与当前状态

| 里程碑 | 状态 | 要点 |
|---|---|---|
| M1 Reader | PASSED | OFT `GEQDSKEquilibrium` 薄 Adapter；真实 DIII-D 提取通过 |
| M2-0 可行性 | PASSED | OFT `gs_Domain`/`build_mesh` 最小链路验证（M2 前置证据） |
| M2 OFT Adapter | PASSED | 三层接口；真实 DIII-D 972 节点/1872 三角形/3 区域 `{1:633,2:678,3:561}`；PNG 人工检查通过 |
| M2.5 Mesh2D 解耦 | PASSED | `Mesh2D` 唯一定义位于 `src/linkmesh/mesh.py` |
| **M3 core** | **PASSED** | 8 核心数据集 Writer、h5py 回读、MATLAB 核心加载与绘图通过 |
| **M3 complete-11** | **PENDING CORRECTION AND VALIDATION** | `71fe09f` 已有 `outer_boundary` 字段、11 数据集 Writer 与相关测试的实现尝试，但 OFT Adapter 将人工矩形四控制角点错误作为 `outer_boundary`；尚未通过架构、真实 GFile、h5py 与 MATLAB/Octave 完整验收；`outer_boundary` 完整自交验证及测试待补齐 |
| CLI 区域密度参数 | 已实现并验收 | 三个 `dx` 参数；37 项 CLI 专项测试 + 165 项全量回归通过；真实 DIII-D 默认/粗/细网格通过 |
| M4-0A 参考证据获取 | PASSED | M3DC1/SCOREC 参考源码与样例获取 |
| M4-0B 源码/样例索引 | PASSED | 生成端/消费端导航索引建立 |
| M4-0C1 程序入口/model·mesh I/O | PASSED | model 文本↔`.smb` 写读、model→mesh 加载依赖 geometric model |
| M4-0C2 topology 与 classification | CONDITIONALLY PASSED | vertex→edge→loop→face 拓扑；`toModel/gmi_dim/gmi_tag` 分类；多 face≠多物理区域 |
| M4-0C3 C1/边界/多 face 兼容性 | CONDITIONALLY PASSED | C1 6/vertex 数值分量；初始 SMB 不预存 field；OFT/Triangle 条件兼容 |
| M4-0D 综合契约 | PASSED | 数据链、Mesh2D 冻结、M3DC1ModelSpec 候选、输入架构裁决 |
| M4-0D1 PUMI/APF/MDS 最小 API 静态侦察 | CONDITIONALLY PASSED | 内存建网候选链；空 2D mesh；classification 矩阵；版本未确认 |
| M4-0D2 TXT+SMB 验收设计 | PASSED | 双文件契约、责任矩阵、Level 1–4、回传模板 |
| **M4-0E 蓝图固化** | 文档固化完成（本轮） | 输入架构/M3DC1ModelSpec/双文件契约/停止条件/验收写入蓝图与 History |
| M4 model Writer + PUMI Adapter + SMB 实现 | NOT STARTED | 禁止字节流；须先 M3 complete-11 通过、确认目标版本 PUMI API |
| 唐同学 Level 2/3 实际验证 | 尚未执行 | 外部开发验收工具，非运行时依赖 |
| M5 | NOT STARTED | — |

CLI 密度参数真实验收统计（DIII-D）：默认 `0.08/0.10/0.15` → 972 节点/1872 三角形；粗 `0.12/0.16/0.24` → 506 节点/968 三角形；细 `0.05/0.08/0.16` → 1587 节点/3108 三角形；三组 PNG 人工检查通过。

旧路径状态：历史 Python `triangle` Wrapper、其专属测试、旧 CLI 边界构造函数与 Python `triangle` 直接依赖**已删除**；正式网格路径收敛到 OFT/TokaMaker-Triangle。删除过程详见 `History.md`。

`nbcRZ/Rbc/Zbc` 历史证据已由两个样例侦察确认（见第 5 节），生成规则清晰，进入 M3 complete-11 实施范围。

---

## 9. 测试与验收门槛

| 测试文件 | 服务对象 | 状态 |
|---|---|---|
| `tests/test_mesh.py` | Mesh2D 数据模型（含 outer_boundary 集中验证，完整自交检查待补齐） | 通过 |
| `tests/test_oft_adapter.py` | OFT Adapter 三层接口（mock/受控假 Domain） | 通过（退出码 0） |
| `tests/test_hdf5_writer.py` | HDF5 Writer 契约 | AUTHORED（11 数据集测试待 M3 complete-11 真实运行验收） |
| `tests/test_cli.py` | CLI 参数解析/验证/转发（monkeypatch 隔离） | 通过（37 项） |

门槛：单元测试不依赖真实 OFT/GFile；集成与真实验收在 Linux 服务器 OFT 26.6 环境执行。M3 complete-11 修正后需：`outer_boundary` 数据来源改为真实重采样离散点列并补齐完整自交验证及测试；两个真实 GFile 回归；h5py 检查 11 数据集 shape/dtype/点序/闭合/方向/`nbcRZ`；`loadfemmesh_h5.m` 验证不再出现缺三字段 warning；测试证明人工控制角点不能错误代替离散边界。M4 需 Level 1（LinkMesh 测试）+ Level 2/3（唐同学或等效消费端）通过后方可标 PASSED。

许可证边界：`TOKAMAKER/` 下 EQDSK 样例受 LGPL v3.0 约束，未经确认不得复制进 `tests/data/` 或 `examples/`，仅开发期只读集成测试使用。

---

## 10. 变更纪律与待决事项

### 10.1 M4-0 与后续严格实施顺序（本轮不实施源码）

M4-0 子阶段：M4-0A 参考证据获取 → M4-0B 源码/样例索引 → M4-0C1 程序入口/model·mesh I/O → M4-0C2 topology 与 classification → M4-0C3 C1/边界/多 face 兼容性 → M4-0D 综合契约 → M4-0D1 PUMI/APF/MDS 最小 API 静态侦察 → M4-0D2 TXT+SMB 验收设计 → M4-0E 蓝图固化（本轮）。

M4-0E 完成后的严格顺序（**不得改变"M3 complete-11 完整通过后才正式开始 M4 实现"**）：

1. 返回 M3 complete-11；
2. 修正 `71fe09f` 的 `outer_boundary` 数据来源（由人工矩形四控制角点改为进入 Triangle 前真实重采样有序离散点列）；
3. 修改 `Mesh2D`（如需）与 OFT Adapter，保留网格生成前传入生成器的有序 outer boundary 并随 `Mesh2D` 返回；
4. 补齐并验证方向（顺时针）、隐式闭合、有限性、无相邻重复点、稳定顺序、不含 Steiner 点，以及**完整非相邻边自交检查及其测试**；
5. HDF5 Writer 写出完整 11 数据集（直接读 `mesh.outer_boundary`）；
6. 更新 Mesh2D/Adapter/Writer 测试，含"人工控制角点不能代替离散边界"与自交拒绝的测试；
7. 两个真实 GFile 回归；
8. h5py 检查 11 数据集 shape/dtype/点序/闭合/方向/`nbcRZ`；
9. `loadfemmesh_h5.m`（MATLAB/Octave）验证无缺字段 warning；PNG 或等效几何检查；
10. M3 complete-11 标记 PASSED、更新 History；
11. 实现输入配置基础设施（`linkmesh.in` + `--config/--no-config` + `EffectiveConfig`，第 6A 节）；
12. 实现首批 single-region boundary source（`lcfs`/`first_wall`/`array_file`）；
13. 实现 `M3DC1ModelSpec` 与 TXT model Writer（Level 1）；
14. 确认目标版本 PUMI/APF/MDS API 后实现 classified mesh 与 SMB 输出（经官方 API）；
15. 生成候选 TXT + SMB；
16. 完成 Level 1；唐同学完成 Level 2 并尽力 Level 3；
17. M4 满足 Level 1–3 后标记 PASSED；
18. 多 face M3DC1 模式以后另行侦察和授权；
19. 最后进入 M5。

停止条件：OFT Adapter 无法获得或保留网格生成前有序外边界；实现会改变已确认 8/11 数据集契约、区域编号、`Mesh2D` 核心字段或默认网格行为；需暴露 `outer_padding` 或改变 outer boundary 形状；M4 目标版本 SCOREC/PUMI API 未确认；需把待确认 PUMI API 写成固定接口；需把 `.dmg` 升级为 P0 必需；需提前开放 M3DC1 多 face；全量或真实回归失败。发生任一情况须停止并报告，先更新蓝图或取得授权，不留部分实现。

### 10.2 蓝图更新纪律（先更新蓝图再实现）

以下变更必须先更新本文档：新增/删除模块；修改 `GFileData`/`Mesh2D` 字段（含 `outer_boundary` 契约与自交验证要求）；修改区域/边界编号约定；修改 HDF5 数据集契约（含 11 数据集 shape/dtype/1-based/`idxevert` 拓扑/`Rbc/Zbc/nbcRZ` 规则）；确认 `.smb` 或 PUMI/model file 任何细节；将【实现候选】PUMI API 转为固定接口；新增/修改 CLI 参数或 `linkmesh.in` 配置层次；修改 `target/profile/boundary_source` 分层与兼容矩阵；修改 `M3DC1ModelSpec` 职责；修改 OFT API 调用方式或 `openfusiontoolkit` 版本；修改默认区域策略或 outer boundary 形状；将任何【待源码确认】转为【已确认事实】（须直接证据）；将 M3DC1 多 face、C1/高阶要求或 Level 验收状态转为已通过。

### 10.3 当前明确待决事项

- M3 complete-11 尚未通过；`71fe09f` 已有 `Mesh2D.outer_boundary`、11 数据集 Writer 与相关测试的实现尝试，但 OFT Adapter 将人工矩形四控制角点错误作为 `outer_boundary`，处于 PENDING CORRECTION AND VALIDATION，尚未通过架构、真实 GFile、h5py 与 MATLAB/Octave 完整验收。
- `Mesh2D.outer_boundary` 的 OFT Adapter 数据来源需修正为真实重采样离散点列；`__post_init__` 的**完整非相邻边自交检查及其测试**尚未补齐，须在返回 M3 complete-11 时核对并补齐。
- M4 PUMI/APF/MDS 目标版本、精确 API、classification 本地判定规则尚待实现阶段确认；M4 业务代码（TXT model Writer、PUMI Adapter、SMB 输出）尚未开始。
- 唐同学 Level 2/3 实际验证尚未执行。
- 两层输入架构（`linkmesh.in` + `EffectiveConfig`）、`target/profile/boundary_source`、`array_file`/`flux_surface` 提取接口尚未实现。
- outer boundary 形状（矩形/放大 LCFS/D 形/椭圆/包络）待 User 与导师确认。
- `m3dc1 + nested_three_region` 与 M3DC1 多 face 物理区域语义未确认前禁止开放。
- M5 尚未开始。

依赖（核心运行）：`numpy>=1.24.0`、`h5py>=3.8.0`、`matplotlib>=3.7.0`、`openfusiontoolkit==26.6`（不写 `>=`）。PYTHONPATH 铁律：绝不将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境，会遮蔽含 `liboftpy.so` 的正式安装包。
