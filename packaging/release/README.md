# LinkMesh 0.2.0 Linux x86-64 Release

LinkMesh 是一个用于生成二维 R-Z 非结构三角网格的命令行工具。

主要功能包括：

- 从 GFile/EQDSK 或单条 counted R-Z 边界生成单区域网格；
- 从一个 multi-array 文件生成多区域网格；
- 从 boundary-list 清单及多个独立坐标文件生成多区域网格；
- 为不同 Region 设置不同目标网格尺度；
- 设置 Region interface 尺寸过渡；
- 设置 R-Z point local refinement；
- 输出 TRIMEG HDF5；
- 输出 M3D-C1 model TXT 和 native SMB；
- 生成网格几何 PNG；
- 生成三角形 Shape quality Q PNG。

## 1. 交付内容

交付目录包含三个文件：

```text
README.md
linkmesh-release-0.2.0-linux-x86_64.tar.gz
linkmesh-release-0.2.0-linux-x86_64.tar.gz.sha256
```

其中：

- `README.md`：环境准备、输入格式和运行说明；
- `.tar.gz`：LinkMesh Linux x86-64 Release；
- `.sha256`：Release 压缩包的 SHA-256 校验文件。

Release 压缩包内部结构：

```text
linkmesh-release-0.2.0-linux-x86_64/
├── bin/
│   ├── linkmesh
│   ├── linkmesh-bootstrap.py
│   ├── linkmesh-check
│   └── linkmesh-scorec-helper
├── manifest/
└── python/
    └── site-packages/
        ├── linkmesh/
        ├── OpenFUSIONToolkit/
        └── openfusiontoolkit-26.6.dist-info/
```

Release 已携带：

- LinkMesh；
- OpenFUSIONToolkit 26.6；
- OpenFUSIONToolkit 配套原生库；
- `linkmesh-scorec-helper`；
- helper 所需的 SCOREC/PUMI 核心组件；
- LinkMesh 启动器；
- 环境检查工具；
- 构建和依赖信息；
- Release 内部文件校验清单。

目标环境需要提供：

- Linux x86-64；
- Python 3；
- NumPy；
- h5py，仅在输出 TRIMEG HDF5 时需要；
- Matplotlib，仅在生成 PNG 时需要；
- 兼容的 MPI runtime，仅在输出 M3D-C1 SMB 时需要；
- 兼容的 glibc 和 libstdc++。

## 2. 校验并解压

进入三个交付文件所在目录：

```bash
cd /path/to/LinkMesh-0.2.0-linux-x86_64-release
```

检查文件：

```bash
ls -lh \
    README.md \
    linkmesh-release-0.2.0-linux-x86_64.tar.gz \
    linkmesh-release-0.2.0-linux-x86_64.tar.gz.sha256
```

校验压缩包：

```bash
sha256sum -c \
    linkmesh-release-0.2.0-linux-x86_64.tar.gz.sha256
```

校验成功时应显示：

```text
linkmesh-release-0.2.0-linux-x86_64.tar.gz: OK
```

解压：

```bash
tar -xzf linkmesh-release-0.2.0-linux-x86_64.tar.gz
```

记录解压目录的绝对路径：

```bash
RELEASE="$PWD/linkmesh-release-0.2.0-linux-x86_64"
```

确认主要入口：

```bash
test -x "$RELEASE/bin/linkmesh"
test -x "$RELEASE/bin/linkmesh-check"
test -x "$RELEASE/bin/linkmesh-scorec-helper"

ls -lh \
    "$RELEASE/bin/linkmesh" \
    "$RELEASE/bin/linkmesh-check" \
    "$RELEASE/bin/linkmesh-scorec-helper"
```

校验解压后的内部文件：

```bash
cd "$RELEASE"
sha256sum -c manifest/SHA256SUMS
cd -
```

Release 目录可以整体移动。移动后重新设置 `RELEASE` 即可：

```bash
RELEASE="/new/path/to/linkmesh-release-0.2.0-linux-x86_64"
```

## 3. 准备 Python 环境

Release 不包含 Python 解释器，也不自动修改用户的 Python 环境。

运行 LinkMesh 的 Python 环境至少需要：

```text
Python 3
NumPy
```

生成 TRIMEG HDF5 还需要：

