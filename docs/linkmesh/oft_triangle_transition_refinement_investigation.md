# OFT 26.6 / Triangle 多区域网格渐变 Refinement 调查报告

- 文档主受众：Aider-facing / Human-facing
- 知识库用途：专项只读源码调查
- 调查状态：静态调查完成；因 native ABI 与内存释放证据不完整而停止
- 最终裁决：**BLOCKED BY MISSING ABI/OWNERSHIP EVIDENCE**
- 调查对象：LinkMesh、OpenFUSIONToolkit/TokaMaker 26.6、随附 Triangle
- 修改范围：仅生成本报告；未修改业务源码、蓝图、测试、配置、CLI、OFT/Triangle
  参考源码、外部库或求解器接口
- 运行状态：未运行 LinkMesh、OFT、Triangle、服务器探针或消费端验证
- 事实边界：本文严格区分当前源码直接事实、既有探针事实、Triangle 一般原理、
  Agent 设计建议和待确认事项。任何 refinement 路线均未实现、未运行、未验证

---

## 1. 调查目标与边界

本报告调查以下候选数据流是否能在不修改 OFT/TokaMaker 和 Triangle 外部源码的
前提下实现：

```text
已有共形 N-region Mesh2D
  → 找出目标 dx 不同的内部 Region interfaces
  → 在粗侧计算距离 d
  → 应用用户给定 transition width W [m]
  → 构造平滑目标尺寸 h(d)
  → 转换为逐 triangle 最大面积 Amax(d)
  → 使用 Triangle 的 refinement 与 q 质量约束
  → 得到新的 points / triangles / Region attributes
  → 重新验证并构造最终 Mesh2D
```

保持不变的项目边界：

1. OFT/TokaMaker 封装的 Triangle 仍是唯一二维剖分底座。
2. 不引入 Cubit、Gmsh、MMG、TetGen、第二个 Python Triangle wrapper 或其他剖分器。
3. 不修改、维护或分叉 OFT/TokaMaker 与 Triangle。
4. `Mesh2D` 仍是最终统一、求解器无关对象。
5. Region ID 继续使用 OFT/Triangle 最终 triangle attributes，不重编号、不压缩、
   不执行 `+1`。
6. refinement 只处理初始网格后的尺寸与形状质量，不改变 `physical_label`、OFT
   technical role 或任何下游 classification 语义。
7. 不调查 M3D-C1、PUMI、SMB、TRIMEG consumer 或 C1 有限元实现。
8. 网格结构和渐变改善不能外推为求解稳定性或物理正确性。

---

## 2. 证据来源和版本身份

### 2.1 证据等级

| 等级 | 本报告使用方式 |
|---|---|
| OFT 26.6 目标源码直接事实 | 当前 `meshing.py`、`_interface.py` 的实际声明和调用 |
| Triangle 随附头文件直接事实 | `triangle.h` 的 `triangulateio` 字段及 In/Out 标记 |
| Triangle 随附 C 源码直接事实 | **当前缺失**，不能确认 option parser、`-r`、q 默认值和释放实现 |
| LinkMesh 当前源码事实 | 当前 regions 配置、生成编排、OFT Adapter、`Mesh2D` 契约 |
| 既有服务器探针事实 | 已有 multi-region 生成、编号与结构检查事实；不含 refinement |
| 一般网格生成数学原理 | 仅用于比较距离、profile 和质量指标，不冒充接口事实 |
| Agent 设计建议 | 明确标记为候选，不是正式蓝图或已实现接口 |
| 待确认事项 | 缺少目标源码、ABI 或服务器直接证据的内容 |

### 2.2 已读取的关键源码

| 文件 | 关键位置 | 可直接确认的内容 |
|---|---:|---|
| `src/linkmesh/cli.py` | `_run_regions_generate()` | regions generate 的配置、map、dx、OFT 和 Writer 编排 |
| `src/linkmesh/config.py` | `RegionsGenerateConfig`、`load_regions_generate_config()` | effective `mesh_dx` 与 `region_dx` |
| `src/linkmesh/regions.py` | `resolve_region_dx()` | 最终 Region ID 到 effective dx 的完整映射 |
| `src/linkmesh/mesher/oft_adapter.py` | `generate_multi_region_mesh()`、`mesh_from_oft_domain()` | OFT Domain 构造、输出验证和 `Mesh2D` 创建 |
| `src/linkmesh/mesh.py` | `Mesh2D`、`_validate_outer_boundary()` | 最终统一对象和 `outer_boundary` 语义 |
| `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` | 19、48、52、545、848、1068、1086 | ctypes 结构、Triangle 调用、Domain、Mesh、Region |
| `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/_interface.py` | `oft_triangle_lib` 加载块 | native 动态库加载和 ctypes 基础类型 |
| `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h` | 257-282 | native `triangulateio` 字段和方向标记 |

OFT 网格 Python 文件的精确符号位置由仓库参考映射确认：

- `triangle_struct`：`meshing.py:19`
- `oft_triangulate`：`meshing.py:48-49`
- `run_triangle()`：`meshing.py:52`
- `gs_Domain.define_region()`：`meshing.py:278`
- `gs_Domain.add_annulus()`：`meshing.py:350`
- `gs_Domain.add_polygon()`：`meshing.py:414`
- `gs_Domain.add_enclosed()`：`meshing.py:484`
- `gs_Domain.build_mesh()`：`meshing.py:545`
- `Mesh`：`meshing.py:848`
- `Mesh.get_mesh()`：`meshing.py:1068`
- `Region`：`meshing.py:1086`
- `Region.get_resampled_points()`：`meshing.py:1162`
- `Region.check_in_poly()`：`meshing.py:1187`
- `Region.get_in_point()`：`meshing.py:1213`

### 2.3 缺失的决定性证据

当前未获得以下文件的完整、可引用内容：

```text
TOKAMAKER\OpenFUSIONToolkit\src\ext_libs\triangle.c
```

必须确认的符号或代码段：

1. `triangulate(...)`
2. option parser 对 `p`、`q`、`a`、`A`、`r`、`z`、`Q` 的实际处理
3. 裸 `q` 的锁定版本默认最小角
4. refinement 输入校验
5. `trianglearealist` 的读取、传播和新 triangle 约束继承
6. Region attribute 的 refinement 传播
7. segment 的 refinement 行为
8. 输出数组分配函数
9. `trifree()` 或实际对应释放函数
10. 错误返回、终止条件和质量约束警告

因此，本报告不能把 Triangle 通用文档中的 `-r` 行为写成目标 OFT 26.6 native
二进制的完整 ABI 事实。

---

## 3. LinkMesh / OFT / Triangle 三层数据流

### 3.1 当前正式初始生成链

```text
linkmesh regions generate
  → cli._run_regions_generate()
  → load_regions_generate_config()
  → read_regions_map()
  → read_multi_boundary_file()
  → build_region_plan()
  → inspect_multi_region_ids()
  → assign_final_region_ids()
  → validate_plan_against_map()
  → resolve_region_dx()
  → generate_multi_region_mesh(numbered_plan, dx_by_region_id)
  → gs_Domain.define_region()
  → gs_Domain.add_polygon()
  → gs_Domain.build_mesh()
  → Mesh(...)
  → Mesh.get_mesh()
  → run_triangle(alpha)
  → oft_triangle_lib.triangulate(...)
  → Triangle triangulateio
  → vertices / triangles / triangle_attributes
  → mesh_from_oft_domain()
  → Mesh2D
```

