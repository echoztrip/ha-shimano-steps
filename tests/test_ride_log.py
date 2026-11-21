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
    async def test_positive_changes_are_retained_across_restarts(self):
        RideLog = load_ride_log()

        def sample(meters, battery=72):
            return SimpleNamespace(
                distance=SimpleNamespace(odometer_m=meters),
                synced_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
                battery=battery,
            )

        log = RideLog(None, "synthetic_bike")
        self.assertIsNone(await log.async_record(sample(184000)))
        self.assertEqual(await log.async_record(sample(184000)), 0)
        self.assertEqual(await log.async_record(sample(192250)), 8.25)
        self.assertEqual(log.records()[0]["battery_percent"], 72)

        restored = RideLog(None, "synthetic_bike")
        await restored.async_load()
        self.assertEqual(restored.records(), log.records())
        self.assertIsNone(await restored.async_record(sample(2500)))
        self.assertEqual(await restored.async_record(sample(4750)), 2.25)
        self.assertEqual([ride["distance_km"] for ride in restored.records()], [8.25, 2.25])
