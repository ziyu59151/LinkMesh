# LinkMesh M4-0D 证据综合、数据职责分层与输入架构裁决草案

> 本报告综合 M3 与 M4-0C1/C2/C3 只读侦察成果，形成供 User 验收的架构裁决草案，为 M4-0E 修改 `LinkMesh_Architecture_Plan.md` 提供有限、可执行依据。本轮不修改蓝图、不修改业务源码、不实现任何功能、不修复 `71fe09f`。

---

## 1. 文档定位与裁决范围

- **性质**：综合与裁决草案，非新一轮大范围源码侦察。
- **依据**：M4-0C1/C2/C3 已确认事实 + 实时 `src/linkmesh/mesh.py`/`oft_adapter.py`/`hdf5_writer.py` + 当前蓝图 v2.0。
- **产物**：仅 `m4_0d_report.md`。
- **不裁决**：物理主程序方程分区、`.smb` 字节布局、未确认 PUMI API 语义、SCOREC/core 内部实现。
- **裁决输出**：数据链、Mesh2D 字段冻结、`M3DC1ModelSpec` 候选、初始 `.smb` 最小契约、两层输入架构、`outer_boundary`/`Rbc/Zbc` 修复契约、M4-0E 蓝图修改清单、严格实施顺序、User 裁决清单。

---

## 2. 当前里程碑

| 里程碑 | 状态 |
|---|---|
| M1 / M2 / M2.5 / M3 core | PASSED |
| M3 complete-11 | 暂停（`71fe09f` 因 `outer_boundary` 数据来源错误未验收）|
| M4-0A / M4-0B / M4-0C1 | PASSED |
| M4-0C2 / M4-0C3 | CONDITIONALLY PASSED |
| **M4-0D（本轮）** | 进行中 |
| M4-0E 蓝图修改 | 未开始 |
| M4 model + `.smb` 实现 | 未开始 |
| M5 | 未开始 |

---

## 3. 直接证据摘要

### M4-0C1【已确认：双向证据】

- M3D-C1 model 文本由 `save_model()`/`save_multi_rgn_model()` 写、`load_model()` 读。
- `.smb` 由 `apf::Mesh2::writeNative()` 保存、`pumi_mesh_load()`/`apf::loadMdsMesh()` 加载。
- 创建/加载 MDS 网格均需相容 geometric model 对象。

### M4-0C1【待确认：不阻塞 P0】

- `.dmg` 是否为正式运行时必需输入（当前更强证据是 model `.txt` analytic model → 加载 `.smb`）。

### M4-0C2【已确认：双向证据 / 生成端证据】

- geometric model 层次：vertex→edge→loop→face。
- model 文本 Writer↔Reader 核心字段逐项对应。
- mesh entity 经 `toModel()`/`gmi_dim()`/`gmi_tag()` 取 classification。
- model tag / mesh local ID / mesh global ID 三套独立编号。

### M4-0C2【待确认：不阻塞 P0】

- 多 geometric face ≠ 已确认的多物理方程区域。
- M3D-C1 model 需比 TRIMEG 单条 `outer_boundary` 更丰富的 edge/loop/face 拓扑。

### M4-0C3【已确认：消费端 / 运行时初始化证据】

- 每 vertex 6 个 C1 自由度是数值场分量，非高阶几何节点。
- mesh load 后删除已有 field/numbering，仅保留可选 `norm_curv` tag。
- C1 field 在 mesh load 后由 `createPackedField()` 创建。
- 初始静态 `.smb` 不需预存 C1 field；主路径不需额外高阶 mesh vertex/edge node。
- edge orientation 与法向符号可从三角形连接及坐标运行时派生。
- boundary normal/curvature 可由 geometric model 计算；`norm_curv` 为可选缓存。
- 当前网格库未见多 face 界面 DOF duplication/jump/mortar/Lagrange 处理。

### M4-0C3 裁决

- OFT/Triangle 与 M3D-C1 初始静态网格：**条件兼容，无网格层硬阻塞**。

---

## 4. SCOREC/PUMI 架构位置

必须准确表达，避免"两个连续独立网格生成器"的误解：

