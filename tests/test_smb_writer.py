from __future__ import annotations

import copy
import os
import stat
import struct
import textwrap
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pytest

from linkmesh.m3dc1_model import (
    GeometricFace,
    M3DC1ModelSpec,
    build_single_face_model_spec,
)
from linkmesh.mesh import Mesh2D
from linkmesh.writers import smb_writer
from linkmesh.writers.smb_writer import (
    SMBWriterError,
    _MAGIC,
    _prepare_exchange,
    _rank0_path,
    _write_exchange,
    write_smb,
)


def _clockwise_square() -> np.ndarray:
    return np.array(
        [
            [0.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [1.0, 0.0],
        ],
        dtype=np.float64,
    )


def _mesh_with_boundary_steiner_points() -> Mesh2D:
    nodes = np.array(
        [
            [0.0, 0.0],
            [0.0, 0.5],
            [0.0, 1.0],
            [0.5, 1.0],
            [1.0, 1.0],
            [1.0, 0.5],
            [1.0, 0.0],
            [0.5, 0.0],
            [0.5, 0.5],
        ],
        dtype=np.float64,
    )
    triangles = np.array(
        [
            [0, 1, 8],
            [1, 2, 8],
            [2, 3, 8],
            [3, 4, 8],
            [4, 5, 8],
            [5, 6, 8],
            [6, 7, 8],
            [7, 0, 8],
        ],
        dtype=np.int32,
    )
    return Mesh2D(
        nodes=nodes,
        triangles=triangles,
        region_ids=np.ones(8, dtype=np.int32),
        outer_boundary=_clockwise_square(),
    )


def _minimal_inputs(tmp_path):
    mesh = _mesh_with_boundary_steiner_points()
    spec = build_single_face_model_spec(mesh)
    base = tmp_path / "mesh.smb"
    return mesh, spec, base


def _read_exchange(path: Path) -> dict:
    data = memoryview(path.read_bytes())
    offset = 0

    def take(fmt: str):
        nonlocal offset
        parsed = struct.Struct(fmt)
        values = parsed.unpack_from(data, offset)
        offset += parsed.size
        return values

    magic = bytes(data[:8])
    offset += 8
    schema_version, = take("<I")
    endian_marker, = take("<I")
    counts = take("<7Q")
    special_loops = take("<4i")
    output_length, = take("<Q")
    output_base = bytes(data[offset:offset + output_length])
    offset += output_length

    n_nodes, n_triangles, n_edges, n_gv, n_ge, n_gl, n_gf = counts

    nodes = np.frombuffer(
        data[offset:offset + n_nodes * 2 * 8],
        dtype="<f8",
    ).reshape(n_nodes, 2).copy()
    offset += n_nodes * 2 * 8

    triangles = np.frombuffer(
        data[offset:offset + n_triangles * 3 * 8],
        dtype="<u8",
    ).reshape(n_triangles, 3).copy()
    offset += n_triangles * 3 * 8

    geometric_vertices = []
    for _ in range(n_gv):
        geometric_vertices.append(take("<i3d"))

    geometric_edges = []
    for _ in range(n_ge):
        geometric_edges.append(take("<4i"))

    loops = []
    for _ in range(n_gl):
        tag, = take("<i")
        count, = take("<Q")
        edge_tags = tuple(take("<i")[0] for _ in range(count))
        loops.append((tag, edge_tags))

    faces = []
    for _ in range(n_gf):
        tag, = take("<i")
        count, = take("<Q")
        loop_tags = tuple(take("<i")[0] for _ in range(count))
        faces.append((tag, loop_tags))

    vertex_classes = [take("<2i") for _ in range(n_nodes)]
    mesh_edges = [take("<2Q2i") for _ in range(n_edges)]
    triangle_classes = [take("<2i") for _ in range(n_triangles)]

    return {
        "magic": magic,
        "schema_version": schema_version,
        "endian_marker": endian_marker,
        "counts": counts,
        "special_loops": special_loops,
        "output_base": os.fsdecode(output_base),
        "nodes": nodes,
        "triangles": triangles,
        "geometric_vertices": geometric_vertices,
        "geometric_edges": geometric_edges,
        "loops": loops,
        "faces": faces,
        "vertex_classes": vertex_classes,
        "mesh_edges": mesh_edges,
        "triangle_classes": triangle_classes,
        "remaining": len(data) - offset,
    }


def _make_helper(
    tmp_path: Path,
    *,
    name: str = "fake-helper",
    exit_code: int = 0,
    create_output: bool = True,
    empty_output: bool = False,
    sleep_seconds: float = 0.0,
) -> Path:
    helper = tmp_path / name
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import pathlib
        import struct
        import sys
        import time
        from urllib.parse import quote

        if len(sys.argv) != 3 or sys.argv[1] != "--input":
            sys.exit(99)

        time.sleep({sleep_seconds!r})

        exchange = pathlib.Path(sys.argv[2])
        data = exchange.read_bytes()
        offset = 8 + 4 + 4 + 7 * 8 + 4 * 4
        length = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        base = pathlib.Path(data[offset:offset + length].decode())
        rank0 = base.with_name(base.stem + "0" + base.suffix)

        if {exit_code} != 0:
            print(
                "LINKMESH_M4_ERROR stage=fake_native "
                "message=fake_failure",
                file=sys.stderr,
            )
            sys.exit({exit_code})

        if {create_output!r}:
            rank0.write_bytes(b"" if {empty_output!r} else b"FAKE_NOT_SMB")

        print(
            "LINKMESH_M4_OK "
            f"base={{quote(str(base), safe='/:\\\\')}} "
            f"rank0={{quote(str(rank0), safe='/:\\\\')}}"
        )
        """
    )
    helper.write_text(script, encoding="utf-8")
    helper.chmod(
        helper.stat().st_mode |
        stat.S_IXUSR |
        stat.S_IXGRP |
        stat.S_IXOTH
    )
    return helper


def test_minimal_exchange_schema_v1(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    prepared = _prepare_exchange(mesh, spec, base)
    exchange = tmp_path / "exchange.bin"

    _write_exchange(prepared, exchange)
    parsed = _read_exchange(exchange)

    assert parsed["magic"] == _MAGIC
    assert parsed["schema_version"] == 1
    assert parsed["endian_marker"] == 0x01020304
    assert parsed["counts"] == (9, 8, 16, 4, 4, 1, 1)
    assert parsed["special_loops"] == (-1, 1, -1, -1)
    assert parsed["remaining"] == 0


def test_exchange_preserves_nodes_and_zero_based_triangles(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    prepared = _prepare_exchange(mesh, spec, base)
    exchange = tmp_path / "exchange.bin"

    _write_exchange(prepared, exchange)
    parsed = _read_exchange(exchange)

    np.testing.assert_array_equal(parsed["nodes"], mesh.nodes)
    np.testing.assert_array_equal(
        parsed["triangles"],
        mesh.triangles.astype(np.uint64),
    )
    assert parsed["triangles"].min() == 0
    assert parsed["triangles"].max() == mesh.n_nodes - 1


def test_exchange_geometric_tags_match_model_spec(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    prepared = _prepare_exchange(mesh, spec, base)
    exchange = tmp_path / "exchange.bin"

    _write_exchange(prepared, exchange)
    parsed = _read_exchange(exchange)

    assert [record[0] for record in parsed["geometric_vertices"]] == [
        1, 2, 3, 4
    ]
    assert parsed["geometric_edges"] == [
        (1, 1, 2, 1),
        (2, 2, 3, 1),
        (3, 3, 4, 1),
        (4, 4, 1, 1),
    ]
    assert parsed["loops"] == [(1, (1, 2, 3, 4))]
    assert parsed["faces"] == [(1, (1,))]


def test_deterministic_classification_dimensions_and_tags(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    prepared = _prepare_exchange(mesh, spec, base)

    assert prepared.vertex_classes == (
        (0, 1),
        (1, 1),
        (0, 2),
        (1, 2),
        (0, 3),
        (1, 3),
        (0, 4),
        (1, 4),
        (2, 1),
    )

    boundary_edge_classes = {
        (node0, node1): (dimension, tag)
        for node0, node1, dimension, tag in prepared.mesh_edges
        if dimension == 1
    }
    assert boundary_edge_classes == {
        (0, 1): (1, 1),
        (1, 2): (1, 1),
        (2, 3): (1, 2),
        (3, 4): (1, 2),
        (4, 5): (1, 3),
        (5, 6): (1, 3),
        (6, 7): (1, 4),
        (0, 7): (1, 4),
    }

    interior_edge_classes = [
        (dimension, tag)
        for _, _, dimension, tag in prepared.mesh_edges
        if dimension == 2
    ]
    assert interior_edge_classes == [(2, 1)] * 8
    assert prepared.triangle_classes == ((2, 1),) * 8


def test_mesh_edges_are_unique_and_lexicographically_sorted(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    prepared = _prepare_exchange(mesh, spec, base)

    endpoints = [
        (node0, node1)
        for node0, node1, _, _ in prepared.mesh_edges
    ]
    assert endpoints == sorted(endpoints)
    assert len(endpoints) == len(set(endpoints))
    assert all(first < second for first, second in endpoints)


def test_helper_missing_fails_clearly(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    missing = tmp_path / "missing-helper"

    with pytest.raises(SMBWriterError, match="helper 定位失败.*不存在"):
        write_smb(mesh, spec, base, helper_path=missing)

    assert list(tmp_path.glob("*.lm4xchg")) == []


def test_explicit_helper_path_has_first_priority(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    explicit_helper = _make_helper(tmp_path, name="explicit-helper")
    environment_helper = _make_helper(
        tmp_path,
        name="environment-helper",
        exit_code=17,
    )
    _make_helper(
        tmp_path,
        name="linkmesh-scorec-helper",
        exit_code=18,
    )
    monkeypatch.setenv("LINKMESH_SCOREC_HELPER", str(environment_helper))
    monkeypatch.setenv("PATH", str(tmp_path))

    write_smb(mesh, spec, base, helper_path=explicit_helper)

    assert _rank0_path(base.absolute()).is_file()


def test_new_environment_variable_has_second_priority(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    environment_helper = _make_helper(
        tmp_path,
        name="environment-helper",
    )
    _make_helper(
        tmp_path,
        name="linkmesh-scorec-helper",
        exit_code=18,
    )
    monkeypatch.setenv("LINKMESH_SCOREC_HELPER", str(environment_helper))
    monkeypatch.setenv("PATH", str(tmp_path))

    write_smb(mesh, spec, base)

    assert _rank0_path(base.absolute()).is_file()


def test_new_helper_name_is_resolved_from_path(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    _make_helper(tmp_path, name="linkmesh-scorec-helper")
    monkeypatch.delenv("LINKMESH_SCOREC_HELPER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))

    write_smb(mesh, spec, base)

    assert _rank0_path(base.absolute()).is_file()


def test_missing_sources_report_only_new_formal_names(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    monkeypatch.delenv("LINKMESH_SCOREC_HELPER", raising=False)
    monkeypatch.delenv("LINKMESH_M3DC1_SMB_HELPER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(SMBWriterError) as captured:
        write_smb(mesh, spec, base)

    message = str(captured.value)
    assert "LINKMESH_SCOREC_HELPER" in message
    assert "linkmesh-scorec-helper" in message
    assert "LINKMESH_M3DC1_SMB_HELPER" not in message
    assert "linkmesh-m3dc1-smb-helper" not in message


def test_explicit_invalid_helper_does_not_fall_back_to_other_sources(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    environment_helper = _make_helper(
        tmp_path,
        name="environment-helper",
    )
    _make_helper(tmp_path, name="linkmesh-scorec-helper")
    monkeypatch.setenv("LINKMESH_SCOREC_HELPER", str(environment_helper))
    monkeypatch.setenv("PATH", str(tmp_path))
    missing = tmp_path / "explicitly-missing"

    with pytest.raises(SMBWriterError, match="explicitly-missing"):
        write_smb(mesh, spec, base, helper_path=missing)

    assert not _rank0_path(base.absolute()).exists()


def test_invalid_new_environment_variable_does_not_fall_back_to_path(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    _make_helper(tmp_path, name="linkmesh-scorec-helper")
    missing = tmp_path / "environment-missing"
    monkeypatch.setenv("LINKMESH_SCOREC_HELPER", str(missing))
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(SMBWriterError, match="environment-missing"):
        write_smb(mesh, spec, base)

    assert not _rank0_path(base.absolute()).exists()


def test_legacy_environment_variable_is_ignored(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    legacy_helper = _make_helper(tmp_path, name="legacy-environment-helper")
    monkeypatch.delenv("LINKMESH_SCOREC_HELPER", raising=False)
    monkeypatch.setenv("LINKMESH_M3DC1_SMB_HELPER", str(legacy_helper))
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(
        SMBWriterError,
        match="PATH 中不存在 linkmesh-scorec-helper",
    ):
        write_smb(mesh, spec, base)

    assert not _rank0_path(base.absolute()).exists()


def test_legacy_helper_name_on_path_is_ignored(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    _make_helper(tmp_path, name="linkmesh-m3dc1-smb-helper")
    monkeypatch.delenv("LINKMESH_SCOREC_HELPER", raising=False)
    monkeypatch.delenv("LINKMESH_M3DC1_SMB_HELPER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(
        SMBWriterError,
        match="PATH 中不存在 linkmesh-scorec-helper",
    ):
        write_smb(mesh, spec, base)

    assert not _rank0_path(base.absolute()).exists()


def test_helper_nonzero_exit_propagates_stage_and_keeps_exchange(
    tmp_path,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path, exit_code=17)

    with pytest.raises(SMBWriterError) as captured:
        write_smb(mesh, spec, base, helper_path=helper)

    message = str(captured.value)
    assert "exit_code=17" in message
    assert "stage=fake_native" in message
    exchanges = list(tmp_path.glob(".*.lm4xchg"))
    assert len(exchanges) == 1
    assert exchanges[0].is_file()


def test_success_locates_rank0_and_removes_exchange(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path)

    write_smb(mesh, spec, base, helper_path=helper)

    rank0 = _rank0_path(base.absolute())
    assert rank0.is_file()
    assert rank0.read_bytes() == b"FAKE_NOT_SMB"
    assert list(tmp_path.glob(".*.lm4xchg")) == []


def test_helper_timeout_keeps_exchange(
    tmp_path,
    monkeypatch,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path, sleep_seconds=0.2)
    monkeypatch.setattr(smb_writer, "_HELPER_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(
        SMBWriterError,
        match=r"stage=helper_timeout.*exchange=",
    ):
        write_smb(mesh, spec, base, helper_path=helper)

    assert len(list(tmp_path.glob(".*.lm4xchg"))) == 1
    assert not _rank0_path(base.absolute()).exists()


def test_success_without_rank0_file_fails_and_keeps_exchange(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path, create_output=False)

    with pytest.raises(SMBWriterError, match="rank-0 SMB 不存在"):
        write_smb(mesh, spec, base, helper_path=helper)

    assert len(list(tmp_path.glob(".*.lm4xchg"))) == 1


def test_success_with_empty_rank0_file_fails_and_keeps_exchange(
    tmp_path,
) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path, empty_output=True)

    with pytest.raises(SMBWriterError, match="rank-0 SMB 为空"):
        write_smb(mesh, spec, base, helper_path=helper)

    assert len(list(tmp_path.glob(".*.lm4xchg"))) == 1


def test_writer_does_not_modify_mesh_or_spec(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    helper = _make_helper(tmp_path)

    nodes_before = mesh.nodes.copy()
    triangles_before = mesh.triangles.copy()
    region_ids_before = mesh.region_ids.copy()
    boundary_before = mesh.outer_boundary.copy()
    spec_before = copy.deepcopy(spec)

    write_smb(mesh, spec, base, helper_path=helper)

    np.testing.assert_array_equal(mesh.nodes, nodes_before)
    np.testing.assert_array_equal(mesh.triangles, triangles_before)
    np.testing.assert_array_equal(mesh.region_ids, region_ids_before)
    np.testing.assert_array_equal(mesh.outer_boundary, boundary_before)
    assert spec == spec_before


def test_multi_region_input_fails_before_helper(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    mesh.region_ids = np.array(
        [1, 1, 1, 1, 2, 2, 2, 2],
        dtype=np.int32,
    )

    with pytest.raises(ValueError, match="single-region"):
        write_smb(
            mesh,
            spec,
            base,
            helper_path=tmp_path / "not-used",
        )


def test_multi_face_spec_fails_before_helper(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    object.__setattr__(
        spec,
        "faces",
        (
            GeometricFace(1, (1,)),
            GeometricFace(2, (1,)),
        ),
    )

    with pytest.raises(ValueError, match="single-face"):
        write_smb(
            mesh,
            spec,
            base,
            helper_path=tmp_path / "not-used",
        )


def test_corner_without_exact_mesh_node_fails(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    mesh.nodes = mesh.nodes.copy()
    mesh.nodes[0, 0] = np.nextafter(0.0, 1.0)

    with pytest.raises(ValueError, match="逐分量精确相等"):
        write_smb(
            mesh,
            spec,
            base,
            helper_path=tmp_path / "not-used",
        )


def test_duplicate_exact_corner_coordinate_fails(tmp_path) -> None:
    mesh, spec, base = _minimal_inputs(tmp_path)
    mesh.nodes = np.vstack([mesh.nodes, mesh.nodes[0]])
    mesh.triangles = mesh.triangles.copy()
    mesh.region_ids = mesh.region_ids.copy()

    with pytest.raises(ValueError, match="候选数=2"):
        write_smb(
            mesh,
            spec,
            base,
            helper_path=tmp_path / "not-used",
        )


def test_ranked_output_path_is_rejected(tmp_path) -> None:
    mesh = _mesh_with_boundary_steiner_points()
    spec = build_single_face_model_spec(mesh)

    with pytest.raises(ValueError, match="rank-0"):
        write_smb(
            mesh,
            spec,
            tmp_path / "mesh0.smb",
            helper_path=tmp_path / "not-used",
        )
