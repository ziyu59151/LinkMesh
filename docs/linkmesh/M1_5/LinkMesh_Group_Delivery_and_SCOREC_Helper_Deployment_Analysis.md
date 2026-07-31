# LinkMesh 组内交付架构、Conda 环境与 SCOREC Helper 部署侦察报告

- 文档性质：交付架构侦察总结与蓝图迭代输入
- 主要受众：LinkMesh 开发主 Agent、项目主管
- 生成依据：当前对话中与 LinkMesh 组内交付、Conda、native helper、服务器运行环境直接相关的讨论和终端输出
- 事实边界：本文明确区分“服务器直接证据”“User 当前决定”“一般部署建议”和“仍待确认事项”。建议内容不代表已经写入 `LinkMesh_Architecture_Plan.md`，需要由主 Agent 根据实时仓库和当前蓝图执行正式的冲突核对与迭代流程。
- 范围限制：本文只总结交付、安装、服务器环境和 helper 部署问题，不重新裁决 LinkMesh 的网格物理契约、HDF5 数据契约或 M3D-C1/PUMI 文件格式契约。

---

## 1. 本轮问题背景

User 是 LinkMesh 的开发者，但不是 Linux 服务器的管理员。服务器管理者是课题组导师。

LinkMesh 当前已经基本完成主要开发流程，按照 User 的判断，现有功能已能满足组内大部分工作需求。项目正从“开发验证阶段”逐渐转入“组内交付和长期维护阶段”。

当前需要解决的问题不再只是“程序能不能在开发者账号下运行”，而是：

1. 组内普通用户是否需要各自安装 Conda；
2. 普通用户是否每次都要手动 `conda activate`；
3. SCOREC/PUMI native helper 应如何编译、安装和定位；
4. 普通用户是否需要自己编译 helper；
5. 是否应建立课题组共享的 Conda 运行环境；
6. 如何把开发环境与组内稳定发布环境分离；
7. 如何使共享环境易于维护、升级、回退和复现实验；
8. 当前服务器环境中的哪些内容可以直接继承，哪些内容需要重新整理；
9. 如何将已决定的 helper 新命名完整写入蓝图并实施迁移。

---

## 2. 当前开发与服务器协作模式

### 2.1 本地与服务器的拟固定分工

当前讨论形成的建议分工为：

```text
本地 Git Bash：
- 编辑源码和文档；
- 运行不依赖 Linux 科学计算栈的静态检查；
- 管理正式源代码版本；
- 准备上传或发布材料；
- 不在本地编译 Linux native helper；
- 不把本地测试结果当成 Linux/OFT/PUMI/M3D-C1 正式验收证据。

Linux 服务器：
- 接收本地上传的源码；
- 构建 native helper；
- 运行 Python、OFT、SCOREC/PUMI 和 M3D-C1 相关测试；
- 执行真实 GFile、网格、SMB 和求解器消费验证；
- 原则上不作为正式源码编辑位置。
```

### 2.2 服务器源码传递方式的当前事实

【服务器工作流事实】

服务器上的 LinkMesh 代码目前不是通过 Git 拉取和管理，而是由 User 直接上传。

当前服务器源码目录为：

```text
/home/lxzeng/LinkMesh_server
```

服务器目录中至少观察到：

```text
docs
examples
LinkMesh_Architecture_Plan_v1.13.md
native
requirements.txt
src
tests
TOKAMAKER
validation_verifivation
```

因此，不能在当前服务器工作流中假定存在以下步骤：

```text
git pull
git status
git log
```

后续部署文档必须准确表述为：

```text
本地维护正式源码
→ 上传某个已确认的源码版本或发布包
→ 服务器构建和验证
```

如果未来引入 Git 服务器工作流，需要单独决策，不能将其写成当前已存在事实。

### 2.3 直接上传模式下必须补充的可追溯信息

由于服务器代码不是通过 Git 管理，正式发布时至少需要保存：

- LinkMesh 发布版本号；
- 对应的本地 Git commit（如果本地仓库使用 Git）；
- 上传日期；
- 上传者；
- 源码归档包或校验值；
- Python 版本；
- Python 依赖版本；
- helper 源码版本；
- helper 编译器版本；
- MPI 版本和来源；
- SCOREC/PUMI 版本和来源；
- 端到端验证日期；
- 验证所用真实案例；
- 验证结果和日志位置。

否则，将来很难回答：

```text
服务器上的这个可执行版本究竟对应哪一份源码？
某次物理计算使用的是哪个 LinkMesh 版本？
当前 helper 是由哪一版源代码编译的？
```

---

## 3. 当前 Conda 开发环境的直接侦察结果

### 3.1 Conda 环境位置

【直接证据】

当前激活环境名称：

```text
linkmesh
```

当前环境绝对路径：

```text
/home/lxzeng/miniconda3/envs/linkmesh
```

终端输出：

```text
CONDA_PREFIX=/home/lxzeng/miniconda3/envs/linkmesh
CONDA_DEFAULT_ENV=linkmesh
```

当前 Python：

```text
/home/lxzeng/miniconda3/envs/linkmesh/bin/python
Python 3.12.13
```

### 3.2 当前 LinkMesh 不是正式安装进 Conda 环境

【直接证据】

当前设置了：

```text
PYTHONPATH=/home/lxzeng/LinkMesh_server/src
```

实际导入位置：

```text
linkmesh = /home/lxzeng/LinkMesh_server/src/linkmesh/__init__.py
```

这说明当前运行结构为：

```text
个人 Conda 环境：
- 提供 Python；
- 提供 OFT；
- 提供 NumPy、h5py、matplotlib 等依赖。

个人上传源码目录：
- 提供 LinkMesh Python 包源码。

PYTHONPATH：
- 把 /home/lxzeng/LinkMesh_server/src 加入 Python 模块搜索路径。
```

即：

```text
/home/lxzeng/miniconda3/envs/linkmesh
        +
PYTHONPATH=/home/lxzeng/LinkMesh_server/src
        ↓
当前 LinkMesh 开发运行环境
```

这适合开发验证，但不适合作为正式组内发布模式，原因包括：

1. LinkMesh 没有作为正式 Python 包安装到发布前缀；
2. 运行依赖个人 `PYTHONPATH`；
3. 运行依赖个人源码目录；
4. 源码目录被替换后，程序行为可能立即变化；
5. 其他用户未必有权进入 User 的主目录；
6. 难以稳定记录用户究竟运行了哪个版本。