```text
h5py
```

生成 PNG 还需要：

```text
Matplotlib
```

### 3.1 使用已有 Conda 环境

激活已经安装相应依赖的环境：

```bash
conda activate linkmesh
```

检查 Python：

```bash
command -v python
python --version
```

指定 LinkMesh 使用当前环境中的 Python：

```bash
export LINKMESH_PYTHON="$(command -v python)"
```

检查依赖：

```bash
"$LINKMESH_PYTHON" -c \
    "import numpy; print('NumPy:', numpy.__version__)"

"$LINKMESH_PYTHON" -c \
    "import h5py; print('h5py:', h5py.__version__)"

"$LINKMESH_PYTHON" -c \
    "import matplotlib; print('Matplotlib:', matplotlib.__version__)"
```

如果允许修改当前 Conda 环境，可以安装缺失依赖：

```bash
conda install numpy h5py matplotlib
```

该命令会修改当前 Conda 环境。

### 3.2 创建独立 Python venv

如果系统提供 `python3` 和 `venv`，可以创建独立环境：

```bash
python3 -m venv "$HOME/venvs/linkmesh-release"
source "$HOME/venvs/linkmesh-release/bin/activate"
```

安装依赖：

```bash
python -m pip install --upgrade pip
python -m pip install numpy h5py matplotlib
```

选择该环境中的 Python：

```bash
export LINKMESH_PYTHON="$(command -v python)"
```

确认：

```bash
"$LINKMESH_PYTHON" --version

"$LINKMESH_PYTHON" -c \
    "import numpy, h5py, matplotlib; print('Python dependencies: OK')"
```

### 3.3 Python 选择规则

Release 启动器按照以下顺序选择 Python：

1. `LINKMESH_PYTHON` 指定的解释器；
2. 当前 `PATH` 中的 `python3`；
3. 当前 `PATH` 中的 `python`。

如果服务器中有多个 Python，建议显式设置：

```bash
export LINKMESH_PYTHON="/absolute/path/to/python"
```

例如：

```bash
export LINKMESH_PYTHON="/home/user/miniconda3/envs/linkmesh/bin/python"
```

`LINKMESH_PYTHON` 必须指向 Python 可执行文件，而不是环境目录。

确认选择结果：

```bash
"$LINKMESH_PYTHON" --version
```

## 4. 启动 LinkMesh

推荐使用 Release 自带的启动器：

```bash
"$RELEASE/bin/linkmesh" -h
```

启动器会优先使用当前 Release 中的：

- LinkMesh；
- OpenFUSIONToolkit 26.6；
- SCOREC helper。

因此，即使当前 Python 环境中存在其他 LinkMesh 或 OFT 安装，也可以明确使用当前 Release 的版本。

用户也可以自行设置 `PYTHONPATH` 或使用：

```bash
python -m linkmesh
```

这种运行方式由当前 Python 环境和模块搜索路径决定。需要确认实际加载的是预期的 LinkMesh 和 OpenFUSIONToolkit：

```bash
python -c \
    "import linkmesh; print(linkmesh.__file__)"

python -c \
    "import OpenFUSIONToolkit; print(OpenFUSIONToolkit.__file__)"
```

如果希望直接使用当前 Release，最简单的方式仍是：

```bash
"$RELEASE/bin/linkmesh"
```

## 5. 环境检查

运行基础检查：

```bash
"$RELEASE/bin/linkmesh-check" core
```

查看 CLI：

```bash
"$RELEASE/bin/linkmesh" -h
"$RELEASE/bin/linkmesh" regions -h
"$RELEASE/bin/linkmesh" regions inspect -h
"$RELEASE/bin/linkmesh" regions generate -h
```

根据任务运行检查：

```bash
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" m3dc1
```

也可以执行全部检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

各模式检查的内容：

- `core`：Python、Release 中的 LinkMesh、OFT 26.6 和 NumPy；
- `plot`：core 加 Matplotlib；
- `trimeg`：core 加 h5py；
- `m3dc1`：core 加 SCOREC helper、动态库和 MPI；
- `all`：依次执行全部检查。

可能出现的状态：

- `OK`：该检查项满足当前运行条件；
- `MISSING`：缺少该任务需要的条件；
- `WARNING`：存在需要注意的兼容性信息；
- `NOT CHECKED`：该检查没有执行真实文件生成或下游加载。

