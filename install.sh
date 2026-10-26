#!/usr/bin/env bash
# Install dependencies only; never open a motor connection or transmit frames.
set -Eeuo pipefail
trap 'printf "\nInstallation failed at line %s. Fix the error above, then rerun ./install.sh.\n" "$LINENO" >&2' ERR

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]
Target: Jetson Orin Nano, Ubuntu 22.04 / Python 3.10 or Ubuntu 24.04 / Python 3.12 (ARM64).

  --check                  Print platform checks without making changes
  --runtime-only           Omit pytest, Ruff and development pip
  --skip-system            Skip apt, driver probing and group changes (CI/prepared hosts)
  --no-serial-permissions   Do not add the current user to dialout
  --allow-x86-64            Allow Ubuntu x86_64 for testing
  -h, --help               Show this help

Run as your normal user, not with sudo. The installer requests sudo for apt
and serial access only. It does not scan, enable, calibrate or move motors.
EOF
}

check_only=false
runtime_only=false
skip_system=false
serial_permissions=true
allow_x86=false
for arg in "$@"; do
    case "$arg" in
        --check) check_only=true ;;
        --runtime-only) runtime_only=true ;;
        --skip-system) skip_system=true ;;
        --no-serial-permissions) serial_permissions=false ;;
        --allow-x86-64) allow_x86=true ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ "$(uname -s)" != Linux || ! -r /etc/os-release ]]; then
    echo 'This installer requires Ubuntu Linux. No changes made.' >&2
    exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "$ID" != ubuntu ]]; then
    echo "Unsupported OS: $PRETTY_NAME. Ubuntu 22.04 or 24.04 required; no changes made." >&2
    exit 1
fi
case "$VERSION_ID" in
    22.04) python_version=3.10 ;;
    24.04) python_version=3.12 ;;
    *) echo "Unsupported Ubuntu version: $VERSION_ID. Supported: 22.04, 24.04; no changes made." >&2; exit 1 ;;
esac
package_arch="$(dpkg --print-architecture)"
case "$package_arch" in
    arm64) ;;
    amd64) if ! $allow_x86; then echo 'ARM64 required; --allow-x86-64 is for tests.' >&2; exit 1; fi ;;
    *) echo "Unsupported userspace architecture: $package_arch. A 64-bit ARM64 Ubuntu installation is required." >&2; exit 1 ;;
esac
if [[ "$(getconf LONG_BIT)" != 64 ]]; then
    echo 'A 64-bit userspace is required; no changes made.' >&2
    exit 1
fi
printf 'Platform: %s; kernel=%s; packages=%s; Python=%s\n' "$PRETTY_NAME" "$(uname -m)" "$package_arch" "$python_version"
if [[ -r /proc/device-tree/model ]]; then
    printf 'Board: '; tr -d '\0' </proc/device-tree/model; printf '\n'
else
    echo 'Board identity unavailable; Ubuntu/architecture checks passed, Jetson hardware unverified.'
fi
if $check_only; then
    command -v "python$python_version" || true
    echo 'Read-only platform check complete.'
    exit 0
fi
if (( EUID == 0 )) && ! $skip_system; then
    echo 'Run ./install.sh as your normal login user, without sudo.' >&2
    exit 1
fi

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
if [[ ! -w "$project_dir" ]]; then
    echo 'The project folder must be writable by your login user. Clone or extract it in your home directory.' >&2
    exit 1
fi
if ! $skip_system; then
    command -v sudo >/dev/null || { echo 'sudo is required.' >&2; exit 1; }
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
        ca-certificates git "python$python_version" "python$python_version-venv" python3-pip \
        can-utils iproute2 usbutils kmod
fi
command -v "python$python_version" >/dev/null || { echo "Install python$python_version and python$python_version-venv first." >&2; exit 1; }
"python$python_version" -c 'import sys, struct; assert ".".join(map(str, sys.version_info[:2])) == sys.argv[1]; assert struct.calcsize("P") == 8' "$python_version"
"python$python_version" -m venv .bootstrap
.bootstrap/bin/python -m pip install --disable-pip-version-check 'uv==0.13.5'
sync_args=()
if $runtime_only; then sync_args+=(--no-dev); fi
UV_PYTHON_DOWNLOADS=never .bootstrap/bin/uv sync --locked --python "$(command -v "python$python_version")" "${sync_args[@]}"
.bootstrap/bin/uv pip check --python .venv/bin/python

if ! $skip_system; then
    if $serial_permissions; then
        target_user="$(id -un)"
        if ! id -nG "$target_user" | tr ' ' '\n' | grep -qx dialout; then
            sudo usermod -aG dialout "$target_user"
            echo 'Serial access configured. Log out and back in before using the adapter.'
        fi
    fi
    if ! sudo modprobe ch341; then
        echo 'WARNING: ch341 could not be loaded. Check your Jetson kernel before using the adapter.' >&2
    fi
fi

.venv/bin/python scripts/doctor.py
if ! $runtime_only; then .venv/bin/python -m pytest -q tests; fi
printf '\nEnvironment installed. No motor commands were sent.\nActivate: source "%s/.venv/bin/activate"\n' "$project_dir"
echo 'For PyCharm, select this project’s .venv/bin/python interpreter.'
