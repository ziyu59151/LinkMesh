# OFT 26.6 单一区域静态空间变网格密度源码调查

- 文档主受众：Aider-facing
- 知识库用途：只读源码侦察报告
- 调查状态：第一轮静态调查完成；服务器运行探针未执行
- 调查对象：OpenFUSIONToolkit/TokaMaker 26.6 二维三角网格尺度控制
- 实现状态：本报告不开放任何新能力，不构成实现批准
- 事实边界：本文只记录已提供源码能够直接证明的事实、源码中可见但仍需运行验证的候选机制，以及当前调用链的证据中断位置。静态源码结论不能替代服务器 pip 安装的 OFT 26.6 运行探针。

---

## 1. 调查范围

本轮唯一问题是：

> OFT 26.6 是否存在“在单一闭合二维区域内部，使目标网格尺度随空间位置变化”的正式能力或可组合机制？

调查范围限定为：

- LinkMesh 当前 CLI/config 到 OFT Adapter 的尺度参数传递；
- OFT 26.6 `gs_Domain`、`Region`、`Mesh`、`run_triangle` 的尺度数据流；
- OFT Python 层提交给 Triangle 的区域种子、区域属性和最大面积约束；
- 已授权源码中可见的位置相关尺度、局部 refinement、adaptation、coarsening、
  background sizing field 或 metric field 候选；
- 通过多个 OFT Region 近似局部加密的可能性和语义风险；
- 下一轮服务器最小运行探针设计；
- 对 LinkMesh 现有 `Mesh2D`、TRIMEG 和 M3D-C1 契约的潜在影响。

本轮不执行以下工作：

- 不运行 OFT、Triangle 或 LinkMesh；
- 不实现局部加密；
- 不修改 LinkMesh、OFT、Triangle、M3D-C1 或 SCOREC/PUMI；
- 不修改蓝图、History、Project Tree、work plan、测试或示例；
- 不新增 CLI、TOML 字段、数据对象或 Writer 契约；
- 不宣布空间变网格密度、动态自适应或磁面对齐已经开放。

---

## 2. 版本和证据边界

### 2.1 已确认的版本对应关系

本轮采用 User 提供的直接比对证据：

1. 本地参考源码声明版本为 OFT 26.6。
2. 服务器 pip 安装包声明版本为 OFT 26.6。
3. 本轮核心文件
   `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
   已与服务器 pip 安装文件完成归一化内容比对，哈希完全相同。
4. 因此，本地 `meshing.py` 可以作为服务器 OFT 26.6 网格 Python 接口及该文件内部
   调用链的直接静态依据。
5. `eqdsk.py` 已知只有一处本地 `float(...item())` 与服务器 `float(...)` 的差异；
   该差异不涉及本轮网格尺度接口。
6. OFT 完整文件集合没有逐文件证明完全一致，不能把 `meshing.py` 的一致性推广到
   整个 OFT 安装包。

### 2.2 不同证据的权重

| 证据 | 本报告可作出的结论 |
|---|---|
| 已完成服务器归一化哈希比对的 `meshing.py` | 可直接说明服务器 OFT 26.6 对应 Python 网格接口的静态结构 |
| 当前 LinkMesh 源码 | 只能说明 LinkMesh 已经使用哪些 OFT 接口，不能证明 OFT 未接入能力不存在 |
| 未单独完成服务器比对的 OFT 文件 | 只能标记为本地 OFT 26.6 参考源码证据 |
| Triangle C 文件摘要或字段名 | 不能仅凭名称确认字段的运行语义 |
| tests/examples | 不作为本轮外部能力裁决依据 |
| 尚未执行的 API 路径 | 只能标记为候选或未验证 |
| 服务器 pip OFT 26.6 最小运行探针 | 下一轮运行行为的最终依据 |

### 2.3 实际阅读的文件和符号

本轮实际用于结论的源码和文档如下。

#### LinkMesh 侧

- `src/linkmesh/cli.py`
  - `build_parser()`
  - `_build_overrides()`
  - `_run()`
- `src/linkmesh/config.py`
  - `EffectiveConfig`
  - `CliOverrides`
  - `load_effective_config()`
  - `_check_positive_float()`
- `src/linkmesh/mesher/oft_adapter.py`
  - `generate_mesh()`
  - `build_oft_domain_from_gfile()`
  - `build_single_region_domain_from_boundary()`
  - `build_single_region_domain_from_lcfs()`
  - `mesh_from_oft_domain()`
  - `_capture_and_attach_outer_region()`
  - `_extract_outer_boundary_from_region()`
- `src/linkmesh/mesh.py`
  - `Mesh2D`
  - `_validate_outer_boundary()`

#### OFT 侧

- `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
  - `triangle_struct`
  - `oft_triangulate`
  - `run_triangle()`
  - `gs_Domain.__init__()`
  - `gs_Domain.define_region()`
  - `gs_Domain.add_polygon()`
  - `gs_Domain.add_annulus()`
  - `gs_Domain.add_rectangle()`
  - `gs_Domain.add_enclosed()`
  - `gs_Domain.build_mesh()`
  - `Mesh.__init__()`
  - `Mesh.get_mesh()`
  - `Region.__init__()`
  - `Region.get_resampled_points()`
  - `Region.get_in_point()`

#### 项目契约和工作计划

- `LinkMesh_Architecture_Plan.md`
- `docs/linkmesh/work_plan.md`
- `CONTEXT.md`
- `Project_Tree.md`
- `History.md`

#### 只获得摘要、尚不足以完成下层语义核对的文件

- `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/_interface.py`
- `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c`

### 2.4 当前调用链证据中断位置

尺度数据流已经从 LinkMesh 追踪到：

```text
run_triangle(alpha)
  → triangle_struct
  → oft_triangle_lib.triangulate(...)
```

但尚未逐行追踪到 `triangle.c` 内部如何：

- 解析 `pqaAzQ`；
- 消费 `regionlist` 的第四列 maximum area；
- 在同一个连通区域中处理多个 region seed；
- 传播 region attribute 和 area constraint；
- 使用 `trianglearealist`；
- 执行 refinement 或质量约束。

因此，本轮能够完整确认 **OFT Python 层如何构造 Triangle 输入**，但尚不能声称
Triangle C 算法内部调用链已经完整追踪。需要追加只读源码后才能关闭这一中断。

---

## 3. 术语定义与能力分类

### 3.1 全局常数尺度

整个计算域或一个 OFT Region 使用一个常数 `dx`。OFT 将其转换为一个常数最大
三角形面积：

```text
maximum_area = dx² / 2
```

当前 LinkMesh 已使用该能力。

状态：

```text
CONFIRMED BY SOURCE
```

### 3.2 分区域常数尺度

多个 OFT Region 分别保存不同的常数 `dx`，每个 Region 向 Triangle 提交自己的
region seed、region attribute 和常数最大面积。

当前 LinkMesh 的 nested 路径已经使用该模式。

状态：

```text
CONFIRMED BY SOURCE
```

### 3.3 边界曲线离散尺度

