from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from linkmesh.m3dc1_model import (
    CurveType,
    GeometricEdge,
    GeometricFace,
    GeometricLoop,
    GeometricVertex,
    M3DC1Curve,
    M3DC1ModelSpec,
    build_single_face_model_spec,
)
from linkmesh.mesh import Mesh2D
from linkmesh.writers.m3dc1_model_writer import (
    serialize_m3dc1_model,
    write_m3dc1_model,
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


def _minimal_mesh() -> Mesh2D:
    boundary = _clockwise_square()
    return Mesh2D(
        nodes=boundary.copy(),
        triangles=np.array(
            [
                [0, 1, 2],
                [0, 2, 3],
            ],
            dtype=np.int32,
        ),
        region_ids=np.array([1, 1], dtype=np.int32),
        outer_boundary=boundary,
    )


def _minimal_spec() -> M3DC1ModelSpec:
    return build_single_face_model_spec(_minimal_mesh())


def _manual_spec(
    *,
    vertices=None,
    edges=None,
    loops=None,
    faces=None,
    separatrix_loop=-1,
    inner_wall_loop=1,
    outer_wall_loop=-1,
    vacuum_loop=-1,
) -> M3DC1ModelSpec:
    if vertices is None:
        vertices = (
            GeometricVertex(1, 0.0, 0.0),
            GeometricVertex(2, 0.0, 1.0),
            GeometricVertex(3, 1.0, 1.0),
            GeometricVertex(4, 1.0, 0.0),
        )
    if edges is None:
        edges = (
            GeometricEdge(1, 1, 2),
            GeometricEdge(2, 2, 3),
            GeometricEdge(3, 3, 4),
            GeometricEdge(4, 4, 1),
        )
    if loops is None:
        loops = (GeometricLoop(1, (1, 2, 3, 4)),)
    if faces is None:
        faces = (GeometricFace(1, (1,)),)

    return M3DC1ModelSpec(
        vertices=tuple(vertices),
        edges=tuple(edges),
        loops=tuple(loops),
        faces=tuple(faces),
        separatrix_loop=separatrix_loop,
        inner_wall_loop=inner_wall_loop,
        outer_wall_loop=outer_wall_loop,
        vacuum_loop=vacuum_loop,
    )


def test_minimal_legal_single_face_model_spec() -> None:
    spec = _minimal_spec()

    assert spec.num_loops == 1
    assert spec.num_faces == 1
    assert spec.separatrix_loop == -1
    assert spec.inner_wall_loop == 1
    assert spec.outer_wall_loop == -1
    assert spec.vacuum_loop == -1


def test_adapter_builds_expected_entity_counts() -> None:
    spec = build_single_face_model_spec(_minimal_mesh())

    assert len(spec.vertices) == 4
    assert len(spec.edges) == 4
    assert len(spec.loops) == 1
    assert len(spec.faces) == 1


def test_adapter_assigns_positive_unique_contiguous_tags() -> None:
    spec = _minimal_spec()

    assert [vertex.tag for vertex in spec.vertices] == [1, 2, 3, 4]
    assert [edge.tag for edge in spec.edges] == [1, 2, 3, 4]
    assert [loop.tag for loop in spec.loops] == [1]
    assert [face.tag for face in spec.faces] == [1]


def test_all_references_exist() -> None:
    spec = _minimal_spec()
    vertex_tags = {vertex.tag for vertex in spec.vertices}
    edge_tags = {edge.tag for edge in spec.edges}
    loop_tags = {loop.tag for loop in spec.loops}

    assert all(
        edge.begin_vertex_tag in vertex_tags
        and edge.end_vertex_tag in vertex_tags
        for edge in spec.edges
    )
    assert set(spec.loops[0].edge_tags) == edge_tags
    assert set(spec.faces[0].loop_tags).issubset(loop_tags)


def test_adapter_preserves_boundary_edge_order() -> None:
    spec = _minimal_spec()

    assert [
        (edge.begin_vertex_tag, edge.end_vertex_tag)
        for edge in spec.edges
    ] == [
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 1),
    ]


def test_last_edge_returns_to_first_vertex() -> None:
    spec = _minimal_spec()

    assert spec.edges[-1].begin_vertex_tag == 4
    assert spec.edges[-1].end_vertex_tag == 1


