# M3D-C1 多区域 Geometric Model 生成侧拓扑证据

## 1. 调查范围与证据等级

本文只回答 LinkMesh 如何把 N-region `Mesh2D`、输入曲线和 Region 包含关系转换为 M3D-C1 analytic geometric model 的 vertices、edges、loops、faces、tags 与 orientation。

本文不讨论 SMB/SMS/SMD、PUMI C++ API、M3D-C1 初始化、时间推进或物理结果。

结论按以下等级标记：

- **已确认源码事实**：由 `m3dc1_model.cc` 的 TXT 字段读取和拓扑组装代码直接确认。
- **教程案例事实**：由教程 `input` 与对应 `diiid.txt` 的一一对应关系确认。
- **LinkMesh 当前实现事实**：由当前 `M3DC1ModelSpec`、builder 和 TXT Writer 确认。
- **待确认事项**：现有直接证据不能证明，禁止提升为格式事实。
- **设计建议**：面向 LinkMesh 多区域 builder 的显式设计，不代表 M3D-C1 已有隐式规则。

引用中的行号以本次只读快照为准。

## 2. 教程三区域案例的直接结论

### 2.1 Loop 和 face 数量

**教程案例事实：**

- `input` 声明 `numFace 3`，随后有三条 `faceBdry`，因此定义了 3 个 faces。
- `diiid.txt` header 首字段是 `3`，随后确有 loop 1、2、3 三段，因此定义了 3 个 loops。
- 这三个 loops 对应第一壁、thick wall 生成的新边界和 vacuum boundary。
- 三个 faces 分别是 plasma、wall、vacuum；这些名称来自教程注释，不是 TXT face record 自带的物理标签。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:2`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:6`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:11`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:15`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:19`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:1`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:14`

### 2.2 三条 `faceBdry` 的精确拓扑含义

教程语法注释给出：

```text
faceBdry n_loops loop_1 ... node_spacing
```

因此三条记录的字段级含义为：

| input 记录 | 精确拓扑含义 | 对应 TXT face |
|---|---|---|
| `faceBdry 1 1 0.04` | 创建一个由 loop 1 限定的 face；`1` 是 loop 数，随后唯一 loop tag 是 1，`0.04` 是该 face 的生成侧 node spacing | `1 1 1` |
| `faceBdry 2 1 2 0.04` | 创建一个同时引用 loop 1 和 loop 2 的 face；在严格嵌套案例中表示两条闭环之间的区域 | `2 2 1 2` |
| `faceBdry 2 2 3 0.1` | 创建一个同时引用 loop 2 和 loop 3 的 face；在严格嵌套案例中表示两条闭环之间的区域 | `3 2 2 3` |

`node_spacing` 不出现在 analytic model TXT 的 face record 中；TXT 只保留 face tag、loop 数和 loop tags。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:21`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:22`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:23`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\input:24`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:15`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:16`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:17`

## 3. `diiid.txt` 字段顺序

### 3.1 文件总布局

**已确认源码事实：**

1. 文件 header；
2. 重复 `numLoops` 次的 loop 段；
3. face 数；
4. 重复 `numFaces` 次的 face record。

`load_model()` 按此顺序读取，当前 LinkMesh Writer 也按相同顺序输出。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:237`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:243`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:331`
- `src\linkmesh\writers\m3dc1_model_writer.py:45`
- `src\linkmesh\writers\m3dc1_model_writer.py:68`
- `src\linkmesh\writers\m3dc1_model_writer.py:111`

### 3.2 Header

```text
numLoops separatrixLoop innerWallLoop outerWallLoop vacuumLoop
```

教程值为：

```text
3 -1 1 2 3
```

含义是 3 个 loops；无 separatrix loop；inner wall、outer wall、vacuum 的 loop tags 分别为 1、2、3。特殊语义由 header 中的显式引用赋予，不应由 loop tag 数值猜测。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:1`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:237`

### 3.3 每个 loop 段

每个 loop 依次包含：

```text
loopTag numEdges
```

随后恰好 `numEdges` 条 geometric vertex records：

```text
vertexTag R Z Y
```

再随后恰好 `numEdges` 条 geometric edge headers：

```text
edgeTag beginVertexTag endVertexTag curveType
```

若 `curveType` 是 `POLY(2)` 或 `BSPLINE(3)`，紧接一条 curve payload：

```text
order numControlPoints
knots[order + numControlPoints]
(R Z)[numControlPoints]
```

`LIN(1)` 没有附加 payload。教程中的每个 loop 都由一条首尾 vertex tag 相同的闭合 `BSPLINE(3)` edge 表示。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:2`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:3`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:4`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:5`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:247`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:254`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:262`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:289`

### 3.4 Face 段

face 段首先是：

```text
numFaces
```

每个 face record 为：

```text
faceTag numLoops loopTag_1 ... loopTag_numLoops
```

因此 face 可以引用一个或多个完整 loops。解析器会展开每个被引用 loop 的全部 edge tags，并把这些 edges 作为该 face 的几何边界。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:14`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:15`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:344`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:352`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:357`

