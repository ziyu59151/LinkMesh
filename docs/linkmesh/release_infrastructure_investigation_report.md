# LinkMesh Release 基础设施侦察与迁移分析报告

- 文档主受众：Aider-facing
- 知识库用途：发布基础设施调查与 master 迁移决策参考
- 文档状态：冻结 Release 分支只读侦察结果；不构成 master 实施授权
- 最高依据：User 当前决定；根目录 `LinkMesh_Architecture_Plan.md`；当前 Release 分支实时源码
- 事实边界：本文只调查冻结 Release 分支中的发布构建、启动、检查、追溯和归档基础设施。本文不修改正式蓝图，不把 Prototype 2 的人工修正描述为仓库自动能力，也不把构建成功或文件生成外推为外部消费、时间推进、稳定性或物理正确性通过。

---

## 1. 调查目标与范围

### 1.1 唯一目标

【当前对话直接事实】本次任务只为后续 master 实施形成发布基础设施调查报告。冻结的
Release 分支不再继续开发，也不整体合并回 master；User 将自行把本报告复制到
master，再单独授权 master 上的正式修改。

【推断或建议】master 后续应按“先修订正式契约，再迁移最小通用逻辑，最后在 Linux
服务器重新构建和验证”的顺序实施，不应把冻结分支整体 merge、cherry-pick 或视为
master 的替代基线。

### 1.2 已调查文件

| 文件 | 调查用途 | 证据定位 |
|---|---|---|
| `LinkMesh_Architecture_Plan.md` | 正式 Release 结构、运行时、验证和状态边界 | 第 8.7～8.15、9.5、9.9、10.1、10.5、10.6 节 |
| `CONTEXT.md` | 蓝图先行、读写隔离、长期文档和历史归档纪律 | 第 2、5、8、10、11 节 |
| `History.md` | 已归档的 Release 设计、实现和阶段事实 | 第 30、32 条及其前置记录 |
| `Project_Tree.md` | 仓库导航和当前 Release 阶段背景 | 第 3、11、16、17 节 |
| `packaging/release/build_release.sh` | Linux 离线组装、审计、manifest、目录和 tar.gz 生成 | `require_value`、参数解析、依赖探针、`WORK_PARENT`、manifest 与归档代码块 |
| `packaging/release/linkmesh-launcher` | 用户入口、解释器选择和 helper 定位 | `resolve_script`、`select_python`、环境变量导出和末尾 `exec` |
| `packaging/release/linkmesh-bootstrap.py` | Release Python 包路径注入和模块启动 | `main()` |
| `packaging/release/linkmesh-check` | 分层环境检查和 native 动态依赖诊断 | `check_core`、`check_python_module`、`check_m3dc1_native`、`run_mode` |
| `packaging/release/README.md` | 当前维护者构建说明和最终用户使用说明 | “交付内容”“两阶段构建流程”“最终用户使用”“分层环境检查”等章节 |
| `native/linkmesh_scorec_helper/CMakeLists.txt` | helper 当前构建入口和链接边界 | `find_package`、`add_executable`、`target_link_libraries` |
| `.gitignore` | 构建、运行和发布产物的 Git 排除边界 | “Build and native compilation output”“Runtime logs and generated outputs” |
| `requirements.txt` | 开发依赖和 OFT 版本锁定背景 | `openfusiontoolkit==26.6` 及科学计算依赖段 |

### 1.3 未调查内容

【实时源码事实】本次未读取或修改 `src/` 业务实现、测试正文、examples 正文、外部
只读源码、真实 Release 目录、tar.gz 内容列表、服务器构建日志、Prototype 2
手工操作命令记录或外部消费端日志。

【当前对话直接事实】Prototype 2 已完成环境检查和实际文件生成，但 HDF5 与 SMB 的
真实消费端有效性仍由同门继续验证。

【推断或建议】以下事项证据不足，不能由本报告补全：

- 共享软件根目录、modulefile 和组权限；
- 目标服务器统一 MPI 来源；
- 可跨服务器复用的 glibc、libstdc++、MPI 或其他 ABI 策略；
- HDF5 与 SMB 的最新外部加载、初始化、时间推进和物理结果；
- master 当前发布文件与冻结分支之间的精确差异；
- Prototype 2 所有人工命令及其可重复性。

### 1.4 调查约束

【蓝图正式契约】业务源码、Writer 格式、`Mesh2D`、M3D-C1 classification、helper
交换 schema、OFT 26.6 兼容接口和求解器能力均不属于本次迁移修改范围。依据蓝图
第 10.1 节，改变 Release 结构、安装、入口或兼容策略必须先修改蓝图并经 User 确认。

【实时源码事实】本次唯一可写文件为本报告；报告没有实施 README、构建器、CMake、
业务源码、测试、示例、蓝图或 History 修改。

---

## 2. 权威依据与证据等级

本文每项结论使用以下标签，不混用证据层级：

| 标签 | 含义 |
|---|---|
| 【实时源码事实】 | 可由本次提供的当前分支文件正文直接确认 |
| 【当前对话直接事实】 | User 在当前任务中明确提供的 Prototype 2 或迁移事实 |
| 【蓝图正式契约】 | 根目录当前 `LinkMesh_Architecture_Plan.md` 的正式规定 |
| 【History 已归档事实】 | `History.md` 已记录的历史实现或验证事实 |
| 【推断或建议】 | 基于上述证据提出的迁移判断、风险或后续方案 |

【推断或建议】当实时源码、当前交付事实和蓝图不一致时，应并列记录冲突，不用较低层
证据覆盖较高层决定，也不把尚未实施的新规则写成当前代码能力。

---

## 3. 当前 Release 基础设施图

### 3.1 发布数据流

