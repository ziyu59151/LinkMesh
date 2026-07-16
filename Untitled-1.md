任务性质：TokaMaker/OpenFUSION Toolkit 平衡文件读取能力专项只读侦察

当前背景：
LinkMesh 当前的 `LinkMesh_Architecture_Plan.md` 将 `readers/gfile_reader.py` 设计为由 LinkMesh 自行实现的 EQDSK/GFile 解析器，具体包括解析尺寸和数值块、读取磁轴与磁通数据、提取 LCFS 和第一壁、重塑 `psirz`、构造 `r_grid/z_grid`，最终返回 `GFileData`。

主管提出了一个必须先核实的架构问题：TokaMaker 或其所属的 OpenFUSION Toolkit（OFT）中可能已经存在 G-EQDSK/EQDSK/GFile 平衡读取、平衡导入、LCFS 提取或相关转换代码。如果已有成熟实现，LinkMesh 自己重新编写完整解析器可能造成重复开发。

注意严格区分：
1. Triangle 是二维三角剖分算法，通常只消费 vertices/segments/regions 等几何输入；
2. 本任务重点调查 TokaMaker Python 层、OFT 公共模块、工具脚本、示例和测试是否具有平衡文件读取能力；
3. 不得因为某个函数名包含 `eq`、`flux` 或 `load` 就直接判定它是 GFile 读取器，必须沿源码调用链确认；
4. 必须区分“读取 G-EQDSK 文件”“读取 TokaMaker 自有保存格式”“把平衡数组载入求解器”“从已经求解的平衡中提取 LCFS”四类不同能力。

唯一目标：
使用现有 OFT 源代码文件索引地图、TokaMaker 架构白皮书以及 `TOKAMAKER/OpenFUSIONToolkit/` 实际源码，确认以下事实：

1. TokaMaker/OFT 是否已有 G-EQDSK、EQDSK 或 GFile 读取实现；
2. 若有，它位于哪里、公开入口是什么、调用链是什么、返回什么数据；
3. 它是否直接提供 LinkMesh 所需的 LCFS、第一壁、磁轴和基础平衡数据；
4. 它能否被 LinkMesh 以稳定、轻量、许可证兼容的方式复用；
5. 若不能完整复用，哪些解析逻辑仍可作为可靠参考；
6. 当前蓝图中“LinkMesh 自行解析完整 EQDSK”的设计应保留、缩减，还是改为适配 OFT 现有能力。

本任务仅做侦察和架构判断，不实现代码、不修改蓝图。

一、必读文件

先阅读以下项目文档，建立现有契约和事实边界：

- `CONTEXT.md`
- `LinkMesh_Architecture_Plan.md`
  - 项目定位与 P0 边界
  - 模块职责矩阵
  - `GFileData` 字段定义
  - 第 6 节 `readers/gfile_reader.py` 实现规范
  - M1 验收标准
  - 蓝图更新纪律
- `Project_Tree.md`
  - 仅用于核对面向人类的当前模块说明，不作为技术裁决依据
- TokaMaker 架构白皮书，优先查找仓库中的实际路径，例如：
  - `docs/tokamaker/TOKAMAKER_Architecture_Whitepaper.md`
  - 或文件名相近的 TokaMaker/OFT 架构白皮书
- 已生成的 OFT 源代码文件索引地图
- `TOKAMAKER/oft-meshing-architecture/SKILL.md`
- `TOKAMAKER/triangle-library-integration/SKILL.md`

如果上述白皮书或索引地图的实际路径不同，先使用 `rg --files` 定位，并在报告中记录实际路径。

二、允许范围与绝对禁止事项

允许：
- 只读搜索和阅读 LinkMesh 文档；
- 只读搜索和阅读 `TOKAMAKER/`；
- 只读搜索 OFT 文件索引地图；
- 必要时运行不会修改仓库的文本检索、源码查看和 Python 只读导入检查；
- 在最终报告中提出蓝图修订建议。

