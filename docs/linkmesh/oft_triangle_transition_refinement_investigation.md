# OFT 26.6 / Triangle 多区域网格渐变 Refinement 调查报告

- 文档主受众：Aider-facing / Human-facing
- 知识库用途：专项只读源码调查
- 调查状态：native ABI、refinement 与 ownership 静态源码契约已确认；待服务器核验
  `liboft_triangle.so` 的实际导出符号和动态依赖
- 最终裁决：**BLOCKED BY MISSING RUNTIME EXPORT EVIDENCE**
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
| Triangle 随附 C 源码直接事实 | `triangle.c` 已直接确认 option parser、`-r`、质量判据、属性传播、输出分配与 `trifree()` |
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
| `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.h` | `struct triangulateio`、`triangulate()`、`trifree()` 声明 | native 字段顺序、C 类型和公开函数签名 |
| `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/triangle.c` | 文件头、`parsecommandline()`、`reconstruct()`、`testtriangle()`、`insertvertex()`、`writenodes()`、`writeelements()`、`writepoly()`、`intern_triangulate()`、`triangulate()` | Triangle 1.6 身份、refinement 契约、属性/面积传播、输出分配与释放实现 |
| `TOKAMAKER/OpenFUSIONToolkit/src/ext_libs/CMakeLists.txt` | `add_library(oft_triangle SHARED triangle.c)`、`target_compile_definitions(...)` | `liboft_triangle` 的编译宏、共享库形态和安装位置 |

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

### 2.3 版本、编译宏与剩余运行时证据

`triangle.c` 文件头直接标识：

```text
Triangle Version 1.6
July 28, 2005
```

OFT 的 `ext_libs/CMakeLists.txt` 直接构建：

```cmake
add_library(oft_triangle SHARED triangle.c)
target_compile_definitions(
  oft_triangle PRIVATE
  -DTRILIBRARY
  -DANSI_DECLARATORS
  -DNO_TIMER
  -DREAL=double
  -DVOID=void
)
```

由此确认：

- `TRILIBRARY`：编译 callable-library 路径，公开 `triangulate()` 而非 CLI `main()`；
- `ANSI_DECLARATORS`：采用 ANSI 原型路径；
- `NO_TIMER`：移除 Unix timing 代码，不改变 `triangulateio` 布局；
- `REAL=double`：native `REAL` 与 Python `ctypes.c_double` 一致；
- `VOID=void`：`trifree(VOID*)` 等价于 `trifree(void*)`；
-未定义 `SINGLE`、`REDUCED`、`CDT_ONLY`，因此 double precision、完整 refinement、
  quality 和 segment 功能均被编译；
- Intel Fortran 工具链下目标使用 `-O0`，其他工具链使用 `-O1`；该优化选项不改变
  ABI；
-目标是 `SHARED` library，并安装到 `bin`。

`triangle.h` 的准确公开签名是：

```c
int triangulate(
    char *,
    struct triangulateio *,
    struct triangulateio *,
    struct triangulateio *);
void trifree(VOID *memptr);
```

`triangle.c` 的 `TRILIBRARY` wrapper 实现与头文件一致：`triangulate()` 返回 `int`，
内部以 `setjmp()`/`longjmp()` 把 Triangle 错误状态转换为非零返回值。

OFT Python 的绑定：

```text
argtypes = [
    c_char_p,
    POINTER(triangle_struct),
    POINTER(triangle_struct),
    POINTER(triangle_struct),
]
restype = c_int
```

与 native `triangulate()` 匹配。Python `triangle_struct._fields_` 与
`triangle.h::triangulateio` 的字段顺序逐项一致；`REAL*` 对应 `c_double_ptr`，
`int*` 对应 `c_int_ptr`，计数字段对应 `c_int`。

静态源码和构建契约还不能代替目标服务器共享库的实际导出表。剩余纯运行时证据只有：

1. 实际加载的 `liboft_triangle.so` 路径；
2. `file` 对该文件的架构/类型输出；
3. `triangulate` 是否实际导出；
4. `trifree` 是否实际导出；
5. `ldd` 是否报告缺失动态库。

因此当前阻塞点已从 ABI/ownership 源码缺口缩小为 runtime export evidence。

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

### 5.1 option parser 直接事实

`triangle.c::parsecommandline()` 初始化：

```c
b->minangle = 0.0;
```

并逐字符解析本任务相关开关：

