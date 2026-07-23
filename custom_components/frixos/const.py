"""Constants for the Frixos integration."""
from typing import Final

DOMAIN: Final = "frixos"
DEFAULT_SCAN_INTERVAL: Final = 300  # seconds (5 minutes)
DEFAULT_TIMEOUT: Final = 10  # seconds
DEFAULT_PORT: Final = 80

# API endpoints
ENDPOINT_SETTINGS: Final = "/api/settings"
ENDPOINT_STATUS: Final = "/api/status"
ENDPOINT_SCREEN: Final = "/api/screen"
ENDPOINT_FILES: Final = "/api/files"

# Non-pXX select keys
SELECT_LAYOUT_PRESET: Final = "layout_preset"

# Parameter field mappings (API uses pXX format)
PARAM_HOSTNAME = "p00"
PARAM_X_OFFSET = "p01"
PARAM_Y_OFFSET = "p02"
PARAM_ROTATION = "p03"
PARAM_DAY_FONT = "p04"
PARAM_NIGHT_FONT = "p05"
PARAM_QUIET_SCROLL = "p06"
PARAM_QUIET_WEATHER = "p07"
PARAM_SHOW_GRID = "p08"
PARAM_MIRRORING = "p09"
PARAM_COLOR_FILTER = "p10"
PARAM_NIGHT_COLOR_FILTER = "p11"
PARAM_MSG_COLOR = "p12"
PARAM_MSG_FONT = "p13"
PARAM_SCROLL_DELAY = "p14"
PARAM_NIGHT_MSG_COLOR = "p15"
PARAM_MESSAGE = "p16"
PARAM_LATITUDE = "p17"
PARAM_LONGITUDE = "p18"
PARAM_TIMEZONE = "p19"
PARAM_LUX_SENSITIVITY = "p20"
PARAM_LUX_THRESHOLD = "p21"
PARAM_DIM_DISABLE = "p22"
PARAM_BRIGHTNESS_LED = "p23"
PARAM_SHOW_LEADING_ZERO = "p24"
PARAM_HA_URL = "p25"
PARAM_HA_TOKEN = "p26"
PARAM_HA_REFRESH_MINS = "p27"
PARAM_STOCK_KEY = "p28"
PARAM_STOCK_REFRESH_MINS = "p29"
PARAM_DEXCOM_REGION = "p30"
PARAM_DEXCOM_USERNAME = "p31"
PARAM_DEXCOM_PASSWORD = "p32"
PARAM_DEXCOM_REFRESH = "p33"
PARAM_WIFI_SSID = "p34"
PARAM_WIFI_PASS = "p35"
PARAM_FAHRENHEIT = "p36"
PARAM_HOUR12 = "p37"
PARAM_SCROLL_SPEED = "p38"
PARAM_UPDATE_FIRMWARE = "p39"
PARAM_LANGUAGE = "p41"
PARAM_PWM_FREQUENCY = "p42"
PARAM_MAX_POWER = "p43"
PARAM_LIBRE_REGION = "p44"
PARAM_GLUCOSE_VALIDITY_DURATION = "p45"
PARAM_WIFI_START = "p46"
PARAM_WIFI_END = "p47"
PARAM_SEC_TIME = "p48"
PARAM_SEC_CGM = "p49"
PARAM_DOTS_BREATHE = "p50"
PARAM_GLUCOSE_HIGH = "p51"
PARAM_GLUCOSE_LOW = "p52"
PARAM_CGM_UNIT = "p53"
PARAM_NIGHTSCOUT_URL = "p54"
PARAM_DIM_START = "p55"
PARAM_DIM_END = "p56"
PARAM_SEC_WEATHER = "p57"
PARAM_DIGIT_SCHEDULE = "p58"
PARAM_AUX_SCHEDULE = "p59"
PARAM_STATIC_IP = "p60"
PARAM_STATIC_GW = "p61"
PARAM_STATIC_NM = "p62"
PARAM_STATIC_DNS = "p63"
PARAM_DARK_THEME = "p40"

# Font options
FONT_OPTIONS = [
    "bold",
    "light",
    "lcd",
    "nixie",
    "robrito",
    "ficasso",
    "lichten",
    "kablame",
    "kablamo",
    "kaboom",
    "user1",
    "user2",
]

# Color filter options
COLOR_FILTER_OPTIONS = {
    0: "None",
    1: "Red",
    2: "Green",
    3: "Blue",
    4: "Black & White",
}

# Rotation options
ROTATION_OPTIONS = {
    0: "0°",
    1: "90°",
    2: "180°",
    3: "270°",
}

# Message font options (layout message widget / legacy p13)
MSG_FONT_OPTIONS = {
    0: "8pt",
    1: "10pt",
    2: "12pt",
    3: "14pt",
    4: "16pt",
}