- **SCOREC**：技术栈总称（科学计算研究中心工具集）。
- **APF / GMI / MDS / PCU**：SCOREC 组件——APF（场与网格抽象）、GMI（几何模型接口）、MDS（网格数据结构）、PCU（并行通信）。
- **PUMI**：M3D-C1 使用的接口/封装层，`pumi_mesh_load`/`pumi_geom_load` 等封装 APF/GMI/MDS。
- **Triangle**：LinkMesh **唯一**网格生成底座（经 OFT/TokaMaker 的 `liboft_triangle`）。
- **职责边界**：SCOREC/PUMI 负责 **geometric model、classification、APF/MDS 网格容器、native `.smb` 输出**，**不是第二个三角剖分引擎**。LinkMesh 不引入第二网格引擎。

---

## 5. 完整数据链

| # | 层 | 输入 | 输出 | 所有权 | 求解器无关 | 持久化 | 可从上层确定性派生 | 证据等级 |
|---|---|---|---|---|---|---|---|---|
| 1 | GFile/外部边界 | EQDSK/点列文件 | 原始平衡/边界 | 外部 | 是 | 外部文件 | — | 【已确认：双向证据】（M1）|
| 2 | Boundary/Domain 配置 | GFile + 用户参数 | 计算域/边界选择 + dx | LinkMesh | 是 | 否（内存）| 否（含用户决策）| 【架构裁决建议】 |
| 3 | OFT/Triangle | 有序边界 + 区域策略 + dx | pts/lc/reg | OFT | 是 | 否 | 否（Triangle 生成）| 【已确认：双向证据】（M2）|
| 4 | Mesh2D | pts/lc/reg + outer_boundary | 统一网格对象 | LinkMesh | 是 | 内存 | 是（薄适配）| 【已确认：消费端证据】（M2.5）|
| 5 | M3DC1ModelSpec（候选）| Mesh2D + Boundary 配置 | loop/face/edge 分段+标签 | LinkMesh Adapter | 否（M3DC1 专用）| 内存 | 部分（需边界分段规则）| 【架构裁决建议】 |
| 6 | M3DC1/PUMI Adapter | M3DC1ModelSpec + Mesh2D | GMI model + classified mesh 调用 | LinkMesh | 否 | 内存 | 否（调用 PUMI）| 【待确认：阻塞 M4 实现】 |
| 7 | GMI geometric model | ModelSpec 拓扑 | analytic model 对象 | PUMI/GMI | 否 | model `.txt` | 是（由 ModelSpec）| 【已确认：双向证据】（C1/C2）|
| 8 | APF/MDS classified mesh | 线性三角网格 + model | classified MDS mesh | PUMI/MDS | 否 | `.smb` | 是（由 mesh+model）| 【待确认：阻塞 M4 实现】 |
| 9 | model 文本 + `.smb` | GMI model + MDS mesh | `.txt` + `.smb` | LinkMesh 输出 | 否 | 是 | 是 | 【已确认：双向证据】（C1）|
| 10 | m3dc1_scorec | `.txt` + `.smb` | 加载的 model + mesh | 消费端 | 否 | — | — | 【已确认：消费端证据】（C1/C3）|
| 11 | M3D-C1 运行时 C1 field | 加载后 mesh | 6/vertex C1 field | 消费端运行时 | 否 | 运行时 | 是（`createPackedField`）| 【已确认：运行时初始化证据】（C3）|

- **关键**：第 5–8 层是 M4 新增实现区；第 6、8 层的确切 PUMI API 链为**阻塞 M4 实现的待确认项**。
- **Triangle 唯一底座**：第 3 层是唯一剖分；第 7–8 层不重新剖分，只做几何模型 + classification + 容器化 + 序列化。

---

## 6. 数据职责分层表

| 层 | 承载内容 | 依据 |
|---|---|---|
| 通用 `Mesh2D` | 线性 vertices、triangles、region_ids、boundary_segments、boundary_markers、outer_boundary | 跨 Writer 求解器无关几何/拓扑 |
| M3DC1ModelSpec（候选）| loop 有序性、face↔loop、edge 分段、edge 方向（model 拓扑用）、语义标签、per-loop/face mesh-size | 仅 M3D-C1、不可可靠反推、有 C1/C2 消费证据 |
| PUMI/MDS | mesh edges、triangle adjacency、classification 关联、`.smb` 容器 | 由 mesh topology + model 派生 |
| M3D-C1 加载后运行时 | C1 field(6/vertex)、edge orientation、boundary normal/curvature（缺 `norm_curv` 时）、transfer metadata | 运行时创建/派生 |

---

## 7. Mesh2D 字段裁决

核对实时 `src/linkmesh/mesh.py`（含 `outer_boundary` 已实现且带 `__post_init__` 集中验证）与蓝图 v2.0。

