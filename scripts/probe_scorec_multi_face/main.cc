#include <PCU.h>
#include <agm.h>
#include <apf.h>
#include <apfMDS.h>
#include <apfMesh2.h>
#include <gmi.h>
#include <gmi_analytic.h>
#include <mpi.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <exception>
#include <filesystem>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr int kInnerFaceTag = 1;
constexpr int kOuterFaceTag = 2;
constexpr std::size_t kSharedInterfaceEdgeCount = 4;

struct StageError : public std::runtime_error {
  StageError(std::string stage, std::string message)
      : std::runtime_error(std::move(message)),
        stage_(std::move(stage)) {}

  const std::string& stage() const noexcept {
    return stage_;
  }

 private:
  std::string stage_;
};

void require(
    bool condition,
    const char* stage,
    const std::string& message) {
  if (!condition) {
    throw StageError(stage, message);
  }
}

std::string single_line(std::string value) {
  std::replace(value.begin(), value.end(), '\n', ' ');
  std::replace(value.begin(), value.end(), '\r', ' ');
  return value;
}

std::string percent_encode(const std::string& value) {
  static constexpr char kHex[] = "0123456789ABCDEF";
  std::string encoded;
  encoded.reserve(value.size());

  for (const unsigned char character : value) {
    const bool safe =
        (character >= 'a' && character <= 'z') ||
        (character >= 'A' && character <= 'Z') ||
        (character >= '0' && character <= '9') ||
        character == '-' || character == '_' || character == '.' ||
        character == '/' || character == ':' || character == '\\';

    if (safe) {
      encoded.push_back(static_cast<char>(character));
    } else {
      encoded.push_back('%');
      encoded.push_back(kHex[(character >> 4U) & 0x0FU]);
      encoded.push_back(kHex[character & 0x0FU]);
    }
  }
  return encoded;
}

struct PointData {
  std::array<double, 3> coordinates{};
};

struct LineData {
  std::array<double, 3> begin{};
  std::array<double, 3> end{};
};

struct ModelVertex {
  int tag;
  std::array<double, 3> coordinates;
};

struct ModelEdge {
  int tag;
  int begin_vertex_tag;
  int end_vertex_tag;
};

struct MeshNode {
  std::array<double, 3> coordinates;
  int model_dimension;
  int model_tag;
};

struct MeshTriangle {
  std::array<std::size_t, 3> nodes;
  int face_tag;
};

struct MeshEdgeClassification {
  int dimension;
  int tag;
};

using EdgeKey = std::pair<std::size_t, std::size_t>;

constexpr std::array<ModelVertex, 8> kModelVertices{{
    {1, {-0.4, -0.4, 0.0}},
    {2, {0.4, -0.4, 0.0}},
    {3, {0.4, 0.4, 0.0}},
    {4, {-0.4, 0.4, 0.0}},
    {5, {-1.0, -1.0, 0.0}},
    {6, {1.0, -1.0, 0.0}},
    {7, {1.0, 1.0, 0.0}},
    {8, {-1.0, 1.0, 0.0}},
}};

constexpr std::array<ModelEdge, 8> kModelEdges{{
    {1, 1, 2},
    {2, 2, 3},
    {3, 3, 4},
    {4, 4, 1},
    {5, 5, 6},
    {6, 6, 7},
    {7, 7, 8},
    {8, 8, 5},
}};

constexpr std::array<int, 4> kInnerLoopEdgeTags{{1, 2, 3, 4}};
constexpr std::array<int, 4> kOuterLoopEdgeTags{{5, 6, 7, 8}};

constexpr std::array<MeshNode, 8> kMeshNodes{{
    {{{-1.0, -1.0, 0.0}}, 0, 5},
    {{{1.0, -1.0, 0.0}}, 0, 6},
    {{{1.0, 1.0, 0.0}}, 0, 7},
    {{{-1.0, 1.0, 0.0}}, 0, 8},
    {{{-0.4, -0.4, 0.0}}, 0, 1},
    {{{0.4, -0.4, 0.0}}, 0, 2},
    {{{0.4, 0.4, 0.0}}, 0, 3},
    {{{-0.4, 0.4, 0.0}}, 0, 4},
}};

