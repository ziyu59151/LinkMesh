# LinkMesh M3D-C1 多区域 PUMI 输入契约最终报告

## 1. 调查边界

本文综合以下既有字段级证据，形成下一轮蓝图修订可采用的实施级候选结论：

- `docs/linkmesh/m3dc1_multi_region_model_topology_evidence.md`
- `docs/linkmesh/m3dc1_multi_region_pumi_api_evidence.md`
- 当前 LinkMesh `M3DC1ModelSpec`、TXT Writer、SMB Writer 和 native helper
- `LinkMesh_Architecture_Plan.md` 的当前正式边界

本文只覆盖：

```text
N-region Mesh2D
  + RegionPlan
  + regions map
  → multi-face M3DC1ModelSpec
  → analytic model TXT
  → LinkMesh exchange
  → native helper
  → SCOREC/PUMI acceptChanges()
  → verify()
  → writeNative()
  → 非空 rank-0 SMB
  → 配套 TXT+SMB 交付
```

本文不调查：

- SMB、SMS、SMD 或 DMG 的二进制或内部格式；
- M3D-C1 loader；
- M3D-C1 加载、初始化、时间推进、稳定性或物理结果；
- 第二剖分引擎、三维网格、并行分区或动态自适应；
- 在 `Mesh2D` 中保存 PUMI、GMI、APF 或 MDS 私有对象。

职责边界：

| 责任方 | 验收范围 |
|---|---|
| LinkMesh | 构造多区域 ModelSpec、写 TXT、写 exchange、调用 helper、完成 `acceptChanges()`/`verify()`/`writeNative()`、确认非空 rank-0 SMB、交付配套 TXT+SMB |
| 同门/消费侧 | M3D-C1 加载、初始化、时间推进、稳定性和物理结果 |

`writeNative()` 成功只证明目标 SCOREC/PUMI 写出非空 native 文件，不证明 M3D-C1 已加载或消费。证据见 `native/linkmesh_scorec_helper/main.cc:1059-1090`，以及 `docs/linkmesh/m3dc1_multi_region_pumi_api_evidence.md` 第 17、19 节。

## 2. 证据等级

本文严格区分：

1. **原始源码或头文件直接事实**：由当前 LinkMesh 源码、目标 SCOREC/PUMI 2.2.9 头文件或教程生成端源码直接确认。
2. **教程案例事实**：由教程 `input` 与 `diiid.txt` 的对应记录确认，只证明该案例。
3. **当前 LinkMesh 实现事实**：说明现有 single-face contract 和实现限制。
4. **实施裁决**：基于直接事实作出的 LinkMesh 设计选择，必须先进入蓝图，再允许编码。
5. **待确认事项**：现有证据不足，不得提升为格式或 API 事实。

两个证据报告中的“设计建议”“修改建议”仍是建议；本文引用其背后的原始文件和行号，不把建议本身伪装为直接事实。

## 3. 当前 Single-face 基线

当前正式链只支持：

- 一个 `Mesh2D.region_id`；
- 一个 geometric loop；
- 一个 geometric face；
- face 引用唯一 loop；
- 全部 triangles 分类到唯一 face；
- special loop tags 固定为 `(-1, inner_wall_loop, -1, -1)`；
- exchange schema version 为 1；
- helper 仅创建 `geometric_faces.front()`。

ModelSpec 的直接限制：

- `GeometricFace` 强制只含一个 loop：`src/linkmesh/m3dc1_model.py:271-292`
- model 强制一个 loop、一个 face：`src/linkmesh/m3dc1_model.py:363-383`
- 唯一 loop 必须覆盖全部 edges：`src/linkmesh/m3dc1_model.py:430-455`
- 唯一 face 必须引用唯一 loop：`src/linkmesh/m3dc1_model.py:456-470`
- special loop 语义写死：`src/linkmesh/m3dc1_model.py:471-489`
- builder 只读取 `Mesh2D.outer_boundary`：`src/linkmesh/m3dc1_model.py:513-570`

SMB Writer 和 helper 的直接限制：

- Python 要求 single-region：`src/linkmesh/writers/smb_writer.py:117-145`
- Python 只读取唯一 loop/face：`src/linkmesh/writers/smb_writer.py:244-259`
- helper 要求 `GL=1`、`GF=1`：`native/linkmesh_scorec_helper/main.cc:438-447`
- helper 只验证唯一 loop/face：`native/linkmesh_scorec_helper/main.cc:500-526`
- helper 只创建一个 face：`native/linkmesh_scorec_helper/main.cc:827-854`
- helper 要求全部 triangles 属于唯一 face：`native/linkmesh_scorec_helper/main.cc:636-652`

以上是当前实现约束，不是 TXT 字段布局或 exchange record 布局天然只能表达一个 face 的证据。

## 4. 教程三 Face 拓扑

教程案例实际定义：

