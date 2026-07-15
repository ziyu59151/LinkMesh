# Introduction to the M3D-C1 MHD Simulation Code

## 1. Overview

M3D-C1 is a high-order finite-element code for three-dimensional, nonlinear magnetohydrodynamic (MHD) simulation of magnetically confined plasmas, especially tokamak plasmas. It is designed to study global macroscopic plasma dynamics over multiple physical timescales, including ideal-MHD waves and instabilities, resistive reconnection, sawtooth cycles, and transport-timescale evolution.

The code sits in a demanding numerical regime. Tokamak MHD contains fast wave physics, slower reconnection physics, and still slower transport processes. A useful simulation may need to follow the slow dynamics without being forced to take time steps set by the fastest MHD waves. M3D-C1 addresses this challenge using a high-continuity finite-element representation together with implicit or semi-implicit time advance methods and scalable preconditioning.

The related M3D-C1-K extension couples M3D-C1's fluid MHD solver to a kinetic energetic-particle module. This enables hybrid kinetic-MHD simulations in which the bulk plasma is evolved with MHD equations while energetic particles are evolved with particle methods and coupled back to the MHD fields through pressure or current coupling schemes.

These notes are based on the following local reference PDFs:

- `Non-Ideal Effects on the Stability and Transport.pdf`
- `Jardin et al. - 2012 - Multiple timescale calculations of sawteeth and ot.pdf`
- `Liu et al. - 2022 - Hybrid simulation of energetic particles interacti.pdf`

## 2. Scientific Motivation

MHD is a fluid model for the low-frequency behavior of magnetized plasma. It is especially useful for large-scale stability, global equilibrium, magnetic reconnection, and macroscopic transport. In fusion plasmas, these phenomena are central to understanding confinement and operational limits.

However, realistic fusion plasmas are not governed by one clean timescale. A simulation may need to resolve or model:

- Fast ideal-MHD wave propagation.
- Global MHD instabilities.
- Resistive magnetic reconnection.
- Parallel and perpendicular transport.
- Non-ideal effects such as viscosity, resistivity, two-fluid physics, finite-Larmor-radius effects, and energetic-particle feedback.

Explicit time-stepping methods can become impractical because the Courant-Friedrichs-Lewy condition ties the stable time step to the fastest waves and smallest mesh elements. M3D-C1 is built around numerical methods that allow larger time steps, so that long-time nonlinear MHD phenomena can be simulated efficiently.

## 3. Key Features

### 3.1 Three-dimensional nonlinear MHD

M3D-C1 solves MHD equations as an initial-value problem in realistic toroidal geometry. It is intended for global simulations where the full three-dimensional structure matters, such as sawtooth oscillations, tearing-like dynamics, nonlinear mode evolution, and tokamak transport-timescale calculations.

The code has been used for simulations spanning multiple timescales, including repeated sawtooth cycles in tokamak plasmas. This requires more than simply resolving a short instability event; it requires a numerically stable and efficient method that can continue through repeated relaxation and recovery phases.

Ferraro et al. 2016 emphasize that, in the multi-region resistive-wall formulation, a different set of equations is solved in each mesh region. In the plasma region, M3D-C1 uses the full two-fluid model:

$$
\frac{\partial n_i}{\partial t}
+ \nabla\cdot(n_i\mathbf{v}) = 0 ,
$$

$$
m_i n_i
\left[
{\partial \mathbf{v} \over \partial t}
+ \mathbf{v}\cdot\nabla\mathbf{v}
\right]
=
\mathbf{J}\times\mathbf{B}
- \nabla p
- \nabla\cdot\boldsymbol{\Pi}_i ,
$$

$$
\frac{\partial p}{\partial t}
+ \mathbf{v}\cdot\nabla p
+ \Gamma p \nabla\cdot\mathbf{v}
=
(\Gamma - 1)
\left[
\eta J^2
- \nabla\cdot\mathbf{q}
- \boldsymbol{\Pi}_i:\nabla\mathbf{v}
\right]
+ {1\over n_e e}
\mathbf{J}\cdot
\left(
\nabla p_e
- \Gamma { \nabla n_i \over n_i} p_e
\right),
$$

$$
\frac{\partial p_e}{\partial t}
+ \mathbf{v}\cdot\nabla p_e
+ \Gamma p_e \nabla\cdot\mathbf{v}
=
(\Gamma - 1)
\left[
\eta J^2
- \nabla\cdot\mathbf{q}_e
\right]
+ {1\over n_e e}
\mathbf{J}\cdot
\left(
\nabla p_e
- \Gamma { \nabla n_i \over n_i} p_e
\right),
$$

$$
{\partial \mathbf{B}^p \over \partial t}
=
-\nabla\times\mathbf{E}.
$$

The closure terms in the same paper are

$$
\boldsymbol{\Pi}
=
-\mu
\left(
\nabla\mathbf{v}
+ \nabla\mathbf{v}^{t}
\right)
+ \boldsymbol{\Pi}_i^{\parallel}
+ \boldsymbol{\Pi}_i^{\wedge},
$$

$$
\mathbf{E}
=
\eta\mathbf{J}
- \mathbf{v}\times\mathbf{B}
+ {1\over n_e e}
\left(
\mathbf{J}\times\mathbf{B}
- \nabla p_e
\right),
$$

$$
\mathbf{q}
=
-\kappa\nabla(T_e + T_i),
$$

$$
\mathbf{q}_{e,i}
=
-\kappa\nabla T_e
-\kappa_{\parallel}
{\mathbf{B}\mathbf{B}\over B^2}\cdot\nabla T_e .
$$

Here $n_i$ is ion density, $\mathbf{v}$ is the plasma velocity, $m_i$ is ion mass, $p$ is total pressure, $p_e$ is electron pressure, $\mathbf{B}^p$ is the magnetic field advanced dynamically by M3D-C1, $\mathbf{J}$ is current density, $\mathbf{E}$ is electric field, $\eta$ is resistivity, $\boldsymbol{\Pi}_i$ represents viscous and gyroviscous stress, and $\mathbf{q}$ and $\mathbf{q}_e$ are heat fluxes.

The multi-region formulation then simplifies the equations outside the plasma. In the resistive-wall region, Ferraro et al. keep only the resistive Faraday law

$$
{\partial \mathbf{B}^p \over \partial t}
=
-\nabla\times(\eta_w\mathbf{J}^p),
$$

while in the external vacuum region the field is constrained to remain current-free:

$$
\nabla\times\mathbf{B}^p = 0 .
$$

This is the key distinction from a single-domain MHD model: the plasma, resistive wall, and external vacuum are all represented inside one computational mesh, but the active equations differ by region. Together, these equations describe nonlinear feedback between plasma flow, pressure evolution, magnetic-field evolution, wall currents, and vacuum magnetic response.