constexpr std::array<MeshTriangle, 10> kMeshTriangles{{
    {{{4, 5, 6}}, kInnerFaceTag},
    {{{4, 6, 7}}, kInnerFaceTag},
    {{{0, 1, 5}}, kOuterFaceTag},
    {{{0, 5, 4}}, kOuterFaceTag},
    {{{1, 2, 6}}, kOuterFaceTag},
    {{{1, 6, 5}}, kOuterFaceTag},
    {{{2, 3, 7}}, kOuterFaceTag},
    {{{2, 7, 6}}, kOuterFaceTag},
    {{{3, 0, 4}}, kOuterFaceTag},
    {{{3, 4, 7}}, kOuterFaceTag},
}};

EdgeKey edge_key(std::size_t first, std::size_t second) {
  return first < second
      ? std::make_pair(first, second)
      : std::make_pair(second, first);
}

const ModelVertex& model_vertex(int tag) {
  for (const auto& vertex : kModelVertices) {
    if (vertex.tag == tag) {
      return vertex;
    }
  }
  throw StageError(
      "fixture",
      "unknown geometric vertex tag=" + std::to_string(tag));
}

const ModelEdge& model_edge(int tag) {
  for (const auto& edge : kModelEdges) {
    if (edge.tag == tag) {
      return edge;
    }
  }
  throw StageError(
      "fixture",
      "unknown geometric edge tag=" + std::to_string(tag));
}

void vertex_function(
    const double[2],
    double xyz[3],
    void* data) {
  const auto* point = static_cast<const PointData*>(data);
  xyz[0] = point->coordinates[0];
  xyz[1] = point->coordinates[1];
  xyz[2] = point->coordinates[2];
}

void line_function(
    const double parameter[2],
    double xyz[3],
    void* data) {
  const auto* line = static_cast<const LineData*>(data);
  const double t = parameter[0];
  for (int dimension = 0; dimension < 3; ++dimension) {
    xyz[dimension] =
        line->begin[dimension] +
        t * (line->end[dimension] - line->begin[dimension]);
  }
}

void face_function(
    const double parameter[2],
    double xyz[3],
    void*) {
  xyz[0] = parameter[0];
  xyz[1] = parameter[1];
  xyz[2] = 0.0;
}

void reparam_zero(const double[2], double to[2], void*) {
  to[0] = 0.0;
  to[1] = 0.0;
}

void reparam_one(const double[2], double to[2], void*) {
  to[0] = 1.0;
  to[1] = 0.0;
}

void edge_to_face_reparam(
    const double from[2],
    double to[2],
    void* data) {
  const auto* line = static_cast<const LineData*>(data);
  const double t = from[0];
  to[0] =
      line->begin[0] +
      t * (line->end[0] - line->begin[0]);
  to[1] =
      line->begin[1] +
      t * (line->end[1] - line->begin[1]);
}

agm_bdry add_boundary(gmi_model* model, gmi_ent* entity) {
  return agm_add_bdry(
      gmi_analytic_topo(model),
      agm_from_gmi(entity));
}

agm_use add_use(
    gmi_model* model,
    agm_bdry boundary,
    int adjacent_tag) {
  agm* topology = gmi_analytic_topo(model);
  const int dimension =
      agm_dim_from_type(agm_bounds(topology, boundary).type);
  gmi_ent* adjacent =
      gmi_find(model, dimension - 1, adjacent_tag);
  require(
      adjacent != nullptr,
      "model_create",
      "cannot find adjacent geometric entity tag=" +
          std::to_string(adjacent_tag));

  return agm_add_use(
      topology,
      boundary,
      agm_from_gmi(adjacent));
}

