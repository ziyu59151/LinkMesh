# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **3.4**（本轮仅进行章节结构整理：将输入/配置/CLI、TRIMEG、M3D-C1 TXT/SMB/native helper、真实场景、里程碑验收及变更纪律重新归类为第 1 至第 10 节，并更新内部交叉引用；不改变任何技术契约、字段、接口、格式、编号约定、阶段状态、验收结论或下一阶段路线）
- 最高依据：本文档自身即为 LinkMesh 项目最高技术依据；开发纪律见 `CONTEXT.md`；已完成阶段的详细测试计数、提交过程与样例侦察证据见 `History.md`；M4-0 前置侦察逐轮证据见 `report.md`、`m4_0d_report.md`、`m4_0d1_report.md`、`m4_0d2_report.md`；OFT Region 重采样接口冲突只读核对见 `m3_complete11a_report.md`（阶段证据，非本蓝图正文的长期正式依赖，蓝图正文自包含）
- 事实边界：标注【已确认事实】为可执行工程事实；【待源码确认】为需只读侦察验证的事项；【PLANNED / PENDING IMPLEMENTATION / NOT IMPLEMENTED】为已批准正式契约但尚未实现的功能；【P0 禁止】为当前阶段严格禁止引入的功能；【实现候选】为已有源码调用点线索但须目标版本与最小运行验证确认、不得写成固定接口的路线；【版本锁定兼容接口】为 User 已批准、绑定特定 OFT 版本、范围受控、失败即停止的私有依赖，不是通用稳定公共 API
- 修改前置条件：任何对本文档接口、字段、验收标准或禁止事项的修改，必须由人类主管在对话中明确确认后方可执行

---

## 1. 项目定位与范围

LinkMesh 是一个**独立命令行程序（CLI）**，用于打通「等离子体平衡文件 GFile/EQDSK → 二维非结构三角网格 → 目标求解器静态网格文件」的转换链路。

**唯一网格生成底座**：OFT/TokaMaker 封装方式调用的 Triangle（OFT 内部经 `liboft_triangle` 完成）。LinkMesh 不维护第二种网格引擎。

**SCOREC/PUMI 架构位置（M4 相关，非第二剖分引擎）**：LinkMesh 调用 SCOREC 网格技术栈中由目标 PUMI 软件包提供的 APF、MDS、GMI、PCU 与 PUMI 接口；SCOREC 与 PUMI 不是两个互不相关的网格引擎，PUMI 也不是 LinkMesh 的第二个剖分器。GMI 表达 analytic geometric model；APF 提供网格实体抽象与接口；MDS 提供 native mesh 数据结构及 SMB 写出能力；PCU 提供初始化、通信或相关运行支持，其最小调用方式由 M4-1B probe 确认；PUMI 提供相关公共接口与 M3D-C1 使用的集成层。M4 中 LinkMesh 把既有 `Mesh2D` 与 `M3DC1ModelSpec` 转换为 classified APF/MDS mesh，再调用官方 `writeNative` 生成 SMB。PUMI/APF/MDS 不重新生成三角剖分；OFT/Triangle 始终是唯一三角剖分底座。

**正式数据流**：

```text
GFile/EQDSK → Reader → OFT Adapter → Mesh2D → TRIMEG HDF5 / M3DC1 TXT model + PUMI SMB → PNG
```

**M4 P0 正式生产链（v3.0）**：

```text
GFile
  → OFT/Triangle
  → Mesh2D
  → single-face M3DC1 model Adapter
  → M3DC1ModelSpec
      ├── LinkMesh TXT model Writer
      │     └── <base>.txt
      └── LinkMesh SCOREC/PUMI Adapter
            └── classified APF/MDS mesh
                  └── 目标版本官方 writeNative（或等价官方接口）
                        └── 分区前串行 native SMB
```

该生产链的目标是替代旧流程中由 Simmetrix 完成的 geometric model 创建与二维
meshing 链，而不是复制旧工具或把旧中间格式纳入 LinkMesh。正式链中禁止引入
Simmetrix、SimModeler、MeshSim、`make_model`、`.smd`、`.sms`、`split_smb`、
`part*.smb`、三维环向拉伸、并行分区、MPI ownership 持久化或手写 SMB。
OFT/Triangle 仍是唯一三角剖分底座；SCOREC/PUMI/APF/MDS 只承担 geometric
classification、APF/MDS mesh 构造和 native SMB 写出。

TXT Writer 与 SCOREC/PUMI Adapter 必须由**同一个** `M3DC1ModelSpec` 驱动，
共享一致的 geometric vertex tags、geometric edge tags、loop tags、face tags、
edge endpoint order、face↔loop topology 与 geometric classification 语义；
禁止两条输出路径各自独立编号。

**证据环境边界**：

- 本地 LinkMesh 仓库是开发与蓝图维护工作区；服务器外部样例目录
  `/data/liuchang/east_fishbone_1/` 不属于本地仓库，也不是 LinkMesh 运行时依赖。
- User 对服务器样例的只读调查仅作为外部直接证据。`east.txt` 的 1 loop、104
  geometric vertices、104 geometric edges、闭合末边与 1 face 只能辅证既有
  `save_model`/`save_multi_rgn_model` ↔ `load_model` 双向契约；104、固定坐标、
  文件大小和校验摘要均不是格式常量或测试期望。
- 服务器日志确认旧流程使用 Simmetrix 创建 geometric model、写 `.smd`、生成并写
  `.sms` 后重新加载；现有证据未确认 `.sms` 到 `.smb` 的具体命令，也未确认
  SCOREC/PUMI 精确版本，不得补写为事实。
- User 已在 liustation 完成目标环境只读调查；服务器 `/opt/spack` 与
  `/data/liuchang` 路径不属于本地 LinkMesh 仓库，不得由本地开发流程访问、复制、
  创建或假定存在。服务器输出在本蓝图中属于外部直接证据。
- M4-1B probe 与 M4-2 PUMI Adapter 已在具有目标 PUMI 安装的服务器环境中完成
  编译和生成侧运行；组内同学随后已在真实 M3D-C1/SCOREC 环境成功加载配套
  TXT+SMB 并完成 M3D-C1 初始化。时间推进、稳定性与物理正确性仍未验收。本地开发
  仓库、服务器外部调查环境与目标编译运行环境必须保持区分。
- M4 首要兼容目标锁定为同一套 Spack 构建实例：PUMI 2.2.9，Git commit
  `f87525cae7597322edfb2ccf1c7d4437402d948`，Spack hash `333b2ut`，
  GCC 13.3.0，Open MPI 4.1.6，Zoltan 3.901，CMake Release 构建；
  variants 为 `~fortran ~int64 ~ipo ~shared +simmodsuite_version_check ~testing
  +zoltan`，`simmodsuite=none`。
- 该服务器实例的调查前缀为
  `/opt/spack/opt/spack/linux-zen4/pumi-2.2.9-333b2utt2vneffaporuf7kaenhpow7x5`；
  该绝对路径只用于标识本次外部调查实例，**不是**跨平台固定路径、默认配置或允许
  硬编码进 LinkMesh 业务源码的值。
- 目标实例已确认存在 `include/apfMDS.h`、`include/apfMesh2.h`、
  `include/apf.h`、`include/gmi.h`、`include/PCU.h` 与 `include/pumi.h`。
  Spack 依赖树同时确认 glibc 2.39、CMake 3.28.3、GNU Make 4.4.1、
  METIS 5.1.0 与 ParMETIS 4.0.3。
- 当前 `m3dc1_2d` 调试信息中的 Spack build hash 与上述 GCC 13.3.0 实例一致；
  另一个 oneAPI 构建不是当前首选，禁止混用两套实例的头文件或库，也禁止混用不同
  MPI ABI。
- 后续依赖定位应通过 M4-1B probe 确认的 CMake 配置、环境变量、Spack 加载或明确
  命令行参数完成，不得把服务器绝对安装前缀写入业务源码。

**当前阶段状态（v3.3）**：

