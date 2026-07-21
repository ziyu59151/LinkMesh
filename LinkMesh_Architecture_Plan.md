# LinkMesh_Architecture_Plan.md
# LinkMesh 独立命令行网格转换工具 —— 唯一技术蓝图（单事实真理源）

- 文档主受众：Aider-facing
- 知识库用途：参考架构
- 文档状态：正式版 v1.11（依据 TRIMEG MATLAB 消费函数 `loadfemmesh_h5.m` 与两个真实 HDF5 样例 femmesh_65402_t1_nr16core.h5 / femmesh_65402_t1_nr16nout4edge.h5 修订 M3 TRIMEG HDF5 正式契约：撤销旧转置/第四列/11 数据集全必需表述；固化 8 个核心数据集磁盘 shape/dtype/1-based 索引与拓扑外边界节点分类规则，明确 3 个可选边界数据集事实边界；新增独立轻量网格模型模块 `src/linkmesh/mesh.py` 计划并规定先完成 Mesh2D 解耦、再实施 HDF5 Writer 的两阶段顺序；M3 仍未通过、M4 仍禁止开始；不改动 M1/M2 已验收行为与 M4 未确认 .smb 契约）
- 最高依据：本文档自身即为 LinkMesh 项目的最高技术依据；开发纪律与协作规范见 CONTEXT.md
- 事实边界：本文档是 LinkMesh 项目唯一的技术蓝图单事实源（Single Source of Truth）。凡涉及目录职责、模块接口、数据结构、第三方库调用规范、输出文件格式（HDF5 / PUMI .smb）以及 MVP 阶段验收标准，均以本文档为最终裁决依据。本文档中标注【已确认事实】的内容为当前可执行的工程事实；标注【待源码确认】的内容为基于白皮书推断、需后续只读侦察验证的事项；标注【待运行验证】的内容为需要在真实 OFT 环境中实际运行后方可确认的事项；标注【计划新增】的内容为蓝图已批准、但尚未在仓库中创建的文件或目录；标注【P0 禁止】的内容为当前 MVP 阶段严格禁止引入的功能。
- 主要用途：本文档为 LinkMesh 项目的单事实真理源（Single Source of Truth），不作为人类泛读材料，专门用于指导 Aider 自动化编码、RAG 知识库精准检索以及下游模块的硬核参数对齐。凡 Aider 在执行编码、新建文件、修改具体业务代码前，必须查阅并严格对齐本文档。
- 场外架构师检索用途：当场外架构师需要判断 LinkMesh 某模块的职责边界、某数据结构的字段定义、某输出格式的对齐标准，或某开发阶段的验收条件时，应优先召回本文档。
- Aider 执行用途：Aider 必须以本文档为最高技术权威。编写任何 `.py` 业务源码前，必须先核对本文档对应章节的接口定义、数据结构字段和验收标准。如发现实际需求与本文档不符，必须先在对话中提出蓝图迭代建议，待主管确认并更新本文档后，方可动手编写代码。
- 修改前置条件：任何对本文档的修改，必须由人类主管在对话中明确确认后方可执行。Aider 严禁自发修改本文档中的接口定义、数据结构、验收标准或禁止事项。

### 修订记录

| 版本 | 修订摘要 |
|---|---|
| v1.5 | M1 验收写入；M2 契约校正（reshape(-1) 替代 squeeze()；mock 目标修正） |
| v1.6 | 批准含第一壁 DIII-D P0 默认三区域简化方案（region_id=1/2/3）；明确无可用壁轮廓降级两区域方案（region_id=1/2）；建立轻量的按表区域传递契约（Wrapper/Writer 不写死区域数）；补充区域种子几何条件与失败原则；记录 M2 自动测试 36/36 通过但真实 region_id=0 阻塞 M2 总体验收；保留 M4 Multi Region 侦察空间 |
| v1.7 | 优先复用 OFT 完成 M1 读取、M2 区域/网格生成和可选静态中间输出；LinkMesh 最小化为输入编排、统一对象适配、目标格式翻译和 CLI；两区域/三区域改为 OFT Multi Region 的特殊验收实例，删除 LinkMesh 固定区域编号和固定区域数量的全局表述；根据 `loadfemmesh_h5.m` 修正 TRIMEG HDF5 直接消费契约（明确 boundary_segments/boundary_markers/node_markers 非 TRIMEG 直接消费字段，/femmesh/tria 第四列含义标注为待真实样例核对）；Mesh2D 重新定义为轻量统一网格对象，boundary_segments/boundary_markers/node_markers 降级为可选内部/适配字段；增加 M2-0 OFT 可行性验证里程碑；明确不修改、不维护 OFT 分支；保留 M4 对 M3DC1 特有要求的 LinkMesh 侧适配空间 |
| v1.8 | 固化 M2-0 OFT 环境、合成两/三区域和真实 DIII-D 通过证据（Linux x86_64 / Python 3.12.13 / OpenFUSIONToolkit 26.6 正式 Conda 环境）；新增正式 `mesher/oft_adapter.py` 模块作为 M2 正式网格生成适配层；将 Python Triangle Wrapper 降级为历史/过渡路径（不再作为 M2 正式主路径）；明确轻量 Mesh2D 核心三数组（nodes/triangles/region_ids）；明确 OFT 区域编号原样保存与元数据从 domain.region_info 获取的规则；约束 LinkMesh 不复制 OFT 通用几何算法；授权进入 M2 Adapter 实现，但不表述为 M2/M3/M4 已通过 |
| v1.9 | 明确单区域 plasma-only 是合法计算域选择及其物理适用边界；明确不存在 LinkMesh/OFT 网格层面“至少两个区域”的全局要求；明确两/三区域只是 OFT Multi Region 代表性验收样例，不是 Adapter 能力边界；建立 OFT Adapter 三层接口（`mesh_from_oft_domain()` 通用 N 区域核心、`build_oft_domain_from_gfile()` 当前 GFile 默认策略层、`generate_mesh()` CLI 便利入口）；`mesh_from_oft_domain()` 对任意正区域数量 N 通用（含 N=1），只按 `domain.region_info` 校验区域集合，不写死区域数量/名称/类型/整数 ID；补充单区域、N>3 及区域缺失/多余/非法编号失败的测试规划；明确 TRIMEG/M3DC1 单区域支持仍为待更多直接证据/待源码确认事项，不得由两/三区域实例外推最小区域数量；保持 CLI 默认 GFile 策略、Mesh2D 核心三数组、M3/M4 字段契约不变；不新增 CLI 参数；旧 Triangle 路径继续历史/过渡状态 |
| v1.10 | M2 OFT Adapter 正式验收通过（M2 总体 PASSED）：固化真实 DIII-D 972 节点 / 1872 三角形 / 3 区域网格与数值质量证据（0-based 索引 0..971、区域统计 {1:633,2:678,3:561}、区域元数据 PLASMA/OUTER/VACUUM、最小内角 20.222°、退化三角形 0）；固化 mock 测试 `tests/test_oft_adapter.py` 退出码 0（未记录测试总数与耗时）；固化区域着色 PNG 人工几何与区域位置检查通过；将 OFT `Repeated points`/`Sliver`/`Small feature` 几何警告记录为当前非阻塞项（未修复、不新增几何修补算法）；明确下一步进入 M3 TRIMEG HDF5 契约核对（M3 尚未开始正式验收）；新增旧 Python Triangle 路径暂留原因与后续减量顺序（本轮不删除源码）；未修改 M3 HDF5 字段契约与 M4 边界 |
| v1.11 | 依据 TRIMEG MATLAB 消费函数 `loadfemmesh_h5.m` 与两个真实 HDF5 样例（femmesh_65402_t1_nr16core.h5 / femmesh_65402_t1_nr16nout4edge.h5，User 在 Linux 服务器以 h5py+NumPy+拓扑检查脚本只读回读、退出码 0）修正 M3 TRIMEG HDF5 正式契约：**撤销**旧 `vert=(2,N)`、`tria=(4,T)`、Python Writer 对 vert/tria 转置、tria 第四列写 region_id、11 数据集全必需等被真实样例否定的表述；固化磁盘契约 `vert=(N,2) float64`、`tria=(T,3) float64` 且为 1-based、无第四列、不写 region_ids；将 4 个计数标量固化为 shape `(1,1) float64`；`idxivert/idxevert` 固化为 shape `(1,nvert_in)/(1,nvert_ex)` float64、1-based；`idxevert` 定义为**拓扑外边界节点**（无向边只出现一次）的升序 1-based 集合，`idxivert` 为其在 `{1..N}` 中的升序补集，不再由 LCFS/第一壁/OFT region/文件名/node_markers 推断；将数据集重新组织为 8 核心 + 3 可选，明确 `nbcRZ/Rbc/Zbc` 事实边界（不得规定 nbcRZ==nvert_ex、不得规定 Rbc/Zbc 覆盖全部 idxevert、不得规定相邻点为拓扑边、不得声称仅凭 Mesh2D 可唯一重建历史 Rbc/Zbc），M3 第一阶段 Writer 默认不写这 3 项；新增独立轻量网格模型模块 `src/linkmesh/mesh.py` 计划，将 `Mesh2D` 从历史 `triangle_wrapper.py` 迁出并规定唯一定义与重导出兼容；规定实施顺序铁律：先完成 Mesh2D 解耦并通过 M2 回归，再实施 HDF5 Writer；M3 仍未通过、M4 仍禁止开始；不改动 M1/M2 已验收行为与 M4 未确认 .smb 契约 |

---

## 0. LinkMesh 项目定位与 MVP P0 边界

### 0.1 项目定位

LinkMesh 是一个**独立命令行程序（CLI）**，专注于打通从**等离子体平衡文件（GFile/EQDSK）**提取边界，到基于**OFT（OpenFUSIONToolkit）已有模块**完成区域组织、边界处理、区域种子和网格生成，再将统一内存网格对象顺次翻译输出为**两大目标物理求解器静态网格文件**的完整工具链路。

**【v1.7 架构决定】LinkMesh 的优先开发路线**：尽量直接调用 OFT 已有模块完成 GFile/EQDSK 读取、区域组织、边界处理、区域种子、网格生成和可选中间静态网格输出；LinkMesh 只负责最小输入编排、必要字段翻译、目标格式输出和 CLI 编排。

**【P0 禁止】** 不得复制 OFT 已实现的通用网格拓扑、区域管理、边界重采样、点合并或 Triangle 调用逻辑。不得修改、补丁化、重新编译或维护新的 OFT 分支。

**关于历史实验代码**：当前 LinkMesh 自有 Triangle/几何代码（`triangle_wrapper.py` 中的 `BoundaryConfig`、`_build_boundary_config()` 等）视为历史实验或过渡候选，不再作为必须保留的正式架构核心。M2 正式路径已由 OFT `gs_Domain` 路线（`mesher/oft_adapter.py`）替代。

**【v1.9 通用性原则】** 两区域和三区域只是 OFT Multi Region 的代表性验收样例，**不是 `oft_adapter.py` 的能力边界**。正式 Adapter 必须对任意正区域数量 N 通用，包括 N=1。LinkMesh 不重新设计一套任意 N 区域配置系统；OFT `gs_Domain` 本身即作为 N 区域定义接口。当前 CLI 仍可使用 GFile 默认区域模型，本轮不新增任意区域配置 CLI 参数。

**正式目标数据流（v1.8，v1.11 保持）**：

```text
GFile/EQDSK
  → OFT GEQDSKEquilibrium（M1，已通过）
  → GFileData（LinkMesh 薄字段适配器）
  → mesher/oft_adapter.py（M2 正式网格生成适配层，已通过）
      → OFT gs_Domain / define_region / add_polygon / add_annulus / add_rectangle / add_enclosed / build_mesh
      → OFT Mesh / liboft_triangle
  → OFT 网格结果（pts, lc, reg）
  → LinkMesh 最小适配（轻量 Mesh2D 统一对象，正式定义位于 src/linkmesh/mesh.py，计划新增）
  → TRIMEG HDF5（M3）/ M3DC1 .smb（M4）
```

**M2 正式核心数据流（v1.8，v1.11 保持）**：

```text
GFileData → oft_adapter → OFT gs_Domain/Mesh/build_mesh → pts/lc/reg → 轻量 Mesh2D
```

**完整项目数据流（v1.8，v1.11 保持）**：

```text
GFile/EQDSK → OFT GEQDSKEquilibrium → GFileData → OFT Adapter → Mesh2D → TRIMEG HDF5 / M3DC1 .smb
```

**关于 OFT 网格后端**：OFT 当前 `run_triangle()` 通过 `ctypes` 调用 OFT 自己的 `liboft_triangle`（见 `meshing.py` 中 `oft_triangulate`），LinkMesh 不需要直接维护该底层实现。LinkMesh 通过调用 OFT 公开接口（`gs_Domain.build_mesh()`）获得网格结果，不直接操作 `liboft_triangle`。

**关于 OFT 适配验证**：不得把"调用 OFT 一定无需任何适配"写成已确认事实。LinkMesh 仍需验证 OFT 输出与目标文件契约之间的字段映射。如当前 OFT 公开接口无法满足某个目标字段，记录为适配验证项；在未确认前不得伪造字段或静默填充。

### 0.2 MVP P0 硬边界（铁律，不得突破）

| 维度 | P0 允许 | P0 禁止 |
|---|---|---|
| 输入端 | 通过 OFT `GEQDSKEquilibrium` 读取 EQDSK/GFile 平衡文件；解析类 Simmetrix `input` 文本配置 | **在 LinkMesh 侧手动执行复杂文本 I/O 与字符串切分解析 GFile**；复杂 CAD 输入；多区域高维输入 |
| 网格生成底座 | **优先调用 OFT `gs_Domain` / `build_mesh()`（经 `mesher/oft_adapter.py`）**；OFT 内部通过 `liboft_triangle` 完成 Triangle 调用 | 复制 OFT 已实现的通用网格拓扑、区域管理、边界重采样、点合并逻辑；引入任何第二种网格生成引擎；三维棱柱/四面体生成；自适应网格细化算法；修改或维护 OFT 分支 |
| 并行切分 | 不涉及 | 将静态网格切分为 `**1.smb`~`**16.smb` 的多区并行分解 |
| 输出端 | TRIMEG 标准 HDF5 静态格式；M3DC1 消费的 PUMI `.smb` 静态二进制网格文件（M4 阶段） | 三维网格输出；其他求解器格式 |
| 可视化 | 基于 `matplotlib` 的简易画图自检 | 交互式可视化；三维渲染 |
| OFT 治理 | 调用 OFT 已提供的公开接口 | 修改 OFT 源码；修改 Conda 安装目录；维护 OFT fork；把 OFT 私有字段固化为长期公共 API |

### 0.3 OFT 已确认能力（来自只读源码侦察与 M2-0 / M2 运行验证）

【已确认事实】以下 OFT 能力已通过只读侦察 `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py` 确认，并已在 M2-0 与 M2 正式验收中通过正式 Conda 环境运行验证（见第 13 节 M2-0 与 M2）：

| OFT 接口 | 能力描述 |
|---|---|
| `gs_Domain` | 支持多个命名区域和区域类型，包括 plasma、vacuum、boundary、conductor、coil |
| `define_region(name, dx, reg_type, ...)` | 定义命名区域及其属性（类型、分辨率、电阻率、匝数等） |
| `add_polygon(contour, name, parent_name, ...)` | 添加多边形几何，定义区域边界 |
| `add_annulus(inner_contour, inner_name, outer_contour, annulus_name, ...)` | 添加环形几何，定义嵌套区域边界 |
| `add_rectangle(rc, zc, w, h, name, parent_name, ...)` | 添加矩形几何 |
| `add_enclosed(in_point, name)` | 添加区域内部种子点 |
| `build_mesh(debug, merge_thresh, require_boundary, setup_only, cubit_path, ...)` | 执行网格生成，返回 `(pts[np,2], lc[nc,3], reg[nc])` |
| `Mesh` | 已实现区域边界组织、点合并、共享边界处理、边界重采样、区域定义和 Triangle 输入构造 |
| `Region` | OFT 区域对象；提供区域名称、类型和最终 ID 等元数据 |
| `run_triangle` | OFT Triangle 调用封装（内部通过 `liboft_triangle.so`） |
| `get_coils()` | 获取线圈区域字典 |
| `get_conductors()` | 获取导体区域字典 |
| `save_gs_mesh()` / `load_gs_mesh()` | 可选静态中间网格文件保存/加载（OFT 自有格式，**不是 TRIMEG HDF5 格式，也不是 M3DC1 `.smb` 格式**） |

【已确认事实】`build_mesh()` 最终返回：
- `pts`：节点坐标数组，shape `(np, 2)`，dtype `float64`
- `lc`：三角形连接表，shape `(nc, 3)`，整数 dtype（M2-0 / M2 实测为 `int32`），**0-based 索引**
- `reg`：三角形区域编号数组，shape `(nc,)`，整数 dtype（M2-0 / M2 实测为 `int32`）

【已确认事实，M2-0 与 M2 运行验证】OFT 26.6 在 M2-0 与 M2 真实运行中：
- `lc` 返回合法 **0-based** 连接表，索引范围为 `0..N-1`；Adapter 应验证 `0 <= lc < N`，无需无依据地再次偏置。
- `reg` 返回的区域编号为正整数，与 `gs_Domain.region_info` 中定义区域的最终 ID 一一对应。非正区域编号（如 0）表示未认领或非法区域，不是"无物理方程"的合法标签。

---

## 1. MVP 物理目录树与职责矩阵

### 1.1 当前仓库与本阶段目标目录结构

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。以下目录树区分了当前已存在的文件与蓝图批准但尚待实施的计划项。

