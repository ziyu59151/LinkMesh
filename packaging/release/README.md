# LinkMesh 0.1.0 Prototype 2 Linux x86-64 Release

## 1. 交付内容

本目录包含：

```text
README.md
linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz
linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz.sha256
example
```

其中：

- `README.md`：环境检查和运行指南；
- `linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz`：LinkMesh Linux x86-64 Release；
- `.sha256` 文件：用于检查 Release 压缩包在传输后是否完整。
- `example`：包含 m3dc1 和 trimeg 样例文件夹各一个，用于测试。其中，m3
dc1_case 中包含一个2d数组形式的边界 + 一个标准配置文件，trimeg_case 中包含一个2d数组形式的边界 + 一个 EQDSK 平衡文件。

Release 已携带：

- LinkMesh Python 包；
- OpenFUSIONToolkit 26.6；
- OpenFUSIONToolkit 配套 Linux 原生库；
- `linkmesh-scorec-helper`；
- 静态链接进 helper 的 SCOREC/PUMI 组件；
- LinkMesh 启动器；
- LinkMesh 分层环境检查器。

Release 不携带：

- Python 解释器；
- NumPy；
- h5py；
- Matplotlib；
- MPI；
- glibc；
- libstdc++。

目标环境应为 Linux x86-64，并提供可用的 Python 3 环境。

本 Release 的构建和直接验证环境使用 CPython 3.12.13。其他 Python 3 版本需要在目标服务器上实际检查。

---

## 2. 校验并解压 Release

进入三个交付文件所在目录，然后执行：

```bash
set -euo pipefail

ARCHIVE="linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"

sha256sum -c "$CHECKSUM"
tar -xzf "$ARCHIVE"
```

校验成功时应显示：

```text
linkmesh-release-0.1.0-prototype2-linux-x86_64.tar.gz: OK
```

解压后得到：

```text
linkmesh-release-0.1.0-prototype2-linux-x86_64/
├── bin/
├── manifest/
└── python/
```

记录 Release 的绝对路径：

```bash
RELEASE="$PWD/linkmesh-release-0.1.0-prototype2-linux-x86_64"
```

确认主要入口存在：

```bash
test -x "$RELEASE/bin/linkmesh"
test -x "$RELEASE/bin/linkmesh-check"

ls -lh \
    "$RELEASE/bin/linkmesh" \
    "$RELEASE/bin/linkmesh-check" \
    "$RELEASE/bin/linkmesh-scorec-helper"
```

后续即使进入其他运行目录，`RELEASE` 仍然指向同一个解压后的 Release。

---

## 3. Python 的选择逻辑

LinkMesh Release 不包含 Python 解释器，因此运行时会使用服务器上已有的 Python。

Release 启动器按照以下优先级选择 Python：

1. 如果设置了 `LINKMESH_PYTHON`，使用该变量指定的 Python；
2. 否则搜索当前 `PATH` 中的 `python3`；
3. 如果没有 `python3`，再搜索当前 `PATH` 中的 `python`；
4. 如果都找不到，启动器停止并报告错误。

如果当前服务器只有一个合适的 Python，通常不需要设置 `LINKMESH_PYTHON`，可以直接运行：

```bash
"$RELEASE/bin/linkmesh-check" core
"$RELEASE/bin/linkmesh" -h
```

如果服务器上有多个 Python，建议显式选择已经安装任务依赖的解释器：

```bash
export LINKMESH_PYTHON="/absolute/path/to/python"
```

`LINKMESH_PYTHON` 必须指向 Python 可执行文件，不能只指向环境目录。

正确示例：

```bash
export LINKMESH_PYTHON="/home/user/miniconda3/envs/linkmesh/bin/python"
```

错误示例：

```bash
export LINKMESH_PYTHON="/home/user/miniconda3/envs/linkmesh"
```

查看当前终端能够找到的 Python：

```bash
command -v python3 || command -v python
```

查看所有候选：

```bash
type -a python3 python 2>/dev/null
```

保存自动找到的 Python 路径：

```bash
PYTHON_CANDIDATE="$(command -v python3 || command -v python)"

printf 'Python candidate: %s\n' "$PYTHON_CANDIDATE"
"$PYTHON_CANDIDATE" --version
```

需要显式指定时执行：

```bash
export LINKMESH_PYTHON="$PYTHON_CANDIDATE"
```

使用本 Release 不需要设置 `PYTHONPATH`。Release 启动器会自动加载包内的 LinkMesh 和 OpenFUSIONToolkit。

