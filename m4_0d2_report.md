# LinkMesh M4-0D2 M3DC1 TXT Model 与 SMB 轻量验证契约及验收交接报告

> 本轮只设计 M3DC1 TXT model + SMB 输出的验证契约、交接输入、验收步骤与证据回传格式。不生成 `.smb`、不实现验证程序、不运行验证、不修改蓝图或业务源码。所有实际验证结果均标为"待填写"，本报告不代表 LinkMesh 输出已通过验证。

---

## 1. 文档定位

- **性质**：面向唐同学的 M3DC1 TXT model + SMB 轻量验证规范与验收交接设计。
- **唯一产物**：`m4_0d2_report.md`。
- **不产出**：候选 `.txt`/`.smb` 文件、验证程序源码、运行结果、蓝图修改。
- **证据基线**：M4-0C1/C2/C3、M4-0D、M4-0D1 报告 + 最新会议 A 级事实 + 老师 `meshgen`/`m3dc1_scorec` 源码。
- **核心边界**：本轮设计"如何验证"，不产出"验证已通过"。唐同学尚未回传任何实际 PASS/FAIL【会议确认：A 级事实】。

---

## 2. 执行摘要

- **双文件输出契约**：M3DC1 P0 输出 = 配套的 **TXT model file** + **SMB mesh file**【会议确认：A 级事实】。TXT 字段顺序由 `save_model`/`save_multi_rgn_model` ↔ `load_model` 双向源码定义【源码确认：双向证据】；SMB 由 PUMI/APF/MDS 正式 API `writeNative` 写出，**LinkMesh 不实现字节序列化**【会议确认：A 级事实 + 源码确认：双向证据】。
- **责任边界**：刘老师定路线；LinkMesh/Aider 未来生成候选文件与仓库内测试（Level 1）；唐同学负责轻量 load-mesh 验证与可视化（Level 2，尽力 Level 3）；完整 M3D-C1 端到端为 Level 4，不由轻量 loader 替代【会议确认：A 级事实 + 验证设计】。
- **四级验收**：Level 1（TXT 静态结构）/ Level 2（SMB 轻量加载）/ Level 3（TXT+SMB 配套加载）/ Level 4（完整 M3D-C1）——**不得混写**。M4 P0 Writer 完成至少需 Level 1+2+3【验证设计】。
- **文件命名**：静态源码显示 `m3dc1_mesh_load` 对 `foo.smb` 插 rank 查 `foo0.smb`【源码确认：消费端证据】；**实际运行行为待唐同学验证**【待唐同学实际验证】。
- **版本**：SCOREC/PUMI 版本仍未确认，唐同学 loader **必须与生成端同版本**；版本证据需回传【待 SCOREC/PUMI 版本确认】。
- **M4-0E 进入条件**：D2 只要形成明确、可执行、可复现的验证契约即可进入 M4-0E；不要求在无 LinkMesh M4 输出时提前获得实际 PASS。蓝图须把 Level 1–3 写入 M4 验收条件；**M4 未经 Level 2/3 验证不得标 PASSED**【验证设计】。
- **项目边界**：TRIMEG `Rbc/Zbc` 契约不变；`71fe09f` 仍暂停；M4-0E 后先返回 M3 complete-11【会议确认：A 级事实】。

---

## 3. 最新会议 A 级事实

以下由刘老师最新会议确认，与旧报告推断冲突时以此为准：

| # | A 级事实 | 对本轮影响 |
|---|---|---|
| 1 | LinkMesh 不得手工解析/拼接 SMB 二进制 | SMB 验证不涉及字节级 |
| 2 | LinkMesh 直接调 PUMI C/C++ 接口 | Adapter 用正式 API |
| 3 | 顶点/三角形/classified mesh 信息录入 PUMI 内存网格，由 PUMI 生成 SMB | SMB 生产者=PUMI |
| 4 | M3DC1 运行需 SMB + TXT model 两类配套文件 | 双文件契约 |
| 5 | SMB 至少含全量顶点与三角形；不得断言仅此两类 | classification 按源码处理 |
| 6 | TXT model 至少含边界点 ID、坐标及恢复 geometric model 所需信息 | TXT 非纯 CSV |
| 7 | TXT 完整字段以 `save_model/save_multi_rgn_model/load_model` 双向证据为准 | 不缩减为两列点表 |
| 8 | 唐同学开发/编译只含 load-mesh 子功能的轻量验证程序 | Level 2 责任人 |
| 9 | 第一轮格式验证不要求完整 M3DC1 依赖 | Level 2 轻量 |
| 10 | LinkMesh 生成候选后由唐同学做格式合法性 + 可视化 | 交接闭环 |
| 11 | 当前只确认验证责任与路线，唐同学未回传结果 | 无实际 PASS |
| 12 | User 已接受 M4-0D 全部架构建议 | 不重议 |

