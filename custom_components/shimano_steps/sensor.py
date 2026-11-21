"""Battery and odometer sensors that retain the last successful reading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import ShimanoCoordinator, Telemetry

if TYPE_CHECKING:
    from . import ShimanoConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShimanoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([ShimanoBattery(coordinator), ShimanoOdometer(coordinator)])


class ShimanoSensor(RestoreSensor):
    """Store the last measured value when the bike is powered off."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ShimanoCoordinator, key: str) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            manufacturer="Shimano",
            name="Shimano STEPS",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (saved := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = saved.native_value
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._coordinator.signal, self._async_update)
        )
        self._async_update()

    @callback
    def _async_update(self) -> None:
        if (latest := self._coordinator.latest) is not None:
            self._attr_native_value = self._value_from(latest)
            self.async_write_ha_state()


class ShimanoBattery(ShimanoSensor):
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ShimanoCoordinator) -> None:
        super().__init__(coordinator, "battery")

    def _value_from(self, latest: Telemetry) -> int:
        return latest.battery


class ShimanoOdometer(ShimanoSensor):
    _attr_name = "Odometer"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: ShimanoCoordinator) -> None:
        super().__init__(coordinator, "odometer")

    def _value_from(self, latest: Telemetry) -> float:
        return latest.distance_m / 1000
