# LinkMesh M4-0C3 C1、边界数据与多 Face 界面兼容性只读侦察报告

> 本报告为 M4 前置只读源码侦察第三轮。回答核心问题：OFT/Triangle 生成的共形线性三角网格经 geometric classification 后，是否足以作为 M3D-C1 C1 有限元的初始静态网格；M3D-C1 是否要求 LinkMesh 在边界或多 face 界面预挂载 OFT/`Mesh2D` 当前不含的特殊数据。所有结论标注 `[meshgen]`（生成端）或 `[m3dc1_scorec]`（消费端），同名文件分别报告。未实现任何 `.smb`、PUMI、model Writer、C1、配置或 CLI。

---

## 1. 执行摘要

- **C1 自由度**：`C1TRIDOFNODE=6`（`[m3dc1_scorec] api/m3dc1_scorec.h`）是**每 mesh vertex 的 6 个数值场分量**（value、d/dR、d/dZ、d²/dR²、d²/dRdZ、d²/dZ²），由 `[meshgen]`/`[m3dc1_scorec]` 的 `explicit_element.F90::eval_field`（dofs(18)=3 vertex×6）与 `ReducedQuinticImplicit::rotateDof`（6 分量旋转）双向印证。**是 field component（数值场自由度），不是 6 个 mesh vertex，也不是高阶几何节点**【双向确认】。
- **field 创建时机**：`.smb` 加载**后**由 `m3dc1_field_create`→`createPackedField` 创建，component 数 `= num_values*(scalar_type+1)*num_dofs_per_value`（`[m3dc1_scorec] api/m3dc1_scorec.cc`）【消费端确认】。
- **初始 `.smb` 是否需预存 C1 field**：**否**。`m3dc1_mesh_load`（`[m3dc1_scorec] api/m3dc1_scorec.cc`）**主动删除** `.smb` 自带的所有 field 与 numbering，仅**保留 `norm_curv` tag**。C1 field 由加载后 API 创建 → **初始 `.smb` 只需基础网格拓扑 + geometric classification**【消费端确认】。
- **高阶节点**：C1 高阶性来自 **ReducedQuintic 在基础线性三角形上的数值基函数**（`[m3dc1_scorec] ReducedQuinticImplicit.cc` 的 20 项五次多项式），**非额外 mesh vertex/edge node**。`Mesh2D.nodes` **无需**扩展为高阶节点表；Triangle 一阶三角形满足基础 topology 要求【消费端确认 / 一般理论辅证】。
- **edge orientation / 法向符号**：`normal_edges`、`sig_edges`（`[meshgen]/[m3dc1_scorec] c1_12_element.F90`）在 `set_element_coord` 中**由 triangle 顶点坐标运行时计算**，`sig_edges` 依 `is_bounary_edges` 与出法向点积确定；`ReducedQuinticImplicit` 在 `slntransferUtil.cc` 中"以最长边为 xi 轴"运行时选局部坐标 → **edge orientation 与法向符号运行时派生，无需 `.smb` 预存独立 orientation 数据**【消费端确认】。
- **外边界额外数据**：`norm_curv` tag 若存在则被 `.smb` 保留并被 `m3dc1_node_getnormvec/getcurv` 读取；**但若不存在则加载后由 geometric model（`gmi_analytic_data`/`evalNormalVector`/`evalCurvature`）计算** → 边界法向/曲率**可预存亦可派生，非强制预存**【消费端确认】。边界条件识别经 **geometric model tag/dimension**（`toModel`+`gmi_dim/gmi_tag`），非独立边界 field【消费端确认】。
- **多 face 界面**：当前授权源码**未出现** C1 跨 face 的 jump condition / constraint matrix / mortar / Lagrange multiplier / interface DOF duplication 的直接实现证据。相邻 face 共享 mesh edge/vertex → C1 field 在共享实体上为**单份全局 DOF**（`createPackedField` 挂 vertex，共享 vertex 唯一）【消费端确认（DOF 唯一性）】/【待确认（是否存在界面特殊处理）】。
- **兼容性裁决**：**【条件兼容，仍有待确认项】**。OFT 线性三角网格 + geometric classification + boundary segments **在当前证据下足以作为初始静态网格**；缺失信息（edge orientation、法向、曲率、C1 field）均**加载后派生或创建**。**待确认项**集中在多 face 界面是否有物理方程分区与特殊 C1 处理（需 M3D-C1 物理主程序，超出当前网格库）。
- **项目边界**：TRIMEG `Rbc/Zbc` 契约不变；`71fe09f` 仍暂停；不为 M3D-C1 改动 TRIMEG Writer。

---

## 2. 已读和跳过文件

### 已读（授权，纯文本源码）

