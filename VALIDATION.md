# Validation

Checked October 26, 2026.

- Full `bash install.sh` succeeded in an Ubuntu 22.04 ARM64 Docker container
  under a normal, non-root user with sudo access.
- Installed Ubuntu's Python 3.10.12 and all locked Python dependencies.
- Package consistency and SDK/serial/numerical/plotting imports passed.
- All six offline transport/scanner regression tests passed.
- `--check` completed without making changes.
- Re-running with `--skip-system` reused the environment and passed all checks.
- `bash -n install.sh` passed; invoking the installer on macOS rejected the
  unsupported platform before making changes.
- A GitHub Actions workflow repeats the ARM64 Ubuntu container test on pushes.

The container has no USB devices or Jetson kernel modules. Its expected `ch341`
module warning does not establish whether that driver is available on the
Jetson. This test verifies installation, not motor detection, adapter protocol
compatibility, physical Jetson execution, or real-time control.