### 3.2 High-order C1 finite elements

One of the defining numerical features of M3D-C1 is its use of high-order finite elements with C1 continuity.

In ordinary C0 finite elements, fields are continuous across element boundaries, but their first derivatives may be discontinuous. In C1 finite elements, both the fields and appropriate first derivatives are continuous across element boundaries. This higher continuity is important for formulations in which the equations involve higher spatial derivatives or where smooth field representations improve the quality of derived quantities such as magnetic fields, currents, vorticity, and pressure gradients.

Jardin et al. describe M3D-C1 as using a triangular wedge high-order finite element formed as a tensor product:

- A reduced quintic triangular element in the poloidal `(R, Z)` plane.
- A Hermite cubic element in the toroidal angle.

This gives a three-dimensional wedge element suitable for toroidal plasma geometry. In the cited formulation, each scalar field has 12 degrees of freedom at each node, reflecting the high-order C1 representation.

### 3.3 Unstructured 3D mesh

M3D-C1 uses unstructured triangular meshing in poloidal planes. The unstructured mesh is valuable because tokamak geometry and plasma physics often demand nonuniform spatial resolution. Mesh elements can be concentrated in regions where gradients, current sheets, resonances, or boundary geometry require finer resolution.

![Triangular wedge finite element from Jardin et al. 2012](assets/m3d_c1_triangular_wedge_element.png)

*Figure: triangular wedge integration volume used in M3D-C1, reproduced from the local Jardin et al. 2012 PDF. The 3D element is built from a reduced quintic triangle in the poloidal `(R, Z)` plane and a Hermite cubic element in the toroidal angle.*

![Multi-region M3D-C1 mesh from Ferraro et al. 2016](assets/ferraro2016_multiregion_mesh.png)

*Figure: multi-region M3D-C1 mesh from Ferraro et al. 2016. The left panel shows a global `(R, Z)` mesh with plasma, vacuum, resistive-wall, and outer-domain boundaries; the right panel zooms near the lower divertor and shows how the resistive-wall region is discretized.*

This mesh illustrates the free-boundary extension of M3D-C1. Instead of treating the plasma boundary as an isolated computational edge, the simulation domain includes neighboring vacuum and resistive-wall regions. That lets the code represent wall currents, vacuum magnetic response, separatrix geometry, and plasma-wall coupling within one finite-element framework. The same unstructured triangular mesh idea is used across regions, while different reduced equations can be solved in different physical regions.

The 3D structure can be viewed as a sequence of toroidal planes. The poloidal plane uses an unstructured triangular discretization, while the toroidal direction has a structured coupling between neighboring planes. This structure is useful both physically and computationally:

- It adapts naturally to complex cross-sectional geometry.
- It supports localized resolution where needed.
- It produces block-structured matrix systems in the toroidal direction.
- It enables block-based preconditioning strategies.

The tensor-product wedge representation also explains why the code can combine geometric flexibility with solver structure. The poloidal plane can be unstructured, while the toroidal direction remains ordered by planes. In the implicit solve, this leads to strong coupling within a plane and more structured coupling between neighboring toroidal planes, a property exploited by block-Jacobi preconditioning.

## 4. The C1 Hermite Basis and Field Representation

The "C1" in M3D-C1 refers to the continuity of the finite-element basis. The code uses basis functions that enforce continuity of the represented fields and their derivatives across element boundaries.

In broad terms:

- The poloidal plane uses high-order triangular basis functions.
- The toroidal direction uses Hermite cubic basis functions.
- The full 3D element is a tensor-product wedge.
- Scalar fields are represented with multiple nodal degrees of freedom, not just nodal values.

This kind of representation is more complex than lower-order finite elements, but it provides a smooth field structure that is well matched to the MHD formulation used in the code.

### 4.1 Finite element method: basis functions, test functions, and Galerkin projection

The finite element method (FEM) is a way to approximate a continuous field by breaking the domain into small elements and representing the field inside each element with simple local functions. For M3D-C1, the elements are triangular wedges in 3D toroidal geometry. In a simpler one-dimensional example, the domain might be divided as

$$
x_0 < x_1 < x_2 < \cdots < x_N .
$$

Instead of solving for an unknown function $u(x)$ at every point, FEM approximates it with a finite expansion

$$
u_h(x) = \sum_{j=1}^{N_\mathrm{dof}} U_j \phi_j(x).
$$

Here:

- $u_h$ is the finite-element approximation to $u$.
- $\phi_j(x)$ are basis functions.
- $U_j$ are the unknown coefficients, or degrees of freedom.
- $N_\mathrm{dof}$ is the number of degrees of freedom in the discrete problem.

A basis function is a shape function used to build the approximate solution. In a standard nodal Lagrange element, $\phi_j$ is often chosen so that

$$
\phi_j(x_i) = \delta_{ij},
$$

meaning that basis function $j$ is one at node $j$ and zero at the other nodes. In Hermite elements, the degrees of freedom include both values and derivatives, so the basis functions are designed to control not only $u(x_i)$ but also derivative quantities such as $u'(x_i)$.

To turn a differential equation into algebraic equations, FEM uses test functions. A test function is a function used to measure the residual error of the approximate solution. Suppose the continuous problem is written abstractly as

$$
\mathcal{L}(u) = f
\qquad \text{in } \Omega .
$$

If we insert the approximation $u_h$, the equation is generally not satisfied pointwise:

$$
R(u_h) = \mathcal{L}(u_h) - f \ne 0 .
$$

The Galerkin method requires this residual to be orthogonal to every test function $w_i$ in the chosen finite-dimensional test space:

$$
\int_\Omega w_i R(u_h)\,d\Omega = 0,
\qquad i = 1,\ldots,N_\mathrm{dof}.
$$

In the standard Galerkin finite element method, the test functions are chosen from the same space as the basis functions:

$$
w_i = \phi_i .
$$

This choice converts the original differential equation into a weak form. For example, consider the Poisson equation

$$
-\nabla^2 u = f
\qquad \text{in } \Omega .
$$

Multiplying by a test function $w$ and integrating gives

$$
\int_\Omega w(-\nabla^2 u)\,d\Omega
=
\int_\Omega wf\,d\Omega .
$$

After integration by parts, the second derivative is transferred from $u$ to the test function:

$$
\int_\Omega \nabla w\cdot\nabla u\,d\Omega
- \int_{\partial\Omega} w\,\nabla u\cdot\mathbf{n}\,dS
=
\int_\Omega wf\,d\Omega .
$$

