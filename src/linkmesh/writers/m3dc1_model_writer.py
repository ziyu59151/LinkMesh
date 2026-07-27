"""
Independent M3D-C1 analytic geometric model TXT writer.

The writer accepts only a validated M3DC1ModelSpec and emits the common text
contract written by meshgen save_model()/save_multi_rgn_model() and consumed
by m3dc1_scorec load_model().

M4-1A does not use PUMI, APF, MDS, MPI, Simmetrix, make_model, SMB, SMD, SMS,
or partitioned mesh files.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from linkmesh.m3dc1_model import (
    CurveType,
    M3DC1ModelSpec,
)


def _format_float(value: float) -> str:
    """Match the reference save_model() default %lf output precision."""
    return f"{float(value):.6f}"


def serialize_m3dc1_model(spec: M3DC1ModelSpec) -> str:
    """Serialize a validated model to deterministic M3D-C1 TXT content.

    Layout:

    1. Five-integer model header:
       numLoops separatrixLoop innerWallLoop outerWallLoop vacuumLoop
    2. For each loop:
       loop ID and edge count
       one geometric vertex record for each ordered edge start
       ordered geometric edge records and optional curve payloads
    3. numFaces
    4. face ID, number of loops, and ordered loop references
    """
    if not isinstance(spec, M3DC1ModelSpec):
        raise TypeError(
            "Writer 只接受 M3DC1ModelSpec，"
            f"实际={type(spec).__name__}"
        )

    spec.validate()

    vertex_by_tag = {vertex.tag: vertex for vertex in spec.vertices}
    edge_by_tag = {edge.tag: edge for edge in spec.edges}

    lines: list[str] = [
        (
            f"{spec.num_loops} "
            f"{spec.separatrix_loop} "
            f"{spec.inner_wall_loop} "
            f"{spec.outer_wall_loop} "
            f"{spec.vacuum_loop}"
        )
    ]

    for loop in spec.loops:
        lines.append(f"{loop.tag} {len(loop.edge_tags)}")

        # Reference save_model() writes the starting vertex of every ordered
        # loop edge. In the P0 polygon each vertex starts exactly one edge.
        for edge_tag in loop.edge_tags:
            edge = edge_by_tag[edge_tag]
            vertex = vertex_by_tag[edge.begin_vertex_tag]
            lines.append(
                f"{vertex.tag} "
                f"{_format_float(vertex.r)} "
                f"{_format_float(vertex.z)} "
                f"{_format_float(vertex.y)}"
            )

        for edge_tag in loop.edge_tags:
            edge = edge_by_tag[edge_tag]
            serialized_type = edge.curve.serialized_curve_type
            lines.append(
                f"{edge.tag} "
                f"{edge.begin_vertex_tag} "
                f"{edge.end_vertex_tag} "
                f"{int(serialized_type)}"
            )

            if serialized_type is CurveType.BSPLINE:
                edge.curve.validate()
                order = int(edge.curve.order)
                num_points = len(edge.curve.control_points)

                payload = [
                    str(order),
                    str(num_points),
                    *(_format_float(value) for value in edge.curve.knots),
                ]
                for r_value, z_value in edge.curve.control_points:
                    payload.append(_format_float(r_value))
                    payload.append(_format_float(z_value))
                lines.append(" ".join(payload))

    lines.append(str(spec.num_faces))
    for face in spec.faces:
        loop_fields = " ".join(str(tag) for tag in face.loop_tags)
        lines.append(
            f"{face.tag} {len(face.loop_tags)} {loop_fields}"
        )

    return "\n".join(lines) + "\n"


def write_m3dc1_model(
    spec: M3DC1ModelSpec,
    filepath: str | os.PathLike[str],
) -> None:
    """Write an M3D-C1 analytic geometric model TXT file atomically.

    Validation and full serialization happen before the destination is
    opened. A temporary file in the destination directory is then replaced
    atomically, preventing validation failures or interrupted writes from
    leaving a partially serialized model.
    """
    content = serialize_m3dc1_model(spec)
    destination = Path(filepath)

    if destination.exists() and destination.is_dir():
        raise OSError(
            f"M3D-C1 model 输出路径是目录而不是文件：{destination}"
        )

    parent = destination.parent
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, destination)
        temporary_path = None
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise OSError(
            f"无法写出 M3D-C1 analytic model TXT 文件 "
            f"{destination}: {exc}"
        ) from exc