```text
LinkMesh/
├── pyproject.toml                     # 【计划新增】标准 Python 包安装元数据与控制台入口（见第 15 节）
├── CONTEXT.md                         # 敏捷开发纪律规范（只读）
├── LinkMesh_Architecture_Plan.md      # 本文档（单事实真理源）
├── History.md                         # 战术战果归档
├── requirements.txt                   # 服务器部署用直接依赖清单（见第 15.4 节）
├── .venv/                             # 独立虚拟环境（不入版本控制）
│
├── src/
│   └── linkmesh/                      # 正式 Python 包根目录
│       ├── __init__.py
│       ├── __main__.py                # 已新建（git: 1fc04f8）：python -m linkmesh 入口（仅调用 cli.main）
│       ├── cli.py                     # CLI 参数解析与主流程控制（已接入 OFT Adapter generate_mesh）
│       ├── mesh.py                    # 【计划新增，v1.11 批准】独立轻量统一内存网格模型模块：
│       │                              # 只定义 Mesh2D（与网格后端无关）；
│       │                              # 不依赖 OFT / Python Triangle / HDF5 / PUMI / CLI / Plotter；
│       │                              # Mesh2D 迁出后此处为唯一正式定义（见第 2.2 节与第 16.1 节）
│       │
│       ├── readers/
│       │   ├── __init__.py
│       │   └── gfile_reader.py        # GFile/EQDSK 读取 Adapter：薄封装 OFT GEQDSKEquilibrium
│       │
│       ├── mesher/
│       │   ├── __init__.py
│       │   ├── oft_adapter.py         # 【已实现，M2 正式主路径，M2 PASSED】OFT gs_Domain 网格生成适配层：
│       │   │                          # 三层接口 mesh_from_oft_domain / build_oft_domain_from_gfile / generate_mesh；
│       │   │                          # mesh_from_oft_domain 对任意正区域数量 N 通用（含 N=1）；
│       │   │                          # 将 pts/lc/reg 规范化为轻量 Mesh2D；不复制 OFT 通用几何算法；
│       │   │                          # 解耦后从 linkmesh.mesh 导入 Mesh2D（见第 16.1 节）
│       │   └── triangle_wrapper.py    # 【历史/过渡实现，非 M2 正式主路径】Python triangle 包底座封装；
│       │                              # 已被 oft_adapter.py 替代为正式路线；
│       │                              # 解耦后不再定义第二份 Mesh2D，而从 linkmesh.mesh 重导出同一类；
│       │                              # 仍承载 BoundaryConfig 定义，暂不删除（见第 16.1 节）；
│       │                              # 禁止继续扩展其区域拓扑与通用几何能力
│       │
│       ├── writers/
│       │   ├── __init__.py
│       │   ├── hdf5_writer.py         # 第一战役：TRIMEG HDF5 静态网格写出器（v1.11 契约见第 4.1 与第 9 节）
│       │   └── smb_writer.py          # 第二战役占位：M3 验收后按侦察结果实现
│       │
│       └── utils/
│           ├── __init__.py
│           └── plotter.py             # matplotlib 可视化自检工具（已支持区域着色与 LCFS 闭合显示）
│
├── docs/
│   └── trimeg/
│       ├── loadfemmesh_h5.m                       # TRIMEG MATLAB 消费函数（只读黄金标尺）
│       ├── femmesh_65402_t1_nr16core.h5           # 真实 TRIMEG HDF5 样例 A（core，只读证据）
│       └── femmesh_65402_t1_nr16nout4edge.h5      # 真实 TRIMEG HDF5 样例 B（edge，只读证据）
│
├── tests/                             # 单元测试目录（M1～M3 验收测试）
│   ├── test_gfile_reader.py           # M1 验收测试（已通过，git: f52a75f）
│   ├── test_triangle_wrapper.py       # 【历史/过渡测试】Python triangle 路线自动测试 36/36 通过；
│   │                                  # 作为历史证据保留；不能作为 OFT Adapter 正式验收的替代；
│   │                                  # 当前保持文件不动，暂不删除、不扩展
│   ├── test_oft_adapter.py            # 【已实现，M2 正式验收测试，mock 退出码 0】OFT Adapter 专用测试；
│   │                                  # 覆盖单区域/两区域/三区域/N>3；区域缺失/多余/非法编号失败；
│   │                                  # 分别验证 mesh_from_oft_domain / build_oft_domain_from_gfile / generate_mesh 三层
│   └── test_hdf5_writer.py            # 【计划重写，M3】按 v1.11 新契约验收（8 核心 + 3 可选默认不写）
│
└── examples/                          # 【计划新增】示例文件目录
    ├── sample.geqdsk                  # 【计划新增，待许可确认】示例 GFile 平衡文件
    └── run_example.sh                 # 【计划新增】示例运行脚本
```

**注意**：
- `examples/` 目录当前尚不存在，其中的 `sample.geqdsk` 来源和许可证待确认（见第 14.2 节）。
- `pyproject.toml` 当前尚不存在，待主管批准后创建（见第 15.1 节）。
- `src/linkmesh/mesh.py` 为 v1.11 批准的计划新增文件，尚未创建；创建与迁移属于下一轮独立解耦任务（见第 16.1 节）。
- `mesher/oft_adapter.py` 已实现并通过 M2 正式验收（见第 7 节与第 13 节 M2）。
- `tests/test_oft_adapter.py` 已实现，mock 契约测试退出码 0（见第 13 节 M2 与第 14.1 节）。
- 本轮不新增 `tests/test_smb_writer.py`，M4 开始前不创建该文件。
- `mesher/triangle_wrapper.py` 与 `tests/test_triangle_wrapper.py` 保留为历史/过渡实现，暂不删除、不扩展；`BoundaryConfig` 定义当前仍位于 `triangle_wrapper.py`；`Mesh2D` 迁出后 `triangle_wrapper.py` 从 `linkmesh.mesh` 重导出，删除前置条件与减量顺序见第 16.1 节。
- `docs/trimeg/` 下的 `.m` 与两个 `.h5` 为 M3 契约的直接只读证据，严禁修改。

### 1.2 模块职责矩阵

| 模块文件 | 核心职责 | 输入 | 输出 | 禁止事项 |
|---|---|---|---|---|
| `src/linkmesh/__main__.py` | `python -m linkmesh` 入口：仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑 | `sys.argv`（透传） | 无（副作用：调用 `cli.main`） | 不得包含任何业务逻辑；不得直接操作文件；不得重复定义参数解析 |
| `src/linkmesh/cli.py` | 解析命令行参数；调用 reader → `mesher/oft_adapter.py`（M2 正式路径，经 `generate_mesh()` 便利入口）→ writer；捕获异常并打印友好错误信息 | `sys.argv` | 无（副作用：调用各模块） | 不得包含任何业务逻辑（除历史过渡 `_build_boundary_config`）；不得直接操作文件；**不得在 CLI 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换**；不得复制 OFT 通用几何逻辑；本轮不新增任意区域配置 CLI 参数 |
| `src/linkmesh/mesh.py` | **【计划新增，v1.11】** 独立轻量统一内存网格模型模块：只定义 `Mesh2D`（与网格后端无关）；提供只读统计属性（`n_nodes`/`n_triangles`/`n_boundary_segments`）；非核心兼容字段使用 `dataclasses.field(default_factory=...)` 提供安全空数组默认值 | 无（纯数据结构模块） | `Mesh2D` 类定义 | **不得依赖 OFT / Python Triangle / HDF5 / PUMI / CLI / Plotter**；不得加入网格生成、边界恢复、HDF5 翻译或通用后端抽象；不得共享可变 NumPy 默认数组 |
| `src/linkmesh/readers/gfile_reader.py` | **薄 Adapter（接线员）**：调用 OFT `GEQDSKEquilibrium` 读取 GFile，从返回对象属性中提取 LCFS 边界坐标、磁轴坐标、第一壁点集等，封装为 `GFileData` 对象 | GFile 文件路径（`str`） | `GFileData` dataclass | **绝对禁止**在 LinkMesh 侧手动执行任何原始 GFile 文本 I/O 与字符串切分；不得调用 Triangle；不得写文件 |
| `src/linkmesh/mesher/oft_adapter.py` | **【M2 正式网格生成适配层，三层接口，M2 PASSED】** `mesh_from_oft_domain(domain)` 通用 N 区域核心：调用已构造 `gs_Domain` 的 `build_mesh()`，将 `pts/lc/reg` 规范化为 `Mesh2D`，只按 `domain.region_info` 校验区域集合，对任意正区域数量 N 通用（含 N=1）；`build_oft_domain_from_gfile(gfile_data, ...)` 当前 GFile 默认策略层：按批准策略构造 `gs_Domain`，不调用 `build_mesh()`；`generate_mesh(gfile_data, ...)` CLI 便利入口：组合前两者 | `GFileData` 对象 / 已构造 `gs_Domain` / 网格尺度参数 | `Mesh2D` 对象（`mesh_from_oft_domain`、`generate_mesh`）；`gs_Domain` 对象（`build_oft_domain_from_gfile`） | **不得复制 OFT 通用几何、区域拓扑、种子搜索、重采样或 Triangle 调用算法**；不得修改 OFT 源码/安装目录/fork；不得依赖 `TOKAMAKER/` 快照作为运行时包；**不得写死区域数量/名称/类型/最终整数 ID**；不得根据整数编号推断区域物理语义；不得对合法 0-based 连接表无依据地再次偏置；`mesh_from_oft_domain` 不得理解或推断 plasma/vacuum/outer 语义；`build_oft_domain_from_gfile` 不得调用 `build_mesh()` 或转换 `pts/lc/reg`；`generate_mesh` 不得包含第二套网格验证或区域算法；**解耦后从 `linkmesh.mesh` 导入 `Mesh2D`，不得从 `triangle_wrapper.py` 获取** |
| `src/linkmesh/mesher/triangle_wrapper.py` | 【历史/过渡实现，非 M2 正式主路径】原 Python triangle 包底座封装；已被 `oft_adapter.py` 替代；仍承载 `BoundaryConfig` 定义；解耦后从 `linkmesh.mesh` 重导出 `Mesh2D`（`from linkmesh.mesh import Mesh2D`），不再定义第二份同名类 | `BoundaryConfig` 对象 | `Mesh2D` 对象 | 不得读取 GFile；不得写文件；不得引入三维网格逻辑；不得引入第二种生成引擎；**不得写死区域数量**；不得推断区域物理含义；**禁止为保存旧实现继续扩展其区域拓扑与通用几何能力**；**禁止在此重新定义第二份 `Mesh2D`** |
| `src/linkmesh/writers/hdf5_writer.py` | **第一战役**：接收 `Mesh2D` 对象；严格对照 `docs/trimeg/loadfemmesh_h5.m` 与两个真实样例，按 v1.11 TRIMEG HDF5 契约写出 `.h5` 文件（8 核心数据集；默认不写 3 可选） | `Mesh2D` 对象，输出路径 | `.h5` 文件（副作用） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；**不得写 `region_ids` 到 HDF5**；**不得对 vert/tria 转置**；**不得写 tria 第四列**；不得推断区域物理含义；不得访问旧 `boundary_segments`/`boundary_markers`/`node_markers`；解耦后从 `linkmesh.mesh` 导入 `Mesh2D`（仅运行时类型需要，否则 `TYPE_CHECKING`） |
| `src/linkmesh/writers/smb_writer.py` | **第二战役占位模块**：在 M3 完整验收及 SCOREC/PUMI/M3DC1 只读侦察完成后，按主管确认的实现路线将 `Mesh2D` 转换为 M3DC1 可消费的 `.smb`；当前不得锁定具体序列化方式；保持 `NotImplementedError` 占位 | `Mesh2D` 对象，输出路径 | `.smb` 文件（副作用，M4 实现后） | 不得修改 `Mesh2D` 对象；不得包含网格生成逻辑；M3 验收前不得实现任何字节流逻辑；解耦后从 `linkmesh.mesh` 导入 `Mesh2D` |
| `src/linkmesh/utils/plotter.py` | 绘制 LCFS 边界与生成三角网格的叠加图；输出 `.png` 自检图；提供 `plot_lcfs_only()`（M1 最小可用版）和 `plot_mesh()`（M2 完整版，支持区域着色与 LCFS 闭合显示）两个函数 | `GFileData`，`Mesh2D`，输出路径 | `.png` 文件（副作用） | 不得修改任何数据对象；解耦后从 `linkmesh.mesh` 导入 `Mesh2D` |

---

## 2. 核心内存数据结构定义

### 2.1 `GFileData`：GFile 读取结果（OFT Adapter 输出）

【已确认事实】`GFileData` 是 `src/linkmesh/readers/gfile_reader.py` 这个薄 Adapter 的输出对象。其字段值**全部来自对 OFT `GEQDSKEquilibrium` 对象属性的直接提取**，LinkMesh 侧不执行任何原始文本解析。

相比旧草案，`GFileData` 已大幅精简，移除了 `nw`、`nh`、`rdim`、`zdim`、`rleft`、`zmid`、`simag`、`sibry`、`psi_grid`、`r_grid`、`z_grid`、`fpol`、`pres`、`qpsi` 等 14 个字段——这些字段由 OFT 内部管理，LinkMesh 无需重复存储。

【已确认事实】`current` 字段单位为安培（A），来源为 OFT `GEQDSKEquilibrium.Ip`，后者直接读取 EQDSK 文件中的 `CURRENT` 字段，全程不进行任何单位缩放。以 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 为例，服务器冒烟测试实测值为约 `1.56e7 A`（即约 15.6 MA），Python 类型为 `float`。以 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 为例，M1 正式验收实测值为 `493324.5 A`（约 0.49 MA），Python 类型为 `float`。

**关于 `wall_r` / `wall_z` 字段的物理含义说明**：

`GFileData.wall_r` 和 `wall_z` 为可选字段，表示输入 GFile 是否提供了可供 LinkMesh 使用的 limiter/第一壁二维轮廓。字段为 `None` 或空数组只表示"输入文件未提供可用壁轮廓"，**不表示物理装置不存在第一壁**。LinkMesh 不得在缺少壁几何时凭空推断真实壁形状。

```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class GFileData:
    """GFile/EQDSK 平衡文件读取结果（OFT Adapter 输出）。

    所有字段均由 src/linkmesh/readers/gfile_reader.py 从 OFT GEQDSKEquilibrium 对象属性
    中直接提取，LinkMesh 侧不执行任何原始文本解析。

    所有坐标单位均为米（SI 单位制）。
    R 为大半径方向，Z 为垂直方向（托卡马克柱坐标系）。

    字段来源（对应 GEQDSKEquilibrium 属性名，来自 eqdsk.py 只读侦察）：
        lcfs_r   ← eq.boundary_R   (eqdsk.py 属性 boundary_R)
        lcfs_z   ← eq.boundary_Z   (eqdsk.py 属性 boundary_Z)
        rmaxis   ← eq.R_mag        (eqdsk.py 属性 R_mag)
        zmaxis   ← eq.Z_mag        (eqdsk.py 属性 Z_mag)
        wall_r   ← eq.limiter_R    (eqdsk.py 属性 limiter_R)，若为空则 None
        wall_z   ← eq.limiter_Z    (eqdsk.py 属性 limiter_Z)，若为空则 None
        rcentr   ← eq.R_center     (eqdsk.py 属性 R_center)
        bcentr   ← eq.B_center     (eqdsk.py 属性 B_center)
        current  ← eq.Ip           (eqdsk.py 属性 Ip)，单位 A，不缩放
    """

    # LCFS 边界坐标（最后闭合磁面，plasma-vacuum interface）
    lcfs_r: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 R 坐标 [m]
    lcfs_z: np.ndarray               # shape=(N_lcfs,)，LCFS 上各点 Z 坐标 [m]

    # 磁轴坐标
    rmaxis: float                    # 磁轴 R 坐标 [m]
    zmaxis: float                    # 磁轴 Z 坐标 [m]

    # 第一壁/limiter 点集（可选）
    # 若 GFile 提供了可用壁轮廓则为数组，否则为 None
    # 字段为 None 只表示"输入文件未提供可用壁轮廓"，不表示物理装置不存在第一壁
    wall_r: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 R 坐标 [m]
    wall_z: Optional[np.ndarray]     # shape=(N_wall,)，第一壁 Z 坐标 [m]

    # 基本平衡参数（可选，用于后续物理验证与可视化）
    rcentr: Optional[float] = None   # 参考大半径 R0 [m]
    bcentr: Optional[float] = None   # 参考磁场强度 B0 [T]
    current: Optional[float] = None  # 等离子体电流 Ip [A]，来源 eq.Ip，不缩放
                                     # ITER 样例实测值约 1.56e7 A（约 15.6 MA）
                                     # DIII-D 样例实测值约 4.93e5 A（约 0.49 MA）
```

### 2.2 `Mesh2D`：LinkMesh 轻量统一网格对象（v1.11 迁入独立模块 src/linkmesh/mesh.py）

【v1.8 明确，v1.11 保持并迁移归属】`Mesh2D` 是 LinkMesh 目标格式之间的**轻量统一网格表示**，而不是 Python Triangle 专属对象。其 M2 正式核心数据收缩为三个数组，全部来自 OFT `build_mesh()` 返回值：

| 字段 | 来源 | 期望 shape | 期望 dtype |
|---|---|---|---|
| `nodes` | OFT `pts` | `(N, 2)` | `float64` |
| `triangles` | OFT `lc` | `(T, 3)` | 整数 dtype（M2-0 / M2 实测 `int32`），**内部 0-based** |
| `region_ids` | OFT `reg` | `(T,)` | 整数 dtype（M2-0 / M2 实测 `int32`），OFT 最终区域编号原样保留 |

**索引基准原则（v1.8）**：内部节点索引基准以 M2-0 / M2 实际证据为准。当前 OFT 26.6 已确认返回合法 **0-based** 连接表；Adapter 应验证 `0 <= lc < N`，**无需无依据地再次偏置**。任何后续偏置（如写入 TRIMEG HDF5 时的 `+1`）由目标 Writer 按其格式契约在写出阶段执行，不在 `Mesh2D` 阶段处理。

**区域编号原则（v1.8，v1.11 保持）**：`region_ids` **原样保存 OFT 返回的三角形区域编号**，不重编号、不压缩、不排序、不执行 `+1`。LinkMesh、`Mesh2D`、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义。区域语义应从 OFT `domain.region_info` 的区域名称、类型和最终 ID 获得。区域数量由 OFT 当前区域模型决定，不在 `Mesh2D` 中写死；**合法的单区域（N=1）网格同样满足该契约**。

**【v1.11 归属修正】** `Mesh2D` 的正式定义位置从历史 `src/linkmesh/mesher/triangle_wrapper.py` **迁出**到独立模块 `src/linkmesh/mesh.py`（计划新增）。迁移属于下一轮独立窄范围解耦任务（见第 16.1 节），本轮蓝图不执行源码迁移，仅固化实施计划。

**当前正式 Mesh2D 生成链路（v1.11 记录，M2 已通过）**：

```text
GFileData
  → oft_adapter.build_oft_domain_from_gfile()   # 构造 OFT gs_Domain（不 build_mesh）
  → OFT gs_Domain
  → domain.build_mesh()                          # 由正式安装的 OFT 生成 pts/lc/reg
  → pts / lc / reg
  → oft_adapter.mesh_from_oft_domain()           # 规范化 + 区域校验
  → Mesh2D
```

【已确认事实，v1.11】关于该链路的关键判断：
- 网格节点、三角形和区域编号**全部由正式安装的 OFT 生成**；
- 正式路径**没有**调用 `triangle_wrapper.generate_mesh()`；
- 正式路径**没有**调用 Python `triangle.triangulate()`；
- 当前 `oft_adapter.py` **仅从 `triangle_wrapper.py` 导入 `Mesh2D` 数据类**，不使用其网格算法；
- 因此**当前不存在网格算法仍依赖旧 Wrapper 的问题**，但存在**核心数据类型归属错误**和**正式路径结构耦合**（正式模块从历史模块导入核心类型）；
- M2 已通过，**解耦不得改变** OFT 调用、区域模型、网格数量、数组内容或 M2 行为。

**唯一定义与重导出兼容（v1.11 规定，下一轮实施）**：迁移后 `triangle_wrapper.py` 不再定义第二份 `Mesh2D`，而应 `from linkmesh.mesh import Mesh2D` 重新导出同一个类，以兼容旧导入。必须保证：

```text
linkmesh.mesh.Mesh2D is linkmesh.mesher.triangle_wrapper.Mesh2D  # 同一个类对象
```

不得在两个模块中保留两个独立的同名数据类。

**Mesh2D 数据类正式定义（迁入 src/linkmesh/mesh.py，下一轮实施）**：