# Dim mode (p22): brightness curve / full / time-of-day
DIM_MODE_OPTIONS = {
    0: "Auto brightness",
    1: "Full brightness",
    2: "Time of day",
}

# Language options
LANGUAGE_OPTIONS = {
    0: "English",
    1: "Deutsch",
    2: "Français",
    3: "Italiano",
    4: "Português",
    5: "Svenska",
    6: "Dansk",
    7: "Polski",
    8: "Español",
}

# Dexcom region options
DEXCOM_REGION_OPTIONS = {
    0: "Disabled",
    1: "US",
    2: "Japan",
    3: "Rest of World",
}

# Libre region options
LIBRE_REGION_OPTIONS = {
    0: "Disabled",
    1: "United States",
    2: "Europe",
    3: "Germany",
    4: "France",
    5: "Japan",
    6: "Australia",
    7: "Global / Rest of World",
}

# CGM unit options
CGM_UNIT_OPTIONS = {
    0: "mg/dL",
    1: "mmol/L",
}

# Settings that trigger device restart (network only on current firmware)
RESTART_REQUIRED_PARAMS = {
    PARAM_HOSTNAME,
    PARAM_WIFI_SSID,
    PARAM_WIFI_PASS,
    PARAM_STATIC_IP,
    PARAM_STATIC_GW,
    PARAM_STATIC_NM,
    PARAM_STATIC_DNS,
}

# Password fields (should be masked in config flow)
PASSWORD_PARAMS = {
    PARAM_WIFI_PASS,
}

# Map parameters to their page number and order (format: page.order)
# Page 1 = Basic, Page 2 = Layout/Display, Page 3 = Integration
PARAM_ORDER = {
    # Page 1: Basic Settings
    PARAM_FAHRENHEIT: "1.01",
    PARAM_HOUR12: "1.02",
    # 1.03 was Scroll Speed (removed)
    PARAM_UPDATE_FIRMWARE: "1.04",
    PARAM_LANGUAGE: "1.05",
    SELECT_LAYOUT_PRESET: "1.06",
    # Page 2: Layout / Display Settings
    # 2.01 / 2.02 were X/Y Offset (removed)
    PARAM_ROTATION: "2.03",
    PARAM_DAY_FONT: "2.04",
    PARAM_NIGHT_FONT: "2.05",
    PARAM_QUIET_SCROLL: "2.06",
    PARAM_QUIET_WEATHER: "2.07",
    PARAM_SHOW_GRID: "2.08",
    PARAM_MIRRORING: "2.09",
    PARAM_COLOR_FILTER: "2.10",
    PARAM_NIGHT_COLOR_FILTER: "2.11",
    PARAM_MSG_COLOR: "2.12",
    PARAM_MSG_FONT: "2.13",
    PARAM_SCROLL_DELAY: "2.14",
    PARAM_NIGHT_MSG_COLOR: "2.15",
    PARAM_MESSAGE: "2.16",
    PARAM_LATITUDE: "2.17",
    PARAM_LONGITUDE: "2.18",
    PARAM_TIMEZONE: "2.19",
    PARAM_LUX_SENSITIVITY: "2.20",
    PARAM_LUX_THRESHOLD: "2.21",
    PARAM_DIM_DISABLE: "2.22",
    PARAM_BRIGHTNESS_LED: "2.23",  # Will be split into Day/Night
    PARAM_SHOW_LEADING_ZERO: "2.24",
    PARAM_PWM_FREQUENCY: "2.25",
    PARAM_MAX_POWER: "2.26",
    PARAM_WIFI_START: "2.27",
    PARAM_WIFI_END: "2.28",
    PARAM_DOTS_BREATHE: "2.29",
    PARAM_DIM_START: "2.30",
    PARAM_DIM_END: "2.31",
    # Page 3: Integration Settings
    PARAM_HA_REFRESH_MINS: "3.01",
    PARAM_STOCK_REFRESH_MINS: "3.02",
    PARAM_DEXCOM_REFRESH: "3.03",
    PARAM_DEXCOM_REGION: "3.04",
    PARAM_LIBRE_REGION: "3.05",
    PARAM_GLUCOSE_VALIDITY_DURATION: "3.06",
    PARAM_SEC_TIME: "3.07",
    PARAM_SEC_CGM: "3.08",
    PARAM_GLUCOSE_HIGH: "3.09",
    PARAM_GLUCOSE_LOW: "3.10",
    PARAM_CGM_UNIT: "3.11",
    PARAM_NIGHTSCOUT_URL: "3.12",
    PARAM_SEC_WEATHER: "3.13",
}
