"""Decode the two telemetry values used by the integration."""


def battery_percent(data: bytes | bytearray) -> int:
    """Decode the one-byte Battery Level characteristic."""
    if len(data) != 1 or data[0] > 100:
        raise ValueError("Invalid Battery Level payload")
    return data[0]


def odometer_meters(data: bytes | bytearray) -> int | None:
    """Return the lifetime distance from a Shimano D-Fly type 0x03 frame."""
    if len(data) < 19 or data[0] != 0x03:
        return None
    meters = int.from_bytes(data[1:5], "little")
    return None if meters == 0xFFFFFFFF else meters