```text
本地 Windows Git commit
  │
  │ git archive + 源码归档 SHA-256
  ▼
源码 tar.gz
  │ 上传并在全新 Linux 源码目录展开
  ▼
packaging/release/build_release.sh
  │ --output / --version / --python / --helper
  │ --source-commit / --source-archive / --source-archive-sha256
  │
  ├─ 校验 Python、OFT 26.6、helper ELF、ldd、readelf
  ├─ 复制 LinkMesh、OFT、dist-info、helper、launcher、bootstrap、check
  ├─ 当前还复制 packaging/release/README.md 到 Release 根目录
  ├─ 生成 build-info、Python/native requirements
  ├─ 删除 __pycache__ 和 *.pyc
  └─ 生成 manifest/SHA256SUMS
  ▼
linkmesh-release-<version>-linux-x86_64/
  │
  ├─ tar -czf
  ▼
linkmesh-release-<version>-linux-x86_64.tar.gz
  │
  ├─ 当前脚本未生成外部 tar.gz.sha256
  ├─ Prototype 2 交付阶段曾手工修正包内 README
  └─ 内容变化后重新计算外部 tar.gz.sha256
  ▼
干净目录解压与 linkmesh-check 分层检查
  │
  ├─ core
  ├─ trimeg
  ├─ plot
  └─ m3dc1
  ▼
真实输入生成验证
  │
  ├─ TRIMEG HDF5
  └─ M3D-C1 TXT + rank-0 SMB + PNG
  ▼
外部用户加载、初始化、时间推进和物理反馈
```

【实时源码事实】`build_release.sh` 直接生成 Release 目录和 tar.gz，并在 Release
内部生成 `manifest/SHA256SUMS`；脚本没有生成外部 `tar.gz.sha256`。证据位置为脚本
末尾 `find ... sha256sum >manifest/SHA256SUMS`、`tar -czf` 和最终 `mv` 代码块。

【当前对话直接事实】0.1.0-prototype2 的最终交付目录包含外部用户 `README.md`、
tar.gz 和 tar.gz.sha256；tar.gz 内部 README 是发布后手工删除的，不是已由当前
构建器自动实现的能力。

### 3.2 运行时调用关系

```text
最终用户
  │
  ▼
bin/linkmesh                         bin/linkmesh-check
  │                                      │
  │ resolve_script()                     ├─ core
  │ select_python()                      ├─ trimeg
  │ export LINKMESH_SCOREC_HELPER        ├─ plot
  │ export LINKMESH_RELEASE_ROOT         ├─ m3dc1
  ▼                                      └─ all
bin/linkmesh-bootstrap.py
  │
  │ Release/python/site-packages 插入 sys.path 首位
  ▼
runpy.run_module("linkmesh.__main__")
  │
  ├─ TRIMEG：Python + NumPy + h5py
  ├─ Plot：Python + NumPy + Matplotlib
  └─ M3D-C1：Python Writer
               │
               ▼
        Release/bin/linkmesh-scorec-helper
               │
               ▼
        MPI + SCOREC/PUMI + 系统 C/C++ runtime
```

【实时源码事实】launcher 只为当前子进程导出 helper 和 Release 根目录，不设置
`PYTHONPATH` 或 `LD_LIBRARY_PATH`；bootstrap 在 Python 进程内调整 `sys.path`。
证据位置分别为 `linkmesh-launcher` 末尾环境变量和 `exec`、以及
`linkmesh-bootstrap.py:main()`。

---

## 4. 逐文件调查结果

### 4.1 `packaging/release/build_release.sh`

**职责**

【实时源码事实】该脚本是 Linux Release 组装入口，负责：

1. 严格解析七个必需参数并拒绝未知参数；
2. 校验版本、源码 commit、归档名和源码归档 SHA-256 的词法格式；
3. 校验构建工具、Python 和 helper；
4. 确认 helper 是可执行 Linux x86-64 ELF；
5. 执行 `ldd` 和 `readelf -d` 审计；
6. 从所选 Python 环境定位精确版本 OFT 26.6 包和 dist-info；
7. 把 LinkMesh、OFT、helper 及发布脚本组装到临时 Release；
8. 生成 manifest、内部普通文件 SHA-256 和 tar.gz；
9. 在成功前不占用最终 Release 路径，并在退出时清理临时目录。

稳定定位：`require_value()`、参数 `case`、`required_command` 循环、
`OFT_LOCATION` Python probe、`WORK_PARENT`/`cleanup`、三个 manifest 生成块、
`SHA256SUMS` 和 `tar -czf` 代码块。

**输入**

【实时源码事实】输入包括源码树、输出目录、版本、目标 Python、已编译 helper、源码
commit、源码归档文件名和源码归档 SHA-256。脚本不读取 Git 状态，也不自行生成源码
归档。

**输出**

【实时源码事实】输出是：

- `linkmesh-release-<version>-linux-x86_64/`；
- 同名 `.tar.gz`；
- Release 内 `manifest/build-info.txt`；
- Release 内 `manifest/python-requirements.txt`；
- Release 内 `manifest/native-requirements.txt`；
- Release 内 `manifest/SHA256SUMS`。

【实时源码事实】脚本不输出外部 tar.gz.sha256，也不生成外部交付目录层。

**运行时边界**

【实时源码事实】脚本没有 `pip`、网络下载或 Git 命令；OFT 必须已存在于所选 Python
环境，helper 必须已构建完成。它是离线组装器，不是环境安装器或 helper 编译器。

【推断或建议】“离线”表示脚本自身不联网，不表示操作系统层面主动阻断网络。

### 4.2 `packaging/release/linkmesh-launcher`

**职责与输入**

【实时源码事实】launcher 是最终用户入口。它通过 `BASH_SOURCE[0]` 和符号链接解析
自身真实路径，定位 Release 根目录、bootstrap 和 Release 内 helper；用户参数通过
末尾 `exec ... "$@"` 原样传递。

**Python 选择顺序**

【实时源码事实】`select_python()` 的顺序是：

1. `LINKMESH_PYTHON`；
2. `python3`；
3. `python`。

当 `LINKMESH_PYTHON` 包含 `/` 时要求路径可执行；否则使用 `command -v` 查找命令。

**输出与运行边界**

【实时源码事实】launcher 不产生业务输出，只选择解释器、设置
`LINKMESH_SCOREC_HELPER` 和 `LINKMESH_RELEASE_ROOT`，然后以 `exec` 启动
bootstrap，因此参数、信号和退出状态不会被额外 shell 进程吞掉。

【推断或建议】`LINKMESH_RELEASE_ROOT` 当前由 launcher 导出，但本次调查没有发现
bootstrap 使用它；是否属于必要公共运行时接口需在 master 迁移时继续检索，不能仅按
变量名决定删除。

