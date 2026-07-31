# LinkMesh 组内用户使用与 Case 管理方案

## 1. 文档目的

本文提出 LinkMesh 在课题组服务器和 M3D-C1 开发工作流中的近期使用方案，重点解决以下问题：

1. LinkMesh 尚处于开发阶段，暂不进行需要管理员 `sudo` 权限的服务器全局安装；
2. M3D-C1 采用按编号组织源码版本和计算 Case 的开发方式；
3. 每个 Case 需要保存自己的网格生成配置；
4. 用户应通过简短、统一的命令生成 M3D-C1 所需的配套 TXT 与 SMB；
5. LinkMesh 的内建默认值、`linkmesh.in` 和命令行参数应形成清晰的覆盖关系；
6. 当前阶段仍需保留 PNG 网格图供人工检查；
7. 后续应逐步从个人源码使用过渡到用户级安装，最终再评估服务器统一安装。

---

## 2. 当前已完成的最小闭环

LinkMesh 已在服务器上使用真实 DIII-D GFile 跑通以下单区域链路：

```text
GFile/EQDSK
→ 读取 LCFS、第一壁和磁轴
→ 以 LCFS 作为单区域计算域边界
→ OFT/Triangle 生成二维三角网格
→ Mesh2D
→ M3D-C1 analytic model TXT
→ PUMI native SMB
→ PNG 网格人工检查图
```

本次真实运行结果为：

```text
节点数：344
三角形数：631
区域数：1
TXT：成功生成
SMB：成功生成
PNG：成功生成
PNG 人工检查：无明显问题
```

当前已经生成的 TXT 与 SMB 已交给组内同学进行真实 M3D-C1/SCOREC 消费验证。

因此，当前状态可表述为：

```text
LinkMesh 单区域网格生成侧最小闭环：已跑通
PNG 人工几何检查：已通过
真实 M3D-C1 消费验证：进行中
多区域网格：尚未进入
```

---

## 3. M3D-C1 Case 管理背景

课题组对 M3D-C1 的使用不仅包括运行已有程序，也包括持续修改和开发源码。因此，Case 编号同时承担“源码版本”和“输入参数版本”的管理功能。

例如：

```text
100/    完整保存某一版 M3D-C1 源码和编译结果
101/    复用 100 的源码版本，只修改输入文件
102/    复用 100 的源码版本，只修改输入文件

200/    完整保存更新后的 M3D-C1 源码和编译结果
201/    复用 200 的源码版本，只修改输入文件
202/    复用 200 的源码版本，只修改输入文件
```

其中：

- `100`、`200` 等目录代表新的 M3D-C1 源码版本；
- `101`、`102`、`201`、`202` 等目录主要代表不同物理参数、平衡文件、网格尺度或求解设置；
- 只有进入新的源码版本系列时才需要复制或检出完整 M3D-C1 源码；
- 同一源码版本下的多个 Case 不需要重复保存完整源码。

LinkMesh 应适应该工作流，而不是要求每个 Case 都复制一份 LinkMesh 源码。

---

## 4. 当前推荐目录结构

在 LinkMesh 尚未稳定、暂不进行服务器全局安装的阶段，建议将一份个人维护的 LinkMesh 源码与各个 M3D-C1 Case 放在同一层级：

```text
work/
├── LinkMesh/
│   ├── src/
│   ├── native/
│   │   └── m3dc1_smb_helper/
│   ├── build/
│   │   └── m3dc1_smb_helper/
│   ├── tests/
│   └── LinkMesh_Architecture_Plan.md
│
├── 100/
│   ├── M3D-C1 源码或编译结果
│   ├── gfile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   ├── job.slurm
│   └── mesh/
│       ├── mesh.txt
│       ├── mesh0.smb
│       └── mesh.png
│
├── 101/
│   ├── gfile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   ├── job.slurm
│   └── mesh/
│
├── 102/
│   └── ...
│
├── 200/
│   ├── 更新后的 M3D-C1 源码或编译结果
│   ├── gfile
│   ├── m3dc1.in
│   ├── linkmesh.in
│   ├── job.slurm
│   └── mesh/
│
└── 201/
    └── ...
```

该结构具有以下特点：

1. LinkMesh 源码只维护一份；
2. LinkMesh 与 `100`、`200` 等 M3D-C1 Case 处于同一层；
3. 每个 Case 保存自己的 `linkmesh.in`；
4. 每个 Case 保存自己的 GFile、M3D-C1 输入和网格产物；
5. `linkmesh.in` 记录该 Case 的网格生成条件；
6. TXT、SMB 和 PNG 可以作为 Case 输入的一部分长期保留；
7. 更换 M3D-C1 源码版本不会自动破坏原有 Case 网格。

---

## 5. LinkMesh 的用户调用方式