### 3.2 LinkMesh regions 层

`resolve_region_dx()` 返回：

```text
dict[final_region_id, effective_dx]
```

规则是：

- `mesh_dx` 提供所有 Region 的默认值；
- `region_dx` 按最终 Region ID 覆盖；
- 无全局默认时要求完整覆盖；
- 未知 ID、非有限值或非正值失败。

`_run_regions_generate()` 当前把该映射传给：

```text
generate_multi_region_mesh(numbered_plan, resolved_dx)
```

但 `generate_multi_region_mesh()` 返回值只有 `Mesh2D`。调用者局部变量
`resolved_dx` 仍然存在，因此未来 refinement 阶段不需要从 triangle 面积反推用户
目标 dx。正确接线位置应是：

```text
mesh = generate_multi_region_mesh(numbered_plan, resolved_dx)
refined_mesh = refine_multi_region_mesh(mesh, resolved_dx, W)
```

这是 Agent 候选，不是当前实现。

### 3.3 OFT Domain 层

`generate_multi_region_mesh()` 对每个 plan entry 调用：

```text
domain.define_region(name, effective_dx, technical_role)
domain.add_polygon(points, name, parent_name=...)
```

输入：

- polygon：独立 `(B,2) float64`
- dx：有限正标量，单位 m
- Region attribute：由 OFT setup/build 后最终编号
- technical role：`boundary`、synthetic `plasma` 或 `vacuum`

输出：

```text
Mesh2D.nodes       (N,2) float64
Mesh2D.triangles   (T,3) int32, 0-based
Mesh2D.region_ids  (T,)  int32
Mesh2D.outer_boundary (B,2) float64 or None
```

### 3.4 OFT Mesh 层

`Mesh.get_mesh()` 在 `meshing.py:1068` 构造：

```text
alpha["vertices"] = self._resampled_points
alpha["segments"] = resampled_flat
alpha["regions"]  = self._reg_defs
```

实际数据：

| 输入 | shape | dtype |
|---|---:|---|
| vertices | `(P,2)` | 在 `run_triangle()` 中转 contiguous `float64` |
| segments | `(S,2)` | 在 `run_triangle()` 中转 contiguous `int32` |
| regions | `(K,4)` | 在 `run_triangle()` 中转 contiguous `float64` |

每个 region record 为：

```text
[seed_R, seed_Z, final_region_attribute, dx^2 / 2]
```

### 3.5 ctypes/native 层

`meshing.py:48-49` 绑定：

```text
oft_triangle_lib.triangulate(
    char*,
    triangle_struct* in,
    triangle_struct* out,
    triangle_struct* vorout
) -> int
```

`_interface.py` 直接加载：

```text
liboft_triangle.so
```

优先位置：

1. Python 包当前目录；
2. 包目录上方的 `bin` 目录。

初始生成使用硬编码 option string：

```text
pqaAzQ
```

`run_triangle()` 在 native 返回后用 `numpy.ctypeslib.as_array()` 创建指向 native
输出内存的 NumPy view，然后返回这些 view。当前函数没有显式复制，也没有调用
Triangle 释放函数。

### 3.6 当前被丢弃或未暴露的数据

当前 OFT Python 返回值只包含：

```text
vertices
triangles
triangle_attributes
```

当前调用链未返回：

- output point attributes；
- point markers；
- triangle area list；
- neighbors；
- output segments；
- segment markers；
- holes；
- copied region list；
- edges；
- edge markers；
- Voronoi 数据；
- native allocation ownership token。

LinkMesh 随后只保存 nodes、triangles、region IDs 和受控恢复的 outer boundary。

---

## 4. 当前 per-Region dx 与共享 boundary 机制

### 4.1 Region dx 的存储

`gs_Domain.define_region()` 位于 `meshing.py:278`，将标量保存为：

```text
domain.region_info[name]["dx"]
```

`Region.__init__()` 位于 `meshing.py:1086`，保存：

```text
Region._dx_vol
Region._dx_curve
```

### 4.2 共享 boundary 的 dx

`gs_Domain.add_polygon()` 位于 `meshing.py:414`：

```text
dx_curve = dx
if parent exists:
    dx_curve = min(dx, parent_dx)
```

`gs_Domain.add_annulus()` 位于 `meshing.py:350`：

- inner contour 使用 `min(inner_dx, annulus_dx)`；
- outer contour 在存在 parent 时使用 `min(annulus_dx, parent_dx)`。

因此，当前 OFT 26.6 对共享界面确实选择相邻 Region 中更小的目标尺度作为曲线离散
尺度。

### 4.3 boundary 重采样

`Mesh.__init__()` 位于 `meshing.py:848`。它：

1. 按 `merge_thresh` 合并近点；
2. 合并或拆分共享 segment；
3. 对共享 segment 再取相关 `_dx_curve` 的最小值；
4. 沿 segment 累计弧长；
5. 使用 `numpy.linspace()` 和 `numpy.interp()` 插入边界点；
6. 形成全局 `_resampled_points` 和 `_resampled_segments`。

这意味着细侧 dx 会直接控制共享 interface 的离散密度。粗侧紧邻 interface 的
triangle 必须连接该较密的界面节点，但粗侧内部仍使用自己的较大常数面积约束，
所以尺寸可能在有限的薄层内快速增大。

这是当前薄变化层形成的直接机制：

```text
共享 interface 按 min(dx_coarse, dx_fine) 离散
+ 粗 Region 内部仍使用 dx_coarse^2 / 2
```

当前没有用户可控的物理厚度 `W`。

### 4.4 Region 最大面积

`Mesh.__init__()` 为每个 Region 追加：

```text
[seed_R, seed_Z, region_id, region._dx_vol * region._dx_vol / 2.0]
```

所以当前直接事实是：

```text
Amax = dx^2 / 2
```

这里 `dx` 是 OFT 的目标网格尺度，不是 Triangle 对每条边长的严格保证。

### 4.5 当前 option string

`run_triangle()` 位于 `meshing.py:52`，准确值为：

```text
pqaAzQ
```

在 Triangle 通用开关语义中：

| 开关 | 通用作用 | 当前目标源码事实边界 |
|---|---|---|
| `p` | PSLG/segment 输入 | 当前确实提交 `segmentlist` |
| `q` | 质量约束 | 当前确实启用裸 `q` |
| `a` | 面积约束 | 当前确实提交 region maximum area |
| `A` | triangle Region attribute | 当前读取 `triangleattributelist` |
| `z` | 0-based 索引 | 当前输出被 LinkMesh 作为 0-based 使用并验证 |
| `Q` | quiet | 当前 option 中存在 |
| `r` | refinement | 当前 option 中不存在 |

开关的内部解析与精确边界仍需锁定 `triangle.c` 确认。