| 文件路径 | 归属 | 用途 |
|---|---|---|
| `api/m3dc1_scorec.cc` | [m3dc1_scorec] | field 创建、mesh load、field 删除/保留、normvec/curv、geomclass |
| `api/m3dc1_scorec.h` | [m3dc1_scorec] | `C1TRIDOFNODE=6`、field/mesh API 声明 |
| `src/m3dc1_field.cc` | [m3dc1_scorec] | `group_complex_dof`、`synchronize_field` |
| `include/m3dc1_field.h` | [m3dc1_scorec] | `m3dc1_field` 类（num_value/value_type/dof_per_value）|
| `src/m3dc1_mesh.cc` | [m3dc1_scorec] | mesh load 后清理、`build3d`、`update_field`、`set_node_adj_tag` |
| `include/m3dc1_mesh.h` | [m3dc1_scorec] | mesh 类字段、tag 声明 |
| `src/m3dc1_entity.cc` | [m3dc1_scorec] | classification 维度、ownership、global adj |
| `src/m3dc1_model.cc` | [m3dc1_scorec] | `evalNormalVector`/`evalCurvature`、geometry |
| `include/m3dc1_model.h` | [m3dc1_scorec] | model 接口 |
| `src/m3dc1_slnTransfer.cc` | [m3dc1_scorec] | `onVertex` C1 解转移 |
| `include/m3dc1_slnTransfer.h` | [m3dc1_scorec] | `ReducedQuinticTransfer`、`dofNode=C1TRIDOFNODE` |
| `src/slntransferUtil.cc` | [m3dc1_scorec] | `evalGeoPara`/`reorder`（最长边为 xi 轴）|
| `include/slntransferUtil.h` | [m3dc1_scorec] | geo para 接口 |
| `src/ReducedQuinticImplicit.cc` | [m3dc1_scorec] | 20 项五次基、`calcuCoeffs`、`rotateDof`、`eval_l` |
| `include/ReducedQuinticImplicit.h` | [m3dc1_scorec] | ReducedQuintic 隐式接口 |
| `include/ReducedQuintic.h` | [m3dc1_scorec] | 抽象基类 |
| `fortran/c1_12_element.F90` | [m3dc1_scorec] | 12 自由度单元、`normal_edges`/`sig_edges`、`eval_basis_function` |
| `fortran/explicit_element.F90` | [m3dc1_scorec] | 18 dof、`glb_dof_2_loc`、`eval_field` |
| `fortran/explicit_element_interface.F90` | [m3dc1_scorec] | Fortran↔C 接口 |
| `fortran/c1_12_element.F90` | [meshgen] | 同名，12 自由度单元（与消费端逐行一致，见 §3.6）|
| `fortran/explicit_element.F90` | [meshgen] | 同名，18 dof（与消费端一致）|
| `fortran/explicit_element_interface.F90` | [meshgen] | 同名接口 |
| `src/ReducedQuinticExplicit.cc` | [meshgen] | **仅生成端存在**，Fortran 桥接 explicit element |
| `include/ReducedQuinticExplicit.h` | [meshgen] | **仅生成端存在** |
| `src/ReducedQuinticImplicit.cc` | [meshgen] | 同名，五次隐式（与消费端近似，见 §3.7）|
| `include/ReducedQuinticImplicit.h` | [meshgen] | 同名接口 |
| `include/ReducedQuintic.h` | [meshgen] | 同名抽象基类 |

### 路径存在性说明

- `ReducedQuinticExplicit.cc`/`.h` **仅存在于 `[meshgen]`**，`[m3dc1_scorec]` 无此文件（不合并、不替换路径）【确认】。
- 未申请生成端 `include/m3dc1_mesh.h` 之外的路径；`[meshgen] include/m3dc1_mesh.h` 存在但本轮 C1 调用链未强依赖，仅在 §7 引用其 field 声明差异【确认】。

### 跳过（未授权 / 二进制 / 需运行）

- `.smb`/`.sms`/`.dmg`/`.smd`/VTK/对象/库/可执行/build。
- SCOREC/core 的 `apf`/`mds`/`gmi`/`pcu` 实现（`createPackedField`/`changeMeshShape`/`toModel` 底层）。
- M3D-C1 物理主程序（不在网格库内，多 face 方程分区无法从当前库证明）。

---

## 3. C1 自由度定义

### 3.1 每三角形局部自由度

- `[m3dc1_scorec]/[meshgen] explicit_element.F90::eval_field`：`dofs(18)`，`do counter=1,18` → **每三角形 18 个 local element DOF**【双向确认】。
- `[m3dc1_scorec]/[meshgen] c1_12_element.F90`：`dofs_per_tri=12`，`dofs_per_element=nodes_per_element*(dofs_per_node+pol_dofs_per_edge)`；`idx_node/idx_loc` 表明 **9 个顶点 dof（3 vertex×3）+ 3 个 edge normal dof** → **另一套 12 自由度 C1 单元**【双向确认】。
- **两套单元并存**：`explicit_element`（18 dof，reduced quintic，每 vertex 6）与 `c1_12_element`（12 dof，每 vertex 3 + 每 edge 1 法向）。消费端主 solution-transfer 路径用 **18 dof / 每 vertex 6**（`slnTransfer` 的 `dofNode=C1TRIDOFNODE=6`）【消费端确认】。

