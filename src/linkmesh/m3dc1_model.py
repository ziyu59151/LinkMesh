"""
M3D-C1 single-face analytic geometric model specification.

This module implements the M4-1A in-memory target model and the adapter from
Mesh2D.outer_boundary. It does not depend on PUMI, APF, MDS, MPI, Simmetrix,
SMB, SMD, or SMS.

The TXT contract follows the common behavior of:

- meshgen save_model()/save_multi_rgn_model()
- m3dc1_scorec load_model()

M4-1A P0 supports exactly one region, one geometric face, and one geometric
loop. The loop is represented by ordered linear geometric edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from numbers import Integral
from typing import TYPE_CHECKING, Any

import numpy as np

from linkmesh.mesh import (
    Mesh2D,
    _validate_outer_boundary as _mesh_validate_outer_boundary,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class CurveType(IntEnum):
    """M3D-C1 curve type numeric codes."""

    LIN = 1
    POLY = 2
    BSPLINE = 3


def _require_positive_tag(value: Any, name: str) -> int:
    """Validate and return a positive integer geometric tag."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} 必须是正整数，实际={value!r}")
    tag = int(value)
    if tag <= 0:
        raise ValueError(f"{name} 必须是正整数，实际={tag}")
    return tag


def _require_special_loop_tag(value: Any, name: str) -> int:
    """Validate a special loop tag, where -1 means absent."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} 必须是 -1 或正整数，实际={value!r}")
    tag = int(value)
    if tag == -1 or tag > 0:
        return tag
    raise ValueError(f"{name} 必须是 -1 或正整数，实际={tag}")


def _require_contiguous_tags(tags: list[int], entity_name: str) -> None:
    """Require deterministic contiguous 1-based tags for the P0 model."""
    expected = list(range(1, len(tags) + 1))
    if tags != expected:
        raise ValueError(
            f"{entity_name} tag 必须按确定性 1-based 连续编号；"
            f"期望={expected}，实际={tags}"
        )


def _normalize_finite_pair(value: Any, name: str) -> tuple[float, float]:
    """Normalize a coordinate pair to an immutable finite float tuple."""
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (2,):
        raise ValueError(f"{name} 必须为二维坐标对，实际 shape={array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} 含非有限值（NaN/Inf）")
    return float(array[0]), float(array[1])


@dataclass(frozen=True)
class M3DC1Curve:
    """Curve representation serialized after an edge header.

    LIN has no additional fields.

    POLY and BSPLINE carry the same serialized spline payload consumed by
    load_model(): order, number of control points, order+num_points knots,
    followed by num_points pairs of R/Z control coordinates. The reference
    save_model() canonicalizes POLY to the BSPLINE numeric code when writing.
    """

    curve_type: CurveType = CurveType.LIN
    order: int | None = None
    knots: tuple[float, ...] = ()
    control_points: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        try:
            curve_type = CurveType(self.curve_type)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"curve_type 必须是 LIN(1)、POLY(2) 或 BSPLINE(3)，"
                f"实际={self.curve_type!r}"
            ) from exc

        object.__setattr__(self, "curve_type", curve_type)

        knots = tuple(float(value) for value in self.knots)
        control_points = tuple(
            _normalize_finite_pair(point, f"control_points[{index}]")
            for index, point in enumerate(self.control_points)
        )
        object.__setattr__(self, "knots", knots)
        object.__setattr__(self, "control_points", control_points)

        self.validate()

    @property
    def serialized_curve_type(self) -> CurveType:
        """Return the curve code emitted by reference save_model()."""
        if self.curve_type is CurveType.POLY:
            return CurveType.BSPLINE
        return self.curve_type

    def validate(self) -> None:
        """Validate curve type and required serialized payload."""
        if self.curve_type is CurveType.LIN:
            if self.order is not None or self.knots or self.control_points:
                raise ValueError(
                    "LIN 曲线不得包含 order、knots 或 control_points 附加字段"
                )
            return

        if isinstance(self.order, bool) or not isinstance(self.order, Integral):
            raise ValueError(
                f"{self.curve_type.name} 曲线的 order 必须是正整数，"
                f"实际={self.order!r}"
            )

        order = int(self.order)
        if order <= 0:
            raise ValueError(
                f"{self.curve_type.name} 曲线的 order 必须大于 0，实际={order}"
            )

        num_points = len(self.control_points)
        if num_points < 2:
            raise ValueError(
                f"{self.curve_type.name} 曲线至少需要 2 个控制点，"
                f"实际={num_points}"
            )
        if num_points < order:
            raise ValueError(
                f"{self.curve_type.name} 曲线控制点数不得小于 order："
                f"num_points={num_points}，order={order}"
            )

        expected_knots = order + num_points
        if len(self.knots) != expected_knots:
            raise ValueError(
                f"{self.curve_type.name} 曲线 knot 数量错误："
                f"期望 order+num_points={expected_knots}，"
                f"实际={len(self.knots)}"
            )

        knot_array = np.asarray(self.knots, dtype=np.float64)
        if not np.all(np.isfinite(knot_array)):
            raise ValueError(
                f"{self.curve_type.name} 曲线 knots 含非有限值（NaN/Inf）"
            )
        if np.any(np.diff(knot_array) < 0.0):
            raise ValueError(
                f"{self.curve_type.name} 曲线 knots 必须单调不减"
            )


@dataclass(frozen=True)
class GeometricVertex:
    """M3D-C1 geometric vertex."""

    tag: int
    r: float
    z: float
    y: float = 0.0

    def __post_init__(self) -> None:
        tag = _require_positive_tag(self.tag, "geometric vertex tag")
        coordinates = np.asarray([self.r, self.z, self.y], dtype=np.float64)
        if not np.all(np.isfinite(coordinates)):
            raise ValueError(
                f"geometric vertex {tag} 坐标含非有限值（NaN/Inf）"
            )
        if float(self.y) != 0.0:
            raise ValueError(
                f"M4-1A P0 geometric vertex {tag} 的第三坐标必须为 0，"
                f"实际={self.y}"
            )

        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "r", float(self.r))
        object.__setattr__(self, "z", float(self.z))
        object.__setattr__(self, "y", 0.0)


@dataclass(frozen=True)
class GeometricEdge:
    """Directed M3D-C1 geometric edge."""

    tag: int
    begin_vertex_tag: int
    end_vertex_tag: int
    curve: M3DC1Curve = field(default_factory=M3DC1Curve)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tag",
            _require_positive_tag(self.tag, "geometric edge tag"),
        )
        object.__setattr__(
            self,
            "begin_vertex_tag",
            _require_positive_tag(
                self.begin_vertex_tag,
                f"geometric edge {self.tag} begin vertex tag",
            ),
        )
        object.__setattr__(
            self,
            "end_vertex_tag",
            _require_positive_tag(
                self.end_vertex_tag,
                f"geometric edge {self.tag} end vertex tag",
            ),
        )
        if self.begin_vertex_tag == self.end_vertex_tag:
            raise ValueError(
                f"geometric edge {self.tag} 起点和终点相同："
                f"vertex={self.begin_vertex_tag}，形成零长度拓扑边"
            )
        if not isinstance(self.curve, M3DC1Curve):
            raise ValueError(
                f"geometric edge {self.tag} 的 curve 必须是 M3DC1Curve，"
                f"实际={type(self.curve).__name__}"
            )
        self.curve.validate()


@dataclass(frozen=True)
class GeometricLoop:
    """Ordered edge references forming one closed geometric loop."""

    tag: int
    edge_tags: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tag",
            _require_positive_tag(self.tag, "geometric loop tag"),
        )
        edge_tags = tuple(
            _require_positive_tag(value, f"geometric loop {self.tag} edge tag")
            for value in self.edge_tags
        )
        object.__setattr__(self, "edge_tags", edge_tags)

        if len(edge_tags) < 3:
            raise ValueError(
                f"geometric loop {self.tag} 至少需要 3 条边，"
                f"实际={len(edge_tags)}"
            )
        if len(set(edge_tags)) != len(edge_tags):
            raise ValueError(
                f"geometric loop {self.tag} 含重复 edge tag：{edge_tags}"
            )


@dataclass(frozen=True)
class GeometricFace:
    """M3D-C1 geometric face and its bounding loop references."""

    tag: int
    loop_tags: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tag",
            _require_positive_tag(self.tag, "geometric face tag"),
        )
        loop_tags = tuple(
            _require_positive_tag(value, f"geometric face {self.tag} loop tag")
            for value in self.loop_tags
        )
        object.__setattr__(self, "loop_tags", loop_tags)

        if len(loop_tags) != 1:
            raise ValueError(
                f"M4-1A P0 geometric face {self.tag} 必须且只能引用 1 个 loop，"
                f"实际={len(loop_tags)}"
            )


@dataclass(frozen=True)
class M3DC1ModelSpec:
    """Validated single-region, single-face M3D-C1 analytic model."""

    vertices: tuple[GeometricVertex, ...]
    edges: tuple[GeometricEdge, ...]
    loops: tuple[GeometricLoop, ...]
    faces: tuple[GeometricFace, ...]
    separatrix_loop: int = -1
    inner_wall_loop: int = 1
    outer_wall_loop: int = -1
    vacuum_loop: int = -1

    def __post_init__(self) -> None:
        object.__setattr__(self, "vertices", tuple(self.vertices))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "loops", tuple(self.loops))
        object.__setattr__(self, "faces", tuple(self.faces))
        object.__setattr__(
            self,
            "separatrix_loop",
            _require_special_loop_tag(
                self.separatrix_loop,
                "separatrix_loop",
            ),
        )
        object.__setattr__(
            self,
            "inner_wall_loop",
            _require_special_loop_tag(
                self.inner_wall_loop,
                "inner_wall_loop",
            ),
        )
        object.__setattr__(
            self,
            "outer_wall_loop",
            _require_special_loop_tag(
                self.outer_wall_loop,
                "outer_wall_loop",
            ),
        )
        object.__setattr__(
            self,
            "vacuum_loop",
            _require_special_loop_tag(
                self.vacuum_loop,
                "vacuum_loop",
            ),
        )
        self.validate()

    @property
    def num_loops(self) -> int:
        """Number written as the first integer in the model header."""
        return len(self.loops)

    @property
    def num_faces(self) -> int:
        """Number written before the face records."""
        return len(self.faces)

    def validate(self) -> None:
        """Validate the complete M4-1A P0 model contract."""
        if len(self.loops) != 1:
            raise ValueError(
                "M4-1A P0 只支持 single-loop 模型，"
                f"实际 loop 数={len(self.loops)}"
            )
        if len(self.faces) != 1:
            raise ValueError(
                "M4-1A P0 只支持 single-face 模型，"
                f"实际 face 数={len(self.faces)}"
            )
        if len(self.vertices) < 3:
            raise ValueError(
                "M4-1A P0 模型至少需要 3 个 geometric vertices，"
                f"实际={len(self.vertices)}"
            )
        if len(self.edges) != len(self.vertices):
            raise ValueError(
                "single-loop 模型的 geometric edge 数必须等于 vertex 数："
                f"vertices={len(self.vertices)}，edges={len(self.edges)}"
            )

        for index, vertex in enumerate(self.vertices):
            if not isinstance(vertex, GeometricVertex):
                raise ValueError(
                    f"vertices[{index}] 必须是 GeometricVertex，"
                    f"实际={type(vertex).__name__}"
                )
        for index, edge in enumerate(self.edges):
            if not isinstance(edge, GeometricEdge):
                raise ValueError(
                    f"edges[{index}] 必须是 GeometricEdge，"
                    f"实际={type(edge).__name__}"
                )
        for index, loop in enumerate(self.loops):
            if not isinstance(loop, GeometricLoop):
                raise ValueError(
                    f"loops[{index}] 必须是 GeometricLoop，"
                    f"实际={type(loop).__name__}"
                )
        for index, face in enumerate(self.faces):
            if not isinstance(face, GeometricFace):
                raise ValueError(
                    f"faces[{index}] 必须是 GeometricFace，"
                    f"实际={type(face).__name__}"
                )

        vertex_tags = [vertex.tag for vertex in self.vertices]
        edge_tags = [edge.tag for edge in self.edges]
        loop_tags = [loop.tag for loop in self.loops]
        face_tags = [face.tag for face in self.faces]

        for tags, entity_name in (
            (vertex_tags, "geometric vertex"),
            (edge_tags, "geometric edge"),
            (loop_tags, "geometric loop"),
            (face_tags, "geometric face"),
        ):
            if len(set(tags)) != len(tags):
                raise ValueError(f"{entity_name} tag 存在重复：{tags}")
            _require_contiguous_tags(tags, entity_name)

        vertex_tag_set = set(vertex_tags)
        edge_by_tag = {edge.tag: edge for edge in self.edges}
        loop_tag_set = set(loop_tags)

        for edge in self.edges:
            if edge.begin_vertex_tag not in vertex_tag_set:
                raise ValueError(
                    f"geometric edge {edge.tag} 起点引用不存在的 vertex "
                    f"{edge.begin_vertex_tag}"
                )
            if edge.end_vertex_tag not in vertex_tag_set:
                raise ValueError(
                    f"geometric edge {edge.tag} 终点引用不存在的 vertex "
                    f"{edge.end_vertex_tag}"
                )
            edge.curve.validate()

        loop = self.loops[0]
        if set(loop.edge_tags) != set(edge_tags):
            raise ValueError(
                f"geometric loop {loop.tag} 必须且只能引用全部 geometric edges："
                f"loop={loop.edge_tags}，edges={edge_tags}"
            )

        for index, edge_tag in enumerate(loop.edge_tags):
            if edge_tag not in edge_by_tag:
                raise ValueError(
                    f"geometric loop {loop.tag} 引用不存在的 edge {edge_tag}"
                )
            current_edge = edge_by_tag[edge_tag]
            next_edge = edge_by_tag[
                loop.edge_tags[(index + 1) % len(loop.edge_tags)]
            ]
            if current_edge.end_vertex_tag != next_edge.begin_vertex_tag:
                raise ValueError(
                    f"geometric loop {loop.tag} 不连续：edge {current_edge.tag} "
                    f"结束于 vertex {current_edge.end_vertex_tag}，"
                    f"下一条 edge {next_edge.tag} 起始于 "
                    f"vertex {next_edge.begin_vertex_tag}"
                )

        face = self.faces[0]
        for loop_tag in face.loop_tags:
            if loop_tag not in loop_tag_set:
                raise ValueError(
                    f"geometric face {face.tag} 引用不存在的 loop {loop_tag}"
                )
        if face.loop_tags != (loop.tag,):
            raise ValueError(
                f"single-face 模型的 face 必须引用唯一 loop {loop.tag}，"
                f"实际={face.loop_tags}"
            )

        if self.separatrix_loop != -1:
            raise ValueError(
                "M4-1A P0 不支持 separatrix loop，separatrix_loop 必须为 -1"
            )
        if self.inner_wall_loop != loop.tag:
            raise ValueError(
                f"M4-1A P0 唯一 loop 必须标记为 inner wall："
                f"期望 inner_wall_loop={loop.tag}，"
                f"实际={self.inner_wall_loop}"
            )
        if self.outer_wall_loop != -1:
            raise ValueError(
                "M4-1A P0 不支持 outer wall loop，outer_wall_loop 必须为 -1"
            )
        if self.vacuum_loop != -1:
            raise ValueError(
                "M4-1A P0 不支持 vacuum loop，vacuum_loop 必须为 -1"
            )


def _validate_single_region_ids(region_ids_in: Any) -> None:
    """Reject Mesh2D inputs outside the single-region P0 scope."""
    region_float = np.asarray(region_ids_in, dtype=np.float64)
    if region_float.ndim != 1:
        raise ValueError(
            f"Mesh2D.region_ids 必须是一维数组，实际 ndim={region_float.ndim}"
        )
    if region_float.size == 0:
        raise ValueError("Mesh2D.region_ids 为空，无法确认 single-region 拓扑")
    if not np.all(np.isfinite(region_float)):
        raise ValueError("Mesh2D.region_ids 含非有限值（NaN/Inf）")
    if not np.all(region_float == np.round(region_float)):
        raise ValueError("Mesh2D.region_ids 含非整数值")

    region_ids = region_float.astype(np.int64)
    if np.any(region_ids <= 0):
        raise ValueError(
            "Mesh2D.region_ids 必须是正整数区域编号，"
            f"实际最小值={int(region_ids.min())}"
        )

    unique_regions = np.unique(region_ids)
    if unique_regions.size != 1:
        raise ValueError(
            "M4-1A P0 只支持 single-region Mesh2D，"
            f"实际 region IDs={unique_regions.tolist()}"
        )


def build_single_face_model_spec(mesh: Mesh2D) -> M3DC1ModelSpec:
    """Build a single-face M3DC1ModelSpec from Mesh2D.outer_boundary.

    Geometry is taken exclusively from the ordered, implicitly closed
    Mesh2D.outer_boundary. No geometry is inferred from triangles, topology
    boundary nodes, idxevert, boundary markers, or Steiner points.

    The input Mesh2D and all of its NumPy arrays remain unchanged.
    """
    if not isinstance(mesh, Mesh2D):
        raise TypeError(
            f"mesh 必须是 Mesh2D，实际={type(mesh).__name__}"
        )

    _validate_single_region_ids(mesh.region_ids)

    if mesh.outer_boundary is None:
        raise ValueError(
            "Mesh2D.outer_boundary 缺失（None）："
            "M4-1A analytic model 必须使用有序原始外边界"
        )

    boundary = _mesh_validate_outer_boundary(mesh.outer_boundary)
    point_count = int(boundary.shape[0])

    vertices = tuple(
        GeometricVertex(
            tag=index + 1,
            r=float(boundary[index, 0]),
            z=float(boundary[index, 1]),
            y=0.0,
        )
        for index in range(point_count)
    )

    linear_curve = M3DC1Curve(CurveType.LIN)
    edges = tuple(
        GeometricEdge(
            tag=index + 1,
            begin_vertex_tag=index + 1,
            end_vertex_tag=((index + 1) % point_count) + 1,
            curve=linear_curve,
        )
        for index in range(point_count)
    )

    loop = GeometricLoop(
        tag=1,
        edge_tags=tuple(edge.tag for edge in edges),
    )
    face = GeometricFace(tag=1, loop_tags=(loop.tag,))

    return M3DC1ModelSpec(
        vertices=vertices,
        edges=edges,
        loops=(loop,),
        faces=(face,),
        separatrix_loop=-1,
        inner_wall_loop=loop.tag,
        outer_wall_loop=-1,
        vacuum_loop=-1,
    )