```python
# src/linkmesh/mesh.py（计划新增，v1.11 批准）
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


def _empty_segments() -> np.ndarray:
    return np.empty((0, 2), dtype=np.int32)


def _empty_markers() -> np.ndarray:
    return np.empty((0,), dtype=np.int32)


@dataclass
class Mesh2D:
    """LinkMesh 轻量统一内存网格对象（v1.11 迁入独立模块）。

    与网格后端无关的统一表示。该对象是 OFT build_mesh() 返回结果经 LinkMesh
    最小适配后的统一表示，同时也是 writers/hdf5_writer.py 和 writers/smb_writer.py
    的共同输入。本模块不依赖 OFT / Python Triangle / HDF5 / PUMI / CLI / Plotter。

    M2 正式核心字段来源（OFT build_mesh() 返回值）：
        nodes      ← pts[np, 2]，OFT 返回的节点坐标，期望 dtype float64
        triangles  ← lc[nc, 3]，OFT 返回的三角形连接表，期望整数 dtype，内部 0-based
        region_ids ← reg[nc]，OFT 返回的三角形区域编号，期望整数 dtype

    索引约定（M2-0 / M2 已确认）：
        OFT 26.6 build_mesh() 返回合法 0-based lc 连接表，索引范围 0..N-1。
        Adapter 应验证 0 <= lc < N，无需无依据地再次偏置。
        任何针对目标格式的偏置（如 TRIMEG HDF5 的 +1）由目标 Writer 在写出阶段执行。

    区域编号约定（v1.8，v1.11 保持）：
        region_ids 原样保存 OFT 返回的三角形区域编号，不重编号、不压缩、不排序、不执行 +1。
        LinkMesh、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义。
        region_ids 不写入 TRIMEG HDF5（见第 4.1 与第 9 节），继续保留在内存对象中供
        Plotter 与 M4 使用。
    """

    # M2 正式核心字段（来自 OFT build_mesh() 返回值）
    nodes: np.ndarray                # shape=(N, 2)，节点 [R, Z] 坐标 [m]，dtype=float64
    triangles: np.ndarray            # shape=(T, 3)，三角形三顶点节点索引，整数 dtype，内部 0-based
    region_ids: np.ndarray           # shape=(T,)，每个三角形的区域 ID，整数 dtype，原样保留

    # 非核心、可选、兼容字段（v1.8 降级；v1.11 提供安全空数组默认值）
    # 这些字段不是 TRIMEG HDF5 loadfemmesh_h5.m 的直接消费数据集，
    # 也不是 M2 正式核心三数组，且不参与 v1.11 M3 HDF5 契约。
    # HDF5 Writer 不得访问这些字段（见第 9 节）。
    # 使用 default_factory 避免共享可变 NumPy 默认数组。
    boundary_segments: np.ndarray = field(default_factory=_empty_segments)  # shape=(0,2) int32
    boundary_markers: np.ndarray = field(default_factory=_empty_markers)    # shape=(0,) int32
    node_markers: np.ndarray = field(default_factory=_empty_markers)        # shape=(0,) int32

    @property
    def n_nodes(self) -> int:
        """节点总数。"""
        return self.nodes.shape[0]

    @property
    def n_triangles(self) -> int:
        """三角形总数。"""
        return self.triangles.shape[0]

    @property
    def n_boundary_segments(self) -> int:
        """边界线段总数。"""
        return self.boundary_segments.shape[0]
```

**【v1.11 重要澄清：`node_markers` 不再用于 idxivert/idxevert 生成】**

旧蓝图曾设想用 `node_markers` 区分内部/边界节点以生成 `/femmesh/idxivert`、`/femmesh/idxevert`。两个真实样例的拓扑检查已确认：`idxevert` 是**拓扑外边界节点**（网格无向边只出现一次的边所含节点）的集合，与 LCFS、第一壁、OFT region ID、`node_markers` 或文件名无关（详见第 4.1.4 节）。因此 HDF5 Writer **不使用** `node_markers` 生成 `idxivert/idxevert`，而是直接从 `triangles` 拓扑推导。`node_markers` 保留为空兼容字段，不参与 M3 契约。

### 2.3 `BoundaryConfig`（历史/过渡候选，非 M2 正式主路径）

【v1.8 状态，v1.11 保持】`BoundaryConfig` 是历史/过渡候选数据结构，原用于向 Python `triangle` 包传递输入。M2 正式主路径已由 `mesher/oft_adapter.py` 的 OFT `gs_Domain` 调用替代。

当前保留其定义（位于 `triangle_wrapper.py`）以维持与现有过渡代码（`triangle_wrapper.py`、`cli.py` 中 `_build_boundary_config()`）的兼容性，但不得将其作为 M2 正式架构的核心数据结构进行扩展。`Mesh2D` 迁出后，`BoundaryConfig` 仍暂留于 `triangle_wrapper.py`。删除前置条件见第 16.1 节。

---

## 3. 数据流转架构（OFT 优先，LinkMesh 最小适配）

### 3.1 正式目标数据管道（v1.8，v1.11 保持）

LinkMesh 的数据流以 OFT 为核心网格生成后端，LinkMesh 只负责最小输入编排、统一对象适配、目标格式翻译和 CLI 编排。

```text
GFile 平衡文本
  │
  ↓ [薄 Adapter：调用 OFT GEQDSKEquilibrium，提取边界坐标，绝不手动解析文本]
src/linkmesh/readers/gfile_reader.py
  │  ← from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium
  │  ← eq = GEQDSKEquilibrium(filepath)
  │  ← 提取 eq.boundary_R / eq.boundary_Z / eq.R_mag / eq.Z_mag 等属性
  │
  ↓ [封装为 GFileData，传递给 CLI 编排层]
GFileData
  │
  ↓ [M2 正式网格生成适配层：src/linkmesh/mesher/oft_adapter.py，M2 PASSED]
  │  [便利入口 generate_mesh(gfile_data, ...)：先 build_oft_domain_from_gfile 再 mesh_from_oft_domain]
  │  │
  │  ├─ build_oft_domain_from_gfile(gfile_data, ...)：当前 GFile 默认策略层
  │  │    [极薄接口规范化：坐标转 (N,2) float64、删首尾重复闭合点、验证最低点数、构造 outer 包围范围]
  │  │    [按当前批准策略调用 gs_Domain.define_region() / add_polygon() / add_annulus() / add_rectangle() / add_enclosed()]
  │  │    [返回已构造 gs_Domain；不调用 build_mesh()，不转换 pts/lc/reg]
  │  │
  │  └─ mesh_from_oft_domain(domain)：通用 N 区域核心（含 N=1）
  │       [调用 gs_Domain.build_mesh() 完成区域组织、边界处理、点合并、重采样、种子和网格生成]
  │       [OFT 内部通过 liboft_triangle 完成 Triangle 调用，LinkMesh 不直接维护]
  │       [build_mesh() 后从 domain.region_info 读取最终区域 ID；只按最终区域集合校验 reg]
  │
  ↓ [OFT build_mesh() 返回 (pts[np,2], lc[nc,3], reg[nc])，lc 为 0-based]
  │  [可选：OFT save_gs_mesh() 写出静态中间网格（OFT 自有格式，非 TRIMEG HDF5）]
  │
  ↓ [mesh_from_oft_domain 最小适配：规范化并检查 shape/dtype/有限值/索引范围/区域编号/退化三角形]
  │  [封装为轻量 Mesh2D 统一对象（正式定义位于 src/linkmesh/mesh.py，计划新增）；原样保存 OFT 区域编号]
Mesh2D  (轻量统一网格对象，v1.8 核心三数组 nodes/triangles/region_ids)
  │
  ├──→ [第一阶段战役：HDF5 映射对齐（v1.11 契约）]
  │      src/linkmesh/writers/hdf5_writer.py
  │      (严格对照 docs/trimeg/loadfemmesh_h5.m 与两个真实样例)
  │      (磁盘 vert=(N,2)、tria=(T,3)、8 核心 float64 数据集；不转置、不写第四列、不写 region_ids)
  │      (idxevert/idxivert 从 triangles 拓扑推导，写 1-based；默认不写 nbcRZ/Rbc/Zbc)
  │        │
  │        ↓
  │      TRIMEG 求解器消费的 HDF5 静态网格
  │
  └──→ [第二阶段战役：M3 验收后按侦察结果实现]
         src/linkmesh/writers/smb_writer.py
         (M3 完整验收后，只读侦察 SCOREC/PUMI/M3DC1 源码，
          按主管确认的实现路线转换；当前保持 NotImplementedError 占位)
           │
           ↓
         M3DC1 求解器消费的 .smb 静态二进制网格
```

**关于可选静态中间网格**：

OFT 已有 `save_gs_mesh()` / `load_gs_mesh()` 能力，可将网格结果保存为 HDF5 或 JSON 格式。这是 OFT 自有格式，**不是 TRIMEG HDF5 格式，也不是 M3DC1 `.smb` 格式**。可将其用于调试、归档和诊断，但正式生产链优先使用内存结果（`OFT build_mesh() → oft_adapter 最小适配 → HDF5/.smb`），不强制增加"OFT 写文件 → LinkMesh 再读文件"的中间步骤。

### 3.2 CLI 参数规范与调用方式

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数：

```text
# 方式 A：通过 python -m linkmesh（依赖 src/linkmesh/__main__.py，已新建 git: 1fc04f8）
python -m linkmesh [选项]

# 方式 B：通过控制台命令（依赖 pyproject.toml 中的 console_scripts 入口，pyproject.toml 计划新增）
linkmesh [选项]
```

两种方式的参数规范完全相同：

```text
用法：linkmesh [选项]

必选参数：
  --gfile PATH          GFile/EQDSK 平衡文件路径

可选参数：
  --output PATH         TRIMEG HDF5 输出路径（默认：mesh.h5）
  --smb PATH            PUMI .smb 输出路径（默认：mesh.smb）
  --min-angle FLOAT     [历史参数] Triangle 最小内角约束（度，默认：20.0）；OFT 正式路径暂不支持
  --max-area FLOAT      [历史参数] Triangle 最大三角形面积约束（m²，默认：不限制）；OFT 正式路径暂不支持
  --plot PATH           可视化自检图输出路径（默认：不生成）
  --no-smb              跳过 .smb 文件生成（仅生成 HDF5）
  --no-hdf5             跳过 HDF5 文件生成（仅生成 .smb）
  --verbose             打印详细日志（节点数、三角形数、写入状态）
  -h, --help            显示帮助信息
```

**【历史参数拦截】** `--min-angle` 与 `--max-area` 属于旧 Python Triangle 参数，OFT 正式路径暂不支持。若用户给出非默认值，CLI 抛出清晰错误，不静默忽略，默认值不传给 OFT Adapter（见 `cli.py` 中 `_check_unsupported_legacy_params`）。

**【v1.8 编排约束，v1.11 保持】** `cli.py` 只负责参数解析和调用 `mesher/oft_adapter.py`（经 `generate_mesh()` 便利入口），不得在 CLI 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换。这些逻辑由 OFT `gs_Domain` 内部处理。

**【v1.9 CLI 约束，v1.11 保持】** 本轮不新增任意区域配置 CLI 参数，当前 CLI 继续使用 GFile 默认区域模型（见第 7.2.2 节）。若未来需要从 CLI 选择计算域范围（例如显式选择 plasma-only），必须另行更新蓝图并定义参数（见第 5.1.2 节与第 7.2.3 节）。

---

## 4. 数据格式对齐规范（两阶段战役核心方法论）

本节是 LinkMesh 两大 Writer 模块的核心实现方法论，Aider 在编写 `src/linkmesh/writers/` 下任何代码前必须完整阅读本节。**v1.11 依据 `loadfemmesh_h5.m` 与两个真实 HDF5 样例重写了 4.1 全节的 TRIMEG HDF5 契约，撤销了此前被真实样例否定的旧规则。**

### 4.1 第一战役：TRIMEG HDF5 格式映射（v1.11 真实样例契约）

**【已确认事实】战役定性**：HDF5 是通用开放格式，TRIMEG 侧已有现成的 MATLAB 读取脚本 `docs/trimeg/loadfemmesh_h5.m` 作为黄金对照标尺，且已获得两个真实 TRIMEG HDF5 样例作为磁盘布局直接证据。以下所有规范均直接从该脚本与两个真实样例逐一核对提取。

**证据基础（v1.11）**：
- `docs/trimeg/loadfemmesh_h5.m`（TRIMEG MATLAB 消费函数）；
- `docs/trimeg/femmesh_65402_t1_nr16core.h5`（样例 A，称 core）；
- `docs/trimeg/femmesh_65402_t1_nr16nout4edge.h5`（样例 B，称 edge）；
- User 在 Linux 服务器使用 h5py、NumPy 与三角形拓扑检查脚本获得的完整输出，脚本只读 HDF5，退出码 0。

**文件名事实边界**：文件名中的 `core` 和 `edge` 可能描述不同计算范围，但**没有作者说明或生成端源码确认其严格物理意义**，不得仅凭文件名做物理裁决，也不得据 core/edge 外推区域物理语义。

#### 4.1.1 MATLAB 消费端事实：8 核心 + 3 可选

【已确认事实】`loadfemmesh_h5.m` **无条件读取** 8 个核心数据集：

| 序号 | HDF5 路径 |
|---|---|
| 1 | `/femmesh/nvert` |
| 2 | `/femmesh/ntria` |
| 3 | `/femmesh/nvert_in` |
| 4 | `/femmesh/nvert_ex` |
| 5 | `/femmesh/vert` |
| 6 | `/femmesh/idxivert` |
| 7 | `/femmesh/idxevert` |
| 8 | `/femmesh/tria` |

【已确认事实】`loadfemmesh_h5.m` 在 `try/catch` 中读取 3 个**可选**数据集：

| HDF5 路径 | 说明 |
|---|---|
| `/femmesh/nbcRZ` | 边界节点坐标点数 |
| `/femmesh/Rbc` | 边界节点 R 坐标 |
| `/femmesh/Zbc` | 边界节点 Z 坐标 |

缺失可选数据集只产生 warning，不阻止核心网格加载。MATLAB 绘图只使用 `femmesh.tria(:,1:3)`，并直接将其中数值作为 MATLAB 节点索引（因此磁盘 `tria` 必须为 1-based）。

**【重要澄清，v1.11 保持】** `loadfemmesh_h5.m` 中**没有**读取 `boundary_segments`、`boundary_markers`、`node_markers`。这些是 LinkMesh 内部字段，不是 TRIMEG 直接消费数据集，不得写入 TRIMEG HDF5 并声称为 TRIMEG 消费字段。

#### 4.1.2 8 个核心数据集磁盘契约（以 h5py 看到的实际磁盘布局为准）

【已确认事实，两个真实样例直接确认】以下为 Python h5py 读取到的**实际磁盘 shape 与 dtype**：

| HDF5 路径 | 磁盘 shape | 磁盘 dtype | 说明 |
|---|---|---|---|
| `/femmesh/nvert` | `(1,1)` | `float64` | 节点总数 N（整数语义，float64 存储） |
| `/femmesh/ntria` | `(1,1)` | `float64` | 三角形总数 T（整数语义，float64 存储） |
| `/femmesh/nvert_in` | `(1,1)` | `float64` | 内部节点数 nvert_in（整数语义，float64 存储） |
| `/femmesh/nvert_ex` | `(1,1)` | `float64` | 外边界节点数 nvert_ex（整数语义，float64 存储） |
| `/femmesh/vert` | `(N,2)` | `float64` | 节点坐标，**每行 `[R,Z]`**，不转置 |
| `/femmesh/tria` | `(T,3)` | `float64` | 三角形连接表，**1-based**，无第四列 |
| `/femmesh/idxivert` | `(1,nvert_in)` | `float64` | 内部节点全局索引，**1-based**，升序 |
| `/femmesh/idxevert` | `(1,nvert_ex)` | `float64` | 外边界节点全局索引，**1-based**，升序 |

**【dtype 铁律】** 计数、连接表和索引虽具有整数语义，两个真实样例**均以 `float64` 存储**。Writer 必须复现该磁盘 dtype（全部核心数据集写 `float64`）。

#### 4.1.3 撤销旧转置与第四列规则（v1.11 明确否定）

**以下旧表述在 v1.11 全篇撤销，标记为已被两个真实样例否定，禁止再据其编码**：

| 被否定的旧表述 | 真实样例直接反证 |
|---|---|
| Python/h5py 写 `vert=(2,N)` | 真实磁盘 `vert=(N,2)`（core `(981,2)`、edge `(1476,2)`） |
| Python/h5py 写 `tria=(4,T)` | 真实磁盘 `tria=(T,3)`（core `(1847,3)`、edge `(2775,3)`），无第四列 |
| Writer 对 `vert/tria` 执行转置 | 真实磁盘即为 `(N,2)`/`(T,3)`，无需转置 |
| `tria` 第四列写 `region_id` | 真实 `tria` 只有 3 列，无 region_id 列 |
| 11 个数据集全部必需 | 实为 8 核心 + 3 可选（可选缺失只 warning） |
| 用 `node_markers`/旧边界字段生成 `idxivert/idxevert` | `idxevert` 由三角形无向边拓扑推导（见 4.1.4） |
| `idxevert` 表示 LCFS 外全部二维区域节点 | `idxevert` 为拓扑外边界节点（无向边只出现一次） |
| `Mesh2D` 正式归属于 `triangle_wrapper.py` | `Mesh2D` 正式归属迁至 `src/linkmesh/mesh.py`（见第 2.2 与 16.1 节） |

**关于 MATLAB `.'` 的正确解释（v1.11）**：`loadfemmesh_h5.m` 中 `h5read(...).'` 是 **MATLAB/HDF5 维度解释**问题（MATLAB h5read 会将磁盘维度按列优先解释导致行列互换），**不能反向推导 Python Writer 必须转置**。蓝图分别记录两个 shape：
- **h5py 磁盘 shape**：`vert=(N,2)`、`tria=(T,3)`（Writer 直接按此写）；
- **MATLAB 消费 shape**：MATLAB 经 `.'` 后在 MATLAB 内存中得到的形状（属于 MATLAB 侧解释，Writer 不据其转置）。

#### 4.1.4 `idxevert` 拓扑定义（外边界节点）

【已确认事实，两个真实样例拓扑检查确认】将每个三角形的三条边视为**无向节点对**；`(a,b)` 与 `(b,a)` 是同一条边：

- 某无向边**出现两次**：内部共享边；
- 某无向边**出现一次**：拓扑外边界边；
- 某无向边**出现超过两次**：非流形边，Writer **必须拒绝**。

两个样例均确认拓扑外边界边所含节点集合与 `idxevert` 完全一致：

| 样例 | 拓扑外边界边数 | 外边界节点数 | 与磁盘 idxevert 一致 |
|---|---|---|---|
| core | 113 | 113 | 是 |
| edge | 175 | 175 | 是 |

**正式规定（v1.11）**：
- `idxevert` 是**拓扑外边界节点**的**升序 1-based** 编号；
- **不得**根据 LCFS、第一壁、OFT region ID 或文件名推断；
- plasma-only 网格的拓扑外边界**可能恰为 LCFS**；
- 多区域网格的拓扑外边界**通常是完整计算域最外边界**。