`dx_curve` 控制 OFT 在调用 Triangle 前对 Region 边界 segment 的重采样间距。
它直接改变边界离散点和 segment 数量。

该参数不等同于内部位置相关 size function。

状态：

```text
CONFIRMED BY SOURCE
```

### 3.4 单一区域静态空间变密度

同一次初始网格生成中，在不增加正式 Region 的前提下，内部目标尺寸直接随
`R`、`Z`、距离场、指定点、曲线或用户函数变化。

在当前已授权并完整阅读的 `meshing.py` 中，没有找到这种公开 API、callback、
数组尺度场、background mesh 或 metric field。

状态：

```text
NOT FOUND IN AUTHORIZED SOURCE
```

这只表示当前授权源码中未找到，不证明 OFT 整个工具包绝对不存在。

### 3.5 生成后静态 refinement

先生成初始网格，再按固定几何条件细化局部单元。

当前 `meshing.py` 的 `gs_Domain`、`Mesh` 和 `run_triangle` 路径中没有找到生成后
refinement、coarsening 或质量改善入口。

状态：

```text
NOT FOUND IN AUTHORIZED SOURCE
```

### 3.6 动态自适应

根据求解结果、误差估计或时间推进状态反复修改网格。

当前调查文件没有提供该能力；即使 OFT 其他模块存在类似能力，也不属于本轮
LinkMesh 初始二维静态网格生成路径。

状态：

```text
OUTSIDE LINKMESH SCOPE
```

### 3.7 磁面对齐

让节点分布或单元方向与磁通面、磁场或磁坐标相关。

`meshing.py` 当前路径只接收二维几何轮廓和区域尺度，没有接收磁通函数、磁场、
磁坐标或方向 metric。

状态：

```text
OUTSIDE LINKMESH SCOPE
```

---

## 4. 当前 LinkMesh 尺度控制基线

### 4.1 CLI 和配置输入

`src/linkmesh/cli.py` 定义：

```text
--plasma-dx
--vacuum-dx
--outer-dx
```

三个参数均由 argparse 转成 Python `float`。未显式提供时使用 `UNSET`，由
`config.py` 执行：

```text
内建默认值 < linkmesh.in < 显式 CLI
```

`src/linkmesh/config.py::_check_positive_float()` 将 TOML 整数或浮点数规范化为
Python `float`，并要求：

```text
isfinite(dx) and dx > 0
```

单位为 m。

当前配置层只能表达三个标量，不能表达：

- 数组；
- `(R,Z) → dx` 函数；
- callback；
- point-size 对；
- background mesh；
- metric tensor；
- refinement polygon 列表。

### 4.2 LinkMesh Adapter

`src/linkmesh/mesher/oft_adapter.py::generate_mesh()` 将三个标量传给不同策略：

| profile/source | 实际使用的尺度 |
|---|---|
| `single_region + lcfs` | `plasma_dx` |
| `single_region + array_file` | `plasma_dx` |
| `nested_three_region + artificial_outer` | `plasma_dx`、`vacuum_dx`、`outer_dx` |

single-region 路径调用：

```text
domain.define_region("plasma", plasma_dx, "plasma")
domain.add_polygon(polygon, "plasma")
```

nested 路径分别定义：

```text
outer  → outer_dx
plasma → plasma_dx
vacuum → vacuum_dx
```

因此 LinkMesh 当前接入的是：

- 单 Region 常数尺度；
- 多 Region 分区域常数尺度。

LinkMesh 当前没有向 OFT 传递位置相关尺寸表达。

---

## 5. OFT 26.6 相关类和 API

## 5.1 `gs_Domain.define_region()`

源码签名：

```text
define_region(
    self,
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

与尺度直接相关的输入只有 `dx`。

保存位置：

```text
self.region_info[name]["dx"] = dx
```

基础检查：

```text
if (dx is None) or (dx < 0.0):
    raise ValueError(...)