### 3.3 OFT 的来源

【直接证据】

OFT 实际导入位置：

```text
/home/lxzeng/miniconda3/envs/linkmesh/lib/python3.12/site-packages/OpenFUSIONToolkit/__init__.py
```

版本：

```text
openfusiontoolkit 26.6
```

这说明当前运行使用的是安装在 Conda 环境 `site-packages` 中的正式 Python 包，而不是通过 `TOKAMAKER/OpenFUSIONToolkit/src/python` 导入源码快照。

这与此前服务器故障排查得到的规则一致：

```text
不得将 TOKAMAKER/OpenFUSIONToolkit/src/python
加入运行环境的 PYTHONPATH。
```

原因是该源码快照不包含正式运行所需的 `liboftpy.so`，并会遮蔽 `site-packages` 中已经安装的 OFT 包。

### 3.4 当前关键 Python 依赖版本

【直接证据】

```text
Python                 3.12.13
NumPy                  2.5.1
h5py                   3.16.0
matplotlib             3.11.0
OpenFUSIONToolkit      26.6
pytest                 9.1.1
triangle               20250106
```

这些是当前开发环境中的实装版本，不自动等同于未来蓝图应锁定的全部发布版本。

特别需要区分：

```text
当前环境中已安装
≠ LinkMesh 的直接运行依赖
≠ 必须锁死为正式版本
≠ 已证明其他版本不可用
```

蓝图若要收紧或放宽依赖版本，需要基于干净发布环境测试确定。

---

## 4. `triangle` Python 包的依赖侦察结果

### 4.1 当前直接证据

源码搜索结果没有发现 LinkMesh 正式源码中存在：

```python
import triangle
```

或：

```python
from triangle ...
```

唯一相关结果位于只读参考源码中，并且是注释行：

```text
TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py:55:
#     import triangle as tr
```

已安装包元数据显示：

```text
Name: OpenFUSIONToolkit
Version: 26.6
Requires: h5py, matplotlib, netCDF4, numpy, scipy
```

其中没有声明 `triangle`。

`triangle` 包自身信息为：

```text
Name: triangle
Version: 20250106
Requires: numpy
Required-by:
```

没有其他已安装 Python 包通过包元数据声明依赖它。

### 4.2 当前可以支持的结论

【高可信判断，但仍需发布环境验证】

当前证据表明：

1. LinkMesh 当前源码没有直接导入 `triangle`；
2. `openfusiontoolkit==26.6` 的包元数据没有把 `triangle` 声明为依赖；
3. TokaMaker 参考源码中的 `triangle` 导入是被注释的内容；
4. 当前 LinkMesh 实际网格路径更可能由 `src/linkmesh/mesher/oft_adapter.py` 调用 OFT 提供的网格能力；
5. `triangle` 很可能不是当前 LinkMesh 发布环境的必要直接依赖。

### 4.3 不能提前作出的结论

尚不能仅依据源码搜索，立即宣布：

```text
triangle 已经确定可以从正式依赖中删除。
```

原因是：

- 当前正在工作的环境已经安装了 `triangle`；
- 尚未在一个完全不安装 `triangle` 的干净环境中运行全部真实案例；
- 仍需确认 OFT 的具体运行路径在所有目标 profile 下都不动态导入或间接需要它；
- 需要验证 GFile → OFT 网格 → LinkMesh 输出 → helper → SMB 的完整路径。

### 4.4 建议的最终确认方法

不要从当前开发环境直接卸载 `triangle`。

应在干净发布候选环境中：

```text
不安装 triangle
→ 正式安装 LinkMesh
→ 运行自动测试
→ 运行真实 GFile 网格生成
→ 运行 HDF5/PNG 输出
→ 运行 helper 和 SMB 输出
→ 执行 M3D-C1 消费验证
```

全部通过后，再从正式依赖清单移除 `triangle`。

---

## 5. 当前 helper 的源码调用机制

### 5.1 Writer 中的当前实现

【直接源码证据】

当前文件：

```text
src/linkmesh/writers/smb_writer.py
```

使用：

```python
_HELPER_NAME = "linkmesh-m3dc1-smb-helper"
_HELPER_ENV = "LINKMESH_M3DC1_SMB_HELPER"
_HELPER_TIMEOUT_SECONDS = 300
```

并定义了：

```python
_resolve_helper(...)
```

从当前源码片段可以确认 helper 的定位顺序为：

```text
1. 调用层显式传入 helper_path；
2. 环境变量 LINKMESH_M3DC1_SMB_HELPER；
3. PATH 中查找 linkmesh-m3dc1-smb-helper；
4. 三者均失败时抛出明确错误。
```

可概括为：

```text
helper_path
   ↓ 未提供
LINKMESH_M3DC1_SMB_HELPER
   ↓ 未设置
PATH 中的 linkmesh-m3dc1-smb-helper
   ↓ 未找到
失败并报告 helper 定位错误
```

### 5.2 当前开发环境实际使用方式

【直接证据】

当前设置：

```text
LINKMESH_M3DC1_SMB_HELPER=/home/lxzeng/LinkMesh_runs/m4_2_helper_build/linkmesh-m3dc1-smb-helper
```

因此，当前 Writer 实际通过环境变量定位 helper，而不是通过 Conda 环境的 `bin/` 或普通 `PATH` 自动找到它。

当前结构为：

```text
smb_writer.py
  ↓ 读取 LINKMESH_M3DC1_SMB_HELPER
/home/lxzeng/LinkMesh_runs/m4_2_helper_build/linkmesh-m3dc1-smb-helper
  ↓
调用当前开发构建目录中的 helper
```

这适合开发调试，因为开发者可以快速切换 helper 二进制；但不适合作为普通组员的最终操作方式，因为普通用户不应手工维护该环境变量。

---

## 6. 当前 helper 二进制的直接侦察结果

### 6.1 当前二进制路径

```text
/home/lxzeng/LinkMesh_runs/m4_2_helper_build/linkmesh-m3dc1-smb-helper
```

文件权限和大小：

```text
-rwxrwxr-x
12686544 bytes
```

所有者和用户组：

```text
owner = lxzeng
group = lxzeng
```

### 6.2 二进制类型

`file` 输出：

