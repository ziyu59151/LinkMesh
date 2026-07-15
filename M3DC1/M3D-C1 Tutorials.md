# M3D-C1 Tutorials

**Important note: the apostrophes used in this google doc are different from the apostrophes used in IDL.  Please do not directly copy the IDL commands from this google doc into IDL, or the apostrophe discrepancy will result in strange IDL errors.**

# Setting up M3D-C1

## Use M3D-C1 Release Versions by Loading Modules

The easiest way to use M3D-C1 is to use pre-installed release versions of M3D-C1.  On the PPPL cluster, this can be done using modules:  
	module use /p/m3dc1/modules  
	module load m3dc1/1.15

Release versions of M3D-C1 have also been installed on a number of other systems.  The location of the M3D-C1 modules for each of these systems is:  
	PPPL Cluster:		module use /p/m3dc1/modules  
	NERSC Perlmutter:	module use /project/projectdirs/mp288/C1/modules/perlmutter  
		CPU:		module load m3dc1/1.15-cpu  
		GPU:		\[ release version not installed \]   
	Princeton Stellar:	module use /projects/M3DC1/modules  
	GA Iris:		module use /fusion/projects/codes/m3dc1/modules

## Set Up IDL

Most of the post-processing tools for M3D-C1 are written in IDL.  Loading the M3D-C1 module will automatically set the IDL\_PATH variable to include the directory that contains the M3D-C1 IDL post-processing tools.  However, IDL must also be configured to properly output graphics (this is a general issue with IDL and not related to the M3D-C1 postprocessing tools).  To configure IDL automatically on startup, we recommend setting the environment variable

	setenv IDL\_STARTUP $HOME/.idl\_startup

The file $HOME/.idl\_startup should contain the following line:

	device, retain=2, decomposed=0, true\_color=24

## Set up a test directory to run tutorials

The tutorials must be run in a directory to which you have permission to write data.  You may set up a directory in your own home directory to run these tutorials, for example:  
	  
mkdir $HOME/m3dc1\_tutorials

Of course, this directory could be named differently or placed elsewhere.  But in this document, we will assume that your local directory for running the tutorials is called $HOME/m3dc1\_tutorials.

## Tutorial directories:

On portal.pppl.gov:  
M3DC1\_TUTORIAL\_DIR=/p/tsc/nferraro/data/Tutorials

On stellar.princeton.edu:  
M3DC1\_TUTORIAL\_DIR=/projects/M3DC1/Tutorials

# Creating a Multi-Region Mesh

	cp \-r $M3DC1\_TUTORIAL\_DIR/Create\_Multiregion\_Mesh $HOME/m3dc1\_tutorials/  
	cd $HOME/m3dc1\_tutorials/Create\_Multiregion\_Mesh

## Step 1: Define the first wall

The first wall should be defined in a text file, where the first line contains the number of (R, Z) points that define the wall, and the subsequent lines contain the (R, Z) values in two columns.  The first wall for a number of devices are defined in the $M3DC1\_DIR/device\_data directory.  
cp  $M3DC1\_DIR/unstructured/device\_data/DIII-D/first\_wall.pts .

## Step 2: Create the mesh

The mesh is created using the m3dc1\_mfmgen utility.  On some systems this can be run directly from the shell using  
	m3dc1\_mfmgen input

However, since m3dc1\_mfmgen is an MPI application, some systems (such as Stellar) require it to be submitted through the job scheduler.  On stellar, this can be done using:  
	sbatch batchjob.stellar

This script will look for the input file “input”, which has a number of options that are explained in the file.  If successful, a mesh file with a name like “diiid-8K0.smb” and a model file with a name like “diiid.txt” should be created.

# Using an EFIT Equilibrium

This tutorial describes how to set up M3D-C1 to use an equilibrium from EFIT.  This includes reading the data into M3D-C1 and packing the mesh to resolve the equilibrium well.

## Step 1: Interpolate the EFIT data

The first step is to interpolate the EFIT data onto the M3D-C1 mesh.  This is done to ensure that M3D-C1 mesh is sized appropriately for the equilibrium data.  
cp \-r $M3DC1\_TUTORIAL\_DIR/Setup\_EFIT\_Equilibrium $HOME/m3dc1\_tutorials/  
cd $HOME/m3dc1\_tutorials/Setup\_EFIT\_Equilibrium

### Step 1a: Copy the EFIT g-file to “geqdsk”

	cp g158115.04701\_590 geqdsk

### Step 1b: Define coils and coil currents

Coil geometry data is available for a number of facilities in the $M3D-C1/device\_data directory.  This example uses DIII-D geometry.  
cp $M3DC1\_DIR/unstructured/device\_data/DIII-D/coil.dat .

The coil currents are different for each case, and can be extracted from the EFIT a-file using the a2cc utility:  
a2cc a158115.04701\_590 \> current.dat

### Step 1c: Define kinetic profiles

