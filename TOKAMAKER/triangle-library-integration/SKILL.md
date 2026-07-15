---
name: triangle-library-integration
description: 记录 Jonathan Shewchuk 的 Triangle 库的项目结构、核心 API 接口、编译选项，以及在不同编程环境 (Python/Fortran/C) 中集成该库的工程决策指南。适用于需要将 Triangle 集成到 C/Fortran 科学计算项目中的场景。
---

# Triangle 库项目结构与工程集成

## 概述

本 Skill 记录了 Triangle 库 (Jonathan Shewchuk) 的项目结构、核心接口调用方法，以及在不同编程环境中集成该库的工程决策指南。

- **GitHub 镜像 (JuliaGeometry) (c 语言版本)**: https://github.com/JuliaGeometry/Triangle
- **原作者官方页面**: http://www.cs.cmu.edu/~quake/triangle.html
- **python 版本包**: https://pypi.org/project/triangle/
---

## 1. 项目基本信息

| 属性 | 信息 |
|------|------|
| **名称** | Triangle: A Two-Dimensional Quality Mesh Generator and Delaunay Triangulator |
| **作者** | Jonathan Richard Shewchuk |
| **版本** | 1.6 (July 28, 2005) |
| **许可证** | 非商业开源 (禁止商业使用，学术/研究免费) |
| **核心语言** | C |
| **代码量** | ~16,000 行 (`triangle.c` + `triangle.h`) |
| **官方页面** | http://www.cs.cmu.edu/~quake/triangle.html |
| **GitHub 镜像** | https://github.com/JuliaGeometry/Triangle (包含针对 Julia 的适配和修改) |

---

## 2. 核心源码文件

| 文件 | 说明 |
|------|------|
| `triangle.c` | 核心算法实现 (~16,000 行 C 代码) |
| `triangle.h` | 头文件，定义 `triangulateio` 结构体和函数原型 |
| `showme.c` | 可视化工具 (Unix/Linux 下显示网格) |
| `tricall.c` | 示例程序，演示如何调用 Triangle 库 |
| `makefile` | 编译配置 (可直接生成可执行文件或库) |

---

## 3. 核心 API 接口

### 3.1 主入口函数

```c
int triangulate(
    char *triswitches,                    /* 控制字符串 */
    struct triangulateio *in,             /* 输入数据结构 */
    struct triangulateio *out,            /* 输出数据结构 */
    struct triangulateio *vorout          /* Voronoi 输出 (可选) */
);
```

### 3.2 控制字符串 (`triswitches`)

| 开关 | 说明 |
|------|------|
| `p` | 读取 PLC (分段线性复合体) |
| `q` | 质量约束 (最小角度) |
| `a` | 面积约束 (最大单元面积) |
| `A` | 分配区域属性 |
| `z` | 从 0 开始编号 (默认从 1 开始) |
| `Q` | 静默模式 (不输出日志) |
| `D` | 输出 Delaunay 三角化 |
| `r` | 重构已有网格 (refinement) |

**OFT 使用的开关**: `"pqaAzQ"`

### 3.3 核心数据结构: `struct triangulateio`

```c
struct triangulateio {
    /* 输入/输出 - 点 */
    REAL *pointlist;          /* 点坐标 [x1,y1, x2,y2, ...] */
    int numberofpoints;
    REAL *pointattributelist; /* 点属性 */
    int *pointmarkerlist;     /* 点标记 */
    int numberofpointattributes;
    
    /* 输入/输出 - 三角形 */
    int *trianglelist;        /* 三角形单元 [idx1,idx2,idx3, ...] */
    int numberoftriangles;
    int numberofcorners;      /* 固定为 3 */
    REAL *triangleattributelist; /* 三角形属性 (区域标记) */
    REAL *trianglearealist;   /* 三角形面积约束 (输入) */
    int numberoftriangleattributes;
    int *neighborlist;        /* 相邻三角形 (输出) */
    
    /* 输入/输出 - 边界段 */
    int *segmentlist;         /* 边界段 [idx1,idx2, ...] */
    int *segmentmarkerlist;   /* 段标记 */
    int numberofsegments;
    
    /* 输入 - 孔洞 */
    REAL *holelist;           /* 孔洞点 [x1,y1, x2,y2, ...] */
    int numberofholes;
    
    /* 输入 - 区域 */
    REAL *regionlist;         /* 区域标记点 [x,y,id,max_area, ...] */
    int numberofregions;
    
    /* 输出 - 边 */
    int *edgelist;            /* 边列表 */
    int *edgemarkerlist;
    int numberofedges;
    
    /* Voronoi 输出 */
    REAL *normlist;           /* 法向量 */
};
```

---

## 4. 编译选项

### 4.1 关键宏定义

| 宏 | 说明 |
|----|------|
| `TRILIBRARY` | **必须定义**，将 Triangle 编译为库而非可执行程序 |
| `ANSI_DECLARATORS` | 使用 ANSI C 函数声明 |
| `NO_TIMER` | 禁用计时器 (避免依赖系统时间函数) |
| `REAL=double` | 定义浮点精度 (可选 `float`) |
| `VOID=void` | 定义返回类型 |

### 4.2 编译命令示例

**编译为静态库**:
```bash
gcc -c -DTRILIBRARY -DANSI_DECLARATORS -DNO_TIMER -DREAL=double -DVOID=void triangle.c
ar rcs libtriangle.a triangle.o
```

