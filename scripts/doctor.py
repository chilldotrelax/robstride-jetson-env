"""Report environment and serial devices without opening any hardware ports."""

import importlib
import importlib.metadata
import platform
import sys

from serial.tools import list_ports


def main():
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Platform: {platform.system()} {platform.machine()}")
    if sys.version_info[:2] not in ((3, 10), (3, 12)):
        raise SystemExit("Use Python 3.10 on Ubuntu 22.04 or Python 3.12 on Ubuntu 24.04.")
    for module, distribution in [
        ("can", "python-can"),
        ("serial", "pyserial"),
        ("numpy", "numpy"),
        ("tqdm", "tqdm"),
        ("matplotlib", "matplotlib"),
        ("robstride_dynamics", "robstride-control"),
    ]:
        importlib.import_module(module)
        print(f"  {distribution}: {importlib.metadata.version(distribution)}")
    from robstride_dynamics.serial_can import RobstrideSerialCan

    assert callable(RobstrideSerialCan)
    ports = list(list_ports.comports())
    print("Serial devices (listed only, not opened):")
    for port in ports:
        print(f"  {port.device}: {port.description} [{port.hwid}]")
    if not ports:
        print("  None detected. Dependency installation can still be complete.")
    print("Imports passed. Adapter protocol and motor communication remain unverified.")


if __name__ == "__main__":
    main()
