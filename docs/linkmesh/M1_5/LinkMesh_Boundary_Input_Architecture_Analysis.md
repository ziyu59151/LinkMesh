# LinkMesh 边界输入架构与 EAST 真实样例调查报告

## 1. 文档定位

本文整理 LinkMesh 当前边界输入架构、实时实现状态、EAST 二维计算边界调查结果，以及后续输入层建设建议。

本文的用途是：

1. 为 `LinkMesh_Architecture_Plan.md` 的下一次更新提供直接证据和架构建议；
2. 明确 `single_region + array_file` 的真实文件需求；
3. 区分 LCFS、第一壁、内部磁面和外部计算边界；
4. 确定下一阶段输入层实现范围和验收顺序。

本文不是正式技术蓝图。字段、函数签名、配置键、错误类型和验收门槛仍应由 `LinkMesh_Architecture_Plan.md` 裁决。

---

## 2. LinkMesh 的核心定位

LinkMesh 是独立、轻量的二维非结构化网格转换工具，核心数据流为：

```text
边界信息获取
→ 计算域构造
→ OFT/Triangle 二维三角剖分
→ Mesh2D
→ TRIMEG HDF5 或 M3D-C1 TXT+SMB
→ PNG 几何自检
```

OFT/Triangle 是唯一二维三角网格生成底座。

PUMI 不负责重新剖分，只负责目标几何分类、APF/MDS 网格构造和 native SMB 写出。

LinkMesh 不建设通用边界插件系统、通用区域 DSL 或第二网格生成引擎。

---

## 3. 边界输入的三个独立层次

### 3.1 输入载体

输入载体回答“边界数据如何进入 LinkMesh”。

当前需要支持的载体是：

1. GFile/EQDSK 平衡文件；
2. 外部二维边界纯文本文件。

文件是否具有扩展名不构成格式语义。老师提供的 `EAST` 文件没有扩展名，但仍是合法的纯文本边界输入。

### 3.2 边界物理语义

边界物理语义回答“这条边界在物理上是什么”。

候选语义包括：

- LCFS 或分离面；
- limiter/第一壁相关轮廓；
- LCFS 内部闭合磁面；
- 为特定研究目标设计的计算边界；
- 研究人员直接给定的计算边界；
- 外部程序生成的计算边界。

二维坐标数组只是数据表达形式，不自动等同于 LCFS、第一壁或磁通面。

### 3.3 边界构造方法

边界构造方法回答“边界是如何得到的”。

可能包括：

- 从 GFile 直接读取 LCFS；
- 从 GFile 直接读取 limiter/第一壁；
- 从 GFile 的二维极向磁通场提取内部磁面；
- 由外部程序构造；
- 由研究人员直接提供；
- LinkMesh 按固定策略构造人工最外边界。

输入载体、物理语义和构造方法必须分别建模，不能混为一个概念。

---

## 4. 推荐的目标输入架构

不同边界来源应在进入网格生成前归一为同一种有序二维闭合轮廓：

```text
GFile LCFS
GFile limiter/第一壁
GFile 内部闭合磁面
外部二维计算边界
        ↓
统一二维 R-Z 闭合轮廓
        ↓
统一 single_region OFT Domain
        ↓
OFT/Triangle
        ↓
Mesh2D
        ↓
Writer 和 Plotter
```

单区域和固定嵌套多区域路径保持分离：

```text
LinkMesh
├── single_region
│   ├── lcfs
│   ├── array_file
│   ├── flux_surface
│   └── first_wall
│
└── nested_three_region
    └── LCFS + 可选第一壁 + artificial_outer
```

这里的固定嵌套多区域不表示支持任意区域拓扑、任意多个 face、三维网格或并行分区。

---

## 5. 当前实现状态

### 5.1 `single_region + lcfs`

状态：**IMPLEMENTED / PASSED**。

当前正式数据流为：

```text
GFile
→ OFT 读取 LCFS
→ LCFS 作为唯一计算域边界
→ single_region OFT Domain
→ OFT/Triangle
→ Mesh2D
→ 目标输出
```

这是当前正式开放的单区域输入路径。

### 5.2 `single_region + first_wall`

状态：**PLANNED / NOT IMPLEMENTED**。

GFile Reader 已经能够获得 limiter/第一壁点列，固定嵌套多区域路径也会使用该数据。

