# multi_array_file 多区域网格生成前置调查报告

- 文档主受众：Aider-facing / Human-facing
- 知识库用途：专项技术调查
- 文档状态：OFT 五类合成案例 **GENERATED**；探针后处理误判修复 **IMPLEMENTED**；修复后重跑与完整结构验收 **PENDING**；multi-array 业务 **DESIGNED / NOT IMPLEMENTED**
- 调查日期：2026-08-10
- 最高依据：User 当前决定、根目录 `LinkMesh_Architecture_Plan.md`、OFT 26.6
  `meshing.py`、OFT 携带的 `triangle.h`、当前 LinkMesh 业务源码
- 事实边界：本文形成多轮廓输入、基础检查、轻量包含推导、Region 映射、分区域常数
  网格尺度和 `regions` 两阶段 CLI 的实施契约；独立调查脚本
  `scripts/probe_oft_multi_array_regions.py` 已运行并完成五类 OFT 网格生成；原
  summary FAIL 来自后处理误判。修复已实现但尚未重跑。本轮未修改业务源码、测试、
  依赖、Writer、native helper 或求解器接口，也未实现生产 N-region `Mesh2D`

---

## 1. 调查目标与范围

目标是为以下候选数据流建立可实施、可验证且不过度扩张的技术边界：

```text
multi_array_file
  → 多轮廓 Reader 与基础检查
  → 轻量包含推导
  → 唯一根 parent/children
  → curve_id / OFT 最终 Region attribute
  → OFT Domain
  → OFT/Triangle 多区域二维网格
  → 分区域常数 dx
  → Mesh2D
  → inspection PNG / mesh PNG
```

本轮调查范围：

1. OFT 26.6 `gs_Domain`、`Mesh`、`Region` 和 `run_triangle` 的真实数据流。
2. OFT 对多轮廓、多 Region、seed、共享 segment、包含关系和几何错误的现有能力。
3. OFT 携带的 Triangle `triangulateio` 数据接口及当前 Python wrapper 的实际使用。
4. 成熟计算几何算法和 GEOS/Shapely 候选。
5. `multi_array_file`、包含树、Region ID、region map、分区域 dx、两阶段 CLI 和
   配置文件候选契约。
6. 后续最小 OFT 运行探针和实施批次。

明确排除：

- M3D-C1 内部实现、classification、C1、TXT/SMB 格式和求解器源码；
- TRIMEG schema 修改；
- `Mesh2D` 字段修改；
- native helper 和 helper exchange schema 修改；
- multi-array Reader、`regions` 子命令或 N-region Adapter 的实际编码；
- 测试、依赖、Release、示例和 work plan 修改；
- 空间连续 size function、动态自适应、磁面对齐、第二剖分器和通用区域 DSL。

---

## 2. 当前正式契约

以下内容由 User 明确确认，作为后续实现的正式设计方向：

1. 新边界来源名称为 `boundary_source="multi_array_file"`。
2. 现有 `array_file` 单曲线语法和行为保持不变。
3. 现有无子命令 `linkmesh [现有参数]` 保持承载当前功能。
4. 新功能使用显式 `linkmesh regions ...` 子命令。
5. `regions` 包含两个明确阶段：
   - 输入、代码几何检查、包含关系分析、Region 着色和人工复核；
   - 按 Region 设置常数网格尺度并生成多区域网格。
6. 阶段不得通过是否提供 dx 或输出参数隐式猜测。
7. `regions` 支持 `--config`，并保留完整长 CLI。
8. 优先级继续为：

   ```text
   程序默认值 < 配置文件 < 用户显式 CLI
   ```

9. 分区域尺度按显式 Region ID 映射，不使用输入数组位置、OFT 输出数组顺序、
   面积、颜色或物理名称猜测。
10. 首版恰好允许一条唯一最外层曲线。
11. 其他曲线必须严格位于最外层曲线内部。
12. 任意两条曲线只能严格包含或完全分离。
13. 首版禁止自交、相交、相切、重合、部分重叠、歧义包含和多个根。
14. 首版不把任何曲线解释为空洞。
15. 一个父曲线可以包含多个互不相交的直接子曲线。
16. 全部曲线共同构成一棵唯一根包含树。
17. 代码承担基础输入检查、轻量包含推导、唯一 root、OFT 组装和结果检查；PNG 是
    必要人工复核，但不是数学证明。
18. 暂不修改、删除或优化 `nested_three_region`。
19. 当前只调查多区域 `Mesh2D` 和 OFT 网格生成，不修改任何 Writer 或 helper。

User 后续已经确认：

- 两阶段正式使用二级子命令：
  `linkmesh regions inspect` 与 `linkmesh regions generate`；
- 不建立第二套面向用户的 LinkMesh Region 编号；
- OFT 完成内部编号后的最终 Triangle Region attribute 是正式 Region ID；
- `curve_id` 只追踪 `multi_array_file` 的输入 block 顺序，不是 Region ID；
- inspect 阶段输出用户可读的 regions map；
- 首版只实施基础输入检查、轻量包含推导和人工看图，不建设通用鲁棒计算几何系统；
- Shapely/GEOS 不作为首版必需依赖。

尚未由 User 最终确认：

- regions map 的正式文件名、序列化格式和 schema；
- regions map 是否为 generate 阶段强制输入；
- `input_sha256` 与颜色是否为 regions map 首版正式字段；
- `--region-dx` 必须完整覆盖还是允许由全局 `--mesh-dx` 提供局部覆盖；
- regions 配置文件的最终 section、文件名和自动发现规则；
- 首版轻量包含推导使用 OFT `Region` 方法时的具体构造顺序；
- `setup_only=True` 能否稳定取得与最终 Triangle attribute 一致的 Region ID。

---

## 3. User 已确认的 M3D-C1 事实边界

User 根据同门展示确认：M3D-C1 本身能够实际开展多区域模拟。这是项目需求和求解器
能力的直接项目事实。

该事实不表示：

- LinkMesh 当前已经实现 `multi_array_file`；
- LinkMesh 当前已经生成新的多区域网格；
- 当前 single-face `M3DC1ModelSpec`、TXT Writer、SMB Writer 或 helper 已支持
  新多区域拓扑；
- 新网格已经被 M3D-C1 加载、初始化、时间推进或物理验证。

后续正确顺序是先验证 LinkMesh/OFT 多区域网格生成，再通过真实 M3D-C1 使用确认
兼容性。本轮不调查或修改 M3D-C1 输出链。

---

## 4. OFT N-region API 和调用链

### 4.1 证据范围

OFT 26.6 官方文档证据：

- [ITER meshing example](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/latest/doc_tMaker_ITER_ex1.html)：
  使用 `gs_Domain` 定义多个 plasma、vacuum、boundary、conductor 和 coil Region，
  为不同 Region 提供不同常数目标尺度，显式调用 `add_polygon()`、
  `add_annulus()` 和 `add_rectangle()` 描述区域关系，使用 `plot_topology()` 人工
  检查曲线是否交叉，再由 `build_mesh()` 生成带逐三角形 Region ID 的网格。
- [gs_Domain API](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/latest/classOpenFUSIONToolkit_1_1TokaMaker_1_1meshing_1_1gs__Domain.html)：
  公布 `define_region()`、`add_polygon()`、`add_annulus()`、`add_enclosed()`、
  `add_rectangle()`、`plot_topology()` 和带 `setup_only` 参数的 `build_mesh()`。
- [Region API](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/latest/classOpenFUSIONToolkit_1_1TokaMaker_1_1meshing_1_1Region.html)：
  公布闭合边界 Region、`check_in_poly()`、`get_in_point()`、
  `get_resampled_points()`、`get_segments()` 和 `plot_segments()`。

官方文档确认 OFT 具备多 Region、分 Region 常数 dx 和由调用者显式提供区域关系的
正式工作流。ITER 示例是复杂聚变装置多区域能力的直接证据，但不能外推为 LinkMesh
候选的任意无序曲线、所有 sibling、四层以上嵌套和混合拓扑已经验证。

本地源码证据：

```text
TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py
TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h
```

本地源码用于确认 Region、segment、seed、编号、Triangle `regionlist` 和
`triangleattributelist` 的实际数据流。OFT Python 调用链：

```text
gs_Domain.define_region()
  → gs_Domain.add_polygon() / add_annulus() / add_rectangle() / add_enclosed()
  → Region(...)
  → gs_Domain.build_mesh()
  → Mesh(region_list, extra_reg_defs, merge_thresh)
  → Mesh.get_mesh()
  → run_triangle(alpha)
  → oft_triangle_lib.triangulate("pqaAzQ", ...)
  → vertices / triangles / triangle_attributes
```

