# LinkMesh M4-0D1 PUMI/APF/MDS 最小内存建模与 SMB 写出 API 侦察报告

> 本轮只调查 M4 实现前的阻塞 API：从 `Mesh2D.nodes/triangles` + 目标专用 geometric model 拓扑出发，创建二维 classified APF/MDS mesh 并 `writeNative` 出 `.smb` 的最小正式调用链。不实现代码、不修改蓝图、不扩展到多物理区域或 C1 数值场。

---

## 1. 文档定位

- **性质**：M4 实现前置 API 侦察，产出候选调用链 + 证据缺口 + 最小验证办法。
- **唯一产物**：`m4_0d1_report.md`。
- **不裁定**：C1 数值场、多 face 物理分区、`.smb` 字节布局、未确认 PUMI API 签名。
- **证据来源**：`[m3dc1_scorec]` 的 `api/m3dc1_scorec.cc`、`src/m3dc1_mesh.cc`、`src/m3dc1_model.cc`、`src/m3dc1_entity.cc`、`include/*`；`[meshgen]` 的 `test/m3dc1_meshgen.cc`、`test/multi_meshgen.cc`、`test/convert_sms.cc`、`src/m3dc1_model.cc`；两套 `CMakeLists.txt`、`FindScorec.cmake`、`README`/`readme`。

---

## 2. 执行摘要

- **两条建网路径并存**：
  1. **Simmetrix 中转路径**（生成端 `m3dc1_meshgen.cc`/`multi_meshgen.cc`）：`PM_load(.sms)` → `apf::createMesh(simApfMesh)` → `apf::createMdsMesh(mdl, simApfMesh)` → `writeNative(.smb)`。**依赖 Simmetrix，不适用于 LinkMesh P0**【生成端确认 / 不适用于 LinkMesh P0】。
  2. **内存直建路径**（消费端 `m3dc1_mesh.cc::build3d` 的 `m3dc1_receiveVertices/Edges/Faces`）：`mesh->createVertex(model_ent, coord, param)` / `mesh->createEntity(EDGE/TRIANGLE, model_ent, down)` / `setResidence` / `acceptChanges`。**这是 LinkMesh P0 从内存 Mesh2D 建 MDS mesh 的最强直接调用证据**【消费端确认（调用点）/ 待明确版本源码确认（签名）】。
- **空 2D MDS mesh**：`apf::makeEmptyMdsMesh(model, 2, false)`（`m3dc1_mesh_load` non-master 分支，`m3dc1_scorec.cc`）与 `pumi_mesh_create(model, 2, false)`（master/2D 分支）——**两者均以 geometric model 为首参、dim=2、matched=false**【消费端确认（调用点）】。
- **geometric model（P0 单 face）**：走 **analytic model 文本路径**——生成端 `create_vtx/create_edge/attach_*_curve/create_loop` + `gmi_add_analytic` + `make_edge_topo` + `make_face_topo`（`m3dc1_model.cc`），消费端 `load_model` 恢复。**单闭合边界用一条 periodic edge（`attach_periodic_cubic_curve`，`vtx.first==vtx.second`）有直接生成端证据**【生成端确认】。
- **`.smb` 写出**：`mesh->writeNative(filename)`（APF/MDS），**非 Simmetrix**；生成端写出前先 `save_model(.txt)`【双向确认（写/读）/ 直接调用证据（writeNative 签名待版本确认）】。
- **classification**：mesh entity 创建时**首参即 geometric model entity**（`createVertex/createEntity` 的 `(ModelEntity*)geom_ent`）；`toModel(e)` 关系**在创建时指定**，`gmi_dim/gmi_tag` 只读【消费端确认（创建时指定）】。
- **单进程文件名**：`m3dc1_mesh_load` 拼 `base + rank + "." + ext`（`m3dc1_scorec.cc`），即 `foo.smb` 实际查找 `foo0.smb`【消费端确认（字符串处理）/ 待最小运行验证】。
- **版本**：**SCOREC/PUMI 版本未确认**；不得默认 GitHub 最新版；`writeNative/createVertex/createEntity/setResidence/acceptChanges/makeEmptyMdsMesh` 的**准确签名与调用顺序必需性**为**阻塞 M4 实现**的核心缺口。
- **裁决**：D1 **可进入 M4-0E**（蓝图可固化 A 组事实 + 保留 B 组停止条件）；建议**不额外读 core**，改为**先取版本证据 + 用 M4-0D2 单进程最小程序运行验证**。

---

## 3. 已读与跳过文件

### 已读（授权，纯文本源码）

| 文件 | 归属 | 用途 |
|---|---|---|
| `api/m3dc1_scorec.cc` | [m3dc1_scorec] | `m3dc1_mesh_load`、`makeEmptyMdsMesh`/`pumi_mesh_load`/`pumi_mesh_create` 调用点、finalize |
| `src/m3dc1_mesh.cc` | [m3dc1_scorec] | `m3dc1_receiveVertices/Edges/Faces`、`build3d`、`createVertex/createEntity/setResidence/acceptChanges` |
| `src/m3dc1_model.cc` | [m3dc1_scorec] | `load_model`、`gmi_add_analytic`、`make_edge_topo/make_face_topo` |
| `src/m3dc1_entity.cc` | [m3dc1_scorec] | `toModel`/`gmi_dim`、classification 读取、`getMdsIndex` |
| `include/m3dc1_mesh.h`/`m3dc1_model.h`/`m3dc1_field.h` | [m3dc1_scorec] | 类型声明 |
| `api/m3dc1_scorec.h` | [m3dc1_scorec] | 对外 API 声明 |
| `test/m3dc1_meshgen.cc` | [meshgen] | Simmetrix→PUMI 转换、`createMdsMesh`、`writeNative` |
| `test/multi_meshgen.cc` | [meshgen] | 多区 model、`createMdsMesh`、`writeNative` |
| `test/convert_sms.cc` | [meshgen] | `PM_load`/`createMesh`/`createMdsMesh`/`writeNative` 精简范式 |
| `src/m3dc1_model.cc` | [meshgen] | `create_vtx/create_edge/attach_*_curve`、`save_model`/`save_multi_rgn_model` |
| `CMakeLists.txt`×2、`FindScorec.cmake`×2、`README`/`readme`×2 | 两端 | 依赖库名、头名、版本证据 |

