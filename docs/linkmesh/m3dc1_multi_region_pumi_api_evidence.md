# LinkMesh 多区域 Helper 的 SCOREC/PUMI 2.2.9 API 与 Exchange 证据

## 1. 范围、事实等级与结论摘要

本文只调查 LinkMesh 向 SCOREC/PUMI 2.2.9 提交的 analytic geometric model、APF/MDS mesh topology、classification 和相关 API。本文不解析 SMB，不调查 M3D-C1 loader，也不把 `writeNative()` 成功解释为 M3D-C1 已成功消费。

事实等级：

- **目标版本头文件直接事实**：来自快照中的 SCOREC/PUMI 2.2.9 头文件。
- **当前 helper 事实**：来自 `native/linkmesh_scorec_helper/main.cc`。
- **当前 Python Writer 事实**：来自 `src/linkmesh/writers/smb_writer.py`。
- **待确认事项**：现有头文件或调用侧证据不足以证明的行为。
- **修改建议**：多区域实现的最小变更，不代表当前代码已经支持。

核心结论：

1. 当前 exchange 的二进制布局已经包含多个 geometric faces、每个 face 的多个 loop 引用，以及逐 triangle 的 `(dimension, tag)` classification；布局本身不缺少多 face 所需引用。
2. 当前 Python Writer 和 helper 的验证、模型创建及分类推导写死 single-loop/single-face。
3. 多区域无需按 Region 重建节点、mesh edges 或 triangles；每个全局 0-based node/triangle 只创建一个 APF/MDS entity。
4. `Mesh2D.region_ids` 不是 model face tags，不执行 `+1`；Python Writer 必须通过显式映射生成 face classification。
5. helper 只能验证 exchange 中已经给出的 classification，不能根据坐标、Region 或邻接关系猜测 classification。
6. PUMI 在该路径中只接收既有三角剖分并创建 APF/MDS entities，不重新剖分。

## 2. Exchange Schema v1 的准确布局

### 2.1 标量编码与字符串

**当前 Python Writer 事实：**

- 所有整数和浮点数使用显式 little-endian `struct` 编码。
- `uint32`：`<I`。
- `int32`：`<i`。
- `uint64`：`<Q`。
- `float64`：`<d`。
- magic 为固定 8 bytes：`b"LM4XCHG\x00"`。
- schema version 为 `uint32`，当前值 `1`。
- endian marker 为 `uint32`，当前值 `0x01020304`。
- 输出路径先通过 `os.fsencode()` 编码，写入 byte length 后写原始 bytes，不带 NUL 终止符。
- helper 使用 `std::filesystem::path(std::string(bytes))` 恢复路径；因此路径是操作系统文件系统字节序列，不是 schema 强制规定的 UTF-8 文本。

证据：

- `src/linkmesh/writers/smb_writer.py:27-45`
- `src/linkmesh/writers/smb_writer.py:592-603`
- `native/linkmesh_scorec_helper/main.cc:31-37`
- `native/linkmesh_scorec_helper/main.cc:226-247`

### 2.2 字段顺序

Schema v1 按以下顺序连续写入，无 padding：

| 顺序 | 字段 | 类型/数量 |
|---:|---|---|
| 1 | magic | 8 bytes |
| 2 | schema_version | `uint32` |
| 3 | endian_marker | `uint32` |
| 4 | `N, T, E, GV, GE, GL, GF` | 7 个 `uint64` |
| 5 | `separatrix_loop, inner_wall_loop, outer_wall_loop, vacuum_loop` | 4 个 `int32` |
| 6 | output path byte length | `uint64` |
| 7 | output base path | 上一步指定数量的 bytes |
| 8 | mesh nodes | `N × (R:float64, Z:float64)` |
| 9 | triangles | `T × 3 × uint64` |
| 10 | geometric vertices | `GV × (tag:int32, R:float64, Z:float64, Y:float64)` |
| 11 | geometric edges | `GE × (tag, begin_vertex_tag, end_vertex_tag, curve_type)`，均为 `int32` |
| 12 | geometric loops | `GL × (tag:int32, edge_count:uint64, edge_tags[edge_count]:int32)` |
| 13 | geometric faces | `GF × (tag:int32, loop_count:uint64, loop_tags[loop_count]:int32)` |
| 14 | vertex classifications | `N × (dimension:int32, tag:int32)` |
| 15 | mesh edges | `E × (node0:uint64, node1:uint64, dimension:int32, tag:int32)` |
| 16 | triangle classifications | `T × (dimension:int32, tag:int32)` |
| 17 | trailing data | 必须为 0 bytes |

