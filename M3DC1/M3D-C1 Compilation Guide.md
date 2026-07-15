# M3D-C1-K Compilation Guide

To compile M3D-C1, you need to install all the dependencies before.

# Spack

For this new method, you first need to install Spack first. You can get it by following the instructions at [https://github.com/spack/spack](https://github.com/spack/spack), or use the Spack provided by the cluster system.

1. Clone the spack repository

git clone \-c feature.manyFiles=true https://github.com/spack/spack.git spack

2. Start spack

. spack-test/share/spack/setup-env.sh

3. Create and activate a spack environment

spack env create m3dc1  
spack env activate m3dc1

4. Now you need to decide the combination of compiler, MPI and LAPACK packages you want to use to compile the PETSC library and M3D-C1. We recommend using the software recommended by the cluster company, like Intel, Nvidia or Cray. Here are some combinations that we recommend

gcc+openmpi+netlib-lapack  
intel(or intel-oneapi)+intel-mpi(or intel-oneapi-mpi)+intel-mkl  
nvhpc+openmpi+nvhpc  
cray+cray-mpich+cray-libsci

Note that some combinations (like intel+openmpi) can cause errors in simulation results.

After you decide the combination, you can add these packages into the m3dc1 spack environment. You can first load these modules like

module load intel

And then ask spack to find the compiler

spack compiler find

You can also add MPI and LAPACK software as external libraries like the compiler. If you want to build the MPI and LAPACK software using spack (for example, using gcc to build openmpi and netlib-lapack) then you can skip this step. Note that most of the MPI and LAPACK libraries cannot be found by spack automatically, so you must add them manually in spack/var/spack/environments/m3dc1/spack.yaml

5. In addition, you can add some other external libraries which is often available in the system, as compiling them can be time consuming,

spack external find cmake gmake hwloc openssl libtool openssh perl pkgconf zlib bzip2 diffutils python autoconf automake m4

6. If you don’t want to use spack to compile M3DC1 (the first option in next section), then you should also add the M3D-C1 dependencies in spack.yaml. Here are the essential dependency list

mpi  
hdf5  
netcdf  
mumps  
superlu-dist  
petsc  
fftw  
gsl  
zoltan  
pumi

You can find examples of the spack environment file in the unstructured/spack folder in M3D-C1 source code. Find the best one that fits your need, and modify the compiler part according to the cluster's setup.

Then you can do 'spack install \-v' to install all the dependencies.

# M3D-C1

To compile M3D-C1 itself, there are three options.

## Spack

The first option is to use Spack to build M3D-C1. M3D-C1 is not in the Spack package repo yet, but I created a Spack package file in the M3D-C1 source code, in unstructured/spack/m3dc1/. You can create a directory in your spack package directory (spack/var/spack/repos/builtin/packages/) called m3dc1, and copy this file into it. Then you can do

spack add m3dc1\~3d\~complex%gcc^openmpi^netlib-lapack

Replace the compiler and dependency package with the ones you want to use. Then

spack concretize \-f

You can check the dependencies tree to make sure it depends on the packages you want. Then

spack install \-v

After the installation finished, run

spack cd \-i m3dc1

You will find the m3dc1 executable there.

Known issues:

1. For GCC version\>12, the gfortran will enable a consistent check for function argument, which can lead to an error when using MPI through ‘include mpi.h’. A temporary solution is to add a fflags for spack spec, like this

spack add m3dc1\~3d\~complex fflags=-fallow-argument-mismatch

## CMake

The second option is to use CMake for both the library and the code. I have created a cmake file in the source code directory. You can create a build directory and run a cmake command inside it. Here is an example

mkdir build && cd build

cmake .. \-DCMAKE\_C\_COMPILER=mpicc \-DCMAKE\_CXX\_COMPILER=mpic++ \-DCMAKE\_Fortran\_COMPILER=mpifort  
\-DCMAKE\_PREFIX\_PATH="/ccs/home/cliu1/project/spack/var/spack/environments/m3dc1/.spack-env/view;/ccs/home/cliu1/project/spack/var/spack/environments/m3dc1/.spack-env/view/petsc-real" \-DENABLE\_PETSC=ON \-DENABLE\_ZOLTAN=ON \-DENABLE\_3D=OFF \-DENABLE\_COMPLEX=OFF \-DENABLE\_PARTICLE=OFF

make \-j8 VERBOSE=1 or cmake \--build . \--verbose \--parallel

## Makefile

The third option is to use the makefile.

You need to compile the m3dc1\_scorec library first. You can find it in the source code. This is a C++ library which has a CMake build system. You can find some examples of how to use cmake in the m3dc1\_scorec/config-files directory.

Then you can create a .mk file in the unstructured directory following other . mk files, and change the library path to your spack view directory. For example, in my system I change the path to /home/cliu/spack/var/spack/environments/m3dc1-complex/.spack-env/view/

Now you can make M3D-C1. You can choose the option depending on which version you need.

for 2D version, make OPT=1  
for 2D complex version, make OPT=1 COM=1  
for 3D version, make 3D=1 OPT=1