---

## 4. Conda、venv 和系统 Python

Conda 不是运行 LinkMesh Release 的硬性要求。

可以使用：

- Conda 环境；
- Python `venv`；
- 已经满足依赖的系统 Python；
- 其他兼容的 Python 3 环境。

无论使用哪一种 Python 环境，LinkMesh 的推荐调用方式都相同：

```bash
"$RELEASE/bin/linkmesh" -h
```

使用配置文件时：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

不要把下面的源码运行方式用于本 Release：

```bash
python -m linkmesh
```

`python -m linkmesh` 要求 `linkmesh` 已经安装在当前 Python 环境中。Release 启动器则会自动加载 Release 自带的 LinkMesh 和 OpenFUSIONToolkit，并选择正确的 helper。

### 4.1 使用 Conda 环境

查看已有环境：

```bash
conda env list
```

激活环境：

```bash
conda activate linkmesh
```

查看 Python：

```bash
command -v python
python --version
```

可以让 Release 从当前 `PATH` 自动选择，也可以显式指定：

```bash
export LINKMESH_PYTHON="$(command -v python)"
```

检查依赖：

```bash
"$LINKMESH_PYTHON" -c "import numpy; print('NumPy:', numpy.__version__)"
"$LINKMESH_PYTHON" -c "import h5py; print('h5py:', h5py.__version__)"
"$LINKMESH_PYTHON" -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)"
```

如果环境缺少依赖，并且允许修改该环境，可以安装：

```bash
conda install numpy h5py matplotlib
```

该命令会修改当前 Conda 环境。共享环境应先确认是否允许安装软件。

### 4.2 使用已有系统 Python

查找 Python：

```bash
command -v python3 || command -v python
```

如果使用 `python3`：

```bash
export LINKMESH_PYTHON="$(command -v python3)"
"$LINKMESH_PYTHON" --version
```

检查依赖：

```bash
"$LINKMESH_PYTHON" -c "import numpy; print('NumPy:', numpy.__version__)"
"$LINKMESH_PYTHON" -c "import h5py; print('h5py:', h5py.__version__)"
"$LINKMESH_PYTHON" -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)"
```

如果系统 Python 已经包含所需依赖，也可以不设置 `LINKMESH_PYTHON`，由 Release 自动选择。

### 4.3 创建 Python venv

如果系统提供 `python3` 和 `venv`，可以创建独立虚拟环境：

```bash
python3 -m venv "$HOME/venvs/linkmesh-release"
source "$HOME/venvs/linkmesh-release/bin/activate"
```

安装 Python 依赖：

```bash
python -m pip install --upgrade pip
python -m pip install numpy h5py matplotlib
```

选择该环境中的 Python：

```bash
export LINKMESH_PYTHON="$(command -v python)"
```

确认环境：

```bash
"$LINKMESH_PYTHON" --version
"$LINKMESH_PYTHON" -c "import numpy, h5py, matplotlib; print('Python dependencies: OK')"
```

创建 venv 和安装依赖会在 `$HOME/venvs/linkmesh-release` 中写入文件，不会修改 Release。

---

## 5. 环境检查

运行核心检查：

```bash
"$RELEASE/bin/linkmesh-check" core
```

查看 CLI：

```bash
"$RELEASE/bin/linkmesh" -h
```

按任务运行分层检查：

```bash
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh-check" m3dc1
```

也可以一次运行全部检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

检查模式含义：

- `core`：检查 Python、Release 内 LinkMesh、OFT 26.6 和 NumPy；
- `trimeg`：在 core 基础上检查 h5py；
- `plot`：在 core 基础上检查 Matplotlib；
- `m3dc1`：检查 helper、ELF、动态库和 MPI；
- `all`：依次运行以上全部检查。

可能出现的状态包括：

```text
OK
MISSING
WARNING
NOT CHECKED
```

其中：

- `OK`：该检查项满足当前诊断条件；
- `MISSING`：缺少对应任务所需条件；
- `WARNING`：发现潜在兼容性问题，需要结合实际运行判断；
- `NOT CHECKED`：该项未完成检查。

环境检查成功不等于 HDF5 或 SMB 已经被外部消费程序加载。

---

## 6. Counted R-Z 边界文件

使用：

```text
boundary_source = "array_file"
```

或 CLI 参数：

```bash
--boundary-source array_file
```

时，需要提供 counted R-Z 边界文本文件。