Boundary conditions determine what happens to the boundary term. For a simple Dirichlet problem, the main volume equation becomes

$$
\int_\Omega \nabla w\cdot\nabla u\,d\Omega
=
\int_\Omega wf\,d\Omega .
$$

Now insert the finite-element expansion

$$
u_h = \sum_j U_j\phi_j,
\qquad
w_i=\phi_i .
$$

The discrete equations become

$$
\sum_j U_j
\int_\Omega \nabla\phi_i\cdot\nabla\phi_j\,d\Omega
=
\int_\Omega \phi_i f\,d\Omega,
\qquad i=1,\ldots,N_\mathrm{dof}.
$$

This is a matrix equation

$$
\mathbf{K}\mathbf{U} = \mathbf{F},
$$

where

$$
K_{ij}
=
\int_\Omega \nabla\phi_i\cdot\nabla\phi_j\,d\Omega,
\qquad
F_i
=
\int_\Omega \phi_i f\,d\Omega .
$$

For time-dependent MHD, the same idea is applied to much larger systems of coupled nonlinear equations. The unknown coefficient vector $\mathbf{U}$ contains the finite-element degrees of freedom for fields such as velocity, pressure, magnetic vector potential, current-related variables, and temperature-like quantities. The matrices are assembled element by element, boundary conditions are applied, and the resulting sparse algebraic systems are advanced in time using implicit or semi-implicit methods.

### 4.2 What a Hermite basis stores

A Lagrange finite element usually stores only function values at interpolation points. A Hermite finite element stores both function values and derivative information.

For a scalar field $u(x)$ in one dimension, a cubic Hermite element on the interval $[x_0,x_1]$ stores four degrees of freedom:

$$
u_0 = u(x_0),
\qquad
u'_0 = \left.{du\over dx}\right|_{x=x_0},
\qquad
u_1 = u(x_1),
\qquad
u'_1 = \left.{du\over dx}\right|_{x=x_1}.
$$

This is enough to construct a cubic polynomial whose value and derivative match at both ends of the element.

### 4.3 One-dimensional cubic Hermite example

Let

$$
h = x_1 - x_0,
\qquad
s = \frac{x-x_0}{h},
\qquad
0 \le s \le 1 .
$$

The cubic Hermite interpolation formula is:

$$
u(x)
=
H_{00}(s)u_0
+ h H_{10}(s)u'_0
+ H_{01}(s)u_1
+ h H_{11}(s)u'_1 .
$$

The four basis functions are:

$$
H_{00}(s) = 2s^3 - 3s^2 + 1,
$$

$$
H_{10}(s) = s^3 - 2s^2 + s,
$$

$$
H_{01}(s) = -2s^3 + 3s^2,
$$

$$
H_{11}(s) = s^3 - s^2 .
$$

These are constructed so that:

$$
H_{00} \leftrightarrow u(x_0),
\qquad
H_{10} \leftrightarrow u'(x_0),
\qquad
H_{01} \leftrightarrow u(x_1),
\qquad
H_{11} \leftrightarrow u'(x_1).
$$

More explicitly:

$$
H_{00}(0)=1,\quad H_{00}(1)=0,\quad
H'_{00}(0)=0,\quad H'_{00}(1)=0,
$$

$$
H_{10}(0)=0,\quad H_{10}(1)=0,\quad
H'_{10}(0)=1,\quad H'_{10}(1)=0,
$$

$$
H_{01}(0)=0,\quad H_{01}(1)=1,\quad
H'_{01}(0)=0,\quad H'_{01}(1)=0,
$$

$$
H_{11}(0)=0,\quad H_{11}(1)=0,\quad
H'_{11}(0)=0,\quad H'_{11}(1)=1.
$$

The factors of $h$ in the interpolation formula are important because $H_{10}$ and $H_{11}$ are defined in the dimensionless coordinate $s$, while $u'_0$ and $u'_1$ are derivatives with respect to the physical coordinate $x$.

### 4.4 Why Hermite elements are C1

Consider two neighboring 1D elements sharing a node:

```text
x0 ---- x1 ---- x2
```

The element on $[x_0,x_1]$ and the element on $[x_1,x_2]$ both use the same nodal value $u(x_1)$ and the same nodal derivative $u'(x_1)$. Therefore, the reconstructed function and its first derivative agree when crossing the shared node.

That is the core idea of C1 continuity:

```text
u is continuous
du/dx is continuous
```

In higher dimensions, the same idea generalizes by storing values and derivative-type degrees of freedom at nodes. The bookkeeping is more complicated, but the purpose is the same: neighboring elements share enough derivative information that the assembled global field is smoother than a standard C0 finite-element field.

### 4.5 Key features of Hermite basis functions

Key properties:

- They represent both field values and derivatives as degrees of freedom.
- They produce C1-continuous fields when neighboring elements share derivative data consistently.
- They allow smooth evaluation of derived quantities involving gradients.
- They are useful for equations or weak forms that involve higher spatial derivatives.
- They reduce derivative jumps at element boundaries.
- They are more complex than C0 Lagrange elements because each node carries more information.

For M3D-C1, the Hermite cubic element appears in the toroidal direction of the triangular wedge element. Combined with the high-order reduced quintic triangular element in the poloidal plane, this gives a smooth 3D representation appropriate for the code's MHD variables and implicit operators.

The high-continuity representation is particularly important in the context of M3D-C1's implicit and split-implicit algorithms. Jardin et al. note that when split-implicit methods and annihilation operators are applied to the M3D-C1 field representation, fourth-order spatial derivatives can arise. A C1 finite-element representation is therefore not just a geometric choice; it is tied to the mathematical structure of the time-advance algorithm.

### 4.6 M3D-C1 scalar field representation for V, B, and J

The document `3D-Equations (1).pdf` gives a compact summary of the field representation used in the 3D two-fluid M3D-C1 equations. The code uses cylindrical coordinates:

$$
(R,\varphi,Z),
\qquad
\nabla\varphi = \frac{1}{R}\hat{\varphi}.
$$

It defines the perpendicular, or poloidal-plane, gradient as:

$$
\nabla_\perp a = a_R \hat{R} + a_Z \hat{Z}.
$$

The key point is that M3D-C1 does not simply store the three Cartesian components of the velocity and magnetic field. Instead, it represents the velocity field and magnetic vector potential using scalar potentials. In Chapter 0, the primary scalar variables are:

```text
U       stream-function-like scalar for poloidal/incompressible flow
omega   toroidal velocity scalar
chi     scalar associated with compressional/potential flow
f       magnetic scalar related to toroidal-field variation
psi     magnetic flux-like scalar
F0      constant related to the externally imposed toroidal-field coil current
```

