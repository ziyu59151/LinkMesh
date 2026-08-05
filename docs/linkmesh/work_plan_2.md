# LinkMesh 服务器部署与 Release 管理讨论稿

> 文档用途：与课题组老师讨论 LinkMesh 在组内 Linux 服务器上的安装、版本管理、更新、回退和用户使用方式。  
> 当前目标：为组员提供尽可能简单的统一前端，隐藏 Python、OFT 和 helper 的环境细节。  
> 当前状态：部署方案已形成建议，服务器共享目录、权限、维护责任和外部依赖来源仍需会议确认。

---

## 1. 已确认事实

### 1.1 LinkMesh 的运行依赖

当前 LinkMesh 的运行环境相对简单，主要包括：

```text
Python
+
LinkMesh Python 包
+
OFT/TokaMaker 相关 Python 依赖
+
linkmesh-scorec-helper
+
helper 所需的 SCOREC/PUMI、MPI 和系统运行库
```

其中：

- LinkMesh 主程序是 Python 包；
- OFT/TokaMaker 提供当前正式网格生成链所需能力；
- `linkmesh-scorec-helper` 是 M3D-C1/SMB 输出链所需的原生 helper；
- 普通组员不应自行配置这些依赖；
- 普通组员不应自行编译 helper；
- 普通组员不应依赖维护者个人目录；
- 普通组员不应手动设置 `PYTHONPATH`；
- 普通组员不应手动设置 helper 路径。

### 1.2 `linkmesh.in` 的相对路径行为

已经通过实际运行确认：

> `linkmesh.in` 中的相对路径以 `linkmesh.in` 所在目录为基准解析。

例如，Case 目录为：

```text
/home/user/cases/case_001/
├── linkmesh.in
└── input.g
```

如果 `linkmesh.in` 中的 SMB 输出只写文件名：

```text
mesh.smb
```

则输出位置为：

```text
/home/user/cases/case_001/mesh.smb
```

也就是与 `linkmesh.in` 位于同一目录。

如果配置中写：

```text
mesh/mesh.smb
```

则输出位置为：

```text
/home/user/cases/case_001/mesh/mesh.smb
```

这一行为有利于 Case 的复制、迁移、归档和复现，因此正式模板应优先使用相对路径，避免个人绝对路径。

---

## 2. 推荐的唯一主要管理方案

推荐采用：

```text
共享只读运行环境
        +
统一 linkmesh 前端命令
        +
版本化 Release
        +
用户个人 Case 目录
```

整体架构如下：

```text
                     维护者
                        |
                        | 安装、更新、验证
                        v
        +--------------------------------------+
        | 组内共享 LinkMesh 运行环境           |
        |                                      |
        | Python + OFT + LinkMesh + helper     |
        |                                      |
        | 普通用户只读                         |
        +------------------+-------------------+
                           |
                           | 暴露统一命令
                           v
                     linkmesh
                           |
             +-------------+-------------+
             |                           |
             v                           v
      用户 A 的 Case                用户 B 的 Case
      ~/cases/case_001/             ~/cases/case_002/
      ├── linkmesh.in               ├── linkmesh.in
      ├── 输入文件                   ├── 输入文件
      └── 输出文件                   └── 输出文件
```

组员只需要：

```bash
cd ~/cases/case_001
linkmesh --config linkmesh.in
```

组员不需要：

```bash
source /path/to/venv/bin/activate
export PYTHONPATH=...
export LINKMESH_SCOREC_HELPER=...
python -m linkmesh ...
cmake ...
make ...
```

这个方案的目标是：

```text
对维护者：
    保留完整环境、版本和发布控制

对普通组员：
    只暴露 linkmesh 前端命令和 linkmesh.in 配置接口
```

这里的“只暴露前端”是指隐藏安装和调用细节，并不意味着通过 Linux 文件权限完全隐藏程序文件。普通组员可以拥有共享环境的读取和执行权限，但不拥有修改权限。

---

## 3. 用户使用方式

### 3.1 用户只管理自己的 Case

每个用户在个人目录下建立自己的 Case，例如：

```text
/home/user/cases/case_001/
├── linkmesh.in
├── input/
│   ├── g65402
│   └── boundary.txt
├── output/
└── logs/
```

也可以采用更简单的扁平结构：

