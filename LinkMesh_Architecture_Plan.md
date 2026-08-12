# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **5.0**（M3D-C1 多区域 PUMI 输入契约调查已完成；教程三 face 拓扑与 exchange 多 face record 表达能力已确认；multi-face ModelSpec、classification、schema v2、helper 多 face 支持及 `regions generate target=m3dc1` 仍是待 User 批准或待 native probe 的候选，尚未实现或开放；多区域 TRIMEG HDF5 已按 User 最新直接证据生成并通过自动测试和实际检测，标准 MATLAB/TRIMEG consumer 加载仍待验收）
- 最高依据：本文档自身即为 LinkMesh 项目唯一有效技术蓝图；开发纪律见 `CONTEXT.md`；完成过程与真实运行证据见 `History.md`；仓库导航见 `Project_Tree.md`；`docs/linkmesh/` 下的 work plan 仅作为人类阶段记事本，不是技术契约或 Aider 执行依据；组内使用说明见 `docs/linkmesh/plan.md`；精简前完整 3.x 技术蓝图见只读快照 `docs/linkmesh/LinkMesh_Architecture_Plan_v3.7.md`；更早历史快照见 `docs/linkmesh/LinkMesh_Architecture_Plan_v1.13.md`；边界输入、交付部署等专题事实见 `docs/linkmesh/` 下相应分析报告。上述文档均不得覆盖本文的正式技术定义
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION / NOT IMPLEMENTED】为已批准正式契约但尚未实现的功能；【P0 禁止】为当前阶段严格禁止引入的功能；【实现候选】为已有源码调用点线索但须目标版本与最小运行验证确认、不得写成固定接口的路线；【版本锁定兼容接口】为 User 已批准、绑定特定 OFT 版本、范围受控、失败即停止的私有依赖，不是通用稳定公共 API
- 修改前置条件：任何对本文档接口、字段、格式、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位、范围与当前状态

### 1.1 项目定位

LinkMesh 是一个独立命令行程序（CLI），用于打通：

```text
等离子体平衡文件 GFile/EQDSK
  → 二维非结构三角网格
  → 目标求解器静态网格文件
```

唯一网格生成底座是 OFT/TokaMaker 封装方式调用的 Triangle，OFT 内部经
`liboft_triangle` 完成。LinkMesh 不维护第二种网格引擎。

SCOREC/PUMI 不是第二剖分器。LinkMesh 使用目标 PUMI 软件包提供的 APF、MDS、
GMI、PCU 与 PUMI 接口，将既有 `Mesh2D` 和 `M3DC1ModelSpec` 转换为 classified
APF/MDS mesh，并调用官方 `writeNative()` 生成 SMB。PUMI/APF/MDS 不重新生成
三角剖分。

### 1.2 总体数据流

```text
GFile/EQDSK
  → Reader
  → OFT Adapter
  → Mesh2D
      ├── TRIMEG HDF5 Writer → HDF5
      ├── M3DC1 model Adapter → M3DC1ModelSpec
      │     ├── TXT Writer → <base>.txt
      │     └── SMB Writer → native helper → rank-0 native SMB
      └── Plotter → PNG
```

M3D-C1 P0 正式生产链：

```text
GFile
  → OFT/Triangle
  → Mesh2D
  → single-face M3DC1 model Adapter
  → M3DC1ModelSpec
      ├── LinkMesh TXT model Writer
      └── LinkMesh SCOREC/PUMI Adapter
            → classified APF/MDS mesh
            → 目标版本官方 writeNative()
            → 分区前串行 native SMB
```

TXT Writer 与 SCOREC/PUMI Adapter 必须由同一个 `M3DC1ModelSpec` 驱动，共享
geometric vertex tags、geometric edge tags、loop tags、face tags、edge endpoint
order、face↔loop topology 与 geometric classification 语义。禁止两条输出路径独立
编号。

### 1.3 P0 范围

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；严格读取 `array_file` counted R-Z boundary text；已设计但尚未实现的 `multi_array_file` 重复 counted blocks | LinkMesh 手写 GFile 解析；复杂 CAD；多维输入；Python ndarray 公共边界 API；CSV 或通用区域 DSL |
| 网格生成 | OFT `gs_Domain` / `build_mesh()` 调用 Triangle | 第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；维护 OFT 分支 |
| 分区 | LinkMesh 不涉及；终点为分区前串行 native SMB | `split_smb`、`part*.smb`、`**1.smb`～`**16.smb`、环向或并行分区 |
| 输出 | TRIMEG HDF5；M3D-C1 analytic model TXT + 分区前串行 PUMI native SMB | Simmetrix、`make_model`、`.smd`、`.sms` 正式依赖；手写、解析、修改、拼接、模板复制或逆向 SMB 字节 |
| 可视化 | matplotlib PNG 自检 | 交互式或三维渲染 |
| 配置 | `linkmesh.in` + CLI + `EffectiveConfig`；已设计但尚未实现的 regions 专用配置 | 通用配置 DSL、插件系统 |

### 1.4 事实环境边界

- 本地 LinkMesh 仓库是开发和蓝图维护工作区。
- `/data/liuchang/east_fishbone_1/`、`/opt/spack` 与 `/data/liuchang` 属于服务器
  外部环境，不是本地运行时依赖，不得由本地开发流程访问、创建或假定存在。
- `east.txt` 的 1 loop、104 geometric vertices、104 geometric edges、闭合末边和
  1 face 只辅证 `save_model`/`save_multi_rgn_model` ↔ `load_model` 契约。104、
  固定坐标、文件大小与摘要都不是格式常量。
- 服务器日志确认旧流程使用 Simmetrix 创建 geometric model、写 `.smd`、生成并写
  `.sms` 后重新加载；现有证据未确认 `.sms` 到 `.smb` 的具体命令。
- LinkMesh M4-1B probe 和 M4-2 helper 已在目标 PUMI 环境完成构建和生成侧运行。
- 正式 TXT+SMB 已由真实 M3D-C1/SCOREC 环境成功加载并完成初始化。
- 成功加载与初始化不表示时间推进、稳定性或物理正确性已经通过。

### 1.5 当前权威状态表

| 阶段或能力 | 状态 |
|---|---|
| M1 Reader | **PASSED** |
| M2 默认 `nested_three_region + artificial_outer` | **PASSED** |
| DIII-D GFile 单区域网格生成 | **PASSED** |
| M3 core | **PASSED** |
| M3 complete-11 | **PASSED** |
| TRIMEG 标准 MATLAB 消费端 A/B 验收 | **PASSED** |
| M4-0 只读侦察与架构契约 | **已完成** |
| M4-1A ModelSpec + TXT Writer + Level 1 | **PASSED** |
| M4-1B 实现入口 probe | **COMPLETED / PASSED** |
| M4-2 TXT Writer | **PASSED** |
| M4-2 SMB Writer/helper 生成侧 | **IMPLEMENTED / PASSED** |
| M5 第一条 `single_region + lcfs` M3DC1 CLI | **PASSED** |
| M5 PNG 人工检查 | **PASSED** |
| M3D-C1 配套 TXT+SMB 加载 | **PASSED** |
| M3D-C1 初始化 | **PASSED** |
| M3D-C1 时间推进主循环 | **PENDING** |
| M3D-C1 中等或长时运行稳定性 | **PENDING** |
| M3D-C1 物理结果正确性 | **PENDING** |
| EAST 文件结构调查 | **PASSED** |
| EAST R-Z 列顺序、单位与基础几何验证 | **PASSED** |
| EAST 物理构造算法及其与 LCFS、第一壁、磁轴、X-point 的精确关系 | **PENDING** |
| `single_region + array_file` 正式输入契约与实现 | **IMPLEMENTED / PASSED** |
| EAST counted R-Z 读取、单区域 OFT/Triangle、Mesh2D 与 PNG | **PASSED** |
| EAST TXT+SMB+PNG 生成侧 | **PASSED** |
| EAST M3D-C1 加载与初始化回归 | **PENDING** |
| EAST M3D-C1 时间推进 | **PENDING** |
| TCV 参考边界调查 | **PENDING** |
| TCV/TRIMEG 实际消费 | **PENDING** |
| `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED；未开放** |
| `single_region + array_file` | **IMPLEMENTED / PASSED；EAST 生成侧已验收** |
| `array_file + 可选 GFile LCFS PNG 参考` | **IMPLEMENTED；自动测试与真实 PNG 回归待本轮实施后记录** |
| `plot_lcfs` 配置字段与 `--plot-lcfs` CLI | **IMPLEMENTED；仅允许 LCFS reference 进入 array-file PNG** |
| Release 构建、launcher、bootstrap 与分层检查基础设施 | **IMPLEMENTED** |
| 初版 Release | **DELIVERED；已发送同门和老师，当前反馈可正常使用** |
| `single_region + flux_surface` | **实现候选 / NOT IMPLEMENTED；需 OFT 26.6 只读侦察，未开放** |
| `boundary_source=multi_array_file` | **IMPLEMENTED；通过独立 `regions` 命令族进入，不开放给旧无子命令入口** |
| `linkmesh regions inspect/generate` 两阶段工作流 | **IMPLEMENTED；真实 two-level/four-level OFT/Triangle 生成与多区域 PNG 人工复核已完成** |
| regions map | **IMPLEMENTED；正式 TOML 用户产物，inspect 必须输出，generate 必须读取** |
| OFT 多 Region与分 Region 常数 dx | **运行探针确认；五类案例 GENERATED / STRUCTURALLY CHECKED** |
| OFT Region 编号主逻辑 | **运行探针确认；setup、fresh rebuild、dx change 一致** |
| OFT 无 plasma technical role 路径 | **运行探针确认不受支持；OFT 前置检查主动拒绝** |
| OFT 任意无序曲线自动包含树 | **未提供** |
| LinkMesh 轻量包含推导 | **IMPLEMENTED** |
| synthetic plasma compatibility role | **IMPLEMENTED；仅用于 OFT Adapter 兼容，不表达用户物理语义** |
| LinkMesh multi-array OFT 最小探针程序 | **调查完成；无需继续扩展当前探针** |
| OFT 五类合成多区域案例 | **全部 PASS；GENERATED / STRUCTURALLY CHECKED** |
| LinkMesh 生产 N-region `Mesh2D` | **GENERATED / STRUCTURALLY CHECKED；含 nodes、triangles、region_ids 和 root outer_boundary** |
| LinkMesh 多区域 mesh PNG | **GENERATED；已由 User 人工复核** |
| LinkMesh 多区域 TRIMEG 接线 | **IMPLEMENTED** |
| 多区域 TRIMEG HDF5 | **GENERATED；User 确认自动测试和实际检测通过，未提供精确 passed 数或完整检测明细** |
| 多区域 TRIMEG 标准 MATLAB/TRIMEG consumer 加载 | **PENDING** |
| M3D-C1 求解器多区域模拟能力 | **User 根据同门实际展示确认** |
| M3D-C1 多区域输入契约调查 | **COMPLETED** |
| 教程三 face 拓扑 | **CONFIRMED** |
| exchange 多 face record 表达能力 | **CONFIRMED** |
| exchange schema v2 | **DESIGNED / USER APPROVAL PENDING** |
| multi-face ModelSpec | **DESIGNED / NOT IMPLEMENTED** |
| 多区域 classification | **DESIGNED / NOT IMPLEMENTED** |
| helper 多 face 支持 | **DESIGNED / NATIVE PROBE PENDING** |
| `regions generate target=m3dc1` | **CANDIDATE / NOT OPEN** |
| LinkMesh 多区域 TXT+SMB | **NOT GENERATED** |
| LinkMesh 多区域 TXT+SMB 同门消费验证 | **PENDING** |
| 三维、自适应网格和并行分区 | **OUT OF P0 / 未开放** |

### 1.6 v4.1 当前主线与优先级

LinkMesh 已建立两条目标格式生产链：

```text
GFile/EQDSK 或 counted R-Z boundary
  → Reader
  → OFT/Triangle
  → Mesh2D
      ├── TRIMEG HDF5
      ├── M3D-C1 TXT + rank-0 native SMB
      └── PNG
```

counted R-Z 输入、M3D-C1 TXT+SMB 生成和 TRIMEG HDF5 生成均已实现。已交付给组内
同学的 M3D-C1 网格仍在继续运行；最新 TRIMEG HDF5 已交付卢老师测试。交付只表示
文件已移交，不自动证明外部加载、初始化、时间推进、稳定性或物理正确性。

当前执行优先级重排如下。

**P0：初期交付与产品化收口**

1. 收口老师和初期使用者需要的现有 `array_file` 与 GFile 可用入口。
2. 实现 `array_file` 实际网格配可选 GFile LCFS PNG 参考工作流。
3. 保持 TRIMEG 与 M3D-C1 Writer、`Mesh2D`、ModelSpec 和 helper 契约稳定。
4. 在已实施的 Release 构建基础设施上完成 Linux 构建、结构检查和干净环境验证。
5. 将通过验证的发布候选交给 M3D-C1 和 TRIMEG 使用者。
6. 收集初期使用报告并按真实证据归档问题。

**P1：发布验证与反馈修正**

1. 根据初期用户反馈修正 CLI、诊断、文档和打包。
2. 完成不依赖个人 `PYTHONPATH` 或开发构建目录的干净发布候选验证。
3. 核对 OFT 26.6、`linkmesh-scorec-helper`、SCOREC/PUMI、MPI、C++ runtime
   和 ABI 的运行时定位与动态依赖。
4. 在共享根目录、权限和 module 能力确认后继续推进正式共享 release。

**P2：多轮廓多区域网格与高级网格能力**

1. OFT 官方多 Region 和分 Region 常数 dx 能力已经确认；OFT 不提供任意无序曲线
   自动包含树。
2. `boundary_source=multi_array_file` 与
   `linkmesh regions inspect/generate` 的公开产品接口、Reader、轻量包含树、
   setup-only 编号、TOML map、分 Region dx、N-region OFT/Triangle、`Mesh2D`
   和 PNG 已实现。真实 two-level/four-level 生成、统一 dx、最终 Region ID
   局部 dx、无全局默认时完整覆盖、TOML 配置及 CLI 覆盖均已通过服务器验证。
3. 修正后的主探针已在 OFT 26.6 环境完成重跑。两层、四层、单父双 sibling、混合树
   和重排输入五类案例及各自 dx variant 均完成 Triangle 网格生成；五类案例的
   generation、mesh structure、numbering 和 overall 状态全部为 PASS，证据层级为
   **GENERATED / STRUCTURALLY CHECKED**。
4. setup-only 编号与 Triangle attribute 一致；全新 Domain 重建和只改变 dx 时编号
   一致。同一 technical role 内的输入定义顺序仍可能改变最终 Region ID，因此输入
   block 重排后必须重新 inspect，并按本次 regions map 使用 `--region-dx`。
5. no-plasma 对照探针确认 OFT 26.6 `gs_Domain.build_mesh()` 强制至少一个 plasma
   technical role；`boundary + vacuum` 且无 plasma 的 setup-only 和完整 build
   均在 OFT 前置检查阶段以 `ValueError: No plasma region specified` 失败。
6. User 已批准 synthetic plasma compatibility role：root 为 boundary；最大深度的
   leaf 为 plasma，深度并列时取最小 curve_id；其他内部 Region 为 vacuum。该规则
   只满足 OFT Adapter 兼容要求，不表达用户物理语义。
7. OFT N-region、编号主逻辑和 no-plasma 调查均已完成，不继续扩展当前探针；
   multi-array inspect 与 generate 生产链已经实现并形成合法 N-region `Mesh2D`。
8. 首版不建设通用鲁棒计算几何系统，不引入 Shapely/GEOS，不承诺精确分类复杂
   自交、相切、重合或近接触输入。
9. `nested_three_region` 暂不修改、删除或优化。
10. 后续再调查 OFT 单区域静态空间变网格密度、Triangle refinement、
    M3D-C1 C1 连续性与多 geometric face。
11. 动态自适应和磁面对齐继续保持未开放。

既有 OFT 调查事实、问题列表和停止条件继续有效，仅降低当前执行优先级。在直接证据
明确并先更新蓝图前，不开放空间变密度、局部 refinement、M3D-C1 多区域、多
geometric face、动态自适应或磁面对齐。M3D-C1 多区域输入契约调查虽已完成，但
schema v2、构建结果接口、classification 与 helper native 能力仍未获完整批准或验证。

`array_file + GFile LCFS reference` 工作流已经实现。初版 Release 已发送给同门和
老师，当前反馈为可以正常使用；该交付事实不得降级为 PENDING，也不得外推为
M3D-C1 时间推进、长期稳定性或物理结果已经验证。后续 Release 基础设施版本的 Linux
归档重建、结构检查和共享部署仍按各自层级单独验收。

---

## 2. 总体架构与模块职责

### 2.1 允许依赖方向

```text
cli
  → config
  → readers
  → mesher
  → writers
  → utils

mesher.oft_adapter → mesh
writers → mesh
utils.plotter → mesh
readers.boundary_reader → mesh
utils.plotter → readers（仅用于可选的 GFileData 类型信息，不读取业务文件）
```

`config` 不依赖 Reader、Mesher、Writer 或 Plotter。`mesh.py` 不依赖任何后端、
Writer、CLI、Plotter 或 config。

### 2.2 模块职责

| 模块 | 职责 | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 参数解析和业务逻辑 |
| `src/linkmesh/cli.py` | 收集显式 CLI 参数；调用配置合并；编排 Reader → Mesher → Writer → Plotter；标准工作流保持旧顶层 target；`regions inspect/generate` 使用独立作用域，generate 可在同一个 N-region `Mesh2D` 上选择 `mesh_only` 或 `trimeg` | 几何、区域、种子、Triangle、dx 换算、配置默认值合并、复制 HDF5 Writer 逻辑、把 regions map 元数据传给 Writer、SMB rank 改写或 helper 环境变量解析 |
| `src/linkmesh/config.py` | 定义冻结的标准 `EffectiveConfig` 及独立 regions 配置对象；严格读取 TOML；执行默认值、配置文件、CLI 合并；验证兼容矩阵、required fields 与输出路径冲突 | 读取业务文件；创建 OFT Domain；调用 Writer；打开 HDF5；通用 DSL、插件或任意 N 区域语言 |
| `src/linkmesh/readers/gfile_reader.py` | 独立薄 Adapter：调用 OFT `GEQDSKEquilibrium`，读取 LCFS、limiter、磁轴和基本平衡参数并输出 `GFileData` | 手写 GFile 解析；读取 array file；调用 `boundary_reader`；决定网格边界来源；调用 Mesher、Plotter 或 Writer |
| `src/linkmesh/readers/boundary_reader.py` | 独立 Boundary Reader：实现 `read_boundary_file(filepath: str \| Path) -> np.ndarray`；严格读取 counted R-Z boundary text，返回独立 `(N,2) float64` 米制边界，并复用统一边界几何验证与方向规范化。未来 multi-array Reader 必须作为独立候选职责处理，不得放宽旧单 block 契约 | 创建 `Mesh2D` 或 OFT Domain；调用 OFT/Triangle；读取 GFile；调用 `gfile_reader`；返回 `GFileData`；组合参考几何；调用 Plotter；判断物理语义；平滑、重采样、排序、全局去重或缩放；使用 pandas |
| `src/linkmesh/mesh.py` | 定义统一 `Mesh2D`、统计属性和 `outer_boundary` 集中验证 | 依赖后端或目标格式；读取 OFT 私有属性 |
| `src/linkmesh/mesher/oft_adapter.py` | 构造 OFT Domain；调用唯一 Triangle 底座；规范化 OFT 输出；受控读取 outer Region 回写边界；`array_file` 路径只接收实际 array boundary。未来 multi-array 路径只接收已经完成基础检查、轻量包含推导和显式 ID/dx 解析的 Region plan | 配置解析；复制 OFT 算法；读取禁止的 OFT 私有结构；写文件；接收参考 `GFileData`；感知 `plot_lcfs`；根据 LCFS 改变 Domain；自行猜测包含树、Region ID、物理名称或 dx 顺序 |
| `src/linkmesh/m3dc1_model.py` | 定义 `M3DC1ModelSpec` 并从 `Mesh2D.outer_boundary` 构造 single-face model | PUMI、MPI、Simmetrix 依赖；保存 PUMI 句柄；固定 104 点 |
| `src/linkmesh/writers/hdf5_writer.py` | 按 TRIMEG 11 数据集契约写出 | 修改输入；写 `region_ids`；转置；网格生成 |
| `src/linkmesh/writers/m3dc1_model_writer.py` | 按 M3D-C1 analytic model 契约写 TXT | 复制样例坐标；调用 Simmetrix；独立分配 tags |
| `src/linkmesh/writers/smb_writer.py` | 验证输入；生成 classification 和交换文件；调用 helper；确认 rank-0 SMB | 创建 APF/MDS entity；读写 SMB 字节；硬编码 PUMI 路径 |
| `native/linkmesh_scorec_helper/main.cc` | 读取交换文件；管理 MPI/PCU/GMI/APF/MDS；创建 classified mesh；调用官方 `writeNative()` | 网格剖分；配置；TXT Writer；loader/validator；多区域、多 face、三维或分区 |
| `native/linkmesh_scorec_helper/CMakeLists.txt` | 构建 `linkmesh-scorec-helper` target | 通用 native/plugin 框架；Python 扩展；运行时编译；硬编码安装前缀 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`；`plot_mesh()` 以 `Mesh2D` 及 `Mesh2D.outer_boundary` 作为实际网格和实际计算域边界来源，并可接收可选 `GFileData` 叠加平衡参考；必须将 actual mesh boundary 与 LCFS reference 视觉和图例区分。未来 regions inspection 绘图候选负责显示全部曲线、候选 parent/children、最终 Region ID 与人工复核颜色，generate 绘图负责最终网格和 Region 映射 | 修改数据对象；要求所有路径必须提供 GFile；把外部边界伪装成 LCFS；把 LCFS、limiter 或其他参考曲线标成实际 mesh boundary；把 PNG 表述为数学证明或消费端验收；用颜色猜测物理材料 |