证据：

- `src/linkmesh/writers/smb_writer.py:576-677`
- `native/linkmesh_scorec_helper/main.cc:189-361`

### 2.3 计数、索引和 tag 语义

- `N`、`T`、`E` 分别是全局 serial mesh 的 node、triangle 和唯一无向 mesh edge 数。
- mesh node index 和 triangle connectivity index 是全局 **0-based** `uint64`。
- mesh edge endpoints 同样是全局 0-based node indices，并要求 `node0 < node1`。
- geometric model tag 是 `int32` 对象标识，**不是数组下标**。
- loop 通过显式 edge tags 引用 edges；face 通过显式 loop tags 引用 loops。
- classification 是 `(model dimension, model tag)`，不是 vector position。
- exchange 不传输 `Mesh2D.region_ids`，因此 helper 不应执行 Region ID 的 `+1`、压缩或排序。

证据：

- `src/linkmesh/writers/smb_writer.py:502-535`
- `src/linkmesh/writers/smb_writer.py:624-677`
- `native/linkmesh_scorec_helper/main.cc:508-546`
- `native/linkmesh_scorec_helper/main.cc:579-615`
- `external_references/m3dc1_multi_region_input_contract_snapshot_20260812/pumi-interfaces/opt/spack/opt/spack/linux-zen4/pumi-2.2.9-xhrun74mrbmnm7losmm56msbicoh5bcb/include/apfMesh.h:257-261`

## 3. Schema 中的多 face 能力与限制

### 3.1 天然支持多个 faces 的字段

布局天然支持：

- 任意 `GF`；
- 每个 face 的独立 positive tag；
- 每个 face 引用任意数量的 loop tags；
- 多个 faces 引用同一个 loop tag；
- 每个 loop 引用一组 geometric edge tags；
- 多个 faces 因共享 loop 而共享同一组 geometric edges；
- 每个 triangle 独立携带 `(2, face_tag)`；
- mesh vertices 和 mesh edges 独立携带任意已声明 model entity classification。

因此多 face 不需要新增 Region ID、face-to-triangle 表或重复 mesh topology。

证据：

- `src/linkmesh/writers/smb_writer.py:636-677`
- `native/linkmesh_scorec_helper/main.cc:308-352`

### 3.2 写死 single-face 的语义校验

当前 helper 要求：

- `GE == GV`；
- `GL == 1`；
- `GF == 1`；
- unique loop 引用全部 geometric edges；
- unique face 只引用 unique loop；
- special loop tags 固定为 `(-1, unique_loop, -1, -1)`；
- 每个 triangle 必须分类到 unique face。

证据：

- `native/linkmesh_scorec_helper/main.cc:425-447`
- `native/linkmesh_scorec_helper/main.cc:500-526`
- `native/linkmesh_scorec_helper/main.cc:528-555`
- `native/linkmesh_scorec_helper/main.cc:636-652`

这些是当前 helper 的 P0 contract，不是 exchange 字节布局的结构性限制。

## 4. 当前 Python Classification 推导

### 4.1 Mesh vertices

`_derive_classification()` 先将全部 mesh vertices 初始化为 unique face 的 `(2, face.tag)`，随后：

1. 精确匹配 geometric corners 与拓扑外边界 mesh nodes；
2. corner node 分类为 `(0, geometric_vertex_tag)`；
3. geometric edge 对应 boundary chain 的非 corner nodes 分类为 `(1, geometric_edge_tag)`；
4. interior nodes 保持 `(2, face.tag)`。

helper 不参与这个推导。

证据：

- `src/linkmesh/writers/smb_writer.py:331-364`
- `src/linkmesh/writers/smb_writer.py:377-462`

