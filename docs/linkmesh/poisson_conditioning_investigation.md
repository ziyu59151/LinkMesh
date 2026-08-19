# Poisson P1 刚度矩阵条件诊断：前置依赖停止报告

## 1. 调查状态

- 调查状态：**REVISED DESIGN / IMPLEMENTATION PENDING**
- Poisson benchmark：**USER-APPROVED / NOT IMPLEMENTED**
- 稀疏条件数估算方法：**DEPENDENCY-FREE LANCZOS / DESIGNED / NOT IMPLEMENTED**
- 源码、测试、真实矩阵和 quality plot 信息框：**NOT IMPLEMENTED / NOT RUN**
- 本轮未修改业务源码、测试、依赖、CLI、配置、`Mesh2D`、Writer、Plotter、
  mesh quality、refinement、helper、OFT/Triangle、native ABI、目标格式或 work plan。

## 2. 修订后的正式方案

本项目不新增 SciPy 或其他运行依赖。后续实现使用现有 NumPy 与 Python 标准库，
并在独立窄职责模块 `src/linkmesh/poisson_conditioning.py` 中提供仅服务于该
benchmark 的内部数据结构。

固定 benchmark 为单位扩散系数二维连续三节点线性三角形有限元：

```text
-Delta u = f
```

每个最终 `Mesh2D` 节点对应一个标量自由度。由最终三角形拓扑提取无向 edge incidence：
incidence=1 的节点施加齐次 Dirichlet，incidence=2 的边（包括 Region interface）
保持普通内部边，incidence>2 继续视为非流形错误。不得仅依赖 `outer_boundary` 坐标，
也不得通过浮点坐标近邻猜测边界节点。右端项不属于本 benchmark。

后续实现可使用以下内部结构：

- P1 局部刚度矩阵解析组装；
- COO-like triplets；
- 合并重复项；
- CSR-like `row_ptr`、`col_idx`、`values`；
- 稀疏 matrix-vector multiplication；
- Dirichlet 自由度消除后的对称 `K_ff`。

该结构不是 LinkMesh 公共稀疏矩阵 API，不修改 `Mesh2D`，不构造生产规模 dense
矩阵，不显式计算逆，不实现通用稀疏矩阵库。

条件数使用 dependency-free Lanczos：

1. 以确定性初始向量启动；
2. 通过稀疏 matrix-vector multiplication 迭代；
3. 将 `K_ff` 投影为较小的对称三对角矩阵 `T_m`；
4. 只使用 NumPy `eigvalsh(T_m)` 获取 Ritz 值；
5. 取最大和最小正 Ritz 值；
6. 计算：

```text
condition_estimate = lambda_max_estimate / lambda_min_estimate
```

实现必须固定并记录初始向量或随机种子、最大阶数、收敛容差、最大迭代次数、Ritz
值稳定性或残差检查，以及有限精度下的重正交策略。必须区分 `converged`、
`not_converged` 和 `failed`，未收敛或无效 Ritz 值时不得伪造条件数。禁止使用
`numpy.linalg.cond` 处理全局矩阵、SciPy `eigsh`/`splu`/`onenormest`、完整特征谱、
显式逆和预条件器。

报告同时包含原始条件数与：

```text
dof_normalized_condition = condition_estimate / N_free
```

该指标仅用于相同计算域、benchmark、边界条件、P1 离散和 Lanczos 设置之间的相对
比较，不是新的矩阵条件数，也不是严格不变量。必须同时报告两者，不设置通用阈值，
不用于不同 PDE、装置、边界条件或有限元阶次之间的绝对排名。

quality plot 的 Q 着色保持不变：`Q=0` 红、`Q=0.5` 蓝、`Q=1` 绿，normalization
固定 `[0,1]`。条件数不映射为逐 triangle 颜色，也不与 Q 合并为综合评分。只有请求
`--quality-plot` 时才执行 benchmark，并在信息框中显示 benchmark 名称、free DOFs、
matrix NNZ、Ritz 值、两个条件指标、estimator 名称和状态；未请求时不增加计算成本。
该设计不新增 CLI/TOML 字段，也不改变现有 `--plot`。

