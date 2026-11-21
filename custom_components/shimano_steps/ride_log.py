"""Keep ride distances after Recorder purges detailed sensor history."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .protocol import distance_since_sync

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import Telemetry


class Ride(TypedDict):
    """A positive odometer change between two Bluetooth syncs."""

    synced_at: str
    distance_km: float
    odometer_km: float
    battery_percent: int


class RideLogData(TypedDict):
    """Persisted odometer baseline and ride records."""

    previous_m: int | None
    rides: list[Ride]


class RideLog:
    """Maintain a separate ride log for each configured bike."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[RideLogData](
            hass, 1, f"{DOMAIN}.rides.{entry_id}", private=True, atomic_writes=True
        )
        self._data: RideLogData = {"previous_m": None, "rides": []}

    async def async_load(self) -> None:
        """Restore the ride records and baseline."""
        if (saved := await self._store.async_load()) is not None:
            self._data = saved

    async def async_record(self, sample: Telemetry) -> float | None:
        """Record a positive change and advance the baseline."""
        current_m = sample.distance.odometer_m
        previous_m = self._data["previous_m"]
        distance_km = distance_since_sync(previous_m, current_m)
        if current_m == previous_m:
            return distance_km
        rides = self._data["rides"]
        if distance_km is not None and distance_km > 0:
            ride: Ride = {
                "synced_at": sample.synced_at.isoformat(),
                "distance_km": distance_km,
                "odometer_km": current_m / 1000,
                "battery_percent": sample.battery,
            }
            rides = [*rides, ride]
        data: RideLogData = {"previous_m": current_m, "rides": rides}
        await self._store.async_save(data)
        self._data = data
        return distance_km

    def records(self) -> list[Ride]:
        """Return rides in sync order."""
        return [ride.copy() for ride in self._data["rides"]]
