"""
tests/test_cli.py —— LinkMesh CLI 分区域网格密度参数（v1.13）验收测试。

测试状态：AUTHORED_NOT_RUN
整体状态：PENDING_MANUAL_REVIEW

本文件所有测试均未执行，不能据此宣布 CLI 分区域密度参数验收通过。最终真实
回归与端到端验收在 Linux 服务器执行。

测试原则（v1.13 第 14.1.1 节）：
    - 只针对 CLI 编排（linkmesh.cli）：参数解析、有限正数验证、关键字转发与
      既有 CLI 组合行为；
    - 通过 monkeypatch 隔离 Reader / OFT Adapter / HDF5 Writer / SMB Writer /
      Plotter，绝不调用真实 OFT、Triangle、h5py、MATLAB 或 matplotlib；
    - 不读取真实 GFile，不写真实网格文件，不依赖本地 OFT 动态库；
    - 通过公开的 build_parser() 与当前实际 CLI 编排入口 _run() 验证行为，
      不测试 _run() 的内部实现细节；
    - mock 目标由 cli.py 的实时延迟导入位置决定（各函数在其源模块被 patch）。

被隔离的源模块（cli.py 内延迟导入位置）：
    linkmesh.readers.gfile_reader.read_gfile
    linkmesh.mesher.oft_adapter.generate_mesh
    linkmesh.writers.hdf5_writer.write_hdf5
    linkmesh.writers.smb_writer.write_smb
    linkmesh.utils.plotter.plot_mesh
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from linkmesh import cli


# --------------------------------------------------------------------------- #
# 测试辅助                                                                      #
# --------------------------------------------------------------------------- #

def _parse(argv):
    """用 build_parser() 解析给定 argv（不含程序名），返回 Namespace。"""
    parser = cli.build_parser()
    return parser.parse_args(argv)


def _fake_gfile_data():
    """构造一个受控假 GFileData（仅提供 CLI verbose 分支访问的字段）。"""
    return SimpleNamespace(
        lcfs_r=[0.0, 1.0, 0.5],
        lcfs_z=[0.0, 0.0, 1.0],
        rmaxis=0.5,
        zmaxis=0.5,
        wall_r=None,
        wall_z=None,
    )


def _fake_mesh():
    """构造一个受控假 Mesh2D（仅提供 CLI 打印访问的统计属性）。"""
    return SimpleNamespace(n_nodes=972, n_triangles=1872)


def _install_cli_mocks(monkeypatch, gfile_data=None, mesh=None):
    """在 cli.py 延迟导入的源模块上安装隔离 mock，返回 mock 句柄字典。

    严格按照 cli.py 内部 `from <module> import <name>` 的源模块路径 patch，
    使被 patch 的对象在延迟导入时被取用。
    """
    if gfile_data is None:
        gfile_data = _fake_gfile_data()
    if mesh is None:
        mesh = _fake_mesh()

    m_read = MagicMock(return_value=gfile_data)
    m_generate = MagicMock(return_value=mesh)
    m_write_hdf5 = MagicMock(return_value=None)
    m_write_smb = MagicMock(return_value=None)
    m_plot = MagicMock(return_value=None)

    monkeypatch.setattr(
        "linkmesh.readers.gfile_reader.read_gfile", m_read, raising=True
    )
    monkeypatch.setattr(
        "linkmesh.mesher.oft_adapter.generate_mesh", m_generate, raising=True
    )
    monkeypatch.setattr(
        "linkmesh.writers.hdf5_writer.write_hdf5", m_write_hdf5, raising=True
    )
    monkeypatch.setattr(
        "linkmesh.writers.smb_writer.write_smb", m_write_smb, raising=True
    )
    monkeypatch.setattr(
        "linkmesh.utils.plotter.plot_mesh", m_plot, raising=True
    )

    return {
        "gfile_data": gfile_data,
        "mesh": mesh,
        "read_gfile": m_read,
        "generate_mesh": m_generate,
        "write_hdf5": m_write_hdf5,
        "write_smb": m_write_smb,
        "plot_mesh": m_plot,
    }


# ==========================================================================
# A. Parser 测试
# ==========================================================================

class TestParserDefaults:
    """默认值与解析行为。"""

    def test_default_scale_values(self):
        args = _parse(["--gfile", "dummy.eqdsk"])
        assert args.plasma_dx == 0.08
        assert args.vacuum_dx == 0.10
        assert args.outer_dx == 0.15

    def test_explicit_scale_values(self):
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "0.12",
            "--vacuum-dx", "0.16",
            "--outer-dx", "0.24",
        ])
        assert args.plasma_dx == 0.12
        assert args.vacuum_dx == 0.16
        assert args.outer_dx == 0.24

    def test_scientific_and_decimal_values_parse(self):
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "5e-2",
            "--vacuum-dx", "0.075",
            "--outer-dx", "1.5e-1",
        ])
        assert args.plasma_dx == pytest.approx(0.05)
        assert args.vacuum_dx == pytest.approx(0.075)
        assert args.outer_dx == pytest.approx(0.15)

    @pytest.mark.parametrize("flag", ["--plasma-dx", "--vacuum-dx", "--outer-dx"])
    def test_non_numeric_text_rejected_by_argparse(self, flag):
        with pytest.raises(SystemExit):
            _parse(["--gfile", "dummy.eqdsk", flag, "abc"])

    def test_defaults_do_not_affect_other_params(self):
        # 新参数不改变其他参数默认值
        args = _parse(["--gfile", "dummy.eqdsk"])
        assert args.output == "mesh.h5"
        assert args.smb == "mesh.smb"
        assert args.plot is None
        assert args.min_angle == 20.0
        assert args.max_area is None
        assert args.no_smb is False
        assert args.no_hdf5 is False
        assert args.verbose is False


class TestParserHelp:
    """--help 中出现三个参数、区域含义与单位。"""

    def test_help_contains_scale_params(self, capsys):
        with pytest.raises(SystemExit):
            _parse(["--help"])
        out = capsys.readouterr().out
        assert "--plasma-dx" in out
        assert "--vacuum-dx" in out
        assert "--outer-dx" in out

    def test_help_contains_regions_and_unit(self, capsys):
        with pytest.raises(SystemExit):
            _parse(["--help"])
        out = capsys.readouterr().out
        # 区域含义
        assert "plasma-region" in out
        assert "vacuum-region" in out
        assert "outer-region" in out
        # 单位（meters / m）
        assert "meters" in out


# ==========================================================================
# B. 验证失败测试（有限正数）
# ==========================================================================

# 每个非法值都必须在调用 generate_mesh() 之前失败。
_INVALID_VALUES = ["0", "-0.1", "nan", "inf", "-inf"]
_SCALE_FLAGS = [
    ("--plasma-dx", "--plasma-dx"),
    ("--vacuum-dx", "--vacuum-dx"),
    ("--outer-dx", "--outer-dx"),
]


class TestValidationFailures:
    """0 / 负数 / nan / inf / -inf 必须被拒绝，且在 OFT 调用前失败。"""

    @pytest.mark.parametrize("flag,expected_name", _SCALE_FLAGS)
    @pytest.mark.parametrize("bad_value", _INVALID_VALUES)
    def test_invalid_value_rejected_before_oft(
        self, monkeypatch, flag, expected_name, bad_value
    ):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse(["--gfile", "dummy.eqdsk", flag, bad_value])

        with pytest.raises(ValueError) as excinfo:
            cli._run(args)

        msg = str(excinfo.value)
        # 错误文本包含对应参数名与稳定短语
        assert expected_name in msg
        assert "必须是有限正数" in msg

        # 核心要求：generate_mesh() 未被调用（未进入 OFT 网格生成）
        assert mocks["generate_mesh"].call_count == 0
        # Writer / Plotter 亦未被调用
        assert mocks["write_hdf5"].call_count == 0
        assert mocks["write_smb"].call_count == 0
        assert mocks["plot_mesh"].call_count == 0

    def test_valid_values_do_not_raise_validation(self, monkeypatch):
        # 合法值不应触发验证错误，generate_mesh 正常被调用
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "0.05",
            "--vacuum-dx", "0.08",
            "--outer-dx", "0.16",
            "--no-hdf5", "--no-smb",
        ])
        cli._run(args)
        assert mocks["generate_mesh"].call_count == 1


# ==========================================================================
# C. 转发测试
# ==========================================================================

class TestForwarding:
    """三个 dx 值原样按关键字转发给 generate_mesh()，不换算、不改序。"""

    def test_default_values_forwarded(self, monkeypatch):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse(["--gfile", "dummy.eqdsk", "--no-hdf5", "--no-smb"])
        cli._run(args)

        assert mocks["generate_mesh"].call_count == 1
        _, kwargs = mocks["generate_mesh"].call_args
        assert kwargs["plasma_dx"] == 0.08
        assert kwargs["vacuum_dx"] == 0.10
        assert kwargs["outer_dx"] == 0.15

    def test_explicit_values_forwarded_without_conversion(self, monkeypatch):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "0.12",
            "--vacuum-dx", "0.16",
            "--outer-dx", "0.24",
            "--no-hdf5", "--no-smb",
        ])
        cli._run(args)

        _, kwargs = mocks["generate_mesh"].call_args
        assert kwargs["plasma_dx"] == 0.12
        assert kwargs["vacuum_dx"] == 0.16
        assert kwargs["outer_dx"] == 0.24

    def test_generate_mesh_receives_same_gfile_data_object(self, monkeypatch):
        gfile_data = _fake_gfile_data()
        mocks = _install_cli_mocks(monkeypatch, gfile_data=gfile_data)
        args = _parse(["--gfile", "dummy.eqdsk", "--no-hdf5", "--no-smb"])
        cli._run(args)

        posargs, _ = mocks["generate_mesh"].call_args
        # Reader 返回的同一个对象作为第一个位置参数传入
        assert posargs[0] is gfile_data

    def test_generate_mesh_called_once(self, monkeypatch):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse(["--gfile", "dummy.eqdsk", "--no-hdf5", "--no-smb"])
        cli._run(args)
        assert mocks["generate_mesh"].call_count == 1

    def test_scale_params_not_passed_to_reader(self, monkeypatch):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "0.12",
            "--no-hdf5", "--no-smb",
        ])
        cli._run(args)

        # read_gfile 只接收文件路径，不含任何 dx 关键字
        posargs, kwargs = mocks["read_gfile"].call_args
        assert "plasma_dx" not in kwargs
        assert "vacuum_dx" not in kwargs
        assert "outer_dx" not in kwargs
        assert 0.12 not in list(posargs)

    def test_scale_params_not_passed_to_writers_or_plotter(self, monkeypatch, tmp_path):
        plot_path = str(tmp_path / "check.png")
        out_path = str(tmp_path / "mesh.h5")
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--output", out_path,
            "--plasma-dx", "0.12",
            "--vacuum-dx", "0.16",
            "--outer-dx", "0.24",
            "--no-smb",
            "--plot", plot_path,
        ])
        cli._run(args)

        for handle in ("write_hdf5", "plot_mesh"):
            for call in mocks[handle].call_args_list:
                _, kwargs = call
                assert "plasma_dx" not in kwargs
                assert "vacuum_dx" not in kwargs
                assert "outer_dx" not in kwargs

    def test_same_mesh_forwarded_to_writer_and_plotter(self, monkeypatch, tmp_path):
        mesh = _fake_mesh()
        plot_path = str(tmp_path / "check.png")
        out_path = str(tmp_path / "mesh.h5")
        mocks = _install_cli_mocks(monkeypatch, mesh=mesh)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--output", out_path,
            "--no-smb",
            "--plot", plot_path,
        ])
        cli._run(args)

        # HDF5 Writer 收到同一个 Mesh2D mock 对象（第一个位置参数）
        w_posargs, _ = mocks["write_hdf5"].call_args
        assert w_posargs[0] is mesh
        # Plotter 也收到同一个 Mesh2D mock 对象（plot_mesh(gfile, mesh, path,...)）
        p_posargs, _ = mocks["plot_mesh"].call_args
        assert p_posargs[1] is mesh


# ==========================================================================
# D. 组合测试
# ==========================================================================

class TestCombinations:
    """密度参数与既有开关组合，保持既有 CLI 行为。"""

    def test_combo_no_hdf5_no_smb_with_plot(self, monkeypatch, tmp_path):
        plot_path = str(tmp_path / "check.png")
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--plasma-dx", "0.12",
            "--vacuum-dx", "0.16",
            "--outer-dx", "0.24",
            "--no-hdf5", "--no-smb",
            "--plot", plot_path,
        ])
        cli._run(args)

        # 密度参数被转发
        _, kwargs = mocks["generate_mesh"].call_args
        assert kwargs["plasma_dx"] == 0.12
        assert kwargs["vacuum_dx"] == 0.16
        assert kwargs["outer_dx"] == 0.24
        # Plotter 调用，两个 Writer 跳过
        assert mocks["plot_mesh"].call_count == 1
        assert mocks["write_hdf5"].call_count == 0
        assert mocks["write_smb"].call_count == 0

    def test_combo_output_no_smb_with_plot(self, monkeypatch, tmp_path):
        plot_path = str(tmp_path / "check.png")
        out_path = str(tmp_path / "out.h5")
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--output", out_path,
            "--plasma-dx", "0.05",
            "--vacuum-dx", "0.08",
            "--outer-dx", "0.16",
            "--no-smb",
            "--plot", plot_path,
        ])
        cli._run(args)

        # HDF5 Writer 与 Plotter 被调用，SMB Writer 跳过
        assert mocks["write_hdf5"].call_count == 1
        assert mocks["plot_mesh"].call_count == 1
        assert mocks["write_smb"].call_count == 0
        # HDF5 输出路径为用户指定
        w_posargs, _ = mocks["write_hdf5"].call_args
        assert out_path in list(w_posargs)

    def test_default_flow_unchanged_when_new_params_absent(self, monkeypatch, tmp_path):
        # 不提供新参数时，既有默认 CLI 流程不变：转发默认 dx，且默认写 HDF5 + SMB
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse(["--gfile", "dummy.eqdsk"])
        cli._run(args)

        _, kwargs = mocks["generate_mesh"].call_args
        assert kwargs["plasma_dx"] == 0.08
        assert kwargs["vacuum_dx"] == 0.10
        assert kwargs["outer_dx"] == 0.15
        # 默认不加 --no-hdf5 / --no-smb：两个 Writer 均被调用
        assert mocks["write_hdf5"].call_count == 1
        assert mocks["write_smb"].call_count == 1
        # 未指定 --plot：Plotter 不调用
        assert mocks["plot_mesh"].call_count == 0

    def test_legacy_min_angle_rejection_still_applies(self, monkeypatch):
        # 历史参数拦截行为不受本次改动影响
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--min-angle", "25.0",
            "--no-hdf5", "--no-smb",
        ])
        with pytest.raises(ValueError) as excinfo:
            cli._run(args)
        assert "--min-angle" in str(excinfo.value)
        # 历史参数在前置拦截阶段失败，未进入 OFT 网格生成
        assert mocks["generate_mesh"].call_count == 0

    def test_legacy_max_area_rejection_still_applies(self, monkeypatch):
        mocks = _install_cli_mocks(monkeypatch)
        args = _parse([
            "--gfile", "dummy.eqdsk",
            "--max-area", "0.01",
            "--no-hdf5", "--no-smb",
        ])
        with pytest.raises(ValueError) as excinfo:
            cli._run(args)
        assert "--max-area" in str(excinfo.value)
        assert mocks["generate_mesh"].call_count == 0