环境检查不会生成网格，也不会调用外部求解器。

## 6. 配置文件规则

LinkMesh 配置文件使用 TOML 语法。

所有正式配置必须在文件顶层包含：

```toml
schema_version = 1
```

`schema_version` 必须是整数，不能写成：

```toml
schema_version = "1"
```

也不能放入 `[task]`、`[input]`、`[regions]` 等 section。

配置优先级：

```text
内建默认值 < TOML配置 < 显式CLI参数
```

路径解析规则：

- 配置文件中的相对路径相对于配置文件所在目录；
- CLI 中显式提供的相对路径相对于当前工作目录；
- 绝对路径保持不变；
- boundary-list 中的相对路径相对于 boundary-list 文件所在目录。

建议每个 Case 使用独立目录：

```text
case_directory/
├── configuration files
├── boundary files
└── output files
```

配置文件名不是固定的。例如下面这些名称都可以：

```text
linkmesh.toml
generate.toml
case.toml
linkmesh.in
```

文件扩展名可以由用户选择，但文件内容必须符合 LinkMesh 的 TOML schema。

## 7. Counted R-Z 边界文件

Counted R-Z 文件用于保存一条有序闭合边界。

格式为：

```text
N
R1 Z1
R2 Z2
...
RN ZN
```

例如：

```text
5
1.000000 0.000000
1.200000 0.000000
1.250000 0.200000
1.100000 0.300000
0.950000 0.150000
```

要求：

- 第一项是边界点数量 `N`；
- 后续恰好包含 `N` 个坐标点；
- 每个坐标点包含 `R Z` 两个数值；
- `R` 在前，`Z` 在后；
- 坐标单位为米；
- 点按边界曲线上的顺序排列；
- 边界必须满足 LinkMesh 的闭合几何要求。

LinkMesh 不要求边界文件使用特定扩展名。

下面这些文件名都可以：

```text
boundary.txt
boundary.pts
wall.dat
plasma.boundary
first_wall
```

`.pts` 只表示“point coordinates”的常见命名习惯，不是 LinkMesh 的强制文件格式。

程序判断的是文件内容，而不是扩展名。

## 8. 单区域工作流

单区域命令为：

```bash
"$RELEASE/bin/linkmesh" [options]
```

支持的边界来源：

- `lcfs`
- `first_wall`
- `array_file`
- `flux_surface`

查看全部参数：

```bash
"$RELEASE/bin/linkmesh" -h
```

### 8.1 单区域 counted R-Z 示例

目录示例：

```text
single_region_case/
├── generate.toml
└── boundary.txt
```

这里的文件名只是示例，也可以使用：

```text
case_config.toml
plasma.pts
```

`generate.toml`：

```toml
schema_version = 1

[task]
target = "mesh_only"

[input]
array_file = "boundary.txt"

[domain]
boundary_source = "array_file"

[mesh]
mesh_dx = 0.04

[output]
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[runtime]
verbose = true
```

运行：

```bash
cd /absolute/path/to/single_region_case

"$RELEASE/bin/linkmesh-check" plot

"$RELEASE/bin/linkmesh" \
    --config "$PWD/generate.toml"
```

预期生成：

```text
mesh.png
mesh_quality.png
```

### 8.2 单区域局部加密

可以在配置中提供一个或多个 R-Z point local refinement：

```toml
[[mesh.local_refinement]]
r = 1.10
z = 0.00
dx = 0.010
width = 0.10

[[mesh.local_refinement]]
r = 1.50
z = 1.00
dx = 0.015
width = 0.30
```

字段含义：

- `r`：加密点的 R 坐标，单位为米；
- `z`：加密点的 Z 坐标，单位为米；
- `dx`：加密区域的目标尺度，单位为米；
- `width`：影响宽度，单位为米。

`dx` 必须小于该点所在 Region 的基准 `mesh_dx`。

## 9. 多区域工作流

多区域网格使用两个阶段：

```text
regions inspect
→ 检查边界和包含关系
→ 生成regions map与inspection PNG

regions generate
→ 读取原始边界和regions map
→ 设置各Region网格尺度
→ 生成最终网格
```

命令：

