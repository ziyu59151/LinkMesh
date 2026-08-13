# LinkMesh 组内使用说明

本文面向日常 Case 使用。正式字段、兼容矩阵和迁移边界以根目录
`LinkMesh_Architecture_Plan.md` 为准。

## 1. 工作流选择

LinkMesh 现在有两类明确入口：

```text
根命令：python -m linkmesh [options]
  → 单个实际计算域边界
  → 单 Region Mesh2D

多区域：python -m linkmesh regions inspect ...
       → 人工确认 regions map
       → python -m linkmesh regions generate ...
       → N-region Mesh2D
```

根命令只用于单区域。需要第一壁外导体层、真空层或其他多个物理 Region 时，必须准备
重复 counted R-Z blocks，并显式执行 `regions inspect/generate`。LinkMesh 不从
GFile 的 LCFS、第一壁和人工外框自动建立多区域。

## 2. 单区域配置

单区域配置不再包含 `profile`，只使用 `mesh_dx`：

```toml
schema_version = 1

[task]
target = "m3dc1"

[input]
gfile = "GFile"

[domain]
boundary_source = "lcfs"

[mesh]
mesh_dx = 0.08

[output]
model = "mesh/model.txt"
smb = "mesh/mesh.smb"
plot = "mesh/mesh.png"

[runtime]
verbose = true
```

运行：

```bash
python -m linkmesh --config linkmesh.in
```

临时生成更细的单区域网格：

```bash
python -m linkmesh --config linkmesh.in --mesh-dx 0.05
```

`mesh_dx` 单位为 m，是唯一单 Region 目标网格尺度。配置优先级保持：

```text
内建默认值 < linkmesh.in < 显式 CLI 参数
```

`lcfs` 表示 LCFS 是唯一实际边界。未来启用 `first_wall` 时，第一壁将作为唯一实际
计算域边界，壁内形成一个 Region；LCFS 即使绘制，也只是参考曲线，不自动成为内部
Region interface。

## 3. 多区域配置与命令

多区域只使用两阶段工作流：

```bash
python -m linkmesh regions inspect --config regions-inspect.in
python -m linkmesh regions generate --config regions-generate.in
```

`inspect` 读取多轮廓输入、建立当前支持的包含关系并生成 regions map 和检查图。
用户确认 map 后，`generate` 重新读取输入和 map，并生成最终多区域网格。

多区域尺度使用：

- `regions generate --mesh-dx`：全部最终 Region 的默认尺度；
- `regions generate --region-dx ID=DX`：按 regions map 的最终 Region ID 覆盖；
- `regions generate --transition-width`：可选全局变化层厚度。

根命令的 `--mesh-dx` 与 regions 的 `--mesh-dx` 名称相同但作用域不同。不要把旧
`plasma_dx/vacuum_dx/outer_dx` 自动换算为 `region_dx`。

## 4. 旧配置迁移

旧单区域配置：

1. 删除 `[domain].profile`。
2. 把稳定的单区域目标尺度写为 `[mesh].mesh_dx`。
3. 删除 `plasma_dx`、`vacuum_dx` 和 `outer_dx`。

旧 nested 配置不能机械一对一迁移。需要多区域时：

1. 准备表达真实物理边界的 multi-array 文件。
2. 执行 `regions inspect`。
3. 检查 inspection PNG 和 regions map。
4. 使用 `regions generate` 的 `mesh_dx/region_dx` 设置尺度。
5. 需要变化层时设置 `transition_width`。

LinkMesh 不自动把旧 LCFS、第一壁和 artificial outer 转换为 multi-array 文件或
regions map。源码清理完成后，旧 `--profile` 和三个 legacy dx 参数将被 argparse
拒绝，旧 TOML 字段将被严格配置校验拒绝；不会静默迁移。

## 5. Case 管理

建议一份 LinkMesh 服务同层级多个 Case，每个 Case 保存自己的配置、GFile 或边界
输入、regions map（多区域时）、M3D-C1 输入和网格产物：

```text
work/
├── LinkMesh/
├── 100/
│   ├── linkmesh.in
│   ├── GFile
│   └── mesh/
└── 101/
    ├── linkmesh.in
    ├── GFile
    └── mesh/
```

配置文件中的相对路径按配置文件目录解析。稳定科研设置写入配置文件，显式 CLI 适合
临时覆盖。

推荐把网格预处理与正式求解分开：

```text
生成网格
  → 人工检查 PNG
  → 固化 TXT/HDF5/SMB 和配置
  → 提交求解作业
```

不要在每次 `sbatch` 中无条件覆盖已经检查的网格。只修改求解参数且网格需求不变时，
可以复用已确认产物；修改边界、Region 结构或网格尺度后应重新生成。

PNG 只用于几何检查，不替代 TRIMEG 或 M3D-C1 的加载、初始化、时间推进、稳定性和
物理正确性验收。