### 4.6 gradation 参数

`gs_Domain.build_mesh()` 位于 `meshing.py:545`，包含：

```text
cubit_gradation=1.05
```

该参数只传给 `run_cubit()` 路径。正式 Triangle 路径不消费它。

结论：

- 当前 Triangle 路径没有 transition width；
- 当前 Triangle 路径没有 gradation 参数；
- `cubit_gradation` 不属于 LinkMesh 当前唯一正式底座，不能用于本任务。

---

## 5. 当前 q 质量约束

### 5.1 已确认事实

1. 当前 OFT 使用裸 `q`，因为 option string 是 `pqaAzQ`。
2. option string 在 `run_triangle()` 内硬编码。
3. `gs_Domain.build_mesh()`、`Mesh.get_mesh()` 和 LinkMesh Adapter 均没有
   minimum-angle 参数。
4. 当前 LinkMesh 无法通过 OFT 高层 API 请求例如 `q25`。
5. 修改高层 `gs_Domain` 参数不足以调节 q，因为没有相应参数通道。

### 5.2 裸 q 默认最小角

锁定 Triangle 版本的裸 `q` 默认最小角必须来自随附 `triangle.c` 的 option parser
或与该源码严格对应的官方说明。

当前已提供的 `triangle.h` 片段和 OFT Python wrapper 没有定义该数值。虽然常见
Triangle 1.6 文档通常说明裸 `q` 使用默认最小角，但本报告不以一般经验替代目标源码
事实。

裁决：

```text
裸 q 默认最小角：待 triangle.c 或锁定版本官方说明直接确认
```

### 5.3 可调性

未来可能存在两种路径：

- LinkMesh 自己构造低层 option string，例如 `rpq25aAzQ`；
- 修改 OFT `run_triangle()` 的硬编码字符串。

第二种会修改外部 OFT 源码，违反任务边界。第一种需要 LinkMesh 侧低层 Adapter，
但只有在 ABI、输入和释放契约确认后才可评估。

不需要重新编译 Triangle的结论目前也不能最终确认，因为必须先验证现有导出
`triangulate` 是否完整解析带数值的 q option；这应由 `triangle.c` 和最小运行探针
确认。

### 5.4 refinement 中 q 的候选行为

Triangle 通用算法通常会在 refinement 模式同时执行面积和质量判据。因此候选
option string 若包含 `r` 和 `q`，面积已达标但形状不达标的 triangle 仍可能被细化。

但在目标 OFT 26.6 环境中，以下问题尚未由直接源码关闭：

- `r` 与裸 `q` 的实际组合路径；
- q 判断是否对所有输入 triangle 执行；
- 受约束小角附近的终止行为；
- 锁定版本的 warning 和最大允许角阈值。

### 5.5 PSLG 小角限制

一般网格生成原理：

- 受约束 segment 形成的小输入角可能无法通过单纯 Steiner refinement 达到任意
  minimum angle；
- 过强质量要求可能导致持续加点、终止警告或无法满足全部 triangle；
- 质量目标不能越过输入 PSLG 的几何可实现边界。

目标版本的精确警告、终止条件和推荐角度必须从 `triangle.c` 或锁定官方说明确认。

---

## 6. Triangle 结构体和 native binding

### 6.1 Python 与 native 字段对照

Python `triangle_struct` 位于 `meshing.py:19`。Native `triangulateio` 位于
`triangle.h:257-282`。当前可见字段顺序一致：

| 字段 | Python 声明 | native 声明 | 初始生成填充 | 当前 Python 返回 |
|---|---|---|---|---|
| `pointlist` | 是 | In/Out | 是 | 是 |
| `pointattributelist` | 是 | In/Out | 否 | 否 |
| `pointmarkerlist` | 是 | In/Out | 否 | 否 |
| `numberofpoints` | 是 | In/Out | 是 | 间接 |
| `numberofpointattributes` | 是 | In/Out | 默认零 | 否 |
| `trianglelist` | 是 | In/Out | 否 | 是 |
| `triangleattributelist` | 是 | In/Out | 否 | 是 |
| `trianglearealist` | 是 | In only | 否 | 否 |
| `neighborlist` | 是 | Out only | 否 | 否 |
| `numberoftriangles` | 是 | In/Out | 默认零 | 间接 |
| `numberofcorners` | 是 | In/Out | 默认零 | 否 |
| `numberoftriangleattributes` | 是 | In/Out | 默认零 | 否 |
| `segmentlist` | 是 | In/Out | 是 | 否 |
| `segmentmarkerlist` | 是 | In/Out | 否 | 否 |
| `numberofsegments` | 是 | In/Out | 是 | 否 |
| `holelist` | 是 | In/copied out | 否 | 否 |
| `numberofholes` | 是 | In/copied out | 默认零 | 否 |
| `regionlist` | 是 | In/copied out | 是 | 否 |
| `numberofregions` | 是 | In/copied out | 是 | 否 |
| `edgelist` | 是 | Out only | 否 | 否 |
| `edgemarkerlist` | 是 | Out only | 否 | 否 |
| `normlist` | 是 | Out only | 否 | 否 |
| `numberofedges` | 是 | Out only | 默认零 | 否 |

字段存在只证明 ctypes 结构可以表达该指针，不能证明当前 wrapper 已正确支持该字段的
输入生命周期、输出 ownership 或释放。

### 6.2 refinement 候选所需输入

按 Triangle 通用 refinement 模型，候选至少需要：

```text
pointlist
numberofpoints
trianglelist
numberoftriangles
numberofcorners = 3
triangleattributelist
numberoftriangleattributes
trianglearealist
segmentlist
numberofsegments
```

可能还需要：

- point markers；
- segment markers；
- holes；
- region list。

精确 required/optional 契约必须由目标 `triangle.c` 确认。

### 6.3 dtype、连续性和索引

现有 OFT wrapper已确认的 ctypes dtype：

| 数据 | dtype | 连续性 |
|---|---|---|
| points | `float64` | C contiguous |
| segments | `int32` | C contiguous |
| regions | `float64` | C contiguous |
| output triangle indices | native `int`，Python view | 目标环境目前按 32-bit int 使用 |
| output attributes | `double`，后转 `int32` | native view |

候选 refinement 还应要求：

- triangles：C contiguous `int32`；
- triangle attributes：C contiguous `float64`；
- triangle area constraints：C contiguous `float64`；
- 所有输入数组在 native 调用结束前保持强引用；
- 使用 `z` 保持 0-based。

### 6.4 ABI 对应

当前 Python `triangle_struct` 和 `triangle.h` 字段列表、顺序表面一致，但以下仍缺少
最终 ABI 证据：

- `REAL` 在实际 `liboft_triangle.so` 中确认为 `double`；
- native `int` 宽度与 Python `ctypes.c_int` 一致；
- 编译宏和结构体 packing；
- `triangulate` 导出签名；
-输出分配与释放函数。

OFT 当前初始生成成功是 ABI 可工作的运行证据，但不能证明此前从未使用的
`trianglearealist` refinement 输入和释放路径安全。

---

## 7. `-r` refinement 输入/输出契约

