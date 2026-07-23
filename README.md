# Frixos Home Assistant Integration

A custom Home Assistant integration for controlling and monitoring Frixos devices.

**Requires firmware 70 (FW70) or later.** Older firmware (including early layout-engine builds) is not supported by this integration version.

## Firmware requirement (FW70)

Integration **1.1.2** targets current Frixos firmware (**fwversion ≥ 70**, marketing versions **2.52+**). FW70 migrated the device data partition from SPIFFS to **LittleFS** (still mounted at `/spiffs`), which unwedged OTA file updates and enables a reliable nested file listing via `/api/files`.

The **screen layout engine** (drag-and-drop widgets, day/night profiles, graphs, icons) landed earlier (around FW67). This HACS release assumes that stack is present **and** that you are on FW70+, so layout presets, `/api/screen` writes, and file discovery behave as on current devices.

Upgrade the clock through the device web UI (or auto-update) before installing or updating this integration.

## Layout engine and Home Assistant

The layout editor is too complex to rebuild inside Home Assistant.

Instead, this integration:

1. Lets you **switch layouts** via a **Layout Preset** select (device gallery `.layout` files such as Default, Diabetic, Weather, Home Assistant, HA Graph, plus any custom presets you save on the device).
2. Keeps **most of the older entity options** for compatibility with existing dashboards and automations.
3. Routes layout-owned fields (message text, message/weather visibility, fonts, color filters, scroll delay, etc.) through `/api/screen` so they still affect the display.

Design the layout on the device web UI; use Home Assistant to apply a saved preset and to tweak settings that still make sense from automations.

**Deprecated options:** Many of the legacy switches/numbers/selects/texts mirror the pre–layout-engine settings model. They are kept for compatibility but are **deprecated by the layout system** and may be removed in a future version. Prefer editing layouts on the device (and switching presets from HA) for anything about on-screen placement and styling.

**Removed options:** Some entities no longer worked under the layout engine and have been dropped, including **X Offset**, **Y Offset**, and **Scroll Speed** (widget positions and scrolling behavior live in the layout now). Entity order prefixes for remaining options are unchanged, so existing automations keep the same numeric labels.

## What's new in this integration

Compared with the previous HACS generation (FW62-era entities), this release adds:

| Setting | Type | Notes |
|--------|------|--------|
| **Layout Preset** | Select | Applies a root `.layout` file from the device gallery via `/api/screen` (same path as the device UI). |
| **Dim Mode** | Select | Replaces the old “Maintain Full Brightness” switch. Options: **Auto brightness**, **Full brightness**, **Time of day**. |
| **Dim Start Hour** / **Dim End Hour** | Number (0–23) | Used when Dim Mode is **Time of day**. |
| **Nightscout URL** | Text | Nightscout base URL for glucose (alongside Dexcom / Libre). |
| **Alternate Weather Display Duration** | Number (seconds) | How long the alternate weather digit mode runs (with Time / CGM alternates). |
| **Message Font Size** | Select | Now **8 / 10 / 12 / 14 / 16 pt** (layout message widget). |

Also updated for current firmware:

- Scrolling message, show message/weather, message colors, day/night fonts & color filters, and scroll delay write through the **layout engine** (`/api/screen`) instead of legacy settings-only paths.
- **PWM Frequency** range: 60–50000 Hz.
- **Glucose Data Validity Duration** and alternate display duration ranges aligned with current firmware.
- Default poll interval: **5 minutes** (with a short settle delay after writes).

## Features

- **Layout presets**: Apply ready-made or custom `.layout` files from the device without rebuilding the layout editor in HA
- **Compatibility entities**: Most previous switches, numbers, selects, and texts remain available (see deprecation note above)
- **Safe message updates**: Scrolling message and related layout-owned fields are written through `/api/screen`, not the legacy `p16`-only path
- **Monitoring**: Light level, uptime, and heap sensors
- **Polling**: Settings/status refresh every **5 minutes** by default (plus a short settle delay after writes)

## Supported Devices