### 4.3 `packaging/release/linkmesh-bootstrap.py`

**职责**

【实时源码事实】bootstrap 从自身所在 `bin` 目录推导
`python/site-packages`，确认目录存在，将该路径放到 `sys.path` 首位，并通过
`runpy.run_module("linkmesh.__main__", run_name="__main__", alter_sys=True)` 启动
统一 CLI。

**边界**

【实时源码事实】bootstrap 不设置 `PYTHONPATH`，不安装依赖，不选择 Python，不定位
helper，也不修改磁盘上的 Python 环境。

【推断或建议】该机制是可移动 Release 的核心隔离层，可复用，但 master 应保留
“Release 自带包优先、目标 Python 正常环境提供通用依赖”的明确边界测试。

### 4.4 `packaging/release/linkmesh-check`

**职责**

【实时源码事实】检查器提供 `core`、`trimeg`、`plot`、`m3dc1` 和 `all` 模式：

| 模式 | 当前检查 | 明确不检查 |
|---|---|---|
| `core` | Python、Release site-packages、Release LinkMesh、OFT 26.6、NumPy | h5py、Matplotlib、helper、MPI |
| `trimeg` | core + h5py | helper、MPI、真实 HDF5 写出和消费 |
| `plot` | core + Matplotlib headless import | helper、MPI、真实 PNG |
| `m3dc1` | core + helper 文件、权限、ELF、readelf、ldd、libmpi 路径 | SMB 写出、M3D-C1 加载和初始化 |
| `all` | 依次运行上述全部模式 | 真实求解器消费 |

稳定定位：`check_core()`、`check_python_module()`、`check_m3dc1_native()`、
`run_mode()`。

**运行边界**

【实时源码事实】SciPy 和 netCDF4 只作 OFT 元数据非阻塞诊断；Matplotlib 强制使用
`Agg`；TRIMEG 与 plot 模式不因 helper 或 MPI 缺失而失败。

【实时源码事实】`file` 或 `readelf` 不可用时为 `WARNING`；`ldd` 不可用、存在
`not found`、未报告 `libmpi` 或未解析实际路径时为阻塞性 `MISSING`。

【推断或建议】检查器证明的是运行环境可见性，不证明 helper 能写 SMB，也不证明
M3D-C1 能加载该 SMB。

### 4.5 `packaging/release/README.md`

【实时源码事实】该文件同时承载维护者的两阶段构建流程和最终用户的解压、入口、环境
检查及反馈说明。稳定章节包括“交付内容”“两阶段构建流程”“最终用户使用”
“分层环境检查”“运行时定位”“外部验证反馈”。

【实时源码事实】当前内容明确声称 Release 自带根目录 README，并展示 tar.gz 解压后
直接运行的结构和命令；这与 Prototype 2 最新“README 只位于 tar.gz 外部”交付规则
发生冲突。

【推断或建议】一个文件同时面向构建维护者和最终用户不是必然错误，但复制位置和交付
职责必须只有一个正式来源，不能形成维护者 README、包内 README、外部 README 三份
独立正文。

### 4.6 `native/linkmesh_scorec_helper/CMakeLists.txt`

【实时源码事实】该文件：

- 要求 CMake 3.20；
- 精确查找 SCOREC 2.2.9 的 `mds`、`apf`、`gmi`、`pcu`；
- 查找 MPI C++；
- 构建 `linkmesh-scorec-helper`；
- 使用 C++17；
- 链接 SCOREC imported targets 和 `MPI::MPI_CXX`；
- 禁止编译器扩展。

【实时源码事实】当前文件没有 `install(TARGETS ...)`，因此构建器通过显式
`--helper PATH` 接收外部已构建 helper，而不是通过本 CMake 文件安装到 Release。

【推断或建议】helper 构建规则可作为 master 的基础，但“CMake install”仍是未实现
能力，不能随发布脚本迁移被描述为已经具备。

### 4.7 `.gitignore`

【实时源码事实】当前忽略 Python 环境和缓存、`build/`、`dist/`、CMake 产物、日志、
HDF5、SMB、PNG 及常见运行输出目录。

【推断或建议】当前规则支持“服务器构建和验证产物不进入 Git”的原则，但不会替代
发布脚本的目标路径检查，也不应成为允许在仓库内长期构建的依据。

### 4.8 `requirements.txt`

【实时源码事实】开发依赖包括 NumPy、h5py、Matplotlib、OFT 26.6 和可选 pytest；
OFT 使用精确版本 `openfusiontoolkit==26.6`。

【实时源码事实】Release 构建器不根据该文件安装依赖；它只复制 OFT 26.6，通用包由
所选目标 Python 环境提供。

【推断或建议】`requirements.txt` 不能当作 Release 完整锁文件或 ABI 清单。master
迁移时不应让发布脚本隐式执行 `pip install -r requirements.txt`。

---

## 5. 已验证的通用能力

### 5.1 当前直接验证边界

【当前对话直接事实】0.1.0-prototype2 已实际生成并交付，在 Linux x86-64 上分别使用
CPython 3.12.13 和系统 CPython 3.12.3 完成环境检查及实际文件生成。

【当前对话直接事实】已实际生成：

- TRIMEG HDF5；
- M3D-C1 TXT；
- rank-0 SMB；
- PNG。

【当前对话直接事实】HDF5 与 SMB 的真实消费端有效性仍由同门验证。因此当前证据只到
Release 运行和文件生成，不得记录为最新交付物已经外部加载、初始化、时间推进、稳定
运行或物理验证。

### 5.2 已有跨版本复用价值

【推断或建议】以下能力已有源码与 Prototype 2 直接运行证据，具备较高迁移价值：

- 基于源码归档而非服务器 Git 的离线组装；
- 不覆盖既有 Release 目录和 tar.gz；
- 临时工作目录、原子式最终移动和失败清理；
- launcher 自定位；
- Python 分级选择；
- bootstrap 的 Release site-packages 优先注入；
- Release 内 helper 的环境变量定位；
- 分层检查器；
- helper ELF、动态库和 MPI 路径诊断；
- build-info、requirements 摘要和内部 SHA-256；
- 源码 commit、源码归档摘要和 helper 摘要追溯；
- 清除 Python 缓存；
- 不依赖个人 `PYTHONPATH`、开发 helper 路径或开发构建目录。