| 阶段 | 状态 |
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
| M4-2 SMB Writer/helper | **IMPLEMENTED / PASSED** |
| M5 第一条 `single_region + lcfs` M3DC1 CLI | **PASSED（真实 DIII-D GFile 最小闭环）** |
| M5 PNG 人工检查 | **PASSED** |
| M3D-C1 配套 TXT+SMB 加载 | **PASSED** |
| M3D-C1 初始化 | **PASSED** |
| M3D-C1 时间推进主循环 | **PENDING** |
| M3D-C1 中等或长时运行稳定性 | **PENDING** |
| M3D-C1 物理结果正确性 | **PENDING** |
| EAST 样例边界调查 | **NEXT** |
| EAST 细密单区域网格生成 | **PENDING** |
| TCV 参考边界调查 | **PENDING** |
| TCV/TRIMEG 实际消费 | **PENDING** |
| `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED；未开放** |
| `single_region + array_file` | **接口预留 / PLANNED；业务未实现** |
| 多区域、多 face、三维和并行分区 | **OUT OF P0 / 未开放** |

M4 P0 使用已经验收的 `single_region + lcfs` `Mesh2D`，限定 single-region +
single-face。M4-1A TXT model、M4-1B 实现入口 probe 与 M4-2 LinkMesh 生成侧均已
完成。Python SMB Writer、独立 C++ helper、schema v1 私有交换、classified
GMI/APF/MDS mesh、严格 `verify()`、官方 `writeNative()` 与正常资源清理已在锁定的
SCOREC/PUMI 2.2.9 目标环境真实运行通过。

组内同学现已在真实 M3D-C1/SCOREC 环境成功加载 LinkMesh 生成的配套 TXT+SMB，
且 M3D-C1 已使用该配套文件完成初始化。因此，配套加载与初始化均更新为
**PASSED**。该证据不表示完整 M3D-C1 模拟已经通过：时间推进主循环、中等或长时
运行稳定性、物理结果正确性以及最终网格精度需求仍为 **PENDING**。LinkMesh 继续
不建设 SMB loader、SMB validator、M3D-C1 消费端或通用 PUMI 验证工具。

**P0 范围**：

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；`array_file` 两列 CSV 边界（PLANNED） | 在 LinkMesh 侧手写 GFile 文本解析；复杂 CAD；多维输入；Python ndarray 公共边界 API |
| 网格生成 | 调用 OFT `gs_Domain` / `build_mesh()` | 引入第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；修改/维护 OFT 分支 |
| 并行切分 | 不涉及；LinkMesh M4 P0 终点为分区前串行 native SMB | 开发、复制或替代 `split_smb`；生成 `part*.smb` 或任何环向/并行分区；生成 `**1.smb`~`**16.smb` 等分区文件 |
| 输出 | TRIMEG HDF5；M3DC1 配套 analytic model TXT + 分区前串行 PUMI native SMB（M4，经 PUMI/APF/MDS 官方 API） | 三维输出；Simmetrix/`make_model`/`.smd`/`.sms` 正式依赖；手写、拼接、修改、模板复制或逆向 `.smb` 二进制字节流 |
| 可视化 | matplotlib 自检 PNG | 交互式/三维渲染 |
| 配置 | 当前 CLI 参数；已实现的两层输入架构（`linkmesh.in` + CLI，见第 6A 节） | 通用配置 DSL / 任意 N 区域语言 / 插件系统 |

---

## 2. 当前架构与模块职责

允许依赖方向：`cli → config / readers / mesher / writers / utils`；`mesher.oft_adapter → mesh`；`writers → mesh`；`utils.plotter → mesh`；`config` 不依赖 Reader/Mesher/Writer/Plotter；`readers.boundary_reader → mesh`（仅复用统一边界验证）。`mesh.py` 不依赖任何后端、Writer、CLI、Plotter 或 config。

| 模块 | 职责（一段式） | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 任何业务逻辑或参数解析 |
| `src/linkmesh/cli.py` | 解析/验证用户显式 CLI 参数（含三个区域 `dx` 与已实现的 `--config/--no-config/--target/--profile/--boundary-source/--array-file`），拦截历史 `--min-angle/--max-area`，调用配置合并（见 `config.py`）得到 `EffectiveConfig`，按 target 编排 Reader → `generate_mesh()` → HDF5 Writer 或共享 `M3DC1ModelSpec` 的 TXT/SMB Writers → Plotter | 实现区域/几何/种子/Triangle 算法或任何 dx 换算；自行合并三套默认值/文件/CLI（合并交给 `config.py`）；恢复已删除历史边界构造代码；解析 TOML；读取 helper 环境变量或插入 SMB rank |
| `src/linkmesh/config.py`（已实现） | 定义只读/不可变 `EffectiveConfig`；用标准库 `tomllib` 读取并严格校验 `linkmesh.in`；合并「内建默认值 < 配置文件 < 用户显式 CLI」；按配置目录/当前工作目录两套基准解析路径；校验 `target/profile/boundary_source` 兼容矩阵与 required fields；输出已完成路径解析与类型验证的 `EffectiveConfig`。当前只放行 `m3dc1 + single_region + lcfs` 这一条 M3DC1 组合，并要求 GFile、TXT model 与 SMB 基础路径 | 读取 GFile；读取 array boundary 数据；构造 OFT Domain；调用 Mesher/Writer/Plotter；建设通用配置 DSL、插件系统或任意 N 区域语言；保存值来源字典/ndarray/句柄/argparse Namespace；放行其他 M3DC1 组合 |
| `src/linkmesh/mesh.py` | 定义 `Mesh2D`（唯一正式统一网格对象）与只读统计属性；对 `outer_boundary`（若提供）执行集中式验证（含完整非相邻边自交检查，见第 3.2 节） | 依赖 OFT/Triangle/HDF5/PUMI/CLI/Plotter/config；共享可变默认数组；读取任何 OFT 私有属性 |
| `src/linkmesh/readers/gfile_reader.py` | 薄 Adapter：调用 OFT `GEQDSKEquilibrium`，提取字段封装为 `GFileData`；仅允许 LCFS 闭合/方向后处理 | 手写文本解析；调用 Triangle；写文件 |
| `src/linkmesh/readers/boundary_reader.py`（PLANNED，未实现） | 轻量边界输入：读取 `array_file`（两列 CSV），输出 `(B,2) float64` 边界点列，执行文件语法/shape/有限性/基础点列检查，完整简单闭环几何验证委托 `mesh.py` 统一边界验证入口 | 创建 `Mesh2D`；调用 OFT；读取 GFile；引入 pandas |
| `src/linkmesh/mesher/oft_adapter.py` | 三层接口：`mesh_from_oft_domain(domain)` 通用 N 区域核心（含 N=1）、`build_oft_domain_from_gfile(gfile_data, plasma_dx, vacuum_dx, outer_dx, ...)` 默认策略层、`generate_mesh(...)` 便利入口；single-region polygon 来源在进入 `add_polygon()` 前按第 6A.11 节执行稳定相邻近重复点规范化；将 `pts/lc/reg` 规范化为 `Mesh2D`；在锁定的 OFT 26.6 环境中，由策略层受控捕获 outer Region 引用并于 `build_mesh()` 后读取 `outer_region._resampled_points` 得到 `outer_boundary`（版本锁定兼容接口，见第 3.2A 节）。所有 OFT 私有属性依赖集中封装于本模块内 | 解析 TOML；复制 OFT 通用几何/种子/重采样/segment 拼接/方向/全局重编号/Triangle 算法；写死区域数量/名称/类型/ID；无依据再次偏置 0-based 连接表；解析 `_reg_seg_map`/`_resampled_segments`/`Mesh._resampled_points`；调用 `Region.get_resampled_points()` 作为 `outer_boundary` 来源；回退四角/`idxevert`/最终 `pts/lc` 反推/自行重采样；把 OFT 私有依赖泄漏到 `Mesh2D`/Writer/CLI/Plotter；修改 OFT 源码或依赖 `TOKAMAKER/` 快照；把 OFT `merge_thresh` 暴露为 P0 公共配置 |
| `src/linkmesh/writers/hdf5_writer.py` | 接收 `Mesh2D`，按 TRIMEG HDF5 契约写出（见第 5 节） | 修改 `Mesh2D`；写 `region_ids`；转置 `vert/tria`；给 `tria` 加第四列；从 `idxevert` 反推 `Rbc/Zbc`；网格生成逻辑；判断配置来源 |
| `src/linkmesh/m3dc1_model.py`（M4-1A 已实现） | 定义 single-region、single-face、single-loop `M3DC1ModelSpec` 及从 `Mesh2D.outer_boundary` 构造 geometric vertices、directed LIN edges、loop 与 face 的 Adapter | 依赖 PUMI/SCOREC/MPI/Simmetrix；保存 PUMI 句柄；固定 104 个点；把 `region_ids` 自动当 face tag |
| `src/linkmesh/writers/m3dc1_model_writer.py`（M4-1A 已实现） | 独立接收 `M3DC1ModelSpec`，按 `save_model()`/`save_multi_rgn_model()` ↔ `load_model()` 双向契约写出 M3D-C1 analytic geometric model TXT；已独立完成 Level 1 | 读取或复制 `east.txt` 固定坐标；把 104 写成常量；输出两列 CSV；调用 Simmetrix/`make_model`；写 `.smd`/`.sms`；自行分配一套与 PUMI Adapter 不一致的 tag |
| `src/linkmesh/writers/smb_writer.py` | M4-2 Python 公开 Writer 与编排入口；接收已验证的 `Mesh2D`、同一 `M3DC1ModelSpec`、SMB 基础路径及可选 helper 路径，确定性生成 classification 与版本化内部交换文件，调用独立 C++ helper，捕获退出码/stdout/stderr，并确认 rank-0 native SMB 存在且非空 | 创建 GMI/APF/MDS entity；读取、解析、修改或实现 SMB 字节；硬编码服务器 PUMI 前缀；实现 Level 2/3 loader；修改输入对象 |
| `native/m3dc1_smb_helper/main.cc`（M4-2 已实现并通过生成侧服务器运行） | 唯一 M4-2 原生 helper 源文件；读取内部交换契约，初始化并管理 MPI/PCU/GMI/APF/MDS 生命周期，创建完整 analytic model 与 classified 2D MDS mesh，执行 `acceptChanges()`、严格 `verify()`、`writeNative()`，并以结构化阶段错误和非零退出码报告失败。helper 不是第二网格生成器 | GFile/OFT/Triangle 网格生成；Python CLI/配置；TXT Writer；SMB loader/validator；M3D-C1 消费端；多区域、多 face、三维、分区、Simmetrix 或 SMB 字节实现 |
| `native/m3dc1_smb_helper/CMakeLists.txt`（M4-2 已实现并通过目标环境构建） | 仅构建 `linkmesh-m3dc1-smb-helper` 的最小独立 CMake target；锁定 SCOREC 2.2.9 imported targets 与相容 MPI C++ target | 通用 native/plugin 框架；Python 扩展打包；运行时编译；硬编码服务器安装前缀 |
| `src/linkmesh/utils/plotter.py` | `plot_lcfs_only()`、`plot_mesh()`（支持区域着色、LCFS/第一壁闭合显示） | 修改任何数据对象 |

M4-1A 已实现 M3DC1 目标专用对象 `M3DC1ModelSpec`、single-face model Adapter
与独立 TXT model Writer；M4-2 已实现 Python SMB Writer → 独立 C++ helper →
SCOREC/PUMI/APF/MDS 官方 API 的生成侧 Adapter（第 7 节）。
首版只实现 single-region + single-face，不在 M4 P0 提前设计多 face Writer；
未来多 face 规划保留。

**M4/M5 当前状态（v3.3）**：

**M4-1A：ModelSpec 与独立 TXT Writer（PASSED）**

M4-1A 已完成以下实际实现：

1. `src/linkmesh/m3dc1_model.py`：single-region、single-face、single-loop
   `M3DC1ModelSpec` 及 `Mesh2D.outer_boundary` Adapter。
2. `src/linkmesh/writers/m3dc1_model_writer.py`：独立 TXT geometric model Writer。
3. `tests/test_m3dc1_model_writer.py`：M4-1A 专项契约测试。

Adapter 从 `Mesh2D.outer_boundary` 动态构造 geometric vertices、directed
geometric edges、唯一 loop 与唯一 face。P0 curve 使用线性类型 `LIN=1`。
TXT Writer 输入仅为 `M3DC1ModelSpec`，不依赖 PUMI、SCOREC、MPI、Simmetrix、
`make_model`、SMB、`.smd` 或 `.sms`，并已实现：

- 严格按 `save_model()`/`save_multi_rgn_model()` ↔ `load_model()` 双向契约写出；
- 写出含 5 个整数的完整头部、loop ID 与 edge 数；
- 写出 geometric vertex ID 及 `x/y/z`（P0 第三坐标为 0）；
- 写出 geometric edge ID、begin/end vertex ID 与 curve type；
- 写出完整 `numFaces>0` face 段；
- 保证全部 ID 唯一、引用存在、edge endpoint order 正确且 loop 闭合；
- 不输出两列 CSV，不读取或复制 `east.txt`，不固定 104 个点。

User 提供的服务器直接运行证据：

- `python -m pytest -q tests/test_m3dc1_model_writer.py`：
  **52 passed in 0.23s，退出码 0**；
- `tests/test_mesh.py` 与 `tests/test_hdf5_writer.py` 相关回归：
  **101 passed in 0.37s**；
- 独立实际写出冒烟验证：`M4_1A_SMOKE=PASS`；
- 冒烟输出为完整 model TXT，头部 `1 -1 1 -1 -1`，最小样例含
  4 geometric vertices、4 geometric edges、1 loop 与 1 face。

上述证据将 M4-1A 与 Level 1 状态更新为 **PASSED**。M4-2 LinkMesh 生成侧随后
已实现并通过；配套 TXT+SMB 的真实 M3D-C1/SCOREC 加载与初始化现也已
**PASSED**。时间推进主循环、中等或长时稳定性与物理结果正确性仍为 **PENDING**。

**M4-1B：目标环境与实现入口 probe（COMPLETED / PASSED）**

首要兼容目标已锁定并完成实现入口验证：

- SCOREC/PUMI 2.2.9；
- Git commit `f87525cae7597322edfb2ccf1c7d4437402d948`；
- Spack hash `333b2ut`；
- GCC 13.3.0；
- 目标 MPI C++ 工具链 `/usr/bin/mpicxx`；
- 本次调查安装前缀
  `/opt/spack/opt/spack/linux-zen4/pumi-2.2.9-333b2utt2vneffaporuf7kaenhpow7x5`。

该绝对安装前缀只标识当前首要兼容环境与验收实例，不是跨平台固定路径，不得硬编码
到 LinkMesh 业务源码。未来更换版本、编译器或 MPI ABI 时必须重新执行入口 probe。

目标 SCOREC 2.2.9 的 CMake 构建接入已确认：

- 使用 `find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED ...)`；
- 使用正式 imported targets：`SCOREC::mds`、`SCOREC::apf`、
  `SCOREC::gmi`、`SCOREC::pcu`；
- 使用 MPI C++ target 或与 `/usr/bin/mpicxx` 目标工具链一致的等价正式接入方式；
- 不使用该目标配置并未提供的 `SCOREC_INCLUDE_DIRS` 或
  `SCOREC_LIBRARIES` 变量。

首次 probe 配置失败的原因是错误假设 `SCORECConfig.cmake` 提供
`SCOREC_INCLUDE_DIRS`/`SCOREC_LIBRARIES`；改用 imported targets 后，CMake
配置、头文件发现、编译与静态链接均成功。该失败属于 probe 构建接入修正过程，
不是 PUMI 安装、LinkMesh 架构或 SMB 方案失败。

目标 PUMI 2.2.9 已由编译和运行确认以下调用形式与最小路径：

- `apf::makeEmptyMdsMesh(gmi_model* model, int dim, bool isMatched)`；
- P0 创建二维非 matched MDS mesh 使用 `model`、`dim=2`、
  `isMatched=false`；
- `Mesh2::createVertex(ModelEntity*, Vector3 const&, Vector3 const&)`；
- `Mesh2::createEntity(int type, ModelEntity*, MeshEntity** down)`；
- 最小 probe 成功创建 3 个 classified mesh vertices、3 个 classified mesh
  edges 与 1 个 classified mesh triangle；
- `acceptChanges()` 成功；
- 写出前 `verify()` 成功；
- 官方 `writeNative()` 成功生成非空 native SMB。

rank-0 文件命名的本次目标版本运行事实：

- `writeNative` 接收带扩展名的基础路径；
- 传入 `m4_pumi_probe.smb` 时，单进程 rank 0 实际磁盘文件为
  `m4_pumi_probe0.smb`；
- 即 `<base>.smb` 对应实际 `<base>0.smb`。

本次 probe 文件大小为 319 字节，SHA-256 为
`bc56e915075146af11a7d4af9f77f578fa1517c0d12efa5814b57e4aa3a740f9`。
文件大小与摘要只用于追踪该次 probe 产物，不是 SMB 格式契约、固定常量或未来测试
期望；`m4_pumi_probe0.smb` 不得复制、模板化或作为 LinkMesh SMB 输出模板。

人工 probe 使用最小 analytic cells 构造 classified mesh，只负责确认目标环境、
构建接入、核心 API、`acceptChanges`、`verify`、`writeNative` 与 rank 文件命名。
其同进程重载没有通过：

1. 一次因把实际 rank 文件名传给会再次处理 rank 的 loader，尝试打开
   `m4_pumi_probe00.smb`；
2. 修正为基础名后，仍在人工 model 重载路径发生段错误。

当前证据不能确认该早期人工 probe 段错误的唯一根因；不得把 analytic model 拓扑
不完整、资源生命周期错误或 PUMI loader 缺陷中的任何一个写成已证实事实。该失败
不否定已经成功的编译、classified entity 创建、`acceptChanges`、`verify`、
`writeNative` 与非空 SMB 写出证据，也不构成 PUMI loader、SMB 格式或正式
LinkMesh 方案失败。该人工 probe 不再继续修补，也不扩展为 LinkMesh
loader/validator。后续正式配套 TXT+SMB 已由组内同学在真实 M3D-C1/SCOREC 环境
成功加载并完成初始化，从而取代该人工 probe 作为正式外部加载证据；时间推进及后续
稳定性、物理正确性仍待验证。

M4-1B 的职责是消除 M4-2 实现入口处的目标环境、构建接入和核心 API 不确定性，
不要求提前完成正式 LinkMesh TXT+SMB 的外部消费验收。因此 M4-1B 状态为
**COMPLETED / PASSED**。

**M4-2：classified mesh 与串行 SMB（IMPLEMENTED / LINKMESH 生成侧 PASSED）**

M4-2 已实现 Python SMB Writer、schema v1 私有交换文件和独立 C++ helper。正式数据链：

```text
Mesh2D + 与 TXT Writer 共用的 M3DC1ModelSpec
  → 构造与 TXT geometric tags 一致的完整 GMI analytic model
  → 构造 classified APF/MDS mesh
  → acceptChanges
  → verify
  → 目标 PUMI 2.2.9 官方 writeNative
  → 分区前串行 rank-0 native SMB
```

M4-2 已落实的生成侧职责：

1. 使用同一 `M3DC1ModelSpec` 创建完整 geometric vertex、edge、loop、face 拓扑。
2. 保证 TXT geometric tags 与 SMB classification tags 完全一致。
3. corner mesh vertex 分类到对应 geometric vertex。
4. boundary curve 上非 corner mesh vertex 分类到对应 geometric edge。
5. interior mesh vertex 分类到 geometric face。
6. boundary mesh edge 分类到对应 geometric edge。
7. interior mesh edge 分类到 geometric face。
8. mesh triangle 分类到 geometric face。
9. 根据 `Mesh2D` 拓扑和 `M3DC1ModelSpec` 显式、确定性地完成本地分类判定；
   不按坐标最近距离猜测，不把 `region_ids` 自动当 face tag。
10. 核对并规范 Triangle 三角形方向，使目标 PUMI `verify` 和正式加载成立。
11. 明确串行 residence/ownership 的目标版本用法。
12. 在成功路径和失败路径上明确并执行 mesh、model、PCU 与 MPI 生命周期。
13. 调用官方 `writeNative` 生成分区前串行 rank-0 native SMB。
14. 为 M5 形成 TXT + SMB + PNG + 终端统计交接包。

以上生成侧职责已实现并通过 synthetic `Mesh2D` 的目标服务器真实运行。该运行证明
Python Writer → schema v1 → helper → GMI/APF/MDS/PCU → 严格 `verify()` →
`writeNative()` → `<base>0.smb` 的 LinkMesh 生成链与正常生命周期成立。此后，正式
LinkMesh 配套 TXT+SMB 已被真实 M3D-C1/SCOREC 消费端成功加载并完成初始化；该新增
证据仍不证明时间推进、中等或长时稳定性、物理结果正确性、多区域、多 face、三维或
并行能力。

首版严格限定 single-region、single-face。M4-2 不实现多 face、多区域、三维、
环向切分、MPI 并行分区、`part*.smb`、`split_smb`、Simmetrix、`make_model`、
`.smd`、`.sms`、`.dmg`、M3D-C1 物理求解或任何手写、解析、修改、拼接、复制、
模板化、逆向 SMB 字节工作。

目标 PUMI 2.2.9 已运行确认 `<base>.smb` 写出实际 `<base>0.smb`；该规则作为首要
兼容目标的实现依据，不升级为跨 PUMI 版本无条件事实。正式验收不要求输出与外部样例
或人工 probe 具有相同文件大小、SHA-256、内部实体编号或字节布局，只比较 topology、
坐标、connectivity、classification、计数、`verify`、可视化与 TXT+SMB 配套加载
语义。

### M4-2 Python/C++ 集成边界（v2.9 正式契约）

#### 唯一集成链

M4-2 P0 的唯一正式跨语言调用链为：

```text
src/linkmesh/writers/smb_writer.py
  → 独立进程 linkmesh-m3dc1-smb-helper
  → SCOREC/PUMI 2.2.9 的 GMI/APF/MDS/PCU 官方 API
  → 分区前串行 rank-0 native SMB
```

选择独立 helper 的原因：

- 首要兼容的 PUMI 2.2.9 实例提供静态库，不能把 `ctypes` 直接加载静态库作为可靠
  集成方案；
- helper 进程隔离 MPI、PCU、GMI、APF、MDS 的初始化、资源所有权和释放顺序，
  避免污染 Python 进程生命周期；
- P0 不引入 pybind11、scikit-build-core 或其他 Python ABI 扩展打包体系；
- helper 是 LinkMesh M4-2 的正式目标格式 Adapter，不执行剖分，不是第二网格
  生成器。

P0 明确禁止：`ctypes` 直接加载静态 PUMI；pybind11/scikit-build-core 扩展；
运行时生成或编译 C++；通用 native plugin/adapter 注册框架；复制 probe 可执行文件；
复制 319 字节 probe SMB；手写、拼接、解析或修改 SMB。

#### 原生组件唯一落点

```text
native/
└── m3dc1_smb_helper/
    ├── CMakeLists.txt
    └── main.cc