---

## 3. 核心数据契约

### 3.1 `GFileData`

坐标单位为 m，R 为大半径，Z 为垂直方向。字段由 OFT
`GEQDSKEquilibrium` 属性提取。

| 字段 | 类型/shape | 来源 | 说明 |
|---|---|---|---|
| `lcfs_r` / `lcfs_z` | `np.ndarray (N_lcfs,)` | `boundary_R` / `boundary_Z` | LCFS [m] |
| `rmaxis` / `zmaxis` | `float` | `R_mag` / `Z_mag` | 磁轴 [m] |
| `wall_r` / `wall_z` | `Optional[np.ndarray (N_wall,)]` | `limiter_R` / `limiter_Z` | 第一壁；无可用轮廓时为 `None` 或空 |
| `rcentr` | `Optional[float]` | `R_center` | R0 [m] |
| `bcentr` | `Optional[float]` | `B_center` | B0 [T] |
| `current` | `Optional[float]` | `Ip` | 等离子体电流 [A]，不缩放 |

### 3.2 `Mesh2D`

`Mesh2D` 是 LinkMesh 面向 TRIMEG、M3D-C1/PUMI 等下游的统一、持久、
求解器无关中间对象。

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | `[R,Z]`，单位 m |
| `triangles` | `(T,3)` | 整数，实测 `int32` | 内部 0-based |
| `region_ids` | `(T,)` | 整数，实测 `int32` | OFT 区域编号原样保留，不重编号、排序、压缩或 `+1` |
| `boundary_segments` | `(0,2)` 默认 | `int32` | 兼容字段 |
| `boundary_markers` | `(0,)` 默认 | `int32` | 兼容字段 |
| `node_markers` | `(0,)` 默认 | `int32` | 兼容字段 |
| `outer_boundary` | `Optional[(B,2)]` | `float64` | Triangle 输入前的有序最外层计算域边界 |

只读统计属性：`n_nodes`、`n_triangles`、`n_boundary_segments`。

由 `triangles` 可确定性派生的边和邻接关系默认不重复存储。P0 不保存 C1 自由度、
高阶节点、PUMI 句柄、MPI ownership、运行时 field 或求解器私有对象。

### 3.3 `outer_boundary`

| 属性 | 契约 |
|---|---|
| shape/dtype | `(B,2)` / `float64` |
| 列与单位 | 第 0 列 R，第 1 列 Z；m |
| 语义 | 进入 Triangle 前的有序最外层计算域几何边界 |
| 闭合 | 末尾不重复首点，最后一点到第一点隐式闭合 |
| 方向 | 顺时针；带符号闭合面积严格为负 |
| 几何 | 至少 3 个互异有限点；无相邻重复、零长度闭合边、退化面积或非相邻边自交 |
| 所有权 | `Mesh2D` 持有独立 `float64` 副本，不共享输入内存 |
| 必选性 | TRIMEG 必须提供；其他 target 按自身契约，可为 `None` |
| Steiner 点 | 不包含 Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑边界节点集合 |
| 起点 | 不规定固定起点；反向时保持原起点 |

统一验证入口 `_validate_outer_boundary` 必须检查 shape、dtype、有限性、点数、
相邻重复、闭合、方向、面积和完整非相邻边自交，包括严格交叉、端点接触和共线重叠；
不得误判相邻边、首末相邻边、合法凹多边形或区间分离的共线边。坐标容差和 orientation
叉积容差必须分别使用长度和长度平方量纲。

`outer_boundary` 不是人工矩形四角、`Region.get_resampled_points()`、最终
`idxevert`、Triangle 插入的所有边界点、最终 `pts/lc` 反推点列或 LinkMesh 自行
重采样点列。

### 3.4 `EffectiveConfig`

`EffectiveConfig` 是 `@dataclass(frozen=True)`，是默认值、配置文件和显式 CLI
合并、类型校验、路径解析、兼容矩阵及 required-fields 校验后的唯一配置对象。

`EffectiveConfig` 正式包含 17 个字段：既有 16 字段加
`mesh_dx: float`。`mesh_dx` 与区域尺度均保存经过有限正数校验的最终值；尺度是否由
TOML 或 CLI 显式提供只在配置合并期间以局部布尔值判断，绝不保存进最终对象。

| 字段 | 类型 |
|---|---|
| `schema_version` | `int`，固定 `1` |
| `config_path` | `Optional[Path]` |
| `target` | `Literal["mesh_only","trimeg","m3dc1"]` |
| `profile` | `Literal["single_region","nested_three_region"]` |
| `boundary_source` | `Literal["lcfs","first_wall","array_file","artificial_outer","flux_surface"]` |
| `gfile_path` | `Optional[Path]` |
| `array_file_path` | `Optional[Path]` |
| `mesh_dx` | `float`；single-region 唯一目标网格长度尺度 [m] |
| `plasma_dx` | `float`；仅用于 nested-three-region plasma 区域 [m] |
| `vacuum_dx` | `float`；仅用于 nested-three-region vacuum 区域 [m] |
| `outer_dx` | `float`；仅用于 nested-three-region outer 区域 [m] |
| `hdf5_path` | `Optional[Path]` |
| `plot_path` | `Optional[Path]` |
| `model_path` | `Optional[Path]` |
| `smb_path` | `Optional[Path]` |
| `verbose` | `bool` |
| `plot_lcfs` | `bool`，默认 `False`；已批准、尚未实现 |

所有非 `None` 路径在构造前解析为绝对路径。对象不保存来源字典、NumPy 数组、
`Mesh2D`、`GFileData`、PUMI 句柄、Writer、argparse Namespace 或可变业务状态。

### 3.5 `M3DC1ModelSpec`

当前 `M3DC1ModelSpec` 的正式实现仍表达 P0 single-region、single-face、
single-loop analytic model：

- geometric vertices：唯一 tag 和 `[R,Z,0]`；
- directed geometric edges：唯一 tag、begin/end vertex tag、`LIN=1`；
- geometric loop：唯一 tag 和有序 edge tags；
- geometric face：唯一 tag 和 loop tags；
- special loop tags：`separatrix_loop`、`inner_wall_loop`、`outer_wall_loop`、
  `vacuum_loop`。

Adapter 从 `Mesh2D.outer_boundary` 动态构造全部实体。不得固定点数，不得把
`region_ids` 自动当作 geometric face tag，不得保存 PUMI/SCOREC 句柄。

多区域调查已确认：现有字段容器在数据形状上可保存多个 vertices、edges、loops 和
faces，`GeometricFace.loop_tags` 也可表示一个 face 引用多个 loops；但当前
`GeometricFace`、`M3DC1ModelSpec.validate()`、Python SMB Writer 和 native helper
均包含 single-face invariants。因此当前 validated contract 尚不能表达或输出
multi-face model。

多区域候选 builder 需要同时消费 `Mesh2D`、`RegionPlan` 和正式 regions map，并
确定性生成 `curve_id_to_loop_tag` 与 `region_id_to_face_tag`。但仅返回
`M3DC1ModelSpec` 不足以保证 SMB Writer 唯一获得：

- `region_id_to_face_tag`；
- `curve_id_to_loop_tag`；
- interface curve 到 geometric edge chain 的对应。

后续蓝图必须由 User 在以下方向中正式裁决，当前不得自行选择最终对象名或公开签名：

1. 扩展 `M3DC1ModelSpec`，保存不可变 mappings 与 interface identity；
2. 新增一个不可变的多区域构建结果对象，统一携带 spec、mappings 和 classification
   所需身份。

无论采用哪种方向，TXT Writer 与 SMB Writer 都必须接收同一个目标专用构建结果及
同一套 tag mappings，不得分别重新编号或重新猜测映射。

---

## 4. 网格生成与物理约定

### 4.1 坐标、单位和索引

- 坐标为 `[R,Z]`，使用 SI：m、T、A。
- `Mesh2D.triangles` 内部为 0-based。
- 目标格式偏置由 Writer 完成。
- `region_id` 与节点索引无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- M3D-C1 多区域候选中，`Mesh2D.region_ids` 不是 face tags，不得直接充当 face
  tag，也不得为此压缩、排序或执行 `+1`；必须通过显式
  `region_id_to_face_tag` 映射分类。
- nodes、triangles 和由 triangles 确定性派生的唯一 mesh edges 使用一套全局
  0-based topology。Region 不拥有局部节点编号；共享界面节点和 mesh edge 不复制。
- 三角形不得有重复顶点、越界索引或绝对面积不大于 `1e-12`。

### 4.2 OFT/Triangle 与区域语义

OFT 输出契约：

- `pts (N,2) float64`；
- `lc (T,3)` 0-based 整数，满足 `0 <= lc < N`；
- `reg (T,)` 正整数；
- `reg` 与 `domain.region_info` 最终 ID 一一对应。

`mesh_from_oft_domain()` 必须在 `build_mesh()` 后读取最终 `region_info`，验证：

1. 至少一个区域；
2. `reg` 全为有限正整数；
3. `len(reg) == T`；
4. 输出 ID 集合与最终 `region_info` 一致；
5. 每个区域至少有一个三角形；
6. 不重编号、排序、压缩或 `+1`。

默认 nested 策略：

- 有有效第一壁：PLASMA + VACUUM + OUTER；
- 无有效第一壁：PLASMA + OUTER；
- 输入使用 GFile LCFS、可选 limiter/第一壁和 LinkMesh 固定策略构造的
  `artificial_outer`；
- 该生成路径已实现，并已有真实 DIII-D 与 fixed-boundary CLI、HDF5 和 PNG
  的 LinkMesh 生成侧验收证据；
- 该结论不开放 M3D-C1 多区域或多 face，不表示支持任意区域拓扑、三维、自适应
  网格或并行分区。

single-region 的 LCFS、first wall、array file 和 flux surface 只在边界获取阶段
不同；合法边界进入 Mesher 前统一为 `(B,2)` 的二维闭合轮廓，并复用同一
single-region OFT Domain 和 OFT/Triangle 核心。`Mesh2D` 与 Writer 不按来源分叉。
具体策略见第 5.10 节。

### 4.3 `merge_thresh` 与边界方向

- OFT 26.6 `build_mesh()` 使用锁定默认 `merge_thresh=1e-4 m`。
- P0 不将 `merge_thresh` 暴露为 CLI 或配置字段。
- single-region polygon 相邻近重复过滤阈值必须与该值同步。
- 若显式改变 `build_mesh()` 的 `merge_thresh`，必须先更新蓝图、规范化阈值和测试。
- `outer_boundary` 最终必须顺时针；逆时针转换使用
  `[p0, p_(B-1), …, p1]`，不得使用改变起点的裸 `pts[::-1]`。

### 4.4 OFT 26.6 私有兼容接口

【已确认事实】OFT 26.6 没有公共方法返回指定 Region 对应的 Triangle 输入前有序
离散边界。`Region.get_resampled_points()` 使用独立重采样路径，不是 Triangle
输入来源，禁止作为 `outer_boundary` 来源。

`Mesh.__init__()` 完成边界重采样、共享边界处理、点合并、全局重编号和 segment
方向处理，并将有序区域点列写入 `region._resampled_points`。`Mesh.get_mesh()`
将 `Mesh._resampled_points` 传给 Triangle。

受控数据链：

```text
边界来源
  → single-region 相邻近重复规范化
  → 策略层创建 outer Region 并保存引用
  → domain.build_mesh()
  → 读取同一个 outer_region._resampled_points
  → float64 独立副本
  → 删除一个普通显式闭合重复末点
  → 验证并规范化为顺时针
  → Mesh2D.outer_boundary
```

唯一允许读取的 OFT 私有属性是策略层已捕获 Region 的
`outer_region._resampled_points`。

禁止读取或解析：

- `domain.mesh._reg_seg_map`
- `domain.mesh._resampled_segments`
- `domain.mesh._resampled_points`

Region 输入和回写语义：

- `Region.__init__()` 仅在首末距离小于 `dx/1000` 时删除显式闭合末点。
- 相邻边小于 `dx_curve/1000` 时可能警告但不删除控制点。
- 全局点距离严格小于 `1e-4 m` 时映射到同一全局点。
- Region 回写点列按有向 segment 拓扑重建，可能重复引用合并后的坐标。
- OFT warning 不等同于 Triangle 失败。
- LinkMesh 不得放宽 `Mesh2D` 契约接纳回写重复坐标。

读取时机固定为：

1. 规范化 single-region polygon 控制点；
2. 创建 outer Region；
3. 立即保存该对象引用；
4. 执行 `domain.build_mesh()`；
5. build 后读取保存对象的 `_resampled_points`；
6. 创建独立 `float64` 副本；
7. 删除可能存在的一个普通显式闭合重复末点；
8. 验证 shape、有限性、点数、简单闭环和自交；
9. 规范化为顺时针并保持起点；
10. 写入 `Mesh2D.outer_boundary`。

以下情况必须失败：

- OFT 版本不是 26.6；
- Region 未捕获或属性缺失、为 `None`；
- shape 不是 `(B,2)`；
- 存在 NaN/Inf；
- 点数不足；
- 规范化后相邻重复、首尾重复、自交或面积退化；
- 无法证明该 Region 是策略层创建的最外边界；
- OFT 私有接口与已核对数据流不一致。

禁止回退到人工四角、原始 LCFS、`Region.get_resampled_points()`、`idxevert`、
最终 `pts/lc` 反推、LinkMesh 自行重采样或对 TRIMEG 静默设置
`outer_boundary=None`。

### 4.5 OFT 升级纪律

OFT 私有接口是版本锁定、范围受控、失败即停止的兼容接口。升级 OFT 时必须重新核对：

- `Region` 创建及捕获方式；
- `_resampled_points` 写回时机和语义；
- `build_mesh()` 默认 `merge_thresh`；
- Triangle 输入数据流；
- 真实 GFile、HDF5、PNG 和相邻回归。

不得把 OFT 26.6 私有实现假定为跨版本公共 API。

---

## 5. 输入、配置与 CLI 契约

### 5.1 权威性和模块落点

配置契约的唯一权威是：

1. `EffectiveConfig` 字段级契约；
2. 三层合并算法；
3. compatibility matrix；
4. required-fields。

模块落点：

- `src/linkmesh/config.py`：配置读取、严格校验、合并和阶段闸门；
- `src/linkmesh/readers/boundary_reader.py`：计划中的 counted R-Z boundary text Reader；
- `src/linkmesh/cli.py`：显式参数收集与业务编排；
- `src/linkmesh/mesher/oft_adapter.py`：边界来源对应的 OFT 策略；
- 不新增 `inputs/`、抽象基类、注册表、插件或任意 N 区域语言。

### 5.2 边界输入分层

边界输入必须分别描述以下三个层次：

| 层次 | 当前正式类别 |
|---|---|
| 输入载体 | GFile/EQDSK；外部二维边界纯文本 |
| 边界物理语义 | LCFS；limiter/第一壁相关轮廓；内部闭合磁面；外部提供的计算边界 |
| 边界构造方法 | GFile 直接读取；从 GFile 磁通场提取；外部程序构造；研究人员直接提供；LinkMesh 固定策略构造 `artificial_outer` |

输入载体、物理语义和构造方法不得互相替代或互相推断。`array_file` 只表示边界通过
外部二维文件进入 LinkMesh，不表示 CSV、NumPy 文件或特定扩展名，也不自动表示
LCFS、第一壁或磁通面。

不同来源必须先归一为统一二维闭合计算边界，再进入 single-region OFT Domain。
Reader 负责获取边界，Mesher 负责构造 Domain，Writer 只消费 `Mesh2D`，不得跨层
猜测来源或物理语义。

#### 5.2.1 实际计算域边界与 LCFS 参考曲线

已批准的候选工作流必须严格区分两个几何对象。

**实际计算域边界**

```text
counted R-Z array file
  → boundary_reader.read_boundary_file()
  → (N,2) float64 米制简单闭环
  → single-region OFT Domain
  → Mesh2D.outer_boundary
      ├── TRIMEG Rbc/Zbc
      └── M3D-C1 single-face geometric boundary
```

该对象是 `array_file` 工作流唯一实际计算域边界，决定 OFT polygon、网格节点、
三角形、`region_ids`、`Mesh2D.outer_boundary`、Writer 输出和求解器计算域。

**LCFS 参考曲线**

```text
可选 GFile/EQDSK
  → gfile_reader.read_gfile()
  → OFT GEQDSKEquilibrium
  → boundary_R / boundary_Z
  → GFileData.lcfs_r / lcfs_z
  → Plotter
```

该对象只在 PNG 中作为平衡几何参考，帮助使用者比较 LCFS 与实际计算域边界的位置。
它不得作为 `array_file` 路径的 OFT polygon，不得改变节点、三角形、Region、
`region_ids` 或 `Mesh2D.outer_boundary`，不得写入 TRIMEG `Rbc/Zbc`、M3D-C1
TXT、SMB 或 helper exchange。

两条输入支路保持独立，只能在 CLI 把 `Mesh2D` 与可选 `GFileData` 一并传给
Plotter 时汇合：

```text
主网格支路：
array_file → boundary_reader → OFT Adapter → Mesh2D ─┐
                                                      ├→ Plotter → PNG
可选参考支路：                                        │
gfile → gfile_reader → GFileData ─────────────────────┘
```

`boundary_reader` 与 `gfile_reader` 不得互相调用。OFT Adapter、`Mesh2D`、Writer、
`M3DC1ModelSpec` 和 native helper 不得感知参考 GFile。不得把 array boundary
伪装成 LCFS，也不得把 LCFS 伪装成 array 实际计算边界。

### 5.3 内建默认值

| 字段 | 内建默认值 |
|---|---|
| `schema_version` | `1` |
| `target` | `"trimeg"` |
| `profile` | `"nested_three_region"` |
| `boundary_source` | `"artificial_outer"` |
| `mesh_dx` | `0.08`；仅用于 `single_region` |
| `plasma_dx` | `0.08`；仅用于 `nested_three_region` |
| `vacuum_dx` | `0.10`；仅用于 `nested_three_region` |
| `outer_dx` | `0.15`；仅用于 `nested_three_region` |
| `verbose` | `False` |
| `plot_lcfs` | `False`（已批准、尚未实现） |
| `gfile_path` | `None` |
| `array_file_path` | `None` |
| `hdf5_path` | target 为 `trimeg` 时为当前工作目录下 `mesh.h5` |
| `plot_path` | `None` |
| `model_path` | `None` |
| `smb_path` | `None` |

裁决规则：

- `mesh.h5` 是配置合并后的 target 条件默认值，不是 `--hdf5`/`--h5` 的 argparse 默认值。
- `smb_path` 不存在 `mesh.smb` 隐式默认值。`target=m3dc1` 时必须通过配置文件或
  显式 CLI 提供。
- `gfile_path=None`。是否必需由 `boundary_source` 和 required-fields 决定。
- `outer_padding` 和 `merge_thresh` 不是配置字段。
- 默认行为保持 `trimeg + nested_three_region + artificial_outer`。

### 5.4 `linkmesh.in` TOML v1

顶层必须包含：

```toml
schema_version = 1
```

只允许：

```text
顶层：
  schema_version

[task]
  target

[input]
  gfile
  array_file

[domain]
  profile
  boundary_source

[mesh]
  mesh_dx
  plasma_dx
  vacuum_dx
  outer_dx

[output]
  hdf5
  plot
  model
  smb
  plot_lcfs

[runtime]
  verbose
```

| TOML 键 | 类型 | 映射 |
|---|---|---|
| `schema_version` | 非布尔整数，必须为 `1` | `schema_version` |
| `[task].target` | 枚举字符串 | `target` |
| `[input].gfile` | 非空字符串 | `gfile_path` |
| `[input].array_file` | 非空字符串 | `array_file_path` |
| `[domain].profile` | 枚举字符串 | `profile` |
| `[domain].boundary_source` | 枚举字符串 | `boundary_source` |
| `[mesh].mesh_dx` | 有限正数 | `mesh_dx`；仅适用于 `single_region` |
| `[mesh].plasma_dx` | 有限正数 | `plasma_dx`；仅适用于 `nested_three_region` |
| `[mesh].vacuum_dx` | 有限正数 | `vacuum_dx`；仅适用于 `nested_three_region` |
| `[mesh].outer_dx` | 有限正数 | `outer_dx`；仅适用于 `nested_three_region` |
| `[output].hdf5` | 非空字符串 | `hdf5_path` |
| `[output].plot` | 非空字符串 | `plot_path` |
| `[output].model` | 非空字符串 | `model_path` |
| `[output].smb` | 非空字符串 | `smb_path` |
| `[output].plot_lcfs` | TOML bool | `plot_lcfs`；默认 `false`；已批准、尚未实现 |
| `[runtime].verbose` | TOML bool | `verbose` |

严格规则：

1. 未知顶层键、section 或 section 内键立即报 `ConfigError`。
2. section 必须为 table。
3. 路径必须为非空字符串。
4. dx 接受整数或浮点数，拒绝 bool、NaN、Inf、零和负数。
5. `verbose` 只接受 TOML bool。
6. TOML 语法、读取和 schema 错误必须包含文件路径和字段位置。
7. 配置层不读取业务文件，不创建目录。
8. `examples/m3dc1_single_region/linkmesh.in.example` 已存在；示例不产生新规则，
   也不开放未实现组合。

