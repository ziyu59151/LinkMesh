# LinkMesh M4-0C1 程序骨架只读侦察报告

> 本报告为 M4 前置只读源码侦察。仅核对生成端（`meshgen`）与消费端（`m3dc1_scorec`）的程序入口、输入路径、model 文件职责、`.smb` 保存/加载顺序及依赖关系。未实现任何 `.smb`、PUMI、model file、C1、配置或 CLI 功能。

---

## 1. 执行摘要

- **生成端入口**：`test/m3dc1_meshgen.cc` 的 `main()`，接受**恰好一个**命令行参数（人类输入文件名），非法参数数量直接报错退出。
- **输入文件**：以纯文本 `fscanf` 逐关键字解析（`modelType`、`inFile`、`bdryFile`、`outFile`、`meshSize`、`vacuumParams` 等），非二进制。
- **四类文件对象**：M3D-C1 model `.txt`、Simmetrix model `.smd`、PUMI geometric model `.dmg`、PUMI native mesh `.smb`，由不同函数/库分别生成，职责清晰可区分。
- **`.smb` 保存 API**：由 SCOREC/PUMI 的 `apf::Mesh2::writeNative(filename)` 保存，属于 APF/MDS 层，**非 Simmetrix**。
- **顺序证据充分**：生成端明确"先创建/保存 model（`save_model` → `GM_write` → `gmi_write_dmg`），再转换并保存 mesh（`writeNative`）"。
- **消费端入口**：`m3dc1_model_load`（model）与 `m3dc1_mesh_load`/`m3dc1_mesh_load_3d`（mesh）；mesh 加载**依赖已加载的 geometric model 对象**（`apf::loadMdsMesh(model, mesh_file)` / `pumi_mesh_load`），构成【双向确认】。
- **依赖**：SCOREC PUMI（apf/mds/gmi/pcu/ma 等）为必需；MPI 必需；Simmetrix 在生成端 `meshgen` 必需，在消费端 `m3dc1_scorec` 为可选编译分支（`ENABLE_SIMMETRIX`）。**具体版本号在授权文件中未明确证明** → 版本未确认。
- **对 LinkMesh 的初步影响**：M3D-C1 消费端**需要 model 文件与 `.smb` 配套**，与 TRIMEG 单一 HDF5 自包含语义显著不同；输入架构需区分 model/几何来源与 mesh 输出。本轮无充分证据新增 `Mesh2D` 字段。

---

## 2. 已读文件

| 文件路径 | 用途 |
|---|---|
| `extracted/meshgen/meshgen/test/m3dc1_meshgen.cc` | 生成端 `main()` 入口与调用链 |
| `extracted/meshgen/meshgen/src/m3dc1_model.cc` | 生成端 model 创建/保存实现 |
| `extracted/meshgen/meshgen/include/m3dc1_model.h` | 生成端 model 接口声明 |
| `extracted/meshgen/meshgen/CMakeLists.txt` | 生成端依赖与可执行目标 |
| `extracted/meshgen/meshgen/cmake/FindScorec.cmake` | 生成端 SCOREC 库依赖列表 |
| `extracted/meshgen/meshgen/readme` | 生成端运行命令与依赖模块 |
| `extracted/meshgen/meshgen/test/data/input3` | 多区域人类输入短样例（已授权） |
| `extracted/meshgen/meshgen/test/data/readme` | 输入样例说明 |
| `extracted/m3dc1_scorec/m3dc1_scorec/api/m3dc1_scorec.cc` | 消费端 model/mesh load 实现 |
| `extracted/m3dc1_scorec/m3dc1_scorec/api/m3dc1_scorec.h` | 消费端对外 API 声明 |
| `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_model.cc` | 消费端 model 加载与几何构建 |
| `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_model.h` | 消费端 model 接口声明 |
| `extracted/m3dc1_scorec/m3dc1_scorec/CMakeLists.txt` | 消费端依赖与可执行目标 |
| `extracted/m3dc1_scorec/m3dc1_scorec/cmake/FindScorec.cmake` | 消费端 SCOREC 库依赖列表 |
| `extracted/m3dc1_scorec/m3dc1_scorec/README` | 消费端安装/运行命令 |
| 两份 `indexes/*_io_navigation.txt`、`*_source_files.txt`、`meshgen_text_sample_types.txt` | 仅定位，不作技术事实 |

