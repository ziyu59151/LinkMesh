#!/usr/bin/env python3
"""OFT 26.6 multi-region behavior probe.

This script is an investigation tool, not a LinkMesh production module. It
constructs deterministic synthetic multi-region domains with the real OFT
``gs_Domain`` API and records setup-only numbering, final Triangle attributes,
seed diagnostics, numbering comparisons, and basic mesh topology.

The probe writes JSON diagnostics for every case plus a summary JSON. When
Matplotlib is available, it also writes topology and mesh PNG files.

No LinkMesh Writer, target format, or production CLI is used.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

REQUIRED_OFT_VERSION = "26.6"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_UNCONFIRMED = "UNCONFIRMED"
STATUS_NA = "NOT APPLICABLE"


@dataclass(frozen=True)
class CurveSpec:
    """One deterministic input curve and its intended Region relationship."""

    key: str
    points: np.ndarray
    parent_key: str | None
    dx: float


@dataclass(frozen=True)
class CaseSpec:
    """One synthetic topology in explicit input/block order."""

    name: str
    curves: tuple[CurveSpec, ...]


@dataclass
class BuiltDomain:
    """OFT objects and deterministic metadata retained for probe inspection."""

    domain: Any
    curve_by_key: dict[str, CurveSpec]
    curve_id_by_key: dict[str, int]
    region_name_by_key: dict[str, str]
    technical_role_by_key: dict[str, str]
    region_object_by_key: dict[str, Any]


def _ellipse(
    center_r: float,
    center_z: float,
    radius_r: float,
    radius_z: float,
    *,
    count: int = 32,
) -> np.ndarray:
    """Create a simple counter-clockwise implicit-closure ellipse."""

    theta = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    return np.column_stack(
        (
            center_r + radius_r * np.cos(theta),
            center_z + radius_z * np.sin(theta),
        )
    ).astype(np.float64)


def _base_case_specs() -> dict[str, CaseSpec]:
    """Create all required synthetic cases with stable geometric keys."""

    two_level = CaseSpec(
        name="two_level_nested",
        curves=(
            CurveSpec("root", _ellipse(5.0, 0.0, 3.0, 2.4), None, 0.42),
            CurveSpec("core", _ellipse(5.0, 0.0, 1.0, 0.75), "root", 0.16),
        ),
    )

    four_level = CaseSpec(
        name="four_level_nested",
        curves=(
            CurveSpec("root", _ellipse(5.0, 0.0, 3.6, 2.8), None, 0.48),
            CurveSpec("level2", _ellipse(5.0, 0.0, 2.7, 2.0), "root", 0.34),
            CurveSpec("level3", _ellipse(5.0, 0.0, 1.8, 1.25), "level2", 0.23),
            CurveSpec("level4", _ellipse(5.0, 0.0, 0.8, 0.52), "level3", 0.13),
        ),
    )

    siblings = CaseSpec(
        name="one_parent_two_siblings",
        curves=(
            CurveSpec("root", _ellipse(5.0, 0.0, 3.8, 2.6), None, 0.44),
            CurveSpec("left", _ellipse(3.7, 0.0, 0.72, 0.58), "root", 0.14),
            CurveSpec("right", _ellipse(6.3, 0.0, 0.82, 0.62), "root", 0.22),
        ),
    )

    mixed = CaseSpec(
        name="mixed_tree",
        curves=(
            CurveSpec("root", _ellipse(5.0, 0.0, 4.0, 2.8), None, 0.46),
            CurveSpec("left", _ellipse(3.45, 0.0, 1.15, 0.90), "root", 0.25),
            CurveSpec("left_core", _ellipse(3.45, 0.0, 0.42, 0.31), "left", 0.11),
            CurveSpec("right", _ellipse(6.55, 0.0, 0.86, 0.65), "root", 0.18),
        ),
    )

    mixed_by_key = {curve.key: curve for curve in mixed.curves}
    reordered = CaseSpec(
        name="reordered_input",
        curves=tuple(
            mixed_by_key[key]
            for key in ("right", "left_core", "root", "left")
        ),
    )

    return {
        case.name: case
        for case in (two_level, four_level, siblings, mixed, reordered)
    }


def _children_by_key(spec: CaseSpec) -> dict[str, list[str]]:
    children = {curve.key: [] for curve in spec.curves}
    for curve in spec.curves:
        if curve.parent_key is not None:
            children[curve.parent_key].append(curve.key)
    return children


def _descendants_by_key(spec: CaseSpec) -> dict[str, set[str]]:
    children = _children_by_key(spec)
    descendants: dict[str, set[str]] = {}

    def collect(key: str) -> set[str]:
        result: set[str] = set()
        for child in children[key]:
            result.add(child)
            result.update(collect(child))
        return result

    for curve in spec.curves:
        descendants[curve.key] = collect(curve.key)
    return descendants


def _depth_by_key(spec: CaseSpec) -> dict[str, int]:
    curves = {curve.key: curve for curve in spec.curves}
    depths: dict[str, int] = {}

    def depth(key: str) -> int:
        if key in depths:
            return depths[key]
        parent = curves[key].parent_key
        value = 0 if parent is None else depth(parent) + 1
        depths[key] = value
        return value

    for key in curves:
        depth(key)
    return depths


def _region_name(curve_key: str) -> str:
    return f"lm_{curve_key}"


def _select_plasma_key(spec: CaseSpec) -> str:
    """Choose exactly one deterministic deepest Region for OFT's plasma role."""

    depths = _depth_by_key(spec)
    return min(
        (curve.key for curve in spec.curves),
        key=lambda key: (-depths[key], key),
    )