```text
ELF 64-bit LSB pie executable
x86-64
GNU/Linux
dynamically linked
interpreter /lib64/ld-linux-x86-64.so.2
for GNU/Linux 3.2.0
with debug_info
not stripped
```

可以确认：

1. 它是 Linux x86-64 原生可执行文件；
2. 它是动态链接程序；
3. 它不是 Python 脚本；
4. 它包含调试信息；
5. 它尚未执行 strip；
6. 它当前更接近开发或验证构建，而不是经过发布整理的最小二进制。

“with debug_info, not stripped”不代表程序错误。它只表示二进制包含调试符号，体积相对较大。发布阶段是否保留调试信息，应由部署策略决定。

### 6.3 当前观察到的动态库

经筛选后的 `ldd` 输出包括：

```text
libmpi.so.40
    => /lib/x86_64-linux-gnu/libmpi.so.40

libstdc++.so.6
    => /lib/x86_64-linux-gnu/libstdc++.so.6
```

并且筛选输出中没有出现：

```text
not found
```

所以当前至少可以确认：

- helper 动态链接系统 MPI；
- helper 动态链接 GNU C++ 标准库；
- 当前 shell 环境能够找到这些库；
- 已筛选的结果中没有发现缺失库。

### 6.4 对 MPI 来源的判断

当前 MPI 动态库来自：

```text
/lib/x86_64-linux-gnu/libmpi.so.40
```

这说明当前 helper 至少在运行时使用服务器系统路径中的 MPI，而不是一个明显位于 Conda 环境内的 MPI。

该事实对共享部署非常重要：

```text
把 helper 文件复制到共享 Conda 环境的 bin/
并不会自动把它的 MPI 运行时依赖变成 Conda 依赖。
```

helper 是否能正常运行，还取决于服务器上对应的系统动态库是否继续存在且 ABI 兼容。

### 6.5 当前输出尚不能确认的事项

当前 `ldd` 输出经过以下正则筛选：

```text
not found|mpi|pumi|apf|mds|gmi|pcu|stdc++
```

没有看到 PUMI/APF/MDS/GMI/PCU 动态库，不代表 helper 没有使用 SCOREC/PUMI。可能原因包括：

1. SCOREC/PUMI 相关库被静态链接进 helper；
2. 库的实际名称没有匹配筛选表达式；
3. 相关功能由其他动态库间接提供；
4. 构建使用了静态归档库；
5. 当前筛选没有显示全部依赖。

因此不能根据这份筛选输出声称：

```text
helper 不依赖 SCOREC/PUMI。
```

后续发布前应补充一次完整二进制审计，例如检查：

```text
完整 ldd 输出
readelf -d 输出
CMake 配置和链接行
构建时使用的 PUMI/SCOREC 路径
MPI 编译器和运行时版本
```

但这些属于发布候选环境的后续侦察，不需要普通用户执行。

---

## 7. helper 的正式命名决定

### 7.1 User 与主 Agent 的最新决定

【User 当前明确决定】

User 已与 LinkMesh 主 Agent 讨论并决定采用更有逻辑的 SCOREC 定向命名。

正式目标命名为：

```text
源码目录：
native/linkmesh_scorec_helper/

CMake target / 可执行文件：
linkmesh-scorec-helper

环境变量：
LINKMESH_SCOREC_HELPER

服务器构建目录：
$HOME/LinkMesh_build/linkmesh_scorec_helper/

Conda 或共享安装前缀中的安装位置：
$CONDA_PREFIX/bin/linkmesh-scorec-helper
```

### 7.2 命名规则的语义

这些名称表示同一个 native 组件在不同阶段的身份：

| 层次 | 正式目标名称 | 作用 |
|---|---|---|
| Git 源码目录 | `native/linkmesh_scorec_helper/` | 保存 C++ 源码和 CMake 规则 |
| CMake target | `linkmesh-scorec-helper` | CMake 构建目标名称 |
| Linux 可执行文件 | `linkmesh-scorec-helper` | 编译后由 Python Writer 调用的程序 |
| 环境变量 | `LINKMESH_SCOREC_HELPER` | 开发期或特殊部署时显式指定 helper 路径 |
| 服务器构建目录 | `$HOME/LinkMesh_build/linkmesh_scorec_helper/` | 存放 CMake 缓存和构建产物 |
| 正式安装位置 | `$CONDA_PREFIX/bin/linkmesh-scorec-helper` | 与安装后的 LinkMesh 命令放在同一前缀中 |

### 7.3 当前旧命名与目标新命名的差异

当前代码和二进制仍使用旧名称：

```text
native 目录：需由实时仓库核对
可执行文件：linkmesh-m3dc1-smb-helper
环境变量：LINKMESH_M3DC1_SMB_HELPER
开发构建目录：/home/lxzeng/LinkMesh_runs/m4_2_helper_build/
```

目标名称为：

```text
native/linkmesh_scorec_helper/
linkmesh-scorec-helper
LINKMESH_SCOREC_HELPER
$HOME/LinkMesh_build/linkmesh_scorec_helper/
```

因此，这不是只改一个文件名，而是一次完整的命名迁移。

### 7.4 蓝图和实现必须同步修改的范围

主 Agent 应根据实时仓库逐项核对，至少可能涉及：

```text
LinkMesh_Architecture_Plan.md
Project_Tree.md
History.md
native 目录名称
native CMakeLists.txt
顶层 CMake 配置（如果存在）
CMake target 名称
CMake install 规则
src/linkmesh/writers/smb_writer.py
CLI 或配置层中 helper 相关参数
tests 中 helper 名称和环境变量
部署脚本
验证脚本
用户文档
服务器构建命令
发布环境安装说明
```

### 7.5 建议保留的 helper 定位顺序

重命名后建议保持当前已有的三级定位机制，仅替换正式名称：

```text
第一优先级：
调用层显式传入 helper_path

第二优先级：
环境变量 LINKMESH_SCOREC_HELPER

第三优先级：
PATH 中查找 linkmesh-scorec-helper

失败条件：
三种方式均无法定位时，报告明确错误并停止
```

这个顺序兼顾：

- 自动测试；
- 开发调试；
- 特殊部署；
- 组内正式安装。

### 7.6 是否需要旧名称兼容期

这是蓝图迭代中需要主 Agent 和 User决定的问题。

有两种策略：

#### 策略 A：一次性强制迁移

新版本只接受：

```text
LINKMESH_SCOREC_HELPER
linkmesh-scorec-helper
```

