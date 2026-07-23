# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **2.3**（在 v2.2 基线上固化输入层字段级实施契约。主要变化：M1–M3 已按 User 最新验收归档为 PASSED（M1/M2/M2.5/M3 core/M3 complete-11/M3 完整闭环全部通过，`71fe09f` 数据来源已修正为受控读取 `outer_region._resampled_points`，`Mesh2D.outer_boundary` 完整非相邻边自交验证已补齐并通过，两个真实 GFile、h5py、MATLAB 与几何检查已验收）；第 6A 节由原则性描述升级为字段级接口契约——规划 `src/linkmesh/config.py` 与 `src/linkmesh/readers/boundary_reader.py` 模块落点、`EffectiveConfig` frozen dataclass 字段表、`linkmesh.in` v1 TOML section/键逐项映射与规范示例、新增 CLI 参数表、内建默认值、配置发现与合并算法、`array_file` v1 CSV 契约、single-region 三来源构造契约、字段级兼容矩阵、required fields、输入层四段实施拆分与验收矩阵。本轮只修改蓝图，未修改任何业务源码或测试；输入层源码仍为 PLANNED / NOT IMPLEMENTED；M4 model/SMB 业务实现仍未开始；M4 SCOREC/PUMI 停止条件保持有效）
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
| `src/linkmesh/mesher/oft_adapter.py` | 三层接口：`mesh_from_oft_domain(domain)` 通用 N 区域核心（含 N=1）、`build_oft_domain_from_gfile(gfile_data, plasma_dx, vacuum_dx, outer_dx, ...)` 默认策略层、`generate_mesh(...)` 便利入口；未来新增 single-region Domain 构造策略（见第 6A.11 节）；将 `pts/lc/reg` 规范化为 `Mesh2D`；在锁定的 OFT 26.6 环境中，由策略层受控捕获 outer Region 引用并于 `build_mesh()` 后读取 `outer_region._resampled_points` 得到 `outer_boundary`（版本锁定兼容接口，见第 3.2A 节）。所有 OFT 私有属性依赖集中封装于本模块内 | 解析 TOML；复制 OFT 通用几何/种子/重采样/segment 拼接/方向/全局重编号/Triangle 算法；写死区域数量/名称/类型/ID；无依据再次偏置 0-based 连接表；解析 `_reg_seg_map`/`_resampled_segments`/`Mesh._resampled_points`；调用 `Region.get_resampled_points()` 作为 `outer_boundary` 来源；回退四角/`idxevert`/最终 `pts/lc` 反推/自行重采样；把 OFT 私有依赖泄漏到 `Mesh2D`/Writer/CLI/Plotter；修改 OFT 源码或依赖 `TOKAMAKER/` 快照 |
| `src/linkmesh/writers/hdf5_writer.py` | 接收 `Mesh2D`，按 TRIMEG HDF5 契约写出（见第 5 节） | 修改 `Mesh2D`；写 `region_ids`；转置 `vert/tria`；给 `tria` 加第四列；从 `idxevert` 反推 `Rbc/Zbc`；网格生成逻辑；判断配置来源 |
| `src/linkmesh/writers/smb_writer.py` | M4 占位；侦察与蓝图确认前保持 `NotImplementedError`；未来经 PUMI/APF/MDS 官方 API 输出 | 手写/拼接/修改/逆向 `.smb` 字节流 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()`（支持区域着色、LCFS/第一壁闭合显示） | 修改任何数据对象 |

M4 规划新增模块（PLANNED，本轮不建源码）：M3DC1 目标专用对象 `M3DC1ModelSpec`（第 7 节）、TXT model Writer 与 PUMI/APF/MDS Adapter（第 7 节）。

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

**正式定位（v2.0，v2.1/v2.2/v2.3 保持）**：`Mesh2D` 是 LinkMesh 面向多个下游模拟代码（TRIMEG、M3DC1/PUMI 等）的**统一、持久、求解器无关**中间网格对象。

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
  → 策略层创建 outer Region 并捕获引用
  → domain.build_mesh()（OFT 内部完成重采样、共享边界处理、点合并、全局重编号、segment 方向处理，并回写 region._resampled_points）
  → 受控读取 outer_region._resampled_points（OFT/Triangle 输入前的真实有序离散点列）
  → 删除可能的显式闭合重复末点 + 验证 + 顺时针规范化 + float64 独立副本
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

**已实现并验收的受控依赖**：

- LinkMesh 在锁定的 `openfusiontoolkit==26.6` 环境中，在 OFT Adapter 内、由策略层明确捕获 outer `Region` 对象后，于 `domain.build_mesh()` 完成后受控读取该对象的私有属性 **`outer_region._resampled_points`**，作为 `outer_boundary` 的权威离散点列来源。
- 读取后创建 `float64` **独立副本**，按 `Mesh2D.outer_boundary` 契约验证并规范化（删除显式闭合重复末点、方向规范为顺时针并保持原起点）。
- 已由第二轮 `oft_adapter.py`/`tests/test_oft_adapter.py` 服务器专项测试通过，并经两个真实 GFile 回归验证（DIII-D 与 fixed_boundary，见 `History.md` 第 19 条）。

**允许读取的 OFT 属性（唯一）**：

- 策略层已明确捕获的 `outer_region._resampled_points`。

**禁止读取或解析的 OFT 属性**：

- `domain.mesh._reg_seg_map`
- `domain.mesh._resampled_segments`
- `domain.mesh._resampled_points`（Mesh 级别聚合点列，禁止 LinkMesh 直接解析）

原因：OFT 已在 `Mesh.__init__` 内完成 Region 点列的方向与拼接并回写到 `region._resampled_points`；LinkMesh 只读取该回写结果，不再解释 OFT 私有 segment 语义、不复制 OFT 重采样/点合并/segment 拼接/方向/全局重编号算法，从而把版本耦合范围压到最小。

**接口性质**：该私有依赖是**版本锁定、范围受控、失败即停止**的兼容接口（【版本锁定兼容接口】），**不是**一般稳定公共 API；只服务于获取 `outer_boundary`，不得扩展为 LinkMesh 对 OFT 私有结构的通用依赖。

**捕获与读取时机（固定）**：

1. 策略层创建 outer Region；
2. 策略层**立即**保存该 Region 对象引用（不写死 region ID、不按名称猜测、不遍历私有 map），并在 `build_mesh()` 前保存到局部变量；
3. `domain.build_mesh()` 创建 OFT `Mesh` 并完成实际重采样及 Region 点列回写；
4. `build_mesh()` **完成后**读取 build 前保存的**同一个** outer Region 对象的 `outer_region._resampled_points`（即使 build 期间 domain 上私有属性被替换，也使用 build 前保存的原对象）；
5. 删除可能存在的显式闭合重复末点；
6. 验证 shape、有限性、点数、简单闭环与非相邻边自交；
7. 规范化为顺时针（保持原起点）；
8. 创建独立 `float64` 副本；
9. 写入 `Mesh2D.outer_boundary`；
10. HDF5 Writer 直接映射为 `nbcRZ/Rbc/Zbc`。

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
- 轮廓退化；
- 方向或点序无法规范化；
- 非相邻边自交；
- 无法证明该 Region 是策略层创建的最外边界；
- OFT 内部接口与已核对签名或数据流不一致。

失败时**禁止**回退到：人工矩形四角；`Region.get_resampled_points()`；`idxevert`；最终 `pts/lc` 反推；LinkMesh 自行重采样；静默设置 `outer_boundary=None` 后继续 TRIMEG 输出。对不需要 `outer_boundary` 的目标仍按目标契约处理。

**禁止加入 `Mesh2D` 的数据（P0）**：triangle adjacency（由 triangles 派生）、geometric model handles、PUMI handles、geometric model tags、C1 field、edge orientation、boundary normal、boundary curvature、high-order nodes、MPI ownership。可确定性派生的数据默认由 Adapter、PUMI/MDS 或 M3D-C1 运行时生成。

**只读统计属性**：`n_nodes`、`n_triangles`、`n_boundary_segments`。

---

## 4. 网格与物理约定

- **坐标/单位**：`[R,Z]`，SI（m、T、A）。
- **内存索引**：`triangles` 内部 0-based；目标格式偏置（如 TRIMEG +1）由对应 Writer 在写出阶段完成。`region_id` 与节点索引转换无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- **OFT 输出契约**（已确认）：`pts (np,2) float64`、`lc (nc,3)` 0-based 整数（`0<=lc<N`）、`reg (nc,)` 正整数，与 `domain.region_info` 最终 ID 一一对应。
- **区域编号**：原样保留 OFT `reg`；区域语义只从 `domain.region_info` 名称/类型/最终 ID 获得，不由整数值推断；区域数量由 OFT 当前区域模型决定，不写死；合法单区域（N=1）满足契约。
- **区域校验**（`mesh_from_oft_domain`，在 `build_mesh()` 之后读取最终 `region_info`）：至少一个区域；`reg` 全为有限正整数；`len(reg)==T`；输出 ID 集合与最终 `region_info` 一致；每个区域至少一个三角形；不重编号/排序/压缩/+1。`build_mesh()` 会原地重排区域 ID，绝不能在其之前提取。
- **当前默认 GFile 区域策略**：有有效第一壁 → PLASMA+VACUUM+OUTER（`add_annulus`+`add_rectangle`）；无壁 → PLASMA+OUTER（`add_polygon`+`add_rectangle`）。这是当前 CLI 便利策略，非 Adapter 能力边界。single-region 策略见第 6A.11 节（PLANNED）。
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

两层输入架构（`linkmesh.in` + CLI + `EffectiveConfig`）契约见第 6A 节（PLANNED，未实现）。`outer_padding` 在 v2.3 仍**不暴露**为正式配置或 CLI 字段，保持内部默认策略。自适应细化、全局 `--mesh-size`、计算域选择参数在 v2.3 未在源码暴露。

---

## 6A. 输入架构（两层输入 + EffectiveConfig，字段级契约，PLANNED / NOT IMPLEMENTED）

以下为 User 已批准的字段级正式契约。本轮只写蓝图，不建源码文件、不实现字段。保持轻量边界：不得建设通用配置 DSL、任意 N 区域语言或插件系统。

### 6A.1 模块落点

- `src/linkmesh/config.py`：`EffectiveConfig` 定义 + `linkmesh.in` 读取/校验/合并 + 兼容矩阵/required fields 校验（职责与禁止见第 2 节表）。
- `src/linkmesh/readers/boundary_reader.py`：`array_file` 两列 CSV → `(B,2) float64`（职责与禁止见第 2 节表）。
- `readers/gfile_reader.py`、`mesher/oft_adapter.py`、`cli.py`、`mesh.py`、`writers/*` 现有职责按第 2 节表调整；`cli.py` 不自行合并三套来源，`oft_adapter.py` 不解析 TOML。

### 6A.2 `EffectiveConfig`（frozen dataclass，只读/不可变）

正式规定为 Python `@dataclass(frozen=True)` 或语义等价的不可变对象。字段表：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | `int` | 固定为 1（v1 schema） |
| `config_path` | `Path \| None` | 实际加载配置文件的**绝对路径**；未加载配置时 `None` |
| `target` | `Literal["mesh_only","trimeg","m3dc1"]` | 目标输出族 |
| `profile` | `Literal["single_region","nested_three_region"]` | 区域策略 |
| `boundary_source` | `Literal["lcfs","first_wall","array_file","artificial_outer","flux_surface"]` | 计算域外边界来源 |
| `gfile_path` | `Path \| None` | GFile/EQDSK 绝对路径 |
| `array_file_path` | `Path \| None` | array boundary CSV 绝对路径 |
| `plasma_dx` | `float` | plasma / single-region 目标网格尺度（m） |
| `vacuum_dx` | `float` | vacuum 区目标网格尺度（m） |
| `outer_dx` | `float` | outer 区目标网格尺度（m） |
| `hdf5_path` | `Path \| None` | TRIMEG HDF5 输出绝对路径 |
| `plot_path` | `Path \| None` | 自检 PNG 绝对路径 |
| `model_path` | `Path \| None` | M3DC1 TXT model 绝对路径（M4） |
| `smb_path` | `Path \| None` | PUMI `.smb` 绝对路径（M4） |
| `verbose` | `bool` | 详细日志 |

要求：

1. 所有 `Path` 在进入 `EffectiveConfig` 前转换为**规范化绝对路径**。
2. `config_path` 为实际加载配置文件的绝对路径；未加载配置时 `None`。
3. `EffectiveConfig` **不保存**"值来自 CLI 还是文件"的运行时来源字典。
4. CLI 解析阶段可用临时 sentinel 或 `None` 表示"用户未显式提供"，但该中间状态**不进入**最终对象。
5. **不把 `outer_padding`** 暴露为新的正式配置或 CLI 字段；保持内部默认策略，除非未来另行修改蓝图。
6. **不加入** PUMI 句柄、`Mesh2D`、`GFileData`、NumPy 数组、Writer 实例或 argparse `Namespace`。
7. `flux_surface` 可出现在枚举与错误信息中，但首批实现必须明确报 `NotImplementedError` 或"配置不支持"错误，**不得伪造磁通面**。

### 6A.3 内建默认值

无配置文件、无新增显式 CLI 时，旧 CLI 行为必须保持。默认值：

| 字段 | 默认 |
|---|---|
| `schema_version` | `1` |
| `target` | `"trimeg"` |
| `profile` | `"nested_three_region"` |
| `boundary_source` | `"artificial_outer"` |
| `plasma_dx` | `0.08` |
| `vacuum_dx` | `0.10` |
| `outer_dx` | `0.15` |
| `verbose` | `false` |

路径默认值（经只读核对实时 `cli.py` 写入）：

- `hdf5_path` 默认沿用现有 HDF5 输出规则：实时 `--output` 默认 `mesh.h5`。`target="trimeg"` 默认写 HDF5 到 `mesh.h5`。
- `plot_path` 默认沿用现有 PNG 规则：实时 `--plot` 默认 `None`（不生成 PNG）。
- `model_path` / `smb_path`：**不制造尚未存在的可执行默认路径**。实时 `--smb` 默认为字符串 `mesh.smb`，但 SMB Writer 仍 `NotImplementedError`；因此 `EffectiveConfig` 首批**不**为 M4 目标提供可执行默认输出路径，`m3dc1` target 在 M4 Writer 未实现时明确失败（见第 6A.13 节）。

**输出默认行为迁移张力（已核对，非损失映射，需实现阶段处理）**：实时 `cli.py` 在无 `--no-smb` 时默认同时尝试 HDF5 与 SMB，而 SMB Writer 为 `NotImplementedError`；即旧默认命令实际依赖显式 `--no-smb` 才能只出 HDF5。为保持旧 CLI 行为不变，输入层 I 实现时：默认 `target="trimeg"` 保留现有 `--no-hdf5`/`--no-smb` 开关语义，`smb_path` 默认仍映射 `mesh.smb`，是否实际写 SMB 由目标与开关共同决定；**不在本轮改变旧 CLI 行为、不静默删除 SMB 尝试**。此为记录性说明，非必须停止的冲突。

### 6A.4 `linkmesh.in` v1 TOML schema

- 文件名：`linkmesh.in`；编码：UTF-8；格式：TOML；标准库 `tomllib` 读取。
- 顶层必须有 `schema_version = 1`。
- 允许 section 仅为：`[task]`、`[input]`、`[domain]`、`[mesh]`、`[output]`、`[runtime]`。

逐键映射：

| 位置 | 键 | 映射到 EffectiveConfig | 说明 |
|---|---|---|---|
| 顶层 | `schema_version` | `schema_version` | 必须为 1 |
| `[task]` | `target` | `target` | `mesh_only`/`trimeg`/`m3dc1` |
| `[input]` | `gfile` | `gfile_path` | 相对配置目录解析 |
| `[input]` | `array_file` | `array_file_path` | 相对配置目录解析 |
| `[domain]` | `profile` | `profile` | `single_region`/`nested_three_region` |
| `[domain]` | `boundary_source` | `boundary_source` | 见枚举 |
| `[mesh]` | `plasma_dx` | `plasma_dx` | 有限正数 |
| `[mesh]` | `vacuum_dx` | `vacuum_dx` | 有限正数 |
| `[mesh]` | `outer_dx` | `outer_dx` | 有限正数 |
| `[output]` | `hdf5` | `hdf5_path` | 相对配置目录解析 |
| `[output]` | `plot` | `plot_path` | 相对配置目录解析 |
| `[output]` | `model` | `model_path` | 相对配置目录解析（M4） |
| `[output]` | `smb` | `smb_path` | 相对配置目录解析（M4） |
| `[runtime]` | `verbose` | `verbose` | 布尔 |

规则：

1. 未知顶层键、未知 section、未知 section 内键**立即失败**。
2. 重复键由 TOML 解析器错误处理。
3. 不执行 Python。
4. 不执行 Shell。
5. 不展开环境变量。
6. 不解释 `~` 为主目录；配置路径按普通相对或绝对路径处理，避免隐式 Shell 语义。
7. 配置中的相对路径相对于**配置文件所在目录**。
8. 不允许大型数组直接写入 TOML（边界点列走 `array_file`）。
9. TOML v1 不提供 `null`；可选路径通过**省略键**表示未提供。

规范性最小示例（仅配置示例，不代表这些路径已存在）：

```toml
schema_version = 1

[task]
target = "trimeg"

[input]
gfile = "equilibrium.gfile"

[domain]
profile = "single_region"
boundary_source = "first_wall"

[mesh]
plasma_dx = 0.08

[output]
hdf5 = "mesh.h5"
plot = "mesh.png"

[runtime]
verbose = true
```

### 6A.5 CLI 正式参数（现有 + 规划新增）

保留第 6 节全部现有参数。规划新增（PLANNED）：

| 参数 | 说明 |
|---|---|
| `--config PATH` | 只加载该配置文件；不存在立即失败 |
| `--no-config` | 禁用自动发现；与 `--config` **互斥** |
| `--target {mesh_only,trimeg,m3dc1}` | 覆盖 `target` |
| `--profile {single_region,nested_three_region}` | 覆盖 `profile` |
| `--boundary-source {lcfs,first_wall,array_file,artificial_outer,flux_surface}` | 覆盖 `boundary_source` |
| `--array-file PATH` | array boundary CSV 路径 |

现有 `--no-hdf5` / `--no-smb` 及其他输出开关迁移兼容规则（经只读核对，不猜测）：

- 旧参数**首批继续接受**；
- 旧命令无配置运行必须保持**原行为**；
- 与新 `target` 明确冲突时**立即报错**，不静默选择（如 `target=mesh_only` 却给出 `--output` 强制 HDF5 属实现阶段定义的冲突判定项）；
- **不在本轮删除**任何旧 CLI 参数。

其余规则：`--config` 与 `--no-config` 互斥；只有用户**显式输入**的 CLI 字段覆盖配置文件，argparse 默认值不覆盖配置；CLI 路径相对于**进程当前工作目录**解析。

### 6A.6 配置发现与合并算法（固定）

1. 建立内建默认值（第 6A.3 节）。
2. 解析 CLI，但**保留每个字段是否由用户显式提供**（sentinel/None）。
3. 若有 `--config PATH`，只加载该文件；不存在**立即失败**。
4. 若有 `--no-config`，不自动发现。
5. 两者都没有时，只检查**当前目录**下 `linkmesh.in`。
6. 加载并**严格校验** TOML（schema_version、section、键）。
7. 相对于**配置文件目录**解析 TOML 路径。
8. 按 `内建默认值 < TOML < 显式 CLI` 合并。
9. 相对于**当前工作目录**解析显式 CLI 路径。
10. 构造并**冻结** `EffectiveConfig`（全部 Path 规范化为绝对路径）。
11. 校验 required fields 与兼容矩阵。
12. verbose 模式打印实际配置文件绝对路径；未加载配置时明确打印"未加载配置"或保持现有安静行为（按实时 CLI 风格在实现时固化）。

**禁止**：递归搜索父目录；搜索用户主目录；加载多个配置文件。

### 6A.7 `array_file` v1 契约（严格两列 CSV）

- UTF-8 文本；
- 每个非空数据行恰好两个以英文逗号分隔的字段；
- 第 0 列 R、第 1 列 Z；单位 m；
- 支持普通十进制与科学计数法；
- 允许空白行并忽略；字段首尾空白允许；
- 不允许标题行；不允许注释；不允许第三列；不允许缺失值；不允许 NaN/Inf；
- 读入后 shape 必须为 `(B,2)`；至少 3 个互异点；
- 末尾若精确或在正式窄容差内重复首点，只删除**一个**末尾重复点；
- 最终必须是**单一简单闭环**；不允许相邻重复、零长度边、退化面积或非相邻边自交；
- 若为逆时针，**保持第 0 点**并反转后续点序，规范化为顺时针；
- 返回独立 `float64` 数组。

明确：`array_file` 是"文件 → 内存二维数组"接口；本轮**不批准** Python 用户直接传入 `numpy.ndarray` 的公共 API；大型点列不得内嵌 TOML；**不引入 pandas**。完整简单闭环几何验证委托 `mesh.py` 统一边界验证入口（`_validate_outer_boundary` 或等价内部入口），`boundary_reader.py` 只做文件语法/shape/有限性/基础点列检查。

### 6A.8 boundary source 正式契约

- `lcfs`：使用 GFile/EQDSK 提取的 LCFS，进入 Mesher 前归一化为有序闭合边界点列；允许用于兼容矩阵批准的 target/profile。
- `flux_surface`：使用归一化磁通 `(psi - psi_axis) / (psi_lcfs - psi_axis)`，合法候选范围 `0 < normalized_flux < 1`；必须从平衡磁通提取真实闭合等磁通轮廓；**禁止**通过径向缩放 LCFS 伪造磁面；轮廓提取接口尚未实现，属后续任务；首批实现必须明确报未实现，TRIMEG 首批不因其未完成被阻塞。
- `first_wall`：使用 GFile 第一壁/limiter 轮廓，归一化为有序闭合边界点列；由兼容矩阵决定用途。
- `array_file`：见第 6A.7 节。
- `artificial_outer`：仅用于当前 `nested_three_region` 演示/内部策略；人工矩形控制几何本身不是最终 `outer_boundary`，必须经 OFT 实际重采样得到进入 Triangle 前的有序离散点列（受控读取 `outer_region._resampled_points`，见第 3.2A 节），该离散点列才进入 `Mesh2D.outer_boundary`。

### 6A.9 target/profile/boundary_source 兼容矩阵（字段级）

**已实现并必须回归**：

| 组合 | 状态 |
|---|---|
| `trimeg + nested_three_region + artificial_outer` | 已实现（M1–M3 PASSED），必须回归 |

**输入层首批实现目标**：

| 组合 | 状态 |
|---|---|
| `mesh_only + nested_three_region + artificial_outer` | 输入层首批目标 |
| `mesh_only + single_region + lcfs` | 输入层首批目标 |
| `mesh_only + single_region + first_wall` | 输入层首批目标 |
| `mesh_only + single_region + array_file` | 输入层首批目标 |
| `trimeg + single_region + lcfs` | 输入层首批目标 |
| `trimeg + single_region + first_wall` | 输入层首批目标 |
| `trimeg + single_region + array_file` | 输入层首批目标 |

**规划但当前禁止执行**：

| 组合 | 状态 |
|---|---|
| `single_region + flux_surface`（任意 target） | 真实磁通面提取未实现，首批明确报未实现 |
| `m3dc1 + single_region + lcfs` | 输入层允许表达，须等 M4 Writer 实现后验收 |
| `m3dc1 + single_region + first_wall` | 输入层允许表达，须等 M4 Writer 实现后验收 |
| `m3dc1 + single_region + array_file` | 输入层允许表达，须等 M4 Writer 实现后验收 |

**明确禁止**：

| 组合 | 理由 |
|---|---|
| `m3dc1 + nested_three_region` | 多物理区域与界面语义未确认 |
| `nested_three_region + lcfs` | profile 与 source 不匹配 |
| `nested_three_region + first_wall` | profile 与 source 不匹配 |
| `nested_three_region + array_file` | profile 与 source 不匹配 |
| `single_region + artificial_outer` | single-region 不使用人工外框 |
| 同时提供互相冲突的 `gfile` 与 `array_file`（目标 source 只消费其一时） | 首批严格拒绝多余冲突输入 |

不得把"技术上可构造"写成"已经实现"或"已通过消费端验证"。不得把多 geometric face 直接等同 plasma/vacuum/wall 多物理方程区域。

### 6A.10 required fields

| 条件 | 必须 | 禁止 |
|---|---|---|
| `boundary_source=lcfs` | `gfile_path` | `array_file_path` |
| `boundary_source=first_wall` | `gfile_path`（且第一壁有效） | `array_file_path` |
| `boundary_source=array_file` | `array_file_path` | `gfile_path` |
| `boundary_source=artificial_outer` | `gfile_path` | `array_file_path` |
| `boundary_source=flux_surface` | 首批总是明确报未实现 | 径向缩放 LCFS |
| `target=trimeg` | `hdf5_path` | — |
| `target=mesh_only` | 不强制 HDF5/model/SMB | — |
| `target=m3dc1` | 未来必须 `model_path` 与 `smb_path`；当前因 M4 未实现明确失败 | — |

`first_wall` 第一壁缺失或非法时明确失败。输出路径父目录不存在时的行为**沿用实时 CLI/Writer 既有纪律**；如实时文件没有正式规则，实现前需确定，**不得由本轮猜测**。

### 6A.11 single_region 构造契约（首批）

1. `lcfs`：需要 `gfile_path`；从 `GFileData` 取 LCFS；使用 OFT 单 polygon Domain；该闭环既是唯一计算域边界，也是唯一区域边界。
2. `first_wall`：需要 `gfile_path`；从 `GFileData` 取有效第一壁；缺失或非法明确失败；使用 OFT 单 polygon Domain；**不再额外创建 artificial outer**；该第一壁是最终计算域边界。
3. `array_file`：需要 `array_file_path`；不要求 GFile；由 `boundary_reader.py` 读取并验证；使用 OFT 单 polygon Domain；**不再额外创建 artificial outer**。
4. 三来源均：
   - 使用一个正式 single-region mesh scale；首批映射到 `plasma_dx`，**不新增泛化的 `mesh_size` 参数**；
   - 捕获由 `add_polygon()` 新增的 Region 对象；
   - `build_mesh()` 后读取**同一个** Region 的 `_resampled_points`；
   - 把 OFT 实际离散点列写入 `Mesh2D.outer_boundary`；
   - 继续执行 OFT 26.6 版本锁定与防御性失败（第 3.2A 节）；
   - **不**使用输入控制点直接冒充 OFT 实际离散边界；
   - **不**调用 `Region.get_resampled_points()`；
   - **不**解析 `_reg_seg_map`。
5. **不得**把 `region_ids` 自动当成 M3DC1 face tag。

### 6A.12 输入层实施拆分（源码任务顺序）

后续源码任务必须拆成四段，全部通过后才进入 M4：

- **输入层 I**：实现 `config.py`；`--config/--no-config`；严格 TOML；`EffectiveConfig`；保持当前 `nested_three_region + artificial_outer` 业务路径不变；旧 CLI 回归。
- **输入层 II**：实现 `boundary_reader.py`；`single_region + lcfs`；真实 GFile、OFT、PNG 与 `mesh_only` 回归。
- **输入层 III**：实现 `single_region + first_wall`；验证有效第一壁真实 GFile 不再生成额外 artificial outer；TRIMEG HDF5 与 MATLAB 绘图验收。
- **输入层 IV**：实现 `single_region + array_file`；CSV 合法/非法矩阵；OFT、Mesh2D、HDF5 与 PNG 验收。

### 6A.13 输入层验收矩阵

至少覆盖：

- 无配置文件时旧 CLI 行为不变；
- 自动发现当前目录 `linkmesh.in`；
- `--no-config` 禁止自动发现；
- `--config` 只加载指定文件；
- `--config` 与 `--no-config` 冲突（报错）；
- 配置文件不存在（报错）；
- TOML 语法错误（报错）；
- `schema_version` 缺失、不为 1（报错）；
- 未知 section（报错）；
- 未知键（报错）；
- argparse 默认值不覆盖 TOML；
- 显式 CLI 覆盖 TOML；
- TOML 相对路径基于配置目录；
- CLI 相对路径基于当前工作目录；
- 三个 `dx` 的默认/文件/CLI 优先级；
- 每个 required field；
- 每个非法兼容组合；
- `array_file` 合法 CSV；
- 标题/注释/第三列/缺失值/NaN/Inf/点数不足/自交/退化/重复点失败；
- single_region 三来源均取得 OFT 实际 `_resampled_points`；
- `first_wall` 模式不创建 artificial outer；
- 旧 `nested_three_region + artificial_outer` 的两个真实 GFile 回归；
- `flux_surface` 明确未实现；
- `m3dc1` 在 Writer 未实现时明确失败。

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
| M1 Reader | **PASSED** | OFT `GEQDSKEquilibrium` 薄 Adapter；真实 DIII-D 提取通过 |
| M2-0 可行性 | PASSED | OFT `gs_Domain`/`build_mesh` 最小链路验证（M2 前置证据） |
| M2 OFT Adapter | **PASSED** | 三层接口；真实 DIII-D 972 节点/1872 三角形/3 区域 `{1:633,2:678,3:561}`；PNG 人工检查通过 |
| M2.5 Mesh2D 解耦 | PASSED | `Mesh2D` 唯一定义位于 `src/linkmesh/mesh.py` |
| M3 core | **PASSED** | 8 核心数据集 Writer、h5py 回读、MATLAB 核心加载与绘图通过 |
| M3 complete-11A | 只读接口冲突核对完成 | 参考快照核对：`Region.get_resampled_points()` 存在但非 Triangle 输入来源；Triangle 输入来自 `Mesh._resampled_points`；见 `m3_complete11a_report.md` |
| M3 complete-11B | 文档裁决完成 | 服务器 OFT 26.6 introspection 双重核对；User 批准受控读取 `outer_region._resampled_points`；私有兼容接口、防御性失败、版本升级纪律写入蓝图（第 3.2A 节） |
| **M3 complete-11** | **PASSED** | 三轮源码修正（4eb38d1/7bd5391/cd9f924）；`outer_boundary` 数据来源改为受控读取 `outer_region._resampled_points`；完整非相邻边自交验证补齐；HDF5 完整 11 数据集；三轮联合回归 196 passed；两个真实 GFile、h5py、MATLAB、几何检查通过（见 `History.md` 第 19 条） |
| **M3 完整闭环** | **PASSED** | M1/M2/M3 core/M3 complete-11 全部通过并归档 |
| CLI 区域密度参数 | 已实现并验收 | 三个 `dx` 参数；37 项 CLI 专项测试 + 165 项全量回归通过；真实 DIII-D 默认/粗/细网格通过 |
| M4-0A 参考证据获取 | PASSED | M3DC1/SCOREC 参考源码与样例获取 |
| M4-0B 源码/样例索引 | PASSED | 生成端/消费端导航索引建立 |
| M4-0C1 程序入口/model·mesh I/O | PASSED | model 文本↔`.smb` 写读、model→mesh 加载依赖 geometric model |
| M4-0C2 topology 与 classification | CONDITIONALLY PASSED | vertex→edge→loop→face 拓扑；`toModel/gmi_dim/gmi_tag` 分类；多 face≠多物理区域 |
| M4-0C3 C1/边界/多 face 兼容性 | CONDITIONALLY PASSED | C1 6/vertex 数值分量；初始 SMB 不预存 field；OFT/Triangle 条件兼容 |
| M4-0D 综合契约 | PASSED | 数据链、Mesh2D 冻结、M3DC1ModelSpec 候选、输入架构裁决 |
| M4-0D1 PUMI/APF/MDS 最小 API 静态侦察 | CONDITIONALLY PASSED | 内存建网候选链；空 2D mesh；classification 矩阵；版本未确认 |
| M4-0D2 TXT+SMB 验收设计 | PASSED | 双文件契约、责任矩阵、Level 1–4、回传模板 |
| M4-0E 蓝图固化 | PASSED | 输入架构/M3DC1ModelSpec/双文件契约/停止条件/验收写入蓝图与 History |
| **输入层字段级接口固化（v2.3，本轮）** | **文档完成** | 第 6A 节升级为 `config.py`/`boundary_reader.py` 落点、`EffectiveConfig` 字段表、TOML section/键表、CLI 参数表、默认值、合并算法、`array_file` 契约、single-region 三来源、字段级兼容矩阵、required fields、实施拆分与验收矩阵 |
| 输入层 I（config + EffectiveConfig） | **PLANNED / NOT IMPLEMENTED** | 下一步；保持当前网格业务行为不变 |
| 输入层 II（single_region + lcfs） | PLANNED / NOT IMPLEMENTED | 依赖输入层 I |
| 输入层 III（single_region + first_wall） | PLANNED / NOT IMPLEMENTED | 有效第一壁不再额外创建 artificial outer |
| 输入层 IV（single_region + array_file） | PLANNED / NOT IMPLEMENTED | `boundary_reader.py` + CSV 矩阵 |
| M4 model Writer + PUMI Adapter + SMB 实现 | NOT STARTED | 禁止字节流；须先输入层通过、确认目标版本 PUMI API |
| 唐同学 Level 2/3 实际验证 | 尚未执行 | 外部开发验收工具，非运行时依赖 |
| M5 | NOT STARTED | — |

CLI 密度参数真实验收统计（DIII-D）：默认 `0.08/0.10/0.15` → 972 节点/1872 三角形；粗 `0.12/0.16/0.24` → 506 节点/968 三角形；细 `0.05/0.08/0.16` → 1587 节点/3108 三角形；三组 PNG 人工检查通过。

旧路径状态：历史 Python `triangle` Wrapper、其专属测试、旧 CLI 边界构造函数与 Python `triangle` 直接依赖**已删除**；正式网格路径收敛到 OFT/TokaMaker-Triangle。删除过程详见 `History.md`。

M3 complete-11 的历史阶段（v2.1/v2.2 中曾记为 PENDING CORRECTION AND VALIDATION、`71fe09f` 数据来源待修正、真实 GFile/h5py/MATLAB/PNG 尚未验收）为**此前状态，现已由真实验收关闭**：`71fe09f` 的四角错误已由三轮源码修正纠正为受控读取 `outer_region._resampled_points`，完整自交验证已补齐，两个真实 GFile、h5py、MATLAB 与几何检查已通过（见 `History.md` 第 19 条），M3 complete-11 与 M3 完整闭环均标记 PASSED。

---

## 9. 测试与验收门槛

| 测试文件 | 服务对象 | 状态 |
|---|---|---|
| `tests/test_mesh.py` | Mesh2D 数据模型（含 outer_boundary 完整自交验证） | 通过（服务器专项测试） |
| `tests/test_oft_adapter.py` | OFT Adapter 三层接口 + outer Region 回写读取（mock/受控假 Domain） | 通过（95 passed） |
| `tests/test_hdf5_writer.py` | HDF5 Writer 完整 11 数据集契约 + 自交二次防线 | 通过（60 passed） |
| `tests/test_cli.py` | CLI 参数解析/验证/转发（monkeypatch 隔离） | 通过（37 项） |

三轮联合回归 196 passed（LinkMesh 正式回归范围为根目录 `tests/` 三个授权测试文件；无路径 pytest 曾误收集只读 `TOKAMAKER/` 上游测试，不属于 LinkMesh 验收）。门槛：单元测试不依赖真实 OFT/GFile；集成与真实验收在 Linux 服务器 OFT 26.6 环境执行；M1–M3 已完成真实 GFile、h5py、MATLAB、几何验收（见 `History.md` 第 19 条）。

**输入层（PLANNED）门槛**：输入层 I–IV 各段须通过第 6A.13 节验收矩阵；旧 `nested_three_region + artificial_outer` 两个真实 GFile 必须持续回归；`config.py`/`boundary_reader.py` 单元测试不依赖真实 OFT/GFile；`array_file` 合法/非法 CSV 矩阵覆盖；single-region 三来源真实 GFile/OFT/PNG 验收。M4 需 Level 1（LinkMesh 测试）+ Level 2/3（唐同学或等效消费端）通过后方可标 PASSED。

许可证边界：`TOKAMAKER/` 下 EQDSK 样例受 LGPL v3.0 约束，未经确认不得复制进 `tests/data/` 或 `examples/`，仅开发期只读集成测试使用。

---

## 10. 变更纪律与待决事项

### 10.1 严格实施顺序（本轮不实施源码）

M4-0 子阶段（已完成）：M4-0A → M4-0B → M4-0C1 → M4-0C2 → M4-0C3 → M4-0D → M4-0D1 → M4-0D2 → M4-0E → M3 complete-11A → M3 complete-11B。M3 complete-11 三轮源码修正与真实闭环验收已完成（见 `History.md` 第 19 条）。

当前严格顺序（**不得把本轮输入层文档任务标为输入层源码已实现**）：

1. M3 complete-11 **已完成并归档**（PASSED）。
2. 固化输入层字段接口（**本轮，文档完成**）。
3. 实现配置基础设施（**输入层 I**：`config.py` + `--config/--no-config` + 严格 TOML + `EffectiveConfig`），保持当前网格业务行为不变，旧 CLI 回归。
4. 实现并验收 `single_region + lcfs`（**输入层 II**：含 `boundary_reader.py` 前置或与 IV 协调，真实 GFile/OFT/PNG/mesh_only 回归）。
5. 实现并验收 `single_region + first_wall`（**输入层 III**：有效第一壁不再额外创建 artificial outer，TRIMEG HDF5 与 MATLAB 绘图验收）。
6. 实现并验收 `single_region + array_file`（**输入层 IV**：`boundary_reader.py` + CSV 合法/非法矩阵，OFT/Mesh2D/HDF5/PNG 验收）。
7. 输入层验收完成（四段全部通过第 6A.13 节验收矩阵）。
8. 之后才实现 `M3DC1ModelSpec` 与 TXT model Writer（Level 1）。
9. 确认目标 SCOREC/PUMI 版本与阻塞 API（第 7.5 节）后，实现 classified mesh 与 SMB 输出（经官方 API）。
10. M4 继续执行 Level 1–3 验收；满足后标 PASSED；多 face M3DC1 以后另行侦察和授权。
11. 最后进入 M5。

停止条件：OFT Adapter 无法获得或保留网格生成前有序外边界（含 `outer_region._resampled_points` 缺失/结构变化/非法）；OFT 运行版本不是已核对的 26.6；OFT 内部数据流与已核对签名不一致；实现会改变已确认 11 数据集契约、区域编号、`Mesh2D` 核心字段或默认网格行为；实时 CLI 无法无损映射到默认 `target=trimeg`；需暴露 `outer_padding` 或改变 outer boundary 形状；需解析 `_reg_seg_map`/`_resampled_segments`/`Mesh._resampled_points`；需把 `Region.get_resampled_points()` 升级为正式来源；需批准 Python ndarray 公共边界 API；需提前实现 `flux_surface`；需引入第二网格引擎或 `inputs/` 插件包；M4 目标版本 SCOREC/PUMI API 未确认；需把待确认 PUMI API 写成固定接口；需把 `.dmg` 升级为 P0 必需；需提前开放 M3DC1 多 face；全量或真实回归失败；需修改 History/CONTEXT 或业务源码才能完成蓝图。发生任一情况须停止并报告，先更新蓝图或取得授权，不留部分实现。

### 10.2 蓝图更新纪律（先更新蓝图再实现）

以下变更必须先更新本文档：新增/删除模块（含 `config.py`/`boundary_reader.py`）；修改 `GFileData`/`Mesh2D` 字段（含 `outer_boundary` 契约、自交验证要求与第 3.2A 节私有兼容接口）；修改 `EffectiveConfig` 字段；修改 `linkmesh.in` TOML 键或 section；修改 CLI 参数；修改 `array_file` 语法；修改默认 `target/profile/boundary_source`；修改兼容矩阵或 required fields；增加 Python ndarray 公共 API；暴露 `outer_padding`；修改区域/边界编号约定；修改 HDF5 数据集契约（含 11 数据集 shape/dtype/1-based/`idxevert` 拓扑/`Rbc/Zbc/nbcRZ` 规则）；确认 `.smb` 或 PUMI/model file 任何细节；将【实现候选】PUMI API 转为固定接口；修改 `M3DC1ModelSpec` 职责；修改 OFT API 调用方式或 `openfusiontoolkit` 版本；修改默认区域策略或 outer boundary 形状；将任何【待源码确认】转为【已确认事实】（须直接证据）；将 M3DC1 多 face、C1/高阶要求或 Level 验收状态转为已通过。

**OFT 版本升级纪律（第 3.2A 版本锁定兼容接口专项）**：`openfusiontoolkit==26.6` 是第 3.2A 节私有兼容接口当前**唯一核对版本**。升级 OFT 前必须重新只读核对：`Mesh.__init__()` 是否仍在内部重采样后回写 `region._resampled_points`；`Mesh.get_mesh()` 的 Triangle 输入是否仍来自 `self._resampled_points`；segment 方向与 Region 点列组装语义是否变化；outer Region 引用在 `build_mesh()` 后是否仍有效；Triangle 输入点保留与 Steiner 点隔离行为是否变化。未重新核对前**不得升级依赖版本**；OFT 私有接口变化属于停止条件，必须先更新蓝图再修代码。

### 10.3 当前明确待决事项

- 输入层字段级接口本轮**只固化蓝图**；`config.py`、`boundary_reader.py`、`EffectiveConfig`、`--config/--no-config/--target/--profile/--boundary-source/--array-file`、single-region 三来源、`array_file` CSV 读取均为 **PLANNED / NOT IMPLEMENTED**，尚无源码。
- 现有 `--no-hdf5`/`--no-smb` 与新 `target` 的迁移兼容判定（含默认 `target=trimeg` 与旧默认 SMB 尝试的兼容）在输入层 I 实现阶段确定，不得改变旧 CLI 行为。
- 输出路径父目录不存在时的行为沿用实时 CLI/Writer 既有纪律；实时若无正式规则，实现前需确定，不得由本轮猜测。
- `flux_surface` 真实磁通轮廓提取接口未实现，首批明确报未实现，禁止径向缩放 LCFS 伪造磁面。
- M4 PUMI/APF/MDS 目标版本、精确 API、classification 本地判定规则尚待实现阶段确认；M4 业务代码（TXT model Writer、PUMI Adapter、SMB 输出）尚未开始。
- 唐同学 Level 2/3 实际验证尚未执行。
- outer boundary 形状（矩形/放大 LCFS/D 形/椭圆/包络）待 User 与导师确认。
- `m3dc1 + nested_three_region` 与 M3DC1 多 face 物理区域语义未确认前禁止开放。
- Python ndarray 公共边界 API 未批准；`outer_padding` 未暴露；均须先改蓝图。
- M5 尚未开始。

依赖（核心运行）：`numpy>=1.24.0`、`h5py>=3.8.0`、`matplotlib>=3.7.0`、`openfusiontoolkit==26.6`（不写 `>=`；第 3.2A 节私有兼容接口锁定该版本，升级须重新核对）。PYTHONPATH 铁律：绝不将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境，会遮蔽含 `liboftpy.so` 的正式安装包。