```text
/home/user/cases/case_001/
├── linkmesh.in
├── g65402
├── boundary.txt
├── femmesh.h5
├── mesh.smb
├── mesh.png
└── linkmesh.log
```

LinkMesh 本身不复制进 Case。以下内容也不放进 Case：

```text
LinkMesh 源码
Python 环境
OFT 安装
SCOREC/PUMI 安装
linkmesh-scorec-helper
CMake 构建目录
```

Case 中只保存：

```text
linkmesh.in
+
当前输入方式需要的物理输入文件
+
生成结果
+
必要的运行日志
```

### 3.2 最简使用命令

用户进入 Case 目录：

```bash
cd ~/cases/case_001
linkmesh --config linkmesh.in
```

由于配置中的相对路径以 `linkmesh.in` 所在目录为基准，因此即使从其他目录调用，也应能保持同一套 Case 路径语义。例如：

```bash
linkmesh --config ~/cases/case_001/linkmesh.in
```

只要 `linkmesh.in` 内部使用正确的相对路径，输入和输出仍以：

```text
~/cases/case_001/
```

为基础。

### 3.3 推荐的 Case 结构

对于希望长期保存和复现实验的 Case，推荐使用：

```text
case_001/
├── linkmesh.in
├── input/
│   ├── geometry.gfile
│   └── boundary.txt
├── output/
│   ├── mesh.txt
│   ├── mesh.h5
│   ├── mesh.smb
│   └── mesh.png
└── logs/
    └── linkmesh.log
```

对应配置使用相对路径：

```text
输入：
    input/geometry.gfile

输出：
    output/mesh.txt
    output/mesh.h5
    output/mesh.smb
    output/mesh.png
```

这样整个 Case 目录可以整体复制到其他用户目录或归档位置，不需要修改配置中的个人路径。

---

## 4. 共享环境目录设计

会议上需要与老师确认实际的组内共享软件根目录。以下使用占位符：

```text
<GROUP_SOFTWARE_ROOT>
```

推荐结构：

```text
<GROUP_SOFTWARE_ROOT>/
└── linkmesh/
    ├── releases/
    │   ├── 0.1.0/
    │   │   ├── env/
    │   │   ├── manifest/
    │   │   └── validation/
    │   │
    │   ├── 0.2.0/
    │   │   ├── env/
    │   │   ├── manifest/
    │   │   └── validation/
    │   │
    │   └── 0.3.0/
    │       ├── env/
    │       ├── manifest/
    │       └── validation/
    │
    ├── current -> releases/0.2.0
    │
    └── bin/
        └── linkmesh
```

各部分职责：

```text
releases/
    保存彼此独立、不可原地修改的版本

releases/<version>/env/
    保存该版本完整运行环境：
    Python、OFT、LinkMesh 和 helper

releases/<version>/manifest/
    保存源码版本、依赖版本和构建信息

releases/<version>/validation/
    保存安装检查、测试和真实案例验证证据

current
    指向当前推荐稳定版本

bin/linkmesh
    对普通组员暴露的统一前端命令
```

---

## 5. 统一前端命令

### 5.1 前端入口目标

组员统一执行：

```bash
linkmesh --config linkmesh.in
```

`linkmesh` 前端入口内部负责：

1. 找到当前稳定 Release；
2. 使用该 Release 的 Python；
3. 使用该 Release 中安装的 LinkMesh；
4. 使用与该 Release 配套的 OFT；
5. 定位与该 Release 配套的 helper；
6. 保留用户当前工作目录；
7. 将参数原样传递给 LinkMesh CLI；
8. 将标准输出、标准错误和退出码原样返回。

前端入口不应修改用户的全局 Python 环境，也不应要求用户激活虚拟环境。

### 5.2 前端包装器的逻辑示意

包装器的逻辑可以概括为：

```text
用户执行：
    linkmesh --config linkmesh.in

包装器：
    找到 <GROUP_SOFTWARE_ROOT>/linkmesh/current
        |
        +--> 使用 current/env 中的 Python
        |
        +--> 定位 current/env 中的 helper
        |
        +--> 调用 python -m linkmesh
        |
        +--> 保留用户传入的全部参数
        |
        +--> 返回 LinkMesh 的退出码
```

示意脚本如下，实际路径和环境变量需要在服务器方案确认后确定：