**编译为共享库**:
```bash
gcc -shared -fPIC -DTRILIBRARY -DANSI_DECLARATORS -DNO_TIMER -DREAL=double -DVOID=void triangle.c -o libtriangle.so
```

**作为独立可执行程序**:
```bash
gcc -O -o triangle triangle.c -lm
```

---

## 5. 多语言集成指南

### 5.1 Python (ctypes)

```python
import ctypes
import numpy as np

# 1. 定义结构体
class TriangulateIO(ctypes.Structure):
    _fields_ = [
        ("pointlist", ctypes.POINTER(ctypes.c_double)),
        ("numberofpoints", ctypes.c_int),
        # ... 其他字段
    ]

# 2. 加载库
lib = ctypes.CDLL("libtriangle.so")
lib.triangulate.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(TriangulateIO),
    ctypes.POINTER(TriangulateIO),
    ctypes.POINTER(TriangulateIO),
]

# 3. 准备数据并调用
in_io = TriangulateIO()
in_io.numberofpoints = n_pts
in_io.pointlist = points.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
# ...
lib.triangulate(b"pqaAzQ", ctypes.byref(in_io), ctypes.byref(out_io), None)
```

### 5.2 Fortran (ISO_C_BINDING)

```fortran
module triangle_interface
    use iso_c_binding
    implicit none
    
    ! 定义 triangulateio 结构体
    type, bind(C) :: triangulateio
        type(c_ptr) :: pointlist
        integer(c_int) :: numberofpoints
        ! ... 其他字段
    end type triangulateio
    
    interface
        function triangulate(switches, in_io, out_io, vorout_io) &
            bind(C, name="triangulate")
            import :: c_char, c_int, c_ptr
            character(c_char), intent(in) :: switches(*)
            type(c_ptr), value :: in_io, out_io, vorout_io
            integer(c_int) :: triangulate
        end function triangulate
    end interface
    
contains
    
    subroutine generate_mesh()
        ! 分配内存 (Fortran 侧)
        real(c_double), target, allocatable :: points(:)
        integer(c_int), target, allocatable :: segments(:)
        type(triangulateio), target :: in_io, out_io
        
        ! 设置指针
        in_io%pointlist = c_loc(points)
        in_io%numberofpoints = size(points) / 2
        
        ! 调用 Triangle
        ierr = triangulate("pqaAzQ" // c_null_char, &
                           c_loc(in_io), c_loc(out_io), c_null_ptr)
    end subroutine generate_mesh
    
end module triangle_interface
```

---

## 6. Python 版本 vs C 版本工程取舍

Triangle 库的官方实现是 C 语言，但开源社区也提供了 Python 封装包 (pip install triangle)。在将 Triangle 集成到新的科学计算项目时，面临选择采用哪个版本的问题，以下对比表可供参考。

### 6.1 对比表

| 评估维度 | Python Triangle | C Triangle (直接集成) |
|---------|----------------|----------------------|
| 开发速度 | 快速原型 | 需要手写 C/Fortran 接口 |
| 内存管理 | 跨语言边界，需要拷贝 | 零拷贝，直接传递指针 |
| 性能 | Python 调用开销 + GIL | 原生性能 |
| 部署 | 依赖 Python 环境 | 自包含，无外部依赖 |
| 调试 | 跨语言栈回溯复杂 | 单一语言调试 |
| 代码复用 | 仅限 Python 项目 | 可移植到任意 C/Fortran 项目 |

### 6.2 决策建议

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 纯 Python 项目 | Python `triangle` 包 | 开发效率最高 |
| Fortran/C 混合编译项目 | C Triangle 直接集成 | 无跨语言内存管理开销 |
| 前期快速验证 | Python `triangle` 包 | 快速迭代验证几何定义 |
| 生产环境/长期维护 | C Triangle 直接集成 | 自包含、高性能、易调试 |
| 网格生成与计算解耦 | 任选 (用文件交换) | 网格数据通过文件静态交换 |

### 6.3 针对 Fortran/C 混合程序的建议

对于 **Fortran + C** 混合编译的科学计算程序 (如 M3DC1):

**推荐: 直接集成 C 源码编译的 Triangle 库**

```fortran
! 在 Fortran 中直接调用 Triangle
ierr = triangulate("pqaAzQ" // c_null_char, c_loc(in), c_loc(out), c_null_ptr)
```

**理由**:
1. 零拷贝数据传递，性能最优
2. 无外部依赖，部署简单
3. 可以直接复用 OFT 中已验证的集成方案
4. 网格生成和物理计算在同一进程中完成，无需文件 I/O 中介

---

## 7. 相关资源

| 资源 | 链接 |
|------|------|
| Triangle 官方页面 | http://www.cs.cmu.edu/~quake/triangle.html |
| Triangle 研究论文 | http://www.cs.cmu.edu/~quake/triangle.research.html |
| **Triangle GitHub 镜像 (JuliaGeometry)** | **https://github.com/JuliaGeometry/Triangle** (包含针对 Julia 的适配和修改) |
| OFT 源码 (参考实现) | https://github.com/OpenFUSIONToolkit/OpenFUSIONToolkit |
| Triangle Python 包 | https://pypi.org/project/triangle/ |
| Triangle.NET | https://github.com/wo80/Triangle.NET |