```

源码没有显式 `isinstance(dx, float)`，但后续路径需要执行：

- `dx < 0.0`
- `dx * dx / 2.0`
- `dl[-1] / dx`
- `min(dx, parent_dx)`

因此实现语义要求 `dx` 是支持标量比较和标量算术的数值。普通 Python 函数、
callback 或一般数组不能沿该路径无歧义工作。

精确结论：

- Python `float` 和 NumPy 标量可能满足该标量算术；
- 一般数组会在比较或 `min()` 中产生歧义；
- callable 不支持比较和平方；
- 源码没有 callback 调用点；
- 源码没有把 `dx` 按坐标采样。

状态：

```text
标量 dx：CONFIRMED BY SOURCE
位置相关 dx 对象：NOT FOUND IN AUTHORIZED SOURCE
```

注意：OFT `define_region()` 自身接受 `dx == 0`，因为只拒绝负值；LinkMesh 配置层
更严格，要求有限正数。`dx == 0` 在后续除法路径没有可用的正常网格尺度语义，
本报告不把它视为特殊自适应能力。

## 5.2 `gs_Domain.add_polygon()`

源码签名：

```text
add_polygon(
    self,
    contour,
    name,
    parent_name=None,
    angle_tol=30.0,
    sliver_tol=120.0,
    small_thresh=None,
)
```

尺度数据流：

1. 从 `region_info[name]["dx"]` 取得 `dx`；
2. 初始设置 `dx_curve = dx`；
3. 若存在 parent，设置：

   ```text
   dx_curve = min(dx, parent_dx)
   ```

4. 构造：

   ```text
   Region(
       contour,
       dx,
       dx_curve,
       angle_tol,
       sliver_tol,
       small_thresh,
       region_id,
   )
   ```

因此：

- `_dx_vol` 保存当前 Region 的体内目标尺度；
- `_dx_curve` 保存边界曲线重采样尺度；
- 共享边界倾向采用相邻两 Region 中更细的尺度；
- `add_polygon()` 没有单独公开 `dx_curve` 参数；
- `dx_curve` 不是按 segment 或位置变化的数组。

## 5.3 `gs_Domain.add_annulus()`

源码签名：

```text
add_annulus(
    self,
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

尺度规则：

- inner Region 的内部尺度为 `inner_dx`；
- annulus Region 的内部尺度为 `annulus_dx`；
- inner contour 的曲线尺度取 `min(inner_dx, annulus_dx)`；
- outer contour 的曲线尺度取 `min(annulus_dx, parent_dx)`（若有 parent）。

这是不同 Region 常数尺度和共享边界较细离散的组合，不是单一 Region 内部的位置
相关 size function。

状态：

```text
CONFIRMED BY SOURCE
```

## 5.4 `gs_Domain.add_rectangle()`

源码签名：

```text
add_rectangle(self, rc, zc, w, h, name, parent_name=None, rot=None)
```

该方法只构造四个控制点，再调用 `add_polygon()`，没有新的尺度能力。

## 5.5 `gs_Domain.add_enclosed()`

源码签名：

```text
add_enclosed(self, in_point, name)
```

它追加：

```text
[x, y, region_id, dx² / 2]
```

到：

```text
self._extra_reg_defs
```

并增加该 Region 的 `count`。

直接源码能够确认：

- 它可以额外提交一个 Triangle region definition/seed；
- seed 坐标为二维 `[R,Z]`；
- attribute 为该 Region 当前 ID；
- maximum area 仍由该 Region 的同一个 `dx` 计算；
- 方法没有独立的 `local_dx` 参数；
- 因而它不能通过公开签名单独为额外 seed 指定更细尺度。

是否可通过先后修改 `region_info[name]["dx"]` 等私有状态制造不同 area，既不是
公开契约，也会造成 Region 对象与 `region_info` 尺度不同步，本报告不把它列为合法
组合机制。

此外，在没有内部约束 segment 分隔的同一连通区域内，多个 seed 的 Triangle
传播和覆盖语义尚未通过下层 C 源码及运行探针确认。

状态：

```text
CANDIDATE, PROBE REQUIRED
```

但该候选目前只涉及“额外 seed 的行为”，并未提供不同局部尺度的正式 API。

## 5.6 `Region.__init__()`

源码签名：

```text
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

与尺度相关的内部字段：

```text
self._dx_vol = dx
self._dx_curve = dx_curve if dx_curve is not None else dx
self._small_thresh = dx_curve / 2  # 默认
```

使用方式：

- `_dx_vol` 最终用于 Triangle maximum area；
- `_dx_curve` 用于边界 segment 重采样；
- `_small_thresh` 只用于小特征 warning；
- `_dx_curve / 1.E3` 用于重复/近重复边界控制点 warning 判据；
- 没有把 `_dx_vol` 或 `_dx_curve` 作为坐标函数调用；
- 没有每个点一个尺度或每条 segment 一个尺度的数据结构。

`Region` 虽可直接构造，但 LinkMesh 正式路径通过 `gs_Domain` 创建它；直接依赖
`Region` 内部字段会扩大 OFT 私有接口范围，当前未获批准。

## 5.7 `Mesh.__init__()`

源码签名：

```text
Mesh(region_list, merge_thresh=1.E-4, debug=False, extra_reg_defs=[])
```

它完成：

1. 合并距离小于 `merge_thresh` 的几何控制点；
2. 合并完全或部分重叠的共享 segment；
3. 对共享 segment 更新：

   ```text
   segment_dx = min(existing_dx_curve, region._dx_curve)
   ```

4. 按每条 segment 的单一常数 `dx_curve` 重采样；
5. 建立全局 `_resampled_points` 和 `_resampled_segments`；
6. 为每个 Region 选择一个内部点；
7. 追加：

   ```text
   [seed_R, seed_Z, region_id, region._dx_vol² / 2]
   ```

   到 `_reg_defs`。

这里存在两个不同的尺度用途：

```text
_dx_curve → 约束边界的离散
_dx_vol²/2 → Triangle 区域内部 maximum area
```

共享 segment 使用相邻 Region 边界尺度的最小值，只能让共享边界采用较细离散。
它不能直接证明边界附近内部三角形也按同样空间梯度细化。

## 5.8 `gs_Domain.build_mesh()`

源码签名：

```text
build_mesh(
    self,
    debug=False,
    merge_thresh=1.E-4,
    require_boundary=True,
    setup_only=False,
    cubit_path=None,
    cubit_gradation=1.05,
)
```

正式 Triangle 路径：

```text
self.mesh = Mesh(
    self.regions,
    debug=debug,
    extra_reg_defs=self._extra_reg_defs,
    merge_thresh=merge_thresh,
)
self._r, self._lc, self._reg = self.mesh.get_mesh()
```

`merge_thresh` 是点合并阈值，单位 m，不是目标单元尺寸。

`cubit_path` 是另一条网格后端路径。LinkMesh 正式契约禁止引入第二网格引擎，
因此它与本轮候选架构无关。

## 5.9 `Mesh.get_mesh()`

它构造：

```text
alpha = {
    "vertices": self._resampled_points,
    "segments": resampled_flat,
    "regions": self._reg_defs,
}
beta = run_triangle(alpha)
```

形状和语义：

| 字段 | shape | Python/OFT dtype | 单位/语义 |
|---|---:|---|---|
| `vertices` | `(P,2)` | 后续转 `float64` | `[R,Z]`，m |
| `segments` | `(S,2)` | 后续转 `int32` | 0-based 点索引 |
| `regions` | `(K,4)` | 后续转 `float64` | `[seed_R, seed_Z, attribute, maximum_area]` |
| maximum area | 标量/seed | `float64` | `dx²/2`，m² |

输出：

```text
vertices
triangles
triangle_attributes
```

并将 triangle attributes 转为 `int32` 的 `reg`。

## 5.10 `run_triangle()`

源码签名：

```text
run_triangle(alpha)
```

输入转换：

```text
vertices → contiguous float64
segments → contiguous int32
regions → contiguous float64
```

设置 `triangle_struct`：

```text
pointlist
numberofpoints
segmentlist
numberofsegments
regionlist
numberofregions
```

调用选项：

```text
pqaAzQ
```

输出转换：

```text
vertices            → (N,2)
triangles           → (T,3)
triangle_attributes → (T,)
```

当前 `run_triangle()` 没有设置以下可见字段：

```text
trianglearealist
pointattributelist
pointmarkerlist
trianglelist（输入）
```

`triangle_struct` 中虽然声明了 `trianglearealist`，但仅凭字段名不能确认其完整语义。
当前 OFT `run_triangle()` 路径没有向它传值。

状态：

```text
trianglearealist 字段存在：PRESENT BUT NOT EXPOSED
其可否支持 LinkMesh 所需局部尺度：CANDIDATE, PROBE REQUIRED
```

在读取 Triangle C 实现前，不得把该字段写成可用的正式 refinement API。

---

## 6. 完整尺度数据流

## 6.1 当前已确认调用链

```text
CLI:
  --plasma-dx / --vacuum-dx / --outer-dx
  Python float，单位 m
    ↓
config.load_effective_config():
  有限正数校验
  EffectiveConfig.plasma_dx/vacuum_dx/outer_dx
    ↓
oft_adapter.generate_mesh():
  按 profile/boundary_source 选择策略
    ↓
gs_Domain.define_region(name, dx, type):
  region_info[name]["dx"] = 标量 dx
    ↓
gs_Domain.add_polygon()/add_annulus()/add_rectangle():
  创建 Region
  Region._dx_vol = dx
  Region._dx_curve = dx 或相邻 Region dx 的最小值
    ↓
gs_Domain.build_mesh():
  Mesh(regions, extra_reg_defs, merge_thresh)
    ↓
Mesh.__init__():
  按 _dx_curve 重采样边界 segment
  每个 Region 构造一个：
  [seed_R, seed_Z, region_id, _dx_vol²/2]
  并追加可选 _extra_reg_defs
    ↓
Mesh.get_mesh():
  alpha["vertices"] = (P,2)
  alpha["segments"] = (S,2)
  alpha["regions"] = (K,4)
    ↓
run_triangle(alpha):
  triangle_struct.pointlist = float64
  triangle_struct.segmentlist = int32
  triangle_struct.regionlist = float64
  setting_string = "pqaAzQ"
    ↓
oft_triangle_lib.triangulate(...)
    ↓
【当前证据中断：Triangle C 内部 area/region 传播和 refinement 实现待补充源码】
    ↓
run_triangle 返回：
  vertices (N,2)
  triangles (T,3)
  triangle_attributes (T,)
    ↓
Mesh.get_mesh():
  triangle_attributes.astype(int32) → reg
    ↓
gs_Domain.build_mesh():
  pts/lc/reg
    ↓
oft_adapter.mesh_from_oft_domain():
  验证并规范化为 nodes/triangles/region_ids
  从捕获 Region._resampled_points 获取 outer_boundary
    ↓
Mesh2D:
  nodes (N,2) float64
  triangles (T,3) int32，0-based
  region_ids (T,) int32
  outer_boundary (B,2) float64
```

## 6.2 各层接口性质

| 层 | 接口性质 | LinkMesh 是否使用 | 对空间变密度的直接作用 |
|---|---|---:|---|
| CLI/config 三个 dx | LinkMesh 公共用户接口 | 是 | 只能表达标量 |
| `generate_mesh()` | LinkMesh 内部公共函数 | 是 | 只转发标量 |
| `gs_Domain.define_region()` | OFT Python 公共接口 | 是 | 每 Region 一个 dx |
| `add_polygon/add_annulus` | OFT Python 公共接口 | 是 | 建立 Region；共享边界取较细 dx |
| `Region._dx_vol/_dx_curve` | OFT 私有字段 | 间接使用 | 都是标量 |
| `Mesh` | OFT 内部实现 | 间接使用 | 将标量转边界采样和 area |
| `_reg_defs` | OFT 私有内部数据 | 否 | `(K,4)` 常数 seed area |
| `run_triangle()` | OFT Python 网格入口 | 间接使用 | 没有 size callback |
| `triangle_struct` | OFT ctypes/C 绑定结构 | 间接使用 | `trianglearealist` 未暴露到当前输入 |
| `Region._resampled_points` | LinkMesh 版本锁定兼容接口 | 是 | 只恢复实际外边界，不控制内部尺度 |
| `Mesh2D` | LinkMesh 正式统一对象 | 是 | 保存结果，不控制生成尺度 |

---

## 7. `dx` 与 `dx_curve` 的精确语义

## 7.1 `dx`

直接源码语义：

```text
Region._dx_vol = dx
Triangle maximum_area = dx² / 2
```

`dx` 是 Region 级标量目标长度尺度，单位 m。它不是三角形边长的严格保证；OFT 将其
转换为最大面积约束，Triangle 仍同时受几何、质量角约束和边界离散影响。

当前源码没有：

- `dx(R,Z)` 调用；
- 每节点 `dx`；
- 每三角形 `dx`；
- 每 seed 独立 `dx` 的公开参数；
- size callback；
- metric tensor。

## 7.2 `dx_curve`

直接源码语义：

- 保存为 `Region._dx_curve`；
- 用于把每条边界 segment 按弧长划分；
- 当 `int(segment_length/dx_curve) >= 2` 时插入等弧长中间点；
- 用于 small-feature 和 repeated-point warning 阈值；
- 共享 segment 的尺度取相关 Region `_dx_curve` 的最小值；
- 不直接写入 Triangle region maximum area。

因此：

```text
dx_curve 控制边界离散；
dx 控制 Region 的 Triangle maximum area。
```

两者可能间接共同影响最终边界附近网格，但不能把 `dx_curve` 的边界点增加解释为
“区域内部已获得位置相关尺度”。

## 7.3 当前公开路径是否允许二者独立设置

`Region.__init__()` 本身接受独立 `dx_curve`，但 `gs_Domain.add_polygon()` 和
`add_annulus()` 没有公开独立 `dx_curve` 参数，而是根据当前 Region 和 parent/annulus
的 `dx` 自动计算。

所以在 LinkMesh 当前使用的 `gs_Domain` 公共路径中：

- 用户不能直接指定任意 `dx_curve`；
- `dx_curve` 主要由相邻 Region 的常数尺度决定；
- 直接构造 `Region` 或修改私有字段不属于当前批准接口。

---

## 8. Triangle area constraint 的构造方式

### 8.1 每个普通 Region 的输入

`Mesh.__init__()` 对每个 Region 生成一个内部点，并追加：

```text
[
    in_point[0],
    in_point[1],
    region._id,
    region._dx_vol * region._dx_vol / 2.0,
]
```

因此每个普通 Region 在 OFT Python 层有：

- 一个 region seed；
- 一个 region attribute；
- 一个常数 maximum area。

### 8.2 额外 seed

`add_enclosed()` 可增加 `_extra_reg_defs`，每条仍为：

```text
[R, Z, region_id, region_dx²/2]
```

该 API 没有独立 local area 参数，所以额外 seed 默认仍使用同一 Region 的同一个
常数 area。

### 8.3 “每个 Region 是否只能提交一个 area constraint”的精确回答

分两层回答：

1. 普通 Region 构造路径：
   每个 `Region` 对象只自动生成一个 seed 和一个常数 area constraint。

2. `add_enclosed()`：
   可以为同一 Region ID 追加多个 seed，但这些 seed 仍从同一个
   `region_info[name]["dx"]` 计算相同 area；当前公开签名不能给每个 seed 指定不同
   area。

因此，当前 OFT 公共 Python API 没有直接提供“同一个 Region 内多个不同常数 area”
的正式表达。

Triangle 对同一连通区内多个 seed 的覆盖规则仍需读取 C 实现并运行探针。

---

## 9. 位置相关尺度能力调查

| 候选能力 | 调查结果 | 分类 |
|---|---|---|
| Region 级标量 `dx` | 明确存在 | CONFIRMED BY SOURCE |
| 多 Region 不同常数 `dx` | 明确存在 | CONFIRMED BY SOURCE |
| 边界 `dx_curve` | 明确存在，只直接控制 segment 重采样 | CONFIRMED BY SOURCE |
| `dx(R,Z)` callback | 当前授权源码未找到 | NOT FOUND IN AUTHORIZED SOURCE |
| 每点 size 数组 | 当前授权源码未找到 | NOT FOUND IN AUTHORIZED SOURCE |
| background sizing mesh | 当前授权源码未找到 | NOT FOUND IN AUTHORIZED SOURCE |
| metric/sizing field | 当前授权源码未找到 | NOT FOUND IN AUTHORIZED SOURCE |
| 每 segment 独立公开尺度 | `gs_Domain` 公共 API 未找到 | NOT FOUND IN AUTHORIZED SOURCE |
| 每 seed 独立 area 参数 | `add_enclosed()` 未暴露 | NOT FOUND IN AUTHORIZED SOURCE |
| 多 Region 模拟粗细区 | 源码结构允许不同 Region dx | REGION-BASED APPROXIMATION |
| `trianglearealist` | ctypes 结构有字段，当前 `run_triangle()` 不设置 | PRESENT BUT NOT EXPOSED |
| Triangle 下层局部 refinement | 当前下层实现未完成阅读 | CANDIDATE, PROBE REQUIRED |

第一轮静态结论是：

> 在已授权并完整阅读的 OFT 26.6 `meshing.py` 公共路径中，没有找到单一 Region
> 内部由位置函数、数组、callback、background mesh 或 metric field直接控制目标
> 尺度的正式能力。

这不是对整个 OFT 包或 Triangle 全部能力的否定。

---

## 10. refinement/adaptation 能力调查

### 10.1 当前 `meshing.py` 路径

没有找到以下公开方法：

- `refine_mesh(...)`
- `adapt_mesh(...)`
- `coarsen_mesh(...)`
- `improve_mesh(...)`
- 基于误差的循环；
- 基于已生成 triangle area 的二次调用；
- 生成后 per-triangle area 更新；
- 求解场驱动的 size function。

当前 `build_mesh()` 对正式 Triangle 路径只调用一次：

```text
Mesh(...)
→ Mesh.get_mesh()
→ run_triangle(alpha)
```

状态：

```text
NOT FOUND IN AUTHORIZED SOURCE
```

### 10.2 `trianglearealist` 的证据边界

`triangle_struct` 声明了 `trianglearealist`，但 `run_triangle()` 没有设置该字段。
只凭字段名不能确认：

- 它用于输入还是输出；
- 是否要求输入已有 triangles；
- 是否与 `r`/`a` 等 Triangle switch 组合；
- 是否支持一次初始生成中的局部 area；
- 是否要求二次 refinement；
- 内存所有权和长度规则。

所以只能记录为：

```text
PRESENT BUT NOT EXPOSED
```

若 Triangle C 证据确认它可接收每三角形 area，则也更可能属于“已有网格后的静态
refinement 候选”，而不是首次生成时的连续位置 size function。该判断目前仍需源码。

### 10.3 动态自适应和磁面对齐

即使其他 OFT 模块存在 adaptation 或误差驱动机制，它也不能未经独立调查直接接入
LinkMesh 当前静态预处理链。

分类：

```text
OUTSIDE LINKMESH SCOPE
```

---

## 11. 多 Region 近似局部加密的可能性和语义风险

### 11.1 源码上可组合的机制

OFT 允许：

- 定义多个 Region；
- 每个 Region 使用不同标量 `dx`；
- 通过 polygon、annulus、rectangle 和 parent 关系构造几何；
- 在共享 segment 上使用较细的 `dx_curve`；
- 将每个 Region 的 ID 和 `dx²/2` 交给 Triangle。

所以可以把计算域划分为粗细不同的多个几何 Region，以近似局部加密。

分类：

```text
REGION-BASED APPROXIMATION
```

### 11.2 它不是真正的位置相关 size function

这种方案的尺度是分片常数：

```text
dx(R,Z) = dx_i,  (R,Z) 位于 Region i
```

尺度变化依赖显式 Region 边界，不是连续 callback 或 background field。

### 11.3 正式 region 标签风险

OFT 输出 `reg` 来自 Triangle triangle attributes。不同 Region 会形成不同正式
region ID，并被 LinkMesh 原样保存到：

```text
Mesh2D.region_ids
```

因此密度分区可能同时成为正式拓扑/区域标签，而不只是隐藏的网格生成提示。

不能在未调查下游语义前自动：

- 删除 region ID；
- 压平成一个 ID；
- 把多个 OFT Region 宣称为一个物理区域；
- 把多个 Region 自动映射为多个 M3D-C1 geometric face；
- 假设 conforming topology 等于 M3D-C1 C1 连续。

### 11.4 是否能保持一个物理区域或一个 geometric face

从当前 `Mesh2D` 角度，多 region ID 可以被保存；但当前 M3D-C1 正式路径要求
single-region、single-face。

存在一个待调查候选：

- OFT Region 仅用于生成阶段密度分区；
- 最终所有三角形仍分类到同一个 M3D-C1 geometric face；
- OFT `region_ids` 不作为 face tag。

当前 SMB Writer 本来就禁止从 `region_ids` 自动推导 face tag，但正式 M3D-C1
输入验证是否接受多个 `region_ids`、以及把它们压到一个 face 是否保持正确物理和
C1 语义，必须由单独的多区域/C1 调查裁决。

当前状态：

```text
CANDIDATE, PROBE REQUIRED
```

本轮不能宣称可以保持 single-region/single-face。

### 11.5 几何和拓扑风险

多 Region 近似还需验证：

- 共享界面是否严格 conforming；
- 是否共享同一节点和边；
- 是否出现重复点、裂缝、重叠或非流形边；
- 不同 `dx_curve` 如何改变共享界面；
- 内部密度边界是否进入 `outer_boundary`；
- Region seed 是否落入正确子域；
- region attribute 是否覆盖预期区域。

这些属于下一阶段多 Region 最小探针和专门调查，不由本报告静态外推。

---

## 12. 候选服务器最小探针

所有探针必须在服务器 pip 安装的 OFT 26.6 上运行，并记录：

- Python 和 openfusiontoolkit 版本；
- OFT 实际导入路径；
- 调用的 API；
- 完整 stdout/stderr；
- OFT/Triangle warning；
- 输入几何和尺度；
- 原始 `pts/lc/reg`；
- 统计结果；
- PNG 仅作辅助。

不得通过 Cubit、Gmsh、Python `triangle` 包或其他剖分器替代
`gs_Domain.build_mesh()` 的默认 `liboft_triangle` 路径。

### 12.1 探针 A：单一常数 `dx` 基准

#### API

```text
gs_Domain()
define_region("plasma", 0.10, "plasma")
add_polygon(boundary, "plasma")
build_mesh()
```

#### 输入几何

使用一个简单、顺时针或逆时针均可由 OFT 正常处理的非退化矩形或平滑凸 polygon，
例如尺度约 `1 m × 1 m`。所有对照案例保持同一外边界。

#### 尺度

```text
dx = 0.10 m
```

#### 预期观察

- 一个 region ID；
- 内部三角形面积总体受 `0.10²/2 = 0.005 m²` 约束；
- 建立节点数、三角形数、面积和边长基线。

#### 失败条件

- Triangle 失败；
- 非正 region ID；
- 越界、重复顶点、退化三角形；
- 外边界改变；
- 出现非流形边。

### 12.2 探针 B：中心局部加密

由于当前公开源码没有单一 Region 的 local-size API，应分两步执行。

#### B1：负向接口探针

尝试确认以下非标量输入被明确拒绝，而不是静默产生错误语义：

- callable `dx`；
- 长度大于 1 的 NumPy 数组 `dx`。

该探针只验证当前 API 的标量边界，不是功能实现。

#### B2：Region-based approximation

API 候选：

```text
define_region("plasma", coarse_dx, "plasma")
define_region("fine_core", fine_dx, 可合法表达的非 plasma Region 类型)
add_polygon(outer_boundary, "plasma")
add_polygon(center_boundary, "fine_core", parent_name="plasma")
build_mesh()
```

具体 Region 类型和 parent/child 合法语义必须先由 OFT 多区域探针确认；若无法在
不误表达物理类型的情况下构造，应停止，不得随意选择 `vacuum` 冒充纯密度区。

尺度建议：

```text
coarse_dx = 0.20 m
fine_dx   = 0.04 m
```

#### 预期观察

- 中心子域 triangle area 显著小于远场；
- 同时出现多个 region ID；
- 共享界面 conforming。

#### 失败条件

- 只能通过非法私有状态修改完成；
- Region 类型改变物理语义；
- 中心子域无显著面积差异；
- 裂缝、重叠、非流形或错误 region attribute。

### 12.3 探针 C：边界附近局部加密

应同时区分“边界点变多”和“内部单元真正变细”。

#### C1：边界曲线离散对照

在不改变内部 `dx_vol` 的理想对照中，只改变局部或共享边界的 `dx_curve`。但
`gs_Domain` 当前公共 API 没有独立的局部 `dx_curve` 参数。

因此可采用以下二选一：

1. 若追加源码证明存在公共边界尺度 API，使用该 API；
2. 否则只做受控诊断探针，直接构造 `Region`，并明确标记为私有实现探针，不作为
   LinkMesh 候选接口。

观察：

- outer boundary 点数；
- 边界 segment 长度；
- 距边界窄带内三角形面积；
- 远场面积。

只有边界点数增加，而窄带内部面积没有稳定下降时，结论只能是边界重采样，不是内部
局部加密。

#### C2：边界窄带 Region 近似

构造一个与外边界相邻的细尺度窄带 Region，粗区保持较大 `dx`。

尺度建议：

```text
coarse_dx = 0.20 m
boundary_band_dx = 0.04 m
```

必须检查：

- 窄带是否形成额外 region ID；
- 内外接口是否 conforming；
- 细化是否扩展到窄带内部，而不只是边界点增加。

### 12.4 探针 D：同一物理域双尺度对照

#### 目标

验证 Region-based approximation 能否在同一个外边界内部形成明显粗细两区，并量化
其 region 语义代价。

#### API 候选

采用两个相邻或嵌套 Region：

```text
coarse_dx = 0.20 m
fine_dx   = 0.04 m
```

要求：

- 外边界与基准完全相同；
- 粗细区域几何面积尽量相近；
- 不使用第二网格引擎；
- 不修改 OFT 内部算法。

#### 预期结果

如果机制有效：

- fine Region 面积分位数明显低于 coarse Region；
- 两区有不同 region ID；
- 共享界面节点和边一致；
- 全局网格合法。

如果只有共享边界变密，而区域内部面积无显著差异，则不能认定分区域体网格尺度生效。

### 12.5 四组探针共同保存内容

每组至少保存：

- OFT 版本与导入路径；
- 输入边界点；
- Region 定义、类型、parent 关系和 dx；
- `domain.region_info` build 前后内容；
- `pts`、`lc`、`reg`；
- 节点数和三角形数；
- region ID 集合和每区 triangle 数；
- triangle area 最小值、最大值、P01、P10、P50、P90、P99；
- 局部目标区和远场区的面积分布；
- 三边边长分布；
- 最小角；
- 长宽比或等价质量指标；
- 重复点和重复 triangle；
- 退化 triangle；
- boundary edge；
- 非流形 edge；
- 共享界面节点/边检查；
- OFT/Triangle warning；
- PNG。

### 12.6 如何区分边界变密与内部局部加密

不能只比较总节点数。至少应定义：

- 边界窄带，例如距外边界小于固定距离的 triangle centroid；
- 目标细化区；
- 远场对照区。

然后比较：

```text
target_area_quantiles / far_field_area_quantiles
target_edge_quantiles / far_field_edge_quantiles
```

只有目标区内部 triangle area 和 edge length 稳定显著下降，且不是单纯由更多边界点
造成的单层小单元，才可认定内部局部加密有效。

---

## 13. 对 LinkMesh 的潜在影响

以下均为影响分析，不是实施决定。

### 13.1 如果 OFT 直接支持位置相关尺度

LinkMesh 至少需要一种可验证、可序列化的用户输入表达，例如：

- 少量局部 refinement point；
- polygon refinement zone；
- OFT 已有的正式 sizing field 参数。

不得在 OFT 没有正式表达时自行发明任意 Python callback DSL。

这会涉及：

- 蓝图先行更新；
- `EffectiveConfig` 新字段；
- TOML schema 和 CLI 是否新增入口；
- 配置类型、路径和单位校验；
- OFT Adapter 映射；
- 新测试和真实探针。

当前均未批准。

### 13.2 是否需要修改 `Mesh2D`

如果局部尺度只改变最终节点和三角形分布，而输出仍为：

```text
nodes
triangles
region_ids
outer_boundary
```

则 `Mesh2D` 理论上无需修改。

只有下游确实需要保存 sizing field、refinement provenance 或内部密度区语义时才可能
需要新字段；当前没有这种需求，YAGNI 原则下不建议修改。

### 13.3 是否需要修改 TRIMEG HDF5 Writer

TRIMEG Writer 只消费最终网格和 `outer_boundary`。如果：

- topology 合法；
- `outer_boundary` 契约不变；
- 不新增目标格式字段；

则 Writer 理论上无需修改。

TRIMEG 当前不写 `region_ids`，所以多 Region 密度分区不会自动进入 HDF5。是否允许
丢弃该生成阶段语义必须由正式蓝图裁决，不能由 Writer 自行决定。

### 13.4 是否需要修改 M3D-C1 TXT/SMB Writer

若 OFT 能在保持单一 Region ID 的情况下直接做位置相关尺度，M3D-C1 的
single-region/single-face 模型可能无需变化。

若只能通过多个 OFT Region：

- 当前 SMB Writer 的 single-region 输入校验可能拒绝；
- 多个 region ID 是否仍分类到一个 geometric face 需要 C1 调查；
- 不得自动创建多个 face；
- 不得自动压平 region ID；
- TXT 与 SMB 必须继续共享同一个 `M3DC1ModelSpec`。

当前不能确认 Writer 无需修改。

### 13.5 helper exchange schema

如果最终仍是同一个 single-face `Mesh2D`，且 classification 不变，则 exchange
schema 理论上无需修改。

如果正式批准多 face、内部 geometric edge/loop 或物理界面，schema、ModelSpec、
TXT、classification 和 helper 都可能需要升级。但这超出本轮范围。

### 13.6 是否会引入多 `region_id`

- 真正的位置相关 size function：不一定。
- Region-based approximation：会产生多个正式 region ID 的风险很高，当前源码路径
  明确把各 Region attribute 写入 `reg`。

### 13.7 是否能保持 M3D-C1 single-region/single-face

- 直接位置相关尺度：候选上可能保持。
- 多 Region 近似：尚未确认，必须等待 OFT 多区域 topology 和 M3D-C1 C1 调查。

### 13.8 `outer_boundary`

只要最外层 Region 捕获和 `_resampled_points` 数据链保持不变，内部局部尺度不应改变
`outer_boundary` 的语义：

```text
Triangle 输入前的有序最外层计算域几何边界
```

但更细的外边界 `dx_curve` 可能改变其点数。方向、简单闭环、独立副本和 Steiner 点
隔离契约仍必须保持。

### 13.9 OFT 26.6 私有接口锁定

若候选实现需要读取或修改以下私有对象：

- `Region._dx_vol`
- `Region._dx_curve`
- `Mesh._reg_defs`
- `Mesh._resampled_segments`
- `triangle_struct.trianglearealist`

则会扩大当前唯一获准的私有接口范围。现有批准只覆盖获取
`outer_region._resampled_points`，不能自动扩展。

任何新增私有依赖都必须先更新蓝图并重新执行 OFT 版本核对。

### 13.10 与当前禁止事项的关系

直接实现以下任一方案都会触发当前蓝图变更门槛：

- 新 CLI/TOML 尺度表达；
- OFT 私有 size 接口；
- 多 Region 作为密度分区；
- 多 face；
- exchange schema 修改；
- 第二网格引擎；
- 复制 Triangle/OFT refinement 算法。

本轮没有执行这些变化。

---

## 14. 已确认事实

以下结论属于 `CONFIRMED BY SOURCE`：

1. LinkMesh 当前只向 OFT 传递有限正数标量 dx。
2. `gs_Domain.define_region()` 为每个 Region 保存一个 `dx`。
3. 后续代码对 `dx` 执行标量比较、除法、平方和 `min()`，没有 callback 调用点。
4. `Region._dx_vol` 是 Region 内部尺度。
5. `Region._dx_curve` 是边界 segment 重采样尺度。
6. `add_polygon()` 的 `dx_curve` 初始等于本 Region `dx`；有 parent 时取二者最小值。
7. `add_annulus()` 的共享边界曲线尺度取相邻 Region dx 的较小值。
8. `Mesh.__init__()` 按 `_dx_curve` 对边界 segment 重采样。
9. `Mesh.__init__()` 为每个普通 Region 生成一个内部 seed。
10. seed 数据为 `[R,Z,region_id,dx²/2]`。
11. `Mesh.get_mesh()` 向 `run_triangle()` 传递 vertices、segments、regions。
12. `run_triangle()` 将它们分别转为 contiguous `float64`、`int32`、`float64`。
13. 当前 OFT Python 路径没有传递位置相关 size callback、background mesh 或 metric。
14. `add_enclosed()` 可增加 seed，但没有独立 local dx 参数。
15. `triangle_struct` 声明 `trianglearealist`，当前 `run_triangle()` 没有设置它。
16. 不同 OFT Region 的不同 dx 会同时携带不同 Region attribute/ID。
17. LinkMesh 将 OFT `reg` 原样保存为 `Mesh2D.region_ids`。
18. `outer_region._resampled_points` 只服务于 `outer_boundary` 恢复，不是内部
    空间变尺度接口。

---

## 15. 待服务器确认事项

以下内容不能仅凭当前静态源码写成已验证行为：

1. `pqaAzQ` 在服务器实际 Triangle 绑定中的完整 switch 语义。
2. `dx²/2` 是否在所有简单案例中形成预期最大面积。
3. 同一连通区内多个 region seed 的覆盖顺序和冲突行为。
4. `add_enclosed()` 是否有可重复的实用场景。
5. 多 Region 不同 dx 的共享界面是否严格 conforming。
6. 多 Region 是否出现裂缝、重复点、重叠或非流形边。
7. 边界 `dx_curve` 变细后，内部面积变化是否只限于边界附近。
8. `trianglearealist` 是否可作为输入，以及所需 switches、shape 和生命周期。
9. Triangle 是否支持已有网格后的 per-triangle area refinement。
10. OFT 其他未授权模块是否有正式 refinement/adaptation API。
11. 多 OFT Region 能否在 M3D-C1 下保持一个 geometric face 和所需 C1 语义。
12. 真实 OFT warning、节点数、triangle 数和质量分布。

---

## 16. 与当前蓝图的冲突

本轮没有发现当前 LinkMesh 实现与蓝图之间的直接冲突。

源码调查反而支持当前蓝图中的以下边界：

- 当前已支持全局常数 dx；
- 当前已支持分区域常数 dx；
- 单一区域静态空间变密度仍处于调查状态；
- 多 Region topology 和 M3D-C1 C1 语义必须单独调查；
- 不得把不同 Region 常数 dx 写成真正的位置相关 size function；
- 不得把边界重采样写成内部局部加密；
- 不得把静态 refinement 写成动态自适应；
- OFT 私有接口必须按 26.6 版本锁定；
- 调查完成前不得修改 Writer/helper 契约。

潜在的未来冲突点仅存在于候选实现阶段：

- 若新增位置相关尺度输入，需要先更新蓝图；
- 若依赖额外私有字段，需要扩大版本锁定契约；
- 若多 Region 进入 M3D-C1，需要先解决 single-region/single-face 和 C1 语义。

---

## 17. 候选架构

### 17.1 候选 A：OFT 正式位置相关 sizing API

适用前提：

- 追加源码或服务器探针证明 OFT 26.6 已有公共 sizing API；
- 不复制 OFT/Triangle 算法；
- 不引入第二网格引擎。

潜在最小数据流：

```text
配置中的有限局部尺度描述
→ OFT Adapter
→ OFT 正式 sizing API
→ Triangle
→ 原有 Mesh2D
```

这是最优候选，但当前：

```text
NOT FOUND IN AUTHORIZED SOURCE
```

### 17.2 候选 B：Triangle 已有但 OFT 未暴露的 area/refinement 接口

适用前提：

- Triangle C 源码证明接口语义；
- OFT 26.6 绑定可以安全使用；
- 不需要复制内部算法；
- User 批准扩展 OFT Adapter 和版本锁定接口。

当前分类：

```text
PRESENT BUT NOT EXPOSED
```

风险：

- 可能只支持已有 mesh 的二次 refinement；
- 可能需要 OFT 当前未管理的内存；
- 可能改变 `run_triangle()` 契约；
- 可能成为维护 OFT 私有分支，触发停止条件。

### 17.3 候选 C：多个 Region 的分片常数近似

数据流：

```text
一个物理计算域
→ 显式划分多个 OFT Region
→ 每区常数 dx
→ conforming Triangle mesh（待验证）
→ 多 region_id Mesh2D
```

分类：

```text
REGION-BASED APPROXIMATION
```

优点：

- 完全沿用当前可见 OFT Region/area 数据流；
- 不需要第二网格引擎。

风险：

- 产生正式 region ID；
- 需要额外内部几何边界；
- 不是连续位置 size function；
- M3D-C1 single-face/C1 语义未确认；
- 可能需要修改当前 single-region 验证。

### 17.4 候选 D：生成后 refinement

只有在追加源码证明 OFT/Triangle 有正式二次 refinement API 后才可评估。

当前分类：

```text
POST-MESH CANDIDATE
```

当前不建议设计 LinkMesh 接口。

---

## 18. 是否建议进入最小运行探针

结论：

```text
建议进入服务器最小运行探针，但只建议执行能力验证，不建议进入业务实现。
```

优先顺序：

1. 运行单 Region 常数 dx 基准；
2. 运行多个 Region 不同 dx 的中心和双尺度探针；
3. 严格检查共享界面 topology；
4. 比较边界重采样与内部面积分布；
5. 在读取 Triangle C 实现后，再决定是否测试 `trianglearealist` 或二次 refinement；
6. 结合 M3D-C1 C1 调查决定多 Region 是否有业务价值。

---

## 19. 是否建议进入实现

当前结论：

```text
不建议进入实现。
```

原因：

1. 当前没有找到单一 Region 的正式位置相关 size API。
2. Triangle 下层 area/refinement 语义尚未完成源码追踪。
3. 多 Region 方案只是分片常数近似。
4. 多 Region 会引入 region 标签语义。
5. M3D-C1 single-face/C1 兼容性尚未确认。
6. 尚无服务器运行探针证明局部加密效果和 topology。
7. 当前实现会提前触发 CLI、配置、Adapter 或私有接口契约变更。

---

## 20. 需要追加的只读文件权限

为完成 Triangle 下层调用链，需要把以下文件的真实内容或至少所列符号的完整连续源码
添加到聊天中。只需只读，不提出修改。

### 20.1 OFT ctypes 库绑定

完整路径：

```text
TOKAMAKER\OpenFUSIONToolkit\src\python\OpenFUSIONToolkit\_interface.py
```

需要符号：

- `oft_triangle_lib` 的定义；
- 动态库加载位置；
- `ctypes_subroutine`；
- `c_struct`；
- `c_double_ptr`、`c_int_ptr`；
- 与 `triangulate` 符号绑定有关的连续代码。

目的：

- 确认 Python 调用的具体动态库和符号；
- 确认参数/返回值 ABI；
- 确认是否存在其他未暴露 Triangle 入口。

证据边界：

- 该文件尚未提供完整源码；
- 即使读取本地参考文件，也需单独标记尚未与服务器安装文件逐内容比对。

### 20.2 Triangle C 实现

完整路径：

```text
TOKAMAKER\OpenFUSIONToolkit\src\ext_libs\triangle.c
```

需要符号和连续调用链：

- `triangulate(...)`；
- switch 解析中 `p`、`q`、`a`、`A`、`z`、`Q` 的处理；
- `regionlist` 的读取；
- region attribute 传播；
- maximum area constraint 传播；
- 同一连通区多个 region seed 的处理；
- `trianglearealist` 的输入/输出语义；
- refinement/quality enforcement 相关实际调用；
- `triangulateio` 或等价结构中相关字段的契约。

目的：

- 关闭 `run_triangle()` 以下的调用链中断；
- 判断下层是否存在 OFT 未暴露的局部 area/refinement 能力；
- 避免仅凭字段名猜测。

证据边界：

- 当前只获得该大型文件的摘要，不能据此确认算法语义；
- 本地文件若未与服务器实际构建来源比对，只能作为 OFT 26.6 参考源码证据；
- 最终行为仍需服务器探针。

### 20.3 可能的 OFT C/C++ bridge

若 `_interface.py` 显示 `oft_triangle_lib.triangulate` 并非直接来自
`src/ext_libs/triangle.c`，还需追加实际导出该符号的 bridge 文件。

在取得 `_interface.py` 和构建符号证据前，本报告不猜测具体 bridge 路径。

---

## 21. 第一轮最终结论

### 21.1 OFT 尺度数据流是否完整追踪

已完整追踪：

```text
LinkMesh CLI/config
→ oft_adapter
→ gs_Domain
→ Region
→ Mesh
→ run_triangle
→ triangle_struct
→ oft_triangle_lib.triangulate 调用边界
→ pts/lc/reg
→ Mesh2D
```

未完整追踪：

```text
Triangle C 内部 switch、region/area 传播和 refinement 算法
```

### 21.2 `dx` 控制什么

`dx` 是每个 OFT Region 的标量内部目标长度尺度，最终转换为：

```text
maximum_area = dx² / 2
```

并随 region seed 提交给 Triangle。

### 21.3 `dx_curve` 控制什么

`dx_curve` 是 Region 边界 segment 的标量重采样尺度。共享 segment 使用相关
Region 中更细的值。它直接控制边界点和 segment 密度，不等同于内部位置相关尺度。

### 21.4 是否找到单一区域位置相关尺度能力

没有在当前已授权并完整阅读的 OFT 26.6 `meshing.py` 中找到：

- `dx(R,Z)`；
- size callback；
- pointwise size；
- background mesh；
- metric field。

分类：

```text
NOT FOUND IN AUTHORIZED SOURCE
```

### 21.5 是否找到生成后 refinement 或 adaptation

`meshing.py` 当前公共路径中未找到。

`triangle_struct.trianglearealist` 存在但未由 `run_triangle()` 设置，其语义仍需
Triangle C 源码。

分类：

```text
PRESENT BUT NOT EXPOSED / POST-MESH CANDIDATE
```

不得写成已验证能力。

### 21.6 是否只能通过多个 Region 近似局部加密

当前已确认的 OFT Python 公共机制中，唯一明确可组合的粗细分区是：

```text
多个 Region + 每 Region 一个常数 dx
```

分类：

```text
REGION-BASED APPROXIMATION
```

它不是真正的位置相关 size function，并可能产生多个正式 region ID。

### 21.7 源码确认与探针待确认边界

源码已确认：

- 标量 dx；
- dx_curve 边界重采样；
- Region seed 的 `(R,Z,attribute,dx²/2)`；
- 多 Region 常数尺度；
- 当前 `run_triangle()` 不传 size callback 或 triangle area list。

运行探针待确认：

- Triangle 对 area 的实际行为；
- 多 seed 行为；
- 多 Region 局部加密效果；
- 共享界面 topology；
- warning 和网格质量；
- 下层 refinement 能力；
- M3D-C1 单 face/C1 兼容性。

### 21.8 是否发现与当前蓝图冲突

没有发现当前实现或事实状态与蓝图直接冲突。

### 21.9 是否建议进入服务器最小探针

建议。应先验证全局基准和多 Region 分片常数近似，再调查 Triangle 下层候选。

### 21.10 是否建议进入实现

不建议。源码和运行证据尚不足，且多 Region 与 M3D-C1 语义风险未关闭。

### 21.11 是否需要补充只读权限

需要。应补充 `_interface.py` 的 Triangle 库绑定和 `triangle.c` 的实际
`triangulate`、region、area、refinement 调用链。

### 21.12 修改范围确认

本轮报告只填充：

```text
docs/linkmesh/OFT_26_6_Variable_Mesh_Density_Investigation.md
```

没有提出或实施对以下内容的修改：

- LinkMesh 业务源码；
- OFT/TOKAMAKER 参考源码；
- Triangle；
- M3D-C1；
- SCOREC/PUMI；
- tests/examples；
- `LinkMesh_Architecture_Plan.md`；
- `History.md`；
- `Project_Tree.md`；
- `docs/linkmesh/work_plan.md`；
- `Mesh2D`、Writer 或 helper exchange schema。