| 开关 | native 解析结果 |
|---|---|
| `p` | `b->poly = 1` |
| `r` | `b->refine = 1` |
| `q` | `b->quality = 1`，随后解析连续数字和小数点 |
| `a` | `b->quality = 1`；带数值时设置固定全局面积，不带数值时设置逐区/逐 triangle 面积 |
| `A` | `b->regionattrib = 1` |
| `z` | `b->firstnumber = 0` |
| `Q` | `b->quiet = 1` |

裸 `q` 的锁定源码默认值明确为：

```c
b->minangle = 20.0;
```

`q` 后可直接跟十进制数字或小数点，例如 `q25`、`q28.6`。parser 使用 `strtod()`；
该解析分支没有显式数值上限校验，也不接受指数记法，因为扫描循环只接受数字和
`.`。随后源码计算 `goodangle` 和 `offconstant`。

当前 OFT `run_triangle()` 的 `pqaAzQ` 因而准确表示：

- PSLG；
-默认 20° 最小角质量细化；
-读取 Region 最大面积；
-初始 PSLG Region attributes；
- 0-based；
- quiet。

### 5.2 refinement 组合与候选字符串

`parsecommandline()` 支持 `r` 与 `p`、`q`、`a`、`A` 的组合。不过 parser 在末尾明确
执行：

```c
if (b->refine || !b->poly) {
  b->regionattrib = 0;
}
```

所以 `A` 在 refinement 中会被关闭；它不会新增 Region attribute。已有
`triangleattributelist` 通过 `reconstruct()` 的 `m->eextras` 路径保留。

本任务静态源码支持的最小候选 option string 是：

```text
rpqazQ
```

含义：

- `r`：重建并细化已有 mesh；
- `p`：同时重建受约束 segments；
-裸 `q`：继续使用 20° 质量约束；
-裸 `a`：读取每个输入 triangle 的 `trianglearealist`；
- `z`：输入输出均为 0-based；
- `Q`：quiet。

不需要 `A`，因为 refinement 会忽略它。该字符串是静态源码候选，尚未在目标服务器
运行。

### 5.3 面积与 q 的独立触发

`triangle.c::testtriangle()` 依次检查：

1. fixed area；
2. per-triangle variable area；
3. user test；
4. minimum-angle quality。

因此：

-面积超过正 `areabound` 时会进入 bad-triangle queue；
-面积达标不会因面积判据细化；
-面积达标但最小角不达标时，仍会因 q 进入 bad-triangle queue；
-面积和 q 都达标时，该函数不会将 triangle 加入质量队列。

### 5.4 最小角边界和 PSLG 小角

锁定 Triangle 1.6 随附说明明确记载：

- `q` 默认把最小角目标设为 20°；
-最小角不超过 28.6° 时，在无限精度假设下有终止保证；
-实践中常能达到约 34°，但某些网格需要降低目标；
-有限浮点精度可能使 refinement 无法终止或产生 precision error；
-输入 PSLG 的小夹角不能被 q 消除，附近可能仍产生低于请求值的角；
- `precisionerror()` 建议增大面积阈值和/或降低最小角；
-达到 Steiner 点上限时可能留下 encroached subsegments，并输出非真正 Delaunay 的
  warning。

当前 LinkMesh/OFT 高层 API 仍不暴露 minimum angle。未来若需 `q25`，只能由
LinkMesh 低层 Adapter 构造 option string；无需修改 OFT 源码，静态源码也未显示需要
重新编译 Triangle。

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

静态源码和 OFT 构建定义已经关闭结构 ABI 的源码证据：

- `REAL=double`，对应 `ctypes.c_double`；
- `VOID=void`；
- native `int` 字段和指针对应 `ctypes.c_int`/`POINTER(c_int)`；
- `triangle_struct` 与 `triangulateio` 字段顺序逐项一致；
-未设置自定义 packing；
- `triangulate()` 的四个参数和 `int` 返回值与 OFT ctypes 绑定一致；
- `trifree(void*)` 是对应的 native 释放入口。

`triangle.c` 中 `trimalloc()` 调用 C `malloc()`，`trifree()` 调用 C `free()`。
LinkMesh 不应直接绑定 libc `free`；应绑定同一 `liboft_triangle.so` 中的
`trifree()`，以保持 allocator 边界一致。

剩余问题不是结构布局，而是服务器实际共享库是否导出 `trifree`。CMake 将
`triangle.c` 直接编译为共享库，源码中的 `triangulate` 和 `trifree` 都不是
`static`，因此按当前构建应导出；仍需在目标服务器以动态符号表实证。

---

