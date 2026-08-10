# multi_array_file 多区域网格生成前置调查报告

- 文档主受众：Aider-facing / Human-facing
- 知识库用途：专项技术调查
- 文档状态：只读源码侦察完成；总体状态 **DESIGNED / NOT IMPLEMENTED / NOT PROBED**
- 调查日期：2026-08-10
- 最高依据：User 当前决定、根目录 `LinkMesh_Architecture_Plan.md`、OFT 26.6
  `meshing.py`、OFT 携带的 `triangle.h`、当前 LinkMesh 业务源码
- 事实边界：本文只形成多轮廓输入、几何验证、包含树、Region 映射、分区域常数
  网格尺度和 `regions` 两阶段 CLI 的候选实施契约。本轮未修改业务源码、测试、
  依赖、Writer、native helper 或求解器接口，未运行 OFT 探针，也未生成新的
  N-region `Mesh2D`

---

## 1. 调查目标与范围

目标是为以下候选数据流建立可实施、可验证且不过度扩张的技术边界：

```text
multi_array_file
  → 多轮廓 Reader
  → 单曲线及曲线间几何验证
  → 唯一根包含树
  → 稳定 curve_id / LinkMesh region_id
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
17. 几何合法性必须由代码检查，PNG 只供人工复核。
18. 暂不修改、删除或优化 `nested_three_region`。
19. 当前只调查多区域 `Mesh2D` 和 OFT 网格生成，不修改任何 Writer 或 helper。

尚未由 User 最终确认：

- 两阶段使用嵌套子命令、互斥 flag 还是 `--mode`；
- region map 是否为 generate 阶段强制输入；
- `--region-dx` 必须完整覆盖还是允许由全局 `--mesh-dx` 提供回退；
- regions 配置文件的最终 section、文件名和自动发现规则；
- 是否引入 Shapely/GEOS；
- 数值容差的具体公式和常数；
- OFT 技术角色与 LinkMesh Region 的最终映射方式。

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

### 4.1 源码证据范围

直接源码：

```text
TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py
TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h
```

OFT Python 调用链：

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

- LinkMesh 稳定 `region_id` 不能被假定等于 OFT 最终 attribute。
- 必须保存显式映射：
  `curve_id → LinkMesh region_id → OFT region name/role → final OFT attribute`。
- 映射必须在 `build_mesh()` 后从最终 `region_info` 读取并验证。
- 分区域 dx 必须在构造 Domain 前按 LinkMesh `region_id` 解析，再绑定到明确 OFT
  region name；不能根据最终 `triangle_attributes` 的出现顺序回填 dx。
- OFT 只有物理角色型 `reg_type`，没有中性的任意 Region 类型。如何把不带物理名称的
  LinkMesh Region 映射为 OFT 的 plasma/boundary/vacuum 技术角色，仍是必须通过
  最小探针裁决的设计项。

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

- `parent_name` 的源码可证语义是共享边界曲线离散尺度协调：边界使用父子两侧较小 dx。
- 不能把 `parent_name` 解释为 OFT 已验证的 polygon containment。
- 不能把它解释为显式布尔差集或 hole 声明。
- 多层嵌套可通过多条受约束 contour 和多个 region seed 候选表达，但任意层级行为
  尚未运行验证。

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

### 4.9 OFT 是否为 N-region 通用实现

源码确认：

- `gs_Domain.regions`、`Mesh` 遍历和 `_reg_defs` 都使用动态 list；
- `run_triangle` 的 `numberofregions` 来自实际数组长度；
- 核心数据容器没有固定三 Region 数组长度；
- `build_mesh()` 的 region ID 重排遍历全部 `region_info`；
- 因而底层组织不是固定三区域数组实现。

但源码不能证明：

- 任意包含树都能得到正确 seed；
- 四层以上严格嵌套能够正确分区；
- 一个父 Region 下多个 sibling 能按候选布尔差集语义生成；
- 任意凹多边形差集仍有单 seed 可达整个目标 Region；
- 多个技术角色的 OFT ID 和最终 attributes 能满足 LinkMesh 稳定映射；
- 所有共享界面必然无裂缝、无重复边、无重叠 triangle 或非流形边。

因此正式结论是：

```text
OFT 26.6 的 Region/PSLG/regionlist 数据结构具有动态 N 条目能力；
任意 N 区域拓扑能力仍为待最小探针确认，不能由已有三区域成功案例外推。
```

---

## 5. OFT 几何检查能力

### 5.1 能力矩阵

| 几何能力 | OFT 26.6 源码结论 |
|---|---|
| shape `(N,2)` 严格检查 | 未见完整主动检查；后续切片操作会依赖该 shape |
| 坐标有限性 | 未见统一主动拒绝 |
| 单 polygon 自交 | 未见 |
| 不同 polygon 边界相交 | 未见 |
| 相切检测 | 未见 |
| 重合边检测 | 未见独立合法性拒绝；Mesh 会尝试合并重合 segment |
| 部分重叠检测 | 未作为非法拒绝；Mesh 有部分 segment 合并/拆分逻辑 |
| polygon orientation | 未见正式验证或规范化 |
| signed/absolute polygon area | 未见 Region 级统一检查 |
| parent/child 自动推断 | 未见 |
| 包含树构建 | 未见 |
| polygon contains polygon | 未见 |
| polygon disjoint | 未见 |
| point-in-polygon | 有 `Region.check_in_poly()`，用途局限于 seed 方向选择 |
| Region seed 自动选择 | 有 `Region.get_in_point()` |
| hole seed 自动选择 | 未见；wrapper 未填充 holelist |
| 相邻重复点 | warning，不是严格拒绝 |
| 零长度边 | 可能以 repeated warning/后续数值问题体现，未统一拒绝 |
| 小边 | warning |
| 尖角/sliver | warning |
| 共享点/segment | Mesh 按 `merge_thresh` 和节点序列合并 |
| Triangle 失败传播 | `oft_triangulate` 非零时抛 `ValueError("Meshing failed!")` |

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

源码只用 parent 的 dx 调整 child contour 的 `dx_curve`。未见以下行为：

- 验证 child 严格位于 parent；
- 自动将 child 从 parent 做几何差；
- 保存 parent/child 引用；
- 自动给父 Region 选择避开 child 的 seed；
- 自动构建 hole 或 containment tree。

因此包含树和严格曲线关系必须由 LinkMesh 几何层负责。

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

### 7.2 GEOS/Shapely 候选

Shapely 基于 GEOS，提供成熟 polygon predicates 和布尔运算候选：

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

建议：

```text
首版优先采用成熟 GEOS/Shapely 做多 polygon 拓扑验证、布尔 difference、
representative point 和 inspection geometry；是否新增依赖必须由 User 后续裁决。
```

本轮不修改依赖，也不把 Shapely 写成已批准依赖。

### 7.3 适合 LinkMesh 内保留的算法

即使采用成熟库，以下轻量逻辑仍适合由 LinkMesh 实现：

- counted block 的严格词法解析；
- stable `curve_id` 和 `region_id` 分配；
- SHA-256；
- containment graph 到唯一根树的确定性转换；
- 最小包含者作为直接父节点；
- ID、parent、children 和 OFT attribute 映射验证；
- dx 映射解析和完整性校验；
- region map 序列化；
- OFT 输出拓扑检查。

不建议自行实现：

- 通用 polygon boolean engine；
- Bentley-Ottmann；
- 自动几何修复；
- 容差吸附、投影或最近邻修补；
- 通用计算几何框架。

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

### 8.2 空行和注释建议

当前 `boundary_reader.py` 风格是严格 counted text：

- 不允许空数据行；
- 不支持注释；
- 不支持额外数据；
- 只接受空白分隔的两个字段。

建议 multi-array v1 同样：

```text
不允许空行，不允许注释，不允许表头，不允许额外列。
```

理由：

- 保持两个 Reader 的认知一致；
- 行号错误清晰；
- block 边界无歧义；
- 不需要建设文本 DSL；
- 配置、说明和物理注释可放在独立配置或 region map 中。

该建议不改变旧 Reader。

### 8.3 ID 分配

建议：

- `curve_id`：按输入 block 顺序从 1 开始，稳定且永久保留；
- `region_id`：首版默认等于 `curve_id`；
- 输入重排会改变两个 ID，因此 inspection 产物中的 SHA-256 可防止误用旧映射；
- 几何树排序不得改变 ID；
- 图例和 map 同时显示 `curve_id` 与 `region_id`，即使首版相等也不删除两个概念。

采用 `region_id=curve_id` 的理由：

- 每条曲线恰好定义一个 Region；
- 用户容易从文件 block 定位 Region；
- 不依赖面积、树深度、物理语义或 OFT ID；
- 将来若 ID 规则变化，独立字段仍允许迁移。

这是候选建议，不表示 OFT attribute 可直接等于该 ID。

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

### 9.2 禁止

- 单曲线自交；
- 曲线间交叉；
- 相切；
- 点接触；
- 边接触；
- 边界重合；
- 共线重叠；
- 部分面积重叠但互不包含；
- 多个互不包含的根；
- 多个独立计算域；
- hole 语义；
- 多轮廓表示一个 Region；
- 开放曲线；
- 显式重复闭合末点；
- 零面积或近退化曲线；
- 自动修复、吸附、排序、平滑、重采样或缩放输入；
- 由颜色或物理名称推断 Region。

近退化和近接触的精确数值判定仍待几何内核选择和真实输入尺度调查后确定，不能在本轮
无证据固定常数。

---

## 10. 包含树算法

候选确定性算法：

1. 严格解析全部 blocks，保留输入顺序并计算原始文件 SHA-256。
2. 为每条曲线分配稳定 `curve_id`。
3. 验证 shape、有限性、点数、重复点、闭合边、面积和单 polygon 简单性。
4. 对每对 polygon 验证边界不相交、不相切、不重合。
5. 对每对 polygon 分类为：
   - A 严格包含 B；
   - B 严格包含 A；
   - 完全分离；
   - 非法/歧义。
6. 对每条曲线收集全部严格包含者。
7. 没有包含者的曲线必须恰好一条，作为 root。
8. 对每条非 root 曲线，从全部包含者中选择实际 polygon 面积最小者作为直接 parent。
9. 验证 parent 链无环并最终到达唯一 root。
10. 按 `curve_id` 升序保存 children，保证确定性。
11. 每条曲线生成一个同号 `region_id`。
12. Region 实际 geometry 定义为自身 polygon 减直接 children polygon 并集。
13. 验证每个 Region geometry 非空、有效，并确认其连通分量数量。
14. 为每个 Region 选择严格位于 Region 实际 geometry 内部的 seed。
15. 验证 seed 不位于任何直接或间接 child 内，也不落在任何边界上。
16. 生成 region map 和 inspection PNG。

步骤 3–5、12–15 不应交给 OFT 隐式完成。OFT 当前提供的 `check_in_poly` 和
`get_in_point` 不足以证明这些契约。

直接父节点选择使用“全部包含者中面积最小者”的前提是：

- 所有 polygon 已证明简单；
- 曲线边界两两不接触；
- 每对关系已证明严格包含或完全分离；
- 面积非退化。

这些前提成立时，最小包含者是唯一直接父节点。仍应显式验证唯一性，不依赖浮点面积
近似打破歧义。

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

### 12.1 推荐映射对象

后续实现应有一个小型、明确、不可歧义的内部记录，至少表达：

```text
curve_id
LinkMesh region_id
parent_region_id
children_region_ids
input_block_index
OFT region name
OFT technical role/type
pre-build OFT id
post-build OFT attribute
mesh_dx
```

这不是修改 `Mesh2D` 的要求。它可属于 regions 几何计划或 region map，最终
`Mesh2D.region_ids` 是否保持 OFT attribute 仍遵循现有 Mesh2D 契约。

### 12.2 建议规则

1. `curve_id = block_index + 1`。
2. 首版 `LinkMesh region_id = curve_id`。
3. OFT region name 使用确定性机器名，例如基于 LinkMesh Region ID 生成，不从物理
   名称猜测。
4. dx 先按 LinkMesh Region ID 校验，再绑定到该 OFT name。
5. `build_mesh()` 后读取最终 `domain.region_info[name]["id"]`。
6. 构造显式双向映射：
   - LinkMesh region_id → final OFT attribute；
   - final OFT attribute → LinkMesh region_id。
7. 验证映射一一对应且每个 Region 至少有一个 triangle。
8. 不按 `triangle_attributes` 首次出现顺序、排序后的 attribute、面积或颜色分配 dx。

### 12.3 当前阻塞

现有 `mesh_from_oft_domain()` 明确原样保存 OFT `reg`，不重编号。这一契约本轮不得
修改。因此后续实现必须先裁决：

- multi-array 的用户稳定 Region ID 是否只存在于 region map；
- 还是需要为该新路径增加显式 attribute 映射后再构造 `Mesh2D`；
- 若重映射 `Mesh2D.region_ids`，会改变现有“原样保存 OFT reg”契约，必须先更新蓝图
  并评估 Writer/Plotter 影响。

本报告建议第一版保守地：

```text
Mesh2D.region_ids 继续保存最终 OFT attribute；
region map 显式记录 LinkMesh region_id ↔ OFT attribute；
用户 dx 始终以 LinkMesh region_id 表达。
```

这样不修改现有 `Mesh2D` 字段和核心契约。是否最终采用需等待 OFT ID 探针。

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

### 13.4 推荐

推荐方案 B：

```text
linkmesh regions inspect ...
linkmesh regions generate ...
```

理由：

- 两阶段是不同用户动作，不是一个布尔模式；
- 能最直接满足“不得隐式猜测阶段”；
- help、required-fields 和输出职责最清楚；
- 与旧无子命令入口兼容：只有首 token 为 `regions` 时进入新 parser；
- 后续仍可保持小型实现，不要求插件或命令框架。

该推荐尚未由 User 最终批准，不能写成已实现或最终 CLI。`--config` 位置建议为
`linkmesh regions --config FILE inspect ...`，但 argparse 对全局参数位置的最终
用户体验应在编码前用最小 parser 原型确认。

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

### 15.1 是否需要

建议 inspection 阶段输出机器可读、版本化 region map，generate 阶段将其作为强制
输入。

理由：

- 稳定连接人工复核与生成阶段；
- 固定 curve/Region ID；
- 保存输入 SHA-256；
- 避免用户在检查后修改或重排 blocks；
- 为 dx 映射提供明确 ID；
- 保存包含树和 OFT attribute 对照；
- 便于复现和诊断。

是否强制仍需 User 最终裁决。

### 15.2 最小字段建议

```text
schema_version
source_path（诊断用途，不作为身份）
source_sha256
curve_count
curve_id
input_block_index
region_id
parent_id 或 null
children_ids
polygon signed/absolute area
tree depth
inspection geometry status
```

generate 后可扩展记录：

```text
resolved mesh_dx
OFT region name
OFT technical role
final OFT attribute
triangle count
```

不应保存：

- NumPy 二进制对象；
- OFT/PUMI 句柄；
- SMB 字节；
- Matplotlib artist；
- 物理名称猜测；
- 自动修复后的替代坐标。

是否在 map 中完整复制输入坐标需后续裁决。即使复制，也必须以源文件 SHA-256 为身份
校验依据。

### 15.3 两阶段一致性

generate 建议：

1. 重新读取原始 multi-array 文件。
2. 重新计算 SHA-256。
3. 与 map 中摘要逐字节比较，不一致立即失败。
4. 重复执行全部词法和几何检查。
5. 重新构造包含树。
6. 与 map 的 curve/parent/children/region ID 比较。
7. 验证 dx 覆盖。
8. 才调用 OFT。

人工确认建议不使用交互式 yes/no 状态写入文件。用户主动执行 generate 并提供已检查
的 region map，即视为进入第二阶段；这比不可审计的终端确认更适合批处理环境。

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

### 17.2 推荐解析规则

建议支持：

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
LinkMesh region_id
  → deterministic OFT region name
  → define_region(name, dx, technical_role)
  → Region._dx_vol
  → regionlist maximum_area = dx^2/2
  → final OFT attribute
```