## 4. Loop、edge 与共享界面

### 4.1 Loop 如何引用 edge

TXT 没有单独的 `edge_tags` 列表。一个 loop 的有序 edge 引用由该 loop 段中随后出现的 `numEdges` 条 edge records 的顺序给出；解析器按读取顺序把 edge tags 追加到 `loopContainer[loopTag]`。

每条 edge 本身通过：

```text
beginVertexTag -> endVertexTag
```

携带方向。多 edge loop 的连续性应满足前一 edge 的终点等于后一 edge 的起点，并最终闭合。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:260`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:319`
- `src\linkmesh\m3dc1_model.py:236`
- `src\linkmesh\m3dc1_model.py:424`

### 4.2 相邻 face 是否共享 loop 和 edges

**教程案例事实：是。**

- face 1 与 face 2 都引用 loop 1；
- face 2 与 face 3 都引用 loop 2；
- 被共享的是同一个 loop tag，而不是复制出的两个 loop；
- 一个 loop tag 在 `loopContainer` 中只对应一组 edge tags，因此相邻 faces 也共享同一组 geometric edges。

教程共享关系：

| 界面 | 相邻 faces | 共享对象 |
|---|---|---|
| loop 1 | face 1、face 2 | loop 1 及其 edge 1 |
| loop 2 | face 2、face 3 | loop 2 及其 edge 2 |
| loop 3 | face 3 与计算域外部 | loop 3 及其 edge 3；没有第二个内部 face |

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:15`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:16`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:17`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:352`

**设计建议：** LinkMesh 应为每条输入曲线只创建一个 geometric loop，并让两侧 faces 引用同一 loop。不得为相邻 Region 复制坐标相同但 tag 不同的界面 loops 或 edges。

## 5. Orientation 的证据边界

### 5.1 已确认的存储方式

直接证据只确认以下两层方向信息：

1. edge 方向存储为 `beginVertexTag` 和 `endVertexTag`；
2. loop 保存有序 edge tags，故多 edge loop 的遍历方向由 edge 顺序和各 edge 的起终点共同确定。

TXT face record 中的 loop tags 都是无符号正整数，没有 `+loop`、`-loop` 或单独 orientation 字段。`make_face_topo()` 只展开 loop 的 edge tags并添加 adjacency，当前证据中没有读取 face-loop orientation 符号。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:262`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:187`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:15`

### 5.2 待确认事项

现有直接证据不能确认：

- M3D-C1 是否要求所有平面 loops 统一顺时针或逆时针；
- 一个多 loop face 的外环和孔洞是否必须使用相反几何方向；
- `faceBdry` 中 loop tags 的排列顺序是否具有 outer/inner orientation 语义；
- 教程单 edge periodic B-spline 的控制点顺序对应何种全局方向约定；
- GMI 内部是否从几何或 adjacency 插入顺序推导面侧向。

因此不得把“顺时针为正”“负 tag 表示孔洞”等规则写入实现。教程和 TXT 中没有负 edge/loop 引用。

**设计建议：** builder 应保留每条输入曲线的确定性点序和 edge 方向；在缺少进一步生成侧证据前，不应发明有符号 loop tag。若 LinkMesh 统一规范化曲线方向，该规范只能标为 LinkMesh 内部确定性约定，不能宣称为 M3D-C1 格式语义。

## 6. Tags、数组顺序和物理语义

### 6.1 已观察到的编号规律

教程中的 vertex、edge、loop、face tags 均为：

- 正整数；
- 1-based；
- 从 1 开始连续；
- 按对应记录在文件中的顺序递增。

当前 LinkMesh `M3DC1ModelSpec` 也要求四类 tag 分别是确定性的连续 `1..N`。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:2`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:6`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\tutorial\diiid.txt:10`
- `src\linkmesh\m3dc1_model.py:52`
- `src\linkmesh\m3dc1_model.py:398`