```bash
"$RELEASE/bin/linkmesh" regions inspect ...
"$RELEASE/bin/linkmesh" regions generate ...
```

支持两种多区域输入方式：

1. `multi_array_file`
2. `boundary_list`

两种方式不能在同一次运行中混用。

`regions map` 保存 Region 关系，但不保存完整边界坐标。因此，generate 仍然需要读取原始边界输入。

## 10. Multi-array 输入

Multi-array 文件在一个文本文件中连续保存多个 counted R-Z blocks：

```text
N1
R1 Z1
...
RN1 ZN1

N2
R1 Z1
...
RN2 ZN2
```

至少需要两个 boundary blocks。

文件扩展名不固定，例如可以使用：

```text
boundaries.txt
regions.dat
multi_boundary
```

### 10.1 Inspect 配置

`inspect.toml`：

```toml
schema_version = 1

[regions]
mode = "inspect"
multi_array_file = "boundaries.txt"
regions_map = "regions.toml"
plot = "inspect.png"

[runtime]
verbose = true
```

运行：

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect.toml"
```

预期生成：

```text
regions.toml
inspect.png
```

查看 map：

```bash
sed -n '1,240p' regions.toml
```

用户应检查：

- 曲线编号；
- Region 包含关系；
- `inspect.png` 中的边界位置；
- Region ID 是否与预期一致。

## 11. Boundary-list 输入

Boundary-list 用一个 TOML 清单分别引用多条独立边界坐标文件。

这里有两类文件：

1. Boundary-list 清单，内容使用 TOML 语法；
2. 边界坐标文件，内容使用 counted R-Z 文本格式。

目录示例：

```text
boundary_list_case/
├── boundary_list.toml
├── inner_boundary.txt
├── outer_boundary.txt
├── inspect_config.toml
└── generate_config.toml
```

这些文件名不是固定要求。

例如：

- `boundary_list.toml` 可以改名为 `boundaries.toml`；
- `inner_boundary.txt` 可以改名为 `inner.pts`；
- `outer_boundary.txt` 可以改名为 `wall.dat`；
- `inspect_config.toml` 可以改名为 `inspect.in`。

清单和配置文件的内容必须符合 TOML 语法。

坐标文件的内容必须符合 counted R-Z 格式。

### 11.1 Boundary-list 清单

`boundary_list.toml`：

```toml
schema_version = 1

[[boundaries]]
file = "inner_boundary.txt"
curve_id = 1

[[boundaries]]
file = "outer_boundary.txt"
```

每个 `[[boundaries]]` 记录表示一条边界。

字段：

- `file`：边界坐标文件路径；
- `curve_id`：可选的正整数曲线编号。

`file` 不要求使用特定扩展名。

下面的引用都是合法的命名形式：

```toml
[[boundaries]]
file = "inner.pts"

[[boundaries]]
file = "wall.dat"

[[boundaries]]
file = "plasma_boundary"
```

清单中的相对路径相对于 boundary-list 文件所在目录解析。

### 11.2 Curve ID

`curve_id` 可以显式填写：

```toml
[[boundaries]]
file = "inner_boundary.txt"
curve_id = 10
```

也可以省略：

```toml
[[boundaries]]
file = "outer_boundary.txt"
```

省略时，LinkMesh 按清单声明顺序分配尚未被显式 ID 占用的最小正整数。

例如：

```toml
schema_version = 1

[[boundaries]]
file = "inner_boundary.txt"
curve_id = 10

[[boundaries]]
file = "outer_boundary.txt"
```

第二条边界会自动获得：

```text
curve_id = 1
```

显式 `curve_id` 必须：

- 是正整数；
- 在同一清单中唯一。

修改清单顺序或 `curve_id` 后，应重新执行 inspect。

### 11.3 独立坐标文件

Boundary-list 引用的每个坐标文件保存一条 counted R-Z 边界：

```text
# Inner boundary
5

1.000000 0.000000
1.200000 0.000000
1.250000 0.200000  # upper point
1.100000 0.300000
0.950000 0.150000
```

Boundary-list 引用的坐标文件允许：

- 空行；
- 以 `#` 开始的整行注释；
- 数据后的行尾 `#` 注释。

注释和空行不计入点数 `N`。

一个被引用的坐标文件只保存一条边界。