未读取任何 `.txt`/`.smd`/`.dmg`/`.smb`/`.sms`/VTK/二进制/build 产物。

---

## 3. 生成端入口调用链

源文件：`test/m3dc1_meshgen.cc`

1. `main(argc, argv)`（约 L99）
   - `MPI_Init` → `m3dc1_scorec_init()`。
   - 参数校验：`if (argc!=2)` 报错 `usage: ./m3dc1_meshgen input_filename` 并 `MPI_Finalize` 返回。**接受恰好 1 个人类输入文件参数。**
2. 打开输入：`FILE* infp = fopen(argv[1],"r")`（约 L111），失败即报"File not found"。
3. 逐关键字解析（`while(EOF!=fscanf(infp,"%s",namebuff))`，约 L118 起）：
   - `modelType`、`reorder`、`numVacuumPts`→`numInterPts`、`inFile`→`in_ptsFile`、`bdryFile`→`out_ptsFile`、`outFile`→`modelName`、`resistive-width`→`thickness`、`vacuum-width/height`、`plasma-offsetX/Y`、`meshSize`（3 个）、`useVacuumParams`、`vacuumParams`（5 个：a/b/c/d/e）、`meshGradationRate`。
4. 几何创建（进入 `m3dc1_model.cc`）：`create_vtx`、`create_edge`、`attach_periodic_cubic_curve`、`attach_b_spline_curve`、`attach_natural_cubic_curve`、`create_loop`、`set_inner_wall_boundary`、`set_outer_wall_boundary`、`set_vacuum_boundary`（视 `modelType` 分支）。
5. 输出文件名确定（约 L640 起）：
   - `sprintf(filename, "%s"/"%s-%0.2f-%0.1f-%0.1f", modelName, ...)`（依 `modelType`）。
   - `model_filename = "%s.txt"` → `save_model(model_filename)`（**M3D-C1 model 文本**，`m3dc1_model.cc::save_model`）。
6. Simmetrix 建模与网格：
   - `make_sim_model(sim_model)`（本文件内，调用 `export_model_data` + Simmetrix `GR_createVertex/GR_createEdge/GR_createFace`）。
   - `model_filename = "%s.smd"` → `GM_write(sim_model, ...)`（**Simmetrix `.smd`**，Simmetrix 库）。
   - `SurfaceMesher_new/execute`（Simmetrix 面网格）→ `M_write(sim_mesh, "%s.sms", ...)`（**Simmetrix `.sms`**）。
7. 转换到 PUMI：
   - `gmi_sim_start(); gmi_register_mesh(); gmi_register_sim();`
   - `gmi_load("%s.smd")` → `gmi_write_dmg(mdl, "%s.dmg")`（**PUMI 几何模型 `.dmg`**，GMI 库）。
   - `PM_load(mesh_filename, sim_model, progress)` → `apf::createMesh` → `apf::createMdsMesh(mdl, simApfMesh)`。
   - `mesh->writeNative("%s.smb")`（约 L726，**PUMI native mesh `.smb`**，APF/MDS）。
8. **顺序结论**【生成端确认】：先 `save_model(.txt)` → `GM_write(.smd)` → `gmi_write_dmg(.dmg)`，最后 `writeNative(.smb)`。model 类文件均在 mesh `.smb` 之前生成。

---

## 4. `input3` 人类输入字段

源文件：`test/data/input3`（已授权，非二进制）。

| 输入行 | 字段 | 生成端读取位置（`m3dc1_meshgen.cc`）| 说明 |
|---|---|---|---|
| `numBdry 3` | 边界数 | **未在 `m3dc1_meshgen.cc` 关键字表中出现** | 属 `m3dc1_mfmgen`（`multi_meshgen.cc`，本轮未授权阅读）→【待确认】 |
| `bdryFile ... 3 0.2` 等 | 边界文件+区+尺度 | `m3dc1_meshgen.cc` 只 `fscanf` 一个 `bdryFile` 到 `out_ptsFile` | 多 `bdryFile` 多区解析不在本文件 →【待确认】 |
| `useVacuum 2 9 0.1` | 真空设置 | 未出现于 `m3dc1_meshgen.cc` | 属多区程序 →【待确认】 |
| `vacuumParams 1.8 1.5 0.4 0.0 2.5` | a/b/c/d/e | `m3dc1_meshgen.cc` L~135 `vacuumParams` 读 5 个 double | 单区程序也读同名参数 |
| `numFace 4` / `faceBdry ...` | 面-边界拓扑 | 未出现于 `m3dc1_meshgen.cc` | 属多区程序 →【待确认】 |
| `outFile input3` | 输出基名 | `m3dc1_meshgen.cc` `outFile`→`modelName` | 决定 `.txt/.smd/.dmg/.smb` 基名 |