### 5.1 标准调用

用户进入某个 Case 目录后，通过该目录中的 `linkmesh.in` 运行：

```bash
python -m linkmesh --config linkmesh.in
```

这条命令应成为组内最基本的 LinkMesh 使用方式。

它表示：

```text
使用当前 Python/Conda 环境中的 LinkMesh
→ 显式读取当前 Case 的 linkmesh.in
→ 读取配置中指定的 GFile
→ 生成配置中指定的 TXT、SMB 和 PNG
```

### 5.2 临时覆盖网格尺度

如果用户只想临时修改网格细密程度，而不修改 `linkmesh.in`，可以执行：

```bash
python -m linkmesh \
  --config linkmesh.in \
  --plasma-dx 0.05
```

这里：

- `--config linkmesh.in` 指定 Case 的正式配置文件；
- `--plasma-dx 0.05` 临时覆盖配置文件中的单区域网格尺度；
- `0.05` 的单位为米；
- 配置文件本身不会被修改。

### 5.3 临时生成另一套网格

如果需要保留原网格，同时生成一套更细的网格，可以继续覆盖输出路径：

```bash
python -m linkmesh \
  --config linkmesh.in \
  --plasma-dx 0.05 \
  --model mesh/fine.txt \
  --smb mesh/fine.smb \
  --plot mesh/fine.png
```

实际生成：

```text
mesh/fine.txt
mesh/fine0.smb
mesh/fine.png
```

其中，命令中传入的 `fine.smb` 是 SMB 基础路径；PUMI 在单进程 rank 0 下实际生成 `fine0.smb`。

---

## 6. 配置优先级

LinkMesh 当前配置优先级为：

```text
内建默认值 < linkmesh.in < 显式 CLI 参数
```

其含义如下。

### 6.1 内建默认值

内建默认值负责提供最低层的基础设置，例如：

```text
plasma_dx = 0.08 m
vacuum_dx = 0.10 m
outer_dx = 0.15 m
verbose = false
```

默认值用于兜底，不应作为正式科研 Case 的唯一配置记录。

### 6.2 `linkmesh.in`

`linkmesh.in` 保存当前 Case 的稳定网格配置，例如：

```text
目标输出类型
GFile 路径
区域策略
计算域边界来源
网格尺度
TXT、SMB 和 PNG 输出路径
日志设置
```

它是该 Case 网格生成过程的可复现记录。

### 6.3 显式 CLI 参数

命令行参数用于本次运行临时覆盖配置文件，例如：

```bash
python -m linkmesh \
  --config linkmesh.in \
  --plasma-dx 0.05
```

如果 `linkmesh.in` 中写的是：

```toml
plasma_dx = 0.08
```

本次实际使用值仍为：

```text
plasma_dx = 0.05 m
```

因此，正式推荐原则是：

```text
稳定设置写入 linkmesh.in
临时实验通过 CLI 覆盖
科学计算不要只依赖隐含默认值
```

---

## 7. 单区域 M3D-C1 标准 `linkmesh.in`

当前已经跑通的单区域 M3D-C1 Case 可以使用以下标准配置：

```toml
schema_version = 1

[task]
target = "m3dc1"

[input]
gfile = "g192185.02440"

[domain]
profile = "single_region"
boundary_source = "lcfs"

[mesh]
plasma_dx = 0.08

[output]
model = "mesh/DIIID.txt"
smb = "mesh/DIIID.smb"
plot = "mesh/DIIID.png"

[runtime]
verbose = true
```

各字段含义如下。

### 7.1 Schema

```toml
schema_version = 1
```

声明该文件采用 LinkMesh v1 配置格式。

### 7.2 输出目标

```toml
[task]
target = "m3dc1"
```

表示生成 M3D-C1 所需的配套 TXT 与 SMB。

### 7.3 GFile 输入

```toml
[input]
gfile = "g192185.02440"
```

表示读取当前 Case 中的 GFile。

配置文件中的相对路径统一相对于 `linkmesh.in` 所在目录解析，而不是相对于 LinkMesh 源码目录解析。

### 7.4 单区域计算域

```toml
[domain]
profile = "single_region"
boundary_source = "lcfs"
```

表示：

- 只生成一个计算区域；
- 使用 GFile 中的 LCFS 作为该区域的外边界；
- 当前 M3D-C1 路径暂不开放多区域、多 face 和其他边界来源。

### 7.5 网格尺度

```toml
[mesh]
plasma_dx = 0.08
```

表示向 OFT 提供 `0.08 m` 的单区域目标网格尺度。

它是目标局部尺度，不要求每条网格边严格等于 `0.08 m`。

### 7.6 输出文件

```toml
[output]
model = "mesh/DIIID.txt"
smb = "mesh/DIIID.smb"
plot = "mesh/DIIID.png"
```