绝对禁止：
- 禁止修改 `TOKAMAKER/` 下任何文件；
- 禁止修改 `M3DC1/` 下任何文件；
- 禁止修改 `readers/`、`mesher/`、`writers/`、`utils/`、`tests/`、`cli.py`；
- 禁止修改 `LinkMesh_Architecture_Plan.md`、`CONTEXT.md`、`Project_Tree.md` 或 `History.md`；
- 禁止新建实现文件、测试文件或临时报告文件；
- 禁止安装依赖、编译 OFT、运行会生成网格或二进制输出的示例；
- 禁止仅凭文件名、文档摘要或一般经验下结论；
- 禁止把“读取自有重启文件”误报成“读取 G-EQDSK”；
- 禁止把“从内存平衡对象提取 LCFS”误报成“从 GFile 解析 LCFS”；
- 禁止因发现现成代码就自行决定改变 LinkMesh 架构。

三、侦察流程

第 1 步：锁定当前 LinkMesh reader 契约

从实时 `LinkMesh_Architecture_Plan.md` 提取并记录：

- `read_gfile` 的正式函数签名；
- `GFileData` 的全部字段、shape、dtype、是否必填；
- M1 对 LCFS 闭合、方向、磁轴、第一壁和可视化的要求；
- 当前蓝图要求 LinkMesh 自行完成的解析步骤；
- `gfile_reader.py` 与 `triangle_wrapper.py` 的职责边界。

必须给出文件路径和准确行号。不要只复述知识库摘要。

第 2 步：从索引地图做全局候选定位

先搜索文件路径和文件名，再搜索源码内容。至少使用以下关键词及合理的大小写、下划线和连字符变体：

- `geqdsk`
- `g-eqdsk`
- `eqdsk`
- `gfile`
- `g_file`
- `read_g`
- `read_eq`
- `load_eq`
- `save_eq`
- `equilibrium`
- `EFIT`
- `rbbbs`
- `zbbbs`
- `nbbbs`
- `limitr`
- `rlim`
- `zlim`
- `simag`
- `sibry`
- `psirz`
- `qpsi`
- `fpol`
- `ffprim`
- `pprime`
- `rmaxis`
- `zmaxis`
- `LCFS`
- `last closed flux surface`
- `separatrix`
- `boundary`
- `limiter`

搜索范围至少包括：

- `TOKAMAKER/OpenFUSIONToolkit/src/python/`
- `TOKAMAKER/OpenFUSIONToolkit/src/examples/`
- `TOKAMAKER/OpenFUSIONToolkit/src/utilities/`
- `TOKAMAKER/OpenFUSIONToolkit/src/docs/`
- `TOKAMAKER/OpenFUSIONToolkit/src/tests/`（若存在）
- OFT 源代码文件索引地图全文

不要先假定实现一定在 `TokaMaker/meshing.py`。应覆盖 TokaMaker 包、通用 Python 包、工具脚本、示例、测试和文档。

第 3 步：对候选文件分类

将每个有效候选归入以下类别之一：

A. 真正解析 G-EQDSK/EQDSK 文本；
B. 写出 G-EQDSK/EQDSK；
C. 将已经解析的平衡数组导入 TokaMaker；
D. 从 TokaMaker 内存平衡或求解结果中提取 LCFS/separatrix；
E. 只处理几何边界或网格，不理解平衡文件；
F. 只处理自有重启文件、HDF5、JSON、XML、NetCDF 等其他格式；
G. 文档、示例或测试中的调用证据；
H. 无关的关键词命中。

报告中只详细展开 A-D 和关键的 E 类证据，但应说明其他候选为何被排除。

第 4 步：沿真实调用链追踪

如果发现疑似读取入口，必须继续追踪：

公开 API/示例调用
→ Python 包入口
→ 实际解析函数或类
→ 辅助函数
→ 返回对象或写入的内部状态
→ LCFS/第一壁/磁轴的后续获取方式

对每一层记录：

- 文件路径和准确行号；
- 函数、类或方法签名；
- 输入参数；
- 返回值或副作用；
- 是否属于公开 API；
- 是否依赖已编译 OFT 动态库；
- 是否可在不启动完整 Grad-Shafranov 求解流程的情况下使用；
- 是否有示例或测试证明其真实用途。