文件格式为：

1. 第一行是边界点总数 `N`；
2. 后续恰好包含 `N` 行坐标；
3. 每行包含一对 `R Z` 坐标；
4. `R` 在前，`Z` 在后；
5. 坐标单位为米。

示例：

```text
5
1.000000 0.000000
1.200000 0.000000
1.250000 0.200000
1.100000 0.300000
0.950000 0.150000
```

这里的第一行 `5` 表示后面有 5 个边界点。

每个坐标点占一行：

```text
R Z
```

边界点应按照边界曲线上的顺序排列，并共同描述计算区域的闭合边界。

文件名和扩展名没有强制要求，例如可以使用：

```text
boundary.txt
ellipse1.boundary
```

在配置文件中指定：

```toml
[input]
array_file = "boundary.txt"
```

使用 CLI 时指定：

```bash
--array-file /absolute/path/to/boundary.txt
```

---

## 7. 路径规则

LinkMesh 接受绝对路径和相对路径。

绝对路径示例：

```text
/home/user/cases/ellipse1.boundary
/home/user/output/mesh.h5
```

相对路径示例：

```text
ellipse1.boundary
mesh.h5
mesh.png
```

本版本中，配置文件和 CLI 参数里的相对路径都相对于**执行 LinkMesh 命令时的当前目录**解析。

例如：

```text
/home/user/m3dc1_case/
├── linkmesh.in
└── ellipse1.boundary
```

配置文件中写入：

```toml
[input]
array_file = "ellipse1.boundary"

[output]
model = "ellipse1.txt"
smb = "ellipse1.smb"
plot = "ellipse1.png"
```

应先进入案例目录：

```bash
cd /home/user/m3dc1_case
```

然后运行：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

此时输入路径解析为：

```text
/home/user/m3dc1_case/ellipse1.boundary
```

输出写入：

```text
/home/user/m3dc1_case/ellipse1.txt
/home/user/m3dc1_case/ellipse10.smb
/home/user/m3dc1_case/ellipse1.png
```

即使通过绝对路径指定其他目录中的 `linkmesh.in`，配置文件内部的相对路径仍然依据运行命令时的当前目录解析。因此，推荐每个案例使用独立目录，并从该目录运行 LinkMesh。

CLI 中的相对路径遵循同样规则。例如：

```bash
cd /home/user/trimeg_case

"$RELEASE/bin/linkmesh" \
    --no-config \
    --target trimeg \
    --profile single_region \
    --boundary-source array_file \
    --array-file boundary.txt \
    --mesh-dx 0.02 \
    --hdf5 mesh.h5 \
    --plot mesh.png
```

其中输入和输出路径都相对于：

```text
/home/user/trimeg_case
```

如果不确定当前目录，可以执行：

```bash
pwd
```

如果希望避免相对路径产生歧义，可以在 CLI 中使用绝对路径。

---

## 8. 使用 `linkmesh.in` 配置文件

LinkMesh 支持通过 `--config` 显式加载一个配置文件：

```bash
"$RELEASE/bin/linkmesh" \
    --config /absolute/path/to/linkmesh.in
```

配置文件不存在、无法读取或不符合当前 schema 时，LinkMesh 会停止并报告错误。

建议每次运行使用独立目录：

```text
run_directory/
├── linkmesh.in
└── boundary.txt
```

进入该目录后运行：

```bash
cd /absolute/path/to/run_directory

"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

无论当前使用 Conda、venv 还是系统 Python，LinkMesh 命令都不变。区别只在于 Release 自动选择或通过 `LINKMESH_PYTHON` 指定哪个 Python。

### 8.1 M3D-C1 配置示例

目录结构：

```text
m3dc1_case/
├── linkmesh.in
└── ellipse1.boundary
```

`linkmesh.in`：

```toml
schema_version = 1

[task]
target = "m3dc1"

[input]
array_file = "ellipse1.boundary"

[domain]
profile = "single_region"
boundary_source = "array_file"

[mesh]
plasma_dx = 0.08

[output]
model = "ellipse1.txt"
smb = "ellipse1.smb"
plot = "ellipse1.png"

[runtime]
verbose = true
```

进入案例目录：

```bash
cd /absolute/path/to/m3dc1_case
```

使用 Conda 时，可以执行：

```bash
conda activate linkmesh
export LINKMESH_PYTHON="$(command -v python)"

"$RELEASE/bin/linkmesh-check" m3dc1
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

使用 venv 时，可以执行：