旧名称立即失效。

优点：

- 规则简单；
- 不保留双重命名；
- 更适合项目尚未广泛发布时实施。

缺点：

- 当前开发脚本和服务器环境变量必须同步修改；
- 旧验证流程会立即失效。

#### 策略 B：一个版本的兼容迁移

定位顺序可临时设计为：

```text
helper_path
→ LINKMESH_SCOREC_HELPER
→ PATH 中的 linkmesh-scorec-helper
→ 旧环境变量 LINKMESH_M3DC1_SMB_HELPER（仅兼容并警告）
→ PATH 中旧名称 linkmesh-m3dc1-smb-helper（仅兼容并警告）
```

下一主版本再删除旧名称。

优点：

- 迁移风险较低；
- 当前服务器验证流程可以逐步切换。

缺点：

- Writer 逻辑和测试稍复杂；
- 必须明确兼容截止版本；
- 容易让旧名称长期残留。

由于 LinkMesh 尚处于组内正式交付前阶段，如果没有外部用户依赖旧名称，一次性强制迁移通常更简洁。但最终策略应由 User 确认并先写入蓝图。

---

## 8. 当前服务器用户和权限事实

### 8.1 User 所属用户组

【直接证据】

```text
uid=1028(lxzeng)
gid=1028(lxzeng)
groups=1028(lxzeng),100(users),1003(m3dc1)
```

User 属于：

```text
lxzeng
users
m3dc1
```

其中 `m3dc1` 组可能适合作为组内共享软件权限的基础，但该用途需要导师确认。

### 8.2 User 主目录权限

【直接证据】

```text
drwxr-x--- /home/lxzeng
```

即数字权限大致为：

```text
750
```

含义：

```text
所有者 lxzeng：读、写、进入
所属组 lxzeng：读、进入
其他用户：无权限
```

由于主目录所属组是私人组 `lxzeng`，而不是 `m3dc1`，普通组员通常无法进入：

```text
/home/lxzeng
```

因此不能把以下个人路径作为正式组内公共运行路径：

```text
/home/lxzeng/miniconda3/envs/linkmesh
/home/lxzeng/LinkMesh_server
/home/lxzeng/LinkMesh_runs
```

即使某个内部文件本身是 `755`，其他用户仍需拥有父目录每一级的执行/进入权限。

### 8.3 当前 Conda 环境目录权限

【直接证据】

```text
drwxrwxr-x /home/lxzeng/miniconda3/envs/linkmesh
```

环境目录自身允许其他用户读取和进入，但由于上层 `/home/lxzeng` 对其他用户是 `---`，普通组员仍不能据此可靠访问环境。

### 8.4 共享目录侦察现状

对：

```text
/share
/shared
```

的简短检查没有返回可用目录信息。

这只能说明：

- 路径可能不存在；
- 或当前用户不可见；
- 或服务器使用其他共享路径。

不能据此断言服务器没有共享存储。

可能的共享目录名称包括但不限于：

```text
/share
/shared
/project
/projects
/work
/data
/home/m3dc1
```

具体位置必须由导师或服务器管理者确认。

### 8.5 module 系统现状

终端输出：

```text
No modules loaded
```

这说明当前 shell 没有加载 module，但不能据此断言 module 命令不可用。相反，该输出通常说明 module 系统可能存在，只是当前没有激活任何模块。

后续可以询问导师：

- 是否使用 Environment Modules 或 Lmod；
- 课题组能否维护自己的 modulefile；
- M3D-C1、MPI、SCOREC/PUMI 是否通过 module 提供。

---

## 9. 为什么不能直接把当前个人开发环境交给组员

当前个人环境不适合作为正式发布环境，主要有以下原因。

### 9.1 依赖个人 `PYTHONPATH`

当前 LinkMesh 来自：

```text
/home/lxzeng/LinkMesh_server/src
```

而不是正式安装在环境的：

```text
site-packages
```

组员必须知道并继承同一 `PYTHONPATH` 才能使用，这不符合稳定交付要求。

### 9.2 依赖个人 helper 构建目录

当前 helper 位于：

```text
/home/lxzeng/LinkMesh_runs/m4_2_helper_build/
```

并通过个人环境变量定位。

组员无法可靠进入该路径，也不应该依赖一个带有任务编号语义的开发构建目录。

### 9.3 当前环境可能包含开发过程遗留内容

当前环境中可能混有：

- pytest 等开发依赖；
- 非必要的 `triangle`；
- 多轮调试安装；
- 临时版本；
- editable 或 PYTHONPATH 源码；
- 未经整理的动态库设置。

它能工作，但不等于它是可复现、可发布的最小环境。

### 9.4 共享个人环境不利于维护

如果组员直接使用开发环境，开发者的一次：

```text
pip install
conda update
源码覆盖
环境变量修改
helper 重编译
```

都可能影响其他人的工作。

稳定发布环境应尽量保持只读，并与开发环境分开。

---

## 10. 推荐的总体交付方案

### 10.1 推荐结论

建议采用：

```text
个人开发环境
+
课题组共享、版本化、普通用户只读的 LinkMesh 发布环境
+
预编译并安装好的 linkmesh-scorec-helper
+
统一包装命令或 modulefile
```

不建议：

```text
让每个组员单独安装 Conda
让每个组员单独安装 LinkMesh
让每个组员自己编译 helper
让每个组员手工设置 PYTHONPATH
让每个组员手工设置 LINKMESH_SCOREC_HELPER
直接共享开发者的个人环境
```

### 10.2 Conda 在该方案中的角色

Conda 是维护者用来构建和管理运行前缀的工具，不必成为普通用户必须学习的操作。

理想分工：

```text
开发者/维护者：
- 创建共享运行环境；
- 安装正式 LinkMesh；
- 安装 Python 依赖；
- 编译并安装 helper；
- 完成端到端验收；
- 发布新版本。

普通组员：
- 使用统一命令；
- 不创建环境；
- 不安装依赖；
- 不编译 helper；
- 不修改共享环境。
```

### 10.3 组员是否需要自己安装 Conda

推荐答案：

```text
不需要。
```

只要共享前缀中已经包含：

```text
bin/python
bin/linkmesh
bin/linkmesh-scorec-helper
lib/python.../site-packages/linkmesh
lib/python.../site-packages/OpenFUSIONToolkit
```

组员可以直接使用共享环境中的程序。

