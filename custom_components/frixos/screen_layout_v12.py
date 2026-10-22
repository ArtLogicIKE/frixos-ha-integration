"""Screen layout wire format of firmware with text widgets (layout version 12, ext version 5).

The device sends 7170 bytes: a 64-byte header, two 795-byte profiles (15 fixed elements, the
scroll text and the graph) and a text-widget section (eight widgets per profile plus their
editor names). Home Assistant only edits a few fields, so it keeps the bytes it read and
patches them in place; presets (.layout JSON from the device) are encoded in full.
"""
from __future__ import annotations

import struct
from typing import Any

LAYOUT_VERSION = 12
HEADER_SIZE = 64
WIDGET_SIZE = 13
SCROLL_LEN = 512
GRAPH_SIZE = 88
ELEM_IDS = [
    "glucose_level", "glucose_trend", "wifi_off", "weather", "moon", "message", "graph",
    "icon_1", "icon_2", "icon_3", "icon_4", "icon_5", "icon_6", "icon_7", "icon_8",
]
PROFILE_SIZE = len(ELEM_IDS) * WIDGET_SIZE + SCROLL_LEN + GRAPH_SIZE
BASE_SIZE = HEADER_SIZE + 2 * PROFILE_SIZE

EXT_MAGIC = 0x54585346
EXT_VERSION = 5
EXT_HEADER_SIZE = 8
TW_IDS = [f"tw_{i}" for i in range(1, 9)]
TW_SLOTS = 3
TW_HEAD_SIZE = 24
TW_TEXT_LEN = 96
TW_SIZE = TW_HEAD_SIZE + TW_SLOTS * TW_TEXT_LEN
ICON_IDS = [f"icon_{i}" for i in range(1, 9)]
INSTANCE_IDS = TW_IDS + ICON_IDS
NAME_LEN = 16
META_SIZE = 2 * 2 + 2 * len(INSTANCE_IDS) * NAME_LEN
EXT_SIZE = EXT_HEADER_SIZE + 2 * len(TW_IDS) * TW_SIZE + META_SIZE
WIRE_SIZE = BASE_SIZE + EXT_SIZE

FLAG_SHOW_UNITS = 0x01
FLAG_TABULAR = 0x02
FLAG_TRANSPARENT = 0x04
FLAG_COLOR_OVERRIDE = 0x08
FLAG_SCROLL = 0x10
DURATION_DEFAULT = 10
THEME_COUNT = 12

# Legacy message font index (0..4, p13) <-> scroll widget pixel size.
MSG_FONT_SIZES = [8, 10, 12, 14, 16]

assert PROFILE_SIZE == 795 and BASE_SIZE == 1654 and TW_SIZE == 312 and WIRE_SIZE == 7170


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


def _clamp_utf8(text: str, max_bytes: int) -> bytes:
    """UTF-8 bytes of the longest prefix of text that fits, never cutting a character."""
    out = bytearray()
    for ch in text or "":
        enc = ch.encode("utf-8", errors="replace")
        if len(out) + len(enc) > max_bytes:
            break
        out += enc
    return bytes(out)


def _write_string(buf: bytearray, offset: int, length: int, value: str | None) -> None:
    buf[offset : offset + length] = b"\x00" * length
    enc = _clamp_utf8(value or "", length - 1)
    buf[offset : offset + len(enc)] = enc


def _read_string(data: bytes, offset: int, length: int) -> str:
    chunk = bytes(data[offset : offset + length])
    end = chunk.find(b"\x00")
    return chunk[: end if end >= 0 else length].decode("utf-8", errors="replace")


def is_v12_wire(data: bytes) -> bool:
    """True for a full text-widget wire this module can edit."""
    return (
        len(data) == WIRE_SIZE
        and struct.unpack_from("<I", data, 0)[0] == 0x4653584C
        and data[5] >= LAYOUT_VERSION
        and struct.unpack_from("<IBBH", data, BASE_SIZE) == (EXT_MAGIC, EXT_VERSION, len(TW_IDS), TW_SIZE)
    )


def _profile_offset(p: int) -> int:
    return HEADER_SIZE + p * PROFILE_SIZE


