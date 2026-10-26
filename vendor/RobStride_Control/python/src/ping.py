#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RobStride CAN bus scanner (Python version)

Usage: python3 ping.py [channel] [--baudrate 921600]
Examples:
    python3 ping.py                         # Detect one CH340 USB-CAN adapter
    python3 ping.py /dev/cu.usbserial-2120   # macOS serial adapter
    python3 ping.py /dev/ttyUSB0             # Linux serial adapter
    python3 ping.py can0                    # Linux SocketCAN adapter

This script pings all IDs from 1 to 254 and reports responding motors.
Only device-ID requests are sent; no motor enable or motion commands are sent.
"""

import sys
import os
import time
import argparse
from serial.tools import list_ports

# --- Import the SDK ---
# Assume this script is in the same directory as position_control.py
# (that is, the parent directory is the SDK root)
try:
    # Try adding the SDK root directory to the import path
    sdk_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)

    # 1. Try importing from the installed package
    from robstride_dynamics import RobstrideBus
except ImportError:
    # 2. Try importing local files (if the SDK is not installed)
    try:
        print("Package 'robstride_dynamics' not found; trying local files...")
        from bus import RobstrideBus
    except ImportError as e:
        print(f"❌ Unable to import the RobstrideBus SDK: {e}")
        print("Make sure the parent directory of this script is the SDK root,")
        print("or that the SDK has been installed with 'pip install -e .'.")
        sys.exit(1)

def main():
    # --- 1. Get the CAN channel ---
    parser = argparse.ArgumentParser(description="Scan RobStride motor IDs without enabling motors.")
    parser.add_argument("channel", nargs="?", help="Serial port or Linux SocketCAN interface")
    parser.add_argument("--baudrate", type=int, default=921600, help="USB serial baud rate (default: 921600)")
    parser.add_argument("--list-ports", action="store_true", help="List serial ports without opening them")
    args = parser.parse_args()
    ports = list(list_ports.comports())
    if args.list_ports:
        for port in ports:
            print(f"{port.device}: {port.description} ({port.hwid})")
        return
    channel = args.channel
    if channel is None:
        matches = [p.device for p in ports if (p.vid, p.pid) == (0x1A86, 0x7523)]
        if len(matches) != 1:
            parser.error("Specify a serial port or Linux CAN interface; found "
                         f"{len(matches)} CH340 adapters. Use --list-ports to inspect devices.")
        channel = matches[0]
        print(f"Selected CH340 adapter: {channel}")
    if not channel.startswith(("/dev/", "COM")) and sys.platform != "linux":
        parser.error("SocketCAN interfaces such as can0 require Linux. "
                     "Run without a channel to detect your USB serial adapter.")

    print(f"🚀 RobStride bus scanner")
    print(f"📡 Scanning channel: {channel}")
    print(f"🔍 Search range: IDs 1 to 254")
    print("...")
    time.sleep(1) # Pause briefly to let the user read the message

    # --- 2. Run the scan ---
    found_motors = None
    try:
        # RobstrideBus.scan_channel already implements all the scanning logic
        # It uses tqdm internally to display a progress bar
        found_motors = RobstrideBus.scan_channel(
            channel, start_id=1, end_id=255, serial_baudrate=args.baudrate,
        ) # end_id=255 scans up to ID 254

    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        if "Operation not permitted" in str(e) or "Permission denied" in str(e):
            print("🔑 Check serial-port permissions (dialout group on Linux) and close other apps using the adapter.")
        elif "No such device" in str(e):
            print(f"🔌 Device error: CAN interface '{channel}' was not found.")
        sys.exit(1)

    # --- 3. Print the results ---
    if not found_motors:
        print("\n🚫 No responding motors were found on the bus.")
        print("Check motor power, CAN wiring/termination, adapter boot switch, and serial baud rate.")
    else:
        print("\n✅ Scan complete! Found the following motors:")
        print("=" * 60)
        print(f"{'Motor ID':<10} | {'MCU unique identifier (UUID)':<45}")
        print("-" * 60)

        # found_motors is a dictionary: {id: (id, uuid_bytearray)}
        # Sort by ID
        for motor_id in sorted(found_motors.keys()):
            # value is a tuple (id, uuid)
            _id, uuid = found_motors[motor_id]

            # Convert the bytearray to a readable hexadecimal string
            uuid_hex = uuid.hex() # 'hex()' is a bytearray method

            print(f"{motor_id:<10} | {uuid_hex}")

        print("=" * 60)

if __name__ == "__main__":
    main()