当前缺少的是把第一壁作为单区域唯一外边界的完整配置放行、Domain 分派和真实验收路径。

因此，“未实现”不表示第一壁无法读取，而是表示 `single_region + first_wall` 尚未形成正式业务闭环。

### 5.3 `single_region + array_file`

状态：**PLANNED / NOT IMPLEMENTED**。

配置层已经预留 `boundary_source=array_file` 及对应路径字段，但业务链尚未接通。

仍需完成：

- counted R-Z boundary text Reader；
- 配置兼容矩阵和 required-fields 放行；
- CLI 对边界 Reader 的编排；
- 单区域 OFT Domain 接入；
- 无 GFile 情况下的 PNG 自检；
- EAST 真实样例验收；
- 异常格式和非法几何测试。

### 5.4 固定嵌套多区域

状态：**IMPLEMENTED / LINKMESH 生成侧真实验收已通过**。

该路径能够使用：

- GFile LCFS；
- 可选 limiter/第一壁；
- LinkMesh 构造的人工最外边界。

它可以形成固定嵌套的两区域或三区域网格。

该结论不表示：

- M3D-C1 多区域或多 face 消费语义已经开放；
- 支持任意区域拓扑；
- 支持三维、自适应网格或并行分区。

### 5.5 `single_region + flux_surface`

状态：**候选能力 / NOT IMPLEMENTED / 需要 OFT 26.6 只读侦察**。

配置名称已经预留，但当前不得进入业务执行。

不得通过缩放 LCFS 或其他几何插值伪造内部磁面。

---

## 6. EAST 真实边界文件调查

老师提供的真实样例位于：

```text
/data/liuchang/east_fishbone_1/EAST
```

已确认文件属性：

- ASCII 纯文本；
- 无文件扩展名；
- 文件大小为 5258 字节；
- 共 105 行；
- 第一行为整数 `104`；
- 后续恰好包含 104 行二维浮点坐标；
- 每个坐标行包含两列；
- 第一列为 `R`；
- 第二列为 `Z`；
- 坐标单位为米；
- 首尾坐标不重复；
- 最后一点连接回第一点，构成隐式闭合轮廓。

文件结构为：

```text
N
R_1 Z_1
R_2 Z_2
...
R_N Z_N
```

该文件通过原有流程中的：

```text
inFile EAST
```

作为网格计算边界输入。

配套流程还分别使用：

- `east.txt`；
- SMB 网格文件；
- EQDSK 平衡文件。

这说明原有流程明确区分：

1. `EAST`：二维网格计算边界；
2. `east.txt` 和 SMB：网格模型及网格文件；
3. EQDSK：独立的平衡数据输入。

因此，EAST 文件是 `single_region + array_file` 的直接真实需求证据。

---

## 7. EAST 几何验证结果

按照第一列 `R`、第二列 `Z`、单位米完成绘图和几何检查，得到：

- 边界节点数：104；
- \(R\) 范围：约 \(1.465\) 至 \(2.269\ \mathrm{m}\)；
- \(Z\) 范围：约 \(-0.627\) 至 \(0.563\ \mathrm{m}\)；
- 包围面积：约 \(0.7211\ \mathrm{m}^2\)；
- 周长：约 \(3.1574\ \mathrm{m}\)；
- 输入点序：逆时针；
- 自交数量：0；
- 首尾点不同；
- 通过隐式连接形成单一闭合轮廓。

绘图外形和数值量级与 EAST 装置二维极向截面相符。

由 User 确认：

```text
第一列为 R
第二列为 Z
坐标单位为米
```

该结论可以作为下一版蓝图 `array_file` 契约的直接依据。

当前仍未确认：

- 该边界的具体物理构造算法；
- 它是否对应某条磁通等值线；
- 它与 LCFS、第一壁、磁轴和 X-point 的精确位置关系。

这些物理来源信息可以继续调查，但不阻塞 LinkMesh 读取已经由研究人员确认的最终计算边界。

LinkMesh 应把它描述为“外部提供的二维计算边界”，不得擅自标记为 LCFS、第一壁或内部磁面。

---

## 8. `array_file` v1 推荐正式契约

现有蓝图中的“两列 CSV、无头部”规划与 EAST 真实文件不一致，应由下一版蓝图替换。

建议 `array_file` v1 固定为严格的 counted R-Z boundary text：