### 5.5 CLI 参数与 `UNSET`

| CLI 参数 | argparse 目标 | 合并语义 |
|---|---|---|
| `--config PATH` | `config` | 指定唯一配置文件 |
| `--no-config` | `no_config` | 禁止自动发现 |
| `--target VALUE` | `target` | 覆盖 `[task].target` |
| `--profile VALUE` | `profile` | 覆盖 `[domain].profile` |
| `--boundary-source VALUE` | `boundary_source` | 覆盖 `[domain].boundary_source` |
| `--gfile PATH` | `gfile` | 覆盖 `[input].gfile` |
| `--array-file PATH` | `array_file` | 覆盖 `[input].array_file` |
| `--mesh-dx FLOAT` | `mesh_dx` | 覆盖 `[mesh].mesh_dx`；仅适用于 `single_region` |
| `--plasma-dx FLOAT` | `plasma_dx` | 覆盖 `[mesh].plasma_dx`；仅适用于 `nested_three_region` |
| `--vacuum-dx FLOAT` | `vacuum_dx` | 覆盖 `[mesh].vacuum_dx`；仅适用于 `nested_three_region` |
| `--outer-dx FLOAT` | `outer_dx` | 覆盖 `[mesh].outer_dx`；仅适用于 `nested_three_region` |
| `--hdf5 PATH` / `--h5 PATH` | `hdf5` | 完全同义；覆盖 `[output].hdf5`，最终形成 `EffectiveConfig.hdf5_path` |
| `--plot PATH` | `plot` | 覆盖 `[output].plot` |
| `--model PATH` | `model` | 覆盖 `[output].model` |
| `--smb PATH` | `smb` | 覆盖 `[output].smb`，表示未插 rank 的基础路径 |
| `--plot-lcfs` | `plot_lcfs` | 显式出现时覆盖 `[output].plot_lcfs` 为 `True`；已批准、尚未实现 |
| `--verbose` | `verbose` | 显式出现时覆盖为 `True` |

参与合并的 CLI 参数必须使用 `UNSET` 区分未提供与显式提供。CLI 层不得通过业务默认
值覆盖 TOML。

TRIMEG HDF5 输出路径的正式 CLI 参数是 `--hdf5 <PATH>`，`--h5 <PATH>` 是完全同义
别名。二者属于同一个 argparse option action，写入同一个 `hdf5` dest，并沿既有
`hdf5 → hdf5_path` 路径进入 `EffectiveConfig.hdf5_path`。同一命令重复提供
`--hdf5`、`--h5` 或二者组合时，遵循 argparse 对同一 action 的既有确定性行为，不
新增自定义冲突层。旧参数 `--output` 已一次性删除，必须作为未知参数由 argparse
拒绝；不得保留兼容别名、弃用警告或静默回退。

该修正只涉及 CLI 用户接口命名，不新增 target、Writer、输出格式、TOML 键或
`EffectiveConfig` 字段。TOML `[output].hdf5`、target=trimeg 的 required-field
`hdf5_path`、`--no-hdf5` 的配置与执行语义、`--plot`、`--model`、`--smb`、
mesh_only 和 m3dc1 行为均保持不变。HDF5 Writer 函数签名以及 TRIMEG 完整 11
数据集的路径、shape、dtype、索引和 `outer_boundary` 契约也保持不变。

附加规则：

- `--config` 与 `--no-config` 互斥。
- `--verbose` 未出现时保持 `UNSET`。
- `--plot-lcfs` 正式拼写使用连字符，不提供 `--plot_lcfs`；未出现时保持 `UNSET`，
  使 TOML `[output].plot_lcfs` 不被 argparse 默认值覆盖。
- `CliOverrides` 实施时新增 `plot_lcfs`，并沿同名标量字段合并到
  `EffectiveConfig.plot_lcfs`。
- `--no-hdf5` 和 `--no-smb` 是执行期开关，不进入 `EffectiveConfig`，不取消
  required-fields；`--no-hdf5` 不改变 `--hdf5`/`--h5` 的配置合并语义。
- 历史 Python Triangle 参数 `--min-angle` 与 `--max-area` 已从正式 CLI 删除。
  前者曾表示旧路径最小角度，后者曾表示旧路径最大三角形面积；OFT 正式路径不消费
  二者。不得保留兼容别名、隐藏入口或弃用警告，使用时由 argparse 按未知参数拒绝。
- CLI 不将 `--smb` 改写为 rank-0 文件名。
- CLI 不解析 `LINKMESH_SCOREC_HELPER`。
- CLI 不硬编码 PUMI 安装路径。

### 5.6 配置发现和三层合并

发现顺序：

1. 同时提供 `--config` 和 `--no-config`：失败。
2. 提供 `--config PATH`：只读取该文件；不存在或非普通文件时失败。
3. 提供 `--no-config`：不加载配置。
4. 均未提供：只检查当前工作目录的 `linkmesh.in`。
5. 不递归父目录，不搜索主目录或仓库根，不从环境变量发现配置。

优先级：

```text
内建默认值 < linkmesh.in < 用户显式 CLI
```

算法：

1. 发现并严格解析 TOML。
2. TOML 相对路径以配置文件目录为基准。
3. CLI 相对路径以进程当前工作目录为基准。
4. 标量先取显式 CLI，否则 TOML，否则内建默认值。
5. 路径键映射：
   `gfile→gfile_path`、`array_file→array_file_path`、
   `hdf5→hdf5_path`、`plot→plot_path`、`model→model_path`、
   `smb→smb_path`。
6. 路径使用 `Path.resolve(strict=False)` 等价语义，不展开 `~` 或环境变量。
7. 合并后再次校验枚举、数值和 bool。
8. `plot_lcfs` 按同一标量规则取显式 CLI，否则 TOML，否则默认 `False`，并严格校验
   为 bool。
9. `mesh_dx` 和三个区域 dx 分别按同一优先级合并并校验为有限正数。
10. 使用 `CliOverrides` 是否为 `UNSET` 及 TOML 是否含键，在局部判断尺度是否显式提供：
    - `single_region` 只允许显式 `mesh_dx`，显式区域 dx 必须失败；
    - `nested_three_region` 只允许显式三个区域 dx，显式 `mesh_dx` 必须失败；
    - 内建默认值不构成冲突。
11. 构造冻结的 17 字段 `EffectiveConfig`，不保存来源信息。
12. 执行兼容矩阵、required-fields 和阶段闸门。
13. 全部通过后才进入 Reader、OFT、Writer 或 Plotter。

配置层不要求输出文件已经存在，不创建父目录。输入业务文件存在性由 Reader 报告。
helper 定位不属于 `EffectiveConfig`。

### 5.6A 网格尺度适用性与 Adapter 兼容映射

网格尺度按 profile 严格消歧：

1. `profile=single_region` 只使用 `mesh_dx`，单位 m。该字段表示单一计算域的目标
   网格长度尺度，不表示 plasma、vacuum 或 outer 的物理区域尺度。用户通过 TOML
   或 CLI 显式提供任一 `plasma_dx/vacuum_dx/outer_dx` 时必须 `ConfigError`。
2. `profile=nested_three_region` 只使用 `plasma_dx/vacuum_dx/outer_dx`，分别表示
   三个物理区域的目标尺度。用户显式提供 `mesh_dx` 时必须 `ConfigError`。
3. 所有字段保留内建默认值，但冲突只根据 TOML/CLI 显式性判断，默认值不得制造冲突。
4. 同一适用字段继续遵循内建默认值 < TOML < 显式 CLI。
5. 不建立任意 N 区域尺度配置语言。

现有 OFT Adapter 公共签名保持不变。CLI 对 single-region 执行唯一兼容映射：

```text
EffectiveConfig.mesh_dx
  → generate_mesh(..., plasma_dx=cfg.mesh_dx, profile="single_region", ...)
```

该映射只适配既有 Adapter 参数名，不把 single-region 重新定义为 plasma 物理区域；
Adapter 的 single-region 分支仍只消费该一个尺度。本轮不修改 `oft_adapter.py`。

### 5.6B CLI help 分组

argparse 帮助按用户任务顺序分组：

1. `Configuration`：`--config`、`--no-config`；
2. `Task`：`--target`、`--profile`、`--boundary-source`；
3. `Input`：`--gfile`、`--array-file`、`--plot-lcfs`；
4. `Mesh Resolution`：`--mesh-dx`、`--plasma-dx`、`--vacuum-dx`、`--outer-dx`；
5. `Output`：`--hdf5/--h5`、`--model`、`--smb`、`--plot`、
   `--no-hdf5`、`--no-smb`；
6. `Runtime`：`--verbose`。

`-h/--help` 继续由 argparse 自动提供。不得重复注册参数或手写整段帮助输出。

### 5.7 `array_file` v1：counted R-Z boundary text

状态为 **IMPLEMENTED / PASSED**。正式语法为：

```text
N
R_1 Z_1
R_2 Z_2
...
R_N Z_N
```

| 项目 | 正式契约 |
|---|---|
| 文件 | 纯文本；扩展名不参与格式判断，无扩展名合法 |
| 计数头 | 第一行只包含一个十进制整数 `N`，且 `N >= 3` |
| 数据行数 | 计数头后必须恰好有 `N` 行，不得少、多或包含额外数据 |
| 坐标行 | 每行恰好两个有限浮点数，以一个或多个空白字符分隔 |
| 列与单位 | 第一列 R，第二列 Z；单位 m |
| 输出 | 独立 `(N,2) float64` 数组 |
| 闭合 | 输入隐式闭合；首末点不得重复；最后一点由 LinkMesh 连接回第一点 |
| 几何 | 至少 3 个互异节点；无相邻重复、零长度闭合边、零面积或自交；P0 只允许一条简单闭环 |
| 方向 | 输入可顺时针或逆时针；进入 `Mesh2D.outer_boundary` 前规范为顺时针并保持起点 |

P0 明确不支持 CSV 逗号分隔、表头、注释、索引列、额外列、空数据行或多条轮廓。
不得根据文件名或内容猜测其他格式，不得自动排序、重采样、全局去重、平滑、缩放、
投影或最近距离修补，也不得把外部边界自动解释为 LCFS、第一壁或磁通面。EAST
原始点序为逆时针不改变 `Mesh2D.outer_boundary` 的全局顺时针契约。

已实现接口为：

```text
src/linkmesh/readers/boundary_reader.py
read_boundary_file(filepath: str | Path) -> np.ndarray
```

职责与错误边界：

1. Reader 只读取并验证 counted R-Z boundary text，返回独立 `(N,2) float64`。
2. 文件不存在或不可读取沿用 `FileNotFoundError`/`OSError`。
3. 文件语法错误与数值词法错误使用 `BoundaryFormatError(ValueError)`，错误信息包含
   路径、行号和原因。
4. 成功解析后先按现有方向约定规范化并保持起点，再复用 `mesh.py` 的统一
   `_validate_outer_boundary`；几何非法沿用 `ValueError`。
5. Reader 不解析 GFile，不构造 OFT Domain 或 `Mesh2D`，不生成网格，不判断物理
   来源，不执行平滑、重采样、排序、全局去重或缩放，不使用 pandas。
6. CLI 只调用 Reader 并编排后续流程，不自行读取或验证文件内容。

EAST 直接证据：

- 路径 `/data/liuchang/east_fishbone_1/EAST`；
- 无扩展名纯文本，`N=104`，随后恰好 104 行 R-Z 米制坐标；
- shape 为 `(104,2)`，首末不重复，隐式闭合，输入逆时针且无自交；
- R 约为 `1.465..2.269 m`，Z 约为 `-0.627..0.563 m`；
- 面积约 `0.7211 m²`，周长约 `3.1574 m`；
- 图形和量级符合 EAST 二维极向截面的工程预期；
- 它是与 EQDSK、M3D-C1 TXT 和 SMB 分离的外部二维计算边界；
- 具体物理构造算法及其与 LCFS、第一壁、磁轴和 X-point 的精确关系仍为
  PENDING，但不阻塞读取已由研究人员确认的最终边界。

### 5.7A `array_file + GFile LCFS reference` 候选工作流

状态：**DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED**。

正式目标命令：

```text
python -m linkmesh \
  --target trimeg \
  --profile single_region \
  --boundary-source array_file \
  --array-file <boundary-path> \
  --plot-lcfs \
  --gfile <gfile-path> \
  --plot <png-path> \
  --hdf5 <hdf5-path>
```

参数语义：

- `--boundary-source array_file`：array file 是唯一实际计算域边界。
- `--array-file PATH`：提供实际计算域边界。
- `--plot-lcfs`：要求读取 GFile LCFS 并叠加到 PNG。
- `--gfile PATH`：仅在该组合中提供 LCFS 参考数据，不参与网格生成。
- `--plot PATH`：提供包含实际网格边界和 LCFS reference 的 PNG 路径。
- 既有 `boundary_source=lcfs` 或 `artificial_outer` 路径中，`gfile_path` 继续承担
  原有网格输入职责，新功能不得改变其语义。

合法组合：

1. 纯 `array_file`：提供 `array_file_path`，`plot_lcfs=False`，不要求或读取 GFile。
2. `array_file + LCFS reference`：同时提供 `array_file_path`、`gfile_path`、
   `plot_path`，并设置 `plot_lcfs=True`。

必须在配置层失败：

1. `array_file + plot_lcfs=True` 缺少 `gfile_path`。
2. `array_file + plot_lcfs=True` 缺少 `plot_path`。
3. `array_file` 同时提供 `gfile_path` 但 `plot_lcfs=False`。
4. 非 `array_file` 路径设置 `plot_lcfs=True`。
5. `[output].plot_lcfs` 类型不是 bool。
6. 配置文件使用未知键。

业务执行阶段必须明确失败：

1. 参考 GFile 无法读取。
2. OFT `GEQDSKEquilibrium` 未提供可用 LCFS，或 LCFS shape、有限性、最低点数
   不满足 `GFileData`/Plotter 参考曲线要求。
3. 参考 LCFS 完全或部分位于实际计算域外。首版将其定义为明确的非致命诊断：
   必须向终端输出英文 warning，说明 LCFS reference 不完全位于 actual mesh
   boundary 内；仍允许生成 PNG，且不得据此修改、裁剪或拒绝实际网格。不得静默
   假定二者包含关系有效。

CLI 编排要求：

1. 正好读取一次 boundary file，形成唯一 Mesher 输入。
2. `plot_lcfs=True` 时正好读取一次 GFile，形成只供 Plotter 使用的 `GFileData`。
3. `GFileData` 不传给 OFT Adapter、`Mesh2D`、Writer、ModelSpec 或 helper。
4. 两条支路只在 `plot_mesh(gfile_data, mesh, plot_path, ...)` 调用处汇合。
5. `plot_lcfs=False` 的旧 `array_file` 路径继续把 `None` 传给 Plotter，并且完全
   不读取 GFile。

绘图语义：

- PNG 至少视觉区分三角网格、actual mesh boundary 和可选 LCFS reference。
- 图例不得把 array boundary 标为 LCFS，不得把 LCFS 标为 mesh boundary，不得把
  limiter contour 标为 LCFS。
- LCFS 可使用虚线，但正式契约只要求视觉和图例可区分，不固定颜色。
- 坐标轴保持 R、Z，单位 m。
- PNG 只用于几何检查，不代表 TRIMEG/M3D-C1 已加载、初始化、时间推进或物理验证。

确定性不变量：

对同一个 array file 和同一组网格参数，以下两次执行：

- A：不提供参考 GFile；
- B：提供 GFile 并启用 `plot_lcfs`；

必须产生完全相同的 `Mesh2D.nodes`、`triangles`、`region_ids`、
`outer_boundary`、TRIMEG 11 个 dataset 的路径/shape/dtype/值，以及 M3D-C1
TXT/SMB 的几何和 classification 输入。唯一允许差异是 B 的 PNG 增加 LCFS
reference。若 HDF5 容器存在非确定性元数据，不要求比较整个文件原始字节。

该工作流不新增 `Mesh2D` 字段，不修改任何 Writer、`M3DC1ModelSpec`、helper
exchange schema 或目标格式。

### 5.7B `multi_array_file` 与 `regions` 两阶段设计

状态：**DESIGNED / NOT IMPLEMENTED；OFT N-region、编号与 no-plasma 前置调查已完成**。
专项证据与设计见 `docs/linkmesh/multi_array_regions_investigation_report.md`。

#### 5.7B.1 OFT 能力边界

OFT 26.6 官方文档和本地源码确认：

1. `gs_Domain`、Region 容器和 Triangle regionlist 不是固定三区域实现。
2. 官方 ITER 多区域示例使用多个 Region，并为不同 Region 提供不同常数 dx。
3. OFT 提供 `define_region()`、`add_polygon()`、`add_annulus()`、
   `add_enclosed()`、`add_rectangle()`、`plot_topology()` 和 `build_mesh()`。
4. 调用者通过 contour、Region name 和 `parent_name` 显式提供已知区域关系。
5. OFT 不提供“输入任意一组无序闭合曲线后自动建立完整包含树”的高级接口。
6. 官方工作流使用 topology plot 和最终 mesh plot 人工检查几何与 Region。

本地源码进一步确认：Region seed、数值 attribute 和 `dx^2/2` 最大面积约束进入
Triangle `regionlist`；Triangle 将 attribute 传播到三角形；OFT 从
`triangleattributelist` 读回。数值可能以浮点存储传递，但业务语义是离散 Region
标签。

OFT 官方能力不等于 LinkMesh 已实现 `multi_array_file`，也不证明 LinkMesh 候选的
sibling、四层以上嵌套、混合拓扑、共享界面和编号稳定性已经通过。

#### 5.7B.2 输入格式和拓扑前提

1. 新来源命名为 `boundary_source="multi_array_file"`；旧 `array_file` 契约不变。
2. 文件由至少两个 counted R-Z block 顺序组成直到 EOF。
3. 文件开头、文件结尾、block 之间以及一个 block 的点数据之间均允许零个或多个
   空行；Reader 忽略空行。完全没有空行的连续 block 同样合法。
4. 空行只影响文本布局，不改变 `curve_id`、Region 身份或包含关系，也不作为 block
   结束标志。block 只由计数 `N` 和随后读取到的 N 个有效 R-Z 数据行确定。
5. 每个 block 的首个有效行必须只包含十进制整数 `N`，且 `N>=3`；随后必须取得
   恰好 N 个有效数据行。每个数据行严格为两个有限浮点数 `R Z`，R 在前、Z 在后，
   单位 m。
6. EOF 前当前 block 未取得 N 个有效点、计数非法、数据非浮点或数据行不是恰好两列
   时必须失败。
7. 首版不支持 `#`、`;`、`//` 或其他注释语法；每个非空行必须是当前语境下的计数行
   或 R-Z 数据行。未来支持注释必须先升级蓝图。
8. 每条曲线隐式闭合，末点不重复首点。
9. block 顺序生成从 1 开始的稳定 `curve_id`。
10. `curve_id` 只追踪输入曲线，不是 Region ID。
11. 不从方向、面积、坐标、顺序或颜色猜测 plasma、vacuum、wall、conductor 等物理
    名称。
12. 只有一个 block 时 `regions inspect` 必须拒绝，并提示用户改用既有
    `array_file + single_region` 入口；不得自动升级、降级或改变旧 `array_file`
    契约。

首版输入前提：

- 曲线是简单闭合曲线，不自交；
- 不同曲线不相交、不相切、不重合；
- 曲线之间为明显严格包含或明显完全分离；
- 恰好一条唯一最外层 root；
- 其他曲线位于 root 内；
- 不支持多个独立计算域；
- 不支持无人占据、完全不剖分的 Triangle hole。

每条曲线定义一个候选 Region：本曲线内部减去全部直接 child 曲线内部。child 不是
不生成网格的 hole，而是由另一个 Region 占据的内部区域；对 parent 而言，child
边界是内部界面。允许多层嵌套、一个 parent 带多个 sibling children，以及二者组合，
但 LinkMesh/OFT 实际行为仍待探针。

#### 5.7B.3 首版轻量包含推导和几何边界

首版只设计：

1. counted blocks 完整解析；
2. `(N,2)`、有限值、最低点数、精确相邻重复、精确零长度闭合边和明显退化面积检查；
3. 为每条曲线获得单 polygon 内部代表点；
4. 使用 OFT `Region.check_in_poly()` 基础能力建立候选包含矩阵；
5. 为每条非 root 曲线选择直接 parent；
6. 验证唯一 root、无环和全部节点可达；
7. 输出 regions map 和 inspection PNG；
8. generate 后检查每个正式 Region 至少有一个三角形并输出 mesh PNG。

该流程不是 OFT 自动包含树，也不是完整 polygon containment 证明。对交叉、相切、
重合、近接触或复杂部分重叠可能误判；用户必须检查 inspection PNG 和 mesh PNG。
人工检查不是数学证明，Triangle 成功也不表示任意异常几何合法。

首版不实现 Bentley-Ottmann、通用扫描线、完整自交/相切/重合分类、DE-9IM、复杂
浮点容差体系、polygon boolean、Shapely/GEOS 运行时依赖、自动几何修复或通用区域
DSL。若真实输入证明轻量方案不足，必须先更新蓝图。

`Region.get_in_point()` 只为单一 polygon 提供内部 seed 候选，不能证明 seed 位于
parent-minus-children 的实际 Region。父 Region seed 被 child 覆盖和 Region
不连通风险必须由探针验证。

#### 5.7B.4 正式 Region ID