至少需要记录的报告字段包括 benchmark name、finite element、boundary condition、
total nodes、Dirichlet DOFs、free DOFs、matrix NNZ、两个 Ritz 值、raw condition
estimate、DOF-normalized indicator、Lanczos iterations、tolerance、convergence
status 和 failure stage/reason。

## 3. 直接证据

### 2.1 实时仓库依赖事实

当前 `requirements.txt` 明确定义：

- `numpy>=1.24.0`
- `h5py>=3.8.0`
- `matplotlib>=3.7.0`
- `openfusiontoolkit==26.6`
- `pytest>=7.0.0`

其中没有 `scipy`，也没有通过该文件锁定 Python 版本。

因此，基于本轮获准读取的实时依赖文件，只能得出：

1. SciPy 当前不是 LinkMesh 在 `requirements.txt` 中声明的正式运行依赖。
2. 当前不存在可核对的最低 SciPy 版本约束。
3. 无法把 `scipy.sparse`、`scipy.sparse.linalg.eigsh`、shift-invert、
   `splu`、`LinearOperator` 或 `onenormest` 写成当前正式支持能力。
4. 即使某个开发或服务器环境碰巧安装 SciPy，也不能将环境偶然状态提升为项目依赖
   契约。
5. 在没有版本下界和代表性运行证据时，不能正式锁定 spectral `cond2` 或 one-norm
   estimator 的生产实现。

这触发 User 指定的停止条件：

> SciPy 不是当前正式依赖或版本无法支持候选方法时，停止并报告。

### 2.2 冲突的实施前提

拟议实现需要稀疏矩阵组装、稀疏 LU 和迭代特征值估算。NumPy 本身不提供对应的通用
稀疏矩阵、SuperLU 或 ARPACK 接口。若不声明 SciPy，后续实现只能：

- 新增其他外部稀疏库；
- 自行实现稀疏矩阵、分解或特征值算法；
- 或依赖未声明的环境包。

三种做法都违反当前任务的依赖纪律、最小实现边界或停止条件。

## 3. 已确认但未落入正式蓝图的方向

以下内容是 User 已批准的产品方向，但本报告不把它们提升为已完成实施契约：

- benchmark 为单位扩散系数二维 P1 Poisson：
  `-Δu=f`；
- 全部 final `Mesh2D` 拓扑外边界施加齐次 Dirichlet；
- 内部 Region interface 保持普通共形内部边；
- 使用全局连续三节点线性三角形 P1 空间；
- 不使用轴对称 R 权重、材料系数、各向异性、高阶单元或预条件器；
- 不组装生产规模 dense 矩阵，不计算完整特征谱，不显式构造矩阵逆；
- 同时报告 raw condition estimate 与
  `estimated_condition / N_free`；
- DOF 归一化指标不是矩阵条件数，也不是严格不变量；
- 不建立通用 pass/fail 阈值；
- 条件摘要未来进入现有 Shape quality Q plot 信息框，但不得改变逐 triangle Q
  颜色、固定 `[0,1]` normalization 或 colorbar；
- benchmark 不代表 TRIMEG、M3D-C1 或其他下游生产矩阵。

由于依赖前提未成立，以下事项保持 **PENDING**：

- spectral `cond2` 与 LU + one-norm 两种候选的最终裁决；
- SciPy API 的最低受支持版本；
- shift-invert 的固定容差、最大迭代数、初始向量和收敛规则；
- 数万自由度代表性 Case 的 LU fill-in、峰值内存和运行时间；
- quality plot 自动执行 benchmark 是否适合正式产品；
- `PoissonConditioningReport` 的最终字段；
- 后续测试矩阵和真实验收状态。

## 4. 已完成的 User 裁决

User 已明确：