最终生成：

```text
mesh/DIIID.txt
mesh/DIIID0.smb
mesh/DIIID.png
```

### 7.7 运行日志

```toml
[runtime]
verbose = true
```

要求 LinkMesh 输出 GFile、LCFS、磁轴、节点数、三角形数和文件路径等基本信息。

---

## 8. 网格文件应在什么时候生成

对于 M3D-C1 Case，有三种可能方式。

### 8.1 提交求解作业前生成

```text
进入 Case
→ 运行 LinkMesh
→ 生成 TXT、SMB 和 PNG
→ 人工检查 PNG
→ 提交 M3D-C1 作业
```

这是当前阶段最稳妥的方式。

优点：

1. 网格生成和求解器运行边界清楚；
2. 可以在消耗大规模计算资源前检查网格；
3. 同一网格可以被多次 M3D-C1 运行复用；
4. LinkMesh 错误与 M3D-C1 错误不会混在同一个 Slurm 日志中；
5. 不会在每次提交作业时覆盖已经确认的网格。

### 8.2 在 M3D-C1 `job.slurm` 中无条件生成

形式上可以写成：

```bash
python -m linkmesh --config linkmesh.in
srun ./m3dc1
```

但当前不建议作为默认流程。

原因包括：

1. 每次提交都重复生成相同网格；
2. 修改求解参数也会无意义地重新生成网格；
3. 新网格未经人工检查便立即进入求解；
4. TXT、SMB 和 PNG 可能被自动覆盖；
5. LinkMesh、OFT、PUMI、MPI 和 M3D-C1 的错误会混合；
6. 难以追踪某次物理结果实际使用了哪份网格。

### 8.3 独立的网格预处理作业

如果服务器不允许在登录节点运行 LinkMesh，可以设置一个轻量网格预处理作业：

```text
sbatch mesh.slurm
→ 生成 TXT、SMB 和 PNG
→ 人工检查 PNG
→ sbatch job.slurm
```

这种方式仍然保持网格生成与求解器运行相互独立。

---

## 9. 当前推荐工作流

当前推荐以下工作流：

```text
1. 建立或进入 M3D-C1 Case 目录；
2. 准备 GFile、m3dc1.in 和 linkmesh.in；
3. 执行：
   python -m linkmesh --config linkmesh.in
4. 检查生成的 PNG；
5. 确认 TXT 与 SMB 已生成；
6. 将 TXT 和 SMB 作为该 Case 的固定输入；
7. 提交 M3D-C1 Slurm 作业；
8. 修改 M3D-C1 求解参数时复用同一网格；
9. 只有 GFile、计算域策略或网格尺度改变时才重新生成网格。
```

因此，现阶段不建议在每次 `sbatch` 中无条件调用 LinkMesh。

可以在 M3D-C1 作业脚本开头检查文件是否存在：

```bash
test -s mesh/DIIID.txt || {
  echo "ERROR: 缺少 mesh/DIIID.txt，请先运行 LinkMesh"
  exit 1
}

test -s mesh/DIIID0.smb || {
  echo "ERROR: 缺少 mesh/DIIID0.smb，请先运行 LinkMesh"
  exit 1
}
```

这只检查输入，不重新生成或覆盖网格。

---

## 10. LinkMesh 的部署方式

### 10.1 当前：个人源码模式

LinkMesh 尚未稳定，因此暂时不请求老师使用 `sudo` 进行服务器全局安装。

当前采用：

```text
LinkMesh 与 100、200 等 Case 同级
每位开发者维护一份自己的 LinkMesh 源码
每个 Case 保存自己的 linkmesh.in
```

在开发阶段，C++ helper 的源码和 Python 源码都属于 LinkMesh 仓库。

C++ helper 的关系是：

```text
native/m3dc1_smb_helper/main.cc
→ CMake + MPI + SCOREC/PUMI 编译
→ linkmesh-m3dc1-smb-helper
→ Python smb_writer.py 调用
→ PUMI writeNative()
→ <base>0.smb
```

`native/m3dc1_smb_helper/` 是正式源码，不是临时 probe。

### 10.2 推荐中间状态：Conda 用户级安装

后续最适合组内日常使用、同时不需要 `sudo` 的方案，是把 LinkMesh 安装到每位用户自己的 Conda 环境中。

目标结构：

```text
个人 Conda 环境
├── LinkMesh Python 包
├── NumPy、h5py、matplotlib、OFT 等依赖
└── bin/linkmesh-m3dc1-smb-helper
```

激活环境后，用户可以在任意 Case 中直接执行：

```bash
python -m linkmesh --config linkmesh.in
```

而不需要每次指定：