def _tw_offset(p: int, i: int) -> int:
    return BASE_SIZE + EXT_HEADER_SIZE + (p * len(TW_IDS) + i) * TW_SIZE


def _meta_offset() -> int:
    return BASE_SIZE + EXT_HEADER_SIZE + 2 * len(TW_IDS) * TW_SIZE


def _scroll_widget(wire: bytes, p: int) -> int | None:
    for i in range(len(TW_IDS)):
        if wire[_tw_offset(p, i) + 8] & FLAG_SCROLL:
            return i
    return None


# ------------------------------------------------------------------ decode (summary view)

def decode(data: bytes) -> dict[str, Any]:
    """Summary of a v12 wire in the shape the rest of the integration reads, plus the raw bytes.

    Only the fields Home Assistant shows are decoded; "_wire" keeps everything else intact.
    """
    wire = bytearray(data)
    layout: dict[str, Any] = {
        "version": wire[5],
        "scroll_delay": wire[6],
        "day_color_filter": wire[7],
        "night_color_filter": wire[8],
        "day_font": _read_string(wire, 12, 12),
        "night_font": _read_string(wire, 24, 12),
        "day_aux_font": _read_string(wire, 36, 12),
        "night_aux_font": _read_string(wire, 48, 12),
        "w": struct.unpack_from("<H", wire, 60)[0],
        "h": struct.unpack_from("<H", wire, 62)[0],
        "profiles": {},
        "_wire": wire,
    }
    for p, mode in enumerate(("day", "night")):
        layout["profiles"][mode] = _profile_view(wire, p)
    return layout


def _profile_view(wire: bytes, p: int) -> dict[str, Any]:
    base = _profile_offset(p)
    weather = wire[base + ELEM_IDS.index("weather") * WIDGET_SIZE]
    message: dict[str, Any] = {"id": "message", "enabled": 0, "options": {}}
    i = _scroll_widget(wire, p)
    if i is not None:
        o = _tw_offset(p, i)
        flags = wire[o + 8]
        size = wire[o + 7]
        color = _rgb_to_hex(*wire[o + 10 : o + 13]) if flags & FLAG_COLOR_OVERRIDE else "#FFFFFF"
        font = min(range(len(MSG_FONT_SIZES)), key=lambda k: abs(MSG_FONT_SIZES[k] - size))
        message = {"id": "message", "enabled": wire[o], "options": {"color": color, "font": font}}
    return {
        "scroll_text": _read_string(wire, base + len(ELEM_IDS) * WIDGET_SIZE, SCROLL_LEN),
        "elements": [{"id": "weather", "enabled": weather}, message],
    }


def _refresh_view(layout: dict[str, Any]) -> None:
    for p, mode in enumerate(("day", "night")):
        layout["profiles"][mode] = _profile_view(layout["_wire"], p)


# ------------------------------------------------------------------ in-place edits

def set_scroll_text(layout: dict[str, Any], text: str) -> None:
    wire = layout["_wire"]
    for p in range(2):
        _write_string(wire, _profile_offset(p) + len(ELEM_IDS) * WIDGET_SIZE, SCROLL_LEN, text)
    _refresh_view(layout)


def _ensure_scroll_widget(wire: bytearray, p: int) -> int:
    i = _scroll_widget(wire, p)
    if i is not None:
        return i
    meta = _meta_offset()
    instanced = struct.unpack_from("<H", wire, meta + 2 * p)[0]
    free = [k for k in range(len(TW_IDS)) if not (instanced >> k) & 1 and not wire[_tw_offset(p, k)]]
    if not free:
        raise ValueError("all text widgets are in use; add the scroll text in the screen editor")
    i = free[0]
    o = _tw_offset(p, i)
    wire[o : o + TW_SIZE] = b"\x00" * TW_SIZE
    # Same place and style as the bundled Default layout's scroll text.
    wire[o : o + 16] = bytes([0, 0, 82, 0, 128, 0, 0, 10, FLAG_SHOW_UNITS | FLAG_SCROLL, 1,
                              255, 255, 255, 0, 0, 0])
    struct.pack_into("<HHH", wire, o + 16, DURATION_DEFAULT, DURATION_DEFAULT, DURATION_DEFAULT)
    struct.pack_into("<H", wire, meta + 2 * p, instanced | (1 << i))
    _write_string(wire, meta + 4 + (p * len(INSTANCE_IDS) + i) * NAME_LEN, NAME_LEN, "Scroll")
    return i