- 项目不新增 SciPy；
- 不引入其他稀疏矩阵库；
- 不建立通用条件数 pass/fail 阈值；
- 原始条件数和 `condition / N_free` 均需报告；
- 条件诊断只用于相同研究问题中不同网格配置的比较；
- quality plot 保持 Q 颜色和 `[0,1]` normalization；
- 不加入预条件器；
- 该 benchmark 不代表 TRIMEG、M3D-C1 或下游求解器真实矩阵。

后续实现仍需单独授权源码和测试修改；本轮仅完成文档方案修订。

继续设计前，需要 User 在独立依赖变更任务中明确批准以下二选一方案之一。

### 方案 A：批准 SciPy 为正式运行依赖

至少需要明确：

1. 将 SciPy 加入正式依赖契约。
2. 批准一个经过目标 Python、Linux Release 和服务器环境核对的最低版本。
3. 允许后续只读核对该版本的官方 API 文档或已安装包元数据。
4. 允许在代表性 final `Mesh2D` 上执行小型方法探针，比较：
   - `eigsh` 最大特征值与 shift-invert 最小特征值的 spectral `cond2`；
   - `splu`、`LinearOperator` 与 `onenormest` 的 estimated `cond1`；
   - 收敛、确定性、LU fill-in、峰值内存和耗时。
5. 方法探针通过后再由 User 裁决正式 estimator。

建议优先调查 spectral `cond2`，因为它与
`κ₂(K_ff) ~ C h⁻²` 及 `N_free ~ C_domain h⁻²` 的归一化推导直接一致；但在依赖版本
和代表性规模探针完成前，本报告不把该建议写成已锁定实现。

### 方案 B：不增加 SciPy

若继续禁止新增依赖，则需要 User 明确撤回或重新定义当前稀疏条件估算目标。当前不批准
LinkMesh 自行实现稀疏 LU、Lanczos、ARPACK 替代品或矩阵逆估算器，也不批准引入另一
个未声明的稀疏库。

## 5. 后续最小权限需求

若 User 批准方案 A，下一轮至少需要：

- 允许修改 `requirements.txt`，加入经核对的 SciPy 版本约束；
- 若项目实际安装依赖还由其他文件定义，提供该文件的只读内容；
- 允许只读核对目标 SciPy 版本的官方 API 与目标服务器安装事实；
- 允许后续单独申请业务源码和测试修改权限。

当前无需修改 `Mesh2D`、Writer、目标格式、helper、OFT/Triangle 或 native ABI，
也不需要新增公开 CLI/TOML 字段。

## 6. 实时 Mesh2D 与 quality plot 只读复核

### 6.1 Mesh2D 与拓扑边界

实时 `src/linkmesh/mesh.py::Mesh2D` 提供：

- `nodes`：约定 shape `(N,2)`，坐标为 `[R,Z]`；正式数据契约为
  `float64`；
- `triangles`：约定 shape `(T,3)`，内部使用 0-based 整数节点索引；
- `region_ids`：shape `(T,)`，保存每个 triangle 的 OFT 最终 Region ID；
- `outer_boundary`：可选 `(B,2) float64` 有序最外层输入几何边界，顺时针、
  隐式闭合，不包含 Triangle 后续插入的全部边界 Steiner nodes。

因此，`outer_boundary` 不能直接充当 Poisson Dirichlet 自由度集合。实时
`Mesh2D.triangles` 足以确定性构造每个 triangle 的三条无向边并统计 incidence：

- incidence `=1`：final mesh 的拓扑外边界 edge；
- incidence `=2`：普通内部 edge，包括共形 Region interface；
- incidence `>2`：non-manifold，应作为诊断失败。

incidence `=1` edges 的全部端点可可靠形成齐次 Dirichlet node 集合，无需修改
`Mesh2D`、增加 marker 字段或进行浮点坐标近邻猜测。Region ID 不参与外边界判定，
所以内部 Region interface 不会被误作 Dirichlet 边界。

