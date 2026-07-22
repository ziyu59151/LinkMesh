# LinkMesh M4-0C2 实体、拓扑与 Geometric Classification 只读侦察报告

> 本报告为 M4 前置只读源码侦察第二轮。基于生成端 `meshgen` 与消费端 `m3dc1_scorec` 源码，确认 M3D-C1 model face/loop/edge/vertex 组织方式、mesh vertex/edge/triangle 到 geometric model entity 的分类关系，以及对 LinkMesh 输入架构与 `Mesh2D` 的影响。未实现任何 `.smb`、PUMI、model Writer、C1、配置或 CLI 功能。

---

## 1. 执行摘要

- **多区域入口**：`test/multi_meshgen.cc` 的 `main()` 按关键字循环解析 `input3`，识别 `numBdry`、多条 `bdryFile`、`useVacuum`、`vacuumParams`、`numFace`、`faceBdry`、`thickWall`、`meshGradationRate`、`outFile`。**`input3` 对应 `m3dc1_mfmgen`（`multi_meshgen.cc`），非 `m3dc1_meshgen`**【生成端确认】。
- **单区域入口**：`test/m3dc1_meshgen.cc` 处理 `analytic-input`（`modelType`/`vacuumParams`/`numVacuumPts`/`meshSize`/`outFile`），走 `createVacuum` 单 loop 路径。
- **多 face ≠ 多物理区域**：生成端多 face 是 **geometric model 的多 face（多 loop）**，源码**未出现**"每 face 对应不同控制方程/材料"的直接证据。多物理区域语义标记【待确认】，**不得**等同 LinkMesh 物理区域。
- **model 拓扑**：vertex→edge→loop→face 四级；edge 在 face 构造中携带**方向（edgeDir 0/1）**；一个 face 可含多个 loop（`face_bdry[i]` 为 loop ID 列表）；`save_multi_rgn_model` 写出 face↔loop 拓扑【生成端确认】。
- **消费端恢复**：`load_model()` 逐字段读回 `numL/separatrixLoop/innerWallLoop/outerWallLoop/vacuumLoop` + 每 loop 的 vtx/edge/curve + face↔loop，构成与 `save_model`/`save_multi_rgn_model` 的**字段级对照**（详见第 8 节），核心字段【双向确认】。
- **mesh classification**：消费端 `m3dc1_ent_getgeomclass` 用 `toModel(ent)`+`gmi_dim/gmi_tag(model, gent)` 取 mesh entity 的 geometric 分类维度与 tag【消费端确认】。**mesh edge/vertex 到 geometric edge/vertex 的具体分类规则（内部 vs 边界）由 PUMI/MDS `.smb` 与 SCOREC/core 决定**，当前授权文件**不足以**逐条证明第七/八/九项，标记【待确认】。
- **编号体系**：model tag（几何 tag）、mesh local ID（MDS index）、mesh global ID 三者独立；edge 方向以 `edgeDir`/`F_edgeDir` 的 **0/1 或负号 ID** 表达【混合确认】。
- **对 LinkMesh 的影响**：M3DC1 model 需要**分段 geometric edge + face↔loop 拓扑 + edge 方向**，比 TRIMEG 单条有序 `outer_boundary` 需要更多拓扑信息。是否进入通用 `Mesh2D` 还是仅进入 M3DC1 Adapter 输入对象，属架构决策，本轮**不定稿**。
- **项目边界**：TRIMEG `Rbc/Zbc` 契约不变；提交 `71fe09f` 的 `outer_boundary` 问题仍暂停，本轮不修复。

---

## 2. 已读文件和跳过文件

### 已读（授权，纯文本源码）

| 文件路径 | 用途 |
|---|---|
| `extracted/meshgen/meshgen/test/multi_meshgen.cc` | 多区域生成端 `main()`、`get_multi_rgn`、`make_sim_model`、`createVacuum`、`createOffsetCurve` |
| `extracted/meshgen/meshgen/test/m3dc1_meshgen.cc` | 单区域生成端入口（对照）|
| `extracted/meshgen/meshgen/src/m3dc1_model.cc` | 生成端 model 拓扑创建、`save_model`、`save_multi_rgn_model` |
| `extracted/meshgen/meshgen/include/m3dc1_model.h` | 生成端 model 接口、`curveType` 枚举、Writer 声明 |
| `extracted/meshgen/meshgen/include/Expression.h` | curve 求值接口 |
| `extracted/meshgen/meshgen/include/BSpline.h` | BSpline 参数（order/ctrlPts/knots/weight）|
| `extracted/meshgen/meshgen/test/data/analytic-input` | 单区域输入样例（低密度文本）|
| `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_model.cc` | 消费端 `load_model`、`get_gent_adj`、`create3D` |
| `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_model.h` | 消费端 model 接口、`get_gent_adj` 声明 |
| `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_mesh.cc` | 消费端网格加载/初始化/计数/`set_node_adj_tag` |
| `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_mesh.h` | 消费端 `m3dc1_mesh` 类字段（local/own/global 计数、tag）|
| `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_entity.cc` | mesh entity classification/ownership/global ID |
| `extracted/m3dc1_scorec/m3dc1_scorec/api/m3dc1_scorec.cc` | `m3dc1_ent_getgeomclass`、`m3dc1_mesh_getnument`、遍历点 |
| `extracted/m3dc1_scorec/m3dc1_scorec/api/m3dc1_scorec.h` | 对外 API 声明 |
| 两份 `*_classification_navigation.txt` | 仅定位 |

### 跳过（未授权 / 二进制 / 高密度）

- `.smb`/`.sms`/`.dmg`/`.smd`/VTK/对象/库/可执行/build 产物。
- `input3.txt`（高密度点列数字，仅读结构性 `input3` 关键字样例，未读点列文件本体）。
- SCOREC/core 的 `pumi`/`gmi`/`mds` 实现（未授权）。
- `Simmetrix` 头（生成端 `make_sim_model` 中 `GR_*`/`GM_write` 仅确认调用点，不进入实现）。

---

## 3. `analytic-input` 与单区域入口

