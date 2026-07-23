"""Encode/decode Frixos screen layout wire format (matches device f-screen-layout-bin).

Used to apply .layout presets and to update layout-owned fields (scroll text,
message visibility/colors/font, weather visibility, fonts, filters, scroll delay)
without rebuilding the layout editor in Home Assistant.
"""
from __future__ import annotations

import struct
from copy import deepcopy
from typing import Any

SCREEN_LAYOUT_VERSION = 10
SCREEN_BIN_MAGIC = 0x4653584C
SCREEN_BIN_FORMAT = 1
SCREEN_BIN_FONT_LEN = 12
SCREEN_BIN_WIDGET_SIZE = 13
SCREEN_BIN_WIDGET_COUNT = 28
SCREEN_BIN_SCROLL_LEN = 512
SCREEN_BIN_STATIC_TEXT_LEN = 96
SCREEN_BIN_STATIC_TEXT_COUNT = 8
SCREEN_BIN_GRAPH_SIZE = 88
SCREEN_BIN_GRAPH_TOKEN_LEN = 64
SCREEN_BIN_HEADER_SIZE = 64
SCREEN_BIN_PROFILE_SIZE = (
    SCREEN_BIN_WIDGET_COUNT * SCREEN_BIN_WIDGET_SIZE
    + SCREEN_BIN_SCROLL_LEN
    + SCREEN_BIN_STATIC_TEXT_COUNT * SCREEN_BIN_STATIC_TEXT_LEN
    + SCREEN_BIN_STATIC_TEXT_LEN * 2
    + SCREEN_BIN_GRAPH_SIZE
)
SCREEN_BIN_WIRE_SIZE = SCREEN_BIN_HEADER_SIZE + SCREEN_BIN_PROFILE_SIZE * 2
SCREEN_BIN_MIME = "application/vnd.frixos.screen-layout+1"
SCREEN_SIZE = 128

GRAPH_VAL_UNSET = -32768
GRAPH_FLAG_AUTOSCALE = 0x01
GRAPH_FLAG_SHOW_AXIS = 0x02
GRAPH_FLAG_BAND = 0x04
GRAPH_FLAG_BACKFILL = 0x08
GRAPH_FLAG_SHOW_VALUE = 0x10
GRAPH_FLAG_BOOLEAN = 0x20
GRAPH_FLAG_THICK = 0x40
GRAPH_FLAG_SHOW_XAXIS = 0x80

SCREEN_WIRE_ELEM_IDS = [
    "glucose_level",
    "glucose_trend",
    "wifi_off",
    "weather",
    "moon",
    "time",
    "message",
    "text_1",
    "text_2",
    "text_3",
    "text_4",
    "text_5",
    "text_6",
    "text_7",
    "text_8",
    "ampm",
    "time_aux",
    "digit_label",
    "digit_label_aux",
    "graph",
    "icon_1",
    "icon_2",
    "icon_3",
    "icon_4",
    "icon_5",
    "icon_6",
    "icon_7",
    "icon_8",
]

SCREEN_TEXT_SLOT_IDS = [
    "text_1",
    "text_2",
    "text_3",
    "text_4",
    "text_5",
    "text_6",
    "text_7",
    "text_8",
]

DEFAULT_SCROLL_TEXT = (
    "[device]: [greeting] [day], [date] [mon], now [temp] today [high]-[low], "
    "hum. [hum], sun [rise]-[set]"
)

DEFAULT_STATIC_TEXTS = {
    "text_1": "UV [uv]",
    "text_2": "[pressure]",
    "text_3": "Wind [wind]",
    "text_4": "Gust [gust]",
    "text_5": "Rain [precip]",
    "text_6": "",
    "text_7": "",
    "text_8": "",
    "digit_label": "",
    "digit_label_aux": "",
}


def layout_display_name(filename: str) -> str:
    """Human-readable name from a .layout filename."""
    name = filename.rsplit("/", 1)[-1]
    if name.lower().endswith(".layout"):
        name = name[: -len(".layout")]
    return name or filename