1. 不建立第二套面向用户的 LinkMesh Region 编号。
2. OFT 完成内部编号后的最终 Triangle Region attribute 是正式 Region ID。
3. 该 ID 用于 regions map、inspection PNG、`--region-dx`、
   `Mesh2D.region_ids` 和后续验证。
4. Region ID 是离散标签，不是数组位置，不按出现顺序解释，不执行节点索引式 `+1`。
5. `curve_id` 仅表示输入 block 顺序；regions map 说明 curve、包含关系和最终
   Region ID 的对应。
6. 程序可在内存中保存 OFT region name、technical role、curve_id、final attribute
   和 dx 的运行时对应，但这不是第二套正式 Region ID。

本地源码确认 `build_mesh()` 在 Triangle 调用前按 OFT technical role 和
`region_info` 遍历顺序重新分配 ID，并更新 `region_info`、`Region._id` 和
`_extra_reg_defs`。最终 ID 进入 Triangle regionlist，并从 triangle attributes
读回。以下仍待探针：

- `setup_only=True` 是否可取得最终编号；
- setup 前后 `region_info` 和 `Region._id` 的变化；
- 同一 Domain 重复调用；
- inspect/generate 分别重建后的编号一致性；
- 改变 dx 后的编号稳定性；
- block 重排对 curve_id 和 Region ID 的影响；
- setup 编号与最终 Triangle attribute 是否一致；
- `Mesh2D.region_ids` 与 regions map 是否一致。

#### 5.7B.5 OFT technical role 与用户物理语义隔离

OFT technical role 是 `gs_Domain` API 的技术分类，由 LinkMesh OFT Adapter 在
Domain 组装时提供。OFT 26.6 支持 plasma、boundary、vacuum、conductor、coil 等
类别；technical role 参与 Domain 前置检查和 Region 编号，但不表示用户已经确认的
材料、物理区域或求解器语义。

no-plasma 对照探针已确认：

- 唯一 root 使用 boundary、全部内部 Region 使用 vacuum 且不存在 plasma 时，
  `setup_only=True` 和完整 `build_mesh()` 均失败；
- 准确异常为 `ValueError: No plasma region specified`；
- 异常来自已安装 OFT 26.6 `gs_Domain.build_mesh()` 的前置检查，不是 Triangle
  建网失败；
- setup-only 不能绕过要求；
- 当前不尝试空 `reg_type`、未经支持的 generic 类型、绕过 `gs_Domain` 或由
  LinkMesh 直接接管 Triangle 输入构造。

首版 multi-array 使用 synthetic plasma compatibility role。它是 Adapter 为满足
OFT 26.6 强制前置条件而赋给一个既有内部 Region 的 technical role，不新增曲线、
Region、网格层或物理材料，也不是 M3D-C1 的真实 plasma classification。

确定性规则：

1. 唯一 root Region 使用 `boundary`。
2. 在全部内部 Region 中选择包含树深度最大的 leaf，使用 `plasma`。
3. 最大深度 leaf 并列时，选择 `curve_id` 最小者。
4. 其余内部 Region 使用 `vacuum`。

该规则必须可重复，不依赖 `physical_label`，不根据坐标、面积、颜色或物理名称猜测
plasma。输入 block 重排可能改变 curve_id 平局裁决和同类 technical role 内的最终
Region ID，因此重排后必须重新执行 inspect。

multi-array 首版必须至少包含两条曲线，即一条唯一 root 和至少一个内部 Region。
只有一条曲线时 `regions inspect` 必须拒绝，并提示使用既有
`array_file + single_region`；不得自动切换 boundary source 或复用旧单 block
Reader 放宽其契约。

现有 single-region Adapter 已使用 `domain.define_region("plasma", ..., "plasma")`
满足同类 OFT 建网要求。该 technical role 只存在于 OFT Domain 构造和编号阶段；
当前数据链只把 `pts/lc/reg` 与有序外边界转换为 `Mesh2D`，未发现 technical role
被传播为 Writer 或外部格式中的用户物理语义。用户也不需要声明 plasma/vacuum。

regions map 的 `physical_label` 是独立的可选用户字段，默认空字符串。留空不得阻塞
inspect 或 generate，且当前不得参与包含树、technical role、Region ID 或 dx 决策，
不得自动驱动 Writer、M3D-C1 classification 或求解器物理语义。任何下游连接必须先
升级蓝图。

#### 5.7B.6 正式 CLI 设计

正式二级子命令：

```text
linkmesh regions inspect [参数]
linkmesh regions generate [参数]
```

`regions generate` 新增且仅在该二级子命令作用域内提供：

```text
--target {mesh_only,trimeg}
--hdf5 PATH
```

正式语义：

- `target=mesh_only` 是默认值，生成 N-region `Mesh2D` 和 mesh PNG，不调用 HDF5
  Writer，并禁止提供 `hdf5_path`；
- `target=trimeg` 生成同一个 N-region `Mesh2D`、调用一次既有 TRIMEG HDF5 Writer，
  并继续生成 mesh PNG；必须提供 `hdf5_path`；
- `--target` 属于 generate 的 `Task` 分组，`--hdf5` 与 `--plot` 属于 generate 的
  `Output` 分组；
- 不在 `regions` 父解析器增加 target；`regions inspect` 不接受 target、hdf5 或
  Writer 参数；
- 顶层旧 `--target` 仍只属于标准无子命令工作流，其作用域和行为不变；
- 不增加 `--no-hdf5`，不开放 `target=m3dc1`，也不增加 model、smb 参数。

正式帮助层级：

```text
linkmesh -h
linkmesh regions -h
linkmesh regions inspect -h
linkmesh regions generate -h
```

规则：

- 旧无子命令入口及其帮助和行为保持不变；
- inspect 与 generate 分别拥有独立 required fields；
- regions 参数必须位于对应二级子命令作用域内，不与旧入口参数任意混写；
- 不同 argparse 子解析器可以定义同名参数；
- 旧入口 `--mesh-dx` 作用于 single-region；
- regions generate `--mesh-dx` 表示全部 Region 的默认尺度，单位 m；
- inspect `--plot` 表示曲线、包含关系和 Region ID 图；
- generate `--plot` 表示最终多区域三角网格图；
- 阶段不得根据 dx 或输出参数是否存在隐式推断；
- `regions` 支持 `--config` 和完整长 CLI，优先级继续为默认值 < 配置 < 显式 CLI。

regions 使用独立配置解析模型，不向旧入口固定 17 字段 `EffectiveConfig` 或旧
TOML v1 允许键集合塞入动态 Region 字段。首版正式配置结构为：

```toml
schema_version = 1

[regions]
mode = "generate"
target = "trimeg"
multi_array_file = "boundaries.txt"
regions_map = "regions.toml"
plot = "mesh.png"
hdf5 = "mesh.h5"

[regions.mesh]
mesh_dx = 0.08

[regions.mesh.region_dx]
1 = 0.03
2 = 0.05
```

规则：

1. `mode` 只允许 `"inspect"` 或 `"generate"`，并必须与实际二级子命令一致。
2. inspect required fields 为 `multi_array_file`、`regions_map`、`plot`。
3. generate required fields 为 `multi_array_file`、`regions_map`、`plot`；默认
   `target="mesh_only"`，`hdf5_path=None`。
4. generate target 只允许字符串 `"mesh_only"` 或 `"trimeg"`；
   `target=trimeg` 时 hdf5 必需，`target=mesh_only` 时 hdf5 禁止。
5. inspect 与 generate 均支持 `--config` 和完整长 CLI；用户不得被强制只使用配置。
6. 优先级固定为内建默认值 < TOML < 显式 CLI。
7. 配置文件相对路径相对配置文件目录，显式 CLI 相对路径相对当前工作目录；
   `hdf5_path` 最终规范化为绝对 `Path`。
8. `multi_array_file_path`、`regions_map_path`、`plot_path` 和存在时的
   `hdf5_path` 两两不同，规范化后冲突必须失败。
9. regions 配置不得被旧无子命令入口加载为动态字段，旧配置发现、schema 和行为保持
   不变。
10. `[regions.mesh.region_dx]` 是最终 Region ID 到浮点 dx 的显式映射，不允许位置
    列表。
11. 配置层不读取边界或 map 内容，不构造 `Mesh2D`，不调用 OFT/Writer，也不打开或
    创建 HDF5。

#### 5.7B.7 regions map 和 dx

inspect 必须写出 TOML regions map；inspection PNG 与 map 共同展示本次输入的包含
关系和最终 Region ID。generate 必须同时读取原始 `multi_array_file` 和该 regions
map；map 是 generate required input，generate 不得只根据 `--region-dx` 数字猜测
Region 身份。

首版最小 schema：

```toml
schema_version = 1

[[regions]]
region_id = 1
curve_id = 3
parent_region_id = 2
child_region_ids = []
color = "#D55E00"
physical_label = ""
```

正式字段：

- `schema_version`：固定为整数 `1`；
- `region_id`：本次 inspect 取得的 OFT 最终 Region attribute；
- `curve_id`：输入 block 编号；
- `parent_region_id`：正式 Region ID；唯一 root 使用 `0` 表示无 parent；
- `child_region_ids`：正式 Region ID 列表，按升序确定性写出；
- `color`：确定生成且可区分的显示颜色，用于 map 与 inspection PNG 对照；
- `physical_label`：普通 TOML 字符串，默认 `""`，可由用户在 inspect 后编辑。

`physical_label` 不要求非空或唯一，不赋予枚举语义；留空不得阻塞 inspect 或
generate。generate 读取并保留该字段，但当前不得据其值改变包含树、synthetic
plasma、OFT technical role、Region ID、dx、Writer、M3D-C1 classification 或求解器
行为。当前没有依据增加任意长度限制。

`color` 只表示显示身份，不表示材料或物理类型，不参与 OFT、dx、Writer 或网格结果；
用户修改颜色不得改变网格。可选 diagnostics/internal 可记录 OFT Region name、
technical role、`technical_role_source="adapter_compatibility"` 和
`physical_semantics=false`，但不得成为用户必填字段，也不得与
`physical_label` 混写。

regions map 不包含 `input_sha256`。inspect 不计算或保存输入摘要，generate 不计算或
校验摘要，也不得以摘要不一致拒绝输入。用户负责保证 inspect 与 generate 使用同一份、
未被实质修改或重排的输入。

generate 必须重新读取 multi-array 文件、分配 `curve_id`、执行基础检查、推导轻量
包含树、重新应用 synthetic technical-role 规则、构造新 OFT Domain 并取得最终
Region ID，然后至少核对：

1. curve 数量；
2. `curve_id` 集合；
3. `region_id` 集合；
4. `curve_id → region_id` 对应；
5. `parent_region_id`；
6. `child_region_ids`；
7. synthetic technical-role 规划重算后产生的最终编号；
8. map 中不存在重复或未知 ID。

冲突必须失败并提示重新执行 `regions inspect`。首版不承诺检测只改变空行、等价数值
文本、未改变结构和编号的坐标微调，或保持相同曲线数量与包含关系的任意输入修改。

regions generate 的尺度参数：

```text
--mesh-dx 0.08
--region-dx 1=0.03 --region-dx 2=0.05
```

正式规则：

1. 只提供 `--mesh-dx`：全部 Region 使用统一值。
2. 同时提供 `--mesh-dx` 和一个或多个 `--region-dx`：局部值覆盖指定 Region，
   其他 Region 使用全局值。
3. 不提供 `--mesh-dx`：`--region-dx` 必须完整覆盖 map 中全部 Region ID。
4. 重复 ID、未知 ID、缺失且无全局默认值、非有限 dx 或 `dx<=0` 均失败。
5. 单位为 m。
6. 不允许位置数组或输入顺序隐式映射；用户必须依据 regions map 的最终 Region ID
   设置局部尺度。

#### 5.7B.8 多区域 TRIMEG 分派与当前边界

`regions generate` 在完整网格生成、map 核对、dx 解析和每 Region 三角形非空检查
通过后，按 target 分派同一个 `Mesh2D`：

```text
target=mesh_only → mesh PNG
target=trimeg    → 既有 write_hdf5(mesh, hdf5_path) + mesh PNG
```

TRIMEG 分派必须延迟导入并只调用一次既有 Writer，不重新生成网格、不构造第二个
`Mesh2D`、不修改 `region_ids`，也不向 Writer 传递 regions map、color 或
`physical_label`。Writer 成功返回后才可报告 HDF5 路径，异常不得吞掉。

多区域输出复用现有 complete-11 契约：

- 11 个 dataset 的路径、shape、dtype、索引和语义不变；
- `vert` 仍为 `(N,2)` 且不转置；
- `tria` 仍为 `(T,3)`，只在 Writer 内由 0-based 转为 1-based，不增加第四列；
- `Mesh2D.region_ids` 不写入当前 TRIMEG 文件；
- 内部 Region 界面保留在共形网格拓扑中，但当前 TRIMEG 文件不携带 LinkMesh
  Region 标签；
- `idxevert` 只来自最终三角形拓扑的外边界，内部 Region 界面不得误作外边界；
- `nbcRZ/Rbc/Zbc` 仍只来自 root 对应的 `Mesh2D.outer_boundary`。

状态分层：

- Writer 成功产生真实文件后为 `GENERATED`；
- h5py 对真实文件完成 complete-11 schema 和数据回读后为
  `STRUCTURALLY CHECKED`；
- 标准 MATLAB/TRIMEG consumer 成功读取后为 `LOADED`；
- PNG 或 mock Writer 调用不能证明 HDF5 已生成、结构已检查或 TRIMEG 已消费。

当前源码接线状态为 `IMPLEMENTED`。User 最新直接证据确认多区域 HDF5 已在服务器
生成，自动测试和实际检测均通过，因此文件状态更新为 `GENERATED`。由于未提供精确
passed 数、实际检测的完整字段清单或标准 consumer 日志，本蓝图不虚构测试数量、
dataset/shape 检测细节，也不将该证据提升为标准 MATLAB/TRIMEG consumer
`LOADED`；该消费层级继续为 `PENDING`。

- `nested_three_region` 暂不修改、删除或优化。
- 当前不修改 `Mesh2D` 字段、regions map schema、dx 规则、OFT technical role、
  TRIMEG schema、M3D-C1 model/SMB、classification 或 helper exchange。
- M3D-C1 本身能够进行多区域模拟，是 User 根据同门实际展示确认的求解器能力。
- VDOM 研究需要第一壁外薄层面电流 Region 和更外层模拟 Region，并要求不同常数 dx。
- LinkMesh 新多区域网格的 M3D-C1 实际兼容性为 **PENDING**，待网格生成后真实试用。
- 本阶段不调查或修改 M3D-C1 classification、TXT、SMB、helper、C1 或求解器源码。

### 5.8 `boundary_source`

| 来源 | 正式来源 | 状态 | 规则 |
|---|---|---|---|
| `lcfs` | `GFileData.lcfs_r/lcfs_z` | 已实现 | single-region 唯一边界；不使用第一壁或人工外框 |
| `first_wall` | `GFileData.wall_r/wall_z` | 未实现 | 需要有效第一壁；首版 single-region |
| `array_file` | counted R-Z boundary text | 已实现并通过 EAST 生成侧验收 | 首版 single-region；EAST 主线；v1 与 GFile 互斥 |
| `artificial_outer` | LCFS/第一壁包围盒加固定 padding | 已实现并完成生成侧真实验收 | 当前只配 nested；四角不直接作为 `outer_boundary` |
| `flux_surface` | 从 GFile 二维极向磁通场提取指定内部闭合磁通等值线 | 实现候选，未实现，待 OFT 26.6 只读侦察 | 只用于 single-region 核心或内部等离子体计算域；禁止缩放 LCFS 伪造 |
| `multi_array_file` | 重复 counted R-Z blocks | DESIGNED / NOT IMPLEMENTED；OFT 调查与产品接口裁决已完成 | 仅供未来 `regions` 命令族；唯一根包含树、代码几何检查、TOML map 和显式 Region ID/dx 映射 |

共同规则：

- 每次任务只有一个计算域外边界来源。
- `lcfs`、`first_wall`、`artificial_outer` 需要 GFile。
- `array_file` v1 需要 array file。纯 array 工作流继续禁止 GFile；已批准但尚未实现的
  `plot_lcfs=True` 例外允许额外 `gfile_path`，且该 GFile 只能提供 PNG LCFS
  reference，不得改变实际计算边界、网格或 Writer 输出。
- `flux_surface` 不是文件格式或第二网格生成器，不能替代需要包含 X-point 或其附近
  区域的 EAST 外部边界。本轮不批准其业务实现；后续必须先只读确认 OFT 26.6
  的磁通场、归一化磁通、轮廓提取、多轮廓选择、闭合和方向接口。
- 未实现来源不得回退。
- 已实现来源必须走 Region 捕获、build 后回写和统一验证。
- `multi_array_file` 不得由旧 `array_file` Reader 静默接收，也不得放宽旧单 block
  契约；业务实现和 OFT 探针通过前不得由现有 nested 成果外推为已支持。

### 5.9 兼容矩阵

| target | profile | boundary_source | 状态 |
|---|---|---|---|
| `mesh_only` | `nested_three_region` | `artificial_outer` | 已实现 |
| `trimeg` | `nested_three_region` | `artificial_outer` | 已实现并验收 |
| `mesh_only` | `single_region` | `lcfs` | 已实现 |
| `trimeg` | `single_region` | `lcfs` | 已实现并验收 |
| `m3dc1` | `single_region` | `lcfs` | 已实现；加载和初始化通过 |
| `mesh_only` / `trimeg` | `single_region` | `first_wall` | 规划有效，未实现 |
| `mesh_only` | `single_region` | `array_file` | 已实现 |
| `trimeg` | `single_region` | `array_file` | 已实现；不改变 HDF5 契约 |
| `m3dc1` | `single_region` | `array_file` | 已实现；EAST 生成侧通过，外部消费待验收 |
| `mesh_only` / `trimeg` / `m3dc1` | `single_region` | `array_file + plot_lcfs` | **DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED**；GFile 只供 PNG 参考，不改变 target 输出 |
| 任意非 `array_file` | 任意 | `plot_lcfs=True` | 禁止，使用 `ConfigError` |
| 任意 | `single_region` | `flux_surface` | 实现候选，未实现，待 OFT 26.6 只读侦察 |
| `regions generate --target mesh_only` | 多区域 | `multi_array_file` | IMPLEMENTED；N-region Mesh2D STRUCTURALLY CHECKED，PNG GENERATED 并人工复核 |
| `regions generate --target trimeg` | 多区域 | `multi_array_file` | IMPLEMENTED；真实 HDF5 GENERATED，User 确认自动测试和实际检测通过；标准 MATLAB/TRIMEG 加载 PENDING |
| `regions generate --target m3dc1` | 多区域 | `multi_array_file` | CANDIDATE / NOT OPEN；model、smb 与 schema v2 均未批准实施 |
| 旧无子命令入口 | 任意 | `multi_array_file` | 当前未开放；不得回退旧 `array_file` 或 nested |
| `m3dc1` | `single_region` | `first_wall` / `flux_surface` | 未开放 |
| `m3dc1` | `nested_three_region` | 任意 | 禁止 |
| 任意 | `nested_three_region` | `lcfs` / `first_wall` / `array_file` | 禁止 |
| 任意 | `single_region` | `artificial_outer` | 禁止 |

禁止组合使用 `ConfigError`。架构可表达但未实现的组合使用
`NotImplementedError`。旧测试若期待不同异常类型，应更新测试，不得放行组合。

### 5.10 required-fields

按边界来源：

| 来源 | 必需 | 禁止同时提供 |
|---|---|---|
| `lcfs` | `gfile_path` | `array_file_path` |
| `first_wall` | `gfile_path` | `array_file_path` |
| `artificial_outer` | `gfile_path` | `array_file_path` |
| `array_file`，`plot_lcfs=False` | `array_file_path` | `gfile_path` |
| `array_file`，`plot_lcfs=True` | `array_file_path`、`gfile_path`、`plot_path` | 无；`gfile_path` 仅作 LCFS PNG reference |
| `flux_surface` | 未定义，阶段闸门报未实现 | 不得猜测 |

按 target：

| target | 必需输出 | 行为 |
|---|---|---|
| `mesh_only` | 无 | 不写 HDF5、TXT、SMB |
| `trimeg` | `hdf5_path` | 未使用 `--no-hdf5` 时写 HDF5 |
| `m3dc1` | `model_path`、`smb_path` | 总写 TXT；未使用 `--no-smb` 时写 SMB |

`--no-smb` 不使 `smb_path` 可选；`--no-hdf5` 不改变有效配置结构。配置层只验证字段
存在和组合，不读取业务内容。

### 5.11 `single_region` 构造

#### 5.11.1 `single_region + lcfs`

1. 读取 `GFileData.lcfs_r/lcfs_z`。
2. 检查 shape、长度、有限性和最低点数，处理普通显式闭合末点。
3. 调用 `add_polygon()` 前稳定过滤相邻近重复点：
   - 保留第一点；
   - 按原顺序遍历；
   - 与最后一个已接受点距离严格小于 `1e-4 m` 时删除候选；
   - 否则保留；
   - 不排序、循环移位、插值、重采样、全局去重或改变保留坐标。
4. 过滤后至少 3 点。
5. 若首末距离仍小于 `1e-4 m`，失败。
6. 定义唯一 `plasma` region，尺度为 `plasma_dx`。
7. 调用一次 `add_polygon(lcfs, "plasma")`，无 parent。
8. 不使用第一壁，不创建 vacuum、annulus 或 artificial outer。
9. 通过 `domain.regions` 长度差捕获唯一新增 Region。
10. build 后读取同一 Region 的 `_resampled_points`。
11. 规范化并验证 `outer_boundary`。
12. `vacuum_dx`、`outer_dx`、`outer_padding` 不参与。
13. 不缩放 LCFS，不从最终拓扑反推边界。