源文件：`test/m3dc1_meshgen.cc`、`test/data/analytic-input`。

`analytic-input`（低密度文本，逐字段）：

| 关键字 | 参数 | 源码读取点（`m3dc1_meshgen.cc`）| 含义 | 状态 |
|---|---|---|---|---|
| `modelType 0` | 1×int | `strcmp(...,"modelType")`→`fscanf(...,&modelType)` | 域类型分支（0=参数化真空）| 【生成端确认】 |
| `outFile analytic` | 1×str | `outFile`→`modelName` | 输出基名 | 【生成端确认】 |
| `meshSize 0.04` | N×double | `meshSize` 循环读 `numFace` 个（单区常为 1）| 网格尺度 | 【生成端确认】 |
| `SimLic ...` | 路径 | 许可（非拓扑）| Simmetrix 许可 | 【生成端确认】 |
| `useVacuumParams 1` | 1×int | `useVacuumParams` | 是否用解析真空参数 | 【生成端确认】 |
| `vacuumParams ...` | 5×double | `vacuumParams`（a/b/c/d/e）| 解析真空曲线参数 | 【生成端确认】 |
| `numVacuumPts 20` | 1×int | `numVacuumPts`→`numInterPts` | 真空曲线插值点数 | 【生成端确认】 |

- 单区域路径：`modelType==0` 且 `useVacuumParams==1` → `createVacuum(vacuumLoopId, ...)`，`aexp(u,xyz)` 生成参数化椭圆状真空边界，`attach_periodic_cubic_curve` + `create_loop` + `set_vacuum_boundary`（单 loop）。
- **单区域程序也可能创建多个 loop**：`m3dc1_meshgen.cc` 其余 `modelType`（1/2/3/4）分支含 inner/outer wall 两条 loop（`set_inner_wall_boundary`/`set_outer_wall_boundary`）。故"单区域可执行"≠"仅一个 loop"【生成端确认】。

---

## 4. `input3` 与多区域入口

源文件：`test/multi_meshgen.cc`。仅读 `input3` 结构性关键字样例（第 5 节表引用），**未读** `bdryFile` 指向的高密度点列文件本体。

- `main()` 打开 `argv[1]`，`while(EOF!=fscanf(infp,"%s",namebuff))` **按关键字循环解析，顺序不固定**【生成端确认】。
- 多区域路径核心：`get_multi_rgn()` 读第一条 `bdryFile`（inner wall），`inner_outer_wall_pts()` 读其余 `bdryFile`；`make_sim_model(sim_model, face_bdry)` 依 `face_bdry`（每 face 的 loop ID 列表）构造 Simmetrix 多 face；`save_multi_rgn_model(...)` 写多区 model 文本。
- **`input3` 对应 `m3dc1_mfmgen`（`multi_meshgen.cc`）**：`numBdry`/`numFace`/`faceBdry` 均在本文件解析，`m3dc1_meshgen.cc` 无这些关键字【生成端确认】。

---

## 5. 人类输入字段表（`input3` / 多区域）

源码位置均在 `test/multi_meshgen.cc` 的 `main()` 关键字循环。

| 关键字 | 参数数 | 类型 | 物理/拓扑含义 | 读取位置 | 后续使用 | 验证规则 | 状态 |
|---|---|---|---|---|---|---|---|
| `numBdry` | 1 | int | 边界文件总数 | `strcmp(...,"numBdry")`→`fscanf(...,&numBdry)` | `assert(numBdry==bdry_files.size())` | 末尾 assert 校验 | 【生成端确认】 |
| `numFace` | 1 | int | geometric face 数 | `numFace`→`fscanf`；`face_bdry.resize(numFace)`；`meshSizes=new double[numFace]` | 分配 `face_bdry`/`meshSizes` | 分配依赖，无独立范围校验 | 【生成端确认】 |
| `bdryFile` | 1×str + 1×int + 1×double | 文件名/loopNumber/edgeMeshSize | 一条边界点列文件 + 其 loop ID + 该 loop 网格尺度 | `fscanf(infp,"%s",bdryFile)`→`push_back`；`fscanf(...,&loopNumber)`；`fscanf(...,&edgeMeshSize)` | `loopsMap[idx]=loopNumber`；`loopSizeMap[loopNumber]=edgeMeshSize` | 无重复 loop 校验（源码未见）| 【生成端确认】 |
| `faceBdry` | 1×int(numLoop) + numLoop×int + 1×double | loop 数 / loop ID 列表 / face 网格尺度 | 一个 face 由哪些 loop 围成 + 该 face 尺度 | `fscanf(...,&numLoop)`；循环 `fscanf(...,&loopID)`→`face_bdry[index].push_back(loopID)`；`fscanf(...,&faceMeshSize)`；`faceSizeMap[index]=faceMeshSize`；`++index` | `make_sim_model` 构造 face | 无非法 loop ID 校验（源码未见）| 【生成端确认】 |
| `useVacuum` | 3 | int/int/double | 真空开关 / 真空 loop ID / 真空网格尺度 | `fscanf(...,&useVacuum)`；`fscanf(...,&vacuumLoopId)`；`fscanf(...,&vacuumLoopMeshSize)` | `loopSizeMap[vacuumLoopId]=...`；`createVacuum(vacuumLoopId,...)` | 无 | 【生成端确认】 |
| `vacuumParams` | 5 | double×5 | a/b/c/d/e 解析真空曲线参数 | `fscanf("%lf %lf %lf %lf %lf",&a_param,...,&e_param)` | `aexp()` 生成真空边界 | 无 | 【生成端确认】 |
| `thickWall` | 4 | int/int/int/double | 开关/内 loop/外 loop/厚度 | `fscanf(...,&useThickWall)`；`wallInLoopId`；`wallOutLoopId`；`thickness` | `createOffsetCurve(wallEdgeId, wallOutLoopId)` | 无 | 【生成端确认】 |
| `modelType` | 1 | int | 模型类型（影响文件名格式）| `fscanf(...,&modelType)` | 文件名 `sprintf` 分支 | 无 | 【生成端确认】 |
| `reorder` | 1 | int | PUMI 重排开关 | `fscanf(...,&reorder)` | 是否 `numberOwnedDimension` 重排 | 无 | 【生成端确认】 |
| `numVacuumPts` | 1 | int | 真空插值点数 | `fscanf(...,&numInterPts)` | `createVacuum` 采样 | 无 | 【生成端确认】 |
| `inFile` | 1 | str | 输入点列文件（与 bdryFile 并列的一种）| `fscanf(...,bdryFile)`→`push_back` | `bdry_files` | 无 | 【生成端确认】 |
| `outFile` | 1 | str | 输出基名 | `fscanf(...,modelName)` | `.txt/.smd/.dmg/.smb` 基名 | 无 | 【生成端确认】 |
| `meshSize` | numFace | double×numFace | 每 face 尺度（旧式）| 循环 `fscanf(meshSizes+i)` | `MS_setMeshSize` | 依赖 `numFace` 已设 | 【生成端确认】 |
| `meshGradationRate` | 1 | double | 网格梯度率 | `fscanf(...,&meshGradationRate)` | `MS_setGlobalSizeGradationRate` | 无 | 【生成端确认】 |