如果函数通过 re-export 暴露，必须同时找到定义位置和导出位置。

第 5 步：核对实际数据覆盖范围

将 OFT 候选能力与 LinkMesh `GFileData` 做逐字段映射，至少形成以下列：

- LinkMesh 字段；
- 字段物理含义；
- OFT 对应字段/API；
- 是否直接获得；
- 是否需要转换；
- shape/dtype/单位；
- 证据位置；
- 尚未确认的问题。

重点核对：

- `nw`、`nh`；
- `r_grid`、`z_grid`；
- `psirz` 的轴顺序和 shape；
- `simag`、`sibry`；
- `rmaxis`、`zmaxis`；
- LCFS 的 `R/Z` 点集；
- 第一壁或 limiter 的 `R/Z` 点集；
- LCFS 是否已闭合；
- LCFS 点序方向；
- 是否保留原始 GFile 中的 `rbbbs/zbbbs`，还是重新由磁通等值线计算；
- 坐标单位；
- 缺少第一壁时的行为；
- Fortran `D` 指数、固定宽度字段、跨行数值块等解析兼容性；
- 错误处理方式。

这里尤其要区分两条路线：

路线 1：直接读取 GFile 中已有的 `rbbbs/zbbbs`；
路线 2：读取 `psirz` 后自行通过 `psi = sibry` 等值线重新计算 LCFS。

两者不能视为完全等价，必须报告 OFT 实际采用哪一种。

第 6 步：确认 Triangle 的职责边界

只需用直接源码证据确认，不做大范围 Triangle 逆向：

- `triangle.c`/`triangle.h` 或 Python Triangle 接口接收哪些几何输入；
- 是否存在任何 EQDSK/GFile 语义；
- TokaMaker 的 `meshing.py` 是消费平衡文件，还是只消费已经构造好的几何边界；
- `gs_Domain`、`Mesh`、`run_triangle` 各自位于平衡读取之前还是之后。

本步骤的目标是防止把“TokaMaker/OFT 可能有 reader”错误表述成“Triangle 有 reader”。

第 7 步：评估可复用性

对确认存在的实现，从以下维度评价：

- API 稳定性：公开 API、内部 API、示例脚本私有函数；
- 依赖重量：纯 Python，还是需要完整 OFT 安装和动态库；
- 许可证：OFT 根许可证及候选文件适用许可证；
- 可移植性：Linux/macOS/Windows 和超算环境；
- 数据契约匹配度：能否稳定填充现有 `GFileData`；
- 测试证据：是否有真实 GFile 示例或自动测试；
- 错误处理：畸形文件、缺失 limiter、不同 EQDSK 变体；
- 维护风险：直接依赖 OFT 内部 API 是否容易随上游版本变化；
- P0 适配性：是否会把 LinkMesh 变成必须安装完整 OFT 的重型程序。

需要分别评价三种复用方式：

1. LinkMesh 直接导入并调用 OFT 的公开 reader；
2. LinkMesh 保留 `gfile_reader.py` 适配层，在内部调用 OFT；
3. LinkMesh 参考经过验证的 OFT 解析逻辑，自行维护最小独立实现。

注意：第 3 种方式涉及许可证和代码来源问题。不得建议直接复制代码，除非已经核对许可证、版权声明和归属要求。

第 8 步：形成架构结论

最终必须从以下结论中选择最符合证据的一项，也可以给出带条件的组合结论：

- 结论 A：OFT 已有公开、轻量、可直接复用的完整 GFile reader；
- 结论 B：OFT 已有 reader，但依赖完整运行时或内部 API，只适合通过 LinkMesh 适配层使用；
- 结论 C：OFT 只有部分能力，例如读取数组或提取 LCFS，LinkMesh 仍需保留部分解析逻辑；
- 结论 D：OFT 没有可复用的 GFile reader，当前 LinkMesh 独立 reader 设计应保留；
- 结论 E：当前源码证据不足，列出还需拉取或读取的准确文件。

结论必须逐条附带直接源码证据，不得依据白皮书推断。