def test_loop_is_closed_and_continuous() -> None:
    spec = _minimal_spec()
    edge_by_tag = {edge.tag: edge for edge in spec.edges}
    edge_tags = spec.loops[0].edge_tags

    for index, edge_tag in enumerate(edge_tags):
        current = edge_by_tag[edge_tag]
        following = edge_by_tag[edge_tags[(index + 1) % len(edge_tags)]]
        assert current.end_vertex_tag == following.begin_vertex_tag


def test_face_references_the_only_loop() -> None:
    spec = _minimal_spec()

    assert spec.faces[0].loop_tags == (spec.loops[0].tag,)


def test_vertices_store_r_z_and_zero_third_coordinate() -> None:
    spec = _minimal_spec()

    assert [
        (vertex.r, vertex.z, vertex.y)
        for vertex in spec.vertices
    ] == [
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
    ]


def test_five_integer_header_matches_source_contract() -> None:
    first_line = serialize_m3dc1_model(_minimal_spec()).splitlines()[0]

    assert first_line == "1 -1 1 -1 -1"
    assert len(first_line.split()) == 5


def test_linear_curve_code_and_no_payload() -> None:
    lines = serialize_m3dc1_model(_minimal_spec()).splitlines()

    assert lines[6:10] == [
        "1 1 2 1",
        "2 2 3 1",
        "3 3 4 1",
        "4 4 1 1",
    ]
    assert lines[10] == "1"
    assert lines[11] == "1 1 1"


def test_curve_numeric_codes_match_m3dc1_enum() -> None:
    assert int(CurveType.LIN) == 1
    assert int(CurveType.POLY) == 2
    assert int(CurveType.BSPLINE) == 3


def test_linear_curve_rejects_additional_payload() -> None:
    with pytest.raises(ValueError, match="LIN.*不得包含"):
        M3DC1Curve(
            CurveType.LIN,
            order=2,
            knots=(0.0, 0.0, 1.0, 1.0),
            control_points=((0.0, 0.0), (1.0, 0.0)),
        )


def test_bspline_curve_writes_required_payload() -> None:
    curve = M3DC1Curve(
        CurveType.BSPLINE,
        order=2,
        knots=(0.0, 0.0, 1.0, 1.0),
        control_points=((0.0, 0.0), (0.0, 1.0)),
    )
    edges = (
        GeometricEdge(1, 1, 2, curve),
        GeometricEdge(2, 2, 3),
        GeometricEdge(3, 3, 4),
        GeometricEdge(4, 4, 1),
    )
    text = serialize_m3dc1_model(_manual_spec(edges=edges))
    lines = text.splitlines()

    assert lines[6] == "1 1 2 3"
    assert lines[7] == (
        "2 2 0.000000 0.000000 1.000000 1.000000 "
        "0.000000 0.000000 0.000000 1.000000"
    )


def test_polynomial_is_canonicalized_to_bspline_on_disk() -> None:
    curve = M3DC1Curve(
        CurveType.POLY,
        order=2,
        knots=(0.0, 0.0, 1.0, 1.0),
        control_points=((0.0, 0.0), (0.0, 1.0)),
    )
    edges = (
        GeometricEdge(1, 1, 2, curve),
        GeometricEdge(2, 2, 3),
        GeometricEdge(3, 3, 4),
        GeometricEdge(4, 4, 1),
    )
    lines = serialize_m3dc1_model(_manual_spec(edges=edges)).splitlines()

    assert lines[6] == "1 1 2 3"


def test_num_faces_is_positive_and_face_record_is_complete() -> None:
    lines = serialize_m3dc1_model(_minimal_spec()).splitlines()

    assert lines[-2] == "1"
    assert lines[-1] == "1 1 1"


def test_output_is_not_two_column_csv() -> None:
    text = serialize_m3dc1_model(_minimal_spec())
    lines = text.splitlines()

    assert "," not in text
    assert len(lines[0].split()) == 5
    assert len(lines[1].split()) == 2
    assert len(lines[2].split()) == 4
    assert len(lines[6].split()) == 4


def test_adapter_does_not_assume_104_points() -> None:
    spec = _minimal_spec()

    assert len(spec.vertices) == 4
    assert len(spec.vertices) != 104


def test_repeated_writes_are_deterministic(tmp_path) -> None:
    spec = _minimal_spec()
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"

    write_m3dc1_model(spec, first)
    write_m3dc1_model(spec, second)

    assert first.read_bytes() == second.read_bytes()