- **未知关键字**：循环中无 `else` 分支报错，未匹配关键字被**静默跳过**（`fscanf("%s")` 读下一 token）【生成端确认】。
- **非法数量/重复 face/无效边界 ID**：源码**未见**显式校验（仅末尾 `assert(numBdry==bdry_files.size())`），其余越界/重复处理【待确认】。
- **mesh size 传递**：per-loop 经 `loopSizeMap`，per-face 经 `faceSizeMap`，在 `make_sim_model` 后由 `MS_setMeshSize(meshCase, edge/face, ...)` 应用【生成端确认】。

---

## 6. model vertex/edge/loop/face 拓扑

源文件：生成端 `multi_meshgen.cc` + `src/m3dc1_model.cc` + `include/m3dc1_model.h`；消费端 `src/m3dc1_model.cc`。

### 生成端构造

1. **vertex/point**：`create_vtx(int* vertex, double* position)`（`m3dc1_model.cc`）→ `vtxContainer[*vertex]=coord` + `gmi_add_analytic(model,0,*vertex,...)`。**ID 由调用方给定**（如 `gv1_id`），非自动分配【生成端确认】。
2. **edge/curve**：`create_edge(int* edge, int* startingvtx, int* endingvtx)` → `edgeContainer[*edge]=make_pair(start,end)`；curve 由 `attach_*_curve` 附加，`gmi_add_analytic(model,1,*edge,...)` + `make_edge_topo(model,gedge,vtx.first,vtx.second)`【生成端确认】。
3. **loop**：`create_loop(int* loopId, int* numEdges, int* EdgeList)` → `loopContainer[*loopId].push_back(EdgeList[i])`。loop = edge ID 列表【生成端确认】。
4. **edge 在 loop 中的方向**：`create_loop` 存储的是 edge ID（正数），**loop 层未显式存正负号**；**方向在 face 构造时以 `edgeDir` 决定**（见下）【生成端确认】。
5. **face**：多区域 `make_sim_model`（`multi_meshgen.cc`）中，对 `face_bdry[i]`（loop ID 列表）逐 loop 取 `edgesOnLoop`，`outerLoop(loopsOnFace)` 判定最外 loop，最外 loop `edgeDir=1`，其余 `edgeDir=0`；`GR_createFace(..., faceEdges, faceDirs, numLoops, loopDef, ...)`。**face 可由多个 loop 组成，外环/内环以 `edgeDir` 区分**【生成端确认】。
6. **外环/内环表达**：通过 `outerLoop()` 计算 + `edgeDir` 标记；`loopDef[]` 记录每 loop 在 `faceEdges` 中的起始偏移【生成端确认】。
7. **多 face 共享 edge / 内部界面**：`edgesOnLoop` 与 `loopContainer` 允许同一 loop/edge 被多个 face 引用（`face_bdry` 中同一 loop ID 可出现在相邻 face），故**内部界面表现为相邻 face 共享一条 geometric edge/loop**——但 `input3` 是否实际这样组织需读点列与实际 face_bdry 数值，标记【待确认（拓扑机制生成端确认，具体 input3 实例待确认）】。
8. **边界语义标记**：`set_inner_wall_boundary`/`set_outer_wall_boundary`/`set_vacuum_boundary`/`set_separatrix` 分别设 `innerWallLoop`/`outerWallLoop`/`vacuumLoop`/`separatrixLoop` 全局标量（loop ID）【生成端确认】。
9. **编号起点/约束**：ID 均由调用方给定（`gv1_id=1`、`ge1_id=1`、`loop_id` 来自输入 `loopNumber`）；`create_edge`/`create_loop` 对重复 ID `throw 1`（去重保护）【生成端确认】。
10. **Writer 写出**：`save_multi_rgn_model` 写 `numL/4 类 loop 标记` + 每 loop 的 vtx/edge/curve + `numFaces` + 每 face 的 `faceNum/numLoops/loop IDs`【生成端确认】。

### `faceBdry` 边界 ID 与方向的流向

- `faceBdry` 的 loop ID → `face_bdry[index]` →（`make_sim_model`）`edgesOnLoop.at(loopID)` → `faceEdges`/`faceDirs`（`edgeDir` 由 `outerLoop` 判定）→ `GR_createFace` → geometric model face → `save_multi_rgn_model` 写 face↔loop【生成端确认】。
- **方向数据**：`edgeDir`（0/1）进入 Simmetrix face 构造；model 文本 Writer（`save_multi_rgn_model`）写 face 的 loop ID 列表，**是否逐 edge 写方向号**需核对第 8 节字段——`save_model`/`save_multi_rgn_model` 写 edge 时记录 `vtx.first/vtx.second`（隐含方向），curve 段写 order/knots/ctrlPts，未见显式 per-edge 正负号列——**model 文本以 vtx 顺序 + loop 顺序隐含方向**，非独立符号列【生成端确认】。