**结论**：`input3` 是**多区域**输入样例，其大部分字段（`numBdry`、多 `bdryFile`、`useVacuum`、`numFace`、`faceBdry`）**不由本轮授权的 `m3dc1_meshgen.cc` 解析**，应由 `test/multi_meshgen.cc`（`m3dc1_mfmgen`）处理。`m3dc1_meshgen.cc` 匹配的短样例应为 `analytic-input`/`circle-input`（见 `test/data/readme`）。此差异标记【待确认】，留待 M4-0C2。

---

## 5. 四类文件对象表

| # | 文件 | 由谁创建（函数/库）| 类别 | 是否 M3D-C1 特有 | 文件名传递 | 是否必须配套 |
|---|---|---|---|---|---|---|
| 1 | M3D-C1 model `.txt` | `m3dc1_model.cc::save_model`（`fprintf` 写 loop/edge/vtx/curve/face）| M3D-C1 描述 | **是** | `sprintf(model_filename,"%s.txt",filename)` | 消费端 `load_model` 读它 →【双向确认】 |
| 2 | Simmetrix model `.smd` | Simmetrix `GM_write(sim_model,...)` | 几何模型（Simmetrix 私有）| 否 | `sprintf("%s.smd",filename)` | 生成端中转，消费端未见直接加载 →【生成端确认】 |
| 3 | PUMI geometric model `.dmg` | GMI `gmi_write_dmg(mdl,...)` | 几何模型（PUMI）| 否 | `sprintf("%s.dmg",filename)` | 是否被消费端加载 →【待确认】（见第 7 节）|
| 4 | PUMI native mesh `.smb` | APF/MDS `mesh->writeNative(...)` | 网格 | 否 | `sprintf("%s.smb"/"%s-%dK.smb",filename,...)` | 消费端 `loadMdsMesh/pumi_mesh_load` 读它 →【双向确认】 |

- **属几何模型**：`.smd`（Simmetrix）、`.dmg`（PUMI）。
- **属网格**：`.smb`。
- **属 M3D-C1 特有描述**：`.txt`（loop/edge/curve/face + separatrix/innerWall/outerWall/vacuum loop 标记）。
- **配套证据**：`.txt` ↔ 消费端 `load_model`【双向确认】；`.smb` ↔ 消费端 mesh load【双向确认】；`.smd/.dmg` 在生成端为中转产物，消费端是否直接读取【待确认】。
- 未由扩展名推断任一文件的内部字节格式。

---

## 6. `.smb` 保存证据

- 直接证据（`m3dc1_meshgen.cc` 约 L726）：
  - `mesh->writeNative(mesh_filename);`，其中 `mesh` 为 `apf::Mesh2*`（`apf::createMdsMesh(mdl, simApfMesh)` 返回），`mesh_filename` 形如 `"%s-%dK.smb"` 或 `"%s-%d.smb"`。
- 保存 API：**`apf::Mesh2::writeNative`**（SCOREC APF/MDS 层），非 Simmetrix `M_write`。
- 前置：`.smb` 由 `createMdsMesh` 产生的 MDS 网格写出，而该网格由 `gmi_load(.smd)` 得到的几何模型 `mdl` 与 `PM_load(.sms)` 的 Simmetrix 网格转换而来。
- 消费端对应保存点（旁证，非本任务主线）：`m3dc1_scorec.cc` 内多处 `writeNative("...smb")`（如 `m3dc1_scorec_finalize` 的 `adapted-mesh.smb`、`m3dc1_mesh_write`），确认 `.smb` 读写均走 `writeNative`/`loadMdsMesh`。

---