#### 4.1.5 `idxivert` 定义（补集）

**正式规定（v1.11）**：
- `idxivert` 是 `{1,...,N}` 排除 `idxevert` 后的**升序补集**；
- `len(idxivert) = nvert_in`；
- `len(idxevert) = nvert_ex`；
- `nvert_in + nvert_ex = nvert`；
- 两集合无重复、互斥且并集覆盖全部节点。

【已确认事实】编号跳跃是**补集结构**，不是数据损坏：
- core：`idxivert = 1..855, 969..981`，`idxevert = 856..968`；
- edge：`idxivert = 1..1130, 1306..1476`，`idxevert = 1131..1305`。

HDF5 查看器顶部从 0 开始显示的是**数组显示位置**，文件内节点编号仍为 **1-based**。

#### 4.1.6 `/femmesh/tria` 契约（v1.11）

【已确认事实，两个真实样例直接确认】：
- core：`tria=(1847,3)`，索引范围 `1..981`；
- edge：`tria=(2775,3)`，索引范围 `1..1476`；
- 均**无第四列**。

**正式规定（v1.11）**：
- `Mesh2D.triangles` 内部保持 **0-based**；
- Writer 写出 `(mesh.triangles + 1).astype(np.float64)`；
- 文件连接表为 **1-based**；
- **不转置**（磁盘 `(T,3)`）；
- **不添加第四列**；
- `Mesh2D.region_ids` **不写入** TRIMEG HDF5；
- `region_ids` 继续保留在内存对象中供 Plotter 和 M4 使用。

#### 4.1.7 3 个可选边界数据集事实边界（`nbcRZ` / `Rbc` / `Zbc`）

【已确认事实，两个真实样例共同确认磁盘布局】：
- `nbcRZ`：shape `(1,1)`、`float64`；
- `Rbc`：shape `(nbcRZ,1)`、`float64`；
- `Zbc`：shape `(nbcRZ,1)`、`float64`；
- 每个 `Rbc/Zbc` 点严格匹配某个 `idxevert` 节点；
- 不重复首点闭合。

**但两个样例揭示不一致，禁止过度规定**：
- edge：`nbcRZ = nvert_ex = 175`，覆盖全部外边界节点；
- core：`nbcRZ = 112`、`nvert_ex = 113`，缺少节点 968，闭合点对 `(856,967)` 不是拓扑边。

**因此 v1.11 明确不得规定**：
- `nbcRZ == nvert_ex`（core 反例：112 ≠ 113）；
- `Rbc/Zbc` 必须覆盖全部 `idxevert`（core 缺节点 968）；
- 每对相邻 `Rbc/Zbc` 必须是拓扑边（core 反例 `(856,967)`）；
- 仅凭 `Mesh2D` 能唯一重建历史 `Rbc/Zbc`。

**M3 第一阶段 Writer 处理策略（v1.11）**：**默认不写这 3 项**。MATLAB 出现缺少可选数据集的预期 warning 可以接受，但核心网格必须成功加载。

#### 4.1.8 两个真实样例结构摘要

**样例 A（core）**：
- `nvert = 981`、`ntria = 1847`；
- `nvert_in = 868`、`nvert_ex = 113`；
- `vert = (981,2)`、`tria = (1847,3)`；
- `idxevert = 856..968`；
- `nbcRZ = 112`。

**样例 B（edge）**：
- `nvert = 1476`、`ntria = 2775`；
- `nvert_in = 1301`、`nvert_ex = 175`；
- `vert = (1476,2)`、`tria = (2775,3)`；
- `idxevert = 1131..1305`；
- `nbcRZ = 175`。

**不得根据 core/edge 文件名外推物理语义。**

### 4.2 第二战役：M3DC1 `.smb` 格式——M3 验收后侦察确定实现路线

**【已确认事实】战役定性**：`.smb` 并非商业公司私有保密格式，而是开源 `SCOREC/PUMI` 库的通用二进制网格格式。这意味着我们可以通过只读侦察项目中已引入的 `m3dc1_scorec` 和 `scorec/pumi` 开源 C++ 源码，完整逆向推导出其格式协议。

**【铁律】M3 完整验收通过后，才能开始 M4 侦察与实现。在侦察完成并经主管确认前，`write_smb()` 保持 `NotImplementedError` 占位，不得锁定任何具体序列化方式。v1.11 不修改任何 M4 `.smb` 未确认契约。**

**侦察目标（M3 验收后执行）**：

1. **侦察入口**：重点只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc` 中读取 `.smb` 文件的 C++ 实现，以及 `scorec/pumi` 库中 `pumi_mesh_load` 的底层解析逻辑。
2. **侦察目标**：从 C++ 读取代码中提取以下关键信息：
   - 文件头格式（魔数、版本号、维度、节点数、单元数等元数据的字节布局）
   - 字节序（Endianness：大端 vs 小端）
   - 数值精度（节点坐标 float32 vs float64；索引 int32 vs int64）
   - 拓扑排列顺序（节点坐标块、三角形连接块、区域标记块、边界标记块的先后顺序）
   - 索引约定（0-based vs 1-based）
   - MeshFile 与 ModelFile 的配对关系（见第 4.2.1 节）
   - M3DC1 特有的区域数量、几何分类、连续性要求（如 C1 连续性、高阶单元等）
   - **M3DC1 是否支持单区域、是否至少需要真空区（见第 5.1.3 节，保留为待源码确认事项）**
3. **实现路线**：由侦察结果和主管确认决定，可能包括但不限于：
   - Python 二进制写出；
   - 调用 SCOREC/PUMI 官方 API；
   - 调用经确认的官方转换程序；
   - 其他由直接证据确认的方式。
4. **前置条件**：`src/linkmesh/writers/smb_writer.py` 的具体实现**必须等待** M3 完整验收通过、只读侦察任务完成并经主管确认后方可开始编写。
5. **M3DC1 特有适配原则**：若 M3DC1 有额外区域、边界实体、几何分类或连续性要求（如 C1 连续性、高阶单元等），只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。

#### 4.2.1 M4 侦察线索（组内交流，非直接源码证据）

以下内容来自组内交流，记录为 M4 侦察线索，不得升级为已确认格式事实：

- M3DC1 可能存在 Multi Region 网格，区域数可能依装置、算例和 ModelFile 而变化；
- MeshFile 可能保存离散网格，ModelFile 可能保存边界/模型信息；
- 导体和线圈的完整含时物理功能可能有限；
- M3DC1 可能有 C1 连续性要求或高阶单元需求，但这不是当前阻止 OFT 网格后端的事实，需要 M4 源码侦察确认。

M4 仍必须在 M3 完整通过后，对 MCD7 样例、官方文档、ModelFile、MeshFile 和 M3DC1/SCOREC/PUMI 源码进行只读侦察，确认区域数量、D1B、几何分类、索引、文件配对和 `.smb` 契约；不得据此提前实现 `.smb`。P0 默认三区域方案不得被外推为 M3DC1 永久固定三区域，单区域/两区域实例也不得被外推为 M3DC1 的最小区域数量要求。

**【待源码确认】当前推断的 `.smb` 格式关键事实**：

| 信息类别 | 当前推断 | 事实状态 |
|---|---|---|
| 文件类型 | 小端序二进制文件 | 【待源码确认】 |
| 文件头 | 包含版本号、维度、节点数、单元数等元数据 | 【待源码确认】 |
| 节点坐标 | 按节点顺序存储 (R, Z) 坐标，float64 | 【待源码确认】 |
| 三角形连接表 | 按三角形顺序存储三顶点节点索引，int32 | 【待源码确认】 |
| 区域标记 | 每个三角形对应一个整数区域 ID | 【待源码确认】 |
| 边界标记 | 每条边界线段对应一个整数边界标记 | 【待源码确认】 |
| 索引约定 | 1-based（Fortran/PUMI 约定） | 【待源码确认】 |
| 高阶节点 | 是否需要边中点（C1 单元需求） | 【待源码确认，见缺口 G1】 |
| 序列化方式 | Python 二进制写出或其他 | 【待侦察后由主管确认】 |
| MeshFile/ModelFile 配对 | 区域数量和 ModelFile 格式 | 【待源码确认，见 M4 侦察线索】 |
| M3DC1 区域数量 | 不固定，依装置和算例而变化 | 【待源码确认，不得由 P0 单/两/三区域样例固定】 |
| M3DC1 单区域支持 | 是否支持单区域、是否至少需要真空区 | 【待源码确认，见第 5.1.3 节】 |

---

## 5. 区域标记与边界标记约定

### 5.1 区域编号总体原则（v1.8，v1.11 保持单区域与通用 N 区域）

【v1.8 原则，v1.11 保持】LinkMesh 不维护全局固定的区域编号映射（如 `1=plasma、2=vacuum、3=wall`）。

**正式原则**：

1. **区域由 OFT `gs_Domain` 的命名区域和最终区域编号定义**；
2. **LinkMesh 原样保存 OFT 返回的三角形区域编号**，不重编号、不压缩、不排序、不执行 `+1`；
3. **LinkMesh、`Mesh2D`、HDF5 Writer 和未来 SMB Writer 不得根据整数编号猜测区域物理语义**；
4. **区域语义应从 OFT `domain.region_info` 的区域名称、类型和最终 ID 获得**，不得从整数值推断；
5. **区域数量由 OFT 当前区域模型决定**，不在 LinkMesh 中写死；
6. **当前两区域 PLASMA/OUTER 与三区域 PLASMA/VACUUM/OUTER 只作为代表性验收样例**，不是 LinkMesh 的全局固定架构，也不是 `oft_adapter.py` 的能力边界；
7. **M3DC1 Multi Region 的区域数不得由这两个样例固定**；单/两/三区域实例也不得被外推为 TRIMEG/M3DC1 的最小区域数量要求（见第 5.1.3 节）；
8. **若某个物理区域不属于目标计算域，正确做法是构造不包含该区域的 OFT 区域模型，使其不生成三角形**；不得保留区域空间后将其编号设为 0。OFT 中非正区域编号表示未认领或非法区域，不是"无物理方程"的合法标签。
9. **【v1.11 补充】区域编号不进入 TRIMEG HDF5**：`region_ids` 不写入 `/femmesh/tria` 或任何 TRIMEG 数据集（真实样例 `tria` 无第四列）；`region_ids` 仅在内存中保留供 Plotter 与 M4 使用。

#### 5.1.1 通用 N 区域能力（v1.9，v1.11 已运行验证）

【v1.9 原则，v1.11 已运行验证】`oft_adapter.py` 正式 Adapter 对**任意正区域数量 N 通用，包括 N=1**：

- LinkMesh 不重新设计一套任意 N 区域配置系统；OFT `gs_Domain` 本身即作为 N 区域定义接口；
- 通用 N 区域核心由 `mesh_from_oft_domain(domain)` 承担（见第 7.1 节），它只根据 `domain.region_info`（在 `build_mesh()` 之后读取的最终区域集合）验证区域集合，不写死区域数量、名称、类型或最终整数 ID；
- 两区域、三区域只是代表性验收样例；N=1 与 N>3 都必须被 `mesh_from_oft_domain()` 正确接受（合法输入时通过，非法输入时失败，见第 5.2 节校验规则）；
- 【M2 mock 证据】`tests/test_oft_adapter.py` 已覆盖单区域（N=1）、两区域、三区域、N>3，以及区域缺失/多余/非法编号失败与 `build_mesh()` 后最终区域 ID 时序场景，mock 测试退出码 0。

#### 5.1.2 单区域 plasma-only 物理定位（v1.9，v1.11 保持）

【v1.9 物理定位，v1.11 保持】单区域 plasma-only 是**合法的计算域选择**：

- **计算域仅为 LCFS 内部**：LCFS 是最外层计算边界，LCFS 外不生成三角形；
- **适用场景**：只计算等离子体内部、LCFS 边界条件由外部给定、不自洽计算真空场、壁响应或线圈耦合的场景；
- **不可替代性**：它**不能替代**需要自由边界、真空场、导体、第一壁或线圈响应的多区域模型；
- **网格层面无最小区域数要求**：**不存在** LinkMesh/OFT 网格层面"至少必须两个区域"的全局要求；
- **区域裁剪原则**：若某个区域不属于计算域，应**不在 OFT Domain 中创建它**，使其生成 0 个三角形；不得保留区域空间后用 `region_id=0` 表示"不求解"；
- **【v1.11 拓扑边界补充】** plasma-only 网格的拓扑外边界（`idxevert`，见第 4.1.4 节）可能恰为 LCFS，但这仍由三角形无向边拓扑决定，不由区域语义推断。

**CLI 与默认策略关系（v1.9，v1.11 保持）**：单区域 plasma-only 作为 `mesh_from_oft_domain()` 的合法输入与自动测试场景（见第 14.1 节）。本轮**不新增 CLI 参数**选择 plasma-only，**不修改当前默认 GFile 策略**（见第 7.2.2 节）。若未来需要从 CLI 选择计算域范围，必须另行更新蓝图并定义参数。

#### 5.1.3 TRIMEG / M3DC1 单区域消费者事实边界（v1.9，v1.11 保持）

【v1.9 事实边界，禁止外推】以下为消费者侧单区域支持的当前事实边界，不得由两/三区域实例外推最小区域数量要求：

| 消费者 | 单区域支持事实边界 | 状态 |
|---|---|---|
| TRIMEG HDF5 加载器（`loadfemmesh_h5.m`） | 当前直接证据**没有**显示要求至少两个二维区域；单区域网格原则上仍可提供节点、三角形、内部/外边界节点索引和可选边界坐标 | 已确认（仅限加载器层面） |
| TRIMEG 物理求解层 | "文件能被 MATLAB 加载"不等于"TRIMEG 所有物理算例都接受 plasma-only"；求解层是否需要真空区仍待更多直接证据 | 【待更多直接证据】 |
| M3DC1 | 是否支持单区域、是否至少需要真空区、是否要求 C1 连续性或高阶单元，全部保留为 M4 待源码确认事项 | 【待源码确认，M4】 |

**结论**：不得把当前两区域或三区域实例外推为 TRIMEG/M3DC1 的最小区域数量要求。网格层面（LinkMesh/OFT）不存在最少两区域要求；消费者层面的区域需求由各自求解器的直接证据决定。

### 5.2 区域校验规则（v1.9，v1.11 已运行验证）

【v1.9 校验规则，v1.11 已运行验证】`mesh_from_oft_domain()` **不得**要求固定区域数量或固定集合 `{1,2}`、`{1,2,3}`。应检查以下各项：

1. `domain.region_info`（在 `build_mesh()` 成功返回之后读取，得到 OFT 最终区域 ID 集合）至少包含**一个**已经创建的区域；
2. OFT 输出 `reg` 全部为**有限正整数**；
3. `reg` 长度等于三角形数（`len(reg) == T`）；
4. 实际输出区域 ID 集合与 `domain.region_info` 的**最终** ID 集合**一致**（既不缺失也不多余）；
5. **每个 Domain 区域至少对应一个三角形**（不允许某个已创建区域生成 0 个三角形；若某区域不应存在，应在构造 Domain 时就不创建它，见第 5.1.2 节区域裁剪原则）；
6. **合法单区域（N=1）输出必须通过**；
7. **不重编号、不压缩、不排序、不执行 `+1`**。

**区域 ID 时序（关键）**：OFT `build_mesh()` 会根据区域类型和定义顺序重排区域 ID，并原地更新 `domain.region_info[name]["id"]`。因此最终区域 ID 集合必须在 `build_mesh()` 成功返回之后从 `domain.region_info` 读取，**绝不能在 `build_mesh()` 之前提取**。`tests/test_oft_adapter.py` 已包含该时序回归测试（RelabelDomain）。

**失败条件（应抛错或验收失败）**：
- 输出缺失某个 Domain 区域（区域 ID 集合缺项）；
- 输出出现额外区域（`reg` 中出现 `domain.region_info` 之外的 ID）；
- 出现 `0`、负数或非整数区域编号；
- `reg` 长度与三角形数不一致；
- `domain.region_info` 为空（无任何已创建区域）。

### 5.3 P0 验收样例（代表性样例，非全局固定架构，非能力边界）

以下样例仅用于 P0 阶段验证，**不代表 LinkMesh 的全局固定区域编号约定，也不代表 `oft_adapter.py` 的能力边界**。OFT 最终编号由 `build_mesh()` 决定。

#### 样例 A：三区域验收样例（当前真实 DIII-D 样例，M2 正式验收已通过）

当 GFile 提供有效、闭合且满足嵌套关系的第一壁/limiter 轮廓时，P0 验收场景从内到外定义三个区域。**M2-0 与 M2 正式验收真实运行已确认 OFT 最终区域编号如下**：

| OFT 区域名称 | OFT reg_type | OFT 最终 ID（M2-0 / M2 实测） |
|---|---|---|
| `PLASMA` | `plasma` | 1 |
| `OUTER` | `boundary` | 2 |
| `VACUUM` | `vacuum` | 3 |

**注意**：该编号只描述当前 OFT 区域模型下的实测结果，**不得外推为所有模型的固定编号表**。区域数量和最终 ID 由 OFT `build_mesh()` 决定。M2 正式验收下该三区域样例真实网格统计为 `{1:633, 2:678, 3:561}`（详见第 13 节 M2）。

#### 样例 B：两区域合成验收样例

两区域合成样例定义 `PLASMA` + `OUTER`。M2-0 合成两区域运行中区域统计为 `{1:83, 2:401}`（详见第 13 节 M2-0 证据）。

#### 样例 C：单区域 plasma-only 样例（v1.9，自动测试场景，M2 mock 已覆盖）

单区域 plasma-only 样例仅定义一个 plasma 区域，计算域为 LCFS 内部，LCFS 外不生成三角形（见第 5.1.2 节）。作为 `mesh_from_oft_domain()` 的合法输入与自动测试场景（mock 单区域 OFT Domain，输出一个正区域 ID，必须通过），不新增 CLI 参数（见第 14.1 节测试规划）。M2 mock 测试已覆盖该场景，退出码 0。

### 5.4 边界标记约定（历史/过渡代码，非 OFT 正式约定，v1.11 不进入 M3 契约）

【历史/过渡】以下为历史过渡代码（Python triangle 路线）中使用的边界标记约定，仅供参考，不作为 OFT 路线的正式约定，**也不参与 v1.11 M3 HDF5 契约**：

| boundary_marker | 历史含义 | 备注 |
|---|---|---|
| 1 | LCFS | 历史过渡代码约定 |
| 2 | first wall/limiter | 历史过渡代码约定 |
| 3 | outer boundary | 历史过渡代码约定 |
| 0 | 内部节点（非边界） | — |

【v1.11 明确】M3 TRIMEG HDF5 的内部/外边界节点区分（`idxivert`/`idxevert`）**不依赖** `boundary_markers`/`boundary_segments`/`node_markers`，而由三角形无向边拓扑推导（见第 4.1.4 节）。M2 正式路径中 OFT Adapter 对这些非核心字段传入空数组占位，未重建边界恢复算法（见第 7.4 节）。

---

## 6. src/linkmesh/readers/gfile_reader.py 实现规范（OFT Adapter 模式）

### 6.1 设计原则：薄 Adapter，绝不重复造轮子

【已确认事实】`src/linkmesh/readers/gfile_reader.py` 的唯一职责是作为**薄 Adapter（接线员）**：

1. 调用 OFT（OpenFUSIONToolkit）提供的 `GEQDSKEquilibrium` 类读取 GFile；
2. 从 OFT 返回对象的属性中提取 LinkMesh 所需的字段；
3. 封装为 `GFileData` 对象返回。

**【绝对禁止】** 在 `src/linkmesh/readers/gfile_reader.py` 中手动执行任何原始 GFile 文本 I/O、字符串切分、Fortran 格式化数值解析或 EQDSK 格式字段手动提取。OFT 已经提供了完整、经过验证的 GFile 解析实现，LinkMesh 直接复用即可。

### 6.2 OFT 运行依赖（已确认事实）

【已确认事实】以下 OFT 版本已在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证；并已在 M2-0 与 M2 正式验收中于正式 Conda 环境（Python 3.12.13）验证网格生成链路：

```text
openfusiontoolkit==26.6
```

**版本约定**：
- 当前记录的经过真实验证的版本为 `openfusiontoolkit==26.6`，不得写成 `>=26.6`，不得声称其他版本已经验证。
- 最终运行安装**不要求**携带整个 `TOKAMAKER/` 源码树；`TOKAMAKER/` 继续作为开发期绝对只读参考区，不参与运行时依赖。

### 6.3 PYTHONPATH 规则（已确认事实，铁律）

【已确认事实】以下 PYTHONPATH 规则来自服务器冒烟测试中的实际故障排查，必须严格遵守：

**【绝对禁止】** 将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入运行环境的 `PYTHONPATH`。该路径下的 OFT 源码快照**不包含编译后的 `liboftpy.so`**，若加入 PYTHONPATH 会遮蔽 `site-packages` 中带有 `liboftpy.so` 的正式安装包，导致 OFT 导入失败，并最终抛出 `FileNotFoundError: Unable to load OFT shared library`。

**开发期临时规则**：
- 标准安装完成后（`pip install -e .` 或 `pip install .`），最终用户**不应**依靠手动设置 PYTHONPATH 来发现 LinkMesh。
- 开发期尚未安装时，可以临时将仓库 `src/` 目录加入 PYTHONPATH（`export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH`），但**绝对不得**同时加入 `TOKAMAKER/OpenFUSIONToolkit/src/python`。

```bash
# 正确：开发期临时将 src/ 加入 PYTHONPATH
export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH

# 错误：绝对禁止将 OFT 源码路径加入 PYTHONPATH
# export PYTHONPATH=/path/to/TOKAMAKER/OpenFUSIONToolkit/src/python:$PYTHONPATH  # 禁止！
```

### 6.4 OFT 可用 API 清单（已确认事实）

【已确认事实】以下两个 OFT API 均已通过只读侦察 `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/eqdsk.py` 确认存在于源码中：

#### 方案 A：`read_geqdsk`（轻量字典接口）

```python
# 来源：TOKAMAKER/.../TokaMaker/eqdsk.py 底部 read_geqdsk 便捷函数
# 注意：正确函数名为 read_geqdsk，不是 read_eqdsk
from OpenFUSIONToolkit.TokaMaker.eqdsk import read_geqdsk

g = read_geqdsk(filepath)
# g 是一个字典，已确认的键（来自 _read_geqdsk 函数）：
#   g['RBBBS']  → LCFS 边界 R 坐标数组 [m]
#   g['ZBBBS']  → LCFS 边界 Z 坐标数组 [m]
#   g['RMAXIS'] → 磁轴 R 坐标 [m]
#   g['ZMAXIS'] → 磁轴 Z 坐标 [m]
#   g['RLIM']   → 第一壁 R 坐标数组 [m]
#   g['ZLIM']   → 第一壁 Z 坐标数组 [m]
```

**事实等级**：`read_geqdsk` 已通过只读源码侦察确认存在；当前没有服务器直接执行 `read_geqdsk` 的运行验证证据，不得声称其已通过服务器验证。

#### 方案 B：`GEQDSKEquilibrium`（高级对象接口，属性更丰富）【当前正式采用】

```python
# 来源：TOKAMAKER/.../TokaMaker/eqdsk.py，GEQDSKEquilibrium 类
from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium

eq = GEQDSKEquilibrium(filepath)
# 已确认的属性（来自 eqdsk.py GEQDSKEquilibrium 类属性定义，只读侦察确认）：
#   eq.boundary_R   → LCFS 边界 R 坐标数组 [m]（属性 boundary_R，来自 _raw['RBBBS']）
#   eq.boundary_Z   → LCFS 边界 Z 坐标数组 [m]（属性 boundary_Z，来自 _raw['ZBBBS']）
#   eq.R_mag        → 磁轴 R 坐标 [m]（属性 R_mag，来自 _raw['RMAXIS']）
#   eq.Z_mag        → 磁轴 Z 坐标 [m]（属性 Z_mag，来自 _raw['ZMAXIS']）
#   eq.limiter_R    → 第一壁 R 坐标数组 [m]（属性 limiter_R，来自 _raw['RLIM']）
#   eq.limiter_Z    → 第一壁 Z 坐标数组 [m]（属性 limiter_Z，来自 _raw['ZLIM']）
#   eq.R_center     → 参考大半径 R0 [m]（属性 R_center，来自 _raw['RCENTR']）
#   eq.B_center     → 参考磁场强度 B0 [T]（属性 B_center，来自 _raw['BCENTR']）
#   eq.Ip           → 等离子体电流 Ip [A]（属性 Ip，来自 _raw['CURRENT']，不缩放）
```

**事实等级**：`GEQDSKEquilibrium` 已通过只读源码侦察确认存在，且已在服务器（liustation，`openfusiontoolkit==26.6`）上实际运行验证，成功读取 `ITER_test.eqdsk` 和 `DIIID/g192185.02440` 并提取全部所需字段；M2-0 与 M2 中进一步验证其输出可直接驱动 OFT `gs_Domain` 网格生成链路。

**当前正式采用方案 B**（`GEQDSKEquilibrium`），因为其属性命名语义清晰，且已提供 `boundary_R`/`boundary_Z`、`limiter_R`/`limiter_Z`、`R_mag`/`Z_mag` 等 LinkMesh 直接需要的字段，并已通过服务器运行验证。

### 6.5 `read_gfile()` 函数接口（已实现）

【已确认事实】以下为 `src/linkmesh/readers/gfile_reader.py` 中已实现的函数签名与核心逻辑：

```python
from OpenFUSIONToolkit.TokaMaker.eqdsk import GEQDSKEquilibrium
import numpy as np

def read_gfile(filepath: str) -> GFileData:
    """读取 GFile/EQDSK 平衡文件，提取 LinkMesh 所需的边界信息。

    实现策略：薄 Adapter 模式。
    直接调用 OFT GEQDSKEquilibrium 读取 GFile，从其属性中提取字段，
    封装为 GFileData 对象。LinkMesh 侧不执行任何原始文本解析。

    参数：
        filepath: GFile 文件路径（字符串）

    返回：
        GFileData 对象

    异常：
        FileNotFoundError: 文件不存在（由 GEQDSKEquilibrium 内部抛出）；
                           或 OFT 共享库缺失时抛出
                           "FileNotFoundError: Unable to load OFT shared library"
        ValueError: 文件格式不符合 EQDSK 规范（由 GEQDSKEquilibrium 内部抛出）
        ImportError: OFT Python 包本身未安装或不在 PYTHONPATH 中
    """
    eq = GEQDSKEquilibrium(filepath)
    # 提取 LCFS 坐标 → 闭合性检查 → 逆时针方向检查 → 封装 GFileData
    ...
```

### 6.6 LCFS 边界后处理（LinkMesh 侧唯一允许的后处理）

从 OFT 提取的 LCFS 坐标可能存在以下问题，`src/linkmesh/readers/gfile_reader.py` 必须处理（这是 LinkMesh 侧唯一允许的后处理逻辑，不属于原始文本解析）：

1. **闭合性**（`_ensure_lcfs_closed`）：确保 LCFS 首尾点相同。使用相对容差（首尾点距离 < 总周长的 0.1%）判断，若不满足则追加首点到末尾。
2. **方向性**（`_ensure_lcfs_ccw`）：使用 Shoelace 公式计算有向面积，若为负值（顺时针）则反转数组为逆时针。
3. **重采样**：LCFS 点数可能过多或过少，OFT `gs_Domain` 在调用 `add_polygon()`/`add_annulus()` 时内部负责重采样（非 `gfile_reader.py` 职责）。

---

## 7. OFT gs_Domain 网格生成适配规范（M2 正式路线：mesher/oft_adapter.py 三层接口，M2 PASSED）

### 7.1 oft_adapter.py 三层接口正式职责（M2 正式主路径，v1.9，v1.11 已实现并通过）

【已实现，M2 正式主路径，M2 PASSED】`src/linkmesh/mesher/oft_adapter.py` 是 M2 正式网格生成适配层。v1.9 将其正式职责拆分为**三层接口**，通用 N 区域核心与当前 GFile 默认策略解耦；v1.10 已在服务器实现并通过 mock 测试与真实 DIII-D 验收；v1.11 规定其解耦后从 `linkmesh.mesh` 导入 `Mesh2D`（不改变 M2 行为）。

#### 7.1.1 `mesh_from_oft_domain(domain) -> Mesh2D`（通用 N 区域核心）

**职责**：

1. 接收**已经由调用方构造完成**的 OFT `gs_Domain`；
2. 调用 `domain.build_mesh()`；
3. 将 OFT `pts/lc/reg` 规范化为 `Mesh2D`；
4. **在 `build_mesh()` 成功返回之后**从 `domain.region_info` 读取 OFT 最终区域 ID 集合，只根据该最终集合验证区域集合（校验规则见第 5.2 节）；
5. **对任意正区域数量 N 通用，包括 N=1**；
6. **不理解或推断 plasma、vacuum、outer 的物理语义**；
7. **不写死区域名称、类型、数量或最终整数 ID**。

**类型标注说明**：`domain` 参数使用运行时 OFT 对象（宽松标注 `Any`），**未引入新的 Protocol、抽象基类或插件系统**。

**Mesh2D 导入（v1.11）**：解耦后 `mesh_from_oft_domain()` 构造的 `Mesh2D` 来自 `from linkmesh.mesh import Mesh2D`，不再从 `triangle_wrapper.py` 获取。解耦不改变 OFT 调用、区域模型、网格数量、数组内容或 M2 行为。

#### 7.1.2 `build_oft_domain_from_gfile(gfile_data, ...)`（当前 GFile 默认策略层）

**职责**：

1. 只负责当前 GFile 默认区域策略和薄输入编排；
2. 根据当前批准策略构造 OFT `gs_Domain`（见第 7.2.2 节默认策略）；
3. **不调用 `build_mesh()`，不转换 `pts/lc/reg`**；
4. **不复制 OFT 的重采样、点合并、种子搜索或 Triangle 算法**。

**返回**：已构造但尚未 `build_mesh()` 的 OFT `gs_Domain` 对象。

**允许的极薄输入规范化**（见第 7.3 节）：坐标转 `(N,2)` float64、删首尾重复闭合点、验证最低点数、构造 outer 包围范围、传递网格尺度参数。

#### 7.1.3 `generate_mesh(gfile_data, ...) -> Mesh2D`（CLI 便利入口）

**职责**：

1. 作为 CLI 便利入口；
2. **只组合前两个函数**：先调用 `build_oft_domain_from_gfile()` 构造默认 OFT Domain，再调用 `mesh_from_oft_domain()` 生成 `Mesh2D`；
3. **不包含第二套网格验证或区域算法**（验证由 `mesh_from_oft_domain()` 唯一承担）。

**三层接口关系示意**：

```text
generate_mesh(gfile_data, ...)                    # CLI 便利入口
  │
  ├─ domain = build_oft_domain_from_gfile(gfile_data, ...)   # 默认策略层：构造 gs_Domain，不 build_mesh
  │
  └─ return mesh_from_oft_domain(domain)          # 通用 N 区域核心：build_mesh + 规范化 + 校验
```

**【OFT 治理铁律】** 三层接口均只调用 Conda 环境中正式安装的 OFT：
- 不修改 OFT 源码；
- 不读取或改写 OFT 安装目录；
- 不维护 OFT fork；
- 不依赖仓库 `TOKAMAKER/` 快照作为运行时包。

### 7.2 OFT gs_Domain 调用方式（M2 正式路线，M2-0 与 M2 已验证）

【已确认事实，来自只读侦察 `meshing.py` 与 M2-0 / M2 运行验证】OFT `gs_Domain` 提供完整的区域定义、边界组织、区域种子和网格生成能力。M2 正式路线通过 `oft_adapter.py` 三层接口调用 OFT `gs_Domain`，不复制 OFT 已实现的通用几何逻辑。

#### 7.2.1 通用调用流程（示意）

```python
from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain

# Step 1：创建 gs_Domain 对象（build_oft_domain_from_gfile 内部）
domain = gs_Domain(...)

# Step 2：定义命名区域（区域类型、分辨率等）
# 区域数量 N 由当前策略决定，可为 1、2、3 或更多（N 区域通用）
domain.define_region('outer', outer_dx, 'boundary')
domain.define_region('plasma', plasma_dx, 'plasma')
# 视策略追加 vacuum 等区域（见第 7.2.2 节）

# Step 3：添加几何边界（LCFS、第一壁、人工 outer boundary 等）
# 使用 add_polygon() / add_annulus() / add_rectangle() 添加区域边界
# 必要时使用 add_enclosed() 添加区域内部种子点

