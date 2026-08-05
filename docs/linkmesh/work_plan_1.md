# LinkMesh 下一阶段工作计划：OFT 高级网格能力侦察与真实求解验证

## 1. 阶段背景

LinkMesh 已完成以下主链：

- GFile/EQDSK 和 counted R-Z 二维边界输入；
- single-region OFT/Triangle 网格生成；
- Mesh2D；
- TRIMEG HDF5；
- M3D-C1 TXT 与 native SMB；
- PNG 几何自检。

`single_region + array_file` 已通过 EAST 生成侧验证。M3D-C1 多档 EAST 网格已交给组内成员进行真实时间推进，TRIMEG HDF5 已交给卢老师进行真实消费测试。

组内交付环境架构已经完成讨论，但共享目录、权限和正式发布环境需要等待老师确认，因此不占用当前 OFT 技术侦察主线。

## 2. 当前阶段目标

下一阶段不立即增加业务功能，而是回答三个问题：

1. OFT 26.6 是否支持在单一闭合二维区域内设置空间变化的网格尺度；
2. OFT 多区域网格的拓扑、区域标签和共享界面如何工作；
3. OFT 中还有哪些能力能够直接改善 LinkMesh 的边界获取、网格质量和真实求解适用性。

所有调查先形成直接源码和最小运行证据，再决定是否升级蓝图和实施业务代码。

## 3. 术语边界

必须区分：

- 全局尺度：整个区域使用一个 `dx`；
- 分区域尺度：不同 OFT Region 使用不同常数 `dx`；
- 静态局部加密：一次网格生成过程中，尺度随空间位置变化；
- 动态自适应：根据误差估计或求解结果反复调整网格；
- 磁面对齐：节点或单元方向与磁通面结构相关。

当前 LinkMesh 已支持全局尺度和固定区域常数尺度。

本阶段优先调查静态局部加密。动态自适应和磁面对齐只做能力定位，不进入实现。

二维任务中的外边界是闭合曲线，不是三维闭合曲面。

## 4. 工作流 A：单区域空间变密度调查

只读侦察 OFT 26.6 正式安装源码和 TOKAMAKER 参考源码，确认：

1. `gs_Domain`、`Region`、`Mesh` 和 `run_triangle` 支持哪些尺度参数；
2. `dx`、`dx_curve`、region seed 和 Triangle area constraint 的真实数据流；
3. 是否存在位置相关 size function、局部 refinement point、refinement region 或背景尺度场；
4. 是否存在网格生成后的 refinement、adaptation 或质量改善接口；
5. 相关能力是公共 API、私有接口、示例能力还是未接入代码；
6. 是否能在一个 single-region 外边界内实现局部加密，而不引入物理多区域语义。

最小运行探针至少比较：

- 单一全局 `dx` 基准；
- 中心或指定点附近局部加密；
- 边界附近局部加密；
- X-point 候选位置附近局部加密。

记录节点数、三角形数、面积分布、边长分布、最小角、长宽比、边界保持情况和运行警告。

## 5. 工作流 B：OFT 多区域调查

现有 nested 路径只能证明 OFT 和 Mesh2D 能生成、承载多个区域，不能证明 M3D-C1 多区域已经开放。

调查内容：

1. 多个 Region 是否共享同一组界面节点和边；
2. 界面两侧三角形是否形成严格 conforming topology；
3. `region_info`、`reg`、parent/child 和 annulus 的真实语义；
4. 是否支持相邻区域、嵌套区域、孔洞和多连通区域；
5. 各区域常数 `dx` 如何影响共享界面重采样；
6. 区域界面是否会产生重复点、裂缝、重叠单元或非流形边；
7. OFT warning 在多区域真实案例中的影响。

最小探针包括：

- 两个嵌套区域；
- 三个嵌套区域；
- 两个相邻区域；
- 不同区域使用显著不同 `dx`；
- 界面拓扑和区域 ID 自动检查。

## 6. 工作流 C：M3D-C1 C1 兼容性调查

必须区分：

- OFT 三角网格的拓扑共形性；
- SCOREC/PUMI geometric classification；
- M3D-C1 的 C1 有限元连续性；
- 物理区域界面是否允许场或导数跳跃。

只读调查 M3D-C1 和 SCOREC/PUMI 参考源码，回答：