### 6.2 final Mesh2D 到 quality plot 的实时调用链

实时 `src/linkmesh/cli.py` 已确认：

- 根命令先生成 initial mesh，再完成可选 local refinement，并把
  `refinement_result.mesh` 作为 final `Mesh2D`；
- `regions generate` 先生成 initial N-region mesh，再完成 transition/local
  combined refinement，并把 `refinement_result.mesh` 作为 final `Mesh2D`；
- 两条路径均在 `quality_plot_path` 非空时，基于同一个 final `Mesh2D` 调用
  `calculate_triangle_shape_quality(mesh)`，随后调用
  `plot_triangle_shape_quality(mesh, triangle_shape_quality, path)`；
- quality plot 并不总是伴随完整 `calculate_mesh_quality()` 报告：完整报告当前只在
 相应 verbose 条件成立时计算，而逐 triangle Q 在请求 quality plot 时独立计算；
- 实时 Plotter 使用固定 `Q=0 red / Q=0.5 blue / Q=1 green` 连续颜色映射和
  `Normalize(vmin=0.0, vmax=1.0)`。

因此，未来“请求现有 quality plot 时才计算 Poisson benchmark；未请求时无新增成本”
在当前编排结构上可表达，不需要新增公开 CLI/TOML 字段，也不要求修改 `Mesh2D`、
Writer、refinement、helper、OFT/Triangle、native ABI 或目标格式。后续若获准实施，
Plotter 只能接收已经计算完成的不可变 Poisson report 并显示信息框，不能组装矩阵、
执行分解或估算特征值。

## 7. 蓝图冲突与停止裁决

### 7.1 冲突位置

当前 `LinkMesh_Architecture_Plan.md` v5.8 没有把 SciPy 定义为正式运行依赖，也没有
定义 Poisson conditioning 模块、估算器版本下界或稀疏分解资源边界。与此同时，
实时 `requirements.txt` 不含 SciPy。

因此，把以下任一内容现在写成正式、可实施的蓝图契约都会超出直接证据：

- 锁定 `scipy.sparse` 的生产组装格式；
- 锁定 `eigsh`、shift-invert、`splu`、`LinearOperator` 或 `onenormest`；
- 宣称当前最低 SciPy 版本支持候选算法；
- 最终裁决 spectral `cond2` 或 estimated `cond1`；
- 宣称代表性数万自由度 Case 的 LU fill-in、峰值内存或收敛已经验证。

这与蓝图先行纪律及当前任务“不得新增依赖”的边界直接冲突，并触发 User 明确规定的
停止条件。故本轮不得修改正式蓝图、History、Project Tree 或组内使用说明来制造一个
依赖前提尚未成立的正式功能定义。

### 7.2 所需最小裁决

恢复任务所需的最小 User 裁决为：

1. 单独批准 SciPy 成为 LinkMesh 正式运行依赖；
2. 结合目标 Python、Linux Release 和服务器环境批准最低 SciPy 版本；
3. 允许只读核对该版本官方 API 和目标服务器安装事实；
4. 允许执行独立小型方法探针和代表性 final `Mesh2D` 资源探针；
5. 探针后再裁决 spectral `cond2` 或 estimated `cond1`；
6. 另行授权修改依赖文件、业务源码和 tests。

若不批准 SciPy，则必须重新定义目标；当前不批准 LinkMesh 自行实现稀疏 LU、
Lanczos/ARPACK 替代算法，也不批准引入另一套未声明稀疏库。

## 8. 本轮结论

原先由“requirements.txt 不含 SciPy”触发的停止报告已经完成方案转向，不再等待
SciPy 版本裁决，也不改回 SciPy 方案。当前正式方向为仅使用现有 NumPy 与标准库的
dependency-free Lanczos 估算，但实现仍未开始。