---

## 4. 已读与跳过文件

### 已读（授权，纯文本源码）

| 文件 | 归属 | 用途 |
|---|---|---|
| `src/m3dc1_model.cc` | [meshgen] | `save_model`/`save_multi_rgn_model` 字段写出顺序 |
| `src/m3dc1_model.cc` | [m3dc1_scorec] | `load_model` 字段读取顺序、`make_face_topo` |
| `include/m3dc1_model.h` | 两端 | model 接口、`curveType` 枚举 |
| `include/BSpline.h` | [meshgen] | BSPLINE order/ctrlPts/knots |
| `api/m3dc1_scorec.cc` | [m3dc1_scorec] | `m3dc1_mesh_load` rank 插入、`m3dc1_model_load`、`writeNative` |
| `src/m3dc1_mesh.cc` | [m3dc1_scorec] | `createVertex/createEntity`、`acceptChanges` 调用点 |
| `src/m3dc1_entity.cc` | [m3dc1_scorec] | `toModel`/`gmi_dim`/`gmi_tag` classification 读取 |
| `test/m3dc1_meshgen.cc`/`multi_meshgen.cc` | [meshgen] | `writeNative` 文件名、`gmi_dim==2` 校验 |
| `FindScorec.cmake`/`CMakeLists.txt`/`README` | 两端 | 依赖库名、版本证据 |
| M4-0C1/C2/C3/D/D1 报告 | LinkMesh | 综合基线 |

### 跳过

- SCOREC/core 声明与实现（未授权、版本未确认）。
- `.smb`/`.sms`/`.dmg`/`.smd`/VTK/对象/库/可执行/`build/`。

---

## 5. 双文件输出契约

| 维度 | TXT model file | SMB mesh file |
|---|---|---|
| 正式用途 | 描述 geometric model（loop/edge/vertex/face 拓扑 + curve）| native 网格（顶点/三角形/classification）|
| 生产者 | LinkMesh model Writer（未来）| PUMI/APF/MDS（经 LinkMesh Adapter 录入内存后 `writeNative`）|
| 输入数据 | `M3DC1ModelSpec`（边界 loop/edge/face + curve）| `Mesh2D.nodes/triangles` + classification |
| 至少包含 | 头行 + loop + geometric vtx ID/坐标 + edge + curve + face↔loop | 全量 mesh 顶点 + 三角形 + geometric classification |
| 生成 API/Writer | `save_model`/`save_multi_rgn_model` 等价文本 Writer | `apf::Mesh2::writeNative`（正式 API）|
| 允许手写二进制 | 否（文本）| **否**（禁止字节级序列化）|
| 消费者 | `m3dc1_model_load`→`load_model`；唐同学 model loader | PUMI/APF loader；`m3dc1_mesh_load` |
| 验证责任人 | LinkMesh 测试（Level 1）+ 唐同学（Level 3）| 唐同学（Level 2/3）|
| 静态验证 | 字段顺序对照 `fscanf` | 文件存在非空、SHA-256 |
| 动态验证 | model loader 成功恢复 | PUMI load + verify + 计数 + classification |
| 与另一文件一致性 | tag 必须被 SMB classification 引用 | classification tag 必须在 TXT model 中存在 |
| 证据等级 | 【源码确认：双向证据】 | 【会议确认：A 级事实 + 源码确认：双向证据】 |

### 正式表述

- M3DC1 P0 输出 = **配套 TXT model + SMB mesh**【会议确认：A 级事实】。
- TXT 字段顺序由 `save_model/save_multi_rgn_model` ↔ `load_model` **双向源码定义**，不得缩减为边界坐标 CSV【源码确认：双向证据】。
- SMB 必须经 PUMI/APF/MDS 正式 API 写出；**LinkMesh 不拥有 SMB 字节协议**【会议确认：A 级事实】。
- TXT 与 SMB 必须描述**相容的 geometric model/classification**【源码确认：消费端证据】。
- `.dmg` **不属于**当前 P0 已确认必需输出【不阻塞 M4-0E / 待确认】。

---

## 6. 责任边界