#### 5.11.2 `single_region + first_wall`

当前未实现。规划契约：

- 使用有效 `wall_r/wall_z` 作为唯一 polygon；
- 首版尺度为 `plasma_dx`；
- 不创建 LCFS 内部界面、vacuum 或 artificial outer；
- 缺壁、点数不足、非有限、退化或非简单闭环时失败；
- 必须走 Region 捕获、build 后回写和统一验证；
- CLI 当前不得放行。

#### 5.11.3 `single_region + array_file`

正式契约已实现并通过 EAST 生成侧验收：

1. 调用 `read_boundary_file()` 获取经验证和方向规范化的唯一 `(N,2)` 计算边界。
2. v1 不读取 GFile；边界物理语义保持“外部提供的计算边界”。
3. 使用现有单区域尺度 `plasma_dx`，不新增同义尺度字段。
4. 复用统一 single-region OFT Domain 构造，调用一次
   `add_polygon(boundary, "plasma")` 创建唯一 Region。
5. 不创建 LCFS interface、first-wall interface、vacuum annulus 或
   `artificial_outer`。
6. 复用现有 OFT/Triangle 网格生成核心，不复制 Triangle、重采样、点合并或种子逻辑。
7. 必须通过 `domain.regions` 长度差捕获唯一 Region，build 后读取同一对象的
   `_resampled_points`，并执行统一 `outer_boundary` 验证。
8. `Mesh2D.outer_boundary` 表达实际 EAST 计算域外边界；`Mesh2D`、Writer 和
   native helper 不感知边界来源。
9. 不自动推断 X-point 附近目标磁拓扑，不改变用户轮廓，不引入插件、抽象基类体系
   或通用区域配置语言。

#### 5.11.4 `single_region + flux_surface`

状态为 **实现候选 / NOT IMPLEMENTED / 需要 OFT 26.6 只读侦察**，本轮不批准业务
实现。它不是文件格式或第二网格生成器，而是从 GFile 二维极向磁通场提取指定内部闭合
磁通等值线，并作为 single-region 唯一边界，适用于核心或内部等离子体计算域。

该能力不能替代需要包含 X-point 或其附近区域的 EAST 外部边界。实现前必须确认
OFT 26.6 的磁通场数据、归一化磁通定义、轮廓提取接口、多轮廓选择规则、闭合和方向
约定及失败行为。禁止径向缩放、中心缩放或任意几何插值伪造内部磁面。

#### 5.11.5 Plotter 的 array-file 与 LCFS reference 契约

1. 基础 `plot_mesh()` 以 `Mesh2D` 及其 `outer_boundary` 作为实际网格和实际计算
   域边界来源。
2. `GFileData` 是可选平衡参考；候选 `plot_lcfs` 工作流只叠加
   `GFileData.lcfs_r/lcfs_z` 作为 LCFS reference。
3. `array_file + plot_lcfs` 模式只允许从参考 `GFileData` 绘制
   `lcfs_r/lcfs_z`；不得绘制 `wall_r/wall_z`、limiter、First wall、
   `rmaxis/zmaxis`、Magnetic axis 或其他平衡字段。
4. 无 GFile 的旧 `array_file` 路径必须仍能绘制实际计算边界和三角网格。
5. 三角网格、actual mesh boundary 和 LCFS reference 必须在视觉与图例上可区分；
   正式契约不固定具体颜色。
6. 不得为兼容 Plotter 把外部边界伪装成 LCFS，也不得把 LCFS、limiter 或第一壁
   标成 actual mesh boundary。
7. `plot_mesh()` 使用默认兼容模式时，既有以 GFile 作为实际网格输入的绘图仍可显示
   LCFS、第一壁和磁轴；CLI 仅在 `array_file + plot_lcfs` 时启用
   `lcfs_reference_only=True`。
8. 参考 LCFS 不完全位于实际计算域内时，首版输出明确英文 warning，但不修改或拒绝
   实际网格。
9. 坐标轴继续明确为 R、Z，单位 m。
10. PNG 仅用于几何检查，不替代 M3D-C1 或 TRIMEG 加载、初始化、时间推进或物理验收。

### 5.12 输入层实施拆分

| 阶段 | 内容 | 状态 |
|---|---|---|
| 输入层 I | `EffectiveConfig`、TOML、发现、合并、矩阵、required-fields、CLI 参数 | **IMPLEMENTED** |
| 输入层 II | `single_region + lcfs`、近重复规范化、真实验收 | **PASSED** |
| 输入层 III | `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED** |
| 输入层 IV | counted R-Z Boundary Reader 与 `single_region + array_file` | **IMPLEMENTED / PASSED** |
| 输入层 V | 真实 `flux_surface` | **实现候选 / NOT IMPLEMENTED / 待 OFT 26.6 只读侦察** |
| 多区域调查 I | OFT 官方能力、`multi_array_file`、轻量包含、Region ID/dx 与 CLI/map 契约 | **DESIGNED / DOCUMENTATION COMPLETED** |
| 多区域调查 II | OFT setup、两层、四层、sibling、混合树、编号、dx 和 no-plasma 对照探针 | **COMPLETED；五类案例 GENERATED / STRUCTURALLY CHECKED** |
| 多区域实现 I | Reader、空行与至少双 block 检查、基础检查、轻量包含、synthetic role plan、setup-only 编号、`regions inspect`、TOML regions map 与 inspection PNG | **IMPLEMENTED / PASSED** |
| 多区域实现 II | `regions generate`、map/结构重验、Region dx、N-region OFT Adapter、Mesh2D 与 mesh PNG | **IMPLEMENTED；真实 two-level/four-level GENERATED，Mesh2D STRUCTURALLY CHECKED，PNG 人工复核 PASSED** |
| 多区域实现 III | `regions generate --target trimeg` 复用 complete-11 Writer | **IMPLEMENTED；真实 HDF5 GENERATED，User 确认自动测试和实际检测通过；标准 MATLAB/TRIMEG consumer 加载 PENDING** |
| 初期交付 I | `array_file + 可选 GFile LCFS PNG reference` | **IMPLEMENTED** |
| 初期交付 II | 初版 Release | **DELIVERED；已发送同门和老师，当前反馈可正常使用** |
| M5 第一条 | M3D-C1 TXT+SMB+PNG CLI | **PASSED；时间推进 PENDING** |

输入层 IV 的 Reader、几何验证、配置放行、CLI 编排、single-region OFT Domain、
无 GFile Plotter 以及 EAST `Mesh2D`、TXT、SMB、PNG 生成侧均已完成。EAST
M3D-C1 加载、初始化和时间推进仍必须分别验收，不得由生成侧结果替代。

后续新增来源仍必须先更新蓝图，再修改最小源码和测试；不得一次实现全部来源或建设
插件体系。

### 5.13 输入与 CLI 验收矩阵

必须覆盖：

- schema 缺失、类型错误和版本错误；
- 未知键、section 和 section 内键；
- 非法枚举、dx、bool；
- `--config`/`--no-config` 互斥和发现规则；
- 默认 < TOML < 显式 CLI；
- `--hdf5` 与 `--h5` 完全同义、共用 `hdf5` dest 并覆盖 TOML
  `[output].hdf5`，旧 `--output` 必须由 argparse 拒绝；
- TOML 与 CLI 两套路径基准；
- 路径不展开；
- `EffectiveConfig` 冻结且恰为 17 字段，覆盖 `mesh_dx` 默认值、TOML、CLI、
  有限正数校验及 profile 显式尺度冲突；
- 已实现、禁止和未实现组合的异常类型；
- boundary source 和 target required-fields；
- `mesh_only` 不调用 Writer；
- `trimeg` 不调用 SMB Writer；
- single-region LCFS 唯一 polygon、近重复过滤和 Region 回写；
- `array_file` counted R-Z boundary text 契约；
- EAST 无扩展名文件正确读取 `N=104`、恰好 104 点、shape `(104,2)`、第一列 R、
  第二列 Z、单位 m；
- 缺计数头、非法整数 N、行数与 N 不一致、列数不是 2、非数字、NaN/Inf、少于
  3 个互异点、首尾重复、相邻重复、零长度闭合边、零面积、自交、多轮廓及额外数据
  必须严格失败；
- `single_region + array_file` 只生成一个区域和合法 `Mesh2D`，不创建嵌套区域
  interface、vacuum annulus 或 artificial outer；
- EAST `outer_boundary` 必须表达实际计算边界并满足正式顺时针约定，Writer 不感知来源；
- 无 GFile 时仍可生成显示实际边界和三角网格的 R-Z 米制 PNG；
- `array_file + plot_lcfs` 必须正好读取一次 boundary file 和一次 GFile，两条 Reader
  支路只在 Plotter 汇合，`GFileData` 不得传给 Mesher、Writer、ModelSpec 或 helper；
  PNG 只从参考 GFile 绘制 LCFS，不绘制 limiter、First wall 或 Magnetic axis；
- 缺 `gfile_path`、缺 `plot_path`、未启用 `plot_lcfs` 却提供 GFile、非
  `array_file` 启用 `plot_lcfs`、GFile 不可读或 LCFS 非法必须按正式边界失败；
- 同一 array boundary 和网格参数在有无 LCFS reference 时必须产生完全相同的
  `Mesh2D`、TRIMEG 11 dataset 值和 M3D-C1 几何/classification 输入；
- LCFS 不完全位于 actual mesh boundary 内时必须产生明确英文 warning，不得静默
  假定有效，也不得修改实际网格；
- EAST TXT、rank-0 SMB 和 PNG 生成、PNG 人工检查、M3D-C1 加载、初始化与时间推进
  必须分层记录，时间推进不得由前述结果替代；
- first wall 缺失不得回退；
- M3D-C1 只构造一次 `M3DC1ModelSpec`；
- SMB 基础路径不插 rank；
- helper 定位由 SMB Writer 管理；
- 默认 nested TRIMEG 行为不变；
- PNG 不替代加载、初始化、时间推进、稳定性或物理正确性验收。

---

## 6. TRIMEG HDF5 输出契约

### 6.1 完整 11 数据集

黄金标尺是 `docs/trimeg/loadfemmesh_h5.m` 和两个真实样例。所有数据集位于
`/femmesh/`，磁盘 dtype 全部为 `float64`。

| 路径 | shape | 语义 |
|---|---|---|
| `/femmesh/nvert` | `(1,1)` | 节点数 N |
| `/femmesh/ntria` | `(1,1)` | 三角形数 T |
| `/femmesh/nvert_in` | `(1,1)` | 内部节点数 |
| `/femmesh/nvert_ex` | `(1,1)` | 拓扑外边界节点数 |
| `/femmesh/vert` | `(N,2)` | 每行 `[R,Z]`，不转置 |
| `/femmesh/idxivert` | `(1,nvert_in)` | 内部节点 1-based 升序索引 |
| `/femmesh/idxevert` | `(1,nvert_ex)` | 外边界节点 1-based 升序索引 |
| `/femmesh/tria` | `(T,3)` | `triangles+1`，无第四列，不转置 |
| `/femmesh/nbcRZ` | `(1,1)` | 有序外边界点数 B |
| `/femmesh/Rbc` | `(B,1)` | `outer_boundary[:,0]` |
| `/femmesh/Zbc` | `(B,1)` | `outer_boundary[:,1]` |

任何数据集不得遗漏、改名、合并或转置。

### 6.2 索引、拓扑和边界映射

- `triangles` 内存为 0-based；`tria`、`idxivert`、`idxevert` 文件端为 1-based。
- `region_ids` 不写入 HDF5，也不得偏置。
- `idxevert` 是只被一个三角形使用的无向边所含节点集合。
- 无向边出现超过两次时在打开文件前拒绝。
- 没有拓扑外边界边时拒绝。
- `idxivert = {1..N} \ idxevert`。
- `nvert_in + nvert_ex = nvert`，两集合互斥且覆盖全部节点。
- `Rbc/Zbc` 只能来自有序 `mesh.outer_boundary`。
- 禁止从升序 `idxevert` 反推 `Rbc/Zbc`。
- `nbcRZ` 不要求等于 `nvert_ex`。
- TRIMEG target 缺少 `outer_boundary` 时在打开文件前失败。
- Writer 必须在打开文件前完成所有 shape、有限性、整数、索引、面积、非流形和边界
  验证，并不得修改输入。

### 6.3 LCFS reference 与 TRIMEG 格式边界

当前授权的标准网格 Loader `docs/trimeg/loadfemmesh_h5.m` 读取第 6.1 节定义的
完整 11 个 `/femmesh/` dataset。该 Loader 和当前正式 11 数据集契约中未发现独立
LCFS、separatrix、equilibrium contour 或 reference-curve dataset。

因此：

1. `nbcRZ/Rbc/Zbc` 继续表示实际网格计算域边界。
2. `Rbc/Zbc` 必须继续直接来自 `Mesh2D.outer_boundary`。
3. `array_file + plot_lcfs` 的 GFile LCFS 不得写入 `Rbc/Zbc`。
4. 本工作流不新增、改名或扩展任何 HDF5 dataset。
5. 不修改 HDF5 Writer或 `docs/trimeg/loadfemmesh_h5.m`。
6. 未获得 TRIMEG 开发者直接确认前，不设计私有 LCFS 扩展 dataset。
7. 第一版 LCFS reference 只存在于 LinkMesh PNG。

该结论仅表示当前授权的标准网格 Loader 与正式 11 数据集契约中未发现独立 LCFS
输入位置，不得扩大表述为整个 TRIMEG 系统永远不支持 LCFS。

### 6.4 真实 CLI 和 MATLAB 验收

| 链路 | 结果 |
|---|---|
| DIII-D `g192185.02440`，nested artificial outer | 972 节点、1872 三角形、3 区域、902 内部、70 外部、70 boundary points；HDF5/PNG 成功 |
| fixed-boundary `gNT_example`，nested artificial outer | 3412 节点、6692 三角形、3 区域、3282 内部、130 外部、130 boundary points；HDF5/PNG 成功 |
| DIII-D `g192185.02440`，single-region LCFS，`plasma_dx=0.08` | 344 节点、631 三角形、1 区域、289 内部、55 外部、55 boundary points；HDF5/PNG 成功 |

三份文件均含完整 11 数据集，保持 `(N,2)`、`(T,3)`、1-based 文件索引、无第四列、
不写 `region_ids`。

MATLAB 标准消费端 A/B 验收为 **PASSED**：

- 原始 `loadfemmesh_h5.m` 成功读取标准样例和 LinkMesh HDF5；
- 标准样例约 981 节点、1847 三角形；
- LinkMesh 样例 344 节点、631 三角形、`nbcRZ=55`；
- 未发现索引、布局或明显跨域连线问题；
- 验证不证明计算边界永久固定为 LCFS。

参考样例确认：

- `Rbc/Zbc` 是有序边界几何；
- `idxevert` 是最终拓扑外边界节点；
- `Rbc/Zbc` 不必包含 Triangle 后插入的边界点；
- `nbcRZ` 可等于或小于 `nvert_ex`；
- 样例不证明固定起点规则。

---

## 7. M3D-C1 TXT、SMB 与 native helper 契约

### 7.1 TXT 与 SMB 配套关系

`build_single_face_model_spec(mesh)` 必须只调用一次。TXT Writer 和 SMB Writer
必须接收同一个 `M3DC1ModelSpec` 对象。

TXT Writer 必须：

- 写完整 5 整数头部；
- 写 geometric vertex ID 和 `x/y/z`；
- 写 edge ID、begin/end vertex ID、curve type；
- 写 loop ID、edge 数及有序 edge tags；
- 写完整 `numFaces>0` face 段；
- 保证 ID 唯一、引用存在、endpoint order 正确和 loop 闭合；
- 不输出两列 CSV，不固定 104 点，不调用 Simmetrix。

### 7.2 目标 SCOREC/PUMI 环境

首要兼容目标：

- PUMI 2.2.9；
- Git commit `f87525cae7597322edfb2ccf1c7d4437402d948`；
- Spack hash `333b2ut`；
- GCC 13.3.0；
- Open MPI 4.1.6；
- Zoltan 3.901；
- `/usr/bin/mpicxx`；
- Release；
- variants：
  `~fortran ~int64 ~ipo ~shared +simmodsuite_version_check ~testing +zoltan`，
  `simmodsuite=none`。

调查实例前缀：

```text
/opt/spack/opt/spack/linux-zen4/pumi-2.2.9-333b2utt2vneffaporuf7kaenhpow7x5
```

该路径只标识外部调查实例，不得硬编码。

CMake 必须使用：

- `find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED ...)`；
- `SCOREC::mds`；
- `SCOREC::apf`；
- `SCOREC::gmi`；
- `SCOREC::pcu`；
- 相容 MPI C++ imported target。

不得使用不存在的 `SCOREC_INCLUDE_DIRS` 或 `SCOREC_LIBRARIES`。

已确认 API：

- `apf::makeEmptyMdsMesh(model, 2, false)`；
- `Mesh2::createVertex(ModelEntity*, Vector3 const&, Vector3 const&)`；
- `Mesh2::createEntity(int type, ModelEntity*, MeshEntity** down)`；
- `acceptChanges()`；
- `verify()`；
- `writeNative()`。

目标版本中传入 `<base>.smb` 时，rank 0 实际文件为 `<base>0.smb`。该规则不自动
外推到其他版本。

### 7.3 Python SMB Writer

公开接口：

```text
write_smb(
    mesh: Mesh2D,
    spec: M3DC1ModelSpec,
    filepath: str | os.PathLike[str],
    *,
    helper_path: str | os.PathLike[str] | None = None,
) -> None
```

职责：

1. 验证类型、shape、dtype、有限性、0-based 索引、退化 triangle、single-region、
   single-face、输出目录和路径冲突。
2. 不修改 `Mesh2D` 或 NumPy 数组。
3. 确定性构造 mesh entity classification。
4. 创建、flush、fsync 并关闭唯一隐藏交换文件。
5. 独立子进程调用 helper，捕获退出码、stdout、stderr。
6. 根据目标版本确认 `<base>0.smb` 是非空普通文件。
7. 成功删除交换文件。
8. Python 校验、子进程、helper 或输出确认失败时保留交换文件，并在异常中报告路径。
9. 不创建 GMI/APF/MDS entity，不读取或修改 SMB 字节。
10. 不硬编码 PUMI 前缀，不实现 loader/validator。

### 7.4 Classification

classification 的唯一责任层是 Python Writer。C++ helper 只执行交换契约，不猜测。

规则：

1. 从 triangles 生成 `(min(node0,node1), max(node0,node1))` 无向边，去重后按字典序。
2. 边出现一次为边界，出现两次为内部，超过两次失败。
3. 外边界必须形成唯一简单环；每个 boundary node degree 为 2，一次遍历覆盖全部边。
4. 每个 geometric vertex 坐标必须与恰好一个 boundary node 逐分量精确相等。
5. 以 directed geometric edge 起点 corner 顺序确定唯一边界方向。
6. corner vertex 分类为 `(dim=0, vertex.tag)`。
7. 相邻 corner 间非 corner boundary vertices 分类为对应
   `(dim=1, edge.tag)`。
8. boundary mesh edges 分类为对应 geometric edge。
9. interior vertices、interior edges、全部 triangles 分类为唯一 face。
10. 不从 `region_ids` 推导 face tag。
11. 禁止最近距离、容差最近邻、投影或启发式 classification。

无法满足精确映射时必须停止并先更新上游数据契约，不得静默改为容差匹配。

### 7.5 Schema v1 内部交换格式

交换文件名称为 `LinkMesh M4 Exchange`，schema version 为 `1`。编码是单个
little-endian 二进制文件。整数使用明确宽度，字符串使用 UTF-8，浮点使用
IEEE-754 binary64。

字段顺序固定为：

1. 8 字节 magic：ASCII `LM4XCHG` 后跟 NUL。
2. `uint32 schema_version`，值 `1`。
3. `uint32 endian_marker`，值 `0x01020304`。
4. `uint64 N`、`T`、`E`、`GV`、`GE`、`GL`、`GF`。
5. 四个 `int32`：
   `separatrix_loop`、`inner_wall_loop`、`outer_wall_loop`、`vacuum_loop`。
6. 输出 SMB 基础路径：`uint64 byte_length` + 不含 NUL 的 UTF-8 字节。
7. `nodes`：`N×2 float64`，C-order，每行 `[R,Z]`，m。
8. `triangles`：`T×3 uint64`，C-order，Python 0-based。
9. geometric vertices：每条
   `int32 tag + float64 r + float64 z + float64 y`。
10. geometric edges：每条
    `int32 tag + int32 begin_vertex_tag + int32 end_vertex_tag +
    int32 curve_type`。
11. geometric loops：每条
    `int32 tag + uint64 edge_count + edge_count×int32 edge_tag`。
12. geometric faces：每条
    `int32 tag + uint64 loop_count + loop_count×int32 loop_tag`。
13. mesh vertex classification：N 条
    `int32 geometric_dimension + int32 geometric_tag`。
14. mesh edges：E 条
    `uint64 node0 + uint64 node1 + int32 geometric_dimension +
    int32 geometric_tag`。
15. triangle classification：T 条
    `int32 geometric_dimension + int32 geometric_tag`。
16. 文件在最后记录后立即结束，不允许截断或尾随字节。

Schema v1 限制：

- `GL=1`；
- `GF=1`；
- curve 仅 `LIN=1`；
- triangle 全部分类到唯一 face；
- node/edge 索引 0-based；
- mesh edge 满足 `node0 < node1` 且按端点字典序；
- Python 和 helper 分别验证计数、溢出、引用、tag、dimension、索引和文件长度；
- 不承载 PUMI 指针、SMB 字节、MPI ownership、C1 field、高阶节点、field、
  numbering、partition、residence 或 ghost 信息。

当前正式 helper 调用：

```text
linkmesh-scorec-helper --input <exchange-file>
```

成功 stdout：

```text
LINKMESH_M4_OK base=<base-path> rank0=<actual-rank0-path>
```

失败 stderr：

```text
LINKMESH_M4_ERROR stage=<stage> message=<summary>
```

不得依赖任意 PUMI 日志判断成功。

### 7.6 C++ helper 生命周期

helper 必须：

1. 初始化 MPI、PCU、GMI。
2. 严格读取 schema v1。
3. 建立完整 geometric vertices、directed edges、loop、face。
4. 查找并验证 classification entities。
5. 调用 `apf::makeEmptyMdsMesh(model, 2, false)`。
6. 按 node index 创建 classified vertices。
7. 按交换顺序创建 classified edges。
8. 按 triangle index 创建 classified triangles，并规范 orientation。
9. 只设置目标版本必需的串行 residence/ownership。
10. 调用 `acceptChanges()`、`verify()`、`writeNative()`。
11. 记录基础路径和实际 rank-0 路径。
12. 按唯一顺序清理：
    - callback data 在 model 使用期间保持有效；
    - `apf::disownMdsModel(mesh)`；
    - `mesh->destroyNative()`；
    - `apf::destroyMesh(mesh)`；
    - `gmi_destroy(model)` 恰好一次；
    - 释放 PCU；
    - MPI Finalize。
13. 任意失败以非零退出码和结构化错误报告。

禁止依靠进程退出泄漏、重复销毁 model、跳过 `disownMdsModel`、跳过 mesh 销毁或以
异常终止掩盖生命周期错误。

### 7.7 helper 名称、定位与 ABI 边界

当前正式接口：

| 层次 | 当前名称 |
|---|---|
| 文档组件名 | LinkMesh SCOREC helper |
| Git 源码目录 | `native/linkmesh_scorec_helper/` |
| CMake target | `linkmesh-scorec-helper` |
| Linux 可执行文件 | `linkmesh-scorec-helper` |
| 环境变量 | `LINKMESH_SCOREC_HELPER` |

唯一定位顺序：

1. Python API 显式 `helper_path`；
2. `LINKMESH_SCOREC_HELPER`；
3. `PATH` 中的 `linkmesh-scorec-helper`；
4. 全部失败时明确报错并停止。

高优先级候选已提供但无效时不得静默回退。Python Writer 不猜测仓库 build、用户主
目录、服务器固定路径或 Python 包同目录 helper。更换 SCOREC/PUMI、编译器、MPI
实现或 ABI 时，必须重新配置空构建目录，重新执行 API/CMake probe、helper 生成侧
验收和外部消费验收；不得复用旧 `CMakeCache.txt` 或把既有二进制视为跨 ABI 可移植。

### 7.8 LinkMesh SCOREC helper 职责边界

helper 是 LinkMesh 自有 native Adapter，连接 Python SMB Writer 与服务器
SCOREC/PUMI C++ 环境。它接收 Python Writer 按正式内部交换 schema 产生的数据，
负责 GMI/APF/MDS mesh 构造、classification 应用、PUMI 生命周期管理和 native SMB
写出。

helper 不读取 GFile、EAST 或其他边界文件；不调用 OFT/Triangle；不重新剖分；不决定
计算边界来源；不承担 M3D-C1 消费端职责；当前不是通用 SCOREC 工具，只服务于
LinkMesh 的 M3D-C1 native SMB 写出。LCFS、`array_file`、未来 `first_wall` 或
`flux_surface` 只要在 Writer 前形成相同合法的 `Mesh2D` 和 `M3DC1ModelSpec`，
通常不需要修改 helper。

需要修改 helper 或至少重新构建的触发条件包括：

- Python/C++ 内部交换 schema 变化；
- classification 或 `M3DC1ModelSpec` 拓扑契约变化；
- 多 face、多 loop、孔洞或多区域能力正式获批；
- SCOREC/PUMI API 或版本变化；
- MPI 实现或 ABI 变化；
- 编译器或 C++ ABI 变化；
- 服务器或 CPU 架构变化；
- helper 自身缺陷修复。

普通 Boundary Reader、Plotter 或网格尺度变化不得自动触发 helper 重构。

### 7.9 当前 helper 二进制事实

当前 helper 是 Linux x86-64 动态链接 ELF，包含 `debug_info` 且尚未 strip。这是
开发/验证构建特征，不表示程序错误。当前已观察到系统路径的 `libmpi.so.40` 和
`libstdc++.so.6`；筛选后的 `ldd` 输出未出现 `not found`。

筛选输出未显示 SCOREC/PUMI 动态库，不能据此声称 helper 不依赖 SCOREC/PUMI。
相关库可能静态链接或以其他名称参与链接。发布前必须审计完整 `ldd`、`readelf -d`、
CMake 配置摘要、编译命令和链接命令。把 helper 安装到 Conda `bin` 只解决安装与
定位，不自动解决 MPI、SCOREC/PUMI、系统 C++ 库或 ABI 兼容。

### 7.10 M4 验收边界

- M4-1A TXT/Level 1：**PASSED**；
- M4-1B probe：**COMPLETED / PASSED**；
- M4-2 LinkMesh single-face 生成侧：**IMPLEMENTED / PASSED**；
- 正式 single-face TXT+SMB 外部加载：**PASSED**；
- M3D-C1 single-face 初始化：**PASSED**；
- 时间推进、稳定性和物理正确性：**PENDING**。

319 字节 probe、955 bytes synthetic SMB、173 bytes TXT、真实运行文件大小和
SHA-256 只用于运行追踪，不是格式常量或测试期望。LinkMesh 不建设 SMB loader、
validator 或 M3D-C1 消费端。

### 7.11 M3D-C1 多区域输入契约调查与候选边界

三份字段级调查已经完成：

- `docs/linkmesh/m3dc1_multi_region_model_topology_evidence.md`
- `docs/linkmesh/m3dc1_multi_region_pumi_api_evidence.md`
- `docs/linkmesh/m3dc1_multi_region_pumi_input_contract_report.md`

#### 7.11.1 已确认事实

1. 教程三层案例定义 3 个 loops 和 3 个 geometric faces；相邻 faces 引用同一个
   loop，并共享该 loop 的 geometric edges。
2. TXT face record 已能表达一个 face 引用一个或多个 loops。
3. 当前 exchange v1 wire layout 已包含多个 loop records、多个 face records、
   face-to-loop 引用和逐 triangle classification。多 face 阻塞来自当前 ModelSpec、
   Python Writer 和 helper 的 single-face invariants，不是 wire layout 缺少 face
   records。
4. LinkMesh mesh topology 使用全局 0-based nodes、triangles 和唯一 mesh edges。
   Region 不拥有局部节点编号；共享界面节点和 mesh edge 不复制。
5. PUMI 只录入已有 `Mesh2D` topology、应用 classification 并调用
   `writeNative()`，不重新剖分。
6. `Mesh2D.region_ids` 是 OFT 最终 Region 标签，不是 model face tags，不得直接
   使用、压缩、排序或执行 `+1`。
7. Python Writer 继续是 classification 唯一责任层；helper 只验证并应用 exchange
   中的 classification，不根据坐标、Region 名称、颜色或邻接关系重新猜测。
8. `Mesh2D` 单独不足以构造多区域 analytic model；还需要输入 curves、
   `RegionPlan` 及正式 curve/Region 对应。
9. `physical_label`、color 和 OFT technical role 不得自动驱动 face topology、
   face tag 或 classification。
10. TXT 与 SMB 必须由同一个目标专用构建结果及同一套 tag mappings 驱动。
11. SCOREC/PUMI 生成侧成功只达到生成侧证据，不等于 M3D-C1 已消费；多区域消费
    验证由同门负责。

#### 7.11.2 待 User 批准的候选设计

以下内容是候选，不是已开放接口：

1. multi-face builder 消费 `Mesh2D`、`RegionPlan` 和 regions map。
2. builder 确定性生成 `curve_id_to_loop_tag` 与
   `region_id_to_face_tag`。
3. 每条 input curve 只建立一个 geometric loop 和一套 geometric edges；相邻
   faces 通过同一 loop tag 共享界面，不复制 geometry。
4. Region face 的候选 boundary loops 为按确定顺序排列的 direct-child loops 加
   own loop；该顺序目前只可作为 LinkMesh 确定性约定，不能宣称为目标 orientation
   语义。
5. triangle classification 由显式 `region_id_to_face_tag` 生成。
6. schema v1 保持现有 single-face invariants；multi-region 候选使用字段布局相同、
   语义 invariants 不同的 schema v2。
7. helper 候选同时读取 v1/v2，保持 v1 回归，并为 v2 创建多个 faces、共享
   geometric edges 和应用任意已声明 face classification。
8. `regions generate` 候选增加 `target=m3dc1`、`model` 和 `smb`。是否增加
   `--no-smb` 尚未经 User 裁决，本蓝图不批准该参数。

候选接口存在第 3.5 节所述构建结果缺口。在该缺口完成正式裁决前，不得让 TXT Writer
和 SMB Writer 分别重建 mappings。

#### 7.11.3 待确认事项

以下事项继续为 `PENDING`：

- 同一个 analytic edge 被两个 face boundaries 使用是否通过目标 PUMI
  `verify()`；
- AGM 是否需要显式 use direction；
- multi-loop face 的 outer/hole orientation；
- face 中 loop tags 的顺序语义；
- sibling/mixed tree 的目标环境 native 验证；
- special loop tags 的通用来源；
- OFT 内部 interface corner 和 edge chain 与原始 curve 的确定性对应；
- multi-face analytic model 的统一 `(R,Z)` parameterization 是否充分；
- 任意 N-region M3D-C1 输出是否可以开放；
- 新多区域 TXT+SMB 的生成、加载、初始化、时间推进及物理结果。

不得通过解析 SMB、调查 M3D-C1 loader、最近距离、容差吸附、投影、
`physical_label` 或 synthetic OFT technical role 补足这些证据。

#### 7.11.4 建议的首版实施顺序

**Agent 建议，尚未获 User 批准：** 优先实施老师教程直接覆盖的严格嵌套三层模型；
任意 sibling/mixed N-region 输出等待目标 PUMI native fixture 通过后再开放。

即使仅实施严格嵌套三层，也必须先解决：

- special loop tags；
- face/loop orientation；
- 共享 analytic edge 的 native `verify()`；
- OFT 内部 interface 到 geometric edge chain 的确定性 classification 对应；
- 第 3.5 节的不可变构建结果与 mappings 传递方式。

当前分层状态：

| 层级 | 状态 |
|---|---|
| M3D-C1 多区域输入契约调查 | **COMPLETED** |
| 教程三 face 拓扑 | **CONFIRMED** |
| exchange 多 face record 表达能力 | **CONFIRMED** |
| schema v2 | **DESIGNED / USER APPROVAL PENDING** |
| multi-face ModelSpec | **DESIGNED / NOT IMPLEMENTED** |
| 多区域 classification | **DESIGNED / NOT IMPLEMENTED** |
| helper 多 face 支持 | **DESIGNED / NATIVE PROBE PENDING** |
| `regions generate target=m3dc1` | **CANDIDATE / NOT OPEN** |
| 多区域 TXT+SMB | **NOT GENERATED** |
| 同门消费验证 | **PENDING** |

---

## 8. 真实场景、使用与部署路线

### 8.1 Case 组织与部署

1. 当前不进行需要 `sudo` 的全局安装。
2. 一份 LinkMesh 源码可与 `100`、`200` 等 Case 系列同层。
3. 每个 Case 保存配置、GFile、M3D-C1 输入、TXT、SMB、PNG 和日志。
4. `100`、`200` 可代表源码版本；`101`、`102` 等复用源码并修改输入。
5. 进入 Case 后通过 CLI 指定配置；临时覆盖使用显式 CLI。
6. 网格预处理与正式求解作业分离。
7. 推荐“生成 → PNG 检查 → 提交求解”，不在每次 `sbatch` 中无条件覆盖网格。
8. 登录节点不允许时可提交独立轻量预处理作业。
9. 只改求解参数可复用网格；改 GFile、边界策略或尺度必须重生成。
10. 后续推荐用户级 Conda 安装 Python 包和 helper。
11. PNG 只做几何检查，不替代消费端验收。

### 8.2 EAST 主线

EAST 已确认为无扩展名 counted R-Z boundary text 提供的独立二维计算边界，文件结构、
列顺序、单位和基础几何验证已通过。其物理构造算法及其与 LCFS、第一壁、磁轴和
X-point 的精确关系仍待确认，不阻塞读取最终边界，也不得被擅自补写。

```text
蓝图 counted R-Z 契约确认
  → single_region + array_file 实现
  → OFT/Triangle 细密二维网格
  → Mesh2D + TXT + rank-0 SMB + PNG
  → PNG 几何检查
  → M3D-C1 加载
  → 初始化回归
  → 时间推进主循环
  → 短时运行
  → 中等时长运行