```

该目录只承载 M4-2 专用 helper，不扩展为通用 `native/adapter/plugin` 抽象体系。
正式构建产物名称固定为：

```text
linkmesh-m3dc1-smb-helper
```

Python 公开 Writer 落点保持：

```text
src/linkmesh/writers/smb_writer.py
```

已实现的 P0 Python 接口为：

```text
write_smb(
    mesh: Mesh2D,
    spec: M3DC1ModelSpec,
    filepath: str | os.PathLike[str],
    *,
    helper_path: str | os.PathLike[str] | None = None,
) -> None
```

上述源文件、构建文件和 Python 接口均已实现；本节现作为 M4-2 已实现集成契约与
后续兼容性维护边界。

#### Python Writer 职责

`write_smb()` 必须：

1. 接受已经验证的 `Mesh2D`、同一个 `M3DC1ModelSpec`、目标 SMB 基础路径和可选
   helper 路径。
2. 启动 helper 前验证类型、shape、dtype、有限值、0-based 索引范围、无退化
   triangle、single-region、single-face、输出父目录及输出路径冲突。
3. 保持 `Mesh2D` 的节点与连接表为 0-based，不修改输入对象或任何 NumPy 数组。
4. 由离散拓扑与 `M3DC1ModelSpec` 确定性生成全部 mesh entity classification。
5. 创建并完整关闭一次调用所需的版本化内部交换文件。
6. 以独立子进程调用 helper，并同时捕获退出码、标准输出和标准错误。
7. 按目标 PUMI 2.2.9 rank-0 命名规则，由 `<base>.smb` 定位实际
   `<base>0.smb`，确认其为普通文件且非空。
8. helper 失败时抛出明确异常，至少包含失败阶段、退出码、原生错误摘要和保留的
   交换文件路径。
9. 成功后删除交换文件；失败后保留交换文件用于诊断，不静默清理。
10. 不在 Python 中创建 GMI/APF/MDS entity，不读取、解析或修改 SMB 字节。
11. 不硬编码服务器 PUMI 安装前缀，不实现 Level 2/3 loader。

#### Classification 唯一责任层与确定性规则

classification 的唯一责任层固定为 **Python Writer 内部的 M4-2 离散拓扑
Adapter**。C++ helper 只消费并严格执行交换契约中的 classification，不再次根据
坐标或拓扑猜测分类。

P0 规则：

1. 从 `triangles` 生成规范无向 mesh edge `(min(node0,node1), max(node0,node1))`，
   去重后按端点二元组字典序确定交换文件中的 edge 顺序。
2. triangle 无向边只出现一次时属于拓扑外边界；所有边必须只出现一次或两次，
   出现次数大于 2 立即失败。
3. 拓扑外边界必须形成唯一简单环：每个 boundary node 的 boundary degree 必须为
   2，且一次遍历必须覆盖全部 boundary edges。
4. `M3DC1ModelSpec` 的每个 geometric vertex 坐标必须与 `Mesh2D.nodes` 中恰好一个
   boundary node **逐分量精确相等**；不得使用最近邻、距离最小化或容差吸附。
   找不到或找到多个候选时立即停止。
5. 以 loop 中 directed geometric edge 的起点 corner 顺序作为方向锚点。拓扑边界
   环必须存在唯一方向，使 corner node 顺序与 geometric loop 的 directed vertex
   顺序完全一致；两个方向都不成立或不能唯一确定时立即停止。
6. corner mesh vertex 分类到对应 geometric vertex `(dim=0, tag=vertex.tag)`。
7. 同一对相邻 corner 之间沿已定向拓扑边界环出现的非 corner mesh vertices 分类到
   对应 directed geometric edge `(dim=1, tag=edge.tag)`。
8. 该边界链中的 mesh edges 分类到同一 geometric edge。
9. 非边界 mesh vertices、非边界 mesh edges 和全部 triangles 分类到唯一
   geometric face `(dim=2, tag=face.tag)`。
10. 不从 `region_ids` 推导 face tag；`region_ids` 只用于确认输入确为单一区域。
11. 禁止按最近坐标距离、几何投影或启发式容差猜测 classification。

以上规则依赖 geometric corner 在最终 `Mesh2D.nodes` 中具有唯一精确对应。若正式
真实输入不能满足该条件，属于 M4-2 实现停止条件；必须先报告并修订蓝图或上游正式
数据契约，不得静默改用容差最近邻。

#### 内部交换契约

内部交换文件仅用于一次 `write_smb()` 调用，schema 名称为
`LinkMesh M4 Exchange`，首版 schema version 为 `1`。它不是用户输入格式、不是
新网格格式、不是长期归档格式，也不是 SMB 替代品。

编码固定为单个 little-endian 二进制文件，以避免新增 JSON/TOML/HDF5 C++ 解析依赖。
所有整数使用明确宽度；字符串使用 UTF-8；浮点使用 IEEE-754 binary64。文件按以下
顺序写入：

1. 8 字节 magic：ASCII `LM4XCHG` 后跟一个 NUL 字节。
2. `uint32 schema_version`，值固定为 `1`。
3. `uint32 endian_marker`，值固定为 `0x01020304`。
4. 计数区，依次为 `uint64 N`、`T`、`E`、`GV`、`GE`、`GL`、`GF`。
5. special loop tags，依次为四个 `int32`：
   `separatrix_loop`、`inner_wall_loop`、`outer_wall_loop`、`vacuum_loop`。
6. 输出 SMB 基础路径：`uint64 byte_length`，随后为不含 NUL 的 UTF-8 字节。
7. `nodes`：`N×2 float64`，C-order，每行 `[R,Z]`，单位 m。
8. `triangles`：`T×3 uint64`，C-order，Python 0-based。
9. geometric vertices：`GV` 条记录，每条为
   `int32 tag + float64 r + float64 z + float64 y`。
10. geometric edges：`GE` 条记录，每条为
    `int32 tag + int32 begin_vertex_tag + int32 end_vertex_tag +
    int32 curve_type`。Schema v1 只接受 `LIN=1`，不含曲线 payload。
11. geometric loops：每个 loop 先写
    `int32 tag + uint64 edge_count`，随后写 `edge_count` 个 `int32 edge_tag`。
12. geometric faces：每个 face 先写
    `int32 tag + uint64 loop_count`，随后写 `loop_count` 个 `int32 loop_tag`。
13. mesh vertex classification：`N` 条
    `int32 geometric_dimension + int32 geometric_tag`。
14. mesh edges：`E` 条
    `uint64 node0 + uint64 node1 + int32 geometric_dimension +
    int32 geometric_tag`；端点满足 `node0 < node1`，记录按端点字典序排列。
15. triangle classification：`T` 条
    `int32 geometric_dimension + int32 geometric_tag`。
16. 文件必须在最后一条记录后立即结束；helper 拒绝截断数据和任何尾随字节。

Schema v1 的 P0 约束固定为：`GL=1`、`GF=1`、所有 geometric curves 为 LIN、
所有 triangle class 为唯一 face、全部节点与边索引为 0-based。Python 和 helper
必须分别进行独立的边界、计数、溢出、引用完整性、tag、classification dimension、
classification tag、索引范围和文件长度校验。

交换契约不得承载 PUMI 指针或句柄、SMB 字节、MPI ownership、C1 field、高阶节点、
adaptation metadata、运行时 field、numbering、partition residence 或 ghost 信息。

Python Writer 在目标输出目录内创建唯一隐藏临时交换文件，写完并 flush、fsync、
关闭后才启动 helper。helper 只读打开该文件且不删除它。成功时 Python Writer 删除
交换文件；任何 Python 校验、子进程、helper 或输出确认失败时保留交换文件，并在
异常中报告其路径。

helper 调用参数语义固定为：

```text
linkmesh-m3dc1-smb-helper --input <exchange-file>
```

输出 SMB 基础路径由交换文件承载，不通过第二套参数重复传入。helper 成功返回 `0`；
交换契约错误、模型构造错误、mesh 构造错误、`acceptChanges`、`verify`、
`writeNative` 或清理错误均返回非零。标准错误必须输出一行结构化阶段信息：

```text
LINKMESH_M4_ERROR stage=<stage> message=<summary>
```

成功时标准输出必须包含：

```text
LINKMESH_M4_OK base=<base-path> rank0=<actual-rank0-path>
```

路径和摘要的具体转义由实现时严格定义；不得依赖解析任意 PUMI 日志来判断成功。

#### C++ Helper 职责与生命周期（已实现并经目标服务器运行确认）

`linkmesh-m3dc1-smb-helper` 只负责：

1. 初始化锁定目标环境所需的 MPI、PCU 和 GMI 运行环境。
2. 读取并严格校验 schema v1 交换文件。
3. 按交换数据中的同一个 `M3DC1ModelSpec` 语义建立完整 geometric vertices、
   directed edges、loop 与 face 拓扑。
4. 通过 `findModelEntity`、`toModel` 或目标版本确认的等价正式方式取得
   classification entities，并校验 dimension/tag。
5. 调用 `apf::makeEmptyMdsMesh(model, 2, false)`。
6. 按 node index 创建 classified mesh vertices。
7. 按交换文件 edge 顺序创建 classified mesh edges。
8. 按 triangle index 创建 classified mesh triangles，并在创建前执行目标版本要求的
   orientation 规范化。
9. 设置且仅设置目标 PUMI 2.2.9 源码确认必需的串行 residence/ownership。
10. 依次执行 `acceptChanges()`、`verify()`、`writeNative()`。
11. 记录输入基础路径与实际 rank-0 文件路径。
12. 按已确认的所有权顺序释放 mesh、model、PCU 和 MPI：
    - helper 创建并独立管理 GMI analytic model；
    - APF/MDS mesh 在构造和写出期间使用该 model；
    - 销毁 mesh 前调用 `apf::disownMdsModel(mesh)`，明确解除 MDS 对 model 的所有权；
    - 随后依次调用 `mesh->destroyNative()` 与 `apf::destroyMesh(mesh)`；
    - GMI model 由 helper 的唯一独立所有者调用一次 `gmi_destroy(model)`；
    - analytic point/line callback data 必须在 mesh 和 model 完成使用及 model 销毁期间保持有效；
    - 完成原生对象合法清理后，再按当前实现顺序释放 PCU 并执行 MPI Finalize。
13. 以非零退出码和 `LINKMESH_M4_ERROR` 报告任何失败。

helper 不负责 GFile、OFT、Triangle、网格生成、Python CLI/配置、TXT model Writer、
classification 推断、Level 2/3 loader、多区域、多 face、三维、分区、split、
Simmetrix、`.smd`、`.sms`、`.dmg` 或 SMB 字节实现。

成功和失败路径都必须遵守上述单一所有权与释放顺序。禁止删除
`gmi_destroy(model)`、依靠 helper 进程退出泄漏 model、重复销毁 model、跳过
`disownMdsModel`、跳过 `destroyNative`/`destroyMesh`，或以进程异常终止掩盖
生命周期问题。该规则来自目标 SCOREC/PUMI 2.2.9 的实际构建、运行与
`gmi_destroy → NativeModel::~NativeModel → main` 故障定位，以及加入
`disownMdsModel` 后的同环境成功重测。

#### 构建和运行时定位

helper 使用 `native/m3dc1_smb_helper/CMakeLists.txt` 中的单一最小 target：

```text
linkmesh-m3dc1-smb-helper
```

构建契约：

- `find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED ...)`；
- 链接 `SCOREC::mds`、`SCOREC::apf`、`SCOREC::gmi`、`SCOREC::pcu`；
- 链接与 `/usr/bin/mpicxx` 首要目标工具链 ABI 相容的 MPI C++ imported target；
- 禁止使用目标配置不存在的 `SCOREC_INCLUDE_DIRS` 或 `SCOREC_LIBRARIES`；
- 禁止在源码或 CMake 文件中硬编码服务器 PUMI 绝对安装前缀；
- 依赖定位只通过 SCOREC CMake config、Spack 加载环境、标准 CMake prefix
  配置或明确构建参数完成；
- 本版不实施 `pyproject.toml` 与 CMake 的自动集成，不允许 Python 运行时编译。

Python Writer 查找 helper 的唯一优先级为：

1. `write_smb(..., helper_path=...)` 显式参数；
2. 环境变量 `LINKMESH_M3DC1_SMB_HELPER`；
3. 当前进程 `PATH` 中的 `linkmesh-m3dc1-smb-helper`。

第一个被指定或找到的候选必须是普通可执行文件，并通过 helper 启动时的 schema 与
目标版本自检；候选缺失、不可执行或版本不相容时立即失败，不继续猜测仓库 build
目录或服务器安装路径。显式参数或环境变量已设置但无效时不得降级到下一层。

更换 PUMI 版本、编译器或 MPI ABI 后，必须重新执行入口 probe、LinkMesh 生成侧
验收及同门外部消费兼容性验收；不得仅复用旧 helper 二进制。

#### 最小测试边界

M4-2 测试与验收按以下最小分层维护：

- Python 静态测试只覆盖输入验证、schema v1 交换读写契约、helper 缺失/不可执行、
  helper 非零退出码、结构化错误传播、rank-0 输出定位、成功/失败临时文件清理策略
  和输入对象/NumPy 数组不变性。
- 不使用 Mock/Fake PUMI 模拟 entity 生命周期、MPI/PCU 释放顺序、`verify` 或
  `writeNative`，也不以 Mock 证明 SMB 正确。
- helper 的 geometric model、classified entity 创建、orientation、串行
  residence/ownership、`acceptChanges`、严格 `verify`、`writeNative` 和生命周期，
  已在锁定的目标服务器 PUMI 2.2.9 环境以 synthetic `Mesh2D` 真实验证。
- Python SMB Writer 专项测试结果为 17 passed；M4 相邻回归结果为 170 passed。
- 正式 M5 `single_region + lcfs` 已在真实 DIII-D GFile 上同时生成 TXT、SMB、PNG
  和终端统计；配套 TXT+SMB 已由组内同学在真实 M3D-C1/SCOREC 环境成功加载并完成
  初始化。时间推进主循环、中等或长时稳定性与物理结果正确性仍待验收。
- LinkMesh 不建设 SMB loader、SMB validator、M3D-C1 消费端、大型 Fake
  SCOREC/PUMI 或通用原生测试框架。

#### M4-2 维护停止条件

后续维护或兼容性修正遇到以下任一情况必须停止并报告：

- 无法无歧义映射 `Mesh2D` node/edge 与 `M3DC1ModelSpec` geometric entities；
- classification 必须依赖最近距离、容差最近邻、投影猜测或其他启发式；
- 必须修改 `Mesh2D` 或 `M3DC1ModelSpec` 字段才能继续；
- 必须新增用户可见格式、CLI 参数或配置字段，但蓝图尚未定义；
- 目标 PUMI 官方 API 与 v2.8 已确认的调用契约冲突；
- helper 只能通过手工 SMB 字节操作完成；
- 必须引入多 face、多区域、Simmetrix、三维或并行分区；
- Python/C++ 交换契约无法严格验证；
- 目标环境无法链接锁定的 SCOREC imported targets；
- helper、PUMI、编译器或 MPI ABI 版本无法确认相容；
- 不能在成功和失败路径上明确 mesh/model/PCU/MPI 所有权与释放顺序。

本节现记录 M4-2 已实现的跨语言边界。M4-1A 为 **PASSED**，M4-1B 为
**COMPLETED / PASSED**，M4-2 LinkMesh 生成侧为 **IMPLEMENTED / PASSED**。
真实 M3D-C1/SCOREC 配套 TXT+SMB 加载与初始化均为 **PASSED**；时间推进主循环、
中等或长时稳定性与物理结果正确性仍为 **PENDING**。这些后续验收不要求 LinkMesh
建设 loader/validator，也不否定已经通过的 M5 第一条真实 CLI 最小闭环。

**M4 验收边界（v3.3）**：

- Level 1（LinkMesh TXT 静态契约）：正式 LinkMesh TXT 结构与 model 契约，
  M4-1A 已通过；
- LinkMesh 生成侧验收：Python SMB Writer 专项测试、M4 相邻回归、目标
  SCOREC/PUMI 2.2.9 helper 构建、schema v1 读取、classified mesh 创建、严格
  `verify()`、官方 `writeNative()`、rank-0 文件确认和完整生命周期已通过；
- 外部加载验收：组内同学已在真实 M3D-C1/SCOREC 环境成功加载同一份
  `M3DC1ModelSpec` 驱动的配套 TXT+SMB，状态为 **PASSED**；
- M3D-C1 初始化验收：消费端已使用该配套 TXT+SMB 完成初始化，状态为
  **PASSED**；
- M3D-C1 时间推进主循环、中等或长时运行稳定性及物理结果正确性仍为
  **PENDING**，不得由成功加载或初始化外推；
- LinkMesh 不开发轻量 PUMI/APF loader、仓库内 SMB validator、M3D-C1 消费端或
  通用 PUMI 验证工具，不解析、反向读取或验证 SMB 字节；
- 后续时间推进若暴露格式或分类兼容性问题，其结果作为必要修正证据，但不会把
  loader/validator 建设纳入 LinkMesh；
- 完整 M3D-C1 正式运行仍由同门或导师环境负责；
- 319 字节人工 probe、synthetic 产物的 955 bytes、173 bytes TXT 或任何 SHA-256
  只用于对应运行追踪，不是格式常量、通用验收标准或外部消费通过证据。

`split_smb`、`part*.smb`、环向切分与并行分区不属于任何 LinkMesh M4 P0
实现里程碑，由既有组内超算流程负责。

M4 P0 使用已验收的 `single_region + lcfs` `Mesh2D`，限定 single-region +
single-face，输出必须是配套 TXT geometric model + PUMI `.smb`。Triangle 仍是唯一
网格剖分底座；PUMI/APF/MDS 只承担目标格式构造与输出，不是第二网格生成器。禁止
手写、拼接、修改、模板复制或逆向 `.smb` 字节流；`region_ids` 不自动等同于
M3DC1 geometric face tag；C1 field、高阶节点、运行时 field 与
adaptation/restart metadata 不属于初始静态网格输出要求。

M4-1B 已消除目标环境、CMake imported targets、`makeEmptyMdsMesh`、
`createVertex`、`createEntity`、`acceptChanges`、`verify`、`writeNative` 与
rank-0 写出命名的实现入口不确定性。该 probe 只是目标环境、CMake、核心 API 和
rank 文件命名的早期入口探测程序，不是官方工具、产品模块、SMB loader 或 validator；
它不进入 LinkMesh 产品目录，也不得继续扩展为正式验证器。

M4-2 已使用同一 `M3DC1ModelSpec` 建立 GMI analytic model，完成确定性
classification、Triangle 方向处理、串行 ownership、严格验证、官方 native 写出与
成功/失败生命周期。LinkMesh 生成侧因此标记为 **PASSED**。真实 M3D-C1/SCOREC
配套 TXT+SMB 加载与初始化均已 **PASSED**；时间推进主循环、中等或长时稳定性与
物理结果正确性仍为 **PENDING**。M5 第一条真实 CLI 最小闭环已经通过，不再处于
待编排状态。目标环境若无法继续使用所需 PUMI/APF/MDS 官方库，仍必须停止，不得
回退手写 SMB。

**版本选择纪律**：

- M4 首要目标固定为上述 PUMI 2.2.9、GCC 13.3.0、`/usr/bin/mpicxx` 与
  Spack hash `333b2ut` 的同一实例，不默认采用 PUMI 最新版本；
- CMake 使用 `find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED ...)`、
  `SCOREC::mds`、`SCOREC::apf`、`SCOREC::gmi`、`SCOREC::pcu` 及相容 MPI
  C++ target，不依赖不存在的 `SCOREC_INCLUDE_DIRS`/`SCOREC_LIBRARIES`；
- 禁止混用 GCC 与 oneAPI 构建的头文件或库，禁止混用不同 MPI ABI；
- 禁止将服务器绝对安装前缀硬编码进 LinkMesh 业务源码；
- 依赖定位通过已确认的 CMake config/imported targets、环境变量、Spack 加载或
  明确命令行参数完成；
- 未来更换 PUMI 版本、编译器或 MPI ABI 时，必须重新执行最小入口 probe、LinkMesh
  生成侧验收及同门外部消费兼容性验收。

当前准确状态：M4-1A TXT/Level 1 **PASSED**；M4-1B 实现入口 probe
**COMPLETED / PASSED**；M4-2 LinkMesh 生成侧 **IMPLEMENTED / PASSED**；M5 第一条
`m3dc1 + single_region + lcfs` 真实 CLI 最小闭环与 PNG 人工检查均 **PASSED**；
真实 M3D-C1/SCOREC 配套 TXT+SMB 加载与初始化均 **PASSED**；时间推进主循环、
中等或长时稳定性与物理结果正确性均 **PENDING**。

**M5 第一条正式 CLI 闭环（PASSED；当前唯一开放的 M3DC1 组合）**

允许组合：

```text
target=m3dc1
profile=single_region
boundary_source=lcfs
```

正式数据流：

```text
CLI / EffectiveConfig
  → read_gfile()
  → oft_adapter.generate_mesh(
        profile="single_region",
        boundary_source="lcfs",
    )
  → Mesh2D
  → build_single_face_model_spec(mesh)  # 一次且仅一次
  → 同一个 M3DC1ModelSpec
      ├── write_m3dc1_model(spec, model_path)
      └── write_smb(mesh, spec, smb_base_path)
  → plot_mesh(gfile_data, mesh, plot_path, show_region_ids=True)
  → 终端统计