| 参与方 | 输入 | 动作 | 输出 | 成功判据 | 失败回传 | 阻塞 M4 |
|---|---|---|---|---|---|---|
| 刘老师 | 项目需求 | 确认目标格式路线与双文件要求 | A 级事实 | 已确认 | — | 否（已完成）|
| LinkMesh（未来）| GFile/边界 + 配置 | 生成候选 TXT + SMB | 交接包 | 文件生成成功 | 生成日志 | 是（Writer 实现）|
| Aider（未来）| 蓝图 | 实现 Writer/Adapter + 仓库测试（Level 1）| 测试证据 | 单测通过 | 测试失败输出 | 是 |
| 唐同学 | 交接包 | 轻量 load-mesh 验证 + 可视化（Level 2/尽力 3）| 回传模板 | 加载+verify+可视化通过 | 回传模板（FAIL 段）| 是（验收）|
| User | 各报告 | 验收、蓝图变更、里程碑切换 | 验收结论 | 报告完整可执行 | 退回意见 | 是（决策）|
| 轻量 load-mesh 程序 | TXT+SMB | 加载/校验/可视化 | 判据结果 | 见 §8/§9 | 日志 | 工具，非运行时依赖 |
| 完整 M3DC1 消费端 | TXT+SMB | 端到端加载+初始化 | Level 4 结论 | 物理程序接受 | 物理层日志 | Level 4（M5/导师）|

- 轻量验证程序是**开发验收工具，不是 LinkMesh 运行时依赖**【会议确认：A 级事实】。
- 完整 M3D-C1 端到端属**更高等级验收，不被 Level 2 替代**【验证设计】。

---

## 7. D2-A SMB 轻量加载验证

为唐同学设计的最小 SMB 验收规范（26 项）。预期值来源=LinkMesh 生成报告/交接包。

| # | 检查项 | 方式 | 所需 API | PASS | FAIL | 静态可确认 | 必须运行 |
|---|---|---|---|---|---|---|---|
| 1 | 文件存在非空 | 文件系统 | — | 大小>0 | 缺失/空 | 是 | 否 |
| 2 | 兼容版本 PUMI 加载 | loader | `loadMdsMesh`/`pumi_mesh_load` | 无异常 | 崩溃/报错 | 否 | 是 |
| 3 | 加载返回成功 | loader | 同上 | 返回有效 mesh | NULL/错误码 | 否 | 是 |
| 4 | dimension=2 | 查询 | `mesh->getDimension` | =2 | ≠2 | 否 | 是 |
| 5 | vertex 数=报告值 | 计数 | `mesh->count(0)` | 相等 | 不等 | 否 | 是 |
| 6 | triangle 数=报告值 | 计数 | `mesh->count(2)` | 相等 | 不等 | 否 | 是 |
| 7 | edge 数与拓扑一致 | 计数 | `mesh->count(1)` | 合理 | 异常 | 否 | 是 |
| 8 | 顶点坐标有限 | 遍历 | `getPoint` | 全有限 | NaN/Inf | 否 | 是 |
| 9 | R/Z 范围与输入相容 | 遍历比对 | `getPoint` | 落在范围 | 越界 | 否 | 是 |
| 10 | 第三坐标满足 2D 约定 | 遍历 | `getPoint` | z=0 或平面 | 异常 z | 否 | 是 |
| 11 | connectivity 合法 | 遍历 | `getDownward` | 索引合法 | 非法 | 否 | 是 |
| 12 | 无越界引用 | 遍历 | `getMdsIndex` | 范围内 | 越界 | 否 | 是 |
| 13 | 无重复顶点退化三角 | 几何 | `getDownward`+坐标 | 无退化 | 有退化 | 否 | 是 |
| 14 | 三角形面积非零 | 几何 | `measure` | >阈值 | ≈0 | 否 | 是 |
| 15 | classification 可读 | 查询 | `toModel`+`gmi_dim` | 可读 | 读失败 | 否 | 是 |
| 16 | triangle→2 维 face | 查询 | `gmi_dim(toModel)==2` | 是 | 否 | 否 | 是 |
| 17 | boundary edge→1 维 edge | 查询 | `gmi_dim==1` | 是 | 否 | 否 | 是 |
| 18 | vertex classification 维度合理 | 查询 | `gmi_dim` | 0/1/2 合理 | 异常 | 否 | 是 |
| 19 | model tag 在 TXT model 可找到 | 交叉 | `gmi_find` | 命中 | 未命中 | 否 | 是 |
| 20 | verify 通过 | 校验 | `apf::verify` 或等效 | 通过 | 失败 | 否 | 是 |
| 21 | 可输出可视化 | 导出 | VTK 等 | 生成成功 | 失败 | 否 | 是 |
| 22 | 可视化无孔洞/折叠/断裂 | 人工 | 可视化工具 | 无异常 | 有异常 | 否 | 是 |
| 23 | 文件命名/rank 符合 loader | 运行 | loader | 一致 | 不一致 | 部分 | 是 |
| 24 | 不要求预存 C1 field | 约定 | — | 无需 | — | 是 | 否 |
| 25 | 不要求预存高阶节点 | 约定 | — | 无需 | — | 是 | 否 |
| 26 | `norm_curv` 缺失不自动判失败 | 约定 | — | 除非 loader 证明必需 | loader 报缺失必需 | 部分 | 是 |