---

## 6. Prototype 2 特有处理与人工步骤

### 6.1 不得伪装为构建器能力的步骤

【当前对话直接事实】Prototype 2 发布后手工删除了 tar.gz 内部 README，并形成外部
README、tar.gz 和 tar.gz.sha256 的最终交付目录。

【实时源码事实】当前 `build_release.sh` 仍要求 README 模板存在并把它复制进
Release 根目录。因此“包内不带 README”不是当前脚本能力。

【推断或建议】master 不应复制已手工改写的 tar.gz，也不应通过在脚本执行后再次解包、
删除和重打包来固定正式流程。正式规则应进入蓝图、构建器和结构回归。

### 6.2 Prototype 2 暴露的配置示例问题

【当前对话直接事实】single-region 配置示例必须使用 `mesh_dx`，不能使用
`plasma_dx`。

【蓝图正式契约】蓝图第 3.4、5.4、5.6A 节规定
`profile=single_region` 只使用 `mesh_dx`；显式区域 dx 应失败。

【推断或建议】master 实施前应检查所有面向用户的 Release README、配置示例和命令
片段。修复范围只应是发布文档和示例，不得改变 `EffectiveConfig` 或 Adapter 的正式
业务映射。

### 6.3 归档结构与摘要一致性

【当前对话直接事实】文档中的 Release 解压结构必须与实际归档一致；tar.gz 内容变化
后必须重新生成外部 tar.gz.sha256。

【实时源码事实】内部 `manifest/SHA256SUMS` 在打包前对 Release 内全部普通文件生成，
排除自身。如果在归档前删除包内 README，就必须在删除后生成该 manifest；如果在
manifest 生成后删除 README，manifest 将包含不存在文件的摘要记录。

【推断或建议】正式构建应按以下顺序保持一致：

```text
组装最终包内内容
  → 删除缓存
  → 生成包内 manifest/SHA256SUMS
  → 创建 tar.gz
  → 生成外部 tar.gz.sha256
  → 干净目录解压并核对内部 manifest 与外部摘要
```

### 6.4 验证状态分层

【蓝图正式契约】蓝图第 9.5 节要求区分 `IMPLEMENTED`、`GENERATED`、`DELIVERED`、
`LOADED`、`INITIALIZED`、`TIME-STEPPED`、`PHYSICALLY VALIDATED` 和 `PENDING`。

【推断或建议】Prototype 2 和 master 后续报告至少应分开记录：

1. 构建脚本成功；
2. Release 目录和 tar.gz 已生成；
3. manifest 和外部摘要一致；
4. 干净解压环境检查通过；
5. HDF5/TXT/SMB/PNG 已生成；
6. 外部程序已加载；
7. 外部程序已初始化；
8. 已完成明确时间推进；
9. 稳定性和物理结果已确认。

---

## 7. README 和归档结构冲突

### 7.1 当前构建器行为

| 问题 | 调查结论 |
|---|---|
| 是否强制要求 `packaging/release/README.md` | 【实时源码事实】是。`build_release.sh` 的 `for template in ... README.md` 会在缺失时失败。 |
| 是否复制到 Release | 【实时源码事实】是。`install -m 0644 "$SCRIPT_DIR/README.md" "$WORK_RELEASE/README.md"`。 |
| 是否进入 tar.gz | 【实时源码事实】是。脚本对整个 `$RELEASE_NAME` 目录执行 `tar -czf`。 |
| 是否进入内部 SHA manifest | 【实时源码事实】是。它是 Release 内普通文件，满足 `find . -type f`。 |
| 是否自动生成外部 README | 【实时源码事实】否。 |
| 是否自动生成 tar.gz.sha256 | 【实时源码事实】否。 |

### 7.2 当前冲突

【当前对话直接事实】User 最新交付规则是 README 仅位于 tar.gz 外部。

【蓝图正式契约】蓝图第 8.15 节当前目录结构包含 Release 根目录 `README.md`，并规定
Release 自带 README。

【实时源码事实】`build_release.sh` 和 `packaging/release/README.md` 都实现或描述
包内 README。

【实时源码事实】`Project_Tree.md` 第 11 节把
`packaging/release/README.md` 描述为 Release 构建和交付说明，但没有落实最新
“仅在 tar.gz 外部”的结构。

【推断或建议】这是“当前对话直接交付事实”与“仓库正式契约及实现”的明确冲突。
冻结分支不得自行宣布蓝图已更新；master 必须先获得 User 对最终外部交付布局的确认并
修改蓝图。

### 7.3 master 采用外部 README 规则时的必改范围

【推断或建议】至少需要先审查并预计修改：

1. `LinkMesh_Architecture_Plan.md`：第 8.15、9.9、10.1 相关 Release 结构和验收；
2. `Project_Tree.md`：Release 结构、文件职责和最终用户路径；
3. `packaging/release/build_release.sh`：README 必需模板、复制位置、内部 manifest、
   tar.gz 和外部摘要生成顺序；
4. `packaging/release/README.md`：构建输出结构、解压命令和最终用户说明；
5. 发布结构回归测试或检查脚本：确认包内无 README、外部 README 存在、两个摘要层
   一致；
6. 任何面向用户的 Release 示例或交付清单。

【推断或建议】是否同步修改 `History.md` 取决于 master 上完成实际实施和验收后是否
形成新战果；不得在实施前把建议写成已完成历史。

### 7.4 README 单一来源策略

【推断或建议】建议保留一个仓库内权威源文件，例如继续使用
`packaging/release/README.md`，但明确其唯一角色。构建器应从该文件生成或复制外部
用户 README，tar.gz 内不再放另一份正文。

【推断或建议】必须先由 User 决定外部交付目录结构，例如 README 是否与某一版本
tar.gz 同目录、是否固定名为 `README.md`。在该决策前，不应擅自引入版本化 README
文件名或新的交付目录层。

【推断或建议】迁移后的最小同步规则应为：

- 仓库中只编辑一个 README 源文件；
- 构建器只复制该源文件到正式外部位置；
- 不允许维护者手工维护第二份包内 README；
- 结构回归对源文件和外部 README 做字节一致性检查；
- README 中的解压结构由归档内容列表测试约束；
- README 的 single-region 示例使用 `mesh_dx`；
- README 更新不改变业务接口或目标格式。