```bash
#!/usr/bin/env bash
set -e

LINKMESH_ROOT="<GROUP_SOFTWARE_ROOT>/linkmesh/current"
LINKMESH_PYTHON="$LINKMESH_ROOT/env/bin/python"
LINKMESH_HELPER="$LINKMESH_ROOT/env/bin/linkmesh-scorec-helper"

export LINKMESH_SCOREC_HELPER="$LINKMESH_HELPER"

exec "$LINKMESH_PYTHON" -m linkmesh "$@"
```

该脚本只是部署接口示意，不是当前已经确认的服务器脚本。

正式包装器还应检查：

```text
current 是否存在
Python 是否可执行
LinkMesh 是否可导入
helper 是否存在并可执行
必要运行库是否可找到
```

如果检查失败，应输出明确错误并停止，而不是静默使用维护者个人环境。

### 5.3 用户如何找到 `linkmesh`

建议由管理员或组内维护者将以下目录加入组员统一的 `PATH`：

```text
<GROUP_SOFTWARE_ROOT>/linkmesh/bin
```

之后组员直接执行：

```bash
linkmesh --config linkmesh.in
```

如果服务器暂时不能修改组员统一的 `PATH`，可以先使用完整路径：

```bash
<GROUP_SOFTWARE_ROOT>/linkmesh/bin/linkmesh \
  --config linkmesh.in
```

长期目标仍应是直接使用：

```bash
linkmesh --config linkmesh.in
```

---

## 6. 最简 Release 的组成

### 6.1 源码发布材料

用于在服务器创建新 Release 的最简源码材料应包含：

```text
linkmesh-source/
├── src/
│   └── linkmesh/
├── native/
│   └── linkmesh_scorec_helper/
├── pyproject.toml
├── requirements.txt
├── README.md
├── LinkMesh_Architecture_Plan.md
├── examples/
│   └── linkmesh.in
└── tests/
```

其中：

```text
src/linkmesh/
    LinkMesh Python 源码

native/linkmesh_scorec_helper/
    helper 源码和 CMake 配置

pyproject.toml
    Python 包定义和正式安装入口

requirements.txt
    可由 Python 包管理器安装的依赖

README.md
    安装、运行和维护说明

LinkMesh_Architecture_Plan.md
    当前有效技术蓝图

examples/linkmesh.in
    面向用户的正式配置模板

tests/
    发布前内部检查
```

### 6.2 安装后的最简 Release

普通组员实际使用的 Release 不需要直接操作源码。安装后的版本至少应包含：

```text
releases/<version>/
├── env/
│   ├── bin/
│   │   ├── python
│   │   ├── linkmesh
│   │   └── linkmesh-scorec-helper
│   └── lib/
│       └── python.../
│           └── site-packages/
│               ├── linkmesh/
│               └── OFT 及其他 Python 依赖
│
├── manifest/
│   ├── RELEASE_MANIFEST.md
│   ├── python-packages.txt
│   ├── build-environment.txt
│   └── checksums.txt
│
└── validation/
    ├── install-check.log
    ├── cli-help.txt
    ├── test.log
    └── case-validation/
```

普通组员只通过统一的 `linkmesh` 命令间接使用其中的环境。

### 6.3 不应放入 Release 的内容

以下内容不属于正式 Release：

```text
个人 `.venv`
Aider 历史和缓存
IDE 配置
Python 缓存
临时 CMake 构建目录
运行生成的临时文件
个人绝对路径
密码、Token 和密钥
未确认许可证的外部参考源码
开发时保存的无关日志
```

M3DC1 和 TOKAMAKER 外部参考源码不应因为开发时用于侦察，就自动进入 LinkMesh Release。

正式 Release 中只安装 LinkMesh 实际运行需要、且允许部署的依赖。

---

## 7. 依赖管理

### 7.1 requirements.txt 的职责

`requirements.txt` 可以记录能够通过 Python 包管理器可靠安装的依赖，例如：

```text
numpy
h5py
matplotlib
triangle
OFT 对应的可安装 Python 包
```

建议在确定兼容版本后固定版本号，例如：

```text
numpy==<verified-version>
h5py==<verified-version>
matplotlib==<verified-version>
triangle==<verified-version>
```

不能在没有服务器验证的情况下任意填写版本号。

### 7.2 OFT 是否需要打包进 LinkMesh

原则上不需要把 OFT 源码直接复制进 LinkMesh 源码包。

更合理的方式是：