- 第 15–19、26 项 classification 的**本地判定规则**仍待 core/运行验证【待唐同学实际验证 / 待 SCOREC/PUMI 版本确认】。
- **不编写验证程序源码，仅设计契约**【验证设计】。

---

## 8. D2-B TXT model 验证

依据 `save_model`/`save_multi_rgn_model`（生成端）↔ `load_model`（消费端）双向源码，字段级验证表。

| # | 字段/段 | 来源 | 验证要点 | 标记 |
|---|---|---|---|---|
| 1 | 文件头 `numL sep inner outer vacuum` | 头行 | 5 个整数 | 双向源码已确认 |
| 2 | loop 总数 numL | 头行 | 与后续 loop 数一致 | 双向源码已确认 |
| 3 | separatrix loop ID | 头行 | 整数（-1=无）| 双向源码已确认 |
| 4 | inner wall loop ID | 头行 | 整数（-1=无）| 双向源码已确认 |
| 5 | outer wall loop ID | 头行 | 整数（-1=无）| 双向源码已确认 |
| 6 | vacuum loop ID | 头行 | 整数（-1=无）| 双向源码已确认 |
| 7 | 每 loop ID | loop 头 | 与头标记引用一致 | 双向源码已确认 |
| 8 | 每 loop edge 数 numE | loop 头 | 与后续 edge 数一致 | 双向源码已确认 |
| 9 | geometric vertex ID | vtx 行 | 整数，被 edge 引用 | 双向源码已确认 |
| 10 | vertex 坐标 x y z | vtx 行 | 有限，z=0 | 双向源码已确认 |
| 11 | geometric edge ID | edge 头 | 整数，唯一 | 双向源码已确认 |
| 12 | edge begin/end vertex ID | edge 头 | 引用存在的 vtx | 双向源码已确认 |
| 13 | curve type | edge 头 | LIN/POLY→BSPLINE/BSPLINE | 双向源码已确认 |
| 14 | LIN 参数 | edge 段 | 无额外参数 | 双向源码已确认 |
| 15 | BSPLINE order | BSPLINE 段 | 正整数 | 双向源码已确认 |
| 16 | control-point 数 numPts | BSPLINE 段 | 正整数 | 双向源码已确认 |
| 17 | knot 数(order+numPts)与有限性 | BSPLINE 段 | 数量匹配、有限 | 双向源码已确认 |
| 18 | control-point 坐标 | BSPLINE 段 | 2×numPts 有限 | 双向源码已确认 |
| 19 | face 数 numFaces | face 段头 | 整数 | 双向源码已确认 |
| 20 | face ID | face 段 | 1 起连续（生成端 `i+1`）| 生成端出现 |
| 21 | face 引用 loop 数 numLoops | face 段 | 正整数 | 双向源码已确认 |
| 22 | face→loop 引用 | face 段 | 引用存在的 loop | 双向源码已确认 |
| 23 | 所有 ID 引用存在 | 全文件 | 无悬空引用 | 必须由 loader 验证 |
| 24 | 单 face P0 拓扑闭合 | 全文件 | 1 loop→1 face 闭合 | 必须由 loader 验证 |
| 25 | Writer 顺序 ↔ Reader `fscanf` 顺序 | 全文件 | 逐字段对应 | 双向源码已确认 |
| 26 | 结尾无缺失字段 | 全文件 | `fscanf` 不早停 | 必须由 loader 验证 |
| 27 | 额外 token 处理 | 全文件 | 允许/报错策略 | 必须由 loader 验证 |
| 28 | 实际 model loader 成功读取 | 运行 | `load_model` 返回成功 | 必须由实际 loader 验证 |

- `numFaces==0` 兼容分支：消费端 `load_model` 回退对 `1..numL` 各建一 face 并提示"用最新 meshgen 重新生成"——**LinkMesh 应写 `numFaces>0` 的完整 face 段**【源码确认：消费端证据】。
- **不把 TXT model 写成 CSV，不改既有格式**【源码确认：双向证据】。

---

## 9. TXT 与 SMB 交叉一致性

