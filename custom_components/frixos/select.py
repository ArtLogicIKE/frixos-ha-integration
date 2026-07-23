"""Select platform for Frixos integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_ROTATION,
    PARAM_DAY_FONT,
    PARAM_NIGHT_FONT,
    PARAM_COLOR_FILTER,
    PARAM_NIGHT_COLOR_FILTER,
    PARAM_MSG_FONT,
    PARAM_DEXCOM_REGION,
    PARAM_LANGUAGE,
    PARAM_LIBRE_REGION,
    PARAM_CGM_UNIT,
    PARAM_DIM_DISABLE,
    SELECT_LAYOUT_PRESET,
    FONT_OPTIONS,
    COLOR_FILTER_OPTIONS,
    ROTATION_OPTIONS,
    MSG_FONT_OPTIONS,
    DEXCOM_REGION_OPTIONS,
    LANGUAGE_OPTIONS,
    LIBRE_REGION_OPTIONS,
    CGM_UNIT_OPTIONS,
    DIM_MODE_OPTIONS,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity
from .screen_layout import layout_display_name

SELECT_DESCRIPTIONS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=PARAM_ROTATION,
        name="Display Rotation",
        icon="mdi:rotate-3d-variant",
        options=list(ROTATION_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_DAY_FONT,
        name="Day Font",
        icon="mdi:format-font",
        options=FONT_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_NIGHT_FONT,
        name="Night Font",
        icon="mdi:format-font",
        options=FONT_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_COLOR_FILTER,
        name="Day Color Filter",
        icon="mdi:palette",
        options=list(COLOR_FILTER_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_NIGHT_COLOR_FILTER,
        name="Night Color Filter",
        icon="mdi:palette",
        options=list(COLOR_FILTER_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_MSG_FONT,
        name="Message Font Size",
        icon="mdi:format-size",
        options=list(MSG_FONT_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_DIM_DISABLE,
        name="Dim Mode",
        icon="mdi:brightness-auto",
        options=list(DIM_MODE_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_DEXCOM_REGION,
        name="Dexcom Region",
        icon="mdi:map-marker",
        options=list(DEXCOM_REGION_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_LANGUAGE,
        name="Language",
        icon="mdi:translate",
        options=list(LANGUAGE_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_LIBRE_REGION,
        name="Libre Region",
        icon="mdi:map-marker",
        options=list(LIBRE_REGION_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key=PARAM_CGM_UNIT,
        name="Glucose Display Unit",
        icon="mdi:format-list-numbered",
        options=list(CGM_UNIT_OPTIONS.values()),
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frixos select entities."""
    coordinator: FrixosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    mappings = {
        PARAM_ROTATION: ROTATION_OPTIONS,
        PARAM_DAY_FONT: None,
        PARAM_NIGHT_FONT: None,
        PARAM_COLOR_FILTER: COLOR_FILTER_OPTIONS,
        PARAM_NIGHT_COLOR_FILTER: COLOR_FILTER_OPTIONS,
        PARAM_MSG_FONT: MSG_FONT_OPTIONS,
        PARAM_DIM_DISABLE: DIM_MODE_OPTIONS,
        PARAM_DEXCOM_REGION: DEXCOM_REGION_OPTIONS,
        PARAM_LANGUAGE: LANGUAGE_OPTIONS,
        PARAM_LIBRE_REGION: LIBRE_REGION_OPTIONS,
        PARAM_CGM_UNIT: CGM_UNIT_OPTIONS,
    }

    entities: list[SelectEntity] = [
        FrixosSelect(coordinator, description, mappings[description.key])
        for description in SELECT_DESCRIPTIONS
    ]
    entities.append(FrixosLayoutPresetSelect(coordinator))
    async_add_entities(entities)


class FrixosSelect(FrixosEntity, SelectEntity):
    """Representation of a Frixos select."""

    def __init__(
        self,
        coordinator: FrixosDataUpdateCoordinator,
        description: SelectEntityDescription,
        options_map: dict[int, str] | None,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(
            coordinator,
            f"{coordinator.host}_{description.key}",
            description.name,
            description.icon,
            description.key,
        )
        self.entity_description = description
        self._param_key = description.key
        self._options_map = options_map

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None

        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return None

        value = settings.get(self._param_key)
        if value is None:
            return None

        if self._options_map:
            try:
                return self._options_map.get(int(value))
            except (ValueError, TypeError):
                return None

        return str(value) if value else None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        key = self._param_key

        if key in (PARAM_DAY_FONT, PARAM_NIGHT_FONT):
            kwargs = {"day_font": option} if key == PARAM_DAY_FONT else {"night_font": option}
            await self.coordinator.async_set_layout_meta(**kwargs)
            return

        if self._options_map:
            for map_key, val in self._options_map.items():
                if val != option:
                    continue
                if key == PARAM_COLOR_FILTER:
                    await self.coordinator.async_set_layout_meta(day_color_filter=map_key)
                elif key == PARAM_NIGHT_COLOR_FILTER:
                    await self.coordinator.async_set_layout_meta(night_color_filter=map_key)
                elif key == PARAM_MSG_FONT:
                    await self.coordinator.async_set_message_font(map_key)
                else:
                    await self.coordinator.async_set_setting(key, map_key)
                return

        await self.coordinator.async_set_setting(key, option)


class FrixosLayoutPresetSelect(FrixosEntity, SelectEntity):
    """Select a ready-made .layout preset from the device SPIFFS gallery."""

    def __init__(self, coordinator: FrixosDataUpdateCoordinator) -> None:
        """Initialize the layout preset select."""
        super().__init__(
            coordinator,
            f"{coordinator.host}_{SELECT_LAYOUT_PRESET}",
            "Layout Preset",
            "mdi:view-dashboard-variant",
            SELECT_LAYOUT_PRESET,
        )
        self._attr_entity_category = EntityCategory.CONFIG
        self._filename_by_label: dict[str, str] = {}

    def _refresh_options(self) -> list[str]:
        files = list(self.coordinator.layout_files or [])
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            listed = self.coordinator.data.get("layout_files")
            if isinstance(listed, list) and listed:
                files = listed
        self._filename_by_label = {layout_display_name(name): name for name in files}
        return list(self._filename_by_label.keys())

    @property
    def options(self) -> list[str]:
        """Return available layout preset names."""
        return self._refresh_options()

    @property
    def current_option(self) -> str | None:
        """Return the last applied layout preset, if known."""
        labels = self._refresh_options()
        active = self.coordinator.active_layout_file
        if active:
            label = layout_display_name(active)
            if label in labels:
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        """Apply the selected layout preset on the device."""
        self._refresh_options()
        filename = self._filename_by_label.get(option)
        if not filename:
            raise HomeAssistantError(f"Unknown layout preset: {option}")
        if not await self.coordinator.async_apply_layout_preset(filename):
            raise HomeAssistantError(f"Failed to apply layout preset: {option}")
        self.async_write_ha_state()