def _build_domain(gs_domain_class: Any, spec: CaseSpec) -> BuiltDomain:
    """Build one fresh OFT Domain without invoking ``build_mesh``."""

    curve_by_key = {curve.key: curve for curve in spec.curves}
    curve_id_by_key = {
        curve.key: index for index, curve in enumerate(spec.curves, start=1)
    }
    region_name_by_key = {
        curve.key: _region_name(curve.key) for curve in spec.curves
    }
    plasma_key = _select_plasma_key(spec)
    technical_role_by_key: dict[str, str] = {}

    domain = gs_domain_class()

    # Definition order intentionally follows input/block order. The probe records
    # how OFT's later role-based reindexing responds to this order.
    for curve in spec.curves:
        if curve.parent_key is None:
            role = "boundary"
        elif curve.key == plasma_key:
            role = "plasma"
        else:
            role = "vacuum"
        technical_role_by_key[curve.key] = role
        domain.define_region(region_name_by_key[curve.key], curve.dx, role)

    region_object_by_key: dict[str, Any] = {}
    for curve in spec.curves:
        before = len(domain.regions)
        parent_name = (
            None
            if curve.parent_key is None
            else region_name_by_key[curve.parent_key]
        )
        domain.add_polygon(
            np.array(curve.points, dtype=np.float64, copy=True),
            region_name_by_key[curve.key],
            parent_name=parent_name,
        )
        if len(domain.regions) != before + 1:
            raise RuntimeError(
                f"add_polygon did not add exactly one Region for {curve.key!r}"
            )
        region_object_by_key[curve.key] = domain.regions[-1]

    return BuiltDomain(
        domain=domain,
        curve_by_key=curve_by_key,
        curve_id_by_key=curve_id_by_key,
        region_name_by_key=region_name_by_key,
        technical_role_by_key=technical_role_by_key,
        region_object_by_key=region_object_by_key,
    )