void add_edge_topology(
    gmi_model* model,
    gmi_ent* edge,
    int begin_vertex_tag,
    int end_vertex_tag) {
  const agm_bdry boundary = add_boundary(model, edge);

  const agm_use begin_use =
      add_use(model, boundary, begin_vertex_tag);
  gmi_add_analytic_reparam(
      model,
      begin_use,
      reparam_zero,
      nullptr);

  const agm_use end_use =
      add_use(model, boundary, end_vertex_tag);
  gmi_add_analytic_reparam(
      model,
      end_use,
      reparam_one,
      nullptr);
}

template <std::size_t EdgeCount>
void add_loop_to_face(
    gmi_model* model,
    gmi_ent* face,
    const std::array<int, EdgeCount>& edge_tags,
    const std::map<int, LineData*>& line_data_by_tag) {
  const agm_bdry boundary = add_boundary(model, face);

  for (const int edge_tag : edge_tags) {
    const auto data_it = line_data_by_tag.find(edge_tag);
    require(
        data_it != line_data_by_tag.end() &&
            data_it->second != nullptr,
        "model_create",
        "cannot find callback data for geometric edge tag=" +
            std::to_string(edge_tag));

    const agm_use edge_use =
        add_use(model, boundary, edge_tag);
    gmi_add_analytic_reparam(
        model,
        edge_use,
        edge_to_face_reparam,
        data_it->second);
  }
}

struct NativeModel {
  gmi_model* model = nullptr;
  std::array<PointData, kModelVertices.size()> point_data{};
  std::array<LineData, kModelEdges.size()> line_data{};

  NativeModel() = default;
  NativeModel(const NativeModel&) = delete;
  NativeModel& operator=(const NativeModel&) = delete;
  NativeModel(NativeModel&&) = delete;
  NativeModel& operator=(NativeModel&&) = delete;

  ~NativeModel() {
    if (model != nullptr) {
      gmi_destroy(model);
    }
  }
};

void create_model(NativeModel& native) {
  native.model = gmi_make_analytic();
  require(
      native.model != nullptr,
      "model_create",
      "gmi_make_analytic returned null");

  for (std::size_t index = 0;
       index < kModelVertices.size();
       ++index) {
    const auto& source = kModelVertices[index];
    auto& data = native.point_data[index];
    data.coordinates = source.coordinates;

    gmi_ent* entity = gmi_add_analytic(
        native.model,
        0,
        source.tag,
        vertex_function,
        nullptr,
        nullptr,
        &data);
    require(
        entity != nullptr,
        "model_create",
        "failed to create geometric vertex tag=" +
            std::to_string(source.tag));
  }

  int edge_periodic = 0;
  double edge_range[2] = {0.0, 1.0};
  std::map<int, LineData*> line_data_by_tag;

  for (std::size_t index = 0;
       index < kModelEdges.size();
       ++index) {
    const auto& source = kModelEdges[index];
    auto& data = native.line_data[index];
    data.begin =
        model_vertex(source.begin_vertex_tag).coordinates;
    data.end =
        model_vertex(source.end_vertex_tag).coordinates;
    line_data_by_tag.emplace(source.tag, &data);

    gmi_ent* entity = gmi_add_analytic(
        native.model,
        1,
        source.tag,
        line_function,
        &edge_periodic,
        &edge_range,
        &data);
    require(
        entity != nullptr,
        "model_create",
        "failed to create geometric edge tag=" +
            std::to_string(source.tag));

    add_edge_topology(
        native.model,
        entity,
        source.begin_vertex_tag,
        source.end_vertex_tag);
  }

  int face_periodic[2] = {0, 0};
  double face_ranges[2][2] = {
      {-1.0, 1.0},
      {-1.0, 1.0},
  };

  gmi_ent* inner_face = gmi_add_analytic(
      native.model,
      2,
      kInnerFaceTag,
      face_function,
      face_periodic,
      face_ranges,
      nullptr);
  require(
      inner_face != nullptr,
      "model_create",
      "failed to create inner geometric face");

  gmi_ent* outer_face = gmi_add_analytic(
      native.model,
      2,
      kOuterFaceTag,
      face_function,
      face_periodic,
      face_ranges,
      nullptr);
  require(
      outer_face != nullptr,
      "model_create",
      "failed to create outer geometric face");

  // Loop 1 is created once as geometric edges 1..4, then used by both
  // face boundaries. Face 2 receives a separate boundary for loop 2.
  add_loop_to_face(
      native.model,
      inner_face,
      kInnerLoopEdgeTags,
      line_data_by_tag);
  add_loop_to_face(
      native.model,
      outer_face,
      kInnerLoopEdgeTags,
      line_data_by_tag);
  add_loop_to_face(
      native.model,
      outer_face,
      kOuterLoopEdgeTags,
      line_data_by_tag);
}