---

## 8. 发布追溯、依赖与 ABI 管理

### 8.1 当前追溯字段

【实时源码事实】`manifest/build-info.txt` 记录：

- Release 名称和版本；
- 源码 commit；
- 源码归档文件名和 SHA-256；
- UTC 构建日期；
- 构建主机和平台；
- Python 实现和版本；
- OFT 版本；
- helper SHA-256；
- helper `file`、`ldd` 和 `readelf -d` 摘要。

稳定定位：`build_release.sh` 中 `HELPER_SHA256` 至 `build-info.txt` here-document。

【实时源码事实】`python-requirements.txt` 区分 bundled 与目标 Python 环境提供的包，
并记录当前验证环境为 CPython 3.12.13。

【实时源码事实】`native-requirements.txt` 说明 helper、静态 PUMI 组件、未封装的 MPI
和系统 ABI 边界，并明确 TRIMEG 不依赖 helper。

### 8.2 SHA-256 的三个不同对象

| 摘要 | 对象 | 当前状态 |
|---|---|---|
| 源码归档 SHA-256 | 输入源码 tar.gz | 【实时源码事实】由构建参数传入并记录，不由脚本计算 |
| `manifest/SHA256SUMS` | Release 内普通文件 | 【实时源码事实】由脚本生成 |
| 外部 tar.gz.sha256 | 最终压缩归档 | 【当前对话直接事实】Prototype 2 最终交付存在；【实时源码事实】当前脚本不生成 |

【推断或建议】三者不可互相替代。master 的构建输出和验收日志应明确摘要对象、计算
时机和验证命令。

### 8.3 helper 与 ABI

【实时源码事实】构建器要求 helper 是 Linux x86-64 ELF、`ldd` 无 `not found`；
检查器进一步报告 `NEEDED`、`RPATH`、`RUNPATH` 和实际 `libmpi` 路径。

【蓝图正式契约】蓝图第 7.7、7.9、8.15 节规定 helper 仍受 Linux、MPI、glibc、
libstdc++、编译器和系统 ABI 约束；当前观察不能外推为任意服务器兼容。

【推断或建议】master 可以迁移“审计机制”，但不能迁移某个个人服务器的动态库路径、
MPI 来源或 ABI 结论。正式 MPI 来源和 ABI 策略仍属于待确认事项。

### 8.4 个人路径隔离

【实时源码事实】构建器会扫描 Release 文本中的特定维护者和开发路径并失败；launcher
通过自身路径定位，不写死个人主目录；helper 由 Release 内路径定位。

【蓝图正式契约】蓝图第 8.8、8.10、8.13、8.15 节禁止正式发布依赖个人
`PYTHONPATH`、开发构建目录或维护者主目录。

【推断或建议】当前禁止路径列表只有已知字符串，不能证明所有个人绝对路径均被覆盖。
master 应保留明确禁止项，并增加结构测试检查常见源码根、构建根和上传目录泄漏。

---

## 9. 可迁移能力分类表

分类定义：

- **A**：可直接迁移的通用基础设施；
- **B**：需要在 master 修订后迁移；
- **C**：受蓝图先行纪律约束，必须先经 User 确认并修改蓝图；
- **D**：仅服务 Prototype 2 或个人服务器路径，不应迁移；
- **E**：证据不足，需继续调查。

