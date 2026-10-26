# Validation

Checked October 26, 2026.

- Full `bash install.sh` succeeded in Ubuntu 22.04 and 24.04 ARM64 Docker containers
  under a normal, non-root user with sudo access.
- Installed Ubuntu's native Python 3.10.12 on 22.04 and Python 3.12.3 on 24.04,
  plus all locked Python dependencies.
- Package consistency and SDK/serial/numerical/plotting imports passed.
- All nine offline regression tests passed on both OS versions: six transport/scanner
  tests plus three read-only architecture-guard tests. The latter cover a kernel
  label of `arm` with ARM64 userspace, and rejection of 32-bit packages/userspace.
- `--check` completed without making changes.
- Re-running with `--skip-system` reused the environment and passed all checks.
- `bash -n install.sh` passed; invoking the installer on macOS rejected the
  unsupported platform before making changes.
- A GitHub Actions matrix repeats both ARM64 Ubuntu container tests on pushes.

The container has no USB devices or Jetson kernel modules. Its expected `ch341`
module warning does not establish whether that driver is available on the
Jetson. This test verifies installation, not motor detection, adapter protocol
compatibility, physical Jetson execution, or real-time control.