需要注意，Conda 环境的共享可执行性仍取决于：

- 服务器文件系统权限；
- 动态库兼容性；
- Python/OFT wheel 与服务器系统兼容性；
- helper 的 MPI/PUMI 依赖；
- 共享目录是否允许执行文件。

### 10.4 组员是否每次都需要 `conda activate`

推荐答案：

```text
不一定，最好不要求普通用户手工 activate。
```

可选方式如下。

#### 方式 A：手工激活共享环境

```text
conda activate <共享环境绝对路径>
linkmesh ...
```

优点是简单直接，缺点是用户必须知道 Conda 和环境路径。

#### 方式 B：共享包装命令

用户直接运行：

```text
<共享软件目录>/linkmesh/bin/linkmesh ...
```

包装脚本内部调用共享环境的绝对 Python/LinkMesh 路径，并设置必要环境变量。

这是当前最容易由开发者独立维护的方案。

#### 方式 C：modulefile

用户运行：

```text
module load linkmesh
linkmesh ...
```

modulefile 可负责：

- 把共享环境 `bin/` 加入 `PATH`；
- 设置 `LINKMESH_SCOREC_HELPER`；
- 加载兼容的 MPI/SCOREC/PUMI 环境；
- 设置必要动态库路径；
- 暴露版本信息。

这是更符合 HPC 习惯的长期方案，但可能需要导师或服务器管理员协助。

### 10.5 LinkMesh 作为预处理程序的使用频率

LinkMesh 主要用于生成或更新 M3D-C1 所需的网格及配套文件，不必在每次 M3D-C1 时间推进作业中都重新运行。

推荐使用流程：

```text
需要新网格时：
加载 LinkMesh 运行环境
→ 运行 LinkMesh
→ 检查 PNG 和统计信息
→ 固化输出文件

后续求解：
M3D-C1 重复使用已经确认的网格文件
```

因此，组员不必在每次 M3D-C1 作业中都激活 LinkMesh 的 Conda 环境。只有需要生成或更新网格时才调用 LinkMesh。

---

## 11. 推荐的共享发布目录结构

共享根目录必须由导师确认。以下仅为结构示意，不代表已经确定使用 `/share`。

```text
<GROUP_SOFTWARE_ROOT>/
└── linkmesh/
    ├── releases/
    │   ├── 1.0.0/
    │   │   ├── env/
    │   │   │   ├── bin/
    │   │   │   │   ├── python
    │   │   │   │   ├── linkmesh
    │   │   │   │   └── linkmesh-scorec-helper
    │   │   │   └── lib/
    │   │   ├── source-manifest/
    │   │   ├── validation/
    │   │   └── VERSION
    │   │
    │   └── 1.1.0/
    │       └── ...
    │
    ├── current -> releases/1.0.0
    │
    ├── bin/
    │   └── linkmesh
    │
    └── modulefiles/
        └── linkmesh
```

### 11.1 `releases/<version>/env`

每个发布版本拥有独立运行前缀：

```text
env/bin/python
env/bin/linkmesh
env/bin/linkmesh-scorec-helper
env/lib/python.../site-packages/linkmesh
```

不得让不同版本共用一个可写环境后再原地升级。

### 11.2 `current`

```text
current -> releases/1.0.0
```

`current` 是符号链接，指向默认稳定版本。

发布新版本时：

```text
创建新的 release
→ 完整验证
→ 再切换 current
```

如果新版本出现问题，可以切回旧版本。

### 11.3 `bin/linkmesh`

这是给普通组员使用的统一入口。

它可以内部完成：

```text
定位 current
→ 选择正确的 Python 环境
→ 设置 helper 路径
→ 调用 LinkMesh
```

普通用户不需要知道共享 Conda 环境的内部路径。

### 11.4 `validation/`

建议保存：

- 自动测试摘要；
- 真实 GFile 测试记录；
- 网格统计；
- helper 版本；
- M3D-C1 加载验证结果；
- 验证日期；
- 运行环境摘要。

---

## 12. helper 在共享发布架构中的处理

### 12.1 普通用户不应自己编译 helper

正式交付目标应是：

```text
维护者在目标服务器软件栈中编译一次
→ 安装到共享发布环境
→ 所有具有权限的组员直接运行
```

普通用户不应被要求了解：

- CMake；
- C++ 编译器；
- MPI 头文件；
- SCOREC/PUMI 链接；
- APF/MDS/GMI/PCU；
- native helper 构建目录；
- 动态库搜索规则。

### 12.2 何时需要重新编译

以下情况通常需要维护者重新构建 helper：

1. helper C++ 源码发生变化；
2. SCOREC/PUMI 版本变化；
3. MPI 实现或 ABI 变化；
4. 编译器 ABI 发生不兼容变化；
5. 更换服务器或 CPU 架构；
6. M3D-C1 使用的软件栈发生关键升级；
7. 链接方式或安装前缀发生变化。

普通组员的每次 LinkMesh 使用不需要重新编译。

### 12.3 helper 的开发构建位置

目标规范：

```text
$HOME/LinkMesh_build/linkmesh_scorec_helper/
```

这里用于保存：

```text
CMakeCache.txt
CMakeFiles/
构建日志
linkmesh-scorec-helper
```

该目录属于可删除、可重建的构建产物目录，不应视为正式源码。

### 12.4 helper 的正式安装位置

个人发布候选环境中：

```text
$CONDA_PREFIX/bin/linkmesh-scorec-helper
```

共享环境中更准确地说是：

```text
<共享 release>/env/bin/linkmesh-scorec-helper
```

这使 Python CLI 和 helper 位于同一个发布前缀：

```text
env/bin/linkmesh
env/bin/linkmesh-scorec-helper
```

### 12.5 helper 的定位建议

正式 Writer 建议保留：

```text
1. helper_path
2. LINKMESH_SCOREC_HELPER
3. PATH 中的 linkmesh-scorec-helper
```

在普通共享发布中，可优先依靠以下任一方式：

#### 方案 A：包装脚本设置环境变量

```text
LINKMESH_SCOREC_HELPER=<共享环境>/bin/linkmesh-scorec-helper
```

#### 方案 B：helper 与 linkmesh 同在 PATH

将：

```text
<共享环境>/bin
```

加入进程 `PATH`，Writer 自动找到：

```text
linkmesh-scorec-helper
```

#### 方案 C：Writer 根据安装前缀定位同目录 helper