def _json_value(value: Any) -> Any:
    """Convert NumPy, Path, tuples, and non-finite floats to strict JSON data."""

    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_value(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _exception_payload(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def _region_info_snapshot(domain: Any) -> dict[str, Any]:
    return copy.deepcopy(_json_value(getattr(domain, "region_info", None)))


def _region_ids_snapshot(built: BuiltDomain) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, region in built.region_object_by_key.items():
        result[key] = _json_value(getattr(region, "_id", None))
    return result


def _final_id_by_key(built: BuiltDomain) -> dict[str, int]:
    result: dict[str, int] = {}
    region_info = built.domain.region_info
    for key, name in built.region_name_by_key.items():
        result[key] = int(region_info[name]["id"])
    return result


def _input_plan(built: BuiltDomain) -> list[dict[str, Any]]:
    children = _children_by_key(
        CaseSpec("snapshot", tuple(built.curve_by_key.values()))
    )
    return [
        {
            "input_index": index,
            "curve_id": built.curve_id_by_key[curve.key],
            "curve_key": curve.key,
            "region_name": built.region_name_by_key[curve.key],
            "technical_role": built.technical_role_by_key[curve.key],
            "parent_key": curve.parent_key,
            "children_keys": children[curve.key],
            "dx_m": curve.dx,
            "point_count": int(curve.points.shape[0]),
        }
        for index, curve in enumerate(built.curve_by_key.values(), start=1)
    ]


def _seed_diagnostics(
    built: BuiltDomain,
    spec: CaseSpec,
) -> dict[str, Any]:
    """Record OFT region seeds and conservative child-exclusion diagnostics."""

    mesh = getattr(built.domain, "mesh", None)
    reg_defs = getattr(mesh, "_reg_defs", None)
    if reg_defs is None:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": "domain.mesh._reg_defs is unavailable",
            "regions": [],
        }

    descendants = _descendants_by_key(spec)
    rows: list[dict[str, Any]] = []
    found_failure = False

    for curve, reg_def in zip(spec.curves, reg_defs):
        seed = np.asarray(reg_def[:2], dtype=np.float64)
        own_region = built.region_object_by_key[curve.key]
        own_contains = bool(own_region.check_in_poly(seed))
        child_hits: list[str] = []
        child_checks: dict[str, bool] = {}

        for child_key in sorted(descendants[curve.key]):
            child_region = built.region_object_by_key[child_key]
            contains = bool(child_region.check_in_poly(seed))
            child_checks[child_key] = contains
            if contains:
                child_hits.append(child_key)

        if not own_contains or child_hits:
            exclusion_status = STATUS_FAIL
            found_failure = True
        elif descendants[curve.key]:
            # Point-in-polygon checks can reject obvious child overlap, but they
            # are not a polygon-boolean proof of parent-minus-children.
            exclusion_status = STATUS_UNCONFIRMED
        else:
            exclusion_status = STATUS_PASS

        rows.append(
            {
                "curve_key": curve.key,
                "curve_id": built.curve_id_by_key[curve.key],
                "final_region_id": int(reg_def[2]),
                "seed_rz": seed.tolist(),
                "maximum_area": float(reg_def[3]),
                "inside_own_polygon": own_contains,
                "descendant_polygon_checks": child_checks,
                "descendant_hits": child_hits,
                "target_region_status": exclusion_status,
            }
        )

    return {
        "status": STATUS_FAIL if found_failure else STATUS_UNCONFIRMED,
        "reason": (
            "At least one seed failed its own/descendant polygon check"
            if found_failure
            else "OFT point-in-polygon checks do not prove polygon boolean difference"
        ),
        "regions": rows,
    }


def _run_setup_only(gs_domain_class: Any, spec: CaseSpec) -> dict[str, Any]:
    built = _build_domain(gs_domain_class, spec)
    result: dict[str, Any] = {
        "status": STATUS_UNCONFIRMED,
        "input_plan": _input_plan(built),
        "before": {
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_ids_snapshot(built),
            "has_mesh": hasattr(built.domain, "mesh"),
        },
    }

    try:
        returned = built.domain.build_mesh(setup_only=True)
        result["first_call"] = {
            "status": STATUS_PASS,
            "return": _json_value(returned),
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_ids_snapshot(built),
            "final_id_by_curve_key": _final_id_by_key(built),
            "has_mesh": hasattr(built.domain, "mesh"),
            "mesh_arrays_available": all(
                getattr(built.domain, name, None) is not None
                for name in ("_r", "_lc", "_reg")
            ),
            "seed_diagnostics": _seed_diagnostics(built, spec),
        }
    except Exception as exc:
        result["status"] = STATUS_FAIL
        result["first_call"] = {
            "status": STATUS_FAIL,
            "exception": _exception_payload(exc),
        }
        return result

    try:
        repeated = built.domain.build_mesh(setup_only=True)
        result["second_call_same_domain"] = {
            "status": STATUS_PASS,
            "return": _json_value(repeated),
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_ids_snapshot(built),
            "final_id_by_curve_key": _final_id_by_key(built),
        }
    except Exception as exc:
        result["second_call_same_domain"] = {
            "status": STATUS_UNCONFIRMED,
            "exception": _exception_payload(exc),
        }

    result["status"] = STATUS_PASS
    return result


def _signed_double_areas(
    nodes: np.ndarray,
    triangles: np.ndarray,
) -> np.ndarray:
    p0 = nodes[triangles[:, 0]]
    p1 = nodes[triangles[:, 1]]
    p2 = nodes[triangles[:, 2]]
    return (
        (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1])
        - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1])
    )