```text
N
R_1 Z_1
R_2 Z_2
...
R_N Z_N
```

推荐契约如下：

1. 文件是纯文本，文件扩展名不参与格式判断。
2. 第一行只包含一个十进制整数 `N`。
3. `N` 表示随后边界坐标点的数量。
4. 第一行之后必须恰好存在 `N` 行坐标。
5. 每个坐标行必须恰好包含两个有限浮点数。
6. 第一列为 `R`，第二列为 `Z`。
7. 坐标单位为米。
8. 列之间使用一个或多个空白字符分隔。
9. P0 不支持逗号分隔、表头、注释、索引列、额外列或多条轮廓。
10. 输入边界采用隐式闭合，首点和末点不得重复。
11. 最后一点由 LinkMesh 连接回第一点。
12. 边界至少包含三个不同节点。
13. 边界必须为单一、简单、非退化闭合轮廓。
14. 坐标必须全部有限。
15. 面积必须非零。
16. 不允许自交。
17. 输入点序可以被读取和验证，进入 `Mesh2D.outer_boundary` 前按照正式内部方向契约归一化。
18. 不根据文件名、扩展名或内容猜测其他格式。
19. 不自动把外部边界解释成 LCFS、第一壁或磁通面。
20. 不通过排序、重采样、全局去重或几何缩放改变用户提供的轮廓。

`array_file` 作为配置名称可以继续保留。它表示文件内容最终形成二维坐标数组，不表示文件必须是 CSV、NumPy 文件或具有特定扩展名。

---

## 9. `array_file` 对功能块的影响

实现 `single_region + array_file` 需要调整：

1. 蓝图输入契约；
2. 二维边界 Reader；
3. 配置兼容矩阵；
4. required-fields；
5. CLI 流程编排；
6. single_region Domain 分派；
7. 无 GFile PNG 自检；
8. 测试和 EAST 真实验收。

原则上不需要修改：

- GFile 原始解析；
- OFT/Triangle 通用网格生成核心；
- Mesh2D 的总体定位；
- TRIMEG HDF5 Writer；
- M3D-C1 TXT Writer；
- M3D-C1 SMB Writer；
- native helper。

Writer 不应根据边界来源分叉。

不同来源应在 Writer 之前统一形成合法 `Mesh2D`。

---

## 10. Plotter 调整原则

当前 Plotter 依赖 `GFileData`，并绘制 LCFS、第一壁、磁轴和三角网格。

`array_file` 路径可能不向 LinkMesh 提供 GFile，因此 Plotter 应调整为：

- 使用 `Mesh2D` 和实际计算边界完成基础几何自检；
- 将 LCFS、第一壁和磁轴作为可选平衡参考信息叠加；
- 在没有 GFile 时仍能输出边界和网格 PNG；
- 不为了兼容 Plotter 而把外部计算边界伪装成 LCFS。

这项调整不能改变 `Mesh2D.outer_boundary` 的正式语义。

---

## 11. `flux_surface` 的功能含义

`flux_surface` 不是文件格式，也不是新的网格生成引擎。

它表示：

> 从 GFile 的二维极向磁通场中提取一条指定的内部闭合磁通面，并将它作为 `single_region` 的唯一计算域边界。

在轴对称平衡中，磁面满足：

\[
\psi(R,Z)=\psi_0
\]

常用归一化极向磁通为：

\[
\psi_N(R,Z)=
\frac{\psi(R,Z)-\psi_{\mathrm{axis}}}
{\psi_{\mathrm{boundary}}-\psi_{\mathrm{axis}}}
\]

通常：

- \(\psi_N=0\) 对应磁轴；
- \(0<\psi_N<1\) 对应 LCFS 内部闭合磁面；
- \(\psi_N=1\) 对应 LCFS 或分离面。

候选数据流为：

```text
GFile
→ OFT 读取二维磁通场
→ 用户选择 ψ_N
→ 提取包围磁轴的合法闭合等值线
→ 统一二维边界验证
→ single_region OFT Domain
→ OFT/Triangle
→ Mesh2D
```

该能力适合：

- 只研究等离子体核心或内部区域；
- 希望计算边界避开 X-point；
- 希望通过归一化磁通控制计算域范围；
- 需要多个内部磁面的参数扫描。

该能力不能替代 EAST 外部计算边界。