## 7. `-r` refinement 输入/输出契约

### 7.1 `trianglearealist` 直接契约

`triangle.c::reconstruct()` 在 `TRILIBRARY` 路径中设置：

```text
m->inelements = in->numberoftriangles
incorners = in->numberofcorners
m->eextras = in->numberoftriangleattributes
```

随后按输入 triangle 的顺序遍历，每个 triangle 在 `b->vararea` 为真时读取：

```c
area = trianglearealist[elementnumber - b->firstnumber];
setareabound(triangleloop, area);
```

因此：

-数组长度必须至少为 `numberoftriangles`；
-第 `i` 项对应 `trianglelist` 中第 `i` 个输入 triangle；
-裸 `a` 设置 `b->vararea=1`，refinement 才读取该数组；
-正值是该 triangle 的最大允许面积；
-零和负值均表示该 triangle 不受 variable-area 约束，因为
  `testtriangle()` 仅在 `areabound > 0.0` 且实际面积更大时触发；
-源码不会自动检查 Python 数组长度，过短会导致越界 native 读取，所以 LinkMesh
  必须在调用前严格验证 `(T,) float64`。

### 7.2 面积与质量细化

`testtriangle()` 直接确认：

-实际面积大于正 `areabound`：因面积进入 refinement；
-实际面积小于等于约束：不因面积进入 refinement；
- q 判据随后独立检查，所以面积达标但角度不达标仍会细化；
-两者均达标时不进入 bad-triangle queue。

`insertvertex()` 在拆分 triangle 时把父 triangle 的 `areabound` 复制给新
triangles；在 edge flip 时，如果两侧约束均为正，则取两者平均，否则设为 `-1.0`。
所以 area constraint 不是不可跨越普通 mesh edge 的永久标签：它可在未受 PSLG
保护的 edge flip 中平均扩散。

### 7.3 输入 triangle、嵌套性和约束传播

refinement 由 `reconstruct()` 重建输入 mesh，再执行 Delaunay/quality 操作。源码
明确允许 edge flips，并说明 refinement 不是 hierarchical：

-输出保留输入 corner nodes，并把新 nodes 追加在后；
-输出 element 不保证严格包含在单个输入 element 中；
-输出 triangle 可跨越原普通 triangle edge；
-一个输出 element 可能覆盖两个或三个输入 elements；
- PSLG segment 是不可翻转的约束边，因此不能被新 triangle 跨越。

所以一次调用中的 `trianglearealist` 是定义在输入 triangles 上的分片常数初值，
随后可通过拆分复制并通过普通 edge flip 平均传播。它不能直接表达在新 triangle
centroid 上重新采样的连续 `h(d)`；若要求更准确逼近 W，仍需要有限次重新计算。

### 7.4 refinement 必需输入

本任务的安全候选输入是：

| 字段 | 要求 |
|---|---|
| `pointlist` | `(N,2)` C-contiguous `float64` |
| `numberofpoints` | `N` |
| `pointattributelist` | 无 point attributes 时为 NULL |
| `numberofpointattributes` | `0` |
| `pointmarkerlist` | 可为 NULL，native 默认 marker 0 |
| `trianglelist` | `(T,3)` C-contiguous `int32`、0-based |
| `numberoftriangles` | `T` |
| `numberofcorners` | `3` |
| `triangleattributelist` | `(T,1)` C-contiguous `float64` |
| `numberoftriangleattributes` | `1` |
| `trianglearealist` | `(T,)` C-contiguous `float64` |
| `segmentlist` | `(S,2)` C-contiguous `int32`、0-based |
| `numberofsegments` | `S` |
| `segmentmarkerlist` | 可为 NULL，marker 默认 0 |
| `holelist`/`regionlist` | refinement 不执行 carve/spread，可为 NULL 且 count 为 0 |

候选 option string：

```text
rpqazQ
```

`p` 必须保留，以使 `reconstruct()` 创建并连接 input segments。`A` 不需要且会在
refinement 模式被 parser 关闭。

---

## 8. 内存 ownership 和释放

### 8.1 allocator 和公开释放入口

`triangle.c::trimalloc()` 使用：

```c
malloc((unsigned int) size)
```

`triangle.c::trifree()` 使用：

```c
free(memptr)
```

`triangle.h` 公开声明：

```c
void trifree(VOID *memptr);
```

OFT 以 `VOID=void` 构建，因此准确签名为 `void trifree(void*)`。LinkMesh 应从
`oft_triangle_lib` 额外绑定该函数为：