### 4.2 Mesh edges

Python 从全部 triangles 建立唯一无向 edge table：

- 共享 1 个 triangle 的 edge 是拓扑边界；
- 共享 2 个 triangles 的 edge 是内部 edge；
- 其他计数拒绝为 non-manifold。

全部 mesh edges 起初分类到 `(2, face.tag)`；沿 geometric boundary chain 的 mesh edges 改为 `(1, geometric_edge.tag)`。最终 records 按 `(node0, node1)` 字典序输出。

证据：

- `src/linkmesh/writers/smb_writer.py:147-178`
- `src/linkmesh/writers/smb_writer.py:377-452`

### 4.3 Triangles

当前全部 triangles 无条件分类到：

```text
(2, unique_face.tag)
```

`region_ids` 只被验证为 single-region，没有参与逐 triangle face mapping。

证据：

- `src/linkmesh/writers/smb_writer.py:117-145`
- `src/linkmesh/writers/smb_writer.py:453-456`

## 5. Python Writer 的 Single-loop/Single-face 假设

当前 Python Writer 中的全部主要限制如下：

| 限制 | 位置 |
|---|---|
| `_as_single_region_ids()` 要求唯一 Region ID | `src/linkmesh/writers/smb_writer.py:117-145` |
| `_loop_entities()` 要求 1 loop、1 face | `src/linkmesh/writers/smb_writer.py:244-256` |
| 只读取 `spec.loops[0]` 和 `spec.faces[0]` | `src/linkmesh/writers/smb_writer.py:258-259` |
| 只建立一条 topology outer-boundary cycle | `src/linkmesh/writers/smb_writer.py:180-242` |
| geometric corners 只与该唯一 outer cycle 匹配 | `src/linkmesh/writers/smb_writer.py:293-374` |
| 所有默认 vertex/edge classes 使用 unique face | `src/linkmesh/writers/smb_writer.py:377-405` |
| 所有 triangles 使用 unique face | `src/linkmesh/writers/smb_writer.py:453-456` |
| `_prepare_exchange()` 调用 single-region validator | `src/linkmesh/writers/smb_writer.py:535-572` |

此外，当前 `M3DC1ModelSpec.validate()` 和 `GeometricFace.__post_init__()` 也写死 single-loop/single-face，但它们属于上游 model contract，不是 exchange 布局。

证据：

- `src/linkmesh/m3dc1_model.py:271-292`
- `src/linkmesh/m3dc1_model.py:363-383`

## 6. Helper 的 Unique-face 假设

当前 helper 中的主要 unique-face 假设：

| 限制 | 位置 |
|---|---|
| `GL == 1`、`GF == 1` | `native/linkmesh_scorec_helper/main.cc:438-447` |
| 使用 `geometric_loops.front()` | `native/linkmesh_scorec_helper/main.cc:500` |
| 使用 `geometric_faces.front()` | `native/linkmesh_scorec_helper/main.cc:517` |
| unique loop 必须包含全部 geometric edges | `native/linkmesh_scorec_helper/main.cc:500-515` |
| unique face 必须且只引用 unique loop | `native/linkmesh_scorec_helper/main.cc:517-526` |
| special loops 按 unique loop 固定 | `native/linkmesh_scorec_helper/main.cc:528-555` |
| `create_model()` 只创建 `faces.front()` | `native/linkmesh_scorec_helper/main.cc:827-854` |
| 所有 triangles 必须等于 unique face tag | `native/linkmesh_scorec_helper/main.cc:636-652` |

`create_and_write_mesh()` 本身已经逐 triangle 使用 exchange classification 调用 `findModelEntity()`；它没有硬编码 face tag 1。真正的限制来自前置验证和 `create_model()` 只创建一个 face。

证据：

- `native/linkmesh_scorec_helper/main.cc:1033-1057`

## 7. Helper 如何读取 Model Records

`read_exchange()`：

- 按 `GV` 分配并读取 geometric vertices；
- 按 `GE` 分配并读取 geometric edges；
- 按 `GL` 分配 loops，每个 loop 先读 tag 和 edge count，再读 edge tags；
- 按 `GF` 分配 faces，每个 face 先读 tag 和 loop count，再读 loop tags；
- 不假设 tag 等于 vector index；
- `validate_exchange()` 使用 tag-keyed maps 检查重复和悬空引用。