## 7. 消费端 model→mesh 加载调用链

源文件：`api/m3dc1_scorec.cc`、`src/m3dc1_model.cc`、`api/m3dc1_scorec.h`、`include/m3dc1_model.h`。

1. **Model load 对外 API**：`int m3dc1_model_load(char* model_file)`（`m3dc1_scorec.cc` L~870；声明 `m3dc1_scorec.h` L62）。
   - 校验文件存在（`fopen`）。
   - `pGeom g = pumi_geom_load(model_file, "analytic");`（**PUMI/GMI 加载，模式 "analytic"**）。
   - `m3dc1_model::instance()->model = g->getGmi();`
   - `m3dc1_model::instance()->load_analytic_model(model_file);` → 进入 `m3dc1_model.cc`。
   - `pumi_geom_freeze(g);` → `caculateBoundingBox()` → 记录 `numEntOrig[0..2]`。
2. `load_analytic_model`（`src/m3dc1_model.cc`）：
   - 若文件名为 `"AnalyticModel"` → 内建 `CMODExpressionR/Z` + `gmi_add_analytic`。
   - 否则 `load_model(name)`：`fscanf` 读 `numL/separatrixLoop/innerWallLoop/outerWallLoop/vacuumLoop`，逐 loop 读 vtx/edge/curve（LIN/POLY/BSPLINE）→ `create_vtx/create_edge/attach_*` → `gmi_add_analytic` + `make_edge_topo/make_face_topo`。
   - **确认：消费端直接读取的是第 5 节表中的 M3D-C1 model `.txt`，经 `pumi_geom_load(...,"analytic")` + `load_model` 构建 GMI analytic 几何模型。**
3. **Mesh load 对外 API（2D）**：`int m3dc1_mesh_load(char* mesh_file)`（`m3dc1_scorec.cc` L~1049；声明 `.h` L72）。
   - 拼接分区文件名 `base + rank + "." + ext`（如 `part<rank>.smb`），逐 rank `fopen` 校验。
   - master plane：`m3dc1_mesh::instance()->mesh = pumi_mesh_load(pumi::instance()->model, mesh_file, m3dc1_model::instance()->group_size);`
   - **参数**：`(geometric model, mesh_file, group_size)` → 依赖已加载 model 与 group size。
   - 非 master plane：`pumi_mesh_create(pumi::instance()->model, 2, false)`（**维度 2**）。
   - 清理 file 带入的 field/numbering/tag（保留 `norm_curv`）。
   - 若 `num_plane==1`：`compute_globalid(...,0)`、`compute_globalid(...,2)`。
4. **Mesh load（3D）**：`void m3dc1_mesh_load_3d(char* mesh_file, int* num_plane)`（`m3dc1_scorec.cc` L~1007；声明 `.h` L73）。
   - 切回 global comm；`m3dc1_model::instance()->create3D();`
   - `m3dc1_mesh::instance()->mesh = apf::loadMdsMesh(m3dc1_model::instance()->model, mesh_file);`（**直接以已加载的 geometric model 为参数加载 MDS 网格**）。
5. **是否必须先加载 model**：**是**【消费端确认】。`pumi_mesh_load`/`loadMdsMesh` 均以 `model`（`pumi::instance()->model` / `m3dc1_model::instance()->model`）为首参，`.smb` 加载依赖已构建的 geometric model。
6. **`.smb` 是否依赖 geometric model**：**是**【消费端确认】（同上，MDS 网格与几何模型分类绑定）。
7. **MPI/group/分区参数**：
   - `group_size`（`m3dc1_model::set_num_plane` 设定 `group_size=PCU_Comm_Peers()/factor`）直接传入 `pumi_mesh_load`。
   - master/non-master plane 分支、`local_planeid`、分区文件名含 `rank` → 加载与 MPI 分区强相关【消费端确认】。
8. **维度要求**：2D 路径 `pumi_mesh_create(model, 2, false)` 明确维度 2；3D 由 `create3D()`+`loadMdsMesh` 处理。当前授权文件足以确认 2D/3D 两条路径【消费端确认】。

> `pumi_geom_load`/`pumi_mesh_load`/`pumi_mesh_create`/`pumi_geom_freeze` 的**具体实现**位于 SCOREC/core 的 `pumi` 封装（未授权）。本轮只确认调用点与参数，实现语义标记【待确认】，申请见第 13 节。