```

`single_region` 描述区域数，不等于 LCFS。不得因为边界可能包含 X-point 推断必须
多区域，不得把 EAST 外部计算边界改写为 LCFS、第一壁或内部磁面。

### 8.3 X-point 附近目标磁拓扑的工程边界

本蓝图只使用“X-point 附近具有特殊或分形特征的磁拓扑结构”描述背景，不定义
“分形面”的严格性质，也不推断形成机制。

LinkMesh 不计算、重建或分析该磁拓扑。输入是一条经物理人员确认、包含目标研究结构
的二维 R-Z 闭合计算边界。计算边界不等同于研究对象，也不必是 LCFS、第一壁或普通
磁通面。

禁止：

- 缩放 LCFS 伪造人工边界；
- 自动推断目标磁拓扑外边界；
- 扩展为磁拓扑分析程序；
- 在缺少数据和算法时自动判断 X-point、LCFS、第一壁和边界包含关系。

### 8.4 EAST 网格与时间推进记录

可比较 `plasma_dx=0.08 m`、`0.05 m`、`0.03 m`，但不是固定标准。每组记录：

- 边界点数、节点数、三角形数；
- 完整配置和 `plasma_dx`；
- TXT、rank-0 SMB、PNG；
- 加载与初始化结果；
- 是否进入时间推进；
- 实际步数；
- 首次错误或停止原因。

短时推进至少检查：

1. 执行若干时间步；
2. 无立即网格、connectivity 或 classification 错误；
3. 无明显 NaN、Inf、段错误或 MPI 异常；
4. 日志区分正常停止、求解器输入、网格和环境问题。

时间推进不报错不等于物理正确或精度充分。

### 8.5 TCV/TRIMEG 路线

调查应比较：

- EQDSK LCFS；
- EQDSK 第一壁；
- 参考 HDF5 `Rbc/Zbc`；
- 参考网格拓扑外边界；
- 磁轴、X-point 和指定研究区域。

真实消费路线：

```text
LinkMesh HDF5
  → 官方 MATLAB Reader
  → TRIMEG 实际读取和运行
```

PNG、截图或 MATLAB 绘图不是 TRIMEG 实际消费通过证据。

### 8.6 OFT/Triangle 真实场景评估顺序

1. 几何：边界贴合、覆盖、孔洞、越界、X-point 包含关系；
2. 网格：节点、三角形、面积、最小角、长宽比、边长分布；
3. 消费端：
   - M3D-C1 加载、初始化、时间推进；
   - TRIMEG MATLAB 读取和实际运行。

在真实场景证明全局 dx 不足前，不开发 refinement、局部加密、磁面对齐或自适应网格。

### 8.7 本地开发、上传与服务器验证分工

正式源码在本地 Windows Git Bash 仓库中维护。本地负责阅读和修改文档、Python、
C++、CMake 与测试源码，使用 Aider 执行 User 授权的修改，审查 `git status`、
`git diff` 和提交记录，并创建经过确认的源码版本或发布归档。

本地不运行任何测试，不运行 OFT/Triangle，不编译 Linux native helper，不运行
SCOREC/PUMI、M3D-C1 或 TRIMEG 消费验证。本地未运行的测试必须记录为
**NOT RUN**，不得由静态阅读或服务器历史结果写成 PASSED。

Linux 服务器负责接收本地上传的已确认源码版本或发布包，创建和维护服务器环境，
编译 helper，运行 Python 自动测试和 OFT/Triangle，生成 `Mesh2D`、HDF5、TXT、
SMB、PNG，并执行 M3D-C1/TRIMEG 真实消费验收和保存命令、日志、环境及产物。

当前服务器源码目录为 `/home/lxzeng/LinkMesh_server`，源码由 User 从本地直接上传，
不是通过服务器 Git 拉取和管理。不得把 `git pull`、服务器 `git status` 或服务器
`git log` 写成当前既有工作流。Linux 服务器原则上不修改正式源码和文档；问题必须
携带直接证据返回本地修复。服务器构建目录、测试缓存、日志和 Case 输出不是正式源码。

正式闭环为：

```text
本地修改与提交
  → 确认源码版本
  → 上传源码版本或发布归档
  → 服务器构建与验证
  → 保存失败或成功证据
  → 如需修复则返回本地修改
  → 再次上传并回归
```

### 8.8 开发、候选与共享环境

| 环境 | 定位 | 正式规则 |
|---|---|---|
| 本地源码开发环境 | Windows Git 仓库 | 维护源码、文档和版本；未执行的 Linux/OFT/native/消费验证必须标记 `NOT RUN` |
| Linux 个人开发验证环境 | 可变开发环境 | 允许测试依赖、临时 `PYTHONPATH` 和开发构建产物；不作为组内稳定发布 |
| Linux 个人发布候选环境 | 全新可写前缀 | 正式安装 LinkMesh 与 helper；从源码目录外运行；不依赖个人 `PYTHONPATH` 或开发构建目录 |
| 组内共享稳定环境 | 导师批准根目录下的版本化 release | 普通用户只读执行；不依赖维护者个人目录；不原地升级；保存版本和验收记录 |

正式发布不得依赖个人 `PYTHONPATH`。OFT 必须来自发布环境正式安装包，不得把
`TOKAMAKER/OpenFUSIONToolkit/src/python` 作为运行时来源。普通用户不负责安装
依赖或编译 helper。当前共享根目录、权限、modulefile、首个版本化 release 和普通
用户验收尚未实施。

### 8.9 发布可追溯性

服务器没有现行 Git 工作流，因此每个发布候选和共享 release 至少保存：

1. LinkMesh 发布版本号和对应本地 Git commit；
2. 上传或发布日期、上传者或维护者；
3. 源码归档文件名及 SHA-256，或其他明确源码标识；
4. Python 版本、直接运行依赖和关键版本；
5. OFT 版本及导入来源；
6. helper 源码版本、二进制 SHA-256、构建日期；
7. CMake 和编译器版本；
8. MPI 版本、来源和 ABI 信息；
9. SCOREC/PUMI 版本、来源和链接信息；
10. 验收日期、案例、测试摘要、日志位置；
11. 已通过和仍待确认的验收层级。

SHA-256 只标识某次具体源码归档或二进制构建，不是跨构建恒定黄金值。

### 8.10 源码、构建和安装分层

批准的目标分层为：

```text
Git 源码：
LinkMesh/native/linkmesh_scorec_helper/
  ├── C++ 正式源码
  ├── CMakeLists.txt
  └── README.md

Linux 开发构建：
$HOME/LinkMesh_build/linkmesh_scorec_helper/<toolchain-id>/

个人发布候选：
$CONDA_PREFIX/bin/linkmesh-scorec-helper
$CONDA_PREFIX/.../site-packages/linkmesh

