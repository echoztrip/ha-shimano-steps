"""Set up Shimano STEPS through Bluetooth discovery or a supplied address."""

from __future__ import annotations

import re
from typing import Any

from habluetooth import BluetoothServiceInfoBleak
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from .const import CONF_BATTERY_CYCLES, CONF_BATTERY_HEALTH, DOMAIN


class ShimanoStepsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one entry per bike."""

    VERSION = 1
    _address: str

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ShimanoDiagnosticsOptions:
        """Allow entering independently measured battery diagnostics."""
        return ShimanoDiagnosticsOptions()

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        self._address = discovery_info.address.upper()
        await self.async_set_unique_id(self._address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Shimano STEPS", data={CONF_ADDRESS: self._address}
            )
        return self.async_show_form(step_id="confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper().replace("-", ":")
            if re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", address):
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Shimano STEPS", data={CONF_ADDRESS: address}
                )
            errors[CONF_ADDRESS] = "invalid_address"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            errors=errors,
        )


class ShimanoDiagnosticsOptions(OptionsFlowWithReload):
    """Store both available diagnostics locally on the bike's config entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        schema = vol.Schema(
            {
                vol.Optional(CONF_BATTERY_HEALTH): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(CONF_BATTERY_CYCLES): vol.All(int, vol.Range(min=0)),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, self.config_entry.options),
        )
