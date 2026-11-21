"""Perform one short Bluetooth telemetry session after the bike advertises."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import logging
from time import monotonic

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from habluetooth import BluetoothServiceInfoBleak

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import BATTERY_LEVEL, DFLY_TELEMETRY, DOMAIN
from .protocol import battery_percent, odometer_meters

_LOGGER = logging.getLogger(__name__)
_WAKE_GAP = 30
_RETRY_DELAY = 8


@dataclass(frozen=True, slots=True)
class Telemetry:
    """One complete battery and odometer reading."""

    battery: int
    distance_m: int


async def async_read_telemetry(device: BLEDevice) -> Telemetry:
    """Read battery and capture one odometer notification."""
    result: asyncio.Future[int | None] = asyncio.get_running_loop().create_future()

    def handle_telemetry(_characteristic, data: bytearray) -> None:
        distance = odometer_meters(data)
        if distance is not None and not result.done():
            result.set_result(distance)

    def handle_disconnect(_client: BleakClient) -> None:
        if not result.done():
            result.set_result(None)

    async with asyncio.timeout(35):
        client = await establish_connection(
            BleakClient, device, "Shimano STEPS",
            disconnected_callback=handle_disconnect, max_attempts=1,
        )
        try:
            await asyncio.sleep(0.6)
            charge = battery_percent(await client.read_gatt_char(BATTERY_LEVEL))
            await client.start_notify(DFLY_TELEMETRY, handle_telemetry)
            async with asyncio.timeout(12):
                distance = await result
            if distance is None:
                raise BleakError("Bike disconnected before reporting the odometer")
            return Telemetry(charge, distance)
        finally:
            result.cancel()
            with suppress(BleakError, TimeoutError, OSError):
                async with asyncio.timeout(5):
                    await client.disconnect()


class ShimanoCoordinator:
    """Resume reading on a new advertisement burst without idle polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
        self.hass = hass
        self.entry = entry
        self.address = address
        self.signal = f"{DOMAIN}_{entry.entry_id}"
        self.latest: Telemetry | None = None
        self._job: asyncio.Task[None] | None = None
        self._last_seen = float("-inf")
        self._last_attempt = float("-inf")
        self._attempts = 0
        self._sampled = False
        self._stopped = False

    @callback
    def start(self) -> Callable[[], None]:
        """Receive live advertisements for this bike through Home Assistant."""
        return bluetooth.async_register_advertisement_callback(
            self.hass, self._async_advertisement, self.address
        )

    @callback
    def _async_advertisement(self, info: BluetoothServiceInfoBleak) -> None:
        if self._stopped or not info.connectable:
            return
        now = monotonic()
        if now - self._last_seen >= _WAKE_GAP and self._job is None:
            self._attempts = 0
            self._sampled = False
        self._last_seen = now
        if self._sampled or self._job is not None or self._attempts >= 2:
            return
        if now - self._last_attempt < _RETRY_DELAY:
            return
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            return
        self._last_attempt = now
        self._attempts += 1
        self._job = self.entry.async_create_background_task(
            self.hass, self._async_sample(device), f"{DOMAIN} read telemetry"
        )

    async def _async_sample(self, device: BLEDevice) -> None:
        try:
            self.latest = await async_read_telemetry(device)
        except (BleakError, TimeoutError, OSError, ValueError) as err:
            # BLE exception strings can contain the address of the bike.
            _LOGGER.debug("Shimano telemetry read failed (%s)", type(err).__name__)
        else:
            self._sampled = True
            async_dispatcher_send(self.hass, self.signal)
        finally:
            self._job = None

    async def async_stop(self) -> None:
        """Stop reading and release the connection on unload."""
        self._stopped = True
        if job := self._job:
            job.cancel()
            with suppress(asyncio.CancelledError):
                await job