```

**真实 DIII-D GFile 最小闭环证据**：

- 正式组合：`target=m3dc1`、`profile=single_region`、
  `boundary_source=lcfs`、`plasma_dx=0.08 m`；
- GFile 读取结果：LCFS 原始点数 81，第一壁点数 88；
- OFT/`Mesh2D` 结果：唯一计算域边界点数 55，344 个节点、631 个三角形、1 个区域；
- `build_single_face_model_spec(mesh)` 只构造一次，TXT Writer 与 SMB Writer 接收
  同一个 `M3DC1ModelSpec`；
- 实际生成 M3D-C1 TXT 2275 bytes、rank-0 native SMB 44823 bytes、PNG
  235388 bytes，CLI 日志完整运行到结束且正常退出；
- SMB Writer/helper 实际完成目标 SCOREC/PUMI 2.2.9 `writeNative()`；
- User 已人工检查 PNG：LCFS 轮廓合理，网格覆盖单区域，未观察到明显孔洞、越界、
  折叠或显著异常单元；
- 上述大小和计数只标识本次运行证据，不是格式常量、固定测试期望或其他输入的结果承诺；
- PNG 人工检查本身不证明 SMB 可被 M3D-C1 正确消费；后续组内同学已独立确认配套
  TXT+SMB 成功加载并完成 M3D-C1 初始化。时间推进主循环、中等或长时稳定性与物理
  结果正确性仍为 **PENDING**。

**自动测试事实边界**：

- 服务器配置与 CLI 专项测试结果为 **145 passed、2 failed**，不得表述为全套通过；
- 一项失败是旧测试期待 `ConfigError`，而未开放的
  `m3dc1 + single_region + first_wall` 实际以 `NotImplementedError` 正确拒绝；
  组合拒绝行为成立，测试对异常类型的预期待清理；
- 另一项失败是旧测试仍期待默认 `trimeg` 流程调用 SMB Writer，而当前正式 target
  分派规定 `trimeg` 只进入 HDF5 分支，不进入 M3DC1 SMB 分支；旧测试预期待清理；
- 相邻回归命令引用了不存在的 Plotter 测试路径，因此未执行，不能记录为通过或失败；
- 这些测试债务不覆盖真实 GFile CLI 最小闭环已经成功的直接证据，也不证明未运行的
  相邻回归已经通过。

M5 编排规则：

1. TXT Writer 与 SMB Writer 必须共享同一个 `M3DC1ModelSpec` 对象，确保 geometric
   dimensions、tags、directed edges、loop 与 face classification 语义一致。
2. `--model` 表示 M3D-C1 analytic model TXT 输出路径。
3. `--smb` 表示未插入 MPI rank 的 SMB 基础路径 `<base>.smb`；CLI 不得改写为
   `<base>0.smb`，单进程物理 rank 文件命名继续由 PUMI 与 SMB Writer 管理。
4. `--plot` 表示现有 `utils.plotter.plot_mesh()` 生成的 PNG 人工自检路径。
5. helper 定位继续完全由 `smb_writer.py` 按显式参数、环境变量
   `LINKMESH_M3DC1_SMB_HELPER`、`PATH` 的既有优先级负责；CLI 不解析该环境变量，
   不硬编码服务器 PUMI 前缀。
6. CLI 只做模块编排，不实现 geometry、LCFS polygon、region、seed、
   classification、GMI/APF/MDS、SMB 字节或 helper 生命周期。
7. PNG 用于人工检查 LCFS 边界形态、单区域网格覆盖、明显孔洞、越界三角形、
   折叠或显著异常单元；PNG 人工检查不替代 M3D-C1 加载、初始化、时间推进、稳定性
   或物理正确性验收。
8. `config.py` 已解除 `m3dc1 + single_region + lcfs` 的过期阶段闸门，并继续拒绝
   其他 M3DC1 组合。
9. `target=trimeg` 保持既有 HDF5 行为；`target=mesh_only` 不进入任何 Writer，
   但配置 `plot_path` 时仍可绘图。

M5 当前不得开放：

- `m3dc1 + nested_three_region`
- `m3dc1 + first_wall`
- `m3dc1 + array_file`
- `m3dc1 + artificial_outer`
- `m3dc1 + flux_surface`
- 多区域、多 face、三维、环向分区或并行 split

**不得规划**：`inputs/` 插件包；抽象基类；source 注册表；通用 source plugin 系统。

---

## 3. 核心数据契约

### 3.1 `GFileData`（Reader 输出）

坐标单位 m，R 为大半径方向，Z 为垂直方向。字段全部由 OFT `GEQDSKEquilibrium` 属性提取，无手写解析。

| 字段 | 类型/shape | 来源属性 | 说明 |
|---|---|---|---|
| `lcfs_r` / `lcfs_z` | `np.ndarray (N_lcfs,)` | `boundary_R` / `boundary_Z` | LCFS 边界坐标 [m] |
| `rmaxis` / `zmaxis` | `float` | `R_mag` / `Z_mag` | 磁轴坐标 [m] |
| `wall_r` / `wall_z` | `Optional[np.ndarray (N_wall,)]` | `limiter_R` / `limiter_Z` | 第一壁；`None`/空表示输入未提供可用壁轮廓，不代表物理无壁 |
| `rcentr` | `Optional[float]` | `R_center` | 参考大半径 R0 [m] |
| `bcentr` | `Optional[float]` | `B_center` | 参考磁场 B0 [T] |
| `current` | `Optional[float]` | `Ip` | 等离子体电流 [A]，不缩放 |

### 3.2 `Mesh2D`（LinkMesh 统一中间网格对象）

**正式定位（v2.0，v2.1/v2.2/v2.3/v2.4 保持）**：`Mesh2D` 是 LinkMesh 面向多个下游模拟代码（TRIMEG、M3DC1/PUMI 等）的**统一、持久、求解器无关**中间网格对象。

原则：

- 保存下游共同需要、且在网格生成后**无法可靠反推**的规范几何、拓扑、物理标记与必要分类信息；
- 目标格式的索引、转置、dtype、布局转换由各 Writer 完成；不得把 TRIMEG/M3DC1/PUMI 的文件布局搬进 `Mesh2D` 内存布局；
- 可从 `triangles` 无损、确定性派生的边集合与邻接关系，**默认不重复存储**，除非 M4 直接证据证明必须持久保存；
- 不因追求"最完备"而提前加入未经证据确认的 C1 自由度、高阶节点、PUMI 私有句柄、MPI ownership、M3DC1 私有数组或求解器运行时对象；
- `Mesh2D` **不读取任何 OFT 私有属性**；所有 OFT 私有依赖集中在 OFT Adapter，`Mesh2D` 只接收已规范化、已验证的 `outer_boundary` 独立副本。

**核心字段（来自 OFT `build_mesh()`，内部索引 0-based）**：

| 字段 | shape | dtype | 说明 |
|---|---|---|---|
| `nodes` | `(N,2)` | `float64` | 线性二维节点 `[R,Z]` [m] |
| `triangles` | `(T,3)` | 整数（实测 `int32`） | 三顶点节点索引，**内部 0-based** |
| `region_ids` | `(T,)` | 整数（实测 `int32`） | OFT 最终区域编号，**原样保留**（不重编号/排序/压缩/+1）；LinkMesh 物理区域标签，**不等同于** M3DC1 geometric face tag |

**兼容字段（现存于 `mesh.py`，均安全空数组默认值，不参与 TRIMEG 契约）**：`boundary_segments (0,2) int32`、`boundary_markers (0,) int32`、`node_markers (0,) int32`。这三个字段**与下文 `outer_boundary` 不同义、不同名、语义不同**；不得改名或删除既有字段。

**`outer_boundary` 字段（正式定义，已实现并验收）**

`Mesh2D.outer_boundary` 表示当前 `Mesh2D` 所代表计算域**在进入 Triangle 前**的有序离散外边界。

| 属性 | 规定 |
|---|---|
| 类型 / shape / dtype | `Optional[np.ndarray]` / `(B,2)` / `float64` |
| 列含义 / 单位 | 第 0 列 R，第 1 列 Z / m |
| 语义 | 传入网格生成器的、有序、最外层计算域几何边界点；一条**单一简单闭合轮廓** |
| 闭合 | 末尾**不重复首点**，最后一点与第一点隐式闭合 |
| 方向 | 顺时针（带符号闭合面积严格为负） |
| 约束 | 至少 3 个互异有限点；无相邻重复点；无零长度闭合边；无退化面积；**单一简单闭环，禁止非相邻边自交**；P0 只允许一条最外层闭合轮廓 |
| 所有权 | 数组由 `Mesh2D` **独立持有**（构造期规范化为 float64 独立副本，即使输入已是 float64 ndarray 也不复用其内存、不修改输入），不与外部可变输入或 OFT 私有数组共享所有权 |
| 必选性 | **TRIMEG target 必须提供**；`mesh_only` 与 M3DC1 target 按各自目标契约处理，可为 `None`（不得把 TRIMEG 必填性扩大为所有目标全局必填） |
| 与 Steiner 点 | **不包含** OFT/Triangle 后续插入的边界 Steiner 节点 |
| 与 `idxevert` | 不等同于最终拓扑外边界节点集合；因生成器插点，`B` 可小于最终 `nvert_ex` |
| 性质 | 求解器无关的计算域几何，**不是**按节点编号升序生成的 `idxevert` 坐标表 |

**验证实现状态（已完成）**：`Mesh2D.__post_init__`（经统一验证入口 `_validate_outer_boundary`）对 shape、dtype、有限性、点数、相邻重复点、隐式闭合语义、方向、退化面积**以及完整非相邻边自交检查**（非相邻边严格交叉、端点接触、共线重叠；不误判相邻边、首末相邻边、合法顺时针凹多边形、共线但区间分离边）执行验证，并区分坐标容差（长度量纲）与 orientation 叉积容差（长度平方量纲）。HDF5 Writer 复用同一统一验证入口作为打开文件前的二次防线，不复制自交算法。该完整自交验证已由第一轮 `mesh.py`/`tests/test_mesh.py` 服务器专项测试通过。

`outer_boundary` **不是**：人工矩形四个控制角点；`Region.get_resampled_points()` 的返回值；最终按节点编号排序的 `idxevert`；Triangle 后续插入的全部 boundary Steiner points；由最终 `pts/lc` 反推的点；LinkMesh 自行重采样的点列；永久固定的 LCFS；永久固定的 first wall；永久固定的 artificial outer。

正确数据链：

```text
控制几何 / 边界来源
  → single-region polygon 来源按第 6A.11 节稳定规范化相邻近重复控制点
  → 策略层创建 outer Region 并捕获引用
  → domain.build_mesh()（OFT 内部完成重采样、共享边界处理、点合并、全局重编号、segment 方向处理，并回写 region._resampled_points）
  → 受控读取 outer_region._resampled_points（OFT/Triangle 输入前的真实有序离散点列）
  → 删除可能的普通显式闭合重复末点 + 验证 + 顺时针规范化 + float64 独立副本
  → Mesh2D.outer_boundary
  → TRIMEG Rbc/Zbc
