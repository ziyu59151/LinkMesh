# LinkMesh 项目目录树

- 文档主受众：Human-facing
- 知识库用途：人类导读
- 文档状态：当前有效
- 最高依据：LinkMesh_Architecture_Plan.md
- 事实边界：本文档是面向人类主管和研究员的轻量导读，不承载任何正式技术蓝图或接口定义。目录结构与职责描述以 `LinkMesh_Architecture_Plan.md` 为最终裁决依据，本文档仅作快速定向参考。
- 主要用途：帮助人类主管和初学者研究员快速理解 LinkMesh 仓库的目录布局、各模块的直观职责，以及应该去哪里找什么。

> 如果你是 Aider 或 AI 代理，请优先阅读 `CONTEXT.md` 和 `LinkMesh_Architecture_Plan.md`，本文档不是你的执行依据。

---

## 1. 这个项目是什么？

LinkMesh 是一个**轻量级独立命令行工具**，专门用于把托卡马克等离子体平衡文件（GFile/EQDSK）转换成物理模拟程序可以直接读取的静态网格文件。

用一句话说：**给它一个平衡文件，它帮你生成网格，然后导出给 TRIMEG 或 M3DC1 用。**

整个工具链路如下：

```text
GFile/EQDSK 平衡文件
        ↓  读取边界
readers/gfile_reader.py
        ↓  生成二维三角网格
mesher/triangle_wrapper.py
        ↓  导出静态网格文件
writers/hdf5_writer.py   →  TRIMEG 用的 HDF5 文件
writers/smb_writer.py    →  M3DC1 用的 .smb 二进制文件
utils/plotter.py         →  可视化自检图（可选）
```

---

## 2. 顶层目录结构

```text
LinkMesh/
├── CONTEXT.md                       # [最高行为宪法] 敏捷开发工作流与纪律规范
├── LinkMesh_Architecture_Plan.md    # [最高技术蓝图] AI 单事实真理源与实操图纸
├── Project_Tree.md                  # [当前文件] 项目全局目录树与人类导读
├── History.md                       # [记忆沉淀] MVP 战术战果单向追加归档
├── requirements.txt                 # Python 依赖清单（pip install -r 安装）
├── .venv/                           # Python 虚拟环境（不提交到 Git）
│
├── readers/                         # 平衡数据读取 (GFile/EQDSK 等文本配置)
│   ├── __init__.py
│   └── gfile_reader.py
│
├── mesher/                          # 2D 网格底座封装 (开源 Triangle 库)
│   ├── __init__.py
│   └── triangle_wrapper.py
│
├── writers/                         # 静态网格导出 (攻坚 TRIMEG HDF5 & Pumi .smb)
│   ├── __init__.py
│   ├── hdf5_writer.py
│   └── smb_writer.py
│
├── utils/                           # 辅助自检工具 (如基于 matplotlib 的网格画图)
│   ├── __init__.py
│   └── plotter.py
│
├── cli.py                           # 命令行参数解析与转换执行流水线入口
│
├── tests/                           # 单元测试
│   ├── test_gfile_reader.py
│   ├── test_triangle_wrapper.py
│   ├── test_hdf5_writer.py
│   └── test_smb_writer.py
│
├── examples/                        # 示例文件与运行脚本
│   ├── sample.geqdsk
│   └── run_example.sh
│
├── docs/                            # [技术情报区] 调研报告与 RAG 规范文档
│   ├── linkmesh/                    # 本地前哨开发清单与 RAG 规范
│   ├── m3dc1/                       # M3DC1 调研报告与 .smb 接口参考事实
│   └── tokamaker/                   # TokaMaker 封装架构与三角剖分参考
│
├── M3DC1/                           # [绝对只读参考区] M3DC1 官方/Scorec 接口源码
└── TOKAMAKER/                       # [绝对只读参考区] TokaMaker 及其核心源码
```

---

## 3. 各模块直观职责说明

### 控制文档（根目录）

| 文件 | 一句话说明 |
|---|---|
| `CONTEXT.md` | 项目最高行为宪法。规定了 Aider 的角色、开发纪律、禁止事项和协作规范。人类主管和 AI 都必须遵守。 |
| `LinkMesh_Architecture_Plan.md` | 项目最高技术蓝图。所有模块接口、数据结构、输出格式和验收标准都在这里定义。Aider 写代码前必须查阅。 |
| `History.md` | 战术战果归档。每攻克一个里程碑，就在这里追加一条记录。 |
| `requirements.txt` | Python 依赖清单。运行 `pip install -r requirements.txt` 安装所有依赖。 |