### 3.2 每顶点自由度

- `explicit_element.F90::glb_dof_2_loc`：每 `inode` 处理 `start_idx..start_idx+5`（6 个）→ **每 vertex 6 dof**【双向确认】。
- `C1TRIDOFNODE=6`（`[m3dc1_scorec] api/m3dc1_scorec.h`）【消费端确认】。

### 3.3 六个顶点自由度的含义

- `explicit_element.F90::glb_dof_2_loc` 逐 dof 变换：`start_idx`=field value；`+1,+2`=一阶导（对两条边方向，等价 d/dR、d/dZ）；`+3,+4,+5`=二阶导（dR²、dRdZ、dZ²）【双向确认】。
- `ReducedQuinticImplicit::rotateDof`（`[m3dc1_scorec]`）：`dofs_r[0]`=值；`[1],[2]`=一阶旋转；`[3],[4],[5]`=二阶旋转 → **6 = {value, ∂R, ∂Z, ∂RR, ∂RZ, ∂ZZ}**【双向确认】。
- **结论**：6 个是**数值场分量（field component / global field DOF）**，对应函数值 + R/Z 一阶 + 三个二阶导，**非几何节点**【双向确认】。

### 3.4 edge 内部自由度

- 18-dof reduced quintic 路径（`explicit_element`）：**无独立 edge DOF**，全部归属 3 顶点【消费端确认】。
- 12-dof 路径（`c1_12_element`）：**有 3 个 edge normal dof**（`pol_dofs_per_edge=1`，`idx_loc` 中的 `4,4,4`）→ 每 edge 1 个法向导数自由度【双向确认】。
- **主 transfer 路径（18 dof）不含 edge DOF**；12-dof 路径含 edge 法向 DOF【场景区分确认】。

### 3.5 triangle interior 自由度

- 两套单元均**无 triangle interior DOF**（`explicit_element` 18=3×6；`c1_12_element` 12=9+3）【双向确认】。

### 3.6 `12 element` / `C1TRIDOFNODE=6` / field component 关系

- `c1_12_element.F90` = 12-dof C1 单元（3 vertex×3 + 3 edge×1）【双向确认】。
- `C1TRIDOFNODE=6` = reduced-quintic 每 vertex 6 dof（18-dof 单元）【消费端确认】。
- field component 数 = `num_values*(scalar_type+1)*num_dofs_per_value`；单场实数时 `num_dofs_per_value` 常 =6，故 `countComponents=6`（`m3dc1_field_create`，`[m3dc1_scorec]`）【消费端确认】。
- **三者关系**：`c1_12_element` 与 `explicit_element(18)` 是**两套不同 C1 单元**；消费端 solution-transfer 与 field 默认走 **6/vertex（18-dof reduced quintic）**【消费端确认】。

### 3.7 ReducedQuintic shape 空间

- `[m3dc1_scorec] ReducedQuinticImplicit.cc::calcuCoeffs`：构造 20×20 矩阵（`poly_idx[20][2]` 为 0..5 次单项），`dgesv_` 求 18→20 系数 → **20 项五次多项式空间，由 18 个约束（3 vertex×6）确定**【消费端确认】。
- `[meshgen] ReducedQuinticImplicit.cc`：同名，`eval_l` 中 `beta[20]`、同 `poly_idx`，**差异仅在消费端 `eval_l` 多一处 `coord_poly[20]` 局部变量声明**（未改变数学），其余逐行一致 → **两仓库 ReducedQuinticImplicit 数学等价**【双向确认，差异微小已注明】。
- `[meshgen] ReducedQuinticExplicit.cc`（**仅生成端**）：不自算多项式，转而经 `set_element_coord_i_`/`eval_field_i_` 桥接 Fortran `explicit_element`【生成端确认】。

### 3.8 几何节点还是数值场分量

- 所有 6/18/12 dof 均为 `apf::Field` 的 component（`getComponents/setComponents` 操作），挂 mesh vertex，**是数值场分量，非高阶几何节点**【双向确认】。

---

## 4. APF field 创建时机

源：`[m3dc1_scorec] api/m3dc1_scorec.cc`、`src/m3dc1_field.cc/.h`、`src/m3dc1_mesh.cc`。