def _mesh_checks(
    nodes: np.ndarray,
    triangles: np.ndarray,
    attributes: np.ndarray,
    expected_region_ids: set[int],
) -> dict[str, Any]:
    checks: dict[str, str] = {}
    details: dict[str, Any] = {}

    checks["nodes_shape"] = (
        STATUS_PASS
        if nodes.ndim == 2 and nodes.shape[1] == 2 and nodes.shape[0] >= 3
        else STATUS_FAIL
    )
    checks["triangles_shape"] = (
        STATUS_PASS
        if triangles.ndim == 2
        and triangles.shape[1] == 3
        and triangles.shape[0] > 0
        else STATUS_FAIL
    )
    checks["attributes_shape"] = (
        STATUS_PASS
        if attributes.ndim == 1 and attributes.shape[0] == triangles.shape[0]
        else STATUS_FAIL
    )
    checks["finite"] = (
        STATUS_PASS
        if np.all(np.isfinite(nodes))
        and np.all(np.isfinite(triangles))
        and np.all(np.isfinite(attributes))
        else STATUS_FAIL
    )

    index_ok = (
        triangles.size > 0
        and int(triangles.min()) >= 0
        and int(triangles.max()) < nodes.shape[0]
    )
    checks["index_range"] = STATUS_PASS if index_ok else STATUS_FAIL

    repeated_vertex = np.any(
        (triangles[:, 0] == triangles[:, 1])
        | (triangles[:, 1] == triangles[:, 2])
        | (triangles[:, 0] == triangles[:, 2])
    )
    checks["triangle_distinct_vertices"] = (
        STATUS_FAIL if repeated_vertex else STATUS_PASS
    )

    signed_double_area = _signed_double_areas(nodes, triangles)
    area_scale = max(
        1.0,
        float(np.ptp(nodes[:, 0])),
        float(np.ptp(nodes[:, 1])),
        float(np.max(np.abs(nodes))),
    )
    area_tolerance = 1.0e-12 * area_scale * area_scale
    checks["positive_triangle_orientation"] = (
        STATUS_PASS
        if np.all(signed_double_area > area_tolerance)
        else STATUS_FAIL
    )
    details["signed_double_area"] = {
        "minimum": float(signed_double_area.min()),
        "maximum": float(signed_double_area.max()),
        "tolerance": area_tolerance,
        "nonpositive_or_degenerate_count": int(
            np.count_nonzero(signed_double_area <= area_tolerance)
        ),
    }

    canonical_triangles = np.sort(triangles.astype(np.int64), axis=1)
    unique_triangles = np.unique(canonical_triangles, axis=0)
    duplicate_triangle_count = triangles.shape[0] - unique_triangles.shape[0]
    checks["no_duplicate_triangles"] = (
        STATUS_PASS if duplicate_triangle_count == 0 else STATUS_FAIL
    )
    details["duplicate_triangle_count"] = int(duplicate_triangle_count)

    edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    for triangle_index, triangle in enumerate(triangles):
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge = tuple(sorted((int(first), int(second))))
            edge_to_triangles[edge].append(triangle_index)

    incidence = Counter(len(adjacent) for adjacent in edge_to_triangles.values())
    nonmanifold_edges = [
        edge for edge, adjacent in edge_to_triangles.items() if len(adjacent) > 2
    ]
    checks["manifold_edge_incidence"] = (
        STATUS_PASS if not nonmanifold_edges else STATUS_FAIL
    )
    details["edge_incidence_counts"] = {
        str(count): int(total) for count, total in sorted(incidence.items())
    }
    details["boundary_edge_count"] = int(incidence.get(1, 0))
    details["interior_edge_count"] = int(incidence.get(2, 0))
    details["nonmanifold_edges"] = nonmanifold_edges

    interface_counts: Counter[tuple[int, int]] = Counter()
    for adjacent in edge_to_triangles.values():
        if len(adjacent) != 2:
            continue
        first_region = int(attributes[adjacent[0]])
        second_region = int(attributes[adjacent[1]])
        if first_region != second_region:
            interface_counts[tuple(sorted((first_region, second_region)))] += 1

    details["shared_interface_edge_counts"] = {
        f"{pair[0]}-{pair[1]}": int(count)
        for pair, count in sorted(interface_counts.items())
    }

    observed_ids = {int(value) for value in np.unique(attributes)}
    checks["region_id_set"] = (
        STATUS_PASS if observed_ids == expected_region_ids else STATUS_FAIL
    )
    region_triangle_counts = Counter(int(value) for value in attributes)
    checks["every_region_has_triangles"] = (
        STATUS_PASS
        if all(region_triangle_counts[region_id] > 0 for region_id in expected_region_ids)
        else STATUS_FAIL
    )
    details["expected_region_ids"] = sorted(expected_region_ids)
    details["observed_region_ids"] = sorted(observed_ids)
    details["region_triangle_counts"] = {
        str(region_id): int(region_triangle_counts[region_id])
        for region_id in sorted(observed_ids | expected_region_ids)
    }

    status = (
        STATUS_PASS
        if all(value == STATUS_PASS for value in checks.values())
        else STATUS_FAIL
    )
    return {"status": status, "checks": checks, "details": details}


