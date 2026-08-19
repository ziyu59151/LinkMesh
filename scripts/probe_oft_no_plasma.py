#!/usr/bin/env python3
"""Minimal OFT 26.6 no-plasma multi-region probe.

This companion probe answers one narrow question:

Can OFT's gs_Domain generate nested multi-region meshes when the outer
Region uses the "boundary" technical role and every internal Region uses
the "vacuum" technical role, with no "plasma" Region?

OFT technical roles in this script are adapter mechanics, not user-facing
physical labels.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from collections import Counter
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


REQUIRED_OFT_VERSION = "26.6"

PASS = "PASS"
FAIL = "FAIL"
UNCONFIRMED = "UNCONFIRMED"


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
    region_name_by_key: dict[str, str]
    technical_role_by_key: dict[str, str]


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
        name="two_level_no_plasma",
        curves=(
            CurveSpec(
                key="root",
                points=_ellipse(5.0, 0.0, 3.0, 2.4),
                parent_key=None,
                dx=0.42,
            ),
            CurveSpec(
                key="core",
                points=_ellipse(5.0, 0.0, 1.0, 0.75),
                parent_key="root",
                dx=0.16,
            ),
        ),
    )

    four_level = CaseSpec(
        name="four_level_no_plasma",
        curves=(
            CurveSpec(
                key="root",
                points=_ellipse(5.0, 0.0, 3.6, 2.8),
                parent_key=None,
                dx=0.48,
            ),
            CurveSpec(
                key="level2",
                points=_ellipse(5.0, 0.0, 2.7, 2.0),
                parent_key="root",
                dx=0.34,
            ),
            CurveSpec(
                key="level3",
                points=_ellipse(5.0, 0.0, 1.8, 1.25),
                parent_key="level2",
                dx=0.23,
            ),
            CurveSpec(
                key="level4",
                points=_ellipse(5.0, 0.0, 0.8, 0.52),
                parent_key="level3",
                dx=0.13,
            ),
        ),
    )

    return {
        two_level.name: two_level,
        four_level.name: four_level,
    }


def _region_name(key: str) -> str:
    return f"LM_{key.upper()}"


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


def _detected_oft_version() -> str:
    try:
        return version("openfusiontoolkit")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "openfusiontoolkit is not installed"
        ) from exc


def _build_domain(gs_domain_class: Any, spec: CaseSpec) -> BuiltDomain:
    domain = gs_domain_class()

    region_name_by_key = {
        curve.key: _region_name(curve.key)
        for curve in spec.curves
    }
    technical_role_by_key: dict[str, str] = {}

    root_count = sum(
        curve.parent_key is None
        for curve in spec.curves
    )
    if root_count != 1:
        raise ValueError(
            f"{spec.name} must have exactly one root, got {root_count}"
        )

    for curve in spec.curves:
        role = "boundary" if curve.parent_key is None else "vacuum"
        technical_role_by_key[curve.key] = role

        domain.define_region(
            region_name_by_key[curve.key],
            curve.dx,
            role,
        )

    for curve in spec.curves:
        parent_name = (
            None
            if curve.parent_key is None
            else region_name_by_key[curve.parent_key]
        )

        domain.add_polygon(
            np.array(
                curve.points,
                dtype=np.float64,
                copy=True,
            ),
            region_name_by_key[curve.key],
            parent_name=parent_name,
        )

    if "plasma" in technical_role_by_key.values():
        raise RuntimeError(
            "Probe construction error: a plasma role was assigned"
        )

    return BuiltDomain(
        domain=domain,
        spec=spec,
        region_name_by_key=region_name_by_key,
        technical_role_by_key=technical_role_by_key,
    )


def _canonical_region_info(domain: Any) -> dict[str, Any]:
    raw_info = getattr(domain, "region_info", None)
    if raw_info is None:
        raise RuntimeError("domain.region_info is unavailable")

    result: dict[str, Any] = {}

    for raw_name, info in raw_info.items():
        name = str(raw_name).upper()
        if name in result:
            raise RuntimeError(
                f"Duplicate canonical Region name: {name}"
            )
        result[name] = info

    return result


def _final_id_by_key(built: BuiltDomain) -> dict[str, int]:
    region_info = _canonical_region_info(built.domain)
    result: dict[str, int] = {}

    for key, expected_name in built.region_name_by_key.items():
        name = expected_name.upper()

        if name not in region_info:
            raise KeyError(
                f"{name!r} is absent from region_info; "
                f"available={sorted(region_info)}"
            )

        raw_id = region_info[name].get("id")
        if raw_id is None:
            raise RuntimeError(
                f"region_info[{name!r}] has no id"
            )

        numeric_id = float(raw_id)
        if not math.isfinite(numeric_id):
            raise RuntimeError(
                f"Region ID is not finite: {name}={raw_id!r}"
            )
        if numeric_id != round(numeric_id):
            raise RuntimeError(
                f"Region ID is not integral: {name}={raw_id!r}"
            )

        result[key] = int(round(numeric_id))

    ids = list(result.values())
    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"OFT assigned duplicate Region IDs: {result}"
        )

    return result


def _input_plan(built: BuiltDomain) -> list[dict[str, Any]]:
    return [
        {
            "curve_id": index,
            "curve_key": curve.key,
            "region_name": built.region_name_by_key[curve.key],
            "parent_key": curve.parent_key,
            "oft_technical_role": built.technical_role_by_key[curve.key],
            "physical_label": "",
            "dx_m": curve.dx,
            "point_count": int(curve.points.shape[0]),
        }
        for index, curve in enumerate(
            built.spec.curves,
            start=1,
        )
    ]


def _run_setup_only(
    gs_domain_class: Any,
    spec: CaseSpec,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": UNCONFIRMED,
    }

    try:
        built = _build_domain(gs_domain_class, spec)
        result["input_plan"] = _input_plan(built)
        result["plasma_region_count"] = sum(
            role == "plasma"
            for role in built.technical_role_by_key.values()
        )

        returned = built.domain.build_mesh(setup_only=True)
        final_mapping = _final_id_by_key(built)

        result.update(
            {
                "status": PASS,
                "return_value": _json_value(returned),
                "final_id_by_curve_key": final_mapping,
                "region_info": _json_value(
                    built.domain.region_info
                ),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": FAIL,
                "exception": _exception_payload(exc),
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
        (p1[:, 0] - p0[:, 0])
        * (p2[:, 1] - p0[:, 1])
        - (p2[:, 0] - p0[:, 0])
        * (p1[:, 1] - p0[:, 1])
    )


def _run_full_build(
    gs_domain_class: Any,
    spec: CaseSpec,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": UNCONFIRMED,
        "generation_status": UNCONFIRMED,
        "structure_status": UNCONFIRMED,
        "numbering_status": UNCONFIRMED,
    }

    try:
        built = _build_domain(gs_domain_class, spec)
        result["input_plan"] = _input_plan(built)
        result["plasma_region_count"] = sum(
            role == "plasma"
            for role in built.technical_role_by_key.values()
        )

        points, cells, regions = built.domain.build_mesh()
        result["generation_status"] = PASS

        nodes = np.asarray(points, dtype=np.float64)
        triangles = np.asarray(cells, dtype=np.int64)
        raw_attributes = np.asarray(regions).reshape(-1)

        if not np.all(np.isfinite(raw_attributes)):
            raise ValueError(
                "Triangle attributes contain NaN or infinity"
            )
        if not np.all(
            raw_attributes == np.round(raw_attributes)
        ):
            raise ValueError(
                "Triangle attributes do not have integer semantics"
            )

        attributes = raw_attributes.astype(np.int64)
        final_mapping = _final_id_by_key(built)
        expected_ids = set(final_mapping.values())
        observed_ids = {
            int(value)
            for value in np.unique(attributes)
        }

        result["arrays"] = {
            "nodes_shape": list(nodes.shape),
            "triangles_shape": list(triangles.shape),
            "attributes_shape": list(attributes.shape),
            "attribute_unique_values": sorted(observed_ids),
        }

        numbering_checks = {
            "expected_ids": sorted(expected_ids),
            "observed_triangle_attribute_ids": sorted(observed_ids),
            "id_sets_equal": expected_ids == observed_ids,
            "final_id_by_curve_key": final_mapping,
        }
        result["numbering"] = numbering_checks
        result["numbering_status"] = (
            PASS
            if numbering_checks["id_sets_equal"]
            else FAIL
        )

        shape_ok = (
            nodes.ndim == 2
            and nodes.shape[1] == 2
            and nodes.shape[0] >= 3
            and triangles.ndim == 2
            and triangles.shape[1] == 3
            and triangles.shape[0] > 0
            and attributes.ndim == 1
            and attributes.shape[0] == triangles.shape[0]
        )

        finite_ok = (
            np.all(np.isfinite(nodes))
            and np.all(np.isfinite(attributes))
        )

        index_ok = (
            triangles.size > 0
            and int(triangles.min()) >= 0
            and int(triangles.max()) < nodes.shape[0]
        )

        distinct_vertices = not np.any(
            (triangles[:, 0] == triangles[:, 1])
            | (triangles[:, 1] == triangles[:, 2])
            | (triangles[:, 0] == triangles[:, 2])
        )

        signed_areas = _signed_double_areas(
            nodes,
            triangles,
        )
        coordinate_scale = max(
            1.0,
            float(np.ptp(nodes[:, 0])),
            float(np.ptp(nodes[:, 1])),
            float(np.max(np.abs(nodes))),
        )
        area_tolerance = (
            1.0e-12
            * coordinate_scale
            * coordinate_scale
        )
        nondegenerate = bool(
            np.all(
                np.abs(signed_areas) > area_tolerance
            )
        )

        region_counts = Counter(
            int(value)
            for value in attributes
        )
        all_regions_populated = all(
            region_counts[region_id] > 0
            for region_id in expected_ids
        )

        structure_checks = {
            "shape_ok": shape_ok,
            "finite_ok": bool(finite_ok),
            "index_ok": index_ok,
            "distinct_triangle_vertices": distinct_vertices,
            "nondegenerate_triangles": nondegenerate,
            "all_regions_have_triangles": all_regions_populated,
            "region_triangle_counts": {
                str(region_id): int(region_counts[region_id])
                for region_id in sorted(expected_ids)
            },
            "minimum_absolute_double_area": float(
                np.min(np.abs(signed_areas))
            ),
            "area_tolerance": area_tolerance,
        }

        result["structure_checks"] = structure_checks
        result["structure_status"] = (
            PASS
            if all(
                (
                    shape_ok,
                    finite_ok,
                    index_ok,
                    distinct_vertices,
                    nondegenerate,
                    all_regions_populated,
                )
            )
            else FAIL
        )

        critical = (
            result["generation_status"],
            result["structure_status"],
            result["numbering_status"],
        )
        result["status"] = (
            PASS if all(item == PASS for item in critical)
            else FAIL
        )
    except Exception as exc:
        if result["generation_status"] == UNCONFIRMED:
            result["generation_status"] = FAIL
        result["status"] = FAIL
        result["exception"] = _exception_payload(exc)

    return result


def _mapping_from_setup(
    result: Mapping[str, Any],
) -> dict[str, int] | None:
    try:
        mapping = result["final_id_by_curve_key"]
        return {
            str(key): int(value)
            for key, value in mapping.items()
        }
    except (KeyError, TypeError, ValueError):
        return None


def _mapping_from_full(
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
) -> dict[str, Any]:
    if first is None or second is None:
        return {
            "status": UNCONFIRMED,
            "reason": "One or both mappings are unavailable",
        }

    equal = dict(first) == dict(second)
    return {
        "status": PASS if equal else FAIL,
        "equal": equal,
        "first": dict(first),
        "second": dict(second),
    }


def _dx_variant(spec: CaseSpec) -> CaseSpec:
    factors = (0.73, 1.19, 0.81, 1.31)

    return replace(
        spec,
        name=spec.name,
        curves=tuple(
            replace(
                curve,
                dx=curve.dx * factors[
                    index % len(factors)
                ],
            )
            for index, curve in enumerate(spec.curves)
        ),
    )


def _run_case(
    gs_domain_class: Any,
    spec: CaseSpec,
) -> dict[str, Any]:
    setup = _run_setup_only(
        gs_domain_class,
        spec,
    )
    full = _run_full_build(
        gs_domain_class,
        spec,
    )
    repeat = _run_full_build(
        gs_domain_class,
        spec,
    )
    dx_variant = _run_full_build(
        gs_domain_class,
        _dx_variant(spec),
    )

    comparisons = {
        "setup_vs_full": _compare_mappings(
            _mapping_from_setup(setup),
            _mapping_from_full(full),
        ),
        "fresh_rebuild": _compare_mappings(
            _mapping_from_full(full),
            _mapping_from_full(repeat),
        ),
        "dx_change": _compare_mappings(
            _mapping_from_full(full),
            _mapping_from_full(dx_variant),
        ),
    }

    statuses = [
        setup["status"],
        full["status"],
        repeat["status"],
        dx_variant["status"],
        comparisons["setup_vs_full"]["status"],
        comparisons["fresh_rebuild"]["status"],
        comparisons["dx_change"]["status"],
    ]

    if FAIL in statuses:
        overall = FAIL
    elif UNCONFIRMED in statuses:
        overall = UNCONFIRMED
    else:
        overall = PASS

    return {
        "case": spec.name,
        "overall_status": overall,
        "setup_only": setup,
        "full_build": full,
        "repeat_build": repeat,
        "dx_variant": dx_variant,
        "comparisons": comparisons,
    }


def _parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe OFT 26.6 multi-region generation without "
            "a plasma technical role."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New or empty directory for JSON results.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    summary: dict[str, Any] = {
        "probe": "oft_no_plasma_multi_region",
        "required_oft_version": REQUIRED_OFT_VERSION,
        "status": FAIL,
        "cases": {},
        "interpretation": {
            "plasma_role_present": False,
            "outer_role": "boundary",
            "internal_roles": "vacuum",
            "technical_roles_are_not_user_physical_labels": True,
            "physical_labels_are_empty": True,
            "production_policy": UNCONFIRMED,
        },
    }

    output_dir: Path | None = None

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

        results: dict[str, dict[str, Any]] = {}

        for name, spec in _case_specs().items():
            result = _run_case(
                gs_Domain,
                spec,
            )
            results[name] = result
            _write_json(
                output_dir / f"{name}.json",
                result,
            )

        failed_cases = [
            name
            for name, result in results.items()
            if result["overall_status"] == FAIL
        ]
        unconfirmed_cases = [
            name
            for name, result in results.items()
            if result["overall_status"] == UNCONFIRMED
        ]
        passed_cases = [
            name
            for name, result in results.items()
            if result["overall_status"] == PASS
        ]

        if failed_cases:
            overall_status = FAIL
            production_policy = (
                "NO_PLASMA_NOT_SUPPORTED_BY_THIS_PROBE"
            )
        elif unconfirmed_cases:
            overall_status = UNCONFIRMED
            production_policy = UNCONFIRMED
        else:
            overall_status = PASS
            production_policy = (
                "ROOT_BOUNDARY_INTERNAL_VACUUM_SUPPORTED"
            )

        summary.update(
            {
                "status": overall_status,
                "cases": {
                    name: {
                        "overall_status": result["overall_status"],
                        "setup_status": result["setup_only"]["status"],
                        "generation_status": result["full_build"][
                            "generation_status"
                        ],
                        "structure_status": result["full_build"][
                            "structure_status"
                        ],
                        "numbering_status": result["full_build"][
                            "numbering_status"
                        ],
                    }
                    for name, result in results.items()
                },
                "failed_cases": failed_cases,
                "unconfirmed_cases": unconfirmed_cases,
                "passed_cases": passed_cases,
                "interpretation": {
                    **summary["interpretation"],
                    "production_policy": production_policy,
                },
            }
        )
    except Exception as exc:
        summary["fatal_exception"] = _exception_payload(exc)

    if output_dir is not None:
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