证据：

- `native/linkmesh_scorec_helper/main.cc:271-329`
- `native/linkmesh_scorec_helper/main.cc:367-389`
- `native/linkmesh_scorec_helper/main.cc:459-499`

## 8. Analytic Model Entity 与 Adjacency 创建

### 8.1 Geometric vertices

每个 exchange geometric vertex 通过：

```cpp
gmi_add_analytic(model, 0, tag, vertex_function,
                 nullptr, nullptr, callback_data)
```

创建。callback 忽略参数并返回固定 `(R,Z,Y)`。

证据：

- `native/linkmesh_scorec_helper/main.cc:659-669`
- `native/linkmesh_scorec_helper/main.cc:741-778`
- `gmi_analytic.h:40-50`

### 8.2 Geometric edges

每个 geometric edge 通过：

```cpp
gmi_add_analytic(model, 1, tag, line_function,
                 &periodic, &range, callback_data)
```

创建，当前 schema 只允许 linear curve，参数范围为 `[0,1]`。

然后：

1. `agm_add_bdry(gmi_analytic_topo(model), agm_from_gmi(edge))` 创建 edge boundary；
2. 查找 begin/end geometric vertices；
3. 各调用一次 `agm_add_use()`；
4. begin vertex reparameterization 固定到 edge parameter `0`；
5. end vertex reparameterization 固定到 edge parameter `1`。

证据：

- `native/linkmesh_scorec_helper/main.cc:671-686`
- `native/linkmesh_scorec_helper/main.cc:698-736`
- `native/linkmesh_scorec_helper/main.cc:785-817`
- `gmi_analytic.h:51-64`

### 8.3 Geometric faces

当前只创建 unique face：

```cpp
gmi_add_analytic(model, 2, face.tag, face_function,
                 face_periodic, face_ranges, nullptr)
```

face callback 将 `(u,v)` 解释为 `(R,Z)`。

`add_face_topology()` 对 face 引用 loop 中的每个 edge：

1. 为 face 创建 `agm_bdry`；
2. 查找已创建 geometric edge；
3. `agm_add_use()` 将 edge 加入 face boundary；
4. 注册 edge-to-face reparameterization，把 edge 的线性参数映射为 `(R,Z)`。

证据：

- `native/linkmesh_scorec_helper/main.cc:688-697`
- `native/linkmesh_scorec_helper/main.cc:738-770`
- `native/linkmesh_scorec_helper/main.cc:827-854`

## 9. 同一 Geometric Edge 邻接两个 Faces

**当前 helper 事实：** `add_face_topology()` 每次为一个 face 创建独立 boundary，并可对已存在的 geometric edge 调用 `agm_add_use()`。调用侧没有“edge 只能用于一个 face”的检查，也没有复制 edge entity。

因此，多 face 实现可以：

- 只创建一次 geometric edge；
- 对每个引用该 loop 的 face 分别调用 `add_face_topology()`；
- 在两个 face boundaries 中创建指向同一个 edge entity 的 uses。

**待确认事项：** 当前对话提供的目标版本 `agm.h` 内容不足以逐字核对 `agm_add_bdry()`、`agm_add_use()`、`agm_bounds()`、`agm_from_gmi()` 的正式声明及 ownership；同时尚无目标版本运行测试证明一个 analytic edge 的两个 face uses 通过 `mesh->verify()`。该能力与 AGM 拓扑模型及当前调用形态一致，但实施时必须用双 face fixture 验证。

证据：

- `native/linkmesh_scorec_helper/main.cc:698-770`
- `gmi_analytic.h:26-28`
- `gmi_analytic.h:51-64`

## 10. 多 Face 是否需要新引用字段

不需要。现有 records 已构成完整引用链：

```text
triangle -> (dimension=2, face_tag)
face -> loop_tags[]
loop -> edge_tags[]
edge -> begin/end vertex tags
```

多 face 创建只需：

