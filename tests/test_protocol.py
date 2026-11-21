"""Synthetic Shimano STEPS payloads and ride-distance edge cases."""

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
        decode = protocol["distance_frame"]
        distance = 232_546
        self.assertEqual(
            decode(b"\x03" + distance.to_bytes(4, "little") + bytes(14)).odometer_m,
            distance,
        )
        self.assertEqual(decode(b"\x03" + bytes(18)).odometer_m, 0)
        for invalid in (b"", b"\x03" + bytes(17), b"\x02" + bytes(18),
                        b"\x03" + b"\xff" * 4 + bytes(14)):
            self.assertIsNone(decode(invalid))

    def test_range_modes_and_reserved_values(self):
        packet = b"\x03" + bytes(12) + bytes.fromhex("2700ffff7d00")
        frame = protocol["distance_frame"](packet)
        self.assertEqual(frame.range_boost_km, 39)
        self.assertIsNone(frame.range_trail_km)
        self.assertEqual(frame.range_eco_km, 125)
        self.assertEqual(protocol["distance_frame"](b"\x03" + bytes(18)).range_eco_km, 0)

    def test_assistance_mode(self):
        decode = protocol["assist_mode"]
        self.assertEqual(decode(bytes([2, 0]) + bytes(8)), "off")
        self.assertEqual(decode(bytes([2, 2]) + bytes(8)), "trail")
        self.assertEqual(decode(bytes([2, 5]) + bytes(8)), "walk_active")
        for invalid in (b"", bytes([3, 1]) + bytes(8), bytes([2, 255]) + bytes(8)):
            self.assertIsNone(decode(invalid))

    def test_distance_between_syncs(self):
        decode = protocol["distance_since_sync"]
        self.assertEqual(decode(8000, 13000), 5)
        self.assertEqual(decode(13000, 13000), 0)
        self.assertIsNone(decode(None, 13000))
        self.assertIsNone(decode(13000, 2000))
