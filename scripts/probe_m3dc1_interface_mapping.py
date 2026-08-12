#!/usr/bin/env python3
"""Probe exact curve-to-mesh interface identity for OFT multi-region meshes.

This investigation script reuses the production ``regions generate`` input,
numbering, map-validation, resolution, and OFT adapter chain. It creates one
Mesh2D, derives global mesh-edge incidence, and verifies that every original
multi-array curve maps exactly to one closed mesh cycle and to deterministic
polygon-segment mesh-edge chains.

It does not call any Writer, Plotter, native helper, or M3D-C1 component.
It never uses nearest-neighbour matching, projection, snapping, or tolerances.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from linkmesh import config as config_mod
from linkmesh.config import UNSET


PASS = "PASS"
FAIL = "FAIL"


class ProbeError(ValueError):
    """Raised when exact interface identity cannot be established."""


EdgeKey = tuple[int, int]
RegionPair = tuple[int, int]


def _edge_key(first: int, second: int) -> EdgeKey:
    if first == second:
        raise ProbeError(
            f"mesh edge contains the same node twice: node={first}"
        )
    return (first, second) if first < second else (second, first)


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
    if not path.parent.is_dir():
        raise FileNotFoundError(
            f"JSON output parent directory does not exist: {path.parent}"
        )
    path.write_text(
        json.dumps(
            _json_value(payload),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe exact identity between multi-array curves and OFT "
            "multi-region mesh interfaces."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Existing regions-generate TOML configuration.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="JSON result path.",
    )
    return parser.parse_args(argv)


def _load_generate_config(config_path: Path) -> Any:
    overrides = config_mod.RegionsGenerateOverrides(
        target=UNSET,
        multi_array_file=UNSET,
        regions_map=UNSET,
        plot=UNSET,
        hdf5=UNSET,
        mesh_dx=UNSET,
        region_dx=UNSET,
        verbose=UNSET,
    )
    return config_mod.load_regions_generate_config(
        overrides,
        config_arg=str(config_path),
    )


def _validate_mesh_arrays(mesh: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nodes = np.asarray(mesh.nodes)
    triangles = np.asarray(mesh.triangles)
    region_ids = np.asarray(mesh.region_ids).reshape(-1)

    if (
        nodes.ndim != 2
        or nodes.shape[1] != 2
        or nodes.shape[0] < 3
    ):
        raise ProbeError(
            f"Mesh2D.nodes must have shape (N,2), actual={nodes.shape}"
        )
    if not np.issubdtype(nodes.dtype, np.floating):
        raise ProbeError(
            f"Mesh2D.nodes must use a floating dtype, actual={nodes.dtype}"
        )
    if not np.all(np.isfinite(nodes)):
        raise ProbeError("Mesh2D.nodes contains NaN or infinity")

    if (
        triangles.ndim != 2
        or triangles.shape[1] != 3
        or triangles.shape[0] == 0
    ):
        raise ProbeError(
            "Mesh2D.triangles must have shape (T,3) with T>0, "
            f"actual={triangles.shape}"
        )
    if not np.issubdtype(triangles.dtype, np.integer):
        raise ProbeError(
            "Mesh2D.triangles must use an integer dtype, "
            f"actual={triangles.dtype}"
        )
    triangles64 = triangles.astype(np.int64, copy=False)
    if (
        int(triangles64.min()) < 0
        or int(triangles64.max()) >= nodes.shape[0]
    ):
        raise ProbeError(
            "Mesh2D.triangles contains an out-of-range global 0-based "
            "node index"
        )
    repeated_vertices = (
        (triangles64[:, 0] == triangles64[:, 1])
        | (triangles64[:, 1] == triangles64[:, 2])
        | (triangles64[:, 0] == triangles64[:, 2])
    )
    if np.any(repeated_vertices):
        triangle_index = int(np.flatnonzero(repeated_vertices)[0])
        raise ProbeError(
            f"triangle {triangle_index} contains repeated node indices"
        )

    canonical_triangles = np.sort(triangles64, axis=1)
    unique_triangles = np.unique(canonical_triangles, axis=0)
    if unique_triangles.shape[0] != triangles64.shape[0]:
        raise ProbeError("Mesh2D contains duplicate global triangles")

    if region_ids.shape != (triangles64.shape[0],):
        raise ProbeError(
            "Mesh2D.region_ids length differs from triangle count: "
            f"regions={region_ids.shape}, triangles={triangles64.shape[0]}"
        )
    if not np.issubdtype(region_ids.dtype, np.integer):
        raise ProbeError(
            "Mesh2D.region_ids must use an integer dtype, "
            f"actual={region_ids.dtype}"
        )
    region_ids64 = region_ids.astype(np.int64, copy=False)
    if np.any(region_ids64 <= 0):
        raise ProbeError("Mesh2D.region_ids contains a non-positive ID")

    return (
        nodes.astype(np.float64, copy=False),
        triangles64,
        region_ids64,
    )


def _build_edge_incidence(
    triangles: np.ndarray,
) -> dict[EdgeKey, list[int]]:
    incidence: dict[EdgeKey, list[int]] = defaultdict(list)

    for triangle_index, triangle in enumerate(triangles):
        local_edges = (
            _edge_key(int(triangle[0]), int(triangle[1])),
            _edge_key(int(triangle[1]), int(triangle[2])),
            _edge_key(int(triangle[2]), int(triangle[0])),
        )
        if len(set(local_edges)) != 3:
            raise ProbeError(
                f"triangle {triangle_index} contains duplicate local edges"
            )
        for edge in local_edges:
            incidence[edge].append(triangle_index)

    if not incidence:
        raise ProbeError("global triangle topology contains no mesh edges")

    for edge, adjacent in incidence.items():
        if len(adjacent) > 2:
            raise ProbeError(
                f"non-manifold mesh edge {edge} has incidence={len(adjacent)}"
            )
        if len(adjacent) not in (1, 2):
            raise ProbeError(
                f"mesh edge {edge} has invalid incidence={len(adjacent)}"
            )
        if len(adjacent) != len(set(adjacent)):
            raise ProbeError(
                f"mesh edge {edge} contains duplicate triangle incidence"
            )

    return dict(incidence)


def _candidate_edges(
    incidence: Mapping[EdgeKey, Sequence[int]],
    region_ids: np.ndarray,
) -> tuple[set[EdgeKey], dict[RegionPair, set[EdgeKey]]]:
    outer_edges: set[EdgeKey] = set()
    interface_edges: dict[RegionPair, set[EdgeKey]] = defaultdict(set)

    for edge, adjacent in incidence.items():
        if len(adjacent) == 1:
            outer_edges.add(edge)
            continue

        first_region = int(region_ids[adjacent[0]])
        second_region = int(region_ids[adjacent[1]])
        if first_region == second_region:
            continue

        pair = tuple(sorted((first_region, second_region)))
        if edge in interface_edges[pair]:
            raise ProbeError(
                f"duplicate interface edge {edge} for Region pair {pair}"
            )
        interface_edges[pair].add(edge)

    if not outer_edges:
        raise ProbeError("mesh topology has no incidence=1 outer edges")
    if not interface_edges:
        raise ProbeError(
            "mesh topology has no incidence=2 cross-Region interface edges"
        )

    return outer_edges, dict(interface_edges)


def _connected_edge_components(
    edges: set[EdgeKey],
) -> list[set[EdgeKey]]:
    by_node: dict[int, set[EdgeKey]] = defaultdict(set)
    for edge in edges:
        by_node[edge[0]].add(edge)
        by_node[edge[1]].add(edge)

    remaining = set(edges)
    components: list[set[EdgeKey]] = []

    while remaining:
        seed = min(remaining)
        component: set[EdgeKey] = set()
        pending = [seed]

        while pending:
            edge = pending.pop()
            if edge not in remaining:
                continue
            remaining.remove(edge)
            component.add(edge)
            for node in edge:
                pending.extend(
                    sorted(
                        by_node[node] & remaining,
                        reverse=True,
                    )
                )

        components.append(component)

    return sorted(
        components,
        key=lambda component: min(component),
    )


def _cycle_from_component(edges: set[EdgeKey], label: str) -> list[int]:
    if len(edges) < 3:
        raise ProbeError(
            f"{label} has fewer than three mesh edges"
        )

    adjacency: dict[int, list[int]] = defaultdict(list)
    for first, second in edges:
        adjacency[first].append(second)
        adjacency[second].append(first)

    invalid_degrees = {
        node: len(neighbours)
        for node, neighbours in adjacency.items()
        if len(neighbours) != 2
    }
    if invalid_degrees:
        raise ProbeError(
            f"{label} is not a closed degree-2 cycle: "
            f"invalid_degrees={invalid_degrees}"
        )
    if len(adjacency) != len(edges):
        raise ProbeError(
            f"{label} does not have equal node and edge counts"
        )

    start = min(adjacency)
    first_neighbour = min(adjacency[start])
    cycle = [start]
    previous: int | None = None
    current = start
    following = first_neighbour

    while following != start:
        if following in cycle:
            raise ProbeError(
                f"{label} revisits node {following} before closing"
            )
        cycle.append(following)
        previous, current = current, following
        neighbours = adjacency[current]
        following = (
            neighbours[0]
            if neighbours[0] != previous
            else neighbours[1]
        )
        if len(cycle) > len(adjacency):
            raise ProbeError(f"{label} traversal did not terminate")

    traversed_edges = {
        _edge_key(cycle[index], cycle[(index + 1) % len(cycle)])
        for index in range(len(cycle))
    }
    if traversed_edges != edges:
        missing = sorted(edges - traversed_edges)
        extra = sorted(traversed_edges - edges)
        raise ProbeError(
            f"{label} traversal does not cover its edge component: "
            f"missing={missing}, extra={extra}"
        )

    return cycle


def _extract_cycles(
    edges: set[EdgeKey],
    label: str,
) -> list[list[int]]:
    components = _connected_edge_components(edges)
    return [
        _cycle_from_component(
            component,
            f"{label} component {index}",
        )
        for index, component in enumerate(components, start=1)
    ]


def _coordinate_index(nodes: np.ndarray) -> dict[tuple[float, float], list[int]]:
    result: dict[tuple[float, float], list[int]] = defaultdict(list)
    for node_index, node in enumerate(nodes):
        key = (float(node[0]), float(node[1]))
        result[key].append(node_index)
    return dict(result)


def _match_curve_corners(
    points: np.ndarray,
    nodes_by_coordinate: Mapping[tuple[float, float], Sequence[int]],
    cycle_nodes: Sequence[int],
    curve_id: int,
) -> list[int]:
    cycle_node_set = set(cycle_nodes)
    matched: list[int] = []

    for corner_index, point in enumerate(points):
        coordinate = (float(point[0]), float(point[1]))
        candidates = tuple(nodes_by_coordinate.get(coordinate, ()))
        if not candidates:
            raise ProbeError(
                f"curve_id={curve_id} corner={corner_index} coordinate="
                f"{coordinate} has no exact mesh-node match"
            )
        if len(candidates) != 1:
            raise ProbeError(
                f"curve_id={curve_id} corner={corner_index} coordinate="
                f"{coordinate} matches multiple mesh nodes {candidates}"
            )

        node_index = int(candidates[0])
        if node_index not in cycle_node_set:
            raise ProbeError(
                f"curve_id={curve_id} corner={corner_index} exact node "
                f"{node_index} is not on the assigned cycle"
            )
        matched.append(node_index)

    if len(set(matched)) != len(matched):
        raise ProbeError(
            f"curve_id={curve_id} maps multiple corners to one mesh node"
        )
    return matched


def _forward_cycle_path(
    cycle_nodes: Sequence[int],
    start: int,
    end: int,
) -> list[int]:
    positions = {
        node: index
        for index, node in enumerate(cycle_nodes)
    }
    if start not in positions or end not in positions:
        raise ProbeError("cycle path endpoint is absent from cycle")

    path = [start]
    cursor = positions[start]
    while path[-1] != end:
        cursor = (cursor + 1) % len(cycle_nodes)
        path.append(int(cycle_nodes[cursor]))
        if len(path) > len(cycle_nodes):
            raise ProbeError("cycle path failed to reach its endpoint")
    return path


def _segment_chain(
    cycle_nodes: Sequence[int],
    start: int,
    end: int,
    all_corner_nodes: set[int],
    curve_id: int,
    segment_index: int,
) -> list[int]:
    forward = _forward_cycle_path(cycle_nodes, start, end)
    backward = list(
        reversed(_forward_cycle_path(cycle_nodes, end, start))
    )
    candidates = [
        path
        for path in (forward, backward)
        if not (set(path[1:-1]) & all_corner_nodes)
    ]

    if len(candidates) != 1:
        raise ProbeError(
            f"curve_id={curve_id} polygon segment={segment_index} "
            "does not map to exactly one cycle path without another "
            f"original corner; candidate_count={len(candidates)}"
        )
    if len(candidates[0]) < 2:
        raise ProbeError(
            f"curve_id={curve_id} polygon segment={segment_index} "
            "produced an empty mesh-edge chain"
        )
    return candidates[0]


def _partition_cycle_by_segments(
    cycle_nodes: Sequence[int],
    corner_nodes: Sequence[int],
    curve_id: int,
) -> list[dict[str, Any]]:
    all_corner_nodes = set(corner_nodes)
    cycle_edges = {
        _edge_key(
            int(cycle_nodes[index]),
            int(cycle_nodes[(index + 1) % len(cycle_nodes)]),
        )
        for index in range(len(cycle_nodes))
    }
    edge_owners: dict[EdgeKey, list[int]] = defaultdict(list)
    chains: list[dict[str, Any]] = []

    for segment_index, start_node in enumerate(corner_nodes):
        end_node = int(
            corner_nodes[(segment_index + 1) % len(corner_nodes)]
        )
        chain_nodes = _segment_chain(
            cycle_nodes,
            int(start_node),
            end_node,
            all_corner_nodes,
            curve_id,
            segment_index,
        )
        chain_edges = [
            _edge_key(chain_nodes[index], chain_nodes[index + 1])
            for index in range(len(chain_nodes) - 1)
        ]

        for edge in chain_edges:
            if edge not in cycle_edges:
                raise ProbeError(
                    f"curve_id={curve_id} segment={segment_index} "
                    f"contains non-cycle edge {edge}"
                )
            edge_owners[edge].append(segment_index)

        chains.append(
            {
                "polygon_segment_index": segment_index,
                "start_corner_index": segment_index,
                "end_corner_index": (
                    segment_index + 1
                ) % len(corner_nodes),
                "start_node_index": int(start_node),
                "end_node_index": end_node,
                "mesh_node_chain": chain_nodes,
                "mesh_edge_chain": [
                    [edge[0], edge[1]]
                    for edge in chain_edges
                ],
            }
        )

    missing = sorted(cycle_edges - set(edge_owners))
    multiply_owned = {
        f"{edge[0]}-{edge[1]}": owners
        for edge, owners in sorted(edge_owners.items())
        if len(owners) != 1
    }
    extra = sorted(set(edge_owners) - cycle_edges)
    if missing or multiply_owned or extra:
        raise ProbeError(
            f"curve_id={curve_id} segment chains do not partition the "
            f"cycle exactly once: missing={missing}, "
            f"multiply_owned={multiply_owned}, extra={extra}"
        )

    return chains


def _region_identity(
    numbered_plan: Any,
) -> tuple[
    dict[int, Any],
    dict[int, int],
]:
    by_curve_id = numbered_plan.by_curve_id()
    region_id_by_curve_id: dict[int, int] = {}

    for entry in numbered_plan.entries:
        if entry.region_id is None:
            raise ProbeError(
                f"curve_id={entry.curve_id} has no final Region ID"
            )
        region_id = int(entry.region_id)
        if region_id <= 0:
            raise ProbeError(
                f"curve_id={entry.curve_id} has invalid Region ID "
                f"{region_id}"
            )
        region_id_by_curve_id[entry.curve_id] = region_id

    if len(set(region_id_by_curve_id.values())) != len(
        region_id_by_curve_id
    ):
        raise ProbeError("numbered RegionPlan contains duplicate Region IDs")

    return by_curve_id, region_id_by_curve_id


def _curve_result(
    *,
    entry: Any,
    cycle_nodes: Sequence[int],
    region_pair: RegionPair | None,
    cycle_kind: str,
    nodes_by_coordinate: Mapping[tuple[float, float], Sequence[int]],
    region_id_by_curve_id: Mapping[int, int],
) -> dict[str, Any]:
    curve_id = int(entry.curve_id)
    points = np.asarray(entry.points, dtype=np.float64)
    corner_nodes = _match_curve_corners(
        points,
        nodes_by_coordinate,
        cycle_nodes,
        curve_id,
    )
    segment_chains = _partition_cycle_by_segments(
        cycle_nodes,
        corner_nodes,
        curve_id,
    )

    parent_region_id = (
        0
        if entry.parent_curve_id == 0
        else int(region_id_by_curve_id[entry.parent_curve_id])
    )
    child_region_ids = [
        int(region_id_by_curve_id[child_curve_id])
        for child_curve_id in entry.child_curve_ids
    ]

    return {
        "status": PASS,
        "curve_id": curve_id,
        "region_id": int(entry.region_id),
        "parent_curve_id": int(entry.parent_curve_id),
        "parent_region_id": parent_region_id,
        "child_curve_ids": [
            int(value) for value in entry.child_curve_ids
        ],
        "child_region_ids": sorted(child_region_ids),
        "cycle_kind": cycle_kind,
        "region_pair": (
            None
            if region_pair is None
            else [region_pair[0], region_pair[1]]
        ),
        "cycle_nodes": [int(node) for node in cycle_nodes],
        "cycle_edges": [
            [
                min(
                    int(cycle_nodes[index]),
                    int(cycle_nodes[(index + 1) % len(cycle_nodes)]),
                ),
                max(
                    int(cycle_nodes[index]),
                    int(cycle_nodes[(index + 1) % len(cycle_nodes)]),
                ),
            ]
            for index in range(len(cycle_nodes))
        ],
        "corner_coordinates": [
            [float(point[0]), float(point[1])]
            for point in points
        ],
        "corner_node_indices": corner_nodes,
        "polygon_segment_chains": segment_chains,
    }


def _probe_mapping(
    mesh: Any,
    numbered_plan: Any,
    records: Sequence[Any],
) -> dict[str, Any]:
    nodes, triangles, region_ids = _validate_mesh_arrays(mesh)
    expected_region_ids = {
        int(record.region_id)
        for record in records
    }
    observed_region_ids = {
        int(value)
        for value in np.unique(region_ids)
    }
    if observed_region_ids != expected_region_ids:
        raise ProbeError(
            "Mesh2D Region set differs from regions map: "
            f"expected={sorted(expected_region_ids)}, "
            f"observed={sorted(observed_region_ids)}"
        )

    incidence = _build_edge_incidence(triangles)
    outer_edges, interface_edges_by_pair = _candidate_edges(
        incidence,
        region_ids,
    )

    outer_cycles = _extract_cycles(outer_edges, "outer boundary")
    if len(outer_cycles) != 1:
        raise ProbeError(
            "incidence=1 outer boundary must form exactly one closed "
            f"cycle, actual={len(outer_cycles)}"
        )
    outer_cycle = outer_cycles[0]

    interface_cycles_by_pair: dict[
        RegionPair,
        list[list[int]],
    ] = {}
    for pair, edges in sorted(interface_edges_by_pair.items()):
        cycles = _extract_cycles(
            edges,
            f"Region pair {pair[0]}-{pair[1]}",
        )
        if len(cycles) != 1:
            raise ProbeError(
                f"Region pair {pair} must form exactly one closed "
                f"interface cycle, actual={len(cycles)}"
            )
        interface_cycles_by_pair[pair] = cycles

    by_curve_id, region_id_by_curve_id = _region_identity(
        numbered_plan
    )
    nodes_by_coordinate = _coordinate_index(nodes)
    mapped_pairs: set[RegionPair] = set()
    curve_results: list[dict[str, Any]] = []

    root_entry = by_curve_id[numbered_plan.root_curve_id]
    if root_entry.parent_curve_id != 0:
        raise ProbeError("RegionPlan root unexpectedly has a parent")
    curve_results.append(
        _curve_result(
            entry=root_entry,
            cycle_nodes=outer_cycle,
            region_pair=None,
            cycle_kind="outer_boundary",
            nodes_by_coordinate=nodes_by_coordinate,
            region_id_by_curve_id=region_id_by_curve_id,
        )
    )

    for entry in sorted(
        numbered_plan.entries,
        key=lambda item: item.curve_id,
    ):
        if entry.curve_id == numbered_plan.root_curve_id:
            continue
        if entry.parent_curve_id == 0:
            raise ProbeError(
                f"non-root curve_id={entry.curve_id} has no parent"
            )

        region_pair = tuple(
            sorted(
                (
                    int(entry.region_id),
                    region_id_by_curve_id[entry.parent_curve_id],
                )
            )
        )
        if region_pair in mapped_pairs:
            raise ProbeError(
                f"multiple non-root curves map to Region pair {region_pair}"
            )
        if region_pair not in interface_cycles_by_pair:
            raise ProbeError(
                f"curve_id={entry.curve_id} expected interface Region "
                f"pair {region_pair}, but no candidate cycle exists"
            )

        mapped_pairs.add(region_pair)
        curve_results.append(
            _curve_result(
                entry=entry,
                cycle_nodes=interface_cycles_by_pair[region_pair][0],
                region_pair=region_pair,
                cycle_kind="internal_interface",
                nodes_by_coordinate=nodes_by_coordinate,
                region_id_by_curve_id=region_id_by_curve_id,
            )
        )

    candidate_pairs = set(interface_cycles_by_pair)
    if mapped_pairs != candidate_pairs:
        missing = sorted(candidate_pairs - mapped_pairs)
        extra = sorted(mapped_pairs - candidate_pairs)
        raise ProbeError(
            "curve-to-interface Region-pair coverage is incomplete: "
            f"unmapped_candidates={missing}, unexpected_mappings={extra}"
        )

    if len(curve_results) != len(numbered_plan.entries):
        raise ProbeError(
            "not every RegionPlan curve produced exactly one mapping"
        )
    if len(curve_results) != 1 + len(interface_cycles_by_pair):
        raise ProbeError(
            "curve count does not equal outer cycle plus internal "
            "interface cycle count"
        )

    return {
        "status": PASS,
        "reason": None,
        "mesh": {
            "node_count": int(nodes.shape[0]),
            "triangle_count": int(triangles.shape[0]),
            "unique_mesh_edge_count": len(incidence),
            "outer_edge_count": len(outer_edges),
            "internal_interface_edge_count": sum(
                len(edges)
                for edges in interface_edges_by_pair.values()
            ),
            "expected_region_ids": sorted(expected_region_ids),
            "observed_region_ids": sorted(observed_region_ids),
        },
        "coverage": {
            "curve_count": len(numbered_plan.entries),
            "outer_cycle_count": len(outer_cycles),
            "internal_interface_cycle_count": len(
                interface_cycles_by_pair
            ),
            "mapped_region_pairs": [
                [pair[0], pair[1]]
                for pair in sorted(mapped_pairs)
            ],
        },
        "curves": sorted(
            curve_results,
            key=lambda item: item["curve_id"],
        ),
    }


def _execute(config_path: Path) -> dict[str, Any]:
    cfg = _load_generate_config(config_path)

    from linkmesh.mesher.oft_adapter import (
        generate_multi_region_mesh,
        inspect_multi_region_ids,
    )
    from linkmesh.readers.boundary_reader import (
        read_multi_boundary_file,
    )
    from linkmesh.regions import (
        assign_final_region_ids,
        build_region_plan,
        read_regions_map,
        resolve_region_dx,
        validate_plan_against_map,
    )

    records = read_regions_map(cfg.regions_map_path)
    blocks = read_multi_boundary_file(cfg.multi_array_file_path)
    plan = build_region_plan(blocks)
    region_id_by_curve_id = inspect_multi_region_ids(plan)
    numbered_plan = assign_final_region_ids(
        plan,
        region_id_by_curve_id,
    )
    validate_plan_against_map(numbered_plan, records)
    resolved_dx = resolve_region_dx(
        records,
        cfg.mesh_dx,
        dict(cfg.region_dx),
    )

    # This is the probe's only full Mesh2D generation.
    mesh = generate_multi_region_mesh(numbered_plan, resolved_dx)
    result = _probe_mapping(mesh, numbered_plan, records)
    result["inputs"] = {
        "config_path": cfg.config_path,
        "multi_array_file_path": cfg.multi_array_file_path,
        "regions_map_path": cfg.regions_map_path,
        "configured_target": cfg.target,
    }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config_path = args.config.resolve()
    output_path = args.output.resolve()

    payload: dict[str, Any] = {
        "probe": "m3dc1_interface_mapping",
        "status": FAIL,
        "reason": "probe did not complete",
        "inputs": {
            "config_path": config_path,
        },
    }

    try:
        if not config_path.is_file():
            raise FileNotFoundError(
                f"regions-generate config does not exist: {config_path}"
            )
        if output_path == config_path:
            raise ProbeError(
                "JSON output path must differ from the config path"
            )

        payload = _execute(config_path)
    except Exception as exc:
        payload.update(
            {
                "status": FAIL,
                "reason": str(exc),
                "exception": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        )

    try:
        _write_json(output_path, payload)
    except Exception as exc:
        print(
            "LINKMESH_INTERFACE_MAPPING_PROBE_ERROR "
            f"reason=failed_to_write_json:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 1

    if payload.get("status") == PASS:
        print(
            "LINKMESH_INTERFACE_MAPPING_PROBE_OK "
            f"output={output_path}"
        )
        return 0

    print(
        "LINKMESH_INTERFACE_MAPPING_PROBE_ERROR "
        f"reason={payload.get('reason', 'unknown failure')} "
        f"output={output_path}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
