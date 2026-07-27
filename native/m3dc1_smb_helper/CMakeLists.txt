cmake_minimum_required(VERSION 3.20)

project(linkmesh_m3dc1_smb_helper LANGUAGES CXX)

find_package(MPI REQUIRED COMPONENTS CXX)
find_package(SCOREC 2.2.9 EXACT CONFIG REQUIRED)

add_executable(
  linkmesh-m3dc1-smb-helper
  main.cc
)

target_compile_features(
  linkmesh-m3dc1-smb-helper
  PRIVATE
    cxx_std_17
)

target_link_libraries(
  linkmesh-m3dc1-smb-helper
  PRIVATE
    MPI::MPI_CXX
    SCOREC::mds
    SCOREC::apf
    SCOREC::gmi
    SCOREC::pcu
)

set_target_properties(
  linkmesh-m3dc1-smb-helper
  PROPERTIES
    CXX_EXTENSIONS OFF
)