The velocity field is represented as:

$$
\mathbf{V}
=
R^2 \nabla U \times \nabla\varphi
+ \omega R^2 \nabla\varphi
+ R^{-2}\nabla_\perp \chi .
$$

This decomposition separates the velocity into three parts:

- $R^2\nabla U\times\nabla\varphi$: poloidal, stream-function-like flow.
- $\omega R^2\nabla\varphi$: toroidal flow.
- $R^{-2}\nabla_\perp\chi$: compressional or potential-like poloidal contribution.

This is closely related to why the momentum equation can be projected onto scalar variables. Instead of solving directly for all vector components, M3D-C1 advances scalar fields whose derivatives reconstruct the vector velocity.

The magnetic vector potential is represented as:

$$
\mathbf{A}
=
R^2\nabla\varphi\times\nabla f
+ \psi\nabla\varphi
- F_0 \ln R\, \hat{Z}.
$$

The magnetic field is then obtained from:

$$
\mathbf{B} = \nabla\times\mathbf{A}.
$$

Using the representation above, Chapter 0 writes the magnetic field as:

$$
\mathbf{B}
=
\nabla\psi\times\nabla\varphi
- \nabla_\perp f'
+ F\nabla\varphi,
$$

or equivalently,

$$
\mathbf{B}
=
\nabla\psi\times\nabla\varphi
- \nabla f'
+ F^*\nabla\varphi.
$$

Here a prime denotes a toroidal derivative:

$$
f' = \frac{\partial f}{\partial\varphi},
\qquad
f'' = \frac{\partial^2 f}{\partial\varphi^2}.
$$

The scalars $F$ and $F^*$ are defined by:

$$
F = F_0 + R^2\nabla\cdot\nabla_\perp f,
$$

$$
F^* = F_0 + R^2\nabla^2 f = F + f''.
$$

Physically, $\psi$ plays a flux-like role in the poloidal magnetic field, while $F$ or $F^*$ represents the toroidal-field component in a way that is compatible with the 3D scalar-potential representation.

The current density is not an independent primary variable in this representation. It is computed from Ampere's law, up to normalization:

$$
\mathbf{J} = \nabla\times\mathbf{B}.
$$

Chapter 0 gives:

$$
\mathbf{J}
=
\nabla F^*\times\nabla\varphi
+ \frac{1}{R^2}\nabla_\perp\psi'
- \Delta^*\psi\,\nabla\varphi.
$$

The operator $\Delta^*$ is the Grad-Shafranov-like elliptic operator:

$$
\Delta^*\psi
=
R^2\nabla\cdot\left(R^{-2}\nabla_\perp\psi\right)
=
\frac{\partial^2\psi}{\partial R^2}
- \frac{1}{R}\frac{\partial\psi}{\partial R}
+ \frac{\partial^2\psi}{\partial Z^2}.
$$

The related perpendicular Laplacian-like operator is:

$$
\Delta^\dagger u
=
\nabla_\perp^2 u
=
\nabla\cdot\nabla_\perp u
=
\frac{\partial^2u}{\partial R^2}
+ \frac{1}{R}\frac{\partial u}{\partial R}
+ \frac{\partial^2u}{\partial Z^2}.
$$

The representation has several important consequences:

- $\nabla\cdot\mathbf{B}=0$ is built in because $\mathbf{B}$ is represented as the curl of $\mathbf{A}$.
- The magnetic and velocity fields are advanced through scalar variables, which supports the projection and annihilation-operator strategy used by the implicit solver.
- The toroidal field contains both the imposed constant $F_0$ and the plasma-generated contribution from $f$.
- The current density $\mathbf{J}$ follows from derivatives of $\psi$ and $F^*$, so smooth C1 field representations are valuable for obtaining well-behaved derived current and force terms.
- The representation naturally separates poloidal and toroidal structure while still allowing fully 3D variation through toroidal derivatives such as $f'$ and $\psi'$.

There is also gauge freedom in the definition of $f$. Chapter 0 notes that constants can be added in ways that leave $\mathbf{B}$ unchanged. This is typical of vector-potential formulations: the physically meaningful quantity is the magnetic field, while the potential representation has gauge choices.

### 4.7 Annihilation operators and velocity variables

M3D-C1 uses a particular choice of velocity variables and associated annihilation operators. The purpose is to approximately separate the dynamics associated with the main MHD wave families:

- Alfvén waves.
- Slow magnetosonic waves.
- Fast magnetosonic waves.

Jardin et al. motivate this from the low-beta tokamak wave hierarchy. In that limit, the three ideal-MHD wave families become nearly distinct:

- The slow wave propagates mainly parallel to $\mathbf{B}$ and compresses the fluid along the field.
- The shear Alfvén wave propagates mainly parallel to $\mathbf{B}$, is approximately incompressible, and bends magnetic field lines.
- The fast wave can propagate across $\mathbf{B}$ and compresses the fluid perpendicular to the field.

For nearly perpendicular tokamak perturbations, $k\cdot\mathbf{B}\simeq 0$, the characteristic speeds satisfy

$$
V_F \gg V_A \gg V_S .
$$

The fast wave is therefore the stiffest part of the system. If all three wave families remain strongly mixed in one matrix, the implicit velocity solve has a very large condition number. The annihilation-operator strategy is designed to reorganize the velocity equation so the dominant pieces of the three wave families appear mostly in separate diagonal blocks.

The first step is to represent the 3D velocity in cylindrical coordinates $(R,\phi,Z)$ using three scalar variables:

$$
\mathbf{V}
=
R^2\nabla U\times\nabla\phi
+ R^2\omega\nabla\phi
+ {1\over R^2}\nabla_\perp\chi .
$$

Here $\nabla_\perp$ is the gradient in the $(R,Z)$ plane, orthogonal to $\nabla\phi$. In this representation:

- $U$ is mainly associated with shear Alfvén dynamics.
- $\omega$ is mainly associated with slow-wave dynamics.
- $\chi$ is mainly associated with fast-wave dynamics.

The reason this helps is that the three pieces have different compressional properties. The $U$ term is built so that it does not compress the strong toroidal magnetic field. The $\omega$ term also does not compress the toroidal field strongly. The $\chi$ term is the part that compresses the toroidal field and therefore carries most of the fast-wave stiffness.

Instead of taking Cartesian projections of the vector momentum equation, M3D-C1 applies three scalar annihilation projections:

$$
\nabla\phi\cdot\nabla_\perp\times R^2,
$$

$$
R^2\nabla\phi\cdot,
$$

$$
-\nabla_\perp\cdot R^{-2}.
$$