# Step 4：调用 build_mesh() 生成网格（mesh_from_oft_domain 内部）
pts, lc, reg = domain.build_mesh()
# pts: shape=(np, 2)，节点坐标，float64
# lc:  shape=(nc, 3)，三角形连接表，int32，0-based（M2-0 / M2 确认）
# reg: shape=(nc,)，三角形区域编号（来自 OFT 区域模型），int32
```

**【M2-0 与 M2 已确认】** 以上调用链在真实运行中通过验证：
- `gs_Domain` 可以直接接受 GFile 提供的 LCFS 和第一壁轮廓（经极薄规范化）；
- `build_mesh()` 返回 `reg` 数组的区域编号为正整数，与 `domain.region_info`（build_mesh 后的最终 ID）中定义区域一一对应；
- `lc` 数组为 0-based，索引范围 `0..N-1`；
- `pts` 数组为 `(N, 2)` float64。

#### 7.2.2 当前 GFile 默认策略（`build_oft_domain_from_gfile` 采用，v1.11 保持）

【v1.11 保持】保留当前已验证的默认策略，由 `build_oft_domain_from_gfile()` 承担：

| 输入条件 | 默认区域模型 | 区域数量 N |
|---|---|---|
| 有有效第一壁（GFile 提供有效、闭合、满足嵌套关系的 limiter/第一壁轮廓） | PLASMA + VACUUM + OUTER（`add_annulus` + `add_rectangle`） | 3 |
| 无第一壁（GFile 未提供可用壁轮廓） | PLASMA + OUTER（`add_polygon` + `add_rectangle`） | 2 |

**明确**：这是**当前 CLI/GFile 便利策略**，**不是 Adapter 全局能力限制**。`mesh_from_oft_domain()` 的通用 N 区域能力（含 N=1、N>3）与该默认策略解耦（见第 5.1.1 节与第 7.1.1 节）。M2 正式验收使用有壁三区域策略（DIII-D）。

#### 7.2.3 未来 CLI 计算域选择（v1.9，v1.11 保持，待另行更新蓝图）

【v1.9 待裁决，v1.11 保持】单区域 plasma-only 作为 `mesh_from_oft_domain()` 的合法输入与自动测试场景（见第 5.3 样例 C 与第 14.1 节）。本轮**不新增 CLI 参数**选择 plasma-only，**不修改当前默认 GFile 策略**。

如果未来需要从 CLI 选择计算域范围（例如显式选择 plasma-only 或其他区域模型），**必须另行更新蓝图并定义参数**，不得擅自新增。

### 7.3 最小输入规范化（`build_oft_domain_from_gfile` 允许的极薄预处理）

允许 `build_oft_domain_from_gfile()` 在构造 OFT Domain 前做**极薄的接口规范化**：

1. 将 LCFS 和第一壁坐标转换为 shape `(N, 2)` 的有限 `float64` 数组；
2. 删除首尾近似重复的闭合点，避免 OFT 产生零长度闭合小段；
3. 验证点数满足 OFT 调用的最低要求；
4. 构造人工 outer boundary 所需的简单包围范围（仅在采用含 OUTER 的策略时）；
5. 把网格尺度参数传给 OFT。

**【严禁】** 不允许在 LinkMesh 中复制 OFT 的尖角处理、Sliver 处理、Small feature 处理、重采样、自交通用框架、共享边界拆分或区域种子搜索。第一壁尖角和短线段优先交给 OFT 处理；只有实际 OFT 运行失败且有直接证据时，才提出新的最小预处理建议。

【M2-0 与 M2 证据】DIII-D 真实样例中，第一壁尖角和短线段触发 OFT `Repeated points`、`Sliver`、`Small feature` 警告，但最终网格质量通过（M2 实测最小内角 `20.222037126210235°`，退化三角形 0）。这证明尖角和短线段交给 OFT 处理是可行的，无需 LinkMesh 侧额外预处理（几何警告为非阻塞项，见第 13 节 M2）。

### 7.4 LinkMesh 最小适配层（OFT 输出 → Mesh2D，`mesh_from_oft_domain` 承担）

OFT `build_mesh()` 返回 `(pts, lc, reg)` 后，`mesh_from_oft_domain()` 进行最小适配，规范化为 `Mesh2D` 轻量统一对象，并执行第 5.2 节的区域校验以及以下检查：

- `nodes`：`pts` 转为 `(N, 2)` float64；检查有限值；
- `triangles`：`lc` 转为 `(T, 3)` 整数；检查 `0 <= lc < N`（0-based，M2-0 / M2 确认，无需再次偏置）；
- `region_ids`：`reg` 转为 `(T,)` 整数；原样保存，不重编号；按第 5.2 节校验区域集合（含 N=1 合法、非正编号失败、区域集合与 `domain.region_info` 最终 ID 一致、每区域至少一个三角形）；
- 退化三角形检查：重复顶点三角形数、绝对面积不大于 `1e-12` 的三角形数应为 0；
- 区域属性长度检查：`len(reg) == T`。

区域语义（名称、类型、ID）从 OFT `domain.region_info` 获得，不从整数值推断。

**非核心边界字段处理**：`Mesh2D` 的 `boundary_segments`/`boundary_markers`/`node_markers` 在 M2 正式路径中由 Adapter 使用默认空数组（或显式空数组占位），**未为填充这些旧字段而重建边界恢复算法**。这些字段不参与 v1.11 M3 HDF5 契约（`idxivert/idxevert` 由三角形拓扑推导，见第 4.1.4 节）。

### 7.5 历史/过渡代码（Python triangle 包路线，非 M2 正式主路径）

【v1.8 状态，v1.11 保持】以下历史/过渡代码不再作为 M2 正式主路径，已被 `oft_adapter.py` 替代：

- `src/linkmesh/mesher/triangle_wrapper.py`：Python `triangle` 包底座封装（仍承载 `BoundaryConfig` 定义；解耦后从 `linkmesh.mesh` 重导出 `Mesh2D`）；
- `src/linkmesh/cli.py` 中的 `_build_boundary_config()` 与 `_resample_closed_curve()`：历史过渡胶水代码；
- `tests/test_triangle_wrapper.py`：历史过渡测试（36/36 通过，作为历史证据保留）。

**处置原则**：本轮保持这些文件不动，暂不删除、不扩展。**禁止为了保存旧实现继续扩展其区域拓扑和通用几何能力。** 是否以后删除旧模块和旧测试由后续减量任务裁决（减量顺序见第 16.1 节）。旧 Triangle 的 36 项测试作为历史证据保留，用于证明历史路径没有被 Mesh2D 解耦过程意外破坏，**但不能作为 OFT Adapter 正式验收的替代**。

---

## 8. src/linkmesh/cli.py 编排规范（M2 OFT 路线，已接入 generate_mesh）

### 8.1 职责与编排原则

`src/linkmesh/cli.py` 是 LinkMesh 的 CLI 编排层，负责：

1. 解析命令行参数；
2. 拦截历史 Triangle 参数（`--min-angle`/`--max-area` 非默认值时抛清晰错误）；
3. 调用 `read_gfile()` 获取 `GFileData`；
4. 将 `GFileData` 传给 `mesher/oft_adapter.py` 的 `generate_mesh()` 便利入口（最小输入编排，使用 Adapter 默认网格尺度）；
5. 由 `generate_mesh()` 内部组合 `build_oft_domain_from_gfile()` 与 `mesh_from_oft_domain()` 返回 `Mesh2D`；
6. 调用 `write_hdf5()` 或 `write_smb()` 写出目标格式；
7. 调用 `plot_mesh()` 生成可视化自检图（区域着色）。

**【禁止】** 不得在 `cli.py` 中实现区域算法、点在多边形算法、区域种子搜索或 Triangle 数据转换。不得复制 OFT 通用几何逻辑（边界重采样、点合并、区域种子搜索等）。这些逻辑由 OFT `gs_Domain` 内部处理，或由 `oft_adapter.py` 三层接口编排。

### 8.2 M2 OFT 编排（已实现）

【已实现】`cli.py` 的 M2 正式路径已接入 `mesher/oft_adapter.py` 的 `generate_mesh()` 便利入口。约束为：

- `cli.py` 只传递 `GFileData`（使用 Adapter 默认网格尺度，不传历史 Triangle 参数）；
- 不在 `cli.py` 中实现任何几何/区域/种子/Triangle 算法；
- 区域编号原样从 `generate_mesh()` 返回的 `Mesh2D` 获取，不在 `cli.py` 中重编号；
- 本轮不新增任意区域配置 CLI 参数（见第 3.2 节与第 7.2.3 节）；
- M2 正式验收 CLI 路径为 `--no-hdf5 --no-smb --plot <PNG> --verbose`，跳过 HDF5 与 SMB Writer，仅生成 `Mesh2D` 与区域着色 PNG。

### 8.3 历史/过渡代码（`_build_boundary_config`）

【v1.8 状态，v1.11 保持】`cli.py` 中现有的 `_build_boundary_config()` 与 `_resample_closed_curve()` 函数是历史/过渡胶水代码，不再由 CLI 正式路径调用；`_build_boundary_config()` 仍导入 `BoundaryConfig`，是本轮暂不删除历史 Triangle Wrapper 的直接原因之一（见第 16.1 节）。

当前保留这些函数以维持与历史过渡代码的兼容性，但不得继续扩展其功能。后续减量任务将按第 16.1 节顺序删除。

---

## 9. src/linkmesh/writers/hdf5_writer.py 实现规范（第一战役：TRIMEG HDF5 格式映射，v1.11 契约）

**【v1.11 依据 `loadfemmesh_h5.m` 与两个真实样例重写本节。旧转置/第四列/11 数据集全必需等表述已在第 4.1.3 节全篇撤销。】**

### 9.1 实现依据与黄金标尺

【已确认事实】`src/linkmesh/writers/hdf5_writer.py` 的实现依据是 `docs/trimeg/loadfemmesh_h5.m`（MATLAB 消费函数）与两个真实样例 `femmesh_65402_t1_nr16core.h5` / `femmesh_65402_t1_nr16nout4edge.h5`。所有数据集路径名、磁盘 shape、dtype 和索引约定均以第 4.1 节 v1.11 契约为最终裁决依据，不得凭推断自行补充。

### 9.2 TRIMEG HDF5 物理文件结构树（v1.11，8 核心 + 3 可选）

【已确认事实，两个真实样例磁盘布局】：

```text
mesh.h5
└── /femmesh/                          # 唯一顶层组，名称固定为 "femmesh"
    │
    ├── nvert        [shape=(1,1), float64]   # 节点总数 N（整数语义，float64 存储）【核心】
    ├── ntria        [shape=(1,1), float64]   # 三角形总数 T（整数语义，float64 存储）【核心】
    ├── nvert_in     [shape=(1,1), float64]   # 内部节点数 nvert_in【核心】
    ├── nvert_ex     [shape=(1,1), float64]   # 外边界节点数 nvert_ex【核心】
    │
    ├── vert         [shape=(N,2), float64]   # 节点坐标，每行 [R,Z]，不转置【核心】
    │
    ├── idxivert     [shape=(1,nvert_in), float64]  # 内部节点全局索引，1-based，升序【核心】
    ├── idxevert     [shape=(1,nvert_ex), float64]  # 外边界节点全局索引，1-based，升序【核心】
    │                                                # nvert_in + nvert_ex == nvert
    │
    ├── tria         [shape=(T,3), float64]   # 三角形连接表，1-based，无第四列【核心】
    │
    ├── nbcRZ        [shape=(1,1), float64]   # 边界节点坐标点数【可选，M3 第一阶段默认不写】
    ├── Rbc          [shape=(nbcRZ,1), float64]  # 边界节点 R 坐标【可选，默认不写】
    └── Zbc          [shape=(nbcRZ,1), float64]  # 边界节点 Z 坐标【可选，默认不写】
```

**【重要说明】** `boundary_segments`、`boundary_markers`、`node_markers`、`region_ids` 不是 TRIMEG HDF5 的直接消费数据集，**不得写入** TRIMEG HDF5。

### 9.3 精确字段映射契约（Field Mapping Contract，v1.11）

见第 4.1.2 节 8 个核心数据集磁盘契约表格，以及第 4.1.4、4.1.5、4.1.6 节的 `idxevert/idxivert/tria` 规则。

### 9.4 `/femmesh/tria` 精确构造公式（v1.11）

```python
# tria 磁盘契约：shape=(T,3)，float64，1-based，无第四列
tria_1based = (mesh.triangles + 1).astype(np.float64)   # shape=(T, 3)
h5file.create_dataset('/femmesh/tria', data=tria_1based)   # 不转置、不加第四列、不写 region_ids
```

### 9.5 `idxevert` / `idxivert` 拓扑生成公式（v1.11）

```python
# Step 1：统计所有三角形的无向边（(a,b) 与 (b,a) 视为同一边）
#   出现一次 → 拓扑外边界边；出现两次 → 内部共享边；出现 >2 → 非流形（拒绝）
# Step 2：外边界节点 = 所有出现一次的无向边所含节点（0-based）
# Step 3：idxevert = 外边界节点集合 +1（1-based），升序排序 → shape (nvert_ex,)
# Step 4：idxivert = {1..N} \ idxevert 的升序补集 → shape (nvert_in,)
#   nvert_ex = len(idxevert)；nvert_in = len(idxivert)；nvert_in + nvert_ex == N
# Step 5：磁盘写出 shape：idxevert=(1,nvert_ex) float64；idxivert=(1,nvert_in) float64
```

**不得**用 `node_markers`/`boundary_segments`/`boundary_markers` 生成 `idxivert/idxevert`；**不得**根据 LCFS/第一壁/region ID/文件名推断（见第 4.1.4 节）。

### 9.6 `write_hdf5()` 职责与约束（v1.11）

完成第 16 节规定的 `Mesh2D` 解耦并通过 M2 回归后，M3 Writer 实施任务只允许修改 `src/linkmesh/writers/hdf5_writer.py` 与 `tests/test_hdf5_writer.py`。Writer 职责：

1. 接收 `linkmesh.mesh.Mesh2D`；
2. 验证 `nodes` shape `(N,2)`、`triangles` shape `(T,3)`；
3. 验证有限值、0-based 整数索引、范围（`0 <= idx < N`）、无重复节点、无零面积（绝对面积 > `1e-12`）；
4. 统计无向边并**拒绝非流形边**（出现 >2 次）；
5. 生成升序 1-based `idxevert`（拓扑外边界节点）；
6. 生成升序 1-based `idxivert`（`{1..N}` 补集）；
7. 写 8 个核心 `float64` 数据集；
8. `vert` 直接写 `(N,2)`（不转置）；
9. `tria` 写 `(T,3)` 的 `triangles+1`（1-based，无第四列）；
10. **不写** `region_ids`；
11. **默认不写** `nbcRZ/Rbc/Zbc`；
12. **不访问**旧 `boundary_segments`、`boundary_markers`、`node_markers`；
13. **不修改**输入 `Mesh2D`；
14. **不进入 M4**。

**M3 前置条件（v1.11 铁律）**：M3 Writer 实施**必须在** `Mesh2D` 解耦完成并通过 M2 mock + 真实 DIII-D 回归**之后**才开始（见第 16 节实施顺序铁律）。**M3 尚未通过，不得宣称 M3 已通过。**

---

## 10. src/linkmesh/writers/smb_writer.py 实现规范（第二战役：M3 验收后侦察确定实现路线）

### 10.1 实现依据与前置条件

`src/linkmesh/writers/smb_writer.py` 的实现依赖对 `SCOREC/PUMI` 开源 C++ 源码的只读侦察结果，以及主管对实现路线的确认。**在 M3 完整验收通过、侦察任务完成并经主管确认前，本模块保持 `NotImplementedError` 占位实现，严禁提前编写任何字节流或序列化逻辑。v1.11 不修改任何 M4 `.smb` 未确认契约。**

侦察目标文件（只读，严禁修改，M3 验收后执行）：
- `M3DC1/m3dc1_scorec/src/m3dc1_mesh.cc`：`.smb` 文件读取的 C++ 实现入口
- `M3DC1/m3dc1_scorec/include/m3dc1_model.h`：model `.txt` 配套文件格式
- `M3DC1/m3dc1_scorec/src/m3dc1_field.cc`：高阶节点需求确认

### 10.2 `write_smb()` 函数接口（占位，待 M4 里程碑实现）

【已确认事实】当前 `write_smb()` 保持 `raise NotImplementedError` 占位实现。实现路线（包括但不限于 Python 二进制写出、调用官方 API 或其他方式）必须由侦察结果和主管确认决定，不得提前锁定。若 M3DC1 有额外区域、边界实体、几何分类或连续性要求，只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。**M3DC1 是否支持单区域、是否至少需要真空区，保留为 M4 待源码确认事项（见第 5.1.3 节）。**

### 10.3 配套 model .txt 文件规范（占位）

M3DC1 在读取 `.smb` 网格文件的同时，还需要读取配套的 model `.txt` 文件来获取区域语义和边界条件定义。

**【待源码确认】**：model `.txt` 文件的具体格式需通过只读侦察 `M3DC1/m3dc1_scorec/src/m3dc1_model.cc` 中 `load_model` 函数确认。从已侦察的 `m3dc1_model.cc` 可知，文件头格式为：

```text
numL separatrixLoop innerWallLoop outerWallLoop vacuumLoop
```

后续每个 loop 的顶点与边的详细格式待进一步侦察确认。

---

## 11. src/linkmesh/utils/plotter.py 实现规范

### 11.1 已实现的两个函数

【已确认事实】`src/linkmesh/utils/plotter.py` 已完整实现以下两个函数：

#### `plot_lcfs_only(gfile_data, filepath)`（M1 最小可用版本）

仅绘制 LCFS 边界曲线，用于 M1 里程碑验收。功能：
- 绘制 LCFS 边界曲线（红色实线，显示闭合）
- 若有第一壁数据，叠加绘制（蓝色虚线，显示闭合）
- 标注磁轴位置（红色叉号）
- 输出统计信息文本框（LCFS 点数、磁轴坐标）
- 保存为 PNG 文件，dpi=150

**PNG 中文字形说明（v1.10 已修复，v1.11 保持）**：为避免服务器默认 `DejaVu Sans` 字体缺少中文字形导致的 `Glyph missing` 警告，所有渲染进 PNG（标题、图例、统计框）或打印到终端的字符串均使用英文；代码注释与文档字符串保留中文（不交给 Matplotlib 渲染）。

#### `plot_mesh(gfile_data, mesh, filepath, show_boundary_markers=True, show_region_ids=False)`（M2 完整版本）

绘制 LCFS 边界与生成三角网格的叠加图。功能：
- 使用 `matplotlib.tri.Triangulation` 绘制三角网格线（仅依赖 `nodes`/`triangles`）
- 若 `show_region_ids=True`，按实际 `region_ids` 着色填充（颜色方案不依赖固定区域编号语义，对排序后的实际 OFT 区域 ID 建立离散索引映射，使用 `ListedColormap` + `BoundaryNorm` 保证三角形填色与图例色块严格一致；图例标签为 `OFT region <id>`；单区域时按单一区域着色，N>3 亦可绘制）
- 叠加绘制 LCFS 边界曲线（红色实线，显示闭合）
- 若有第一壁数据，叠加绘制（蓝色虚线，显示闭合）
- 标注磁轴位置（红色叉号）
- 若 `show_boundary_markers=True` 且存在真实边界段时才绘制旧边界段（空兼容数组时跳过）
- 统计信息文本框始终显示 `Nodes` / `Triangles`；仅当存在真实边界段时显示 `Boundary segments`，避免空兼容数组导致误导性的 `Boundary segments: 0`
- 设置 `aspect='equal'`，保存为 PNG 文件，dpi=150
- CLI 正式路径以 `show_region_ids=True` 调用，使 M2 PNG 默认显示各 OFT 区域离散颜色

**Mesh2D 导入（v1.11）**：解耦后 `plotter.py` 从 `linkmesh.mesh` 导入 `Mesh2D`（仅用于类型标注可用 `TYPE_CHECKING`）。`region_ids` 仍由 Plotter 使用（着色），不受 M3 HDF5 契约"不写 region_ids"影响——后者只约束 HDF5 Writer 磁盘输出。

### 11.2 LCFS 显示闭合（v1.10 已实现，v1.11 保持）

【v1.10 已实现】`plotter.py` 通过 `_closed_for_display()` 在绘制 LCFS 与第一壁显示曲线时，若首尾不同则临时追加首点用于显示闭合，**仅用于绘图显示，绝不修改底层数据对象**。M2 正式验收 PNG 中 LCFS 红线与 First wall 蓝色虚线均闭合。

---

## 12. 依赖清单

### 12.1 核心运行依赖

```text
numpy>=1.24.0
h5py>=3.8.0
matplotlib>=3.7.0
openfusiontoolkit==26.6
```

**说明**：
- `openfusiontoolkit==26.6` 为当前在 Linux x86_64 服务器（liustation）上通过 pip 安装官方 manylinux wheel 并完成真实冒烟测试验证、并在 M2-0 与 M2 正式验收中于正式 Conda 环境（Python 3.12.13）验证网格生成链路的版本，不得写成 `>=26.6`，不得声称其他版本已经验证。
- OFT 通过 pip 安装官方 wheel 获取，**不依赖** `TOKAMAKER/` 源码树。
- OFT 内部通过 `liboft_triangle` 完成 Triangle 调用，LinkMesh 不需要单独安装 Python `triangle` 包。
- 【历史/过渡】`triangle>=20230923`：历史过渡代码依赖，M2 正式路线（`oft_adapter.py`）不需要该依赖；是否从依赖清单移除由主管在后续裁决（与第 16.1 节旧 Triangle 路径减量顺序一并处理）。
- `pyproject.toml`（计划新增）和 `requirements.txt` 的核心运行依赖和版本约束必须保持一致（见第 15 节）。

### 12.2 开发与测试依赖（可选）

```text
pytest>=7.0.0
```

---

## 13. 敏捷渐进里程碑（MVP 开发阶段）

**【铁律】开发时序严格锁死：先完成 M2-0（OFT 可行性验证，已通过），再完成 M2（OFT 网格生成验收，已通过），再完成 Mesh2D 解耦（v1.11 新增前置任务），再完成 M3（TRIMEG HDF5 闭环验证，尚未通过），确认网格几何物理质量完全合格后，再进军 M4（`.smb` 侦察与实现）。严禁跳序。**

### 里程碑 M1：GFile 读取验收（P0 第一步）

**当前状态**：【M1 已通过，允许进入 M2-0 / M2】

【已确认事实】M1 全部验收项均已通过，具体证据如下：

**自动测试**：`tests/test_gfile_reader.py` 运行结果 `19 passed in 0.61s`，退出码 `0`（git: f52a75f）。临时日志路径 `/tmp/m1_reader_test.log`，该路径不保证长期保存。

**真实 GFile 验收**：
- 样例文件：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 调用链：DIII-D GFile → 正式安装的 OFT `GEQDSKEquilibrium`（`openfusiontoolkit==26.6`）→ LinkMesh `read_gfile` → `GFileData`，未使用 mock
- 实测结果：LCFS 81 点；第一壁 88 点；磁轴 `R=1.78029311 m`、`Z=-0.0421587565 m`；等离子体电流 `493324.5 A`
- CLI 路径：`--no-hdf5 --no-smb --plot` 进入 M1 专用路径，不调用 M2 Triangle、M3 HDF5 或 M4 SMB
- PNG 临时路径：`/tmp/linkmesh_diiid_m1.png`，该路径不保证长期保存

**人工几何检查**（User 已确认）：
- LCFS 闭合连续，无明显跳点或自交
- 第一壁整体包围 LCFS
- 磁轴位于 LCFS 内
- R/Z 方向和尺度合理
- DIII-D 极向截面形状正常

**非阻塞问题（M1 时观察，v1.10 PNG 文本已改英文修复）**：M1 阶段 matplotlib `DejaVu Sans` 缺少中文字形，产生 `Glyph missing` 警告。M2 正式验收 PNG 已将渲染文本改为英文，不再出现该警告。

**M1 验收标准逐项确认**：
1. ✅ `python -m linkmesh --gfile ... --no-hdf5 --no-smb --plot lcfs_check.png` 能够运行
2. ✅ 生成的 PNG 中 LCFS 边界曲线闭合、方向正确
3. ✅ 终端打印 LCFS 点数、磁轴坐标
4. ✅ `GFileData` 对象所有必填字段均已正确填充
5. ✅ `gfile_reader.py` 中不存在任何手动文本解析逻辑（AST 测试通过）
6. ✅ `tests/test_gfile_reader.py` 中的 M1 自动测试全部通过（19 passed）

**涉及模块**：`src/linkmesh/__main__.py`（已新建，git: 1fc04f8），`src/linkmesh/readers/gfile_reader.py`（OFT Adapter），`src/linkmesh/utils/plotter.py`（`plot_lcfs_only` 函数），`tests/test_gfile_reader.py`（已通过，git: f52a75f）

---

### 里程碑 M2-0：OFT gs_Domain 可行性验证（P0 第一点五步）

**当前状态**：【已通过，M2 正式实现前的可行性证据；不是与 M2 并列的第二个已完成里程碑】

**目标**：在正式 Linux OFT 环境中验证 OFT `gs_Domain`、`Mesh`、`build_mesh()` 的最小调用链，确认 OFT 网格生成路线的可行性，为 M2 正式实现提供直接运行证据。

#### M2-0 已确认环境证据

【已确认事实】M2-0 运行环境：
- 操作系统：Linux x86_64；
- Python：3.12.13；
- OFT：正式 Conda 环境中的 `OpenFUSIONToolkit 26.6`；
- OFT 包路径：`/home/lxzeng/miniconda3/envs/linkmesh/lib/python3.12/site-packages/OpenFUSIONToolkit`；
- `gs_Domain`、`Mesh`、`Region`、`run_triangle` 均存在且可调用；
- `liboft_triangle.so` 已找到并成功加载；
- LinkMesh 从 `/home/lxzeng/LinkMesh_server/src/linkmesh` 导入。

#### M2-0 合成网格证据

【已确认事实，直接运行结果】

- **两区域合成网格**：267 个节点、484 个三角形；`pts (267,2) float64`、`lc (484,3) int32`、`reg (484,) int32`；索引范围 `0..266`；区域统计 `{1:83, 2:401}`；零面积三角形 0；**通过**。
- **三区域合成网格**：302 个节点、554 个三角形；`pts (302,2) float64`、`lc (554,3) int32`、`reg (554,) int32`；索引范围 `0..301`；区域统计 `{1:83, 2:291, 3:180}`；零面积三角形 0；**通过**。

#### M2-0 真实 DIII-D 证据

【已确认事实，直接运行结果】

- 真实样例：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 实际链路：`真实 GFile → LinkMesh read_gfile/OFT GEQDSKEquilibrium → GFileData → OFT gs_Domain → OFT Mesh/build_mesh → liboft_triangle → pts/lc/reg`

**输入**：
- LCFS 80 个不重复闭合输入点；
- 第一壁 87 个不重复闭合输入点；
- 磁轴 `(R=1.78029311 m, Z=-0.0421587565 m)`。

**输出**：
- 972 个节点；
- 1872 个三角形；
- `pts (972,2) float64`；
- `lc (1872,3) int32`；
- `reg (1872,) int32`；
- 索引范围 `0..971`；
- 区域统计 `{1:633, 2:678, 3:561}`；
- 区域元数据：`PLASMA id=1 type=plasma`、`OUTER id=2 type=boundary`、`VACUUM id=3 type=vacuum`；
- 最小面积 `3.0697138006999725e-06 m²`；
- 最大面积 `0.01121952731171436 m²`；
- 重复顶点三角形 0；
- 面积不大于 `1e-12 m²` 的三角形 0；
- 非正有向面积三角形 0；
- 实际最小内角 `20.222037126210235°`；
- PNG `/tmp/m2_0_oft_diiid.png` 已生成；
- 最终退出码 0。

**人工检查**：
- 三个区域网格覆盖与 LCFS、第一壁、人工 outer boundary 的位置关系正常；
- 第一壁尖角和短线段触发 OFT `Repeated points`、`Sliver`、`Small feature` 警告，但最终网格质量通过；
- LCFS 红线局部缺口由临时绘图脚本删除重复末点后未重新连接首尾造成，是显示问题，不是 OFT 几何或网格缺口（v1.10 正式 Plotter 已通过 `_closed_for_display()` 修复显示闭合）。

#### M2-0 结论

| 验证项 | 状态 |
|---|---|
| OFT 环境与动态库验证 | PASSED |
| 合成两区域网格 | PASSED |
| 合成三区域网格 | PASSED |
| 真实 DIII-D 三区域网格 | PASSED |
| OFT `pts/lc/reg` 最小契约 | PASSED |

**M2-0 授权**：M2-0 的通过授权进入 M2 Adapter 实现。M2-0 是 M2 正式实现前的可行性证据，**不是与 M2 并列的第二个已完成里程碑**。

**涉及模块**：OFT `gs_Domain`（只读参考），`src/linkmesh/mesher/oft_adapter.py`（M2 新建）

---

### 里程碑 M2：OFT 网格生成验收（P0 第二步）

**当前状态**：【M2 总体 PASSED（已由 User 在 Linux 服务器确认）】

**目标（已达成）**：新建 `src/linkmesh/mesher/oft_adapter.py` 正式网格生成适配层（三层接口，见第 7.1 节），并最小修改 `cli.py` 接入 `generate_mesh()` 便利入口，使 OFT 网格结果进入 LinkMesh 轻量统一对象（`Mesh2D`）并完成真实样例和 PNG/统计验收。

**正式 M2 路径（已实现）**：

```text
真实 GFile
  → read_gfile / OFT GEQDSKEquilibrium
  → GFileData
  → oft_adapter.generate_mesh
      → build_oft_domain_from_gfile → OFT gs_Domain
      → mesh_from_oft_domain → OFT Mesh / build_mesh → liboft_triangle → pts/lc/reg
  → Mesh2D
  → plot_mesh（区域着色 PNG）