---

## 8. 生成端—消费端对照表

| 环节 | 生成端证据 | 消费端证据 | 判定 |
|---|---|---|---|
| model 创建 ↔ model 加载 | `save_model` 写 `.txt`（loop/edge/curve/face + 4 类 loop 标记）| `m3dc1_model_load`→`load_analytic_model`→`load_model` 读同结构 | 【双向确认】 |
| `.smd` 写出 ↔ `.smd` 加载 | `GM_write(sim_model,"%s.smd")` | 消费端未见直接加载 `.smd` | 【生成端确认】 |
| `.dmg` 写出 ↔ `.dmg` 加载 | `gmi_write_dmg(mdl,"%s.dmg")` | 消费端走 `pumi_geom_load(...,"analytic")`+`load_model(.txt)`，未见显式 `gmi_load(.dmg)` | 【待确认】（是否用 `.dmg` 或 `.txt` 作为几何入口需 SCOREC/core 佐证）|
| `.smb` 保存 ↔ `.smb` 加载 | `mesh->writeNative("%s.smb")`（APF/MDS）| `pumi_mesh_load(model, mesh_file, group_size)` / `apf::loadMdsMesh(model, mesh_file)` | 【双向确认】 |
| 文件路径参数 | `sprintf` 基于 `outFile`/`modelName` 生成各扩展名 | `model_file`、`mesh_file` 作为 API 参数传入 | 【双向确认】 |
| model 对象在 mesh I/O 中的作用 | 生成端 `createMdsMesh(mdl, simApfMesh)` 以几何模型建 MDS | 消费端 `loadMdsMesh(model, mesh_file)` 以几何模型加载 MDS | 【双向确认】 |
| MPI/group 参数 | 生成端 `PM_load(...,sim_model,progress)`；`m3dc1_scorec_init` 起 PUMI | 消费端 `group_size`、master/non-master plane、rank 分区文件 | 【消费端确认】（生成端此处未显式 group 分区）|

---

## 9. 单区域/多区域初步线索

仅基于本轮入口/model 源码直接出现的符号：

- **单区域 vs 多区域分支**：
  - 生成端 `m3dc1_meshgen.cc` 按 `modelType`（0/1/2/3/4）分支，含 `useVacuumParams` 决定 5 边或 6 边；`m3dc1_mfmgen`（`multi_meshgen.cc`，未授权）为多区域专用（由 `input3` 的 `numFace`/`faceBdry` 推断）→【待确认】多区细节。
  - 消费端 `load_model` 读 `numL`（loop 数）与 `numFaces`，支持多 loop/多 face → 消费端**结构上支持多区域**【消费端确认】。
- **region / boundary loop / curve / point 概念**：
  - 明确出现：`loopContainer`、`edgeContainer`、`vtxContainer`、`create_loop`、`create_edge`、`create_vtx`、`attach_*_curve`（LIN/POLY/BSPLINE）。
  - 边界语义：`set_inner_wall_boundary`、`set_outer_wall_boundary`、`set_vacuum_boundary`、`set_separatrix` 及 `separatrixLoop/innerWallLoop/outerWallLoop/vacuumLoop`。
- **geometric classification**：
  - 消费端 `m3dc1_ent_getgeomclass` 用 `gmi_dim/gmi_tag(model, gent)`，`toModel(ent)` 取得实体的几何分类 → **网格实体分类到 model 实体**【消费端确认】。
- **model entity 与网格实体编号体系不同**：
  - 消费端 mesh 实体用 `getMdsIndex/getMdsEntity`（MDS 本地索引）与 `get_ent_globalid`；model 实体用 `gmi_tag`（几何 tag）。二者独立 → **不是同一编号体系**【消费端确认】。

（完整 entity/classification 契约不在本轮展开，留 M4-0C2。）

---

## 10. 版本与依赖

来源：授权的 `README`、两份 `CMakeLists.txt`、两份 `FindScorec.cmake`、`readme`。