### 6.2 源码约束强度

TXT 解析器使用显式 tag 建立 maps，说明 tag 是对象标识，不只是数组下标。但后续源码存在按 `1..numL` 遍历 loops、按 `edgeTag - 1` 访问 vectors、以及 `numLoops == numFaces` 的假设。因此，在没有更强证据前，LinkMesh 不应输出稀疏、0-based 或乱序 tags。

证据：

- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:664`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:668`
- `external_references\m3dc1_multi_region_input_contract_snapshot_20260812\generation-source\projects\m3dc1\M3DC1\m3dc1_scorec\src\m3dc1_model.cc:727`

### 6.3 Tag 是否承载物理语义

普通 tag 本身不应被解释为物理类别：

- loop 的特殊类别由 header 中四个显式 loop-tag 字段给出；
- face record 没有 `plasma`、`wall`、`vacuum` 字符串；
- 教程 face 1/2/3 与 plasma/wall/vacuum 对齐，只是该生成案例的输入顺序和编号结果；
- 不得据此推广“face tag 1 永远是 plasma”等规则。

## 7. Region ID 与 face tag 的显式映射

### 7.1 `Mesh2D.region_ids` 不能直接充当 face tag

**LinkMesh 当前实现事实：** `Mesh2D.region_ids` 保存 OFT 最终区域编号，明确不重编号、不排序、不压缩。它可能稀疏，且编号来源与 geometric model face 的确定性连续 tags 不同。

因此不能执行：

```text
face_tag = Mesh2D.region_id
```

即使某个案例的值偶然相同，也只能视为显式映射后的结果。

证据：

- `src\linkmesh\mesh.py:27`
- `src\linkmesh\mesh.py:99`
- `src\linkmesh\regions.py:338`
- `src\linkmesh\m3dc1_model.py:52`

### 7.2 建议的显式映射

多区域 builder 应在构建时生成并验证两个独立映射：

```text
curve_id  -> loop_tag
region_id -> face_tag
```

建议规则：

- `loop_tag`：按稳定的 input `curve_id` 顺序分配连续 `1..C`；
- `face_tag`：按稳定的 Region/curve 身份顺序分配连续 `1..N`；
- 映射必须一对一、覆盖全部输入 curves 和全部 mesh Region IDs；
- 每个三角形的 `region_id` 通过 `region_id -> face_tag` 分类到 geometric face；
- 不根据整数大小、颜色、标签文本或 synthetic technical role 猜测映射。

## 8. 各类身份字段必须分离

| 字段 | 来源 | 用途 | 不得替代 |
|---|---|---|---|
| `curve_id` | 输入 block 顺序 | 输入曲线的稳定身份；用于包含树和 `curve_id -> loop_tag` | 不是 OFT Region ID，也不是 face tag |
| `region_id` | OFT 最终网格区域编号 | 标识 `Mesh2D.triangles` 所属 Region | 不能直接假定为 face tag |
| `physical_label` | 用户可编辑 metadata | 人类可读物理名称 | 不得自动创建 face 或决定拓扑 |
| OFT technical role | OFT 建域所需技术参数 | 驱动 OFT 的 region 定义 | synthetic `plasma` role 不是可信物理分类 |
| `face_tag` | M3D-C1 model builder | geometric face 的连续正整数标识 | 不应反向解释为 physical label |

`physical_label` 和 color 被当前 Region map 明确视为可编辑 metadata；结构验证不使用它们。

证据：

- `src\linkmesh\regions.py:45`
- `src\linkmesh\regions.py:70`
- `src\linkmesh\regions.py:491`
- `src\linkmesh\regions.py:496`

## 9. 从包含树推导每个 Region 的 boundary loops

### 9.1 推导规则

令每条输入曲线 `C` 对应唯一 loop `L(C)`，并令一个 Region 表示：

```text
曲线 C 内部，扣除 C 的所有直接 child 曲线内部
```

则该 Region 对应 face 的 boundary loops 应为：

```text
{L(C)} ∪ {L(child) | child 是 C 的直接 child}
```

为保持确定性，建议序列化顺序采用：

```text
按 curve_id 升序的直接 child loops，最后是 Region 自身的 loop
```