The “extract\_profiles.sh” script can be used to create ascii files in a format readable by M3D-C1 from EFIT p-files and other formats, such as Tom Osborne’s Python Tools and GAprofiles:  
	extract\_profiles.sh p158115.04701\_590  
This will create ascii files containing profile data for several kinetic profiles.  The ascii files each have two columns: the first is the normalized poloidal flux, and the second is the corresponding value of the kinetic data.  Extract\_profiles.sh will create the following files (assuming the data is available):  
	profile\_ne: electron density in units of m\-3  
	profile\_te: electron temperature in units of keV  
	profile\_omega: ExB rotation in units of krad/s  
These profiles will be read by M3D-C1 if iread\_ne=1, iread\_te=1, and iread\_omega\_ExB=1 in C1input respectively.

Kinetic profiles are often defined only up until psi\_N=1.  By default, M3D-C1 will use this outermost value at all points with psi\_N greater than the maximum psi\_N defined in the profile file.  This can lead to unphysically large values of Te, for example, since the value of Te is often \~60--100 eV at psi\_N \= 1\.  An IDL function “extend\_profile” exists to extrapolate these kinetic profiles beyond the last psi\_N value provided in the file.  For example, to extend the Te profile using the data in profile\_te, run  
	IDL\> extend\_profile, ‘profile\_te’, psimax=1.1, minval=2e-4, fitrange=\[0.9,1\], smooth=5![][image1]  
This function fits a modified tanh to the data in profile\_te from 0.9 \< psi\_N \< 1 such that the asymptotic value as psi\_N → infinity is 2e-4 keV.  This function is then used to define Te in the range 1 \< psi\_N \< 1.1.  The data in the range covered by profile\_te (psi\_N \< 1\) is not modified.  In order to ensure that a discontinuity does not occur at psi\_N \= 1, the function then does a boxcar averaging over 5 data points around psi\_N \= 1\.  The extrapolated profile is written to the file profile\_te.extended.  If you wish to use this profile in place of the original profile\_te file,  
	mv profile\_te.extended profile\_te

### Step 1d: Copy the mesh files and Run M3D-C1

cp ../Create\_Multiregion\_Mesh/diiid-\*.smb .  
cp ../Create\_Multiregion\_Mesh/diiid.txt .  
sbatch batchjob.$M3DC1\_ARCH.interpolate  
This script uses C1input.interpolate, and moves the output into a subdirectory called “interpolated/”

### Step 1e: Verify solution

IDL\> plot\_field, 'jy', \-1, /iso, /lcfs, /bound, range=\[-1,1\], file=’interpolated/C1.h5’  
	  
You should check to make sure that:

1. No coils are inside the “extended-MHD” or “resistive wall” regions of the mesh; and  
2. The EFIT grid extends beyond the “extend-MHD” region of the mesh in all directions.  The extent of the EFIT grid can be inferred from the current density in the interpolated solution.  In this example, it can be seen that the EFIT grid spans roughly 0.8 \< R \< 2.5 and \-1.5 \< Z \< 1.5

![][image2]

## Step 2: Refine the equilibrium using the M3D-C1 Grad-Shafranov Solver

### Step 2a: Run M3D-C1

sbatch batchjob.$M3DC1\_ARCH.refine  
This batch script uses C1input file C1input.refine.

### Step 2b: Verify solution

IDL\> plot\_field, 'jy', \-1, /iso, /lcfs, /bound, range=\[-1,1\]  
![][image3]

### Step 2c: Compare M3D-C1 solution to interpolated EFIT data

IDL\> plot\_shape, \['interpolated/C1.h5', 'C1.h5'\], /iso, rrange=\[0.8, 2.5\], zrange=\[-1.5,1.5\]  
![][image4]

## Step 3: Adapt the mesh

### Step 3a: Run M3D-C1

sbatch batchjob.$M3DC1\_ARCH.adapt  
This script uses C1input file C1input.adapt.

### Step 3b: Verify output

After the bach job has finished completed, there should be a new series of files “ts0-adapted\#.smb” representing the partitions of the adapted mesh created by each MPI task.  There should also be a combined mesh file mesh0.smb that is created by the “collapse” utility after M3D-C1 has finished running.

## Step 4: Verify the new mesh

### Step 4a: Run M3D-C1

sbatch batchjob.$M3DC1\_ARCH.test  
This script uses C1input file C1input.test

### Step 4b: Verify output

IDL\> plot\_mesh, /iso  
![][image5]

## Step 5: Verify the M3D-C1 equilibrium

It is very important to check that the equilibrium solution is well-resolved and physically realistic; otherwise the output from any subsequent stability or response calculations will be suspect.  In particular, you should check that all thermodynamic quantities are positive:  
	plot\_field, ‘ne’, \-1, cutz=0, /mks, /ylog  
	plot\_field, ‘Te’, \-1, cutz=0, /mks, /ylog  
	plot\_field, ‘Ti’, \-1, cutz=0, /mks, /ylog  