1. **`.smb` 加载后删除已有 field**：`m3dc1_mesh_load` 中 master plane 分支 `while(mesh->countFields()){ apf::Field* f=mesh->getField(0); destroyField(f); }`【消费端确认】。
2. **删除 numbering**：`while(mesh->countNumberings()){ destroyNumbering(...); }`【消费端确认】。
3. **保留 tag**：遍历 tags，`if(mesh->findTag("norm_curv")==tags[i]) continue;` 其余 `destroyTag` → **仅 `norm_curv` 保留**【消费端确认】。
4. **C1/物理 field 创建 API**：`m3dc1_field_create(field_id, name, num_values, scalar_type, num_dofs_per_value)`→`createPackedField(mesh, name, components)`→`apf::freeze(f)`【消费端确认】。
5. **创建发生在 mesh load 后**：`m3dc1_field_create` 需 `m3dc1_mesh::instance()->mesh` 已就绪；调用序为 load→create【消费端确认】。
6. **component 数确定**：`components = (*num_values)*(*scalar_type+1)*(*num_dofs_per_value)`【消费端确认】。
7. **field 挂载实体**：`createPackedField` + `setComponents(f, e, 0, ...)` 遍历 `mesh->begin(0)` → **挂 mesh vertex**【消费端确认】。
8. **是否在 edge/triangle 建 field**：主路径 field 操作均 `begin(0)`（vertex）；`ip_field`/`size_field` 为 IP/element field（`createIPField`/element，用于 adaptation），**非初始物理 field**【消费端确认（adaptation 场景）】。
9. **初始 `.smb` 是否必须含 C1 field**：**否**（field 加载后创建，且 load 时删除自带 field）【消费端确认】。
10. **`.smb` 仅需拓扑 + classification**：mesh load 后 `initialize()`→`set_mcount`/`set_node_adj_tag`，classification 经 `toModel`；**未从 `.smb` 读取 C1 field 作为初始必需**【消费端确认】。

---

## 5. 初始 `.smb` 是否包含 field

- **初始静态网格要求**：基础 mesh 拓扑（vertex/edge/triangle）+ geometric classification（`toModel` 可解析）+（可选）`norm_curv` tag。**不含 C1 field**【消费端确认】。
- **restart/adapted mesh**：`m3dc1_mesh_write`（option=1，`.smb`）会临时把 field12 存为 double tag（`createDoubleTag("field12",numDof)`）再 `writeNative`，写后移除 → **adapted/restart `.smb` 可能临时携带 field tag**，但这是**输出侧行为，非初始输入要求**【消费端确认（restart 场景）】。
- **不得反推**：restart 携带 field ≠ 初始 LinkMesh 输出必须写 field。初始 LinkMesh `.smb` **不需要** C1 field【消费端确认】。

---

## 6. 高阶节点

1. **mesh shape 是否线性**：主路径未见对初始网格调用高阶 `changeMeshShape`；field 用 `createPackedField`（packed，DOF 挂 vertex），几何仍线性三角形【消费端确认】。
2. **是否调用 `changeMeshShape()`/高阶 FieldShape/建 edge-triangle node**：主初始路径**未见**；`changeMdsDimension`（2↔3）用于 build3d，**非高阶节点**【消费端确认】。
3. **ReducedQuintic 在线性三角形上定义高阶数值基**：`ReducedQuinticImplicit::eval_l` 在线性三角形几何上求 20 项五次多项式 → **高阶来自数值基函数，非几何**【消费端确认 / 一般理论辅证】。
4. **是否额外 mesh vertex**：无（field DOF ≠ vertex）【消费端确认】。
5. **是否有仅属 field shape 的高阶 node**：18-dof reduced quintic 全挂 vertex（每 vertex 6），**无独立高阶 node 实体**；12-dof 单元的 edge 法向 dof 逻辑上属 edge，但主 transfer 路径不用【消费端确认 / 场景区分】。
6. **`Mesh2D.nodes` 是否需扩展**：**否**。高阶是数值 DOF，非几何节点【消费端确认 → 架构候选：不扩展】。
7. **Triangle 一阶三角形是否满足基础 topology**：满足（基础网格即线性三角形 + 顶点坐标）【消费端确认】。

> SCOREC/core 的 `createPackedField`/`FieldShape` 底层未授权，仅确认**当前程序未对初始网格调用高阶几何 API**，不猜测 core 内部【待确认（core 层）】。

---

## 7. edge orientation 与法向符号

源：`[meshgen]/[m3dc1_scorec] c1_12_element.F90`、`explicit_element.F90`、`[m3dc1_scorec] ReducedQuinticImplicit.cc`、`slntransferUtil.cc`。