1. 遍历全部 face records；
2. 按每个 face 的 loop tags 展开对应 edges；
3. 为每个 face 创建 analytic entity；
4. 为每个 face 建立 boundary uses；
5. 按 triangle record 中已有 face tag 创建 triangle。

Schema 不需要传 `region_id`，也不需要为 face 增加 triangle index list。

## 11. `findModelEntity(dim, tag)` 的多 Face 能力

目标版本声明：

```cpp
ModelEntity* Mesh::findModelEntity(int type, int tag);
```

它按 model dimension 和 tag 查找 model entity，不含 unique-face 参数，也不依赖 vector index。当前 helper 已对每个 mesh vertex、mesh edge 和 triangle 使用 classification 中的 `(dimension, tag)` 调用它。

因此，只要所有 faces 已先加入同一个 GMI model，`findModelEntity(2, face_tag)` 已具备多 face 通用调用形态。

证据：

- `apfMesh.h:257-261`
- `native/linkmesh_scorec_helper/main.cc:894-910`
- `native/linkmesh_scorec_helper/main.cc:953-978`
- `native/linkmesh_scorec_helper/main.cc:1033-1057`

## 12. Classification 验证的多 Face 升级

### 12.1 Triangles

当前 `validate_classification()` 已接受任意存在于 `face_tags` set 中的 `(2, tag)`。随后附加检查又要求 tag 等于 unique face。

最小升级是删除：

```text
classification.tag == unique_face.tag
```

但保留：

- dimension 必须为 2；
- tag 必须存在于已声明 `face_tags`；
- 每个 triangle 恰好有一条 classification；
- classification 数量等于 `T`。

证据：

- `native/linkmesh_scorec_helper/main.cc:402-423`
- `native/linkmesh_scorec_helper/main.cc:636-652`

### 12.2 Mesh edges 与 vertices

`validate_classification()` 已使用完整 sets：

- mesh vertex 可分类到已声明 geometric vertex、edge 或 face；
- mesh edge 可分类到已声明 geometric edge 或 face；
- triangle 可分类到已声明 face。

因此 set-based 验证天然接受多个 model entities。需要升级的是 Python 推导和 model topology consistency，而不是这段基本 membership 检查。

证据：

- `native/linkmesh_scorec_helper/main.cc:402-423`
- `native/linkmesh_scorec_helper/main.cc:565-585`
- `native/linkmesh_scorec_helper/main.cc:653-660`

## 13. 全局 APF/MDS Entity 的唯一性

多区域不得按 Region 重建 mesh：

- `mesh_vertices` 长度固定为 `N`，每个 global 0-based node 创建一次 vertex；
- `mesh_edge_entities` 以规范化 `(node0,node1)` 为 key，每条唯一 mesh edge 创建一次；
- triangles 按全局 triangle records 各创建一次；
- Region 界面上的 mesh vertices/edges 通过 model classification 表达共享界面，不复制 APF entities；
- 相邻 triangles 继续引用同一个 mesh edge entity。

证据：

- `native/linkmesh_scorec_helper/main.cc:919-950`
- `native/linkmesh_scorec_helper/main.cc:952-984`
- `native/linkmesh_scorec_helper/main.cc:986-1057`

这条路径调用 `createVertex()` 和 `createEntity()` 组装输入 topology；没有调用 meshing、refinement 或 adaptation API，PUMI 不重新剖分。

## 14. 当前使用的 SCOREC/PUMI 2.2.9 API

### 14.1 MPI

| 生命周期 | 调用 | 参数/返回 |
|---|---|---|
| 初始化 | `MPI_Init(int* argc, char*** argv)` | 返回 MPI error code；helper 要求 `MPI_SUCCESS` |
| rank 数 | `MPI_Comm_size(MPI_COMM_WORLD, int* size)` | 写入 communicator size |
| 结束 | `MPI_Finalize()` | 返回 MPI error code；当前 helper 未检查 finalize 返回值 |

ownership：MPI runtime 由 helper 初始化并最终 finalize；异常路径依据布尔状态清理。

证据：

- `native/linkmesh_scorec_helper/main.cc:1096-1113`
- `native/linkmesh_scorec_helper/main.cc:1131-1163`