def test_adapter_does_not_modify_mesh_or_arrays() -> None:
    mesh = _minimal_mesh()
    nodes_before = mesh.nodes.copy()
    triangles_before = mesh.triangles.copy()
    region_ids_before = mesh.region_ids.copy()
    boundary_before = mesh.outer_boundary.copy()

    build_single_face_model_spec(mesh)

    np.testing.assert_array_equal(mesh.nodes, nodes_before)
    np.testing.assert_array_equal(mesh.triangles, triangles_before)
    np.testing.assert_array_equal(mesh.region_ids, region_ids_before)
    np.testing.assert_array_equal(mesh.outer_boundary, boundary_before)


def test_writer_does_not_modify_spec() -> None:
    spec = _minimal_spec()
    snapshot = repr(spec)

    serialize_m3dc1_model(spec)

    assert repr(spec) == snapshot


def test_adapter_uses_independent_boundary_values() -> None:
    mesh = _minimal_mesh()
    spec = build_single_face_model_spec(mesh)

    mesh.outer_boundary[0, 0] = 99.0

    assert spec.vertices[0].r == 0.0


def test_missing_outer_boundary_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = None

    with pytest.raises(ValueError, match="outer_boundary.*缺失"):
        build_single_face_model_spec(mesh)


def test_boundary_with_too_few_points_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = np.array(
        [[0.0, 0.0], [1.0, 0.0]],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="至少需要 3 个点"):
        build_single_face_model_spec(mesh)


def test_boundary_with_wrong_shape_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = np.array(
        [0.0, 0.0, 1.0, 1.0],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="二维数组"):
        build_single_face_model_spec(mesh)


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_boundary_with_non_finite_coordinate_fails(invalid_value) -> None:
    mesh = _minimal_mesh()
    boundary = _clockwise_square()
    boundary[1, 0] = invalid_value
    mesh.outer_boundary = boundary

    with pytest.raises(ValueError, match="非有限值"):
        build_single_face_model_spec(mesh)


def test_boundary_with_adjacent_duplicate_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = np.array(
        [
            [0.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
            [1.0, 0.0],
        ],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="相邻重复点"):
        build_single_face_model_spec(mesh)


def test_explicitly_closed_boundary_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = np.array(
        [
            [0.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [1.0, 0.0],
            [0.0, 0.0],
        ],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="首点与末点相同"):
        build_single_face_model_spec(mesh)


def test_self_intersecting_boundary_fails() -> None:
    mesh = _minimal_mesh()
    mesh.outer_boundary = np.array(
        [
            [0.0, 0.0],
            [2.0, 2.0],
            [0.0, 2.0],
            [2.0, 0.0],
        ],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="面积退化|自交"):
        build_single_face_model_spec(mesh)


def test_multi_region_mesh_fails() -> None:
    mesh = _minimal_mesh()
    mesh.region_ids = np.array([1, 2], dtype=np.int32)

    with pytest.raises(ValueError, match="single-region"):
        build_single_face_model_spec(mesh)


def test_duplicate_vertex_tag_fails() -> None:
    vertices = (
        GeometricVertex(1, 0.0, 0.0),
        GeometricVertex(1, 0.0, 1.0),
        GeometricVertex(3, 1.0, 1.0),
        GeometricVertex(4, 1.0, 0.0),
    )

    with pytest.raises(ValueError, match="tag 存在重复"):
        _manual_spec(vertices=vertices)


def test_non_positive_tag_fails() -> None:
    with pytest.raises(ValueError, match="正整数"):
        GeometricVertex(0, 0.0, 0.0)


def test_non_contiguous_tag_fails() -> None:
    vertices = (
        GeometricVertex(1, 0.0, 0.0),
        GeometricVertex(2, 0.0, 1.0),
        GeometricVertex(4, 1.0, 1.0),
        GeometricVertex(5, 1.0, 0.0),
    )

    with pytest.raises(ValueError, match="1-based 连续编号"):
        _manual_spec(vertices=vertices)


def test_dangling_edge_vertex_reference_fails() -> None:
    edges = (
        GeometricEdge(1, 1, 2),
        GeometricEdge(2, 2, 99),
        GeometricEdge(3, 3, 4),
        GeometricEdge(4, 4, 1),
    )

    with pytest.raises(ValueError, match="不存在的 vertex 99"):
        _manual_spec(edges=edges)


def test_dangling_loop_edge_reference_fails() -> None:
    loops = (GeometricLoop(1, (1, 2, 3, 99)),)

    with pytest.raises(ValueError, match="引用全部 geometric edges|不存在的 edge"):
        _manual_spec(loops=loops)


def test_dangling_face_loop_reference_fails() -> None:
    faces = (GeometricFace(1, (2,)),)

    with pytest.raises(ValueError, match="不存在的 loop 2"):
        _manual_spec(faces=faces)


def test_discontinuous_loop_fails() -> None:
    edges = (
        GeometricEdge(1, 1, 2),
        GeometricEdge(2, 3, 4),
        GeometricEdge(3, 4, 3),
        GeometricEdge(4, 2, 1),
    )

    with pytest.raises(ValueError, match="不连续"):
        _manual_spec(edges=edges)


def test_multiple_loops_are_rejected() -> None:
    loops = (
        GeometricLoop(1, (1, 2, 3, 4)),
        GeometricLoop(2, (1, 2, 3, 4)),
    )

    with pytest.raises(ValueError, match="single-loop"):
        _manual_spec(loops=loops)


def test_multiple_faces_are_rejected() -> None:
    faces = (
        GeometricFace(1, (1,)),
        GeometricFace(2, (1,)),
    )

    with pytest.raises(ValueError, match="single-face"):
        _manual_spec(faces=faces)


@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        ("separatrix_loop", 1, "separatrix"),
        ("outer_wall_loop", 1, "outer wall"),
        ("vacuum_loop", 1, "vacuum"),
    ],
)
def test_unsupported_special_loop_tags_fail(
    field_name,
    field_value,
    message,
) -> None:
    arguments = {field_name: field_value}

    with pytest.raises(ValueError, match=message):
        _manual_spec(**arguments)


