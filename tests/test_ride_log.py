"""Exercise ride history and baseline restoration with a simulated HA Store."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class MemoryStore:
    data = {}

    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, _hass, _version, key, **_kwargs):
        self.key = key

    async def async_load(self):
        return deepcopy(self.data.get(self.key))

    async def async_save(self, data):
        self.data[self.key] = deepcopy(data)


def load_ride_log():
    package = ModuleType("_shimano_test")
    package.__path__ = [
        str(Path(__file__).resolve().parents[1] / "custom_components/shimano_steps")
    ]
    storage = ModuleType("homeassistant.helpers.storage")
    storage.Store = MemoryStore
    with patch.dict(sys.modules, {package.__name__: package, storage.__name__: storage}):
        return importlib.import_module("_shimano_test.ride_log").RideLog


class RideLogTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def sample(meters, battery=72):
        return SimpleNamespace(
            distance=SimpleNamespace(odometer_m=meters),
            synced_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
            battery=battery,
        )

    async def test_positive_changes_are_retained_across_restarts(self):
        RideLog = load_ride_log()
        log = RideLog(None, "synthetic_bike")
        self.assertIsNone((await log.async_record(self.sample(184000))).distance_km)
        charged = await log.async_record(self.sample(184000, 80))
        self.assertEqual((charged.distance_km, charged.battery_pp), (0, 8))
        self.assertEqual(log.records(), [])
        restored = RideLog(None, "synthetic_bike")
        await restored.async_load()
        trip = await restored.async_record(self.sample(192250, 65))
        self.assertEqual((trip.distance_km, trip.battery_pp), (8.25, -15))
        self.assertEqual(restored.records()[0]["battery_percent"], 65)
        self.assertEqual(restored.records()[0]["battery_change_pp"], -15)
        self.assertIsNone((await restored.async_record(self.sample(2500))).distance_km)
        self.assertEqual((await restored.async_record(self.sample(4750))).distance_km, 2.25)
        self.assertEqual([ride["distance_km"] for ride in restored.records()], [8.25, 2.25])

    async def test_legacy_history_is_preserved_without_inventing_a_charge_delta(self):
        RideLog = load_ride_log()
        original = {
            "synced_at": "2025-01-14T01:00:00+00:00",
            "distance_km": 5.0,
            "odometer_km": 12.0,
            "battery_percent": 55,
        }
        MemoryStore.data["shimano_steps.rides.legacy"] = {
            "previous_m": 12000,
            "rides": [original],
        }
        log = RideLog(None, "legacy")
        await log.async_load()
        upgraded = await log.async_record(self.sample(16000, 70))
        self.assertEqual(upgraded.distance_km, 4)
        self.assertIsNone(upgraded.battery_pp)
        self.assertEqual(log.records()[0], original)
        self.assertNotIn("battery_change_pp", log.records()[1])