如果未来需要，可在蓝图中规划 Writer 检查当前安装前缀的 `bin/`。但这属于新的正式定位规则，必须先写入蓝图，不应未经确认直接实现。

当前已有的环境变量和 PATH 机制已经足以支持可靠部署。

---

## 13. 包装命令的建议职责

最终共享入口可以是一个很小的 shell 包装程序。

其概念职责为：

```text
1. 确定共享 LinkMesh 当前版本；
2. 设置共享环境的 PATH；
3. 设置 LINKMESH_SCOREC_HELPER；
4. 必要时设置动态库运行环境；
5. 调用共享环境中的 linkmesh；
6. 原样传递用户参数；
7. 返回 LinkMesh 的退出状态。
```

概念示意如下，实际路径必须由导师确认后再生成：

```bash
#!/usr/bin/env bash
set -e

LINKMESH_ROOT="<GROUP_SOFTWARE_ROOT>/linkmesh/current"
export PATH="$LINKMESH_ROOT/env/bin:$PATH"
export LINKMESH_SCOREC_HELPER="$LINKMESH_ROOT/env/bin/linkmesh-scorec-helper"

exec "$LINKMESH_ROOT/env/bin/linkmesh" "$@"
```

说明：

- 这只是部署架构示意，不是当前已经存在的文件；
- 如果 helper 还依赖额外的动态库路径，包装脚本或 modulefile 还需处理相应运行环境；
- 不应硬编码开发者个人目录；
- 不应让普通用户手工设置环境变量；
- 是否加入 `LD_LIBRARY_PATH` 必须根据完整动态库侦察决定，不能凭经验提前加入。

---

## 14. 开发环境、发布候选环境和共享环境的分层

建议明确区分三类环境。

### 14.1 个人开发环境

当前实例：

```text
/home/lxzeng/miniconda3/envs/linkmesh
```

允许：

- 安装测试依赖；
- 使用 `PYTHONPATH`；
- 调用开发构建目录中的 helper；
- 临时设置环境变量；
- 快速调试。

不向组员承诺稳定。

### 14.2 个人发布候选环境

建议在 User 个人目录中从零创建一个干净环境，例如概念名称：

```text
linkmesh-release-candidate
```

要求：

- 不依赖 `PYTHONPATH`；
- LinkMesh 以正式安装方式进入 `site-packages`；
- 只包含必要运行依赖和明确的测试依赖；
- helper 使用正式目标名称；
- helper 安装到候选环境 `bin/`；
- 不依赖个人开发构建目录；
- 能从任意工作目录运行；
- 完成真实端到端测试。

这个环境用于证明正式发布方案可复现。

### 14.3 组内共享发布环境

在导师批准的共享目录中创建。

要求：

- 版本化；
- 普通组员只读；
- 不原地升级；
- 已完成端到端验证；
- 包含正式 LinkMesh 和 helper；
- 不依赖开发者个人主目录；
- 不依赖 `PYTHONPATH`；
- 有统一入口；
- 有版本和验证记录。

---

## 15. 共享 Conda 环境的维护策略

### 15.1 不应允许多人修改同一环境

共享 Conda 前缀适合多用户读取和执行，不适合所有用户共同执行：

```text
conda install
conda update
pip install
pip uninstall
```

推荐权限：

```text
维护者：
可写。

普通组员：
只读和可执行。
```

### 15.2 不应原地更新稳定版本

错误模式：

```text
所有用户正在使用 current/env
→ 维护者直接 conda update 或 pip install
→ 当前运行中的用户行为发生变化
```

推荐模式：

```text
创建 releases/1.1.0/env
→ 安装和测试
→ 完成验证
→ 切换 current
```

### 15.3 旧版本应保留一段时间

旧版本可用于：

- 复现实验；
- 回退；
- 对比行为差异；
- 验证新版本是否引入回归。

### 15.4 Conda 环境不是完整的二进制兼容保证

helper 安装到 Conda `bin/` 只解决“程序放在哪里”和“如何找到”的问题。

它不自动解决：

- MPI ABI；
- SCOREC/PUMI ABI；
- 系统 C++ 标准库；
- 动态库搜索路径；
- M3D-C1 运行栈一致性。

因此，每个发布版本仍需记录 native 软件栈并执行真实服务器验证。

---

## 16. 推荐的发布流程

建议将组内发布流程固定为以下阶段。

### 阶段 1：蓝图迭代

先在 `LinkMesh_Architecture_Plan.md` 中确认：

- 共享交付原则；
- helper 新命名；
- helper 定位优先级；
- 构建目录；
- 安装位置；
- Conda 环境角色；
- 普通用户不编译 helper；
- 是否提供包装脚本或 modulefile；
- 发布环境不得依赖 `PYTHONPATH`；
- Python 和 helper 的版本绑定；
- 发布验收标准。

### 阶段 2：命名迁移

同步修改：

```text
native/linkmesh_scorec_helper/
linkmesh-scorec-helper
LINKMESH_SCOREC_HELPER
Writer 常量
CMake target
测试
文档
部署脚本
```

### 阶段 3：个人干净发布候选环境

从零创建环境，不克隆当前开发环境。

安装：

- Python；
- OFT；
- LinkMesh 正式包；
- 经过确认的必要依赖；
- 编译后的 helper。

### 阶段 4：依赖最小化验证

特别确认：

- 是否确实不需要 `triangle`；
- 是否需要 pytest 进入运行环境；
- 是否需要编译工具进入最终运行环境；
- 是否能在无 `PYTHONPATH` 条件下运行；
- helper 的全部动态库是否可解析。

### 阶段 5：端到端验收

至少包括：

```text
Python 包导入
CLI 启动
真实 GFile 读取
OFT 网格生成
LinkMesh 内存对象检查
目标文件写出
helper 调用
SMB 生成
M3D-C1/SCOREC/PUMI 消费验证
错误信息和退出码验证
```

具体完成程度必须以实时项目测试和 User 验收为准。

### 阶段 6：导师确认共享目录

需要导师确认：

- 共享软件根目录；
- User 是否有维护写权限；
- `m3dc1` 组是否作为读取执行权限组；
- 共享目录是否允许运行 ELF 二进制；
- 是否使用 module 系统；
- 系统 MPI、PUMI、M3D-C1 的正式环境来源；
- 是否存在备份、配额或清理策略。

