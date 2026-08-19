# LinkMesh 当前工作计划

## 1. 文档用途

本文档面向 LinkMesh 项目负责人，用于记录当前阶段的工作顺序、调查任务、交付边界和人工验收安排。

本文档不是技术蓝图，不定义正式字段、schema、CLI 或外部接口，也不作为仓库内执行端的参考依据。

正式技术定义以 `LinkMesh_Architecture_Plan.md` 为准；已完成事实和证据归档到 `History.md`。

## 2. 当前项目状态

### 2.1 已完成

- 单区域 GFile/EQDSK 和 counted R-Z boundary 输入链已经实现。
- 多轮廓 `regions inspect` 已经实现。
- 多区域 `regions generate` 已经实现。
- 支持全部 Region 的默认常数 `mesh_dx`。
- 支持按最终 Region ID 设置独立常数 `region_dx`。
- 支持 TOML 配置与显式 CLI 覆盖。
- 多区域网格采用统一的全局节点表和全局三角形连接表。
- 多区域 PNG 已完成真实生成和人工检查。
- 多区域 TRIMEG HDF5 生成代码、自动测试和服务器实际检查已经通过。

### 2.2 当前主任务

实现：

```text
N-region Mesh2D
→ PUMI 输入数据
→ SCOREC/PUMI helper
→ 配套 model.txt + native SMB
→ 交付同门验证
```

### 2.3 并行调查任务

调查可控网格密度渐变：

```text
分 Region 常数 dx
→ OFT/Triangle 内部密度控制能力
→ MFM/Meshgen gradation rate 参考
→ LinkMesh 静态空间尺度渐变方案
```

## 3. Mesh2D 索引事实

LinkMesh 的 `Mesh2D` 使用全局索引：

```text
nodes:
    shape = (N, 2)
    全局节点坐标表

triangles:
    shape = (T, 3)
    使用 nodes 全局行号的三角形连接表

region_ids:
    shape = (T,)
    每个三角形所属的最终 Region ID
```

内部三角形节点索引统一为 0-based。

不同 Region 不分别维护局部节点表。共形内部界面上的节点由相邻 Region 共享，不在界面两侧重复编号。

Writer 或外部适配器负责目标格式需要的索引转换。

`region_ids` 可以在不携带区域标签的 TRIMEG complete-11 输出中不写出，但在构造 M3D-C1/PUMI 多区域 classification 之前不得丢弃。

## 4. M3D-C1/PUMI 任务边界

### 4.1 LinkMesh 负责

- 接收已经生成的 N-region `Mesh2D`。
- 保留全局节点、三角形和逐三角形 Region ID。
- 根据已确认契约构造 geometric model 输入。
- 确定 geometric vertex、edge、loop、face 和 tag。
- 确定 mesh vertex、edge、triangle 的 classification 输入。
- 构造 Python 到 C++ helper 的交换数据。
- 调用服务器实际安装的 SCOREC/PUMI API。
- 创建 classified APF/MDS mesh。
- 调用 PUMI 官方 native writer。
- 生成配套的 `model.txt` 和 SMB。
- 检查输入数组、索引、引用和 classification 的内部一致性。
- 检查 helper 成功退出以及目标文件存在且非空。
- 将文件交付同门。

### 4.2 SCOREC/PUMI 的角色

SCOREC/PUMI 作为成熟黑箱使用。

PUMI 不负责重新三角剖分，不是 LinkMesh 的第二种网格生成引擎。它只接收 LinkMesh 提供的几何模型、网格拓扑和 classification 数据，建立 APF/MDS mesh 并写出 native SMB。

### 4.3 本阶段不负责

- 逆向分析 SMB 二进制内部结构。
- 手写 SMB 文件。
- 证明 PUMI 输出的 SMB 内部格式符合 M3D-C1。
- 调查 M3D-C1 的 SMB 读取实现。
- M3D-C1 真实加载。
- M3D-C1 初始化。
- 时间推进、稳定性和物理验证。
- 复刻原商业网格生成器的剖分算法。

上述消费验证由同门完成。

## 5. M3D-C1/PUMI 精准调查

### 5.1 调查目标

只调查 LinkMesh 调用 PUMI 所需的输入契约和准确 API：

1. `Mesh2D.region_ids` 如何映射到 geometric face tag。
2. 多区域模型需要多少 geometric face。
3. 闭合曲线如何表示为 model edge 和 loop。
4. 内部共享界面如何被相邻 face 引用。
5. loop 中 edge 的方向如何编码。
6. mesh vertex、edge、triangle 分别 classified 到哪个 model entity。
7. PUMI 创建 analytic/GMI model 的准确接口。
8. PUMI 创建 APF/MDS mesh entity 的准确接口。
9. `acceptChanges`、`verify` 和 `writeNative` 的调用顺序。
10. MPI、PCU、GMI、APF/MDS 的生命周期和 ownership。
11. Python/helper 交换数据所需数组、shape、dtype 和索引。
12. 当前单区域 helper 可以复用和必须扩展的部分。

### 5.2 不调查

- SMB 内部字段和二进制布局。
- M3D-C1 如何解析 SMB。
- M3D-C1 求解字段和 C1 自由度。
- M3D-C1 初始化和时间推进。
- 商业网格器的三角剖分算法。
- 参考网格与 LinkMesh 网格的逐节点一致性。

### 5.3 证据来源

本地证据：

- 当前 `LinkMesh_Architecture_Plan.md`。
- 既有 M3D-C1/SCOREC 调查报告。
- LinkMesh 当前单区域 ModelSpec、TXT Writer、SMB Writer 和 C++ helper。
- 本地 M3D-C1 的 model、mesh 和 API 源码。
- `m3dc1_reference_map.txt`。

