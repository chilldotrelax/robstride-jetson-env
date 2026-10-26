"""Read-only platform-guard checks inside the Ubuntu validation containers."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Ubuntu container checks")
ROOT = Path(__file__).resolve().parents[1]


def run_check(tmp_path, program, body):
    shim = tmp_path / program
    shim.write_text("#!/bin/sh\n" + body + "\n")
    shim.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"])
    return subprocess.run(["bash", str(ROOT / "install.sh"), "--check"],
                          env=env, capture_output=True, text=True)


def test_arm_kernel_label_uses_actual_package_architecture(tmp_path):
    # Some shells report "arm"; dpkg and userspace width determine compatibility.
    if subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip() != "arm64":
        pytest.skip("Requires an actual ARM64 Ubuntu container")
    result = run_check(tmp_path, "uname", 'if [ "$1" = -m ]; then echo arm; else exec /usr/bin/uname "$@"; fi')
    assert result.returncode == 0, result.stderr
    assert "kernel=arm; packages=arm64" in result.stdout


def test_32_bit_package_architecture_is_rejected(tmp_path):
    result = run_check(tmp_path, "dpkg", "echo armhf")
    assert result.returncode != 0
    assert "Unsupported userspace architecture: armhf" in result.stderr


def test_32_bit_userspace_is_rejected(tmp_path):
    result = run_check(tmp_path, "getconf", "echo 32")
    assert result.returncode != 0
    assert "64-bit userspace is required" in result.stderr