### 4.2 `define_region`

稳定位置：`class gs_Domain` 的 `define_region()`。

接口：

```python
define_region(
    name,
    dx,
    reg_type,
    eta=None,
    noncontinuous=None,
    nTurns=None,
    coil_set=None,
    allow_xpoints=False,
    inner_limiter=False,
)
```

已确认数据：

```text
domain.region_info[NAME] = {
    "id": next_id,
    "dx": dx,
    "count": 0,
    "type": reg_type,
    "allow_xpoints": ...
}
```

允许的 `reg_type` 是：

```text
plasma
vacuum
boundary
conductor
coil
```

已确认 ID 行为：

1. `plasma` 在定义时被赋值 `id=1`。
2. 非 plasma 的初始 ID 根据当前 `region_info` 数量和 plasma 数量计算。
3. `build_mesh()` 在实际建网格前重新排列 ID：
   - plasma 保持首位语义；
   - 随后按 `boundary`、`vacuum`、`conductor`、`coil` 类型顺序重新赋值；
   - 原地更新 `domain.region_info[name]["id"]`；
   - 同时更新每个 `Region._id` 和 `_extra_reg_defs` 中的 attribute。
4. 因此 OFT 不保留任意调用方指定的自由整数 Region ID。
5. 当前接口没有 `region_id=` 参数。

对 LinkMesh 的影响：

- OFT 在 `build_mesh()` 中完成内部编号后，最终 Region attribute 直接作为正式
  Region ID；不再建立第二套面向用户的 LinkMesh Region 编号。
- `curve_id` 只标识输入 block。regions map 负责说明
  `curve_id → OFT region name → final Region attribute/Region ID`。
- 分区域 dx 由用户按 regions map 中的最终 Region ID 指定，不能根据
  `triangle_attributes` 的数组位置、首次出现顺序、面积或颜色猜测。
- inspect 与 generate 均需重建 OFT Domain。两次重建后的编号一致性、改变 dx 后的
  编号稳定性和 block 重排影响尚未运行验证，必须列入最小探针。
- OFT 只有技术/物理角色型 `reg_type`，没有中性的任意 Region 类型。如何把无物理
  名称的输入曲线映射为 OFT technical role，仍是探针和后续设计项。

### 4.3 `add_polygon`

接口：

```python
add_polygon(
    contour,
    name,
    parent_name=None,
    angle_tol=30.0,
    sliver_tol=120.0,
    small_thresh=None,
)
```

已确认行为：

1. `contour` 转为 NumPy 数组。
2. 查找已定义的 `name`，读取该 Region 的 `dx`。
3. 默认 `dx_curve=dx`。
4. 提供 `parent_name` 时，只读取父 Region 的 `dx`，并令：

   ```text
   dx_curve = min(child_dx, parent_dx)
   ```

5. 检查 contour 最小 R 不得为负。
6. 更新 Domain 包围统计。
7. 创建一个 `Region(contour, dx, dx_curve, ..., region_id)`。
8. `parent_name` 不保存为拓扑边，不建立父子对象关系，不执行空间包含验证，也不构造
   包含树。

准确结论：

- 官方 API 把 `parent_name` 描述为 polygon 外部 Region 的名称；ITER 示例由调用者
  显式传入该关系。
- 本地源码确认 `parent_name` 被用于查找外侧 Region，并以两侧较小 dx 协调共享
  边界的 `dx_curve`。
- `parent_name` 是调用者提供的关系，不是 OFT 根据坐标自动推导包含树的输出。
- `parent_name` 不执行严格 polygon containment 验证，也不构造显式布尔差集或
  Triangle hole。
- 多层嵌套可通过多条约束 contour、调用者提供的关系和 Region seed 表达，但
  LinkMesh 候选的任意层级、sibling 和混合行为尚未运行验证。

### 4.4 `add_annulus`

接口：

```python
add_annulus(
    inner_countour,
    inner_name,
    outer_contour,
    annulus_name,
    parent_name=None,
    angle_tol=30.0,
    sliver_tol=120.0,
    small_thresh=None,
)
```

已确认行为：

1. 内轮廓创建 `inner_name` 对应 Region。
2. 外轮廓创建 `annulus_name` 对应 Region。
3. 内轮廓的 `dx_curve` 取 inner/annulus 两侧较小值。
4. 外轮廓的 `dx_curve` 在提供 parent 时再与 parent dx 取较小值。
5. 方法不建立显式 polygon-with-hole 数据结构。
6. “annulus”效果来自同一 PSLG 中的内外约束 segment 和不同区域 seed，而不是
   Triangle `holelist`。
7. 方法未执行内轮廓严格位于外轮廓的主动几何检查。

对 LinkMesh 的影响：

- 两层嵌套是 OFT 当前已有的直接表达模式，但不能据此证明四层、sibling 或混合树。
- N-region 实现不能简单递归调用 `add_annulus()` 后宣称任意树已支持；sibling 和多层
  seed 必须单独探针验证。

### 4.5 `add_enclosed`

接口：

```python
add_enclosed(in_point, name)
```

已确认行为：

```text
_extra_reg_defs.append([
    in_point[0],
    in_point[1],
    region_id,
    dx*dx/2.0,
])
```

并增加该 region 的 count。

准确语义：

- 它向 Triangle regionlist 增加一个额外 seed、已有 Region attribute 和面积约束。
- 它不添加 contour、segment 或 hole。
- 它不创建新的 LinkMesh Region。
- 它可为由已有 PSLG segment 围成的连通区域补充 seed，但调用者必须自己提供合法内部点。
- 它不验证点是否位于目标几何 Region。

对 LinkMesh 的影响：

- 若一个 LinkMesh Region 在几何上有多个不连通分量，理论上可能需要多个 seed；
  首版候选定义中，父 Region 减去多个 sibling 子 Region 后通常仍可能保持连通，但
  对一般凹几何不能未经证明假定。
- `add_enclosed` 不能替代包含树、polygon difference 或 Region seed 验证。

### 4.6 `Region`

构造接口：

```python
Region(
    points,
    dx=None,
    dx_curve=None,
    angle_tol=30.0,
    sliver_tol=120.0,
    small_thresh=None,
    id=0,
    load_dict=None,
)
```

已确认数据流：

1. 保存原始点列和 Region attribute。
2. `dx` 保存为 `_dx_vol`。
3. `dx_curve` 保存为 `_dx_curve`，缺省时等于 `dx`。
4. 若首末距离小于 `dx/1000`，删除显式闭合末点。
5. 通过相邻切向量夹角识别 corner，将闭合 contour 划分为有向 segment。
6. 相邻点距离小于 `_dx_curve/1000` 时只输出 repeated-points warning 并跳过该次
   tangent 更新；不构成 LinkMesh 所需的严格拒绝。
7. 尖角可能输出 sliver warning。
8. `_small_thresh` 缺省为 `_dx_curve/2`。

`get_segments()` 返回：

```text
每个已识别 segment 对应的原始坐标子数组列表
```

闭合边通过最后一个 segment 的末节点回到点 0 表达。

### 4.7 `Mesh.__init__`

已确认职责：

1. 遍历全部 `Region`。
2. 将 Region 点映射到全局 `_unique_points`。
3. 点间距离严格小于 `merge_thresh` 时合并为同一个全局点。
4. 比较 Region segment 的节点映射，处理：
   - 完全重合 segment；
   - 方向相反的完全重合 segment；
   - 部分重合 segment；
   - 已有 segment 的拆分。
5. 合并共享 segment 时：
   - 曲线采样尺度取两侧 `_dx_curve` 的较小值；
   - small-feature threshold 取较小值。
6. 按最终 segment 长度和 `dx_curve` 做线性插值重采样。
7. 重建全局 `_resampled_points` 和 `_resampled_segments`。
8. 为每个 Region 组装有序 `_resampled_points`。
9. 为每个 Region 自动调用 `get_in_point()` 选择一个 seed。
10. 构造 `_reg_defs` 每行：

   ```text
   [seed_R, seed_Z, Region._id, Region._dx_vol^2 / 2]
   ```

11. `extra_reg_defs` 直接并入同一 region definition 列表。

对 LinkMesh 的影响：

- OFT 具有跨 Region 的点与 segment 合并代码，是形成共形共享界面的关键候选能力。
- 该实现依赖距离阈值和节点序列匹配。近接触、不完全一致离散、部分重合和
  `merge_thresh` 可能产生意外合并或 segment 拆分。
- LinkMesh 首版明确禁止不同输入曲线相交、相切、重合或部分重叠，因此不能依赖 OFT
  的合并逻辑修复非法输入。