| 类别 | 能力 | 当前实现位置 | 解决的问题 | 直接证据 | 对 master 的价值 | 建议方式 | 依赖与风险 |
|---|---|---|---|---|---|---|---|
| A | 参数严格校验与未知参数拒绝 | `build_release.sh`：`require_value`、参数 `case` | 防止不完整或歧义构建 | 【当前对话直接事实】Prototype 2 已构建 | 高 | 原样迁移后静态核对 | master 参数契约不能已发生不兼容变化 |
| A | 不覆盖既有 Release | `FINAL_DIR`/`FINAL_ARCHIVE` 存在性检查 | 避免破坏已发布版本 | 【实时源码事实】有明确失败逻辑 | 高 | 原样迁移 | 新外部交付文件也需同等不覆盖规则 |
| A | 临时目录与失败清理 | `mktemp`、`trap cleanup EXIT`、最终 `mv` | 避免半成品占用正式路径 | 【实时源码事实】已实现；【当前对话直接事实】构建已运行 | 高 | 原样迁移 | 信号、跨文件系统移动需服务器验证 |
| A | LinkMesh、OFT 26.6 和 helper 组装 | `cp -a`、`install`、OFT probe | 形成不依赖源码目录的移动包 | 【当前对话直接事实】两种 CPython 已生成文件 | 高 | 修订后整体保留核心逻辑 | master 包布局和 OFT 契约必须一致 |
| A | launcher 自定位 | `linkmesh-launcher:resolve_script()` | 支持移动目录和符号链接入口 | 【当前对话直接事实】Release 已运行 | 高 | 原样迁移 | 目标平台仍为 Bash/Linux |
| A | Python 分级选择 | `select_python()` | 支持显式和系统解释器 | 【当前对话直接事实】CPython 3.12.13 与 3.12.3 已验证 | 高 | 原样迁移 | 其他 Python 版本仍需验证 |
| A | bootstrap 注入 site-packages | `linkmesh-bootstrap.py:main()` | 不使用 `PYTHONPATH` 启动内置包 | 【当前对话直接事实】实际文件生成 | 高 | 原样迁移 | master 包需可由 `linkmesh.__main__` 启动 |
| A | Release 内 helper 定位 | launcher 导出 `LINKMESH_SCOREC_HELPER` | 避免开发 helper 路径泄漏 | 【当前对话直接事实】SMB 已生成 | 高 | 原样迁移 | helper 名称和 Writer 定位契约必须未变 |
| A | 分层环境检查 | `linkmesh-check:run_mode()` | TRIMEG 与 M3D-C1 依赖解耦诊断 | 【当前对话直接事实】已执行环境检查 | 高 | 原样迁移后回归 | 检查不能被描述为真实消费 |
| A | helper ELF/动态库/MPI 审计 | 构建器和 `check_m3dc1_native()` | 提前发现架构和动态库缺失 | 【实时源码事实】已实现 | 高 | 原样迁移 | 不能固定当前 MPI 路径或 ABI 结论 |
| A | 删除缓存 | `find __pycache__`、`*.pyc` | 避免开发缓存污染 Release | 【实时源码事实】已实现 | 中 | 原样迁移 | 应在内部 manifest 前执行 |
| A | 禁止通用包和源码内容误打包 | `forbidden_path`、`forbidden_package` | 控制包边界和体积 | 【实时源码事实】已实现 | 高 | 修订列表后迁移 | master 目录结构可能变化 |
| B | build-info 与 requirements manifest | 三个 manifest 生成块 | 追溯构建环境和依赖边界 | 【实时源码事实】已实现 | 高 | 修订后迁移 | 字段必须与 master 当前事实一致 |
| B | 内部 `SHA256SUMS` | `find/sort/xargs sha256sum` | 检查包内普通文件完整性 | 【实时源码事实】已实现 | 高 | 修订后迁移 | 必须在最终包内容确定后生成 |
| B | 外部 tar.gz.sha256 | 当前脚本无实现 | 验证最终交付归档 | 【当前对话直接事实】Prototype 2 有人工产物 | 高 | 在 master 正式实现 | 必须防止归档变化后摘要过期 |
| B | helper CMake 构建规则 | `native/.../CMakeLists.txt` | 复现目标 helper 编译 | 【History 已归档事实】目标环境曾构建通过 | 高 | 对比 master 后迁移 | 当前无 `install(TARGETS ...)` |
| B | 禁止个人路径泄漏 | `grep -R` 已知路径 | 防止发布包含维护者路径 | 【实时源码事实】有部分检查 | 中 | 扩充后迁移 | 现有列表不完备 |
| B | single-region 用户配置说明 | 发布 README 和 master 示例 | 防止使用 `plasma_dx` | 【当前对话直接事实】Prototype 2 暴露问题 | 高 | 修订后迁移 | 不能改变业务配置契约 |
| C | README 仅位于 tar.gz 外部 | 当前未实现 | 统一交付结构 | 【当前对话直接事实】最新规则；与蓝图冲突 | 高 | 先改蓝图再改构建器 | 外部目录结构和命名需 User 确认 |
| C | Release 解压结构调整 | 蓝图 8.15、构建器、README | 保证文档和归档一致 | 【实时源码事实】当前结构含 README | 高 | 先改蓝图再实施 | 会改变正式发布结构 |
| C | 外部 README 单一来源 | `packaging/release/README.md` 候选源 | 防止三份 README 分叉 | 【推断或建议】尚无正式实现 | 高 | 先确认契约 | 维护者与用户受众边界需决定 |
| C | 新增正式发布结构回归 | master 测试或发布脚本 | 防止结构和摘要回归 | 【推断或建议】当前未见对应测试 | 高 | 蓝图确认后新增 | 不应扩展到业务测试 |
| D | Prototype 2 手工重打包步骤 | 不在仓库脚本中 | 临时满足交付规则 | 【当前对话直接事实】手工执行 | 低 | 不迁移 | 易造成内部 manifest 失真 |
| D | 个人绝对路径和开发 helper 路径 | 服务器个人环境 | 仅服务个人开发 | 【蓝图正式契约】正式 Release 禁止 | 无 | 不迁移 | 隐私、不可移植、ABI 不确定 |
| D | 生成的 Release、tar.gz 和 helper 二进制 | 服务器构建产物 | 某次交付 | 【当前对话直接事实】已生成 | 无 | 不进入 master Git | 二进制和摘要只对应一次构建 |
| E | modulefile 与共享根目录 | 当前未实现 | 组内统一入口 | 【蓝图正式契约】PENDING | 潜在 | 暂不迁移 | 根目录、权限和维护责任未确认 |
| E | 统一 MPI 来源和 ABI 策略 | 当前仅审计 | 跨服务器 native 兼容 | 【蓝图正式契约】需目标环境验证 | 高 | 继续调查 | 不能从 Prototype 2 外推 |
| E | CMake install 流程 | 当前 CMake 无 install | 标准化 helper 安装 | 【实时源码事实】未实现 | 中 | 仅保留设计 | 需 master 构建和发布方案确认 |
| E | 最新 HDF5/SMB 外部消费状态 | 同门验证中 | 确认求解器有效性 | 【当前对话直接事实】PENDING | 高 | 等待反馈 | 不得由文件生成替代 |

---

## 10. Master 分批实施建议

### 10.1 批次 1：修复发布文档和归档结构契约

**前置决策**

【推断或建议】User 需确认：

- README 是否确定只在 tar.gz 外部；
- 外部 README 的文件名和所在目录；
- 外部 tar.gz.sha256 的正式名称和格式；
- 是否由 `build_release.sh` 一次性生成全部三类外部交付物。

**预计修改文件**

【推断或建议】

- `LinkMesh_Architecture_Plan.md`；
- `Project_Tree.md`；
- `packaging/release/README.md`；
- 可能涉及 `docs/linkmesh/` 下 master 当前发布说明；
- master 当前 single-region 配置示例。

**禁止触碰的业务契约**

【蓝图正式契约】不得修改 `EffectiveConfig`、`mesh_dx` 语义、TRIMEG 11 数据集、
M3D-C1 TXT/SMB、`Mesh2D`、helper exchange schema 或 OFT 26.6 网格行为。

**验收证据**

【推断或建议】

- 文档只定义一种归档结构；
- 所有 single-region 示例使用 `mesh_dx`；
- README 单一来源和复制位置明确；
- 蓝图、导读和用户说明无相互冲突。

**停止条件**

【推断或建议】若 User 未确认外部 README 布局，或 master 当前业务参数已改变但没有
蓝图依据，应停止，不先改构建器。

### 10.2 批次 2：迁移或整理通用构建、launcher、bootstrap、检查器与 manifest

**前置决策**

【推断或建议】完成批次 1，并比较 master 当前的目录、helper 名称、Python入口和 OFT
版本契约。

**预计修改文件**

【推断或建议】

