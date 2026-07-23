"""Switch platform for Frixos integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_FAHRENHEIT,
    PARAM_HOUR12,
    PARAM_QUIET_SCROLL,
    PARAM_QUIET_WEATHER,
    PARAM_SHOW_GRID,
    PARAM_MIRRORING,
    PARAM_SHOW_LEADING_ZERO,
    PARAM_UPDATE_FIRMWARE,
    PARAM_DOTS_BREATHE,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity

SWITCH_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key=PARAM_FAHRENHEIT,
        name="Temperature in Fahrenheit",
        icon="mdi:thermometer",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_HOUR12,
        name="12-Hour Time Format",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_QUIET_SCROLL,
        name="Show Scrolling Message",
        icon="mdi:message-scroll",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_QUIET_WEATHER,
        name="Show Weather Forecast",
        icon="mdi:weather-partly-cloudy",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_SHOW_GRID,
        name="Show Grid",
        icon="mdi:grid",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_MIRRORING,
        name="Mirror Display",
        icon="mdi:mirror",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_SHOW_LEADING_ZERO,
        name="Show Leading Zero",
        icon="mdi:clock-digital",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_UPDATE_FIRMWARE,
        name="Auto Firmware Update",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=PARAM_DOTS_BREATHE,
        name="Disable Breathing Time Dots",
        icon="mdi:dots-horizontal",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frixos switch entities."""
    coordinator: FrixosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrixosSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    ]

    async_add_entities(entities)


class FrixosSwitch(FrixosEntity, SwitchEntity):
    """Representation of a Frixos switch."""

    def __init__(
        self,
        coordinator: FrixosDataUpdateCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator,
            f"{coordinator.host}_{description.key}",
            description.name,
            description.icon,
            description.key,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return if the switch is turned on."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None

        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return None

        value = settings.get(self.entity_description.key)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_set(False)

    async def _async_set(self, enabled: bool) -> None:
        key = self.entity_description.key
        if key == PARAM_QUIET_SCROLL:
            await self.coordinator.async_set_message_enabled(enabled)
            return
        if key == PARAM_QUIET_WEATHER:
            await self.coordinator.async_set_weather_enabled(enabled)
            return
        await self.coordinator.async_set_setting(key, 1 if enabled else 0)