```

**Adapter 三层接口（已实现）**：
- `mesh_from_oft_domain(domain) -> Mesh2D`：通用正区域数量 N 的核心，包括 N=1 和 N>3；`build_mesh()` 后从 `domain.region_info` 读取最终区域 ID，只按最终集合校验；
- `build_oft_domain_from_gfile(gfile_data, ...)`：有壁三区域、无壁两区域默认策略，不调用 `build_mesh()`；
- `generate_mesh(gfile_data, ...)`：只组合前两层。

LinkMesh 原样保存 OFT `reg`，不重编号、不排序、不压缩、不执行 `+1`。

#### M2 mock 测试证据

【已确认事实，直接运行结果】Linux 服务器已实际运行：

```text
python -m pytest -v tests/test_oft_adapter.py
```

**最终退出码为 0**。该结果证明 OFT Adapter 的 mock 契约测试通过，覆盖受控 Domain 编排、三层接口、单区域（N=1）/两区域/三区域/N>3 的 N 区域转换、输入/输出防御、`build_mesh()` 后最终区域 ID 时序（RelabelDomain）以及区域缺失/多余/非法编号失败场景。

**证据边界**：当前证据仅提供"测试文件通过、退出码 0"，**未提供准确的测试总数与耗时**；蓝图与 History 不记录 `N passed in Xs`。mock 测试不依赖真实 OFT 动态库，不能替代真实 DIII-D 验收。

#### M2 真实 DIII-D 正式验收证据

【已确认事实，直接运行结果】

- 真实样例：`TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440`
- 正式 CLI 路径：
  ```text
  python -m linkmesh --gfile TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440 --no-hdf5 --no-smb --plot <PNG_PATH> --verbose
  ```
- 该路径已确认：调用正式 Reader；调用正式 OFT Adapter；调用正式安装的 OFT `gs_Domain/Mesh/build_mesh` 和 `liboft_triangle.so`；生成 `Mesh2D`；跳过 HDF5 Writer；跳过 SMB Writer；生成区域着色 PNG。

**真实输出**：
- 节点数：972；
- 三角形数：1872；
- OFT 区域数：3；
- `nodes/pts` shape `(972,2)`、dtype `float64`；
- `triangles/lc` shape `(1872,3)`、dtype `int32`；
- `region_ids/reg` shape `(1872,)`、dtype `int32`；
- 三角形节点索引范围 `0..971`；
- 区域统计 `{1:633, 2:678, 3:561}`；
- OFT 最终区域元数据：`PLASMA id=1 type=plasma`、`OUTER id=2 type=boundary`、`VACUUM id=3 type=vacuum`；
- 最小三角形面积 `3.0697138006999725e-06 m²`；
- 最大三角形面积 `0.01121952731171436 m²`；
- 重复顶点三角形数 0；
- 面积不大于 `1e-12 m²` 的三角形数 0；
- 非正有向面积三角形数 0；
- 实际最小内角 `20.222037126210235°`；
- 正式 CLI 运行退出码 0。

**区域语义说明**：区域物理语义必须结合 OFT 区域元数据（`domain.region_info` 的名称与类型）解释，不得根据整数编号固定推断。

#### M2 区域着色 PNG 人工验收证据

【已确认事实，User 人工检查确认】最终区域着色 PNG：
- 标题为英文，不再出现中文方框或 `Glyph missing` 警告；
- 统计框显示 `Nodes: 972`、`Triangles: 1872`；
- 不再显示误导性的 `Boundary segments: 0`；
- OFT region 1、2、3 使用三种可区分颜色；
- 图例色块与实际区域颜色一致；
- `OFT region 1` 位于 LCFS 内部；
- `OFT region 3` 位于 LCFS 与第一壁之间；
- `OFT region 2` 位于第一壁与人工 outer boundary 之间；
- LCFS 红线闭合；
- First wall 蓝色虚线闭合；
- Magnetic axis 位于 LCFS 内；
- 未见明显网格缺口、跨区域错误、翻折、自交或空洞；
- PNG 人工几何和区域位置检查通过。

（PNG 为临时验收产物，路径不保证长期保存，不作为永久归档文件。）

#### M2 OFT 几何警告（当前非阻塞项）

【已确认事实】真实第一壁触发 OFT 的 `Repeated points`、`Sliver` 和 `Small feature` 警告。当前记录为**非阻塞诊断信息**，原因是：
- OFT 成功生成完整网格；
- 没有重复顶点三角形；
- 没有近零面积三角形；
- 没有非正有向面积三角形；
- 最小内角通过；
- 区域和 PNG 验收通过。

**不得**将这些警告描述成已修复，也**不得**要求 LinkMesh 在本轮增加几何修补算法。

#### M2 最终状态

| 验证项 | 状态 |
|---|---|
| M2-0 OFT 环境与可行性 | PASSED |
| OFT Adapter 静态审查 | PASSED |
| OFT Adapter mock 测试（退出码 0） | PASSED |
| 真实 DIII-D Reader → OFT Adapter → Mesh2D | PASSED |
| 数组、0-based 索引、区域集合与网格质量 | PASSED |
| 区域着色 PNG 生成 | PASSED |
| User 人工几何和区域位置检查 | PASSED |
| **M2 总体** | **PASSED** |

**M2 边界声明**：M2 通过**不等于** M3、M4 或 M5 通过。M3 尚未通过（见下方 M3 与第 16 节）。

**涉及模块**：`src/linkmesh/mesher/oft_adapter.py`（已实现，三层接口），`src/linkmesh/cli.py`（已接入 `generate_mesh()`），`src/linkmesh/utils/plotter.py`（区域着色 + LCFS 闭合显示 + PNG 英文文本），`tests/test_oft_adapter.py`（已实现，mock 退出码 0）

**本轮源码提交号**：v1.10 文档提交为 `e5633fe`（docs：更新 M2 OFT Adapter 正式验收状态为 PASSED 并归档至 History）；M2 相关源码提交号待 User 补充。

---

### 里程碑 M2.5：Mesh2D 解耦（v1.11 新增前置任务，M3 Writer 前必须完成）

**当前状态**：【待实施；M3 Writer 的强制前置任务】

**目标**：将轻量 `Mesh2D` 从历史 `triangle_wrapper.py` 迁入独立正式模块 `src/linkmesh/mesh.py`，消除"正式 OFT 路径核心数据类型归属于历史 Wrapper"的结构耦合，且**不改变任何 M2 行为**。

**允许修改的文件（下一轮独立窄范围任务）**：
- 新建 `src/linkmesh/mesh.py`；
- 修改 `src/linkmesh/mesher/oft_adapter.py`（`Mesh2D` 导入改为 `from linkmesh.mesh import Mesh2D`）；
- 最小修改 `src/linkmesh/mesher/triangle_wrapper.py`（删除本地 `Mesh2D` 定义，改为 `from linkmesh.mesh import Mesh2D` 重导出）；
- 最小修改 `src/linkmesh/utils/plotter.py`（`Mesh2D` 类型导入改为 `linkmesh.mesh`）；
- 按实际引用最小修改 Writer 的类型导入（`hdf5_writer.py`、`smb_writer.py`，仅类型导入，可 `TYPE_CHECKING`）；
- 新增或调整必要测试，证明新旧导入指向同一个类。

**解耦验收标准**：
1. `Mesh2D` 只有一个正式定义（位于 `src/linkmesh/mesh.py`）；
2. OFT Adapter 不再从旧 Wrapper 获取 `Mesh2D`；
3. 旧 Wrapper 重新导出同一个类（`linkmesh.mesh.Mesh2D is linkmesh.mesher.triangle_wrapper.Mesh2D`）；
4. M2 mock 测试通过；
5. 真实 DIII-D 仍生成 972 节点、1872 三角形和相同区域集合 `{1:633, 2:678, 3:561}`；
6. PNG 行为不变；
7. 不修改任何网格算法或数据。

**铁律**：**只有解耦回归通过后才开始 M3 Writer 实现。**

**涉及模块**：`src/linkmesh/mesh.py`（计划新增），`src/linkmesh/mesher/oft_adapter.py`，`src/linkmesh/mesher/triangle_wrapper.py`，`src/linkmesh/utils/plotter.py`，`src/linkmesh/writers/hdf5_writer.py`，`src/linkmesh/writers/smb_writer.py`

---

### 里程碑 M3：TRIMEG HDF5 输出验收（P0 第三步，第一战役闭环）

**当前状态**：【M3 总体未通过；契约侦察已完成，Writer 待实施（前置：M2.5 解耦）】

**目标**：将 OFT 生成的三角网格（经 `mesh_from_oft_domain()` / `generate_mesh()` 最小适配后的 `Mesh2D`）写出为 TRIMEG 可消费的 HDF5 文件（8 核心数据集，v1.11 契约），并通过 `loadfemmesh_h5.m` 读取验证。

**M3 分项状态（v1.11）**：

| 分项 | 状态 |
|---|---|
| MATLAB 消费接口侦察（`loadfemmesh_h5.m`：8 核心 + 3 可选） | PASSED |
| 两个真实样例结构侦察（core / edge） | PASSED |
| `vert`/`tria` shape、dtype 和 1-based 契约 | PASSED |
| `idxivert`/`idxevert` 拓扑契约 | PASSED |
| `Rbc`/`Zbc` 历史生成规则 | 未完全确认，当前可选（默认不写） |
| 独立 `Mesh2D` 解耦（M2.5） | 待实施 |
| M3 Writer 实现 | 待实施 |
| Python/h5py 回读 | 待实施 |
| MATLAB 消费验收 | 待实施 |
| **M3 总体** | **未通过** |
| M4 | **禁止开始** |

**M3 Writer 实施任务（前置：M2.5 解耦通过）**：只允许修改 `src/linkmesh/writers/hdf5_writer.py` 与 `tests/test_hdf5_writer.py`。Writer 职责与约束见第 9.6 节。

**M3 测试要求（v1.11）**：
- 精确检查 8 个核心路径存在；
- 确认可选 3 路径默认不存在；
- 全部核心 dtype 为 `float64`；
- 计数 shape `(1,1)`；
- `vert` shape `(N,2)`；
- `tria` shape `(T,3)` 且等于 `mesh.triangles+1`；
- 无第四列、无 region ID；
- `idxevert`/`idxivert` 的 shape、计数、唯一性、互斥和全集覆盖正确；
- 用含内部节点的受控网格验证边界提取；
- 验证 Writer 不修改输入 `Mesh2D`；
- 非法 shape、空网格、NaN/Inf、非整数连接、负索引、越界、重复节点、零面积和非流形边必须失败；
- 使用 h5py 写临时文件并回读；
- 最终在 Linux 服务器运行；
- MATLAB `loadfemmesh_h5.m` 必须成功读取核心网格，允许缺少可选 3 项的预期 warning。

**M3 验收标准（v1.11）**：
1. `python -m linkmesh --gfile <真实 DIII-D 样例> --output mesh.h5 --no-smb` 能够运行；
2. 生成的 `mesh.h5` 文件可用 `h5py` 正常打开并回读 8 个核心数据集；
3. `h5py` 读取验证：`/femmesh/vert` shape=`(N,2)`，`/femmesh/tria` shape=`(T,3)` 且为 1-based，`/femmesh/nvert` 值为 N，`/femmesh/ntria` 值为 T，核心 dtype 均为 float64；
4. `idxevert`/`idxivert` 满足互斥、全集覆盖、升序、1-based；
5. 使用 `loadfemmesh_h5.m` 在 MATLAB 中读取 `mesh.h5`，核心网格成功加载，可选 3 项缺失产生预期 warning；
6. 终端打印：`HDF5 写出完成：mesh.h5，节点数: N，三角形数: T`；
7. `tests/test_hdf5_writer.py`（v1.11 契约）全部通过。

**涉及模块**：`src/linkmesh/writers/hdf5_writer.py`（待按 v1.11 契约实现），`tests/test_hdf5_writer.py`（待按 v1.11 契约重写）

---

### 里程碑 M4：`.smb` 输出验收（P0 第四步，第二战役攻坚）

**当前状态**：【占位，禁止开始；待 M3 验收通过后开始侦察】

**目标**：在 M3 完全验收通过、网格质量确认合格后，完成 SCOREC/PUMI/M3DC1 只读侦察，由主管确认实现路线，将同一 `Mesh2D` 对象写出为 M3DC1 可消费的 `.smb` 静态网格文件。

**M4 侦察范围**：M4 必须在 M3 完整通过后，对 MCD7 样例、官方文档、ModelFile、MeshFile 和 M3DC1/SCOREC/PUMI 源码进行只读侦察，确认区域数量、D1B、几何分类、索引、文件配对、`.smb` 契约，以及 **M3DC1 是否支持单区域、是否至少需要真空区**（见第 5.1.3 节）。P0 默认三区域方案不得被外推为 M3DC1 永久固定三区域；单/两/三区域实例也不得被外推为 M3DC1 的最小区域数量要求；M3DC1 实际区域数量和 ModelFile 格式待侦察确认。

**M4 适配原则**：若 M3DC1 有额外区域、边界实体、几何分类或连续性要求（如 C1 连续性、高阶单元等），只在 LinkMesh 适配层中增加必要翻译，不得修改 OFT。

**前置条件**：
1. M3 里程碑已完全验收通过；
2. 已完成对 `m3dc1_mesh.cc`、`m3dc1_model.cc`、`m3dc1_field.cc` 的只读侦察；
3. 侦察结果已经主管确认，`.smb` 格式事实已从【待源码确认】转为【已确认事实】，实现路线已确定。

**验收标准**：
1. `python -m linkmesh --gfile sample.geqdsk --smb mesh.smb --no-hdf5` 能够运行；
2. 生成的 `mesh.smb` 文件能被 M3DC1 的 `pumi_mesh_load` 顺畅读取（无报错）；
3. M3DC1 读取后能正确识别节点数、三角形数、区域标记和边界标记；
4. 终端打印：`.smb 写出完成：mesh.smb`。

**涉及模块**：`src/linkmesh/writers/smb_writer.py`（当前为占位实现）

---

### 里程碑 M5：完整 CLI 端到端验收（P0 完成）

**当前状态**：【占位，待 M4 验收通过后开始】

**目标**：一条命令完成从 GFile 到 HDF5 + .smb + PNG 的完整转换链路。

**验收标准**：
```bash
linkmesh \
  --gfile sample.geqdsk \
  --output mesh.h5 \
  --smb mesh.smb \
  --plot mesh_check.png \
  --verbose
