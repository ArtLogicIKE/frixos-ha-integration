"""Config flow for Frixos integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_IDENTITY_HOST, DOMAIN, DEFAULT_PORT, ENDPOINT_STATUS, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default="Frixos"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, DEFAULT_PORT)

    # Construct URL
    url = f"http://{host}:{port}{ENDPOINT_STATUS}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract device info if available
                    device_info = {
                        "hostname": host,
                        "app": result.get("app", "Frixos"),
                        "version": result.get("version", "Unknown"),
                    }
                    return device_info
                else:
                    raise CannotConnect(f"Server returned status {response.status}")
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Error connecting to device: {err}") from err
        except asyncio.TimeoutError as err:
            raise CannotConnect(f"Timeout connecting to device: {err}") from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frixos."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Use hostname as unique_id if available, otherwise use host:port
            unique_id = f"{user_input[CONF_HOST]}:{user_input.get(CONF_PORT, DEFAULT_PORT)}"
            
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, info.get("app", "Frixos")),
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                    CONF_NAME: user_input.get(CONF_NAME, info.get("app", "Frixos")),
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Point an existing entry at a new host or port, keeping its entities."""
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            unique_id = f"{host}:{port}"
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                for other in self._async_current_entries(include_ignore=False):
                    if other.entry_id != entry.entry_id and other.unique_id == unique_id:
                        return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data={
                        **entry.data,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        # Entity and device IDs stay keyed on the first host.
                        CONF_IDENTITY_HOST: entry.data.get(
                            CONF_IDENTITY_HOST, entry.data[CONF_HOST]
                        ),
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Optional(
                        CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)
                    ): int,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