- 3 个 loops；
- 3 个 faces；
- face 1 引用 loop 1；
- face 2 引用 loops 1、2；
- face 3 引用 loops 2、3。

对应记录：

```text
faceBdry 1 1 0.04
faceBdry 2 1 2 0.04
faceBdry 2 2 3 0.1
```

其字段级含义分别为：

| 记录 | 拓扑含义 |
|---|---|
| `faceBdry 1 1 0.04` | 一个 face，以 loop 1 为唯一边界；`0.04` 是生成侧 node spacing |
| `faceBdry 2 1 2 0.04` | 一个 face，同时引用 loop 1 和 loop 2，表示两闭环之间的区域 |
| `faceBdry 2 2 3 0.1` | 一个 face，同时引用 loop 2 和 loop 3，表示两闭环之间的区域 |

TXT face records 分别为 `1 1 1`、`2 2 1 2`、`3 2 2 3`。证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:19-24`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:1`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:14-17`

教程证明相邻 faces 共享同一个 loop tag：

- face 1 与 face 2 共享 loop 1；
- face 2 与 face 3 共享 loop 2；
- loop tag 对应唯一一组有序 geometric edges，因而相邻 faces 也共享同一组 geometric edges。

解析器按 face 的 loop tags 展开对应 loop edges，证据见：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:344-357`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:260-319`

教程中的 plasma、wall、vacuum 名称来自案例语境，不是 face tag 自带的物理语义。

## 5. RegionPlan、Curves 和 Mesh2D 到 ModelSpec 的输入契约

### 5.1 明确裁决：`Mesh2D` 单独不足

`Mesh2D` 只提供：

- 全局 nodes；
- 全局 triangles；
- 每个 triangle 的 OFT final `region_id`；
- 最外层 `outer_boundary`。

它不提供：

- 每条原始输入曲线的有序点；
- `curve_id`；
- parent/children 包含树；
- 内部共享界面的原始几何；
- `curve_id -> region_id`；
- `curve_id -> loop_tag`；
- `region_id -> face_tag`。

直接证据：

- `src/linkmesh/mesh.py:127-139`
- `src/linkmesh/regions.py:45-65`
- `src/linkmesh/regions.py:70-80`

因此，多区域 builder 的最小输入应为：

```text
mesh: Mesh2D
plan: RegionPlan
region_map: Sequence[RegionMapEntry]
```

候选签名：

```text
build_multi_face_model_spec(
    mesh: Mesh2D,
    plan: RegionPlan,
    region_map: Sequence[RegionMapEntry],
) -> M3DC1ModelSpec
```

这是实施裁决，不是当前公开接口。

### 5.2 输入对象职责

| 输入 | 提供内容 | 不负责 |
|---|---|---|
| `Mesh2D` | 全局节点、三角形、逐 triangle Region ID | 不保存 PUMI 对象，不提供内部 analytic geometry |
| `RegionPlan` | 每条 curve 的坐标、`curve_id`、parent/children | 不把 technical role 解释为物理类型 |
| `RegionMapEntry` | `curve_id` 与 OFT final `region_id` 的已确认对应 | `physical_label` 和 color 不驱动 topology |
| builder | 分配 model tags、构造 loops/faces、生成显式映射 | 不重新剖分，不猜测物理语义 |

`physical_label` 是可编辑 metadata；OFT technical role 是 OFT 建域兼容输入。二者均不得自动决定 face、face tag 或 classification。直接证据见：

- `src/linkmesh/regions.py:45-80`
- `src/linkmesh/regions.py:491-496`

## 6. Region ID 到 Face Tag 映射

### 6.1 明确裁决：Region ID 不直接作为 face tag

`Mesh2D.region_ids` 原样保存 OFT final IDs，不重编号、不排序、不压缩、不执行 `+1`。证据：

- `src/linkmesh/mesh.py:27`
- `src/linkmesh/mesh.py:99`
- `src/linkmesh/regions.py:338-373`

ModelSpec 当前要求各维 model tags 按记录顺序连续为 `1..N`。证据：

- `src/linkmesh/m3dc1_model.py:52-60`
- `src/linkmesh/m3dc1_model.py:398-417`

因此禁止：

```text
face_tag = region_id
face_tag = region_id + 1
```

### 6.2 明确裁决：必须显式生成映射

builder 必须生成并验证：

```text
region_id_to_face_tag: dict[int, int]
curve_id_to_loop_tag: dict[int, int]
```

候选确定性规则：

- `curve_id_to_loop_tag`：按 `curve_id` 升序分配连续 `1..C`；
- `region_id_to_face_tag`：按对应 `curve_id` 升序分配连续 `1..R`；
- 两个映射均一对一并完整覆盖；
- mesh 中 `region_id` 集合必须与 regions map 完全一致；
- 每个 triangle 通过 `region_id_to_face_tag` 得到 `(2, face_tag)`；
- 映射不依据 Region ID 数值大小、颜色、`physical_label` 或 technical role。

是否把两个映射作为 ModelSpec 的持久字段仍待蓝图裁决。最低实现可以由 builder 返回不可变构建结果对象，或由调用链显式传递映射；不得在 Writer 中重新独立编号。

## 7. Boundary Loops、共享 Loop 和 Geometric Edge

每条输入 curve 只创建一次：

```text
curve
  → 一组 geometric vertices
  → 一组 directed geometric edges
  → 一个 geometric loop
