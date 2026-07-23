# LinkMesh M3 complete-11A OFT Region 重采样接口冲突核对报告

## 1. 文档定位

本报告是 LinkMesh M3 complete-11A 的只读核对成果，唯一目标是消除上一轮
M3 complete-11 实施前侦察中出现的证据冲突：

- 上一轮结论：进入 Triangle 前的真实离散外边界只能从 OFT `Mesh` 私有属性
  （`_resampled_points` / `_resampled_segments` / `_reg_seg_map`）恢复，触发停止条件。
- 冲突线索：`Region.get_resampled_points()` 可能直接提供某个 Region 的重采样点列，
  从而绕开 `Mesh` 私有 segment map。

本轮唯一核心问题：`Region.get_resampled_points()` 或等价方法能否直接、可靠、按正确
点序提供 artificial outer region 在进入 Triangle 前的真实离散边界。

本报告不实现业务代码、不修改测试、不修改蓝图/History/CONTEXT、不运行任何程序、
不访问 Mesh 私有属性实施功能。

## 2. 执行摘要

- `Region` 类与 `Region.get_resampled_points()` 在参考 `meshing.py` 中【直接定义证据】
  真实存在；它是不带前导下划线的公开命名方法，返回 `(np,2)` 点列，逐 segment 沿弧长
  按 `dx_curve` 重采样。
- **关键冲突点已定位**：`Mesh.__init__()` 在参考源码中【直接调用证据】**并未调用**
  `Region.get_resampled_points()`。`Mesh` 走的是一条**独立**的重采样路径
  （`Mesh._resampled_points` / `_resampled_segments`），与 `Region.get_resampled_points()`
  的结果不是同一份数据。
- 因此 `Region.get_resampled_points()` 返回的点列**不能被证明**与实际进入 Triangle 的
  `vertices` 逐值一致：真正进入 Triangle 的 `vertices` 来自 `Mesh._resampled_points`，
  而 `Mesh` 的重采样发生在 `Mesh.__init__` 内部（含点合并、共享边界处理、重编号、
  segment 方向翻转），`Region.get_resampled_points()` 不参与该路径。
- 最终裁决为**结论 C（接口不足）**（在参考快照层面）：`Region.get_resampled_points()`
  虽然存在且语义清晰，但它不是 Triangle 输入点列的来源，无法满足蓝图「进入 Triangle 前
  的、与最终 `vert` 精确吻合的有序离散外边界」契约。
- 上一轮停止条件**维持**。不解除。是否改用 `Mesh` 私有结构（方案 B）需 User 明确授权
  并承担版本耦合风险；或由 User 裁决改变 `outer_boundary` 语义来源（方案 C 数据源变体）。

## 3. 已读与跳过文件

已读（只读）：

