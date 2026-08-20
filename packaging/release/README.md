# LinkMesh Linux x86-64 Release

LinkMesh 是用于生成二维 R-Z 非结构三角网格的命令行工具。

主要工作流：

- 从 GFile/EQDSK 或单条 counted R-Z 边界生成单区域网格；
- 从 multi-array 文件生成多区域网格；
- 从 boundary-list 清单及多个独立坐标文件生成多区域网格；
- 按 Region 设置不同目标尺度；
- 设置 interface transition refinement；
- 设置 R-Z point local refinement；
- 输出 TRIMEG HDF5；
- 输出 M3D-C1 model TXT 和 native SMB；
- 生成网格几何 PNG 和三角形 Shape quality Q PNG。

## 1. 交付内容

交付目录包含三个文件：

```text
README.md
linkmesh-release-<VERSION>-linux-x86_64.tar.gz
linkmesh-release-<VERSION>-linux-x86_64.tar.gz.sha256
```

其中：

- `README.md`：安装、环境检查和运行指南；
- `.tar.gz`：LinkMesh Linux x86-64 Release；
- `.sha256`：Release 压缩包的 SHA-256 校验文件。

Release 压缩包内部包含：

```text
linkmesh-release-<VERSION>-linux-x86_64/
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
        └── OpenFUSIONToolkit-*.dist-info/
```

Release 已携带：

- LinkMesh Python 包；
- OpenFUSIONToolkit 26.6；
- OpenFUSIONToolkit 配套原生库；
- `linkmesh-scorec-helper`；
- 静态链接进 helper 的 SCOREC/PUMI 组件；
- LinkMesh 启动器；
- LinkMesh 分层环境检查器；
- 构建信息、依赖信息和内部 SHA-256 manifest。

Release 不携带：

- Python 解释器；
- NumPy；
- h5py；
- Matplotlib；
- MPI runtime；
- glibc；
- libstdc++。

目标系统必须是 Linux x86-64，并提供兼容的 Python 3 环境。

其他 Python 3 版本是否可用，应以目标服务器上的 `linkmesh-check` 和真实运行结果为准。

## 2. 校验与解压

进入三个交付文件所在目录。

先设置实际压缩包名称：

```bash
ARCHIVE="linkmesh-release-<VERSION>-linux-x86_64.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"
```

将 `<VERSION>` 替换为收到的实际版本，例如：

```bash
ARCHIVE="linkmesh-release-0.2.0-linux-x86_64.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"
```

检查文件：

```bash
ls -lh README.md "$ARCHIVE" "$CHECKSUM"
```

校验压缩包：

```bash
sha256sum -c "$CHECKSUM"
```

成功时应显示：

```text
linkmesh-release-<VERSION>-linux-x86_64.tar.gz: OK
```

解压：

```bash
tar -xzf "$ARCHIVE"
```

记录解压目录的绝对路径：

```bash
RELEASE="$PWD/linkmesh-release-<VERSION>-linux-x86_64"
```

确认入口：

```bash
test -x "$RELEASE/bin/linkmesh"
test -x "$RELEASE/bin/linkmesh-check"
test -x "$RELEASE/bin/linkmesh-scorec-helper"

ls -lh \
    "$RELEASE/bin/linkmesh" \
    "$RELEASE/bin/linkmesh-check" \
    "$RELEASE/bin/linkmesh-scorec-helper"
```

检查 Release 内部文件：

```bash
cd "$RELEASE"

sha256sum -c manifest/SHA256SUMS
```

完成后可以返回工作目录：

```bash
cd -
```

Release 可以整体移动。移动后重新设置 `RELEASE` 即可。

## 3. Python 环境

Release 不包含 Python 解释器。

启动器按以下优先级选择 Python：

1. `LINKMESH_PYTHON` 指定的解释器；
2. 当前 `PATH` 中的 `python3`；
3. 当前 `PATH` 中的 `python`。

查看可用解释器：

```bash
command -v python3 || command -v python
type -a python3 python 2>/dev/null
```

如果当前环境已经满足要求，可以直接运行：

```bash
"$RELEASE/bin/linkmesh-check" core
"$RELEASE/bin/linkmesh" -h
```