These operators are called annihilation operators because, when applied to the velocity representation, they suppress or eliminate parts of the vector field associated with the other scalar components. In practice they act like physics-aware projections: each projection produces a scalar equation whose dominant terms couple most strongly to one of the scalar velocity variables.

The resulting association is:

$$
\nabla\phi\cdot\nabla_\perp\times R^2
\quad \longrightarrow \quad
U
\quad \text{and shear Alfvén dynamics},
$$

$$
R^2\nabla\phi\cdot
\quad \longrightarrow \quad
\omega
\quad \text{and slow-wave dynamics},
$$

$$
-\nabla_\perp\cdot R^{-2}
\quad \longrightarrow \quad
\chi
\quad \text{and fast-wave dynamics}.
$$

Schematically, the transformed velocity matrix has the form

$$
\mathbf{A}
\approx
\begin{bmatrix}
A_U & \epsilon_{U\omega} & \epsilon_{U\chi} \\
\epsilon_{\omega U} & A_\omega & \epsilon_{\omega\chi} \\
\epsilon_{\chi U} & \epsilon_{\chi\omega} & A_\chi
\end{bmatrix},
$$

where the diagonal blocks $A_U$, $A_\omega$, and $A_\chi$ contain most of the shear-Alfvén, slow-wave, and fast-wave dynamics, respectively, while the off-diagonal blocks are comparatively smaller couplings. The matrix is not exactly block diagonal, but it becomes much more block-diagonally dominant than it would be under a generic component-wise projection.

Jardin et al. also point out that this structure supports reduced and full MHD variants:

- Keeping only $U$ gives a two-variable reduced-MHD model.
- Keeping $U$ and $\omega$ gives a four-variable reduced-MHD model.
- Keeping $U$, $\omega$, and $\chi$ gives the full-MHD velocity representation.

The practical solver benefit is that the condition number relevant to Krylov convergence is closer to the condition number of the individual diagonal blocks than to the condition number of the entire unsplit matrix. In the eigenvalue examples in the paper, the annihilation projections split the spectrum into groups associated with the Alfvén, slow, and fast waves. This approximate spectral separation is what makes the later block-Jacobi preconditioning effective.

## 5. Semi-implicit and Implicit Time Advance

### 5.1 Why implicit or semi-implicit methods are needed

The MHD equations contain fast waves and instabilities that impose severe restrictions on explicit time stepping. If the goal is to simulate slower physical processes, such as resistive evolution or transport-timescale sawtooth cycles, an explicit method may spend most of its computation resolving waves that are not the main physics target.

Implicit and semi-implicit methods address this by treating the stiff parts of the equations in a way that relaxes the explicit CFL time-step restriction. The time step can then be chosen primarily for accuracy and physical resolution rather than only for numerical stability.

### 5.2 Split implicit method

Jardin et al. describe a split implicit method, also called a differential approximation, that reduces the size and improves the structure of the implicit matrix equation solved at each time step.

The basic idea is:

1. Linearize the time advance around the current state.
2. Separate or eliminate variables so the resulting implicit system is smaller and better conditioned.
3. Use physics-based transformations to expose the different MHD wave families.
4. Solve the resulting sparse linear system with Krylov methods such as GMRES.

This approach is designed to handle the multiple wave timescales present in full MHD.

### 5.3 Method of differential approximation

Sections 9.5.5 and 9.5.6 of Jardin's *Computational Methods in Plasma Physics* give useful background for the semi-implicit strategy used in multidimensional MHD codes. The starting point is a stiff hyperbolic system whose fastest waves would normally impose a severe explicit time-step limit.

A model one-dimensional wave system is:

$$
\frac{\partial v}{\partial t}
=
c\frac{\partial \omega}{\partial x},
\qquad
\frac{\partial \omega}{\partial t}
=
c\frac{\partial v}{\partial x}.
$$

Combining the two equations gives:

$$
\frac{\partial^2 v}{\partial t^2}
=
L(v),
\qquad
L(v)=c^2\frac{\partial^2 v}{\partial x^2}.
$$

The method of differential approximation modifies the time advance so that the stiff wave operator appears inside an elliptic solve:

$$
\left(1-\theta^2\Delta t^2 L\right)v^{n+1}
=
\left(1-\alpha\Delta t^2 L\right)v^n
+ \Delta t\,c\left(\frac{\partial\omega}{\partial x}\right)^m .
$$

The companion variable is then advanced using a weighted derivative of the old and new $v$:

$$
\omega^{m+1}
=
\omega^m
+ \Delta t\,c\,\phi
\left(\frac{\partial v}{\partial x}\right)^{n+1}
+ \Delta t\,c\,(1-\phi)
\left(\frac{\partial v}{\partial x}\right)^n .
$$

The important practical point is that the method replaces a fully coupled implicit update with a sequence of simpler solves. Instead of solving for all wave variables simultaneously, one solves an elliptic equation for one variable and then updates the companion variable.

Two parameter choices discussed by Jardin are especially important:

- Caramana differential approximation: $\phi=1$ and $\alpha=\theta^2$.
- Split $\theta$-implicit method: $\phi=\theta$ and $\alpha=\theta(\theta-1)$.

For the Caramana method, the stability analysis gives a non-dissipative linearly stable method for $\theta\ge 1/2$. It is also second-order accurate in time for stable values of $\theta$ and has a useful steady-state property: when $v^{n+1}=v^n$, the added differential-approximation operator cancels between the two sides and does not change the steady solution.

For the split $\theta$-implicit method, the method is stable for $\theta\ge 1/2$, but it is non-dissipative only at $\theta=1/2$ and second-order accurate only at that same centered value.

The computational advantage is that the operator:

$$
1-\theta^2\Delta t^2 L
$$

is typically symmetric, diagonally dominant, and much easier to solve than a fully implicit unsplit system.

### 5.4 Ideal-MHD operator used in the differential approximation

For ideal MHD, Jardin derives the wave operator by differentiating the momentum equation in time and substituting the ideal magnetic-field and pressure evolution equations.

Ignoring density variation and convective terms for clarity, the momentum equation is written schematically as:

$$
\rho_0\dot{\mathbf{u}}+\nabla p
=
\frac{1}{\mu_0}(\nabla\times\mathbf{B})\times\mathbf{B}.
$$

The ideal induction and pressure equations are:

$$
\dot{\mathbf{B}}
=
\nabla\times(\mathbf{u}\times\mathbf{B}),
$$

$$
\dot{p}
=
-\mathbf{u}\cdot\nabla p
-\gamma p\nabla\cdot\mathbf{u}.
$$

Substituting these into the time-differentiated momentum equation identifies the ideal-MHD wave operator:

$$
L(\mathbf{u})
=
\frac{1}{\mu_0}
\left\{
\nabla\times[\nabla\times(\mathbf{u}\times\mathbf{B})]
\right\}
\times\mathbf{B}
$$

$$
\quad
+ \frac{1}{\mu_0}
\left\{
(\nabla\times\mathbf{B})
\times
\nabla\times(\mathbf{u}\times\mathbf{B})
\right\}
+ \nabla\left(
\mathbf{u}\cdot\nabla p
+\gamma p\nabla\cdot\mathbf{u}
\right).
$$

The corresponding velocity advance has the schematic form:

$$
\left(\rho_0-\theta^2\Delta t^2 L\right)\mathbf{u}^{n+1}
=
\left(\rho_0-\theta^2\Delta t^2 L\right)\mathbf{u}^{n}
+\Delta t
\left[
-\nabla p
+\frac{1}{\mu_0}(\nabla\times\mathbf{B})\times\mathbf{B}
\right]^{n+1/2}.
$$

Once $\mathbf{u}^{n+1}$ is found, the magnetic field and pressure are advanced using time-centered combinations of old and new velocity:

$$
\dot{\mathbf{B}}
=
\nabla\times\left(
[\theta\mathbf{u}^{n+1}+(1-\theta)\mathbf{u}^{n}]
\times\mathbf{B}
\right),
$$

$$
\dot{p}
=
-[\theta\mathbf{u}^{n+1}+(1-\theta)\mathbf{u}^{n}]
\cdot\nabla p
-\gamma p\nabla\cdot
[\theta\mathbf{u}^{n+1}+(1-\theta)\mathbf{u}^{n}].
$$

This is the sense in which the method is semi-implicit: the stiff wave response is stabilized by the implicit operator, while the full nonlinear system is not necessarily solved as one monolithic nonlinear implicit problem.

Non-ideal effects such as viscosity and resistivity can be added by treating them implicitly. Jardin notes that the main practical challenge is not the stability idea itself, but finding efficient solvers and preconditioners for the matrix corresponding to the operator on the left-hand side.

### 5.5 Semi-implicit operator approximations

Section 9.5.6 distinguishes the semi-implicit method from the exact differential-approximation method. Instead of using the exact stiff operator $L$, the semi-implicit method replaces it with a simpler operator that is easier to invert but still strong enough to stabilize the fastest waves.

For the scalar model problem, one may replace:

$$
L(v)=c^2\frac{\partial^2 v}{\partial x^2}
$$

with:

$$
L(v)=a_0^2\frac{\partial^2 v}{\partial x^2},
$$

where $a_0$ is a constant chosen large enough to dominate the physical wave speed. The stability condition becomes, schematically,

$$
4\theta^2 a_0^2 > c^2.
$$

This is useful when the true wave-speed operator has variable coefficients. A constant-coefficient approximation may be much easier to invert, sometimes allowing fast transform or simpler elliptic solvers.

For ideal MHD, Harned and Schnack proposed replacing the full ideal-MHD operator with a simplified stabilizing operator of the form:

$$
L(\mathbf{u})
\approx
\frac{1}{\mu_0}
\left\{
\nabla\times[\nabla\times(\mathbf{u}\times\mathbf{C}_0)]
\right\}
\times\mathbf{C}_0,
$$

where $\mathbf{C}_0$ is a constant vector chosen to bound the components of the magnetic field. Jardin emphasizes an important detail from the stability analysis: in Cartesian form, cross terms of the form $C_iC_j$ are replaced by $C_iC_j\delta_{ij}$. Keeping the cross terms can destabilize the semi-implicit operator.

For two-fluid MHD, Harned and Mikic developed a semi-implicit operator for the Hall term in the magnetic-field equation. The stiff Hall contribution has the schematic form:

$$
\frac{\partial\mathbf{B}}{\partial t}
=
\nabla\times
\left[
-\frac{1}{ne}\mathbf{J}\times\mathbf{B}
+\cdots
\right].
$$

The corresponding semi-implicit Hall stabilizing operator is:

$$
L(\mathbf{B})
=
-\frac{1}{(ne\mu_0)^2}
(\mathbf{B}_0\cdot\nabla)^2
\nabla^2\mathbf{B}.
$$

This operator is designed to stabilize the dispersive Hall/whistler-like dynamics that can otherwise impose severe time-step restrictions.

The practical philosophy is:

```text
Use a simpler implicit operator to stabilize fast waves,
but keep the full physical terms in the explicit or time-centered residual.
```

This makes the method cheaper than a fully implicit exact solve, while still allowing time steps larger than a purely explicit CFL-limited method.

### 5.6 Example: parabolic velocity operator in M3D-C1

Pages 7 and 8 of `3D-Equations (1).pdf` show how this idea appears in the M3D-C1 weak form for the first projection of the momentum equation, the projection associated with the scalar velocity variable $U$.

Recall the velocity representation:

$$
\mathbf{V}
=
R^2\nabla U\times\nabla\varphi
+\omega R^2\nabla\varphi
+R^{-2}\nabla_\perp\chi .
$$

The three scalar velocity variables are therefore:

```text
U       poloidal stream-function-like velocity variable
omega   toroidal velocity variable
chi     compressional/potential-like velocity variable
```

In the weak form, M3D-C1 projects the momentum equation onto finite-element test functions $\nu_i(R,Z)$. The first projection has the schematic form:

$$
I_1
\equiv
\rho R^2(\nu_i,U^{n+1})
-\rho[\nu_i,\chi^{n+1}]
-(\theta\Delta t)^2
\left[
\delta W_{11}(\nu_i,U^{n+1})
+\delta W_{12}(\nu_i,\omega^{n+1})
+\delta W_{13}(\nu_i,\chi^{n+1})
\right]
+\cdots .
$$

The first two terms are mass-like couplings for the velocity representation. The important semi-implicit part is:

$$
-(\theta\Delta t)^2
\left[
\delta W_{11}
+\delta W_{12}
+\delta W_{13}
\right].
$$

This is the M3D-C1 analogue of the stabilizing operator:

$$
1-\theta^2\Delta t^2 L .
$$

Instead of applying a scalar wave operator $L$ to one variable, the M3D-C1 velocity advance applies a block operator to the three scalar velocity variables:

$$
\begin{bmatrix}
\delta W_{11} & \delta W_{12} & \delta W_{13} \\
\delta W_{21} & \delta W_{22} & \delta W_{23} \\
\delta W_{31} & \delta W_{32} & \delta W_{33}
\end{bmatrix}
\begin{bmatrix}
U \\ \omega \\ \chi
\end{bmatrix}.
$$

For the first projection, only the first row appears:

```text
delta W11: response of the U projection to U
delta W12: response of the U projection to omega
delta W13: response of the U projection to chi
```

The notation $\delta W$ reflects its origin in the linearized ideal-MHD force operator or energy-principle-like bilinear form. These terms contain the stabilizing wave physics associated with magnetic tension, field-line bending, pressure/compressibility, and geometric coupling.

The complete equation from page 7 and the full $\delta W_{11}$, $\delta W_{12}$, and $\delta W_{13}$ expressions from page 8 are included below as images from the source PDF to avoid omitting terms during transcription.

![Full first projected momentum equation from page 7 of 3D-Equations (1).pdf](assets/3d_equations_page_7_first_projection.png)

![Full delta W11, delta W12, and delta W13 expressions from page 8 of 3D-Equations (1).pdf](assets/3d_equations_page_8_deltaW_blocks.png)

The page-8 expression is long because it keeps the full toroidal geometry, finite-$F$ terms, pressure terms, and coupling to the 3D magnetic representation. The important structural point is that $\delta W_{11}$ is the $U$-$U$ block of the ideal-MHD stabilizing operator, while $\delta W_{12}$ and $\delta W_{13}$ couple the $U$ projection to toroidal and compressional velocity components.

The same page-7 weak form also includes a viscous parabolic contribution:

$$
\mu\theta\Delta t
\left[
R^2(\nabla_\perp^2\nu_i)(\nabla_\perp^2 U)
-(\nu_i,U'')
\right]^{n+1}.
$$

This term is parabolic in the more familiar diffusion sense: it damps small-scale velocity structure through higher spatial derivatives. In contrast, the $(\theta\Delta t)^2\delta W$ operator is a hyperbolic-wave stabilizer that becomes elliptic/parabolic-like after the semi-implicit time discretization.

So the first projected velocity equation contains three layers:

1. Mass-like terms from the scalar velocity representation.
2. Semi-implicit ideal-MHD wave stabilization through the $\delta W$ blocks.
3. Viscous parabolic damping through $\mu$-dependent terms.

This is the concrete M3D-C1 version of the semi-implicit idea described in Jardin's computational-methods text: fast MHD wave physics is placed into an implicit stabilizing operator, while the nonlinear residual and older-time terms remain on the right-hand side.

### 5.7 Block-Jacobi preconditioning

The toroidal-plane structure of the discretization leads to a matrix with strong in-plane coupling and weaker coupling to neighboring toroidal planes. M3D-C1 exploits this using a block-Jacobi preconditioner, where each toroidal plane or block is approximately inverted as part of the preconditioning operation.

In the Jardin et al. paper, the block solves are performed using sparse direct solvers through PETSc, with examples using packages such as SuperLU_DIST or MUMPS. The preconditioned system is then solved with Krylov methods.

The combined strategy is:

- Split implicit time advance to reduce and improve the matrix.
- Annihilation operators to separate wave-family structure.
- Block-Jacobi preconditioning to reduce the condition number of the large 3D system.
- GMRES or related Krylov methods for the final iterative solve.

This combination allows the code to use time steps much larger than those allowed by an explicit CFL condition while still resolving the physics of interest.

## 6. Kinetic-MHD Extension: M3D-C1-K

### 6.1 Why kinetic energetic particles matter

Energetic particles are central to burning plasma physics. Fusion-born alpha particles, neutral-beam ions, RF-driven ions, and energetic electrons can resonate with global MHD modes and modify their stability. These interactions can drive or damp modes and can also lead to energetic-particle transport or loss.

A fully kinetic treatment of both the thermal plasma and energetic particles is often too expensive for global long-time simulations. A hybrid kinetic-MHD method is a compromise:

- The bulk plasma is evolved with MHD equations.
- Energetic particles are represented kinetically using markers.
- Particle moments are deposited back onto the MHD grid.
- The MHD fields act back on the particles.

This retains essential energetic-particle wave-particle physics while avoiding the cost of a fully kinetic plasma simulation.

### 6.2 M3D-C1-K architecture

Liu et al. introduce M3D-C1-K as a kinetic-MHD extension based on M3D-C1. The base M3D-C1 code evolves the MHD fields with high-order 3D finite elements. The kinetic extension adds a particle module for energetic particles.

The workflow is approximately:

1. M3D-C1 advances the MHD fields.
2. Field information is transferred to the particle module.
3. Energetic-particle markers are pushed through the electromagnetic fields.
4. Particle weights and distribution-function perturbations are updated.
5. Energetic-particle moments are deposited.
6. These moments are coupled back into the MHD equations.

The particle and MHD updates are evolved separately over each MHD time step. Particle pushing can use subcycles between MHD field updates, allowing particle orbits to be resolved more accurately while the MHD step remains large.

### 6.3 Delta-f method

M3D-C1-K uses a delta-f method for energetic particles. Instead of representing the full distribution function entirely through noisy particle markers, the method decomposes the distribution into an equilibrium part and a perturbation:

```text
f = f0 + delta f
```

Particle markers carry weights associated with the perturbation. This reduces numerical noise when the perturbation is small compared with the equilibrium distribution.

The energetic-particle moments are computed from the marker distribution and then coupled into the MHD equations.

### 6.4 Pressure coupling and current coupling

M3D-C1-K includes two related schemes for energetic-particle feedback:

- Pressure coupling.
- Current coupling.

In pressure coupling, energetic-particle pressure moments enter the MHD momentum equation. In current coupling, energetic-particle current contributions are used in the coupling. Liu et al. discuss both schemes and show that they can produce equivalent results in the tested linear energetic-particle-driven mode cases.

For pressure coupling, the particle module first deposits the perturbed energetic-particle pressure moments. Liu et al. write the parallel and perpendicular pressure perturbations as

$$
\delta P_{\parallel}(\mathbf{x})
= \int m v_{\parallel}^{2} w f B^{*} \, dv_{\parallel} d\mu d\theta
\approx \sum_k m v_{\parallel k}^{2} w_k {f_k \over g_k} B^{*} S(\mathbf{x}-\mathbf{x}_k),
$$

and

$$
\delta P_{\perp}(\mathbf{x})
= \int \mu B \left(w + {B_{1\parallel} \over B_0}\right) f B^{*} \, dv_{\parallel} d\mu d\theta
= \sum_k \mu_k B \left(w_k + {B_{1\parallel} \over B_0}\right) {f_k \over g_k} B^{*} S(\mathbf{x}-\mathbf{x}_k).
$$

Here $w_k$ is the marker weight, $S$ is the particle shape/deposition function, $g_k$ is the marker loading distribution, $B^{*}$ is the phase-space Jacobian, and $B_{1\parallel} = \mathbf{b}_0 \cdot \mathbf{B}_1$. In the M3D-C1-K implementation described by Liu et al., markers are initialized using the same distribution function $f_0$, so the explicit $f/g$ factor can often be avoided in the summation.