```

一个 Region 对应 curve `C`，其 face boundary loops 为：

```text
direct_child_loops(C) + own_loop(C)
```

其中 direct children 按 `curve_id` 升序，own loop 放在最后，作为 LinkMesh 的确定性序列化规则。

该规则适用于：

| 树形 | face boundary loops |
|---|---|
| leaf | `[own_loop]` |
| 严格嵌套中间层 | `[direct_child_loop, own_loop]` |
| sibling 的 parent | `[child_loop_1, child_loop_2, ..., own_loop]` |
| mixed tree | 每个 Region 独立使用直接 children，不包含孙代 loop |

不得把全部 descendants 都加入当前 face，因为孙代边界不是该 Region 的直接边界。

一个内部 loop 被恰好两个相邻 faces 引用；root 的 outer loop 只被 root face 引用。不得为相邻 Region 复制坐标相同但 tag 不同的 loops 或 edges。

教程共享证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:15-17`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:352-357`

待确认：face 中 child loops 与 own loop 的顺序是否具有目标格式 orientation 语义。当前只能把上述顺序定义为 LinkMesh 确定性输出约定。

## 8. Triangle、Mesh Edge 和 Vertex Classification

Python Writer 继续是 classification 的唯一责任层。helper 只验证和应用 records，不根据坐标、Region 名称或邻接关系猜测 classification。

### 8.1 Triangles

对每个 triangle：

```text
mesh.region_ids[triangle_index]
  → region_id_to_face_tag
  → (dimension=2, face_tag)