- 父子双方引用同一条输入曲线时，理论上可被合并为共享约束 segment；实际 N 层和
  sibling 结果必须通过拓扑探针验证。
- `_reg_defs` 是 seed 驱动，不是显式布尔 Region 几何。Region 差集定义必须由 PSLG
  界面和正确 seed 共同实现。

### 4.8 `Mesh.get_mesh` 与 `run_triangle`

`Mesh.get_mesh()` 构造：

```python
alpha = {
    "vertices": self._resampled_points,
    "segments": resampled_flat,
    "regions": self._reg_defs,
}
```

随后：

```text
run_triangle(alpha)
  → beta["vertices"]
  → beta["triangles"]
  → beta["triangle_attributes"].astype("int32").ravel()
```

`run_triangle()` 实际填充：

- `pointlist`：连续 `float64` vertices；
- `numberofpoints`；
- `segmentlist`：连续 `int32` segments；
- `numberofsegments`；
- `regionlist`：连续 `float64` regions；
- `numberofregions`。

实际选项：

```text
pqaAzQ
```

实际读取输出：

- `out_struct.pointlist`；
- `out_struct.trianglelist`；
- `out_struct.triangleattributelist`。

### 4.9 OFT N-region 能力结论

官方文档确认：

- `gs_Domain` 可建立包含多个 Region 的聚变装置网格；
- 每个 Region 可通过 `define_region(name, dx, reg_type, ...)` 使用不同常数 dx；
- 调用者通过 `add_polygon()`、`add_annulus()`、`add_rectangle()` 和
  `parent_name` 显式提供已知区域关系；
- 官方 ITER 工作流在建网格前使用 `plot_topology()` 人工检查曲线位置和交叉风险，
  建网格后按 Region 绘图检查结果。

本地源码确认：

- `gs_Domain.regions`、`Mesh` 遍历和 `_reg_defs` 都使用动态 list；
- `run_triangle` 的 `numberofregions` 来自实际数组长度；
- 核心数据容器没有固定三 Region 数组长度；
- `build_mesh()` 的 Region ID 重排遍历全部 `region_info`；
- 因而底层组织不是固定三区域数组实现。

OFT 不提供“输入任意一组无序闭合曲线后自动建立完整包含树”的高级接口。调用者必须
先确定曲线和 Region 的关系，再组合 OFT API。

官方文档和源码仍不能证明：

- 任意包含树都能得到正确 seed；
- 四层以上严格嵌套能够正确分区；
- 一个父 Region 下多个 sibling 能按候选布尔差集语义生成；
- 任意凹多边形差集仍有单 seed 可达整个目标 Region；
- 多个技术角色的 OFT ID 和最终 attributes 能满足 LinkMesh 稳定映射；
- 所有共享界面必然无裂缝、无重复边、无重叠 triangle 或非流形边。

因此正式结论是：

```text
OFT 26.6 的多 Region 与分 Region 常数 dx 能力已经由官方文档确认；
OFT 不自动从无序曲线生成包含树；
LinkMesh multi_array_file 的具体拓扑映射、编号稳定性和共享界面仍待最小探针。
```

---

## 5. OFT 几何检查能力

### 5.1 能力矩阵与首版使用边界

| 几何能力 | OFT 26.6 证据与首版处理 |
|---|---|
| shape `(N,2)` | OFT API 以 `[:,2]` 闭合边界为输入；LinkMesh 首版执行基础 shape 检查 |
| 坐标有限性 | OFT 未见统一主动拒绝；LinkMesh 首版检查有限值 |
| 单 polygon 自交 | OFT 未见完整主动分类；首版把简单曲线作为输入前提 |
| 不同 polygon 相交/相切/重合 | OFT 官方示例依赖 topology plot 人工检查；首版不建设鲁棒分类器 |
| parent/child 自动推断 | OFT 未提供自动包含树；LinkMesh 首版进行轻量推导 |
| point-in-polygon | `Region.check_in_poly()` 提供基础 polygon 内点判断 |
| Region seed 候选 | `Region.get_in_point()` 提供 Triangle 内部 seed 候选 |
| boundary resampling | `Region.get_resampled_points()` 存在，但不是 LinkMesh outer boundary 的权威来源 |
| polygon/segment 表达 | `Region` 保存闭合边界和 segments，`get_segments()` 可读取曲线分段 |
| hole seed | wrapper 未填充 holelist；首版不支持无人占据的 hole |
| 相邻重复点 | OFT warning，不是严格拒绝；LinkMesh 首版拒绝精确相邻重复 |
| 小边和 sliver | OFT warning；用户通过 topology/mesh PNG 复核 |
| 共享点/segment | Mesh 按 `merge_thresh` 和节点序列合并 |
| Triangle 失败传播 | `oft_triangulate` 非零时抛 `ValueError("Meshing failed!")` |
| Region 覆盖 | LinkMesh 必须验证每个最终 Region ID 至少对应一个三角形 |

### 5.2 `Region.check_in_poly`

算法：

1. 对每条 polygon 边检查水平射线与边的相交。
2. 根据 y 坐标跨越和计算出的 `xInter` 计数。
3. 奇数次交点表示内部。

该实现属于 ray casting/even-odd 规则。

限制：

- 没有显式数值容差。
- 点恰好落在顶点、水平边或边界上的行为由分支比较细节决定，不形成稳定公开契约。
- 代码对普通内部点可用，但不提供严格 `contains`、`covers`、`touches`、
  `overlaps` 或 DE-9IM 关系。
- 不验证 polygon 自交；对自交 polygon 的奇偶结果不能作为 LinkMesh 合法性证据。
- 不提供 polygon contains polygon。

### 5.3 `Region.get_in_point`

算法：

1. `Mesh.__init__` 先为 Region 边界点计算其到其他全局点的最近距离。
2. 选择该距离最大的边界位置 `i`。
3. `get_in_point(i, dx)` 将 offset 限制为：

   ```text
   min(dx, dx_curve) / 4
   ```

4. 计算相邻两条边的单位切向量。
5. 用两个左法向量之和构造候选 offset。
6. 调用 `check_in_poly(candidate)`。
7. 若候选不在 polygon 内，将 offset 反向。

已确认它只保证候选尝试位于该 Region 自身 polygon 内部。它不检查：

- seed 是否位于“自身 polygon 减去直接子 polygon”的目标 Region；
- seed 是否落入任意子 Region；
- seed 是否离边界达到鲁棒安全距离；
- seed 是否对极凹角、近共线边或狭窄通道稳定；
- 父 Region 被多个 child 分割后是否仍是单连通分量。

这是 multi-array 任意树的主要阻塞风险之一。

### 5.4 `add_polygon(parent_name=...)`

官方 API 将 `parent_name` 定义为 polygon 外部 Region 的名称，ITER 示例由调用者
显式提供该关系。本地源码使用该名称查找外侧 Region，并调整共享边界
`dx_curve`。未见以下行为：

- 从任意无序曲线坐标自动推导 parent；
- 验证 child 严格位于 parent；
- 自动构建完整 containment tree；
- 自动给父 Region 选择避开所有 children 的 seed；
- 自动构建 Triangle hole。

因此 LinkMesh 必须先用轻量流程推导候选 parent/children，再把关系显式交给 OFT。
这项轻量推导基于简单、明显包含或明显分离的输入前提，不是完整几何证明。

### 5.5 主动拒绝、warning、合并和最终失败的区分

**OFT 调用前主动拒绝**

- 未定义 Region name；
- 重复 Region name；
- 未知 `reg_type`；
- `dx` 为 `None` 或负数；
- contour 含负 R；
- Region 定义但未创建；
- 要求 boundary Region 但未定义/创建；
- build 后存在未认领 Region attribute；
- 部分包围范围错误。

**OFT warning**

- repeated points；
- small feature；
- sliver。

warning 不表示几何合法，也不表示 LinkMesh 首版契约通过。

**OFT 点/segment 处理**

- `merge_thresh` 内点合并；
- 重合/反向/部分重叠 segment 合并或拆分；
- segment 重采样；
- seed 自动选择。

这些是网格组装，不是严格输入合法性证明。

**Triangle 或 wrapper 最终失败**

- `oft_triangulate` 返回非零；
- 输出含未认领 region attribute。

Triangle 成功同样不能证明输入满足 LinkMesh 对简单 polygon、严格包含、完全分离、
唯一根和无相切的首版契约。

---

## 6. Triangle region、segment、hole 和 area 接口

### 6.1 `triangulateio` 数据结构

`triangle.h` 确认：