```
运行后：
1. 生成 `mesh.h5`（TRIMEG HDF5 格式，通过 M3 验收标准）；
2. 生成 `mesh.smb`（M3DC1 格式，通过 M4 验收标准）；
3. 生成 `mesh_check.png`（LCFS + 三角网格叠加图）；
4. 终端打印完整统计信息，无报错，无警告。

（注：M2 正式路径已拦截 `--min-angle`/`--max-area` 历史参数，M5 端到端命令不应携带非默认历史参数。）

---

## 14. 测试目录规划（M1～M3 验收测试）

### 14.1 测试文件职责

| 测试文件 | 服务里程碑 | 状态 | 核心验收内容 |
|---|---|---|---|
| `tests/test_gfile_reader.py` | M1 | 已通过（19 passed，git: f52a75f） | 验证 `read_gfile()` 能正确读取 EQDSK 文件；`GFileData` 所有字段类型与形状正确；LCFS 首尾闭合；LCFS 方向为逆时针；`current` 单位为 A（不缩放）；`gfile_reader.py` 中无手动文本解析逻辑 |
| `tests/test_oft_adapter.py` | M2（正式） | 已实现，mock 契约测试退出码 0（测试总数与耗时未记录） | 见下方三层接口测试内容；解耦后应仍通过并可验证新旧导入指向同一 `Mesh2D` 类 |
| `tests/test_triangle_wrapper.py` | M2（历史/过渡） | 历史证据保留（自动测试 36/36 通过；不能作为 OFT Adapter 正式验收替代） | 历史过渡测试，验证 Python triangle 包路线；用于证明 Mesh2D 解耦未意外破坏历史路径；当前保持文件不动，暂不删除、不扩展 |
| `tests/test_hdf5_writer.py` | M3 | 【计划重写，v1.11 契约】 | 精确检查 8 核心路径存在、3 可选路径默认不存在、核心 dtype float64、计数 shape(1,1)、vert(N,2)、tria(T,3)=triangles+1 无第四列无 region ID、idxevert/idxivert 拓扑正确、Writer 不修改输入、各类非法输入失败、h5py 回读、MATLAB 消费成功（允许可选缺失 warning） |

#### `tests/test_oft_adapter.py` 测试内容（v1.10 已实现，v1.11 保持）

【已实现】`tests/test_oft_adapter.py` 使用 mock / 受控假 OFT Domain，覆盖：

**`mesh_from_oft_domain()` 转换与校验测试（通用 N 区域核心）**：
- mock 单区域 OFT Domain：输出一个正区域 ID，**通过**（N=1 合法）；
- mock 两区域和三区域：作为代表性样例**通过**；
- mock N>3 区域（如 5 区域）：证明 Adapter **不写死区域数量**，正确通过；
- 失败场景（**失败**）：输出缺失某个 Domain 区域、出现额外区域、出现 `0`/负数或非整数区域编号、`reg` 长度与三角形数不一致、`domain.region_info` 为空、重复/非正区域 ID；
- `build_mesh()` 后最终区域 ID 时序回归（RelabelDomain：调用前临时 ID，调用后最终 ID）；
- 验证 `Mesh2D` 核心三数组 shape/dtype：`nodes` shape=`(N,2)` float64；`triangles` shape=`(T,3)` 整数、`0 <= lc < N`；`region_ids` shape=`(T,)` 整数、原样保存无重编号；
- 退化三角形检查（重复顶点、零面积、越界索引）。

**`build_oft_domain_from_gfile()` 默认策略测试**：
- 验证有壁默认策略构造 PLASMA + VACUUM + OUTER（`add_annulus` + `add_rectangle`）；
- 验证无壁默认策略构造 PLASMA + OUTER（`add_polygon` + `add_rectangle`）；
- 验证该函数**不调用** `build_mesh()`、**不转换** `pts/lc/reg`；
- 输入非法（壁 R/Z 只有其一、长度不一致、含 NaN/Inf、点数不足、退化范围、网格尺度非法）失败。

**`generate_mesh()` 组合测试**：
- 验证它**只组合前两个入口**（先 `build_oft_domain_from_gfile()` 再 `mesh_from_oft_domain()`），不复制转换逻辑或第二套区域算法。

**`_load_gs_domain_class()` 导入失败测试**：
- 验证 OFT 导入失败时抛 `ImportError` 并保留原始异常链。

**测试执行方式**：
- 测试使用 **mock**，不依赖本地 Windows 运行 OFT；
- 最终真实测试和交付验收在 **Linux 服务器正式 OFT 26.6 环境**执行，已实测退出码 0（测试总数与耗时未记录）。

**关于 `Mesh2D` 定义位置（v1.11）**：解耦后 `Mesh2D` 唯一正式定义位于 `src/linkmesh/mesh.py`，`oft_adapter.py` 与 `triangle_wrapper.py` 均从 `linkmesh.mesh` 获取同一个类；测试应验证 `linkmesh.mesh.Mesh2D is linkmesh.mesher.triangle_wrapper.Mesh2D`。

### 14.2 测试数据来源与许可证边界

**测试分层原则**：

| 测试层次 | 数据来源 | 依赖范围 | 说明 |
|---|---|---|---|
| 单元测试 | 受控合成对象或 mock（含 mock OFT Domain：单区域/两区域/三区域/N>3；含内部节点的受控网格用于 HDF5 边界提取测试） | 不依赖 `TOKAMAKER/` 源码树 | 验证 Adapter 转换与校验逻辑、HDF5 Writer 拓扑边界提取与非法输入拒绝，不需要真实 GFile 或本地 OFT |
| 集成测试（开发期） | 只读访问 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 或 `TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk`；只读访问 `docs/trimeg/` 下两个真实 HDF5 样例 | 依赖 `TOKAMAKER/` 源码树（只读）/ `docs/trimeg/`（只读） | 验证 OFT 真实读取链路与 TRIMEG HDF5 契约核对；仅在开发环境中使用，不得打包进最终交付物 |
| 交付测试 | LinkMesh 自有、来源明确、许可允许分发的样例 GFile | 不依赖 `TOKAMAKER/` 源码树 | 【计划新增，待许可确认】 |

**许可证说明**：

`TOKAMAKER/OpenFUSIONToolkit/src/tests/physics/ITER_test.eqdsk` 和 `TOKAMAKER/OpenFUSIONToolkit/src/examples/TokaMaker/DIIID/g192185.02440` 均受 `TOKAMAKER/OpenFUSIONToolkit/LICENSE`（GNU LGPL v3.0）约束。在未经主管和法务确认这些 EQDSK 样例可单独复制和再分发之前：

- 这些文件**不得**被复制到 `tests/data/` 或 `examples/` 目录。
- 这些文件**不得**作为 LinkMesh 正式自动测试或交付测试的唯一数据来源。
- 开发期集成测试可以通过只读路径访问这些文件，但必须在测试代码中明确标注为"开发期集成测试，不打包进交付物"。

**计划新增的自有样例**（待许可确认后实施）：

- `examples/sample.geqdsk`：LinkMesh 自有、来源明确、许可允许分发的示例 GFile，用于交付测试和用户示例。来源和许可证状态：【待许可确认】，本轮不创建。

**测试依赖**：
- 测试框架：`pytest>=7.0.0`
- M2/M3 单元测试可使用最小合成 `Mesh2D`、合成 OFT 返回值（`pts/lc/reg`）或 mock OFT Domain 进行，不依赖真实 GFile，不依赖本地运行 OFT。

---

## 15. 包安装与运行环境规范

### 15.1 src 布局与标准安装

【已确认事实】实际仓库采用 `src/linkmesh/` 包布局（src layout）。仓库根目录需要 `pyproject.toml` 来支持标准 Python 包安装。**`pyproject.toml` 当前尚不存在，为计划新增文件，待主管批准后创建。**

**`pyproject.toml` 的职责**：
1. 声明标准 Python 包元数据（名称、版本、描述、作者等）
2. 配置 src 布局的包发现（`packages = {find = {where = ["src"]}}`）
3. 声明控制台入口：`linkmesh = "linkmesh.cli:main"`
4. 声明正式运行依赖（与 `requirements.txt` 核心依赖保持一致）

**`pyproject.toml` 规划示例**（待实施时创建，本轮不创建）：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "linkmesh"
version = "0.1.0"
description = "轻量级托卡马克二维非结构网格转换命令行工具"
requires-python = ">=3.9"
dependencies = [
    "numpy>=1.24.0",
    "h5py>=3.8.0",
    "matplotlib>=3.7.0",
    "openfusiontoolkit==26.6",
]

[project.scripts]
linkmesh = "linkmesh.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### 15.2 `src/linkmesh/__main__.py` 规范

【已确认事实】`src/linkmesh/__main__.py` 已新建（git: 1fc04f8）。其唯一职责是使 `python -m linkmesh` 调用进入 `linkmesh.cli.main`。

**规范**：
- 文件内容极简，仅调用 `linkmesh.cli.main()`，不承载任何参数解析或业务逻辑
- 不得在 `__main__.py` 中重复定义 `argparse` 参数或任何业务函数

```python
# src/linkmesh/__main__.py
from linkmesh.cli import main

if __name__ == "__main__":
    main()
```

### 15.3 两种调用方式的等价性

【已确认事实】以下两种调用方式最终必须进入同一个 `linkmesh.cli.main` 函数，行为完全等价：

| 调用方式 | 依赖条件 | 入口路径 |
|---|---|---|
| `python -m linkmesh` | `src/linkmesh/__main__.py` 存在（已完成，git: 1fc04f8）；`src/` 在 PYTHONPATH 中或已安装 | `__main__.py` → `linkmesh.cli.main` |
| `linkmesh`（控制台命令） | `pyproject.toml` 中 `console_scripts` 已配置（计划新增）；包已通过 `pip install` 安装 | `linkmesh.cli:main` 直接调用 |

### 15.4 `pyproject.toml` 与 `requirements.txt` 的关系

- **`pyproject.toml`**（计划新增）：正式安装元数据与运行依赖依据。通过 `pip install .` 或 `pip install -e .` 安装时使用。
- **`requirements.txt`**：服务器部署用的直接依赖清单，适合 `pip install -r requirements.txt` 快速部署。
- **一致性要求**：两者的核心运行依赖和版本约束必须保持一致。当 `openfusiontoolkit` 版本约束更新时，两个文件必须同步修改。

### 15.5 PYTHONPATH 与安装规则汇总

【已确认事实】以下规则来自服务器冒烟测试实际故障排查，为铁律：

| 场景 | 规则 |
|---|---|
| 标准安装后（`pip install .`） | 最终用户不应依靠手动设置 PYTHONPATH 来发现 LinkMesh；`linkmesh` 控制台命令直接可用 |
| 开发期未安装时 | 可临时将仓库 `src/` 加入 PYTHONPATH：`export PYTHONPATH=/path/to/LinkMesh/src:$PYTHONPATH` |
| OFT 源码路径 | **绝对禁止**将 `TOKAMAKER/OpenFUSIONToolkit/src/python` 加入任何运行环境的 PYTHONPATH；该路径下的源码快照不含 `liboftpy.so`，会遮蔽正式安装包，导致 OFT 导入失败并抛出 `FileNotFoundError: Unable to load OFT shared library` |
| OFT 运行依赖 | 通过 `pip install openfusiontoolkit==26.6` 获取官方 manylinux wheel；不依赖 `TOKAMAKER/` 源码树 |
| `TOKAMAKER/` 目录 | 继续作为开发期绝对只读参考区；不参与运行时依赖；不得修改其中任何文件 |

---

## 16. 下一步任务与旧 Triangle 路径减量计划

### 16.1 Mesh2D 解耦与旧 Python Triangle 路径减量顺序

【v1.11 记录，本轮不修改或删除任何源码】M2 正式路径已由 `oft_adapter.py` 承担，但正式模块从历史 `triangle_wrapper.py` 导入核心 `Mesh2D` 数据类，存在结构耦合。v1.11 规定先解耦 `Mesh2D`，再实施 M3 Writer。

**当前暂时不得删除以下历史/过渡文件**：
- `src/linkmesh/mesher/triangle_wrapper.py`
- `tests/test_triangle_wrapper.py`

**直接原因**：
- 迁移前 `oft_adapter.py` 仍从 `triangle_wrapper.py` 导入 `Mesh2D`（结构耦合，非算法依赖）；
- `cli.py` 的历史 `_build_boundary_config()` 仍导入 `BoundaryConfig`（`BoundaryConfig` 仍位于旧 Wrapper）；
- 旧测试仍用于证明历史路径没有被解耦过程意外破坏；
- 其他模块可能仍有旧导入，需要先静态搜索和迁移。

**解耦 + 减量顺序（本轮仅记录计划，不执行）**：
1. 新建独立 `src/linkmesh/mesh.py`，作为 `Mesh2D` 唯一正式定义；
2. 更新所有正式模块导入（`oft_adapter.py`、`plotter.py`、Writer 类型导入）为 `linkmesh.mesh`；
3. `triangle_wrapper.py` 删除本地 `Mesh2D` 定义，改为 `from linkmesh.mesh import Mesh2D` 重导出（保证 `is` 同一类）；
4. 运行 OFT Adapter mock 测试和真实 DIII-D M2 回归（972 节点、1872 三角形、区域集合 `{1:633,2:678,3:561}` 不变）；
5. 完成并验收 M3 Writer（第 9、13 节 M3）；
6. 删除 CLI 历史 `BoundaryConfig` 构造逻辑（`_build_boundary_config()`/`_resample_closed_curve()`）；
7. 全仓库静态搜索确认无正式引用 `triangle_wrapper`/`BoundaryConfig`；
8. 再单独删除旧 Wrapper（`triangle_wrapper.py`）和其专属测试（`test_triangle_wrapper.py`）；
9. 视情况在依赖清单中移除历史 `triangle` 依赖（与第 12.1 节一并处理）。

**【铁律】** 不得在 M3 Writer 实现任务中顺带删除旧路径。删除旧 Wrapper 属于 M3 验收之后的独立减量步骤。

### 16.2 实施顺序铁律（v1.11）

后续必须严格按以下顺序执行，禁止跳序或合并：

1. **蓝图 v1.11 完成**（本轮）；
2. **实施独立 Mesh2D 解耦**（M2.5，见第 16.1 节步骤 1–3）；
3. **运行 M2 mock 和真实 DIII-D 回归**（确认 M2 行为不变）；
4. **实施 HDF5 Writer**（按第 9 节 v1.11 契约，仅改 `hdf5_writer.py` 与 `tests/test_hdf5_writer.py`）；
5. **运行 pytest 和 h5py 回读**；
6. **运行真实 DIII-D `Mesh2D → HDF5`**；
7. **使用 MATLAB `loadfemmesh_h5.m` 消费**（核心网格成功加载，允许可选 3 项缺失 warning）；
8. **User 验收后更新 History**；
9. **M3 完整通过后才能进入 M4**。

**每一步的执行都属于后续独立任务，必须在对应任务中单独裁决与验证，不在本轮实施。**

### 16.3 本轮不实施与禁止事项

本轮 v1.11 仅更新蓝图，不实施任何源码。禁止：
- 修改任何源码、测试、History、OFT、TRIMEG 样例或其他文件；
- 运行任何代码、测试或格式化工具；
- 宣称 M3 已通过；
- 修改 M1/M2 已验收行为；
- 修改 M4 `.smb` 未确认契约；
- 新增通用区域配置文件、插件系统、后端抽象、Protocol/抽象基类或第二网格引擎；
- 引入 CLI 计算域选择参数（未来如需，另行更新蓝图，见第 7.2.3 节）。

若新增测试路径或 `Mesh2D` 定义位置与当前蓝图目录规则冲突，应在后续蓝图更新中明确最终位置；若无法确认，跳过该具体位置并在报告中列为待 User 裁决，不得整体停机。

---

## 17. 蓝图更新纪律

本文档是 LinkMesh 项目的单事实真理源。以下情况必须先更新本文档，再进入代码实现：

1. 新增或删除任何模块文件；
2. 修改任何数据结构的字段定义（`GFileData`、`BoundaryConfig`、`Mesh2D`）；
3. 修改区域标记或边界标记的整数约定；
4. 修改 HDF5 文件结构或数据集路径名；
5. 确认 `.smb` 格式的任何细节（将【待源码确认】转为【已确认事实】）或确认实现路线；
6. 新增任何 CLI 参数（包括未来的计算域选择参数）；
7. 调整任何里程碑的验收标准；
8. **修改 OFT API 的调用方式（如从 `GEQDSKEquilibrium` 切换到 `read_geqdsk` 或反之，或新增/移除 OFT 依赖）**；
9. **修改 `openfusiontoolkit` 版本约束**（需同步更新 `pyproject.toml` 和 `requirements.txt`）；
10. **修改 `src/linkmesh/__main__.py` 的职责或内容**；
11. **修改 `pyproject.toml` 中的控制台入口或包发现配置**；
12. **修改 P0 区域方案或全局区域传递契约**；
13. **修改区域种子几何条件或失败原则**；
14. **将任何【待运行验证】事项更新为【已确认事实】**（必须有直接运行证据和 User 确认）；
15. **修改 OFT 网格生成路线（如从历史/过渡代码切换到 OFT gs_Domain 路线，或决定废弃历史/过渡代码）**；
16. **修改 `mesher/oft_adapter.py` 的三层接口职责边界或最小适配契约**；
17. **迁移 `Mesh2D` 定义位置或修改其核心三数组契约**（v1.11 已批准迁至 `src/linkmesh/mesh.py`，实施细节变更仍需更新蓝图）；
18. **修改通用 N 区域校验规则或单区域 plasma-only 合法性定位**；
19. **修改当前 GFile 默认区域策略（有壁三区域 / 无壁两区域）**；
20. **将 TRIMEG/M3DC1 单区域支持从待证据/待源码确认转为已确认事实**（必须有直接证据）；
21. **删除旧 Python Triangle 路径（`triangle_wrapper.py` / `test_triangle_wrapper.py`）或迁移其中的 `BoundaryConfig` 定义**（按第 16.1 节减量顺序）；
22. **修改 M3 TRIMEG HDF5 契约（8 核心数据集磁盘 shape/dtype/1-based 索引、`idxevert/idxivert` 拓扑规则、3 可选数据集事实边界）**（必须有新的真实样例或生成端源码直接证据）；
23. **将 `Rbc/Zbc/nbcRZ` 历史生成规则从"未完全确认/可选"转为"必需/已确认"**（必须有生成端直接证据）。

**蓝图更新流程**：
1. Aider 在对话中向主管提出蓝图迭代修改建议；
2. 主管确认后，Aider 更新本文档；
3. 主管 git commit 本文档更新；
4. Aider 方可开始编写对应的业务代码。
