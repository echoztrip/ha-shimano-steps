"""Telemetry sensors that keep their last readings between syncs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.dt import parse_datetime

from .const import CONF_BATTERY_CYCLES, CONF_BATTERY_HEALTH, DOMAIN
from .coordinator import ShimanoCoordinator, Telemetry
from .protocol import ASSIST_MODES

if TYPE_CHECKING:
    from . import ShimanoConfigEntry


@dataclass(frozen=True, kw_only=True)
class ShimanoDescription(SensorEntityDescription):
    """Description for a sensor sourced directly from a telemetry snapshot."""

    read: Callable[[Telemetry], int | float | str | datetime | None]


DESCRIPTIONS = (
    ShimanoDescription(
        key="battery", name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        read=lambda sample: sample.battery,
    ),
    ShimanoDescription(
        key="battery_change", name="Battery change since previous sync",
        native_unit_of_measurement="pp",
        suggested_display_precision=0,
        read=lambda sample: sample.since_previous_sync_battery_pp,
    ),
    ShimanoDescription(
        key="odometer", name="Odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        read=lambda sample: sample.distance.odometer_m / 1000,
    ),
    ShimanoDescription(
        key="range_eco", name="Eco range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        read=lambda sample: sample.distance.range_eco_km,
    ),
    ShimanoDescription(
        key="range_trail", name="Trail range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        read=lambda sample: sample.distance.range_trail_km,
    ),
    ShimanoDescription(
        key="range_boost", name="Boost range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        read=lambda sample: sample.distance.range_boost_km,
    ),
    ShimanoDescription(
        key="assist_mode", name="Assist mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(ASSIST_MODES),
        read=lambda sample: sample.assist_mode,
    ),
    ShimanoDescription(
        key="last_sync", name="Last sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        read=lambda sample: sample.synced_at,
    ),
    ShimanoDescription(
        key="sync_distance", name="Distance since previous sync",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=3,
        read=lambda sample: sample.since_previous_sync_km,
    ),
)


DIAGNOSTICS = (
    SensorEntityDescription(
        key=CONF_BATTERY_HEALTH, name="Battery health",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=CONF_BATTERY_CYCLES, name="Battery charge cycles",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


def _device_info(address: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, address)}, manufacturer="Shimano", name="Shimano STEPS",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShimanoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [ShimanoSensor(coordinator, description) for description in DESCRIPTIONS]
        + [
            ShimanoDiagnostic(coordinator.address, description, entry.options.get(description.key))
            for description in DIAGNOSTICS
        ]
    )


class ShimanoSensor(RestoreSensor):
    """Store the last measured value when the bike is powered off."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ShimanoCoordinator, description: ShimanoDescription
    ) -> None:
        self._coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = _device_info(coordinator.address)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (saved := await self.async_get_last_sensor_data()) is not None:
            value = saved.native_value
            if self.device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
                value = parse_datetime(value)
            self._attr_native_value = value
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._coordinator.signal, self._async_update)
        )
        self._async_update()

    @callback
    def _async_update(self) -> None:
        if (latest := self._coordinator.latest) is not None:
            self._attr_native_value = self.entity_description.read(latest)
            self.async_write_ha_state()


class ShimanoDiagnostic(SensorEntity):
    """Expose the last manually supplied battery diagnostic."""

    _attr_has_entity_name = True
    _attr_extra_state_attributes = {"source": "manual_diagnostic"}

    def __init__(
        self, address: str, description: SensorEntityDescription, value: int | None
    ) -> None:
        self.entity_description = description
        self._attr_device_info = _device_info(address)
        self._attr_unique_id = f"{address}_{description.key}"
        self._attr_native_value = value