服务器证据：

- 实际 SCOREC/PUMI 安装头文件。
- CMake package/config 和链接信息。
- 老师提供的 `Create_Multiregion_Mesh`。
- 老师提供的 `Setup_EFIT_Equilibrium`。
- 实际 MFM/Meshgen 输入及相关源码。
- 服务器当前使用的软件版本和环境。

### 5.4 调查产物

生成独立专题报告：

```text
docs/linkmesh/m3dc1_multi_region_pumi_input_report.md
```

报告必须包含：

- 证据来源和版本。
- `Mesh2D` 到 PUMI 输入对象的字段映射。
- 多区域 geometric model 拓扑。
- classification 规则。
- Python/helper 交换 schema 建议。
- C++ helper 的准确 API、签名和生命周期。
- model TXT 的生成侧字段要求。
- 单区域兼容策略。
- 实现文件规划。
- 测试和生成侧验收标准。
- 未确认事项。
- 蓝图修订建议。

报告不得宣称 PUMI 输出已经被 M3D-C1 消费。

## 6. M3D-C1/PUMI 实施顺序

```text
本地源码只读调查
→ 服务器 PUMI 接口取证
→ 老师参考案例调查
→ 精准输入契约报告
→ User 确认
→ 更新 LinkMesh_Architecture_Plan.md
→ 扩展多区域 ModelSpec
→ 扩展 TXT Writer
→ 扩展 Python/helper 交换数据
→ 扩展 C++ SCOREC/PUMI helper
→ 接入 regions generate CLI/config
→ 生成 model.txt + SMB
→ 内部一致性检查
→ 交付同门
```

## 7. PUMI 生成侧验收

LinkMesh 本阶段的验收终点是：

- 多区域 ModelSpec 已实现。
- model TXT 已生成。
- helper 输入数据完整且索引合法。
- 所有 classification 引用的 model entity 均存在。
- PUMI/APF/MDS 建网调用成功。
- `acceptChanges` 和 `verify` 按已确认接口完成。
- PUMI native writer 调用成功。
- SMB 文件存在且非空。
- model TXT 与本次 helper 输入来自同一份 ModelSpec。
- 目标文件已交付同门。

状态记录：

```text
DESIGNED
IMPLEMENTED
GENERATED
STRUCTURALLY CHECKED
DELIVERED
```

以下状态由同门提供直接证据后再更新：

```text
LOADED
INITIALIZED
TIME-STEPPED
STABILITY-VALIDATED
PHYSICALLY VALIDATED
```

## 8. 网格密度渐变调查

### 8.1 当前问题

当前 LinkMesh 支持每个最终 Region 使用独立常数 `dx`。当相邻 Region 的尺度差异很大时，界面附近的网格尺度过渡可能过快。

会议提出需要适配约 10 倍尺度差的场景，并调查 `Mesh Gradation Rate`。

### 8.2 OFT 调查

核对 OFT/TokaMaker 和 Triangle 调用链是否原生支持：

- Region 内位置相关的 size field。
- 边界尺度和面尺度的联合约束。
- 相邻三角形边长比或面积比限制。
- 网格尺度传播。
- refinement。
- background mesh 或 callback size function。
- gradation 参数。

必须区分：

- 全局常数尺度。
- 分 Region 常数尺度。
- 单一 Region 内静态空间变密度。
- 根据结果迭代的动态自适应。
- 磁面对齐网格。

本阶段只考虑静态空间尺度渐变，不开放动态自适应或磁面对齐。

### 8.3 MFM/Meshgen 参考调查

核对会议提出的 `Mesh Gradation Rate`：

- 参数所在输入文件和源码位置。
- 默认值是否确实为 `0.3`。
- 有效取值范围。
- 接近 0 和接近 1 的准确行为。
- 控制的是边长比、面积比还是尺度场梯度。
- 是否对 boundary 和 face 使用不同尺度。
- 渐变传播算法。
- 是否依赖特定商业网格器。
- 哪些算法可以在 OFT/Triangle 数据链中合法复用。

会议纪要中的默认值和参数含义目前仅作为调查线索，不作为 LinkMesh 正式契约。

### 8.4 渐变调查产物

生成独立报告：

```text
docs/linkmesh/mesh_gradation_investigation_report.md
```

报告必须给出：

- OFT 已有能力。
- MFM/Meshgen 实现。
- 可复用算法与许可证边界。
- 候选数据结构。
- 候选 CLI/config 参数。
- 与现有 `mesh_dx/region_dx` 的合并规则。
- 极端尺度差测试。
- 网格质量验收指标。
- 蓝图修订建议。

M3D-C1/PUMI 输出调查与渐变调查不得合并成一份报告。

## 9. 当前工作优先级

1. 完成多区域 PUMI 输入契约调查。
2. 完成多区域 model TXT + SMB 生成。
3. 交付同门验证。
4. 并行完成 OFT 与 MFM/Meshgen 渐变调查。
5. 根据直接证据修订蓝图。
6. 实现可控静态网格密度渐变。
7. 开始 DCD 场景适配。

## 10. 禁止事项

- 不把 SCOREC/PUMI 作为第二剖分引擎。
- 不手写 SMB。
- 不逆向 SMB 二进制格式。
- 不根据一般经验猜测服务器 PUMI API。
- 不根据 `region_ids` 自动猜测 face tag。
- 不在调查完成前开放多区域 M3D-C1 CLI。
- 不把会议 AI 纪要自动提升为正式接口证据。
- 不把参考商业网格器的节点分布作为 LinkMesh 必须复制的结果。
- 不把生成文件表述为已经被 M3D-C1 加载。