共享界面的 `dx_curve` 取两侧较小 dx 是当前 `add_polygon(parent_name=...)` 和
`add_annulus()` 的源码行为，但任意树构造时如何确保每条共享 curve 的两侧尺度都进入
该最小值，需要独立 Adapter 设计和探针验证。

---

## 18. OFT 最小探针设计

本轮未运行以下探针。所有项目状态均为 **PLANNED / NOT RUN**。

### 18.1 几何和拓扑案例

1. 两层严格嵌套。
2. 四层严格嵌套。
3. 一个父 Region 包含两个 sibling。
4. 多 sibling 与更深层嵌套组合。
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

### 18.2 dx 和 ID

1. 所有 Region 使用相同 dx。
2. 相邻 Region 使用明显不同 dx。
3. 四层 Region 使用单调变化 dx。
4. 指定 LinkMesh Region ID 后记录：
   - OFT region name；
   - define 后 ID；
   - build 后最终 attribute；
   - triangle attribute 计数。
5. 重排输入 blocks 后确认稳定规则只按 block ID 改变，不按 OFT 输出顺序猜测。
6. 确认每个共享 interface 的采样尺度是否采用相邻两侧较小 dx。

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

非法几何应在 LinkMesh 几何层、OFT 调用前失败。探针仍可单独直接调用 OFT，以记录
OFT 自身行为，但该结果只用于风险评估：

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

