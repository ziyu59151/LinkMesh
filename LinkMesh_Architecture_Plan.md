# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **2.0**（在 v1.13 已验收基线上的有意结构精简：删除逐版本补丁、长篇日志、教学内容与旧实施提示；将 `Mesh2D` 正式定位为面向多个下游模拟代码的统一、持久、求解器无关中间网格对象；规划新增 `Mesh2D.outer_boundary` 有序外边界几何字段；将 TRIMEG HDF5 契约扩展为完整 11 数据集；区分 `M3 core`（已 PASSED）与 `M3 complete-11`（待实现）；记录 M4 PUMI C/C++ API 候选路线与 C1/高阶待确认项）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION】为已批准正式契约但尚未实现且未通过验收的功能；【P0 禁止】为当前阶段严格禁止引入的功能
- 修改前置条件：任何对本文档接口、字段、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位与范围

LinkMesh 是一个**独立命令行程序（CLI）**，用于打通「等离子体平衡文件 GFile/EQDSK → 二维非结构三角网格 → 目标求解器静态网格文件」的转换链路。

**唯一网格生成底座**：OFT/TokaMaker 封装方式调用的 Triangle（OFT 内部经 `liboft_triangle` 完成）。LinkMesh 不维护第二种网格引擎。

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
| 输出 | TRIMEG HDF5；M3DC1 PUMI `.smb`（M4，经 PUMI API） | 三维输出；手写猜测 `.smb` 二进制字节流 |
| 可视化 | matplotlib 自检 PNG | 交互式/三维渲染 |
| 配置 | 当前 CLI 参数 | 通用插件式任意区域配置系统 |

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
| `src/linkmesh/writers/smb_writer.py` | M4 占位；侦察与蓝图确认前保持 `NotImplementedError` | 手写/猜测 `.smb` 字节流 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()`（支持区域着色、LCFS/第一壁闭合显示） | 修改任何数据对象 |

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

**正式定位（v2.0）**：`Mesh2D` 是 LinkMesh 面向多个下游模拟代码（TRIMEG、M3DC1/PUMI 等）的**统一、持久、求解器无关**中间网格对象。

原则：

- 保存下游共同需要、且在网格生成后**无法可靠反推**的规范几何、拓扑、物理标记与必要分类信息；
- 目标格式的索引、转置、dtype、布局转换由各 Writer 完成；不得把 TRIMEG/M3DC1/PUMI 的文件布局搬进 `Mesh2D` 内存布局；
- 可从 `triangles` 无损、确定性派生的边集合与邻接关系，**默认不重复存储**，除非 M4 直接证据证明必须持久保存；
- 不因追求"最完备"而提前加入未经证据确认的 C1 自由度、高阶节点、PUMI 私有句柄、MPI ownership、M3DC1 私有数组或求解器运行时对象。

**核心字段（来自 OFT `build_mesh()`，内部索引 0-based）**：

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | 节点 `[R,Z]` [m] |
| `triangles` | `(T,3)` | 整数（实测 `int32`） | 三顶点节点索引，**内部 0-based** |
| `region_ids` | `(T,)` | 整数（实测 `int32`） | OFT 最终区域编号，**原样保留**（不重编号/排序/压缩/+1） |

**兼容字段（现存于 `mesh.py`，均安全空数组默认值，不参与 TRIMEG 契约）**：`boundary_segments (0,2) int32`、`boundary_markers (0,) int32`、`node_markers (0,) int32`。这三个字段**与下文 `outer_boundary` 不同义、不同名、语义不同**；不得改名或删除既有字段。

**规划新增字段（PLANNED，本轮不改源码）**：`outer_boundary`

| 属性 | 规定 |
|---|---|
| 类型 / shape / dtype | `np.ndarray` / `(B,2)` / `float64` |
| 列含义 / 单位 | 第 0 列 R，第 1 列 Z / m |
| 语义 | 传入网格生成器的、有序、最外层计算域几何边界点；一条简单闭合轮廓 |
| 闭合 | 末尾**不重复首点**，最后一点与第一点隐式闭合 |
| 方向 | 顺时针 |
| 约束 | 至少 3 个互异有限点；无相邻重复点；无零长度闭合边；P0 只允许一条最外层闭合轮廓 |
| 与 Steiner 点 | **不包含** OFT/Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑外边界节点集合；因生成器插点，`B` 可小于最终 `nvert_ex` |
| 性质 | 求解器无关的计算域几何，**不是**按节点编号升序生成的 `idxevert` 坐标表 |

起点规则：当前无足够证据，不规定固定起点（不强制从最小 R/最大 R/最小 Z 起）。只要求点序相邻正确、方向为顺时针、同一输入与配置产生确定顺序。

**只读统计属性**：`n_nodes`、`n_triangles`、`n_boundary_segments`。

---

## 4. 网格与物理约定

- **坐标/单位**：`[R,Z]`，SI（m、T、A）。
- **内存索引**：`triangles` 内部 0-based；目标格式偏置（如 TRIMEG +1）由对应 Writer 在写出阶段完成。
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
- `Rbc/Zbc` 来自有序 `mesh.outer_boundary`；**禁止**用升序 `idxevert` 反推 `Rbc/Zbc`；`Rbc/Zbc` 不含生成器后插入的 Steiner 边界点。
- `nbcRZ` 不要求等于 `nvert_ex`。
- Writer 全部输入验证（shape/有限性/整数语义/索引范围/重复顶点/面积/非流形）在打开目标文件前完成，且不修改输入 `Mesh2D`。

**两个样例直接证据（User 提供，紧凑归档）**：

| 样例 | Rbc/Zbc | nbcRZ | nvert_ex | 匹配 | 连续点对为拓扑边 | 方向/闭合 |
|---|---|---|---|---|---|---|
| `femmesh_65402_t1_nr16core.h5` | `(112,1)` | 112 | 113 | 112 点全部精确匹配最终 `vert`/`idxevert`（最大距离 0） | 111/112；唯一额外外边界节点位于最后一点→首点的闭合边上，为生成后插入的边界点 | 顺时针、单闭环、末尾不重复首点 |
| `femmesh_65402_t1_nr16nout4edge.h5` | `(175,1)` | 175 | 175 | 175 点全部精确匹配 | 175/175 均为实际拓扑边界边 | 顺时针、单闭环、末尾不重复首点 |

由此确认：`Rbc/Zbc` 是有序边界几何（非升序坐标集合）；`idxevert` 描述最终拓扑外边界节点；`Rbc/Zbc` 不含生成器后插入点；`nbcRZ` 可等于或小于 `nvert_ex`。两样例均未证明固定起点规则，不得写成事实。

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

不在 v2.0 暴露 `outer_padding`、全局 `--mesh-size`、自适应细化或计算域选择参数。`linkmesh.in` 配置文件为会议提出的新需求，尚未设计；其格式/键名/路径解析/未知键/优先级契约留待单独蓝图任务，不在 v2.0 预先设计任意区域插件系统。

---

## 7. M3DC1 / PUMI 待确认契约（M4）

当前事实边界：

- M4 **不手写或猜测** `.smb` 二进制字节流。
- 候选正式路线：调用 SCOREC/PUMI **C/C++ API** 创建网格实体并由 PUMI 保存 `.smb`。
- 需要配套文本 **model file**，字段仍待真实样例与读取程序确认。
- 初始单区域 MVP 线索为 LCFS 内 plasma 网格，尚未成为已批准正式接口（改动前须 User 单独确认并更新蓝图）。
- 唐成曜负责的轻量 load-mesh 程序将作为外部消费验收工具，接口仍待交付。
- M3DC1 的 C1 连续性、高阶单元、边方向、几何模型分类、高阶节点与自由度均为【待源码确认】。

`Mesh2D` 长期方向是保存经证据确认、跨 Writer 需要且不可可靠反推的规范网格语义。只读侦察确认后：若属跨 Writer 规范语义，先更新蓝图与 `Mesh2D`；若只是单个 Writer 可派生的消费细节，留在对应 Adapter/Writer。当前**禁止**凭推测给 `Mesh2D` 增加 C1 导数自由度、高阶边节点、PUMI 句柄、MPI ownership、M3DC1 私有数组或运行时场。

`smb_writer.py` 在侦察完成、User 确认并更新蓝图前保持 `NotImplementedError`。

---

## 8. 里程碑与当前状态

| 里程碑 | 状态 | 要点 |
|---|---|---|
| M1 Reader | PASSED | OFT `GEQDSKEquilibrium` 薄 Adapter；真实 DIII-D 提取通过 |
| M2-0 可行性 | PASSED | OFT `gs_Domain`/`build_mesh` 最小链路验证（M2 前置证据） |
| M2 OFT Adapter | PASSED | 三层接口；真实 DIII-D 972 节点/1872 三角形/3 区域 `{1:633,2:678,3:561}`；PNG 人工检查通过 |
| M2.5 Mesh2D 解耦 | PASSED | `Mesh2D` 唯一定义位于 `src/linkmesh/mesh.py` |
| **M3 core** | **PASSED** | 8 核心数据集 Writer、h5py 回读、MATLAB 核心加载与绘图通过 |
| **M3 complete-11** | **PENDING IMPLEMENTATION** | `outer_boundary` 传递与 `nbcRZ/Rbc/Zbc` 写出尚未实现 |
| CLI 区域密度参数 | 已实现并验收 | 三个 `dx` 参数；37 项 CLI 专项测试 + 165 项全量回归通过；真实 DIII-D 默认/粗/细网格通过 |
| M4 `.smb` | 前置已满足；侦察未开始 | 禁止实现字节流；须先完成 PUMI/model file/C1 只读侦察并更新蓝图 |

CLI 密度参数真实验收统计（DIII-D）：默认 `0.08/0.10/0.15` → 972 节点/1872 三角形；粗 `0.12/0.16/0.24` → 506 节点/968 三角形；细 `0.05/0.08/0.16` → 1587 节点/3108 三角形；三组 PNG 人工检查通过。

旧路径状态：历史 Python `triangle` Wrapper、其专属测试、旧 CLI 边界构造函数与 Python `triangle` 直接依赖**已删除**；正式网格路径收敛到 OFT/TokaMaker-Triangle。删除过程详见 `History.md`。

`nbcRZ/Rbc/Zbc` 历史证据已由两个样例侦察确认（见第 5 节），生成规则清晰，进入 M3 complete-11 实施范围。

---

## 9. 测试与验收门槛

| 测试文件 | 服务对象 | 状态 |
|---|---|---|
| `tests/test_mesh.py` | Mesh2D 数据模型 | 通过 |
| `tests/test_oft_adapter.py` | OFT Adapter 三层接口（mock/受控假 Domain） | 通过（退出码 0） |
| `tests/test_hdf5_writer.py` | HDF5 Writer 契约 | 通过（M3 core） |
| `tests/test_cli.py` | CLI 参数解析/验证/转发（monkeypatch 隔离） | 通过（37 项） |

门槛：单元测试不依赖真实 OFT/GFile；集成与真实验收在 Linux 服务器 OFT 26.6 环境执行。M3 complete-11 实现后需：两个真实 GFile 回归；h5py 检查 11 数据集 shape/dtype/点序/闭合/方向/`nbcRZ`；`loadfemmesh_h5.m` 验证不再出现缺三字段 warning。

许可证边界：`TOKAMAKER/` 下 EQDSK 样例受 LGPL v3.0 约束，未经确认不得复制进 `tests/data/` 或 `examples/`，仅开发期只读集成测试使用。

---

## 10. 变更纪律与待决事项

### 10.1 M3 complete-11 后续实现顺序（本轮不实施源码）

1. 修改 `Mesh2D`，增加并验证 `outer_boundary`；
2. 修改 OFT Adapter，保留网格生成前传入生成器的有序 outer boundary 并随 `Mesh2D` 返回；
3. 验证方向（顺时针）、隐式闭合、有限性、无相邻重复点、稳定顺序、不含 Steiner 点；
4. 修改 HDF5 Writer 写出完整 11 数据集（直接读 `mesh.outer_boundary`）；
5. 更新 Mesh2D / Adapter / Writer 测试；
6. 对两个真实 GFile 回归；
7. h5py 检查 11 数据集 shape/dtype/点序/闭合/方向/`nbcRZ`；
8. `loadfemmesh_h5.m` 验证无缺字段 warning；
9. 通过后再更新 History。

停止条件：OFT Adapter 无法获得或保留网格生成前有序外边界；实现会改变已确认 8 数据集契约、区域编号、`Mesh2D` 核心字段或默认网格行为；需暴露 `outer_padding` 或改变 outer boundary 形状；全量或真实回归失败。发生任一情况须停止并报告，先更新蓝图或取得授权，不留部分实现。

### 10.2 蓝图更新纪律（先更新蓝图再实现）

以下变更必须先更新本文档：新增/删除模块；修改 `GFileData`/`Mesh2D` 字段（含 `outer_boundary` 契约）；修改区域/边界编号约定；修改 HDF5 数据集契约（含 11 数据集 shape/dtype/1-based/`idxevert` 拓扑/`Rbc/Zbc/nbcRZ` 规则）；确认 `.smb` 或 PUMI/model file 任何细节；新增 CLI 参数（含 `linkmesh.in` 配置或计算域选择）；修改 OFT API 调用方式或 `openfusiontoolkit` 版本；修改默认区域策略或 outer boundary 形状；将任何【待源码确认】转为【已确认事实】（须直接证据）；将 M3DC1 单区域支持或 C1/高阶要求转为已确认。

### 10.3 当前明确待决事项

- `Mesh2D.outer_boundary` 尚未实施（PLANNED）。
- TRIMEG 完整 11 数据集 Writer 尚未实施（M3 complete-11 PENDING）。
- M4 PUMI C/C++ API、model file、C1/高阶只读侦察尚未开始。
- outer boundary 形状（矩形/放大 LCFS/D 形/椭圆/包络）待 User 与导师确认。
- `linkmesh.in` 配置文件需求尚未设计。
- 单区域 MVP 是否作为 M4 起点须 User 单独确认。

依赖（核心运行）：`numpy>=1.24.0`、`h5py>=3.8.0`、`matplotlib>=3.7.0`、`openfusiontoolkit==26.6`（不写 `>=`）。PYTHONPATH 铁律：绝不将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境，会遮蔽含 `liboftpy.so` 的正式安装包。
