"""
oft_adapter.py —— M2 正式网格生成适配层（v1.9 三层接口）。

职责（严格对齐 LinkMesh_Architecture_Plan.md v1.9 第 7 节）：
    - mesh_from_oft_domain(domain) -> Mesh2D
          通用 N 区域核心：接收已构造的 OFT gs_Domain，调用一次 build_mesh()，
          将 pts/lc/reg 规范化并验证为 Mesh2D。对任意正区域数量 N 通用（含 N=1）。
    - build_oft_domain_from_gfile(gfile_data, ...) -> gs_Domain
          当前 GFile 默认区域策略层：构造 OFT gs_Domain，不调用 build_mesh()，
          不转换 pts/lc/reg。有壁三区域（PLASMA+VACUUM+OUTER），无壁两区域（PLASMA+OUTER）。
    - generate_mesh(gfile_data, ...) -> Mesh2D
          CLI 便利入口：只组合前两者。

正式数据流：
    GFileData → build_oft_domain_from_gfile → OFT gs_Domain
             → mesh_from_oft_domain/build_mesh → pts/lc/reg → Mesh2D

区域 ID 时序（重要）：
    OFT gs_Domain.build_mesh() 会根据区域类型和定义顺序重新排列区域 ID，
    并原地更新 domain.region_info[name]["id"]。因此 Adapter 必须在 build_mesh()
    成功返回之后再读取 domain.region_info，得到 OFT 最终区域 ID 集合，
    并以该最终集合校验输出 reg。绝不能在 build_mesh() 之前提取区域 ID 集合。

禁止事项：
    - 不复制 OFT 的区域拓扑、点合并、重采样、区域种子或 Triangle 调用逻辑；
    - 不修改 OFT 源码/安装目录/fork；
    - 不把 TOKAMAKER/ 快照加入 sys.path/PYTHONPATH；
    - 不在通用核心中判断 plasma/vacuum/outer 语义，不写死区域数量/名称/类型/整数 ID；
    - 不重编号、不排序、不压缩、不执行 +1；
    - 不访问 OFT 私有下划线字段；
    - 不引入 Protocol、抽象基类、插件系统、通用区域配置类或额外模块。

Mesh2D 兼容说明：
    Mesh2D 从只读的 triangle_wrapper.py 导入。其构造函数当前要求六个必填字段，
    OFT Adapter 显式传入核心三数组，并对 boundary_segments/boundary_markers/node_markers
    传入空数组以兼容旧构造签名。空数组只是兼容占位，不表示已生成任何边界语义。

参考规范：
    LinkMesh_Architecture_Plan.md v1.9 第 5、7 节
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from linkmesh.mesher.triangle_wrapper import Mesh2D

if TYPE_CHECKING:
    from linkmesh.readers.gfile_reader import GFileData


# --------------------------------------------------------------------------- #
# OFT 延迟导入                                                                  #
# --------------------------------------------------------------------------- #

def _load_gs_domain_class() -> Any:
    """延迟导入 OFT gs_Domain 类。

    在函数内部执行导入，避免模块顶层静态导入完整 OFT meshing 模块时
    触发 Windows 平台检查或动态库加载失败。

    正式 OFT 类来自 Linux Conda 环境安装的：
        OpenFUSIONToolkit.TokaMaker.meshing.gs_Domain

    绝不把仓库 TOKAMAKER/OpenFUSIONToolkit/src/python 加入 sys.path 或 PYTHONPATH。

    返回：
        gs_Domain 类对象

    异常：
        ImportError: OFT 未安装、不在 PYTHONPATH 中，或共享库加载失败。
                     保留原始异常链（__cause__）。
    """
    try:
        from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain
    except Exception as e:
        raise ImportError(
            "无法导入 OFT gs_Domain。正式运行环境为 Linux Conda 环境（linkmesh），"
            "需通过 pip 安装正式的 openfusiontoolkit==26.6，且 liboft_triangle.so 可加载。"
            "绝不要将 TOKAMAKER/OpenFUSIONToolkit/src/python 加入 PYTHONPATH。"
            f"\n原始错误：{e}"
        ) from e
    return gs_Domain


# --------------------------------------------------------------------------- #
# 内部数值校验辅助                                                              #
# --------------------------------------------------------------------------- #

def _as_finite_float_2d(arr: Any, name: str) -> np.ndarray:
    """将输入转换为有限的二维 float64 数组，非法时抛 ValueError。"""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"{name} 必须是二维数组，实际 ndim={a.ndim}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} 含非有限值（NaN/Inf）")
    return a


def _validate_integer_semantics(arr_float: np.ndarray, name: str) -> None:
    """验证浮点数组具有整数语义（有限且等于其四舍五入值）。

    在 astype(np.int32) 之前调用，防止 astype 静默截断 1.5、NaN 或 Inf。
    """
    if not np.all(np.isfinite(arr_float)):
        raise ValueError(f"{name} 含非有限值（NaN/Inf），不具备整数语义")
    if not np.all(arr_float == np.round(arr_float)):
        raise ValueError(f"{name} 含非整数值，不具备整数语义")


# --------------------------------------------------------------------------- #
# 1. 通用 N 区域核心                                                            #
# --------------------------------------------------------------------------- #

def mesh_from_oft_domain(domain: Any) -> Mesh2D:
    """通用 N 区域核心：将已构造 OFT gs_Domain 转换为轻量 Mesh2D。

    仅负责：
        1. 在调用前验证 domain 提供可调用的 build_mesh() 和可读取的 region_info 属性；
        2. 调用一次 domain.build_mesh()；
        3. 接收 pts, lc, reg；
        4. build_mesh() 成功后重新读取 domain.region_info，
           提取 OFT 最终区域 ID 集合（build_mesh 会原地重排区域 ID）；
        5. 规范化并验证输出，用最终区域 ID 集合校验 reg；
        6. 构造 Mesh2D。

    对任意正区域数量 N 通用，包括 N=1、N=2、N=3、N>3，无特殊分支。
    不判断 LCFS/第一壁/plasma/vacuum/outer，不写死区域名称/类型/数量/整数 ID。
    不重编号、不排序、不压缩、不执行 +1。

    区域 ID 时序（关键）：
        OFT build_mesh() 会根据区域类型和定义顺序重排区域 ID，并原地更新
        domain.region_info[name]["id"]。因此最终区域 ID 集合必须在 build_mesh()
        成功返回之后从 domain.region_info 读取，绝不能在 build_mesh() 之前提取。

    参数：
        domain: 已由调用方构造完成的 OFT gs_Domain 对象

    返回：
        Mesh2D 对象（核心三数组 nodes/triangles/region_ids，兼容空边界数组）

    异常：
        ValueError: 输出不满足契约（形状、dtype、索引范围、退化、区域集合等），
                    或 build_mesh() 后 region_info 为空/非法/含重复或非正 ID
        TypeError:  domain 缺少 build_mesh() 或 region_info
    """
    # --- Step 1：调用前只验证 domain 接口存在（不在此处提取最终区域 ID）---
    build_mesh = getattr(domain, "build_mesh", None)
    if not callable(build_mesh):
        raise TypeError("domain 必须提供可调用的 build_mesh() 方法")

    # 仅验证 region_info 属性存在且可读取；不在 build_mesh() 前提取最终 ID，
    # 因为 build_mesh() 会原地重排区域 ID。
    if not hasattr(domain, "region_info"):
        raise TypeError("domain 必须提供可读取的 region_info 属性")

    # --- Step 2：调用且只调用一次 build_mesh() ---
    result = build_mesh()
    try:
        pts, lc, reg = result
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"build_mesh() 应返回 (pts, lc, reg) 三元组，实际无法解包：{e}"
        ) from e

    # --- Step 4：build_mesh() 成功后重新读取 region_info，提取 OFT 最终区域 ID 集合 ---
    region_info = getattr(domain, "region_info", None)
    if region_info is None:
        raise TypeError("build_mesh() 后 domain.region_info 为 None，无法读取最终区域 ID")

    # 从生成后的 region_info 读取最终区域 ID 集合（不推断物理语义，仅取整数 ID）
    expected_ids = _extract_region_ids(region_info)
    if len(expected_ids) == 0:
        raise ValueError(
            "build_mesh() 后 domain.region_info 为空，未定义任何区域"
        )

    # --- Step 5：规范化并验证 nodes ---
    nodes = _as_finite_float_2d(pts, "pts")
    if nodes.shape[0] == 0:
        raise ValueError("build_mesh() 返回节点数为 0")
    if nodes.shape[1] != 2:
        raise ValueError(f"pts 必须为 (N,2)，实际 shape={nodes.shape}")
    n_nodes = nodes.shape[0]

    # 验证并转换 triangles（lc）
    lc_float = np.asarray(lc, dtype=np.float64)
    if lc_float.ndim != 2 or lc_float.shape[1] != 3:
        raise ValueError(f"lc 必须为 (T,3)，实际 shape={lc_float.shape}")
    if lc_float.shape[0] == 0:
        raise ValueError("build_mesh() 返回三角形数为 0")
    _validate_integer_semantics(lc_float, "lc")
    triangles = lc_float.astype(np.int32)
    n_triangles = triangles.shape[0]

    # 索引范围校验（0-based，M2-0 确认）
    if triangles.min() < 0 or triangles.max() >= n_nodes:
        raise ValueError(
            f"三角形节点索引越界：应满足 0 <= index < {n_nodes}，"
            f"实际范围 [{int(triangles.min())}, {int(triangles.max())}]"
        )

    # 退化检查：三个顶点索引互不相同
    for i in range(n_triangles):
        a, b, c = int(triangles[i, 0]), int(triangles[i, 1]), int(triangles[i, 2])
        if a == b or b == c or a == c:
            raise ValueError(f"三角形 {i} 存在重复顶点索引：{[a, b, c]}")

    # 退化检查：绝对面积严格大于 1e-12
    for i in range(n_triangles):
        p0 = nodes[triangles[i, 0]]
        p1 = nodes[triangles[i, 1]]
        p2 = nodes[triangles[i, 2]]
        area = abs(
            (p1[0] - p0[0]) * (p2[1] - p0[1])
            - (p2[0] - p0[0]) * (p1[1] - p0[1])
        ) / 2.0
        if not (area > 1e-12):
            raise ValueError(f"三角形 {i} 面积过小或退化：area={area}")

    # 验证并转换 region_ids（reg）
    reg_float = np.asarray(reg, dtype=np.float64).reshape(-1)
    _validate_integer_semantics(reg_float, "reg")
    region_ids = reg_float.astype(np.int32).reshape(-1)

    if len(region_ids) != n_triangles:
        raise ValueError(
            f"reg 长度（{len(region_ids)}）与三角形数（{n_triangles}）不一致"
        )

    # 所有区域编号必须为正
    if region_ids.min() <= 0:
        raise ValueError(
            f"region_ids 含非正编号（0/负数）：最小值={int(region_ids.min())}；"
            "非正区域编号表示未认领或非法区域，不是合法标签"
        )

    # --- 区域集合一致性校验（与 build_mesh 后的 OFT 最终区域 ID 集合完全一致）---
    actual_ids = set(int(x) for x in region_ids.tolist())
    if actual_ids != expected_ids:
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        raise ValueError(
            "输出区域 ID 集合与 build_mesh 后的 OFT 最终 region_info 不一致："
            f"缺失={sorted(missing)}，多余={sorted(extra)}；"
            f"期望（最终）={sorted(expected_ids)}，实际={sorted(actual_ids)}"
        )

    # 每个已定义区域至少对应一个三角形（actual_ids == expected_ids 已隐含，
    # 但显式检查以覆盖 region_info 提供 ID 而输出缺该 ID 的情况）
    for rid in expected_ids:
        if rid not in actual_ids:
            raise ValueError(f"区域 ID {rid} 未对应任何三角形")

    # --- Step 6：构造 Mesh2D（兼容旧六字段构造签名）---
    mesh = Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=region_ids,
        boundary_segments=np.empty((0, 2), dtype=np.int32),
        boundary_markers=np.empty((0,), dtype=np.int32),
        node_markers=np.empty((0,), dtype=np.int32),
    )
    return mesh


def _extract_region_ids(region_info: Any) -> set:
    """从 domain.region_info 提取最终区域整数 ID 集合。

    注意：本函数应在 build_mesh() 成功返回之后调用，读取的是 OFT 重排后的
    最终区域 ID。只读取整数 ID，不推断物理语义。region_info 结构由 OFT 决定；
    这里做宽松适配：支持形如 {name: {'id': int, ...}} 或 {name: id} 的映射，
    以及提供 .id 属性的区域对象。

    参数：
        region_info: OFT domain.region_info（build_mesh 后的最终状态）

    返回：
        区域 ID 的 set（int）

    异常：
        ValueError: 无法从 region_info 提取合法整数 ID，或出现 ID 重复
    """
    ids: list = []

    if hasattr(region_info, "items"):
        for _name, info in region_info.items():
            ids.append(_coerce_region_id(info))
    elif isinstance(region_info, (list, tuple)):
        for info in region_info:
            ids.append(_coerce_region_id(info))
    else:
        raise ValueError(
            "无法解析 domain.region_info：既非映射也非序列"
        )

    if len(ids) == 0:
        return set()

    id_set = set(ids)
    if len(id_set) != len(ids):
        raise ValueError(f"domain.region_info 存在重复区域 ID：{sorted(ids)}")

    for rid in id_set:
        if rid <= 0:
            raise ValueError(
                f"domain.region_info 含非正区域 ID：{rid}"
            )
    return id_set


def _coerce_region_id(info: Any) -> int:
    """从单个区域记录中提取整数 ID（宽松适配）。"""
    candidate: Any = None

    if isinstance(info, dict):
        if "id" in info:
            candidate = info["id"]
        elif "reg_id" in info:
            candidate = info["reg_id"]
        else:
            raise ValueError(f"区域记录缺少 id 字段：{info}")
    elif hasattr(info, "id"):
        candidate = getattr(info, "id")
    elif isinstance(info, (int, np.integer)):
        candidate = info
    elif isinstance(info, float):
        candidate = info
    else:
        raise ValueError(f"无法从区域记录提取 ID：{info!r}")

    cf = float(candidate)
    if not np.isfinite(cf) or cf != round(cf):
        raise ValueError(f"区域 ID 不是合法整数：{candidate!r}")
    return int(cf)


# --------------------------------------------------------------------------- #
# 2. 当前 GFile 默认区域策略层                                                  #
# --------------------------------------------------------------------------- #

def build_oft_domain_from_gfile(
    gfile_data: "GFileData",
    *,
    plasma_dx: float = 0.08,
    vacuum_dx: float = 0.10,
    outer_dx: float = 0.15,
    outer_padding: float = 0.12,
) -> Any:
    """当前 GFile 默认区域策略层：构造 OFT gs_Domain（不调用 build_mesh）。

    默认策略：
        - 有有效第一壁：OUTER(boundary) + PLASMA(plasma) + VACUUM(vacuum)，
          使用 add_annulus(lcfs, "plasma", first_wall, "vacuum", parent_name="outer")；
        - 无第一壁：OUTER(boundary) + PLASMA(plasma)，
          使用 add_polygon(lcfs, "plasma", parent_name="outer")。
        两种策略均创建人工 outer rectangle。

    本函数不调用 build_mesh()，不转换 pts/lc/reg，不复制 OFT 的重采样、
    点合并、种子搜索或 Triangle 算法。

    参数：
        gfile_data:    GFileData 对象（含 lcfs_r/lcfs_z，可选 wall_r/wall_z）
        plasma_dx:     plasma 区域网格尺度（有限正数）
        vacuum_dx:     vacuum 区域网格尺度（有限正数）
        outer_dx:      outer 区域网格尺度（有限正数）
        outer_padding: 人工 outer 矩形四侧扩展比例（有限非负数）

    返回：
        已构造但尚未 build_mesh() 的 OFT gs_Domain 对象

    异常：
        ValueError: 参数或轮廓非法
        ImportError: OFT 不可用
    """
    # --- 参数校验 ---
    for dxname, dxval in (("plasma_dx", plasma_dx), ("vacuum_dx", vacuum_dx), ("outer_dx", outer_dx)):
        if not (np.isfinite(dxval) and dxval > 0):
            raise ValueError(f"{dxname} 必须是有限正数，实际={dxval}")
    if not (np.isfinite(outer_padding) and outer_padding >= 0):
        raise ValueError(f"outer_padding 必须是有限非负数，实际={outer_padding}")

    # --- LCFS 轮廓校验与薄规范化 ---
    lcfs = _prepare_contour(
        getattr(gfile_data, "lcfs_r", None),
        getattr(gfile_data, "lcfs_z", None),
        name="LCFS",
    )

    # --- 第一壁校验：同时存在或同时缺失 ---
    wall_r = getattr(gfile_data, "wall_r", None)
    wall_z = getattr(gfile_data, "wall_z", None)
    has_wall_r = wall_r is not None and len(np.asarray(wall_r)) > 0
    has_wall_z = wall_z is not None and len(np.asarray(wall_z)) > 0

    if has_wall_r != has_wall_z:
        raise ValueError(
            "第一壁 R/Z 必须同时存在或同时缺失："
            f"wall_r 存在={has_wall_r}，wall_z 存在={has_wall_z}"
        )

    first_wall = None
    if has_wall_r:
        # 第一壁 R/Z 长度不一致、点数不足或含非有限值时，
        # _prepare_contour 在 _load_gs_domain_class() 之前抛出 ValueError。
        first_wall = _prepare_contour(wall_r, wall_z, name="第一壁")

    # --- 计算人工 outer 矩形（LCFS 与可用第一壁的联合包围范围）---
    all_r = [lcfs[:, 0]]
    all_z = [lcfs[:, 1]]
    if first_wall is not None:
        all_r.append(first_wall[:, 0])
        all_z.append(first_wall[:, 1])
    cat_r = np.concatenate(all_r)
    cat_z = np.concatenate(all_z)

    r_min, r_max = float(cat_r.min()), float(cat_r.max())
    z_min, z_max = float(cat_z.min()), float(cat_z.max())
    dr = r_max - r_min
    dz = z_max - z_min
    if not (np.isfinite(dr) and np.isfinite(dz) and dr > 0 and dz > 0):
        raise ValueError(
            f"轮廓包围范围退化：R 跨度={dr}，Z 跨度={dz}"
        )

    pad = outer_padding * max(dr, dz)
    rect_rmin = r_min - pad
    rect_rmax = r_max + pad
    rect_zmin = z_min - pad
    rect_zmax = z_max + pad

    rect_rc = 0.5 * (rect_rmin + rect_rmax)
    rect_zc = 0.5 * (rect_zmin + rect_zmax)
    rect_w = rect_rmax - rect_rmin
    rect_h = rect_zmax - rect_zmin
    if not (np.isfinite(rect_w) and np.isfinite(rect_h) and rect_w > 0 and rect_h > 0):
        raise ValueError(
            f"人工 outer 矩形尺寸非法：宽={rect_w}，高={rect_h}"
        )

    # --- 构造 OFT Domain（延迟导入）---
    gs_Domain = _load_gs_domain_class()
    domain = gs_Domain()

    domain.define_region("outer", outer_dx, "boundary")
    domain.define_region("plasma", plasma_dx, "plasma")

    if first_wall is not None:
        # 有壁三区域：PLASMA + VACUUM + OUTER
        domain.define_region("vacuum", vacuum_dx, "vacuum")
        domain.add_annulus(
            lcfs, "plasma", first_wall, "vacuum", parent_name="outer"
        )
    else:
        # 无壁两区域：PLASMA + OUTER
        domain.add_polygon(lcfs, "plasma", parent_name="outer")

    # 人工 outer rectangle
    domain.add_rectangle(rect_rc, rect_zc, rect_w, rect_h, name="outer")

    return domain


def _prepare_contour(r: Any, z: Any, *, name: str) -> np.ndarray:
    """轮廓薄规范化：转 (N,2) float64，删除首尾近似重复点，验证最低点数。

    不自行重采样、平滑尖角、自交修补、点在多边形判断或区域种子搜索。

    参数：
        r:    R 坐标数组
        z:    Z 坐标数组
        name: 轮廓名称（用于错误信息）

    返回：
        (N,2) float64 轮廓数组

    异常：
        ValueError: R/Z 缺失、长度不一致、有效点少于 3、或含非有限值（NaN/Inf）
    """
    if r is None or z is None:
        raise ValueError(f"{name} 的 R/Z 坐标必须同时提供")

    ra = np.asarray(r, dtype=np.float64).reshape(-1)
    za = np.asarray(z, dtype=np.float64).reshape(-1)

    if len(ra) != len(za):
        raise ValueError(
            f"{name} 的 R/Z 长度不一致：len(R)={len(ra)}，len(Z)={len(za)}"
        )
    if len(ra) < 3:
        raise ValueError(f"{name} 至少需要 3 个点，实际={len(ra)}")
    if not (np.all(np.isfinite(ra)) and np.all(np.isfinite(za))):
        raise ValueError(f"{name} 含非有限值（NaN/Inf）")

    contour = np.column_stack([ra, za]).astype(np.float64)

    # 尺度相关的窄容差判断首尾近似重复；只删除最后一个重复点
    dr = float(contour[:, 0].max() - contour[:, 0].min())
    dz = float(contour[:, 1].max() - contour[:, 1].min())
    scale = max(dr, dz)
    if not (np.isfinite(scale) and scale > 0):
        raise ValueError(f"{name} 包围范围退化：R 跨度={dr}，Z 跨度={dz}")

    tol = 1e-9 * scale
    gap = float(np.hypot(contour[0, 0] - contour[-1, 0], contour[0, 1] - contour[-1, 1]))
    if gap <= tol:
        contour = contour[:-1]

    if len(contour) < 3:
        raise ValueError(f"{name} 删除重复闭合点后不足 3 个点，实际={len(contour)}")

    return contour


# --------------------------------------------------------------------------- #
# 3. CLI 便利入口                                                              #
# --------------------------------------------------------------------------- #

def generate_mesh(
    gfile_data: "GFileData",
    *,
    plasma_dx: float = 0.08,
    vacuum_dx: float = 0.10,
    outer_dx: float = 0.15,
    outer_padding: float = 0.12,
) -> Mesh2D:
    """CLI 便利入口：只组合 build_oft_domain_from_gfile 与 mesh_from_oft_domain。

    本函数不包含第二套输入规范化、输出验证、区域判断或网格算法。

    参数：
        gfile_data:    GFileData 对象
        plasma_dx:     plasma 区域网格尺度
        vacuum_dx:     vacuum 区域网格尺度
        outer_dx:      outer 区域网格尺度
        outer_padding: 人工 outer 矩形扩展比例

    返回：
        Mesh2D 对象
    """
    domain = build_oft_domain_from_gfile(
        gfile_data,
        plasma_dx=plasma_dx,
        vacuum_dx=vacuum_dx,
        outer_dx=outer_dx,
        outer_padding=outer_padding,
    )
    return mesh_from_oft_domain(domain)
