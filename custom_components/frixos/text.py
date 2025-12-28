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
    PASSWORD_PARAMS,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity

# Map parameter keys to their max lengths
TEXT_MAX_LENGTHS = {
    PARAM_MESSAGE: 511,
    PARAM_LATITUDE: 12,
    PARAM_LONGITUDE: 12,
    PARAM_TIMEZONE: 64,
    PARAM_MSG_COLOR: 7,  # Hex color format: #RRGGBB
    PARAM_NIGHT_MSG_COLOR: 7,  # Hex color format: #RRGGBB
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
        )
        self.entity_description = description
        self._attr_native_min = 0
        # Get max length from our mapping
        self._attr_native_max = TEXT_MAX_LENGTHS.get(description.key, 255)
        # Set password mode for sensitive fields
        if description.key in PASSWORD_PARAMS:
            self._attr_mode = "password"

    @property
    def native_value(self) -> str | None:
        """Return the current value."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return ""
        
        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return ""
        
        value = settings.get(self.entity_description.key)
        if value is None:
            return ""
        
        value_str = str(value)
        
        # Normalize color values when reading
        if self.entity_description.key in (PARAM_MSG_COLOR, PARAM_NIGHT_MSG_COLOR):
            value_str = self._normalize_color(value_str)
        
        return value_str

    def _normalize_color(self, value: str) -> str:
        """Normalize hex color value to #RRGGBB format."""
        if not value:
            return value
        
        # Remove any whitespace
        value = value.strip()
        
        # Remove # if present (we'll add it back)
        value = value.lstrip("#")
        
        # Handle 3-digit hex (e.g., "F00" -> "FF0000")
        if len(value) == 3:
            value = "".join(c * 2 for c in value)
        
        # Ensure we have 6 hex digits
        if len(value) == 6 and all(c in "0123456789ABCDEFabcdef" for c in value):
            return f"#{value.upper()}"
        
        # If it doesn't match hex format, return as-is (let device handle validation)
        return value if value.startswith("#") else f"#{value}"

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        # Normalize color values to standard hex format
        if self.entity_description.key in (PARAM_MSG_COLOR, PARAM_NIGHT_MSG_COLOR):
            value = self._normalize_color(value)
        
        success = await self.coordinator.async_set_setting(self.entity_description.key, value)
        if success:
            self.async_write_ha_state()