```text
PYTHONPATH
LinkMesh 源码路径
helper 构建目录
LINKMESH_M3DC1_SMB_HELPER
```

这种安装方式具有以下优点：

1. 不需要 `sudo`；
2. 每位用户可以维护自己的版本；
3. Python 包和 C++ helper 与 Conda 环境绑定；
4. 激活环境后即可直接使用；
5. 删除 Conda 环境时可以完整移除；
6. 不污染服务器全局环境；
7. 适合 LinkMesh 尚在开发的阶段。

### 10.3 未来：服务器统一安装

当 LinkMesh 的接口、依赖和 M3D-C1 消费契约稳定后，可以再评估由老师或管理员统一安装。

统一安装的潜在目标是：

```text
组内成员加载统一环境
→ 进入任意 Case
→ python -m linkmesh --config linkmesh.in
```

但在快速开发阶段，全局安装会增加版本更新、依赖冲突和管理员维护成本，因此暂不采用。

---

## 11. 面向用户的改进目标

LinkMesh 下一阶段的用户体验目标不是增加新的网格算法，而是把当前已经跑通的最小闭环整理成普通组员容易使用的工具。

建议优先完成以下改进。

### 11.1 标准配置模板

在 LinkMesh 仓库中提供一个单区域 M3D-C1 配置模板，例如：

```text
examples/m3dc1_single_region/linkmesh.in.example
```

用户复制到自己的 Case 中并改名为：

```text
linkmesh.in
```

### 11.2 简短用户说明

提供一页简明说明，只保留最常用命令：

```bash
python -m linkmesh --config linkmesh.in
```

临时覆盖网格尺度：

```bash
python -m linkmesh \
  --config linkmesh.in \
  --plasma-dx 0.05
```

### 11.3 用户级安装

建立不需要 `sudo` 的安装过程，使 Python 包和 C++ helper 一起进入个人 Conda 环境。

### 11.4 清理开发阶段命名

普通用户不应接触以下开发阶段概念：

```text
M4-2
probe
runtime validation
helper build experiment
Level 2/3 loader
```

用户只需要理解：

```text
GFile
linkmesh.in
TXT
SMB
PNG
```

### 11.5 保持模块边界

用户体验改进不得改变 LinkMesh 的正式职责：

```text
LinkMesh 负责生成 TXT、SMB 和 PNG
M3D-C1 负责消费 TXT 与 SMB
LinkMesh 不建设 SMB loader 或 M3D-C1 验证器
OFT/Triangle 仍是唯一二维网格生成底座
PUMI 只负责 classified APF/MDS 网格与 SMB 写出
```

---

## 12. 建议向组内成员提供的最简说明

组内用户日常只需要理解以下内容。

### 首次生成 Case 网格

```bash
cd 100
python -m linkmesh --config linkmesh.in
```

### 临时生成更细网格

```bash
python -m linkmesh \
  --config linkmesh.in \
  --plasma-dx 0.05
```

### 配置优先级

```text
内建默认值 < linkmesh.in < CLI 显式参数
```

### 生成结果

```text
TXT：M3D-C1 analytic geometric model
SMB：PUMI native 静态网格
PNG：二维网格人工检查图
```

### 使用原则

```text
先生成网格
→ 检查 PNG
→ 固化 TXT 与 SMB
→ 再提交 M3D-C1 作业
```

修改求解参数不必重新生成网格；修改 GFile、边界策略或网格尺度时需要重新生成。

---

## 13. 当前结论

现阶段建议采用以下方案：

```text
1. LinkMesh 暂不进行 sudo 全局安装；
2. LinkMesh 源码与 100、200 等 M3D-C1 Case 放在同一层；
3. 每位开发者维护一份个人 LinkMesh；
4. 每个 Case 只保存自己的 linkmesh.in、GFile、M3D-C1 输入和网格产物；
5. 用户通过 python -m linkmesh --config linkmesh.in 生成网格；
6. CLI 参数可以临时覆盖 linkmesh.in；
7. 配置优先级固定为：
   内建默认值 < linkmesh.in < 显式 CLI；
8. TXT、SMB 和 PNG 在 M3D-C1 求解前生成；
9. PNG 人工检查后再提交正式计算；
10. 当前不把 LinkMesh 无条件嵌入每次 M3D-C1 sbatch 求解作业；
11. 下一步建设无需 sudo 的 Conda 用户级安装；
12. LinkMesh 稳定后再评估服务器统一安装。
```

该方案兼顾：

```text
M3D-C1 源码版本开发
Case 输入参数管理
LinkMesh 快速迭代
网格生成可复现性
人工检查
超算作业安全性
组内用户使用简洁性
```

当前已经完成的单区域 `GFile → TXT + SMB + PNG` 最小闭环可以作为该使用方案的第一条正式工作流。