如果服务器存在多个 Python，建议显式指定：

```bash
export LINKMESH_PYTHON="/absolute/path/to/python"
```

例如：

```bash
export LINKMESH_PYTHON="/home/user/miniconda3/envs/linkmesh/bin/python"
```

`LINKMESH_PYTHON` 必须指向 Python 可执行文件，不能只指向环境目录。

确认选择结果：

```bash
"$LINKMESH_PYTHON" --version
```

使用 Release 不需要设置：

```text
PYTHONPATH
LINKMESH_SCOREC_HELPER
```

启动器会优先加载 Release 自带的 LinkMesh 和 OpenFUSIONToolkit，并自动选择 Release 内的 SCOREC helper。

不要使用下面的源码运行方式启动 Release：

```bash
python -m linkmesh
```

推荐始终使用：

```bash
"$RELEASE/bin/linkmesh"
```

### 3.1 Conda

激活已有环境：

```bash
conda activate linkmesh
export LINKMESH_PYTHON="$(command -v python)"
```

检查依赖：

```bash
"$LINKMESH_PYTHON" -c "import numpy; print('NumPy:', numpy.__version__)"
"$LINKMESH_PYTHON" -c "import h5py; print('h5py:', h5py.__version__)"
"$LINKMESH_PYTHON" -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)"
```

如需安装缺失依赖：

```bash
conda install numpy h5py matplotlib
```

该命令会修改当前 Conda 环境。共享环境中安装软件前应确认权限和使用约定。

### 3.2 Python venv

创建独立环境：

```bash
python3 -m venv "$HOME/venvs/linkmesh-release"
source "$HOME/venvs/linkmesh-release/bin/activate"
```

安装 Python 依赖：

```bash
python -m pip install --upgrade pip
python -m pip install numpy h5py matplotlib
```

选择该环境：

```bash
export LINKMESH_PYTHON="$(command -v python)"
```

确认：

```bash
"$LINKMESH_PYTHON" --version
"$LINKMESH_PYTHON" -c "import numpy, h5py, matplotlib; print('Python dependencies: OK')"
```

## 4. 环境检查

核心检查：

```bash
"$RELEASE/bin/linkmesh-check" core
```

查看命令：

```bash
"$RELEASE/bin/linkmesh" -h
"$RELEASE/bin/linkmesh" regions -h
"$RELEASE/bin/linkmesh" regions inspect -h
"$RELEASE/bin/linkmesh" regions generate -h
```

按任务检查：

```bash
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
"$RELEASE/bin/linkmesh-check" m3dc1
```

全部检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

检查模式：

- `core`：Python、Release 内 LinkMesh、OFT 26.6 和 NumPy；
- `trimeg`：core 加 h5py；
- `plot`：core 加 Matplotlib；
- `m3dc1`：helper、ELF、动态库和 MPI；
- `all`：执行全部检查。

状态含义：

- `OK`：当前检查项满足诊断条件；
- `MISSING`：缺少该任务需要的条件；
- `WARNING`：存在潜在兼容性问题；
- `NOT CHECKED`：该项没有执行真实验证。

环境检查成功不等于求解器已经加载输出文件。

## 5. 配置规则

LinkMesh 配置使用严格 TOML schema。

所有正式配置必须在顶层包含：

```toml
schema_version = 1
```

不能写成：

```toml
schema_version = "1"
```

也不能把它放入任何 section。

配置优先级：

```text
内建默认值 < TOML配置 < 显式CLI参数
```

配置文件中的相对路径相对于配置文件所在目录解析。

CLI 中显式路径相对于执行命令时的当前目录解析。

建议每个 Case 使用独立目录：

```text
case_directory/
├── generate.toml
├── input files
└── output files
```

## 6. 单区域输入

单区域命令为：

```bash
"$RELEASE/bin/linkmesh" [options]
```

支持的边界来源包括：

- `lcfs`
- `first_wall`
- `array_file`
- `flux_surface`

### 6.1 Counted R-Z 文件

单轮廓 counted R-Z 文件格式：

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

- 第一行是点数 `N`；
- 后续恰好有 `N` 个坐标点；
- 每行是 `R Z`；
- 坐标单位为米；
- 点按边界曲线顺序排列；
- 边界必须满足 LinkMesh 的闭合几何要求。