def _hex_to_rgb(hex_color: str | None, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not hex_color or len(hex_color) != 7 or hex_color[0] != "#":
        return fallback
    try:
        value = int(hex_color[1:], 16)
    except ValueError:
        return fallback
    return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _read_fixed_string(data: bytes, offset: int, length: int) -> str:
    chunk = data[offset : offset + length]
    end = chunk.find(b"\x00")
    if end < 0:
        end = length
    return chunk[:end].decode("utf-8", errors="replace")


def _write_fixed_string(buf: bytearray, offset: int, length: int, value: str | None) -> None:
    encoded = (value or "").encode("utf-8", errors="replace")[: length - 1]
    buf[offset : offset + length] = b"\x00" * length
    buf[offset : offset + len(encoded)] = encoded


def _find_element(profile: dict[str, Any], elem_id: str) -> dict[str, Any] | None:
    elements = profile.get("elements") or []
    for elem in elements:
        if elem and elem.get("id") == elem_id:
            return elem
    if elem_id == "time_aux":
        for elem in elements:
            if elem and elem.get("id") == "glucose":
                return elem
    return None


def _ensure_element(profile: dict[str, Any], elem_id: str) -> dict[str, Any]:
    elem = _find_element(profile, elem_id)
    if elem is not None:
        if elem.get("id") == "glucose":
            elem["id"] = "time_aux"
        return elem
    elem = {"id": elem_id, "enabled": 0, "x": 0, "y": 0, "z": 0}
    profile.setdefault("elements", []).append(elem)
    return elem


def prepare_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """Normalize a JSON .layout object before encoding."""
    layout = deepcopy(layout)
    if not layout.get("profiles"):
        raise ValueError("layout missing profiles")

    layout.setdefault("scroll_delay", 65)
    layout.setdefault("day_font", "bold")
    layout.setdefault("night_font", "bold")
    layout.setdefault("day_aux_font", layout.get("day_font") or "bold")
    layout.setdefault("night_aux_font", layout.get("night_font") or "bold")
    layout.setdefault("day_color_filter", 0)
    layout.setdefault("night_color_filter", 0)
    layout.setdefault("w", SCREEN_SIZE)
    layout.setdefault("h", SCREEN_SIZE)
    layout["version"] = SCREEN_LAYOUT_VERSION

    for mode in ("day", "night"):
        profile = layout["profiles"].get(mode)
        if not isinstance(profile, dict):
            raise ValueError(f"layout missing {mode} profile")
        if "scroll_text" not in profile:
            profile["scroll_text"] = DEFAULT_SCROLL_TEXT
        static = profile.setdefault("static_texts", {})
        for key, default in DEFAULT_STATIC_TEXTS.items():
            static.setdefault(key, default)
        elements = profile.setdefault("elements", [])
        for elem in elements:
            if elem and elem.get("id") == "glucose":
                elem["id"] = "time_aux"
        for elem_id in SCREEN_WIRE_ELEM_IDS:
            _ensure_element(profile, elem_id)

    return layout


def encode_screen_layout_binary(layout: dict[str, Any]) -> bytes:
    """Encode a prepared layout dict to the 3912-byte wire format."""
    layout = prepare_layout(layout)
    buf = bytearray(SCREEN_BIN_WIRE_SIZE)

    struct.pack_into("<I", buf, 0, SCREEN_BIN_MAGIC)
    buf[4] = SCREEN_BIN_FORMAT
    buf[5] = SCREEN_LAYOUT_VERSION
    buf[6] = int(layout.get("scroll_delay") or 65) & 0xFF
    buf[7] = int(layout.get("day_color_filter") or 0) & 0xFF
    buf[8] = int(layout.get("night_color_filter") or 0) & 0xFF
    _write_fixed_string(buf, 12, SCREEN_BIN_FONT_LEN, layout.get("day_font") or "bold")
    _write_fixed_string(buf, 24, SCREEN_BIN_FONT_LEN, layout.get("night_font") or "bold")
    _write_fixed_string(
        buf, 36, SCREEN_BIN_FONT_LEN, layout.get("day_aux_font") or layout.get("day_font") or "bold"
    )
    _write_fixed_string(
        buf,
        48,
        SCREEN_BIN_FONT_LEN,
        layout.get("night_aux_font") or layout.get("night_font") or "bold",
    )
    struct.pack_into("<H", buf, 60, int(layout.get("w") or SCREEN_SIZE))
    struct.pack_into("<H", buf, 62, int(layout.get("h") or SCREEN_SIZE))

    offset = SCREEN_BIN_HEADER_SIZE
    for mode in ("day", "night"):
        profile = layout["profiles"][mode]
        for elem_id in SCREEN_WIRE_ELEM_IDS:
            _write_widget(buf, offset, _find_element(profile, elem_id))
            offset += SCREEN_BIN_WIDGET_SIZE

        _write_fixed_string(buf, offset, SCREEN_BIN_SCROLL_LEN, profile.get("scroll_text") or "")
        offset += SCREEN_BIN_SCROLL_LEN

        static = profile.get("static_texts") or {}
        for slot_id in SCREEN_TEXT_SLOT_IDS:
            _write_fixed_string(buf, offset, SCREEN_BIN_STATIC_TEXT_LEN, static.get(slot_id) or "")
            offset += SCREEN_BIN_STATIC_TEXT_LEN
        _write_fixed_string(
            buf, offset, SCREEN_BIN_STATIC_TEXT_LEN, static.get("digit_label") or ""
        )
        offset += SCREEN_BIN_STATIC_TEXT_LEN
        _write_fixed_string(
            buf, offset, SCREEN_BIN_STATIC_TEXT_LEN, static.get("digit_label_aux") or ""
        )
        offset += SCREEN_BIN_STATIC_TEXT_LEN

        graph_elem = _find_element(profile, "graph")
        opts = (graph_elem or {}).get("options") or {}
        _write_graph_cfg(buf, offset, opts)
        offset += SCREEN_BIN_GRAPH_SIZE

    if offset != SCREEN_BIN_WIRE_SIZE:
        raise ValueError(f"screen wire size mismatch: wrote {offset}, expected {SCREEN_BIN_WIRE_SIZE}")
    return bytes(buf)


def decode_screen_layout_binary(data: bytes) -> dict[str, Any]:
    """Decode a 3912-byte wire blob into a layout dict."""
    if len(data) != SCREEN_BIN_WIRE_SIZE:
        raise ValueError(f"invalid screen wire size: {len(data)}")
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != SCREEN_BIN_MAGIC:
        raise ValueError("invalid screen wire magic")
    if data[4] != SCREEN_BIN_FORMAT:
        raise ValueError("unsupported screen wire format")

    layout: dict[str, Any] = {
        "version": data[5],
        "scroll_delay": data[6],
        "day_color_filter": data[7],
        "night_color_filter": data[8],
        "day_font": _read_fixed_string(data, 12, SCREEN_BIN_FONT_LEN),
        "night_font": _read_fixed_string(data, 24, SCREEN_BIN_FONT_LEN),
        "day_aux_font": _read_fixed_string(data, 36, SCREEN_BIN_FONT_LEN),
        "night_aux_font": _read_fixed_string(data, 48, SCREEN_BIN_FONT_LEN),
        "w": struct.unpack_from("<H", data, 60)[0],
        "h": struct.unpack_from("<H", data, 62)[0],
        "profiles": {},
    }

    offset = SCREEN_BIN_HEADER_SIZE
    for mode in ("day", "night"):
        profile, offset = _read_profile(data, offset)
        layout["profiles"][mode] = profile
    return layout


def _write_widget(buf: bytearray, offset: int, elem: dict[str, Any] | None) -> None:
    opts = (elem or {}).get("options") or {}
    fg = _hex_to_rgb(opts.get("color"), (255, 255, 255))
    bg = _hex_to_rgb(opts.get("bg_color"), (0, 0, 0))
    buf[offset] = 1 if elem and elem.get("enabled") else 0
    buf[offset + 1] = int((elem or {}).get("x") or 0) & 0xFF
    buf[offset + 2] = int((elem or {}).get("y") or 0) & 0xFF
    buf[offset + 3] = int((elem or {}).get("z") or 0) & 0xFF
    buf[offset + 4] = int(opts.get("font") or 0) & 0xFF
    buf[offset + 5] = int(opts.get("width") or 0) & 0xFF
    buf[offset + 6] = int(opts.get("align") or 0) & 0xFF
    buf[offset + 7], buf[offset + 8], buf[offset + 9] = fg
    buf[offset + 10], buf[offset + 11], buf[offset + 12] = bg


def _read_widget(data: bytes, offset: int) -> dict[str, int]:
    return {
        "enabled": 1 if data[offset] else 0,
        "x": data[offset + 1],
        "y": data[offset + 2],
        "z": data[offset + 3],
        "font": data[offset + 4],
        "width": data[offset + 5],
        "align": data[offset + 6],
        "color_r": data[offset + 7],
        "color_g": data[offset + 8],
        "color_b": data[offset + 9],
        "bg_r": data[offset + 10],
        "bg_g": data[offset + 11],
        "bg_b": data[offset + 12],
    }


def _write_graph_cfg(buf: bytearray, offset: int, opts: dict[str, Any]) -> None:
    def i16(value: Any) -> int:
        return GRAPH_VAL_UNSET if value is None else int(value)

    _write_fixed_string(buf, offset, SCREEN_BIN_GRAPH_TOKEN_LEN, opts.get("token") or "")
    struct.pack_into("<H", buf, offset + 64, int(opts.get("interval_min") or 5))
    buf[offset + 66] = int(opts.get("points") or 60) & 0xFF
    buf[offset + 67] = int(opts.get("gwidth") or 80) & 0xFF
    buf[offset + 68] = int(opts.get("gheight") or 36) & 0xFF

    flags = GRAPH_FLAG_BACKFILL
    if opts.get("autoscale"):
        flags |= GRAPH_FLAG_AUTOSCALE
    if opts.get("show_axis"):
        flags |= GRAPH_FLAG_SHOW_AXIS
    if opts.get("show_xaxis"):
        flags |= GRAPH_FLAG_SHOW_XAXIS
    if opts.get("band_on"):
        flags |= GRAPH_FLAG_BAND
    if opts.get("show_value"):
        flags |= GRAPH_FLAG_SHOW_VALUE
    if opts.get("boolean"):
        flags |= GRAPH_FLAG_BOOLEAN
    if opts.get("thick"):
        flags |= GRAPH_FLAG_THICK
    buf[offset + 69] = flags

    struct.pack_into("<h", buf, offset + 70, i16(opts.get("band_low")))
    struct.pack_into("<h", buf, offset + 72, i16(opts.get("band_high")))
    struct.pack_into("<h", buf, offset + 74, i16(opts.get("y_min")))
    struct.pack_into("<h", buf, offset + 76, i16(opts.get("y_max")))

    bc = _hex_to_rgb(opts.get("band_color"), (40, 60, 40))
    wc = _hex_to_rgb(opts.get("warn_color"), (255, 80, 80))
    ac = _hex_to_rgb(opts.get("axis_color"), (120, 120, 120))
    buf[offset + 78 : offset + 81] = bytes(bc)
    buf[offset + 81 : offset + 84] = bytes(wc)
    buf[offset + 84 : offset + 87] = bytes(ac)
    buf[offset + 87] = 0


def _read_graph_cfg(data: bytes, offset: int) -> dict[str, Any]:
    def i16(off: int) -> int | None:
        value = struct.unpack_from("<h", data, off)[0]
        return None if value == GRAPH_VAL_UNSET else value

    flags = data[offset + 69]
    return {
        "token": _read_fixed_string(data, offset, SCREEN_BIN_GRAPH_TOKEN_LEN),
        "interval_min": struct.unpack_from("<H", data, offset + 64)[0] or 5,
        "points": data[offset + 66] or 60,
        "gwidth": data[offset + 67] or 80,
        "gheight": data[offset + 68] or 36,
        "autoscale": bool(flags & GRAPH_FLAG_AUTOSCALE),
        "show_axis": bool(flags & GRAPH_FLAG_SHOW_AXIS),
        "show_xaxis": bool(flags & GRAPH_FLAG_SHOW_XAXIS),
        "band_on": bool(flags & GRAPH_FLAG_BAND),
        "show_value": bool(flags & GRAPH_FLAG_SHOW_VALUE),
        "boolean": bool(flags & GRAPH_FLAG_BOOLEAN),
        "thick": bool(flags & GRAPH_FLAG_THICK),
        "band_low": i16(offset + 70),
        "band_high": i16(offset + 72),
        "y_min": i16(offset + 74),
        "y_max": i16(offset + 76),
        "band_color": _rgb_to_hex(data[offset + 78], data[offset + 79], data[offset + 80]),
        "warn_color": _rgb_to_hex(data[offset + 81], data[offset + 82], data[offset + 83]),
        "axis_color": _rgb_to_hex(data[offset + 84], data[offset + 85], data[offset + 86]),
    }


def _read_profile(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    profile: dict[str, Any] = {
        "elements": [],
        "scroll_text": "",
        "static_texts": dict(DEFAULT_STATIC_TEXTS),
    }
    for elem_id in SCREEN_WIRE_ELEM_IDS:
        widget = _read_widget(data, offset)
        offset += SCREEN_BIN_WIDGET_SIZE
        elem: dict[str, Any] = {
            "id": elem_id,
            "enabled": widget["enabled"],
            "x": widget["x"],
            "y": widget["y"],
            "z": widget["z"],
        }
        if elem_id == "message" or elem_id.startswith("text_") or elem_id.startswith("digit_label"):
            elem["options"] = {
                "font": widget["font"],
                "color": _rgb_to_hex(widget["color_r"], widget["color_g"], widget["color_b"]),
                "bg_color": _rgb_to_hex(widget["bg_r"], widget["bg_g"], widget["bg_b"]),
                "width": widget["width"],
                "align": widget["align"],
            }
        elif elem_id == "graph":
            elem["options"] = {
                "color": _rgb_to_hex(widget["color_r"], widget["color_g"], widget["color_b"]),
                "bg_color": _rgb_to_hex(widget["bg_r"], widget["bg_g"], widget["bg_b"]),
            }
        profile["elements"].append(elem)

    profile["scroll_text"] = _read_fixed_string(data, offset, SCREEN_BIN_SCROLL_LEN)
    offset += SCREEN_BIN_SCROLL_LEN
    for slot_id in SCREEN_TEXT_SLOT_IDS:
        profile["static_texts"][slot_id] = _read_fixed_string(
            data, offset, SCREEN_BIN_STATIC_TEXT_LEN
        )
        offset += SCREEN_BIN_STATIC_TEXT_LEN
    profile["static_texts"]["digit_label"] = _read_fixed_string(
        data, offset, SCREEN_BIN_STATIC_TEXT_LEN
    )
    offset += SCREEN_BIN_STATIC_TEXT_LEN
    profile["static_texts"]["digit_label_aux"] = _read_fixed_string(
        data, offset, SCREEN_BIN_STATIC_TEXT_LEN
    )
    offset += SCREEN_BIN_STATIC_TEXT_LEN

    gcfg = _read_graph_cfg(data, offset)
    offset += SCREEN_BIN_GRAPH_SIZE
    for elem in profile["elements"]:
        if elem.get("id") == "graph":
            elem["options"] = {**(elem.get("options") or {}), **gcfg}
            break

    return profile, offset


def set_scroll_text(layout: dict[str, Any], text: str) -> None:
    """Set day and night scroll_text (display source of truth)."""
    text = text[: SCREEN_BIN_SCROLL_LEN - 1]
    for mode in ("day", "night"):
        profile = layout.setdefault("profiles", {}).setdefault(mode, {})
        profile["scroll_text"] = text


def set_widget_enabled(layout: dict[str, Any], elem_id: str, enabled: bool) -> None:
    """Enable/disable a widget in both day and night profiles."""
    for mode in ("day", "night"):
        profile = layout.setdefault("profiles", {}).setdefault(mode, {})
        elem = _ensure_element(profile, elem_id)
        elem["enabled"] = 1 if enabled else 0


def set_message_style(
    layout: dict[str, Any],
    *,
    color: str | None = None,
    night_color: str | None = None,
    font: int | None = None,
) -> None:
    """Update message widget style in day and/or night profiles."""
    for mode, color_value in (("day", color), ("night", night_color)):
        if color_value is None and font is None:
            continue
        profile = layout.setdefault("profiles", {}).setdefault(mode, {})
        elem = _ensure_element(profile, "message")
        opts = elem.setdefault("options", {})
        if mode == "day" and color is not None:
            opts["color"] = color
        if mode == "night" and night_color is not None:
            opts["color"] = night_color
        if font is not None:
            opts["font"] = int(font)


def get_scroll_text(layout: dict[str, Any] | None) -> str | None:
    """Return day-profile scroll text if present."""
    if not layout:
        return None
    profiles = layout.get("profiles") or {}
    day = profiles.get("day") or {}
    text = day.get("scroll_text")
    return str(text) if text is not None else None