### 几何验证与包含树

- 单 polygon 与 polygon-pair predicates；
- 唯一根树；
- Region difference geometry；
- seed；
- stable IDs；
- region map；
- 不调用 Triangle。

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
8. 自行实现多 polygon 鲁棒 predicates 和 boolean difference 风险较高。
9. Shapely 可降低几何风险，但会新增依赖和发布负担。
10. inspection 与 generate 若无强制 map/SHA-256 连接，可能对不同输入执行。
11. `Mesh2D.region_ids` 当前原样保存 OFT attributes，与用户稳定 Region ID 是两个
    不同概念。
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

### 批次 1：几何层决策

1. User 裁决是否引入 Shapely。
2. 最终确认 `regions inspect/generate` 模式。
3. 最终确认 regions 配置发现和 schema。
4. 最终确认 region map 是否强制。
5. 最终确认 dx 完整覆盖/局部覆盖规则。
6. 确认数值精度策略的原则，不静默修复。

### 批次 2：纯输入和几何

1. 多 block Reader。
2. 单 polygon 验证。
3. polygon-pair predicates。
4. 唯一根包含树。
5. Region difference 和 seed。
6. region map。
7. inspection PNG。
8. 此批次不调用 OFT。

### 批次 3：OFT 最小探针

1. synthetic tree cases。
2. technical role 和 ID 映射。
3. seed。
4. sibling 和深层嵌套。
5. shared interface。
6. dx 差异。
7. 拓扑与 triangle 质量检查。

探针通过前不得宣告任意 N-region 支持。

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

因此推荐架构是：

```text
LinkMesh 严格 Reader
  → 成熟计算几何 predicates/boolean difference
  → 唯一根包含树和显式 Region plan
  → stable LinkMesh IDs 和 region map
  → 显式 dx 映射
  → OFT PSLG/seed/attribute
  → Triangle
  → Mesh2D 和拓扑验证
```

最终状态：

- 本轮达到 **DESIGNED + READ-ONLY INVESTIGATION**；
- 未实现 `multi_array_file`；
- 未实现 `regions` 子命令；
- 未生成新的 N-region `Mesh2D`；
- 未运行任意多轮廓 OFT 探针；
- 未验证 sibling、四层嵌套或任意 N 拓扑；
- 未修改 `nested_three_region`；
- 未修改 `Mesh2D`、Writer、helper、格式、测试或依赖；
- 已知 M3D-C1 本身能够进行多区域模拟；
- 尚未证明 LinkMesh 新多区域网格能够被 M3D-C1 正确使用。
