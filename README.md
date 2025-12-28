# Frixos Home Assistant Integration

A custom Home Assistant integration for controlling and monitoring Frixos devices.

## Features

- **Full Settings Control**: Access and modify all device settings through Home Assistant entities
- **Real-time Monitoring**: Monitor device status, sensor readings, and system information
- **Automatic Updates**: Settings and sensor data are automatically refreshed every 60 seconds
- **User-Friendly UI**: All settings are properly categorized as switches, numbers, selects, and text inputs

## Supported Entities

### Sensors (Diagnostic)
- Light Level (lux)
- Uptime
- Free Heap Memory
- Min Free Heap Memory

### Switches (Configuration)
- Temperature in Fahrenheit
- 12-Hour Time Format
- Show Scrolling Message
- Show Weather Forecast
- Show Grid
- Mirror Display
- Maintain Full Brightness
- Show Leading Zero
- Auto Firmware Update

### Number Inputs (Configuration)
- X Offset (0-160)
- Y Offset (0-160)
- Scroll Delay (30-500 ms)
- Light Sensitivity (0-50 lux)
- Day Threshold (0-500 lux)
- LED Brightness Day (1-100%)
- LED Brightness Night (1-100%)
- PWM Frequency (10-5000 Hz)
- Max Power (1-1023)
- Home Assistant Refresh Interval (1-7200 min)
- Stock Refresh Interval (1-1440 min)
- Dexcom Refresh Interval (1-60 min)

### Select Dropdowns (Configuration)
- Display Rotation (0°, 90°, 180°, 270°)
- Day Font (bold, light, lcd, nixie, etc.)
- Night Font (same options)
- Day Color Filter (None, Red, Green, Blue, B&W)
- Night Color Filter (same options)
- Message Font Size (8pt, 10pt, 12pt)
- Dexcom Region (Disabled, US, Japan, Rest of World)
- Language (English, Deutsch, Français, etc.)

### Color Pickers (Configuration)
- Message Color (Day) - RGB color picker for scrolling messages during day
- Message Color (Night) - RGB color picker for scrolling messages during night

### Text Inputs (Configuration)
- Scrolling Message (supports tokens like [HA:entity:path], [temp], etc.)
- Latitude
- Longitude
- Timezone (POSIX format, e.g., "EET-2EEST,M3.5.0/3,M10.5.0/4")

## Settings Not Included in Home Assistant Integration

The following settings are available on the Frixos device but are **not currently exposed** as Home Assistant entities. These settings can still be configured directly through the device's web interface:

### Switches (Not Implemented)
- **Dark Theme** - Enable dark theme for the device display

### Number Inputs (Not Implemented)
- **Scroll Speed** - Control the scrolling speed of messages (separate from scroll delay)

### Text Inputs (Not Implemented)
- **Hostname** - Device hostname (triggers device restart when changed)
- **Home Assistant URL** - URL for Home Assistant integration
- **Home Assistant Token** - Authentication token for Home Assistant integration (password field)
- **Stock API Key** - API key for stock price integration (password field)
- **Dexcom Username** - Username for Dexcom integration
- **Dexcom Password** - Password for Dexcom integration (password field)
- **WiFi SSID** - WiFi network name (triggers device restart when changed)
- **WiFi Password** - WiFi network password (password field, triggers device restart when changed)

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
   git clone https://github.com/yourusername/frixos-ha-integration.git
   
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

Or use the search bar to find specific entities by name.

### Automations

You can create automations using Frixos entities:

```yaml
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

⚠️ **Device Restart**: Some settings trigger a device restart:
- Latitude/Longitude
- Timezone

When changing these settings, the device will restart and become temporarily unavailable.

⚠️ **Polling Interval**: The integration polls the device every 60 seconds by default. This can be adjusted in `coordinator.py` if needed.

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

### Entity States Show as "Unknown"

1. **Wait for initial update**: The integration needs to fetch data on first load
2. **Check device connectivity**: Ensure the device is reachable
3. **Check coordinator logs**: Look for errors in the data update process

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
├── sensor.py            # Sensor entities
├── switch.py            # Switch entities
├── number.py            # Number entities
├── select.py            # Select entities
├── text.py              # Text entities
└── strings.json         # UI strings
```

### API Endpoints

The integration uses the following endpoints:

- `GET /api/settings` - Retrieve all device settings
- `POST /api/settings` - Update device settings (JSON payload)
- `GET /api/status` - Retrieve device status and sensor data

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

### Version 1.0.0
- Initial release
- Full settings control via Home Assistant entities
- Real-time sensor monitoring
- Support for all device parameters
- Entity categories for better organization
- Clean entity names without "Frixos" prefix