def test_unique_loop_must_be_inner_wall() -> None:
    with pytest.raises(ValueError, match="inner wall"):
        _manual_spec(inner_wall_loop=-1)


def test_writer_rejects_non_model_spec() -> None:
    with pytest.raises(TypeError, match="只接受 M3DC1ModelSpec"):
        serialize_m3dc1_model(object())


def test_writer_revalidates_structurally_corrupted_spec() -> None:
    spec = _minimal_spec()
    object.__setattr__(
        spec,
        "faces",
        (
            GeometricFace(1, (1,)),
            GeometricFace(2, (1,)),
        ),
    )

    with pytest.raises(ValueError, match="single-face"):
        serialize_m3dc1_model(spec)


def test_writer_validates_before_touching_destination(tmp_path) -> None:
    destination = tmp_path / "model.txt"
    destination.write_text("original\n", encoding="utf-8")

    spec = _minimal_spec()
    object.__setattr__(spec, "inner_wall_loop", -1)

    with pytest.raises(ValueError, match="inner wall"):
        write_m3dc1_model(spec, destination)

    assert destination.read_text(encoding="utf-8") == "original\n"


def test_writer_preserves_existing_spec_collections() -> None:
    spec = _minimal_spec()
    vertices_before = spec.vertices
    edges_before = spec.edges
    loops_before = spec.loops
    faces_before = spec.faces

    serialize_m3dc1_model(spec)

    assert spec.vertices is vertices_before
    assert spec.edges is edges_before
    assert spec.loops is loops_before
    assert spec.faces is faces_before


def test_complete_minimal_text_layout() -> None:
    expected = (
        "1 -1 1 -1 -1\n"
        "1 4\n"
        "1 0.000000 0.000000 0.000000\n"
        "2 0.000000 1.000000 0.000000\n"
        "3 1.000000 1.000000 0.000000\n"
        "4 1.000000 0.000000 0.000000\n"
        "1 1 2 1\n"
        "2 2 3 1\n"
        "3 3 4 1\n"
        "4 4 1 1\n"
        "1\n"
        "1 1 1\n"
    )

    assert serialize_m3dc1_model(_minimal_spec()) == expected


def test_write_model_creates_requested_file_only(tmp_path) -> None:
    destination = tmp_path / "custom-model-name.txt"

    write_m3dc1_model(_minimal_spec(), destination)

    assert destination.read_text(encoding="utf-8") == (
        serialize_m3dc1_model(_minimal_spec())
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "custom-model-name.txt"
    ]


def test_dataclass_replace_preserves_valid_model() -> None:
    spec = _minimal_spec()
    replaced = replace(spec)

    assert serialize_m3dc1_model(replaced) == serialize_m3dc1_model(spec)