apf::ModelEntity* find_model_entity(
    apf::Mesh2* mesh,
    int dimension,
    int tag) {
  apf::ModelEntity* entity =
      mesh->findModelEntity(dimension, tag);
  require(
      entity != nullptr,
      "mesh_create",
      "cannot find model entity dim=" +
          std::to_string(dimension) +
          " tag=" + std::to_string(tag));
  return entity;
}

std::map<EdgeKey, int> build_edge_incidence() {
  std::map<EdgeKey, int> incidence;
  for (const auto& triangle : kMeshTriangles) {
    const auto& nodes = triangle.nodes;
    ++incidence[edge_key(nodes[0], nodes[1])];
    ++incidence[edge_key(nodes[1], nodes[2])];
    ++incidence[edge_key(nodes[2], nodes[0])];
  }

  for (const auto& item : incidence) {
    require(
        item.second == 1 || item.second == 2,
        "fixture",
        "fixture contains a non-manifold mesh edge");
  }
  return incidence;
}

std::map<EdgeKey, int> build_triangle_face_pairs() {
  std::map<EdgeKey, std::set<int>> faces_by_edge;
  for (const auto& triangle : kMeshTriangles) {
    const auto& nodes = triangle.nodes;
    for (const auto& key : {
             edge_key(nodes[0], nodes[1]),
             edge_key(nodes[1], nodes[2]),
             edge_key(nodes[2], nodes[0])}) {
      faces_by_edge[key].insert(triangle.face_tag);
    }
  }

  std::map<EdgeKey, int> shared_interfaces;
  for (const auto& item : faces_by_edge) {
    if (item.second.size() == 2) {
      require(
          item.second ==
              std::set<int>{kInnerFaceTag, kOuterFaceTag},
          "fixture",
          "interface edge has unexpected adjacent face tags");
      shared_interfaces.emplace(item.first, 1);
    }
  }

  require(
      shared_interfaces.size() == kSharedInterfaceEdgeCount,
      "fixture",
      "fixture does not contain exactly four shared interface edges");
  return shared_interfaces;
}

MeshEdgeClassification classify_mesh_edge(const EdgeKey& key) {
  static const std::map<EdgeKey, int> kGeometricEdgeByMeshEdge{
      {edge_key(4, 5), 1},
      {edge_key(5, 6), 2},
      {edge_key(6, 7), 3},
      {edge_key(7, 4), 4},
      {edge_key(0, 1), 5},
      {edge_key(1, 2), 6},
      {edge_key(2, 3), 7},
      {edge_key(3, 0), 8},
  };

  const auto geometric_it = kGeometricEdgeByMeshEdge.find(key);
  if (geometric_it != kGeometricEdgeByMeshEdge.end()) {
    return {1, geometric_it->second};
  }

  if (key == edge_key(4, 6)) {
    return {2, kInnerFaceTag};
  }

  return {2, kOuterFaceTag};
}

std::filesystem::path rank0_path(
    const std::filesystem::path& base) {
  return base.parent_path() /
      (base.stem().string() + "0" + base.extension().string());
}