### 14.2 PCU

目标头文件声明：

```cpp
int PCU_Comm_Init(void);
int PCU_Comm_Free(void);
int PCU_Comm_Peers(void);
```

当前 helper 在 MPI 初始化后调用 `PCU_Comm_Init()`，退出前调用 `PCU_Comm_Free()`，并要求 MPI 与 PCU peer count 都为 1。

ownership：PCU communication state 由 init/free 成对管理。当前 helper 没有检查 init/free 的整数返回值。

证据：

- `PCU.h:27-33`
- `native/linkmesh_scorec_helper/main.cc:1102-1113`
- `native/linkmesh_scorec_helper/main.cc:1131-1160`

### 14.3 GMI analytic model

```cpp
gmi_model* gmi_make_analytic(void);
gmi_ent* gmi_add_analytic(
    gmi_model* m,
    int dim,
    int tag,
    gmi_analytic_fun f,
    int* periodic,
    double (*ranges)[2],
    void* user_data);
void gmi_add_analytic_reparam(
    gmi_model* m,
    agm_use use,
    gmi_reparam_fun f,
    void* user_data);
void gmi_destroy(gmi_model* m);
```

参数：

- `dim` 是 model entity dimension；
- `tag` 是 dimension-local model tag，不是数组下标；
- `f` 是 geometry evaluation callback；
- `periodic` 和 `ranges` 描述 parametric axes；
- `user_data` 的生命周期必须覆盖所有 callback 使用；
- reparameterization callback 把 lower-dimensional use 参数映射到 owning entity 参数。

返回值：

- `gmi_make_analytic()` 返回 owned model pointer；
- `gmi_add_analytic()` 返回 model-owned entity pointer；
- reparam 注册和 destroy 返回 `void`。

ownership：

- `NativeModel` 最终调用 `gmi_destroy()`；
- `point_data`、`line_data` 由 helper 保存，地址在 model/mesh 生命周期内保持稳定；
- model entity pointers 不单独释放。

证据：

- `gmi_analytic.h:30-50`
- `gmi_analytic.h:51-64`
- `gmi.h:167-169`
- `native/linkmesh_scorec_helper/main.cc:772-854`

### 14.4 Analytic topology adjacency

当前 helper 使用：

```cpp
gmi_analytic_topo(model)
agm_from_gmi(entity)
agm_add_bdry(topology, entity)
agm_bounds(topology, boundary)
agm_dim_from_type(type)
agm_add_use(topology, boundary, adjacent)
```

用途分别是获取 analytic AGM topology、转换 entity handle、创建 boundary、查询被 boundary 限定的 entity、取得其 dimension，以及添加 lower-dimensional use。

**待确认事项：** 当前材料未包含目标版本 `agm.h` 声明正文，以上是 helper 的准确调用表达式，不将参数 ownership 或失败返回约定提升为头文件直接事实。

证据：

- `native/linkmesh_scorec_helper/main.cc:698-736`
- `gmi_analytic.h:26-28`

### 14.5 APF/MDS mesh

```cpp
Mesh2* makeEmptyMdsMesh(gmi_model* model, int dim, bool isMatched);
MeshEntity* Mesh2::createVertex(
    ModelEntity* c,
    Vector3 const& point,
    Vector3 const& param);
MeshEntity* Mesh2::createEntity(
    int type,
    ModelEntity* c,
    MeshEntity** down);
ModelEntity* Mesh::findModelEntity(int type, int tag);
void Mesh2::acceptChanges();
void Mesh::verify();
void Mesh::writeNative(const char* fileName);
void disownMdsModel(Mesh2* mesh);
void Mesh::destroyNative();
void destroyMesh(Mesh* mesh);
```

参数与返回：

- `makeEmptyMdsMesh(model, 2, false)` 创建二维、非 matched 的 empty MDS mesh，返回 `Mesh2*`；
- `createVertex()` 接收 geometric classification、spatial point 和 parametric point，返回 mesh vertex；
- `createEntity()` 接收 APF entity type、classification 和 one-level downward adjacency array；
- `findModelEntity()` 返回对应 model entity，找不到时 helper 拒绝；
- lifecycle/write/verify 方法返回 `void`；
- `writeNative()` 接收未插 rank 的 base path。