| # | 一致性问题 | 判据 | 标记 |
|---|---|---|---|
| 1 | TXT geometric vertex tag ↔ SMB vertex classification tag | `gmi_find(model,0,tag)` 命中 | 待唐同学实际验证 |
| 2 | TXT geometric edge tag ↔ SMB boundary entity classification | `gmi_find(model,1,tag)` 命中 | 待唐同学实际验证 |
| 3 | TXT face tag ↔ SMB triangle classification | `gmi_find(model,2,tag)` 命中 | 待唐同学实际验证 |
| 4 | TXT geometric vertex 坐标 ↔ SMB corner vertex 坐标 | 坐标一致（容差）| 待唐同学实际验证 |
| 5 | boundary mesh vertices 落在 TXT geometric edge 上 | 曲线上/容差 | 待唐同学实际验证 |
| 6 | TXT loop 闭合 | 首尾 vtx 一致/periodic | 源码确认：双向证据 |
| 7 | SMB boundary edges 组成与 TXT loop 相容闭合边界 | 边界环闭合 | 待唐同学实际验证 |
| 8 | model 维度=2 | `mesh->getDimension`、`gmi_dim` | 源码确认：消费端证据 |
| 9 | 单 face P0 只有一个 2 维 face | model face 数=1 | 验证设计 |
| 10 | `region_ids` 不等同 model face tag | Adapter 明确分配 face tag | 会议确认：A 级事实 + 验证设计 |
| 11 | 文件名共享 base name | `<base>.txt` + `<base>0.smb` | 源码确认：消费端证据（字符串）|
| 12 | loader 分别接收 TXT 与 SMB 路径 | `m3dc1_model_load`/`m3dc1_mesh_load` 分别传参 | 源码确认：消费端证据 |
| 13 | geometric model 必须先于 SMB mesh 加载 | model load → mesh load 顺序 | 源码确认：消费端证据 |
| 14 | TXT 可加载但 SMB classification 不相容 → 整体失败 | 交叉失败判整体 FAIL | 验证设计 |
| 15 | SMB 可单读但无法与 TXT 配套 → 整体失败 | 同上 | 验证设计 |

### 四个 PASS 等级区别

- **单文件 PASS**：TXT 单独结构合法 或 SMB 单独可加载。
- **双文件配套 PASS**：TXT+SMB classification 相容，形成完整初始网格输入。
- **格式级 PASS**：Level 1+2+3 通过，格式可被 loader 消费（不含物理）。
- **完整 M3DC1 运行 PASS**：Level 4，物理程序端到端接受。

---

## 10. 单进程文件名与加载调用

来源：`m3dc1_scorec.cc::m3dc1_mesh_load` 字符串处理【源码确认：消费端证据】。

| 项 | 候选值 | 依据 |
|---|---|---|
| model 写出名 | `<base>.txt` | 生成端 `sprintf("%s.txt")` |
| SMB 实际文件 | `<base>0.smb` | mesh_load 插 rank |
| model load 参数 | `<base>.txt` | `m3dc1_model_load` 裸名 |
| mesh load 参数 | `<base>.smb` | `m3dc1_mesh_load` 传裸名 |
| loader 预期实际打开 | `<base>0.smb` | `base+rank+"."+ext` |

必须标注：
- rank 插入来自**静态源码**（`in.rfind('.')`+`pumi_rank()`）【源码确认：消费端证据】。
- 实际运行行为**尚待唐同学验证**，验证前不固化为无条件事实【待唐同学实际验证】。
- 需测试传入已带 `0` 的名（`foo0.smb`）是否错误展开为 `foo00.smb`【待唐同学实际验证】。
- 需记录 rank=0、group_size=1、MPI size=1。
- 需记录 loader 接收的原始参数与实际打开路径。
- 需记录 model 与 mesh 是否必须同 base。
- 需记录验证程序是否绕过 `m3dc1_mesh_load` 直接调 APF/PUMI loader。

### 两种验证方式区分

1. **直接 PUMI/APF load-mesh**（`loadMdsMesh(model, file)`）：验证 SMB 格式与 classification，**不经** `m3dc1_mesh_load` 的 rank 插入逻辑 → 文件名可直接传实际路径【验证设计】。
2. **`m3dc1_scorec` load API**（`m3dc1_model_load`+`m3dc1_mesh_load`）：验证 M3D-C1 文件命名与 model→mesh 加载顺序，**经** rank 插入【验证设计】。

若唐同学只实现方式 1，则**方式 2（M3D-C1 命名与加载顺序）仍待后续验收**【待唐同学实际验证】。

---

## 11. 唐同学交接包清单

未来 LinkMesh 生成候选文件后交唐同学的最小交接包。

