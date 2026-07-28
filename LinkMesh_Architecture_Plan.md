# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 **3.0**（保持 M1–M3、TRIMEG 真实消费端、M4-1A 与 M4-1B 的既有验收结论不变；同步 M4-2 已实现并完成 LinkMesh 生成侧服务器验收的事实，固化 `disownMdsModel → destroyNative → destroyMesh → gmi_destroy` 的 model ownership 与生命周期规则，明确真实 M3D-C1/SCOREC 外部消费验收由同门负责且仍为 PENDING，并授权 M5 第一条 `target=m3dc1 + profile=single_region + boundary_source=lcfs` CLI 闭环进入实施。LinkMesh 不建设 SMB loader/validator 或 M3D-C1 消费端；Simmetrix、并行 split、Python ABI 扩展与手写 SMB 仍严格排除在 P0 外）
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
  编译和生成侧运行。本地开发仓库、服务器外部调查环境与目标编译运行环境必须保持区分。
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

**当前阶段状态（v2.7）**：

| 阶段 | 状态 |
|---|---|
| M1 Reader | **PASSED** |
| M2 默认 `nested_three_region + artificial_outer` | **PASSED** |
| M2 `single_region + lcfs` 真实 CLI | **PASSED** |
| M3 core | **PASSED** |
| M3 complete-11 | **PASSED** |
| TRIMEG 标准 MATLAB 消费端 A/B 验收 | **PASSED** |
| M4-0 只读侦察与架构契约 | **已完成** |
| M4-1A ModelSpec + TXT Writer + Level 1 | **PASSED** |
| M4-1B 实现入口 probe | **COMPLETED / PASSED** |
| M4-2 LinkMesh 生成侧：classified APF/MDS mesh + 串行 SMB | **IMPLEMENTED / PASSED** |
| M4 外部 M3D-C1/SCOREC 消费验收 | **PENDING；由同门负责** |
| M4 P0 生成侧总体 | **PASSED** |
| M5 第一条 `single_region + lcfs` M3DC1 CLI | **AUTHORIZED / READY FOR IMPLEMENTATION** |

M4 P0 使用已经验收的 `single_region + lcfs` `Mesh2D`，限定 single-region +
single-face。M4-1A TXT model、M4-1B 实现入口 probe 与 M4-2 LinkMesh 生成侧均已
完成。Python SMB Writer、独立 C++ helper、schema v1 私有交换、classified
GMI/APF/MDS mesh、严格 `verify()`、官方 `writeNative()` 与正常资源清理已在锁定的
SCOREC/PUMI 2.2.9 目标环境真实运行通过。

上述结论只表示 **LinkMesh 内部生成侧 PASSED**。配套 TXT+SMB 尚未由同门在真实
M3D-C1/SCOREC 消费环境完成加载验收，因此外部消费状态仍为 **PENDING**。外部验收
结果用于提供格式兼容性反馈并可能触发必要修正，但 LinkMesh 不因此建设 SMB loader、
SMB validator、M3D-C1 消费端或通用 PUMI 验证工具。项目主线现已获准进入 M5 第一条
正式 CLI 闭环。

**P0 范围**：

| 维度 | 允许 | 禁止 |
|---|---|---|
| 输入 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile；`array_file` 两列 CSV 边界（PLANNED） | 在 LinkMesh 侧手写 GFile 文本解析；复杂 CAD；多维输入；Python ndarray 公共边界 API |
| 网格生成 | 调用 OFT `gs_Domain` / `build_mesh()` | 引入第二网格引擎；复制 OFT 通用几何算法；三维网格；自适应细化；修改/维护 OFT 分支 |
| 并行切分 | 不涉及；LinkMesh M4 P0 终点为分区前串行 native SMB | 开发、复制或替代 `split_smb`；生成 `part*.smb` 或任何环向/并行分区；生成 `**1.smb`~`**16.smb` 等分区文件 |
| 输出 | TRIMEG HDF5；M3DC1 配套 analytic model TXT + 分区前串行 PUMI native SMB（M4，经 PUMI/APF/MDS 官方 API） | 三维输出；Simmetrix/`make_model`/`.smd`/`.sms` 正式依赖；手写、拼接、修改、模板复制或逆向 `.smb` 二进制字节流 |
| 可视化 | matplotlib 自检 PNG | 交互式/三维渲染 |
| 配置 | 当前 CLI 参数；两层输入架构（`linkmesh.in` + CLI，见第 6A 节，PLANNED） | 通用配置 DSL / 任意 N 区域语言 / 插件系统 |

---

## 2. 当前架构与模块职责