def _plot_case(
    built: BuiltDomain,
    spec: CaseSpec,
    output_dir: Path,
    nodes: np.ndarray,
    triangles: np.ndarray,
    attributes: np.ndarray,
) -> dict[str, Any]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": f"Matplotlib unavailable: {exc}",
        }

    written: dict[str, str] = {}

    try:
        figure, axis = plt.subplots(figsize=(7, 6), constrained_layout=True)
        built.domain.plot_topology(figure, axis)
        for curve in spec.curves:
            center = np.mean(curve.points, axis=0)
            axis.text(
                center[0],
                center[1],
                f"curve {built.curve_id_by_key[curve.key]}\n{curve.key}",
                ha="center",
                va="center",
                fontsize=8,
            )
        axis.set_title(f"{spec.name}: OFT topology")
        topology_path = output_dir / f"{spec.name}_topology.png"
        figure.savefig(topology_path, dpi=160)
        plt.close(figure)
        written["topology_png"] = str(topology_path)

        figure, axis = plt.subplots(figsize=(7, 6), constrained_layout=True)
        unique_ids = sorted(int(value) for value in np.unique(attributes))
        color_index = {
            region_id: index for index, region_id in enumerate(unique_ids)
        }
        face_values = np.array(
            [color_index[int(value)] for value in attributes],
            dtype=np.float64,
        )
        axis.tripcolor(
            nodes[:, 0],
            nodes[:, 1],
            triangles,
            facecolors=face_values,
            cmap="tab20",
            edgecolors="0.55",
            linewidth=0.25,
        )
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlabel("R (m)")
        axis.set_ylabel("Z (m)")
        region_counts = Counter(int(value) for value in attributes)
        counts_text = ", ".join(
            f"ID {region_id}: {region_counts[region_id]} tris"
            for region_id in unique_ids
        )
        axis.set_title(f"{spec.name}\n{counts_text}", fontsize=10)
        mesh_path = output_dir / f"{spec.name}_mesh.png"
        figure.savefig(mesh_path, dpi=180)
        plt.close(figure)
        written["mesh_png"] = str(mesh_path)
    except Exception as exc:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": f"PNG generation failed: {exc}",
            "files": written,
        }

    return {"status": STATUS_PASS, "files": written}


