# LinkMesh 初版 Linux 可移动 Release

本目录保存 Release 构建源码。构建脚本由 Windows Git 仓库维护，但只能在 Linux
服务器执行。生成的 Release 是可移动目录和同名 `tar.gz`，不是单文件程序。

## 交付内容

Release 自带：

- LinkMesh Python 包；
- OpenFUSIONToolkit 26.6 完整 Python 包、dist-info 和其配套原生库；
- 已编译并验证的 `linkmesh-scorec-helper`；
- launcher、Python bootstrap 和分层环境检查器；
- README、构建信息、依赖信息和普通文件 SHA-256。

Release 不自带：

- Python 解释器；
- NumPy、h5py、Matplotlib、SciPy、netCDF4 或 pytest；
- MPI、glibc 或 libstdc++；
- 独立 PUMI `.a` 或 `.so`；
- tests、examples、TOKAMAKER 或 M3DC1 参考源码。

PUMI 2.2.9 的 mds、apf、gmi、pcu、mth 和 lion 已静态链接到 helper。helper
仍动态需要相容的 `libmpi.so.40` 和系统 C/C++ 运行库。TRIMEG HDF5 路径不调用
helper，不应因 MPI 不可用而被阻塞。

## 两阶段构建流程

### 1. Windows 本地仓库

本地负责 Git、源码修改、构建脚本和发布版本。先提交本轮源码，再创建源码归档：

```bash
git commit
git archive --format=tar.gz --output=linkmesh-source-<version>.tar.gz HEAD
sha256sum linkmesh-source-<version>.tar.gz
scp linkmesh-source-<version>.tar.gz <server>:<upload-directory>/
```

Linux 服务器不执行 `git clone`、`git pull` 或其他 LinkMesh 源码 Git 工作流。

### 2. Linux 服务器

把源码归档展开到全新的临时目录。在该目录中调用构建器，并明确提供服务器 Python、
已经编译验证的 helper 以及源码追踪信息：

```bash
tar -xzf linkmesh-source-<version>.tar.gz -C <fresh-source-directory>
bash <fresh-source-directory>/packaging/release/build_release.sh --output <release-output-directory> --version <version> --python <python-path> --helper <helper-path> --source-commit <commit-hash> --source-archive linkmesh-source-<version>.tar.gz --source-archive-sha256 <archive-sha256>
```

构建器：

- 不调用 Git；
- 不联网；
- 不运行 pip；
- 不安装或修改 Conda 环境；
- 严格要求所选 Python 的 OpenFUSIONToolkit 版本为 26.6；
- 验证 helper 为可执行 Linux x86-64 ELF；
- 在 `ldd` 出现 `not found` 时失败；
- 不覆盖已有 Release 目录或 tar.gz。

成功后得到：

```text
linkmesh-release-<version>-linux-x86_64/
linkmesh-release-<version>-linux-x86_64.tar.gz
```

随后在 Linux 服务器运行分层检查、自动测试和真实案例，并保存完整命令、日志、
环境、产物及消费端结果。将 tar.gz 和验证记录下载归档。构建成功本身不表示 OFT、
TRIMEG、M3D-C1、MPI 或物理结果已经通过。

## 最终用户使用

最终用户不需要进入维护者个人目录，不设置 `PYTHONPATH`，不设置
`LINKMESH_SCOREC_HELPER`，不安装 OFT，不编译 helper，也不安装 PUMI。

```bash
tar -xzf linkmesh-release-<version>-linux-x86_64.tar.gz
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check core
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh -h
```

默认依次查找 `python3`、`python`。需要选择特定 Python 时，仅为当前命令设置：

```bash
LINKMESH_PYTHON=/path/to/python ./linkmesh-release-<version>-linux-x86_64/bin/linkmesh -h
```

该 Python 环境负责提供任务所需的通用包：

- 所有模式：NumPy；
- TRIMEG HDF5：h5py；
- PNG：Matplotlib；
- SciPy 和 netCDF4：当前仅作 OFT 相关非阻塞诊断，是否为具体任务必需以真实调用证据
  为准。

## 分层环境检查

```bash
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check core
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check trimeg
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check plot
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check m3dc1
./linkmesh-release-<version>-linux-x86_64/bin/linkmesh-check all
```

- `core`：Python、Release LinkMesh、Release OFT 26.6、NumPy；
- `trimeg`：core 和 h5py，不检查 helper/MPI；
- `plot`：core 和 Matplotlib headless import；
- `m3dc1`：core、helper、动态库解析和实际 `libmpi` 路径；
- `all`：依次运行全部模式。

输出状态包括 `OK`、`MISSING`、`WARNING` 和 `NOT CHECKED`。检查器只验证环境边界，
不能替代真实 GFile/OFT、TRIMEG、M3D-C1 加载、初始化、时间推进或物理验收。

## 运行时定位

`bin/linkmesh` 通过自身真实路径定位 Release 根目录，为当前子进程设置 Release 内
helper 路径，然后调用 `linkmesh-bootstrap.py`。bootstrap 把 Release
`python/site-packages` 放到当前 Python 进程 `sys.path` 首位，再启动
`linkmesh.__main__`。

launcher 不设置 `PYTHONPATH`，不设置全局 `LD_LIBRARY_PATH`，不修改 shell 配置或
Case 文件，也不在普通启动阶段强制检查 MPI。参数、信号和退出码由 `exec` 原样传递。