1. **三条局部边编号**：`c1_12_element.F90` 注释「edge order: 12 23 31」；`normal_edges(3,2)`【双向确认】。
2. **边方向由何决定**：`set_element_coord` 中由 **triangle 顶点坐标（`dx_dedge`/`dy_dedge`）运行时计算**；`sig_edges` 由 `is_bounary_edges` + `edge32_dot_normal_edge` 出法向点积符号决定【双向确认】。
3. **`normal_edges`/`sig_edges` 含义**：`normal_edges`=各边单位外/一致法向；`sig_edges`= ±1，协调相邻单元共享边法向一致性（内部边比较全局法向取 ±1，边界边强制外法向 -1）【双向确认】。
4. **相邻三角形共享边局部方向协调**：`calcu_normal_edges` 用 `dy_dedge(inode1,inode2)>0` 等**坐标判据**统一法向方向，使相邻单元对同一几何边得到**一致法向** → 运行时坐标派生，不依赖预存 orientation【双向确认】。
5. **法向导数是否需符号翻转**：`sig_edges(iedge)<0` 时 `normal_mid_edge(counter,iedge)=-1*...`（`calcu_normal_mid_edge`）→ **有符号翻转，运行时按 `sig_edges` 施加**【双向确认】。
6. **符号是否运行时由拓扑/坐标计算**：**是**（`set_element_coord` 全程由坐标算）【双向确认】。
7. **是否需 `.smb` 预存 edge orientation**：**否**（运行时派生）【消费端确认】。
8. **是否需 LinkMesh 显式保存 edge orientation**：**否**（可从有向三角形连接 + 顶点坐标派生）【消费端确认 → 架构候选：不保存】。
9. **是否可从有向三角形连接表 + 共享边端点确定性派生**：**是**（`dx_dedge/dy_dedge` 仅需顶点坐标与连接）【消费端确认】。
10. **geometric edge 参数方向是否参与 C1 orientation**：主 C1 element（`c1_12_element`/`explicit_element`）orientation 由 **mesh 顶点坐标**决定，**未见**直接用 geometric curve 参数方向定 C1 法向符号；geometric edge 方向用于 model 拓扑（M4-0C2），非 C1 element 符号【消费端确认 / 待确认（是否间接经 classification 影响边界 element）】。

### 四类方向严格区分

| 概念 | 来源 | 依据 |
|---|---|---|
| geometric curve direction | model 文本 vtx 顺序 + reparam | [meshgen] M4-0C2；本轮未见其定 C1 符号 |
| mesh edge endpoint order | MDS/三角形连接 | `getDownward`（`[m3dc1_scorec]`）|
| triangle local edge orientation | 顶点坐标运行时算 | `set_element_coord`（双向）|
| C1 normal-derivative sign | `sig_edges` 运行时算 | `calcu_normal_edges`（双向）|

- **两仓库同名文件一致性**：`c1_12_element.F90`、`explicit_element.F90`、`explicit_element_interface.F90` 在 `[meshgen]` 与 `[m3dc1_scorec]` **逐行一致**（含 `normal_edges`/`sig_edges`/`glb_dof_2_loc`）→ orientation 逻辑生成端消费端统一【双向确认】。

---

## 8. 外边界额外数据

源：`[m3dc1_scorec] api/m3dc1_scorec.cc`（`m3dc1_node_getnormvec`/`getcurv`）、`src/m3dc1_model.cc`（`evalNormalVector`/`evalCurvature`）、`src/m3dc1_mesh.cc`（tag 保留）。

1. **boundary mesh edge/vertex 是否建额外 tag/field**：主路径边界识别用 classification；`norm_curv` tag 若 `.smb` 自带则保留，否则不强制【消费端确认】。
2. **boundary condition 是否经 geometric model tag/dimension 识别**：**是**。`m3dc1_node_getnormvec`/`isongeombdry` 用 `toModel`+`gmi_dim`（0/1 维=边界）【消费端确认】。
3. **separatrix/inner/outer/vacuum loop 标记是否进入 C1 field 初始化**：当前 field 创建/初始化路径（`m3dc1_field_create`/`assign`）**未见**读取这些 loop 标记；标记属 model 语义（M4-0C2），**未见**直接驱动 C1 field 初始化【消费端确认（未见）/ 待确认（物理主程序）】。
4. **是否为边界节点存 normal/curvature/tangent/derivative constraint**：`m3dc1_node_getnormvec`/`getcurv` **优先读 `norm_curv` tag，缺失则由 geometric model 计算**（`evalNormalVector`/`evalCurvature`）→ **可预存可派生**【消费端确认】。
5. **`norm_curv` 来源/用途/是否必须**：用途=提供边界法向/曲率；来源=生成端可写入或加载后算；**非初始 `.smb` 强制**（缺失走 geometric model 计算分支）【消费端确认】。
6. **边界法向/曲率预存还是加载后算**：**二者皆可**——有 tag 用 tag，无 tag 用 model 计算【消费端确认】。
7. **LinkMesh 是否必须写边界法向/曲率/C1 约束到 `.smb`**：**否**（可由 geometric model 派生，前提是 model 提供解析曲线；若 LinkMesh 只给线性边界点列，则法向/曲率由离散点算或由 model curve 算）【消费端确认 / 待确认（离散 vs 解析 model 的精度契约）】。
8. **边界只依赖 classification 还是独立边界 field**：主路径依赖 **classification + 可选 `norm_curv`**，未见强制独立边界 field【消费端确认】。
9. **哪些是网格输入 vs 求解器初始化结果**：网格输入=拓扑 + classification（+可选 norm_curv）；法向/曲率/C1 field=**加载后计算/初始化结果**【消费端确认】。
10. **OFT `boundary_segments/boundary_markers` 是否足够几何起点**：**是**（提供边界拓扑 + 标记，classification 与法向可据此 + 顶点坐标派生）【消费端确认 → 条件兼容】。

---

