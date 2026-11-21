"""Decode read-only Shimano STEPS telemetry."""

from dataclasses import dataclass

ASSIST_MODES = ("off", "eco", "trail", "boost", "walk", "walk_active")


@dataclass(frozen=True, slots=True)
class DistanceFrame:
    """Odometer and the bike's estimated range for each assist mode."""

    odometer_m: int
    range_boost_km: int | None
    range_trail_km: int | None
    range_eco_km: int | None


def battery_percent(data: bytes | bytearray) -> int:
    """Decode the one-byte Battery Level characteristic."""
    if len(data) != 1 or data[0] > 100:
        raise ValueError("Invalid Battery Level payload")
    return data[0]


def distance_frame(data: bytes | bytearray) -> DistanceFrame | None:
    """Read a Shimano D-Fly type 0x03 frame with a valid odometer."""
    if len(data) < 19 or data[0] != 0x03:
        return None
    odometer_m = int.from_bytes(data[1:5], "little")
    if odometer_m == 0xFFFFFFFF:
        return None
    return DistanceFrame(
        odometer_m=odometer_m,
        range_boost_km=_range_km(data[13:15]),
        range_trail_km=_range_km(data[15:17]),
        range_eco_km=_range_km(data[17:19]),
    )


def _range_km(raw: bytes | bytearray) -> int | None:
    value = int.from_bytes(raw, "little")
    return None if value == 0xFFFF else value


def assist_mode(data: bytes | bytearray) -> str | None:
    """Return a recognized assist mode from a D-Fly type 0x02 frame."""
    if len(data) < 10 or data[0] != 0x02 or data[1] >= len(ASSIST_MODES):
        return None
    return ASSIST_MODES[data[1]]


def distance_since_sync(previous_m: int | None, current_m: int) -> float | None:
    """Return kilometres travelled, or establish a baseline after a reset."""
    if previous_m is None or current_m < previous_m:
        return None
    return (current_m - previous_m) / 1000