```

对于 `artificial_outer`：人工矩形控制几何 → OFT 按网格尺度重采样 → `region._resampled_points`（Triangle 输入前离散边界）→ `outer_boundary`。**四个矩形控制角点不得直接代替离散边界点列。**

起点规则：当前无足够证据，不规定固定起点（不强制从最小 R/最大 R/最小 Z 起）。只要求点序相邻正确、方向为顺时针、同一输入与配置产生确定顺序。逆时针输入规范化为顺时针时**保持原起点**（输出 `[p0, p_(B-1), …, p1]`，不使用裸 `pts[::-1]`）。

### 3.2A `outer_boundary` 的 OFT 26.6 私有兼容接口（版本锁定兼容接口，User 已批准，已实现并验收）

**背景事实（服务器正式安装版 `openfusiontoolkit==26.6` 只读 introspection 直接证据，见 `History.md` 第 18/19 条与 `m3_complete11a_report.md`）**：

- OFT 26.6 **没有公开方法**直接返回"指定 Region 对应的 Triangle 输入前有序离散边界"。
- `Region.get_resampled_points()` 在 OFT 26.6 中**存在**，但它走**独立**重采样路径，**不是** Triangle 输入 `alpha["vertices"]` 的来源，**禁止**作为 `outer_boundary` 来源。
- OFT 26.6 的 `Mesh.__init__()` 在内部完成实际的边界重采样、共享边界处理、点合并、全局重编号与 segment 方向处理，并把对应 Region 的有序离散点列**回写**到 `region._resampled_points`（`region._resampled_points = numpy.asarray(reg_points)`；组装 `reg_points` 时负 segment 通过反向遍历 `_resampled_segments` 处理方向）。
- `Mesh.get_mesh()` 使用 `alpha = dict(vertices=self._resampled_points, segments=..., regions=...)`，Triangle 经 `run_triangle(alpha)` 接收该输入；即 Triangle 输入 `vertices` 的权威来源是 `Mesh._resampled_points`，与各 Region 回写的 `region._resampled_points` 同源同批（同一 `Mesh.__init__` 重采样过程）。

**OFT 26.6 Region 输入、全局点合并与回写点列语义（v2.4 新增已确认事实）**：

- `Region.__init__()` 对输入首末点执行普通显式闭合检查：仅当首末点距离小于 `dx / 1000` 时删除一个末尾点。
- 对相邻控制点，`Region.__init__()` 在相邻边长度小于 `dx_curve / 1000` 时输出 `Repeated points detected` 警告并跳过该点对应的角点分析，但**不从** `Region._points` 或 `Region._segments` 删除该相邻控制点。
- OFT 26.6 `Mesh.__init__()` 的锁定默认参数为 `merge_thresh=1e-4 m`；`gs_Domain.build_mesh()` 当前默认使用同一值。构造全局点表时，局部点与已有全局点的欧氏距离严格小于 `merge_thresh`，即 `< 1e-4 m`，则映射到同一个全局点。
- `Mesh.__init__()` 先构造经过全局点合并和 segment 重采样的坐标与拓扑表示，再按照每个 Region 的有向 segment 顺序，通过 `_reg_seg_map` 与 `_resampled_segments` 重建 `reg_points`，最后写入 `region._resampled_points`。
- 因此，`Region._resampled_points` 是**按区域 segment 拓扑顺序重建**的有序区域边界点列，坐标来自经过全局点合并与 segment 重采样的坐标表；它不是原始输入控制点的直接副本，不是 Triangle 后续生成的全部边界节点，不是无序的全局唯一点集合，也不是仅按坐标去重后的简单数组。
- 多个局部控制点可能因 `merge_thresh` 映射到同一个全局点，但区域 segment 的有序重建仍可能在 `region._resampled_points` 中多次引用该合并坐标。因此，OFT 全局点合并可能表现为 **Region 回写点列中的重复坐标**。
- 术语必须区分：输入末点重复首点是“显式闭合末点”；两个相邻输入控制点距离小于 OFT `merge_thresh` 是“相邻近重复控制点”；多个局部点映射到同一全局点是“OFT 全局点合并”；区域 segment 重建后同一合并坐标在有序点列中出现多次是“Region 回写重复坐标”；LinkMesh 要求末尾不重复首点、最后一点隐式连接第一点是“隐式闭合”。
- OFT 的 `Repeated points` / `Small feature` 警告不表示 Triangle 失败。真实 DIII-D
  LCFS 单区域来源曾在将含重复闭合坐标的回写点列转换为
  `Mesh2D.outer_boundary` 时暴露问题；该问题现已通过 single-region polygon
  相邻近重复控制点规范化修复。修复后 OFT/Triangle 已成功生成 344 个节点、
  631 个三角形和 1 个区域，并完成后续 TXT、SMB、PNG、M3D-C1 加载与初始化链路。
- `Region._resampled_points` 仍是 `outer_boundary` 的直接权威来源，但它是 OFT 私有拓扑表示，进入 `Mesh2D` 前必须规范化为 LinkMesh 的独立、顺时针、隐式闭合、单一简单闭环表示。不得通过放宽 `Mesh2D` 契约接纳 OFT 回写重复坐标。

**已实现并验收的受控依赖**：

- LinkMesh 在锁定的 `openfusiontoolkit==26.6` 环境中，在 OFT Adapter 内、由策略层明确捕获 outer `Region` 对象后，于 `domain.build_mesh()` 完成后受控读取该对象的私有属性 **`outer_region._resampled_points`**，作为 `outer_boundary` 的权威离散点列来源。
- 读取后创建 `float64` **独立副本**，按 `Mesh2D.outer_boundary` 契约验证并规范化（删除普通显式闭合重复末点、方向规范为顺时针并保持原起点）。
- 该受控读取链已由第二轮 `oft_adapter.py`/`tests/test_oft_adapter.py` 服务器专项测试
  通过，并经现有 `nested_three_region + artificial_outer` 两个真实 GFile 回归
  验证。LCFS 单区域来源暴露出的 OFT 点合并回写重复坐标问题已由第 6A.11 节规定的
  相邻近重复控制点规范化修复，并已通过真实 DIII-D GFile 的 TRIMEG、M3D-C1 生成
  闭环、配套加载与初始化验收；该路径当前为 PASSED。

**允许读取的 OFT 属性（唯一）**：

- 策略层已明确捕获的 `outer_region._resampled_points`。

**禁止读取或解析的 OFT 属性**：

- `domain.mesh._reg_seg_map`
- `domain.mesh._resampled_segments`
- `domain.mesh._resampled_points`（Mesh 级别聚合点列，禁止 LinkMesh 直接解析）

原因：OFT 已在 `Mesh.__init__` 内完成 Region 点列的方向与拼接并回写到 `region._resampled_points`；LinkMesh 只读取该回写结果，不再解释 OFT 私有 segment 语义、不复制 OFT 重采样/点合并/segment 拼接/方向/全局重编号算法，从而把版本耦合范围压到最小。第 6A.11 节规定的 single-region polygon 相邻近重复控制点预处理发生在调用 `add_polygon()` **之前**，仅用于避免已知输入控制点在 OFT 锁定默认 `merge_thresh` 下塌缩为同一全局点；它不解析上述私有属性，也不替代 build 后的 Region 回写读取。

**接口性质**：该私有依赖是**版本锁定、范围受控、失败即停止**的兼容接口（【版本锁定兼容接口】），**不是**一般稳定公共 API；只服务于获取 `outer_boundary`，不得扩展为 LinkMesh 对 OFT 私有结构的通用依赖。

**捕获与读取时机（固定）**：

1. single-region polygon 来源先按第 6A.11 节规范化相邻近重复控制点；nested 路径保持既有输入行为；
2. 策略层创建 outer Region；
3. 策略层**立即**保存该 Region 对象引用（不写死 region ID、不按名称猜测、不遍历私有 map），并在 `build_mesh()` 前保存到局部变量；
4. `domain.build_mesh()` 创建 OFT `Mesh` 并完成实际重采样、全局点合并及 Region 点列回写；
5. `build_mesh()` **完成后**读取 build 前保存的**同一个** outer Region 对象的 `outer_region._resampled_points`（即使 build 期间 domain 上私有属性被替换，也使用 build 前保存的原对象）；
6. 转换为独立 `float64` 副本；
7. 删除可能存在的一个普通显式闭合重复末点；
8. 验证 shape、有限性、点数、隐式闭合、简单闭环与非相邻边自交；
9. 规范化为顺时针（保持原起点）；
10. 写入 `Mesh2D.outer_boundary`；
11. HDF5 Writer 直接映射为 `nbcRZ/Rbc/Zbc`。

**不得**把读取时机写成 `build_mesh()` 之前——服务器证据已确认权威 Region 点列在 `Mesh.__init__()` 处理后才回写。通用 `mesh_from_oft_domain()` **不得**通过 region ID、名称猜测或遍历私有 map 推断 outer Region；outer Region 的选择与引用捕获属于**策略层**职责。

**防御性失败规则（任一条件必须明确失败）**：

- `openfusiontoolkit` 运行版本不是 26.6；
- outer Region 引用未捕获；
- `outer_region` 缺少 `_resampled_points`；
- 属性值为 `None`；
- shape 不是 `(B,2)`；
- 数据含 NaN 或 Inf；
- 点数不足；
- 显式闭合规范化后点数不足；
- single-region polygon 输入相邻近重复过滤后不足 3 点；
- single-region polygon 输入规范化后仍有相邻重复点或首尾重复点；
- Region 回写规范化后仍有相邻重复点、首尾重复点、自交、面积退化或不足 3 点；
- 轮廓退化；
- 方向或点序无法规范化；
- 非相邻边自交；
- 无法证明该 Region 是策略层创建的最外边界；
- OFT 内部接口与已核对签名或数据流不一致。

失败时**禁止**继续扩大静默修补，也禁止回退到：人工矩形四角；清理后的原始 LCFS 控制点；`Region.get_resampled_points()`；`idxevert`；最终 `pts/lc` 反推；LinkMesh 自行重采样；静默设置 `outer_boundary=None` 后继续 TRIMEG 输出。对不需要 `outer_boundary` 的目标仍按目标契约处理。

**禁止加入 `Mesh2D` 的数据（P0）**：triangle adjacency（由 triangles 派生）、geometric model handles、PUMI handles、geometric model tags、C1 field、edge orientation、boundary normal、boundary curvature、high-order nodes、MPI ownership。可确定性派生的数据默认由 Adapter、PUMI/MDS 或 M3D-C1 运行时生成。

**只读统计属性**：`n_nodes`、`n_triangles`、`n_boundary_segments`。

---

## 4. 网格与物理约定

- **坐标/单位**：`[R,Z]`，SI（m、T、A）。
- **内存索引**：`triangles` 内部 0-based；目标格式偏置（如 TRIMEG +1）由对应 Writer 在写出阶段完成。`region_id` 与节点索引转换无关，任何 Writer 都不得对 `region_id` 执行 `+1`。
- **OFT 输出契约**（已确认）：`pts (np,2) float64`、`lc (nc,3)` 0-based 整数（`0<=lc<N`）、`reg (nc,)` 正整数，与 `domain.region_info` 最终 ID 一一对应。
- **区域编号**：原样保留 OFT `reg`；区域语义只从 `domain.region_info` 名称/类型/最终 ID 获得，不由整数值推断；区域数量由 OFT 当前区域模型决定，不写死；合法单区域（N=1）满足契约。
- **区域校验**（`mesh_from_oft_domain`，在 `build_mesh()` 之后读取最终 `region_info`）：至少一个区域；`reg` 全为有限正整数；`len(reg)==T`；输出 ID 集合与最终 `region_info` 一致；每个区域至少一个三角形；不重编号/排序/压缩/+1。`build_mesh()` 会原地重排区域 ID，绝不能在其之前提取。
- **当前默认 GFile 区域策略**：有有效第一壁 → PLASMA+VACUUM+OUTER（`add_annulus`+`add_rectangle`）；无壁 → PLASMA+OUTER（`add_polygon`+`add_rectangle`）。这是当前 CLI 便利策略，非 Adapter 能力边界。single-region 策略见第 6A.11 节。
- **OFT 点合并参数（版本锁定）**：P0 继续调用 OFT 26.6 `build_mesh()` 的锁定默认 `merge_thresh=1e-4 m`，不新增公共参数，不向 CLI 或 `linkmesh.in` 暴露。single-region polygon 输入规范化阈值必须与该锁定默认值同步；未来若 LinkMesh 显式改变 `build_mesh()` 的 `merge_thresh`，必须先修订蓝图并同步更新规范化阈值和测试。
- **outer boundary 形状**：当前 `nested_three_region` 为 LCFS 与第一壁联合包围盒加 `outer_padding` 的**矩形**；`single_region` 首批直接使用 LCFS/第一壁/`array_file` 边界本身。`outer_boundary` 字段只保存实际计算域边界几何，不决定形状生成策略。放大 LCFS、D 形、椭圆、自定义多边形或线圈/导体包络仍待 User 与导师确认；未来更换形状沿用同一 `(B,2)` 字段，Writer 契约不随形状变化。
- **退化检查**：无重复顶点、无越界索引、绝对面积 > `1e-12`。
- **边界编号（历史/过渡约定，不参与 TRIMEG 契约）**：`1=LCFS`、`2=first wall`、`3=outer boundary`、`0=内部`。TRIMEG 内外节点区分由三角形拓扑推导，不依赖此表。

---

## 5. TRIMEG HDF5 契约（完整 11 数据集，已实现并验收）

黄金标尺：`docs/trimeg/loadfemmesh_h5.m` 与两个真实样例。所有数据集位于 `/femmesh/`，磁盘 dtype **全部 float64**。

完整 11 数据集：`nvert ntria nvert_in nvert_ex vert idxivert idxevert tria nbcRZ Rbc Zbc`

| 路径 | 磁盘 shape | 说明 |
|---|---|---|
| `nvert` | `(1,1)` | 节点总数 N（整数语义） |
| `ntria` | `(1,1)` | 三角形总数 T |
| `nvert_in` | `(1,1)` | 内部节点数 |
| `nvert_ex` | `(1,1)` | 拓扑外边界节点数 |
| `vert` | `(N,2)` | 节点坐标，每行 `[R,Z]`，**不转置** |
| `tria` | `(T,3)` | 连接表，**1-based**，无第四列（`triangles+1`） |
| `idxivert` | `(1,nvert_in)` | 内部节点全局索引，1-based 升序（`{1..N}` 补集） |
| `idxevert` | `(1,nvert_ex)` | 拓扑外边界节点全局索引，1-based 升序 |
| `nbcRZ` | `(1,1)` | 有序外边界点数 B（整数语义） |
| `Rbc` | `(B,1)` | `mesh.outer_boundary[:,0]` |
| `Zbc` | `(B,1)` | `mesh.outer_boundary[:,1]` |

规则要点：

- Mesh2D 内部 0-based；文件连接表与 `idxivert/idxevert` 为 1-based。
- `region_ids` **不写入** TRIMEG HDF5。
- `idxevert` 定义为三角形无向边中只出现一次的边所含节点集合（拓扑外边界）；非流形边（同一无向边被 >2 三角形共享）在打开目标文件前拒绝；无任何拓扑外边界边时拒绝。
- `idxivert = {1..N} \ idxevert`；`nvert_in+nvert_ex=nvert`；两集合互斥且覆盖全部节点。
- `nbcRZ = len(outer_boundary)`；`Rbc = outer_boundary[:,0]`；`Zbc = outer_boundary[:,1]`。
- `Rbc/Zbc` 来自有序 `mesh.outer_boundary`；**禁止**用升序 `idxevert` 反推 `Rbc/Zbc`；`Rbc/Zbc` 不含生成器后插入的 Steiner 边界点。
- `nbcRZ` **不要求**等于 `nvert_ex`。
- TRIMEG target 下 `outer_boundary` 缺失（`None`）时，Writer 在打开输出文件前失败；Writer 不负责猜测 boundary source、不从 `idxevert` 恢复点序、不做边界重采样。
- Writer 全部输入验证（shape/有限性/整数语义/索引范围/重复顶点/面积/非流形/`outer_boundary` 合法性含自交）在打开目标文件前完成，且不修改输入 `Mesh2D`；Writer 复用 `mesh.py` 统一 `_validate_outer_boundary`（含完整非相邻边自交检查）作为二次防线，不复制自交算法。

**v2.5 最新真实 CLI 与消费端证据**：

| 真实链路 | 结果 |
|---|---|
| DIII-D `g192185.02440`；`target=trimeg`、`profile=nested_three_region`、`boundary_source=artificial_outer` | CLI 退出码 0；972 节点、1872 三角形、3 区域、902 内部节点、70 拓扑外边界节点、`outer_boundary` 70 点；成功生成 HDF5、PNG 与运行日志 |
| fixed-boundary `gNT_example`；`target=trimeg`、`profile=nested_three_region`、`boundary_source=artificial_outer` | CLI 退出码 0；3412 节点、6692 三角形、3 区域、3282 内部节点、130 拓扑外边界节点、`outer_boundary` 130 点；成功生成 HDF5、PNG 与运行日志 |
| DIII-D `g192185.02440`；`target=trimeg`、`profile=single_region`、`boundary_source=lcfs`、`plasma_dx=0.08 m` | CLI 退出码 0；344 节点、631 三角形、1 区域、289 内部节点、55 拓扑外边界节点、`outer_boundary` 55 点；成功生成 HDF5、PNG 与运行日志；LCFS 相邻近重复控制点导致的 OFT 回写失败不再阻塞真实链路 |

三份 LinkMesh HDF5 经 `h5ls` 确认均包含完整 11 个 `/femmesh` 数据集：
`nvert`、`ntria`、`nvert_in`、`nvert_ex`、`vert`、`tria`、`idxivert`、
`idxevert`、`nbcRZ`、`Rbc`、`Zbc`。实际布局继续遵守本节正式契约：
`vert=(N,2)`、`tria=(T,3)`、文件端节点索引 1-based、无第四列、不写
`region_ids`，`Rbc/Zbc` 来自 `Mesh2D.outer_boundary`，且不要求
`nbcRZ == nvert_ex`。

OFT 的 `Repeated points`、`Sliver` 与 `Small feature` 信息仍作为诊断 warning
保留；上述 nested 网格、HDF5 与 PNG 均已成功生成，不得把这些 warning 表述为
Triangle 失败。

**MATLAB 标准消费端 A/B 验收（PASSED）**：使用老师原始
`docs/trimeg/loadfemmesh_h5.m` 读取并绘制标准样例
`femmesh_65402_t1_nr16core.h5` 与 LinkMesh `single_region + lcfs` 生成的
`mesh.h5`。两者均成功读取并通过基础网格检查；标准样例约 981 节点、1847
三角形，LinkMesh 文件为 344 节点、631 三角形且 `nbcRZ=55`。两幅 MATLAB
图均表现为单一闭合计算域内部三角剖分，未发现节点索引错误、明显跨域错误连线或
读取布局错误；验证脚本只读、检查并绘图，未修改、删除或写回 HDF5。

该 A/B 证据确认 TRIMEG 接受“单一闭合计算域内部网格化”的静态网格，并确认当前
`single_region + lcfs` 与标准样例在拓扑形态上相容；它不证明 TRIMEG 永久固定使用
LCFS，也不固定 `Rbc/Zbc` 的物理来源。`Rbc/Zbc` 表示任务选定的有序计算域外边界。
因此，`single_region + first_wall` 仍是有价值的后续来源，但“必须先实现第一壁内部
全域网格”不再是启动 M4 的前置条件。

**两个参考样例直接证据（User 提供，紧凑归档）**：

| 样例 | Rbc/Zbc | nbcRZ | nvert_ex | 匹配 | 连续点对为拓扑边 | 方向/闭合 |
|---|---|---|---|---|---|---|
| `femmesh_65402_t1_nr16core.h5` | `(112,1)` | 112 | 113 | 112 点全部精确匹配最终 `vert`/`idxevert`（最大距离 0） | 111/112；唯一额外外边界节点位于最后一点→首点的闭合边上，为生成后插入的边界点 | 顺时针、单闭环、末尾不重复首点 |
| `femmesh_65402_t1_nr16nout4edge.h5` | `(175,1)` | 175 | 175 | 175 点全部精确匹配 | 175/175 均为实际拓扑边界边 | 顺时针、单闭环、末尾不重复首点 |

由此确认：`Rbc/Zbc` 是有序边界几何（非升序坐标集合）；`idxevert` 描述最终拓扑外边界节点；`Rbc/Zbc` 不含生成器后插入点；`nbcRZ` 可等于或小于 `nvert_ex`。两样例均未证明固定起点规则，不得写成事实。

**M3 complete-11 真实验收证据（已 PASSED，见 `History.md` 第 19 条）**：`71fe09f` 早期把人工矩形四控制角点错误作为 `outer_boundary`，此错误已修正为受控读取 `outer_region._resampled_points`（见第 3.2A 节）。两个真实 GFile 结果：DIII-D `g192185.02440` → 972 节点/1872 三角形/3 区域/内部 902/外边界 70/`outer_boundary` 70、`signed_area` 顺时针、所有 `Rbc/Zbc` 与最终 `vert` 最大匹配距离 0、h5py 11 数据集通过、MATLAB `loadfemmesh_h5.m` 成功读取重建且与 Python Plotter 图人工一致、无缺三字段 warning；fixed_boundary `gNT_example` → 3412 节点/6692 三角形/3 区域/内部 3282/外边界 130/`outer_boundary` 130、h5py 11 数据集与 shape/dtype/索引/计数检查通过。第一样例 `nbcRZ==nvert_ex==70`、第二样例二者均 130，均为样例实际结果，**不表示**格式要求二者恒等。当前默认 `nested_three_region + artificial_outer` 下 `Rbc/Zbc` 表示人工矩形最外计算域、第一壁为内部界面（MATLAB 红色矩形与固定策略一致，非读取错误）。M3 complete-11、M3 完整闭环均 **PASSED**。

---

## 6. CLI 契约

必进入同一 `cli.main()`：`python -m linkmesh [选项]` 与控制台命令 `linkmesh [选项]`（后者依赖计划中的 `pyproject.toml`）。

**现有已实现参数与配置原则**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--gfile PATH` | 必选（当前实现） | GFile/EQDSK 路径 |
| `--output PATH` | `mesh.h5` | TRIMEG HDF5 输出 |
| `--smb PATH` | `mesh.smb` | 未插入 MPI rank 的 PUMI SMB 基础路径；目标 PUMI 2.2.9 单进程实际生成 `<base>0.smb`，CLI 不插入 rank |
| `--plasma-dx FLOAT` | `0.08` | LCFS 内 plasma 区目标网格尺度（m） |
| `--vacuum-dx FLOAT` | `0.10` | LCFS 与第一壁间 vacuum 区目标网格尺度（m） |
| `--outer-dx FLOAT` | `0.15` | 第一壁与最外层边界间 outer 区目标网格尺度（m） |
| `--min-angle FLOAT` | `20.0` | 历史参数；非默认值直接报错拒绝 |
| `--max-area FLOAT` | `None` | 历史参数；给出即报错拒绝 |
| `--plot PATH` | `None` | 自检 PNG |
| `--no-smb` / `--no-hdf5` | `False` | 跳过对应输出 |
| `--verbose` | `False` | 详细日志 |