| 字段 | 当前已有 | TRIMEG 消费 | M3D-C1 消费 | 跨 Writer | 可确定性派生 | 建议进入 Mesh2D | 触发蓝图字段修改 |
|---|---|---|---|---|---|---|---|
| nodes | 是 | 是 | 是 | 是 | — | 是（保留）| 否 |
| triangles | 是 | 是 | 是 | 是 | — | 是（保留）| 否 |
| region_ids | 是 | 否（不写 HDF5）| 待确认（≠face tag）| 是 | 否 | 是（保留）| 否 |
| boundary_segments | 是（空默认）| 否 | Adapter 起点 | 是 | 部分 | 是（保留兼容）| 否 |
| boundary_markers | 是（空默认）| 否 | Adapter 起点 | 是 | 部分 | 是（保留兼容）| 否 |
| node_markers | 是（空默认）| 否 | 否 | 是 | 部分 | 是（保留兼容）| 否 |
| outer_boundary | 是（可选 None）| 是（Rbc/Zbc/nbcRZ）| 可作单 loop 输入 | 是 | 否（生成前几何）| 是（保留，必选性见 §15）| 是（正式定义/必选性）|
| triangle adjacency | 否 | 否 | PUMI 需要 | 否 | 是（由 triangles）| 否（留 Adapter/PUMI）| 否 |
| geometric model tags | 否 | 否 | 是（但由 Adapter 生成）| 否 | 否（Adapter 分配）| 否 | 否 |
| edge orientation | 否 | 否 | 运行时派生 | 否 | 是 | 否 | 否 |
| boundary normal | 否 | 否 | 可选/加载后算 | 否 | 是 | 否 | 否 |
| boundary curvature | 否 | 否 | 可选/加载后算 | 否 | 是 | 否 | 否 |
| C1 field | 否 | 否 | 加载后创建 | 否 | 是（运行时）| 否 | 否 |
| high-order nodes | 否 | 否 | 否 | 否 | 不需要 | 否 | 否 |
| MPI ownership | 否 | 否 | 运行时/分区 | 否 | 运行时 | 否 | 否 |

### 裁决原则与冲突核对

- **不因 M3D-C1 需要就加入通用 `Mesh2D`**：edge orientation/normal/curvature/C1 field/high-order/MPI ownership 一律不进 `Mesh2D`。
- **mesh edges/adjacency** 由 triangles 派生，留 Adapter/PUMI。
- **实时代码 vs 报告一致性**：实时 `mesh.py` 已含 `outer_boundary`（可选、float64、(B,2)、顺时针、隐式闭合、集中验证），与本报告一致，**无冲突**；`node_markers` 存在于实时代码，蓝图 v2.0 亦列为兼容字段，**无冲突**。
- **不修改代码**：本轮仅核对，未改 `mesh.py`。

---

## 8. M3DC1ModelSpec 候选

名称为候选，未获批准。定位：轻量、仅 M3D-C1、承载不可从 `Mesh2D` 可靠反推的 model 拓扑与语义。

| 承载项 | 直接消费证据 | 能否从 Boundary 配置+Mesh2D 派生 | 必须持久 | 仅 M3D-C1 | 进入正式结构 |
|---|---|---|---|---|---|
| geometric vertices | 【已确认：双向证据】(C2) | 部分（边界角点）| 内存 | 是 | 建议是 |
| geometric edges | 【已确认：双向证据】(C2) | 部分（需分段规则）| 内存 | 是 | 建议是 |
| edge endpoint order | 【已确认：消费端证据】(C2) | 是（由有序边界）| 内存 | 是 | 建议是 |
| loops | 【已确认：双向证据】(C2) | 部分（需环组织）| 内存 | 是 | 建议是 |
| face↔loop topology | 【已确认：生成端证据】(C2) | 否（需区域策略）| 内存 | 是 | 建议是 |
| model tags | 【已确认：消费端证据】(C2) | 否（Adapter 分配）| model `.txt` | 是 | 建议是 |
| separatrix/inner/outer/vacuum 标签 | 【已确认：生成端证据】(C2) | 否（语义决策）| model `.txt` | 是 | 建议是 |
| model edge segmentation | 【已确认：生成端证据】(C2) | 否（分段规则）| 内存 | 是 | 建议是 |
| curve representation | 【已确认：生成端证据】(C2) | 是（Adapter 从点列拟合）| model `.txt` | 是 | 建议是（Adapter 内部）|
| per-loop/per-face mesh-size | 【已确认：生成端证据】(C2) | 是（配置）| 内存 | 是 | 建议是 |
| model 文本输出路径 | 【架构裁决建议】 | 是（配置/CLI）| 配置 | 是 | 建议是 |