```bash
source "$HOME/venvs/linkmesh-release/bin/activate"
export LINKMESH_PYTHON="$(command -v python)"

"$RELEASE/bin/linkmesh-check" m3dc1
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

使用系统 Python，或者让 Release 自动选择时，可以执行：

```bash
unset LINKMESH_PYTHON

"$RELEASE/bin/linkmesh-check" m3dc1
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

预期生成：

```text
ellipse1.txt
ellipse10.smb
ellipse1.png
```

配置中的 SMB 基础路径是：

```text
ellipse1.smb
```

SCOREC helper 会管理 rank-0 文件名，因此实际文件通常为：

```text
ellipse10.smb
```

### 8.2 TRIMEG 配置示例

目录结构：

```text
trimeg_case/
├── linkmesh.in
└── boundary.txt
```

`linkmesh.in`：

```toml
schema_version = 1

[task]
target = "trimeg"

[input]
array_file = "boundary.txt"

[domain]
profile = "single_region"
boundary_source = "array_file"

[mesh]
mesh_dx = 0.02

[output]
hdf5 = "mesh.h5"
plot = "mesh.png"

[runtime]
verbose = true
```

进入案例目录：

```bash
cd /absolute/path/to/trimeg_case
```

使用 Conda 时，可以执行：

```bash
conda activate linkmesh
export LINKMESH_PYTHON="$(command -v python)"

"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

使用 venv 时，可以执行：

```bash
source "$HOME/venvs/linkmesh-release/bin/activate"
export LINKMESH_PYTHON="$(command -v python)"

"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

使用系统 Python，或者让 Release 自动选择时，可以执行：

```bash
unset LINKMESH_PYTHON

"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

预期生成：

```text
mesh.h5
mesh.png
```

### 8.3 配置文件与 CLI 参数

`--config` 用于显式选择配置文件：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in"
```

`--no-config` 用于禁用配置文件自动发现：

```bash
"$RELEASE/bin/linkmesh" \
    --no-config \
    ...
```

`--config` 与 `--no-config` 互斥，不能同时使用。

CLI 中显式给出的任务参数可以覆盖配置文件中的对应值。例如：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/linkmesh.in" \
    --mesh-dx 0.04 \
    --verbose
```

建议：

1. 每个案例使用独立目录；
2. 将配置文件和输入文件放在案例目录中；
3. 进入案例目录后再运行 LinkMesh；
4. 使用绝对路径指定 `--config`；
5. 首次运行前执行对应的 `linkmesh-check`；
6. 不在不同案例间共用相同输出文件名。

---

## 9. 使用 CLI 参数生成 TRIMEG HDF5

如果不使用配置文件，可以用 `--no-config` 和显式 CLI 参数运行。

先记录 Release 的绝对路径：

```bash
RELEASE="/absolute/path/to/linkmesh-release-0.1.0-prototype2-linux-x86_64"
```

创建案例目录并放入 counted R-Z 边界文件：

```text
trimeg_case/
└── boundary.txt
```

进入案例目录：

```bash
cd /absolute/path/to/trimeg_case
```

使用 Conda 时：

```bash
conda activate linkmesh
export LINKMESH_PYTHON="$(command -v python)"
```

使用 venv 时：

```bash
source "$HOME/venvs/linkmesh-release/bin/activate"
export LINKMESH_PYTHON="$(command -v python)"
```

使用系统 Python或让 Release 自动选择时：

```bash
unset LINKMESH_PYTHON
```

运行环境检查：

```bash
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
```

生成 TRIMEG HDF5 和 PNG：

```bash
"$RELEASE/bin/linkmesh" \
    --no-config \
    --target trimeg \
    --profile single_region \
    --boundary-source array_file \
    --array-file "$PWD/boundary.txt" \
    --mesh-dx 0.02 \
    --hdf5 "$PWD/mesh.h5" \
    --plot "$PWD/mesh.png" \
    --verbose
```

预期生成：

```text
mesh.h5
mesh.png
```

检查文件：

```bash
ls -lh \
    "$PWD/mesh.h5" \
    "$PWD/mesh.png"
