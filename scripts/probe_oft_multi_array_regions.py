#!/usr/bin/env python3
"""Focused OFT 26.6 multi-region and Region-numbering probe.

This is an investigation script, not a LinkMesh production module.

It verifies:
- nested, sibling, and mixed multi-region mesh generation;
- OFT Region IDs exposed by region_info and Region._id;
- Triangle attributes returned for generated cells;
- numbering consistency between setup_only and full build;
- numbering stability across fresh rebuilds and dx changes;
- the observed effect of input/definition order.

The synthetic OFT technical roles used here are probe mechanics only. They are
not inferred physical semantics and must not be exposed as user physics labels.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


REQUIRED_OFT_VERSION = "26.6"

PASS = "PASS"
FAIL = "FAIL"
UNCONFIRMED = "UNCONFIRMED"
NOT_APPLICABLE = "NOT APPLICABLE"


@dataclass(frozen=True)
class CurveSpec:
    key: str
    points: np.ndarray
    parent_key: str | None
    dx: float


@dataclass(frozen=True)
class CaseSpec:
    name: str
    curves: tuple[CurveSpec, ...]


@dataclass
class BuiltDomain:
    domain: Any
    spec: CaseSpec
    curve_id_by_key: dict[str, int]
    region_name_by_key: dict[str, str]
    technical_role_by_key: dict[str, str]
    region_object_by_key: dict[str, Any]


def _ellipse(
    center_r: float,
    center_z: float,
    radius_r: float,
    radius_z: float,
    count: int = 32,
) -> np.ndarray:
    theta = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    return np.column_stack(
        (
            center_r + radius_r * np.cos(theta),
            center_z + radius_z * np.sin(theta),
        )
    ).astype(np.float64)


def _case_specs() -> dict[str, CaseSpec]:
    two_level = CaseSpec(
        "two_level_nested",
        (
            CurveSpec("root", _ellipse(5.0, 0.0, 3.0, 2.4), None, 0.42),
            CurveSpec("core", _ellipse(5.0, 0.0, 1.0, 0.75), "root", 0.16),
        ),
    )

    four_level = CaseSpec(
        "four_level_nested",
        (
            CurveSpec("root", _ellipse(5.0, 0.0, 3.6, 2.8), None, 0.48),
            CurveSpec(
                "level2",
                _ellipse(5.0, 0.0, 2.7, 2.0),
                "root",
                0.34,
            ),
            CurveSpec(
                "level3",
                _ellipse(5.0, 0.0, 1.8, 1.25),
                "level2",
                0.23,
            ),
            CurveSpec(
                "level4",
                _ellipse(5.0, 0.0, 0.8, 0.52),
                "level3",
                0.13,
            ),
        ),
    )

    siblings = CaseSpec(
        "one_parent_two_siblings",
        (
            CurveSpec("root", _ellipse(5.0, 0.0, 3.8, 2.6), None, 0.44),
            CurveSpec(
                "left",
                _ellipse(3.7, 0.0, 0.72, 0.58),
                "root",
                0.14,
            ),
            CurveSpec(
                "right",
                _ellipse(6.3, 0.0, 0.82, 0.62),
                "root",
                0.22,
            ),
        ),
    )

    mixed = CaseSpec(
        "mixed_tree",
        (
            CurveSpec("root", _ellipse(5.0, 0.0, 4.0, 2.8), None, 0.46),
            CurveSpec(
                "left",
                _ellipse(3.45, 0.0, 1.15, 0.90),
                "root",
                0.25,
            ),
            CurveSpec(
                "left_core",
                _ellipse(3.45, 0.0, 0.42, 0.31),
                "left",
                0.11,
            ),
            CurveSpec(
                "right",
                _ellipse(6.55, 0.0, 0.86, 0.65),
                "root",
                0.18,
            ),
        ),
    )

    mixed_by_key = {curve.key: curve for curve in mixed.curves}
    reordered = CaseSpec(
        "reordered_input",
        tuple(
            mixed_by_key[key]
            for key in ("right", "left_core", "root", "left")
        ),
    )

    return {
        case.name: case
        for case in (
            two_level,
            four_level,
            siblings,
            mixed,
            reordered,
        )
    }


def _children_by_key(spec: CaseSpec) -> dict[str, list[str]]:
    result = {curve.key: [] for curve in spec.curves}
    for curve in spec.curves:
        if curve.parent_key is not None:
            result[curve.parent_key].append(curve.key)
    return result


def _depth_by_key(spec: CaseSpec) -> dict[str, int]:
    curves = {curve.key: curve for curve in spec.curves}
    depths: dict[str, int] = {}

    def get_depth(key: str) -> int:
        if key in depths:
            return depths[key]

        parent = curves[key].parent_key
        value = 0 if parent is None else get_depth(parent) + 1
        depths[key] = value
        return value

    for key in curves:
        get_depth(key)

    return depths


def _select_probe_plasma_key(spec: CaseSpec) -> str:
    """Choose one deterministic deepest Region for OFT probe mechanics."""

    depths = _depth_by_key(spec)
    return min(
        (curve.key for curve in spec.curves),
        key=lambda key: (-depths[key], key),
    )


def _canonical_region_name(curve_key: str) -> str:
    """Use the same canonical form that OFT exposes in region_info."""

    return f"LM_{curve_key.upper()}"


def _canonicalize_region_info(
    region_info: Mapping[str, Any],
) -> dict[str, Any]:
    canonical: dict[str, Any] = {}

    for raw_name, value in region_info.items():
        name = str(raw_name).upper()
        if name in canonical:
            raise RuntimeError(
                f"OFT region_info has duplicate canonical name {name!r}"
            )
        canonical[name] = value

    return canonical


def _build_domain(gs_domain_class: Any, spec: CaseSpec) -> BuiltDomain:
    domain = gs_domain_class()

    curve_id_by_key = {
        curve.key: index
        for index, curve in enumerate(spec.curves, start=1)
    }
    region_name_by_key = {
        curve.key: _canonical_region_name(curve.key)
        for curve in spec.curves
    }

    plasma_key = _select_probe_plasma_key(spec)
    technical_role_by_key: dict[str, str] = {}

    # These are OFT technical roles required by this probe. They are not
    # user-facing physical labels and are not inferred from geometry.
    for curve in spec.curves:
        if curve.parent_key is None:
            role = "boundary"
        elif curve.key == plasma_key:
            role = "plasma"
        else:
            role = "vacuum"

        technical_role_by_key[curve.key] = role
        domain.define_region(
            region_name_by_key[curve.key],
            curve.dx,
            role,
        )

    region_object_by_key: dict[str, Any] = {}

    for curve in spec.curves:
        parent_name = (
            None
            if curve.parent_key is None
            else region_name_by_key[curve.parent_key]
        )

        before_count = len(domain.regions)
        domain.add_polygon(
            np.array(curve.points, dtype=np.float64, copy=True),
            region_name_by_key[curve.key],
            parent_name=parent_name,
        )

        if len(domain.regions) != before_count + 1:
            raise RuntimeError(
                "add_polygon did not add exactly one Region for "
                f"{curve.key!r}"
            )

        region_object_by_key[curve.key] = domain.regions[-1]

    return BuiltDomain(
        domain=domain,
        spec=spec,
        curve_id_by_key=curve_id_by_key,
        region_name_by_key=region_name_by_key,
        technical_role_by_key=technical_role_by_key,
        region_object_by_key=region_object_by_key,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            _json_value(payload),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _exception_payload(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def _input_plan(built: BuiltDomain) -> list[dict[str, Any]]:
    children = _children_by_key(built.spec)

    return [
        {
            "input_index": index,
            "curve_id": built.curve_id_by_key[curve.key],
            "curve_key": curve.key,
            "region_name": built.region_name_by_key[curve.key],
            "technical_role": built.technical_role_by_key[curve.key],
            "physical_label": "",
            "parent_key": curve.parent_key,
            "children_keys": children[curve.key],
            "dx_m": curve.dx,
            "point_count": int(curve.points.shape[0]),
        }
        for index, curve in enumerate(built.spec.curves, start=1)
    ]


def _region_info_snapshot(domain: Any) -> dict[str, Any]:
    info = getattr(domain, "region_info", None)
    if info is None:
        return {}
    return _json_value(info)


def _region_object_ids(built: BuiltDomain) -> dict[str, Any]:
    return {
        key: _json_value(getattr(region, "_id", None))
        for key, region in built.region_object_by_key.items()
    }


def _final_id_by_key(built: BuiltDomain) -> dict[str, int]:
    raw_region_info = getattr(built.domain, "region_info", None)
    if raw_region_info is None:
        raise RuntimeError("domain.region_info is unavailable")

    region_info = _canonicalize_region_info(raw_region_info)
    result: dict[str, int] = {}

    for curve_key, expected_name in built.region_name_by_key.items():
        canonical_name = expected_name.upper()

        if canonical_name not in region_info:
            raise KeyError(
                f"{canonical_name!r} is absent from OFT region_info; "
                f"available names={sorted(region_info)}"
            )

        raw_id = region_info[canonical_name].get("id")
        if raw_id is None:
            raise RuntimeError(
                f"OFT region_info[{canonical_name!r}] has no id"
            )

        numeric_id = float(raw_id)
        if not math.isfinite(numeric_id):
            raise RuntimeError(
                f"OFT Region ID is not finite: {canonical_name}={raw_id!r}"
            )
        if numeric_id != round(numeric_id):
            raise RuntimeError(
                "OFT Region ID does not have integer semantics: "
                f"{canonical_name}={raw_id!r}"
            )

        result[curve_key] = int(round(numeric_id))

    ids = list(result.values())
    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"OFT assigned duplicate Region IDs: {result}"
        )

    return result


def _region_object_id_check(
    built: BuiltDomain,
    final_id_by_key: Mapping[str, int],
) -> dict[str, Any]:
    observed = _region_object_ids(built)
    mismatches: dict[str, Any] = {}

    for key, expected in final_id_by_key.items():
        raw_value = observed.get(key)

        try:
            actual = int(raw_value)
        except (TypeError, ValueError):
            mismatches[key] = {
                "region_info_id": expected,
                "region_object_id": raw_value,
            }
            continue

        if actual != expected:
            mismatches[key] = {
                "region_info_id": expected,
                "region_object_id": actual,
            }

    return {
        "status": PASS if not mismatches else FAIL,
        "observed": observed,
        "mismatches": mismatches,
    }


def _run_setup_only(
    gs_domain_class: Any,
    spec: CaseSpec,
) -> dict[str, Any]:
    built = _build_domain(gs_domain_class, spec)

    result: dict[str, Any] = {
        "status": UNCONFIRMED,
        "generation_status": NOT_APPLICABLE,
        "numbering_status": UNCONFIRMED,
        "input_plan": _input_plan(built),
        "before": {
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_object_ids(built),
            "has_mesh": hasattr(built.domain, "mesh"),
        },
    }

    try:
        returned = built.domain.build_mesh(setup_only=True)
    except Exception as exc:
        result.update(
            {
                "status": FAIL,
                "numbering_status": FAIL,
                "exception": _exception_payload(exc),
            }
        )
        return result

    result["setup_completed"] = True
    result["return_value"] = _json_value(returned)
    result["has_mesh_after_setup"] = hasattr(built.domain, "mesh")

    try:
        final_mapping = _final_id_by_key(built)
        object_check = _region_object_id_check(
            built,
            final_mapping,
        )
    except Exception as exc:
        result.update(
            {
                "status": FAIL,
                "numbering_status": FAIL,
                "numbering_exception": _exception_payload(exc),
            }
        )
        return result

    result.update(
        {
            "status": (
                PASS if object_check["status"] == PASS else FAIL
            ),
            "numbering_status": object_check["status"],
            "after": {
                "region_info": _region_info_snapshot(built.domain),
                "region_object_ids": _region_object_ids(built),
                "final_id_by_curve_key": final_mapping,
                "region_object_id_check": object_check,
            },
        }
    )

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
        PASS
        if nodes.ndim == 2
        and nodes.shape[1] == 2
        and nodes.shape[0] >= 3
        else FAIL
    )
    checks["triangles_shape"] = (
        PASS
        if triangles.ndim == 2
        and triangles.shape[1] == 3
        and triangles.shape[0] > 0
        else FAIL
    )
    checks["attributes_shape"] = (
        PASS
        if attributes.ndim == 1
        and attributes.shape[0] == triangles.shape[0]
        else FAIL
    )

    checks["finite_nodes"] = (
        PASS if np.all(np.isfinite(nodes)) else FAIL
    )
    checks["finite_attributes"] = (
        PASS if np.all(np.isfinite(attributes)) else FAIL
    )

    index_range_valid = (
        triangles.size > 0
        and int(triangles.min()) >= 0
        and int(triangles.max()) < nodes.shape[0]
    )
    checks["index_range"] = PASS if index_range_valid else FAIL

    repeated_vertex = np.any(
        (triangles[:, 0] == triangles[:, 1])
        | (triangles[:, 1] == triangles[:, 2])
        | (triangles[:, 0] == triangles[:, 2])
    )
    checks["distinct_triangle_vertices"] = (
        FAIL if repeated_vertex else PASS
    )

    signed_double_area = _signed_double_areas(nodes, triangles)
    absolute_double_area = np.abs(signed_double_area)

    coordinate_scale = max(
        1.0,
        float(np.ptp(nodes[:, 0])),
        float(np.ptp(nodes[:, 1])),
        float(np.max(np.abs(nodes))),
    )
    area_tolerance = 1.0e-12 * coordinate_scale * coordinate_scale

    near_zero_count = int(
        np.count_nonzero(absolute_double_area <= area_tolerance)
    )
    positive_count = int(
        np.count_nonzero(signed_double_area > area_tolerance)
    )
    negative_count = int(
        np.count_nonzero(signed_double_area < -area_tolerance)
    )

    checks["nondegenerate_triangles"] = (
        PASS if near_zero_count == 0 else FAIL
    )

    if near_zero_count:
        orientation = "contains_degenerate"
        orientation_status = FAIL
    elif positive_count and not negative_count:
        orientation = "counter_clockwise"
        orientation_status = PASS
    elif negative_count and not positive_count:
        orientation = "clockwise"
        orientation_status = PASS
    else:
        orientation = "mixed"
        orientation_status = UNCONFIRMED

    checks["orientation"] = orientation_status
    details["triangle_area"] = {
        "minimum_absolute_double_area": float(
            absolute_double_area.min()
        ),
        "maximum_absolute_double_area": float(
            absolute_double_area.max()
        ),
        "tolerance": area_tolerance,
        "near_zero_count": near_zero_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "orientation": orientation,
    }

    canonical_triangles = np.sort(
        triangles.astype(np.int64),
        axis=1,
    )
    duplicate_count = int(
        triangles.shape[0]
        - np.unique(canonical_triangles, axis=0).shape[0]
    )
    checks["no_duplicate_triangles"] = (
        PASS if duplicate_count == 0 else FAIL
    )
    details["duplicate_triangle_count"] = duplicate_count

    edge_to_triangles: dict[
        tuple[int, int],
        list[int],
    ] = defaultdict(list)

    for triangle_index, triangle in enumerate(triangles):
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge = tuple(sorted((int(first), int(second))))
            edge_to_triangles[edge].append(triangle_index)

    incidence_counts = Counter(
        len(adjacent)
        for adjacent in edge_to_triangles.values()
    )
    nonmanifold_edges = [
        edge
        for edge, adjacent in edge_to_triangles.items()
        if len(adjacent) > 2
    ]

    checks["manifold_edge_incidence"] = (
        PASS if not nonmanifold_edges else FAIL
    )
    details["edge_incidence_counts"] = {
        str(count): int(total)
        for count, total in sorted(incidence_counts.items())
    }
    details["nonmanifold_edge_count"] = len(nonmanifold_edges)

    interface_counts: Counter[tuple[int, int]] = Counter()

    for adjacent in edge_to_triangles.values():
        if len(adjacent) != 2:
            continue

        first_region = int(attributes[adjacent[0]])
        second_region = int(attributes[adjacent[1]])

        if first_region != second_region:
            interface_counts[
                tuple(sorted((first_region, second_region)))
            ] += 1

    details["shared_interface_edge_counts"] = {
        f"{first}-{second}": int(count)
        for (first, second), count in sorted(interface_counts.items())
    }

    observed_ids = {
        int(value)
        for value in np.unique(attributes)
    }

    checks["region_id_set"] = (
        PASS if observed_ids == expected_region_ids else FAIL
    )

    region_triangle_counts = Counter(
        int(value)
        for value in attributes
    )
    checks["every_region_has_triangles"] = (
        PASS
        if all(
            region_triangle_counts[region_id] > 0
            for region_id in expected_region_ids
        )
        else FAIL
    )

    details["expected_region_ids"] = sorted(expected_region_ids)
    details["observed_region_ids"] = sorted(observed_ids)
    details["region_triangle_counts"] = {
        str(region_id): int(region_triangle_counts[region_id])
        for region_id in sorted(
            observed_ids | expected_region_ids
        )
    }

    if FAIL in checks.values():
        status = FAIL
    elif UNCONFIRMED in checks.values():
        status = UNCONFIRMED
    else:
        status = PASS

    return {
        "status": status,
        "checks": checks,
        "details": details,
    }


def _plot_mesh(
    spec: CaseSpec,
    variant: str,
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
            "status": UNCONFIRMED,
            "reason": f"Matplotlib unavailable: {exc}",
        }

    try:
        figure, axis = plt.subplots(
            figsize=(7, 6),
            constrained_layout=True,
        )

        unique_ids = sorted(
            int(value)
            for value in np.unique(attributes)
        )
        color_index = {
            region_id: index
            for index, region_id in enumerate(unique_ids)
        }
        face_values = np.array(
            [
                color_index[int(value)]
                for value in attributes
            ],
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

        counts = Counter(
            int(value)
            for value in attributes
        )
        counts_text = ", ".join(
            f"ID {region_id}: {counts[region_id]} cells"
            for region_id in unique_ids
        )
        axis.set_title(
            f"{spec.name} [{variant}]\n{counts_text}",
            fontsize=10,
        )

        path = output_dir / f"{spec.name}__{variant}_mesh.png"
        figure.savefig(path, dpi=180)
        plt.close(figure)

        return {
            "status": PASS,
            "path": str(path),
        }
    except Exception as exc:
        return {
            "status": UNCONFIRMED,
            "reason": f"Mesh PNG generation failed: {exc}",
        }


def _run_full_build(
    gs_domain_class: Any,
    spec: CaseSpec,
    output_dir: Path,
    variant: str,
) -> dict[str, Any]:
    built = _build_domain(gs_domain_class, spec)

    result: dict[str, Any] = {
        "variant": variant,
        "status": UNCONFIRMED,
        "generation_status": UNCONFIRMED,
        "mesh_structure_status": UNCONFIRMED,
        "numbering_status": UNCONFIRMED,
        "plot_status": UNCONFIRMED,
        "input_plan": _input_plan(built),
        "before": {
            "region_info": _region_info_snapshot(built.domain),
            "region_object_ids": _region_object_ids(built),
        },
    }

    try:
        points, cells, regions = built.domain.build_mesh()
    except Exception as exc:
        result.update(
            {
                "status": FAIL,
                "generation_status": FAIL,
                "generation_exception": _exception_payload(exc),
            }
        )
        return result

    # Generation is complete at this point. Later diagnostic failures must not
    # overwrite this status.
    result["generation_status"] = PASS

    nodes = np.asarray(points, dtype=np.float64)
    triangles = np.asarray(cells, dtype=np.int64)
    raw_attributes = np.asarray(regions).reshape(-1)

    result["arrays"] = {
        "nodes_shape": list(nodes.shape),
        "nodes_dtype": str(nodes.dtype),
        "triangles_shape": list(triangles.shape),
        "triangles_dtype": str(triangles.dtype),
        "attributes_shape": list(raw_attributes.shape),
        "attributes_dtype": str(raw_attributes.dtype),
    }

    try:
        if not np.all(np.isfinite(raw_attributes)):
            raise ValueError(
                "Triangle attributes contain NaN or infinity"
            )
        if not np.all(raw_attributes == np.round(raw_attributes)):
            raise ValueError(
                "Triangle attributes do not have integer semantics"
            )

        attributes = raw_attributes.astype(np.int64)

        final_id_by_key = _final_id_by_key(built)
        object_id_check = _region_object_id_check(
            built,
            final_id_by_key,
        )
        expected_ids = set(final_id_by_key.values())
        observed_ids = {
            int(value)
            for value in np.unique(attributes)
        }

        attribute_check = {
            "status": (
                PASS if observed_ids == expected_ids else FAIL
            ),
            "expected_ids": sorted(expected_ids),
            "triangle_attribute_ids": sorted(observed_ids),
        }

        result["numbering_status"] = (
            PASS
            if object_id_check["status"] == PASS
            and attribute_check["status"] == PASS
            else FAIL
        )
        result["numbering"] = {
            "final_id_by_curve_key": final_id_by_key,
            "region_object_id_check": object_id_check,
            "triangle_attribute_check": attribute_check,
            "region_info": _region_info_snapshot(built.domain),
        }
    except Exception as exc:
        result["numbering_status"] = FAIL
        result["numbering_exception"] = _exception_payload(exc)
        attributes = raw_attributes.astype(np.int64, copy=False)
        expected_ids = {
            int(value)
            for value in np.unique(attributes)
        }

    try:
        mesh_checks = _mesh_checks(
            nodes,
            triangles,
            attributes,
            expected_ids,
        )
        result["mesh_checks"] = mesh_checks
        result["mesh_structure_status"] = mesh_checks["status"]
    except Exception as exc:
        result["mesh_structure_status"] = FAIL
        result["mesh_structure_exception"] = _exception_payload(exc)

    plot_result = _plot_mesh(
        spec,
        variant,
        output_dir,
        nodes,
        triangles,
        attributes,
    )
    result["plot"] = plot_result
    result["plot_status"] = plot_result["status"]

    critical = (
        result["generation_status"],
        result["mesh_structure_status"],
        result["numbering_status"],
    )

    if FAIL in critical:
        result["status"] = FAIL
    elif UNCONFIRMED in critical:
        result["status"] = UNCONFIRMED
    else:
        result["status"] = PASS

    return result


def _mapping_from_setup(
    result: Mapping[str, Any],
) -> dict[str, int] | None:
    try:
        mapping = result["after"]["final_id_by_curve_key"]
        return {
            str(key): int(value)
            for key, value in mapping.items()
        }
    except (KeyError, TypeError, ValueError):
        return None


def _mapping_from_build(
    result: Mapping[str, Any],
) -> dict[str, int] | None:
    try:
        mapping = result["numbering"]["final_id_by_curve_key"]
        return {
            str(key): int(value)
            for key, value in mapping.items()
        }
    except (KeyError, TypeError, ValueError):
        return None


def _compare_mappings(
    first: Mapping[str, int] | None,
    second: Mapping[str, int] | None,
    *,
    observational: bool = False,
) -> dict[str, Any]:
    if first is None or second is None:
        return {
            "status": UNCONFIRMED,
            "reason": "One or both Region mappings are unavailable",
        }

    equal = dict(first) == dict(second)

    return {
        "status": (
            UNCONFIRMED
            if observational
            else (PASS if equal else FAIL)
        ),
        "equal": equal,
        "first": dict(first),
        "second": dict(second),
        "reason": (
            "Observed input-order effect; equality is not required"
            if observational
            else None
        ),
    }


def _dx_variant(spec: CaseSpec) -> CaseSpec:
    factors = (0.73, 1.19, 0.81, 1.31, 0.91)

    return replace(
        spec,
        name=spec.name,
        curves=tuple(
            replace(
                curve,
                dx=curve.dx * factors[index % len(factors)],
            )
            for index, curve in enumerate(spec.curves)
        ),
    )


def _run_case(
    gs_domain_class: Any,
    spec: CaseSpec,
    output_dir: Path,
) -> dict[str, Any]:
    setup = _run_setup_only(gs_domain_class, spec)
    full = _run_full_build(
        gs_domain_class,
        spec,
        output_dir,
        "full",
    )
    repeat = _run_full_build(
        gs_domain_class,
        spec,
        output_dir,
        "repeat",
    )
    dx_result = _run_full_build(
        gs_domain_class,
        _dx_variant(spec),
        output_dir,
        "dx_variant",
    )

    setup_mapping = _mapping_from_setup(setup)
    full_mapping = _mapping_from_build(full)
    repeat_mapping = _mapping_from_build(repeat)
    dx_mapping = _mapping_from_build(dx_result)

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

    generation_statuses = [
        full["generation_status"],
        repeat["generation_status"],
        dx_result["generation_status"],
    ]
    structure_statuses = [
        full["mesh_structure_status"],
        repeat["mesh_structure_status"],
        dx_result["mesh_structure_status"],
    ]
    numbering_statuses = [
        setup["numbering_status"],
        full["numbering_status"],
        repeat["numbering_status"],
        dx_result["numbering_status"],
        comparisons["setup_vs_triangle"]["status"],
        comparisons["fresh_rebuild"]["status"],
        comparisons["dx_change"]["status"],
    ]

    generation_status = (
        FAIL if FAIL in generation_statuses else PASS
    )

    if FAIL in structure_statuses:
        structure_status = FAIL
    elif UNCONFIRMED in structure_statuses:
        structure_status = UNCONFIRMED
    else:
        structure_status = PASS

    if FAIL in numbering_statuses:
        numbering_status = FAIL
    elif UNCONFIRMED in numbering_statuses:
        numbering_status = UNCONFIRMED
    else:
        numbering_status = PASS

    critical = (
        generation_status,
        structure_status,
        numbering_status,
    )

    if FAIL in critical:
        overall = FAIL
    elif UNCONFIRMED in critical:
        overall = UNCONFIRMED
    else:
        overall = PASS

    return {
        "case": spec.name,
        "overall_status": overall,
        "generation_status": generation_status,
        "mesh_structure_status": structure_status,
        "numbering_status": numbering_status,
        "setup_only": setup,
        "full_build": full,
        "repeat_build": repeat,
        "dx_variant": dx_result,
        "comparisons": comparisons,
    }


def _reordered_input_comparison(
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    mixed = results.get("mixed_tree")
    reordered = results.get("reordered_input")

    if mixed is None or reordered is None:
        return {
            "status": UNCONFIRMED,
            "reason": "Required cases are unavailable",
        }

    mixed_mapping = _mapping_from_build(
        mixed.get("full_build", {})
    )
    reordered_mapping = _mapping_from_build(
        reordered.get("full_build", {})
    )

    comparison = _compare_mappings(
        mixed_mapping,
        reordered_mapping,
        observational=True,
    )

    if mixed_mapping is not None and reordered_mapping is not None:
        keys = sorted(set(mixed_mapping) & set(reordered_mapping))
        comparison["curve_key_comparison"] = {
            key: {
                "mixed_tree_region_id": mixed_mapping[key],
                "reordered_input_region_id": reordered_mapping[key],
                "changed": (
                    mixed_mapping[key] != reordered_mapping[key]
                ),
            }
            for key in keys
        }

    return comparison


def _detected_oft_version() -> str:
    try:
        return version("openfusiontoolkit")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "openfusiontoolkit is not installed"
        ) from exc


def _prepare_output_dir(path: Path) -> Path:
    output_dir = path.expanduser().resolve()

    if output_dir.exists():
        if not output_dir.is_dir():
            raise RuntimeError(
                f"Output path exists and is not a directory: {output_dir}"
            )
        if any(output_dir.iterdir()):
            raise RuntimeError(
                "Output directory already exists and is not empty: "
                f"{output_dir}. Use a new directory."
            )
    else:
        output_dir.mkdir(parents=True)

    return output_dir


def _parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe OFT 26.6 multi-region generation and numbering."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New or empty output directory for JSON and PNG results.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    summary: dict[str, Any] = {
        "probe": "oft_multi_array_regions_numbering",
        "required_oft_version": REQUIRED_OFT_VERSION,
        "status": FAIL,
        "cases": {},
    }

    try:
        output_dir = _prepare_output_dir(args.output_dir)
        detected_version = _detected_oft_version()
        summary["detected_oft_version"] = detected_version

        if detected_version != REQUIRED_OFT_VERSION:
            raise RuntimeError(
                "OFT version mismatch: "
                f"required={REQUIRED_OFT_VERSION}, "
                f"detected={detected_version}"
            )

        from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain

        specs = _case_specs()
        results: dict[str, dict[str, Any]] = {}

        for case_name, spec in specs.items():
            result = _run_case(
                gs_Domain,
                spec,
                output_dir,
            )
            results[case_name] = result
            _write_json(
                output_dir / f"{case_name}.json",
                result,
            )

        reorder_comparison = _reordered_input_comparison(results)

        generation_failures = [
            name
            for name, result in results.items()
            if result["generation_status"] == FAIL
        ]
        structural_failures = [
            name
            for name, result in results.items()
            if result["mesh_structure_status"] == FAIL
        ]
        numbering_failures = [
            name
            for name, result in results.items()
            if result["numbering_status"] == FAIL
        ]
        unconfirmed_cases = [
            name
            for name, result in results.items()
            if result["overall_status"] == UNCONFIRMED
        ]
        fully_passed_cases = [
            name
            for name, result in results.items()
            if result["overall_status"] == PASS
        ]

        critical_failures = sorted(
            set(
                generation_failures
                + structural_failures
                + numbering_failures
            )
        )

        if critical_failures:
            overall_status = FAIL
        elif unconfirmed_cases:
            overall_status = UNCONFIRMED
        else:
            overall_status = PASS

        summary.update(
            {
                "status": overall_status,
                "cases": {
                    name: {
                        "overall_status": result["overall_status"],
                        "generation_status": result[
                            "generation_status"
                        ],
                        "mesh_structure_status": result[
                            "mesh_structure_status"
                        ],
                        "numbering_status": result[
                            "numbering_status"
                        ],
                    }
                    for name, result in results.items()
                },
                "generation_failures": generation_failures,
                "structural_failures": structural_failures,
                "numbering_failures": numbering_failures,
                "critical_failures": critical_failures,
                "unconfirmed_cases": unconfirmed_cases,
                "fully_passed_cases": fully_passed_cases,
                "reordered_input_comparison": reorder_comparison,
                "interpretation": {
                    "oft_technical_roles_are_probe_mechanics": True,
                    "oft_technical_roles_are_not_user_physical_labels": True,
                    "physical_label_may_be_empty": True,
                    "production_multi_array_implementation": NOT_APPLICABLE,
                    "m3dc1_compatibility": UNCONFIRMED,
                    "input_reorder_comparison_is_observational": True,
                },
            }
        )
    except Exception as exc:
        summary["fatal_exception"] = _exception_payload(exc)

    if "output_dir" in locals():
        _write_json(
            output_dir / "summary.json",
            summary,
        )

    print(
        json.dumps(
            _json_value(summary),
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if summary.get("status") == PASS else 1


if __name__ == "__main__":
    sys.exit(main())