### 7.1 当前可直接确认的内容

- `trianglearealist` 在 Python 结构中存在。
- `trianglearealist` 在 `triangle.h:266` 标记为 `In only`。
- 当前 `run_triangle()` 不设置它。
- 当前 option string 不包含 `r`。
- OFT 高层 API 没有 refinement 方法或参数。
- 当前 LinkMesh 没有 refinement 阶段。

因此：

```text
trianglearealist 能否作为目标 OFT 26.6 refinement 输入：
结构可表达，但当前调用链未使用；实际契约仍待 native 源码确认。
```

### 7.2 必须由锁定源码确认的问题

以下内容不能仅根据字段名或一般 Triangle 经验定案：

1. `trianglearealist` 长度是否必须精确等于输入 triangle 数。
2. 负值、零和正值的准确含义。
3. `r` 是否强制要求 `numberofcorners=3`。
4. 输入 triangle attributes 的 shape 和 attribute count。
5. 是否必须同时提供 `p` 才能保留全部 PSLG segments。
6. `rpqaAzQ` 是否是正确组合。
7. `A` 在 refinement 时如何处理已有 attributes。
8. area constraint 如何传播到新子 triangle。
9. output segment list是否重新分配。
10. 原输入 vertex 是否全部保留。
11. 原输入 segment 是否可能被拆分。
12. output triangle 是否严格嵌套于输入 triangle。
13. 是否允许新边跨越原 triangle 内部边。
14. region attributes 是否从父 triangle 继承。
15. q 与 a 的判据执行顺序。
16. 错误码和部分分配后的清理要求。

### 7.3 PSLG 保留候选

要保留计算域外边界和内部 Region interfaces，候选 refinement 输入应重新构造完整
全局 PSLG：

```text
segments =
    topology outer-boundary edges
    ∪ all Region-interface edges
```

只提交外边界会丢失内部 Region interface 的受约束身份；只提交 triangles 而不保留
PSLG 的行为也不能在缺少 native 证据时假定安全。

### 7.4 一次 refinement 是否足够

一次调用可以为当前输入 triangle 提供分片常数 `trianglearealist`。但 refinement
产生新 triangle 后，若目标 `h(d)` 应基于新 triangle 的空间位置重新评估，则一次
调用只能近似初始 triangle 采样后的 profile。

尤其当：

- 初始粗 triangle 跨越较大的 d 范围；
- `W` 较小；
- refinement 后 centroid 移动到不同 profile 区间；
- 多个 interface transition 重叠；

一次调用未必足够表达连续 `h(d)`。有限迭代是合理候选，但尚未批准。

---

## 8. 内存 ownership 和释放

### 8.1 当前输入 ownership

现有 `run_triangle()` 创建本地 NumPy contiguous arrays，并将其指针传给 native。
这些数组在函数调用期间由 Python 局部变量持有，输入生命周期对同步调用是明确的。

### 8.2 当前输出 ownership

Native 填充 `out_struct` 指针。Python 使用：

```text
numpy.ctypeslib.as_array(native_pointer, shape=...)
```

返回 NumPy view。该 view 不拥有 native 内存。

当前 `run_triangle()`：

- 没有显式复制输出；
- 没有保存 native owner；
- 没有调用释放函数；
- 没有暴露释放 API；
- 没有说明多次调用后的内存生命周期。

因此，现有初始调用存在一个本任务必须正视的 ownership 证据缺口：不能安全地设计
有限多轮 refinement，同时假定每轮 native 分配会被正确释放。

### 8.3 必须确认的释放规则

需要从 `triangle.c` 确认：

1. 哪些 output pointers 由 Triangle 分配。
2. 是否使用 `malloc()`、`trimalloc()` 或其他 allocator。
3. 应调用 `trifree()`、`free()` 还是其他符号。
4. `vorout` 中哪些指针也可能被分配。
5. 输入 `holelist`/`regionlist` 被复制还是借用。
6. 错误返回后哪些输出可能已分配。
7. output segments、markers、neighbors、edges 是否需要分别释放。
8. `trifree` 是否导出到 `liboft_triangle.so`。
9. Python ctypes 是否可以绑定该释放函数。
10. 复制到 Python-owned arrays 后的正确释放顺序。

候选安全顺序应是：

```text
native triangulate
→ 检查错误码
→ 把所有需要的 output 完整复制成 Python-owned NumPy arrays
→ 对每个由 native 分配的指针按官方规则释放
→ 丢弃 ctypes structs
→ 构造 Mesh2D
```

该顺序目前是设计要求，不是已确认可执行事实。

### 8.4 停止裁决

任务明确规定无法确认 ownership/free 规则时必须停止。当前正处于该条件，因此不能
批准 LinkMesh 低层 refinement 实现。

---

## 9. Region attributes 与 PSLG 保留

### 9.1 当前 Region identity

初始 mesh 的 Region ID 来自：

```text
OFT final Region ID
→ Triangle regionlist attribute
→ triangleattributelist
→ int32 region_ids
→ Mesh2D.region_ids
```

现有探针已确认：

- setup-only 编号与 Triangle attributes 一致；
- fresh rebuild 编号稳定；
-只改变 dx 时编号稳定；
-输入 block 重排可能改变部分最终 ID；
-每次 generate 必须依赖当次 map。

这些事实只覆盖初始生成，不覆盖 refinement attribute propagation。

### 9.2 refinement 候选

候选 refinement 输入应把当前 `Mesh2D.region_ids` 转为：

```text
triangleattributelist (T,1) float64
numberoftriangleattributes = 1
```

输出后必须验证：

- attribute 全部有限；
- attribute 具有整数语义；
-输出 attribute 集合严格等于输入正式 Region ID 集合；
-每个 Region 仍有 triangle；
-不通过最近邻、triangle centroid polygon 查询或面积统计恢复 Region identity。

如果 Triangle refinement 不能原生保留 attributes，该路线应停止，因为用几何最近邻
恢复 Region identity 违反项目边界。

### 9.3 interface PSLG

从当前 triangles 和 region IDs 可确定性提取：

- edge incidence=1：计算域外边界；
- edge incidence=2 且两侧 Region ID 不同：内部 Region interface；
- edge incidence=2 且两侧 Region ID 相同：Region 内部 edge；
- incidence>2：non-manifold，失败。

候选 refinement 的 PSLG segment list应包含：

```text
all incidence=1 edges
+ all cross-Region incidence=2 edges
```

输出后必须再次提取 topology，确认：

-内部 interface 仍由共享 mesh edges 表达；
-没有裂缝或重复界面节点；
-界面两侧 Region ID 仍不同且合法；
-全局 edge incidence 仅为 1 或 2。

---

## 10. Mesh2D 信息与 effective dx

### 10.1 当前 `Mesh2D`

`Mesh2D` 保存：

```text
nodes
triangles
region_ids
boundary_segments
boundary_markers
node_markers
outer_boundary
```

它不保存：

- effective dx；
- RegionPlan；
- regions map；
- Triangle input segments；
- native pointers；
- per-triangle area constraints；
- transition profile。

这符合其求解器无关职责。