| 字段 | 数据含义 |
|---|---|
| `pointlist` | 每点两个 REAL 坐标 |
| `pointmarkerlist` | 每点一个 marker |
| `trianglelist` | triangle corner 索引 |
| `triangleattributelist` | 每 triangle 的 attributes |
| `trianglearealist` | 每 triangle 的输入面积约束 |
| `segmentlist` | 每 segment 两个端点索引 |
| `segmentmarkerlist` | 每 segment 一个 marker |
| `holelist` | 每 hole 两个坐标 |
| `regionlist` | 每项四个 REAL：x、y、attribute、maximum area |
| `edgelist` | 输出 edge 端点 |
| `edgemarkerlist` | 输出 edge marker |

### 6.2 `regionlist`

头文件明确每项布局：

```text
[x, y, regional_attribute, maximum_area]
```

并确认：

- `A` 选项启用 regional attribute；
- 无数值参数的 `a` 选项启用每 Region maximum area；
- 即使未启用其中某项，内存布局仍保持四个 REAL。

OFT `_reg_defs` 对应：

```text
x              = seed_R
y              = seed_Z
attribute      = Region._id
maximum_area   = Region._dx_vol^2 / 2
```

因此 OFT 常数 `dx` 到 Triangle 最大面积的实际转换为：

```text
max_area = dx^2 / 2
```

这只是 OFT 当前目标尺度映射，不保证 triangle 边长严格等于 dx。

### 6.3 `dx` 与 `dx_curve`

| 参数 | OFT 数据流 | 作用 |
|---|---|---|
| `dx` / `_dx_vol` | `_reg_defs[...,3] = dx^2/2` | Region 内 triangle 最大面积约束 |
| `dx_curve` / `_dx_curve` | Mesh segment 重采样 | 约束边界点间距候选尺度 |
| parent 两侧 dx | `min(child_dx, parent_dx)` | 共享界面按较细一侧重采样 |

两者不能混为同一个机制。`dx_curve` 改变 PSLG 边界离散点，`dx` 进入 regionlist
面积约束。

### 6.4 holelist

`triangle.h` 支持：

```text
holelist
numberofholes
```

但当前 OFT `run_triangle(alpha)`：

- 不读取 `alpha["holes"]`；
- 不设置 `in_struct.holelist`；
- 不设置非零 `numberofholes`；
- `Mesh.get_mesh()` 构造的 alpha 只有 vertices、segments、regions。

因此当前 OFT Python wrapper 路径没有实际向 Triangle 传递 hole seed。首版
multi-array 也明确不使用 hole 语义。

### 6.5 marker

`triangle.h` 支持 point/segment marker。当前 OFT wrapper：

- 填充 `segmentlist`；
- 不填充 `segmentmarkerlist`；
- LinkMesh 当前 Adapter 只接收 `pts/lc/reg`；
- 不从 OFT 返回边界 marker。

因此 marker 数据结构存在不等于当前 OFT/LinkMesh 路径使用 marker。

### 6.6 当前选项 `pqaAzQ`

可由当前源码和头文件安全确认：

- `p`：当前调用使用 PSLG segment、region 和 hole 相关输入结构；
- `a`：启用 regionlist 中的最大面积约束；
- `A`：启用 region attribute，并使输出 triangle attributes 有意义；
- `z`：使用 0-based 编号；
- `Q`：quiet；
- `q`：当前调用启用了 Triangle 的质量网格能力，但给定头文件不足以证明无参数 `q`
  的精确默认最小角、全部失败条件和运行时细节。

`triangle.h` 还说明 `q/a` 属于高级网格能力开关，但不是完整命令行手册。要精确确认
无参数 `q` 默认值、PSLG 非法输入诊断和全部选项交互，所需最小新增只读证据为：

```text
TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c
```

或与该内嵌版本严格对应的 Triangle 1.6 官方选项说明。本轮设计不需要用一般经验补全
这些未知项。

### 6.7 四层能力边界

必须始终区分：

1. Triangle C 数据结构支持某字段；
2. OFT Python wrapper 是否实际填充该字段；
3. `pqaAzQ` 是否实际启用该字段语义；
4. LinkMesh Adapter 是否读取和保存对应输出。

例如：

- Triangle 支持 holes；
- OFT wrapper 没有填充 holelist；
- multi-array 首版也不采用 hole；
- 因此不能把 Triangle hole 支持写成 LinkMesh hole 支持。

---

## 7. 成熟计算几何算法和库候选

### 7.1 算法比较

| 候选 | 解决问题 | 关系区分能力 | 复杂度 | 首版适用性 |
|---|---|---|---|---|
| Shoelace signed area | 面积、方向、近退化指标 | 不判断曲线间关系 | O(N) | 适合内部实现；当前已有同类实现 |
| 成对线段相交 | 自交、交叉、相切、共线重叠 | 可通过 orientation/on-segment 区分 | 单曲线 O(N²)，曲线对 O(NM) | 小规模输入可用，但数值鲁棒性责任高 |
| Bentley-Ottmann/扫描线 | 大规模 segment 交点 | 可发现交点，重合和退化需额外处理 | O((S+K) log S) | 当前 P0 过重，不建议自行实现 |
| Ray casting | 点在 polygon 内 | inside/outside；边界行为需单独定义 | O(N) 每点 | 可作辅助，不足以完成严格拓扑 |
| Winding number | 点在 polygon 内 | 对一般有向 polygon 更明确；边界仍需处理 | O(N) 每点 | 可作辅助，不替代边界关系验证 |
| Polygon containment graph | 两两包含关系 | 依赖可靠 polygon predicates | O(C²) predicates | 适合首版 |
| 最小包含者选父 | 构造直接父节点 | 在严格包含且无边界接触时无歧义 | O(C²) 或排序优化 | 适合首版 |
| Polygon boolean difference | Region 实际面积和着色 | 可表达父 polygon 减直接 children | 依赖鲁棒几何内核 | inspection PNG 很有价值 |

其中：

- `C` 是曲线数；
- `S` 是总 segment 数；
- `K` 是交点数。

OFT 当前 Region 规模和 P0 文件通常有限，自行实现扫描线没有现实收益。真正困难不是
渐近复杂度，而是浮点退化、相切、共线重合和稳定布尔差集。

### 7.2 GEOS/Shapely 的后续候选地位

Shapely 基于 GEOS，可提供成熟 polygon predicates 和布尔运算：

- `is_valid`；
- `contains` / `within`；
- `covers`；
- `touches`；
- `overlaps`；
- `crosses`；
- `disjoint`；
- boundary intersection；
- DE-9IM `relate` / `relate_pattern`；
- `difference`；
- `representative_point`。

可解决：

1. 单 polygon 有效性和自交诊断；
2. 不同 polygon 严格包含、分离、相切、重叠和交叉的区分；
3. 父 polygon 减直接子 polygon 的实际 Region geometry；
4. inspection PNG 的正确分区着色；
5. 在实际 Region geometry 中选 representative point，作为 OFT seed 候选；
6. 构造和验证 containment graph/tree。

优点：

- 成熟的拓扑谓词和布尔运算；
- 比在 LinkMesh 内扩展 O(N²) orientation 代码更适合多 polygon 关系；
- 可使用 DE-9IM 明确边界接触和内部关系；
- 支持复杂凹 polygon 和多个 sibling difference。

限制：

- 浮点计算并非精确算术，近接触输入仍需要明确精度模型和诊断策略；
- `is_valid` 不自动等于 LinkMesh 全部业务规则；
- `contains`、`covers` 的边界语义不同，必须按严格包含契约明确选用；
- geometry repair（例如自动 `buffer(0)` 或 `make_valid`）不得静默使用，因为会修改
  用户输入；
- 需要新增运行时依赖。

当前 `requirements.txt` 未包含 Shapely。NumPy、h5py、Matplotlib、OFT 和 pytest
不能替代 GEOS polygon predicates。

最新裁决：

```text
Shapely/GEOS 不作为首版必需依赖。
首版不实施通用 DE-9IM、polygon boolean 或鲁棒相切/重合分类。
```

若真实输入证明轻量方案不足，可在后续蓝图迭代中重新评估 Shapely。本轮和首版均不
修改依赖，不静默使用 `buffer(0)`、`make_valid` 或其他几何修复。

### 7.3 首版轻量实现边界

首版适合由 LinkMesh 实现：

- counted block 的严格词法解析；
- 稳定 `curve_id` 分配；
- shape、有限性、最低点数、精确重复点和明显退化面积检查；
- 使用 OFT Region 内点和 point-in-polygon 基础能力建立候选包含矩阵；
- 唯一 root、直接 parent 和 children 的确定性推导；
- OFT 最终 attribute/Region ID 与 curve、parent、children 的对应核对；
- dx 映射解析和完整性校验；
- regions map 序列化；
- inspection PNG、mesh PNG 和每 Region 三角形计数；
- OFT 输出的基本拓扑检查。