同一个实际文件不能在清单中重复引用。

### 11.4 Boundary-list inspect

`inspect_config.toml`：

```toml
schema_version = 1

[regions]
mode = "inspect"
boundary_list = "boundary_list.toml"
regions_map = "regions.toml"
plot = "inspect.png"

[runtime]
verbose = true
```

运行：

```bash
cd /absolute/path/to/boundary_list_case

"$RELEASE/bin/linkmesh-check" plot

"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect_config.toml"
```

预期生成：

```text
regions.toml
inspect.png
```

查看：

```bash
sed -n '1,240p' regions.toml
ls -lh inspect.png
```

## 12. Regions map

Inspect 生成的 `regions.toml` 类似：

```toml
schema_version = 1

[[regions]]
region_id = 1
curve_id = 1
parent_region_id = 2
child_region_ids = []
color = "#0072B2"
physical_label = ""

[[regions]]
region_id = 2
curve_id = 10
parent_region_id = 0
child_region_ids = [1]
color = "#D55E00"
physical_label = ""
```

字段含义：

- `region_id`：最终 Region ID；
- `curve_id`：对应输入曲线编号；
- `parent_region_id`：包含该 Region 的父 Region；
- `child_region_ids`：该 Region 直接包含的子 Region；
- `color`：检查图中的显示颜色；
- `physical_label`：可选的用户物理语义。

用户可以填写：

```toml
physical_label = "plasma"
```

也可以保持为空：

```toml
physical_label = ""
```

`physical_label` 允许为空，不参与网格编号和建网过程。

通常不应手工修改：

- `region_id`
- `curve_id`
- `parent_region_id`
- `child_region_ids`

如果修改了以下内容，应重新执行 inspect：

- 原始边界坐标；
- 曲线数量；
- boundary-list 顺序；
- 显式 `curve_id`；
- multi-array block 顺序；
- 曲线包含关系。

## 13. 多区域 Generate

Boundary-list 的 generate 配置示例：

```toml
schema_version = 1

[regions]
mode = "generate"
target = "mesh_only"
boundary_list = "boundary_list.toml"
regions_map = "regions.toml"
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[regions.mesh]
mesh_dx = 0.08

[runtime]
verbose = true
```

运行：

```bash
"$RELEASE/bin/linkmesh" regions generate \
    --config "$PWD/generate_config.toml"
```

预期生成：

```text
mesh.png
mesh_quality.png
```

使用 multi-array 输入时，将来源写为：

```toml
[regions]
multi_array_file = "boundaries.txt"
```

不能同时设置：

```toml
multi_array_file = "boundaries.txt"
boundary_list = "boundary_list.toml"
```

Inspect 和 generate 应使用同一组原始边界。

## 14. 分 Region 网格尺度

为全部 Region 设置默认尺度：

```toml
[regions.mesh]
mesh_dx = 0.08
```

按最终 Region ID 覆盖尺度：

```toml
[regions.mesh]
mesh_dx = 0.08

[regions.mesh.region_dx]
"1" = 0.030
"2" = 0.150
"3" = 0.070
```

`region_dx` 中的键是 inspect 生成的最终 Region ID。

如果不提供全局 `mesh_dx`，则 `region_dx` 必须覆盖所有最终 Region：

```toml
[regions.mesh.region_dx]
"1" = 0.030
"2" = 0.150
"3" = 0.070
```

所有尺度单位均为米。

## 15. Interface Transition

当相邻 Region 使用不同目标尺度时，可以设置 interface transition。

两种 transition 模式互斥。

### 15.1 固定变化层宽度

```toml
[regions.mesh]
transition_width = 0.30
```

单位为米。

`0` 表示关闭。

### 15.2 对数尺度梯度

```toml
[regions.mesh]
transition_gradient = 5.0
```

单位为 `1/m`。

LinkMesh 根据相邻 Region 的目标尺度，为每条不同尺度 interface 计算对应的变化层宽度。

不能同时设置：

```toml
transition_width = 0.30
transition_gradient = 5.0
```

## 16. 多区域局部加密

可以重复配置 R-Z point local refinement：

```toml
[[regions.mesh.local_refinement]]
r = 1.10
z = 0.00
dx = 0.010
width = 0.10

[[regions.mesh.local_refinement]]
r = 1.50
z = 1.00
dx = 0.015
width = 0.30
```