---

## 7. curve 类型与方向

源文件：`include/m3dc1_model.h`、`include/Expression.h`、`include/BSpline.h`、生成端 `m3dc1_model.cc`。

1. **curve 类型枚举**：`enum curveType{LIN=1, POLY, BSPLINE, OTHER}`（`m3dc1_model.h`）【生成端确认】。
2. **各类型参数**：
   - `LIN`：`attach_linear_curve` → 内部转 `attach_polynomial_curve`（order=2，4 个系数），`edgeType=LIN`；Writer 中 `LIN` 段无额外参数（仅 vtx）【生成端确认】。
   - `POLY`：`attach_polynomial_curve`，`edgeType=POLY`（order>2）；Writer 时 `POLY` 转 `BSPLINE` 写出（`if(curveType==POLY) curveType=BSPLINE`）【生成端确认】。
   - `BSPLINE`：`attach_b_spline_curve`/`attach_natural_cubic_curve`/`attach_piecewise_linear_curve`/`attach_periodic_cubic_curve`，参数为 `order`、`numPts`、`knots[order+numPts]`、`ctrlPts[2*numPts]`；Writer 写 `order numPts` + knots + ctrlPtsX/Y【生成端确认】。
3. **curve 几何 ↔ topological edge**：一条 `edgeContainer` 记录（start,end vtx）对应一条 topological edge，其几何由 `gmi_add_analytic` 绑定的 `M3DC1::Expression**`（X/Y 两条）表达【生成端确认】。
4. **edge direction 来源**：
   - **曲线参数方向**：`edgeRange[2]={0,1}`（或 `{0,2π}`），`edgePeriodic`（首尾同 vtx 时=1）；
   - **loop/face 中的符号**：`edgeDir`（`make_sim_model`）+ `curveOrientation()` 判定 clockwise → `edgeDir=0/1`；
   - **结论**：方向由**曲线参数方向 + face 构造时的 `edgeDir`（含 `curveOrientation` 顺逆判定）共同决定**【生成端确认】。
5. **接口提供信息**：`Expression::eval/evalFirstDeriv/evalSecondDeriv`；`M3DC1::evalCoord`（坐标）、`evalNormalVector`（法向）、`evalCurvature`（曲率）；`BSpline::getpara(order, ctrlPts, knots, weight)`（Writer 用）【生成端确认】。
6. **曲线参数是否属于 model 文本**：**是**。`save_model`/`save_multi_rgn_model` 的 BSPLINE 段写出 order/knots/ctrlPts【生成端确认】。
7. **是否必须进入 `Mesh2D`**：curve 参数（BSpline 控制点/节点）由生成端从**边界点列**经 `attach_*_curve` 拟合得到，**可由 M3DC1 model Adapter 从边界点列重新生成**，不必进入通用 `Mesh2D`——此为架构判断，标记【架构候选，非 M3D-C1 强制要求】。

---

## 8. `save_model()` ↔ `load_model()` 字段对照

生成端 Writer：`m3dc1_model.cc::save_model`（单区）/`save_multi_rgn_model`（多区）。
消费端 Reader：`m3dc1_scorec/src/m3dc1_model.cc::load_model`。

| 字段/段 | 生成端写（`save_*`）| 消费端读（`load_model`）| 判定 |
|---|---|---|---|
| 头行 `numL sep inner outer vacuum` | `fprintf("%d %d %d %d %d", numL, separatrixLoop, innerWallLoop, outerWallLoop, vacuumLoop)` | `fscanf("%d %d %d %d %d", &numL, &separatrixLoop, &innerWallLoop, &outerWallLoop, &vacuumLoop)` | 【双向确认】 |
| 每 loop 头 `loopID numE` | `fprintf("%d %d", it->first, numE)` | `fscanf("%d %d", &loop, &numE)` | 【双向确认】 |
| loop 上 vtx `vtx x y z` | `fprintf("%d %lf %lf %lf", vtx.first, xyz...)` | `fscanf("%d %lf %lf %lf", &vertex, xyz...)`→`create_vtx` | 【双向确认】 |
| edge 头 `edge begin end type` | `fprintf("%d %d %d %d", edge, vtx.first, vtx.second, curveType)` | `fscanf("%d %d %d %d", &edge,&beginvtx,&endvtx,&edgeType)`→`create_edge` | 【双向确认】 |
| LIN 段 | 无额外参数 | `case LIN: attach_linear_curve` | 【双向确认】 |
| BSPLINE 段 `order numPts knots ctrlPts` | `fprintf("%d %d ",order,numPts)` + knots + ctrlPtsX/Y | `fscanf("%d %d ",&order,&numPts)` + knots + ctrlPts → `attach_b_spline_curve` | 【双向确认】 |
| POLY→BSPLINE 归一 | 写出前 `if(POLY) curveType=BSPLINE` | 读时按 BSPLINE 处理 | 【双向确认】 |
| loop→loopContainer | 写 loop 的 edge 顺序 | `loopContainer[loop].push_back(edges[i])` | 【双向确认】 |
| `numFaces` | `save_multi_rgn_model`: `fprintf("%d", numFaces)` | `fscanf("%d", &numFaces)` | 【双向确认】 |
| 每 face `faceNum numLoops loopIDs` | `fprintf("%d %d ",faceNum,numLoops)` + 循环 `loopID` | `fscanf("%d %d",&faceNumber,&numLoops)` + 循环 `loopNumber`；`make_face_topo(gf, edgeIdsOnFace)` | 【双向确认】 |
| `numFaces==0` 兼容分支 | 旧文件可能无 face 段 | `if(!numFaces)` 回退：对 `1..numL` 各建一 face + 提示"重新用最新 meshgen 生成" | 【消费端确认】（向后兼容）|

### 关键判定