### 6.2 单区域配置示例

目录：

```text
single_region_case/
├── generate.toml
└── boundary.pts
```

`generate.toml`：

```toml
schema_version = 1

[task]
target = "mesh_only"

[input]
array_file = "boundary.pts"

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

### 6.3 单区域局部加密

可在 `[mesh]` 后增加一个或多个 point local refinement：

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

字段单位均为米：

- `r`：点源 R 坐标；
- `z`：点源 Z 坐标；
- `dx`：点源目标尺度；
- `width`：影响宽度。

`dx` 必须严格小于点所属 Region 的 baseline `mesh_dx`。

## 7. 多区域工作流

多区域使用两个阶段：

```text
regions inspect
→ 生成并检查regions map

regions generate
→ 读取原始边界和经用户确认的regions map
→ 生成最终网格
```

命令：

```bash
"$RELEASE/bin/linkmesh" regions inspect ...
"$RELEASE/bin/linkmesh" regions generate ...
```

支持两种互斥输入来源：

1. `multi_array_file`
2. `boundary_list`

两种来源不能同时使用。

`regions map` 不保存完整坐标，因此 generate 仍必须读取原始边界输入。

## 8. Multi-array 输入

Multi-array 文件在一个文件中连续保存多个 counted R-Z blocks：

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

至少需要两条边界。

### 8.1 Inspect 配置

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

检查：

```bash
ls -lh regions.toml inspect.png
```

人工检查 `inspect.png` 和 `regions.toml` 后，可按需要填写 `physical_label`。

`physical_label` 允许为空，不参与网格技术编号和建网过程。

## 9. Boundary-list 输入

Boundary-list 使用一个 TOML 清单引用多个独立坐标文件。

目录示例：

```text
boundary_list_case/
├── boundaries.toml
├── inner.pts
├── outer.pts
├── inspect.toml
└── generate.toml
```

### 9.1 清单格式

`boundaries.toml`：

```toml
schema_version = 1

[[boundaries]]
file = "inner.pts"
curve_id = 1

[[boundaries]]
file = "outer.pts"
```

`curve_id` 可以省略。

省略后，LinkMesh 按清单顺序分配尚未被显式 ID 占用的最小正整数。

例如：

```toml
[[boundaries]]
file = "inner.pts"
curve_id = 10

[[boundaries]]
file = "outer.pts"
```

第二条边界自动获得 `curve_id = 1`。

清单中的相对路径相对于 `boundaries.toml` 所在目录解析。

同一个实际文件不能重复引用。重复文件路径、路径别名或符号链接指向同一文件时会失败。

### 9.2 独立坐标文件

Boundary-list 引用的每个坐标文件保存一条 counted R-Z 曲线：

```text
# Inner boundary
5

1.000000 0.000000
1.200000 0.000000
1.250000 0.200000  # upper point
1.100000 0.300000
0.950000 0.150000
```

该输入方式允许：

- 空行；
- 以 `#` 开始的整行注释；
- 数据后的行尾 `#` 注释。

注释和空行不计入点数 `N`。

### 9.3 Boundary-list inspect

`inspect.toml`：

```toml
schema_version = 1

[regions]
mode = "inspect"
boundary_list = "boundaries.toml"
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
    --config "$PWD/inspect.toml"
```

预期生成：

```text
regions.toml
inspect.png
```

检查：

```bash
sed -n '1,240p' regions.toml
ls -lh inspect.png
```

### 9.4 Regions map

生成的 map 类似：

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

允许用户填写：

```toml
physical_label = "plasma"
```

也可以保持：

```toml
physical_label = ""
```

不要手工修改：

- `region_id`
- `curve_id`
- `parent_region_id`
- `child_region_ids`

如果原始边界、清单顺序或 `curve_id` 发生变化，应重新执行 inspect。

## 10. 多区域 Generate

Boundary-list 的 `generate.toml` 示例：

```toml
schema_version = 1

[regions]
mode = "generate"
target = "mesh_only"
boundary_list = "boundaries.toml"
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
    --config "$PWD/generate.toml"
```

预期生成：