### `readers/`：读取平衡文件

这个模块负责读取托卡马克平衡文件（GFile/EQDSK），提取出网格生成所需的边界信息。

- **`gfile_reader.py`**：读取 EQDSK 格式的平衡文件，提取最后闭合磁面（LCFS）坐标、第一壁坐标、磁轴位置等信息，返回一个 `GFileData` 数据对象。

### `mesher/`：生成二维三角网格

这个模块负责调用开源 Triangle 库，把边界点集转换成二维非结构化三角网格。

- **`triangle_wrapper.py`**：封装 `triangle` Python 包的调用细节，接收边界配置，返回包含节点坐标、三角形连接表、区域标记和边界标记的 `Mesh2D` 数据对象。

### `writers/`：导出静态网格文件

这个模块负责把内存中的 `Mesh2D` 对象写出为目标物理求解器可以读取的文件格式。这是 LinkMesh 最核心的攻坚方向。

- **`hdf5_writer.py`**：按 TRIMEG 标准写出 HDF5 格式的静态网格文件（`.h5`）。
- **`smb_writer.py`**：按 PUMI 协议写出 M3DC1 可消费的二进制静态网格文件（`.smb`）。这是难度最高的部分，需要逆向分析 PUMI 的私有二进制格式。

### `utils/`：辅助自检工具

- **`plotter.py`**：用 `matplotlib` 绘制 LCFS 边界与生成三角网格的叠加图，输出 PNG 自检图，方便人眼快速判断网格质量是否正常。

### `cli.py`：命令行入口

整个工具的入口。解析用户输入的命令行参数，按顺序调用 reader → mesher → writer，完成从平衡文件到网格文件的完整转换。

典型用法：

```bash
linkmesh \
  --gfile sample.geqdsk \
  --output mesh.h5 \
  --smb mesh.smb \
  --min-angle 20 \
  --max-area 0.001 \
  --plot mesh_check.png \
  --verbose
```

### `docs/`：技术情报区

存放调研报告、架构白皮书和 RAG 规范文档，不包含任何业务源码。

| 子目录 | 内容 |
|---|---|
| `docs/linkmesh/` | LinkMesh 本地开发清单、RAG 友好化文档规范（`RAG_Friendly_Documentation_Guide.md`）等。 |
| `docs/m3dc1/` | M3DC1 宏观架构白皮书、`.smb` 接口调研报告、源码侦察清单等。 |
| `docs/tokamaker/` | TokaMaker/OFT 网格生成链路白皮书、Triangle 集成规范等。 |

### `M3DC1/` 和 `TOKAMAKER/`：只读参考区

这两个目录存放外部参考工程的源码，**绝对只读，严禁修改**。

- **`M3DC1/`**：M3DC1 官方源码与 `m3dc1_scorec` 接口库。LinkMesh 通过只读侦察这里的代码来逆向推导 `.smb` 文件格式。
- **`TOKAMAKER/`**：TokaMaker/OpenFUSION Toolkit 源码。LinkMesh 通过只读侦察这里的代码来学习 Triangle 库的调用方式。

---

## 4. MVP 开发里程碑（当前进度参考）

LinkMesh 按以下顺序逐步攻克各个里程碑：

| 里程碑 | 目标 | 核心模块 |
|---|---|---|
| M1 | 从 GFile 提取 LCFS 边界并可视化 | `readers/gfile_reader.py`，`utils/plotter.py` |
| M2 | 从 LCFS 边界生成二维三角网格并可视化 | `mesher/triangle_wrapper.py`，`utils/plotter.py` |
| M3 | 将三角网格写出为 TRIMEG HDF5 文件 | `writers/hdf5_writer.py` |
| M4 | 将三角网格写出为 M3DC1 可消费的 `.smb` 文件 | `writers/smb_writer.py` |
| M5 | 一条命令完成完整端到端转换链路 | `cli.py` + 全部模块 |

详细验收标准请查阅 `LinkMesh_Architecture_Plan.md` 第 11 节。

---

## 5. 阅读建议

如果你是**人类主管或研究员**，建议按以下顺序阅读：

```text
Project_Tree.md（当前文件，快速定向）
        ↓
CONTEXT.md（了解项目纪律与协作规范）
        ↓
LinkMesh_Architecture_Plan.md（深入理解技术蓝图与接口定义）
```

如果你是 **Aider 或 AI 代理**，请直接跳转：

```text
CONTEXT.md → LinkMesh_Architecture_Plan.md
```

本文档（`Project_Tree.md`）不是 Aider 的执行依据，仅供人类快速定向使用。