struct ProbeResult {
  std::size_t mesh_vertices = 0;
  std::size_t mesh_edges = 0;
  std::size_t mesh_triangles = 0;
  std::size_t shared_interface_edges = 0;
  std::filesystem::path rank0_output;
};

ProbeResult create_and_write_mesh(
    gmi_model* model,
    const std::filesystem::path& output_base) {
  const auto edge_incidence = build_edge_incidence();
  const auto shared_interfaces = build_triangle_face_pairs();

  apf::Mesh2* mesh = apf::makeEmptyMdsMesh(model, 2, false);
  require(
      mesh != nullptr,
      "mesh_create",
      "makeEmptyMdsMesh returned null");

  try {
    std::array<apf::MeshEntity*, kMeshNodes.size()> vertices{};

    for (std::size_t index = 0;
         index < kMeshNodes.size();
         ++index) {
      const auto& source = kMeshNodes[index];
      const apf::Vector3 coordinate(
          source.coordinates[0],
          source.coordinates[1],
          source.coordinates[2]);
      const apf::Vector3 parameter(0.0, 0.0, 0.0);

      vertices[index] = mesh->createVertex(
          find_model_entity(
              mesh,
              source.model_dimension,
              source.model_tag),
          coordinate,
          parameter);
      require(
          vertices[index] != nullptr,
          "mesh_create",
          "createVertex returned null for node=" +
              std::to_string(index));
    }

    std::map<EdgeKey, apf::MeshEntity*> mesh_edges;
    for (const auto& item : edge_incidence) {
      const EdgeKey& key = item.first;
      const auto classification = classify_mesh_edge(key);

      apf::Downward downward{};
      downward[0] = vertices[key.first];
      downward[1] = vertices[key.second];

      apf::MeshEntity* entity = mesh->createEntity(
          apf::Mesh::EDGE,
          find_model_entity(
              mesh,
              classification.dimension,
              classification.tag),
          downward);
      require(
          entity != nullptr,
          "mesh_create",
          "createEntity(EDGE) returned null");

      const bool inserted =
          mesh_edges.emplace(key, entity).second;
      require(
          inserted,
          "mesh_create",
          "duplicate mesh edge entity");
    }

    for (std::size_t index = 0;
         index < kMeshTriangles.size();
         ++index) {
      const auto& source = kMeshTriangles[index];

      apf::Downward downward{};
      downward[0] =
          mesh_edges.at(edge_key(source.nodes[0], source.nodes[1]));
      downward[1] =
          mesh_edges.at(edge_key(source.nodes[1], source.nodes[2]));
      downward[2] =
          mesh_edges.at(edge_key(source.nodes[2], source.nodes[0]));

      apf::MeshEntity* entity = mesh->createEntity(
          apf::Mesh::TRIANGLE,
          find_model_entity(mesh, 2, source.face_tag),
          downward);
      require(
          entity != nullptr,
          "mesh_create",
          "createEntity(TRIANGLE) returned null for triangle=" +
              std::to_string(index));
    }

    mesh->acceptChanges();
    mesh->verify();
    mesh->writeNative(output_base.string().c_str());

    const auto output_rank0 = rank0_path(output_base);
    require(
        std::filesystem::is_regular_file(output_rank0),
        "write_native",
        "writeNative did not create rank-0 SMB: " +
            output_rank0.string());
    require(
        std::filesystem::file_size(output_rank0) > 0,
        "write_native",
        "writeNative created an empty rank-0 SMB: " +
            output_rank0.string());

    ProbeResult result{
        mesh->count(0),
        mesh->count(1),
        mesh->count(2),
        shared_interfaces.size(),
        output_rank0,
    };

    require(
        result.mesh_vertices == kMeshNodes.size(),
        "mesh_verify",
        "unexpected mesh vertex count");
    require(
        result.mesh_edges == edge_incidence.size(),
        "mesh_verify",
        "unexpected mesh edge count");
    require(
        result.mesh_triangles == kMeshTriangles.size(),
        "mesh_verify",
        "unexpected mesh triangle count");

    apf::disownMdsModel(mesh);
    mesh->destroyNative();
    apf::destroyMesh(mesh);
    mesh = nullptr;
    return result;
  } catch (...) {
    if (mesh != nullptr) {
      apf::disownMdsModel(mesh);
      mesh->destroyNative();
      apf::destroyMesh(mesh);
    }
    throw;
  }
}