首版不实现：

- 通用 polygon boolean engine；
- Bentley-Ottmann 或通用扫描线；
- 完整自交、相切、交叉和共线重合分类；
- 通用 DE-9IM 验证；
- 复杂浮点容差体系；
- 自动几何修复；
- 容差吸附、投影或最近邻修补；
- 通用计算几何框架或区域 DSL。

---

## 8. `multi_array_file` 候选格式

### 8.1 正式设计方向

文件由一个或多个 counted R-Z block 顺序组成，直到 EOF：

```text
N
R_1 Z_1
...
R_N Z_N
N
R_1 Z_1
...
R_N Z_N
```

每个 block 表示一条隐式闭合曲线。

候选规则：

1. block 第一行只包含一个十进制整数 `N`，`N>=3`。
2. 随后恰好读取 N 行。
3. 坐标行恰好包含两个空白分隔有限浮点数。
4. 第一列 R，第二列 Z，单位 m。
5. 末点不得重复首点。
6. N 行结束后，下一非 EOF 内容必须是下一个 block 的 N。
7. EOF 结束整个文件。
8. 至少一个 block。
9. 输入 block 顺序原样保留。
10. 不从面积、方向、坐标、顺序或文件名推断物理名称。
11. 每条曲线表示区域界面，不自动表示 plasma、vacuum、wall 或 conductor。
12. 旧 `array_file` 的单 block 且全文件恰好 N 行契约不变；不得用新 Reader 替换旧
    Reader 后悄悄放宽旧格式。

### 8.2 空行和注释待确认

当前 `boundary_reader.py` 风格是严格 counted text：

- 不允许空数据行；
- 不支持注释；
- 不支持额外数据；
- 只接受空白分隔的两个字段。

沿用旧 Reader 的严格风格、不允许空行和注释，是当前保守候选；User 尚未最终裁决
multi-array 是否允许 block 间空行或注释。实现前必须确认，不得借新格式改变旧
`array_file` Reader 的严格契约。

### 8.3 curve_id 与正式 Region ID

正式规则：

- `curve_id` 按输入 block 顺序从 1 开始，只追踪输入曲线；
- `curve_id` 不是 Region ID，也不要求等于 Region ID；
- OFT 完成内部编号后的最终 Triangle Region attribute 是正式 Region ID；
- regions map 同时展示 `curve_id`、包含关系和最终 Region ID；
- inspection PNG、`--region-dx`、`Mesh2D.region_ids` 和后续验证统一使用该最终
  Region ID；
- Region ID 是离散区域标签，不是数组位置，不执行节点索引式 `+1`。

输入 block 重排会改变 `curve_id`，也可能影响 OFT 最终编号；具体影响尚待最小探针，
不得预先承诺稳定。

---

## 9. 首版允许和禁止的拓扑

### 9.1 允许

1. 一条唯一根曲线。
2. 严格多层嵌套。
3. 一个父曲线包含多个彼此完全分离的直接子曲线。
4. sibling 与更深层嵌套组合。
5. 每条曲线是有限、非退化、简单、隐式闭合 polygon。
6. 任意曲线对只能：
   - A 严格包含 B；
   - B 严格包含 A；
   - 完全分离。
7. 所有非根曲线都有唯一直接父节点。
8. 所有曲线形成一棵覆盖全部节点的无环树。

### 9.2 输入前提与非目标

首版要求用户提供：

- 简单闭合、不自交的曲线；
- 不同曲线之间无交叉、相切或重合；
- 曲线关系是明显严格包含或明显完全分离；
- 恰好一个最外层根；
- 不存在无人占据、完全不剖分的 hole；
- 不存在多个独立计算域。

首版基础检查会拒绝明确的解析错误、非有限坐标、精确重复点、精确零长度闭合边和明显
退化面积，并验证候选树只有一个 root。首版不保证对自交、相切、共线重合、近接触或
复杂部分重叠给出完整、鲁棒或精确分类。

用户必须检查 inspection PNG 和最终 mesh PNG。人工看图不是数学证明，Triangle
成功也不表示所有异常几何均合法。LinkMesh 不自动修复、吸附、排序、平滑、重采样、
缩放或布尔修改输入。

---

## 10. 首版轻量包含推导

OFT 没有自动包含树 API。首版候选流程组合 OFT Region 的基础能力：

1. 严格解析全部 counted blocks并保留输入顺序。
2. 为每条曲线分配稳定 `curve_id`。
3. 执行 shape、有限性、最低点数、精确相邻重复、精确零长度闭合边和明显退化面积
   检查。
4. 为每条曲线构造 OFT `Region` 候选，并获得一个位于该单一 polygon 内的代表点。
5. 使用其他曲线的 `Region.check_in_poly()` 判断代表点位于哪些曲线内部。
6. 建立候选包含矩阵。
7. 对每条非根曲线，从包含它的曲线中选择直接 parent。
8. 验证只有一个 root，parent 链无环且覆盖全部曲线。
9. 建立 parent/children 关系。
10. 组装 OFT Domain，取得候选最终 Region attribute。
11. 输出 regions map 和 inspection PNG。
12. 用户人工确认曲线几何、包含关系、颜色和 Region ID。
13. generate 阶段重新构造 OFT Domain，并核对最终编号和每 Region 三角形计数。

该流程是基于简单、非交叉、明显包含或明显分离输入前提的轻量组合：

- 不是 OFT 自动包含树；
- 不是完整 polygon containment 数学证明；
- 对交叉、相切、重合、近接触或复杂部分重叠可能产生错误判断；
- 必须配合 inspection PNG、最终 mesh PNG 和 OFT/Triangle 结果检查。

`Region.get_in_point()` 只能为单一 polygon 提供内部 seed 候选，不能证明 seed 位于
“父 polygon 减去 children”的实际 Region。父 Region seed 被 child 覆盖、实际
Region 不连通等风险继续保留，必须通过最小探针确认。

---

## 11. Region 几何定义及 OFT 映射风险

### 11.1 几何定义

对曲线 C：

```text
Region(C)
  = interior(C)
    minus
    union(interior(direct_children(C)))
```

三层严格嵌套：

```text
curve 1
└── curve 2
    └── curve 3
```

对应：

```text
Region 1 = inside(curve 1) - inside(curve 2)
Region 2 = inside(curve 2) - inside(curve 3)
Region 3 = inside(curve 3)
```

sibling：

```text
curve 1
├── curve 2
└── curve 3
```

对应：

```text
Region 1 = inside(curve 1) - inside(curve 2) - inside(curve 3)
Region 2 = inside(curve 2)
Region 3 = inside(curve 3)
```

### 11.2 OFT 表达候选

OFT 不直接接收 polygon boolean difference。候选映射依赖：

1. 所有 curve 作为 PSLG constrained segments。
2. 每个 LinkMesh Region 有一个或多个严格内部 seed。
3. seed 携带 OFT region attribute 和 `dx^2/2`。
4. Triangle 从 seed 在 constrained segment 分隔的连通区域内传播 attribute 和面积
   约束。
5. 同一 curve 同时作为其内外两个 Region 的共享界面，由 Mesh segment 合并形成同一
   PSLG segment。

该映射从源码数据流上可解释，但以下行为没有运行证据：

- 多层树是否始终产生预期传播区域；
- sibling child 是否形成一个具有多个内部界面的父 Region；
- 父 Region 的单 seed 是否覆盖其全部目标区域；
- 凹外边界和多个 child 是否导致父 Region 分裂为多个连通分量；
- OFT `get_in_point` 是否会把父 seed 放入 child；
- 如何不引入物理名称地分配 OFT `reg_type`；
- outermost Region 应使用 `boundary`、`plasma` 或其他技术角色；
- 唯一 `plasma` 要求如何与任意研究 Region 对齐；
- 多个同类 OFT Region 的 ID 重排是否与预期映射一致。

这些必须先由最小探针裁决。

### 11.3 hole 区别

候选 topology 中 child 不是 hole：

- child 内部必须生成 triangles；
- child 有自己的 Region ID 和 dx；
- shared interface 两侧都属于有效 Region；
- 当前 wrapper 不传 holelist。

若某区域应为空洞，则超出首版范围，不能通过漏掉 seed 或误用 child 模拟。

---

## 12. curve_id、LinkMesh region_id 与 OFT attribute

### 12.1 正式编号规则

User 已裁决不建立第二套面向用户的 LinkMesh Region 编号：