All Frixos projection clocks (https://buyfrixos.com) running **firmware 70 or later**.

## Supported Entities

### Sensors (Diagnostic)
- Light Level (lux)
- Uptime
- Free Heap Memory
- Min Free Heap Memory

### Layout
- **Layout Preset** (select) — applies a `.layout` file from the device gallery (Default, Diabetic, Weather, Home Assistant, HA Graph, plus custom presets). Full widget placement stays on the device web UI.

### Switches (Configuration)
- Temperature in Fahrenheit
- 12-Hour Time Format
- Show Scrolling Message *(layout widget; deprecated as a standalone setting)*
- Show Weather Forecast *(layout widget; deprecated as a standalone setting)*
- Show Grid
- Mirror Display
- Show Leading Zero
- Auto Firmware Update
- Disable Breathing Time Dots

### Number Inputs (Configuration)
- Scroll Delay (30–255 ms, layout-owned; deprecated as a standalone setting)
- Light Sensitivity / Day Threshold
- LED Brightness Day / Night
- PWM Frequency (60–50000 Hz)
- Max Power
- WiFi Active Hours Start / End
- Home Assistant / Stock / Dexcom refresh intervals
- Glucose Data Validity Duration
- Alternate Time / CGM / Weather display durations
- High Glucose Threshold
- Dim Start Hour / Dim End Hour (used when Dim Mode is “Time of day”)

### Select Dropdowns (Configuration)
- Layout Preset
- Display Rotation
- Day / Night Font *(layout-owned; deprecated as a standalone setting)*
- Day / Night Color Filter *(layout-owned; deprecated as a standalone setting)*
- Message Font Size (8–16pt, layout-owned; deprecated as a standalone setting)
- Dim Mode (Auto brightness / Full brightness / Time of day)
- Dexcom Region / Libre Region / Language / Glucose Display Unit

### Color / Text Inputs (Configuration)
- Scrolling Message *(layout `scroll_text`; supports tokens like `[HA:…]`, `[temp]`, etc.)*
- Message Color Day / Night *(layout-owned; deprecated as a standalone setting)*
- Latitude / Longitude / Timezone
- Low Glucose Threshold
- Nightscout URL

## Settings Not Included in Home Assistant Integration

The following settings are available on the Frixos device but are **not currently exposed** as Home Assistant entities. These settings can still be configured directly through the device's web interface:

### Text Inputs (Not Implemented)
- **Hostname** - Device hostname (triggers device restart when changed)
- **Home Assistant URL** - URL for Home Assistant integration
- **Home Assistant Token** - Authentication token for Home Assistant integration (password field)
- **Stock API Key** - API key for stock price integration (password field)
- **Dexcom Username** - Username for Dexcom integration
- **Dexcom Password** - Password for Dexcom integration (password field)
- **WiFi SSID** - WiFi network name (triggers device restart when changed)
- **WiFi Password** - WiFi network password (password field, triggers device restart when changed)
- **Static IP / Gateway / Netmask / DNS** - Network addressing (triggers restart)
- **Digit / aux schedules (p58/p59)** - Complex JSON schedules; edit on the device UI

### Layout editor (device web UI only)
Full widget placement, graphs, static text slots, and user icons are edited on the device. Save layouts there, then use **Layout Preset** in Home Assistant to switch between them. X/Y offsets and scroll speed are no longer exposed in HA for the same reason.

### Notes on Unimplemented Settings

⚠️ **Security Settings**: Password fields (WiFi Password, Home Assistant Token, Stock API Key, Dexcom Password) are intentionally not exposed in the integration for security reasons. These should be configured directly through the device's web interface.

⚠️ **Network Settings**: Hostname and WiFi settings (SSID/Password) trigger device restarts and are typically configured during initial device setup. They are not included in the integration to prevent accidental disconnection.

⚠️ **Integration Credentials**: Home Assistant URL/Token and Dexcom credentials are device-specific integration settings that are typically configured once during setup. They can be managed through the device's web interface if needed.

## Installation

### Method 1: Manual Installation

1. **Access your Home Assistant installation**
   - If using Home Assistant OS/Supervised: Use SSH add-on or direct file system access
   - If using Home Assistant Core: Access the installation directory

2. **Navigate to the custom components directory**
   ```bash
   cd /config/custom_components
   ```
   
   Note: If the `custom_components` directory doesn't exist, create it:
   ```bash
   mkdir -p /config/custom_components
   ```

3. **Copy the integration folder**
   ```bash
   # Clone this repository
   git clone https://github.com/ArtLogicIKE/frixos-ha-integration.git
   
   # Copy the integration folder
   cp -r frixos-ha-integration/custom_components/frixos /config/custom_components/
   ```
   
   Or download and extract the ZIP file, then copy the `custom_components/frixos` folder.

4. **Set proper permissions** (if needed)
   ```bash
   chmod -R 755 /config/custom_components/frixos
   ```

5. **Restart Home Assistant**
   - Go to Settings → System → Hardware → Restart
   - Or restart from the terminal/SSH

### Method 2: Using HACS (Home Assistant Community Store)

**Note**: This requires the integration to be published in the HACS default repository. For now, use manual installation.

If/when published to HACS:

1. Install HACS if you haven't already (see [HACS documentation](https://hacs.xyz/docs/setup/download))
2. Go to HACS → Integrations
3. Click "Explore & Download Repositories"
4. Search for "Frixos"
5. Click "Download"
6. Restart Home Assistant

## Configuration

### Adding the Integration

1. **Open Home Assistant**
   - Go to Settings → Devices & Services
   - Click "Add Integration" button (bottom right)

2. **Search for Frixos**
   - Type "Frixos" in the search box
   - Select "Frixos" from the results

3. **Configure the device**
   - **Host**: Enter the IP address or hostname of your Frixos device (e.g., `frixos.local` or `192.168.1.100`)
   - **Port**: Enter the HTTP port (default: 80)
   - **Name**: Enter a friendly name for this device (default: "Frixos")

4. **Submit**
   - Click "Submit"
   - The integration will validate the connection
   - If successful, you'll see a confirmation message

### Multiple Devices

You can add multiple Frixos devices by repeating the configuration process. Each device will have its own set of entities.

## Usage

### Accessing Entities

Once configured, all entities will appear in Home Assistant:

- **Sensors**: Settings → Devices & Services → Sensors (Diagnostic section)
- **Switches**: Settings → Devices & Services → Switches (Configuration section)
- **Numbers**: Settings → Devices & Services → Numbers (Configuration section)
- **Selects**: Settings → Devices & Services → Selects (Configuration section)
- **Texts**: Settings → Devices & Services → Texts (Configuration section)

All configuration entities are organized with numeric prefixes (e.g., "1.01", "2.01", "3.01") that match the UI page structure:
- **Page 1 (Basic)**: Basic settings + Layout Preset
- **Page 2 (Layout / Display)**: Display, brightness, message, location
- **Page 3 (Integration)**: Home Assistant, Stock, Dexcom, Libre, Nightscout, glucose

Or use the search bar to find specific entities by name.

### Automations

You can create automations using Frixos entities:

```yaml
# Example: Apply the Diabetic layout at night
automation:
  - alias: "Frixos Diabetic layout overnight"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.<host>_layout_preset
        data:
          option: Diabetic

# Example: Adjust brightness based on light level
automation:
  - alias: "Frixos Auto Brightness"
    trigger:
      - platform: numeric_state
        entity_id: sensor.light_level
        below: 20
    action:
      - service: number.set_value
        target:
          entity_id: number.led_brightness_night
        data:
          value: 30
```

### Scrolling Message Tokens

When setting the scrolling message, you can use tokens that the device will replace:

- `[device]` - Device name
- `[greeting]` - Time-based greeting
- `[day]` - Current day of the week
- `[date]` - Current date
- `[mon]` - Current month
- `[temp]` - Current temperature
- `[hum]` - Current humidity
- `[high]` - Today's high temperature
- `[low]` - Today's low temperature
- `[rise]` - Sunrise time
- `[set]` - Sunset time
- `[HA:entity_id:path]` - Fetch from Home Assistant (requires HA integration enabled on device)
- `[$:symbol]` - Stock price (requires stock integration enabled)

### Important Notes

⚠️ **Firmware 70 required**: This integration version expects FW70+. After upgrading from SPIFFS-era firmware, the device may reformat the data partition once and re-download files (self-heal) before the web UI and layout presets are fully available.

⚠️ **Layout engine vs Home Assistant**: The layout editor is device-only. HA switches presets and keeps many legacy options for compatibility; those layout-adjacent entities are deprecated and may go away later. Prefer presets + the device UI for display design.

⚠️ **Layout-owned settings**: Message text, message visibility/style, weather icon visibility, day/night fonts, color filters, and scroll delay live in the **screen layout**. This integration updates those via `/api/screen` when you change the corresponding entities.

⚠️ **Device Restart**: Network settings (hostname, WiFi, static IP) trigger a device restart. Latitude/longitude/timezone no longer force a reboot on current firmware.

⚠️ **Polling Interval**: The integration polls the device every **5 minutes** by default. After writes it waits briefly before refreshing so the device can finish layout/integration work.

⚠️ **Message updates & device stability**: Older integration versions posted only `{"p16": "..."}`. That updated a legacy NVS string but **not** `layout.scroll_text` (what the display actually renders), and it ran a **synchronous** `parse_integrations()` on the HTTP task while holding shared buffers. Repeated message sets from Home Assistant could therefore look like “nothing changed” while still stressing heap and eventually locking up the device. Current releases write messages through `/api/screen` instead (same path as the device web UI), serialize writes, retry HTTP 503 “busy”, and settle before polling again.

## Troubleshooting

### Integration Not Showing Up

1. **Check file structure**: Ensure the `frixos` folder is directly in `custom_components/`
2. **Check permissions**: Files should be readable
3. **Check logs**: Look in Settings → System → Logs for errors
4. **Restart**: Make sure you've restarted Home Assistant after installation

### Cannot Connect to Device

1. **Verify network connectivity**: Ensure Home Assistant can reach the Frixos device
   ```bash
   ping frixos.local
   # or
   ping 192.168.1.100
   ```

2. **Check device IP/hostname**: Ensure the hostname or IP address is correct
3. **Check port**: Verify the port (default is 80)
4. **Check device web UI**: Try accessing the device's web interface directly in a browser
5. **Check firewall**: Ensure no firewall is blocking the connection

### Settings Not Updating

1. **Check device logs**: Some settings may require device restart
2. **Check integration logs**: Look for errors in Home Assistant logs
3. **Verify API response**: Check if `/api/settings` endpoint is accessible
4. **Layout fields**: Message / fonts / filters / scroll delay need a successful `/api/screen` write (FW70+ with the layout engine)
5. **Firmware**: Confirm the device reports fwversion ≥ 70 in its status / web UI

### Entity States Show as "Unknown"

1. **Wait for initial update**: The integration needs to fetch data on first load
2. **Check device connectivity**: Ensure the device is reachable
3. **Check coordinator logs**: Look for errors in the data update process

### Device becomes slow or crashes after setting the message

1. Update to integration **1.1.2+** and firmware **70+** (layout-safe message path)
2. Avoid rapid-fire automations that rewrite the message every few seconds
3. Prefer fewer `[HA:…]` tokens if free heap is low after boot
4. Watch `sensor.*_free_heap` / `min_free_heap` while reproducing

## Development

### File Structure

```
custom_components/frixos/
├── __init__.py          # Main integration setup
├── config_flow.py       # Configuration UI
├── const.py             # Constants and parameter mappings
├── coordinator.py       # Data update coordinator
├── entity.py            # Base entity class
├── manifest.json        # Integration metadata
├── icon.png             # Integration icon
├── screen_layout.py     # Screen layout wire encode/decode (presets + message)
├── sensor.py            # Sensor entities
├── switch.py            # Switch entities
├── number.py            # Number entities
├── select.py            # Select entities (incl. layout presets)
├── text.py              # Text entities
└── strings.json         # UI strings
```

### API Endpoints

The integration uses the following endpoints:

- `GET /api/settings` - Retrieve device settings (`pXX`)
- `POST /api/settings` - Update non-layout settings (JSON payload)
- `GET /api/status` - Retrieve device status and sensor data (includes `fwversion`)
- `GET /api/files` - List files on the device filesystem (LittleFS on FW70+; used to discover `.layout` presets)
- `GET /{name}.layout` - Fetch a layout JSON preset from the device
- `GET /api/screen` - Current screen layout (3912-byte binary wire format)
- `POST /api/screen` - Apply a screen layout (same binary format the device web UI uses)

### Contributing

To contribute improvements:

1. Fork the repository
2. Make your changes
3. Test thoroughly with your Frixos device
4. Submit a pull request

## Support

For issues or questions:

1. Check this README and troubleshooting section
2. Check device logs in Home Assistant (Settings → System → Logs)
3. Open an issue on the GitHub repository
4. Contact Frixos support at support@buyfrixos.com

## License

This integration is provided as-is for use with Frixos devices.

## Changelog

### Version 1.1.2
- Requires **firmware 70 (FW70)+**
- Docs: layout engine is device-only; HA switches presets instead of rebuilding the editor
- Docs: most legacy entities kept for compatibility but deprecated; may be removed later
- Documented new settings: Layout Preset, Dim Mode, Dim Start/End, Nightscout URL, alternate weather duration, expanded message font sizes
- Removed non-working X Offset, Y Offset, and Scroll Speed entities (order prefixes for remaining entities unchanged)
- Fix Layout Preset apply when the device serves `.layout` without a JSON Content-Type

### Version 1.1.1
- Version bump for release

### Version 1.1.0
- Layout Preset select (applies device `.layout` gallery via `/api/screen`)
- Scrolling message, show message/weather, message colors/font, day/night fonts & filters, and scroll delay write through the layout engine
- Avoid legacy `p16`-only message updates that could stress/crash the device
- Serialized device writes, HTTP 503 busy retries, post-write settle delay
- Dim Mode select (replaces Maintain Full Brightness switch); dim start/end hours
- Nightscout URL, alternate weather duration
- Message font sizes 8–16pt; PWM / glucose validity ranges aligned with current firmware
- Docs: 5-minute poll interval; layout engine notes

### Version 1.0.4
- Updated PWM Frequency range to 10-78000 Hz
- Updated Alternate Time Display Duration range to 0-300 seconds
- Updated Alternate CGM Display Duration range to 0-300 seconds

### Version 1.0.0
- Initial release
- Full settings control via Home Assistant entities
- Real-time sensor monitoring
- Support for all device parameters
- Entity categories for better organization
- Numeric prefixes (page.order) for entity organization matching UI structure
- Support for all configuration pages: Basic, Advanced, and Integration settings
- Complete glucose monitoring integration (Dexcom, Libre, thresholds, units)
- WiFi active hours scheduling
- Alternate display duration controls

### Version 1.0.3
- minor bufixes