def set_widget_enabled(layout: dict[str, Any], elem_id: str, enabled: bool) -> None:
    wire = layout["_wire"]
    for p in range(2):
        if elem_id == "message":
            i = _ensure_scroll_widget(wire, p) if enabled else _scroll_widget(wire, p)
            if i is not None:
                wire[_tw_offset(p, i)] = 1 if enabled else 0
        elif elem_id in ELEM_IDS:
            wire[_profile_offset(p) + ELEM_IDS.index(elem_id) * WIDGET_SIZE] = 1 if enabled else 0
    _refresh_view(layout)


def set_message_style(
    layout: dict[str, Any], *, color: str | None = None, night_color: str | None = None, font: int | None = None
) -> None:
    wire = layout["_wire"]
    for p, color_value in ((0, color), (1, night_color)):
        if color_value is None and font is None:
            continue
        i = _ensure_scroll_widget(wire, p)
        o = _tw_offset(p, i)
        if color_value is not None:
            wire[o + 10 : o + 13] = bytes(_hex_to_rgb(color_value, (255, 255, 255)))
            wire[o + 8] |= FLAG_COLOR_OVERRIDE
        if font is not None:
            wire[o + 7] = MSG_FONT_SIZES[max(0, min(int(font), len(MSG_FONT_SIZES) - 1))]
    _refresh_view(layout)


def encode(layout: dict[str, Any]) -> bytes:
    """The edited wire, with the header fields Home Assistant may have changed."""
    wire = layout["_wire"]
    wire[6] = max(30, min(255, int(layout.get("scroll_delay") or 60)))
    wire[7] = int(layout.get("day_color_filter") or 0) & 0xFF
    wire[8] = int(layout.get("night_color_filter") or 0) & 0xFF
    _write_string(wire, 12, 12, layout.get("day_font") or "bold")
    _write_string(wire, 24, 12, layout.get("night_font") or "light")
    return bytes(wire)


# ------------------------------------------------------------------ presets (.layout JSON)

def is_v12_layout_json(layout: dict[str, Any]) -> bool:
    """True for a .layout file saved by the text-widget editor."""
    if int(layout.get("version") or 0) >= 11:
        return True
    for profile in (layout.get("profiles") or {}).values():
        for elem in (profile or {}).get("elements") or []:
            if elem and str(elem.get("id", "")).startswith("tw_"):
                return True
    return False


def _find(profile: dict[str, Any], elem_id: str) -> dict[str, Any] | None:
    for elem in profile.get("elements") or []:
        if elem and elem.get("id") == elem_id:
            return elem
    return None


def _write_widget(buf: bytearray, off: int, elem: dict[str, Any] | None) -> None:
    opts = (elem or {}).get("options") or {}
    fg = _hex_to_rgb(opts.get("color"), (255, 255, 255))
    bg = _hex_to_rgb(opts.get("bg_color"), (0, 0, 0))
    buf[off : off + WIDGET_SIZE] = bytes([
        1 if elem and elem.get("enabled") else 0,
        int((elem or {}).get("x") or 0) & 0xFF,
        int((elem or {}).get("y") or 0) & 0xFF,
        int((elem or {}).get("z") or 0) & 0xFF,
        int(opts.get("font") or 0) & 0xFF,
        int(opts.get("width") or 0) & 0xFF,
        int(opts.get("align") or 0) & 0xFF,
        *fg, *bg,
    ])


