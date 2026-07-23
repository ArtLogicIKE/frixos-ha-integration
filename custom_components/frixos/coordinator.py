"""Data update coordinator for Frixos integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Callable
from urllib.parse import quote

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ENDPOINT_FILES, ENDPOINT_SCREEN, ENDPOINT_SETTINGS, ENDPOINT_STATUS, DEFAULT_SCAN_INTERVAL
from .screen_layout import (
    SCREEN_BIN_WIRE_SIZE,
    decode_screen_layout_binary,
    encode_screen_layout_binary,
    get_scroll_text,
    layout_display_name,
    prepare_layout,
    set_message_style,
    set_scroll_text,
    set_widget_enabled,
)

_LOGGER = logging.getLogger(__name__)

# Give the device time to finish layout/integration work before we hammer it
# with a dual GET refresh (important after message/layout writes).
_POST_WRITE_SETTLE_SECONDS = 1.5
_BUSY_RETRY_DELAY_SECONDS = 1.0
_MAX_BUSY_RETRIES = 3


class FrixosDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Frixos data."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._session = async_get_clientsession(hass)
        self._write_lock = asyncio.Lock()
        self.layout_files: list[str] = []
        self.active_layout_file: str | None = None
        self._layout_cache: dict[str, Any] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Frixos device."""
        try:
            settings_data, status_data, files_data = await asyncio.gather(
                self._fetch_settings(),
                self._fetch_status(),
                self._fetch_files(),
                return_exceptions=True,
            )

            if isinstance(settings_data, Exception):
                _LOGGER.warning("Failed to fetch settings: %s", settings_data)
                settings_data = {}
            elif not isinstance(settings_data, dict):
                _LOGGER.warning("Settings data is not a dict: %s", type(settings_data))
                settings_data = {}

            if isinstance(status_data, Exception):
                _LOGGER.warning("Failed to fetch status: %s", status_data)
                status_data = {}
            elif not isinstance(status_data, dict):
                _LOGGER.warning("Status data is not a dict: %s", type(status_data))
                status_data = {}

            if isinstance(files_data, Exception):
                _LOGGER.debug("Failed to fetch files list: %s", files_data)
                files_data = self.layout_files
            elif isinstance(files_data, list):
                self.layout_files = files_data
            else:
                files_data = self.layout_files

            if not settings_data and not status_data:
                raise UpdateFailed("Failed to fetch both settings and status from device")

            # Warm layout cache once so message/preset entities reflect the screen engine.
            if self._layout_cache is None:
                try:
                    await self._fetch_screen_layout()
                except Exception as err:  # noqa: BLE001 - optional cache warm
                    _LOGGER.debug("Could not warm screen layout cache: %s", err)

            return {
                "settings": settings_data or {},
                "status": status_data or {},
                "layout_files": files_data or [],
                "active_layout_file": self.active_layout_file,
                "layout": self._layout_cache,
            }
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def _fetch_settings(self) -> dict:
        """Fetch settings from device."""
        url = f"{self.base_url}{ENDPOINT_SETTINGS}"
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise UpdateFailed(f"Settings endpoint returned invalid data: {type(data)}")
                    return data
                text = await response.text()
                raise UpdateFailed(f"Settings endpoint returned status {response.status}: {text}")
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error fetching settings: {err}") from err

    async def _fetch_status(self) -> dict:
        """Fetch status from device."""
        url = f"{self.base_url}{ENDPOINT_STATUS}"
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise UpdateFailed(f"Status endpoint returned invalid data: {type(data)}")
                    return data
                text = await response.text()
                raise UpdateFailed(f"Status endpoint returned status {response.status}: {text}")
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error fetching status: {err}") from err

    async def _fetch_files(self) -> list[str]:
        """Fetch SPIFFS file list and return .layout preset names."""
        url = f"{self.base_url}{ENDPOINT_FILES}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                return list(self.layout_files)
            data = await response.json()
            files = data.get("files", []) if isinstance(data, dict) else []
            names: list[str] = []
            for entry in files:
                name = entry.get("name") if isinstance(entry, dict) else entry
                if isinstance(name, str) and name.lower().endswith(".layout"):
                    names.append(name)
            names.sort(key=lambda n: layout_display_name(n).lower())
            return names

    async def async_set_setting(self, param: str, value: Any) -> bool:
        """Update a setting on the device via /api/settings."""
        url = f"{self.base_url}{ENDPOINT_SETTINGS}"
        payload = {param: value}

        async with self._write_lock:
            try:
                result = await self._post_json_with_busy_retry(url, payload)
                if result is None:
                    return False
                await asyncio.sleep(_POST_WRITE_SETTLE_SECONDS)
                await self.async_request_refresh()
                return result.get("status") == "ok" if isinstance(result, dict) else True
            except Exception as err:
                _LOGGER.error("Error updating setting %s: %s", param, err)
                return False

    async def async_apply_layout_preset(self, filename: str) -> bool:
        """Load a .layout file from the device and apply it via /api/screen."""
        async with self._write_lock:
            try:
                # Device serves .layout as a static file with no JSON Content-Type
                # (browser fetch().json() is fine; aiohttp requires content_type=None).
                safe_name = quote(filename.lstrip("/"), safe="/")
                layout_url = f"{self.base_url}/{safe_name}"
                async with self._session.get(
                    layout_url, timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        _LOGGER.error("Failed to load layout %s: HTTP %s", filename, response.status)
                        return False
                    data = await response.json(content_type=None)

                if not isinstance(data, dict) or "profiles" not in data:
                    _LOGGER.error("Layout file %s is invalid", filename)
                    return False

                layout = prepare_layout(data)
                body = encode_screen_layout_binary(layout)
                if not await self._post_screen_binary(body):
                    return False

                self.active_layout_file = filename
                self._layout_cache = layout
                self._mirror_layout_into_settings(layout)
                await asyncio.sleep(_POST_WRITE_SETTLE_SECONDS)
                await self.async_request_refresh()
                return True
            except Exception as err:
                _LOGGER.error("Error applying layout preset %s: %s", filename, err)
                return False

    async def async_set_scroll_message(self, text: str) -> bool:
        """Set scrolling message via layout scroll_text (not legacy p16 alone)."""
        return await self._async_mutate_screen(
            lambda layout: set_scroll_text(layout, text),
            heavy=True,
        )

    async def async_set_message_enabled(self, enabled: bool) -> bool:
        """Show/hide scrolling message widget via layout."""
        return await self._async_mutate_screen(
            lambda layout: set_widget_enabled(layout, "message", enabled)
        )

    async def async_set_weather_enabled(self, enabled: bool) -> bool:
        """Show/hide weather widget via layout."""
        return await self._async_mutate_screen(
            lambda layout: set_widget_enabled(layout, "weather", enabled)
        )

    async def async_set_message_color(self, *, day: str | None = None, night: str | None = None) -> bool:
        """Update message colors via layout widgets."""
        return await self._async_mutate_screen(
            lambda layout: set_message_style(layout, color=day, night_color=night)
        )

    async def async_set_message_font(self, font: int) -> bool:
        """Update message font index via layout widgets."""
        return await self._async_mutate_screen(
            lambda layout: set_message_style(layout, font=font)
        )

    async def async_set_layout_meta(
        self,
        *,
        day_font: str | None = None,
        night_font: str | None = None,
        day_color_filter: int | None = None,
        night_color_filter: int | None = None,
        scroll_delay: int | None = None,
    ) -> bool:
        """Update layout header fields that the screen engine owns."""

        def _mutate(layout: dict[str, Any]) -> None:
            if day_font is not None:
                layout["day_font"] = day_font
            if night_font is not None:
                layout["night_font"] = night_font
            if day_color_filter is not None:
                layout["day_color_filter"] = day_color_filter
            if night_color_filter is not None:
                layout["night_color_filter"] = night_color_filter
            if scroll_delay is not None:
                layout["scroll_delay"] = scroll_delay

        return await self._async_mutate_screen(_mutate)

    def get_scroll_message(self) -> str | None:
        """Prefer layout scroll_text; fall back to mirrored p16 settings."""
        text = get_scroll_text(self._layout_cache)
        if text is not None:
            return text
        if self.data and isinstance(self.data, dict):
            settings = self.data.get("settings") or {}
            if isinstance(settings, dict) and "p16" in settings:
                return str(settings.get("p16") or "")
        return None

    async def _async_mutate_screen(
        self,
        mutator: Callable[[dict[str, Any]], None],
        *,
        heavy: bool = False,
    ) -> bool:
        """GET current screen layout, mutate, POST back."""
        async with self._write_lock:
            try:
                layout = await self._fetch_screen_layout()
                if layout is None:
                    return False
                mutator(layout)
                body = encode_screen_layout_binary(layout)
                if not await self._post_screen_binary(body):
                    return False
                self._layout_cache = layout
                self._mirror_layout_into_settings(layout)
                # Message/layout updates can trigger deferred integration parsing
                # and a full display rebuild; wait longer before refreshing.
                await asyncio.sleep(_POST_WRITE_SETTLE_SECONDS * (2 if heavy else 1))
                await self.async_request_refresh()
                return True
            except Exception as err:
                _LOGGER.error("Error updating screen layout: %s", err)
                return False

    async def _fetch_screen_layout(self) -> dict[str, Any] | None:
        """Fetch and decode current screen layout binary."""
        url = f"{self.base_url}{ENDPOINT_SCREEN}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                _LOGGER.error("Failed to fetch screen layout: HTTP %s", response.status)
                return None
            data = await response.read()
        if len(data) != SCREEN_BIN_WIRE_SIZE:
            _LOGGER.error(
                "Unexpected screen layout size %s (expected %s)",
                len(data),
                SCREEN_BIN_WIRE_SIZE,
            )
            return None
        layout = decode_screen_layout_binary(data)
        self._layout_cache = layout
        return layout

    async def _post_screen_binary(self, body: bytes) -> bool:
        """POST encoded layout to /api/screen with busy retries."""
        if len(body) != SCREEN_BIN_WIRE_SIZE:
            _LOGGER.error("Refusing to POST screen layout with size %s", len(body))
            return False

        url = f"{self.base_url}{ENDPOINT_SCREEN}"
        for attempt in range(_MAX_BUSY_RETRIES):
            try:
                async with self._session.post(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Accept": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as response:
                    if response.status == 503:
                        _LOGGER.warning(
                            "Device busy (503) posting screen layout, retry %s/%s",
                            attempt + 1,
                            _MAX_BUSY_RETRIES,
                        )
                        await asyncio.sleep(_BUSY_RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    result = await response.json(content_type=None)
                    if response.status == 200 and isinstance(result, dict) and result.get("status") == "ok":
                        return True
                    _LOGGER.error(
                        "Failed to post screen layout: status %s, response: %s",
                        response.status,
                        result,
                    )
                    return False
            except Exception as err:
                _LOGGER.error("Error posting screen layout: %s", err)
                if attempt + 1 < _MAX_BUSY_RETRIES:
                    await asyncio.sleep(_BUSY_RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return False
        return False

    async def _post_json_with_busy_retry(self, url: str, payload: dict[str, Any]) -> dict | None:
        """POST JSON settings with retries on HTTP 503 (web server busy)."""
        for attempt in range(_MAX_BUSY_RETRIES):
            async with self._session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 503:
                    _LOGGER.warning(
                        "Device busy (503) updating settings, retry %s/%s",
                        attempt + 1,
                        _MAX_BUSY_RETRIES,
                    )
                    await asyncio.sleep(_BUSY_RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                if response.status == 200:
                    result = await response.json()
                    return result if isinstance(result, dict) else {"status": "ok"}
                response_text = await response.text()
                _LOGGER.error(
                    "Failed to update settings: status %s, response: %s",
                    response.status,
                    response_text,
                )
                return None
        _LOGGER.error("Device remained busy after %s retries", _MAX_BUSY_RETRIES)
        return None

    def _mirror_layout_into_settings(self, layout: dict[str, Any]) -> None:
        """Keep coordinator settings mirrors in sync after a layout write."""
        if not self.data or not isinstance(self.data, dict):
            return
        settings = self.data.get("settings")
        if not isinstance(settings, dict):
            return

        scroll = get_scroll_text(layout)
        if scroll is not None:
            settings["p16"] = scroll
        if "scroll_delay" in layout:
            settings["p14"] = layout["scroll_delay"]
        if "day_font" in layout:
            settings["p04"] = layout["day_font"]
        if "night_font" in layout:
            settings["p05"] = layout["night_font"]
        if "day_color_filter" in layout:
            settings["p10"] = layout["day_color_filter"]
        if "night_color_filter" in layout:
            settings["p11"] = layout["night_color_filter"]

        day = (layout.get("profiles") or {}).get("day") or {}
        for elem in day.get("elements") or []:
            if not elem:
                continue
            if elem.get("id") == "message":
                settings["p06"] = 1 if elem.get("enabled") else 0
                opts = elem.get("options") or {}
                if "color" in opts:
                    settings["p12"] = opts["color"]
                if "font" in opts:
                    settings["p13"] = opts["font"]
            elif elem.get("id") == "weather":
                settings["p07"] = 1 if elem.get("enabled") else 0

        night = (layout.get("profiles") or {}).get("night") or {}
        for elem in night.get("elements") or []:
            if elem and elem.get("id") == "message":
                opts = elem.get("options") or {}
                if "color" in opts:
                    settings["p15"] = opts["color"]
                break