## 9. 多 face 界面处理

源：`[m3dc1_scorec] api/m3dc1_scorec.cc`、`src/m3dc1_mesh.cc`、`src/m3dc1_entity.cc`、`src/m3dc1_model.cc`。

1. **相邻 face 是否共享同一 mesh edge/vertex**：共形网格中相邻 face 的 mesh 实体由 MDS 共享（`getBridgeAdjacent`/`getUpward` 依赖共享下位实体）【消费端确认】。
2. **共享实体 C1 field 是否单份全局 DOF**：`createPackedField` 按 mesh vertex 挂 DOF，共享 vertex 唯一 → **单份全局 DOF**【消费端确认】。
3. **是否按 geometric face 建独立 field 副本**：**未见**。field 按整 mesh 创建，非 per-face【消费端确认（未见 per-face 副本）】。
4. **是否存在 interface DOF duplication**：当前授权源码**未见**界面 DOF 复制实现【待确认】。
5. **jump/constraint/mortar/Lagrange multiplier**：当前授权源码（网格库）**未见**任何界面约束矩阵/mortar/乘子实现【待确认（需物理主程序）】。
6. **内部 geometric edge 是否施特殊 BC**：`m3dc1_matrix_setbc`/`setlaplacebc` 按 row（field DOF）设 BC，**未见**按内部 geometric edge 自动施界面 BC 的实现【待确认】。
7. **跨 face 函数值连续**：共享 vertex 单份 DOF **隐含** C0 连续；C1 连续性由 reduced-quintic 基跨单元装配保证（一般理论）→ **值连续由共享 DOF 保证**【消费端确认（DOF 共享）/ 一般理论辅证（C1）】。
8. **跨 face 一阶导连续**：由 reduced-quintic C1 基函数保证（一般理论），**当前库未见针对 face 界面的额外一阶导约束代码**【待确认（程序层）/ 一般理论辅证】。
9. **plasma/vacuum/wall face 是否用不同 field/方程**：当前网格库**未见**per-face 不同 field 或方程分区证据；4 类 loop 标记是 model 语义，方程分区属**物理主程序**（不在本库）【待确认】。
10. **多 face 是否主要用于分类与网格尺寸而非方程分区**：本库证据显示多 face 用于 **geometric classification + per-face/loop mesh size**（M4-0C2 `faceSizeMap`）；**方程分区无本库证据**【消费端确认（分类/尺寸）/ 待确认（方程分区）】。
11. **geometric edge classification 是否改变 C1 shape/assembly**：主 C1 element 用顶点坐标，**未见** classification 改变 shape；边界 element 的 `is_bounary_edges` 影响 `sig_edges`（法向符号），此为 element 级 BC 处理，**非跨 face 界面特殊装配**【消费端确认（sig 受边界影响）/ 待确认（是否经 classification 传入）】。
12. **OFT 共形网格是否满足共享实体要求**：满足（共形三角网格天然共享边界实体）【消费端确认 → 条件兼容】。
13. **是否存在 OFT 无法提供且不可派生的界面数据**：**当前网格库层无此证据**；若存在必为物理主程序需求（超范围）→ **【待确认】不构成本轮网格层阻塞**。

---

## 10. solution transfer / adaptation

源：`[m3dc1_scorec] src/m3dc1_slnTransfer.cc`、`include/m3dc1_slnTransfer.h`、`src/slntransferUtil.cc`、`api/m3dc1_scorec.cc`。

1. **transfer 是否仅用于 adaptation/repartition**：`ReducedQuinticTransfer : ma::SolutionTransfer`，`hasNodesOn` 仅 `dimension==0`；被 `adapt_by_field`/`spr_adapt` 调用 → **仅 adaptation 路径**【消费端确认】。
2. **`onVertex/onEdge/onTriangle`**：仅实现 `onVertex`（`m3dc1_slnTransfer.cc`）；无 `onEdge/onTriangle` → **C1 DOF 挂 vertex，转移在新 vertex 上插值**【消费端确认】。
3. **是否说明 C1 field 挂载实体**：`dofNode=C1TRIDOFNODE=6`，`onVertex` 对每 field 取 3 顶点 dof→`thecase->setDofs`→`eval_g` 在新点求值 → **确认 C1 DOF 挂 vertex（每 vertex 6）**【消费端确认】。
4. **transfer 是否依赖 edge orientation**：`onVertex` 经 `slntransferUtil::evalGeoPara`「最长边为 xi 轴」运行时选局部系（`reorder`），**依赖运行时局部定向而非预存 orientation**【消费端确认】。
5. **transfer 所需信息是否属初始 `.smb`**：所需=顶点坐标 + 现有 field DOF；**不需要初始 `.smb` 预存 transfer 专用数据**【消费端确认】。
6. **OFT 初始静态网格是否需预生成 transfer tag**：**否**（transfer 是 adaptation 运行时行为）【消费端确认】。
7. **adaptation 额外数据不得升级为初始要求**：`ip_field`/`size_field`/`field12` double tag 均 **adaptation/restart 场景**，**不构成**初始 LinkMesh 输出要求【消费端确认（场景限定）】。