如果 EAST 边界用于包含 X-point 或其附近目标磁拓扑区域，那么 LCFS 内部的 `flux_surface` 通常无法满足该需求。

实现前必须只读确认：

- OFT 26.6 是否提供稳定的磁面轮廓提取接口；
- 归一化磁通的正式定义；
- 多轮廓选择规则；
- 包围磁轴的判断方法；
- 闭合、方向和采样约定；
- 接近分离面时的失败行为。

当前不得把 `flux_surface` 纳入本轮 `array_file` 实现。

---

## 12. TRIMEG 特殊 X-point 边界

TRIMEG 为研究 X-point 附近物理可能使用专门设计的计算边界。

该边界：

- 不一定等于 LCFS；
- 不一定等于第一壁；
- 不一定是普通闭合磁通面；
- 可能由外部程序或研究人员构造。

在真实构造算法确认前，LinkMesh 不应：

- 根据经验自动构造该边界；
- 通过缩放 LCFS 代替真实边界；
- 因边界包含 X-point 就自动引入多区域；
- 把未知构造方法写成正式项目事实。

只要最终边界能够转换为正式 counted R-Z boundary text，就可以复用统一输入路径：

```text
外部特殊边界构造
→ counted R-Z boundary text
→ LinkMesh array_file Reader
→ single_region OFT/Triangle
→ Mesh2D
→ TRIMEG HDF5
```

因此，不需要分别为 EAST 和 TRIMEG 建设两套边界输入系统。

---

## 13. 输入层复用原则

以下边界具有不同来源和物理语义：

- LCFS；
- limiter/第一壁；
- 内部磁面；
- 外部二维计算边界。

但它们进入网格生成前都应归一为统一二维计算边界：

```text
边界获取
→ 统一闭合轮廓验证和方向归一化
→ 统一 single_region Domain
→ 通用 OFT/Triangle
→ Mesh2D
```

工程原则为：

- 边界获取逻辑按来源分离；
- 几何验证规则尽量共用；
- single_region Domain 构造逻辑共用；
- Triangle 网格生成核心不复制；
- Writer 不判断边界来源；
- Plotter 以实际计算边界为基础；
- 不引入插件系统、抽象基类或通用区域配置语言。

---

## 14. 下一版蓝图建议更新内容

下一版 `LinkMesh_Architecture_Plan.md` 应至少完成：

1. 将 EAST 边界调查状态更新为已获得真实文件证据。
2. 记录 EAST 文件路径和格式结构。
3. 将 `array_file` v1 从旧 CSV 规划改为 counted R-Z boundary text。
4. 明确文件扩展名不参与格式判断。
5. 固化第一列 `R`、第二列 `Z`、单位米。
6. 固化计数头、严格行数、双列浮点和隐式闭合规则。
7. 固化有限性、非退化、非自交和方向归一化要求。
8. 放行 `single_region + array_file` 的下一阶段实现。
9. 明确 `array_file` 路径不要求 GFile。
10. 明确 Plotter 必须支持无 GFile 的基础 PNG 自检。
11. 明确 Writer 和 Mesh2D 不按边界来源分叉。
12. 修正固定嵌套多区域状态为“已实现并完成 LinkMesh 生成侧真实验收”。
13. 保持 M3D-C1 多区域、多 face 消费语义未开放。
14. 保持 `single_region + first_wall` 为低优先级未实现能力。
15. 保持 `flux_surface` 为候选能力，并要求 OFT 26.6 只读侦察。
16. 保持 M3D-C1 时间推进、长期稳定性和物理正确性为 `PENDING`。
17. 不在本次蓝图更新中引入局部加密、多 face、三维、自适应或并行分区。

---

## 15. 推荐实施顺序

当前主线建议为：

```text
EAST R-Z 和单位验证：完成
→ 更新 array_file 蓝图契约
→ User 确认蓝图
→ 实现 counted R-Z boundary Reader
→ 放行 single_region + array_file
→ 接入统一 single_region OFT Domain
→ 支持无 GFile PNG
→ 单元测试和异常输入测试
→ EAST 真实 Mesh2D、TXT+SMB、PNG 验收
→ M3D-C1 加载和初始化回归
→ M3D-C1 时间推进主循环
```

`flux_surface` 作为独立后续任务：

