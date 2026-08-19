# Poisson P1 刚度矩阵条件诊断：前置依赖停止报告

## 1. 调查状态

- 调查状态：**STOPPED / DEPENDENCY DECISION REQUIRED**
- Poisson benchmark：**USER-APPROVED / NOT IMPLEMENTED**
- 稀疏条件数估算方法：**METHOD PENDING**
- 源码、测试、真实矩阵和 quality plot 信息框：**NOT IMPLEMENTED / NOT RUN**
- 本轮未修改业务源码、测试、依赖、CLI、配置、`Mesh2D`、Writer、Plotter、
  mesh quality、refinement、helper、OFT/Triangle、native ABI、目标格式或 work plan。

## 2. 直接证据

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

## 4. 所需最小 User 裁决

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

## 6. 本轮结论

当前不能诚实地完成“根据实时 SciPy 版本锁定稀疏条件估算方法”的蓝图迭代，因为
`requirements.txt` 没有 SciPy，项目也没有最低 SciPy 版本契约。按照 User 明确给出的
停止条件，本轮在依赖核对处停止。

明确回答：

- 固定 benchmark 方向是否为单位系数 P1 Poisson：**是，User 已批准方向**。
- 是否拟对全部拓扑外边界施加齐次 Dirichlet：**是**。
- 内部 Region interface 是否保持内部边：**是**。
- 是否允许生产实现使用 dense 全局矩阵：**否**。
- 是否允许计算完整特征谱：**否**。
- 是否允许显式求逆：**否**。
- 最终推荐 spectral `cond2` 还是 one-norm：**PENDING；倾向调查 spectral
  `cond2`，但依赖与方法证据不足，尚未正式锁定**。
- 是否报告 raw condition：**设计方向是**。
- 是否报告 condition / `N_free`：**设计方向是**。
- 是否明确归一化不是严格不变量：**是**。
- 是否设置通用阈值：**否**。
- 是否加入预条件器：**否**。
- 是否改变 Q 热图颜色：**否**。
- 是否新增公开 CLI/TOML 字段：**本轮否**。
- Poisson conditioning 是否仍为 NOT IMPLEMENTED：**是**。