If you find that one of these is negative near or outside the separatrix, there are a few ways to improve the situation:

1. If ne \< 0 somewhere, then   
   1. If iread\_ne \= 1, then make sure profile\_ne contains only positive values.  If the values in profile\_ne get very small at large psi\_N, then these either need to be increased or the mesh resolution should be increased  
   2. If iread\_ne \= 0, then try increasing pedge or increasing the mesh resolution  
2. If Te \< 0 somewhere, then  
   1. If iread\_Te \= 1, then make sure profile\_Te contains only positive values.  If the values in profile\_Te get very small at large psi\_N, then these either need to be increased or the mesh resolution should be increased  
   2. If iread\_Te \= 0, then try increasing pedge or increasing the mesh resolution  
3. If Ti \< 0 somewhere, then increase pedge

If you find that Ti is too large outside the separatrix, then reduce pedge.

You should also double check other equilibrium quantities to verify that these profiles are as you expect.  For example, you can plot the equilibrium safety factor profile:  
	plot\_flux\_average, ‘q’, \-1  
![][image6]  
and the equilibrium rotation profile:  
	plot\_omega  
![][image7]

# Linear Stability

	cp \-r $M3DC1\_TUTORIAL\_DIR/Linear\_stability $HOME/m3dc1\_tutorials/  
	cd $HOME/m3dc1\_tutorials/Linear\_stability

## Step 1: Run M3D-C1

	cp ../Setup\_EFIT\_Equilibrium/mesh0.smb .  
	cp ../Setup\_EFIT\_Equilibrium/diiid.txt .  
	cp ../Setup\_EFIT\_Equilibrium/g158115.04701\_590 geqdsk  
sbatch batchjob.$M3DC1\_ARCH

## Step 2: Calculate the growth rate

	IDL\> plot\_scalar, ‘ke’, /growth

The “/growth” option to plot\_scalar will plot the derivative of the log of the quantity in question.  So the above example will plot t Twhere Tis the total kinetic energy in the simulation.  Note that if uet then Te2t, so  t T=2, so the asymptotic value plotted here is actually twice the growth rate of the mode.

## Step 3: Plot the Eigenfunction

IDL\> plot\_field, 'p', /last, /linear, q=1, /iso, /bound, rrange=\[0.8, 2.5\], zrange=\[-1.5,1.5\], /lcfs

![][image8]

# Linear Plasma Response to Non-Axisymmetric Fields

cp \-r $M3DC1\_TUTORIAL\_DIR/Linear\_RMP $HOME/m3dc1\_tutorials/  
cd $HOME/m3dc1\_tutorials/Linear\_RMP

## Step 1: Run M3D-C1	

cp ../Setup\_EFIT\_Equilibrium/mesh0.smb .  
	cp ../Setup\_EFIT\_Equilibrium/diiid.txt .  
	cp ../Setup\_EFIT\_Equilibrium/g158115.04701\_590 geqdsk  
sbatch batchjob.$M3DC1\_ARCH

## Step 2: Analyze the perturbed field spectrum

### Step 2a: Compute the perturbed field spectrum

Compute the perturbed field spectrum for the applied field:  
	plot\_br, points=600, slice=0, bmncdf=’bmn\_vac.nc’  
and for the total field:  
	plot\_br, points=600, slice=1, bmncdf=’bmn.nc’  
By default, these functions calculate the poloidal Fourier components of the normal perturbed fields in PEST coordinates.  Alternatively, Hamada or Boozer coordinates can be used by specifying /hamada or /boozer in the calls to plot\_br.

### Step 2b: Plot the perturbed field spectrum

The Fourier components can be plotted as a function of radius:  
IDL\> plot\_m\_vs\_r, 'bmn.nc', mrange=\[-12, \-1\]  
![][image9]  
Note that in this case, the plasma is left-handed (IP is in the opposite direction from BT), and therefore it is the negative m components that are resonant with the plasma response.

The resonant components of the perturbed field can be plotted as a function of radius:  
IDL\> plot\_bmn, \['bmn\_vac.nc','bmn.nc'\], /netcdf, /ylog, names=\['Vacuum', 'Total'\], out=’bmn’  
![][image10]  
This will output the vacuum and total resonant field data to the files ‘bmn1’ and ‘bmn2’ respectively.

Similarly, the island widths and chirikov parameters can be plotted:  
IDL\> plot\_bmn, \['bmn\_vac.nc','bmn.nc'\], /netcdf, /ylog, names=\['Vacuum', 'Total'\], /width, out='island\_widths'  
IDL\> plot\_bmn, \['bmn\_vac.nc','bmn.nc'\], /netcdf, /ylog, names=\['Vacuum', 'Total'\], /chirikov, out='chirikov'  
Note that the chirikov parameters are calculated at psi\_N values intermediate to the resonant surfaces.