```text
mesh.png
mesh_quality.png
```

使用 multi-array 时，只需把输入来源改为：

```toml
[regions]
multi_array_file = "boundaries.txt"
```

不能同时写：

```toml
multi_array_file = "boundaries.txt"
boundary_list = "boundaries.toml"
```

## 11. 分 Region 尺度

可以为全部 Region 提供默认尺度：

```toml
[regions.mesh]
mesh_dx = 0.08
```

也可以按最终 Region ID 覆盖：

```toml
[regions.mesh]
mesh_dx = 0.08

[regions.mesh.region_dx]
"1" = 0.030
"2" = 0.150
"3" = 0.070
```

如果不提供全局 `mesh_dx`，则 `region_dx` 必须覆盖全部最终 Region：

```toml
[regions.mesh.region_dx]
"1" = 0.030
"2" = 0.150
"3" = 0.070
```

Region ID 应以 inspect 生成的 `regions.toml` 为准。

## 12. Interface Transition

两种 transition 模式互斥。

### 12.1 固定宽度

```toml
[regions.mesh]
transition_width = 0.30
```

单位为米。

`0` 表示关闭。

变化层位于不同尺度 interface 的粗侧。

### 12.2 对数尺度梯度

```toml
[regions.mesh]
transition_gradient = 5.0
```

单位为 `1/m`。

LinkMesh 按每条不同尺度 interface 的细、粗 baseline 尺度推导各自的变化层宽度。

不能同时配置：

```toml
transition_width = 0.30
transition_gradient = 5.0
```

## 13. 多区域局部加密

可重复配置 R-Z point local refinement：

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

LinkMesh 自动判断每个点所属的 Region。

点源不会改变 Region 拓扑，也不要求该点成为 mesh node。

启用 `--verbose` 后会报告：

- 点坐标；
- 自动识别的 Region；
- point target dx；
- Region baseline dx；
- 影响宽度；
- affected triangle 数量；
- maximum area excess。

## 14. PNG 输出

### 14.1 几何网格图

单区域：

```toml
[output]
plot = "mesh.png"
```

多区域：

```toml
[regions]
plot = "mesh.png"
```

### 14.2 Shape quality Q 图

单区域：

```toml
[output]
quality_plot = "mesh_quality.png"
```

多区域：

```toml
[regions]
quality_plot = "mesh_quality.png"
```

颜色固定为：

- `Q = 0`：红色；
- `Q = 0.5`：蓝色；
- `Q = 1`：绿色。

颜色范围固定为 `[0,1]`，不会按每个 Case 的最小和最大 Q 自动拉伸。

质量图使用所有 refinement 完成后的 final Mesh2D。

质量图是数值报告的视觉补充，不替代：

- 结构检查；
- 外部程序加载；
- 初始化；
- 时间推进；
- 稳定性验证；
- 物理验证。

## 15. TRIMEG 输出

单区域配置：

```toml
schema_version = 1

[task]
target = "trimeg"

[input]
array_file = "boundary.pts"

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

检查：

```bash
"$RELEASE/bin/linkmesh-check" trimeg
"$RELEASE/bin/linkmesh-check" plot
```

运行：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/generate.toml"
```

文件成功生成只表示：

```text
GENERATED
```

不自动表示 TRIMEG 或 MATLAB 已成功读取。

## 16. M3D-C1 输出

单区域配置：

```toml
schema_version = 1

[task]
target = "m3dc1"

[input]
array_file = "boundary.pts"

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

检查：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
"$RELEASE/bin/linkmesh-check" plot
```

运行：

```bash
"$RELEASE/bin/linkmesh" \
    --config "$PWD/generate.toml"
```

SCOREC helper 管理 rank-0 文件名。传入：

```text
mesh.smb
```

时，实际输出通常为：

```text
mesh0.smb
```

M3D-C1 SMB 输出还需要：

- Linux x86-64；
- 兼容 MPI；
- 可解析的 `libmpi.so.40`；
- 兼容 glibc；
- 兼容 libstdc++。

文件生成成功不自动表示 M3D-C1 已完成加载或初始化。

## 17. CLI 运行

单区域可通过 CLI 显式运行：