### 阶段 7：建立版本化共享 release

创建新 release，安装 Python 环境和 helper，执行验收。

### 阶段 8：提供统一入口

优先顺序建议：

```text
长期最优：
module load linkmesh

短期可控：
共享包装命令

最低可用：
用户直接调用共享环境绝对路径
```

### 阶段 9：发布与回退

验收通过后切换 `current`。旧版本不立即删除。

---

## 17. 建议加入蓝图的交付验收标准

主 Agent 可评估是否在蓝图中新增“组内交付里程碑”或“部署验收章节”。建议至少覆盖以下内容。

### 17.1 Python 安装验收

```text
1. LinkMesh 已安装到发布环境 site-packages；
2. 不设置 PYTHONPATH 也能导入 linkmesh；
3. 从源码目录之外可以启动 linkmesh；
4. OFT 从发布环境 site-packages 导入；
5. 不使用 TOKAMAKER 源码路径作为运行时依赖。
```

### 17.2 CLI 验收

```text
1. 统一终端命令可运行；
2. 普通用户不需要手工设置 PYTHONPATH；
3. 普通用户不需要知道源码目录；
4. 包装入口能原样传递 CLI 参数；
5. 程序退出码与错误状态一致。
```

### 17.3 helper 验收

```text
1. 正式名称为 linkmesh-scorec-helper；
2. 安装到发布环境 bin；
3. Writer 能通过正式定位规则找到 helper；
4. helper 可执行；
5. helper 二进制架构与服务器一致；
6. ldd 不出现 not found；
7. MPI 与 SCOREC/PUMI 软件栈已记录；
8. helper 可完成真实 SMB 写出；
9. 普通用户无需编译 helper；
10. 普通用户无需手工设置 helper 环境变量。
```

### 17.4 多用户权限验收

```text
1. m3dc1 组普通成员能进入共享目录；
2. 普通成员能执行 linkmesh 和 helper；
3. 普通成员能读取 Python 包和动态库；
4. 普通成员不能修改稳定 release；
5. 维护者能创建新 release；
6. 旧 release 可以回退。
```

### 17.5 真实消费端验收

```text
1. 使用正式共享入口生成目标文件；
2. 生成物能被目标 M3D-C1/SCOREC/PUMI 环境加载；
3. 验收不依赖开发者个人目录；
4. 验收不依赖开发环境 PYTHONPATH；
5. 验收记录保存到对应 release 的 validation 目录。
```

---

## 18. 主 Agent 在蓝图迭代时应避免的错误

1. 不得把当前个人开发环境直接定义为组内正式环境。
2. 不得把 `/share` 写成已确认路径，当前共享根目录尚未由导师确认。
3. 不得声称每个用户都必须安装 Conda。
4. 不得要求每个用户自己编译 helper。
5. 不得要求普通用户手工设置 `LINKMESH_SCOREC_HELPER`。
6. 不得继续把 `PYTHONPATH=/home/lxzeng/LinkMesh_server/src` 作为正式安装方案。
7. 不得把 helper 安装到 Conda `bin/` 误解为“所有 MPI/PUMI 依赖自动由 Conda提供”。
8. 不得因为筛选后的 `ldd` 没显示 PUMI 库，就声称 helper 不依赖 SCOREC/PUMI。
9. 不得未经干净环境完整测试就删除 `triangle` 正式依赖。
10. 不得只修改 helper 文件名而遗漏环境变量、CMake、测试和文档。
11. 不得把服务器直接上传源码的流程误写成当前使用 `git pull`。
12. 不得把“User 报告基本流程已完成”自动升级为所有交付验收已通过。
13. 不得在共享稳定环境中原地更新 Python 包。
14. 不得让普通组员对稳定 release 具有写权限。
15. 不得在业务源码中硬编码 `/home/lxzeng/...`。
16. 不得在蓝图未确认前自行创建系统级 modulefile 或修改共享目录权限。

---

## 19. 仍待确认的关键问题

### 19.1 需要导师或服务器管理者确认

1. 课题组正式共享软件目录在哪里；
2. User 是否可获得该目录的维护写权限；
3. 普通组员是否统一属于 `m3dc1` 用户组；
4. 共享目录是否允许执行 ELF 二进制；
5. 是否支持课题组私有 modulefile；
6. M3D-C1 使用哪一套正式 MPI；
7. SCOREC/PUMI 的正式安装位置和版本；
8. 系统库升级策略；
9. 共享软件目录的备份和配额规则。

### 19.2 需要实时仓库侦察确认

1. 当前 native 源码目录名称；
2. helper 的 CMake target；
3. helper 当前 install 规则；
4. 是否存在顶层 CMake 工程；
5. Writer 的完整 helper 定位逻辑；
6. CLI 是否暴露 helper 路径参数；
7. 测试中有多少旧名称；
8. 文档中有多少旧名称；
9. 是否已有包装脚本或部署脚本；
10. `pyproject.toml` 是否已经存在并能正式安装 LinkMesh；
11. `requirements.txt` 是否仍声明 `triangle`；
12. OFT 网格路径是否在所有 profile 下都不需要 Python `triangle`。

### 19.3 需要发布候选环境测试确认

1. 删除 `triangle` 后是否仍可完成全部真实流程；
2. Python 3.12 是否作为正式发布版本；
3. helper 是否能在共享目录中正常运行；
4. helper 的完整动态库依赖；
5. helper 是否静态链接部分 SCOREC/PUMI 库；
6. 不设置 `PYTHONPATH` 时是否可以运行；
7. 不设置 helper 环境变量、只依赖 `PATH` 时是否可以运行；
8. 普通组员权限下是否能执行完整流程；
9. modulefile 与包装脚本哪种更适合当前服务器；
10. 共享环境是否可以由不同用户并发只读使用。

---

## 20. 推荐的近期行动顺序

建议主 Agent 按以下顺序指挥后续工作：