---

## 11. OFT/Mesh2D 兼容性矩阵

| 数据项 | M3D-C1 是否需要 | 初始 `.smb` 是否预存 | OFT 当前是否提供 | 能否从 `nodes+triangles+boundary_segments+classification` 派生 | 负责层 | 是否真实不兼容 |
|---|---|---|---|---|---|---|
| 线性 mesh vertices | 是【消费端确认】 | 是 | 是 | — | Mesh2D | 否 |
| triangles | 是【消费端确认】 | 是 | 是 | — | Mesh2D | 否 |
| mesh edges | 是【消费端确认】 | 是（由 MDS 建）| 三角形隐含 | 是（由三角形派生）| PUMI/MDS | 否 |
| triangle adjacency | 是【消费端确认】 | 是（MDS）| 可派生 | 是 | PUMI/MDS | 否 |
| boundary segments | 是【消费端确认】 | 经 classification | 是 | 是 | Mesh2D→Adapter | 否 |
| geometric classification | 是【消费端确认】 | **是（必需）** | 需 Adapter 生成 model+分类 | 部分（需 model 拓扑）| Adapter+PUMI | 条件 |
| model edge segmentation | 是（多 face）【生成端确认】 | 经 model | 否（需 Adapter 组织）| 部分（需边界分段规则）| Adapter | 条件 |
| edge orientation | 否（运行时派生）【消费端确认】 | 否 | — | 是 | M3D-C1 运行时 | 否 |
| boundary normal | 可选【消费端确认】 | 可选(`norm_curv`) | 可派生 | 是（顶点坐标/ model curve）| 运行时或 `norm_curv` | 否 |
| boundary curvature | 可选【消费端确认】 | 可选(`norm_curv`) | 可派生 | 是（离散或 model curve）| 运行时或 `norm_curv` | 否 |
| C1 field components(6/vertex) | 是【消费端确认】 | **否** | — | 加载后创建 | M3D-C1 运行时 | 否 |
| high-order nodes | 否【消费端确认】 | 否 | — | 不需要（数值基）| M3D-C1 shape | 否 |
| interface DOF mapping | 【待确认】 | 【待确认】 | — | 未知 | 物理主程序 | 待确认 |
| field transfer metadata | 否（adaptation）【消费端确认】 | 否 | — | 运行时生成 | M3D-C1 adaptation | 否 |

### 裁决

**【条件兼容，仍有待确认项】**

- OFT 线性三角网格 + boundary segments/markers + Adapter 生成的 geometric model/classification，**在当前网格库证据下足以**作为 M3D-C1 初始静态网格。
- edge orientation、boundary normal/curvature、C1 field 均**加载后派生或创建**，非初始预存强制。
- **待确认项**：多 geometric face 界面是否存在 C1 interface DOF mapping / 方程分区（需 M3D-C1 物理主程序，超当前网格库）；`norm_curv` 在离散边界 vs 解析 model 下的精度契约。
- 证据不足以判定【基础兼容】或【存在阻塞】，故取【条件兼容】。

---

## 12. 数据对象职责分层（候选，不改蓝图）

1. **通用 `Mesh2D` 应含**：线性 vertices、triangles、triangle adjacency、boundary segments、boundary markers、region_ids【架构候选】。
2. **M3DC1 geometric model/Adapter 输入对象应含**：model edge segmentation、face↔loop 拓扑、edge 方向（model 拓扑用）、loop 语义标签（inner/outer/vacuum/separatrix）【架构候选】。
3. **PUMI 依 mesh topology 创建**：mesh edges、adjacency、部分 classification 关联【架构候选】。
4. **M3D-C1 加载后创建**：C1 field（6/vertex）、edge orientation（运行时）、boundary normal/curvature（缺 `norm_curv` 时）、transfer metadata【架构候选】。
5. **是否需 `M3DC1ModelSpec` 等目标专用对象**：**建议候选**——承载 model 拓扑/分段/语义标签，避免污染 `Mesh2D`【架构候选，M4-0E 裁定】。
6. **是否必须扩展 `Mesh2D`**：**当前证据不支持**新增跨 Writer、不可反推、有直接消费证据的字段 → **不建议扩展**【架构候选】。
7. **若建议扩展的门槛**：需同时满足跨 Writer + 不可可靠反推 + 直接消费证据；本轮无一项 C1/边界数据满足（均可派生或加载后创建）。
8. **不污染 TRIMEG Writer**：C1/orientation/多 face 细节**不进入** TRIMEG HDF5【架构候选】。

---

## 13. 对 M4 实现的阻塞项