允许依赖方向：`cli → config / readers / mesher / writers / utils`；`mesher.oft_adapter → mesh`；`writers → mesh`；`utils.plotter → mesh`；`config` 不依赖 Reader/Mesher/Writer/Plotter；`readers.boundary_reader → mesh`（仅复用统一边界验证）。`mesh.py` 不依赖任何后端、Writer、CLI、Plotter 或 config。

| 模块 | 职责（一段式） | 禁止 |
|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口，仅调用 `cli.main()` | 任何业务逻辑或参数解析 |
| `src/linkmesh/cli.py` | 解析/验证用户显式 CLI 参数（含三个区域 `dx` 与规划中的 `--config/--no-config/--target/--profile/--boundary-source/--array-file`），拦截历史 `--min-angle/--max-area`，调用配置合并（见 `config.py`）得到 `EffectiveConfig`，按顺序编排 Reader → `generate_mesh()` → Writer → Plotter | 实现区域/几何/种子/Triangle 算法或任何 dx 换算；自行合并三套默认值/文件/CLI（合并交给 `config.py`）；恢复已删除历史边界构造代码；解析 TOML |
| `src/linkmesh/config.py`（已实现；M5 将解除唯一获准组合的过期阶段闸门） | 定义只读/不可变 `EffectiveConfig`；用标准库 `tomllib` 读取并严格校验 `linkmesh.in`；合并「内建默认值 < 配置文件 < 用户显式 CLI」；按配置目录/当前工作目录两套基准解析路径；校验 `target/profile/boundary_source` 兼容矩阵与 required fields；输出已完成路径解析与类型验证的 `EffectiveConfig`。M5 当前只允许放行 `m3dc1 + single_region + lcfs` | 读取 GFile；读取 array boundary 数据；构造 OFT Domain；调用 Mesher/Writer/Plotter；建设通用配置 DSL、插件系统或任意 N 区域语言；保存值来源字典/ndarray/句柄/argparse Namespace；放行其他 M3DC1 组合 |
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

**M4 当前状态与 M5 实施顺序（v3.0）**：

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
已实现并通过；真实 M3D-C1/SCOREC 外部消费验收仍为 **PENDING**。

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

当前证据不能确认段错误的唯一根因；不得把 analytic model 拓扑不完整、资源生命周期
错误或 PUMI loader 缺陷中的任何一个写成已证实事实。该失败不否定已经成功的编译、
classified entity 创建、`acceptChanges`、`verify`、`writeNative` 与非空 SMB
写出证据，也不构成 PUMI loader、SMB 格式或正式 LinkMesh 方案失败。该人工 probe
不再继续修补，也不扩展为 LinkMesh loader/validator；正式配套 TXT+SMB 的加载检查
属于由同门执行的真实 M3D-C1/SCOREC 外部消费验收。

M4-1B 的职责是消除 M4-2 实现入口处的目标环境、构建接入和核心 API 不确定性，
不要求提前完成正式 LinkMesh TXT+SMB 的 Level 2/3。因此 M4-1B 状态更新为
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
`writeNative()` → `<base>0.smb` 的 LinkMesh 生成链与正常生命周期成立；不证明该
TXT+SMB 已被真实 M3D-C1/SCOREC 消费端加载，也不证明多区域、多 face、三维或并行
能力。

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
- 正式 M5 `single_region + lcfs` 候选应同时生成 TXT、SMB、PNG 和终端统计，并交由
  同门在真实 M3D-C1/SCOREC 环境执行外部消费验收。
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
真实 M3D-C1/SCOREC 外部消费验收仍为 **PENDING**，由同门负责；该待验收项不要求
LinkMesh 建设 loader/validator，也不阻塞 M5 第一条 CLI 编排开始实施。

**M4 验收边界（v3.0）**：

- Level 1（LinkMesh TXT 静态契约）：正式 LinkMesh TXT 结构与 model 契约，
  M4-1A 已通过；
- LinkMesh 生成侧验收：Python SMB Writer 专项测试、M4 相邻回归、目标
  SCOREC/PUMI 2.2.9 helper 构建、schema v1 读取、classified mesh 创建、严格
  `verify()`、官方 `writeNative()`、rank-0 文件确认和完整生命周期已通过；
- 外部消费验收（旧 Level 2/3 的合并替代定义）：由同门在真实
  M3D-C1/SCOREC 环境加载同一份 `M3DC1ModelSpec` 驱动的配套 TXT+SMB，核对
  geometric tags、classification 与消费语义；当前 **PENDING**；
- LinkMesh 不开发轻量 PUMI/APF loader、仓库内 SMB validator、M3D-C1 消费端或
  通用 PUMI 验证工具，不解析、反向读取或验证 SMB 字节；