1. `curve_id = block_index + 1`，只追踪输入 block。
2. OFT `build_mesh()` 完成内部编号后的最终 Region attribute 是正式 Region ID。
3. Triangle `regionlist` 中 attribute 以数值字段传递；业务语义是离散 Region 标签。
4. Triangle 将 attribute 传播到 triangle，OFT 从 `triangleattributelist` 读回。
5. LinkMesh 验证 attribute 具有整数语义，并保存到 `Mesh2D.region_ids`。
6. inspection PNG、regions map、`--region-dx` 和后续验证均使用该正式 Region ID。
7. Region ID 不是数组位置，不根据出现顺序解释，也不执行节点索引式 `+1`。

### 12.2 运行时对应关系

程序仍需维护内部运行时对应，但它不是第二套 Region ID：

```text
curve_id
parent/children curve relationship
deterministic OFT region name
OFT technical role/type
pre-build OFT internal id
post-build final OFT attribute / formal Region ID
resolved mesh dx
```

regions map 向用户展示 `curve_id`、parent/children 和最终 Region ID。程序内部记录
OFT name 和 technical role，用于重新构造 Domain 和核对最终 attribute。

### 12.3 编号稳定性待验证

本地源码确认 `build_mesh()` 在调用 Triangle 前按 technical role 顺序
`boundary → vacuum → conductor → coil` 遍历 `region_info`，在保留 plasma 首位语义
的同时重新分配 ID，并同步更新 `region_info`、`Region._id` 和 `_extra_reg_defs`。
随后这些 ID 进入 Triangle `regionlist`，最终从 `triangleattributelist` 读回。

以下行为尚未运行验证：

- `setup_only=True` 是否可在不剖分时取得最终 Region ID；
- setup 前后 `region_info` 和 `Region._id` 的准确变化；
- 同一 Domain 重复调用的行为；
- inspect 与 generate 分别重建 Domain 后编号是否一致；
- 相同拓扑改变 dx 后编号是否一致；
- 输入 block 重排后 curve_id 和最终 Region ID 如何变化；
- 最终 Triangle attribute 是否与 setup 阶段编号一致；
- `Mesh2D.region_ids` 是否与 regions map 完全一致。

在这些探针完成前，不承诺跨重建、跨 dx 或 block 重排的编号稳定性。

---

## 13. `regions` 两阶段 CLI 方案比较

### 13.1 方案 A：互斥 flags

```text
linkmesh regions --inspect ...
linkmesh regions --generate ...
```

优点：

- 对现有单层 argparse 改动较小；
- 命令较短。

缺点：

- 必须手工建立互斥组；
- 阶段专属参数和 help 混在一个 parser；
- 配置 required-fields 分支较复杂；
- 后续新增阶段会增加互斥 flag；
- `--inspect/--generate` 视觉上像布尔选项，不如动作子命令明确。

### 13.2 方案 B：嵌套子命令

```text
linkmesh regions inspect ...
linkmesh regions generate ...
```

优点：

- 用户意图最清晰；
- 阶段天然互斥；
- 每个阶段有独立 help 和 required arguments；
- argparse 可用 nested subparsers 直接表达；
- 配置可按 inspect/generate 分离 section；
- 后续增加只读导出或诊断动作时边界清晰；
- 不需要根据参数集合推断阶段。

缺点：

- argparse 结构比方案 A 多一层；
- 必须明确 `--config` 放在 `regions` 还是阶段 parser，以及哪些通用参数可继承；
- 需要独立 regions 配置加载入口以防旧配置串扰。

### 13.3 方案 C：显式 mode

```text
linkmesh regions --mode inspect ...
linkmesh regions --mode generate ...
```

优点：

- 单 parser；
- 配置中可直接保存 mode。

缺点：

- 阶段专属 help 仍混合；
- required-fields 需要按 mode 手工判断；
- CLI 较啰嗦；
- mode 更像配置值，不如动作子命令可读；
- 后续扩展仍会使单 parser 膨胀。

### 13.4 正式 CLI 设计方向

User 已批准方案 B：

```text
linkmesh regions inspect ...
linkmesh regions generate ...
```

正式帮助层级：

```text
linkmesh -h
linkmesh regions -h
linkmesh regions inspect -h
linkmesh regions generate -h
```

作用域规则：

- 旧无子命令入口及其帮助和行为保持不变；
- inspect 和 generate 拥有独立 required fields；
- regions 参数必须位于对应二级子命令作用域，不与旧入口参数任意混写；
- 不同 argparse 子解析器可以定义同名参数；
- 旧入口 `--mesh-dx` 作用于 single-region；
- regions generate `--mesh-dx` 表示全部 Region 的默认尺度；
- inspect `--plot` 表示输入曲线、包含关系和 Region ID 图；
- generate `--plot` 表示最终多区域三角网格图；
- 阶段不得根据 dx 或输出参数是否存在隐式推断。

`--config` 的最终参数位置、regions 专用配置 schema 和发现规则仍待实现前确认。

---

## 14. 配置 schema 和 CLI 覆盖规则

### 14.1 隔离原则

旧命令：

```text
linkmesh [现有参数]
```

继续使用当前 17 字段 `EffectiveConfig` 和当前 `linkmesh.in` schema。

新命令：

```text
linkmesh regions ...
```

应使用独立的 command-scoped 配置对象和严格 section 集，避免：

- regions 字段进入旧 `EffectiveConfig`；
- 旧自动发现配置被 regions 错误加载；
- regions 配置被旧 parser 当作未知键；
- 两条命令共享不适用默认值。

本轮不修改既有 `EffectiveConfig` 字段。

### 14.2 schema version 建议

候选建议：

- regions 配置仍可使用顶层 `schema_version=1`，但它是独立的 regions 配置 schema，
  不是向当前旧 schema 静默加入任意区域语言；
- 配置中增加明确命令族标识或使用专用 section，防止把两个 schema 混淆；
- 若 User 要求同一 `linkmesh.in` 同时表达旧命令和 regions，则应升级并重新设计完整
  schema，不能在当前 schema v1 中静默塞入新键。

更保守的首版建议：

```text
regions 只在显式 --config 时加载专用配置；
不自动发现旧工作目录 linkmesh.in。
```

这样最能避免配置串扰，但自动发现规则尚未由 User 确认。

### 14.3 候选字段

候选配置信息：

```text
multi_array_file path
inspection PNG path
region map path
mesh PNG path
global mesh_dx
region_id → dx mapping
```

候选 TOML 表达：

```toml
schema_version = 1

[regions]
input = "regions.rz"
region_map = "regions.map.json"

[inspection]
plot = "regions-inspection.png"

[mesh]
mesh_dx = 0.08

[mesh.region_dx]
"2" = 0.05
"3" = 0.03

[output]
plot = "regions-mesh.png"
```

这是调查建议，不是最终 schema。`curve_id`、parent、children、SHA-256 和 OFT
attribute 属于派生 region map，不应要求用户手工重复输入。

### 14.4 路径和优先级

建议沿用现有清晰规则：

- 配置文件中的相对路径相对配置文件目录；
- 显式 CLI 相对路径相对当前工作目录；
- 不展开环境变量或 `~`；
- 配置层不创建目录；
- CLI 显式覆盖配置；
- 未提供值使用 regions 自身默认值；
- 旧命令和 regions 各自只读取自己的 schema。

完整长 CLI 必须可以表达全部必需输入和输出，不强制配置文件。

---

## 15. region map

### 15.1 正式职责

User 已决定 inspect 阶段输出用户可读的 regions map。它不是第二套 Region 编号翻译
系统，职责是：

- 展示 OFT 最终 Region ID；
- 展示对应 `curve_id`；
- 展示 parent Region 和 child Regions；
- 展示 inspection PNG 中的颜色候选；
- 让用户按最终 Region ID 设置目标 dx；
- 帮助用户确认轻量推导的包含关系。

generate 是否必须读取该 map，仍需 User 最终裁决。

### 15.2 候选内容

regions map 可采用 TOML，但正式文件名、格式和 schema 尚未确认。候选内容：

```text
schema_version
input_sha256
region_id（OFT 最终 attribute）
curve_id
parent_region_id
child_region_ids
inspection color
```

程序内存对象可额外保存 OFT region name、technical role 和 resolved dx，但这些
运行时对应不构成第二套用户 Region ID。

不应保存：

- NumPy 二进制对象；
- OFT/PUMI 句柄；
- SMB 字节；
- Matplotlib artist；
- 物理名称猜测；
- 自动修复后的替代坐标。

是否在 map 中完整复制输入坐标需后续裁决。即使复制，也必须以源文件 SHA-256 为身份
校验依据。

### 15.3 尚待裁决

当前尚未最终确认：