这与教程严格嵌套记录 `(1)`、`(1,2)`、`(2,3)` 一致。但 **loop 列表顺序是否具有 M3D-C1 orientation 语义仍待确认**；这里仅作为 LinkMesh 的稳定输出顺序。

### 9.2 严格嵌套

若 `C_outer -> C_middle -> C_inner`：

- inner Region：`[L_inner]`；
- middle Region：`[L_inner, L_middle]`；
- outer Region：`[L_middle, L_outer]`。

每条内部 loop 被 child face 与 parent face 共同引用。

### 9.3 Sibling

若 `C_root` 有 siblings `C_a`、`C_b` 作为直接 children：

- Region A：`[L_a]`，或 `[children(A)..., L_a]`；
- Region B：`[L_b]`，或 `[children(B)..., L_b]`；
- root Region：`[L_a, L_b, L_root]`。

这表示 root Region 具有一个外边界和两个内部边界。`L_a`、`L_b` 分别是 root face 与对应 child face 的共享界面；siblings 不互相共享 loop。

### 9.4 Mixed tree

对任意 mixed tree，逐 Region 使用同一局部规则：

```text
face(C).loops = direct_child_loops(C) + own_loop(C)
```

禁止把全部 descendants 都加入 face；孙代 loop 已被直接 child Region 隔开，不是当前 Region 的直接边界。

### 9.5 三层嵌套示意

下表的 Region IDs `30/20/10` 故意使用非连续值，以强调它们不能直接作为 face tags。

| input curve | loop tag | Region ID | face tag | face boundary loops | shared interface |
|---|---:|---:|---:|---|---|
| curve 1（inner leaf） | 1 | 30 | 1 | `[1]` | loop 1：face 1 ↔ face 2 |
| curve 2（middle） | 2 | 20 | 2 | `[1, 2]` | loop 1：face 1 ↔ face 2；loop 2：face 2 ↔ face 3 |
| curve 3（outer root） | 3 | 10 | 3 | `[2, 3]` | loop 2：face 2 ↔ face 3；loop 3：face 3 ↔ 域外 |

这是拓扑示意，不给 curve、Region 或 face 自动附加物理类别。

## 10. `Mesh2D` 是否足够

### 10.1 结论

`Mesh2D` 单独不足以无损构造目标多区域 analytic model。

它提供：

- 网格节点；
- 三角形连接；
- 每个三角形的 OFT `region_id`；
- 至多一条 `outer_boundary`。

它不提供：

- 每条原始输入曲线的有序几何点；
- curve 身份；
- curve parent/children 包含树；
- `curve_id -> region_id`；
- `curve_id -> loop_tag`；
- `region_id -> face_tag`；
- 内部 Region 界面的原始 analytic geometry。

证据：

- `src\linkmesh\mesh.py:127`
- `src\linkmesh\mesh.py:139`
- `src\linkmesh\regions.py:45`
- `src\linkmesh\regions.py:58`

### 10.2 最小额外输入

建议最小额外输入为：

1. 每个 `curve_id` 的有序、隐式闭合坐标；
2. 每个 curve 的直接 `parent_curve_id` 和 `child_curve_ids`；
3. `curve_id -> OFT final region_id` 的显式身份映射；
4. 经校验的 `region_id -> face_tag` 和 `curve_id -> loop_tag` 确定性映射。

`physical_label`、color 和 OFT technical role 可以随 Region metadata 一同存在，但不是构造 geometric topology 的必要输入，也不得驱动 face 创建。

## 11. 当前 `M3DC1ModelSpec` 的能力与限制

### 11.1 数据字段已经具备的多对象表达能力

**LinkMesh 当前实现事实：**

- `M3DC1ModelSpec.vertices`、`edges`、`loops`、`faces` 都是 tuples；
- `GeometricLoop.edge_tags` 可以引用多条 edges；
- `GeometricFace.loop_tags` 的类型可以容纳多个 loop tags；
- TXT Writer 已按 `spec.loops` 和 `spec.faces` 迭代；
- Writer 对 face 输出 `face tag + loop count + loop tags`；
- Writer 的数据布局原则上可以序列化多个 loops/faces。

证据：

- `src\linkmesh\m3dc1_model.py:301`
- `src\linkmesh\m3dc1_model.py:236`
- `src\linkmesh\m3dc1_model.py:271`
- `src\linkmesh\writers\m3dc1_model_writer.py:68`
- `src\linkmesh\writers\m3dc1_model_writer.py:112`