```

`--mesh-dx` 的单位为米，应按实际几何和网格需求调整。

文件生成成功表示：

```text
GENERATED
```

这不自动表示 TRIMEG 或 MATLAB 已经成功读取该文件。

---

## 10. 使用 CLI 参数生成 M3D-C1 Model 和 SMB

如果不使用配置文件，可以用 `--no-config` 和显式 CLI 参数运行。

先记录 Release 的绝对路径：

```bash
RELEASE="/absolute/path/to/linkmesh-release-0.1.0-prototype2-linux-x86_64"
```

创建案例目录并放入 counted R-Z 边界文件：

```text
m3dc1_case/
└── boundary.txt
```

进入案例目录：

```bash
cd /absolute/path/to/m3dc1_case
```

使用 Conda 时：

```bash
conda activate linkmesh
export LINKMESH_PYTHON="$(command -v python)"
```

使用 venv 时：

```bash
source "$HOME/venvs/linkmesh-release/bin/activate"
export LINKMESH_PYTHON="$(command -v python)"
```

使用系统 Python或让 Release 自动选择时：

```bash
unset LINKMESH_PYTHON
```

检查 M3D-C1 环境：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
```

生成 M3D-C1 model、SMB 和 PNG：

```bash
"$RELEASE/bin/linkmesh" \
    --no-config \
    --target m3dc1 \
    --profile single_region \
    --boundary-source array_file \
    --array-file "$PWD/boundary.txt" \
    --mesh-dx 0.08 \
    --model "$PWD/mesh.txt" \
    --smb "$PWD/mesh.smb" \
    --plot "$PWD/mesh.png" \
    --verbose
```

预期生成：

```text
mesh.txt
mesh0.smb
mesh.png
```

SCOREC helper 会管理 rank-0 SMB 文件名，因此传入：

```text
mesh.smb
```

时，实际生成文件通常为：

```text
mesh0.smb
```

检查文件：

```bash
find "$PWD" \
    -maxdepth 1 \
    -type f \
    -printf '%f %s bytes\n' |
    sort
```

M3D-C1 SMB 路径要求目标系统能够解析兼容的 MPI。当前 helper 需要兼容的 `libmpi.so.40`，并依赖目标系统的 glibc 和 libstdc++。

文件生成成功表示：

```text
GENERATED
```

这不自动表示 M3D-C1 已经加载、初始化或推进该网格。

---

## 11. 依赖边界

### 11.1 Release 已携带

```text
LinkMesh
OpenFUSIONToolkit 26.6
OpenFUSIONToolkit 配套 Linux 原生库
linkmesh-scorec-helper
静态链接进 helper 的 SCOREC/PUMI 组件
```

用户不需要：

- 安装 LinkMesh；
- 安装 OpenFUSIONToolkit；
- 编译 helper；
- 安装 PUMI；
- 设置 `PYTHONPATH`；
- 设置 `LINKMESH_SCOREC_HELPER`；
- 修改 shell 启动文件。

### 11.2 Python 环境需要提供

基础网格路径需要：

```text
Python 3
NumPy
```

TRIMEG HDF5 输出需要：

```text
h5py
```

PNG 自检图需要：

```text
Matplotlib
```

### 11.3 M3D-C1 原生环境需要提供

M3D-C1 SMB 输出还需要：

```text
Linux x86-64
兼容的 MPI
当前可解析的 libmpi.so.40
兼容的 glibc
兼容的 libstdc++
```

即使 Python 环境检查成功，MPI 或系统 ABI 不兼容仍可能导致 SMB helper 无法运行。

---

## 12. 建议反馈的信息

请反馈环境信息：

```bash
uname -a
```

如果显式设置了 Python：

```bash
"$LINKMESH_PYTHON" --version
```

如果使用自动选择：

```bash
command -v python3 || command -v python
python3 --version 2>/dev/null || python --version
```

运行全部环境检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

列出生成物：

```bash
find . \
    -maxdepth 2 \
    -type f \
    -printf '%s %p\n' |
    sort
```

请同时提供：

- 实际执行的 LinkMesh 命令；
- 使用的 `linkmesh.in`；
- 完整 stdout；
- 完整 stderr；
- Python 路径和版本；
- 生成文件的名称和大小；
- HDF5 或 SMB 在消费端达到的验证状态。

验证状态应分别说明：

```text
GENERATED
STRUCTURALLY CHECKED
DELIVERED
LOADED
INITIALIZED
TIME-STEPPED
STABILITY-VALIDATED
PHYSICALLY VALIDATED
```

文件生成成功只代表 `GENERATED`。

它不自动代表：

- 外部程序已经成功加载；
- 求解器已经完成初始化；
- 求解器已经完成时间推进；
- 运行已经达到稳定性要求；
- 物理结果已经得到确认。