```text
LinkMesh 源码包
    不内嵌 OFT 源码

Release 环境
    安装经过验证的 OFT 版本

依赖清单
    记录 OFT 的来源、版本和安装方式
```

如果 OFT 可以通过稳定的 Python 包渠道安装，可以写入：

```text
requirements.txt
```

如果 OFT 需要独立安装、Conda 安装、源码构建或服务器预装环境，则应在 Release 构建流程中单独处理，而不能假设：

```bash
python -m pip install -r requirements.txt
```

一定能够完整安装 OFT。

决定 OFT 是否写进 `requirements.txt` 的标准是：

```text
1. 安装来源明确；
2. 版本明确；
3. 服务器可重复安装；
4. 不依赖开发者本地源码目录；
5. LinkMesh 使用的接口已经验证；
6. 正式运行环境可以从源码目录外导入；
7. 与当前 Triangle 调用链一致。
```

### 7.3 requirements.txt 不能覆盖的依赖

以下内容不能仅依靠 `requirements.txt` 管理：

```text
MPI
SCOREC/PUMI
C/C++ 编译器
CMake
helper 的编译和安装
系统运行库
与服务器 ABI 相关的依赖
```

因此，依赖应分为：

```text
Python 层：
    pyproject.toml
    requirements.txt

原生构建层：
    CMake
    编译器
    MPI
    SCOREC/PUMI

运行环境层：
    服务器模块或共享运行库
    动态库搜索路径
    helper 可执行文件
```

### 7.4 当前最简依赖管理建议

LinkMesh 当前环境较简单，建议优先保持：

```text
pyproject.toml
+
requirements.txt
+
RELEASE_MANIFEST.md
```

其中：

```text
pyproject.toml
    定义 LinkMesh Python 包和 CLI

requirements.txt
    定义可重复安装的 Python 依赖

RELEASE_MANIFEST.md
    记录 OFT、MPI、SCOREC/PUMI、编译器、CMake 和 helper 信息
```

没有必要在服务器方案尚未确认前同时建立大量重复的依赖文件。

---

## 8. 服务器安装流程

### 8.1 安装原则

每个版本都安装到新的独立目录：

```text
releases/0.1.0/
releases/0.2.0/
releases/0.3.0/
```

禁止把新版本直接覆盖到旧版本环境中。

禁止在稳定 Release 上直接执行：

```bash
pip install --upgrade ...
conda update ...
替换 helper 二进制
修改已安装的 LinkMesh 源码
```

稳定 Release 应视为不可变版本。

### 8.2 新版本安装流程

```text
确定源码版本
    |
    v
创建新的 releases/<version>/
    |
    v
创建独立 Python 环境
    |
    v
安装经过确认的 OFT 和 Python 依赖
    |
    v
安装 LinkMesh Python 包
    |
    v
编译并安装 linkmesh-scorec-helper
    |
    v
从源码目录外运行检查
    |
    v
运行自动化测试
    |
    v
运行真实 Case
    |
    v
保存构建与验证记录
    |
    +---- 验证失败：不切换 current
    |
    +---- 验证通过：切换 current
```

### 8.3 Python 包安装

正式 Release 应采用普通安装：

```bash
python -m pip install .
```

不建议采用开发模式：

```bash
python -m pip install -e .
```

原因是开发模式会持续依赖源码目录，更适合个人开发环境，不适合组内稳定共享环境。

安装完成后必须从源码目录外验证：

```text
import linkmesh
python -m linkmesh --help
linkmesh --config /path/to/case/linkmesh.in
```

正式 Release 不应依赖：

```text
PYTHONPATH
LinkMesh 源码工作树
开发者个人 `.venv`
个人 CMake build 目录
TOKAMAKER 参考源码路径
```

### 8.4 helper 安装

helper 建议使用仓库外构建目录，并安装到对应 Release 的环境中：

```text
源码：
    <source>/native/linkmesh_scorec_helper/

构建：
    <temporary-build>/linkmesh-scorec-helper/

安装：
    releases/<version>/env/bin/linkmesh-scorec-helper
```

构建关系：

```text
helper 源码
    |
    v
CMake configure
    |
    v
CMake build
    |
    v
CMake install
    |
    v
Release env/bin/linkmesh-scorec-helper
```

普通用户不应接触构建目录。

统一前端应自动定位同一 Release 中的 helper。

---

## 9. 版本更新与回退

### 9.1 更新方式