ownership：

- MDS mesh 由 `makeEmptyMdsMesh()` 创建；
- `disownMdsModel()` 解除 mesh 对 GMI model 的 ownership，防止 mesh teardown 销毁由 `NativeModel` 管理的 model；
- `destroyNative()` 销毁底层 MDS 数据；
- `destroyMesh()` 销毁 APF wrapper；
- 最后由 `NativeModel` 调用 `gmi_destroy()`；
- 当前正常和异常路径均按此顺序清理。

证据：

- `apfMDS.h:44-50`
- `apfMDS.h:198-201`
- `apfMesh2.h:73-104`
- `apfMesh2.h:119-121`
- `apfMesh.h:257-261`
- `apfMesh.h:280-286`
- `apf.h:73-80`
- `native/linkmesh_scorec_helper/main.cc:899-917`
- `native/linkmesh_scorec_helper/main.cc:1059-1090`

## 15. Schema v1 的兼容扩展与最小 v2

### 15.1 是否可以直接扩展 v1

从 wire layout 看，可以：现有 `GF`、face loop lists 和 triangle classifications 已足够。新 helper 放宽验证并遍历 faces 后，仍能读取旧 single-face v1 文件。

但当前代码和文档把 schema v1 明确描述为 single-loop/single-face，并在两端强制该语义。保持 version 1 会把“同一版本、不同接受集合”隐藏在实现中。

### 15.2 建议的最小 schema v2

建议把多区域作为 schema version 2，**不增加字段**，仅升级 invariants：

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

v2 语义变化：

- `GL >= 1`、`GF >= 1`；
- face 可引用一个或多个 loops；
- loop/edge 可被多个 faces 共享；
- triangle `(2, tag)` 可引用任意已声明 face；
- 不再要求 `GE == GV`；
- 不再要求一个 loop 覆盖全部 edges；
- 不再固定 special loop tags 为 single-region 值；
- 不增加 Region IDs，因为 helper 不应理解 OFT Region 语义。

兼容策略：helper 同时接受 v1 和 v2；v1 继续执行旧严格 invariant，v2 执行多区域 invariant。

## 16. Helper 应验证的 Multi-face Invariants

Python Writer 继续作为 classification 唯一责任层时，helper 应验证：

1. 所有 model tags 为 positive、dimension 内唯一；不得把 tag 当 vector index。
2. 每条 edge 的 endpoint vertex tags 均存在。
3. 每个 loop tag 唯一，edge tag 引用均存在，loop 内不得重复 edge。
4. 每个 face tag 唯一，loop tag 引用均存在，face 内不得重复 loop。
5. 每个 geometric edge 至少被一个 loop 引用；每个 loop 至少被一个 face 引用。
6. 一个 loop 可被一个或两个 faces 引用；超过两个应拒绝为非流形 model interface。
7. internal shared loop 应被两个不同 faces 引用；outer-domain loop 可只被一个 face 引用。
8. special loop tag 必须为 `-1` 或引用已声明 loop；不得从 tag 数值猜测其类别。
9. vertex classifications 必须为已声明 `(0, vertex)`、`(1, edge)` 或 `(2, face)`。
10. mesh edge classifications 必须为已声明 `(1, edge)` 或 `(2, face)`。
11. triangle classifications 必须为已声明 `(2, face)`。
12. counts 必须与 records 数量完全一致。
13. triangle node indices 和 mesh edge node indices 必须是全局 0-based 且范围合法。
14. mesh edge table 必须唯一、排序，并恰好覆盖 triangle topology。
15. triangle orientation/area、non-manifold mesh edge 和 trailing bytes 继续验证。
16. helper 不根据 node 坐标、边界位置或相邻 triangle 猜测 classification。
17. 可以交叉验证：分类到 geometric edge 的 mesh edge，其相邻 triangles 的 face tags 必须属于引用该 edge 所在 loop 的 faces。
18. 可以交叉验证：分类到 face 的内部 mesh edge，其两个相邻 triangles 应具有同一 face tag。
19. 不在 helper 中执行 `region_id + 1`，因为 exchange 没有 Region ID。