- `packaging/release/build_release.sh`；
- `packaging/release/linkmesh-launcher`；
- `packaging/release/linkmesh-bootstrap.py`；
- `packaging/release/linkmesh-check`；
- `packaging/release/README.md`；
- 必要时 `native/linkmesh_scorec_helper/CMakeLists.txt`，但仅限已授权的构建或安装
  边界调整。

**禁止触碰的业务契约**

【蓝图正式契约】不得修改 Python Writer、helper schema、classification、OFT Adapter、
HDF5 格式或 CLI 业务组合。

**验收证据**

【推断或建议】

- 脚本 shell/Python 静态检查通过；
- 构建器不会覆盖既有输出；
- 最终包内内容先确定，再生成内部 SHA manifest；
- tar.gz 创建后生成外部 tar.gz.sha256；
- launcher 不依赖个人目录或 `PYTHONPATH`；
- TRIMEG 检查不被 helper/MPI 阻塞。

**停止条件**

【推断或建议】如 master helper 名称、OFT 版本、包入口或输出结构无法与冻结分支逻辑
无歧义映射，应停止并先更新蓝图，不添加兼容猜测。

### 10.3 批次 3：增加最小静态和结构回归

**前置决策**

【推断或建议】批次 2 的输出结构和摘要规则已经固定。

**预计修改文件**

【推断或建议】在 master 现有测试约定下新增或修改最少量发布专项测试文件；不复制
冻结分支的业务测试。具体文件名应以 master 实时测试布局为准。

**禁止触碰的业务契约**

【蓝图正式契约】结构回归只检查发布基础设施，不模拟 OFT、PUMI、TRIMEG 或 M3D-C1
物理行为。

**验收证据**

【推断或建议】至少覆盖：

- 缺参数、非法 digest 和未知参数失败；
- 既有 Release 不覆盖；
- 失败临时目录清理；
- 包内 README 存在或不存在与新蓝图完全一致；
- 外部 README 与仓库唯一源一致；
- `manifest/SHA256SUMS` 与解压后普通文件一致；
- 外部 tar.gz.sha256 与最终 tar.gz 一致；
- 包内无 `__pycache__`、`*.pyc`、tests、examples 和个人路径；
- launcher 参数和退出状态透传；
- `core/trimeg/plot/m3dc1/all` 分层不串扰。

**停止条件**

【推断或建议】如果测试需要伪造业务格式、PUMI 生命周期或求解器消费结果，应停止并
缩回结构边界。

### 10.4 批次 4：Linux 服务器重新构建和直接验证

**前置决策**

【推断或建议】master 修改已提交并生成可追溯源码归档；服务器使用全新源码展开目录和
新的 Release 版本，不覆盖 Prototype 2。

**预计修改文件**

【推断或建议】服务器原则上不修改正式源码；只生成构建目录、Release、日志和验证
产物。

**禁止触碰的业务契约**

【蓝图正式契约】服务器不通过 Git 修改正式源码，不手工修正归档后伪装为构建器输出，
不修改外部只读源码。

**验收证据**

【推断或建议】

1. build-info 中源码 commit 和归档 digest 正确；
2. 干净解压后内部和外部摘要均通过；
3. CPython 3.12.13 和系统 CPython 3.12.3 分别执行适用检查；
4. `core`、`trimeg`、`plot`、`m3dc1`、`all` 输出保存；
5. 真实输入生成 HDF5、TXT、rank-0 SMB 和 PNG；
6. 输出状态只记录到实际达到的层级。

**停止条件**

【推断或建议】出现动态库 `not found`、MPI 路径不明、helper 架构不符、OFT 不是
26.6、摘要不一致、个人路径泄漏或需要手工改 tar.gz 时停止发布。

### 10.5 批次 5：根据同门消费反馈更新证据状态

**前置决策**

【推断或建议】取得可归属到具体 Release 版本、源码 commit、输入和产物摘要的直接
反馈。

**预计修改文件**

【推断或建议】

- `History.md`；
- `LinkMesh_Architecture_Plan.md` 的当前状态表；
- 必要的用户文档；
- 若发现缺陷，再单独授权对应源码或发布脚本修复。

**禁止触碰的业务契约**

【蓝图正式契约】不得把 HDF5 加载结果外推到 M3D-C1，也不得把 SMB 加载或初始化外推
为时间推进、稳定性或物理正确性。

**验收证据**

【推断或建议】分别记录 `LOADED`、`INITIALIZED`、明确时间步、稳定性和物理确认；
失败时保存完整错误、环境和产物身份。

**停止条件**

【推断或建议】若反馈无法对应到明确 Release、输入和文件摘要，只能记录为待核对，
不能更新正式通过状态。

---

## 11. 建议复制到 master 的最小文件或逻辑清单

【推断或建议】不要整体 merge 冻结 Release 分支。应在 master 实时比较后，最小提取：

1. `packaging/release/build_release.sh` 中的参数校验、OFT 精确定位、helper
   ELF/ldd/readelf 审计、临时目录、不覆盖、缓存清理、manifest 和归档框架；
2. `packaging/release/linkmesh-launcher` 的真实路径解析、Python 分级选择、Release
   内 helper 定位和 `exec` 透传；
3. `packaging/release/linkmesh-bootstrap.py` 的 Release site-packages 注入；
4. `packaging/release/linkmesh-check` 的五种分层模式和 TRIMEG/M3D-C1 解耦；
5. `packaging/release/README.md` 中仍符合 master 正式契约的用户环境边界和验证分层，
   但 README 位置及结构说明必须先修订；
6. `native/linkmesh_scorec_helper/CMakeLists.txt` 中 SCOREC 2.2.9 imported targets、
   MPI target 和 C++17 基础构建逻辑；
7. `.gitignore` 中对构建缓存、Release 产物和验证输出的原则性排除规则；
8. 源码 commit、源码归档 digest、helper digest、build-info、内部普通文件 SHA 和
   外部 tar.gz SHA 的分层追溯设计；
9. 最小发布结构回归逻辑，而不是冻结分支的业务测试或历史 passed 数量。

【推断或建议】上述清单中的“原样迁移”只表示逻辑成熟度较高，不表示可以跳过 master
实时 diff、蓝图核对和 Linux 重新验证。

---

## 12. 不应迁移的产物

【推断或建议】以下内容不应复制或提交到 master：