### 跳过（未授权 / 二进制 / 需运行）

- SCOREC/core 的 `apfMDS.h`/`apfMesh2.h`/`apf.h`/`gmi*.h`/`pumi.h` **实现与声明**（未授权）。
- `.smb`/`.sms`/`.dmg`/`.smd`/VTK/对象/库/可执行/`build/`。
- Simmetrix 私有头实现。

---

## 4. 当前版本证据

来源：两套 `FindScorec.cmake`、`CMakeLists.txt`、`README`/`readme`。

- **SCOREC 库名**（`FindScorec.cmake` `SCOREC_LIB_NAMES`）：非 Simmetrix 分支 `crv (dsp) ph sam spr ma apf_zoltan parma mds apf lion mth gmi pcu`；Simmetrix 分支加 `apf_sim gmi_sim`。
- **头探测**：`find_path(SCOREC_INCLUDE_DIR NAMES apf.h PCU.h ma.h ...)`。
- **源码 include**：消费端 `m3dc1_scorec.cc` 直接 `#include "apfMDS.h" "apfMesh2.h" "pumi.h" "apfShape.h" <gmi_analytic.h> "gmi_null.h"`；生成端 `m3dc1_meshgen.cc` `#include <apfMDS.h> <apfMesh2.h> <apfConvert.h> <gmi_sim.h> "gmi_mesh.h" <ma.h>`。
- **版本/提交/tag/branch**：README 出现安装路径样例（`simmetrix/simModSuite/11.0-170826`、`SimModSuite18.0-230521`、`PETSC 3.5.1`、`openmpi/latest` 等），但 **未固定 SCOREC/core 版本或提交号**。
- **生成端与消费端是否同版本**：两端均用同名 `apf/mds/gmi/pcu` 与 `writeNative`/`loadMdsMesh`，接口族一致，但 **无证据证明使用同一 SCOREC/core 版本**。

**结论**：**SCOREC/PUMI 版本未确认**。不得默认 GitHub 最新版。下一步应先从老师编译环境/模块文件/依赖清单/导师取得版本证据，再按需申请具体 core 文件（见 §18）。

---

## 5. API 调用点总表