### 10.2 effective dx 是否仍可获得

在 `_run_regions_generate()` 中，`resolved_dx` 与 `mesh` 同时存在。因此最小候选是把
二者显式传入 refinement 函数：

```text
refine_multi_region_mesh(
    mesh,
    dx_by_region_id=resolved_dx,
    transition_width=W,
)
```

不建议把 effective dx 加入 `Mesh2D`，因为：

- dx 是生成策略输入，不是最终通用网格事实；
- refinement 完成后不应强制所有 Writer 消费它；
- CLI 编排层已经拥有完整映射。

也不得从以下信息反推 dx：

-实际 triangle 平均面积；
-PNG；
-Region 名称；
-`physical_label`；
-OFT technical role；
-Region ID 数值大小。

### 10.3 `outer_boundary` 语义

当前 `Mesh2D.outer_boundary` 是 Triangle 初始输入前的有序最外层计算域几何边界：

-不是最终拓扑边界节点集合；
-不包含 Triangle 后续插入的 boundary Steiner points；
-可以少于最终 topology boundary node 数；
-保持顺时针、隐式闭合。

refinement 后应保留原 `mesh.outer_boundary` 的独立副本。新增 boundary points 只进入
最终 nodes/topology，不应被反推或写回 `outer_boundary`。

---

## 11. interface 提取与粗细侧判定

### 11.1 transition 来源

本任务的 transition 来源仅为：

```text
两个不同 Region 共享、且 effective dx 不同的内部 interface
```

计算域外边界不默认参与 transition。是否需要外边界层加密属于另一项独立需求。

### 11.2 确定性粗细规则

对 interface 两侧 Region `a`、`b`：

```text
ha = effective_dx[a]
hb = effective_dx[b]
```

规则：

- `ha == hb`：不创建 transition；
- `ha > hb`：`a` 是粗侧，`b` 是细侧；
- `hb > ha`：`b` 是粗侧，`a` 是细侧；
- interface 目标尺寸取 `hf = min(ha, hb)`；
-粗侧远场目标取 `hc = max(ha, hb)`。

比较是否相等应使用配置层已规范化的数值。未来蓝图必须定义是否采用精确浮点相等或
受控相对容差；当前不批准容差。

### 11.3 一个 Region 邻接更粗和更细 Region

同一 Region 可能：

-相对某邻居是粗侧，需要在自身内生成 transition；
-相对另一邻居是细侧，该 interface 的粗侧 transition 位于对方 Region；
-与第三邻居 dx 相同，不生成 transition。

每个 interface 约束必须独立计算，只作用于该 interface 的粗侧 Region。

### 11.4 多 interface 组合

对同一粗 Region 中 triangle `K`，每个适用 interface 给出候选尺寸 `h_i(K)`。
推荐组合：

```text
h_target(K) = min(h_region, h_1(K), h_2(K), ...)
```

原因：

- refinement 只能细化，不能 coarsen；
-多个约束重叠时采用最严格尺寸；
-结果与 interface 遍历顺序无关；
-不依赖 Region 名称或编号顺序。

---

## 12. 距离 d 定义比较

| 定义 | 单位 | 优点 | 风险/缺点 | 新依赖 |
|---|---|---|---|---|
| triangle centroid 到 interface segments 的欧氏最短距离 | m | 平移/旋转不变、确定、便于逐 triangle profile | 粗 triangle 上只采样中心，可能低估跨越范围 | 不需要 |
|三个 vertices 到 interface 距离的最小值 | m | 保守地捕捉接近 interface 的 triangle | 一个顶点靠近会细化整个 triangle，transition 偏厚 | 不需要 |
|三个 vertices 距离的平均值 | m | 比 centroid 更平滑 | 解释不直观；可能漏掉局部靠近 | 不需要 |
|三个 vertices 距离的最大值 | m | 保证 triangle 全部进入对应层后才变粗 | transition 显著偏厚、细化成本高 | 不需要 |
| circumcenter 到 interface 距离 | m | 与 Delaunay 几何相关 | 钝 triangle 的 circumcenter 可远离单元甚至在外部 | 不需要 |
| mesh graph/geodesic 距离 | m 或层数 | 可限制传播在 topology 内 | 路径依赖网格、编号与分辨率；不直接对应欧氏 W | 不需要 |
| polygon/GEOS distance | m | 成熟几何谓词 | 引入新依赖；当前不需要 | Shapely/GEOS |

### 12.1 推荐首版候选

Agent 建议首版使用：

```text
triangle centroid 到目标 interface mesh segments 的欧氏最短距离
```

并且：

-只计算粗侧 Region 内 triangle；
-interface 使用当前共形 topology 中实际共享的 mesh edge；
-多个 interface 分别计算后取最严格尺寸；
-距离单位自然为 m；
-不依赖 triangle 编号；
-不需要 Shapely/GEOS。

该定义是设计建议，不是现有源码事实。

### 12.2 复杂度

直接逐 triangle、逐 interface segment 计算为：

```text
O(T_region * S_interface)
```

对 P0 网格可作为最小实现起点。若实际规模证明不足，再考虑纯 NumPy 分块、包围盒或
空间索引；不应预先引入几何依赖。

---

## 13. transition profile 比较

设：

```text
hf = 细侧有效 dx
hc = 粗侧有效 dx
W  = 用户指定 transition width [m]
d  = 粗侧 triangle 到 interface 的距离 [m]
```

### 13.1 指数 profile

```text
h(d) = hf * (hc / hf)^(d / W),  0 <= d < W
h(d) = hc,                       d >= W
```

性质：

- `h(0)=hf`
- `h(W)=hc`
-函数在 `W` 处连续；
-相对增长率 `d(log h)/dd = log(hc/hf)/W` 为常数；
-对尺寸比大的界面比线性 profile 更自然地控制相对增长；
-`W` 直接是从细尺寸增长到粗尺寸的物理厚度。

### 13.2 线性 profile

```text
h(d) = hf + (hc - hf) * d / W,  0 <= d < W
h(d) = hc,                       d >= W
```

性质：

- `h(0)=hf`
- `h(W)=hc`
-函数在 `W` 处连续；
-绝对增长率固定；
-当 `hc/hf` 很大时，界面附近相对增长可能过快；
-解释简单。

### 13.3 源码既有 gradation

当前 OFT Triangle 路径没有现成 gradation profile。唯一出现的
`cubit_gradation=1.05` 只属于 Cubit 路径，不能复用或冒充 Triangle 能力。

### 13.4 推荐首版候选

Agent 建议优先指数 profile：

```text
h(d) = hf * (hc / hf)^(min(d/W, 1))
Amax(d) = h(d)^2 / 2
```

原因：

-保持常数相对增长率；
-与网格尺寸跨数量级变化更相容；
-只需要 `hf`、`hc`、`W`；
-用户只提供 W。

### 13.5 边界情况