### P0 轻量边界

- 不建通用 geometric-model 框架；不建任意 N 区域插件系统。
- 不引入 PUMI 句柄到 `Mesh2D` 或 `M3DC1ModelSpec`（句柄属 Adapter 运行时）。
- 不为未知未来目标提前抽象。
- **裁决建议**：规划 `M3DC1ModelSpec`（或等效目标专用对象）承载上表内容，**与 `Mesh2D` 分离**；是否采用需 User 裁决（见 §21）。

---

## 9. 初始 `.smb` 最小契约

| 已确认（不阻塞）| 待确认 | 禁止猜测 |
|---|---|---|
| 线性 mesh vertices【消费端】 | PUMI 从内存创建 2D 网格的准确函数链【阻塞 M4】 | `.smb` 字节布局 |
| mesh triangles【消费端】 | model entity 创建 + mesh entity classification 的准确 API【阻塞 M4】 | 手写二进制 |
| APF/MDS 可加载拓扑【双向】 | `acceptChanges()`/`verify()` 等调用顺序【阻塞 M4】 | C1 field 序列化 |
| 与 model 相容的 classification【消费端】 | 单进程最小 `.smb` 文件名约定【阻塞 M4】 | MPI 分区格式 |
| 不需预存 C1 physical field【消费端】 | group size/plane/rank 与分区文件最小要求【阻塞 M4】 | 未确认 PUMI API |
| 不需额外高阶几何节点【消费端】 | model `.txt` + `.smb` 验收加载命令【阻塞 M4】 | — |
| 不需独立预存 C1 edge orientation【消费端】 | `.dmg` 是否需作正式运行输入【不阻塞 P0】 | — |
| `norm_curv` 当前可选【消费端】 | SCOREC/PUMI 版本或兼容提交【阻塞 M4】 | — |

- **阻塞判定**：上表"待确认（阻塞 M4）"各项**必须在编码前**由 M4-0D1/D2 侦察确认。C3 未发现 C1 阻塞**不等于** M4 已可编码——PUMI 内存建模/classification/`writeNative` 的确切 API 与调用顺序仍为硬缺口。

---

## 10. C1 与边界数据结论

- **C1 自由度**：6/vertex 数值场分量，运行时 `createPackedField` 创建，初始 `.smb` 不含【已确认：运行时初始化证据】。
- **高阶节点**：不需要；线性三角形 + ReducedQuintic 数值基【已确认：消费端证据】。
- **edge orientation / 法向符号**：运行时由三角形连接 + 坐标派生；`Mesh2D`/`.smb` 不预存【已确认：消费端证据】。
- **boundary normal/curvature**：`norm_curv` 可选缓存，缺失则由 geometric model 计算；LinkMesh 不强制写入【已确认：消费端证据】。
- **边界识别**：经 geometric classification（`gmi_dim/gmi_tag`），非独立边界 field【已确认：消费端证据】。
- **裁决**：LinkMesh 初始 `.smb` 只需 **线性网格 + classification（+可选 norm_curv）**；C1/orientation/normal/curvature **不进 Mesh2D**。

---

## 11. 多 face 与物理层待确认项

### 网格层已确认

- 多 geometric face、model classification、共形共享 mesh entities【已确认：消费端证据】。
- 当前未见初始 C1 特殊预挂数据要求【已确认：消费端证据】。

### 物理层待确认

- plasma/vacuum/wall 是否对应不同 field/控制方程【待确认：需物理主程序】。
- 是否存在 jump/mortar/Lagrange/interface DOF duplication【待确认：需物理主程序】。
- separatrix 在具体任务的物理角色【待确认：需物理主程序】。

### 阻塞裁决

- **P0 首个 M3DC1 闭环采用 `single_region` 单 face**：上述物理层问题**不阻塞**该最小闭环（单 face 无跨 face 界面）。
- **若开放 `nested_three_region` 给 M3DC1**：物理层问题**必须先确认**。
- **禁止**通过输入 schema 提前开放未经验证的多物理区域模式。

---

## 12. 两层输入架构

规划但**不实现**：