- `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
  （`Region`、`Mesh`、`gs_Domain`、`run_triangle` 相关定义与调用）。
- `TOKAMAKER/OpenFUSIONToolkit/src/python/OpenFUSIONToolkit/TokaMaker/__init__.py`
  （版本暴露核对）。
- `src/linkmesh/mesher/oft_adapter.py`（LinkMesh 当前策略层与核心结构）。
- `src/linkmesh/mesh.py`（`Mesh2D.outer_boundary` 契约现状）。
- `LinkMesh_Architecture_Plan.md` v2.1（第 3.2、5 节契约）。

未读 / 跳过（避免读取整个 OFT 源码树）：

- OFT `_core.py`、`_interface.py`、`io.py`、`util.py` 的完整实现（仅在需要时参考签名，
  本轮未逐行阅读）。
- OFT 全部测试、示例、Fortran/C 源码、其余 Python 子模块。
- 服务器正式安装的 `openfusiontoolkit==26.6` 包（本轮无法访问，见第 10 节）。

## 4. 证据等级说明

本报告结论均按提示词第五节标注下列等级之一：
【直接定义证据】【直接调用证据】【实时 LinkMesh 证据】【参考快照证据】
【待安装版 OFT 26.6 核对】【待最小运行验证】【接口足够】【接口不足】
【版本耦合风险】【待 User 裁决】。

## 5. Region 接口核对（任务一）

文件：`TOKAMAKER/.../TokaMaker/meshing.py`；类：`Region`。

1. 构造函数签名：`Region.__init__(self, points, dx=None, dx_curve=None, angle_tol=30.0,
   sliver_tol=120.0, small_thresh=None, id=0, load_dict=None)`【直接定义证据】。
2. 保存的控制几何：`self._points`（边界控制点）、`self._segments`（按尖角切分的段，
   每段是 `self._points` 的索引列表）、`self._id`、`self._dx_vol`、`self._dx_curve`、
   `self._small_thresh`、`self._resampled_points`（初值 `None`）【直接定义证据】。
3. 参数语义：`points` 为闭合边界控制点 `[:,2]`；`dx` 为区域内目标网格尺度（存为
   `_dx_vol`）；`dx_curve` 为曲线重采样尺度（未给时等于 `dx`）【直接定义证据】。
4. `get_resampled_points()` 是否存在：**存在**，方法名为
   `Region.get_resampled_points(self)`【直接定义证据】。
5. 语义等价方法：无需另找，该方法即候选目标。
6. 是否带前导下划线：**否**，`get_resampled_points` 为公开命名（但其操作对象
   `self._points`、`self._segments`、`self._resampled_points` 均为下划线私有字段）
   【直接定义证据】。
7. 方法参数：仅 `self`【直接定义证据】。
8. 返回类型：`numpy.ndarray`【直接定义证据】。
9. 返回 shape：`(np,2)`，第 0 列 R、第 1 列 Z【直接定义证据】。
10. 返回结构：**单个**二维数组（内部把各 segment 的重采样点顺序 append 后一次性
    `numpy.asarray`），非多段数组、非索引映射【直接定义证据】。
11. 是否含原始控制点：**含**每段起点（`pts_out.append(pts_tmp[0,:])`），随后 append
    该段沿弧长插值的中间点【直接定义证据】。
12. 是否含 OFT 插入的重采样点：**含**（对每段按 `int(dl[-1]/self._dx_curve) >= 2` 决定
    是否用 `numpy.linspace` 沿弧长插入中间点）【直接定义证据】。
13. 是否重复闭合首点：**不显式重复首点**。方法逐段 append，每段只 append 该段起点与
    中间点，不 append 段末点；由于 `Region.__init__` 已将首尾近似重复点删除且 segment
    首尾相接，末点由下一段起点承接，最后一段回到首点索引 `0`——但方法只 append 段起点，
    故末尾不会显式重复第 0 点【直接定义证据；末尾闭合行为为【待最小运行验证】】。
14. 返回方向：继承 `self._points` 的原始输入方向；方法本身不做方向规范化
    【直接定义证据】。
15. 是否确定顺序：**是**（严格按 `self._segments` 顺序、每段按弧长升序）【直接定义证据】。
16. 是否逐 segment 独立重采样：**是**（`for segment in self._segments`）【直接定义证据】。
17. 重采样尺度：按 `self._dx_curve`（`int(dl[-1]/self._dx_curve)`）【直接定义证据】。
18. 注释/docstring/调用点说明：方法带简短 docstring「Get resampled points for bounding
    curve，@result Point list [np,2]」【直接定义证据】。
19. 公开 API 还是仅名称公开：命名上公开，但 OFT 未在 `__init__.py` 或文档中承诺其为稳定
    对外 API（`__all__` 仅暴露 `TokaMaker`）；操作对象为私有字段【参考快照证据】。
20. 当前源码是否有外部调用者：在参考 `meshing.py` 内，`get_resampled_points()` **未被
    `Mesh.__init__` 调用**（见第 7 节）；仅 `Region.get_in_point`/`check_in_poly`/`plot_*`
    使用 `self._resampled_points`，但这些路径的 `_resampled_points` 由 `Mesh.__init__`
    直接赋值而非通过 `get_resampled_points()` 触发【直接调用证据】。

**关键子结论（Region 层）**：`get_resampled_points()` 真实存在、语义清晰、返回单个有序
`(np,2)` 重采样点列，末尾不显式重复首点。但它属于「Region 返回点列」（提示词第五节第 5 类），
**不等于**「Mesh 全局合并后的 Triangle 输入点列」（第 6 类）。

## 6. add_polygon / add_rectangle 核对（任务二）

文件同上；类：`gs_Domain`。

1. `add_rectangle()` 是否创建四角：**是**，构造 `contour` 为 4 行
   `[-w/2,-h/2],[+w/2,-h/2],[+w/2,+h/2],[-w/2,+h/2]`，可选旋转后平移到 `(rc,zc)`
   【直接定义证据】。
2. 四角顺序/方向：左下→右下→右上→左上（在标准 R 右、Z 上系中为逆时针）【直接定义证据】。
3. `add_rectangle()` 是否返回 Region：**否**，它转调 `self.add_polygon(contour,name,
   parent_name)`，无返回值【直接定义证据】。
4. 新增 Region 保存位置：`add_polygon` 内 `self.regions.append(Region(contour,dx,
   dx_curve,angle_tol,sliver_tol,small_thresh,reg["id"]))`，即 `gs_Domain.regions`
   列表【直接定义证据】。
5. `add_polygon()` 是否返回 Region：**否**，无返回值（仅 append 并更新
   `reg["count"]`）【直接定义证据】。
6. 是否保存在公开容器：`self.regions` 无前导下划线，属命名公开列表【参考快照证据】。
7. Region 是否带名称/类型/ID：`Region` 对象本身只带整数 `_id`；名称/类型保存在
   `gs_Domain.region_info[name]`，`add_polygon` 用 `reg["id"]` 把 `region_info` 的 ID
   传给 Region【直接定义证据】。
8. 能否通过前后差异取得新 Region 引用：**能**（`add_rectangle`→`add_polygon` 调用前后
   `domain.regions` 长度 +1，末元素即新增 outer Region）【参考快照证据；【待最小运行验证】
   确认无并发/隐藏 append】。
9. 能否通过稳定名称取得 outer Region：**不能直接**。`Region` 对象不存名称，
   `region_info["OUTER"]["id"]` 存整数 ID，需用整数 ID 反查 `domain.regions` 中
   `region._id` 匹配——但提示词禁止写死区域 ID，且 `build_mesh()` 会重排 `_id`
   （见第 7 节 build_mesh 重编号）【直接定义证据】。
10. `build_mesh()` 前保存的 Region 引用构建后是否仍有效：Region 对象本身不被替换，
    但 `build_mesh()` 会**原地修改** `region._id`（`region._id = reg_reorder[...]`），
    并在 `Mesh.__init__` 中把 `region._resampled_points` 赋为**该 Region 在 Mesh 全局
    重采样后的子集**（`region._resampled_points = numpy.asarray(reg_points)`），
    因此引用有效但其 `_resampled_points` 语义在 build 后被 Mesh 改写【直接定义证据】。
11. 有壁/无壁 outer 创建方式是否一致：**一致**。两条路径都用
    `add_rectangle(rc,zc,w,h,name="outer")`→`add_polygon`（`build_oft_domain_from_gfile`
    实时代码）【实时 LinkMesh 证据】。
12. 是否存在不依赖整数 ID 的稳定识别：可用「创建前后 `domain.regions` 长度差异」在策略层
    捕获 outer Region 引用，属稳定且不依赖整数 ID 的方式【参考快照证据】。
13. LinkMesh 当前 `build_oft_domain_from_gfile()` 能否在创建时显式保存 outer Region 引用：
    **能**（策略层可在 `add_rectangle` 调用后取 `domain.regions[-1]`），但需注意
    `add_rectangle` 无返回值【实时 LinkMesh 证据】。
14. 若 API 不返回 Region 是否需改调用方式：需在策略层增加「捕获 `domain.regions[-1]`」
    的动作，属策略层结构小改，非 OFT 改动【参考快照证据】。
15. 是否改变默认网格行为：单纯捕获引用**不改变**网格行为（不改 dx、不改区域策略、
    不改矩形几何）【参考快照证据】。

## 7. Mesh 重采样调用链核对（任务三）

文件同上；类：`Mesh`。

1. `Mesh.__init__()` 是否调用 `Region.get_resampled_points()`：**否**。`Mesh.__init__`
   自建 `self._segments` 与 `self._resampled_segments`/`self._resampled_points`，通过内部
   逻辑对 `region._segments`、`region._points` 直接处理，未调用
   `Region.get_resampled_points()`【直接调用证据——此为消除冲突的核心事实】。
2. 调用发生时机：不适用（未调用）。
3. 对每个 Region 调用几次：0 次（`get_resampled_points` 未在 Mesh 路径出现）
   【直接调用证据】。
4. 结果如何保存：Mesh 自身的重采样点存入 `self._resampled_points`；对每个 Region 另把其
   在 Mesh 全局点中的子集赋回 `region._resampled_points`【直接定义证据】。
5. 是否进入 `_resampled_points`：Mesh 自建的 `self._resampled_points` 是 Triangle 输入点
   来源；它不是 `Region.get_resampled_points()` 的返回值【直接定义证据】。
6. `_resampled_segments` 如何建立：Mesh 在「Resample segments」段对 `self._segments`
   逐段沿弧长按 `dx` 用 `numpy.linspace` 插点，构造重采样段的点索引列表
   【直接定义证据】。
7. `_reg_seg_map` 如何建立：Mesh 在装配阶段记录每个 Region 用到的（可能带负号表示反向的）
   段索引列表【直接定义证据】。
8. 是否点去重：**是**，Mesh 用 `merge_thresh`（默认 1e-4）合并临近点，并做重编号
   （`reindex`）【直接定义证据】。
9. 是否合并不同 Region 共享边界：**是**（「Merging curve segments」/「partially
   overlapping」逻辑）【直接定义证据】。
10. 是否改变某 Region 自身点列坐标：Mesh 重采样点来自对 `_segments` 的独立插值，
    坐标由插值决定；`region._resampled_points` 被赋为 Mesh 全局点子集，可能因 merge/
    reindex 与 `Region.get_resampled_points()` 结果不同【直接定义证据】。
11. 是否改变点序：Mesh 有自己的段顺序与 `reindex`，`_reg_seg_map` 用负号表示某段反向
    使用，故 Region 视角的点序可能被 Mesh 翻转/重排【直接定义证据】。
12. 是否翻转 segment 方向：**是**，`_reg_seg_map` 中负索引表示反向遍历该段
    （`reversed(self._resampled_segments[-segment])`）【直接定义证据】。
13. 负 segment ID/负索引语义：负号表示「反向使用该重采样段」；在装配 `region._resampled
    _points` 时 `if segment < 0: tmp_pt_map = reversed(...)`【直接定义证据】。
14. Region 返回点列与 Mesh 全局点列关系：两者是**不同重采样过程**的产物——
    `Region.get_resampled_points()` 用 `_dx_curve` 逐段独立采样、不 merge、不 reindex；
    Mesh 用 `dx`（`region._dx_curve` 传入构造 `_segments` 时也参与，但走 Mesh 自己的
    linspace + merge + reindex）。二者点数、坐标、顺序都不保证一致【直接定义证据】。
15. 最外层不共享边界的矩形是否仍会被 Mesh 影响：即使 outer 矩形不与其他 Region 共享边，
    Mesh 仍会对其执行独立的 linspace 重采样、merge_thresh 去重与全局 reindex，
    并可能在 `_reg_seg_map` 中以反向段引用它；因此其在 `self._resampled_points` 中的
    坐标/顺序仍由 Mesh 决定，而非 `Region.get_resampled_points()`【直接定义证据】。
16. Region 方法结果能否视为最终 Triangle 输入点的有序子集：**不能被证明**。因为 Triangle
    输入点来自 `Mesh._resampled_points`（Mesh 路径），Region 方法结果来自另一条路径，
    二者只是「针对同一控制几何的两种重采样」，无源码保证逐值一致或子集关系
    【直接定义证据 + 接口不足】。
17. 若不能，具体差异：重采样尺度参数（`_dx_curve` vs Mesh 的 `dx`/段构造）、是否 merge、
    是否 reindex、是否反向段、末点闭合处理，均可能造成点数与坐标差异【直接定义证据】。
18. 是否必须读 `_reg_seg_map` 才能恢复完整 outer loop（在 Mesh 路径下）：**是**。要从
    `Mesh._resampled_points` 恢复「outer region 的有序闭环」，必须借助 `_reg_seg_map`
    （含负号方向语义）拼接对应段——这正是上一轮触发停止条件的私有结构【直接定义证据】。
19. 是否存在公开方法从 Mesh 取指定 Region 完整 loop：**未发现**。`Mesh.get_mesh()` 只返回
    `vertices/triangles/triangle_attributes`（Triangle 输出），无「按 Region 返回有序输入
    边界 loop」的公开方法【直接调用证据】。
20. 若必须用私有结构，不可避免原因：Triangle 输入点列的唯一权威来源是
    `Mesh._resampled_points` + `_resampled_segments` + `_reg_seg_map`，OFT 未对外暴露
    「某 region 的有序 Triangle 输入边界」，故 Mesh 路径下无法回避私有结构【直接定义证据】。

**关键子结论（Mesh 层）**：`Region.get_resampled_points()` 与 Mesh 实际用于 Triangle 的
重采样是**两条独立路径**。这直接解释并消除了上一轮的证据冲突——方法名存在（第 2 类，
方法名存在但用于 Triangle 的语义不成立），但它不是 Triangle 输入点列来源。

## 8. Triangle 输入组装核对（任务四）

文件同上；`Mesh.get_mesh()` 与 `run_triangle()`。

1. Triangle 输入 `vertices` 来源：`alpha = dict(vertices=self._resampled_points,
   segments=resampled_flat, regions=self._reg_defs)`【直接定义证据】。
2. 是否直接来自 `_resampled_points`：**是**（Mesh 私有属性）【直接定义证据】。
3. Triangle 输入 `segments` 来源：`resampled_flat` 由 `self._resampled_segments` 展开
   相邻点对得到【直接定义证据】。
4. Region 重采样点是否逐值进入 `vertices`：**无证据**。进入 `vertices` 的是
   `self._resampled_points`（Mesh 路径），非 `Region.get_resampled_points()` 结果
   【直接定义证据 + 接口不足】。
5. Mesh 是否在传入 Triangle 前修改坐标：Mesh 的重采样即坐标生成过程；传入前坐标即
   `_resampled_points`，无额外二次修改，但该坐标本身由 Mesh 路径产生【直接定义证据】。
6. Triangle 输入前是否还有额外重采样：Mesh 路径内已完成重采样；`get_mesh()` 只做段展开，
   无额外重采样【直接定义证据】。
7. Triangle 输出 `pts` 与输入 `vertices` 关系：`run_triangle` 用选项 `pqaAzQ` 调用；
   Triangle 通常保留输入点并可能追加 Steiner 点，但**当前静态源码不足以证明**输入边界点
   在输出中的索引与保留细节【参考快照证据 +【待最小运行验证】】。
8. Steiner 点出现阶段：Triangle 执行阶段（`oft_triangulate`）【直接定义证据】。
9. 输入 boundary vertices 是否保留在输出 `pts`：**未由静态源码证明**（依赖 Triangle 选项
   与库行为）【待最小运行验证】。
10. 当前源码是否足以证明第 9 点：**不足**，需运行验证【接口不足 + 待最小运行验证】。
11. outer Region 返回点列是否与 Triangle 输入 outer boundary 坐标逐值一致：**不能证明**
    （Region 方法与 Mesh 路径不同，见第 7 节）【接口不足】。
12. 若仅集合一致但顺序不同能否恢复：即使坐标集合偶然一致，恢复正确有序 outer loop 仍需
    `_reg_seg_map` 私有结构，回到停止条件【直接定义证据】。
13. 若 Region 返回多段如何拼接：`Region.get_resampled_points()` 已返回单数组（无需拼接），
    但该数组不是 Triangle 输入来源，拼接问题在 Region 层不适用；在 Mesh 层拼接需私有 map。
14. 拼接是否需删段间重复端点：Region 方法内部已按「每段只 append 起点+中间点」避免段间
    重复；Mesh 层则用 merge/reindex 处理【直接定义证据】。
15. 闭合末点是否需删除：Region 方法末尾不显式重复首点（第 5 节第 13 点）【待最小运行验证】。
16. 拼接逻辑属「使用 OFT 返回数据」还是「复制 OFT 重采样」：若在 Mesh 层用 `_reg_seg_map`
    自行拼接 loop，涉及理解并重走 OFT 的段方向与重编号语义，接近「解析私有结构」而非纯
    「使用返回数据」【直接定义证据 + 版本耦合风险】。
17. 能否用不超过一个局部规范化步骤得到 `(B,2)`：**在 Region 方法层可以**（其返回已是
    `(np,2)`，只需方向规范化 + 末点确认）；**但该来源语义不符 Triangle 输入契约**
    【接口不足】。
18. 该规范化是否需私有属性：Region 方法返回本身不需再读私有属性；但要保证「与 Triangle
    输入一致」则必须转向 Mesh 私有属性【直接定义证据】。
19. 是否存在浮点坐标变换/复制：Region 方法内部有插值（浮点新点生成），属 OFT 内部行为；
    LinkMesh 侧只需复制返回数组【直接定义证据】。
20. 能否证明 `B <= nvert_ex`：无法从静态源码证明具体关系；两 TRIMEG 样例（蓝图第 5 节）
    显示 `nbcRZ <= nvert_ex`，但那是最终 `vert` 匹配下的经验，不能移植为 Region 方法结果
    的保证【参考快照证据 + 待最小运行验证】。

## 9. LinkMesh 当前接口核对（任务五）

文件：`src/linkmesh/mesher/oft_adapter.py`【实时 LinkMesh 证据】。

1. `build_oft_domain_from_gfile()` 当前返回：已构造但未 `build_mesh()` 的 `gs_Domain`，
   并附加私有属性 `_linkmesh_outer_boundary`。
2. 是否只返回 domain：返回 domain（携带私有属性）。
3. 是否有能力同时返回 outer Region/预构建边界：当前通过私有属性 `_OUTER_BOUNDARY_ATTR`
   附加边界数据，未直接返回 Region 引用。
4. 修改返回类型是否破坏公开接口/测试：`generate_mesh` 与 `test_oft_adapter.py` 依赖当前
   「返回 domain」语义；改为返回元组会破坏调用者与测试。宜保持返回 domain。
5. 能否保持返回 domain 同时保存 boundary：**能**（现已用私有属性附加）。
6. 当前是否用 `_linkmesh_outer_boundary` 私有附加属性：**是**（`_OUTER_BOUNDARY_ATTR =
   "_linkmesh_outer_boundary"`）。
7. 该属性目前保存四角还是重采样点：**保存人工矩形四角**（`_make_clockwise_rectangle_
   boundary` 生成的 4 点），这正是 `71fe09f` 的错误来源。
8. `mesh_from_oft_domain(domain)` 如何提取：`_extract_prebuild_outer_boundary(domain)`
   读取该私有属性并 `copy=True` 复制，注入 `Mesh2D.outer_boundary`。
9. 通用核心是否应猜测 outer Region：**不应**（蓝图要求核心通用、不写死区域语义）。
10. 是否应由策略层显式准备并传递：**是**，更符合蓝图职责划分。
11. 三层接口是否允许增加可选参数：可在 `mesh_from_oft_domain` 增加可选参数或继续用
    domain 私有属性传递；两者都不破坏现有位置参数调用。
12. 影响最小的候选改法：保持「策略层附加、核心读取」结构，仅**更换附加数据的来源**
    （从四角改为真实离散边界）。
13. 最符合蓝图的候选改法：策略层显式捕获真实离散 outer boundary 并传递，核心不猜测。
14. 需蓝图更新的改法：若最终改用 Mesh 私有结构或改变 outer_boundary 语义来源，需蓝图更新
    与 User 授权。
15. 能否不改 OFT 实现：能（LinkMesh 侧改造）。
16. 能否避免访问 Mesh 私有属性：**在 Mesh 路径下不能**（见第 7/8 节）；只有当 User 接受
    「用 Region 方法结果作为 outer_boundary」这一语义时才可避免，但那不满足「与 Triangle
    输入一致」的严格契约。
17. 能否避免复制重采样算法：能（无论方案 A 或 B，均不应把 OFT 弧长插值逻辑抄进 LinkMesh）。
18. 有壁/无壁能否共用实现：能（两路径 outer 均由 `add_rectangle(name="outer")` 创建）。
19. 通用假 Domain 单元测试如何保留：现有 `FakeDomain`/`RelabelDomain` 与私有属性注入测试
    可保留；若改数据源，只需更新 outer boundary 相关断言，核心 N 区域测试不受影响。
20. 无法可靠实现时的阻塞点：**阻塞点 = 无公开接口返回「outer region 的 Triangle 输入前
    有序离散边界」**；唯一权威来源在 `Mesh` 私有结构。

## 10. 参考快照与 OFT 26.6 版本边界（任务六）

1. 参考 `meshing.py` 是否含版本标识：文件头 docstring 有 `@date May 2023`、
   `SPDX-License-Identifier: LGPL-3.0-only`，**无明确语义版本号**【参考快照证据】。
2. `__init__.py` 是否暴露版本：`TokaMaker/__init__.py` 仅 `__all__ = ["TokaMaker"]`，
   **未暴露 `__version__`**【直接定义证据】。
3. CMake/README/文件头能否确认版本：本轮读取的文件均无 `26.6` 语义版本；`meshgen`
   `CMakeLists.txt`/`readme` 属 M3DC1，非 OFT 版本来源【参考快照证据】。
4. 是否有证据证明快照 == `openfusiontoolkit==26.6`：**无**【参考快照证据 + 待安装版
   OFT 26.6 核对】。
5. 只能标记「参考快照证据」的结论：第 5–8 节所有关于 `Region`/`Mesh`/`get_mesh` 具体
   实现细节的结论，其「与服务器安装版一致性」均为【待安装版 OFT 26.6 核对】。
6. 必须在服务器重新核对的结论：`Mesh.__init__` 是否调用 `Region.get_resampled_points()`；
   `get_mesh()` 的 `alpha['vertices']` 来源；`_reg_seg_map` 负号语义；Triangle 是否保留
   输入边界点。
7. 服务器最少检查：`Region`、`Mesh`、`gs_Domain` 三类的相关方法源码与签名。
8. 是否只需 introspection：主要结论可用 `inspect.getsource` / `inspect.signature`
   静态确认，不必运行 Triangle【待安装版 OFT 26.6 核对】。
9. 是否需读安装包 `meshing.py`：需（用 `inspect.getsourcefile` 定位安装路径后只读查看）。
10. 是否需打印 `getsourcefile`/`signature`：建议打印以确认版本一致性，不修改环境。
11. 哪些核对不改环境：纯 `inspect` 静态读取、打印源文件路径与方法源，均只读。
12. 版本不一致停止条件：若安装版 `Mesh.__init__` 调用关系或 `get_mesh` 输入来源与本报告
    不符，立即停止并报告差异，不得沿用参考快照结论。

## 11. 方案 A/B/C/D 对照（任务七）

方案 A（使用公开/稳定的 Region 重采样方法）
- 直接源码证据：`get_resampled_points()` 存在【直接定义证据】。
- 是否访问私有属性：方法调用本身不需；但要保证与 Triangle 输入一致则需 Mesh 私有属性。
- 是否复制重采样算法：调用 OFT 方法不算复制。
- 是否与 Triangle 输入逐值一致：**不能证明**（Region 路径 ≠ Mesh 路径）【接口不足】。
- 是否需服务器核对：是【待安装版 OFT 26.6 核对】。
- 是否满足蓝图：**不满足**（蓝图要求与最终 `vert` 精确吻合的 Triangle 输入前边界）。
- 是否解除停止条件：**不解除**。

方案 B（使用 Mesh 私有重采样结构 `_resampled_points`/`_resampled_segments`/`_reg_seg_map`）
- 是否不可避免：在「与 Triangle 输入一致」的严格契约下，**是**唯一权威来源。
- 私有语义是否被源码完整确认：主要语义（负号=反向、merge、reindex）由参考快照确认，
  但服务器一致性未确认【直接定义证据 + 待安装版 OFT 26.6 核对】。
- 版本耦合风险：**高**【版本耦合风险】（下划线私有结构可能随 OFT 版本变化）。
- 是否需 User 明确批准：**是**【待 User 裁决】（CONTEXT 与提示词禁止把私有属性当稳定接口）。
- 应加防御性失败：属性缺失/形状异常/无法恢复单一闭环时明确 raise，禁止回退四角或
  `idxevert`。
- 是否需蓝图记录风险：是（应在蓝图记录私有依赖与版本风险）。

方案 C（直接使用原始 GFile / array_file 点列作为 outer_boundary）
- OFT 是否仍重采样：**是**（Mesh 仍会重采样该轮廓）。
- 是否等同 Triangle 输入：**否**（原始点列 ≠ 重采样后 Triangle 输入）。
- 结论：对 `artificial_outer` 矩形语义**不符当前蓝图**；但对 boundary source 语义变体
  （由 User 重新定义 `outer_boundary` = 传入生成器的原始有序边界，接受其与最终 `vert`
  不逐值吻合）属【待 User 裁决】的语义变更，需蓝图修订，**本轮不推荐擅自采用**。

方案 D（LinkMesh 自行复刻 OFT 重采样）
- 违反唯一 OFT/Triangle 底座与「不复制 OFT 算法」纪律。
- **禁止**。

裁决：
- 推荐方案：无「立即可实施且满足严格蓝图」的方案；在严格契约下**方案 B**是唯一技术可行
  路线，但**必须先经 User 授权私有依赖 + 服务器 OFT 26.6 核对**。
- 备选方案：方案 C 数据源语义变体（需 User 裁决改蓝图）。
- 禁止方案：方案 D；以及方案 A 冒充「Triangle 输入一致」。
- 是否解除上一轮停止条件：**否**。

## 12. 最终三选一裁决

选择 **结论 C：接口不足**（在满足「与 Triangle 输入/最终 `vert` 精确吻合」严格蓝图契约的
前提下），叠加 **结论 B 的核对要求**（任何后续推进都必须先在服务器安装版 OFT 26.6 上核对）。

理由（直接源码证据）：
- `Region.get_resampled_points()` 真实存在，但 **`Mesh.__init__` 未调用它**；Triangle 输入
  `vertices` 来自 `Mesh._resampled_points`（独立路径）。
- 因此 Region 方法结果**不能被证明**等于 Triangle 输入 outer boundary，也无法据此满足
  「与最终 `vert` 精确吻合」的 TRIMEG 契约。
- 要取得权威的 Triangle 输入前有序 outer loop，必须解析 `Mesh` 私有结构（含
  `_reg_seg_map` 负号方向语义），即回到上一轮停止条件。

输出：
- **保持停止条件**，不恢复上一轮业务编辑。
- 是否需 User 授权私有接口：**需**（方案 B 前置）。
- 是否触发蓝图修订：若采用方案 B 需在蓝图记录私有依赖与版本风险；若采用方案 C 变体需
  修订 `outer_boundary` 语义来源。二者均【待 User 裁决】。

## 13. 后续实现草案（仅数据流/接口层，条件性）

以下草案**仅在 User 批准方案 B 且服务器 OFT 26.6 核对通过后**才可执行；本轮不实现。

1. outer Region 创建层：仍在策略层 `build_oft_domain_from_gfile()`，保持
   `add_rectangle(name="outer")`，不改区域策略与 dx。
2. 引用获取：策略层在 `add_rectangle` 后捕获 `domain.regions[-1]`（不写死整数 ID）。
3. 重采样方法调用时机：**在 `build_mesh()` 之后**，从 `domain.mesh` 私有结构读取；
   因为 Triangle 输入点列（`_resampled_points`）在 `Mesh.__init__` 期间才生成。
4. 调用位置：`build_mesh()` 之后（与上一轮「build 前读取」相反——这是本报告修正点）。
5. 规范化为 `(B,2)`：借 `_reg_seg_map` 拼接 outer region 对应段（含负号反向），
   映射到 `_resampled_points`，得有序闭环点列。
6. 删除显式闭合重复点：拼接时对段间共享端点去重，末尾不重复首点。
7. 转顺时针：用带符号闭合面积判定，必要时整体反转。
8. 独立复制：`np.array(..., copy=True)` 存入 `Mesh2D.outer_boundary`。
9. 显式传递：策略层将结果通过显式参数或 domain 私有属性交给 `mesh_from_oft_domain`；
   核心不猜测 outer Region。
10. 避免核心猜测：核心只接收已准备好的 boundary，不自行判定哪个是 outer。
11. 保持公开接口兼容：`build_oft_domain_from_gfile` 仍返回 domain；`generate_mesh`
    组合不变。
12. 必须先写的测试：Region/Mesh 私有结构解析的单元测试（用受控假对象模拟
    `_resampled_points`/`_reg_seg_map`）、四角不能通过的回归测试、Steiner 点隔离测试。
13. 必须服务器验证的行为：`Mesh.__init__` 调用关系、`get_mesh` 输入来源、`_reg_seg_map`
    负号语义、Triangle 是否保留输入边界点、`B` 与 `nvert_ex` 关系、与最终 `vert` 逐值吻合。
14. 防御性失败点：私有属性缺失/结构变更/无法恢复单一闭环/方向或面积退化时 raise，
    禁止回退四角或 `idxevert`。
15. 为何不复制 OFT 算法：仅**读取** OFT 已生成的 `_resampled_points` 并按 `_reg_seg_map`
    拼接顺序，不重走弧长插值；插值仍由 OFT 完成。

## 14. 服务器最小只读核对清单

在服务器 `linkmesh` 环境（OFT 26.6）执行以下**只读** Python introspection（不运行
Triangle、不改环境、不写文件）：

1. 定位安装版源文件：`inspect.getsourcefile(gs_Domain)`、`inspect.getsourcefile(Mesh)`、
   `inspect.getsourcefile(Region)`。
2. 打印签名：`inspect.signature(Region.__init__)`、`inspect.signature(gs_Domain.add_
   rectangle)`、`inspect.signature(gs_Domain.build_mesh)`。
3. 确认 `hasattr(Region, "get_resampled_points")` 及其源码
   `inspect.getsource(Region.get_resampled_points)`。
4. 关键核对：`inspect.getsource(Mesh.__init__)` 中是否出现
   `get_resampled_points` 调用（预期**不出现**）。
5. 核对 `inspect.getsource(Mesh.get_mesh)` 中 `alpha` 的 `vertices` 是否为
   `self._resampled_points`。
6. 核对 `_reg_seg_map` 负号反向逻辑是否与本报告一致。
7. 记录 OFT 包路径与（若可得）`OpenFUSIONToolkit.__version__` 或 pip 元数据版本。

停止条件：上述任一结论与本报告参考快照不符时停止，报告差异，不沿用快照结论。

## 15. 仍未确认事项

- 服务器安装版 OFT 26.6 是否与参考快照的 `Mesh`/`Region`/`get_mesh` 实现一致
  【待安装版 OFT 26.6 核对】。
- Triangle 选项 `pqaAzQ` 下输入边界点是否全部保留在输出 `pts`、以及其索引/顺序
  【待最小运行验证】。
- `Region.get_resampled_points()` 末尾闭合的确切行为（是否任何情况下都不重复首点）
  【待最小运行验证】。
- 方案 B 中 `_reg_seg_map` 拼接能否在所有有壁/无壁真实 GFile 上稳定恢复单一 outer 闭环
  【待最小运行验证】。
- User 是否授权依赖 OFT `Mesh` 私有结构，或是否改变 `outer_boundary` 语义来源
  【待 User 裁决】。

## 16. 完成声明

- 本轮只修改 `m3_complete11a_report.md`；
- 未修改 LinkMesh 业务源码或测试；
- 未修改蓝图、History、CONTEXT 或 Project_Tree；
- 未修改 OFT/TokaMaker 参考源码；
- 未创建其他文件；
- 未运行 OFT、Triangle、LinkMesh 或测试；
- 未访问 Mesh 私有属性实施功能（仅做只读源码语义核对，未据此实现任何功能）；
- 未从 `idxevert` 反推 `outer_boundary`；
- 未使用人工矩形四角冒充重采样边界；
- 未复制 OFT 重采样算法；
- 未执行 Git 提交；
- M3 complete-11 仍保持 PENDING CORRECTION AND VALIDATION，等待本报告验收及必要的
  服务器 OFT 26.6 核对。