- `W<=0`：未来接口应解释为关闭 transition，不进入 refinement；不能除以零。
- `W` 很小：profile 接近当前快速跳变，可能没有 triangle centroid落入 transition。
- `W` 大于粗 Region 局部厚度：该 Region 可能全部受细化影响。
- transition 重叠：取所有候选尺寸的最小值。
- profile 必须截断到 `[hf, hc]`。
-不得使用 profile 请求大于粗 Region 基准 `hc` 的尺寸。
-不得把全部 Region 被细化自动视为错误，但应报告该诊断。

这些均需蓝图正式定义。

---

## 14. 逐 triangle 面积约束

### 14.1 候选构造

对初始 mesh 中每个 triangle `K`：

1. 读取其正式 `region_id`。
2. 取得 `h_region = effective_dx[region_id]`。
3. 若该 Region 不作为任何 interface 的粗侧：

   ```text
   h_target = h_region
   ```

4. 若受一个或多个粗侧 transition 影响：
   -计算每个适用 interface 的 `d_i`；
   -计算 `h_i(d_i)`；
   -取：

   ```text
   h_target = min(h_region, h_1, h_2, ...)
   ```

5. 转换：

   ```text
   Amax = h_target^2 / 2
   ```

6. 形成 `(T,) float64` 的 `trianglearealist`。

### 14.2 与当前 triangle 面积的关系

Triangle refinement 只能细化，不能 coarsen。因此：

-若候选 `Amax` 大于当前 Region 常数面积，也不得借此请求粗化；
-`min(region_Amax, transition_Amax)` 是安全的候选上界；
-实际 triangle 面积大于 `Amax` 时，面积判据应触发 refinement；
-实际面积已经小于等于 `Amax` 时，面积判据本身不要求 refinement；
-若 q 仍不满足，质量判据可能继续触发 refinement；
-面积和 q 都满足时，不应因 transition profile之外的理由无条件细化。

### 14.3 对 User 核心问题的回答

问题：

> 面积已经达标时，Triangle 是否可能不执行 refinement？

回答：

**是。** 如果某 triangle 已满足它的逐 triangle 最大面积约束，面积判据本身可以不
触发 refinement。

还必须区分：

1. 面积达标、q 不达标：若目标 refinement 调用确实启用并执行 q，仍可能因形状质量
   被细化。
2. 面积不达标、q 达标：应因面积被细化。
3. 面积和 q 都达标：通常不应被无理由细化。
4. 即使所有离散判据满足，也不代表实际分箱统计严格复现用户 W，因为约束只在离散
   triangle 上采样，且 Triangle 同时受 PSLG 与 Delaunay/质量处理影响。

目标 OFT 二进制中的精确执行顺序仍待 `triangle.c` 和运行探针确认。

### 14.4 无效约束

未来实现应在 native 调用前拒绝：

- NaN/Inf；
-非正且语义未由目标源码确认的 area 值；
-长度不等于 T；
-比 dtype 范围异常的值；
-缺少 Region dx；
-未知 Region ID。

在 `triangle.c` 明确负值或零值语义前，不应依赖特殊 sentinel。

---

## 15. 有限迭代需求

### 15.1 候选流程

```text
initial conforming N-region Mesh2D
  → 提取当前 outer boundary/interface topology
  → 根据当前 triangles 计算 d 与 Amax
  → Triangle refinement
  → 复制并释放 native 输出
  → 验证 attributes 和共形 topology
  → 重新计算 interfaces、d 与 Amax
  → 达到停止条件或最大轮数
```

### 15.2 为什么可能需要迭代

一次 constraints 基于初始 triangle 的代表点。refinement 后：

-子 triangle 有新的 centroid；
-子 triangle 与 interface 的距离分布更细；
-原来跨越多个 profile 区间的大 triangle 被拆分；
-多个 transition 的重叠关系可能更准确。

因此有限迭代可能更接近目标 W。

### 15.3 候选停止条件

未来蓝图可从以下条件选择最小集合：

1. nodes 和 triangles 数量不再变化；
2.所有 triangle 面积满足当前 `Amax`；
3. q 指标达到锁定 Triangle 的实际要求，或目标源码报告完成；
4.按距离分箱的 `hK` profile 误差低于批准容差；
5.连续两轮 connectivity 和 attributes 完全相同；
6.达到最大迭代次数；
7.节点或 triangle 数超过安全上限时失败。

### 15.4 当前不批准的值

本报告不批准：

-最大迭代次数；
-profile 误差容差；
-面积比较容差；
-最大节点数；
-运行时间上限。

这些必须由蓝图和服务器探针共同裁决。

### 15.5 每轮不变量

每轮必须：

-重新提交完整 PSLG；
-保留全部正式 Region attributes；
-只增加或细分 topology，不猜测 Region；
-输出 Python-owned arrays；
-释放本轮 native allocations；
-产生确定性的诊断；
-失败时报告轮次、节点/triangle 数、失败条件和 native 错误。

---

## 16. 输出 Mesh2D 契约

refinement 输出必须重新验证：

| 项目 | 要求 |
|---|---|
| nodes | `(N,2) float64`、有限、Python 独立所有权 |
| triangles | `(T,3)` 整数、全局 0-based |
| triangle index | `0 <= index < N` |
| attributes | `(T,)`、有限、整数语义 |
| Region ID 集合 | 与输入正式集合完全一致 |
| Region coverage | 每个 Region 至少一个 triangle |
| triangle vertices | 每个 triangle 三个 index 互异 |
| triangle area | 严格正且大于批准阈值 |
| orientation | LinkMesh 当前 Adapter 接受绝对面积；若未来要求统一正向须先更新蓝图 |
| duplicate triangle | 禁止 |
| edge incidence | 只能为 1 或 2 |
| interfaces | 两侧 Region 不同的 incidence=2 共享 edge |
| non-manifold | 禁止 |
| native pointers | 不得保存到 `Mesh2D` |
| `outer_boundary` | 保留输入对象的正式几何边界副本，不从 refinement topology 反推 |

任务要求中提到“正有向面积”，但当前 `Mesh2D` 正式契约和 Adapter 实现只要求绝对
面积非退化，没有全局统一 triangle orientation 契约。未来若要求统一正向，必须先
更新蓝图，并明确由低层输出验证还是 LinkMesh 确定性重排每个 triangle；本报告不擅自
改变现有契约。

---

## 17. 质量与渐变验收指标

未来实现后，LinkMesh 生成侧至少计算：

### 17.1 triangle angle

对每个 triangle 的三边计算：

- minimum angle；
- maximum angle；
-低于锁定 q 目标的 triangle 数量。

### 17.2 shape quality

```text
Q = 4 * sqrt(3) * A / (l1^2 + l2^2 + l3^2)
```

性质：

-等边 triangle 为 1；
-退化 triangle 趋近 0。

### 17.3 equivalent size

```text
hK = sqrt(2 * A)
```

该定义与 OFT 当前 `Amax = dx^2/2` 对应，但 `hK` 是面积等效尺度，不是最大边长。

### 17.4 相邻 size ratio

对每对共享 edge 的相邻 triangles：

```text
max(hK1, hK2) / min(hK1, hK2)
```

分别统计：

-全局最大值和分位数；
- Region interface 附近；
-同 Region 内部。

### 17.5 transition profile

按粗侧 triangle 到 interface 的距离分箱：