- **字段级逐项对应**：头行、loop、vtx、edge、curve、face↔loop 段**逐字段双向对应**【双向确认】。
- **edge direction 是否被读取使用**：`load_model` 读 `beginvtx/endvtx`（隐含方向），`make_edge_topo(model, gedge, vtx.first, vtx.second)` 使用之；**未见独立"方向符号列"读写**，方向以 vtx 顺序 + loop 顺序 + `make_face_topo` 的 reparam 表达【消费端确认】。
- **多 face 构造**：消费端 `make_face_topo(gf, tagsOfEdgesOnFace)` 用 `add_bdry`/`add_adj`/`gmi_add_analytic_reparam(faceFunction)` 建 face-edge 拓扑；face 由 `numFaces` 段 + loop→edge 展开【消费端确认】。
- **face↔loop 关联保存**：生成端写 face 的 loop ID 列表；消费端读后展开为 `edgeIdsOnFace` 建 face topo【双向确认】。
- **4 类 loop 标记恢复**：`separatrixLoop/innerWallLoop/outerWallLoop/vacuumLoop` 由头行读回（全局标量）【双向确认】。
- **model entity tag 分配**：`create_vtx`/`create_edge` 用**文本中的 ID 直接作为 gmi tag**（`gmi_add_analytic(model, dim, *id, ...)`），**非加载时重新分配**（2D 加载路径）【消费端确认】。
- **ID 偏置/重排/压缩**：2D `load_model` **未见** +1 偏置或重排；但 **3D `create3D`** 中对 tag 做 plane 偏移（`av_org_tag=edgeTag+local_planeid*numV` 等，`set_gent_tag`/`gmi_base_set_tag`）——3D 存在系统性 tag 重编号【消费端确认】。
- **二维维度表达**：model 通过 `gmi_add_analytic(model, 0/1/2, ...)` 建 0/1/2 维实体；`numEntOrig[0..2]` 保存原平面各维计数【消费端确认】。
- **face↔物理材料/控制方程**：`load_model` **未见**将 face 关联到不同材料或方程的字段；4 类 loop 标记是**语义标签**而非"多物理区域方程选择"的直接证据 → **face≠物理区域方程**在当前文件层面【待确认】（需 M4-0C3/C1 层佐证）。

---

## 9. mesh vertex/edge/triangle 分类

源文件：消费端 `m3dc1_entity.cc`、`m3dc1_mesh.cc`、`api/m3dc1_scorec.cc`。

1. **加载后遍历维度**：`m3dc1_mesh::set_mcount` 对 `d=0..3` `mesh->begin(d)` 遍历，设 `local_entid_tag`、`own_partid_tag`；`num_local_ent[d]=mesh->count(d)`【消费端确认】。
2. **数量取得**：`m3dc1_mesh_getnument(ent_dim, num_ent)` → `mesh->count(*ent_dim)`；own/global 分别 `num_own_ent`/`num_global_ent`【消费端确认】。
3. **mesh dimension 检查**：`mesh->count(3)?3:2`（多处，如 `get_ent_global2ndadj`）；2D 加载 `pumi_mesh_create(model,2,false)`【消费端确认】。
4. **triangle→geometric face / edge→geometric edge / vertex→geometric vertex**：统一经 `m3dc1_ent_getgeomclass`（`api/m3dc1_scorec.cc`）：`gmi_ent* gent=(gmi_ent*)mesh->toModel(ent)`；`geom_class_dim=gmi_dim(model,gent)`；`geom_class_id=gmi_tag(model,gent)`【消费端确认】。
5. **`get_ent_gclasdim`**（`m3dc1_entity.cc`）：`gmi_dim(model, toModel(e))` 返回 mesh entity 的 geometric 分类维度【消费端确认】。
6. **内部 mesh edge 分类到 2 维 face、边界 mesh edge 分类到 1 维 model edge、corner vertex 分类到 0 维、曲线内部 vertex 分类到 1 维**：
   - `m3dc1_entity.cc` 的 DEBUG 块用 `get_ent_gclasdim(m,down_e)==ent_dim-1` 判定"边界"下边（`bdry_cnt`），**间接暗示**边界 mesh edge 的 geometric 分类维度 = 网格维度-1；
   - 但**该分类由 `.smb`/MDS 在网格生成/加载时确定**（`toModel` 返回值来自 MDS 存储），当前授权文件**未包含**"内部 edge→2 维、边界 edge→1 维"的显式赋值实现；
   - → **第 7/8/9 项机制来自 PUMI/MDS 与 `.smb` classification**，当前授权源码**不足以逐条证明**，标记【待确认】。
7. **`toModel/gmi_dim/gmi_tag/getMdsIndex/getMdsEntity/global ID` 职责**：
   - `toModel(ent)`：mesh entity → geometric model entity；
   - `gmi_dim/gmi_tag`：取 geometric entity 的维度/tag；
   - `getMdsIndex(mesh,e)`：mesh local ID（MDS 本地索引）；
   - `getMdsEntity(mesh,dim,id)`：由 local ID 取 mesh entity；
   - `get_ent_globalid`：从 `"global_id"` tag 取 mesh global ID【消费端确认】。
8. **local/global/model tag 转换**：三者独立存储（`local_entid_tag`、`"global_id"` tag、几何 `gmi_tag`），**不互相 +1 派生**；`compute_globalid` 用 `PCU_Exscan_Ints` 跨分区前缀和生成 global ID【消费端确认】。
9. **classification 是否被主动使用**：`m3dc1_ent_getgeomclass`、`get_ent_gclasdim` 被调用（如 `m3dc1_mesh_write` 写 `geoId`、3D 判 `gmi_dim==2`）→ **主动读取使用**【消费端确认】。
10. **仅 PUMI 保存、当前路径未显式消费的 classification**：mesh edge/vertex 的**逐条几何分类**在当前授权文件中主要用于 DEBUG 断言与 3D 构造，是否在 2D 主求解路径被 M3D-C1 逐条消费**不足以完全确认**，标记【待确认】。

---

## 10. 外边界与内部界面

