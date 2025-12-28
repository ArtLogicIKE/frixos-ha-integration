"""Color platform for Frixos integration."""
from __future__ import annotations

from homeassistant.components.color import ColorEntity, ColorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_MSG_COLOR,
    PARAM_NIGHT_MSG_COLOR,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity

COLOR_DESCRIPTIONS: tuple[ColorEntityDescription, ...] = (
    ColorEntityDescription(
        key=PARAM_MSG_COLOR,
        name="Message Color (Day)",
        icon="mdi:palette",
        entity_category=EntityCategory.CONFIG,
    ),
    ColorEntityDescription(
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
    """Set up Frixos color entities."""
    coordinator: FrixosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrixosColor(coordinator, description)
        for description in COLOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class FrixosColor(FrixosEntity, ColorEntity):
    """Representation of a Frixos color picker."""

    def __init__(
        self,
        coordinator: FrixosDataUpdateCoordinator,
        description: ColorEntityDescription,
    ) -> None:
        """Initialize the color entity."""
        super().__init__(
            coordinator,
            f"{coordinator.host}_{description.key}",
            description.name,
            description.icon,
        )
        self.entity_description = description
        self._param_key = description.key

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int] | None:
        """Convert hex color string to RGB tuple."""
        if not hex_color or not isinstance(hex_color, str):
            return None
        
        # Remove # if present
        hex_color = hex_color.lstrip("#")
        
        # Handle 3-digit hex (e.g., #F00 -> #FF0000)
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        
        # Handle 6-digit hex
        if len(hex_color) == 6:
            try:
                return (
                    int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16),
                )
            except ValueError:
                return None
        
        return None

    def _rgb_to_hex(self, rgb: tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color string."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [0..255], [0..255], [0..255]."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None
        
        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return None
        
        value = settings.get(self._param_key)
        
        if value is None:
            return None
        
        # Handle different formats
        if isinstance(value, str):
            # Hex string format (e.g., "#FF0000" or "FF0000")
            rgb = self._hex_to_rgb(value)
            if rgb:
                return rgb
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            # RGB tuple/list format [r, g, b]
            try:
                return (int(value[0]), int(value[1]), int(value[2]))
            except (ValueError, TypeError):
                pass
        elif isinstance(value, int):
            # Integer format - might be a packed RGB value
            # Try to interpret as 0xRRGGBB
            hex_str = f"{value:06x}"
            rgb = self._hex_to_rgb(hex_str)
            if rgb:
                return rgb
        
        # Default to white if we can't parse
        return (255, 255, 255)

    async def async_turn_on(
        self,
        rgb_color: tuple[int, int, int] | None = None,
        brightness: int | None = None,
        **kwargs,
    ) -> None:
        """Set the color."""
        if rgb_color is None:
            return
        
        # Convert RGB to hex format for the device
        hex_color = self._rgb_to_hex(rgb_color)
        
        success = await self.coordinator.async_set_setting(self._param_key, hex_color)
        if success:
            self.async_write_ha_state()