必须继续保留的实现停止条件包括：当前 NumPy 无法执行小型三对角
`eigvalsh`、无法可靠提取 final `Mesh2D` 拓扑外边界、无法在不修改 `Mesh2D` 的前提
下完成数据流、Lanczos 无法形成可验证的收敛状态，或实现被迫新增依赖、CLI/TOML
字段、Writer/Reader/refinement/外部接口修改。遇到这些情况必须停止并报告准确文件、
符号、实时证据、冲突条款和所需最小裁决。

最终状态：

- P1 Poisson stiffness conditioning benchmark：**DESIGNED / USER-APPROVED / NOT IMPLEMENTED**；
- dependency-free Lanczos estimator：**DESIGNED / NOT IMPLEMENTED**；
- raw condition estimate：**DESIGNED / NOT IMPLEMENTED**；
- DOF-normalized indicator：**DESIGNED / NOT IMPLEMENTED**；
- quality plot conditioning information box：**DESIGNED / NOT IMPLEMENTED**；
- universal condition threshold：**NOT ADOPTED**；
- preconditioner benchmark：**OUT OF SCOPE**；
- SciPy 和其他新增运行依赖：**OUT OF SCOPE**。

明确回答：

- 不新增 SciPy 或其他运行依赖：**是**；
- benchmark 为单位系数 P1 Poisson：**是**；
- 对 final triangle 拓扑外边界施加齐次 Dirichlet：**是**；
- 内部 Region interface 作为普通内部边：**是**；
- 使用无依赖内部稀疏结构：**设计为是，源码尚未实现**；
- 避免 dense 矩阵、完整特征谱和显式逆：**是**；
- 使用 Lanczos 估算：**是，源码尚未实现**；
- 同时报告 raw condition 和 `condition / N_free`：**设计为是，源码尚未实现**；
- 明确归一化不是严格不变量：**是**；
- 不设置通用阈值：**是**；
- 不加入预条件器：**是**；
- 保持 Q 热图颜色与 normalization：**是**；
- Poisson conditioning 仍为 NOT IMPLEMENTED：**是**。

当前不能诚实地完成“根据实时 SciPy 版本锁定稀疏条件估算方法”的蓝图迭代，因为
`requirements.txt` 没有 SciPy，项目也没有最低 SciPy 版本契约。按照 User 明确给出的
停止条件，本轮在依赖核对处停止。

本轮修改范围仅为补充本专项停止报告中的实时 `Mesh2D`、拓扑边界、quality plot
调用链、蓝图冲突和最小裁决证据。未修改正式蓝图、History、Project Tree、组内使用
说明、业务源码、tests、依赖、examples、Reader、Writer、Plotter、Mesh quality、
refinement、helper、OFT/Triangle、native ABI、目标格式或任何 work plan。

明确回答：

- 固定 benchmark 方向是否为单位系数 P1 Poisson：**是，User 已批准方向**。
- 是否拟对全部拓扑外边界施加齐次 Dirichlet：**是**。
- 内部 Region interface 是否保持内部边：**是**。
- 是否使用全局稀疏矩阵：**设计方向是，但依赖尚未批准**。
- 是否允许生产实现使用 dense 全局矩阵：**否**。
- 是否允许计算完整特征谱：**否**。
- 是否允许显式求逆：**否**。
- 最终推荐 spectral `cond2` 还是 one-norm：**METHOD PENDING；数学上优先调查
  spectral `cond2`，但实时依赖和代表性探针证据不足，尚未正式锁定**。
- 是否使用稀疏 LU：**候选方法需要，但尚未形成正式实现契约**。
- 是否同时报告 raw condition 和 condition / `N_free`：**设计方向是**。
- 是否明确归一化不是严格不变量：**是**。
- 是否设置通用阈值：**否**。
- 是否加入预条件器：**否**。
- 是否改变 Q 热图颜色或 `[0,1]` normalization：**否**。
- 是否新增公开 CLI/TOML 字段：**本轮否**。
- Poisson conditioning 是否仍为 NOT IMPLEMENTED：**是**。
