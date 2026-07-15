---
name: oft-meshing-architecture
description: 记录 OpenFUSION Toolkit (OFT) 中三角形网格生成模块的完整调用链路，从顶层 Python 用户接口 (gs_Domain) 到底层 C 语言 Triangle 库 (triangulate 函数)。适用于需要理解、移植或扩展 OFT 网格生成功能的场景。
---

# OFT 网格生成模块 (meshing.py) 架构链路

## 概述

本 Skill 记录了 OpenFUSION Toolkit (OFT) 中三角形网格生成模块的完整调用链路，展示了科学计算软件中 Python + Fortran + C 混合编程的典型架构。

- **OFT GitHub 仓库**: https://github.com/OpenFUSIONToolkit/OpenFUSIONToolkit
- **本模块 Python 源码路径**: `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`
- **Triangle C 源码路径**: `src/ext_libs/triangle.c`

---

## 1. 完整调用链路图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Python 用户层 (meshing.py)                                                │
│  gs_Domain.build_mesh()                                                    │
│    - 管理几何区域 (plasma/vacuum/boundary/conductor/coil)                 │
│    - 调用 Mesh 类生成网格                                                  │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Python 中间层 (meshing.py)                                                │
│  Mesh 类 (全局拓扑处理)                                                    │
│    - 点合并 (merge_thresh)                                                │
│    - 边界段合并/拆分 (共享边界处理)                                        │
│    - 边界重采样 (dx_curve 分辨率控制)                                      │
│    - 区域标记点生成 (Triangle regionlist)                                  │
│    - 构造输入字典: {vertices, segments, regions}                          │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Python 封装层 (meshing.py)                                                │
│  run_triangle(alpha)                                                       │
│    - 将 Python dict 转换为 triangle_struct (C 风格结构体)                 │
│    - 调用 oft_triangulate (ctypes 包装)                                   │
│    - 将输出转为 numpy 数组返回                                             │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Python ctypes 接口层 (_interface.py)                                      │
│  路径: src/python/OpenFUSIONToolkit/TokaMaker/_interface.py               │
│  oft_triangle_lib = ctypes.CDLL("liboft_triangle.so")                     │
│  oft_triangulate = ctypes_subroutine(oft_triangle_lib.triangulate, ...)   │
│    - 定义参数类型: c_char_p, POINTER(triangle_struct) ...                 │
│    - 从动态库加载 triangulate 符号                                        │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  共享库层 (编译后生成)                                                     │
│  路径: build_release/bin/liboft_triangle.dylib / .so / .dll               │
│  导出的符号 (通过 nm 验证):                                                │
│    _triangulate           ← Python 调用的目标                              │
│    _intern_triangulate    ← 内部实现                                      │
│    _triangulatepolygon    ← 多边形 Delaunay 递归实现                       │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  C 源码层 (src/ext_libs/triangle.c)                                       │
│  int triangulate(char *switches, triangulateio *in,                       │
│                  triangulateio *out, triangulateio *vorout)               │
│    - 第 14903 行: 主入口函数                                              │
│    - 调用 intern_triangulate (第 14578 行)                                │
│    - 内部实现: Delaunay 三角化 + 质量优化                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 各层职责详解

### 2.1 用户层: `gs_Domain` 类

**文件**: `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`

**职责**:
- 用户接口，定义几何区域的类型和属性
- 管理区域信息: `define_region()`, `add_polygon()`, `add_annulus()`, `add_rectangle()`
- 调度网格生成: `build_mesh()` 方法

**关键数据**:
```python
self.region_info = {
    "plasma": {"id": 1, "dx": 0.01, "type": "plasma", ...},
    "vacuum": {"id": 2, "dx": 0.02, "type": "vacuum", ...},
}
self.regions = [Region(...), Region(...)]  # 几何轮廓列表
```

### 2.2 中间层: `Mesh` 类

**文件**: `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`

**职责**: 全局拓扑处理，将多个 Region 组装成 Triangle 的输入格式

**关键步骤**:

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1. 点合并 | `__init__` | 合并距离 < `merge_thresh` 的相邻区域边界点 |
| 2. 边界段合并 | `__init__` | 合并/拆分共享边界，保持拓扑一致性 |
| 3. 边界重采样 | `__init__` | 按 `dx_curve` 均匀插入新点 |
| 4. 区域标记点生成 | `__init__` | 为每个区域生成内部标记点 (Triangle regionlist) |
| 5. 调用 Triangle | `get_mesh()` | 构造字典并调用 `run_triangle()` |

**关键数据结构**:
```python
alpha = {
    "vertices": self._resampled_points,  # [N, 2] 边界点
    "segments": resampled_flat,          # [M, 2] 边界线段
    "regions": self._reg_defs,           # [K, 4] [R, Z, region_id, max_area]
}
```