```text
第 1 步：
读取实时 LinkMesh_Architecture_Plan.md、CONTEXT.md、History.md 和相关源码。

第 2 步：
把本文中的直接证据与当前蓝图逐项对照，列出冲突和缺口。

第 3 步：
由 User 确认交付架构决策：
- helper 新名称；
- 开发/发布环境分离；
- 共享只读环境；
- 普通用户不编译 helper；
- 包装命令或 modulefile 方向。

第 4 步：
先修改技术蓝图，不先改业务源码。

第 5 步：
完成 helper 全量命名迁移。

第 6 步：
补齐标准 Python 包安装能力，使 LinkMesh 不依赖 PYTHONPATH。

第 7 步：
在个人目录创建干净发布候选环境。

第 8 步：
验证不安装 triangle 的候选环境。

第 9 步：
完整审计 helper 的构建和动态库依赖。

第 10 步：
执行完整自动测试和真实端到端验证。

第 11 步：
向导师确认共享软件根目录和权限。

第 12 步：
创建第一个版本化共享 release。

第 13 步：
提供统一包装入口；若条件允许，再提供 modulefile。

第 14 步：
使用普通组员账号或等价权限进行最终可用性验证。

第 15 步：
发布并保存版本、环境和验收记录。
```

---

## 21. 面向蓝图迭代的建议决策摘要

以下内容可作为主 Agent 提交给 User 确认的架构决策候选：

```text
D1. LinkMesh 正式区分个人开发环境、个人发布候选环境和组内共享发布环境。

D2. 组内共享环境采用版本化、普通用户只读的运行前缀，不直接共享开发者个人 Conda 环境。

D3. 普通组员不需要自行安装 Conda，不需要自行编译 native helper。

D4. 普通组员原则上不需要手工 conda activate；通过包装命令或 modulefile 进入正确运行环境。

D5. LinkMesh 正式发布不得依赖开发者个人 PYTHONPATH 或个人源码目录。

D6. helper 正式更名为：
- 源码目录 native/linkmesh_scorec_helper/
- target/executable linkmesh-scorec-helper
- 环境变量 LINKMESH_SCOREC_HELPER
- 构建目录 $HOME/LinkMesh_build/linkmesh_scorec_helper/
- 安装位置 <release-env>/bin/linkmesh-scorec-helper

D7. helper 定位顺序保持：
helper_path → LINKMESH_SCOREC_HELPER → PATH 中的 linkmesh-scorec-helper → 失败。

D8. helper 由维护者针对目标服务器的 MPI 和 SCOREC/PUMI 软件栈构建并安装，普通用户只运行。

D9. helper 与 Python LinkMesh 属于同一个发布版本，必须一同验收和发布。

D10. 共享环境不得原地升级；新版本使用新的 release 目录，验收后再切换 current。

D11. triangle 是否保留为正式依赖，必须由不安装 triangle 的干净发布候选环境端到端测试裁决。

D12. 共享根目录、组权限和 modulefile 支持情况由导师确认，蓝图在确认前使用占位符，不硬编码 /share。

D13. 服务器当前采用直接上传源码，不将 git pull 写成现有服务器流程。

D14. 每个共享 release 必须保存版本清单、native 软件栈信息和端到端验收记录。
```

---

## 22. 当前事实的最终汇总

### 22.1 已由服务器直接确认

```text
当前用户：
lxzeng

当前用户组：
lxzeng、users、m3dc1

当前 Conda 环境：
/home/lxzeng/miniconda3/envs/linkmesh

当前 Python：
/home/lxzeng/miniconda3/envs/linkmesh/bin/python
Python 3.12.13

当前 LinkMesh 来源：
/home/lxzeng/LinkMesh_server/src/linkmesh
通过 PYTHONPATH 导入，尚非正式安装状态

当前 OFT：
openfusiontoolkit 26.6
来自 Conda 环境 site-packages

当前 triangle：
triangle 20250106
已安装，但未发现 LinkMesh 直接导入，也未被 OFT 包元数据声明为依赖

当前 helper 定位：
环境变量 LINKMESH_M3DC1_SMB_HELPER

当前 helper：
/home/lxzeng/LinkMesh_runs/m4_2_helper_build/linkmesh-m3dc1-smb-helper

helper 类型：
Linux x86-64 动态链接 ELF
包含 debug_info
not stripped

当前观察到的 helper 动态库：
系统路径 libmpi.so.40
系统路径 libstdc++.so.6

当前主目录权限：
/home/lxzeng 为 750，不能作为可靠的组内公共软件路径

当前 module 状态：
No modules loaded

服务器代码管理：
直接上传，不通过服务器 Git 工作流
```

### 22.2 User 已明确决定

```text
helper 目标新命名：
native/linkmesh_scorec_helper/
linkmesh-scorec-helper
LINKMESH_SCOREC_HELPER
$HOME/LinkMesh_build/linkmesh_scorec_helper/
$CONDA_PREFIX/bin/linkmesh-scorec-helper
```

### 22.3 当前推荐但尚未正式写入蓝图的交付方案

```text
个人开发环境
+
干净发布候选环境
+
导师批准的组内共享、版本化、普通用户只读环境
+
维护者预编译的 helper
+
包装命令或 modulefile
```

普通用户目标体验：

```text
不安装 Conda
不编译 helper
不设置 PYTHONPATH
不手工设置 LINKMESH_SCOREC_HELPER
不进入开发者个人目录
只运行统一的 LinkMesh 命令
```

---

## 23. 结论

当前 LinkMesh 在服务器上采用的是：

```text
个人 Conda 依赖环境
+
个人 PYTHONPATH 源码
+
个人构建目录中的 helper
+
环境变量显式定位 helper
```

这是一套合理的开发验证结构，但不是适合组内长期使用的正式交付结构。

推荐把正式交付架构迭代为：

```text
开发者个人环境：
继续用于开发、调试和服务器验证。

发布候选环境：
从零构建，验证无 PYTHONPATH、正式安装、依赖最小化和 helper 安装。

组内共享环境：
位于导师批准的共享软件目录；
按版本建立 release；
普通用户只读；
包含正式安装的 LinkMesh 和预编译的 linkmesh-scorec-helper；
通过包装命令或 modulefile 提供统一入口；
不要求普通用户安装 Conda、激活个人环境或编译 C++ helper。
```

helper 新命名已经由 User 与主 Agent同意，应通过“先更新蓝图、再同步修改源码/CMake/测试/文档、再重新构建和验收”的方式完成，不应只修改单一文件名。

共享 Conda 环境是当前场景下可行且推荐的方案之一，但必须准确理解为：

```text
Conda 负责提供和隔离用户级运行前缀；
helper 仍是与服务器 MPI/SCOREC/PUMI 软件栈相关的 Linux 二进制；
普通用户只消费经过维护者验证的共享 release；
共享根目录和权限必须由导师确认。
```