- regions map 的正式文件名；
- 是否固定采用 TOML；
- schema version；
- color 是否为正式字段；
- `input_sha256` 是否首版必需；
- generate 是否必须把 regions map 作为输入；
- generate 是否只重新推导并核对相同编号；
- 用户主动执行 generate 是否隐式表达人工确认。

无论 map 是否强制，generate 都必须重新组装 OFT Domain、生成 Triangle 网格，并核对
最终 Region ID、每 Region 三角形数量和 mesh PNG。编号一致性由下一轮探针先验证。

---

## 16. inspection PNG

必须在代码几何检查全部通过后生成。

候选内容：

1. 绘制全部原始曲线。
2. 标注稳定 `curve_id`。
3. 按实际 Region geometry 着色：
   `parent polygon - direct children union`。
4. sibling 分别着色。
5. 标注 `region_id`。
6. 显示 parent ID、children IDs 或紧凑 containment tree。
7. 使用 R、Z 坐标和 m。
8. 保持 equal aspect。
9. 颜色只表示不同 Region，不表示 plasma、vacuum、wall、conductor 或材料。
10. 图例与着色共享同一离散颜色映射。
11. 代码检查失败时不生成看似成功的普通 inspection PNG；可选错误诊断图必须有明确
    failure 标记并另行设计。

inspection PNG 职责：

- 复核输入曲线、ID、包含树和 Region 差集着色。

mesh PNG 职责：

- 复核 OFT/Triangle 节点、triangle、共享界面和最终 Region attribute/LinkMesh
  Region 映射。

两者不能互相替代，也不能替代代码验证或真实 M3D-C1 使用。

---

## 17. 分区域常数 dx

### 17.1 CLI 候选

统一尺度：

```text
--mesh-dx 0.08
```

显式 Region 尺度：

```text
--region-dx 1=0.08 2=0.05 3=0.03
```

`--region-dx` 应支持重复 option 或一个 option 后多个 token，最终需根据 argparse
help 可读性裁决。无论语法实现如何，解析结果必须是显式
`dict[LinkMesh region_id, float]`。

### 17.2 当前推荐解析规则

以下仍是推荐方案，局部覆盖规则尚未由 User 最终裁决：

1. 只提供 `--mesh-dx`：
   - 所有 Region 使用该统一值。
2. 同时提供 `--mesh-dx` 和部分 `--region-dx`：
   - `mesh_dx` 是明确基础值；
   - `region_dx` 对列出的 Region 做显式覆盖。
3. 不提供 `--mesh-dx` 但提供 `--region-dx`：
   - 必须完整覆盖 region map 中全部 Region。
4. 两者都不提供：
   - 使用 regions 自身明确默认 `mesh_dx`，前提是 User 批准该默认值。
5. 重复 Region ID：
   - 立即失败，不采用 last-wins。
6. 未知 Region ID：
   - 立即失败。
7. 缺失 Region ID 且无全局回退：
   - 立即失败。
8. dx 必须为有限正数，bool、NaN、Inf、零和负数失败。
9. 单位统一为 m。
10. 解析和覆盖在调用 OFT 前完成。
11. 输出 resolved mapping 到日志和 region map 补充记录。

该规则兼顾统一尺度和局部覆盖，同时不依赖位置顺序。完整覆盖还是局部覆盖仍需 User
最终确认。

### 17.3 OFT 绑定

每个 resolved dx 必须按以下显式链绑定：

```text
regions map 中的 final OFT Region ID
  → 对应 deterministic OFT region name
  → define_region(name, dx, technical_role)
  → Region._dx_vol
  → regionlist maximum_area = dx^2/2
  → final OFT attribute / formal Region ID
```

共享界面的 `dx_curve` 取两侧较小 dx 是当前 `add_polygon(parent_name=...)` 和
`add_annulus()` 的源码行为，但任意树构造时如何确保每条共享 curve 的两侧尺度都进入
该最小值，需要独立 Adapter 设计和探针验证。

---

## 18. OFT 最小探针

独立调查程序已实现：

```text
scripts/probe_oft_multi_array_regions.py
```

程序已在正式 OFT 26.6 服务器运行，五类案例及 dx variants 均完成网格生成，状态为
**GENERATED**。首次 summary 全部 FAIL 由两项后处理误判造成：

1. `_seed_diagnostics()` 使用输入曲线顺序与 OFT `_reg_defs` 位置顺序关联 seed，
   与探针正在调查的 technical-role 重排相冲突；
2. `_mesh_checks()` 要求 signed double area 全部为正，把统一顺时针 triangle
   错误判为失败。

修复后改为按最终 Region attribute 显式匹配 seed，并将绝对面积退化与 orientation
诊断分离。修复状态为 **IMPLEMENTED**，尚未重新运行。该程序不被 `src/linkmesh`
导入，不改变正式 CLI，不写 HDF5、TXT 或 SMB，也不构成生产实现。

### 18.1 已取得的生成证据

- `two_level_nested`：353 points、664 cells、2 regions；dx variant 为
  449 points、841 cells、2 regions。
- `four_level_nested`：539 points、1035 cells、4 regions；dx variant 为
  640 points、1221 cells、4 regions。
- `one_parent_two_siblings`：420 points、792 cells、3 regions；dx variant 为
  603 points、1141 cells、3 regions。
- `mixed_tree`：457 points、866 cells、4 regions；dx variant 为
  627 points、1188 cells、4 regions。
- `reordered_input`：457 points、866 cells、4 regions；dx variant 为
  621 points、1183 cells、4 regions。

以上只证明 OFT/Triangle 实际返回了相应 Region 数的网格。原 summary FAIL 不能
解释为建网失败，也不能反向升级为结构检查通过。

### 18.1A 尚未纳入当前脚本或仍待后续的几何案例
5. 凹 root + sibling children。
6. 会使父 Region 分裂为多个连通分量的构造，用于确认单 seed 边界。
7. 自交单曲线。
8. 两曲线交叉。
9. 点相切。
10. 边相切/共线接触。
11. 边界完全重合。
12. 部分重合。
13. 两个独立根。
14. 相同几何但输入 block 顺序重排。

### 18.2 dx、setup_only 和 Region ID

1. 所有 Region 使用相同 dx。
2. 相邻 Region 使用明显不同 dx。
3. 四层 Region 使用单调变化 dx。
4. `setup_only=True` 是否能在不剖分时取得最终编号。
5. setup 前后 `region_info` 和 `Region._id` 的变化。
6. 同一 Domain 重复调用的行为。
7. inspect 与 generate 分别重建 Domain 后编号是否一致。
8. 相同拓扑改变 dx 后编号是否一致。
9. 输入 block 重排后 curve_id 和最终 Region ID 如何变化。
10. 最终 Triangle attribute 是否与 setup 阶段编号一致。
11. `Mesh2D.region_ids` 是否与 regions map 一致。
12. 每个共享 interface 的采样尺度是否采用相邻两侧较小 dx。

### 18.3 输出检查

每个成功探针至少验证：

- `nodes (N,2)` 有限；
- `triangles (T,3)` 0-based、无越界；
- triangle 无重复顶点；
- triangle 面积严格大于阈值；
- 每个预期 OFT attribute 有 triangle；
- triangle attribute 与显式映射一致；
- 每条共享界面节点和无向边唯一；
- 无裂缝；
- 无重复 triangle；
- 无重叠 triangle；
- 无非流形边；
- 拓扑外边界只有唯一 root；
- child interface 两侧均有 triangle；
- Region 实际 triangle 数大于零；
- dx 差异在面积/边长分布上有可观察效果，但不要求严格边长等于 dx；
- `Mesh2D.outer_boundary` 仍只表示唯一 root 外边界；
- inspection PNG 和 mesh PNG 角色区分。

重叠 triangle 检查需要成熟 polygon/triangle intersection 能力，不能只比较重复
connectivity。

### 18.4 失败案例判定

生产实现只承诺基础输入检查和轻量包含推导，不承诺对复杂非法几何作完整分类。探针
直接调用 OFT 记录其行为，但该结果只用于风险评估：

- OFT warning 不算接受；
- Triangle 成功不算 LinkMesh 合法；
- Triangle 失败不替代 LinkMesh 精确错误诊断；
- crash、hang 或未认领 region 必须保存最小输入和日志。

---

## 19. 后续实现模块边界

候选职责，不代表文件已存在：

### 多轮廓 Reader

- 严格读取重复 counted blocks；
- 保留 block 顺序和行号；
- 计算或返回源摘要所需字节；
- 不构造包含树，不调用 OFT。

### 基础检查与轻量包含推导

