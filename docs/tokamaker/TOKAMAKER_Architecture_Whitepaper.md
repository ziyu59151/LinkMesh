# TOKAMAKER 网格生成链路与 LinkMesh 架构对齐白皮书

- 文档主受众：LinkMesh 开发团队
- 知识库用途：侦察证据
- 文档状态：当前有效
- 最高依据：当前仓库的 CONTEXT.md (LinkMesh 敏捷开发工作流规范)
- 事实边界：本文档是基于 TOKAMAKER/OFT 只读技术资产形成的参考工程白皮书。本文档中的所有底层物理与接口调研情报，在当前阶段【仅服务于 LinkMesh 独立命令行程序具体解析与写入脚本的编写】，不涉及任何通用抽象中间件或插件体系设计。本文档不承载 LinkMesh 的正式组件接口定义，也不得替代 `LinkMesh_Architecture_Plan.md` 中关于 LinkMesh 各模块边界的最高技术蓝图。
- 主要用途：帮助 LinkMesh 开发团队理解 TOKAMAKER/OFT 的 Triangle 网格生成链路，为 LinkMesh `mesher/triangle_wrapper.py` 模块的 Triangle 调用封装提供参考。
- 修改前置条件：如需把本文档中的架构启示转化为 LinkMesh 代码实现，必须先完成对应方案审阅，并同步更新 `LinkMesh_Architecture_Plan.md`。

## 1. 文档定位

本文档记录 LinkMesh 项目在外部参考代码宏观哨探阶段，对 TOKAMAKER / OpenFUSION Toolkit 网格生成链路与 Triangle 库集成方式的第一层结构化分析。

本轮分析严格基于以下只读技术资产：

- `TOKAMAKER/oft-meshing-architecture/SKILL.md`
- `TOKAMAKER/triangle-library-integration/SKILL.md`
- `CONTEXT.md`

本文档不直接分析尚未加载的外部源码文件，不对未读取的实现细节进行推测。本文的作用是：

1. 从宏观层面对齐 TOKAMAKER 的二维三角网格生成事实与 LinkMesh 的 `mesher/` 模块规划；
2. 评估 Triangle 风格的二维非结构化网格拓扑事实如何被 LinkMesh 的内存数据结构承载；
3. 明确下一轮 BFS 第二层源码侦察所需物理拉取清单；
4. 为 LinkMesh `mesher/triangle_wrapper.py` 的实现提供 Triangle 集成规范参考。

---

## 2. 宏观调用链路概览

根据 `TOKAMAKER/oft-meshing-architecture/SKILL.md`，TOKAMAKER / OFT 的三角网格生成链路可以抽象为以下分层结构：

```text
Python 用户层
gs_Domain.build_mesh()
    - 管理几何区域
    - 定义 plasma / vacuum / boundary / conductor / coil 等区域语义
    - 调用 Mesh 类生成网格

        ↓

Python 中间层
Mesh 类
    - 点合并
    - 边界段合并与拆分
    - 共享边界处理
    - 边界重采样
    - 区域标记点生成
    - 构造 Triangle 输入字典

        ↓

Python 封装层
run_triangle(alpha)
    - 将 Python dict 转换为 C 风格 triangle_struct
    - 通过 ctypes 调用 oft_triangulate
    - 将 Triangle 输出转换为 NumPy 数组

        ↓

Python ctypes 接口层
_interface.py
    - 动态加载 liboft_triangle
    - 绑定 triangulate 函数签名

        ↓

共享库层
liboft_triangle.so / liboft_triangle.dylib / liboft_triangle.dll
    - 导出 triangulate 符号

        ↓

C 源码层
src/ext_libs/triangle.c
    - triangulate()
    - intern_triangulate()
    - Delaunay 三角化与质量优化
```

对 LinkMesh 的启示是：LinkMesh 的 `mesher/triangle_wrapper.py` 可以参考 OFT 的 Python ctypes 封装方式，直接调用 `triangle` Python 包（或通过 ctypes 调用 `triangle.c`），无需重新实现 Triangle 算法本身。