```text
真实研究需求确认
→ OFT 26.6 只读侦察
→ 形成直接接口证据
→ 蓝图更新
→ User 确认
→ 业务实现
```

`single_region + first_wall` 保持候选能力，其优先级低于当前 EAST `array_file` 主线。

---

## 16. `array_file` 实现验收建议

实现完成后至少验证：

### 文件读取

- 正确读取 EAST 的 `N=104`；
- 后续恰好读取 104 个坐标点；
- 输出为有限二维浮点数组；
- 第一列保持 `R`，第二列保持 `Z`；
- 不依赖文件扩展名。

### 严格失败

- 缺少计数头；
- 非整数或非法 `N`；
- 实际坐标行数少于或多于 `N`；
- 坐标列数不是 2；
- 空字段或缺失字段；
- 非数字；
- NaN 或 Inf；
- 少于三个不同节点；
- 首尾重复；
- 零面积；
- 自交；
- 多轮廓或额外数据。

### 网格生成

- 只构造一个 OFT region；
- 不创建 LCFS interface、first-wall interface、vacuum annulus 或 artificial outer；
- 使用 `plasma_dx`；
- 生成合法 `Mesh2D`；
- `Mesh2D.outer_boundary` 表达实际 EAST 计算边界；
- Writer 不需要知道边界来自 `array_file`。

### PNG

- 无 GFile 时仍能绘制计算边界和网格；
- 坐标轴明确为 \(R\) 和 \(Z\)，单位为米；
- 边界和网格无明显越界、翻转或拓扑异常。

### 真实消费

- 生成 M3D-C1 TXT+SMB；
- 生成 PNG；
- 完成 M3D-C1 加载；
- 完成初始化回归；
- 时间推进结果单独记录，不由加载或初始化成功代替。

---

## 17. 已确认事实

- `single_region + lcfs` 已实现并通过验收。
- 固定嵌套多区域路径已实现并完成 LinkMesh 生成侧真实验收。
- GFile Reader 能够读取 LCFS 和 limiter/第一壁数据。
- `single_region + first_wall` 尚未正式开放。
- `array_file` 已有配置入口，但业务链尚未接通。
- `flux_surface` 已预留名称，但业务功能未实现。
- EAST 是真实的外部二维计算边界文件。
- EAST 文件采用计数头加二维坐标点列。
- EAST 文件无扩展名。
- EAST 第一列为 `R`，第二列为 `Z`。
- EAST 坐标单位为米。
- EAST 包含 104 个边界点。
- EAST 首尾点不同，采用隐式闭合。
- EAST 输入点序为逆时针。
- EAST 边界面积非零且无自交。
- EAST 边界与 EQDSK 平衡数据是分离输入。
- Mesh2D 用于承载实际计算域最外层边界。
- M3D-C1 时间推进、长期稳定性和物理正确性仍未通过验收。

---

## 18. 仍待确认事项

- EAST 边界的具体物理构造算法。
- EAST 边界与 LCFS、第一壁、磁轴和 X-point 的精确关系。
- OFT 26.6 是否提供适合 LinkMesh 的内部磁面提取接口。
- `flux_surface` 的正式用户需求和优先级。
- `single_region + first_wall` 是否有近期真实使用需求。
- TCV/TRIMEG 特殊边界的实际文件样例和构造来源。

这些待确认事项不阻塞 `single_region + array_file` 的蓝图修订和后续实现。

---

## 19. 最终结论

EAST 真实样例已经提供足够证据，将 LinkMesh 的 `array_file` 首版契约固定为：

```text
第一行节点数 N
后续 N 行 R Z 坐标
单位米
空白分隔
无扩展名要求
首尾不重复
隐式闭合
单一简单非自交轮廓
```

该输入应汇合到现有统一 `single_region` OFT/Triangle 路径，不复制网格生成核心，也不修改 Writer 的边界来源无关性。

当前下一项正式任务应为：

```text
更新 LinkMesh_Architecture_Plan.md 中的 array_file 契约
→ User 验收蓝图
→ Aider 实现 single_region + array_file
→ EAST 真实网格和 M3D-C1 验收
```

`flux_surface` 是从 GFile 二维磁通场提取内部闭合磁面的独立候选能力，不属于当前 EAST `array_file` 实现范围，应在真实需求确认和 OFT 26.6 只读侦察后另行处理。