```

要求：

- Region ID 是正整数且属于映射；
- 不执行 `+1`；
- 每个 face 至少有一个 triangle；
- triangle classification 数量严格等于 `T`。

当前 single-face Writer 将全部 triangles 固定为唯一 face，证据见：

- `src/linkmesh/writers/smb_writer.py:453-456`

helper 已按每条 triangle record 的 `(dimension, tag)` 调用 `findModelEntity()`，证据见：

- `native/linkmesh_scorec_helper/main.cc:1033-1057`

### 8.2 Mesh Edges

从全局 triangles 构造一次唯一、规范化、字典序 mesh edge table：

- incidence 1：计算域外边界 edge；
- incidence 2 且两侧 triangles 属于不同 faces：Region interface edge，分类到对应 geometric edge；
- incidence 2 且两侧 triangles 属于同一 face：分类到该 face；
- incidence 不是 1 或 2：拒绝为 non-manifold。

Region interface 必须能唯一对应一条输入 curve 的 geometric loop/edge chain。无法由现有 curve identity 和 mesh topology 无歧义对应时必须停止，不能使用最近距离、投影或容差吸附猜测。

当前 edge table 和 incidence 逻辑见：

- `src/linkmesh/writers/smb_writer.py:147-178`
- `src/linkmesh/writers/smb_writer.py:377-452`

### 8.3 Mesh Vertices

分类规则：

- geometric corner node：`(0, geometric_vertex_tag)`；
- geometric edge 上的非 corner node：`(1, geometric_edge_tag)`；
- face 内部 node：`(2, face_tag)`；
- 多条 Region interfaces 相交的 node 只有在 model topology 中存在对应唯一 geometric vertex 时才能分类；
- 无法唯一分类时停止。

当前 single-face 路径用坐标精确匹配 geometric corners，证据见：

- `src/linkmesh/writers/smb_writer.py:293-329`
- `src/linkmesh/writers/smb_writer.py:331-364`

多区域路径能否继续仅靠逐分量精确坐标匹配所有内部 curve corners，必须由真实 OFT 网格验证。在证据不足时不得降级为最近距离猜测。

## 9. 全局索引与 Entity 唯一性

硬性规则：

- mesh node index：全局 0-based；
- triangle connectivity：全局 0-based；
- mesh edge endpoints：全局 0-based，且 `node0 < node1`；
- Region ID：离散业务标签，不是数组下标，不执行 `+1`；
- model tag：显式对象标识，不是 vector/array 下标；
- geometric vertex/edge/loop/face tags 分维度确定性分配；
- PUMI 不重新剖分。

helper 必须：

- 每个全局 node 只调用一次 `createVertex()`；
- 每条唯一 mesh edge 只调用一次 `createEntity(EDGE, ...)`；
- 每个全局 triangle 只调用一次 `createEntity(TRIANGLE, ...)`；
- 相邻 Region 共享同一 mesh vertex、mesh edge 和 geometric interface；
- 不按 Region 重建或复制 APF/MDS mesh。

直接证据：

- `native/linkmesh_scorec_helper/main.cc:919-950`
- `native/linkmesh_scorec_helper/main.cc:952-984`
- `native/linkmesh_scorec_helper/main.cc:986-1057`

## 10. ModelSpec 最小扩展

### 10.1 当前表达能力裁决

当前字段容器在类型层面已经可以保存：

- 多个 vertices；
- 多个 edges；
- 多个 loops；
- 多个 faces；
- 一个 loop 的多个 edge tags；
- 一个 face 的多个 loop tags。

证据：

- `src/linkmesh/m3dc1_model.py:236-292`
- `src/linkmesh/m3dc1_model.py:301-312`

但当前 validation 写死 single-loop/single-face。因此明确裁决是：

> 当前 ModelSpec 的数据形状原则上足以承载 sibling 和 mixed tree，但当前 validated contract 不足以表达它们。

### 10.2 最小校验扩展

后续蓝图应批准：

- `len(loops) >= 1`；
- `len(faces) >= 1`；
- 每个 face 至少引用一个 loop；
- face 内 loop tags 唯一且全部存在；
- 每个 loop 至少包含满足当前 polygon 表达所需的有序 edges；
- loop 内 edge tags 唯一且全部存在；
- 每个 loop 有向连续并闭合；
- 每条 geometric edge 被一个 loop 引用；
- 每个 loop 被一个或两个 faces 引用；
- 被两个 faces 引用的 loop 表示内部共享界面；
- 被一个 face 引用的 loop 必须是计算域 outer loop；
- 超过两个 faces 引用同一 loop 时拒绝；
- tags 分维度连续、正整数、1-based；
- special loop tags 为 `-1` 或引用已声明 loop。

应删除的 single-face invariant：

- 全局 `GE == GV`；
- 唯一 loop 覆盖全部 edges；
- 唯一 face 引用唯一 loop；
- special loop 固定为 `(-1, unique_loop, -1, -1)`。

待确认：

- 一般 N-region 情况下四个 special loop tags 的业务赋值来源；
- `numLoops == numFaces` 是否为目标路径硬约束；
- periodic single-edge B-spline 是否需要进入本轮范围。

本轮最小多区域实现应继续使用每条 curve 的 linear polygon edges，不扩大到新的曲线类型。

## 11. TXT Writer 最小扩展

当前 TXT Writer 已：

- 遍历 `spec.loops`；
- 按 loop edge 顺序写 vertices；
- 按 loop edge 顺序写 edges；
- 遍历 `spec.faces`；
- 写 `face_tag loop_count loop_tags...`。

证据：

- `src/linkmesh/writers/m3dc1_model_writer.py:45-68`
- `src/linkmesh/writers/m3dc1_model_writer.py:68-109`
- `src/linkmesh/writers/m3dc1_model_writer.py:111-118`

因此 Writer 的字段布局无需新增 record。最小修改集中于：

1. 接受通过新多 face validation 的 ModelSpec；
2. 确保共享 loop 只在 loop 段定义一次；
3. 多个 faces 通过相同 loop tag 引用同一 loop；
4. 保持确定性 tag 和记录顺序；
5. single-face serialization 字节内容保持不变。

TXT 字段顺序的直接证据：

- header：`external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:237-243`
- loop/vertex/edge：同文件 `:247-319`
- face 段：同文件 `:331-357`

## 12. Exchange Schema v1/v2 裁决

### 12.1 布局事实

当前 wire layout 已天然包含：

- `GL` 和 `GF`；
- 多个 loop records；
- 多个 face records；
- 每个 face 的 loop tag 列表；
- 每个 triangle 的独立 classification。

字段顺序和类型见：

- `src/linkmesh/writers/smb_writer.py:576-677`
- `native/linkmesh_scorec_helper/main.cc:189-361`

因此多 face 不缺少必要引用字段。

### 12.2 明确裁决：升级为 schema v2

虽然无需增加字段，但 schema v1 已被代码和蓝图定义为 single-loop/single-face。为避免同一 version 隐式改变合法输入集合，采用：

- single-region：继续写 schema v1；
- multi-region：写 schema v2；
- helper：同时接受 v1 和 v2；
- v1：继续执行现有严格 invariants；
- v2：执行 multi-face invariants。

v2 与 v1 使用相同字段布局，仅改变 `schema_version` 和语义约束：

```text
magic[8]
schema_version:u32 = 2
endian_marker:u32
N,T,E,GV,GE,GL,GF:u64
special_loop_tags[4]:i32
output_path_length:u64
output_path_bytes
nodes[N]
triangles[T]
geometric_vertices[GV]
geometric_edges[GE]
geometric_loops[GL]
geometric_faces[GF]
vertex_classifications[N]
mesh_edges[E]
triangle_classifications[T]
EOF
```

路径编码继续使用 Python `os.fsencode()` 产生的文件系统 bytes，不应错误宣称 schema 强制 UTF-8。证据：

- `src/linkmesh/writers/smb_writer.py:592-603`
- `native/linkmesh_scorec_helper/main.cc:226-247`

v2 不新增 Region ID，因为 helper 不应理解 OFT Region 语义；Python Writer 在写 exchange 前已将 Region ID 映射为 model face tag。

## 13. Helper 多 Face 修改

最小修改：

1. reader 接受 version 1 和 2，records 布局不变；
2. v1 保留全部旧校验；
3. v2 允许 `GL>=1`、`GF>=1`；
4. 建立 tag-keyed vertex、edge、loop、face maps；
5. 校验全部 loop/face 引用；
6. 遍历全部 faces 创建 analytic face entity；
7. 对每个 face 展开其全部 loop edges；
8. 对共享 loop 的 geometric edges 只创建一次 entity，但分别加入相邻 face boundaries；
9. triangle classification 接受任意已声明 `(2, face_tag)`；
10. mesh vertex/edge classification 接受任意已声明合法 model entity；
11. APF/MDS nodes、edges、triangles 创建循环保持全局唯一；
12. 不根据坐标或相邻 triangles重新推导 classification。

当前 `validate_classification()` 的 set-based membership 已能接受多个 model tags；需要删除的是随后对 unique face tag 的附加限制。证据：

- `native/linkmesh_scorec_helper/main.cc:402-423`
- `native/linkmesh_scorec_helper/main.cc:565-585`
- `native/linkmesh_scorec_helper/main.cc:636-660`

当前 `create_and_write_mesh()` 已逐 entity 使用 exchange classification 调用 `findModelEntity()`，无需按 Region 分叉。证据：

- `native/linkmesh_scorec_helper/main.cc:919-978`
- `native/linkmesh_scorec_helper/main.cc:1033-1057`

## 14. SCOREC/PUMI 2.2.9 API 与生命周期

### 14.1 当前准确调用链

| 阶段 | API | 当前用途 |
|---|---|---|
| Runtime | `MPI_Init` | 初始化 MPI |
| Runtime | `PCU_Comm_Init` | 初始化 PCU |
| Model | `gmi_make_analytic` | 创建 analytic model |
| Model | `gmi_add_analytic` | 创建 geometric vertices、edges、faces |
| Topology | `agm_add_bdry` / `agm_add_use` | 创建 entity boundary 和 lower-dimensional uses |
| Reparam | `gmi_add_analytic_reparam` | 注册 vertex-to-edge、edge-to-face 参数映射 |
| Mesh | `apf::makeEmptyMdsMesh(model, 2, false)` | 创建空二维 MDS mesh |
| Mesh | `createVertex` | 创建 classified mesh vertex |
| Mesh | `createEntity` | 创建 classified edge/triangle |
| Lookup | `findModelEntity(dim, tag)` | 按 dimension 和 tag 查 model entity |
| Finalize mesh | `acceptChanges` | 接受拓扑修改 |
| Verify | `verify` | 验证 APF/MDS mesh |
| Output | `writeNative` | 写 native rank 文件 |
| Teardown | `apf::disownMdsModel` | 解除 mesh 对 model 的 ownership |
| Teardown | `destroyNative` | 销毁 native MDS 数据 |
| Teardown | `apf::destroyMesh` | 销毁 APF mesh wrapper |
| Teardown | `gmi_destroy` | 销毁 analytic model |
| Runtime | `PCU_Comm_Free` / `MPI_Finalize` | 释放 runtime |

头文件和签名证据：

- MPI 调用：`native/linkmesh_scorec_helper/main.cc:1096-1113`
- PCU 声明：`PCU.h:27-33`
- GMI analytic 声明：`gmi_analytic.h:30-64`
- GMI destroy：`gmi.h:167-169`
- `makeEmptyMdsMesh`：`apfMDS.h:44-50`
- `disownMdsModel`：`apfMDS.h:198-201`
- `createVertex`/`createEntity`：`apfMesh2.h:73-104`
- `acceptChanges`：`apfMesh2.h:119-121`
- `findModelEntity`：`apfMesh.h:257-261`
- `verify`/`writeNative`：`apfMesh.h:280-286`
- `destroyMesh`：`apf.h:73-80`

### 14.2 Ownership

当前生命周期顺序必须保持：

```text
gmi model 创建
→ callback data 保持地址稳定
→ MDS mesh 创建并使用 model
→ acceptChanges
→ verify
→ writeNative
→ disownMdsModel
→ destroyNative
→ destroyMesh
→ gmi_destroy
→ PCU_Comm_Free
→ MPI_Finalize
```

证据：

- callback data 生命周期：`native/linkmesh_scorec_helper/main.cc:772-854`
- mesh 正常与异常清理：`native/linkmesh_scorec_helper/main.cc:1059-1090`
- runtime 清理：`native/linkmesh_scorec_helper/main.cc:1131-1163`

### 14.3 多 Face API 能力裁决

`findModelEntity(int type, int tag)` 本身按 dimension/tag 查找，不含 unique-face 参数，具备多 face 通用调用形态。证据：

- `apfMesh.h:257-261`
- `native/linkmesh_scorec_helper/main.cc:894-910`

现有 face records、loop records 和 classification records 已提供创建多个 faces 所需引用。因此无需新增 Python 绑定路线、pybind11、ctypes 或第二套 helper。

但以下仍待目标环境 native fixture 确认：

- 同一个 analytic edge 分别作为两个 face boundaries 的 use 是否通过 `verify()`；
- 是否要求显式 use direction；
- 多 loop face 的 outer/hole orientation 如何表达；
- 当前统一 `(R,Z)` face parameterization 对多 loop face 是否满足目标版本要求。

当前 `agm.h` 正文证据不足，不能把这些事项写成已确认 API 事实。

## 15. Single-region 兼容策略

必须保持：

- `build_single_face_model_spec(mesh)` 公开签名不变；
- single-region 不要求 RegionPlan 或 regions map；
- vertices/edges/loop/face tags 和记录顺序不变；
- TXT header 保持 `1 -1 1 -1 -1`；
- TXT 序列化内容不变；
- exchange schema version 保持 1；
- v1 wire layout 不变；
- helper 对 v1 继续执行旧 single-face invariants；
- rank-0 路径和 success/error marker 不变；
- 既有 single-region tests 继续作为回归基线。

可以在内部复用低层构造或校验辅助函数，但不得迫使旧调用方制造虚假的多区域 metadata。

## 16. `regions generate --target=m3dc1` 候选 CLI/Config

这是蓝图修订候选，当前不得直接实现。

### 16.1 候选参数

在现有 `regions generate` 作用域内扩展：

```text
--target {mesh_only,trimeg,m3dc1}
--model PATH
--smb PATH
--no-smb
```

保留现有：

```text
--multi-array-file PATH
--regions-map PATH
--plot PATH
--mesh-dx FLOAT
--region-dx REGION_ID=DX
```

不新增：

- `physical-label-to-face`；
- `technical-role-to-face`；
- PUMI 路径参数；
- Region ID 偏置参数；
- 并行分区参数；
- 第二剖分引擎参数。

### 16.2 候选配置字段

在独立 regions config 中允许：

```toml
[regions]
mode = "generate"
target = "m3dc1"
multi_array_file = "boundaries.txt"
regions_map = "regions.toml"
plot = "mesh.png"
model = "model.txt"
smb = "mesh.smb"
```

候选 required fields：

| target | 必需 | 禁止 |
|---|---|---|
| `mesh_only` | 现有 mesh/plot 输入 | `hdf5`、`model`、`smb` |
| `trimeg` | `hdf5` | `model`、`smb` |
| `m3dc1` | `model`、`smb` | `hdf5` |

`--no-smb` 可作为执行期开关，但不取消 `smb` required field，与旧顶层 M3D-C1 入口保持一致。

### 16.3 编排候选

```text
read multi-array
→ rebuild/validate RegionPlan
→ read/validate regions map
→ resolve Region dx
→ generate one N-region Mesh2D
→ build one multi-face M3DC1ModelSpec
→ write TXT from that exact spec
→ write SMB exchange from same mesh/spec/mappings
→ invoke helper
→ verify non-empty rank-0 SMB
→ write plot/report paths
```

TXT 和 SMB 必须使用同一个 ModelSpec 和同一套 tag mappings，不得各自编号。

## 17. 逐文件修改清单

以下仅是下一轮蓝图批准后的最小实施清单，不是本轮源码修改。

| 文件 | 最小修改 |
|---|---|
| `LinkMesh_Architecture_Plan.md` | 先正式批准多区域 M3D-C1 输入、映射、schema v2、CLI/config、验收和停止条件 |
| `src/linkmesh/m3dc1_model.py` | 增加 multi-face builder；推广完整 ModelSpec 校验；保留 single-face builder |
| `src/linkmesh/writers/m3dc1_model_writer.py` | 接受 validated multi-face spec；保持现有记录布局和 v1 输出回归 |
| `src/linkmesh/writers/smb_writer.py` | 接受显式 mappings；推导多 face classification；multi-region 写 schema v2；single-region 写 v1 |
| `native/linkmesh_scorec_helper/main.cc` | 同时读取 v1/v2；增加 v2 invariants；创建全部 faces；应用任意已声明 classification |
| `native/linkmesh_scorec_helper/CMakeLists.txt` | 原则上无需新依赖；仅在目标构建直接证据要求时调整 |
| `src/linkmesh/config.py` | regions generate 增加 `m3dc1` target、`model`、`smb` 和 required-fields |
| `src/linkmesh/cli.py` | 增加参数并编排同一 Mesh2D/ModelSpec 的 TXT+SMB 输出 |
| `tests/test_format_contracts.py` | 增加 ModelSpec、TXT、exchange v1/v2、classification 和 helper 边界测试 |
| CLI/config 现有测试文件 | 增加 regions m3dc1 参数、配置合并、required-fields 和互斥测试 |
| native 目标环境 fixture | 增加双 face、三层 nested、sibling/mixed smoke tests |

`Mesh2D` 不需要新增 PUMI private handles，也不需要为每个 Region 保存重复 mesh topology。

## 18. 测试矩阵

### 18.1 纯 Python 契约

1. single-face ModelSpec 和 TXT 完全回归。
2. 两层 nested：2 loops、2 faces、共享 1 个内部 loop。
3. 三层 nested：3 loops、3 faces，face loops 为 `[1]`、`[1,2]`、`[2,3]`。
4. sibling：root face 引用多个 child loops 加 own loop。
5. mixed tree：只引用 direct children，不包含孙代 loops。
6. non-contiguous Region IDs 映射到 contiguous face tags。
7. 确认 Region ID 不执行 `+1`。
8. `physical_label`、color、technical role 变化不改变 ModelSpec topology。
9. 缺失、重复、未知或不完整映射失败。
10. mesh Region ID 集合与 map 不一致失败。
11. loop/edge/face 悬空引用失败。
12. loop 不连续或不闭合失败。
13. loop 被超过两个 faces 引用失败。
14. face 无 loop 或重复 loop 失败。
15. v1 exchange bytes 保持不变。
16. v2 字段顺序与 v1 相同，仅 version/invariants 不同。
17. triangle classification 按显式 Region-to-face 映射。
18. interface mesh edges 分类到 geometric edges。
19. same-face interior mesh edges 分类到 face。
20. 全局 node/edge/triangle 数量不随 Region 拆分而重复。

### 18.2 Helper 失败边界

1. v1 multi-face 输入必须拒绝。
2. v2 single-face 和 multi-face 合法输入可读。
3. 未声明 face 的 triangle classification 拒绝。
4. 未声明 edge/face 的 mesh entity classification 拒绝。
5. dangling edge/loop/face tag 拒绝。
6. loop 被三个 faces 使用拒绝。
7. mesh edge table 缺失、重复、乱序或与 triangles 不一致时拒绝。
8. 非流形 mesh edge 拒绝。
9. trailing bytes、截断、错误 version/endian 拒绝。
10. helper 不修复或猜测 classification。

### 18.3 Native 目标环境

1. 两 face 共享 analytic edge 的 `acceptChanges()`/`verify()`。
2. 三层 nested 的 `verify()`/`writeNative()`。
3. sibling multi-loop face 的 `verify()`/`writeNative()`。
4. mixed tree 的 `verify()`/`writeNative()`。
5. 非空 rank-0 SMB 检查。
6. repeated fresh runs 的 tags、TXT 和 exchange 确定性。
7. v1 single-region native 回归。

Native `writeNative()` 测试不替代 M3D-C1 加载测试。

## 19. LinkMesh 生成侧验收

LinkMesh 生成侧完成标准应逐层记录：

| 层级 | 通过条件 |
|---|---|
| Model | Region/curve mappings 完整；multi-face ModelSpec validation 通过 |
| TXT | 文件非空；字段顺序、tags、loop/face 引用与 ModelSpec 一致 |
| Exchange | v2 layout、计数、索引、classification 和 EOF 校验通过 |
| Helper | 目标 PUMI 2.2.9 环境正常退出 |
| APF/MDS | `acceptChanges()` 和 `verify()` 成功 |
| Native output | `writeNative()` 成功且预期 rank-0 SMB 为非空普通文件 |
| Delivery | 同一 ModelSpec 产生的配套 TXT+SMB 交付，并记录 mappings 与案例输入 |

必须记录：

- curve 数、Region 数、loop 数、face 数；
- `curve_id_to_loop_tag`；
- `region_id_to_face_tag`；
- 每个 face 的 loop tags；
- 每个 face 的 triangle 数；
- interface mesh edge 数；
- TXT、exchange 调用和 rank-0 SMB 路径；
- helper/PUMI 目标版本和运行结果。

不得通过 PNG、非空 SMB 或 `verify()` 单独宣称 M3D-C1 消费成功。

## 20. 同门消费验证边界

LinkMesh 交付后，由同门分别验证：

1. M3D-C1 是否成功加载配套 TXT+SMB；
2. 是否完成初始化；
3. 是否进入时间推进；
4. 明确推进步数和停止原因；
5. 中等或长时稳定性；
6. 物理结果正确性。

状态必须分层：

```text
GENERATED
→ DELIVERED
→ LOADED
→ INITIALIZED
→ TIME-STEPPED
→ STABILITY-VALIDATED
→ PHYSICALLY VALIDATED
```

任何前一层不得自动推出后一层。LinkMesh helper 成功最多支持生成侧 `GENERATED`，实际交付后可记录 `DELIVERED`。

## 21. 仍待确认事项

1. `agm.h` 中 adjacency API 的目标版本完整签名、失败约定和 ownership。
2. 同一 analytic edge 作为两个 face uses 时是否需要显式方向。
3. 多 loop face 的 outer/hole orientation 由 edge direction、use direction还是插入顺序表达。
4. face record 的 loop tag 顺序是否具有目标格式语义。
5. sibling 和 mixed tree 的 multi-loop face 是否在目标 PUMI 2.2.9 环境通过 `verify()`。
6. 统一 `(R,Z)` analytic face parameterization 对有内部边界 face 是否充分。
7. 一般 N-region 模型的 special loop tags 如何从业务输入获得。
8. `numLoops == numFaces` 是硬约束还是教程/后续源码路径假设。
9. OFT 生成的内部 interface corner coordinates 是否与原始 curves 保持逐分量精确匹配。
10. 多条 interfaces 相交时 model vertex 和 mesh vertex classification 如何唯一对应。
11. 是否只支持 linear polygon loops，还是未来需要 periodic B-spline；本轮建议保持 linear。
12. 目标环境 `verify()` 和 `writeNative()` 成功后，M3D-C1 是否接受产物，必须由同门独立验证。

## 22. 蓝图修订建议

编码前，蓝图至少应新增或修改以下正式契约：

1. 将 LinkMesh 多区域 M3D-C1 从禁止项升级为经批准的独立阶段。
2. 定义 `build_multi_face_model_spec(mesh, plan, region_map)`。
3. 定义 `curve_id_to_loop_tag` 和 `region_id_to_face_tag` 的确定性规则。
4. 明确 Region ID 不等于 face tag且不执行 `+1`。
5. 定义 direct-child loops 加 own loop 的 face topology。
6. 定义共享 loop/edge 不复制。
7. 定义 ModelSpec multi-face invariants 和 special loop 待确认边界。
8. 定义 TXT Writer 继续使用既有字段布局。
9. 定义 exchange v1/v2 兼容策略。
10. 定义 Python Writer 是 classification 唯一责任层。
11. 定义 helper 只验证和应用 classification。
12. 定义全局 APF/MDS entities 不按 Region 重建。
13. 在 `regions generate` 中批准 `target=m3dc1`、`model`、`smb`、`no-smb`。
14. 定义 LinkMesh 生成侧和同门消费侧的分层验收。
15. 保留 single-region v1、公开 API和输出兼容要求。
16. 纳入第 23 节停止条件。

待确认事项在取得直接证据前应继续标为待确认，不应以实现假设写入正式格式事实。

## 23. 实施停止条件

遇到以下任一情况必须停止实现并返回蓝图或证据阶段：

1. 无法从 RegionPlan/regions map 无歧义建立 `curve_id -> region_id`。
2. mesh Region ID 集合与 map 不一致。
3. 需要直接使用 Region ID 作为 face tag或对其执行 `+1` 才能继续。
4. 无法确定性建立 `curve_id_to_loop_tag` 或 `region_id_to_face_tag`。
5. 内部 mesh interface 无法唯一对应输入 curve。
6. classification 需要最近距离、容差吸附、投影或物理标签猜测。
7. 需要由 helper 根据坐标、Region 或邻接重新推导 classification。
8. 同一 analytic edge 邻接两个 faces 无法通过目标 PUMI 2.2.9 `verify()`。
9. multi-loop face 需要当前 exchange 不具备的 orientation/use 信息。
10. sibling 或 mixed tree 不能用当前 ModelSpec records 无歧义表达。
11. 必须修改 `Mesh2D` 保存 PUMI/GMI/APF/MDS 私有对象。
12. 必须按 Region 复制全局 nodes、mesh edges 或 triangles。
13. 必须引入第二剖分引擎、三维、并行分区、pybind11 或 ctypes 新路线。
14. v2 无法在不破坏 v1 single-region wire/output contract 的情况下实现。
15. SCOREC/PUMI、MPI、编译器或 ABI 与锁定目标环境不一致。
16. helper lifecycle 无法保持明确 ownership 和唯一释放顺序。
17. 只能通过解析、修改或猜测 SMB 内容继续。
18. 必须调查或修改 M3D-C1 loader 才能完成 LinkMesh 生成侧实现。
19. 必须把 `physical_label` 或 synthetic OFT technical role 当作 face 物理分类。
20. 实现要求超出蓝图已批准的多区域 M3D-C1 范围。

最终实施原则是：保留一份全局三角网格，以显式 model tags、共享 loops/edges 和逐 entity classification 表达 N-region topology；由 SCOREC/PUMI 接收既有 topology 并写出 native mesh，而不是重新剖分或猜测区域语义。