def _run_full_build(
    gs_domain_class: Any,
    spec: CaseSpec,
    output_dir: Path,
) -> dict[str, Any]:
    built = _build_domain(gs_domain_class, spec)
    result: dict[str, Any] = {
        "status": STATUS_FAIL,
        "input_plan": _input_plan(built),
        "before": {
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_ids_snapshot(built),
        },
    }

    try:
        points, cells, regions = built.domain.build_mesh()
        nodes = np.asarray(points)
        triangles = np.asarray(cells)
        attributes_raw = np.asarray(regions).reshape(-1)

        if not np.all(np.isfinite(attributes_raw)):
            raise ValueError("Triangle attributes contain NaN/Inf")
        if not np.all(attributes_raw == np.round(attributes_raw)):
            raise ValueError("Triangle attributes do not have integer semantics")
        attributes = attributes_raw.astype(np.int64)

        final_id_by_key = _final_id_by_key(built)
        expected_ids = set(final_id_by_key.values())
        mesh_checks = _mesh_checks(
            nodes.astype(np.float64, copy=False),
            triangles.astype(np.int64, copy=False),
            attributes,
            expected_ids,
        )
        seed_diagnostics = _seed_diagnostics(built, spec)

        result.update(
            {
                "status": (
                    STATUS_PASS
                    if mesh_checks["status"] == STATUS_PASS
                    and seed_diagnostics["status"] != STATUS_FAIL
                    else STATUS_FAIL
                ),
                "arrays": {
                    "nodes_shape": list(nodes.shape),
                    "nodes_dtype": str(nodes.dtype),
                    "triangles_shape": list(triangles.shape),
                    "triangles_dtype": str(triangles.dtype),
                    "attributes_shape": list(attributes_raw.shape),
                    "attributes_dtype": str(attributes_raw.dtype),
                    "attribute_unique_values": sorted(
                        int(value) for value in np.unique(attributes)
                    ),
                },
                "after": {
                    "region_info": _region_info_snapshot(built.domain),
                    "region_object_ids": _region_ids_snapshot(built),
                    "final_id_by_curve_key": final_id_by_key,
                },
                "mesh_checks": mesh_checks,
                "seed_diagnostics": seed_diagnostics,
                "plots": _plot_case(
                    built,
                    spec,
                    output_dir,
                    nodes.astype(np.float64, copy=False),
                    triangles.astype(np.int64, copy=False),
                    attributes,
                ),
            }
        )
    except Exception as exc:
        result["exception"] = _exception_payload(exc)

    return result


def _mapping_from_full(full: Mapping[str, Any]) -> dict[str, int] | None:
    try:
        mapping = full["after"]["final_id_by_curve_key"]
        return {str(key): int(value) for key, value in mapping.items()}
    except (KeyError, TypeError, ValueError):
        return None


def _compare_mappings(
    first: Mapping[str, int] | None,
    second: Mapping[str, int] | None,
) -> dict[str, Any]:
    if first is None or second is None:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": "One or both final Region mappings are unavailable",
        }
    return {
        "status": STATUS_PASS if dict(first) == dict(second) else STATUS_FAIL,
        "first": dict(first),
        "second": dict(second),
        "equal": dict(first) == dict(second),
    }


def _dx_variant(spec: CaseSpec) -> CaseSpec:
    factors = (0.73, 1.19, 0.81, 1.31, 0.91)
    return replace(
        spec,
        name=f"{spec.name}__dx_variant",
        curves=tuple(
            replace(curve, dx=curve.dx * factors[index % len(factors)])
            for index, curve in enumerate(spec.curves)
        ),
    )


def _run_case(
    gs_domain_class: Any,
    spec: CaseSpec,
    output_dir: Path,
) -> dict[str, Any]:
    case_result: dict[str, Any] = {
        "case": spec.name,
        "status": STATUS_FAIL,
        "setup_only": {},
        "full_build": {},
        "repeat_build": {},
        "dx_variant": {},
        "comparisons": {},
    }

    try:
        setup_result = _run_setup_only(gs_domain_class, spec)
        full_result = _run_full_build(gs_domain_class, spec, output_dir)
        repeat_result = _run_full_build(gs_domain_class, spec, output_dir)
        dx_spec = _dx_variant(spec)
        dx_result = _run_full_build(gs_domain_class, dx_spec, output_dir)

        setup_mapping = None
        try:
            setup_mapping = {
                str(key): int(value)
                for key, value in setup_result["first_call"][
                    "final_id_by_curve_key"
                ].items()
            }
        except (KeyError, TypeError, ValueError):
            pass

        full_mapping = _mapping_from_full(full_result)
        repeat_mapping = _mapping_from_full(repeat_result)
        dx_mapping = _mapping_from_full(dx_result)

        comparisons = {
            "setup_vs_triangle": _compare_mappings(
                setup_mapping,
                full_mapping,
            ),
            "fresh_rebuild": _compare_mappings(
                full_mapping,
                repeat_mapping,
            ),
            "dx_change": _compare_mappings(
                full_mapping,
                dx_mapping,
            ),
        }

        critical_statuses = [
            setup_result.get("status"),
            full_result.get("status"),
            repeat_result.get("status"),
            dx_result.get("status"),
            comparisons["setup_vs_triangle"]["status"],
            comparisons["fresh_rebuild"]["status"],
            comparisons["dx_change"]["status"],
        ]
        case_result.update(
            {
                "status": (
                    STATUS_FAIL
                    if STATUS_FAIL in critical_statuses
                    else STATUS_PASS
                ),
                "setup_only": setup_result,
                "full_build": full_result,
                "repeat_build": repeat_result,
                "dx_variant": dx_result,
                "comparisons": comparisons,
            }
        )
    except Exception as exc:
        case_result["exception"] = _exception_payload(exc)

    return case_result