- **无网格层硬阻塞**：初始 `.smb` 只需拓扑 + classification，OFT 可提供【条件兼容】。
- **待澄清（非阻塞）**：
  1. 多 face 界面 C1 interface DOF / 方程分区（物理主程序层，超网格库）【待确认】；
  2. geometric model 生成路径：LinkMesh 走 `.txt`（analytic model）还是 `.dmg`（M4-0C1 遗留）【待确认】；
  3. `norm_curv` 是否需 LinkMesh 预写（精度/收敛考量）还是全由加载后算【待确认】；
  4. `.smb` 分区（rank/plane）与 group size 在单机初始生成时的最小要求【待确认，M4-0D 核对】。

---

## 14. 与 TRIMEG `Rbc/Zbc` 的隔离

- TRIMEG `Rbc/Zbc` 仍是所选 TRIMEG 计算域进入 Triangle 前的**有序离散外边界**，HDF5 格式不变。
- `71fe09f` 把人工矩形四角固定保存为 `outer_boundary` 的问题**尚未修复**，本轮不处理。
- M3D-C1 的 edge orientation、C1 field、多 face topology **不改变** TRIMEG HDF5 格式与消费契约。
- `Rbc/Zbc` 修复将在 **M4-0E 蓝图固化后返回 M3 complete-11** 实施。
- **不得**为 M3D-C1 直接改动 TRIMEG Writer。

---

## 15. 已确认事项

- 【双向确认】`C1TRIDOFNODE=6` = 每 vertex 6 数值 DOF {value, ∂R, ∂Z, ∂RR, ∂RZ, ∂ZZ}；`explicit_element` 18=3×6；`c1_12_element` 12=9+3。
- 【消费端确认】mesh load 删除自带 field/numbering，仅保留 `norm_curv`；C1 field 加载后由 `createPackedField` 创建，挂 vertex；初始 `.smb` 不含 C1 field。
- 【双向确认】edge orientation / `sig_edges` 法向符号由顶点坐标运行时计算，可从有向三角形连接派生，无需预存。
- 【消费端确认】边界法向/曲率有 `norm_curv` 则读、无则由 geometric model 计算；边界 BC 经 classification 识别。
- 【消费端确认】solution transfer 仅 adaptation，`onVertex` only，DOF 挂 vertex。
- 【双向确认】两仓库 `c1_12_element.F90`/`explicit_element.F90`/接口逐行一致；`ReducedQuinticImplicit` 数学等价（消费端 `eval_l` 多一处未用局部变量声明）；`ReducedQuinticExplicit` 仅 `[meshgen]` 存在。

## 16. 未确认事项【待确认】

- 多 geometric face 是否存在 C1 interface DOF mapping / jump / mortar / Lagrange（当前网格库无实现证据，疑在物理主程序）。
- plasma/vacuum/wall face 是否对应不同 field/控制方程（无本库证据）。
- geometric edge 参数方向是否间接经 classification 影响边界 element C1 符号。
- `norm_curv` 在 LinkMesh 离散边界 vs 解析 model 下的精度/收敛契约。
- 初始 `.smb` geometric model 来源（`.txt` analytic vs `.dmg`）——M4-0C1 遗留。
- `.smb` 分区/plane/group 在单机初始生成的最小契约。
- SCOREC/core（`createPackedField`/`FieldShape`/`toModel` 底层）实现——未授权。

## 17. M4-0D 综合契约建议核对表

1. 汇总 M4-0C1/C2/C3 的【双向确认】项，形成生成端↔消费端契约清单。
2. 确认初始 `.smb` 最小必需 = 拓扑 + classification（+可选 `norm_curv`），据此定义 LinkMesh `.smb` Writer 输出契约。
3. 裁定 geometric model 载体：M3D-C1 model `.txt`（analytic）优先，`.dmg` 待定。
4. 裁定 `M3DC1ModelSpec` / Adapter 输入对象边界（承载 loop/face/segmentation/语义标签）。
5. 明确 `Mesh2D` **不扩展** C1/orientation/法向字段（均派生/加载后创建）。
6. 冻结"多 face = 分类 + 网格尺寸"网格层结论，"方程分区"标记为物理主程序范围、超 LinkMesh 网格输出。
7. 保留 TRIMEG `Rbc/Zbc` 主线，`71fe09f` 修复排入 M4-0E 之后。
8. 汇总 M4-0C3 待确认项，决定是否需最小额外 SCOREC/core 文件（明确版本下单文件）。

---

## 18. 完成声明

- 本轮只修改 `report.md`。
- 未修改 LinkMesh 源码、测试、蓝图、History 或 CONTEXT。
- 未修改老师提供的参考源码和索引。
- 未创建除 `report.md` 外的任何文件。
- 未编译或运行 C/C++/Fortran、M3D-C1、PUMI、SCOREC 或 MPI。
- 未读取或解析 `.smb`/`.dmg`/`.smd`/`.sms`/VTK/对象/库/可执行文件。
- 未实施 `.smb`、PUMI、model Writer、C1 field、配置或 CLI 代码。
- 未修复提交 `71fe09f`。
- TRIMEG `Rbc/Zbc` 数据来源问题仍保留到 M4-0E 后返回 M3 complete-11 处理。