组内共享 release：
<GROUP_SOFTWARE_ROOT>/linkmesh/releases/<version>/env/
```

Git 只保存 C++ 源码、CMake 和维护文档，不提交 helper 二进制、`CMakeCache.txt`、
`CMakeFiles`、Makefile、`cmake_install.cmake` 或构建日志。开发构建树位于仓库外，
可删除并从源码重建，可按 PUMI、MPI 和编译器组合区分 `<toolchain-id>`；Python
Writer 不猜测该路径，不再把长期构建树放在 `LinkMesh_runs`。

个人候选环境必须通过正式 Python 安装把 LinkMesh 放入 `site-packages`，并通过
CMake install 把 helper 放入 `bin`；不得依赖 `PYTHONPATH` 或开发构建目录。共享
release 中 Python LinkMesh 与 helper 属于同一版本组合，不依赖维护者个人目录。

native 构建后续实施要求：

- 保持已验证的 SCOREC/PUMI imported targets 和 MPI 发现方式，除非直接证据要求修改；
- target 更名为 `linkmesh-scorec-helper`；
- 添加或核对 `install(TARGETS ...)`；
- 支持 `cmake --install <build-dir> --prefix <install-prefix>`；
- 从空构建目录可复现配置和编译；
- 检查可执行权限、`file`、完整 `ldd`、`readelf -d`、CMake 配置摘要及编译链接命令；
- 不得出现 `not found`；
- 优先使用目标服务器正式软件栈、CMake RUNPATH/RPATH 或管理员确认环境；
- 不要求普通用户长期维护复杂 `LD_LIBRARY_PATH`；
- 不复制 SCOREC/PUMI 库进 Git，不以 `sudo` 全局安装为当前默认方案。

是否 strip 发布二进制留待后续裁决，但必须保留构建可追溯性和调试策略。

### 8.11 Python 正式安装与 triangle 验证

发布前必须建立可复现的正式 Python 安装方式。个人候选和共享 release 中 LinkMesh
必须安装到 `site-packages`，从源码目录外可以 `import linkmesh`、启动统一 CLI 并
运行批准的真实流程；发布运行不得依赖 `PYTHONPATH`。OFT 必须从发布环境
`site-packages` 导入，不得从 `TOKAMAKER` 参考源码导入。

当前交付侦察尚未确认仓库具备完整正式打包元数据和统一安装入口；若后续实时核对确认
缺少 `pyproject.toml` 或其他必要元数据，应作为独立实现缺口处理。本版不创建打包
文件，精确安装、命令入口和版本元数据另行设计和测试。

triangle 事实边界：

- 当前开发环境安装 triangle 20250106；
- 当前只读证据未发现 LinkMesh 正式源码直接导入 triangle；
- OpenFUSIONToolkit 26.6 包元数据未声明 triangle；
- `TOKAMAKER` 参考源码中的相关 import 是注释线索；
- 这些证据只支持“triangle 可能不是正式运行依赖”的候选判断，不批准删除依赖。

最终裁决必须来自不安装 triangle 的干净候选环境：正式安装 LinkMesh，运行自动测试、
真实 GFile 和 `array_file`、所有批准 profile，生成 HDF5/TXT/SMB/PNG，调用 helper
并完成相应真实消费验证。全部通过后才能修改正式依赖契约。

### 8.12 组内版本化共享发布

目标结构使用占位符，正式根目录仍待导师或服务器管理者确认：

```text
<GROUP_SOFTWARE_ROOT>/
└── linkmesh/
    ├── releases/
    │   ├── <version>/
    │   │   ├── env/
    │   │   ├── source-manifest/
    │   │   ├── validation/
    │   │   └── VERSION
    │   └── ...
    ├── current -> releases/<stable-version>
    ├── bin/
    │   └── linkmesh
    └── modulefiles/
        └── linkmesh
