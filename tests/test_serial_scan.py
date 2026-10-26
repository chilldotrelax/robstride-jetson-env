"""Offline regression tests: no real serial port is opened."""

from collections import deque
from unittest.mock import patch

import can
import pytest
from robstride_dynamics import RobstrideBus
from robstride_dynamics.serial_can import RobstrideSerialCan


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.chunks = deque()
        self.writes = []
        self.closed = False

    @property
    def in_waiting(self):
        return len(self.chunks[0]) if self.chunks else 0

    def read(self, count):
        if not self.chunks:
            return b""
        data = self.chunks.popleft()
        self.chunks.appendleft(data[count:]) if len(data) > count else None
        return data[:count]

    def write(self, packet):
        self.writes.append(packet)
        return len(packet)

    def close(self):
        self.closed = True


@pytest.fixture
def transport():
    serial = FakeSerial()
    with patch("robstride_dynamics.serial_can.serial.Serial", return_value=serial):
        bus = RobstrideSerialCan("/dev/test")
    yield bus, serial
    bus.shutdown()


def test_manufacturer_example(transport):
    bus, serial = transport
    # RS02 manual page 14: CAN 0x1200FD01 -> packed ID 0x9007E80C.
    frame = can.Message(arbitration_id=0x1200FD01, is_extended_id=True,
                        data=bytes.fromhex("05 70 00 00 01 00 00 00"))
    bus.send(frame)
    expected = bytes.fromhex("41 54 90 07 e8 0c 08 05 70 00 00 01 00 00 00 0d 0a")
    assert serial.writes == [expected]
    serial.chunks.extend([expected[:1], expected[1:6], expected[6:]])
    response = bus.recv(0.05)
    assert response.arbitration_id == frame.arbitration_id
    assert response.data == frame.data


def test_noise_malformed_packets_and_consecutive_frames(transport):
    bus, serial = transport
    # Embedded header/trailer bytes in payload are not delimiters.
    first = bytes.fromhex("41 54 00 00 0f f4 04 41 54 0d 0a 0d 0a")
    second = bytes.fromhex("41 54 00 00 17 f4 00 0d 0a")
    bad_dlc = b"AT" + b"\x00" * 4 + b"\x09"
    bad_tail = second[:-2] + b"xx"
    serial.chunks.append(b"noise\r\n" + bad_dlc + bad_tail + first + second)
    assert bus.recv(0.05).data == b"AT\r\n"
    assert bus.recv(0.05).arbitration_id == 0x2FE
    assert bus.recv(0.001) is None


def test_incomplete_packet_does_not_hang(transport):
    bus, serial = transport
    serial.chunks.append(b"AT\x00\x00\x00\x04\x08abc")
    assert bus.recv(0.001) is None


def test_reject_standard_can_frames(transport):
    bus, serial = transport
    with pytest.raises(ValueError):
        bus.send(can.Message(arbitration_id=1, is_extended_id=False))
    assert not serial.writes


def test_scan_uses_only_id_requests_and_closes_port():
    class RespondingSerial(FakeSerial):
        def write(self, packet):
            result = super().write(packet)
            can_id = int.from_bytes(packet[2:6], "big") >> 3
            assert can_id >> 24 == 0  # GET_DEVICE_ID only
            motor_id = can_id & 0xFF
            if motor_id == 2:
                # Unrelated status frame before the matching ID response.
                self.chunks.append(b"AT" + ((0x020002FF << 3) | 4).to_bytes(4, "big")
                                   + b"\x08" + b"\x00" * 8 + b"\r\n")
                self.chunks.append(b"AT" + (((motor_id << 8 | 0xFE) << 3) | 4).to_bytes(4, "big")
                                   + b"\x08" + b"12345678" + b"\r\n")
            return result

    serial = RespondingSerial()
    with patch("robstride_dynamics.serial_can.serial.Serial", return_value=serial):
        found = RobstrideBus.scan_channel("/dev/test", start_id=1, end_id=4)
    assert found == {2: [2, bytearray(b"12345678")]}
    assert len(serial.writes) == 3
    assert serial.closed


def test_scan_closes_port_when_interrupted():
    serial = FakeSerial()
    with (
        patch("robstride_dynamics.serial_can.serial.Serial", return_value=serial),
        patch.object(RobstrideBus, "ping_by_id", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        RobstrideBus.scan_channel("/dev/test", start_id=1, end_id=2)
    assert serial.closed
    assert not serial.writes