def _reorder_comparison(
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    original = results.get("mixed_tree")
    reordered = results.get("reordered_input")
    if original is None or reordered is None:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": "mixed_tree or reordered_input result is unavailable",
        }

    original_mapping = _mapping_from_full(original.get("full_build", {}))
    reordered_mapping = _mapping_from_full(reordered.get("full_build", {}))
    if original_mapping is None or reordered_mapping is None:
        return {
            "status": STATUS_UNCONFIRMED,
            "reason": "Final Region mapping is unavailable",
        }

    shared_keys = sorted(set(original_mapping) & set(reordered_mapping))
    changes = {
        key: {
            "mixed_tree_region_id": original_mapping[key],
            "reordered_input_region_id": reordered_mapping[key],
            "changed": original_mapping[key] != reordered_mapping[key],
        }
        for key in shared_keys
    }
    return {
        # This comparison is observational. Either stable or changed numbering is
        # valid probe evidence, so it is not a pass/fail production requirement.
        "status": STATUS_UNCONFIRMED,
        "reason": "Observed block-order effect; no stability assumption is imposed",
        "curve_key_comparison": changes,
        "all_equal": all(not item["changed"] for item in changes.values()),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe OFT 26.6 multi-region setup, numbering, seeds, and mesh topology."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for per-case JSON, summary JSON, and optional PNG files.",
    )
    return parser.parse_args(argv)


def _oft_version() -> str:
    try:
        return version("openfusiontoolkit")
    except PackageNotFoundError as exc:
        raise RuntimeError("openfusiontoolkit is not installed") from exc


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "probe": "oft_multi_array_regions",
        "required_oft_version": REQUIRED_OFT_VERSION,
        "status": STATUS_FAIL,
        "cases": {},
    }

    try:
        detected_version = _oft_version()
        summary["detected_oft_version"] = detected_version
        if detected_version != REQUIRED_OFT_VERSION:
            raise RuntimeError(
                "OFT version mismatch: "
                f"required={REQUIRED_OFT_VERSION}, detected={detected_version}"
            )

        from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain

        specs = _base_case_specs()
        case_results: dict[str, dict[str, Any]] = {}

        for name, spec in specs.items():
            result = _run_case(gs_Domain, spec, output_dir)
            case_results[name] = result
            _write_json(output_dir / f"{name}.json", result)

        reorder = _reorder_comparison(case_results)
        critical_failures = [
            name
            for name, result in case_results.items()
            if result.get("status") == STATUS_FAIL
        ]
        summary.update(
            {
                "status": (
                    STATUS_PASS if not critical_failures else STATUS_FAIL
                ),
                "cases": {
                    name: result.get("status", STATUS_UNCONFIRMED)
                    for name, result in case_results.items()
                },
                "critical_failures": critical_failures,
                "reordered_input_comparison": reorder,
                "interpretation": {
                    "unconfirmed_is_not_pass": True,
                    "png_is_not_topology_proof": True,
                    "triangle_success_is_not_invalid_geometry_acceptance": True,
                    "production_multi_array_implementation": STATUS_NA,
                    "m3dc1_compatibility": STATUS_UNCONFIRMED,
                },
            }
        )
    except Exception as exc:
        summary["fatal_exception"] = _exception_payload(exc)

    _write_json(output_dir / "summary.json", summary)
    print(json.dumps(_json_value(summary), indent=2, sort_keys=True))
    return 0 if summary.get("status") == STATUS_PASS else 1


if __name__ == "__main__":
    sys.exit(main())