假设当前稳定版本是：

```text
0.1.0
```

新版本是：

```text
0.2.0
```

更新时保留两个版本：

```text
releases/
├── 0.1.0/
└── 0.2.0/
```

新版本验收前：

```text
current -> releases/0.1.0
```

新版本验收通过后：

```text
current -> releases/0.2.0
```

组员命令保持不变：

```bash
linkmesh --config linkmesh.in
```

### 9.2 回退方式

如果新版本出现问题，只需要恢复：

```text
current -> releases/0.1.0
```

不需要：

```text
重新安装旧环境
要求用户修改 Case
要求用户修改 linkmesh.in
要求用户修改命令
```

### 9.3 并发运行注意事项

统一入口不能只在启动时不断动态访问一个可能变化的 `current` 路径。

包装器启动时应先解析 `current` 指向的实际 Release，再使用该固定路径启动本次进程。这样即使运行期间管理员切换 `current`，已经启动的任务也继续使用原来的版本。

正式生产任务还应记录实际使用的 LinkMesh 版本，例如在日志中输出：

```text
LinkMesh version: 0.2.0
Release path: <GROUP_SOFTWARE_ROOT>/linkmesh/releases/0.2.0
```

如果某个长期计算流程必须严格复现，可以允许高级用户使用具体版本入口：

```bash
<GROUP_SOFTWARE_ROOT>/linkmesh/releases/0.2.0/env/bin/linkmesh \
  --config linkmesh.in
```

但普通交互式使用仍统一采用：

```bash
linkmesh --config linkmesh.in
```

---

## 10. 权限管理

### 10.1 普通用户权限

普通组员需要：

```text
共享 Release：
    读取权限
    执行权限
    无修改权限

个人 Case：
    读取权限
    写入权限
    创建和删除自己的输出文件
```

### 10.2 维护者权限

LinkMesh 维护者需要：

```text
创建新 Release
安装依赖
安装 LinkMesh
构建并安装 helper
保存验证记录
切换 current
执行回退
维护统一 linkmesh 包装器
```

### 10.3 不应发生的情况

普通用户不应：

```text
修改共享 Python 环境
更新共享 OFT
替换共享 helper
在稳定 Release 中执行 pip install
直接修改 current 指向
把运行输出写进共享 Release
```

维护者也不应直接在当前稳定 Release 中调试和修改源码。

开发调试应在个人开发环境进行；共享 Release 只接收已经确定并验证的版本。

---

## 11. linkmesh.in 的正式模板

### 11.1 模板目标

需要整理一份面向普通组员的正式模板，例如：

```text
examples/linkmesh.in
```

或：

```text
examples/linkmesh.in.example
```

模板需要做到：

```text
字段少而明确
默认值合理
相对路径可迁移
参数与 CLI 一致
不包含开发者个人路径
不包含尚未开放的功能
不宣称未验证的能力
```

### 11.2 路径原则

已经确认：

> 所有相对输入和输出路径以 `linkmesh.in` 所在目录为基础。

因此模板中应优先使用：

```text
input/geometry.gfile
output/mesh.h5
output/mesh.smb
output/mesh.png
```

避免：

```text
/home/lxzeng/...
/home/某个用户/...
D:/project/...
开发环境的 build 路径
helper 绝对路径
OFT 源码路径
```

### 11.3 不同输入方式的 Case

不同输入方式需要不同物理文件，但使用流程应保持一致。

例如：

```text
GFile 输入 Case：
case_gfile/
├── linkmesh.in
└── input/
    └── equilibrium.gfile
```

```text
二维边界数组输入 Case：
case_array/
├── linkmesh.in
└── input/
    └── boundary.txt
```

用户始终执行：

```bash
linkmesh --config linkmesh.in
```

不同输入方式的差异由 `linkmesh.in` 和对应物理输入文件表达，不应要求用户切换 Python 环境或更换执行程序。

---

## 12. CLI 精简原则

明晚会议前，开发重点是精简和稳定用户前端。

需要检查：

```bash
linkmesh --help
```

CLI 应只展示当前正式支持、能够验证的功能。

需要删除或隐藏：

```text
尚未实现的参数
仅为开发调试存在的参数
与当前正式数据链无关的功能
未获得直接证据的外部接口
未在蓝图中开放的高级能力
容易导致用户误用的重复入口
```

CLI 应围绕：