- shape、有限性、最低点数、精确重复点和明显退化面积；
- OFT Region 内点与 point-in-polygon 基础能力的候选包含矩阵；
- 唯一根 parent/children；
- seed 风险诊断；
- curve_id、最终 OFT Region ID 和 regions map；
- 不建设通用 polygon predicates、boolean engine 或第二剖分器。

是否建立新模块及文件名需编码前由 User 批准。不得把候选文件写成当前仓库已有文件。

### OFT Adapter

- 把已验证几何计划映射到 OFT Regions；
- 显式绑定 dx；
- 记录最终 OFT attributes；
- 调用现有唯一 Triangle 底座；
- 验证 Mesh2D 和映射；
- 不做输入文本解析或物理名称猜测。

### Plotter

- inspection：曲线、差集 Region、ID、树；
- generate：Mesh2D、共享界面和 Region 映射；
- 不承担合法性判定。

### CLI/config

- `regions` 命令族；
- 明确 inspect/generate 阶段；
- command-scoped 配置；
- 默认 < 配置 < CLI；
- required-fields；
- 不改变旧无子命令行为。

---

## 20. 风险、未知项和停止条件

### 20.1 主要风险

1. OFT `get_in_point` 可能把父 Region seed 放入 child。
2. parent-minus-children Region 可能有多个连通分量，而 OFT 每个 Region 默认只生成
   一个 seed。
3. OFT `reg_type` 是物理/技术角色枚举，不是中性任意 Region 类型。
4. build 会重排 attributes，不能直接保存用户 ID。
5. segment merge 依赖 `merge_thresh`，近接触曲线可能被意外合并。
6. sibling 和深层嵌套没有运行证据。
7. 当前 OFT wrapper 不传 holes，但首版也不需要 holes。
8. 首版轻量 point-in-polygon 包含判断可能误判交叉、相切、重合或近接触输入。
9. inspection PNG 是必要人工复核步骤，但不是数学证明。
10. inspect 与 generate 分别重建 Domain 后的编号稳定性尚未验证。
11. `Mesh2D.region_ids` 将直接保存 OFT 最终 attributes；curve_id 不是第二套 Region ID。
12. 当前 single-face M3D-C1 输出链不能由求解器本身支持多区域的事实自动升级。

### 20.2 停止条件

后续遇到以下情况必须停止并先更新蓝图：

- OFT 无法无歧义表达候选 Region difference；
- seed 无法保证位于目标 Region；
- sibling 或多层拓扑产生裂缝、重复/重叠 triangle 或非流形边；
- 必须把 child 当 hole；
- 必须修改 `Mesh2D` 字段才能生成首版网格；
- 必须修改 Writer/helper 才能完成网格生成调查；
- 必须依赖最近距离、容差吸附或自动修复；
- OFT technical role 无法与稳定 Region 映射；
- 需要多个独立 root；
- 需要连续 size function、自适应、磁面对齐或第二剖分器；
- 需要改变旧 `array_file` 或旧无子命令 CLI；
- 需要读取 M3D-C1 内部实现才能决定网格生成契约。

### 20.3 新增只读证据需求

当前报告已能完成设计。若要精确确认 Triangle 无参数 `q` 默认值、全部选项交互和
非法 PSLG 失败行为，最小新增只读文件是：

```text
TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c
```

该文件不属于本轮必要阻塞项。实际 sibling、深层嵌套、seed 和 attribute 行为必须由
Linux OFT 26.6 最小运行探针确认，不能仅靠继续阅读头文件推断。

---

## 21. 与 M3D-C1 后续真实验证的边界

已知：

- M3D-C1 本身能够进行多区域模拟；
- 这是 User 根据同门展示确认的实际项目事实；
- 项目确实需要不同 Region 具有不同网格密度。

未知且本轮不调查：

- LinkMesh 新 N-region `Mesh2D` 如何映射到 M3D-C1 geometric faces；
- 当前 single-face model 是否可承载所需多区域语义；
- classification 如何表达；
- TXT/SMB 是否需要变化；
- C1 连续性要求；
- 新网格能否加载、初始化、时间推进或满足实际模拟。

因此本轮结论只能是：

```text
多区域网格生成是已确认需求；
LinkMesh multi-array 多区域生成链仍未实现；
与 M3D-C1 的实际兼容性必须在生成侧完成后分层真实验证。
```

---

## 22. 建议实施批次

### 批次 1：重跑已修复的 OFT 最小探针

1. 在正式 openfusiontoolkit==26.6 环境使用新的空目录运行
   `scripts/probe_oft_multi_array_regions.py --output-dir <dir>`。
2. 收集两层、四层、sibling、混合拓扑和重排输入的逐案例 JSON。
3. 核对 `setup_only`、最终编号、重复重建、改变 dx 和 block 重排。
4. 核对 Region attribute、三角形计数、seed 状态和共享界面。
5. 核对裂缝、重复 triangle、非流形边和退化单元。
6. 保存 summary JSON 和可用时生成的 topology/mesh PNG。
7. 结果返回后再更新 `History.md` 和技术状态；不得在运行前预写 PASS。

### 批次 2：剩余 User 裁决

1. regions 专用配置发现和 schema。
2. regions map 的格式、字段和 generate 输入职责。
3. dx 完整覆盖或全局默认加局部覆盖规则。
4. multi-array 空行和注释规则。

### 批次 3：纯输入、轻量包含和 inspection

1. 多 block Reader。
2. 基础曲线检查。
3. OFT Region 内点与 point-in-polygon 的轻量包含推导。
4. 唯一根 parent/children 树。
5. regions map。
6. inspection PNG。
7. 不引入 Shapely/GEOS 或通用 polygon boolean。

五类案例已 GENERATED，但原后处理结果存在误判。修复后结果返回并完成证据归档前，
不得宣告 LinkMesh multi-array 拓扑已完整验证，也不得进入完整生产实现。

### 批次 4：generate 业务链

1. `regions generate`。
2. map/SHA-256 重验。
3. resolved dx。
4. OFT Domain。
5. N-region `Mesh2D`。
6. mesh PNG。
7. 不修改 Writer/helper。

### 批次 5：真实输入和 M3D-C1 后续评估

1. 真实 multi-array 输入。
2. inspection 人工确认。
3. 生成不同 dx 网格。
4. 网格拓扑/质量检查。
5. 另行更新蓝图后评估 M3D-C1 输出映射。
6. 分层记录 GENERATED、LOADED、INITIALIZED、TIME-STEPPED 和物理验证。

---

## 23. 结论

OFT 26.6 源码确认：

- `gs_Domain`、`Mesh`、`Region` 和 `run_triangle` 使用动态 Region/seed 列表；
- Region seed 进入 Triangle `regionlist`；
- Region attribute 来自 OFT ID；
- 常数 dx 转为 `dx^2/2` 最大面积约束；
- `dx_curve` 控制 segment 重采样；
- parent_name 只确认会协调边界尺度，不构造或验证包含树；
- Mesh 具有共享点和 segment 合并能力；
- build 会重排 OFT Region ID；
- wrapper 不传 holelist；
- OFT 没有提供 LinkMesh 首版所需的完整自交、曲线间关系、唯一根和包含树验证；
- OFT 自动 seed 只检查自身 polygon，不能证明位于 parent-minus-children Region。

因此首版架构是：

```text
LinkMesh 严格 Reader 与基础检查
  → OFT Region 内点/point-in-polygon 的轻量包含推导
  → 唯一根 parent/children plan
  → OFT 最终 attribute 作为正式 Region ID
  → regions map + inspection PNG + 用户人工确认
  → 显式 Region ID/dx 映射
  → OFT PSLG/seed/attribute
  → Triangle
  → Mesh2D + mesh PNG + Region 三角形计数
```

最终状态：

- OFT 五类合成案例和 dx variants 已 **GENERATED**；
- 探针 seed 关联、绝对面积和分层状态误判修复已 **IMPLEMENTED**；
- 未实现 `multi_array_file`；
- 未实现 `regions` 子命令；
- 未生成新的 N-region `Mesh2D`；
- OFT 官方多 Region 和分 Region 常数 dx 能力已经确认；
- OFT 不提供任意无序曲线自动包含树；
- `regions inspect/generate`、regions map 和轻量包含推导均为 **DESIGNED**；
- 修复后的探针尚未重跑，完整结构验收仍为 **PENDING**；
- sibling、四层嵌套和混合拓扑已生成网格，但 seed、共享界面、退化单元和编号稳定性
  尚未由修复后结果确认；
- 未修改 `nested_three_region`；
- 未修改 `Mesh2D`、Writer、helper、格式、测试或依赖；
- 已知 M3D-C1 本身能够进行多区域模拟；
- 尚未证明 LinkMesh 新多区域网格能够被 M3D-C1 正确使用。