三个 `dx` 契约：`dx` 是传给 OFT 的**目标区域尺度**，非硬边长约束；使用物理区域名映射到 `define_region(name, dx, reg_type)`，不依赖 `region_ids` 数值顺序。验证规则：可解析浮点、有限、严格大于 0；`0`/负数/`nan`/`±inf` 必须在调用 OFT 前失败，错误含参数名与"必须是有限正数"；非数字文本由 argparse 拒绝；不静默恢复默认、不取绝对值、不裁剪、不换算单位。CLI 只解析/验证/转发，原样按关键字传给 `generate_mesh(gfile_data, plasma_dx=..., vacuum_dx=..., outer_dx=...)`。用户不提供时行为与默认完全兼容。

两层输入架构（`linkmesh.in` + CLI + `EffectiveConfig`）契约见第 6A 节。配置优先级为
“内建默认值 < `linkmesh.in` < 用户显式 CLI”。TOML `schema_version=1` 配置中的
相对路径相对配置文件目录解析；显式 CLI 相对路径相对当前工作目录解析；路径不展开
`~` 或环境变量。未显式指定配置文件且未使用 `--no-config` 时，只检查当前工作目录
中的标准配置文件，不递归父目录。

当前 M3DC1 单区域 Case 需要 `target=m3dc1`、`profile=single_region`、
`boundary_source=lcfs`、GFile 路径、TXT model 路径、未插入 rank 的 SMB 基础路径
与有限正数 `plasma_dx`；建议同时提供 PNG 路径用于人工检查。稳定 Case 参数写入
标准配置文件，显式 CLI 参数只用于临时覆盖网格尺度或输出路径。`outer_padding` 在
v3.1 仍**不暴露**为正式配置或 CLI 字段，保持内部默认策略。OFT `merge_thresh`
同样不暴露为 CLI 或配置字段，继续锁定使用 OFT 26.6 默认 `1e-4 m`。自适应细化和
全局 `--mesh-size` 未在源码暴露。M5 当前只开放既有字段表达的
`target=m3dc1 + profile=single_region + boundary_source=lcfs`，不新增 CLI 参数
或配置字段。

### 6.1 近期输入层优先级（v2.5 冻结）

1. 保持并维护已有真实运行证据的 `nested_three_region + artificial_outer`。
2. 保持并维护已通过真实 CLI 与 TRIMEG MATLAB 消费验收的
   `single_region + lcfs`。
3. `single_region + first_wall` 保留为有价值的后续边界来源，但不再阻塞 M4。
4. `single_region + array_file` 保留为后续轻量外部轮廓输入，当前不实施。
5. `single_region + flux_surface` 仍需真实磁面提取证据；禁止径向缩放 LCFS
   伪造磁面，当前不实施。
6. 不继续扩建大型 Fake OFT/Mock 测试体系。未来新增边界来源以少量关键单元测试，
   配合真实 GFile、OFT 26.6、CLI、PNG/HDF5 验收为主。

上述调整只冻结近期实施顺序，不删除未来 boundary source 的正式规划，也不表示
`first_wall`、`array_file` 或 `flux_surface` 已实现。

### 6.2 当前组内 Case 使用与部署原则（v3.3）

1. LinkMesh 尚未稳定，当前不进行需要 `sudo` 的服务器全局安装。
2. 一份 LinkMesh 源码可与 `100`、`200` 等 M3D-C1 Case 系列目录处于同一层级，
   不必复制到每个 Case。
3. 每个 Case 保存自己的标准配置文件、GFile、M3D-C1 输入与生成的 TXT、SMB、PNG
   网格产物。
4. `100`、`200` 等目录可代表完整 M3D-C1 源码版本；`101`、`102`、`201`、`202`
   等可复用对应源码版本并只修改输入。
5. 用户进入 Case 后，通过简短 CLI 指定该 Case 的配置文件；临时改变 `plasma_dx`
   或输出名时使用显式 CLI 参数覆盖。
6. 当前推荐先独立生成 TXT、SMB 和 PNG，人工检查 PNG 后再提交 M3D-C1 求解作业；
   不建议每次 `sbatch` 求解都无条件重新生成并覆盖网格。
7. 若登录节点不允许运行网格预处理，可提交独立轻量预处理作业，但仍与正式求解作业
   分离。
8. 只修改 M3D-C1 求解参数时可复用同一网格；修改 GFile、计算域策略或网格尺度时
   应重新生成。
9. 后续推荐无需 `sudo` 的 Conda 用户级安装，使 Python 包与
   `linkmesh-m3dc1-smb-helper` 一起进入个人环境；服务器全局安装待工具稳定后再评估。
10. 当前使用顺序是“生成 → PNG 人工检查 → 提交求解 → 消费端加载与初始化 →
    时间推进 → 稳定性与物理结果检查”；PNG 只做几何人工自检，不替代 M3D-C1
    加载、初始化、时间推进、稳定性或物理正确性验收。

### 6.3 下一阶段主线：EAST 时间推进验证

下一阶段主目标是使用老师提供的 EAST 样例边界，通过 LinkMesh 生成足够细密的
single-region 网格和配套 TXT+SMB，使其成功进入 M3D-C1 时间推进主循环，并记录
是否出现新的网格、几何分类、数值稳定性或运行时问题。

正式路线：

```text
老师提供的 EAST 边界与相关输入
  → 确认边界来源和文件契约
  → LinkMesh/OFT 生成细密二维三角网格
  → TXT + SMB + PNG
  → PNG 人工检查
  → M3D-C1 加载
  → M3D-C1 初始化
  → 时间推进主循环
  → 短时运行
  → 必要时中等时长运行
```

#### EAST 边界调查闸门

在实现任何新边界能力前，必须先由老师或物理人员确认 EAST 样例边界的真实类型：

1. 如果 EAST 边界就是 LCFS：
   - 直接复用现有 `single_region + lcfs`；
   - 不新增接口、字段或边界 Reader。
2. 如果 EAST 边界就是 GFile 第一壁：
   - 评估 `single_region + first_wall`；
   - 先确认 GFile limiter 点列与老师指定边界逐点语义一致；
   - 未确认前不得开放该业务路径。
3. 如果 EAST 边界是独立二维闭合轮廓：
   - 归入 `single_region + array_file`；
   - 先确认文件格式、R/Z 坐标、单位、闭合表示、方向和简单闭环几何；
   - 先更新本蓝图中的实现契约与验收证据，再编写业务代码。

不得仅根据“需要包含 X-point”推断必须使用多区域网格，也不得替 User 选择边界来源。
`single_region` 描述计算域区域数量，不等于 `boundary_source=lcfs`。一条包围 X-point
和目标研究结构的人工闭合边界仍可形成 single-region 网格，因此潜在扩展方向仍是
`single_region + first_wall` 或 `single_region + array_file`；当前唯一正式开放的
M3D-C1 路径仍为 `single_region + lcfs`。

#### X-point 与特殊磁拓扑的工程边界

本蓝图仅使用“**X-point 附近具有特殊或分形特征的磁拓扑结构**”描述当前研究背景，
不在本阶段定义“分形面”的严格数学或物理性质，也不推断其一定由 RMP、误差场或
其他特定机制产生。

LinkMesh 不计算、重建或分析该磁拓扑结构。LinkMesh 接收的是一条经物理人员确认的
二维闭合计算边界；该边界应将 X-point 及其附近目标研究结构包含在内部，但计算边界
与研究对象本身不是同一个对象。计算边界不一定是 LCFS、第一壁或普通闭合磁通面，
也可能是位于第一壁以内的人工闭合轮廓。LinkMesh 当前只处理二维 R-Z 极向截面，
不得把二维边界点列与完整三维磁拓扑混为一谈。

当前禁止：

- 根据 LCFS 做简单径向或中心缩放来伪造人工边界；
- 由 LinkMesh 自动推断特殊磁拓扑结构的外边界；
- 把 LinkMesh 扩展为磁拓扑分析程序；
- 在缺少可靠数据来源和算法时自动检查 X-point、LCFS、第一壁与计算边界的包含关系。

若第一版需要 `array_file`，边界点列必须由老师、物理人员或已有前处理程序提供并确认。
自动构造边界只有在数学算法、物理意义、输入证据和验收标准均明确后才能另行评估。

#### EAST 细密网格与时间推进验收

在同一条已确认 EAST 边界上比较多档 `plasma_dx`。`0.08 m`、`0.05 m`、
`0.03 m` 可作为初始候选值，但不是固定强制标准；最终取值必须依据 EAST 几何尺度、
老师意见和真实运行结果调整。

每组必须记录：

- 边界点数、节点数和三角形数；
- 实际 `plasma_dx` 与完整 LinkMesh 配置；
- TXT、rank-0 SMB 和 PNG；
- M3D-C1 加载结果与初始化结果；
- 是否进入时间推进主循环；
- 实际推进时间步数；
- 首次错误、异常退出或停止原因。

短时推进至少检查：

1. 已离开初始化阶段并执行若干时间步；
2. 无立即发生的网格、connectivity 或几何分类错误；
3. 无明显 NaN、Inf、段错误或 MPI 异常退出；
4. 日志能明确区分正常停止、求解器输入问题、网格问题和运行环境问题。

短时推进通过后再进行中等时长测试。每次运行必须保存网格配置、求解器输入、日志、
LinkMesh 版本、M3D-C1 源码版本和运行资源配置。时间推进不报错只能证明对应运行阶段
未立即失败，不能单独证明物理结果正确、科学结论有效或网格已经满足全部精度需求。

### 6.4 TCV/TRIMEG 并行真实场景路线

TCV 是装置名称。TCV/TRIMEG 是与 EAST/M3D-C1 并行的第二条真实场景验证路线，
当前状态为 **PENDING**。

边界调查需要比较：

- EQDSK LCFS；
- EQDSK 第一壁；
- 参考 HDF5 的 `Rbc/Zbc`；
- 参考网格最终拓扑外边界；
- 磁轴、X-point 与老师指定研究区域。

重点确认参考边界究竟是 LCFS、第一壁还是独立人工轮廓。如果参考边界不能由 GFile
直接表达，它可成为 `single_region + array_file` 的第二项直接需求证据，但在真实
样例和文件契约确认前仍不得把该路径标记为已实现。

TRIMEG 真实消费验收路线为：

```text
LinkMesh HDF5
  → 官方 MATLAB 读取脚本
  → TRIMEG 实际读取和运行
```

截图、PNG 或 MATLAB 绘图只能作为几何辅助证据，不得单独宣布 TCV/TRIMEG 实际消费
已经通过。

### 6.5 OFT/Triangle 真实场景评估顺序

当前使用 EAST 和 TCV 真实场景判断 OFT/Triangle 是否足够满足 P0，评估顺序固定为：

1. 几何层：边界贴合、覆盖、孔洞、越界和 X-point 包含关系；
2. 网格层：节点数、三角形数、面积、最小角、长宽比和边长分布；
3. 消费端层：
   - M3D-C1 加载、初始化和时间推进；
   - TRIMEG MATLAB 读取与实际运行。

在真实场景证明全局 `dx` 不足之前，暂不开发 Triangle refinement 新路径、X-point
局部加密、区域差异化密度、磁面对齐节点或自适应动态网格。若真实消费端暴露问题，
先记录输入、网格、分类、日志和失败阶段，再判断是否需要最小修正；不得预先扩建
通用网格平台。

---

## 6A. 输入架构（两层输入 + EffectiveConfig，字段级契约）

以下为 User 已批准的字段级正式契约。保持轻量边界：不得建设通用配置 DSL、任意 N 区域语言或插件系统。

**标准 `linkmesh.in` 示例状态（v3.3）**：两层输入架构、TOML
`schema_version=1`、`EffectiveConfig`、优先级“内建默认值 < `linkmesh.in` <
用户显式 CLI”、未知键严格报错、`--config/--no-config` 互斥及
`target/profile/boundary_source` 兼容矩阵均保持正式有效。仓库已存在
`examples/m3dc1_single_region/linkmesh.in.example`，用于展示当前唯一开放的
`m3dc1 + single_region + lcfs` 配置。该示例不开放 `first_wall`、`array_file`、
多区域或其他 M3D-C1 组合，也不替代每个 Case 对实际 GFile、输出路径和网格尺度的
明确配置。

### 6A.1 模块落点