第 17、18 项属于验证，不是 classification 推导。

## 17. Single-region v1 兼容策略

- Python single-region 路径继续写 schema v1。
- v1 字段顺序、路径规则、success/error marker 均保持不变。
- helper 对 v1 继续执行当前 single-loop/single-face invariants。
- 多区域 Python Writer 写 schema v2。
- helper 根据 schema version 选择 validation contract，但复用同一读取布局和 APF/MDS 创建流程。
- single-region builder、现有 fixture 和预期 rank-0 `<base>0.smb` 路径不变。
- `writeNative()` 成功只证明 PUMI 写出了非空 native 文件，不证明 M3D-C1 已加载或消费。

## 18. 实施阶段的最小修改点

### 18.1 Python Writer

- 增加 schema v2 常量或按 model multiplicity 选择版本。
- 用多 Region validator 替换 multi-face 路径中的 `_as_single_region_ids()`。
- 接收显式 `region_id -> face_tag`、`curve_id -> loop_tag` 结果。
- 对每个 triangle 由原始 `region_id` 查表生成 `(2, face_tag)`，不执行 `+1`。
- 从全部 Region interfaces 推导 vertex/mesh-edge classifications。
- 保持 nodes、triangles 和 unique mesh edge table 全局唯一。
- 删除 `_loop_entities()` 的 unique loop/face 假设，仅在 v1 路径保留。

### 18.2 Helper

- reader 布局无需新增字段。
- 按 version 执行 v1 或 v2 invariants。
- `create_model()` 遍历全部 faces，并展开每个 face 引用的全部 loops。
- 删除 `front()` 和 unique face tag 检查。
- 保留 tag-keyed lookup、classification membership 和 entity uniqueness。
- APF/MDS 创建循环不按 Region 拆分。

### 18.3 CMake

当前 CMake 已链接所需组件：

- `MPI::MPI_CXX`
- `SCOREC::mds`
- `SCOREC::apf`
- `SCOREC::gmi`
- `SCOREC::pcu`

多 face 不需要新增库、pybind11、ctypes 或新的语言绑定路线。预计仅在目标库导出依赖不足时才需调整链接顺序；当前证据不要求修改。

证据：

- `native/linkmesh_scorec_helper/CMakeLists.txt:5-35`

### 18.4 测试

最小新增测试应覆盖：

1. v1 single-face exchange byte layout 完全不变。
2. v2 两 face 共享一个 loop/edge。
3. 三层嵌套三个 faces、三个 loops 和逐 triangle face classifications。
4. sibling topology：root face 引用 own loop 与多个 child loops。
5. non-contiguous Region IDs 显式映射到 contiguous face tags，确认不执行 `+1`。
6. 全局 node、edge、triangle entity counts 不因 Region 数增加。
7. helper 拒绝悬空 face/loop/edge tags。
8. helper 拒绝 triangle 分类到未声明 face。
9. helper 拒绝同一 loop 邻接超过两个 faces。
10. native smoke test执行 `acceptChanges()`、`verify()`、`writeNative()` 并检查非空输出。
11. 消费侧验收必须单列，不能用 `writeNative()` 成功代替。

## 19. 待确认事项

1. 目标版本 `agm.h` 中 topology API 的正式签名、返回失败约定和 ownership。
2. 同一 analytic edge 被两个 face boundaries 使用时，AGM 是否要求显式 use direction。
3. 多 loop face 的 outer/hole orientation 是否由 edge direction、use direction或插入顺序表达。
4. analytic face 的统一 `(R,Z)` parameterization 对含孔 face 是否满足目标版本 `verify()` 的全部要求。
5. special loop tags 在一般多区域输入中的业务来源。
6. loop 被两个 faces 共享时，是否还需额外 reparameterization record 区分两侧。
7. `writeNative()` 生成物能否被目标 M3D-C1 工作流消费必须由独立集成验收确认，不能从 PUMI 写文件成功推导。

以上待确认项不得通过解析 SMB、调查 M3D-C1 loader 或从物理标签自动映射来补足。