-每箱 triangle 数；
- `hK` min/median/max/P10/P90；
-目标 `h(d)`；
-相对误差；
-首次达到粗侧稳定尺寸的距离；
-实际 transition thickness。

### 17.6 规模和成本

记录：

-每 Region triangle 数；
-总 nodes/triangles；
-refinement 前后增长率；
-每轮运行时间；
-总运行时间；
-迭代次数；
-重复运行的 arrays/connectivity/attributes 确定性。

### 17.7 验收层级

必须分开记录：

| 层级 | 可由 LinkMesh 生成侧检查 |
|---|---|
| 结构正确 | 是 |
| shape quality 改善 | 是 |
| transition thickness 接近 W | 是，需批准误差定义 |
| M3D-C1 数值稳定 | 否，本任务不调查 |
| 物理正确性 | 否，本任务不调查 |

---

## 18. CLI/config 候选

### 18.1 当前作用域

当前 `regions generate` 已有：

```text
--target
--multi-array-file
--regions-map
--mesh-dx
--region-dx
--hdf5
--model
--smb
--plot
--verbose
```

regions 配置使用独立 `RegionsGenerateConfig`，不污染旧 `EffectiveConfig`。

### 18.2 最小用户表面候选

Agent 建议未来只公开一个新参数：

```text
--transition-width FLOAT
```

语义候选：

-单位 m；
-未提供或 `0`：关闭 transition refinement；
-正有限值：启用；
-负值、NaN、Inf：配置阶段失败；
-只适用于 `regions generate`；
-对同一个生成 mesh 的所有 target 一致生效；
-发生在 Writer 之前；
-与 `mesh_dx/region_dx` 共同决定 hf/hc；
-相邻 effective dx 相同时不触发。

TOML 候选：

```text
[regions.mesh]
transition_width = <meters>
```

该字段尚未获蓝图批准，不是正式接口。

### 18.3 是否公开 minimum angle

本轮不建议首版公开 minimum-angle：

-当前 q 默认值尚未由目标源码确认；
-当前 OFT 高层 API 不暴露它；
-用户唯一目标是控制 W；
-增加 angle 会扩大接口和验收矩阵。

应先锁定 Triangle 默认 q 行为并验证 transition refinement。只有真实案例证明需要
用户控制时再更新蓝图。

### 18.4 是否公开 max iterations

首版可考虑内部受控常量，而不立即公开：

-避免用户同时调 W、angle、迭代次数；
-先通过探针确定一次或有限轮 refinement 的行为；
-达到上限时明确失败并输出诊断。

具体常量必须由蓝图批准。

---

## 19. 测试与真实案例矩阵

本节仅设计，不创建、不运行。

### 19.1 最小合成测试

| 案例 | 目的 |
|---|---|
| 两 Region，不同 dx | 基本粗细侧、interface、W |
| 三层 nested | 两条 transition |
| sibling | 一个 parent 对多个 child interfaces |
| 一个 Region 同时邻接更粗和更细 Region | 双重角色判定 |
| 相邻 Region 相同 dx | 不创建 transition、不 refinement |
| W 很小 | 接近当前薄层行为 |
| W 大于粗 Region 局部厚度 | 全 Region 受影响诊断 |
| 多 transition 重叠 | `min()` 组合 |
| 非连续 Region IDs | 不按数组位置解释 |
| q 不合格、面积合格 | q 是否单独触发 |
| 面积不合格、q 合格 | a 是否单独触发 |
| 面积和 q 都合格 | 不应无理由增长 |
| PSLG interface | refinement 前后共享界面保留 |
| Region attributes | refinement 前后集合与逐 triangle 传播 |
|有限迭代 | 停止条件和确定性 |
|输出 Mesh2D | shape/dtype/index/topology/ownership |

### 19.2 服务器真实矩阵

建议使用当前已验证的 multi-array 链：

1. two-level synthetic；
2. four-level nested；
3. sibling；
4. mixed tree；
5.真实 two-level；
6.真实 four-level；
7. `case_002` 的 W 扫描。

W 扫描候选只定义相对覆盖，不预设正式数值：

```text
W = 0
W << hc
W ≈ hc
W 为若干 hc
W 接近粗 Region 局部厚度
W 超过粗 Region 局部厚度
```

每个案例保存：

-完整 effective dx mapping；
-W；
-option string；
-每轮结构和质量统计；
-interface topology；
-Region attributes；
-运行时间；
-最终 PNG；
-失败日志。

未运行前状态必须保持 `NOT RUN`。

---

## 20. 最小未来修改范围

### 20.1 必须先修改

| 文件 | 原因 |
|---|---|
| `LinkMesh_Architecture_Plan.md` | 增加 refinement 阶段、W 字段、低层 ABI、ownership、验收和停止条件 |
| `docs/linkmesh/oft_triangle_transition_refinement_investigation.md` | 在 ABI 和探针完成后更新直接证据 |
| 相关现有测试 | 保护 transition、attributes、PSLG、ownership 和 Mesh2D 输出 |

达到明确战术节点并由 User 验收后，按项目纪律再更新：

- `History.md`
- `Project_Tree.md`（仅当新增文件或职责变化）

### 20.2 最小业务候选

| 文件 | 候选修改 |
|---|---|
| `src/linkmesh/mesher/oft_adapter.py` | 新增版本锁定的低层 Triangle refinement Adapter，或调用独立内部模块 |
| `src/linkmesh/regions.py` | 纯 topology interface 提取、粗细侧、距离/profile/area constraints |
| `src/linkmesh/config.py` | regions 专用 `transition_width` 合并与校验 |
| `src/linkmesh/cli.py` | 收集 W，在初始 mesh 与 Writer 之间调用 refinement |
| 必要独立调查脚本 | 先验证 native ABI、free、`-r`、attributes 和 PSLG |

若低层 Adapter 使 `oft_adapter.py` 过大，可在蓝图批准后新增一个窄职责模块；本报告不
预先确定文件名。

### 20.3 默认不修改

当前没有证据要求修改：

- `src/linkmesh/mesh.py`
- requirements
- HDF5 Writer
- TXT Writer
- SMB Writer
- regions map schema
- OFT/TokaMaker 外部源码
- Triangle 外部源码
- M3D-C1/PUMI

`Mesh2D` 不应保存 Triangle 私有状态或 effective dx。

---

## 21. 蓝图修订建议

在任何实现前，蓝图至少需要批准：

1. refinement 在 initial N-region mesh 与 Writer 之间的位置。
2. `transition_width` 的名称、单位、关闭语义和作用域。
3. effective dx mapping 显式传递规则。
4. interface 的 topology 定义。
5.粗侧/细侧和相同 dx 规则。
6.距离 d 的正式定义。
7.指数或线性 profile。
8.多个 interface 的组合规则。
9. `Amax=h^2/2` 的逐 triangle 转换。
10. low-level Triangle API 的版本锁定边界。
11.准确 option string。
12. q 默认角或受控角度策略。
13. triangle attributes 和 PSLG 保留要求。
14. native output ownership 与释放顺序。
15.有限迭代停止条件和安全上限。
16.输出 Mesh2D 的完整验证。
17.结构、shape、transition profile 验收指标。
18.失败状态和服务器探针矩阵。
19.明确禁止修改 OFT/Triangle 和引入第二剖分器。
20.消费端稳定性与物理正确性不由生成侧外推。