| # | 项 | 提供方 |
|---|---|---|
| 1 | `<base>.txt` | LinkMesh |
| 2 | `<base>0.smb`（或实际生成名）| LinkMesh |
| 3 | 生成命令 | LinkMesh |
| 4 | LinkMesh Git commit | LinkMesh |
| 5 | 配置文件（linkmesh.in）| LinkMesh/User |
| 6 | 输入 GFile/边界来源说明 | LinkMesh/User |
| 7 | 节点数 | LinkMesh |
| 8 | edge 数 | LinkMesh |
| 9 | triangle 数 | LinkMesh |
| 10 | boundary segment 数 | LinkMesh |
| 11 | geometric vertex/edge/face 数 | LinkMesh |
| 12 | model tag 分配表 | LinkMesh |
| 13 | 坐标单位（m）| LinkMesh |
| 14 | 坐标范围（R/Z min/max）| LinkMesh |
| 15 | triangle orientation 约定 | LinkMesh |
| 16 | PUMI/SCOREC 版本 | 构建环境 |
| 17 | MPI 版本与进程数 | 构建环境 |
| 18 | 编译器版本 | 构建环境 |
| 19 | 预期 loader 调用 | LinkMesh/User |
| 20 | 预期可视化输出 | LinkMesh/User |
| 21 | 文件 SHA-256 | LinkMesh |
| 22 | 已知限制 | LinkMesh/Aider |
| 23 | 不含 C1 field 的明确声明 | LinkMesh |
| 24 | `norm_curv` 是否存在 | LinkMesh |
| 25 | 失败回传格式（指向 §12）| User |

- **不要求**把老师参考源码或完整 SCOREC/core 打包进交接包【验证设计】。

---

## 12. 验证结果回传模板

结构化回传模板。**所有结果位置写"待填写"，不制造示例 PASS**【会议确认：A 级事实】。

| 字段 | 值 |
|---|---|
| 验证日期 | 待填写 |
| 验证人 | 待填写 |
| 操作系统 | 待填写 |
| 编译器 | 待填写 |
| MPI | 待填写 |
| SCOREC/PUMI 版本或 commit | 待填写 |
| loader 源码 commit | 待填写 |
| loader 编译命令 | 待填写 |
| loader 运行命令 | 待填写 |
| model 文件名 | 待填写 |
| SMB 文件名 | 待填写 |
| SHA-256（txt/smb）| 待填写 |
| model load 返回值 | 待填写 |
| mesh load 返回值 | 待填写 |
| 实际打开路径 | 待填写 |
| mesh dimension | 待填写 |
| vertex/edge/triangle 数 | 待填写 |
| classification 维度统计 | 待填写 |
| verify 结果 | 待填写 |
| 可视化文件 | 待填写 |
| 截图/日志路径 | 待填写 |
| warning | 待填写 |
| error | 待填写 |
| PASS/FAIL | 待填写 |
| 失败定位 | 待填写 |
| 建议修复层（ModelSpec/Adapter/PUMI 调用/文件命名/验证环境）| 待填写 |

---

## 13. 失败分类

| 类 | 典型证据 | 责任层 | 属 LinkMesh | 阻塞 M4 | 需改蓝图 | 只需修实现 | 必须回传日志 |
|---|---|---|---|---|---|---|---|
| A TXT model Writer 失败 | 字段缺失/顺序错 | LinkMesh Writer | 是 | 是 | 否（除非契约错）| 是 | Writer 输出 + TXT |
| B geometric model loader 失败 | `load_model` 报错 | TXT 契约/loader | 部分 | 是 | 可能 | 可能 | loader 日志 |
| C PUMI/APF mesh 创建失败 | createEntity 异常 | Adapter | 是 | 是 | 否 | 是 | Adapter 日志 |
| D classification 不相容 | tag 未命中 | Adapter/ModelSpec | 是 | 是 | 可能 | 可能 | 交叉检查日志 |
| E SMB writeNative 失败 | 写出异常 | Adapter/PUMI | 是 | 是 | 否 | 是 | 写出日志 |
| F SMB load 失败 | load 崩溃 | 格式/版本 | 部分 | 是 | 否 | 可能 | loader 日志 |
| G rank/文件命名失败 | 打开路径不符 | 命名约定 | 部分 | 是 | 可能 | 是 | 打开路径记录 |
| H topology verify 失败 | verify 报错 | Adapter | 是 | 是 | 否 | 是 | verify 输出 |
| I 计数不一致 | 数不等报告 | Adapter | 是 | 是 | 否 | 是 | 计数对比 |
| J 坐标/单位错误 | 越界/NaN | Adapter | 是 | 是 | 否 | 是 | 坐标统计 |
| K 可视化几何异常 | 孔洞/折叠 | Adapter/上游 | 是 | 是 | 否 | 是 | 可视化文件 |
| L SCOREC/PUMI 版本不匹配 | ABI/加载错 | 环境 | 否 | 是 | 否 | 否（环境）| 版本证据 |
| M MPI/编译器 ABI | 链接/运行错 | 环境 | 否 | 是 | 否 | 否 | 构建日志 |
| N 完整 M3DC1 物理层失败 | 物理初始化错 | Level 4 | 否（超范围）| 否（Level 2/3）| 否 | 否 | 物理层日志 |