字段含义：

- `r`：加密点的 R 坐标，单位为米；
- `z`：加密点的 Z 坐标，单位为米；
- `dx`：目标尺度，单位为米；
- `width`：影响宽度，单位为米。

LinkMesh 自动判断加密点所属的 Region。

点源不要求成为最终 mesh node，也不会改变 Region 拓扑。

## 17. PNG 输出

### 17.1 网格几何图

单区域配置：

```toml
[output]
plot = "mesh.png"
```

多区域配置：

```toml
[regions]
plot = "mesh.png"
```

### 17.2 Shape quality Q 图

单区域配置：

```toml
[output]
quality_plot = "mesh_quality.png"
```

多区域配置：

```toml
[regions]
quality_plot = "mesh_quality.png"
```

颜色含义：

- `Q = 0`：红色；
- `Q = 0.5`：蓝色；
- `Q = 1`：绿色。

颜色范围固定为 `[0,1]`，便于比较不同 Case。

建议在 generate 后检查：

- 边界形状；
- Region 关系；
- 局部加密位置；
- interface 过渡；
- 是否存在明显异常三角形。

## 18. TRIMEG HDF5 输出

### 18.1 单区域示例

```toml
schema_version = 1

[task]
target = "trimeg"

[input]
array_file = "boundary.txt"

[domain]
boundary_source = "array_file"

[mesh]
mesh_dx = 0.04

[output]
hdf5 = "mesh.h5"
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[runtime]
verbose = true
```

运行检查：

```bash
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
```

生成：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/generate.toml"
```

预期输出：

```text
mesh.h5
mesh.png
mesh_quality.png
```

### 18.2 多区域示例

```toml
schema_version = 1

[regions]
mode = "generate"
target = "trimeg"
boundary_list = "boundary_list.toml"
regions_map = "regions.toml"
hdf5 = "mesh.h5"
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[regions.mesh]
mesh_dx = 0.08

[runtime]
verbose = true
```

运行：

```bash
"$RELEASE/bin/linkmesh" regions generate \
    --config "$PWD/generate_config.toml"
```

## 19. M3D-C1 输出

### 19.1 单区域示例

```toml
schema_version = 1

[task]
target = "m3dc1"

[input]
array_file = "boundary.txt"

[domain]
boundary_source = "array_file"

[mesh]
mesh_dx = 0.08

[output]
model = "mesh.txt"
smb = "mesh.smb"
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[runtime]
verbose = true
```

运行环境检查：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
"$RELEASE/bin/linkmesh-check" plot
```

生成：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/generate.toml"
```

### 19.2 多区域示例

```toml
schema_version = 1

[regions]
mode = "generate"
target = "m3dc1"
boundary_list = "boundary_list.toml"
regions_map = "regions.toml"
model = "mesh.txt"
smb = "mesh.smb"
plot = "mesh.png"
quality_plot = "mesh_quality.png"

[regions.mesh]
mesh_dx = 0.08

[runtime]
verbose = true
```

运行：

```bash
"$RELEASE/bin/linkmesh" regions generate \
    --config "$PWD/generate_config.toml"
```

SCOREC helper 管理 rank-0 SMB 文件名。

如果配置中指定：

```text
mesh.smb
```

实际输出通常为：

```text
mesh0.smb
```

M3D-C1 SMB 输出要求：

- Linux x86-64；
- 与当前 `linkmesh-scorec-helper` 兼容的 MPI runtime；
- 兼容的 glibc；
- 兼容的 libstdc++。

首次在一台服务器上使用 M3D-C1 输出前，应运行：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
```

当前 Release 中 helper 的具体动态库信息记录在：

```text
manifest/build-info.txt
manifest/native-requirements.txt
```

### 19.3 在新服务器上重新编译 helper（仅维护者）

Release 已包含编译好的 `linkmesh-scorec-helper`，普通使用者不需要编译。仅当目标
服务器缺少兼容 MPI，或需要更换 SCOREC/PUMI、MPI 或编译器时，维护者才在源代码
仓库根目录按以下步骤重新编译：

