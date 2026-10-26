"""RobStride USB-CAN AT serial transport (not SLCAN).

Framing follows the RS02 manual, communication box example on page 14:
https://files.seeedstudio.com/products/RobStride/Product%20Literature/RS02/RS02User%20Manual251112.pdf
"""

import struct
import time

import can
import serial


class RobstrideSerialCan:
    """Provide the send/recv/shutdown interface used by RobstrideBus.

    The serial baud rate is independent of the adapter's CAN bitrate. This
    transport uses the adapter's existing CAN configuration without changing it.
    """

    def __init__(self, channel: str, baudrate: int = 921600):
        self._buffer = bytearray()
        self._serial = serial.Serial(
            port=channel, baudrate=baudrate, timeout=0.1, write_timeout=1.0,
            exclusive=True,
        )

    def send(self, frame: can.Message):
        if (not frame.is_extended_id or frame.is_remote_frame
                or frame.is_error_frame or frame.is_fd):
            raise ValueError("RobStride serial transport requires extended classic CAN data frames")
        if not 0 <= frame.arbitration_id <= 0x1FFFFFFF or len(frame.data) > 8:
            raise ValueError("Invalid classic CAN frame")
        packed_id = (frame.arbitration_id << 3) | 0x04
        packet = b"AT" + struct.pack(">IB", packed_id, len(frame.data)) + bytes(frame.data) + b"\r\n"
        if self._serial.write(packet) != len(packet):
            raise serial.SerialTimeoutException("Incomplete USB-CAN packet write")

    def _extract_frame(self):
        while True:
            start = self._buffer.find(b"AT")
            if start < 0:
                # Keep a possible partial header across reads.
                self._buffer[:] = b"A" if self._buffer.endswith(b"A") else b""
                return None
            del self._buffer[:start]
            if len(self._buffer) < 7:
                return None
            packed_id, dlc = struct.unpack(">IB", self._buffer[2:7])
            if dlc > 8 or packed_id & 0x07 != 0x04:
                del self._buffer[0]
                continue
            length = 9 + dlc
            if len(self._buffer) < length:
                return None
            if self._buffer[length - 2:length] != b"\r\n":
                del self._buffer[0]
                continue
            data = bytes(self._buffer[7:7 + dlc])
            del self._buffer[:length]
            return can.Message(
                arbitration_id=packed_id >> 3, is_extended_id=True, data=data,
            )

    def recv(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + max(0, timeout)
        while True:
            frame = self._extract_frame()
            if frame is not None:
                return frame
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return None
            self._serial.timeout = 0.1 if remaining is None else min(0.1, remaining)
            self._buffer.extend(self._serial.read(max(1, min(self._serial.in_waiting, 4096))))

    def shutdown(self):
        self._serial.close()
