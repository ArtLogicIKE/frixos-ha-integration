"""Number platform for Frixos integration."""
from __future__ import annotations

import json

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_SCROLL_DELAY,
    PARAM_LUX_SENSITIVITY,
    PARAM_LUX_THRESHOLD,
    PARAM_BRIGHTNESS_LED,
    PARAM_PWM_FREQUENCY,
    PARAM_MAX_POWER,
    PARAM_HA_REFRESH_MINS,
    PARAM_STOCK_REFRESH_MINS,
    PARAM_DEXCOM_REFRESH,
    PARAM_WIFI_START,
    PARAM_WIFI_END,
    PARAM_GLUCOSE_VALIDITY_DURATION,
    PARAM_SEC_TIME,
    PARAM_SEC_CGM,
    PARAM_GLUCOSE_HIGH,
    PARAM_DIM_START,
    PARAM_DIM_END,
    PARAM_SEC_WEATHER,
    PARAM_DIGIT_SCHEDULE,
)
from .coordinator import FrixosDataUpdateCoordinator
from .entity import FrixosEntity

# The device stores these as minutes from midnight (0-1439); the entities show hours.
MINUTE_OF_DAY_PARAMS = {PARAM_WIFI_START, PARAM_WIFI_END, PARAM_DIM_START, PARAM_DIM_END}

# The digit display rotation is the p58 schedule (slot "t" = type, "d" = seconds);
# the legacy p48/p49/p57 values are only read when the device migrates an empty schedule.
SCHEDULE_SLOT_TYPES = {PARAM_SEC_TIME: 0, PARAM_SEC_CGM: 1, PARAM_SEC_WEATHER: 2}
MAX_SCHEDULE_SLOTS = 8


def _schedule_slots(settings: dict) -> list | None:
    """Return the p58 display schedule as a list, or None when the device has none."""
    raw = settings.get(PARAM_DIGIT_SCHEDULE)
    if not isinstance(raw, str) or not raw:
        return None
    try:
        slots = json.loads(raw)
    except ValueError:
        return None
    return slots if isinstance(slots, list) else None


def _with_slot_duration(slots: list, slot_type: int, seconds: int) -> list:
    """Set every slot of a type to the duration; 0 removes them, a missing one is appended."""
    out = []
    found = False
    for slot in slots:
        if isinstance(slot, dict) and slot.get("t") == slot_type:
            found = True
            if seconds <= 0:
                continue
            slot = {**slot, "d": seconds}
        out.append(slot)
    if not found and seconds > 0 and len(out) < MAX_SCHEDULE_SLOTS:
        out.append({"t": slot_type, "d": seconds})
    return out


NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key=PARAM_SCROLL_DELAY,
        name="Scroll Delay",
        icon="mdi:timer-outline",
        native_min_value=30,
        native_max_value=255,
        native_step=1,
        native_unit_of_measurement="ms",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_LUX_SENSITIVITY,
        name="Light Sensitivity",
        icon="mdi:brightness-6",
        native_min_value=0,
        native_max_value=50,
        native_step=0.1,
        native_unit_of_measurement="lux",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_LUX_THRESHOLD,
        name="Day Threshold",
        icon="mdi:brightness-6",
        native_min_value=0,
        native_max_value=500,
        native_step=0.1,
        native_unit_of_measurement="lux",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=f"{PARAM_BRIGHTNESS_LED}_0",
        name="LED Brightness Day",
        icon="mdi:led-on",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=f"{PARAM_BRIGHTNESS_LED}_1",
        name="LED Brightness Night",
        icon="mdi:led-on",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_PWM_FREQUENCY,
        name="PWM Frequency",
        icon="mdi:sine-wave",
        native_min_value=60,
        native_max_value=50000,
        native_step=1,
        native_unit_of_measurement="Hz",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_MAX_POWER,
        name="Max Power",
        icon="mdi:lightbulb-on",
        native_min_value=1,
        native_max_value=1023,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_HA_REFRESH_MINS,
        name="Home Assistant Refresh Interval",
        icon="mdi:refresh",
        native_min_value=1,
        native_max_value=7200,
        native_step=1,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_STOCK_REFRESH_MINS,
        name="Stock Refresh Interval",
        icon="mdi:refresh",
        native_min_value=1,
        native_max_value=1440,
        native_step=1,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_DEXCOM_REFRESH,
        name="Dexcom Refresh Interval",
        icon="mdi:refresh",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_WIFI_START,
        name="WiFi Active Hours Start",
        icon="mdi:clock-time-one",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        native_unit_of_measurement="h",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_WIFI_END,
        name="WiFi Active Hours End",
        icon="mdi:clock-time-twelve",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        native_unit_of_measurement="h",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_GLUCOSE_VALIDITY_DURATION,
        name="Glucose Data Validity Duration",
        icon="mdi:timer",
        native_min_value=10,
        native_max_value=360,
        native_step=1,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_SEC_TIME,
        name="Alternate Time Display Duration",
        icon="mdi:clock-outline",
        native_min_value=1,
        native_max_value=120,
        native_step=1,
        native_unit_of_measurement="s",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_SEC_CGM,
        name="Alternate CGM Display Duration",
        icon="mdi:medical-bag",
        native_min_value=0,
        native_max_value=120,
        native_step=1,
        native_unit_of_measurement="s",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_SEC_WEATHER,
        name="Alternate Weather Display Duration",
        icon="mdi:weather-partly-cloudy",
        native_min_value=0,
        native_max_value=120,
        native_step=1,
        native_unit_of_measurement="s",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_GLUCOSE_HIGH,
        name="High Glucose Threshold",
        icon="mdi:arrow-up-bold",
        native_min_value=1,
        native_max_value=400,
        native_step=1,
        native_unit_of_measurement="mg/dL",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_DIM_START,
        name="Dim Start Hour",
        icon="mdi:weather-night",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        native_unit_of_measurement="h",
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key=PARAM_DIM_END,
        name="Dim End Hour",
        icon="mdi:weather-sunset-up",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        native_unit_of_measurement="h",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frixos number entities."""
    coordinator: FrixosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FrixosNumber(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    ]

    async_add_entities(entities)


class FrixosNumber(FrixosEntity, NumberEntity):
    """Representation of a Frixos number."""

    def __init__(
        self,
        coordinator: FrixosDataUpdateCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        # Extract base param key (remove _0 or _1 suffix for brightness)
        # Both Day and Night brightness use the same order number
        param_key = description.key
        if param_key.startswith(f"{PARAM_BRIGHTNESS_LED}_"):
            param_key = PARAM_BRIGHTNESS_LED
        
        super().__init__(
            coordinator,
            f"{coordinator.host}_{description.key}",
            description.name,
            description.icon,
            param_key,
        )
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Display schedule durations exist only up to firmware 73 (text widgets replaced them)."""
        if self.entity_description.key in (PARAM_SEC_TIME, PARAM_SEC_CGM, PARAM_SEC_WEATHER):
            data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
            settings = data.get("settings") or {}
            if isinstance(settings, dict) and settings and self.entity_description.key not in settings:
                return False
        return super().available

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None
        
        settings = self.coordinator.data.get("settings", {})
        if not isinstance(settings, dict):
            return None
        
        # Handle brightness LED array (indexed by _0 or _1 suffix)
        if self.entity_description.key.startswith(f"{PARAM_BRIGHTNESS_LED}_"):
            brightness_array = settings.get(PARAM_BRIGHTNESS_LED, [])
            if isinstance(brightness_array, list):
                index = int(self.entity_description.key.split("_")[-1])
                if index < len(brightness_array):
                    return float(brightness_array[index])
            return None

        key = self.entity_description.key
        if key in SCHEDULE_SLOT_TYPES:
            slots = _schedule_slots(settings)
            if slots is not None:
                slot_type = SCHEDULE_SLOT_TYPES[key]
                for slot in slots:
                    if isinstance(slot, dict) and slot.get("t") == slot_type:
                        return float(slot.get("d", 0))
                return 0.0

        value = settings.get(key)
        if value is not None and key in MINUTE_OF_DAY_PARAMS:
            return round(float(value) / 60, 2)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        param_key = self.entity_description.key

        if param_key == PARAM_SCROLL_DELAY:
            await self.coordinator.async_set_layout_meta(scroll_delay=int(value))
            return

        settings = {}
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            settings = self.coordinator.data.get("settings", {})

        # Handle brightness LED array
        if param_key.startswith(f"{PARAM_BRIGHTNESS_LED}_"):
            brightness_array = list(settings.get(PARAM_BRIGHTNESS_LED, [0, 0]))
            index = int(param_key.split("_")[-1])
            # Ensure array is long enough for the index
            while len(brightness_array) <= index:
                brightness_array.append(0)
            brightness_array[index] = int(value)

            await self.coordinator.async_set_setting(PARAM_BRIGHTNESS_LED, brightness_array)
        elif param_key in SCHEDULE_SLOT_TYPES and (slots := _schedule_slots(settings)) is not None:
            slots = _with_slot_duration(slots, SCHEDULE_SLOT_TYPES[param_key], int(value))
            await self.coordinator.async_set_setting(
                PARAM_DIGIT_SCHEDULE, json.dumps(slots, ensure_ascii=False, separators=(",", ":"))
            )
        elif param_key in MINUTE_OF_DAY_PARAMS:
            await self.coordinator.async_set_setting(param_key, int(round(value * 60)))
        else:
            await self.coordinator.async_set_setting(param_key, value)
