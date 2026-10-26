#!/usr/bin/env bash
# Install dependencies only; never open a motor connection or transmit frames.
set -Eeuo pipefail
trap 'printf "\nInstallation failed at line %s. Fix the error above, then rerun ./install.sh.\n" "$LINENO" >&2' ERR

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]
Target: Jetson Orin Nano, JetPack 6 / Ubuntu 22.04 ARM64 / Python 3.10.

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
if [[ "$ID" != ubuntu || "$VERSION_ID" != 22.04 ]]; then
    echo 'Supported target: Ubuntu 22.04 (JetPack 6). No changes made.' >&2
    exit 1
fi
case "$(uname -m)" in
    aarch64|arm64) ;;
    x86_64) if ! $allow_x86; then echo 'ARM64 required; --allow-x86-64 is for tests.' >&2; exit 1; fi ;;
    *) echo 'Unsupported CPU architecture.' >&2; exit 1 ;;
esac
printf 'Platform: %s, %s\n' "$PRETTY_NAME" "$(uname -m)"
if [[ -r /proc/device-tree/model ]]; then
    printf 'Board: '; tr -d '\0' </proc/device-tree/model; printf '\n'
else
    echo 'Board identity unavailable; Ubuntu/architecture checks passed, Jetson hardware unverified.'
fi
if $check_only; then
    command -v python3.10 || true
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
        ca-certificates git python3.10 python3.10-venv python3-pip \
        can-utils iproute2 usbutils kmod
fi
command -v python3.10 >/dev/null || { echo 'Install python3.10 and python3.10-venv first.' >&2; exit 1; }
python3.10 -c 'import sys; assert sys.version_info[:2] == (3, 10)'
python3.10 -m venv .bootstrap
.bootstrap/bin/python -m pip install --disable-pip-version-check 'uv==0.13.5'
sync_args=()
if $runtime_only; then sync_args+=(--no-dev); fi
UV_PYTHON_DOWNLOADS=never .bootstrap/bin/uv sync --locked --python "$(command -v python3.10)" "${sync_args[@]}"
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