- `linkmesh.in`：保存完整任务（TOML，`schema_version = 1`）。
- CLI：只覆盖用户显式输入字段。
- **优先级**：程序默认值 < `linkmesh.in` < 显式 CLI（形成 EffectiveConfig）。

### 候选分层

| 层 | 内容 | 说明 |
|---|---|---|
| target | `mesh_only` / `trimeg` / `m3dc1` | 决定输出与 Writer |
| domain profile | `single_region` / `nested_three_region` | 决定区域策略 |
| boundary source | `lcfs`/`flux_surface`/`first_wall`/`array_file`/`artificial_outer` | 决定计算域外边界来源 |
| mesh resolution | `plasma_dx`/`vacuum_dx`/`outer_dx`（现有）+ per-loop/face（M3DC1）| 网格尺度 |
| output | `output`(HDF5)/`smb`/`model_txt`/`plot` 路径 | 输出文件 |
| runtime | `verbose`/`no_hdf5`/`no_smb` 等 | 运行开关 |

- **EffectiveConfig**：合并三来源后的只读有效配置对象（候选），CLI 与配置文件解析后产出，供后续层消费。

---

## 13. boundary source 契约

| source | 规划 | 证据等级 |
|---|---|---|
| `lcfs` | 现有 OFT LCFS 提取；有序离散外边界 | 【已确认：双向证据】(M2) |
| `flux_surface` | 归一化磁通 `ψ_n=(ψ-ψ_axis)/(ψ_lcfs-ψ_axis)`，`0<ψ_n<1`；从平衡磁通提取真实闭合等磁通轮廓；**禁止径向缩放 LCFS 伪造磁面**；提取接口需单独侦察 | 【架构裁决建议】+【待确认：不阻塞 P0】 |
| `first_wall` | 现有 GFile limiter 轮廓 | 【已确认：消费端证据】(M1) |
| `array_file` | `(B,2)` R/Z，单位 m，有限、无相邻重复、非退化、简单闭环、末尾不重复首点；首版两列 CSV 文本；大型点列**不内嵌 TOML** | 【架构裁决建议】 |
| `artificial_outer` | 仅当前 `nested_three_region` 演示；人工矩形包络 | 【已确认：生成端证据】(M2) |

- **归一化几何契约**：所有 source 最终归一化为 `Mesh2D.outer_boundary`（有序、顺时针、隐式闭合）——但**是否允许**由 target/profile 兼容矩阵决定（§14）。

---

## 14. target/profile/boundary_source 兼容矩阵

| 组合 | 状态 |
|---|---|
| `mesh_only + nested_three_region + artificial_outer` | 已确认可执行 |
| `trimeg + single_region + lcfs` | 架构候选 |
| `trimeg + single_region + flux_surface` | 架构候选（依赖 `flux_surface` 提取实现）|
| `trimeg + single_region + first_wall` | 架构候选 |
| `trimeg + single_region + array_file` | 架构候选 |
| `m3dc1 + single_region + lcfs` | 架构候选，待消费端验证 |
| `m3dc1 + single_region + flux_surface` | 架构候选，待消费端验证 |
| `m3dc1 + single_region + first_wall` | 架构候选，待消费端验证 |
| `m3dc1 + single_region + array_file` | 架构候选，待消费端验证 |
| `m3dc1 + nested_three_region` | 当前禁止（多物理区域语义未验证）|

- **不得**把"技术上可构造单 loop 单 face"写成"M3D-C1 正式物理任务已确认"。
- **不得**把多 geometric face 直接等同 plasma/vacuum/wall 多物理方程区域。

---

## 15. TRIMEG `outer_boundary` 与 `Rbc/Zbc`

核对实时 `mesh.py`（`outer_boundary` 已实现）、`oft_adapter.py`（`_make_clockwise_rectangle_boundary` 在 build_mesh 前捕获、附加 `_linkmesh_outer_boundary`、注入 Mesh2D）、`hdf5_writer.py`（Rbc/Zbc/nbcRZ 直读 outer_boundary）、`test_hdf5_writer.py`/`test_mesh.py`/`test_oft_adapter.py`。

### M4-0E 应写入蓝图的精确定义