---

## 22. 未确认事项

当前仍缺少直接证据：

1. 锁定 Triangle 裸 `q` 默认最小角。
2.目标 `triangle.c` 对 `r` 的准确输入要求。
3. `p+r` 对 PSLG segment 的保留方式。
4. `trianglearealist` 的长度和值语义。
5. area constraints 对新 triangle 的传播。
6. q 与 a 的执行顺序。
7. triangle attributes 的 refinement 传播。
8.输入 point/segment marker 是否必须提供。
9.已有 points 是否全部保留。
10.已有 segments 是否可能拆分。
11.新 triangle 是否严格嵌套在输入 triangle。
12. output arrays 的实际 allocator。
13.所有 output pointers 的释放方法。
14.错误返回后的部分分配清理。
15. `trifree` 是否由当前共享库导出。
16. Python view 在释放前复制的完整字段集合。
17.多轮调用是否无泄漏。
18.候选 option string在服务器是否运行。
19.一次 refinement 对 W 的实际逼近误差。
20.有限迭代是否稳定终止。

---

## 23. 实施停止条件

当前已经触发以下停止条件：

### 23.1 native Triangle 准确实现未纳入当前可引用内容

缺失路径：

```text
TOKAMAKER\OpenFUSIONToolkit\src\ext_libs\triangle.c
```

需要最小只读权限的符号：

```text
triangulate
intern_triangulate
parsecommandline 或实际 option parser
quality/refinement 主循环
region attribute 传播
trianglearealist 读取和传播
output allocation
trifree 或实际释放函数
```

### 23.2 ownership/free 规则未确认

虽然 `triangle.h` 将 `trianglearealist` 标记为输入字段，但当前证据不足以确认：

- output pointer ownership；
-错误路径 ownership；
-正确释放函数；
-多轮 refinement 的无泄漏调用方式。

因此不能批准 LinkMesh 低层 Adapter。

### 23.3 后续继续调查所需最小只读证据

请将以下文件完整加入后续只读调查：

```text
TOKAMAKER\OpenFUSIONToolkit\src\ext_libs\triangle.c
```

如 `triangle.c` 显示释放函数或导出 wrapper 位于其他文件，还需仅追加该符号所在的
最小文件。还应提供目标 OFT 26.6 构建中 `liboft_triangle` 的导出符号证据，以确认：

```text
triangulate
trifree（若适用）
```

在这些证据到位前，不用一般 Triangle 经验补足 ABI。

---

## 24. 最终可行性裁决

### 24.1 对十八个必须问题的回答

1. **OFT 当前为何形成薄变化层？**  
   共享 interface 按相邻 Region 的更小 `dx` 重采样，而粗 Region 内部仍使用
   `hc^2/2` 的常数面积约束，且没有 W/gradation 参数。

2. **当前 q 的准确行为和可调性？**  
   OFT 使用硬编码裸 `q`；LinkMesh/OFT 高层 API 当前不可调。裸 q 的锁定默认角和
   refinement 精确行为因缺少 `triangle.c` 仍待确认。

3. **OFT 高层 API 是否支持 refinement？**  
   **不支持。** 当前 `gs_Domain`、`Mesh` 和 `run_triangle()` 没有公开 refinement
   入口。

4. **低层 binding 是否足以安全执行 refinement？**  
   结构字段表面足够表达候选输入，但 ownership/free 规则未确认，当前不能判定为安全。

5. **是否需要修改或重新编译 OFT/Triangle？**  
   目前没有证据证明必须修改或重新编译；也没有足够证据证明完全不需要。若现有
   `triangulate` 和释放符号足够，可由 LinkMesh 低层 Adapter 完成。

6. **`trianglearealist` 能否作为输入？**  
   `triangle.h:266` 直接标记为 `In only`，Python结构也有该字段；但目标 refinement
   的值语义、长度和传播仍未确认，不能宣告当前 LinkMesh 可用。

7. **如何保持 interfaces 和 Region attributes？**  
   候选是提交 topology outer edges 与 cross-Region interface edges 作为完整 PSLG，
   并提交每 triangle 的一个 Region attribute。是否由目标 binary 正确保留仍待验证。

8. **一次 refinement 是否足够？**  
   不一定。初始 triangle 采样的 profile 可能需要有限迭代重新计算。

9. **面积达标但形状差时 q 是否仍触发？**  
   Triangle 通用机制候选为会触发，但目标 OFT 26.6 的直接源码和运行证据尚缺。

10. **q+a 是否直接保证 W？**  
    **不能。** q 约束形状，a 约束离散 triangle 面积；W 是 LinkMesh 通过距离
    profile 映射出的目标，最终只能通过生成后分箱指标验收。

11. **推荐 d？**  
    粗侧 triangle centroid 到实际 interface mesh segments 的欧氏最短距离。

12. **推荐 h(d)？**  
    首版候选为指数 profile，并截断到 `[hf,hc]`。

13. **多个 interfaces 如何组合？**  
    只在各自粗侧生效，对同一 triangle 取所有候选尺寸和 Region 基准尺寸的最小值。

14. **W 以米表示是否可行？**  
    数学上可行；坐标和 dx 都以 m 表示，欧氏距离 d 也以 m 表示。

15. **refinement 后如何构造 Mesh2D？**  
    复制 native 输出到 Python-owned arrays，释放 native 内存，重新验证
    nodes/triangles/attributes/topology，并保留原 `outer_boundary` 独立副本。

16. **最小实现修改文件候选？**  
    蓝图、`oft_adapter.py`、`regions.py`、regions config/CLI 和现有相关测试；通常不
    修改 `Mesh2D`、Writer、requirements 或 regions map schema。

17. **蓝图必须先修订什么？**  
    W、d、profile、area mapping、low-level ABI、free、PSLG、attributes、迭代、
    输出验证和生成侧验收标准。

18. **仍缺哪些直接证据？**  
    完整目标 `triangle.c`、导出释放符号、`-r` 输入和传播契约，以及服务器最小
    ABI/refinement 探针。

### 24.2 五选一最终状态

```text
BLOCKED BY MISSING ABI/OWNERSHIP EVIDENCE
```

这不是判定算法不可行，也不是判定必须修改 OFT。当前更精确的工程结论是：

- OFT 高层 API 不直接支持所需 refinement；
-现有 ctypes 结构在形状上具备表达 refinement 输入的候选能力；
- LinkMesh 可以在 initial mesh 后计算 interface、d、h(d) 和逐 triangle Amax；
-但 native `-r` 契约、attribute/PSLG 传播与输出释放规则尚未由目标源码关闭；
-在补齐 `triangle.c` 和导出符号证据前，不能把候选升级为
  `FEASIBLE BUT REQUIRES LINKMESH-SIDE LOW-LEVEL ADAPTER`；
-不得开始业务实现、CLI/config 修改或多轮 native 调用。
