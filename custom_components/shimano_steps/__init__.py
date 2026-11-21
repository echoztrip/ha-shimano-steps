"""Read Shimano STEPS data over Home Assistant Bluetooth."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .coordinator import ShimanoCoordinator

type ShimanoConfigEntry = ConfigEntry[ShimanoCoordinator]

PLATFORMS = (Platform.SENSOR,)


async def async_setup_entry(hass: HomeAssistant, entry: ShimanoConfigEntry) -> bool:
    """Load entities even if the bike is currently switched off."""
    entry.runtime_data = ShimanoCoordinator(hass, entry, entry.data[CONF_ADDRESS])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.runtime_data.start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShimanoConfigEntry) -> bool:
    """Unload sensors and cancel the associated Bluetooth work."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_stop()
    return True