- `src/linkmesh/config.py`：`EffectiveConfig` 定义 + `linkmesh.in` 读取/校验/合并 + 兼容矩阵/required fields 校验（职责与禁止见第 2 节表）。
- `src/linkmesh/readers/boundary_reader.py`：`array_file` 两列 CSV → `(B,2) float64`（职责与禁止见第 2 节表）。
- `readers/gfile_reader.py`、`mesher/oft_adapter.py`、`cli.py`、`mesh.py`、
  各 Writer 与 Plotter：继续遵守第 2 节定义的现有职责边界；输入层不得把配置解析、
  边界来源选择或路径合并逻辑下沉到这些业务模块。
- 不新增 `inputs/` 包、source 抽象基类、注册表、插件系统或任意 N 区域配置语言。

### 6A.2 `EffectiveConfig`

`EffectiveConfig` 已在 `src/linkmesh/config.py` 中实现为
`@dataclass(frozen=True)`。它是内建默认值、配置文件和用户显式 CLI 覆盖完成合并、
类型校验、路径解析、兼容矩阵校验及 required fields 校验后的唯一正式配置对象。

正式字段共 15 个：

| 字段 | 类型 | 正式含义 |
|---|---|---|
| `schema_version` | `int` | 配置 schema 版本；v1 固定为 `1` |
| `config_path` | `Optional[Path]` | 实际加载的配置文件绝对路径；未加载时为 `None` |
| `target` | `Literal["mesh_only","trimeg","m3dc1"]` | 当前目标输出族 |
| `profile` | `Literal["single_region","nested_three_region"]` | 区域构造策略 |
| `boundary_source` | `Literal["lcfs","first_wall","array_file","artificial_outer","flux_surface"]` | 计算域外边界来源 |
| `gfile_path` | `Optional[Path]` | GFile/EQDSK 绝对路径 |
| `array_file_path` | `Optional[Path]` | 两列 CSV 边界文件绝对路径 |
| `plasma_dx` | `float` | plasma 或 single-region 目标网格尺度 [m] |
| `vacuum_dx` | `float` | vacuum 区目标网格尺度 [m] |
| `outer_dx` | `float` | outer 区目标网格尺度 [m] |
| `hdf5_path` | `Optional[Path]` | TRIMEG HDF5 输出绝对路径 |
| `plot_path` | `Optional[Path]` | PNG 输出绝对路径 |
| `model_path` | `Optional[Path]` | M3D-C1 analytic model TXT 输出绝对路径 |
| `smb_path` | `Optional[Path]` | 未插入 MPI rank 的 SMB 基础输出绝对路径 |
| `verbose` | `bool` | 是否输出详细日志 |

约束：

1. 所有非 `None` 的 `Path` 在 `EffectiveConfig` 构造前规范化为绝对路径。
2. 配置文件相对路径相对配置文件所在目录解析；显式 CLI 相对路径相对进程当前工作
   目录解析；内建默认输出路径相对当前工作目录解析。
3. 路径不展开 `~`，不展开环境变量，不因输出路径尚不存在而创建目录。
4. `EffectiveConfig` 不保存值来源字典、NumPy 数组、`Mesh2D`、`GFileData`、
   PUMI 句柄、Writer、argparse Namespace 或可变业务状态。
5. `schema_version` 不是 CLI 可覆盖字段。
6. `EffectiveConfig` 只表达配置事实，不读取 GFile、array CSV 或任何输出文件。
7. 当前已实现的 M3DC1 组合只有
   `target=m3dc1 + profile=single_region + boundary_source=lcfs`；不得因字段存在而
   推断其他组合已经实现。

### 6A.3 内建默认值

内建默认值的唯一实现来源是 `src/linkmesh/config.py`，CLI 不得维护第二套默认值。

| 字段 | 内建默认值 |
|---|---|
| `schema_version` | `1` |
| `target` | `"trimeg"` |
| `profile` | `"nested_three_region"` |
| `boundary_source` | `"artificial_outer"` |
| `plasma_dx` | `0.08` m |
| `vacuum_dx` | `0.10` m |
| `outer_dx` | `0.15` m |
| `verbose` | `False` |
| `hdf5_path` | target 为 `trimeg` 时使用当前工作目录下的 `mesh.h5` |
| `plot_path` | `None` |
| `model_path` | `None` |
| `smb_path` | `None` |
| `gfile_path` | `None` |
| `array_file_path` | `None` |

规则：

- 无配置文件且无新增显式 CLI 参数时，默认行为保持
  `trimeg + nested_three_region + artificial_outer`。
- `model_path` 与 `smb_path` 不制造隐式可执行默认路径；当前 M3DC1 CLI 必须由配置
  文件或显式 CLI 提供二者。
- `hdf5_path` 的 `mesh.h5` 默认只在 `target=trimeg` 时建立；其他 target 不产生
  无意义的 HDF5 默认输出。
- `outer_padding` 与 OFT `merge_thresh` 不是 `EffectiveConfig` 字段，当前不得通过
  CLI 或 `linkmesh.in` 暴露。
- `--min-angle` 与 `--max-area` 是 CLI 历史兼容参数，不进入
  `EffectiveConfig`；非默认使用由 CLI 在配置加载及 OFT 调用前拒绝。

### 6A.4 `linkmesh.in` v1 TOML schema

标准配置文件采用 Python 标准库 `tomllib` 可读取的 TOML，顶层必须包含：

```toml
schema_version = 1
```

v1 只允许以下 section 和键：

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
  plasma_dx
  vacuum_dx
  outer_dx

[output]
  hdf5
  plot
  model
  smb

[runtime]
  verbose