def encode_layout_json(layout: dict[str, Any], write_graph_cfg) -> bytes:
    """Encode a text-widget .layout JSON exactly as the device's screen editor does."""
    buf = bytearray(WIRE_SIZE)
    struct.pack_into("<IBB", buf, 0, 0x4653584C, 1, LAYOUT_VERSION)
    buf[6] = int(layout.get("scroll_delay") if layout.get("scroll_delay") is not None else 60) & 0xFF
    buf[7] = int(layout.get("day_color_filter") or 0) & 0xFF
    buf[8] = int(layout.get("night_color_filter") or 0) & 0xFF
    profiles = layout["profiles"]
    for k, mode in ((9, "day"), (10, "night")):
        try:
            theme = int(profiles[mode].get("weather_theme") or 0)
        except (TypeError, ValueError):
            theme = 0
        buf[k] = max(0, min(THEME_COUNT, theme))
    _write_string(buf, 12, 12, layout.get("day_font") or "bold")
    _write_string(buf, 24, 12, layout.get("night_font") or "light")
    _write_string(buf, 36, 12, layout.get("day_aux_font") or layout.get("day_font") or "bold")
    _write_string(buf, 48, 12, layout.get("night_aux_font") or layout.get("night_font") or "light")
    struct.pack_into("<HH", buf, 60, int(layout.get("w") or 128), int(layout.get("h") or 128))

    for p, mode in enumerate(("day", "night")):
        profile = profiles[mode]
        off = _profile_offset(p)
        for elem_id in ELEM_IDS:
            _write_widget(buf, off, _find(profile, elem_id))
            off += WIDGET_SIZE
        _write_string(buf, off, SCROLL_LEN, profile.get("scroll_text") or "")
        off += SCROLL_LEN
        graph = _find(profile, "graph")
        write_graph_cfg(buf, off, (graph or {}).get("options") or {})

    struct.pack_into("<IBBH", buf, BASE_SIZE, EXT_MAGIC, EXT_VERSION, len(TW_IDS), TW_SIZE)
    meta = _meta_offset()
    for p, mode in enumerate(("day", "night")):
        profile = profiles[mode]
        for i, tw_id in enumerate(TW_IDS):
            elem = _find(profile, tw_id) or {}
            opts = elem.get("options") or {}
            slots = [s if isinstance(s, dict) else {} for s in (opts.get("slots") or [{}])][:TW_SLOTS]
            fg = _hex_to_rgb(opts.get("color"), (255, 255, 255))
            bg = _hex_to_rgb(opts.get("bg_color"), (0, 0, 0))
            color_enabled = opts.get("color_enabled")
            if color_enabled is None:
                color_enabled = (opts.get("color") or "#ffffff").lower() != "#ffffff"
            flags = ((FLAG_SHOW_UNITS if opts.get("show_units", True) else 0)
                     | (FLAG_TABULAR if opts.get("tabular", True) else 0)
                     | (FLAG_TRANSPARENT if opts.get("transparent") else 0)
                     | (FLAG_COLOR_OVERRIDE if color_enabled else 0)
                     | (FLAG_SCROLL if opts.get("scroll") else 0))
            o = _tw_offset(p, i)
            head = [1 if elem.get("enabled") else 0, int(elem.get("x", 4) or 0), int(elem.get("y", 4) or 0),
                    int(elem.get("z", 2) or 0), int(opts.get("width") or 0), int(opts.get("align") or 0),
                    int(opts.get("family") or 0), int(opts.get("size") or 16), flags, len(slots), *fg, *bg]
            buf[o : o + 16] = bytes(v & 0xFF for v in head)
            for s in range(TW_SLOTS):
                slot = slots[s] if s < len(slots) else None
                duration = int(slot.get("duration") or DURATION_DEFAULT) if slot else DURATION_DEFAULT
                struct.pack_into("<H", buf, o + 16 + s * 2, duration)
                _write_string(buf, o + TW_HEAD_SIZE + s * TW_TEXT_LEN, TW_TEXT_LEN, (slot or {}).get("text") or "")
        mask = 0
        for i, inst_id in enumerate(INSTANCE_IDS):
            elem = _find(profile, inst_id)
            if elem and (elem.get("instanced") or elem.get("enabled")):
                mask |= 1 << i
            _write_string(buf, meta + 4 + (p * len(INSTANCE_IDS) + i) * NAME_LEN, NAME_LEN,
                          (elem or {}).get("name") or "")
        struct.pack_into("<H", buf, meta + 2 * p, mask)
    return bytes(buf)