- `outer_boundary` = 当前 Mesh2D 计算域**进入 Triangle 前**的有序离散外边界。
- **不是**人工矩形四控制角点（`71fe09f` 错误固定四角，即此问题）。
- **不是**按节点编号排序的 `idxevert`。
- **不含** Triangle 后续插入的全部 boundary Steiner points。
- **不永久绑定** LCFS/first wall/artificial outer。
- 可由 target/profile 允许的 `lcfs/flux_surface/first_wall/array_file/artificial_outer` 归一化产生。
- `Rbc = outer_boundary[:,0]`；`Zbc = outer_boundary[:,1]`；`nbcRZ = len(outer_boundary)`。
- 不要求 `nbcRZ == nvert_ex`；Writer 不从 `idxevert` 反推。
- `71fe09f` 当前实现尝试**未验收**。

### 必须裁决的蓝图问题

1. **必填/可选**：建议 `outer_boundary` 为 **target 相关必选**——`trimeg` target 必填，`mesh_only`/`m3dc1` 可选（None 合法）。当前实时代码为可选 None，与该建议一致。**需 User 裁决**。
2. **目标不需要时是否仍要求 Mesher 提供**：建议不强制；仅 `trimeg` 路径在 Writer 前校验非 None。
3. **是否复制输入数组**：**是**。实时 `mesh.py::_validate_outer_boundary` 经 `np.asarray(..., float64)`，Adapter `_extract_prebuild_outer_boundary` 用 `np.array(..., copy=True)` 独立副本——保证所有权，建议蓝图明文化。
4. **验证分层**：几何有效性（有限值/点数/闭合/方向/相邻重复/退化）在 **`Mesh2D.__post_init__` 集中验证**（实时已实现）；`trimeg` 必填性在 **HDF5 Writer 打开文件前**校验（实时已实现）。建议蓝图确认此双层。
5. **真实点列捕获**：OFT 重采样后、`build_mesh()` 调用前捕获——实时 `oft_adapter.py` 在构造 domain 时由 LinkMesh 亲手算矩形四角并附加为私有属性；**`71fe09f` 的错误在于把该人工矩形当作最终 outer_boundary**。正确修复需捕获**实际传入生成器的有序边界点列**（当前 boundary source 归一化后的点列），而非人工包络角点。
6. **返回 M3 complete-11 必补测试**：11 数据集 shape/dtype；`nbcRZ` 值；`Rbc/Zbc` 来自 outer_boundary 非 idxevert；点序/闭合/方向；Steiner 点不进入；真实 GFile 回归；MATLAB/Octave 消费无缺字段 warning。

---

## 16. TRIMEG 与 M3DC1 隔离

| 维度 | TRIMEG | M3DC1 |
|---|---|---|
| 目标计算域 | 单连续域 | 单 face（P0）/ 多 face（待验证）|
| 外边界对象 | 单条有序 `outer_boundary` | loop/edge 分段拓扑 |
| geometric model | 无（HDF5 自包含）| GMI analytic model（`.txt`）|
| region/face 语义 | region_ids 不写 HDF5 | face↔loop + 语义标签 |
| Writer 输入 | Mesh2D | Mesh2D + M3DC1ModelSpec |
| 索引转换 | 0-based→1-based（+1）| model tag / MDS local / global 独立 |
| C1 数据 | 无 | 运行时创建（不进输出）|
| 输出文件 | `.h5` | `.txt` + `.smb` |
| 加载验收 | `loadfemmesh_h5.m` | `m3dc1_scorec` model+mesh 加载 |

- **隔离原则**：TRIMEG Writer 只做 HDF5 格式映射；M3DC1 Adapter 负责 model topology + classification；M3DC1 的 C1/orientation/multi-face 细节**不污染** TRIMEG Writer；TRIMEG 单条 `outer_boundary` **不替代** M3DC1 edge/loop/face 拓扑；二者共享同一基础 `Mesh2D`，目标专用结构可不同。

---

## 17. 阻塞项与非阻塞项

### 阻塞 M4 实现【待确认：阻塞 M4 实现】

1. PUMI 内存创建 2D 网格的准确函数链。
2. model entity 创建 + mesh entity classification 的准确 API 与调用顺序（含 `acceptChanges`/`verify`）。
3. 单进程最小 `.smb` 文件名 / group / plane / rank 最小要求。
4. model `.txt` + `.smb` 的 `m3dc1_scorec` 验收加载命令。
5. SCOREC/PUMI 版本或兼容提交。

### 不阻塞 P0【待确认：不阻塞 P0】

- `.dmg` 是否正式运行输入（当前 analytic `.txt` 路径证据更强）。
- 多 face 物理方程分区（P0 用 single_region 规避）。
- `flux_surface` 提取接口细节（首批可先支持 lcfs/first_wall/array_file）。
- `norm_curv` 离散 vs 解析精度契约。