```text
选择配置文件
    |
    v
读取物理输入
    |
    v
生成二维三角网格
    |
    v
写出目标格式
    |
    v
生成 PNG 几何检查
```

对于组内普通用户，最主要的正式入口应收敛为：

```bash
linkmesh --config linkmesh.in
```

其他 CLI 显式参数可以用于维护、调试或覆盖配置，但不应让普通用户必须拼接大量参数才能完成标准任务。

---

## 13. 发布验证

每个新 Release 至少应完成以下验证。

### 13.1 安装验证

```text
1. 独立环境创建成功；
2. Python 版本符合要求；
3. OFT 可以从 Release 环境导入；
4. LinkMesh 可以从源码目录外导入；
5. `linkmesh --help` 可以运行；
6. helper 存在且具有执行权限；
7. helper 所需动态库可以找到；
8. 普通用户对 Release 只有读取和执行权限。
```

### 13.2 Case 验证

```text
1. 创建独立测试 Case；
2. 将 linkmesh.in 放入 Case；
3. 使用相对输入路径；
4. 使用相对输出路径；
5. 从 Case 目录运行统一 linkmesh 命令；
6. 输出写入 Case，而不是共享环境；
7. 记录使用的 Release 版本；
8. 检查 TXT、HDF5、SMB 和 PNG 等实际目标输出。
```

### 13.3 验证状态分层

需要区分：

```text
DESIGNED
    已完成方案设计

IMPLEMENTED
    已完成代码或安装实现

GENERATED
    已生成目标文件

STRUCTURALLY CHECKED
    已检查文件结构、shape、dtype 或基础格式

DELIVERED
    已交付外部测试者

LOADED
    已由外部程序成功读取

INITIALIZED
    外部程序已完成初始化

TIME-STEPPED
    已完成明确时间推进

STABILITY-VALIDATED
    已完成规定时长或工况稳定性检查

PHYSICALLY VALIDATED
    物理结果已得到确认
```

不能因为网格文件已经生成，就写成 M3D-C1 或 TRIMEG 已完成全部验证。

---

## 14. Release 记录

每个 Release 建议保存：

```text
版本号
Git commit
源码归档 SHA-256
发布时间
维护者
Python 版本
OFT 版本和来源
NumPy、h5py、Triangle 等 Python 依赖版本
编译器版本
CMake 版本
MPI 版本
SCOREC/PUMI 版本
helper 二进制 SHA-256
安装命令或安装流程
测试结果
真实 Case 信息
达到的验证层级
已知限制
```

示例：

```text
releases/0.2.0/
├── manifest/
│   ├── RELEASE_MANIFEST.md
│   ├── git-commit.txt
│   ├── python-packages.txt
│   ├── native-environment.txt
│   └── checksums.txt
└── validation/
    ├── install-check.log
    ├── cli-help.txt
    ├── tests.log
    └── case_65402/
```

---

## 15. 当前到明晚会议前的工作

当前不急于实施共享服务器 Release。会议前优先完成用户前端的整理。

### 15.1 CLI 整理

```text
1. 审查 `linkmesh --help`；
2. 删除冗余参数；
3. 删除尚未实现的参数；
4. 删除超出当前正式范围的参数；
5. 统一参数名称和说明；
6. 明确 `--config` 为标准使用入口；
7. 改善错误提示；
8. 确认退出码和日志行为。
```

### 15.2 linkmesh.in 整理

```text
1. 确定正式字段；
2. 删除冗余配置；
3. 删除未实现字段；
4. 为不同输入方式准备清楚的物理输入说明；
5. 统一使用相对于 linkmesh.in 所在目录的路径；
6. 提供可直接复制的模板；
7. 不写个人绝对路径；
8. 确认输出文件位置；
9. 用真实 Case 重复验证。
```

### 15.3 最小 Case 整理

至少准备：

```text
一个正式 linkmesh.in 模板
一个最小输入案例
一组预期输出说明
一份用户运行说明
```

如果不同输入方式都准备作为正式用户接口，应分别提供最小模板，例如：

```text
examples/
├── gfile_case/
│   ├── linkmesh.in
│   └── README.md
└── array_boundary_case/
    ├── linkmesh.in
    └── README.md
```

是否提交真实物理输入文件，需要根据数据权限、文件大小和项目规定决定。

---

## 16. 明晚会议需要确认的问题

### 16.1 共享目录