### 11.2 写死 single-face/single-loop 的校验

当前校验明确限制：

- `GeometricFace` 必须且只能引用 1 个 loop；
- model 必须恰好有 1 个 loop；
- model 必须恰好有 1 个 face；
- 全局 edge 数必须等于全局 vertex 数；
- 唯一 loop 必须且只能引用全部 edges；
- 唯一 face 必须引用唯一 loop；
- `separatrix_loop`、`outer_wall_loop`、`vacuum_loop` 必须为 `-1`；
- 唯一 loop 必须是 `inner_wall_loop`；
- builder 只从 `Mesh2D.outer_boundary` 生成一个 polygon loop 和一个 face；
- `GeometricEdge` 禁止起终点相同，因此当前模型不能表示教程中的单 vertex periodic closed edge。

证据：

- `src\linkmesh\m3dc1_model.py:284`
- `src\linkmesh\m3dc1_model.py:363`
- `src\linkmesh\m3dc1_model.py:368`
- `src\linkmesh\m3dc1_model.py:377`
- `src\linkmesh\m3dc1_model.py:430`
- `src\linkmesh\m3dc1_model.py:456`
- `src\linkmesh\m3dc1_model.py:471`
- `src\linkmesh\m3dc1_model.py:476`
- `src\linkmesh\m3dc1_model.py:481`
- `src\linkmesh\m3dc1_model.py:513`

因此，“字段容器可容纳多个对象”不等于“当前 contract 已支持多区域”。多区域需要重写完整模型校验，而不是只放宽 `len(...) == 1`。

## 12. 建议的新 builder 接口

建议复用现有正式 Region 类型，避免再引入平行拓扑模型：

```text
build_multi_face_model_spec(
    mesh: Mesh2D,
    plan: RegionPlan,
    region_map: Sequence[RegionMapEntry],
) -> M3DC1ModelSpec
```

职责边界建议：

- `mesh`：提供最终三角网格和实际 `region_ids`；
- `plan`：提供输入曲线坐标及 parent/children 包含关系；
- `region_map`：提供已确认的 `curve_id <-> region_id` 身份；
- builder 内部生成连续 `curve_id -> loop_tag` 和 `region_id -> face_tag`；
- builder 校验 mesh 中 Region ID 集合与 map 完全一致；
- 每个 curve 生成一次 vertices/edges/loop；
- 每个 Region 生成一次 face；
- 相邻 faces 引用同一 loop；
- 不使用 `physical_label` 或 technical role 推断拓扑。

这是接口建议，不是实现代码；是否把已编号 `RegionPlan` 与 `RegionMapEntry` 合并为单一输入，应由后续蓝图变更明确决定。

## 13. Single-region 兼容策略

现有：

```text
build_single_face_model_spec(mesh: Mesh2D) -> M3DC1ModelSpec
```

应保持公开签名和既有输出不变：

- 使用 `Mesh2D.outer_boundary`；
- vertices、edges 连续 1-based；
- loop tag 为 1；
- face tag 为 1；
- face boundary loops 为 `[1]`；
- header 保持 `1 -1 1 -1 -1`；
- 继续输出线性 polygon edges；
- 不要求 single-region 调用方提供 Region tree 或 Region map。

后续可让 single-region builder 在内部复用经过验证的通用低层构造辅助函数，但不能为了统一接口而强迫既有 single-region 用户制造虚假的多区域 metadata。

## 14. 待确认清单

在正式修改多区域 ModelSpec 或 builder 前，仍需取得生成侧直接证据确认：

1. outer loop 与 hole loops 是否有强制 CW/CCW 方向；
2. face record 中多个 loop tags 的顺序是否具有语义；
3. sibling、多孔和 mixed tree 是否被目标生成器正式支持；
4. `numLoops == numFaces` 是当前 M3D-C1 路径的硬约束，还是教程路径的实现假设；
5. 多 edge polygon loops 在共享 face 界面时是否需要额外的 use orientation；
6. special loop tags 在一般 N-region 输入中的赋值来源；
7. 非连续 tags 是否只是解析器可读但后续流程不安全。

这些事项不能从 SMB/SMS/SMD 推测，也不能由当前 single-region LinkMesh 约束反推为 M3D-C1 通用格式事实。