---

## 18. 最小后续侦察任务

从 C1/C2/C3 未确认项中，仅筛选**真正阻塞 M4** 的最小集合，最多两个窄范围任务。

### M4-0D1：PUMI 内存建模、classification、writeNative 最小 API 侦察

1. **问题**：如何从内存 `nodes/triangles` + geometric model 创建 classified MDS 2D 网格并 `writeNative` 出 `.smb`？
2. **证据缺口**：`createMdsMesh`/`createVertex`/`createEntity`/`setPoint`/`toModel`/`acceptChanges`/`writeNative` 的确切签名与顺序（当前仅见调用点，未见最小自建流程）。
3. **最小文件/API 来源**：`[m3dc1_scorec] src/m3dc1_mesh.cc`（`m3dc1_receiveVertices/Edges/Faces` 内 `createVertex/createEntity/setResidence/acceptChanges` 已出现，可作最小模板）；如仍不足，申请**明确版本**的 SCOREC/core 单个头 `apfMDS.h` 或 `apfMesh2.h`。
4. **是否需明确版本 SCOREC/core**：是（先确认消费端 README 版本，再申请单文件）。
5. **可否编译后最小验证程序确认**：可（M4-0D1 输出一个最小 build 计划，但本轮不编译）。
6. **停止条件**：调用进入未授权 core 且无明确版本；只有声明无实现。
7. **验收输出**：一页 API 调用链 + 调用顺序 + 单文件申请清单。

### M4-0D2：单进程 model.txt + `.smb` 被 m3dc1_scorec 加载的最小验收设计

1. **问题**：单进程下 `m3dc1_model_load(model.txt)` + `m3dc1_mesh_load(.smb)` 的最小成功加载命令与前置条件？
2. **证据缺口**：分区文件名约定（`base<rank>.ext`）、group_size=1 时行为、model 与 mesh 相容性校验点。
3. **最小文件/API 来源**：已读 `[m3dc1_scorec] api/m3dc1_scorec.cc`（`m3dc1_mesh_load` 分区名逻辑）+ `src/m3dc1_mesh.cc`；证据基本充分，主要缺**可运行验收命令**。
4. **是否需明确版本 SCOREC/core**：否（消费端 API 已授权）。
5. **可否编译后最小验证程序确认**：可（需消费端可执行，属实现阶段）。
6. **停止条件**：需运行程序才能最终确认——设计阶段只产出命令与前置清单，不运行。
7. **验收输出**：单进程验收命令草案 + 前置文件清单 + 预期成功判据。

> 若 User 认为 §17 阻塞项可在实现阶段边做边验，可将 M4-0D1/D2 合并为实现前置步骤，不重复申请大范围源码。

---

## 19. M4-0E 蓝图修改清单

本轮**不改蓝图**，仅列清单。

| # | 蓝图章节 | 要写入的正式定义 | 证据等级 | 需 User 裁决 | 触发源码修改 | 后续验收测试 |
|---|---|---|---|---|---|---|
| 1 | 新增 M4-0 里程碑章 | M4-0A..0E 侦察/裁决序列与状态 | 【架构裁决建议】 | 否 | 否 | 无 |
| 2 | 新增 输入架构章 | 两层输入（linkmesh.in TOML + CLI），优先级默认<文件<CLI | 【架构裁决建议】 | 是 | 是（未来）| 配置解析单测 |
| 3 | 输入架构章 | EffectiveConfig 只读合并对象 | 【架构裁决建议】 | 是 | 是（未来）| 合并优先级单测 |
| 4 | 输入架构章 | target/profile/boundary_source 分层定义 | 【架构裁决建议】 | 是 | 是（未来）| 兼容矩阵单测 |
| 5 | boundary source 章 | `flux_surface` 归一化磁通定义 + 禁止缩放 LCFS | 【架构裁决建议】+【待确认：不阻塞】 | 是 | 是（未来）| 提取实现后回归 |
| 6 | boundary source 章 | `array_file` (B,2) CSV 契约 | 【架构裁决建议】 | 是 | 是（未来）| 读取/校验单测 |
| 7 | §3.2 Mesh2D | `outer_boundary` 正式定义 + 必选性（target 相关）+ 副本所有权 + 双层验证 | 【已确认：消费端证据】+【架构裁决建议】 | 是 | 是（M3 complete-11）| 11 数据集/回归 |
| 8 | §5 TRIMEG 契约 | `Rbc/Zbc/nbcRZ` 来源=outer_boundary，非 idxevert，非人工四角 | 【已确认：双向证据】 | 否 | 是（修复 71fe09f）| h5py+MATLAB+GFile |
| 9 | 新增 M3DC1 章 | `M3DC1ModelSpec` 候选对象职责 | 【架构裁决建议】 | 是 | 是（未来）| Adapter 单测 |
| 10 | 新增 M3DC1 章 | model 文本 + `.smb` 输出契约 + 初始 `.smb` 最小要求 | 【已确认：双向证据】+【待确认：阻塞】 | 是 | 是（未来）| 消费端加载验收 |
| 11 | 新增 M3DC1 章 | C1 初始网格边界：不预存 C1/orientation/normal/high-order | 【已确认：消费端证据】 | 否 | 否 | 无 |
| 12 | §10 变更纪律 | M4 实现停止条件（PUMI API 缺口/版本未确认/物理分区未验证）| 【待确认：阻塞 M4】 | 否 | 否 | 无 |
| 13 | §10.1 | 返回 M3 complete-11 的顺序（蓝图固化后先修 outer_boundary/Rbc/Zbc）| 【架构裁决建议】 | 否 | 是（顺序约束）| 无 |
| 14 | §8 里程碑表 | M4-0C1/C2/C3/D 状态更新 | 【已确认】 | 否 | 否 | 无 |