```text
1. 组内软件根目录是什么？
2. 是否允许建立 linkmesh/releases/？
3. 谁可以写入 Release 目录？
4. 普通组员是否只读？
5. 谁负责切换 current？
6. 是否需要管理员协助设置 PATH？
```

### 16.2 维护职责

```text
1. LinkMesh 由谁负责发布？
2. 是否只允许一名或少数维护者更新？
3. 新版本由谁验收？
4. 发生问题时由谁执行回退？
5. 旧版本保留多久？
6. 发布记录保存在什么位置？
```

### 16.3 依赖来源

```text
1. Python 使用哪个版本？
2. OFT 从哪里安装？
3. OFT 是否有组内固定版本？
4. OFT 能否通过 pip 或 Conda 重复安装？
5. MPI 从哪个服务器模块获得？
6. SCOREC/PUMI 从哪里获得？
7. helper 应使用哪个编译器和 MPI 构建？
8. 动态库路径如何统一设置？
```

### 16.4 统一入口

```text
1. 是否允许将共享 bin 目录加入组员 PATH？
2. 最终是否统一使用 `linkmesh --config linkmesh.in`？
3. 是否需要提供版本查询命令？
4. 是否需要允许用户指定旧版本？
5. 包装器由谁维护？
6. 包装器如何记录实际 Release 版本？
```

### 16.5 验收标准

```text
1. 发布前必须运行哪些自动化测试？
2. 是否必须验证 GFile 输入？
3. 是否必须验证二维边界数组输入？
4. TRIMEG 输出需要达到哪个验证层级？
5. M3D-C1/SMB 输出需要达到哪个验证层级？
6. 是否需要外部加载、初始化或时间推进？
7. 哪个 Case 作为标准发布验收 Case？
```

---

## 17. 推荐的会议决议草案

建议会议最终确认以下管理原则：

```text
1. 组内维护一套版本化的 LinkMesh 共享运行环境；
2. 每个 Release 包含 Python、OFT、LinkMesh 和对应 helper；
3. 普通组员对共享 Release 只有读取和执行权限；
4. 对普通组员只暴露统一的 linkmesh 前端命令；
5. 普通组员不需要激活环境、设置 PYTHONPATH 或定位 helper；
6. 用户在个人目录中建立 Case；
7. Case 只保存 linkmesh.in、物理输入文件、输出和日志；
8. linkmesh.in 中的相对路径以其所在目录为基准；
9. 每个新版本安装到独立 releases/<version>/ 目录；
10. 新版本通过验证后才切换 current；
11. 稳定 Release 不进行原地更新；
12. 旧版本保留用于复现和回退；
13. requirements.txt 管理可重复安装的 Python 依赖；
14. MPI、SCOREC/PUMI、编译器和 helper 构建信息单独记录；
15. 发布记录明确区分生成、结构检查、外部加载和物理验证。
```

---

## 18. 最终推荐方案

LinkMesh 最方便的组内使用方式是：

```text
                      组内共享环境
       +------------------------------------------+
       | Python + OFT + LinkMesh + helper         |
       | 版本化、只读、由维护者统一管理           |
       +--------------------+---------------------+
                            |
                            | 统一前端
                            v
                        linkmesh
                            |
                            | --config linkmesh.in
                            v
                      用户个人 Case
       +------------------------------------------+
       | linkmesh.in                              |
       | 不同输入方式所需的物理文件               |
       | TXT / HDF5 / SMB / PNG / 日志            |
       +------------------------------------------+
```

用户的标准操作只有：

```bash
cd ~/cases/my_case
linkmesh --config linkmesh.in
```

维护者负责：

```text
安装环境
管理依赖
构建 helper
发布版本
运行验证
切换 current
保留旧版本
执行回退
```

普通组员负责：

```text
准备 linkmesh.in
准备物理输入文件
在个人 Case 中运行 linkmesh
检查生成结果
保存 Case 和运行证据
```

该方案同时满足：

```text
用户操作简单
环境集中管理
输入输出相互隔离
版本可以更新
旧版本可以回退
Case 可以复制和归档
运行结果可以追溯
无需在每个用户目录重复安装依赖
```

当前最优先的开发工作是收敛 `linkmesh --help` 和正式 `linkmesh.in` 模板。共享目录、权限、OFT 来源、helper 构建环境和验收标准在会议确认后，再进入服务器实施阶段。