std::filesystem::path parse_arguments(int argc, char** argv) {
  if (argc != 3 || std::string(argv[1]) != "--output-base") {
    throw StageError(
        "arguments",
        "usage: linkmesh-scorec-multiface-probe "
        "--output-base <base.smb>");
  }

  std::filesystem::path output_base(argv[2]);
  require(
      output_base.extension() == ".smb",
      "arguments",
      "output base must end with .smb");
  require(
      !output_base.stem().string().empty(),
      "arguments",
      "output base filename is empty");
  require(
      output_base.stem().string().back() != '0',
      "arguments",
      "output base appears to be an already ranked rank-0 path");

  const auto parent = output_base.parent_path();
  require(
      parent.empty() || std::filesystem::is_directory(parent),
      "arguments",
      "output parent directory does not exist: " +
          parent.string());

  return output_base;
}

}  // namespace

int main(int argc, char** argv) {
  bool mpi_initialized = false;
  bool pcu_initialized = false;

  try {
    const auto output_base = parse_arguments(argc, argv);

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
      throw StageError("mpi_init", "MPI_Init failed");
    }
    mpi_initialized = true;

    require(
        PCU_Comm_Init() == PCU_SUCCESS,
        "pcu_init",
        "PCU_Comm_Init failed");
    pcu_initialized = true;

    int peer_count = 0;
    require(
        MPI_Comm_size(MPI_COMM_WORLD, &peer_count) == MPI_SUCCESS,
        "runtime_validate",
        "MPI_Comm_size failed");
    require(
        peer_count == 1 && PCU_Comm_Peers() == 1,
        "runtime_validate",
        "multi-face probe only supports one MPI rank");

    ProbeResult result;
    {
      NativeModel native_model;
      create_model(native_model);
      result = create_and_write_mesh(
          native_model.model,
          output_base);
    }

    std::cout
        << "LINKMESH_MULTIFACE_PROBE_OK"
        << " vertices=" << result.mesh_vertices
        << " edges=" << result.mesh_edges
        << " triangles=" << result.mesh_triangles
        << " face_tags=" << kInnerFaceTag << ',' << kOuterFaceTag
        << " shared_interface_edges="
        << result.shared_interface_edges
        << " rank0="
        << percent_encode(result.rank0_output.string())
        << '\n';

    require(
        PCU_Comm_Free() == PCU_SUCCESS,
        "pcu_free",
        "PCU_Comm_Free failed");
    pcu_initialized = false;

    require(
        MPI_Finalize() == MPI_SUCCESS,
        "mpi_finalize",
        "MPI_Finalize failed");
    mpi_initialized = false;
    return 0;
  } catch (const StageError& error) {
    std::cerr
        << "LINKMESH_MULTIFACE_PROBE_ERROR stage="
        << percent_encode(error.stage())
        << " message="
        << percent_encode(single_line(error.what()))
        << '\n';
  } catch (const std::exception& error) {
    std::cerr
        << "LINKMESH_MULTIFACE_PROBE_ERROR stage=unexpected"
        << " message="
        << percent_encode(single_line(error.what()))
        << '\n';
  } catch (...) {
    std::cerr
        << "LINKMESH_MULTIFACE_PROBE_ERROR stage=unexpected"
        << " message=unknown_native_exception\n";
  }

  if (pcu_initialized) {
    PCU_Comm_Free();
  }
  if (mpi_initialized) {
    MPI_Finalize();
  }
  return 1;
}