```bash
# 前提：Linux x86-64、CMake ≥ 3.20、可用的 mpicxx、SCOREC/PUMI 2.2.9
PUMI_PREFIX=/path/to/pumi-2.2.9        # 该前缀中应包含 SCORECConfig.cmake
cmake -S native/linkmesh_scorec_helper -B "$HOME/LinkMesh_build/helper" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$PUMI_PREFIX" \
    -DMPI_CXX_COMPILER="$(command -v mpicxx)"
cmake --build "$HOME/LinkMesh_build/helper" -j "$(nproc)"
ldd "$HOME/LinkMesh_build/helper/linkmesh-scorec-helper"   # 不应出现 not found
```

产物为 `$HOME/LinkMesh_build/helper/linkmesh-scorec-helper`。重新打包时把
`build_release.sh` 的 `--helper` 参数指向该产物即可（完整参数见
`build_release.sh -h`）；脚本会校验 ELF 格式与动态库解析，并把 helper 的
SHA-256 和 `file`/`ldd`/`readelf` 信息写入 `manifest/build-info.txt`。

更换 SCOREC/PUMI、MPI 或编译器后，必须从空构建目录重新配置，不得复用旧
`CMakeCache.txt`，也不得把既有二进制视为跨 ABI 可移植。编译与重新打包都需要
源代码仓库，而不只是 Release 包。

## 20. 使用 CLI 参数

### 20.1 单区域

不使用配置文件时，可以通过 CLI 显式提供参数：

```bash
"$RELEASE/bin/linkmesh" \
    --no-config \
    --target mesh_only \
    --boundary-source array_file \
    --array-file "$PWD/boundary.txt" \
    --mesh-dx 0.04 \
    --plot "$PWD/mesh.png" \
    --quality-plot "$PWD/mesh_quality.png" \
    --verbose
```

### 20.2 Boundary-list inspect

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --boundary-list "$PWD/boundary_list.toml" \
    --regions-map "$PWD/regions.toml" \
    --plot "$PWD/inspect.png" \
    --verbose
```

### 20.3 Boundary-list generate

```bash
"$RELEASE/bin/linkmesh" regions generate \
    --boundary-list "$PWD/boundary_list.toml" \
    --regions-map "$PWD/regions.toml" \
    --target mesh_only \
    --mesh-dx 0.08 \
    --plot "$PWD/mesh.png" \
    --quality-plot "$PWD/mesh_quality.png" \
    --verbose
```

CLI 参数和 TOML 字段的完整映射以帮助信息为准：

```bash
"$RELEASE/bin/linkmesh" -h
"$RELEASE/bin/linkmesh" regions inspect -h
"$RELEASE/bin/linkmesh" regions generate -h
```

## 21. 网格质量报告

启用：

```toml
[runtime]
verbose = true
```

或使用：

```bash
--verbose
```

LinkMesh 会报告最终网格的数值质量。

主要指标：

- `angle min/P01/P05/max`：三角形角度分布；
- `shape Q min/P01/P05/median`：三角形形状质量；
- `equivalent size`：三角形等效尺寸；
- `adjacent size ratio`：相邻三角形尺寸比；
- `degenerate`：退化三角形数量；
- `duplicate`：重复三角形数量；
- `non-manifold`：非流形结构数量。

`P01` 表示第 1 百分位数。

`P05` 表示第 5 百分位数。

例如：

```text
shape Q [-]: min=0.62, P01=0.74, P05=0.78, median=0.94
```

表示：

- 最差三角形的 Q 约为 `0.62`；
- 约 1% 的三角形 Q 不高于 `0.74`；
- 约 5% 的三角形 Q 不高于 `0.78`；
- 一半三角形的 Q 不低于约 `0.94`。

建议同时检查 PNG、结构计数和目标求解器的实际加载结果。

## 22. 常见问题

### 22.1 找不到 NumPy、h5py 或 Matplotlib

运行：

```bash
"$RELEASE/bin/linkmesh-check" all
```

确认 LinkMesh 使用的 Python：

```bash
printf '%s\n' "${LINKMESH_PYTHON:-not explicitly set}"
```

如果没有显式设置，可查看：

```bash
command -v python3 || command -v python
```

在所选 Python 环境中安装缺失依赖。

### 22.2 Boundary-list 引用的文件不存在

Boundary-list 中的相对路径相对于清单文件所在目录。

例如：

```text
case/
├── lists/
│   └── boundary_list.toml
└── coordinates/
    ├── inner.txt
    └── outer.txt