In the finite-element representation, these deposited moments are obtained weakly by multiplying by a test function $\nu_i$ and integrating over the element volume:

$$
\int \nu_i \delta P_{\parallel} J \, d\mathbf{x}
= \sum_k w_k m v_{\parallel k}^{2}
  \int \nu_i(\mathbf{x}) J(\mathbf{x}) S(\mathbf{x}-\mathbf{x}_k)\, d\mathbf{x},
$$

$$
\int \nu_i \delta P_{\perp} J \, d\mathbf{x}
= \sum_k w_k \mu_k B(\mathbf{x}_k)
  \int \nu_i(\mathbf{x}) J(\mathbf{x}) S(\mathbf{x}-\mathbf{x}_k)\, d\mathbf{x}.
$$

The energetic-particle pressure tensor is then written as

$$
\mathbf{P}_h
= P_{\parallel}\mathbf{b}\mathbf{b}
+ P_{\perp}(\mathbf{I}-\mathbf{b}\mathbf{b}),
$$

and the pressure-coupled total momentum equation is

$$
\rho {\partial \mathbf{V} \over \partial t}
+ \rho(\mathbf{V}\cdot\nabla \mathbf{V})
+ {\partial \mathbf{K}_h \over \partial t}
= \mathbf{J}\times\mathbf{B} - \nabla p - \nabla\cdot\mathbf{P}_h .
$$

For a $\delta f$ simulation, the equilibrium force balance is subtracted:

$$
\mathbf{J}_0 \times \mathbf{B}_0
= \nabla p_0 + \nabla p_{h0}.
$$

Assuming an isotropic energetic-particle equilibrium pressure, the perturbed pressure-coupling equation becomes

$$
\rho {\partial \mathbf{V} \over \partial t}
+ \rho(\mathbf{V}\cdot\nabla \mathbf{V})
+ {\partial \mathbf{K}_h \over \partial t}
= \mathbf{J}_0\times\mathbf{B}_1
+ \mathbf{J}_1\times\mathbf{B}_0
+ \mathbf{J}_1\times\mathbf{B}_1
- \nabla\delta p
- \nabla\cdot\delta\mathbf{P}_h ,
$$

with $\mathbf{J}_1=\nabla\times\mathbf{B}_1$. In words, the perturbed energetic-particle pressure tensor contributes a force density $-\nabla\cdot\delta\mathbf{P}_h$ to the MHD momentum equation. Liu et al. note that the M3D-C1-K pressure-coupling implementation keeps all components of $\nabla\cdot\mathbf{P}_h$ while following the earlier M3D-K approximation of neglecting $\partial\mathbf{K}_h/\partial t$.

The purpose of both schemes is the same: allow kinetic energetic particles to exchange energy and momentum with MHD modes.

### 6.5 GPU acceleration and hybrid parallelism

The base M3D-C1 code uses distributed-memory parallelism with MPI and decomposes the 3D mesh into subdomains. For the kinetic module, Liu et al. adopt a particle-based parallelization strategy:

- Each particle-pushing thread advances one particle for several substeps.
- Field information is made available to GPU kernels.
- Particle pushing and weight calculation are accelerated on GPUs.
- OpenACC is used for accelerator programming.
- OpenMP is used for multicore CPU particle pushing.
- MPI communication remains part of the broader distributed-memory framework.

This model avoids the cost of constantly communicating particles as they move across mesh subdomains during the particle-pushing phase. Instead, the field information is collected and made available to the particle-pushing hardware.

Liu et al. report significant GPU acceleration of the particle-pushing component and argue that M3D-C1-K is suitable for long-time nonlinear MHD simulations involving kinetic energetic-particle effects.

## 7. Example Physics Applications

The reference materials discuss or motivate several classes of simulation:

- Sawtooth cycles in tokamak plasmas.
- Resistive and ideal MHD stability.
- Transport-timescale evolution.
- Non-ideal two-fluid effects.
- Energetic-particle-driven fishbone modes.
- Toroidal Alfvén eigenmodes.
- Reversed-shear Alfvén eigenmodes.

These applications highlight the main purpose of the code family: to connect global MHD dynamics, realistic geometry, long-time evolution, and extended kinetic or non-ideal effects in a numerically tractable way.

## 8. Source Notes

The following source PDFs were used:

1. Nathaniel Mandrachia Ferraro, `Non-Ideal Effects on the Stability and Transport.pdf`.
   - Used for background on non-ideal MHD, two-fluid modeling, unstructured mesh motivation, and M3D-C1 as an implicit finite-element code.

2. S. C. Jardin, N. Ferraro, J. Breslau, and J. Chen, `Jardin et al. - 2012 - Multiple timescale calculations of sawteeth and ot.pdf`.
   - Used for the M3D-C1 overview, multiple-timescale MHD motivation, split implicit method, annihilation operators, block-Jacobi preconditioning, triangular-wedge C1 finite element, sawtooth simulation context, and the embedded triangular-wedge element figure.

3. C. Liu, S. C. Jardin, H. Qin, J. Xiao, N. M. Ferraro, and J. Breslau, `Liu et al. - 2022 - Hybrid simulation of energetic particles interacti.pdf`.
   - Used for M3D-C1-K, energetic-particle hybrid simulation, delta-f method, pressure/current coupling, particle subcycling, and GPU/OpenACC acceleration.

4. S. C. Jardin et al., `3D-Equations (1).pdf`.
   - Used for Chapter 0 definitions of cylindrical coordinates, scalar variables, velocity representation, magnetic vector potential, magnetic field, current density, and the $\Delta^\dagger$ and $\Delta^*$ operators. Also used pages 7-8 for the first projected momentum equation and the $\delta W_{11}$, $\delta W_{12}$, and $\delta W_{13}$ velocity-operator blocks.

5. S. C. Jardin, `Jardin - Computational Methods in Plasma Physics.pdf`.
   - Used for sections 9.5.5 and 9.5.6 on the method of differential approximation, Caramana and split theta-implicit methods, the ideal-MHD stabilizing operator, and semi-implicit operator approximations for ideal MHD and Hall/two-fluid dynamics.

6. N. M. Ferraro et al., `Ferraro et al. - 2016 - Multi-region approach to free-boundary three-dimen.pdf`.
   - Used for the multi-region free-boundary M3D-C1 model, including the plasma-region two-fluid equations, resistive-wall and external-vacuum equations, plasma/vacuum/wall region structure, and the embedded unstructured mesh figure.