1. **外边界表达**：geometric model 中由**最外 loop（`outerLoop()` 判定）对应的 geometric edge 序列**表达；可由**多个 geometric edge 组成**（loop = edge 列表）【生成端确认】。
2. **内部界面表达**：由**相邻 face 共享的 geometric edge/loop**表达（`face_bdry` 中同一 loop ID 出现在多个 face 的机制）【生成端确认（机制）】/【待确认（input3 实例）】。
3. **外边界是否多 geometric edge 组成**：**是**（loop 可含多条 edge）【生成端确认】。
4. **一个闭合 loop 是否必对应一个 face**：**否**。一个 face 可由多个 loop 组成（`numLoops>1`，`loopDef[]`），loop 是 face 的边界环，非一一对应【生成端确认】。
5. **face 是否允许孔洞/多 loop**：**允许**（`GR_createFace(..., numLoops, loopDef, ...)`，外环 `edgeDir=1` + 内环 `edgeDir=0`）【生成端确认】。
6. **separatrix 归属**：由生成路径决定——`set_separatrix` 设 `separatrixLoop`（一个 loop ID），是**语义标签**；它是外边界/内部界面取决于该 loop 在 face_bdry 中的角色，**不由标记本身唯一决定**【生成端确认（标记机制）】/【待确认（角色）】。
7. **first/inner/outer wall、vacuum boundary 本质**：均为 **loop ID 的语义标签**（`innerWallLoop`/`outerWallLoop`/`vacuumLoop` 全局标量），底层是 geometric loop（进而是 geometric edge 集合），**非独立几何类型**【生成端确认】。
8. **是否需要每条边界方向**：face 构造需要（`edgeDir`/`curveOrientation`）；model 文本以 vtx 顺序 + loop 顺序隐含方向【生成端确认】。
9. **边界起点是否需稳定**：`get_multi_rgn`/`inner_outer_wall_pts` 对点列做首尾闭合处理（`if(fabs(first-last)>1e-16) 补末点`），起点由点列顺序决定；**是否要求跨运行稳定**源码未显式约束，标记【待确认】。
10. **重采样后保留 geometric edge 分段**：这是 LinkMesh/OFT 侧问题，当前 meshgen/m3dc1 参考代码**未直接涉及 LinkMesh 的重采样**，仅作**架构问题**列出，**不写成已确认实现**【架构问题，非实现】。

---

## 11. 编号和索引体系表

| 编号 | 起点 | 连续 | 允许负号表方向 | 写入 model 文本 | 写入 `.smb` | 加载端重生成 | 物理标签 | 可直接互映 | 依据 |
|---|---|---|---|---|---|---|---|---|---|
| 输入 boundary/loop ID | 输入给定（`loopNumber`）| 否（由输入定）| 否 | 是（loop 头）| 否 | 否（直用）| 否 | 与 model tag 直接对应（2D）| `multi_meshgen.cc` `loopsMap`；`save_multi_rgn_model` |
| face ID | 1 起（`faceNum=i+1`）| 是 | 否 | 是（`numFaces` 段）| 否 | 否 | 否（几何 face）| — | `save_multi_rgn_model` |
| loop ID | 输入给定 | 否 | 否 | 是 | 否 | 否 | 否 | ↔ boundary ID | `create_loop` |
| edge ID | 调用给定（`ge1_id` 等）| 否 | **是**（`F_edgeDir` 写 `-ID`；face dir）| 是（edge 头）| 否 | 否（2D 直用）| 否 | ↔ gmi edge tag（2D）| `create_edge`；生成端 `write` 中 `if(!F_edgeDir) ID=-ID` |
| vertex/point ID | 调用给定（`gv1_id=1`）| 否 | 否 | 是（vtx 行）| 否 | 否 | 否 | ↔ gmi vertex tag（2D）| `create_vtx` |
| geometric model tag | = 文本 ID（2D）| 依输入 | 否 | 是（隐含=ID）| 否（几何在 model，非 mesh）| 2D 否 / **3D 是（plane 偏移）** | 否 | 2D 直等文本 ID | `gmi_add_analytic(...,*id,...)`；3D `set_gent_tag` |
| mesh local ID (MDS) | 0 起 | 是 | 否 | 否 | 是（MDS 顺序）| 是（加载即定）| 否 | 与 global/tag 独立 | `getMdsIndex`；`local_entid_tag` |
| mesh global ID | 前缀和（`PCU_Exscan_Ints`）| 分区内连续 | 否 | 否 | 由 `compute_globalid` 生成/或存 tag | 是（`compute_globalid`）| 否 | 与 local 独立 | `m3dc1_mesh.cc::compute_globalid` |
| MPI rank/partition ID | 0 起 | 是 | 否 | 否 | 分区文件名含 rank | 是（运行期）| 否 | 与实体编号独立 | `m3dc1_mesh_load` 分区文件名 |
| `Mesh2D.region_ids` | LinkMesh 定 | LinkMesh 定 | 否 | 否（LinkMesh 侧）| 否 | — | **是（三角形物理区域标签）**| **与 model face tag 无直接源码证据的映射** | LinkMesh 侧，本轮无 M3D-C1 侧直接证据 |

- **关键约束**：不得对所有 ID 统一 `+1`。edge 方向以 **`F_edgeDir`/`edgeDir` 的 0/1 或 `-ID`** 表达（生成端 `write`），非全局符号规则【生成端确认】。
- **`region_ids` ↔ model face tag**：**无直接源码证据**证明二者一一映射，标记【待确认】。

---

## 12. 单区域与多区域证据

| 项 | 单区域 (`m3dc1_meshgen.cc`/`analytic-input`) | 多区域 (`multi_meshgen.cc`/`input3`) | 判定 |
|---|---|---|---|
| 处理输入模式 | `modelType`+`vacuumParams` 参数化/分段 | `numBdry`+多 `bdryFile`+`numFace`+`faceBdry` | 【生成端确认】 |
| 是否可多 loop | 是（modelType 1-4 有 inner/outer wall）| 是（多 bdryFile + 多 face）| 【生成端确认】 |
| 如何创建多 face | 单区通常 1 face | `make_sim_model` 依 `face_bdry` 建多 face | 【生成端确认】 |
| 多能力本质 | 多 loop（几何）| **多 geometric face（多 loop）**，非已证多物理方程区域 | 【生成端确认 / 多物理待确认】 |
| 是否同一 Writer | 单区 `save_model`；多区 `save_multi_rgn_model` | 两者不同函数，但同 `.txt` 家族 | 【生成端确认】 |
| 产出文件类别 | `.txt/.smd/.dmg/.smb` | 同 | 【生成端确认（M4-0C1 已核）】 |
| mesh-size 语义 | per-face `meshSizes[]` | per-loop `loopSizeMap` + per-face `faceSizeMap` | 语义相近但键不同：单区按 face，多区按 loop+face【生成端确认】 |