```text
argtypes = [c_void_p]
restype = None
```

不得直接调用 Python 进程加载的 libc `free`。

### 8.2 字段级 ownership

下表假定 LinkMesh 把所有 `out` 指针预初始化为 NULL；若调用者预先提供 output
buffer，则该 buffer 仍由调用者拥有，Triangle 不负责释放。

| field | input ownership | output ownership | alias possibility | Python copy | free |
|---|---|---|---|---|---|
| `pointlist` | NumPy/input-owned | NULL 时由 Triangle `trimalloc` |正常路径不与 input 别名 | 必须 | output 非 NULL 时 `trifree` |
| `pointattributelist` | NumPy/input-owned 或 NULL |有 attributes 且 NULL 时由 Triangle 分配 |正常路径不别名 | 若请求则必须 | `trifree` |
| `pointmarkerlist` | NumPy/input-owned 或 NULL |未用 `B` 且 NULL 时由 Triangle 分配 |正常路径不别名 | 若请求则必须 | `trifree` |
| `trianglelist` | NumPy/input-owned | NULL 时由 Triangle 分配 |不与 input 别名 | 必须 | `trifree` |
| `triangleattributelist` | NumPy/input-owned |有 attributes 且 NULL 时由 Triangle 分配 |不与 input 别名 | 必须 | `trifree` |
| `trianglearealist` | NumPy/input-owned | input only，不写 output |无 output 指针 | 不适用 | 不释放 input |
| `neighborlist` |无 input ownership |仅 `n` 时分配 |不别名 |需要时复制 | `trifree` |
| `segmentlist` | NumPy/input-owned | `p`/`c` 且允许 poly output 时分配 |不与 input 别名 |多轮 refinement 必须 | `trifree` |
| `segmentmarkerlist` | NumPy/input-owned 或 NULL |未用 `B` 时随 segment output 分配 |不与 input 别名 |多轮 refinement 必须 | `trifree` |
| `holelist` | NumPy/input-owned | `out->holelist = in->holelist` |明确别名 |通常不复制 |绝对不得从 out 释放 |
| `regionlist` | NumPy/input-owned | `out->regionlist = in->regionlist` |明确别名 |通常不复制 |绝对不得从 out 释放 |
| `edgelist` |无 input ownership |仅 `e` 时分配 |不别名 |需要时复制 | `trifree` |
| `edgemarkerlist` |无 input ownership | `e` 且未用 `B` 时分配 |不别名 |需要时复制 | `trifree` |
| `normlist` |无普通 mesh input |仅 Voronoi output 分配 |不别名 |需要时复制 | `trifree` |

本任务的 `rpqazQ` 不请求 neighbors、edges 或 Voronoi，但会输出 points、point
markers、triangles、triangle attributes、segments 和 segment markers。多轮调用需要
复制并释放这六类 native allocations。

### 8.3 hole/region alias 与 double-free

`intern_triangulate()` 在写 PSLG output 后明确执行：

```c
out->holelist = in->holelist;
out->regionlist = in->regionlist;
```

这两个字段只是借用 input 指针，不是新分配。释放规则：

- input NumPy arrays由 Python 管理；
-不得对 `out->holelist` 或 `out->regionlist` 调用 `trifree`；
-即使二者非 NULL，也不能仅凭“out pointer 非 NULL”判断需要释放；
-本任务 refinement 可把 input count 设为 0、指针设为 NULL，从源头避免别名处理。

### 8.4 错误路径和部分分配

`triangulate()` 通过 `setjmp()` 捕获 `triexit()`。如果错误发生在 output 写出阶段，
此前成功执行的 `writenodes()`、`writeelements()` 或 `writepoly()` 可能已经分配部分
output arrays。源码没有统一的 output rollback。

LinkMesh 低层 Adapter 必须：

1. 调用前保存哪些 output 字段由 Adapter 以 NULL 提交；
2. 无论返回值为零还是非零，都检查这些 output-owned 字段；
3. 成功时先复制所需 arrays，再进入释放；
4. 失败时不读取未完成的 shape 数据，只释放已非 NULL 的 output-owned pointers；
5. 跳过 `holelist`、`regionlist` 和所有 input-owned pointers；
6. 每个 native pointer 最多释放一次；
7. 清空已释放的 ctypes field，避免清理分支重复释放。

### 8.5 `vorout`

`triangle.h` 说明未使用 `v` 时 `vorout` 可以是 NULL。当前 OFT wrapper传入一个零初始
`vor_struct`，也不会触发 Voronoi 分配。

