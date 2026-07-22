"""Text platform for Frixos integration."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_MESSAGE,
    PARAM_LATITUDE,
    PARAM_LONGITUDE,
    PARAM_TIMEZONE,
    PARAM_MSG_COLOR,
    PARAM_NIGHT_MSG_COLOR,
    PARAM_GLUCOSE_LOW,
    PARAM_NIGHTSCOUT_URL,
    PASSWORD_PARAMS,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity

TEXT_MAX_LENGTHS = {
    PARAM_MESSAGE: 511,
    PARAM_LATITUDE: 12,
    PARAM_LONGITUDE: 12,
    PARAM_TIMEZONE: 64,
    PARAM_MSG_COLOR: 7,
    PARAM_NIGHT_MSG_COLOR: 7,
    PARAM_GLUCOSE_LOW: 4,
    PARAM_NIGHTSCOUT_URL: 100,
}

TEXT_DESCRIPTIONS: tuple[TextEntityDescription, ...] = (
    TextEntityDescription(
        key=PARAM_MESSAGE,
        name="Scrolling Message",
        icon="mdi:message-text",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_LATITUDE,
        name="Latitude",
        icon="mdi:latitude",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_LONGITUDE,
        name="Longitude",
        icon="mdi:longitude",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_TIMEZONE,
        name="Timezone",
        icon="mdi:map-clock",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_MSG_COLOR,
        name="Message Color (Day)",
        icon="mdi:palette",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_NIGHT_MSG_COLOR,
        name="Message Color (Night)",
        icon="mdi:palette",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_GLUCOSE_LOW,
        name="Low Glucose Threshold",
        icon="mdi:arrow-down-bold",
        entity_category=EntityCategory.CONFIG,
    ),
    TextEntityDescription(
        key=PARAM_NIGHTSCOUT_URL,
        name="Nightscout URL",
        icon="mdi:cloud",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frixos text entities."""
    coordinator: FrixosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrixosText(coordinator, description)
        for description in TEXT_DESCRIPTIONS
    ]

    async_add_entities(entities)


class FrixosText(FrixosEntity, TextEntity):
    """Representation of a Frixos text entity."""

    def __init__(
        self,
        coordinator: FrixosDataUpdateCoordinator,
        description: TextEntityDescription,
    ) -> None:
        """Initialize the text entity."""
        super().__init__(
            coordinator,
            f"{coordinator.host}_{description.key}",
            description.name,
            description.icon,
            description.key,
        )
        self.entity_description = description
        self._attr_native_min = 0
        self._attr_native_max = TEXT_MAX_LENGTHS.get(description.key, 255)
        if description.key in PASSWORD_PARAMS:
            self._attr_mode = "password"

    @property
    def native_value(self) -> str | None:
        """Return the current value."""
        if self.entity_description.key == PARAM_MESSAGE:
            value_str = self.coordinator.get_scroll_message()
            if value_str is None:
                return None
            if len(value_str) > 255:
                return value_str[:252] + "..."
            return value_str

        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None

        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return None

        value = settings.get(self.entity_description.key)
        if value is None:
            return None

        value_str = str(value)

        if self.entity_description.key in (PARAM_MSG_COLOR, PARAM_NIGHT_MSG_COLOR):
            value_str = self._normalize_color(value_str)

        return value_str

    def _normalize_color(self, value: str) -> str:
        """Normalize hex color value to #RRGGBB format."""
        if not value:
            return value

        value = value.strip().lstrip("#")

        if len(value) == 3:
            value = "".join(c * 2 for c in value)

        if len(value) == 6 and all(c in "0123456789ABCDEFabcdef" for c in value):
            return f"#{value.upper()}"

        return value if value.startswith("#") else f"#{value}"

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        key = self.entity_description.key

        if key == PARAM_MESSAGE:
            await self.coordinator.async_set_scroll_message(value)
            return

        if key == PARAM_MSG_COLOR:
            value = self._normalize_color(value)
            await self.coordinator.async_set_message_color(day=value)
            return

        if key == PARAM_NIGHT_MSG_COLOR:
            value = self._normalize_color(value)
            await self.coordinator.async_set_message_color(night=value)
            return

        await self.coordinator.async_set_setting(key, value)