- **必须分开表述**：**"多 geometric face model"**（已确认）与 **"多物理区域模拟"**（待确认，无当前文件直接证据）。

---

## 13. 对 LinkMesh 输入架构的影响

仅基于本轮确认事实：

1. **多 face model ↔ `nested_three_region`**：M3DC1 多 face 是几何多 face（多 loop），与 LinkMesh `nested_three_region` 的**几何嵌套**结构上可对应，但**物理方程区域对应**无直接证据 → **不得直接等同**【待确认】。
2. **`Mesh2D.region_ids` 是否足以构造 model**：**不足**。构造 M3DC1 geometric model 还需 **loop（有序边界环）+ face↔loop 拓扑 + edge 分段 + 方向**，`region_ids`（每三角形标签）不含边界环有序性【待确认→倾向不足】。
3. **是否需要边界 segment→model edge 分类**：**需要**。geometric model edge 是分段的（loop=多 edge），需 LinkMesh 提供边界 segment 到 model edge 的划分【生成端确认（M3DC1 侧需要）】。
4. **是否需保留 geometric vertex/edge/face tag**：2D 加载 tag 直接来自 model 文本 ID，故**生成 model 文本时需分配稳定 vertex/edge/face/loop ID**【生成端确认】。
5. **可从 `nodes+triangles+boundary_segments+region_ids` 确定性派生**：网格实体（vertex/edge/triangle）与其**是否在边界**可派生；边界点列可派生 curve 拟合输入。
6. **不能可靠反推**：**geometric loop 的有序性、face↔loop 归属、edge 方向、per-loop/per-face 语义标签（inner/outer/vacuum/separatrix）** 无法仅从三角形标签可靠反推 → 需显式提供【待确认→倾向需显式】。
7. **不可反推信息去向**：倾向进入 **M3DC1 model Adapter 的输入对象**，而非污染通用 `Mesh2D`——**架构决策，本轮不定稿**。
8. **`single_region` 是否能构造最小 model**：结构上单 loop→单 face 可构成最小 model（对应单区域路径 `createVacuum` 单 loop），**技术上可构造**，但**非 M3D-C1 已正式要求**【技术可构造，非强制】。
9. **四类边界来源能否进入同一最小单 face model**：`lcfs`/`flux_surface`/`first_wall`/`array_file` 若都归一化为一条有序外边界点列，则均可作为单 loop 输入——**技术上可行**，但**是否允许由 target/profile 兼容矩阵决定**，非本轮裁定【架构候选】。
10. **仅 LinkMesh 候选、未经 M3D-C1 消费端证明**：`lcfs`/`flux_surface`/`first_wall`/`array_file` 四类来源**均未在 M3D-C1 消费端源码中直接出现**，属 LinkMesh 输入能力，非 M3D-C1 直接要求【待确认】。

---

## 14. 对 Mesh2D 和 M3DC1 Adapter 边界的影响

1. **不新增 `Mesh2D` 字段**：本轮仍**未发现**必须持久化且无法从现有数据反推、且被 M3D-C1 消费端直接要求的跨 Writer 规范数据 → **不提出** `Mesh2D` 新字段。
2. **倾向 Adapter 输入对象承载**：geometric loop 有序性、face↔loop、edge 方向、语义标签，倾向由 **M3DC1 model Adapter** 从 `boundary_segments`/`region_ids`/边界来源组织，而非通用 `Mesh2D`——**架构候选，M4-0E 裁定**。
3. **curve 拟合非 Mesh2D 职责**：BSpline 控制点/节点由 Adapter 从边界点列生成，`Mesh2D` 只需提供有序边界点列与分段信息【架构候选】。

---

## 15. 与 TRIMEG `Rbc/Zbc` 的职责隔离

- TRIMEG `Rbc/Zbc` 仍表示 TRIMEG 输出计算域进入 Triangle 前的**有序离散外边界**，格式契约不变。
- 提交 `71fe09f` 错误固定保存人工矩形四角点，**尚未修复**，本轮不处理。
- M3DC1 geometric model edge/loop/classification **不得改写** `Rbc/Zbc` 格式契约。
- `lcfs`/`flux_surface`/`first_wall`/`array_file` 最终**可能**归一化为 `Mesh2D.outer_boundary`（对应 TRIMEG 单条有序边界），**是否允许由 target/profile 兼容矩阵决定**。
- **关键差异**：M3DC1 需要**分段 geometric edges + face↔loop 拓扑 + edge 方向**，比 TRIMEG **单条有序 `outer_boundary`** 需要更多拓扑信息。
- 本轮**只识别差异**，**不提出** HDF5 Writer 修改。

---

## 16. 已确认事项

- 【生成端确认】`input3` 由 `multi_meshgen.cc`（`m3dc1_mfmgen`）解析；关键字循环、非顺序；字段表（第 5 节）。
- 【生成端确认】model 拓扑 vertex→edge→loop→face；face 可多 loop；外/内环以 `edgeDir` + `outerLoop` 区分；ID 由调用方给定；curve 类型 LIN/POLY/BSPLINE 及参数；曲线参数写入 model 文本。
- 【双向确认】`save_model`/`save_multi_rgn_model` ↔ `load_model` 头行/loop/vtx/edge/curve/face↔loop 逐字段对应；4 类 loop 标记恢复；POLY→BSPLINE 归一。
- 【消费端确认】2D tag = 文本 ID（不重编号）；3D 存在 plane 偏移重编号；`m3dc1_ent_getgeomclass` 用 `toModel+gmi_dim/gmi_tag`；local/global/model tag 三体系独立；`compute_globalid` 前缀和；mesh dimension 2/3 检查。
- 【消费端确认】mesh 遍历 0..3 维、计数 API、classification 被主动读取用于写 `geoId` 与 3D 判定。