- 已生成的 `linkmesh-release-*` 目录；
- 已生成的 Release tar.gz；
- 某次构建对应的 tar.gz.sha256；
- helper 二进制；
- CMake build 目录、`CMakeCache.txt`、`CMakeFiles`、Makefile 和编译日志；
- `__pycache__`、`*.pyc` 和测试缓存；
- HDF5、TXT、SMB、PNG 和求解器输出；
- 验证临时目录和运行日志；
- Prototype 2 手工解包、删除 README 和重打包步骤；
- 个人绝对路径、个人 Conda 环境路径、上传目录和开发 helper 路径；
- 个人服务器的 `libmpi` 路径或未经批准的 `LD_LIBRARY_PATH`；
- 固定的 helper SHA-256、文件大小或某次 Release 摘要；
- 冻结分支中过期的状态文字；
- TOKAMAKER/OpenFUSIONToolkit 参考源码或其 `src/python` 路径；
- M3DC1、SCOREC/PUMI 外部参考源码；
- 未经确认的共享根目录、modulefile 或组权限配置；
- 任何为整体合并冻结 Release 分支而产生的兼容层。

【实时源码事实】`.gitignore` 已覆盖多类构建和运行产物，但外部交付 tar.gz 和
tar.gz.sha256 是否被所有命名模式覆盖需在 master 单独核对，不能仅凭当前规则假定。

---

## 13. 风险、未知事项与停止条件

### 13.1 主要风险

| 风险 | 证据与影响 | 处理建议 |
|---|---|---|
| README 规则三方不一致 | 【当前对话直接事实】外部-only；【蓝图正式契约】包内；【实时源码事实】构建器复制包内 | 先改蓝图和文档，再改构建器 |
| 内部 manifest 与手工归档修正失配 | 【实时源码事实】README 当前进入内部 SHA；手工删除可能留下过期记录 | 最终内容确定后再生成 manifest |
| 外部 tar.gz.sha256 过期 | 【当前对话直接事实】归档内容曾手工变化 | tar.gz 最终生成后自动计算并干净验证 |
| single-region 示例使用错误尺度 | 【当前对话直接事实】必须使用 `mesh_dx` | 全面检查 Release 用户文档和示例 |
| 构建证据被误写成消费通过 | 【蓝图正式契约】验证必须分层 | 报告中保存状态层级和直接日志 |
| helper 跨服务器 ABI 不兼容 | 【蓝图正式契约】MPI/glibc/libstdc++ 仍需验证 | 每个目标环境执行 file/readelf/ldd 和真实 SMB |
| master 与冻结分支漂移 | 【当前对话直接事实】不整体合并 | 按逻辑逐项移植并实时审查 |
| README 同时承担两类受众 | 【实时源码事实】当前内容包含构建和最终用户说明 | 确认单一源及受众边界，不维护多份正文 |

### 13.2 未知事项

【推断或建议】以下保持 E 类：

- master 是否已有新的 packaging 文件或发布测试；
- master 当前 helper 是否仍使用同名、同路径和同一环境变量；
- 外部 README 的最终目录层与命名；
- 是否由同一个构建命令生成外部 README 和 tar.gz.sha256；
- 是否正式增加 CMake install；
- 共享部署根目录、modulefile、组权限；
- 正式 MPI 来源和跨主机 ABI 策略；
- 同门对 Prototype 2 HDF5 和 SMB 的最终消费结果。

### 13.3 全局停止条件

【推断或建议】master 实施遇到以下任一情况应停止：

1. 需要改变正式 Release 结构但蓝图未先更新；
2. master 的 helper 名称、OFT 版本、入口或包布局与冻结分支无法无歧义映射；
3. 需要修改业务源码才能完成纯发布迁移；
4. 只能依赖个人路径、`PYTHONPATH`、开发 helper 或开发构建目录；
5. 需要把 TOKAMAKER/OpenFUSIONToolkit `src/python` 当作运行时来源；
6. 需要固定未经确认的 MPI 路径、共享根目录或 modulefile；
7. 内部 manifest、外部摘要或归档内容不一致；
8. 仍需发布后手工修改 tar.gz；
9. 静态检查、构建成功或文件生成被要求写成外部消费通过；
10. 反馈缺少具体 Release、源码 commit、输入和产物身份。

---

## 14. 结论

【实时源码事实】冻结 Release 分支已经形成一套结构完整的发布基础设施：Linux 离线
组装、临时工作目录、不覆盖、OFT 26.6 和 helper 组装、自定位 launcher、Python
bootstrap、Release 内 helper 定位、分层检查、native 审计、manifest 和内部摘要。

【当前对话直接事实】Prototype 2 已证明该基础设施能够在 Linux x86-64 上使用
CPython 3.12.13 和系统 CPython 3.12.3 完成检查并生成 TRIMEG HDF5、M3D-C1
TXT、rank-0 SMB 和 PNG；最新外部消费结果仍待同门反馈。

【推断或建议】A 类通用能力应作为 master 的主要迁移对象；B 类能力应结合 master
当前结构修订后迁移；C 类 README 和归档结构规则必须先经 User 确认并更新蓝图；D 类
手工重打包、个人路径和生成产物不应迁移；E 类共享部署、MPI/ABI 策略、CMake install
和外部消费状态需继续调查。

【当前对话直接事实】已发现的核心冲突是：Prototype 2 最新交付要求 README 仅位于
tar.gz 外部，而当前蓝图、构建器和发布说明仍定义包内 README。该冲突只能在 master
通过蓝图先行流程解决，不能在冻结分支中静默修正。

【推断或建议】master 首批应处理
`LinkMesh_Architecture_Plan.md`、`Project_Tree.md`、
`packaging/release/README.md` 和相关用户示例；完成结构契约后，再处理
`build_release.sh`、launcher、bootstrap、检查器、manifest 和最小结构回归。

【实时源码事实】本次唯一新增内容是
`docs/linkmesh/release_infrastructure_investigation_report.md`。未修改任何发布基础
设施、native helper、业务源码、蓝图、History、Project Tree、测试、示例、依赖或
外部参考源码，也未执行构建、测试、OFT、TRIMEG、M3D-C1、SCOREC/PUMI 或服务器命令。