LinkMesh 候选低层 Adapter 可传 `None` 作为第四参数，因为 `rpqazQ` 不含 `v`；
这比创建无用结构更明确。

### 8.6 无泄漏同步调用顺序

在服务器确认 `trifree` 导出后，多轮同步调用可以采用确定顺序：

```text
构造并强引用所有 Python-owned contiguous inputs
→ 将所有 output pointers 初始化为 NULL
→ triangulate(...)
→ 成功时按 native counts 创建 view 并立即 copy()
→ 在 finally 中逐个 trifree output-owned pointers
→ 清空 ctypes pointers
→ 验证 Python-owned copies
→ 开始下一轮
```

静态源码已经确认该 ownership 方案；剩余阻塞只在实际共享库是否导出 `trifree`。

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

### 9.2 refinement attributes 直接契约

候选 refinement 输入应把当前 `Mesh2D.region_ids` 转为：

```text
triangleattributelist (T,1) float64
numberoftriangleattributes = 1
```

`reconstruct()` 按每个输入 triangle、每个 attribute 读取
`triangleattriblist[attribindex++]`。`insertvertex()` 创建子 triangle 时复制父
triangle attributes；普通 edge flip 时取两侧 attribute 的平均值。

这意味着 Region ID 可以原生保留，但有一个关键前提：

```text
所有不同 Region 的共享 interface 必须作为 PSLG segment 提交
```

segment edge 不允许 flip，所以不同 Region attributes 不会在 interface 两侧平均。
同一 Region 内两侧 attribute 相同，平均后数值不变。因此在完整 interface PSLG
前提下，输出 `(T,1)` attribute 可直接恢复原整数 Region ID，无需几何回查、重建、
重编号或 `+1`。

`A` 在 refinement 中不会新增 attribute，因为 parser 主动清除
`b->regionattrib`；保留 Region ID 依赖输入 `numberoftriangleattributes=1` 和
`triangleattributelist`，不依赖 `A`。

输出后仍必须验证：

- attribute 全部有限且具有整数语义；
- attribute 集合严格等于输入正式 Region ID 集合；
-每个 Region 仍有 triangles；
-任何非整数或未知 attribute 都作为 native contract failure，而不做最近邻恢复。

### 9.3 PSLG 与 conforming topology

从当前 triangles 和 region IDs 可确定性提取：

- edge incidence=1：计算域外边界；
- edge incidence=2 且两侧 Region ID 不同：内部 Region interface；
- edge incidence=2 且两侧 Region ID 相同：Region 内部 edge；
- incidence>2：non-manifold，失败。

本任务提交：

```text
segments =
    all incidence=1 outer topology edges
    ∪ all cross-Region incidence=2 interface edges
```

符合 native PSLG 输入契约：segment endpoints 都是 `pointlist` 中的 0-based vertex
indices，且每条 segment 对应已重建 mesh edge。

`reconstruct()` 在 `p+r` 路径中创建 subsegments 并连接到相邻 triangles。后续
quality refinement：

-不得 flip PSLG segment；
-新 triangle edge 不得跨越 PSLG segment；
-允许拆分 encroached segment，并插入新的 segment vertex；
-输出 `segmentlist` 包含拆分后的 subsegments；
-全局 mesh 保持共形；
-输入 linear corner points保持在输出点集中，新增点追加；必须设置
  `numberofcorners=3`，避免高阶额外节点被 `reconstruct()` 丢弃；
- point markers 可为 NULL，默认 0；
- segment markers 可为 NULL，默认 0；
- markers 不承担 Region identity，Region identity由 triangle attributes承担；
- refinement 分支不执行 `carveholes()` 或新的 Region propagation，因此
  `holelist`、`regionlist` 可为 NULL 且 counts 为 0。

多轮 refinement 必须使用上一轮输出的拆分后 `segmentlist`，不能继续提交旧的
pre-refinement segments。

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

native 静态源码已确认 ABI、`-r`、q/a、attributes、PSLG 和 ownership 契约。当前只剩
以下运行时或尚未执行的证据：

1. 服务器实际加载的 `liboft_triangle.so` 路径。
2. 该文件的架构和 shared-object 身份。
3. `triangulate` 是否出现在实际动态符号表。
4. `trifree` 是否出现在实际动态符号表。
5. `ldd` 是否存在缺失依赖。
6.候选 `rpqazQ` 是否在目标服务器成功运行。
7.实际输出 attributes 是否保持整数 Region IDs。
8.拆分后的外边界和内部 interface segments 是否完整输出。
9.成功和故意失败调用后的常驻内存是否符合预期。
10.一次 refinement 对 W 的实际逼近误差。
11.有限迭代是否稳定终止。