- 外部消费失败时，结果作为格式兼容性反馈和必要修正证据，但不会把 loader/validator
  建设纳入 LinkMesh；
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
外部消费验收仍由同门负责且当前为 **PENDING**；该边界不阻塞 M5 第一条 CLI 编排。
目标环境若无法继续使用所需 PUMI/APF/MDS 官方库，仍必须停止，不得回退手写 SMB。

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
**COMPLETED / PASSED**；M4-2 LinkMesh 生成侧 **IMPLEMENTED / PASSED**；真实
M3D-C1/SCOREC 外部消费验收 **PENDING，由同门负责**；M5 第一条
`m3dc1 + single_region + lcfs` CLI 闭环 **AUTHORIZED / READY FOR IMPLEMENTATION**。

**M5 第一条正式 CLI 闭环（当前唯一获准 M3DC1 组合）**

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
   折叠或显著异常单元；PNG 人工检查不替代同门的外部 M3D-C1/SCOREC 消费验收。
8. `config.py` 只允许解除 `m3dc1 + single_region + lcfs` 的过期阶段闸门，并继续
   拒绝其他 M3DC1 组合。
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
- OFT 的 `Repeated points` / `Small feature` 警告不表示 Triangle 失败。真实 DIII-D LCFS 单区域来源中，OFT 与 Triangle 已成功生成 344 个节点、631 个三角形和 1 个区域；失败发生在随后将含重复闭合坐标的回写点列转换为 `Mesh2D.outer_boundary` 时。
- `Region._resampled_points` 仍是 `outer_boundary` 的直接权威来源，但它是 OFT 私有拓扑表示，进入 `Mesh2D` 前必须规范化为 LinkMesh 的独立、顺时针、隐式闭合、单一简单闭环表示。不得通过放宽 `Mesh2D` 契约接纳 OFT 回写重复坐标。

**已实现并验收的受控依赖**：

- LinkMesh 在锁定的 `openfusiontoolkit==26.6` 环境中，在 OFT Adapter 内、由策略层明确捕获 outer `Region` 对象后，于 `domain.build_mesh()` 完成后受控读取该对象的私有属性 **`outer_region._resampled_points`**，作为 `outer_boundary` 的权威离散点列来源。
- 读取后创建 `float64` **独立副本**，按 `Mesh2D.outer_boundary` 契约验证并规范化（删除普通显式闭合重复末点、方向规范为顺时针并保持原起点）。
- 该受控读取链已由第二轮 `oft_adapter.py`/`tests/test_oft_adapter.py` 服务器专项测试通过，并经现有 `nested_three_region + artificial_outer` 两个真实 GFile 回归验证。LCFS 单区域来源暴露出的 OFT 点合并回写重复坐标问题仍处于代码修复和真实集成验收阶段，不得据此前既有验收将该新增路径标记为 PASSED。

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

**现有已实现参数**：

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

两层输入架构（`linkmesh.in` + CLI + `EffectiveConfig`）契约见第 6A 节。`outer_padding` 在 v3.0 仍**不暴露**为正式配置或 CLI 字段，保持内部默认策略。OFT `merge_thresh` 同样不暴露为 CLI 或配置字段，继续锁定使用 OFT 26.6 默认 `1e-4 m`。自适应细化和全局 `--mesh-size` 未在源码暴露。M5 当前只授权既有字段表达的 `target=m3dc1 + profile=single_region + boundary_source=lcfs`，不新增 CLI 参数或配置字段。

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

---

## 6A. 输入架构（两层输入 + EffectiveConfig，字段级契约）

以下为 User 已批准的字段级正式契约。保持轻量边界：不得建设通用配置 DSL、任意 N 区域语言或插件系统。

**标准 `linkmesh.in` 示例决策（v2.5）**：两层输入架构、TOML
`schema_version=1`、`EffectiveConfig`、优先级“内建默认值 < `linkmesh.in` <
用户显式 CLI”、未知键严格报错、`--config/--no-config` 互斥及
`target/profile/boundary_source` 兼容矩阵均保持正式有效。仓库当前尚无面向用户的
标准化 `linkmesh.in` 示例，本阶段不创建示例；缺少示例文件不表示配置架构未实现。
待 LinkMesh 的 TRIMEG HDF5 与未来 M3DC1 TXT+SMB 均通过各自真实消费端验收后，
再构造能够覆盖或清晰表达两个下游目标的标准示例，避免现在只围绕 TRIMEG 提前固化。

### 6A.1 模块落点

- `src/linkmesh/config.py`：`EffectiveConfig` 定义 + `linkmesh.in` 读取/校验/合并 + 兼容矩阵/required fields 校验（职责与禁止见第 2 节表）。
- `src/linkmesh/readers/boundary_reader.py`：`array_file` 两列 CSV → `(B,2) float64`（职责与禁止见第 2 节表）。
- `readers/gfile_reader.py`、`mesher/oft_adapter.py`、`cli.py`、`mesh.py`、
[Upstream error: stream_read_error]