```

字段契约：

| TOML 键 | 类型 | 映射字段 |
|---|---|---|
| `schema_version` | 整数，且必须等于 `1` | `schema_version` |
| `[task].target` | 字符串枚举 | `target` |
| `[input].gfile` | 非空字符串路径 | `gfile_path` |
| `[input].array_file` | 非空字符串路径 | `array_file_path` |
| `[domain].profile` | 字符串枚举 | `profile` |
| `[domain].boundary_source` | 字符串枚举 | `boundary_source` |
| `[mesh].plasma_dx` | 有限正数 | `plasma_dx` |
| `[mesh].vacuum_dx` | 有限正数 | `vacuum_dx` |
| `[mesh].outer_dx` | 有限正数 | `outer_dx` |
| `[output].hdf5` | 非空字符串路径 | `hdf5_path` |
| `[output].plot` | 非空字符串路径 | `plot_path` |
| `[output].model` | 非空字符串路径 | `model_path` |
| `[output].smb` | 非空字符串路径 | `smb_path` |
| `[runtime].verbose` | TOML 布尔值 | `verbose` |

严格校验规则：

1. `schema_version` 必须存在，必须是非布尔整数，且必须等于 `1`。
2. 未列出的顶层键、section 或 section 内键立即报 `ConfigError`。
3. section 必须是 TOML table；不得用标量冒充 section。
4. 路径必须是非空字符串；v1 不接受 TOML 数组、Path 对象或环境变量表达式。
5. `dx` 接受 TOML 整数或浮点数，但拒绝布尔值、NaN、Inf、零和负数。
6. `verbose` 必须是 TOML 布尔值，不接受字符串 `"true"` 或整数 `1`。
7. TOML 语法错误、读取错误和 schema 错误必须包含配置文件路径及字段位置。
8. 配置 Reader 不读取路径指向的业务文件内容，不创建输出目录。
9. 仓库已提供 `examples/m3dc1_single_region/linkmesh.in.example`，其内容必须遵守
   本节 v1 schema；示例存在不表示其中未出现的 boundary source 或 target 组合已实现。

### 6A.5 CLI 正式参数

输入层正式参数及其合并语义如下：

| CLI 参数 | argparse 目标 | 语义 |
|---|---|---|
| `--config PATH` | `config` | 只加载指定配置文件；不存在立即失败 |
| `--no-config` | `no_config` | 禁止当前目录自动发现配置文件 |
| `--target VALUE` | `target` | 覆盖 `[task].target` |
| `--profile VALUE` | `profile` | 覆盖 `[domain].profile` |
| `--boundary-source VALUE` | `boundary_source` | 覆盖 `[domain].boundary_source` |
| `--gfile PATH` | `gfile` | 覆盖 `[input].gfile` |
| `--array-file PATH` | `array_file` | 覆盖 `[input].array_file` |
| `--plasma-dx FLOAT` | `plasma_dx` | 覆盖 `[mesh].plasma_dx` |
| `--vacuum-dx FLOAT` | `vacuum_dx` | 覆盖 `[mesh].vacuum_dx` |
| `--outer-dx FLOAT` | `outer_dx` | 覆盖 `[mesh].outer_dx` |
| `--output PATH` | `hdf5` | 覆盖 `[output].hdf5` |
| `--plot PATH` | `plot` | 覆盖 `[output].plot` |
| `--model PATH` | `model` | 覆盖 `[output].model` |
| `--smb PATH` | `smb` | 覆盖 `[output].smb`；仍表示未插入 rank 的基础路径 |
| `--verbose` | `verbose` | 显式 `True` 时覆盖 `[runtime].verbose` |

规则：

1. `--config` 与 `--no-config` 互斥。
2. 参与三层合并的可选参数使用 `UNSET` 区分“用户未提供”和“用户显式提供”；
   argparse 默认值不得覆盖 TOML。
3. `--verbose` 为 `store_true`；只有显式出现时才以 `True` 覆盖 TOML，未出现时保持
   `UNSET` 语义。
4. `--no-hdf5` 与 `--no-smb` 是执行期开关，不进入 `EffectiveConfig`，也不取消
   target 对 required output path 的配置校验。
5. `--min-angle` 默认 `20.0`，非默认值在任何配置或网格生成前拒绝；
   `--max-area` 默认 `None`，一旦提供即拒绝。二者不映射为 OFT `dx`。
6. CLI 只收集显式输入并编排业务模块；类型、有限正数、枚举、兼容矩阵和路径合并的
   最终校验集中在 `config.py`。
7. `--smb` 不由 CLI 改写为 rank-0 文件名。`<base>0.smb` 的定位由
   `smb_writer.py` 与目标 PUMI 版本规则负责。
8. CLI 不解析 `LINKMESH_M3DC1_SMB_HELPER`，不猜测 helper 构建目录，不硬编码
   PUMI 安装路径。

### 6A.6 配置发现与合并算法

配置发现顺序固定为：

1. 同时提供 `--config` 与 `--no-config`：立即失败。
2. 提供 `--config PATH`：只解析该路径；相对路径相对进程当前工作目录解析；
   文件不存在或不是普通文件立即失败，不再自动发现。
3. 提供 `--no-config`：不加载任何配置文件。
4. 二者均未提供：只检查当前工作目录下的 `linkmesh.in`。
5. 不递归父目录，不搜索用户主目录，不搜索仓库根目录，不读取环境变量指定的配置。

合并优先级固定为：

```text
内建默认值 < linkmesh.in < 用户显式 CLI
```

合并算法：

1. 发现配置文件并解析、严格校验 TOML。
2. 以当前工作目录为 CLI 路径基准，以配置文件所在目录为 TOML 路径基准。
3. 标量字段先取显式 CLI；否则取 TOML；否则取内建默认值。
4. 路径字段分别按 CLI 短键名与 TOML/`EffectiveConfig` 长字段名映射：
   `gfile→gfile_path`、`array_file→array_file_path`、`hdf5→hdf5_path`、
   `plot→plot_path`、`model→model_path`、`smb→smb_path`。
5. 路径使用 `Path.resolve(strict=False)` 等价语义规范化为绝对路径；不要求输出
   已存在，不创建目录，不展开 `~` 或环境变量。
6. 合并后再次校验枚举、数值和布尔类型，覆盖 CLI 直接构造输入的情况。
7. 构造冻结的 `EffectiveConfig`。
8. 依次执行兼容矩阵、required fields 和当前实现阶段闸门校验。
9. 只有全部校验通过后才进入 Reader、OFT、Writer 或 Plotter。
10. 未实现组合必须明确失败，不得回退到
    `nested_three_region + artificial_outer`。

路径存在性边界：

- `--config` 指定的配置文件在发现阶段必须存在。
- GFile、array file 的业务输入存在性或内容有效性由对应 Reader/业务阶段报告；
  `config.py` 不读取其内容。
- 输出父目录不会由配置层创建；具体 Writer 按自身契约检查。
- helper 路径不属于 `EffectiveConfig`，继续由 SMB Writer 的显式参数、环境变量和
  `PATH` 优先级管理。

### 6A.7 `array_file` v1 契约

`boundary_source=array_file` 的正式输入格式为轻量两列 CSV，但该来源当前仍为
**接口预留 / PLANNED / NOT IMPLEMENTED**，不得因配置枚举、字段级契约或 EAST/TCV
候选需求而标记为已实现。其下一步候选用途是接收经老师或物理人员确认的独立二维闭合
计算边界，服务 EAST、TCV 或其他不能由 LCFS 直接表达的真实场景；是否成为下一项
正式实现必须由真实样例和文件契约调查结果裁决。

文件契约：

| 项目 | 规定 |
|---|---|
| 编码 | UTF-8 文本 |
| 数据列 | 恰好两列，依次为 `R,Z` |
| 单位 | m |
| 数值类型 | 可解析为有限 `float64` |
| header | v1 不允许 header |
| 注释 | v1 不定义注释语法 |
| 空行 | 可忽略纯空白行；数据行不得为空字段 |
| 分隔符 | 逗号 |
| shape | 读取后 `(B,2)` |
| 最低点数 | 至少 3 个有效点 |
| 闭合 | 末尾不得重复首点；最后一点到第一点隐式闭合 |
| 方向 | 输入可为任一方向；进入 `Mesh2D.outer_boundary` 前规范化为顺时针并保持起点 |
| 几何 | 单一简单闭环；禁止相邻重复、退化面积、非相邻边交叉、端点接触或共线重叠 |

`boundary_reader.py` 的计划职责：

1. 只读取 CSV 语法并转换为 `(B,2) float64`。
2. 报告文件不存在、无法读取、列数错误、空字段、非数字、NaN/Inf 和点数不足。
3. 创建独立数组，不返回对解析缓冲区的共享可变视图。
4. 复用 `mesh.py` 的统一边界验证入口完成简单闭环几何验证，不复制自交算法。
5. 不创建 `Mesh2D`，不调用 OFT，不读取 GFile，不使用 pandas。
6. 不自动闭合、不自行重采样、不平滑、不排序、不投影、不按最近距离修补。
7. 不从文件名或坐标范围推断物理区域语义。

实施前停止条件：

- 需要改变两列 `R,Z`、单位 m、隐式闭合或单一简单闭环契约；
- 需要引入多轮廓、孔洞、区域种子、任意 N 区域语言或 pandas；
- 需要修改 `Mesh2D` 字段才能表示首版输入；
- array boundary 与 GFile 同时存在时的业务语义无法按第 6A.10 节无歧义拒绝。

### 6A.8 boundary source 正式契约

| `boundary_source` | 正式来源 | 当前实现状态 | P0 规则 |
|---|---|---|---|
| `lcfs` | `GFileData.lcfs_r/lcfs_z` | **已实现并通过真实 CLI** | single-region 唯一计算域边界；不使用第一壁、不创建人工外框、不缩放 LCFS |
| `first_wall` | `GFileData.wall_r/wall_z` | **PLANNED / NOT IMPLEMENTED** | 需要有效第一壁；首版用于 single-region；缺壁必须失败 |
| `array_file` | 经物理人员确认的 v1 两列 CSV 独立二维闭合边界 | **接口预留 / PLANNED / NOT IMPLEMENTED** | 首版用于 single-region；与 GFile 输入互斥；候选服务 EAST/TCV 等不能由 LCFS 直接表达的场景 |
| `artificial_outer` | LCFS/第一壁联合包围盒加内部固定 padding 的人工矩形 | **已实现并通过真实 CLI** | 当前只配 `nested_three_region`；四个控制角点不得直接作为 `outer_boundary` |
| `flux_surface` | 从平衡数据提取的真实磁通面 | **NOT IMPLEMENTED** | 禁止径向缩放 LCFS 伪造磁面；真实轮廓提取契约确认前不得实现 |

共同规则：

1. `boundary_source` 选择的是计算域最外边界来源，不等同于 OFT region ID。
2. 每次任务只允许一个正式计算域外边界来源。
3. `lcfs`、`first_wall` 和 `artificial_outer` 需要 GFile。
4. `array_file` 需要 `array_file_path`，并禁止同时提供 `gfile_path`。
5. `flux_surface` 在真实提取输入、参数和验收依据未定义前明确报未实现。
6. 已实现来源最终都必须通过策略层捕获 Region、OFT build 后回写点列及
   `Mesh2D.outer_boundary` 统一验证链。
7. 未实现来源不得静默回退到 LCFS、第一壁或人工外框。
8. `first_wall` 和 `array_file` 的字段与契约存在不表示对应 Reader、OFT 策略层或
   CLI 业务路径已实现。

### 6A.9 target/profile/boundary_source 兼容矩阵

当前正式矩阵：

| target | profile | boundary_source | 契约状态 |
|---|---|---|---|
| `mesh_only` | `nested_three_region` | `artificial_outer` | 已实现 |
| `trimeg` | `nested_three_region` | `artificial_outer` | 已实现并验收 |
| `mesh_only` | `single_region` | `lcfs` | 已实现 |
| `trimeg` | `single_region` | `lcfs` | 已实现并通过真实 CLI/MATLAB 消费验收 |
| `m3dc1` | `single_region` | `lcfs` | 已实现；真实 CLI、TXT+SMB 加载与 M3D-C1 初始化 PASSED；时间推进 PENDING |
| `mesh_only` / `trimeg` | `single_region` | `first_wall` | 规划有效，但当前未实现 |
| `mesh_only` / `trimeg` | `single_region` | `array_file` | 规划有效，但当前未实现 |
| 任意 | `single_region` | `flux_surface` | 未实现 |
| `m3dc1` | `single_region` | `first_wall` / `array_file` / `flux_surface` | 当前未开放 |
| `m3dc1` | `nested_three_region` | 任意 | 禁止 |
| 任意 | `nested_three_region` | `lcfs` / `first_wall` / `array_file` | profile/source 不匹配，禁止 |
| 任意 | `single_region` | `artificial_outer` | profile/source 不匹配，禁止 |

裁决规则：

1. 禁止组合使用 `ConfigError` 拒绝。
2. 在架构上可表达但当前阶段尚未实现的组合使用 `NotImplementedError` 明确拒绝。
3. 当前实际异常边界以 `config.py` 的兼容矩阵与阶段闸门为准；旧测试若期待不同异常
   类型，应更新测试预期，不得为满足旧预期放行未实现组合。
4. `target=trimeg` 只进入 HDF5 Writer，不调用 SMB Writer。
5. `target=m3dc1` 只在当前唯一开放组合中进入共享 ModelSpec 的 TXT/SMB Writers。
6. `target=mesh_only` 不进入 HDF5、TXT 或 SMB Writer；配置了 `plot_path` 时仍可绘图。
7. 新增矩阵组合必须先更新本蓝图并取得 User 确认，不得只修改 argparse choices 或
   删除阶段闸门。

### 6A.10 required fields

required fields 在路径合并完成后、业务执行前校验。

按 boundary source：

| boundary_source | 必需字段 | 禁止同时提供 |
|---|---|---|
| `lcfs` | `gfile_path` | `array_file_path` |
| `first_wall` | `gfile_path` | `array_file_path` |
| `artificial_outer` | `gfile_path` | `array_file_path` |
| `array_file` | `array_file_path` | `gfile_path` |
| `flux_surface` | 当前未定义完整 required fields；阶段闸门直接报未实现 | 不得猜测 |

按 target：

| target | 必需输出字段 | Writer 行为 |
|---|---|---|
| `mesh_only` | 无 | 不写 HDF5、TXT 或 SMB |
| `trimeg` | `hdf5_path` | 未使用 `--no-hdf5` 时写 HDF5 |
| `m3dc1` | `model_path`、`smb_path` | 总是写 TXT；未使用 `--no-smb` 时写 SMB |

补充规则：

1. 当前所有已实现业务路径均由 GFile Reader 进入，因此 `lcfs` 与
   `artificial_outer` 必须有 `gfile_path`。
2. `first_wall` 即使字段齐全，仍必须由未来输入层检查 GFile 是否实际包含至少三个
   有效壁点；该来源当前未实现。
3. `array_file` 即使字段齐全，仍须由未来 `boundary_reader.py` 验证文件内容；
   该来源当前未实现。
4. `target=m3dc1` 的 `smb_path` 是未插入 rank 的基础路径。
5. `--no-smb` 不使 `smb_path` 在配置层变为可选；该开关只控制执行期跳过 helper。
6. `--no-hdf5` 不改变 `target=trimeg` 的有效配置结构。
7. `plot_path` 对所有 target 均为可选。
8. 配置层只校验字段存在与组合关系，不读取 GFile、CSV、HDF5、TXT 或 SMB 内容。
9. required fields 通过不等于对应组合已经实现；之后仍须通过当前阶段闸门。

### 6A.11 `single_region` 构造契约

`single_region` 表示由一条外边界围成、只生成一个 OFT 区域的二维计算域。它不是
“从多区域结果中筛选某个 region”，也不创建真空 annulus 或人工 outer region。

#### `single_region + lcfs`（已实现并验收）

正式构造：

1. 从 `GFileData.lcfs_r/lcfs_z` 取得 LCFS。
2. 执行基础 shape、长度、有限性、最低点数和普通显式闭合末点处理。
3. 在调用 OFT `add_polygon()` 前，按锁定的 OFT 26.6 默认
   `merge_thresh=1e-4 m` 稳定过滤相邻近重复控制点：
   - 保留第一个点；
   - 按原顺序遍历候选点；
   - 候选点与最后一个已接受点的欧氏距离严格小于 `1e-4 m` 时删除候选点；
   - 否则保留候选点；
   - 不排序、不循环移位、不插值、不重采样、不全局去重、不修改保留坐标。
4. 过滤后必须至少有 3 点。
5. 过滤后首末点距离若仍小于 `1e-4 m`，明确失败，不继续静默删除。
6. 定义唯一 OFT region，类型沿当前实现为 `plasma`，网格尺度使用
   `plasma_dx`。
7. 调用一次 `add_polygon(lcfs, "plasma")`，不提供 parent region。
8. 不读取或使用第一壁，不定义 vacuum，不创建 artificial outer，不创建 annulus。
9. 在 `add_polygon()` 前后通过 `domain.regions` 长度差异捕获唯一新增 Region 引用。
10. `mesh_from_oft_domain()` 在 `build_mesh()` 前保存该引用，在 build 后读取同一对象
    的 `_resampled_points`。
11. 按第 3.2A 节规范化并验证 `outer_boundary`，再构造 `Mesh2D`。
12. `vacuum_dx`、`outer_dx` 和 `outer_padding` 不参与该分支；保留前两字段只为统一
    配置对象与调用签名，不得把它们合并为新的通用 `mesh_size`。
13. 不径向缩放 LCFS，不从最终 `pts/lc`、`idxevert` 或原始控制点直接构造
    `outer_boundary`。

该路径已在真实 DIII-D GFile 上生成 344 节点、631 三角形、1 区域和 55 点
`outer_boundary`，并通过 TRIMEG 与 M3DC1 第一条 CLI 的现有验收。该结果不开放其他
single-region boundary source。

#### `single_region + first_wall`（规划有效，当前未实现）

正式规划：

1. 从 `GFileData.wall_r/wall_z` 取得有效第一壁。
2. 第一壁作为唯一计算域边界和唯一 Region polygon。
3. 网格尺度首版使用 `plasma_dx`，不增加新的公共 `mesh_size` 字段。
4. 不创建 LCFS 内部界面、vacuum annulus 或 artificial outer。
5. 缺壁、R/Z 不同时存在、点数不足、非有限、退化或非简单闭环时失败。
6. 仍须走 OFT Region 捕获、build 后回写和统一 `outer_boundary` 验证链。
7. 该路径当前不得标记为已实现或由 CLI 放行。

#### `single_region + array_file`（接口预留 / 规划有效，业务未实现）

正式规划：

1. 由第 6A.7 节的两列 CSV 提供经老师或物理人员确认的唯一二维闭合计算边界。
2. 不同时读取 GFile，不从文件名推断物理语义，也不由 LinkMesh 自动推断 X-point
   附近特殊磁拓扑结构的边界。
3. 网格尺度首版使用 `plasma_dx`。
4. 由 OFT `add_polygon()` 创建唯一 Region。
5. 仍须捕获该 Region，并以 build 后 `_resampled_points` 作为最终
   `Mesh2D.outer_boundary` 来源。
6. 候选用途包括 EAST、TCV 或其他不能由 LCFS 直接表达的 single-region 场景；
   是否实施必须由真实样例证明需求，并在实现前确认文件、坐标、单位、闭合、方向和
   简单闭环契约。
7. X-point、LCFS 与第一壁的包含关系检查，只有在可靠数据来源、算法和验收标准确认
   后才能成为正式实现要求。
8. 该路径当前不得标记为已实现或由 CLI 放行。

#### `single_region + flux_surface`（当前未实现）

必须先确认真实磁通面提取所需的平衡字段、用户输入参数、轮廓选择规则和真实验收依据。
禁止通过 LCFS 坐标径向缩放、中心缩放或任意几何插值伪造磁通面。

共同停止条件：

- 必须复制 OFT 重采样、点合并、segment 拼接、种子搜索或 Triangle 算法；
- 无法可靠捕获唯一 outer Region；
- 必须从最终拓扑或最近距离猜测有序边界；
- 需要放宽 `Mesh2D.outer_boundary` 的简单闭环契约；
- 需要新增多轮廓、孔洞、任意 N 区域配置或第二网格引擎；
- 需要改变当前正式字段、索引、单位或 Writer 契约但蓝图尚未更新。

### 6A.12 输入层实施拆分

输入层按小步闭环维护，不把所有 boundary source 一次性实现：

| 阶段 | 内容 | 当前状态 |
|---|---|---|
| 输入层 I | `EffectiveConfig`、严格 TOML v1、配置发现、默认/TOML/CLI 合并、兼容矩阵、required fields、CLI 新参数 | **IMPLEMENTED** |
| 输入层 II | `single_region + lcfs` OFT 策略、相邻近重复控制点规范化、真实 GFile/CLI/TRIMEG 验收 | **PASSED** |
| 输入层 III | `single_region + first_wall` | **PLANNED / NOT IMPLEMENTED** |
| 输入层 IV | `boundary_reader.py` 与 `single_region + array_file` | **接口预留 / PLANNED / NOT IMPLEMENTED；等待 EAST/TCV 真实边界证据** |
| 输入层 V | 真实 `flux_surface` 提取与 single-region 构造 | **NOT IMPLEMENTED；需求与证据待确认** |
| M5 第一条 | `m3dc1 + single_region + lcfs` 的 TXT+SMB+PNG CLI 编排 | **PASSED；加载与初始化 PASSED，时间推进 PENDING** |

实施纪律：

1. 每一阶段先更新蓝图，再修改对应最小源码和测试。
2. 新来源以少量关键单元测试加真实 OFT 26.6/GFile/CLI/PNG/HDF5 验收为主，
   不扩建大型 Fake OFT 体系。
3. 输入层 III–V 不阻塞已通过的 M4 生成侧和 M5 第一条 CLI。
4. 不因未来来源规划改变当前默认
   `nested_three_region + artificial_outer`。
5. 维护现有 `examples/m3dc1_single_region/linkmesh.in.example` 与当前唯一开放组合
   一致；不得用该示例提前开放 `first_wall`、`array_file` 或其他 M3D-C1 组合。
6. 不提前建设 boundary source plugin、抽象基类、注册表或通用区域 DSL。
7. 未实现阶段必须在配置阶段明确拒绝，不进入 Reader 或 OFT 后再隐式回退。

### 6A.13 输入层验收矩阵

#### 配置与发现

- `schema_version=1` 可读取；缺失、类型错误、其他版本均失败。
- 未知顶层键、未知 section、未知 section 键均失败。
- TOML 类型错误、非法枚举、非有限或非正 `dx`、非布尔 `verbose` 均失败。
- `--config` 与 `--no-config` 互斥。
- 显式 `--config` 不存在时立即失败，不再自动发现。
- `--no-config` 禁止自动发现。
- 默认只发现当前工作目录下的 `linkmesh.in`，不递归父目录。
- 优先级严格为“默认 < TOML < 显式 CLI”。
- TOML 相对路径相对配置目录；CLI 相对路径相对当前工作目录。
- 路径不展开 `~` 或环境变量。
- `EffectiveConfig` 冻结，字段精确为第 6A.2 节定义的 15 项。

#### 兼容矩阵与 required fields

- 已实现组合可通过配置层。
- 禁止组合以 `ConfigError` 拒绝。
- 规划有效但当前未实现组合以 `NotImplementedError` 拒绝。
- `lcfs`、`first_wall`、`artificial_outer` 要求 GFile，并拒绝 array file。
- `array_file` 要求 array file，并拒绝 GFile。
- `trimeg` 要求 HDF5 输出路径。
- `m3dc1` 要求 TXT model 与 SMB 基础路径。
- `m3dc1 + nested_three_region` 始终禁止。
- 当前只放行 `m3dc1 + single_region + lcfs`。
- `mesh_only` 不调用 Writer；`trimeg` 不调用 SMB Writer。
- `--no-smb`、`--no-hdf5` 只控制执行，不改变有效配置 required fields。

#### `single_region + lcfs`

- LCFS 是唯一 polygon 和唯一计算域边界。
- 只创建一个 OFT region，不创建 first-wall interface、vacuum、annulus 或人工外框。
- 网格尺度使用 `plasma_dx`。
- 相邻距离 `<1e-4 m` 的控制点按稳定顺序过滤后一点。
- 过滤不排序、不重采样、不全局去重、不改变保留坐标。
- 过滤后不足 3 点或首末仍近重复时失败。
- build 后读取已捕获 Region 的 `_resampled_points`，不得读取禁止的 Mesh 私有结构。
- `Mesh2D.outer_boundary` 是独立 float64、顺时针、隐式闭合、单一简单闭环。
- OFT 输出为单一区域，`region_ids` 原样保留。
- 真实 DIII-D GFile、TRIMEG HDF5、MATLAB A/B 与 M3DC1 第一条 CLI 的既有通过结论
  保持不变。

#### `array_file` 和 `first_wall`

- `array_file` 两列、有限 float64、至少 3 点、无 header、单位 m、单一简单闭环。
- CSV 语法错误、列数错误、空字段、非数字和 NaN/Inf 必须失败。
- `first_wall` 缺失或无效必须失败，不得回退 LCFS。
- 两个来源均不得创建人工 outer 或多区域 annulus。
- 两个来源当前均为 **NOT IMPLEMENTED**；契约测试和字段存在不得写成业务路径已通过。

#### target 编排与回归

- 默认 `trimeg + nested_three_region + artificial_outer` 行为保持。
- `trimeg + single_region + lcfs` 保持 HDF5 与可选 PNG 行为。
- `m3dc1 + single_region + lcfs` 只构造一次 `M3DC1ModelSpec`，TXT/SMB Writers
  共享同一对象。
- SMB 基础路径不由 CLI 插入 rank。
- helper 定位仍由 SMB Writer 管理。
- PNG 不替代 M3D-C1 加载、初始化、时间推进、稳定性或物理正确性验收。
- M4 生成侧、M5 第一条真实 CLI、TXT+SMB 加载、M3D-C1 初始化、helper 生命周期与
  部署原则不得因输入层契约维护而降级或回退。
- 时间推进主循环、中等或长时稳定性与物理结果正确性必须继续保持 PENDING，直到取得
  对应直接运行证据。
- 当前已记录的两项旧测试预期债务不得误写为全部自动测试通过。

---

本蓝图在 `d947b04dd5243cd69a28ddd133d33cc76f640b37` 事故后形成的 M4、M5、CLI、
helper、部署和验收更新，已在前述第 1、2、6 节及本节当前状态表中保留。事故前第 7
至第 10 节涉及的 M4 规划、里程碑、测试门槛、实施纪律和待决事项，已由当前蓝图前述
章节中的较新正式内容覆盖；为避免恢复过期状态和形成大段语义重复，本次不机械追加
这些旧章节。

当前准确结论为：M1–M3 与既有 TRIMEG 消费验收已通过；M4 LinkMesh 生成侧已通过；
M5 第一条 `m3dc1 + single_region + lcfs` 真实 CLI 与 PNG 人工检查已通过；配套
TXT+SMB 已由真实 M3D-C1/SCOREC 环境成功加载，且 M3D-C1 初始化已完成。时间推进
主循环、中等或长时稳定性及物理结果正确性仍为 PENDING。下一阶段先调查老师提供的
EAST 边界真实类型，再决定复用 `lcfs`、评估 `first_wall` 或实施 `array_file`；
TCV/TRIMEG 为并行的第二条真实消费验证路线。`single_region + first_wall`、
`single_region + array_file` 与真实 `flux_surface` 仍未实现，多区域、多 face、
三维、自适应网格和并行分区仍未开放。
