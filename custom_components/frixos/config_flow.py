"""Config flow for Frixos integration."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .auth import (
    AuthLocked,
    InvalidAuth,
    async_get_challenge,
    async_login,
    hash_password,
    new_cookie_session_kwargs,
)
from .const import CONF_IDENTITY_HOST, CONF_PASSWORD_HASH, DOMAIN, DEFAULT_PORT, ENDPOINT_STATUS, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default="Frixos"): str,
        vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any], password_hash: str | None = None
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    A typed password wins over password_hash (the one already stored). The result's
    "password_hash" is what to store: None when the device has no access password.
    """
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, DEFAULT_PORT)
    base_url = f"http://{host}:{port}"

    async with aiohttp.ClientSession(**new_cookie_session_kwargs()) as session:
        try:
            challenge = await async_get_challenge(session, base_url)
            if challenge.get("auth"):
                if data.get(CONF_PASSWORD):
                    password_hash = await hass.async_add_executor_job(
                        hash_password, data[CONF_PASSWORD], challenge
                    )
                await async_login(session, base_url, password_hash)
            else:
                password_hash = None

            async with session.get(
                f"{base_url}{ENDPOINT_STATUS}", timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract device info if available
                    device_info = {
                        "hostname": host,
                        "app": result.get("app", "Frixos"),
                        "version": result.get("version", "Unknown"),
                        "password_hash": password_hash,
                    }
                    return device_info
                else:
                    raise CannotConnect(f"Server returned status {response.status}")
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Error connecting to device: {err}") from err
        except asyncio.TimeoutError as err:
            raise CannotConnect(f"Timeout connecting to device: {err}") from err


def _with_password_hash(data: dict[str, Any], password_hash: str | None) -> dict[str, Any]:
    """Entry data with the hash to keep, and never the typed password."""
    data = {k: v for k, v in data.items() if k not in (CONF_PASSWORD, CONF_PASSWORD_HASH)}
    if password_hash:
        data[CONF_PASSWORD_HASH] = password_hash
    return data


async def _validate(
    hass: HomeAssistant, data: dict[str, Any], errors: dict[str, str], password_hash: str | None = None
) -> dict[str, Any] | None:
    """validate_input that reports a failure in errors instead of raising."""
    try:
        return await validate_input(hass, data, password_hash)
    except InvalidAuth:
        errors["base"] = "invalid_auth"
    except AuthLocked:
        errors["base"] = "auth_locked"
    except CannotConnect:
        errors["base"] = "cannot_connect"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        errors["base"] = "unknown"
    return None


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

        errors: dict[str, str] = {}
        info = await _validate(self.hass, user_input, errors)
        if info is not None:
            # Use hostname as unique_id if available, otherwise use host:port
            unique_id = f"{user_input[CONF_HOST]}:{user_input.get(CONF_PORT, DEFAULT_PORT)}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, info.get("app", "Frixos")),
                data=_with_password_hash(
                    {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                        CONF_NAME: user_input.get(CONF_NAME, info.get("app", "Frixos")),
                    },
                    info["password_hash"],
                ),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, {k: v for k, v in user_input.items() if k != CONF_PASSWORD}
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """The clock asked for an access password: one was set or changed on it."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the clock's access password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            info = await _validate(self.hass, {**entry.data, **user_input}, errors)
            if info is not None:
                return self.async_update_reload_and_abort(
                    entry, data=_with_password_hash(dict(entry.data), info["password_hash"])
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Point an existing entry at a new host or port, keeping its entities."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            unique_id = f"{host}:{port}"
            # An empty password field keeps the stored hash.
            info = await _validate(self.hass, user_input, errors, entry.data.get(CONF_PASSWORD_HASH))
            if info is not None:
                for other in self._async_current_entries(include_ignore=False):
                    if other.entry_id != entry.entry_id and other.unique_id == unique_id:
                        return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data=_with_password_hash(
                        {
                            **entry.data,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            # Entity and device IDs stay keyed on the first host.
                            CONF_IDENTITY_HOST: entry.data.get(
                                CONF_IDENTITY_HOST, entry.data[CONF_HOST]
                            ),
                        },
                        info["password_hash"],
                    ),
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Optional(
                        CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)
                    ): int,
                    vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
