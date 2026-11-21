"""Synthetic payloads for the two supported fields."""

import runpy
from pathlib import Path
import unittest

protocol = runpy.run_path(
    Path(__file__).resolve().parents[1] / "custom_components/shimano_steps/protocol.py"
)


class ProtocolTests(unittest.TestCase):
    def test_battery(self):
        decode = protocol["battery_percent"]
        for percent in (0, 47, 100):
            self.assertEqual(decode(bytes([percent])), percent)
        for invalid in (b"", b"\x65", b"\x11\x00"):
            with self.assertRaises(ValueError):
                decode(invalid)

    def test_odometer(self):
        decode = protocol["odometer_meters"]
        distance = 232_546
        self.assertEqual(
            decode(b"\x03" + distance.to_bytes(4, "little") + bytes(14)),
            distance,
        )
        self.assertEqual(decode(b"\x03" + bytes(18)), 0)
        for invalid in (b"", b"\x03" + bytes(17), b"\x02" + bytes(18),
                        b"\x03" + b"\xff" * 4 + bytes(14)):
            self.assertIsNone(decode(invalid))