四、需要回答的关键问题

最终报告必须明确回答：

1. 当前蓝图是否确实预设 LinkMesh 自己编写 EQDSK 解析器？
2. Triangle 本身是否读取平衡文件？
3. TokaMaker/OFT 是否读取 G-EQDSK/EQDSK？
4. 若有，准确入口和调用链是什么？
5. 它读取的是原始边界点，还是从磁通场重新计算 LCFS？
6. 是否读取第一壁/limiter？
7. 是否提供磁轴和 LinkMesh 需要的基础参数？
8. 是否需要完整 OFT 动态库或求解器初始化？
9. 是否存在示例、测试和真实样例文件？
10. 直接依赖它是否仍符合 LinkMesh“独立、轻量命令行工具”的定位？
11. 现有 `GFileData` 是否足以承接其输出？
12. 是否发现与实时蓝图冲突的直接证据？
13. 建议保留、缩减还是替换 `readers/gfile_reader.py` 的内部实现？
14. 是否需要蓝图迭代？如果需要，具体应修改哪些章节？

五、最终输出格式

在对话中输出一份报告，不要写入仓库。严格按以下结构组织：

# TokaMaker/OFT 平衡文件读取能力只读侦察报告

## 1. 执行摘要
用 5-10 条短句直接回答最重要结论，并标注结论的证据等级：
- 已确认
- 部分确认
- 未确认

## 2. 当前 LinkMesh 蓝图设计
列出 `gfile_reader.py`、`GFileData`、M1 的当前正式要求及准确行号。

## 3. 搜索范围与检索词
列出实际搜索过的目录、索引地图、关键词和未找到的预期路径。

## 4. 候选文件分类表
列：路径、符号、类别 A-H、用途、是否继续追踪、证据行号。

## 5. OFT 平衡读取调用链
使用文本箭头展示完整调用链；如果不存在，明确写“未发现”。

## 6. Triangle 职责边界
用源码证据说明 Triangle 是否理解 EQDSK/GFile。

## 7. GFileData 字段映射表
列：LinkMesh 字段、OFT 对应、转换要求、单位/shape/dtype、证据、缺口。

## 8. LCFS 与第一壁处理
分别说明原始边界读取、磁通等值线重建、闭合、方向和缺失 wall 的行为。

## 9. 依赖、许可证与轻量化评估
比较直接调用、适配调用、最小独立实现三种方案。

## 10. 与当前蓝图的冲突
逐项写明：
- 无冲突；
- 文档描述不完整；
- 或存在需要主管裁决的正式冲突。

## 11. 推荐方案
给出首选方案、备选方案、理由、风险和最小后续动作。

## 12. 蓝图修订建议
只提供建议，不修改文件。按以下格式逐项列出：
- 目标章节；
- 当前设计摘要；
- 建议改法；
- 直接证据；
- 对 `GFileData`、M1、依赖和测试的影响。

## 13. 未确认事项
列出仍需补充的源码、样例、运行验证或上游文档。

## 14. 证据索引
集中列出所有关键证据：
- `path/to/file:line`
- 符号名
- 该证据证明什么

六、停止条件

出现以下任一情况时停止扩展调查并报告，不得自行进入实现：

- 发现 OFT 实现与 `GFileData` 正式字段冲突；
- 发现需要修改 `GFileData`、reader 接口、依赖清单或 M1 验收标准；
- 发现候选 reader 只能通过编译或安装完整 OFT 才能确认；
- 缺少索引地图中指向的关键源码文件；
- 许可证或复制边界无法确认；
- 需要修改蓝图才能继续；
- 需要运行可能生成或覆盖文件的示例。

本轮验收条件：
- 对“Triangle 是否读取平衡文件”和“TokaMaker/OFT 是否已有 GFile reader”分别给出结论；
- 每项关键结论都有实际源码路径、符号和行号；
- 完成 `GFileData` 逐字段映射；
- 完成轻量化与依赖评估；
- 不修改任何文件；
- 不编写 LinkMesh reader 实现；
- 不修改技术蓝图；
- 将推断、已确认事实和未确认项明确分开。