```

清单中可以写：

```toml
schema_version = 1

[[boundaries]]
file = "../coordinates/inner.txt"

[[boundaries]]
file = "../coordinates/outer.txt"
```

检查文件：

```bash
find . -maxdepth 3 -type f -print
```

### 22.3 Multi-array 与 boundary-list 冲突

同一个多区域配置只能选择一种来源。

使用 multi-array：

```toml
multi_array_file = "boundaries.txt"
```

或者使用 boundary-list：

```toml
boundary_list = "boundary_list.toml"
```

不能同时设置。

### 22.4 Regions map 与边界不匹配

修改以下内容后，应重新执行 inspect：

- 边界坐标；
- 边界数量；
- boundary-list 顺序；
- 显式 `curve_id`；
- multi-array block 顺序；
- 曲线包含关系。

重新执行：

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect_config.toml"
```

检查新的 `inspect.png` 和 `regions.toml` 后，再执行 generate。

### 22.5 Helper 或 MPI 检查失败

运行：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
```

该命令会检查：

- helper 是否存在并可执行；
- helper 是否为 Linux x86-64 ELF；
- helper 所需动态库是否可以解析；
- MPI runtime 是否可以解析。

具体依赖名称以以下文件为准：

```text
manifest/build-info.txt
manifest/native-requirements.txt
```

如果目标服务器缺少兼容的 MPI runtime，由维护者在源代码仓库中按 §19.3 重新
编译 helper。

TRIMEG HDF5 和普通 PNG 输出不调用 SCOREC helper，因此不要求 M3D-C1 helper 和 MPI 检查成功。

### 22.6 输出的 SMB 文件名多了一个 `0`

这是 rank-0 native SMB 的正常命名方式。

例如配置：

```text
mesh.smb
```

实际输出通常为：

```text
mesh0.smb
```

### 22.7 如何确认使用的是当前 Release

运行：

```bash
"$RELEASE/bin/linkmesh-check" core
```

输出中的 LinkMesh 和 OpenFUSIONToolkit 路径应位于：

```text
$RELEASE/python/site-packages/
```

## 23. 建议的使用流程

### 单区域

```text
准备GFile或单条边界
→ 编写配置
→ 运行环境检查
→ 生成网格
→ 检查PNG和质量报告
→ 使用目标输出文件
```

### 多区域

```text
准备multi-array或boundary-list输入
→ regions inspect
→ 检查inspect.png
→ 检查regions.toml
→ 按需要填写physical_label
→ regions generate
→ 检查mesh PNG和质量报告
→ 使用目标输出文件
```

## 24. 反馈运行问题

反馈问题时，建议提供：

系统信息：

```bash
uname -a
```

Python 信息：

```bash
if [[ -n "${LINKMESH_PYTHON:-}" ]]; then
    "$LINKMESH_PYTHON" --version
else
    command -v python3 || command -v python
    python3 --version 2>/dev/null || python --version
fi
```

环境检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

输出文件：

```bash
find . \
    -maxdepth 2 \
    -type f \
    -printf '%s %p\n' 2>&1 |
    sort
```

同时提供：

- 实际执行的 LinkMesh 命令；
- 使用的配置文件；
- boundary-list 和 regions map；
- 完整标准输出；
- 完整错误输出；
- Python 路径和版本；
- 输出文件名称和大小；
- TRIMEG 或 M3D-C1 的实际加载结果。

## 25. 结果状态说明

建议分别描述以下状态：

- `GENERATED`：目标文件已经生成；
- `STRUCTURALLY CHECKED`：文件结构或网格结构已经检查；
- `DELIVERED`：文件已经交付给下游测试者；
- `LOADED`：外部程序已经成功读取；
- `INITIALIZED`：外部程序已经完成初始化；
- `TIME-STEPPED`：外部程序已经完成明确的时间推进；
- `STABILITY-VALIDATED`：已经完成规定工况的稳定性检查；
- `PHYSICALLY VALIDATED`：物理结果已经得到确认。

文件生成成功表示已经达到：

```text
GENERATED
```

它不自动表示外部程序已经完成加载、初始化、时间推进或物理验证。