### 停止并标待确认的情况

- 未知 SCOREC/PUMI 版本【待 SCOREC/PUMI 版本确认】。
- loader 使用与生成端不兼容的库。
- TXT 能加载但 classification tag 不匹配。
- 只能手工改 SMB 才能加载。
- 需要完整 M3DC1 才能完成格式级验证。
- 轻量 loader 无法读取 classification。
- rank 文件名规则与静态源码不一致。
- 验证结果无法复现。

---

## 14. 四级验收

| 等级 | 内容 | 责任 | 判据 |
|---|---|---|---|
| Level 1 TXT 静态结构 | Writer 字段↔Reader 顺序对应；ID 引用/计数/坐标/拓扑合法 | LinkMesh 测试 + 源码对照 | §8 全部 |
| Level 2 SMB 轻量加载 | PUMI/APF 加载；topology/classification/计数/坐标/verify；可视化 | 唐同学（主要）| §7 全部 |
| Level 3 TXT+SMB 配套 | model 先加载；SMB 与 model classification 相容；两文件形成完整初始网格 | 唐同学（尽力）| §9 全部 |
| Level 4 完整 M3D-C1 | 正式运行环境加载 + 初始化 + 物理接受 | M5/导师 | 端到端 |

- 唐同学当前主要负责 **Level 2**，尽力 **Level 3**【会议确认：A 级事实】。
- **Level 1** 由 LinkMesh 测试与源码对照完成【验证设计】。
- **Level 4 不由轻量 loader 替代**【验证设计】。
- M4 P0 Writer 完成至少需 **Level 1+2+3**；M5/求解器对接需 **Level 4 或导师等效验收**【验证设计】。

---

## 15. 版本证据采集

本轮不读 core，设计需回传的版本证据（不猜测老师服务器配置）：

| # | 证据 | 说明 |
|---|---|---|
| 1 | SCOREC/PUMI 安装根路径 | 待唐同学/环境回传 |
| 2 | 库文件路径 | 同上 |
| 3 | 关键头文件路径 | `apfMDS.h`/`apfMesh2.h`/`pumi.h` |
| 4 | Git commit/tag/包版本 | 版本锁定关键 |
| 5 | CMake package 信息 | FindScorec 命中路径 |
| 6 | 编译链接库列表 | `SCOREC_LIB_NAMES` 实际解析 |
| 7 | `apfMDS.h`/`apfMesh2.h`/`pumi.h` 来源 | 声明确认 |
| 8 | MPI 实现与版本 | ABI 相关 |
| 9 | 编译器与标准 | ABI 相关 |
| 10 | 是否启用 Simmetrix | LinkMesh P0 不需 |
| 11 | loader 与生成端是否同库 | 兼容性关键 |
| 12 | ABI/编译选项差异 | 排查 M 类失败 |

- **SCOREC/PUMI 版本未确认；不得默认 GitHub 最新版**【待 SCOREC/PUMI 版本确认】。

---

## 16. M4-0E 进入条件

| 问题 | 裁决 |
|---|---|
| 哪些会议事实可直接写蓝图 | 双文件输出、PUMI API 生成 SMB、不手写字节、唐同学 Level 2 责任 |
| 哪些源码事实可直接写蓝图 | TXT 字段双向契约、`writeNative`/`loadMdsMesh` 正式 API、rank 插入命名 |
| 哪些写成停止条件 | 未确认 API 签名/版本、classification 本地判定、`acceptChanges/verify` 顺序、实际加载行为 |
| 哪些只能 M4 输出后回填 | Level 2/3 实际 PASS、计数一致、可视化、rank 实际展开 |
| 是否允许进入 M4-0E | **允许**（D2 已形成可执行契约）|
| M4-0E 前是否需实际运行 loader | 否（无 LinkMesh M4 输出，无法运行）|
| 实际 loader 验证放在哪个里程碑 | M4 实现产生候选文件后，作 M4 验收项 |
| D2 是否形成可执行交接闭环 | 是（契约+交接包+回传模板+四级验收）|

### 裁决原则