1. M3D-C1 的 C1 基函数是否要求整个计算域属于一个 geometric face；
2. 多 geometric face 之间默认保持、降低还是中断 C1 连续性；
3. 多个 OFT region 是否可以只作为网格密度分区，最终仍分类到一个 M3D-C1 face；
4. 如果保留物理区域语义，M3D-C1 需要哪些 face、edge、loop 和 interface 标签；
5. 当前 TXT、M3DC1ModelSpec、classification 和 helper 哪些契约必须改变；
6. TRIMEG HDF5 不写 `region_ids` 时，多区域信息是否只可用于生成阶段。

不得通过简单删除或压平 `region_ids` 绕过正式契约。

## 7. 工作流 D：OFT 相关能力清单

只调查直接服务于 LinkMesh 的能力：

- GFile 和平衡数据读取；
- LCFS、第一壁和内部磁通面提取；
- X-point、磁轴和磁通坐标信息；
- 边界重采样和曲线尺度；
- 网格质量诊断；
- 局部尺度和 refinement；
- 多区域 Domain；
- 网格导出或转换；
- 对 LinkMesh 当前私有兼容接口的公共替代方案。

每项标记为：

- 已使用；
- 可直接使用；
- 需要最小探针；
- 需要蓝图升级；
- 与 LinkMesh 无关；
- 当前禁止。

不以“OFT 功能多”为理由把 LinkMesh建设成 OFT 通用前端。

## 8. 交付物

本阶段应输出三份只读侦察报告：

1. `OFT_26_6_Variable_Mesh_Density_Investigation.md`
2. `OFT_26_6_Multi_Region_Topology_Investigation.md`
3. `M3DC1_C1_Multi_Region_Compatibility_Investigation.md`

每份报告必须包含：

- 直接源码位置和调用链；
- API 签名和版本；
- 最小运行探针；
- 已确认事实；
- 未确认事项；
- 与当前蓝图的冲突；
- 候选架构；
- 是否建议进入实现。

## 9. 决策门槛

只有满足以下条件后才能批准局部加密实现：

- OFT 26.6 存在可复现能力；
- 不需要复制 Triangle 或 OFT 内部算法；
- 输出仍能形成合法 Mesh2D；
- 对 M3D-C1 和 TRIMEG 的 Writer 契约影响明确；
- 真实场景表明全局 `dx` 不足或局部加密具有明确收益。

只有满足以下条件后才能批准 M3D-C1 多区域：

- OFT 界面拓扑已验证；
- M3D-C1 C1 连续性和多 face 语义已由源码或维护者确认；
- M3DC1ModelSpec、TXT、classification 和 helper 的升级范围明确；
- 蓝图先完成更新；
- 单区域链路保持回归通过。

## 10. 并行真实验收

OFT 调查期间继续收集：

- EAST 不同密度网格的 M3D-C1 时间推进结果；
- 网格密度对稳定性、耗时和物理场平滑性的影响；
- TRIMEG 对新 HDF5 的读取和运行结果；
- 老师对 EQDSK 在 TRIMEG 网格流程中作用的说明。

真实求解结果用于判断局部加密和多区域是否确有必要。

## 11. 当前禁止事项

本阶段不得：

- 修改 OFT、M3D-C1 或 SCOREC/PUMI 参考源码；
- 实现第二网格生成引擎；
- 直接开放局部加密、自适应网格或磁面对齐；
- 直接开放 M3D-C1 多区域或多 face；
- 修改 Mesh2D、HDF5、TXT 或 SMB 契约；
- 通过区域标签数量推断 C1 兼容性；
- 为展示 OFT 功能而增加与真实工作流无关的功能。

## 12. 推荐顺序

1. 收集 EAST M3D-C1 和 TRIMEG 真实消费结果；
2. 侦察 OFT 单区域空间变密度能力；
3. 运行局部尺度最小探针；
4. 侦察并验证 OFT 多区域界面拓扑；
5. 调查 M3D-C1 C1 与多 face 语义；
6. 建立 LinkMesh 相关 OFT 能力清单；
7. 比较全局加密、局部加密和分区域加密的收益与复杂度；
8. 提交蓝图升级建议；
9. User 和老师确认后再实施最小功能；
10. 实施后分别进行 M3D-C1 和 TRIMEG 真实消费回归。