- **SCOREC/PUMI 库依赖**（`FindScorec.cmake` `SCOREC_LIB_NAMES`）：
  - 非 Simmetrix 分支：`crv (dsp) ph sam spr ma apf_zoltan parma mds apf lion mth gmi pcu`。
  - Simmetrix 分支：额外 `apf_sim gmi_sim`。
  - 头文件探测：`apf.h PCU.h ma.h`。→ 确认 **APF / GMI / MDS / PCU / MA** 接口名。
- **MPI**：必需。两端源码含 `MPI_Init/MPI_Finalize/PCU`，README 用 `mpirun -np ...`。
- **Simmetrix / SimModSuite**：
  - 生成端 `meshgen/CMakeLists.txt`：`set(ENABLE_SIMMETRIX "ON")`，`find_package(SimModSuite/Simmetrix REQUIRED)` → **生成端必需**。
  - 消费端 `m3dc1_scorec/CMakeLists.txt`：`if (ENABLE_SIMMETRIX) ... else PETSC/TRILINOS` → **消费端可选**（默认走 PETSc）。
- **PETSc / Trilinos**（消费端）：`ENABLE_PETSC`/`ENABLE_TRILINOS` 分支，非本轮 I/O 主线。
- **明确版本/提交/分支/路径**：
  - README 出现安装路径样例（如 `/usr/local/openmpi/latest`、`simmetrix/simModSuite/11.0-170826`、`PETSC 3.5.1`、`SimModSuite18.0-230521` 注释、`2024.0-231117dev` 等），但**未固定 SCOREC/core 的版本或提交号**。
  - → **SCOREC/PUMI/APF/GMI 版本未确认**；不得默认 GitHub 最新 core。
- **两端依赖接口一致性**：均使用同名 `apf/mds/gmi/pcu` 库与 `writeNative/loadMdsMesh`（生成端）、`pumi_*`（消费端）→ 接口族一致，但**版本一致性未确认**。

---

## 11. 对 LinkMesh 输入架构的初步影响

仅基于本轮直接证据：

1. **model 与 `.smb` 必须配套**：消费端 `loadMdsMesh/pumi_mesh_load` 首参即 geometric model，`.smb` 无法脱离已加载 model 独立消费 →【消费端确认】。LinkMesh 若走 M3DC1 路线，**必须同时产出网格与其几何 model 描述**（M3D-C1 `.txt` 或 PUMI 几何），不能只给 `.smb`。
2. **输入架构需区分角色**：本轮证据显示生成端输入天然区分：几何来源（loop/curve/point、边界文件 `bdryFile`）、区域/真空参数（`vacuumParams`/`useVacuum`）、输出基名（`outFile`）。LinkMesh 输入架构若扩展 M3DC1，应区分 **target（输出基名/格式）/ domain profile（区域与网格尺度）/ boundary source（几何边界来源）/ 输出文件**。
3. **可能属于未来 `linkmesh.in` 的字段**：输出基名、每区域网格尺度、边界文件来源、真空/wall 参数、`modelType` 类似的域类型选择。**均为线索，非本轮定稿**。
4. **仍需 M4-0C2/C3 确认**：`.dmg` 是否为消费端几何入口；`pumi_geom_load("analytic")` 对 model 文本的确切格式要求；多区域 `faceBdry` 拓扑语义；classification/entity 编号契约；C1 自由度与高阶节点。
5. **不得套用 TRIMEG 语义**：TRIMEG 为单一自包含 HDF5、单连续域；M3DC1 为 model+mesh 双件、支持多 loop/多 face/几何分类，语义不可直接迁移。
6. **不新增 `Mesh2D` 字段**：本轮**未发现**必须持久保存且无法从现有数据反推的跨 Writer 规范数据的直接证据，故**不提出**任何 `Mesh2D` 新字段。

---

## 12. 未确认项【待确认】

- `input3` 多区字段（`numBdry`/多 `bdryFile`/`useVacuum`/`numFace`/`faceBdry`）的实际解析代码（应在 `multi_meshgen.cc`，未授权）。
- 消费端几何入口究竟是 M3D-C1 `.txt`（经 `pumi_geom_load("analytic")`）还是 PUMI `.dmg`；`.dmg` 在消费端是否被 `gmi_load` 使用。
- `pumi_geom_load` / `pumi_mesh_load` / `pumi_mesh_create` / `pumi_geom_freeze` 的实现语义（位于 SCOREC/core `pumi`，未授权）。
- M3D-C1 model `.txt` 的确切文本格式契约（本轮只从 `save_model`/`load_model` 的 `fprintf`/`fscanf` 结构间接推断，未读实际 `.txt`）。
- SCOREC/PUMI/APF/GMI 的**具体版本**：版本未确认。
- 多区域 region↔face↔loop 拓扑与 classification 完整契约。
- C1 连续性、高阶单元、边方向、几何分类到自由度的映射。

