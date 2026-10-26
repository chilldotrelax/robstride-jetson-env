# RobStride Jetson development environment

Single-command dependency setup for **Jetson Orin Nano on Ubuntu 22.04 or 24.04
ARM64**. The installer selects the OS-native Python: **3.10 on Ubuntu 22.04**
or **3.12 on Ubuntu 24.04**. Internet access and sudo access are required for installation.
JetPack/Ubuntu must already be installed; this repository does not flash the board.

## Install

Clone or download this repository to the Jetson, open a terminal in its folder,
and run as your normal user:

```bash
bash install.sh
```

Repository: https://github.com/chilldotrelax/robstride-jetson-env (private).
Sign into GitHub in the Jetson's browser, select **Code > Download ZIP**, and
extract it into your home directory. Alternatively, with authenticated Git:

```bash
git clone https://github.com/chilldotrelax/robstride-jetson-env.git
cd robstride-jetson-env
bash install.sh
```

Private cloning requires a GitHub credential or SSH key on the Jetson; signing
into GitHub on the Mac does not sign in the Jetson. The ZIP route avoids needing
Git credentials in the Jetson terminal.

The installer installs Ubuntu utilities, creates a project `.venv`, installs
locked Python dependencies, adds your user to `dialout` if needed, tries to load
the kernel's `ch341` driver, and runs offline checks. Re-running it restores the
same locked environment. It does not scan the bus or enable, calibrate, move,
configure, or flash motors. It does not change JetPack, CUDA, kernel firmware,
adapter firmware, or CAN bitrate.

Log out and back in after the installer adds serial permissions. Activate:

```bash
source .venv/bin/activate
python scripts/doctor.py
```

`doctor.py` imports packages and lists serial devices without opening them.
For PyCharm, open this folder and select `.venv/bin/python` as an existing
interpreter. Workstation-specific IDE settings are intentionally not included.

Options: `bash install.sh --help`. Use `--check` for a read-only platform check,
`--runtime-only` to omit development tools, or `--no-serial-permissions` to keep
your existing group memberships. `--skip-system` is for an already prepared
host or CI; it skips apt, driver loading, and group changes.

## Included dependencies

- Python CAN, pySerial, NumPy, tqdm, Matplotlib, and the vendored RobStride SDK.
- pytest, Ruff, and pip for development (default).
- Ubuntu: the appropriate Python/venv/pip, `can-utils`, `iproute2`, `usbutils`, `kmod`, Git,
  and CA certificates.
- uv 0.13.5 bootstraps the locked environment; `uv.lock` pins package versions
  and hashes. `requirements-jetson.txt` is a runtime-only export excluding the
  separately vendored SDK.

No ROS, CUDA Python packages, or unrelated language toolchains are needed for
this baseline. Unsupported Ubuntu releases and 32-bit userspaces are rejected.
Architecture is checked using `dpkg --print-architecture` plus userspace width;
a kernel/shell label of `arm` alone is not treated as proof of a 32-bit system.

For an existing checkout, fetch the installer update before retrying:

```bash
git pull --ff-only
bash install.sh
```

If you originally downloaded a ZIP, download and extract the updated ZIP instead.

## Adapter and motor status

The adapter is the [RobStride USB-to-CAN module, Seeed SKU 100012096](https://www.seeedstudio.com/Robostride-CAN-USB-Driver-Board-p-6708.html),
with a CH340 serial bridge. It normally appears as `/dev/ttyUSB0` on Linux and
uses AT serial framing. It does **not** automatically create SocketCAN `can0`.
The kernel normally supplies `ch341`; if loading it fails, the installer warns
and leaves kernel/driver installation to the appropriate Jetson configuration.

**Motor communication is not yet verified.** The local AT transport passes
offline tests, but the previous Mac scan received no motor replies. Moving to
Linux does not by itself establish that the adapter protocol/configuration or
motor wiring is correct. The 921600 serial baud rate is an assumption that may
need adjustment; it is separate from CAN bitrate. No end-to-end timing or
real-time performance is guaranteed.

RobStride 01, 03 and 04 model entries are present. EduLite 05 support and scaling
remain unverified; no EduLite alias or new motor parameters have been added.
Motion programs are omitted from this repository.

## Optional ID scan (run explicitly)

After checking motor power, CAN wiring/termination, and adapter configuration:

```bash
python vendor/RobStride_Control/python/src/ping.py --list-ports
python vendor/RobStride_Control/python/src/ping.py /dev/ttyUSB0 --baudrate 921600
```

This sends only device-ID requests across IDs 1–254; it does not enable or move
motors. With no channel argument, the scanner selects exactly one CH340 device
with USB ID `1a86:7523`. Other products share that USB ID, so an explicit device
path is preferable. Close other programs using the serial port first.

For a different, SocketCAN-compatible adapter on Linux, pass its configured
interface name, such as `can0`. Its bitrate/interface setup is hardware specific
and is not performed by the installer.

If no motors reply, compare the same hardware setup in RobStride's official
debugging application. Detection there would point toward the Python transport
or its configuration; no detection leaves hardware and adapter setup to check.

## Offline tests

```bash
python -m pytest -q tests
```

Tests use simulated serial data and never open an adapter. Source provenance and
local modifications are recorded in [THIRD_PARTY.md](THIRD_PARTY.md).
Ubuntu 22.04 is documented by [NVIDIA JetPack 6.2](https://developer.nvidia.com/embedded/jetpack-sdk-62);
Ubuntu 24.04 and Jetson Linux 39.2.1 are documented by
[NVIDIA JetPack 7.2.1](https://developer.nvidia.com/embedded/jetpack/downloads).