| 符号 | 文件 | 调用者/函数 | 观察到的参数 | 返回值用法 | 端 | 是否见定义 | 与 P0 关系 | 证据等级 |
|---|---|---|---|---|---|---|---|---|
| `apf::makeEmptyMdsMesh` | api/m3dc1_scorec.cc | `m3dc1_mesh_load`(non-master) | `(model, 2, false)` | 赋 `m3dc1_mesh::instance()->mesh` | 消费端 | 否 | **核心**（空 2D mesh）| 直接调用证据 |
| `pumi_mesh_create` | api/m3dc1_scorec.cc | `m3dc1_mesh_load`(2D 分支) | `(pumi::instance()->model, 2, false)` | 赋 mesh | 消费端 | 否 | 核心（PUMI 封装等价）| 直接调用证据 |
| `pumi_mesh_load` | api/m3dc1_scorec.cc | `m3dc1_mesh_load`(master) | `(model, mesh_file, group_size)` | 赋 mesh | 消费端 | 否 | 加载（对称）| 直接调用证据 |
| `apf::loadMdsMesh` | api/m3dc1_scorec.cc | `m3dc1_mesh_load_3d` | `(model, mesh_file)` | 赋 mesh | 消费端 | 否 | 加载（对称）| 直接调用证据 |
| `apf::createMdsMesh` | test/m3dc1_meshgen.cc / multi_meshgen.cc / convert_sms.cc | main | `(mdl, simApfMesh)` | 赋 `apf::Mesh2*` | 生成端 | 否 | **不适用**（Simmetrix 中转）| 生成端确认 |
| `apf::createMesh` | test/convert_sms.cc 等 | main | `(sim_pmesh)` | Simmetrix→APF | 生成端 | 否 | 不适用 | 生成端确认 |
| `mesh->createVertex` | src/m3dc1_mesh.cc | `m3dc1_receiveVertices` | `((ModelEntity*)geom_ent, coord, param)` | `MeshEntity*` 存映射/设 tag | 消费端 | 否 | **核心**（建 vertex）| 消费端确认（调用点）|
| `mesh->createEntity` | src/m3dc1_mesh.cc | `m3dc1_receiveEdges/Faces` | `(apf::Mesh::EDGE/TRIANGLE, (ModelEntity*)geom_ent, down_ent)` | `MeshEntity*` | 消费端 | 否 | **核心**（建 edge/tri）| 消费端确认（调用点）|
| `mesh->setPoint` | src/m3dc1_mesh.cc | `build3d`（3D 坐标更新）| `(e, 0, coord)` | — | 消费端 | 否 | 相关（设坐标）| 消费端确认（调用点）|
| `mesh->getPoint` | 多处 | 遍历 | `(e, 0, xyz)` | 读坐标 | 双端 | 否 | 相关 | 直接调用证据 |
| `mesh->setResidence` | src/m3dc1_mesh.cc | `build3d` | `(e, parts)` | — | 消费端 | 否 | 单进程可能可省 | 消费端确认 / 待运行验证 |
| `mesh->addRemote` | src/m3dc1_mesh.cc | `m3dc1_receiveVertices`/`build3d` | `(e, pid, NULL/r)` | — | 消费端 | 否 | **多分区**（P0 不需）| 不适用于 P0（单进程）|
| `mesh->acceptChanges` | src/m3dc1_mesh.cc | `build3d` | `()` | — | 消费端 | 否 | 核心（拓扑提交）| 消费端确认（调用点）|
| `mesh->writeNative` | test/m3dc1_meshgen.cc / multi_meshgen.cc；api/m3dc1_scorec.cc | main / `m3dc1_mesh_write` | `(filename)` / `(filename_buff)` | 写 `.smb` | 双端 | 否 | **核心**（写出）| 双向确认（调用点）|
| `mesh->destroyNative` | test/*.cc；m3dc1_scorec_finalize | 清理 | `()` | — | 双端 | 否 | 释放 | 直接调用证据 |
| `apf::verify` / `mesh->verify` | api/m3dc1_scorec.cc `m3dc1_mesh_verify` | 调试 | `(mesh, false)` | — | 消费端 | 否 | 校验（可选）| 直接调用证据 |
| `apf::destroyMesh` | test/*.cc | 清理 | `(simApfMesh)` | — | 生成端 | 否 | 释放 | 生成端确认 |
| `gmi_add_analytic` | src/m3dc1_model.cc（两端）| `create_vtx/attach_*` | `(model, dim, tag, func, periodic, range, data)` | `gmi_ent*` | 双端 | 否 | **核心**（建 model）| 双向确认（调用点）|
| `make_edge_topo` | src/m3dc1_model.cc | `attach_*_curve` | `(model, gedge, v0tag, v1tag)` | — | 双端 | 是（本文件定义）| 核心（edge 拓扑）| 直接定义证据 |
| `make_face_topo` | src/m3dc1_model.cc | `load_model` | `(gf, tagsOfEdgesOnFace)` | — | 消费端 | 是（本文件定义）| 核心（face 拓扑）| 直接定义证据 |
| `gmi_find` | src/m3dc1_mesh.cc | receive* | `(model, dim, tag)` | `gmi_ent*` | 消费端 | 否 | 核心（按 tag 取 model ent）| 直接调用证据 |
| `getMdsEntity` / `getMdsIndex` | src/m3dc1_mesh.cc / entity.cc | 多处 | `(mesh, dim, id)` / `(mesh, e)` | local id↔entity | 消费端 | 否 | 核心（本地索引映射）| 直接调用证据 |
| `changeMdsDimension` | src/m3dc1_mesh.cc | `build3d` | `(mesh, 3)` | 2↔3 | 消费端 | 否 | **不适用**（3D）| 不适用于 P0 |
| `m3dc1_receiveVertices/Edges/Faces` | src/m3dc1_mesh.cc | `build3d` | 见 §8–9 | 建实体 | 消费端 | 是（本文件定义）| **核心模板** | 消费端确认 |
| `m3dc1_receiveMesh` | — | — | — | — | — | **授权文件未发现** | — | 授权文件未发现 |

> 所有 `mesh->*`/`apf::*` 的**定义位于未授权 SCOREC/core**；本表"是否见定义"为否者，均**只确认调用点，签名/所有权/返回值待明确版本源码确认**。

---

## 6. geometric model 最小创建链（P0 单 face）

P0 `single_region` 单 face 的 analytic model 最小实体（生成端 `m3dc1_model.cc` 直接证据）：

- **geometric vertex 数**：单条 periodic 闭合边界 → **1 个 geometric vertex**（`attach_periodic_cubic_curve` 要求 `vtx.first==vtx.second`，`assert(vtx.first==vtx.second)`）【生成端确认】。
- **geometric edge 数**：**1 条 periodic edge**（`edgePeriodic=1`）【生成端确认】。
- **loop 组织**：`create_loop(&loopId, &numEdges=1, edgeList={edge})` → `loopContainer[loopId]={edge}`【生成端确认】。
- **face 创建**：消费端 `load_model` 读 `numFaces` 段后 `gmi_add_analytic(model, 2, faceNumber, faceFunction, ...)` + `make_face_topo(gf, edgeIdsOnFace)`【消费端确认】。
- **tag 分配**：`gmi_add_analytic(model, dim, *id, ...)`——**tag = 文本 ID**，2D 不重编号【双向确认】。
- **model 文本保存**：`save_model` 写头行 `numL sep inner outer vacuum` + 每 loop 的 vtx/edge/curve + `numFaces` + face↔loop【生成端确认】。
- **消费端恢复**：`load_model` 逐字段读回并 `create_vtx/create_edge/attach_*` + `make_face_topo`【消费端确认】。
- **关键调用实参**：
  - `gmi_add_analytic(model, 1, *edge, edgeFunction, &edgePeriodic, &edgeRange, data)`（edge）；
  - `make_edge_topo(model, gedge, vtx.first, vtx.second)`；
  - `make_face_topo(gf, edgeIdsOnFace)`（`add_bdry`/`add_adj`/`gmi_add_analytic_reparam(faceFunction)`）【直接定义证据（topo 函数在 model.cc 内定义）/ 直接调用证据（gmi_add_analytic 定义在 core）】。
- **单闭合边界方案**：**一条 periodic edge**（有生成端直接证据）；多分段 edge 亦可（`attach_piecewise_linear_curve` 用于多区），但 P0 单 face 首选 periodic 单 edge【生成端确认】。
- **curve 最低表示**：periodic cubic BSpline（`attach_periodic_cubic_curve` → `interpolateCubicBSpline` → `BSpline`）；或分段线性（`attach_piecewise_linear_curve`）。**由 `M3DC1ModelSpec` 提供 curve 表示决策，Adapter 从有序边界点列拟合控制点**【生成端确认 / 架构裁决建议】。

### 三路径分开报告

| 路径 | 证据 | 是否 P0 采用 |
|---|---|---|
| M3D-C1 analytic model（`gmi_add_analytic` + `.txt`）| 双向确认 | **是（P0 候选）** |
| Simmetrix 中转（`GR_createVertex/Edge/Face` + `GM_write` + `gmi_load(.smd)`）| 生成端确认 | **否（依赖 Simmetrix）** |
| LinkMesh P0 候选 | 架构裁决建议 | Adapter 用 analytic model 路径 |

---

## 7. empty 2D MDS mesh 创建

- **创建函数**：`apf::makeEmptyMdsMesh(model, 2, false)`（`m3dc1_scorec.cc` `m3dc1_mesh_load` non-master 分支）；等价封装 `pumi_mesh_create(model, 2, false)`（2D 分支）【直接调用证据】。
- **是否含 geometric model**：**是**，首参 `model`（`m3dc1_model::instance()->model` / `pumi::instance()->model`）【消费端确认】。
- **dimension=2**：第二参 `2`【消费端确认】。
- **matched/partitioned 布尔**：第三参 `false`（观察到）——**语义（matched? / 是否分区）待明确版本源码确认**【待版本确认】。
- **返回类型**：赋给 `apf::Mesh2*`（`m3dc1_mesh::instance()->mesh`）【直接调用证据】。
- **所有权**：mesh 由 `m3dc1_mesh` 单例持有，finalize 时 `destroyNative`/`pumi_mesh_delete`【消费端确认】。
- **创建前初始化**：老师源码出现 `m3dc1_scorec_init`→`pumi_start()`（消费端）/ `MPI_Init`+`m3dc1_scorec_init`（生成端）；`gmi_register_*`（生成端 Simmetrix 路径）。**PCU/PUMI 起始为必需**【消费端确认（调用点）】。
- **仅多进程/Simmetrix 的初始化**：`gmi_register_sim`/`gmi_sim_start`（Simmetrix）、plane/group split（多分区）【不适用于 P0】。
- **对称释放/finalize**：`destroyNative`/`apf::destroyMesh`/`pumi_finalize`/`PCU_Comm_Free`/`MPI_Finalize`【直接调用证据】。

**候选调用链（每步标注）**：
1. PCU/PUMI 起始（`pumi_start`/`PCU_Comm_Init`）— 仅调用点 / 待版本确认必需性。
2. 构造 analytic geometric model（§6）— 双向确认（调用点）。
3. `makeEmptyMdsMesh(model, 2, false)` — 直接调用证据 / 第三参语义待版本确认。

---

## 8. mesh vertex 创建与坐标

来源：`m3dc1_mesh.cc::m3dc1_receiveVertices`（**从内存数据建 vertex 的最强模板**）。

1. **创建函数**：`new_ent = mesh->createVertex((ModelEntity*)geom_ent, coord, param)`【消费端确认（调用点）】。
2. **是否必须传 geometric model entity**：**是**，首参 `(ModelEntity*)geom_ent`（由 `gmi_find(model, e_geom_type[index], e_geom_tag[index])` 取得）【消费端确认】。
3. **vertex 分类目标**：由 `geom_ent` 决定——`geom_type`（0/1/2）+ `geom_tag`。receive 路径下每个 vertex 携带其 `e_geom_type/e_geom_tag`【消费端确认】。
4. **内部 vertex classification**：`geom_type=2`（face）——**在 receive 分区网格场景下由发送端携带**，非本地重算【消费端确认（限 receive 场景）】。
5. **边界曲线内部 vertex**：`geom_type=1`（edge）——同上，场景限定【消费端确认（限 receive 场景）】。
6. **corner vertex**：`geom_type=0`（geometric vertex）——同上【消费端确认（限 receive 场景）】。
7. **坐标设置**：`createVertex` 直接接收 `coord`（`Vector3`），无需单独 `setPoint`（3D `build3d` 才用 `setPoint` 改 z）【消费端确认】。
8. **2D R/Z→3D 坐标**：`coord[0]=R, coord[1]=Z, coord[2]=?`——receive 路径逐分量拷贝；生成端 model 中 `xyz[2]=0.`（`create_vtx`/`edgeFunction`）→ **第三坐标置 0**【生成端确认（model 侧 z=0）/ mesh 侧待运行验证】。
9. **第三坐标=0**：model 侧确认；mesh vertex 侧在 2D 初始网格应为 0，**待运行验证**。
10. **是否必须设 residence**：`build3d` 对 shared/多分区实体设 `setResidence(e, parts)`；**单进程无 remote 时是否必需 → 待最小运行验证**【待运行验证】。
11. **单进程 residence**：receive/build3d 属多分区；**P0 单进程可能可省 residence/addRemote**，需运行确认【待运行验证 / 不适用于 P0（多分区部分）】。
12. **`acceptChanges` 时机**：`build3d` 在**所有实体创建 + residence 后**统一 `mesh->acceptChanges()`——**未见按 vertex 分阶段调用**【消费端确认】。
13. **local index→entity 指针**：`getMdsEntity(mesh, 0, index)` 取指针，`getMdsIndex(mesh, e)` 反查；receive 时设 `local_entid_tag=index`【消费端确认】。
14. **临时 `MeshEntity*` 映射表**：`m3dc1_receiveVertices` 未显式建数组，但 `build3d` 显式用 `remote_vertices=new MeshEntity*[num_local_vtx]` 保存 index→entity。**LinkMesh P0 建 edge/triangle 时需保存 vertex index→`MeshEntity*` 映射**【消费端确认】。

> 第 3–6 项的 classification **来源于 receive（分区网格）场景发送端携带的 geom_type/tag**；LinkMesh P0 需由 **Adapter 主动为每个 mesh vertex 分配 geom 分类**（哪些在边界 edge、哪些在 corner vertex、哪些在 interior face），此规则**当前无本地重算证据，待 core 或运行验证**。

---

## 9. mesh edge/triangle 创建

来源：`m3dc1_receiveEdges` / `m3dc1_receiveFaces` / `build3d`。

1. **edge 是否必须显式创建**：receive 路径**显式创建 edge**（`m3dc1_receiveEdges` 先建 edge，`m3dc1_receiveFaces` 再用 edge 建 triangle）【消费端确认】。
2. **triangle 能否无显式 edge 创建**：`m3dc1_receiveFaces` 的 triangle **downward 用 edge**（`getMdsEntity(mesh, 1, e_down_lid[...])`）→ **该路径需要先有 edge**；APF 是否支持"仅 vertex 建 triangle 自动补 edge" → **待明确版本源码确认**【待版本确认】。
3. **entity type 常量**：`apf::Mesh::EDGE`、`apf::Mesh::TRIANGLE`（`m3dc1_mesh.cc`）【消费端确认】。
4. **edge downward**：`down_ent[0/1] = getMdsEntity(mesh, 0, e_down_lid[...])`（两个 vertex）【消费端确认】。
5. **triangle downward**：`m3dc1_receiveFaces` 用 **edge**（dim 1）作 downward（`num_down=f_down_num[index]`，`down_ent[i]=getMdsEntity(mesh,1,...)`）【消费端确认】。
6. **entity 创建时传 model entity**：`mesh->createEntity(TYPE, (ModelEntity*)geom_ent, down_ent)`——**首参后即 geom 分类**【消费端确认】。
7. **triangle 分类到 single face**：receive 时 triangle 的 `geom_ent=gmi_find(model, e_geom_type, e_geom_tag)`；P0 单 face 时所有 triangle → 该 face tag【消费端确认（机制）/ 架构裁决建议（P0 Adapter 分配）】。
8. **interior edge 分类**：应到 2 维 face（`geom_type=2`）——**receive 携带，非本地算**；LinkMesh 需 Adapter 判定【待 core/运行验证】。
9. **boundary edge 分类**：应到 1 维 model edge（`geom_type=1`）——同上【待 core/运行验证】。
10. **corner/boundary-curve/interior vertex 分类**：见 §8 第 3–6【待 core/运行验证】。
11. **是否需统一三角形方向**：**授权文件未见对 receive triangle 做方向翻转**（3D `build3d` 有 `flip_wedge` 但属 3D wedge，不适用 2D）；2D triangle 方向要求 → **待最小运行验证**【待运行验证】。
12. **APF/MDS 是否接受 CW/CCW**：**当前源码无 2D triangle 顺逆强制证据** → **待运行验证**【待运行验证】。
13. **错误方向在哪检测**：可能在 `verify()` 或求解期；**无静态证据** → 待运行验证【待运行验证】。
14. **创建后拓扑提交**：`mesh->acceptChanges()`（统一）；调试期 `apf::verify`【消费端确认】。

---

## 10. classification 矩阵（2D single-face P0）

| entity | mesh dim | geom dim | geom tag 来源 | 创建 API | 是否写入 `.smb` | 消费端读取 | 证据等级 | 阻塞 M4 |
|---|---|---|---|---|---|---|---|---|
| geometric vertex | — | 0 | model 文本 ID | `gmi_add_analytic(model,0,tag,...)` | 否（在 model）| `gmi_find`/`load_model` | 双向确认 | 否 |
| geometric edge | — | 1 | model 文本 ID | `gmi_add_analytic(model,1,tag,...)` | 否（在 model）| `load_model` | 双向确认 | 否 |
| geometric face | — | 2 | model 文本 ID | `gmi_add_analytic(model,2,tag,...)`+`make_face_topo` | 否（在 model）| `load_model` | 消费端确认 | 否 |
| mesh vertex @corner | 0 | 0 | corner geom vtx tag | `createVertex((ModelEntity*)gv,coord,param)` | 是 | `toModel`+`gmi_dim=0` | 待 core/运行验证 | **是** |
| mesh vertex on boundary curve | 0 | 1 | boundary geom edge tag | `createVertex((ModelEntity*)ge,...)` | 是 | `gmi_dim=1` | 待 core/运行验证 | **是** |
| interior mesh vertex | 0 | 2 | face tag | `createVertex((ModelEntity*)gf,...)` | 是 | `gmi_dim=2` | 待 core/运行验证 | **是** |
| boundary mesh edge | 1 | 1 | boundary geom edge tag | `createEntity(EDGE,(ModelEntity*)ge,down)` | 是 | `gmi_dim=1` | 待 core/运行验证 | **是** |
| interior mesh edge | 1 | 2 | face tag | `createEntity(EDGE,(ModelEntity*)gf,down)` | 是 | `gmi_dim=2` | 待 core/运行验证 | **是** |
| mesh triangle | 2 | 2 | face tag | `createEntity(TRIANGLE,(ModelEntity*)gf,down)` | 是 | `gmi_dim=2` | 消费端确认（机制）| 部分 |

- **`toModel` 关系何时指定**：**创建时**（`createVertex/createEntity` 首个 model 参数）——非后续附加【消费端确认】。
- **`gmi_dim/gmi_tag`**：**只读**（`m3dc1_ent_getgeomclass`/`get_ent_gclasdim`）【消费端确认】。
- **classification 错误检测**：`verify()`/加载端/求解期——**无静态确证** → 待运行验证【待运行验证】。
- **tag 一致性**：model `.txt` 与 `.smb` 的 geom tag **必须一致**（`.smb` 存 mesh entity 的 model 分类，加载时 `gmi_find(model, dim, tag)` 对应）【消费端确认】。
- **`region_ids` ≠ geometric face tag**：P0 single-face 由 **Adapter 明确分配 face tag**，标为**目标专用映射**，不得直接用 `region_ids`【架构裁决建议】。

**关键阻塞**：LinkMesh P0 必须为每个 mesh vertex/edge **本地判定并分配** geom 分类（corner→gvtx、boundary→gedge、interior→gface）。当前 receive 路径的分类**来自发送端携带**，非本地重算 → **该本地判定规则待 core 或最小运行验证**。

---

## 11. acceptChanges/verify/writeNative 顺序

### 参考源码实际顺序

**（A）Simmetrix 中转（生成端 `m3dc1_meshgen.cc`，不适用 P0）**：
1. `save_model(.txt)`；2. `make_sim_model` + `GM_write(.smd)`；3. `SurfaceMesher` + `M_write(.sms)`；4. `gmi_load(.smd)` + `gmi_write_dmg(.dmg)`；5. `PM_load(.sms)` → `createMesh` → `createMdsMesh(mdl, simApfMesh)`；6. `mesh->writeNative(.smb)`；7. `destroyNative`/`destroyMesh`。**未见 `writeNative` 前显式 `verify`**【生成端确认】。

**（B）内存直建（消费端 `build3d`，最接近 P0）**：
1. `changeMdsDimension`（3D，P0 跳过）；2. `m3dc1_receiveVertices`（createVertex）；3. `m3dc1_receiveEdges`（createEntity EDGE）；4. `m3dc1_receiveFaces`（createEntity TRIANGLE）；5. `setResidence`/`addRemote`（多分区）；6. **统一 `mesh->acceptChanges()`**；7. 后续 field/numbering；（DEBUG）`printStats`/`pumi_mesh_verify`。**`acceptChanges` 在全部实体后统一调用，未见分阶段**【消费端确认】。

### LinkMesh P0 候选最小顺序

1. PCU/PUMI 起始；
2. 构造 analytic geometric model（vtx/edge/loop/face）；
3. `makeEmptyMdsMesh(model, 2, false)`；
4. 建全部 mesh vertex（`createVertex`，保存 index→`MeshEntity*`）；
5. 建 mesh edge（去重后，`createEntity(EDGE,...)`）；
6. 建 mesh triangle（`createEntity(TRIANGLE,...)`）；
7. （单进程）**可能可省** residence/remotes — 待运行验证；
8. `mesh->acceptChanges()`（统一）；
9. `apf::verify(mesh)` — 可选，`writeNative` 前是否必需**待运行验证**；
10. `mesh->writeNative(filename)`；
11. `save_model(.txt)`（model 文本，可在 mesh 前后，生成端在 mesh 前）；
12. 释放 + finalize。

**回答**：
- `acceptChanges` **参考源码统一调用**；分阶段是否可行**待版本确认**。
- `verify` 仅在 `m3dc1_mesh_verify`（调试）出现；`writeNative` 前是否必需**待运行验证**。
- `writeNative` 输入**观察为文件名字符串**（`filename_buff` 形如 `"%s-%dK.smb"`）；是裸名/路径/base **待运行验证**（生成端传含扩展名的完整名）。
- 写后 barrier：多分区 receive 有 `MPI_Barrier`，**单进程 P0 是否需要 → 待运行验证**。
- **仅多 rank**：residence/addRemote/`m3dc1_stitchLink`/plane split。
- **P0 可省（候选）**：residence/remotes/barrier — **待运行验证**。

---

## 12. 单进程文件名与加载路径

来源：`m3dc1_scorec.cc::m3dc1_mesh_load`。

1. **mesh 文件参数形式**：`char* mesh_file`。
2. **是否自动插 rank**：**是**。源码：`std::string in(mesh_file); p=in.rfind('.'); base=in.substr(0,p); ext=in.substr(p+1); s<<base<<pumi_rank()<<"."<<ext; partFile=s.str();`【消费端确认（字符串处理）】。
3. **`foo.smb` 实际查找**：`foo<rank>.smb`，单进程 rank=0 → **`foo0.smb`**【消费端确认 / 待运行验证】。
4. **已带 rank 文件名处理**：源码对 `mesh_file` 一律拆最后一个 `.` 再插 rank → 传入 `foo0.smb` 会变 `foo00.smb`（推断）**待运行验证**【待运行验证】。
5. **`group_size=1`**：`m3dc1_model::set_num_plane(1)` → `group_size=PCU_Comm_Peers()`；master plane 分支走 `pumi_mesh_load(model, mesh_file, group_size)`【消费端确认】。
6. **master/non-master 差异**：master `pumi_mesh_load(...)`；non-master `pumi_mesh_create(model,2,false)`（空 mesh）【消费端确认】。
7. **单进程是否需 rank 后缀**：字符串逻辑**强制插 rank** → 单进程仍查 `<base>0.<ext>`【消费端确认（字符串）/ 待运行验证（实际行为）】。
8. **生成端单进程写出名**：生成端 `writeNative` 传 `"%s-%dK.smb"`/`"%s-%d.smb"`（不含 rank 插入，因生成端不经 `m3dc1_mesh_load` 的拆分逻辑）→ **生成端写出名与消费端加载名的 rank 约定需对齐**【待运行验证】。
9. **model 与 mesh 是否共享 base**：生成端 `sprintf` 用同一 `filename` 基名生成 `.txt/.smd/.dmg/.smb`；消费端 `m3dc1_model_load(model_file)` 与 `m3dc1_mesh_load(mesh_file)` **分别传参**，不强制同名，但实践共享 base【生成端确认（同基名）/ 消费端（分别传参）】。
10. **必须运行验证项**：rank 后缀实际展开、单进程是否生成 `foo0.smb`、生成端写出名与加载名对齐。

---

## 13. 生成端与消费端对照

| 环节 | 生成端 | 消费端 | 判定 |
|---|---|---|---|
| geometric model 建 | `gmi_add_analytic`+`make_edge_topo`+`save_model` | `load_model`+`gmi_add_analytic`+`make_face_topo` | 双向确认 |
| 空 mesh / mesh 来源 | Simmetrix→`createMdsMesh(mdl,simApfMesh)` | `makeEmptyMdsMesh(model,2,false)` / `pumi_mesh_load` | 生成端（Simmetrix）/ 消费端（内存/加载）|
| vertex 建 | （Simmetrix 内部）| `createVertex((ModelEntity*)gv,coord,param)` | 消费端确认 |
| edge/tri 建 | （Simmetrix 内部）| `createEntity(EDGE/TRIANGLE,(ModelEntity*)ge,down)` | 消费端确认 |
| 拓扑提交 | （Simmetrix + createMdsMesh）| `acceptChanges` | 消费端确认 |
| `.smb` 写 | `mesh->writeNative(.smb)` | `m3dc1_mesh_write`(option=1) `writeNative` | 双向确认 |
| `.smb` 读 | — | `pumi_mesh_load`/`loadMdsMesh` | 消费端确认 |
| model 文件 | `.txt`(save_model)/`.smd`(GM_write)/`.dmg`(gmi_write_dmg) | `m3dc1_model_load`→`load_analytic_model`→`load_model`(`.txt`) | 双向确认（`.txt`）/ 待确认（`.dmg` 是否运行必需）|

**结论**：**LinkMesh P0 采用消费端"内存直建 + analytic `.txt` model"路径**，绕开生成端 Simmetrix 中转。

---

## 14. LinkMesh P0 候选调用链（≤25 步）

| # | 步骤 | 状态 |
|---|---|---|
| 1 | 读 `Mesh2D.nodes/triangles`（+ `M3DC1ModelSpec` 边界拓扑）| 已由 LinkMesh 侧确认 |
| 2 | PCU/PUMI 起始（`pumi_start`/`PCU_Comm_Init`）| 只确认调用点 |
| 3 | 由 `M3DC1ModelSpec` 建 geometric vertex（`gmi_add_analytic dim0`）| 双向确认（调用点）|
| 4 | 建 geometric edge + curve（`attach_*_curve`+`gmi_add_analytic dim1`）| 生成端确认 |
| 5 | `make_edge_topo(model,gedge,v0,v1)` | 直接定义证据 |
| 6 | 建 loop（`create_loop`）| 生成端确认 |
| 7 | 建 geometric face（`gmi_add_analytic dim2`+`make_face_topo`）| 消费端确认 |
| 8 | `makeEmptyMdsMesh(model,2,false)` | 直接调用证据 / 第三参语义待版本确认 |
| 9 | 遍历 `nodes` → `createVertex((ModelEntity*)geom,coord{R,Z,0})` | 消费端确认（调用点）|
| 10 | 保存 node index → `MeshEntity*` 映射 | 消费端确认 |
| 11 | 为每 vertex 判定并分配 geom 分类（corner/boundary/interior）| 待 core/运行验证 |
| 12 | 从 triangles 去重 edge（Adapter 侧）| 已由决策（adjacency 派生）|
| 13 | 建 mesh edge（`createEntity(EDGE,(ModelEntity*)geom,down_vtx)`）| 消费端确认（调用点）|
| 14 | 为每 edge 分配 geom 分类（boundary→gedge / interior→gface）| 待 core/运行验证 |
| 15 | 建 mesh triangle（`createEntity(TRIANGLE,(ModelEntity*)gface,down_edge)`）| 消费端确认（调用点）|
| 16 | triangle → face tag（Adapter 分配）| 架构裁决建议 |
| 17 | 三角形方向是否需统一 | 待最小运行验证 |
| 18 | （单进程）跳过 residence/remotes | 待运行验证（可省性）|
| 19 | `mesh->acceptChanges()` | 消费端确认（调用点）|
| 20 | `apf::verify(mesh)`（可选）| 待运行验证（是否必需）|
| 21 | `mesh->writeNative("<base>0.smb")` | 直接调用证据 / 名称约定待运行验证 |
| 22 | `save_model("<base>.txt")` | 生成端确认 |
| 23 | 释放 `destroyNative`/`destroyMesh` | 直接调用证据 |
| 24 | PUMI/PCU finalize | 直接调用证据 |
| 25 | 消费端 `m3dc1_model_load(.txt)`+`m3dc1_mesh_load(base.smb→base0.smb)` 验收 | 消费端确认 / 待运行验证 |

> 仅架构与 API 草案，不含 LinkMesh 业务代码补丁。

---

## 15. 已确认事实

- 【双向确认】geometric model 由 `gmi_add_analytic`+`make_edge_topo`/`make_face_topo` 构造，`save_model`↔`load_model` 恢复；`.smb` 由 `writeNative` 写、`pumi_mesh_load`/`loadMdsMesh` 读。
- 【消费端确认】内存建网模板：`createVertex((ModelEntity*)geom,coord,param)`、`createEntity(EDGE/TRIANGLE,(ModelEntity*)geom,down)`、统一 `acceptChanges`；classification 在**创建时**经 model 首参指定；`gmi_dim/gmi_tag` 只读。
- 【消费端确认】空 2D mesh：`makeEmptyMdsMesh(model,2,false)` / `pumi_mesh_create(model,2,false)`。
- 【消费端确认】mesh_load 自动插 rank：`foo.smb`→`foo<rank>.smb`。
- 【生成端确认】P0 单 face 最小 model：1 geom vtx + 1 periodic edge + 1 loop + 1 face。
- 【生成端确认】Simmetrix `createMdsMesh(mdl,simApfMesh)` 是中转路径，**不适用 P0**。

## 16. 待版本源码确认项（阻塞 M4 实现）

- `makeEmptyMdsMesh` 第三参（matched/partitioned）语义。
- `createVertex`/`createEntity` 精确签名、`ModelEntity*` 与 `gmi_ent*` 转换、返回所有权。
- `writeNative` 输入是裸名/路径/base，是否需前置 `verify`。
- `acceptChanges` 能否分阶段、单进程必需性。
- `apf::Mesh::EDGE/TRIANGLE` 枚举定义。
- triangle downward 用 vertex 还是必须 edge；是否支持仅 vertex 建 triangle。
- SCOREC/PUMI 版本/提交。

## 17. 待最小运行验证项

- 单进程是否可省 residence/remotes/barrier。
- 2D triangle 方向（CW/CCW）是否被接受或需统一，错误在何处检测。
- 第三坐标 z=0 在 mesh vertex 侧的实际要求。
- `foo.smb` 单进程实际展开为 `foo0.smb`；生成端写出名与加载名 rank 对齐。
- 每 vertex/edge 的**本地** geom 分类判定规则（corner/boundary/interior）。
- `writeNative` 前 `verify` 是否必需。

## 18. 最小外部文件申请（版本阻塞，≤8）

> **版本未确认前不申请 core 文件**。以下为**版本确认后**的候选清单，每项说明符号与理由；当前一律标【版本阻塞】。

| # | 路径候选 | SCOREC 组件 | 确认符号 | 为何调用点不足 | 声明/实现 | 版本阻塞 |
|---|---|---|---|---|---|---|
| 1 | `apfMDS.h` | mds | `makeEmptyMdsMesh` 签名 | 只见调用，第三参语义未知 | 声明 | 是 |
| 2 | `apfMesh2.h` | apf | `createVertex`/`createEntity`/`acceptChanges`/`writeNative` | 只见调用点 | 声明 | 是 |
| 3 | `apfMesh.h` | apf | `Mesh::EDGE/TRIANGLE` 枚举、`ModelEntity` | 枚举/类型未确认 | 声明 | 是 |
| 4 | `apf.h` | apf | `verify` 签名 | 仅调试调用 | 声明 | 是 |
| 5 | `gmi.h` | gmi | `gmi_ent`/`gmi_find`/`gmi_add_analytic` | model↔mesh 类型转换 | 声明 | 是 |
| 6 | `gmi_analytic.h` | gmi | `gmi_add_analytic`/`gmi_add_analytic_reparam` | 参数语义 | 声明 | 是 |
| 7 | `pumi.h` | pumi | `pumi_mesh_create`/`pumi_mesh_load` | 封装层参数 | 声明 | 是 |
| 8 | `apfConvert.h` | apf | （仅确认 Simmetrix 路径边界，可选）| 排除误用 | 声明 | 是 |

- **停止规则**：以上均**待版本确认**；不得申请整个 core；不得下载最新版。

## 19. 对 M4-0E 的影响

### A. 蓝图可现在固化

- Triangle 唯一剖分底座；SCOREC/PUMI 非第二剖分引擎。
- M3DC1 P0 = `single_region` 单 face。
- P0 输出 = analytic model `.txt` + `.smb`（`.dmg` 延后）。
- 初始 `.smb` 不预存 C1 field / 高阶节点 / orientation。
- `M3DC1ModelSpec` 与 `Mesh2D` 分离；`region_ids` ≠ geom face tag。
- 禁止手写 `.smb` 字节流；采用正式 `writeNative`。
- 内存建网模板 = `createVertex`/`createEntity`/`acceptChanges`/`writeNative`（记为候选链，签名待确认）。

### B. 蓝图保留为实现停止条件

- 未确认版本的 API 签名（§16）。
- 每 entity 的本地 classification 判定与分配方式。
- `acceptChanges/verify/writeNative` 精确顺序与必需性。
- 单进程文件命名（`base0.smb`）与加载对齐。

### C. M4-0E 前是否需继续确认

1. **D1 完成后可进入 M4-0E**：A 组可固化，B 组作停止条件写入。
2. **是否需 D1.1 极窄 core 补充**：**否（先取版本证据）**；版本确认后再按 §18 申请单文件。
3. **是否需先做 D2**：**建议是**——D2 单进程最小 model+`.smb` 加载验收，可一次性运行验证 §17 全部项 + §16 部分签名。
4. **可延后到 M4 实现前**：§16 签名细节、§17 运行项，随 D2/实现验证。
5. **仍阻塞蓝图正式接口**：无——蓝图可用 A/B 两组表述固化，不被 B 组阻塞。

---

## 20. M4-0D2 初步验收输入

- **单进程 model 文件候选名**：`<base>.txt`（`m3dc1_model_load` 传裸名，无 rank 插入证据）。
- **单进程 mesh 文件候选名**：写出 `<base>0.smb`；加载传 `<base>.smb`（消费端插 rank → `<base>0.smb`）。
- **load API 参数**：`m3dc1_model_load(<base>.txt)` + `m3dc1_mesh_load(<base>.smb)`；`group_size=1`。
- **预期实际打开路径**：model=`<base>.txt`；mesh=`<base>0.smb`。
- **当前静态证据**：字符串拆分插 rank 逻辑（§12）确认；打开行为待运行。
- **待运行验证**：rank 展开、`group_size=1` 分支、model/mesh base 对齐、`verify`/`acceptChanges` 必需性、triangle 方向、residence 可省性。
- **预期成功判据**：`m3dc1_model_load`+`m3dc1_mesh_load` 返回 `M3DC1_SUCCESS`，`m3dc1_mesh_getnument` 顶点/三角形数与 `Mesh2D` 一致，classification 维度分布合理。

---

## 21. 与 TRIMEG Rbc/Zbc 的隔离

- TRIMEG `outer_boundary` 是进入 Triangle **前**的有序离散计算域边界。
- 人工矩形四控制角点**不能代替**重采样后的离散边界点列（`71fe09f` 错误）。
- `artificial_outer` 作为 boundary source 仍合法。
- 正确链路：控制几何 → 重采样边界 → Triangle 输入前点列 → `Mesh2D.outer_boundary` → `Rbc/Zbc`。
- `Rbc/Zbc` **不从 `idxevert` 反推**。
- M3D-C1 geometric classification **不改变** TRIMEG Writer。
- 本轮**不修改** `71fe09f`。
- M4-0E 后**先返回 M3 complete-11** 修复并验收，再正式实现 M4。

---

## 22. 完成声明

- 本轮只修改 `m4_0d1_report.md`。
- 未修改 `LinkMesh_Architecture_Plan.md`、`CONTEXT.md`、`History.md`。
- 未修改 LinkMesh 业务源码或测试。
- 未修改老师提供的参考源码。
- 未创建其他文件。
- 未编译或运行程序。
- 未下载 SCOREC/core。
- 未读取或解析 `.smb`/`.dmg`/`.smd`/`.sms`。
- 未猜测 `.smb` 字节布局。
- 未实现 model Writer、PUMI Adapter 或 SMB Writer。
- 未修改 `Mesh2D`。
- 未修复 `71fe09f`。
- TRIMEG `Rbc/Zbc` 修复仍保留在 M4-0E 蓝图验收后的 M3 complete-11 阶段。