---

## 3. TOKAMAKER / Triangle 暴露的核心网格事实

当前 Skill 文本明确提到，TOKAMAKER 在调用 Triangle 前会构造类似如下输入结构：

```python
alpha = {
    "vertices": self._resampled_points,
    "segments": resampled_flat,
    "regions": self._reg_defs,
}
```

这些对象可解释为：

| 名称 | 形态 | 网格含义 |
|---|---|---|
| `vertices` | `[N, 2]` | 二维边界点坐标表 |
| `segments` | `[M, 2]` | 边界线段连接表 |
| `regions` | `[K, 4]` | 区域内部标记点、区域 ID 与最大面积约束 |

其中 `regions` 通常具有如下逻辑结构：

```text
[x, y, region_id, max_area]
```

含义分别是：

| 字段 | 含义 |
|---|---|
| `x` | 区域内部标记点的第一坐标 |
| `y` | 区域内部标记点的第二坐标 |
| `region_id` | 区域编号或区域属性 |
| `max_area` | 该区域允许的最大三角形面积约束 |

对 LinkMesh 的直接意义是：LinkMesh 的 `mesher/triangle_wrapper.py` 在调用 Triangle 时，需要构造类似的 `vertices`、`segments`、`regions` 输入，其中 `regions` 的 `region_id` 将直接对应 LinkMesh 内存网格对象中的区域标记，并最终被 `writers/smb_writer.py` 写入 `.smb` 文件的区域标记字段。

---

## 4. Triangle 输出字段与 LinkMesh 内存网格对象的对齐

根据 `TOKAMAKER/triangle-library-integration/SKILL.md`，`triangulateio` 结构体的主要输出字段包括：

| 输出字段 | 含义 | LinkMesh 内存对象对应字段 |
|---|---|---|
| `pointlist` | 节点坐标列表 `[N, 2]` | `mesh.nodes`：`np.ndarray shape=(N,2)` |
| `trianglelist` | 三角形连接表 `[T, 3]` | `mesh.triangles`：`np.ndarray shape=(T,3)` |
| `triangleattributelist` | 三角形区域属性 `[T, 1]` | `mesh.region_ids`：`np.ndarray shape=(T,)` |
| `segmentlist` | 边界线段连接表 `[S, 2]` | `mesh.boundary_segments`：`np.ndarray shape=(S,2)` |
| `segmentmarkerlist` | 边界线段标记 `[S, 1]` | `mesh.boundary_markers`：`np.ndarray shape=(S,)` |
| `pointmarkerlist` | 节点边界标记 `[N, 1]` | `mesh.node_markers`：`np.ndarray shape=(N,)` |
| `neighborlist` | 三角形邻接表 `[T, 3]` | 可选，用于拓扑查询 |

这些字段将构成 LinkMesh 内存中的核心网格数据结构，并被 `writers/hdf5_writer.py` 和 `writers/smb_writer.py` 消费。

---

## 5. Triangle 集成规范对 LinkMesh 的工程启发

根据 `TOKAMAKER/triangle-library-integration/SKILL.md`，Triangle 集成有以下关键事实：

| 项目 | 工程含义 | 对 LinkMesh 的影响 |
|---|---|---|
| `triangulate()` | Triangle C API 主入口 | LinkMesh 可通过 `triangle` Python 包调用，无需直接调用 C API。 |
| `struct triangulateio` | C 侧输入输出结构体 | `triangle` Python 包已封装，LinkMesh 直接使用 Python 接口。 |
| `TRILIBRARY` | 将 Triangle 编译为库而不是可执行程序 | `triangle` Python 包已处理，LinkMesh 无需关心编译宏。 |
| `"pqaAzQ"` | OFT 当前使用的 Triangle 控制字符串 | LinkMesh 可参考此控制字符串，根据需要调整质量参数。 |
| `pointlist` | 点坐标列表 | 对应 LinkMesh `mesh.nodes`。 |
| `segmentlist` | 边界线段列表 | 对应 LinkMesh `mesh.boundary_segments`。 |
| `regionlist` | 区域点、区域属性和最大面积约束 | 对应 LinkMesh `mesh.region_ids` 的生成输入。 |