```

不得把 `/share`、`/shared` 或其他候选路径写成当前事实。每个版本使用独立环境前缀；
不得在稳定 release 上原地执行 `conda update`、`pip install` 或替换 helper。新版本
在新 release 中安装和验收，通过后才切换 `current`，旧版本保留用于回退和复现实验。
普通用户只读和执行；维护者创建、验证和发布。`source-manifest` 保存源码与构建来源，
`validation` 保存测试摘要、真实案例、native 软件栈和消费结果。

### 8.13 普通用户入口与权限边界

普通组员原则上不需要自行安装 Conda，不编译 helper，不设置 `PYTHONPATH`，不手工
设置 `LINKMESH_SCOREC_HELPER`，不进入 `/home/lxzeng`，也不需要知道源码或构建目录。
用户只在生成或更新网格时运行 LinkMesh；已确认网格可供后续 M3D-C1 作业重复使用。

统一入口优先级：

1. 第一阶段共享包装命令；
2. 条件允许时 `module load linkmesh`；
3. 最低可用回退为共享 release 中的绝对命令路径。

首版包装入口负责定位 `current`、准备 release `PATH`，必要时设置
`LINKMESH_SCOREC_HELPER`，仅在直接证据要求时准备动态库环境，调用 release 中的
LinkMesh，原样传递参数并保留退出状态。不得硬编码 `/home/lxzeng`、修改用户 Case、
隐藏失败退出码，或在完整审计前凭经验加入复杂 `LD_LIBRARY_PATH`。modulefile 是
条件性长期入口，其支持、位置和维护权限仍待确认。本版不创建包装脚本或 modulefile。

当前权限直接事实：

- User 属于 `lxzeng`、`users` 和 `m3dc1`；
- `/home/lxzeng` 权限约为 `750`，父目录权限使个人主目录不能作为可靠共享软件位置；
- 当前 shell 显示 `No modules loaded`，不能据此证明 module 系统不存在。

以下事项保持 PENDING：共享软件根目录、User 发布维护写权限、普通组员是否统一属于
`m3dc1`、该组是否承担 release 读执行权限、共享目录是否允许执行 ELF、modulefile
支持、正式 MPI 来源、SCOREC/PUMI 正式位置和版本、系统库与 ABI 管理、备份、配额及
清理策略。

### 8.14 发布实施边界

交付环境和环境管理原则已经完成讨论，但共享部署仍为 `PENDING`。实施时必须：

1. 建立不依赖个人 `PYTHONPATH` 的正式 Python 安装。
2. 通过 CMake install 安装 `linkmesh-scorec-helper`。
3. 在个人干净候选环境完成自动测试、真实输入、格式输出和外部消费回归。
4. 审计 helper 的完整动态库、MPI、SCOREC/PUMI、编译器和 ABI 信息。
5. 等待老师确认共享根目录、组权限和 modulefile 能力。
6. 创建新的版本化只读 release，验收后切换 `current`，保留旧版本回退。
7. 使用普通用户或等价权限验证统一入口、输出目录和退出状态。

不得因为个人开发环境可运行而宣告正式共享部署完成。

### 8.15 正式 Release 构建与交付契约

仓库内唯一 Release README 来源是：

```text
packaging/release/README.md
```

该文件只面向最终用户。构建器必须原样复制它，不维护第二份包内 README 或独立
维护者 README。

构建器在指定输出父目录中一次性创建且不得覆盖：

```text
LinkMesh-<version>-linux-x86_64-release/
├── README.md
├── linkmesh-release-<version>-linux-x86_64.tar.gz
└── linkmesh-release-<version>-linux-x86_64.tar.gz.sha256
```

外部交付目录必须且只能包含以上三个普通文件。构建完成后不得把解压后的内部 Release
目录作为第四个正式交付项保留。

tar.gz 必须包含一个内部根目录：

```text
linkmesh-release-<version>-linux-x86_64/
├── bin/
├── manifest/
└── python/
```

内部根目录必须且只能包含以上三个一级目录，不得包含 `README.md`。其中：

- `bin/` 保存 launcher、bootstrap、分层检查器和 `linkmesh-scorec-helper`；
- `python/site-packages/` 保存 LinkMesh、OpenFUSIONToolkit 26.6 及对应 dist-info；
- `manifest/` 保存构建来源、Python/native 依赖边界和内部文件摘要；
- Release 不携带 Python、NumPy、h5py、Matplotlib、MPI、glibc 或 libstdc++；
- TRIMEG 和 PNG 路径不得因 helper 或 MPI 不可用而被环境检查器阻塞。

摘要职责严格分层：

1. `manifest/SHA256SUMS` 只覆盖 tar.gz 内部根目录下的全部普通文件，排除自身。
2. 外部 README、tar.gz、tar.gz.sha256 和外部交付目录路径不得进入内部 manifest。
3. 外部 `<archive>.tar.gz.sha256` 只校验最终 tar.gz，并使用实际归档文件名。
4. 源码归档 SHA-256、helper SHA-256、内部文件 SHA-256 和最终 tar.gz SHA-256
   标识不同对象，不得互相替代。

固定生成顺序：

1. 创建临时工作目录和外部交付暂存目录，复制唯一外部 README。
2. 组装全部内部文件并清除 `__pycache__`、`*.pyc`。
3. 验证内部根目录仅有 `bin/`、`manifest/`、`python/`。
4. 在内部内容完全确定后生成 `manifest/SHA256SUMS`。
5. 从内部根目录创建最终 tar.gz；外部交付目录本身不得进入归档。
6. tar.gz 完成后生成外部 tar.gz.sha256。
7. 验证外部暂存目录恰有三个正式文件后，原子移动为正式交付目录。
8. 任一步失败时清理临时目录，不留下或覆盖正式输出。

README 内容变化不得改变 tar.gz，除非归档内部其他内容也发生变化。禁止发布后人工
解包、删除 README、修改 manifest、重新压缩或重算摘要来伪装正式构建结果。

发布状态必须分层记录：

- `DESIGNED`：正式结构和职责已定义；
- `IMPLEMENTED`：构建、launcher、bootstrap、检查器和结构回归源码已实现；
- `GENERATED`：本轮正式外部三文件交付目录已实际生成；
- `STRUCTURALLY CHECKED`：内部 manifest、外部 SHA-256、目录和可移动入口已验证；
- `LOADED`、`INITIALIZED`、`TIME-STEPPED`、`STABILITY-VALIDATED`、
  `PHYSICALLY VALIDATED`：分别需要目标消费端直接证据。

构建或环境检查成功不得自动升级文件生成、结构检查或外部消费状态。本轮 master
迁移最多达到 `DESIGNED / IMPLEMENTED`；Linux Release 构建、正式 tar.gz 生成、
内部 manifest 与外部 SHA-256 验证及外部消费均须后续单独验收。

---

## 9. 里程碑、测试与验收

### 9.1 M1–M3 和 TRIMEG

- M1 Reader：**PASSED**；
- M2 nested 默认链：**PASSED**；
- M3 core：**PASSED**；
- M3 complete-11：**PASSED**；
- TRIMEG 11 数据集写出：**PASSED**；
- MATLAB 标准消费 A/B：**PASSED**。

### 9.2 M4

- M4-0 只读侦察：完成；
- M4-1A ModelSpec + TXT：**PASSED**；
- M4-1B API/CMake probe：**PASSED**；
- M4-2 Python Writer/helper 生成侧：**PASSED**；
- Python SMB Writer 专项：17 passed；
- M4 相邻回归：170 passed；
- helper 目标环境构建、`verify()`、`writeNative()` 和生命周期：通过。

### 9.3 M5 和 M3D-C1 分层验收

真实 DIII-D 最小闭环：

- LCFS 原始 81 点；
- 第一壁 88 点；
- `outer_boundary` 55 点；
- 344 节点；
- 631 三角形；
- 1 区域；
- TXT 2275 bytes；
- rank-0 SMB 44823 bytes；
- PNG 235388 bytes。

计数和大小不是格式常量。

分层状态：

| 层级 | 状态 |
|---|---|
| LinkMesh CLI 生成 TXT+SMB+PNG | **PASSED** |
| PNG 人工检查 | **PASSED** |
| TXT+SMB 加载 | **PASSED** |
| M3D-C1 初始化 | **PASSED** |
| 时间推进主循环 | **PENDING** |
| 中等或长时稳定性 | **PENDING** |
| 物理结果正确性 | **PENDING** |

### 9.4 输入层

- 输入层 I：**IMPLEMENTED**；
- 输入层 II：**PASSED**；
- first wall：**PLANNED / NOT IMPLEMENTED**；
- EAST 文件结构、R-Z 列顺序、单位与基础几何调查：**PASSED**；
- array file counted R-Z Reader、配置、CLI、OFT 与生成侧：**IMPLEMENTED / PASSED**；
- EAST 生成侧结果：104 个输入边界点、185 个节点、329 个三角形、1 个区域；
- EAST PNG 人工几何检查：**PASSED**；
- EAST TXT+SMB+PNG 生成：**PASSED**；
- EAST M3D-C1 加载、初始化和时间推进：**PENDING**；
- flux surface：**实现候选 / NOT IMPLEMENTED / 待 OFT 26.6 只读侦察**。

新增来源以少量关键单元测试和真实 OFT/GFile/CLI/PNG/HDF5 验收为主，不扩建大型
Fake OFT。

### 9.5 自动测试与外部证据边界

`tests/` 是小型内部契约回归集。自动测试用于证明当前模块的确定性数据契约、关键
失败边界和最小编排行为，不能独立证明外部求解器消费能力或物理正确性。测试文件
存在、mock 通过、覆盖率或 passed 数量不得替代真实程序的分层证据。

外部状态必须分别记录：

| 状态 | 含义 |
|---|---|
| `IMPLEMENTED` | 代码链已经实现 |
| `GENERATED` | 目标文件已经生成 |
| `DELIVERED` | 文件已经交付外部人员或程序测试 |
| `LOADED` | 外部程序已经成功加载 |
| `INITIALIZED` | 外部程序完成初始化 |
| `TIME-STEPPED` | 有直接证据证明完成明确时间推进 |
| `PHYSICALLY VALIDATED` | 物理结果已由责任方确认 |
| `PENDING` | 当前缺少对应层级的直接证据 |

后一个状态不得由前一个状态自动推导。未实际运行的命令必须记录为 `NOT RUN`。

### 9.6 EAST 和 TCV

- EAST 文件结构调查：**PASSED**；
- EAST R-Z 列顺序、单位和基础几何验证：**PASSED**；
- EAST 边界物理构造算法及其与 LCFS、第一壁、磁轴、X-point 的精确关系：
  **PENDING**；
- `single_region + array_file`：**IMPLEMENTED / PASSED**；
- EAST Mesh2D 与 TXT+SMB+PNG 生成侧：**PASSED**；
- EAST PNG 人工几何检查：**PASSED**；
- EAST M3D-C1 加载和初始化回归：**PENDING**；
- EAST M3D-C1 时间推进：**PENDING**；
- TCV 边界调查：**PENDING**；
- TCV/TRIMEG 实际消费：**PENDING**。

任何状态更新必须有对应直接证据，不得由 PNG、生成、加载或初始化向后续层级外推。

### 9.7A multi-array 多区域调查和未来验收

当前状态为：OFT 26.6 N-region、编号主逻辑和 no-plasma 行为调查
**COMPLETED**；五类合成案例 **GENERATED / STRUCTURALLY CHECKED**；synthetic
plasma compatibility role、multi-array Reader、inspect/generate、TOML map、
分 Region dx 和 N-region `Mesh2D` 均已实现。真实 two-level/four-level 网格为
**GENERATED**，生产 `Mesh2D` 为 **STRUCTURALLY CHECKED**，mesh PNG 为
**GENERATED / USER-REVIEWED**。

官方文档与源码已确认：

- OFT 支持多 Region 和分 Region 常数 dx；
- OFT Region、segment 和 region seed 数据容器使用动态列表；
- 调用者通过 API 显式提供区域关系，OFT 不自动从无序曲线建立包含树；
- OFT regionlist 每行为 seed R/Z、数值 attribute 和 `dx^2/2` 最大面积；
- Triangle 将 attribute 传播到 triangle，OFT 从 triangle attributes 读回；
- OFT build 会在 Triangle 调用前重新分配内部 Region ID；
- 当前 wrapper 未向 Triangle 填充 holelist；
- `Region.check_in_poly()` 和 `get_in_point()` 只提供首版轻量组合所需的基础能力；
- 官方工作流使用 topology plot 和最终 mesh plot 人工检查。

独立探针程序已在 OFT 26.6 服务器运行。五类案例均完成生成：

- `two_level_nested`：353 points、664 cells、2 regions；dx variant 为
  449 points、841 cells、2 regions；
- `four_level_nested`：539 points、1035 cells、4 regions；dx variant 为
  640 points、1221 cells、4 regions；
- `one_parent_two_siblings`：420 points、792 cells、3 regions；dx variant 为
  603 points、1141 cells、3 regions；
- `mixed_tree`：457 points、866 cells、4 regions；dx variant 为
  627 points、1188 cells、4 regions；
- `reordered_input`：457 points、866 cells、4 regions；dx variant 为
  621 points、1183 cells、4 regions。

修正后的探针已重跑。五类案例的 `generation_status`、
`mesh_structure_status`、`numbering_status` 和 `overall_status` 全部为 PASS，
因此证据层级更新为 **GENERATED / STRUCTURALLY CHECKED**。已确认：

1. OFT 26.6 可生成两层和四层严格嵌套网格；
2. 可生成单父双 sibling 和 sibling 加深层嵌套的混合树；
3. 不同 Region 常数 dx 的 variant 全部完成生成；
4. 输入 block 重排后仍可生成对应多区域网格；
5. setup-only 可取得最终 Region ID，且与完整 Triangle attribute 一致；
6. 相同输入使用全新 Domain 重建时编号一致；
7. 只改变 Region dx 时编号一致；
8. Triangle attribute 具有离散整数 Region 标签语义；
9. 探针规定的数组、索引、单元、Region 覆盖、重复 triangle、edge incidence 和
   基本结构检查通过。

输入重排只作观察，不要求 Region ID 不变。`mixed_tree` 与 `reordered_input` 中
`left_core` 保持 ID 1、root 保持 ID 2，而 left 从 3 变为 4、right 从 4 变为 3。
因此 curve_id 不是正式 Region ID；同一 technical role 内的定义或输入顺序可能影响
最终编号。重排输入后必须重新 inspect，并按本次 regions map 使用 `--region-dx`。

no-plasma 对照探针使用 root=boundary、内部=vacuum，且没有 plasma。两层和四层案例
的 setup-only 与完整 build 均由 OFT 主动抛出
`ValueError: No plasma region specified`。这确认至少一个 plasma technical role 是
OFT 26.6 `gs_Domain.build_mesh()` 的强制前置条件，失败发生在 Triangle 之前。

调查阶段至此结束，不继续扩展当前 OFT 探针。上述结果不证明异常 polygon、自交、
相切、重合或任意近退化输入受支持，也不表示 LinkMesh multi-array 业务、M3D-C1
多区域输出或真实求解已经实现。首版仍依赖已定义的输入前提、轻量检查和人工 PNG；
复杂异常几何不承诺精确分类。新网格的 M3D-C1 加载、初始化、时间推进和物理验证仍为
PENDING。

### 9.7 初期交付候选工作流验收

新增能力当前状态为
**DESIGNED / APPROVED FOR IMPLEMENTATION / NOT YET IMPLEMENTED**。实施后至少验收：

1. 无 GFile 的旧 `array_file` 命令继续成功，且不读取 GFile。
2. `array_file + plot_lcfs` 正好读取一次 boundary file 和一次 GFile。
3. `GFileData` 只传给 Plotter，不传给 OFT Adapter、`Mesh2D`、Writer、
   `M3DC1ModelSpec` 或 helper。
4. 同一 array file 和相同网格参数在有无参考 GFile时产生完全相同的
   `nodes`、`triangles`、`region_ids` 和 `outer_boundary`。
5. TRIMEG 比较 11 个 dataset 的路径、shape、dtype和值；不因 HDF5 容器元数据
   要求整个文件字节相同。
6. M3D-C1 TXT/SMB 的几何和 classification 输入保持相同。
7. 唯一允许的输出差异是参考工作流 PNG 增加视觉可区分的 LCFS reference。
8. LCFS 不完全位于实际边界内时出现明确英文 warning。
9. 所有 required-fields、非法组合、GFile 读取和 LCFS 数据错误均明确失败。
10. PNG 结果不得记录为 TRIMEG/M3D-C1 消费或物理验收。

### 9.8 当前自动测试树与精简策略

当前正式自动测试树只有：

- `tests/test_cli_contract.py`
- `tests/test_configuration_contract.py`
- `tests/test_format_contracts.py`
- `tests/test_geometry_and_readers.py`
- `tests/test_oft_adapter_contract.py`
- `tests/test_plotter_contract.py`
- `tests/test_release_packaging.py`

当前不存在 `tests/test_hdf5_writer.py`，不得引用或为了恢复历史名称而新建该文件。
TRIMEG HDF5/Writer 的当前格式契约由 `tests/test_format_contracts.py` 保护。
本轮实现开始前服务器精简测试基线为 **96 passed**；这是实现前基线，不是本轮修改后
的测试结果。本轮最终 passed 数只能依据 User 实际服务器运行证据更新，未运行时必须
记录为 `NOT RUN`，不得猜测。

自动测试只保护稳定、确定、可独立观察的内部契约，不以覆盖率、测试数量或 passed
数量作为质量目标、里程碑或外部证据。

测试分为三类：

1. **核心契约测试**：保留在 `tests/`，检查 shape、dtype、索引基准与范围、有限值、
   几何方向、闭合与重复点、区域 ID、文件 dataset、序列化布局、配置合并、合法或
   非法组合、确定性纯函数和明确失败条件。
2. **最小编排测试**：仅为 CLI、Writer/helper 等无法完全通过纯输入输出验证的薄边界
   保留少量 mock。只证明主分支选择、禁止对象没有越层传递、外部副作用边界被调用，
   以及错误在副作用前停止；不得穷举内部调用顺序、局部变量、import 或日志文本。
3. **真实探针与外部验收**：OFT 真实 GFile/网格生成、HDF5 标准 Loader、
   M3D-C1/SCOREC/PUMI 加载、初始化、时间推进和物理确认不得由 mock 替代，继续按
   `GENERATED`、`STRUCTURALLY CHECKED`、`LOADED`、`INITIALIZED`、
   `TIME-STEPPED`、`PHYSICALLY VALIDATED` 分层记录。

测试裁决必须依次判断：实现重写但正式行为不变时测试是否仍应通过；是否能发现用户可
观察错误或正式契约破坏；是否直接检查返回值、文件或异常；是否已有更强测试覆盖；
是否只是复述实现；维护成本是否与独立故障发现能力相称。结论使用：

- `KEEP`：保护独立正式契约；
- `MERGE`：多个测试保护同一契约；
- `REWRITE`：契约有价值但测试绑定实现；
- `DELETE`：无独立故障发现能力。

优先删除或合并：

- 只断言 mock 调用次数且没有架构意义的测试；
- 只断言私有 helper 被调用或绑定内部执行顺序的测试；
- 仅替换一个输入值而复制的异常测试；
- 与 dataclass、argparse、NumPy、h5py、pathlib、tomllib 或标准库自身行为重复的测试；
- 对 docstring、注释、内部常量位置、日志全文、artist 顺序或装饰文本的脆弱断言；
- 已被真实临时文件输入输出测试覆盖的较弱 mock；
- 已被当前正式契约取代的旧 target/profile/source 或旧 CLI 预期；
- 为已删除路径、未来未开放能力、测试计数或覆盖率排列而存在的测试。

原则上保留或合并后保留：

- `Mesh2D` 与 `outer_boundary` 的独立几何不变量；
- counted R-Z 文件的关键语法和几何拒绝；
- GFile Reader 最小字段映射、闭合、方向和依赖失败边界；
- OFT Adapter 三数组、最终 region ID、outer Region 时序和版本锁定契约；
- TRIMEG 11 dataset 的路径、shape、dtype、索引和值；
- M3D-C1 ModelSpec/TXT 与 Python/helper exchange schema；
- helper 定位、subprocess 成功/失败和 rank-0 输出确认；
- 配置默认值、优先级、路径基准、required-fields 和关键兼容矩阵；
- 每条正式 CLI 主工作流至多一个代表性编排测试；
- `array_file + plot_lcfs` 不改变 Mesher/Writer 输入的不变量；
- Plotter 生成非空 PNG、选择正确参考内容且不修改输入。

数量纪律：

1. 不规定覆盖率、最低测试数或 passed 数目标。
2. 每项正式契约只保留能发现独立故障模式的最小集合。
3. 同一规则的多个非法输入优先参数化。
4. 存在更强真实输入输出测试时删除较弱 mock。
5. 新功能不自动要求大量新增测试。
6. 不建设 fixture DSL、复杂工厂、抽象测试基类、snapshot、property-based testing
   或测试生成器，不引入新依赖。
7. 测试代码应明显少于其验证的业务复杂度，格式契约本身确有复杂性时除外。

测试清理只改变内部回归资产，不自动改变任何已确认业务能力、外部验收状态、
`History.md` 事实、接口、字段、shape、dtype、索引、格式或
`IMPLEMENTED/PASSED/PENDING` 状态。稳定复现正式业务缺陷的最小高价值测试必须保留；
不得为获得全绿结果删除真实失败证据。

### 9.9 组内发布与部署验收

Release 构建、launcher、bootstrap、分层检查器和静态结构回归为
**IMPLEMENTED / NOT YET VALIDATED ON LINUX**。以下 Linux 构建、正式归档、
运行时和消费验收当前均为 **PENDING / NOT RUN**，不得写成 PASSED。

**Python 安装**

- LinkMesh 安装到 release `site-packages`；
- 不设置 `PYTHONPATH` 也可导入；
- 从源码目录外可启动；
- OFT 从 release `site-packages` 导入；
- 不使用 `TOKAMAKER` 源码路径。

**CLI**

- 统一入口可运行；
- 参数原样传递；
- 错误退出码保留；
- 普通用户不依赖个人目录。

**helper**

- 正式名称为 `linkmesh-scorec-helper`；
- 安装到 release `env/bin`；
- Writer 按正式定位规则找到；
- 可执行权限和 `file` 正确；
- 完整 `ldd` 无 `not found`；
- MPI、PUMI、编译器及链接信息已记录；
- 能生成真实 SMB；
- 普通用户无需编译或设置环境变量。

**多用户权限**

- `m3dc1` 普通成员或等价测试用户可进入共享目录；
- 可执行 LinkMesh 和 helper，读取 Python 包及所需库；
- 不能修改稳定 release；
- 维护者可创建新 release；
- `current` 可切换和回退。

**真实消费**

- 通过正式共享入口运行真实案例；
- 输出可被目标 M3D-C1/SCOREC/PUMI 软件栈加载；
- 不依赖开发者个人目录、`PYTHONPATH` 或开发 helper；
- 验收记录保存到 release `validation`。

**并发与稳定性**

- 多个普通用户可只读并发调用发布环境；
- 并发验证不修改共享 release；
- 每个用户把 Case 输出写入自己的可写工作目录。

---

## 10. 变更纪律、停止条件与待决事项

### 10.1 蓝图先行纪律

以下变化必须先修改本蓝图并经 User 确认：

- 新字段、CLI 参数、TOML key 或用户格式；
- 新 target/profile/boundary-source 组合或 `regions` 命令阶段；
- helper 名称、定位、构建、安装或兼容策略变化；
- Python 打包、共享 release、包装入口或 modulefile 契约变化；
- shape、dtype、索引、单位或 Writer 契约变化；
- OFT 版本或私有接口变化；
- PUMI 版本、API、编译器或 MPI ABI 变化；
- 多区域、多 face、三维、自适应或并行能力；
- 验收标准或阶段状态变化。

不得先修改业务代码再补蓝图。

### 10.2 PUMI/API 停止条件

遇到任一情况必须停止：

- `Mesh2D` 与 `M3DC1ModelSpec` 无法无歧义映射；
- classification 依赖最近距离、容差吸附或投影猜测；
- 必须修改核心字段才能继续；
- 需要新增用户格式或 CLI，但蓝图未定义；
- 官方 API 与已确认契约冲突；
- 只能手写 SMB 字节；
- 必须引入多 face、多区域、Simmetrix、三维或并行分区；
- 交换格式无法严格验证；
- 无法链接锁定 imported targets；
- helper、编译器、PUMI 或 MPI ABI 无法确认相容；
- 无法明确 mesh/model/PCU/MPI 所有权和释放顺序。

### 10.3 输入层停止条件

遇到任一情况必须停止：

- `array_file` 需要改变 counted R-Z 计数头、空白分隔双列 R/Z、单位 m、严格 N 行、
  隐式闭合或简单闭环契约；
- 旧 `array_file` 路径需要多轮廓、孔洞、种子或任意 N 区域语言；已批准的
  `multi_array_file` 必须走独立 `regions` 契约，不能污染旧 Reader；
- 必须修改 `Mesh2D` 表示首版边界；
- GFile 与 array boundary 语义无法无歧义拒绝；
- 必须复制 OFT 重采样、点合并、segment、种子或 Triangle 算法；
- 无法可靠捕获唯一 outer Region；
- 必须从最终拓扑或最近距离猜测有序边界；
- 必须放宽 `outer_boundary` 简单闭环契约；
- 新来源缺少真实输入、物理语义或验收证据；
- `plot_mesh()` 无法在不修改 `Mesh2D` 的情况下接收参考 `GFileData`；
- 实现要求 `boundary_reader` 与 `gfile_reader` 直接依赖；
- 参考 GFile 必须进入 Mesher 或 Writer 才能绘制 LCFS；
- `array_file_path` 与只读参考 `gfile_path` 无法在 `plot_lcfs` 条件下无歧义校验；
- 当前授权 TRIMEG Loader 出现本蓝图未定义的正式 LCFS dataset；
- HDF5 Writer 的 `Rbc/Zbc` 不再直接来自 `Mesh2D.outer_boundary`；
- 必须修改 `Mesh2D`、Writer、ModelSpec 或 helper exchange 才能完成 PNG 叠加；
- 必须把 LCFS 写入目标格式才能完成参考绘图；
- 发布候选相对路径设计依赖未经验证的 ABI、RPATH、临时解压或系统库假设。

### 10.4 当前禁止事项

- 第二网格引擎、三维网格、环向或并行分区；
- 未经调查和蓝图批准的局部加密、动态自适应或磁面对齐；
- 未经生成侧探针和后续 C1/classification 调查批准的 LinkMesh M3D-C1 多区域或多
  geometric face；M3D-C1 求解器本身具备多区域模拟能力不自动开放 LinkMesh 输出；
- 在 schema v2 获 User 批准且 native probe 前修改 helper exchange schema；
- 把 conforming triangle topology 等同于 C1 有限元连续性；
- 把网格密度分区自动解释为物理区域；
- 仅凭 Region 数量判断 M3D-C1 C1 是否冲突；
- `split_smb`、`part*.smb`、SMB loader 或 validator；
- 手写、解析、修改、拼接或模板化 SMB；
- Simmetrix、`make_model`、`.smd`、`.sms` 正式依赖；
- 自动猜测物理边界、通用插件、注册表或区域 DSL；
- 为展示 OFT 功能而把 LinkMesh 扩展为 OFT 通用前端；
- 让 Reader 互相调用，或让 Mesher/Writer读取参考 GFile；
- 把 array boundary 解释为 LCFS，或把 LCFS 解释为 array 实际计算边界；
- 把 LCFS 写入 TRIMEG `Rbc/Zbc` 或私自新增 HDF5 dataset；
- 在没有对应测试或真实运行证据时把 `plot_lcfs` 工作流写成 PASSED 或 GENERATED；
- 在打包探针完成前宣称已实现物理意义上的真正单文件可执行程序；
- 修改 M3D-C1、TokaMaker 或 SCOREC/PUMI 只读参考源码。

### 10.5 v4.1 交付优先级、调查边界与待决事项

初版 Release 已发送给同门和老师，当前反馈为可以正常使用。该事实只达到实际交付和
当前用户反馈层级，不自动证明时间推进、长期稳定性或物理正确性。

multi-array OFT 能力、编号和 no-plasma 调查已经完成，inspect/generate 与生产
N-region `Mesh2D` 已实现。多区域 TRIMEG 接线已完成，User 最新直接证据确认真实
HDF5 已生成且自动测试和实际检测通过；标准 MATLAB/TRIMEG consumer 加载仍待验收。
M3D-C1 多区域输入契约调查已经完成，但实现仍未开放。以下更高级 OFT 能力调查契约
继续保留：

必须区分：

| 能力 | 含义 | 当前状态 |
|---|---|---|
| 全局常数 `dx` | 整个 Region 使用一个目标尺度 | 已支持 |
| 分区域常数 `dx` | 不同 Region 使用不同常数尺度 | OFT 官方能力已确认；LinkMesh multi-array 尚未实现和探针 |
| 静态空间变密度 | 单一闭合二维区域中尺度随位置变化 | 待调查，未实现 |
| 动态自适应 | 根据求解结果或误差反复调整网格 | 不在当前实现范围 |
| 磁面对齐 | 网格方向或节点分布与磁通面/磁场结构关联 | 待能力定位，未开放 |

OFT 26.6 调查必须确认：

1. `gs_Domain`、`Region`、`Mesh`、`run_triangle`、`dx`、`dx_curve`、region seed
   和 Triangle area constraint 的真实数据流。
2. 是否存在位置相关 size function、局部 refinement、背景尺度场、生成后 refinement
   或质量改善接口。
3. nested、adjacent、hole 和不同 Region `dx` 下是否共享节点和边，界面是否严格
   conforming，是否出现重复点、裂缝、重叠或非流形边。
4. Region 仅作为网格密度分区时，是否可以在下游保持一个 geometric face。
5. OFT topology、SCOREC/PUMI geometric classification 与 M3D-C1 C1 有限元连续性
   的关系。
6. 多 geometric face 是否保持、中断或改变 M3D-C1 所需连续性。
7. 若升级当前 single-region/single-face 契约，`M3DC1ModelSpec`、TXT、
   classification、exchange schema 和 helper 分别需要哪些修改。

调查只能形成直接源码证据、最小运行探针和候选架构。调查完成并先更新蓝图前，不得
开放空间变密度、M3D-C1 多区域或多 face，也不得修改当前 Writer 和 helper 契约。
具体技术裁决以本文为准；`docs/linkmesh/work_plan.md` 仅是人类阶段记事本，不是
Aider 执行依据或第二份技术契约。

当前 multi-array 产品接口裁决和实施边界：

- `multi_array_file` 至少包含两个 block；单 block 由 inspect 拒绝并引导到既有
  `array_file + single_region`；
- 空行在文件首尾、block 间和 block 数据内均忽略，首版不支持注释；
- regions 使用独立配置解析模型、正式二级子命令和默认 < TOML < CLI 优先级；
- inspect 必须输出 TOML regions map，generate 必须同时读取 map 和原始输入；
- map 不保存摘要，首版不计算或校验 SHA-256；
- generate 只核对可重建的 curve/Region/parent/children/technical-role/编号结构，
  用户负责保持输入未被实质修改或重排；
- `physical_label` 是可编辑的可选普通字符串，默认空且不参与建网；
- dx 使用全局默认加局部覆盖；无全局默认时局部映射必须完整覆盖；
- 第一批 inspect 业务已经实现：multi-array Reader、基础数组检查、curve_id、
  轻量 parent/child、唯一 root、deterministic synthetic plasma role、OFT setup-only
  最终 Region ID、TOML regions map 和 inspection PNG；
- 第二批 generate 业务已经实现并通过真实 two-level/four-level 验证：map/结构重验、
  `--mesh-dx`、`--region-dx`、独立配置合并、N-region OFT/Triangle、`Mesh2D`、
  Region triangle count、基本结构检查和 mesh PNG；
- 当前第三批已实现 `regions generate --target {mesh_only,trimeg}` 与 `--hdf5`，
  默认保持 mesh-only；TRIMEG 分支复用既有 complete-11 Writer；
- 多区域 HDF5 已由 User 确认生成，自动测试和实际检测通过；标准 MATLAB/TRIMEG
  consumer 加载仍为 PENDING；
- M3D-C1 多区域输入契约调查已完成。下一步不是直接开放任意 N-region，而是由 User
  裁决构建结果/mappings 接口和 schema v2，并用严格嵌套最小 fixture 验证共享
  analytic edge、orientation、special loop tags 与 interface classification；
- 在 Linux 基于本轮 master 生成外部三文件 Release，验证内部 manifest、外部
  tar.gz.sha256、可移动入口和干净环境运行；
- 将通过结构与运行验证的发布候选交付普通用户并取得初期 M3D-C1/TRIMEG 使用报告；
- 已交付 M3D-C1 网格的后续加载、初始化、时间推进、稳定性和物理结果；
- 卢老师对最新 LinkMesh TRIMEG HDF5 的测试反馈；
- EAST 边界物理构造算法和网格尺度需求；
- TCV 参考边界和 TRIMEG 实际消费；
- Python 正式打包、CMake install 和干净发布候选；
- 正式共享根目录、权限、modulefile、首个 release 和普通用户验收。

### 10.6 文档完整性纪律

- 本文档保持第 1 至第 10 节连续结构。
- v1–v3 的实施过程、故障排查、测试计数和迁移过程由 `History.md` 与
  `docs/linkmesh/LinkMesh_Architecture_Plan_v3.7.md` 承载，不在 v4.0 重复展开。
- 不通过重复章节保存过期状态。
- 字段表、格式表、算法步骤、停止条件和验收矩阵应作为完整语义块维护。
- 完全等价重复只保留一处；包含额外约束的内容必须保留其额外约束。
- 内部引用必须指向当前章节，不得引用旧第 6A 节。
- `History.md` 保存完成阶段的详细过程和证据；本文只保存当前权威契约与必要证据边界。
- `examples/m3dc1_single_region/linkmesh.in.example` 的存在不产生新契约。
- 状态更新必须有直接证据，并保持加载、初始化、时间推进、稳定性和物理正确性分层。
- 多 face、三维、自适应网格和并行分区继续未开放。

当前准确结论：M1–M3 和既有 TRIMEG 消费验收已通过；nested-three-region 已完成
真实 DIII-D 与 fixed-boundary 的 LinkMesh 生成侧验收；M4 LinkMesh 生成侧已通过；
M5 第一条 `m3dc1 + single_region + lcfs` 真实 CLI、PNG、TXT+SMB 加载和
M3D-C1 初始化已通过。EAST counted R-Z 文件结构、Reader、`single_region +
array_file`、OFT/Triangle、Mesh2D、TXT+SMB+PNG 生成侧和 PNG 人工几何检查已通过；
本次结果为 104 个输入边界点、185 个节点、329 个三角形和 1 个区域。EAST
M3D-C1 加载、初始化回归和时间推进仍为 PENDING；其物理构造算法及其与 LCFS、
第一壁、磁轴和 X-point 的精确关系仍为 PENDING。

当前 TRIMEG HDF5 CLI 使用 `--hdf5` 作为正式参数，`--h5` 作为完全同义别名；
二者共用 `hdf5` 配置输入并最终形成 `EffectiveConfig.hdf5_path`。旧 `--output`
已从当前接口一次性删除。TOML `[output].hdf5`、`--no-hdf5`、HDF5 Writer 和
TRIMEG 完整 11 数据集契约均未改变。

当前 helper 正式接口为 `native/linkmesh_scorec_helper/`、`linkmesh-scorec-helper`
和 `LINKMESH_SCOREC_HELPER`。Release 外部三文件构建、launcher、bootstrap、
分层检查和静态结构回归已在源码层实施；尚未基于本轮 master 在 Linux 生成正式
tar.gz，也尚未验证内部 manifest、外部 tar.gz.sha256、完整二进制依赖或普通用户
运行。Python 正式安装、CMake install、共享根目录、包装入口、modulefile、第一个
共享 release 和普通用户验收仍为 `PENDING`。

v4.2 正式收口 `array_file + 可选 GFile LCFS PNG reference`、CLI help 分组和
profile 尺度消歧。`EffectiveConfig` 为 17 字段；single-region 用户接口使用
`mesh_dx`，nested-three-region 用户接口使用三个区域 dx。旧 `--min-angle` 与
`--max-area` 不再属于 CLI。array reference PNG 仅绘制 Mesh boundary 与 LCFS
reference，不绘制参考 GFile 的 limiter、First wall 或 Magnetic axis。

该候选工作流中，array file 永远是唯一实际计算域边界，GFile LCFS 只供 Plotter。
因此不修改 `Mesh2D`、TRIMEG 11 数据集、HDF5 Writer、M3D-C1 ModelSpec、TXT、
SMB、classification 或 helper exchange。当前授权 TRIMEG Loader 和正式 11 数据集
契约中未发现独立 LCFS reference 输入位置，第一版参考曲线只进入 PNG。

初版 Release 已经交付同门和老师，当前反馈可正常使用。后续新版本可移动发布归档和
正式共享部署仍须分层验收。文档必须区分一个统一用户入口命令、一个可移动发布目录和
物理意义上的单文件可执行程序；在打包及 ABI 探针完成前不得宣称真正单文件已经实现。
候选运行时仍需专门处理 OFT 26.6、
`linkmesh-scorec-helper`、SCOREC/PUMI、MPI、C++ runtime 和 ABI，不得提前写死
未经验证的相对目录、RPATH、临时解压方案或系统库兼容性。

OFT 单区域静态空间变密度、Triangle refinement、多区域界面拓扑、M3D-C1 C1 与
多区域/多 face 兼容性调查继续保留为 P2。动态自适应、磁面对齐、M3D-C1 多区域、
多 face、三维和并行分区均未开放。

v4.3 Release 迁移只修改正式蓝图、仓库导读、发布基础设施、唯一最终用户 README、
发布专项静态回归和必要 Git 排除规则。未修改业务源码、native helper、业务测试、
示例、依赖、`History.md`、`CONTEXT.md`、历史蓝图、外部参考源码或
`docs/trimeg/loadfemmesh_h5.m`。

v4.4 新增 `multi_array_file` 与 `regions` 的初始设计方向，并完成 OFT 26.6
`meshing.py`、OFT 携带 `triangle.h` 和当前 LinkMesh 业务边界的只读调查。

v4.5 补充 OFT 官方 `gs_Domain`、`Region` 与 ITER 多区域示例证据，确认 OFT
多 Region 和分 Region常数 dx 能力；正式采用 `regions inspect/generate` 二级
子命令、OFT 最终 Triangle attribute Region ID、inspect regions map 与首版轻量包含
推导。首版不引入 Shapely/GEOS 或通用鲁棒计算几何系统。专项报告为
`docs/linkmesh/multi_array_regions_investigation_report.md`。本轮只更新技术文档，
未修改业务源码、测试、依赖、nested-three-region、Mesh2D、Writer、helper 或目标
格式，未运行 OFT 探针，也未生成新的 N-region 网格。

初版 Release 已经发送给同门和老师，当前反馈为可以正常使用；不得再笼统记录为尚未
生成或尚未交付。缺少更高等级直接证据的时间推进、稳定性和物理结果继续按各自状态
记录，不由 Release 反馈外推。

multi-array 业务状态为 **IMPLEMENTED**。OFT 五类合成案例及其 dx variants 已完成
修正后重跑，generation、mesh structure、numbering 和 overall 全部 PASS，证据层级
为 **GENERATED / STRUCTURALLY CHECKED**；setup-only、fresh rebuild、dx-change
编号和输入重排影响已确认，no-plasma 路径已确认由 OFT 主动拒绝。生产路径的轻量
包含推导、regions inspect/generate、TOML regions map、synthetic role Adapter、
分 Region dx 和 N-region `Mesh2D` 已实现；真实 two-level/four-level 多区域网格已
生成并完成结构检查，PNG 已生成并由 User 人工复核。

`regions generate` 的多区域 TRIMEG 接线为 **IMPLEMENTED**，真实多区域 HDF5 为
**GENERATED**；User 确认自动测试和实际检测均通过，但未提供精确 passed 数、完整
结构检查字段或标准 consumer 日志，因此标准 MATLAB/TRIMEG consumer 加载仍为
**PENDING**。

M3D-C1 多区域输入契约调查为 **COMPLETED**，教程三 face 拓扑与 exchange 多 face
record 表达能力为 **CONFIRMED**。schema v2、multi-face ModelSpec、多区域
classification、helper 多 face 支持和 `regions generate target=m3dc1` 分别保持
`DESIGNED / USER APPROVAL PENDING`、`DESIGNED / NOT IMPLEMENTED`、
`DESIGNED / NOT IMPLEMENTED`、`DESIGNED / NATIVE PROBE PENDING` 和
`CANDIDATE / NOT OPEN`。多区域 TXT+SMB 为 **NOT GENERATED**，同门消费验证为
**PENDING**。不得从共形 Triangle topology、`Mesh2D.region_ids` 或 single-face
ModelSpec 自动推导 multi-face classification 或 C1 兼容性。