第 6-11 项属于后续最小服务器验证，不改变本文的静态源码结论，也不得在未运行前写成
已验证能力。

---

## 23. 实施停止条件

native 源码缺失和 ownership 不明这两个停止条件已经解除：

- `triangle.c` 已确认 `triangulate()` 的错误包装；
- `reconstruct()` 已确认 refinement 输入；
- `testtriangle()` 已确认 q/a 独立判据；
- `insertvertex()` 已确认 attributes 和 area constraints 的复制/平均；
- `writenodes()`、`writeelements()`、`writepoly()` 已确认输出分配；
- `trimalloc()`/`trifree()` 已确认 allocator 配对；
- `triangle.h` 和 OFT CMake 已确认 ABI 类型与编译宏。

当前唯一停止条件是实际共享库导出尚未实证。服务器只需一次性确认：

```text
实际 liboft_triangle.so 路径
file <实际路径>
动态符号表中的 triangulate
动态符号表中的 trifree
ldd <实际路径> 是否含 not found
```

不要求创建或维护新的长期 probe。若 `triangulate` 与 `trifree` 均导出且动态依赖完整，
静态证据支持把最终状态升级为：

```text
FEASIBLE BUT REQUIRES LINKMESH-SIDE LOW-LEVEL ADAPTER
```

若 `trifree` 未导出，则不能用 libc `free` 绕过；在“不修改或重编 OFT/Triangle”
边界下应保持阻塞。

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
   静态 ABI 与 ownership 契约足以构造安全的 LinkMesh 低层调用；仍需确认实际共享库
   导出 `trifree` 后才能运行。

5. **是否需要修改或重新编译 OFT/Triangle？**  
   静态源码显示不需要。LinkMesh 可复用 `oft_triangle_lib`，自行绑定 `triangulate` 和
   `trifree`。若服务器库未导出 `trifree`，则在当前边界下保持阻塞，不能以 libc
   `free` 绕过。

6. **`trianglearealist` 能否作为输入？**  
   **能。** 裸 `a` refinement 按输入 triangle 顺序读取 `(T,)` constraints；正值是
   最大面积，零/负值是不约束。数组长度必须由 LinkMesh 在 native 调用前严格验证。

7. **如何保持 interfaces 和 Region attributes？**  
   提交 outer edges 与全部 cross-Region interface edges 作为 PSLG，并提交
   `(T,1)` input attributes。受约束 interface 不允许 flip，子 triangle 原生继承
   attributes，无需几何回查或重编号。

8. **一次 refinement 是否足够？**  
   不一定。初始 triangle 采样的 profile 可能需要有限迭代重新计算。

9. **面积达标但形状差时 q 是否仍触发？**  
   **会。** `testtriangle()` 在面积判据之后独立执行 minimum-angle 判据。

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
    只缺目标服务器实际 `liboft_triangle.so` 的路径、架构、`triangulate`/`trifree`
    动态导出和依赖完整性，以及尚未执行的最小 refinement 运行验证。

### 24.2 最终状态

```text
BLOCKED BY MISSING RUNTIME EXPORT EVIDENCE
```

最终静态裁决：

- LinkMesh 能构造 `rpqazQ` refinement 所需的 contiguous、typed、0-based 输入；
- `trianglearealist` 原生支持逐输入 triangle 的面积上界；
- Region attributes 可在完整 interface PSLG 前提下原生保留；
-外边界和内部 interfaces 可作为 PSLG 原生保留，并允许共形拆分；
- native 输出可先复制到 Python-owned NumPy arrays，再用同库 `trifree()` 逐字段释放；
-当前 OFT `run_triangle()` 确实没有复制或释放由 native 分配的 points、point markers、
  triangles、triangle attributes、segments 和 segment markers，因此每次当前初始生成
  调用都会遗留这些 native allocations；
- LinkMesh 低层 Adapter 可以独立修复自己新增调用的完整生命周期，无需修改 OFT
  wrapper；
-静态源码不要求修改或重新编译 OFT/Triangle；
-只要服务器实际库导出 `triangulate` 和 `trifree` 且依赖完整，即具备进入蓝图迭代的
  技术条件；
-在运行时导出核验前，不得把静态可行性写成运行通过，也不得开始完整业务实现。