对 LinkMesh 的工程启发是：

1. LinkMesh 应通过 `triangle` Python 包调用 Triangle，而不是直接调用 C API；
2. Triangle 的控制字符串 `"pqaAzQ"` 可作为 LinkMesh 默认质量参数的参考起点；
3. Triangle 的输入输出字段与 LinkMesh 内存网格对象的字段应保持直接对应关系；
4. LinkMesh 的 `mesher/triangle_wrapper.py` 应封装 Triangle 调用细节，对外只暴露 `generate_mesh(boundary_points, segments, regions, options)` 这样的简洁接口。

---

## 6. BFS 第二层源码侦察清单

本节清单仅基于当前 Skill 文本明确提及的组件路径。在实际源码文件被物理加入并读取之前，不对其内部实现进行任何主观推测。

### 6.1 TOKAMAKER / OFT Python 网格生成链路源码

| 优先级 | 建议拉取文件 | 来源依据 | 侦察目的 |
|---:|---|---|---|
| 1 | `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` | `oft-meshing-architecture/SKILL.md` 明确提及 | 读取 `gs_Domain`、`Mesh`、`run_triangle()` 的真实实现，确认点合并、边界段处理、区域标记点生成和 Triangle 输入构造逻辑。 |
| 2 | `src/python/OpenFUSIONToolkit/TokaMaker/_interface.py` | `oft-meshing-architecture/SKILL.md` 明确提及 | 读取 `ctypes` 动态库加载、Triangle 结构体绑定和 C 接口签名定义方式。 |

### 6.2 Triangle C 层源码

| 优先级 | 建议拉取文件 | 来源依据 | 侦察目的 |
|---:|---|---|---|
| 3 | `src/ext_libs/triangle.c` | 两份 Skill 均明确提及 | 读取 `triangulate()`、`intern_triangulate()` 等入口附近实现，确认 OFT 编译集成的 C 入口。 |
| 4 | `src/ext_libs/triangle.h` | `triangle-library-integration/SKILL.md` 明确 Triangle 标准结构 | 核对 `triangulateio` 结构体字段顺序与跨语言绑定一致性。 |

---

## 7. 对 LinkMesh 当前开发路线的建议

基于本轮宏观比对，建议 LinkMesh 继续保持当前主线：

```text
先完成 readers/gfile_reader.py（GFile/EQDSK 读取）
        ↓
再完成 mesher/triangle_wrapper.py（Triangle 封装）
        ↓
再完成 writers/hdf5_writer.py（TRIMEG HDF5 输出）
        ↓
最后完成 writers/smb_writer.py（M3DC1 PUMI .smb 输出）
```

TOKAMAKER / Triangle 的调研结果直接服务于 `mesher/triangle_wrapper.py` 的实现，是 LinkMesh P0 主线的核心技术输入。

---

## 8. 总结

本轮 TOKAMAKER 宏观哨探形成以下结论：

1. TOKAMAKER 的网格生成链路具有清晰的 Python 拓扑预处理到 C Triangle 后端的分层结构；
2. Triangle 输入中的 `vertices`、`segments`、`regions` 可被解释为二维非结构化网格生成前的通用几何拓扑事实；
3. Triangle 输出的 `pointlist`、`trianglelist`、`triangleattributelist`、`segmentlist`、`segmentmarkerlist` 等字段直接对应 LinkMesh 内存网格对象的核心字段；
4. `max_area`、Triangle switch、`triangulateio` 等内容属于生成器约束或后端实现细节，应封装在 `mesher/triangle_wrapper.py` 内部；
5. 当前不建议修改 `LinkMesh_Architecture_Plan.md` 的核心模块规划；
6. 下一步应物理拉取并只读分析 `meshing.py`、`_interface.py`、`triangle.c`、`triangle.h`。

本文件作为 TOKAMAKER 第一层宏观哨探成果归档，供后续 BFS 第二层源码逆向分析使用。