## 17. 未确认事项【待确认】

- 多区域越界/重复 face/非法 loop ID 的显式校验（源码仅末尾 `assert(numBdry==...)`）。
- `input3` 实例中相邻 face 是否真的共享 geometric edge（需读点列与 face_bdry 数值）。
- mesh **内部 edge→2 维 face / 边界 edge→1 维 model edge / corner vertex→0 维 / 曲线内部 vertex→1 维** 的**显式分类实现**（由 `.smb`/MDS/SCOREC/core 决定，当前文件仅 DEBUG 断言间接暗示）。
- 2D 主求解路径是否逐条消费 mesh edge/vertex 的几何分类。
- `separatrix` 是外边界/内部界面/独立标记的**具体角色**（取决于 face_bdry 数值）。
- 边界起点跨运行稳定性要求。
- **face ↔ 不同物理材料/控制方程**的直接证据（需 C1/field 层）。
- `Mesh2D.region_ids` ↔ model face tag 的映射关系。
- `lcfs`/`flux_surface`/`first_wall`/`array_file` 四类来源被 M3D-C1 消费端直接要求的证据。
- `.dmg` 是否为 M3D-C1 运行时必需输入（M4-0C1 遗留，仍未确认）。

## 18. M4-0C3 最小文件申请（≤10）

围绕 C1 field 创建 / 六自由度 / 高阶节点 / shape·basis / edge orientation / `.smb` 是否预存 field / 加载后 field 初始化。

| # | 完整路径 | 当前调用点指向 | 要确认的问题 | 为何现有文件不足 |
|---|---|---|---|---|
| 1 | `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_field.h` | `m3dc1_mesh.h` 的 `field_container`；`m3dc1_scorec.cc` `m3dc1_field_create` | field 六自由度/value_type/dof_per_value 结构 | 仅有摘要，未见完整字段定义 |
| 2 | `extracted/m3dc1_scorec/m3dc1_scorec/api/m3dc1_scorec.cc`（field 段复核 `createPackedField`）| `m3dc1_field_create`→`createPackedField(mesh, name, components)` | 每节点 dof 数（C1TRIDOFNODE=6）如何决定；是否高阶节点 | 已读但需聚焦 field 创建段核对 dof 布局 |
| 3 | `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_slnTransfer.h` | `m3dc1_scorec.cc` `ReducedQuinticTransfer`；`onVertex` | C1 解转移是否依赖高阶/边自由度 | 决定 field 是否绑定 edge orientation |
| 4 | `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_slnTransfer.cc` | `onVertex`（`m3dc1_slnTransfer.cc:22`）| C1 field 在 vertex/edge 的 dof 组织 | 只有声明不足以确认 dof 归属 |
| 5 | `extracted/meshgen/meshgen/fortran/c1_12_element.F90` | 索引 `c1_12_element.F90` `dofs_per_element`/`normal_edges`/`sig_edges` | 12 自由度单元、边法向/符号、edge orientation 依赖 | 唯一直接描述 C1 单元边方向的文件 |
| 6 | `extracted/m3dc1_scorec/m3dc1_scorec/include/slntransferUtil.h` | `slntransferUtil.cc:22`「set the longest edge as xi axis」 | 边方向/局部坐标如何选取（edge orientation）| 需确认 edge orientation 是否影响 mesh 输入 |
| 7 | `extracted/m3dc1_scorec/m3dc1_scorec/src/m3dc1_mesh.cc`（field 相关段复核 `update_field`）| `build3d(num_field, field_id, num_dofs_per_value)`；`update_field` | `.smb` 加载后 field 是否需重建/预存 | 需聚焦 field 与网格加载耦合段 |
| 8 | `extracted/m3dc1_scorec/m3dc1_scorec/include/ReducedQuinticImplicit.h`（若存在且为文本）| `m3dc1_scorec.cc` `ReducedQuinticImplicit shape` | 高阶 shape/basis 是否需要几何/边方向输入 | 现有文件只用不声明 shape 契约 |
| 9 | `extracted/meshgen/meshgen/fortran/explicit_element.F90` | 索引 `explicit_element.F90` `boundary_info`/`dedge_dx` | 单元边界信息与边导数，佐证 edge orientation | 与 #5 互补，确认边方向来源 |
| 10 | `extracted/m3dc1_scorec/m3dc1_scorec/include/m3dc1_sizeField.h`（field→size 段）| `SizeFieldError`/`setSizeFieldOnVertex` | field 是否在加载后立即初始化并驱动 size | 判断 field 初始化时机 |

> 不申请任何目录、整个 M3DC1 仓库或整个 SCOREC/core。如确需 SCOREC/core，仅在明确版本下申请单个头/实现文件并说明版本阻塞（当前 SCOREC 版本未确认，故本轮不申请 core 文件）。

---

## 19. 完成声明

- 本轮只修改 `report.md`。
- 未修改 LinkMesh 源码、测试、`LinkMesh_Architecture_Plan.md`、`History.md` 或 `CONTEXT.md`。
- 未修改老师提供的 `meshgen`/`m3dc1_scorec` 参考源码和索引。
- 未创建除 `report.md` 外的任何文件。
- 未编译或运行 meshgen、M3D-C1、SCOREC、PUMI、Simmetrix、MPI 或 Fortran。
- 未读取高密度数值模型或二进制文件（未读 `.smb`/`.sms`/`.dmg`/`.smd`/VTK/对象/库/可执行/`input3.txt` 点列本体）。
- 未解析 `.smb` 字节流。
- 未实施 `.smb`、PUMI、model Writer、C1、配置或 CLI 代码。
- 未修复提交 `71fe09f`。
- TRIMEG `Rbc/Zbc` 数据来源问题仍保留到 M4-0E 蓝图固化后处理。