### 2.3 封装层: `run_triangle()` 函数

**文件**: `src/python/OpenFUSIONToolkit/TokaMaker/meshing.py`

**职责**: 将 Python 数据转换为 C 结构体，调用底层库

**关键流程**:
1. 创建 `triangle_struct` 实例 (对应 C 的 `struct triangulateio`)
2. 将 NumPy 数组转换为 `ctypes` 指针
3. 调用 `oft_triangulate` (由 `ctypes` 包装)
4. 从输出结构体中提取网格数据

### 2.4 接口层: `_interface.py`

**文件**: `src/python/OpenFUSIONToolkit/TokaMaker/_interface.py`

**职责**: 加载编译好的共享库，定义 `ctypes` 调用接口

**关键代码**:
```python
# 定位库文件
root_path = os.path.realpath(os.path.dirname(__file__))
oft_triangle_lib = ctypes.CDLL(
    os.path.join(root_path, "..", "..", "..", "bin", "liboft_triangle" + lib_suffix)
)

# 定义调用签名
oft_triangulate = ctypes_subroutine(
    oft_triangle_lib.triangulate,
    [c_char_p, POINTER(triangle_struct), POINTER(triangle_struct), POINTER(triangle_struct)],
    c_int,
)
```

### 2.5 共享库层: `liboft_triangle`

**文件**: `build_release/bin/liboft_triangle.dylib` (macOS) / `.so` (Linux) （注意：build_release 目录是在源码编译后才有的）

**构建来源**: `src/ext_libs/CMakeLists.txt`

### 2.6 C 源码层: `triangle.c`

**文件**: `src/ext_libs/triangle.c`

**来源**: Jonathan Shewchuk 的 Triangle 库 (Version 1.6, July 28, 2005)

**核心函数入口**:
```c
// 第 14903 行
int triangulate(char *triswitches, struct triangulateio *in,
                struct triangulateio *out, struct triangulateio *vorout)
{
    intern_triangulate(triswitches, in, out, vorout);
    return 0;
}
```

---

## 3. 关键数据结构

### Python 侧: `triangle_struct`

```python
class triangle_struct(c_struct):
    _fields_ = [
        ("pointlist", c_double_ptr),
        ("numberofpoints", c_int),
        ("trianglelist", c_int_ptr),
        ("numberoftriangles", c_int),
        ("segmentlist", c_int_ptr),
        ("numberofsegments", c_int),
        ("regionlist", c_double_ptr),
        ("numberofregions", c_int),
        # ... 完整定义见 meshing.py
    ]
```

### C 侧: `struct triangulateio`

```c
struct triangulateio {
    REAL *pointlist;          /* 点坐标 [x1,y1, x2,y2, ...] */
    int numberofpoints;
    int *trianglelist;        /* 三角形单元 [idx1,idx2,idx3, ...] */
    int numberoftriangles;
    int *segmentlist;         /* 边界段 [idx1,idx2, ...] */
    int numberofsegments;
    REAL *regionlist;         /* 区域标记点 [x,y,id,max_area, ...] */
    int numberofregions;
    /* ... 完整定义见 triangle.h */
};
```

---

## 4. 依赖关系与构建

### 源码结构

```
OpenFUSIONToolkit/
├── src/
│   ├── ext_libs/
│   │   ├── CMakeLists.txt    ← 构建配置
│   │   └── triangle.c        ← Triangle 核心源码
│   └── python/
│       └── OpenFUSIONToolkit/
│           └── TokaMaker/
│               ├── _interface.py     ← ctypes 接口
│               └── meshing.py        ← Python 网格生成模块 (本 Skill 分析目标)
├── build_release/                     ← 编译输出目录
│   └── bin/
│       └── liboft_triangle.*          ← 编译后的共享库
└── ...
```

### CMake 构建配置

```cmake
# src/ext_libs/CMakeLists.txt
add_library(oft_triangle SHARED triangle.c)
target_compile_definitions(oft_triangle PRIVATE 
    -DTRILIBRARY 
    -DANSI_DECLARATORS 
    -DNO_TIMER 
    -DREAL=double 
    -DVOID=void
)
```

---

## 5. 总结

OFT 的网格生成模块展示了科学计算软件中分层架构的典型设计:

| 层级 | 语言 | 职责 |
|------|------|------|
| 用户接口 | Python | 区域管理、几何定义 |
| 拓扑处理 | Python | 点合并、边界处理、分辨率控制 |
| 封装层 | Python + ctypes | 数据转换、库调用 |
| 接口层 | Python + ctypes | 动态库加载 |
| 算法层 | C | Delaunay 三角化 + 质量优化 |