---

## 13. M4-0C2 最小文件申请（≤10）

| # | 完整路径 | 已有调用点指向 | 需确认问题 | 为何现有文件不足 |
|---|---|---|---|---|
| 1 | `extracted/meshgen/meshgen/test/multi_meshgen.cc` | `input3` 的 `numBdry/numFace/faceBdry`；生成端多区可执行 `m3dc1_mfmgen` | 多区域输入字段如何解析、多 face/loop 拓扑如何建立 | `m3dc1_meshgen.cc` 不解析这些字段 |
| 2 | `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_mesh.cc` | `m3dc1_mesh::instance()->initialize()`、`build3d`、`set_node_adj_tag` | mesh 加载后如何初始化本地/全局实体计数与维度约束 | I/O 主文件只调用未展开实现 |
| 3 | `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_mesh.h` | 同上 `m3dc1_mesh` 类 | 网格对象字段/维度/plane 结构声明 | 需接口才能读懂 mesh load 语义 |
| 4 | `extracted/meshgen/meshgen/include/Expression.h` | `m3dc1_model.cc` `M3DC1::Expression`、`evalCoord/evalNormalVector` | curve/几何求值接口，判断 model 文本几何语义 | model.cc 仅使用不声明 |
| 5 | `extracted/meshgen/meshgen/include/BSpline.h` | `attach_b_spline_curve`、`save_model` 的 `getpara` | model `.txt` 中 BSPLINE 段字段含义（order/knots/ctrlPts）| 需确认 `.txt` 几何格式而不读实际 `.txt` |
| 6 | `extracted/m3dc1_scorec/m3dc1_scorec/api/name_convert.h` | `m3dc1_scorec.h` `#include "name_convert.h"`；`m3dc1_model_load_`/`m3dc1_mesh_load_` | Fortran↔C 符号映射，确认对外 API 真实调用名 | 头文件只 `#define` 引用 |
| 7 | `extracted/m3dc1_scorec/m3dc1_scorec/README`（复核 PUMI 段） | 已读，但需定位 `pumi.h` 来源 | `pumi_*` 封装归属哪个 core 头/库 | 现 README 未给 `pumi.h` 路径 |
| 8 | `extracted/meshgen/meshgen/test/data/analytic-input`（若为文本、低密度） | `test/data/readme` 指 `m3dc1_meshgen` 用 `analytic-input`/`circle-input` | 与 `m3dc1_meshgen.cc` 匹配的单区输入字段对照 | `input3` 属多区，不匹配本文件 |
| 9 | `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_entity.cc` | `get_ent_globalid`、`getMdsIndex`、`toModel` 相关 | mesh 实体与 model 实体编号/分类的确切来源 | I/O 文件只调用，未定义 |
| 10 | `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_field.h`（已摘要） | `m3dc1_mesh_load` 后 field 清理；`build3d(num_field,...)` | field 与网格加载的耦合，判断是否影响纯网格输入 | 仅有摘要，需完整确认耦合边界 |

> 不申请任何目录、完整 M3DC1 仓库或完整 SCOREC/core。第 8 项以"若为低密度文本"为前提，若为高密度数值则放弃。

---

## 完成声明

- 未修改任何文件（仅在唯一可编辑文件 `report.md` 中输出本报告）。
- 未创建除 `report.md` 外的报告文件；`report.md` 为本轮唯一 Editable 目标。
- 未运行或编译任何程序。
- 未读取高密度数值模型或二进制文件（未读 `.txt`/`.smd`/`.dmg`/`.smb`/`.sms`/VTK/对象/库/可执行/build）。
- 未修改蓝图、History、LinkMesh 源码或测试。
- 未实施 `.smb`、PUMI、C1、配置或 CLI 代码。
- 未处理暂停中的 M3 complete-11 提交 `71fe09f`。