---

## 20. 严格实施顺序

User 验收本报告后按以下顺序，**不得改变"M3 complete-11 完整通过后才正式开始 M4 实现"**：

1. User 验收 M4-0D。
2. 若存在阻塞 API 缺口，先完成 M4-0D1/D2。
3. M4-0E 只修改蓝图（`LinkMesh_Architecture_Plan.md`）。
4. User 验收并提交蓝图。
5. 返回 M3 complete-11。
6. 修复 `outer_boundary` 与 `Rbc/Zbc`（含 `71fe09f` 纠正）。
7. 运行 HDF5 11 数据集、h5py、MATLAB/Octave、真实 GFile 验收。
8. M3 complete-11 标记 PASSED。
9. 实现输入配置基础设施（linkmesh.in + CLI + EffectiveConfig）。
10. 实现 single_region boundary source。
11. 实现 M3DC1 model Adapter。
12. 通过正式 SCOREC/PUMI API 创建并保存 `.smb`。
13. 使用消费端完成 model + `.smb` 加载验收。
14. 再评估多 face M3DC1 模式。
15. 最后进入 M5。

---

## 21. User 必须裁决的问题

1. 是否采用 TOML `linkmesh.in` 作为完整任务配置。
2. 是否自动发现当前目录的 `linkmesh.in`。
3. 是否采用 `target/profile/boundary_source` 三分层。
4. 是否采用 `single_region` 与 `nested_three_region` 两个首版 profile。
5. 是否采用 `M3DC1ModelSpec` 或等效目标专用对象。
6. `outer_boundary` 是否作为 `Mesh2D` **必填**字段（建议：trimeg 必填、其他可选）。
7. TRIMEG 首批允许哪些 boundary source（建议：lcfs/first_wall/array_file 先行，flux_surface 待提取实现）。
8. M3DC1 P0 是否只开放 `single_region` 单 face。
9. `.dmg` 是否延后到进一步证据确认（建议：延后，先走 analytic `.txt`）。
10. 是否先完成 PUMI 最小 API 侦察（M4-0D1）再改蓝图，还是在蓝图中保留明确阻塞项。

---

## 22. 完成声明

- 本轮只修改 `m4_0d_report.md`。
- 未修改 `LinkMesh_Architecture_Plan.md`、`History.md`、`CONTEXT.md`、业务源码或测试。
- 未修改老师提供的参考源码和索引。
- 未创建除 `m4_0d_report.md` 外的任何文件。
- 未编译或运行任何程序。
- 未读取或解析 `.smb`/`.dmg`/`.smd`/`.sms`/VTK/对象/库/可执行等二进制格式。
- 未实现配置、CLI、HDF5、model Writer、PUMI 或 `.smb`。
- 未修改 `Mesh2D`。
- 未修复提交 `71fe09f`。
- TRIMEG `Rbc/Zbc` 修复仍保留在 M4-0E 蓝图验收后的 M3 complete-11 阶段。