- D2 只要形成明确、可执行、可复现的验证契约即可进入 M4-0E【验证设计】。
- 不要求在无 LinkMesh M4 输出时提前获得虚假实际 PASS【会议确认：A 级事实】。
- 蓝图须把 **Level 1–3 写入 M4 验收条件**【验证设计】。
- 实际验证在 M4 实现产生候选文件后执行。
- **M4 未经唐同学 Level 2/3 验证不得标 PASSED**【验证设计】。

---

## 17. M4 实现与验收停止条件

- 未确认 SCOREC/PUMI 版本前不申请 core 文件、不写死 API 签名【待 SCOREC/PUMI 版本确认 / 阻塞 M4 实现】。
- classification 本地判定（corner/boundary/interior）规则未经 core 或运行验证前，Adapter 分类逻辑保留为停止条件【阻塞 M4 实现】。
- `acceptChanges/verify/writeNative` 精确顺序与必需性未运行验证前不固化【阻塞 M4 实现】。
- 单进程文件命名（`base0.smb`）实际展开未验证前不固化【待唐同学实际验证】。
- Level 2/3 未通过前 M4 不得 PASSED【验证设计】。

---

## 18. 与 TRIMEG Rbc/Zbc 的隔离

- TRIMEG `outer_boundary` 是进入 Triangle **前**的有序离散计算域边界。
- 人工矩形四控制角点**不能代替**重采样后的离散边界点列。
- `artificial_outer` 作为 boundary source 仍合法。
- 正确链路：控制几何 → 重采样边界 → Triangle 输入前点列 → `Mesh2D.outer_boundary` → `Rbc/Zbc`。
- `Rbc/Zbc` **不从 `idxevert` 反推**。
- M3DC1 TXT model 的边界点与 TRIMEG `Rbc/Zbc` **可能同源，但数据契约不同**（TXT=geometric loop/edge/curve 拓扑；`Rbc/Zbc`=单条有序外边界）。
- M3DC1 model/classification **不改变** TRIMEG Writer。
- M4-0E 蓝图验收后**先返回 M3 complete-11** 修复 `71fe09f`。
- M3 complete-11 完整通过后才开始 M4 正式业务实现。

---

## 19. 已确认事项

- 【会议确认：A 级事实】M3DC1 P0 输出=TXT model + SMB；SMB 经 PUMI API 生成，LinkMesh 不手写字节；唐同学负责轻量 load-mesh 验证。
- 【源码确认：双向证据】TXT model 字段顺序由 `save_model/save_multi_rgn_model`↔`load_model` 定义；`.smb` 由 `writeNative` 写、`loadMdsMesh`/`pumi_mesh_load` 读。
- 【源码确认：消费端证据】`m3dc1_mesh_load` 对 `foo.smb` 插 rank 查 `foo0.smb`；model 必须先于 mesh 加载；classification 经 `toModel`+`gmi_dim/gmi_tag`。
- 【验证设计】四级验收（Level 1–4）、责任矩阵、交接包、回传模板、失败分类均已形成可执行契约。

## 20. 待实际验证事项

- SMB 实际加载、计数一致、classification 相容、verify、可视化（Level 2）【待唐同学实际验证】。
- TXT+SMB 配套加载与 tag 交叉一致（Level 3）【待唐同学实际验证】。
- 单进程 rank 文件名实际展开（`base0.smb`、`base00.smb` 边界）【待唐同学实际验证】。
- classification 本地判定规则、`acceptChanges/verify` 必需性【待 SCOREC/PUMI 版本确认 / 阻塞 M4 实现】。
- SCOREC/PUMI 版本、MPI、编译器 ABI【待 SCOREC/PUMI 版本确认】。
- 完整 M3D-C1 端到端（Level 4）【不适用于 P0 当前轮 / 后续里程碑】。

---

## 21. 完成声明

- 本轮只修改 `m4_0d2_report.md`。
- 未修改 `LinkMesh_Architecture_Plan.md`、`CONTEXT.md`、`History.md`。
- 未修改 LinkMesh 业务源码或测试。
- 未修改老师提供的参考源码。
- 未创建其他文件。
- 未编译或运行程序。
- 未生成 TXT model 或 SMB 候选文件。
- 未伪造唐同学的验证结果（所有结果位置为"待填写"）。
- 未下载 SCOREC/core。
- 未读取或解析 `.smb`/`.dmg`/`.smd`/`.sms`。
- 未猜测 SMB 字节布局。
- 未实现 model Writer、PUMI Adapter、SMB Writer 或 load-mesh 工具。
- 未修改 `Mesh2D`。
- 未修复 `71fe09f`。
- TRIMEG `Rbc/Zbc` 修复仍保留在 M4-0E 蓝图验收后的 M3 complete-11 阶段。