```bash
"$RELEASE/bin/linkmesh" \
    --no-config \
    --target mesh_only \
    --boundary-source array_file \
    --array-file "$PWD/boundary.pts" \
    --mesh-dx 0.04 \
    --plot "$PWD/mesh.png" \
    --quality-plot "$PWD/mesh_quality.png" \
    --verbose
```

多区域 inspect：

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect.toml"
```

也可以显式使用 boundary-list：

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect.toml" \
    --boundary-list "$PWD/boundaries.toml" \
    --regions-map "$PWD/regions.toml" \
    --plot "$PWD/inspect.png" \
    --verbose
```

多区域 generate：

```bash
"$RELEASE/bin/linkmesh" regions generate \
    --config "$PWD/generate.toml"
```

CLI 参数和 TOML 路径的最新映射应以对应 `-h` 输出为准：

```bash
"$RELEASE/bin/linkmesh" -h
"$RELEASE/bin/linkmesh" regions inspect -h
"$RELEASE/bin/linkmesh" regions generate -h
```

## 18. Verbose 质量报告

启用：

```toml
[runtime]
verbose = true
```

或：

```bash
--verbose
```

后，LinkMesh 会报告 final Mesh2D 的数值质量。

主要指标：

- `angle min/P01/P05/max`：三角形角度分布；
- `shape Q min/P01/P05/median`：三角形形状质量；
- `equivalent size`：等效尺寸；
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
- 一半三角形的 Q 不高于 `0.94`，另一半不低于该值。

低 Q 不会自动代表求解器失败。网格质量应结合结构检查、尺寸过渡和真实消费端结果判断。

## 19. 常见问题

### 19.1 `OpenFUSIONToolkit==26.6 required`

Release 固定携带并要求 OpenFUSIONToolkit 26.6。

如果检查报告导入了 Release 外部的 OFT，确认使用的是：

```bash
"$RELEASE/bin/linkmesh"
```

而不是：

```bash
python -m linkmesh
```

### 19.2 缺少 NumPy、h5py 或 Matplotlib

检查：

```bash
"$RELEASE/bin/linkmesh-check" all
```

确认实际 Python：

```bash
printf '%s\n' "${LINKMESH_PYTHON:-not explicitly set}"
```

在所选 Python 环境中安装缺失依赖。

### 19.3 Helper 或 MPI 失败

运行：

```bash
"$RELEASE/bin/linkmesh-check" m3dc1
```

重点检查：

- helper 是否为 Linux x86-64 ELF；
- `ldd` 是否存在 `not found`；
- `libmpi.so.40` 是否可解析；
- glibc 和 libstdc++ 是否兼容。

TRIMEG 和普通 PNG 输出不调用 SCOREC helper，不应因为 helper 或 MPI 缺失而被阻塞。

### 19.4 Boundary-list 文件缺失

清单中的相对路径相对于清单文件所在目录，而不是当前终端目录。

检查：

```bash
sed -n '1,240p' boundaries.toml
find . -maxdepth 3 -type f -print
```

### 19.5 Multi-array 与 boundary-list 冲突

同一个 effective 配置只能选择一种来源：

```toml
multi_array_file = "boundaries.txt"
```

或者：

```toml
boundary_list = "boundaries.toml"
```

不能同时使用。

### 19.6 Regions map 不匹配

如果修改了以下任一内容，应重新 inspect：

- 曲线坐标；
- 曲线数量；
- 清单顺序；
- 显式 `curve_id`；
- multi-array block 顺序；
- 曲线包含关系。

重新执行：

```bash
"$RELEASE/bin/linkmesh" regions inspect \
    --config "$PWD/inspect.toml"
```

人工检查新的 PNG 和 map 后，再执行 generate。

## 20. 建议反馈内容

请提供系统信息：

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

生成文件：

```bash
find . \
    -maxdepth 2 \
    -type f \
    -printf '%s %p\n' 2>&1 |
    sort
```

同时提供：

- 实际执行的 LinkMesh 命令；
- 配置文件；
- boundary list 和 regions map；
- 完整 stdout；
- 完整 stderr；
- Python 路径和版本；
- 输出文件名称和大小；
- 外部消费端达到的验证状态。