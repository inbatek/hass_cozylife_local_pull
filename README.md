# CozyLife & Home Assistant

CozyLife Assistant integration for controlling CozyLife devices using local network, with improvements and energy storage support.

## Supported Device Types

- **RGBCW Light** - Full color + white control with optimized performance
- **CW Light** - Color temperature adjustable white lights
- **Switch & Plug** - Simple on/off control
- **Energy Storage** (NEW!) - Power stations with AC/DC outputs, LED lamp, battery monitoring

## Installation

### 1. Install the Integration

Clone this repo to your Home Assistant custom_components directory:

```bash
cd /config/custom_components
git clone https://github.com/inbatek/hass_cozylife_local_pull.git
```

### 2. Discover Your Devices

Use the network scanner to find CozyLife devices on your network:

```bash
cd hass_cozylife_local_pull
python3 scan_cozylife.py 192.168.1.0/24
```

**Scan options:**
- CIDR notation: `python3 scan_cozylife.py 192.168.1.0/24`
- IP range: `python3 scan_cozylife.py 192.168.1.100-192.168.1.200`
- Single IP: `python3 scan_cozylife.py 192.168.1.50`

The scanner will output a ready-to-use configuration block.

### 3. Configure

Add the generated configuration to your `configuration.yaml`:

```yaml
hass_cozylife_local_pull:
  lang: en
  devices:
    - serial_number: 767941640050c2edda8b
      alias: Living Room Light
      ip: 192.168.1.101
    - serial_number: 73034068e4b063351fe0
      alias: Garage Power Station
      ip: 192.168.1.103
```

**Configuration options:**
- `lang`: Language for device models (en, zh, es, pt, ja, ru, nl, ko, fr, de)
- `devices`: List of devices with serial numbers, friendly aliases, and IPs
- Legacy `ip` list format still supported (see `configuration_example.yaml`)

### 4. Restart Home Assistant

Restart HA to load the integration. Your devices will appear as entities.

## Device Features

### Lights
- Optimized for high-frequency updates (Ambilight/HyperHDR ready)
- Async operations with optimistic updates
- Full RGB + white + color temperature control
- No polling - instant response

### Energy Storage Devices
Entities created for each device:
- **3 Switches**: AC Output, LED Lamp, DC 12V Output (independent control)
- **1 Select**: LED Mode (Low/High/SOS brightness)
- **5 Sensors**:
  - Battery Percentage
  - Output Power (W)
  - Input Power (W) - shows charging status
  - Time Remaining (minutes until empty)
  - Battery Capacity (Wh)

## Advanced Configuration

### Network Requirements
- Devices must be on **2.4 GHz WiFi** (5 GHz not supported by CozyLife devices)
- Disable router "Client Isolation" or "AP Isolation" if enabled
- Recommended: Assign static IP addresses to devices via DHCP reservation

### UDP Discovery (Legacy)
Automatic UDP broadcast discovery is supported but not recommended:
```yaml
hass_cozylife_local_pull:
  lang: en
  # No devices/ip specified = UDP discovery only
```

**Note**: UDP discovery requires router support and can be unreliable. Device-based configuration is preferred.

## Troubleshooting

### Devices Not Found
- Ensure devices are powered on and connected to WiFi
- Check that you're scanning the correct IP range
- Verify router allows connections to port 5555
- Disable network isolation on router

### Lights Not Responding
- Weak WiFi signal - CozyLife devices have weak antennas
- Ensure strong 2.4 GHz signal at device location
- Consider separate 2.4 GHz SSID to prevent band steering issues

### State Out of Sync
- Light platform uses optimistic updates (no polling)
- Won't detect changes made via CozyLife app
- Control through Home Assistant to resync state

### Connection Issues
- TCP reconnection is automatic but takes 60 seconds between retries
- Check Home Assistant logs for specific errors
- Verify devices respond: `telnet <device-ip> 5555`

## Technical Details

### Communication Protocol
- **Discovery**: UDP broadcast on port 6095
- **Control**: TCP on port 5555
- **Format**: JSON messages with CRLF terminators
- **Commands**: CMD_INFO (0), CMD_QUERY (2), CMD_SET (3)

### Performance Optimizations
- Lights use async/await with optimistic updates
- No polling - eliminates constant state queries
- Concurrent device connections on startup
- Suitable for rapid update scenarios (Ambilight)

### Energy Storage Protocol
Energy devices use a bitmask for independent output control (DPID 1):
- Bit 0 (value & 1): AC output
- Bit 1 (value & 2): LED lamp
- Bit 2 (value & 4): DC 12V output

Example: Value 7 (binary 111) = all outputs on

## Compatibility

**✅ Home Assistant 2025.5+ and 2026.1+ Compatible**

This integration uses modern Home Assistant APIs and is fully compatible with:
- Home Assistant Core 2025.5+ (async platform loading)
- Home Assistant Core 2026.1+ (kelvin color temperature, ColorMode enums)

The integration uses:
- Kelvin-based color temperature (not deprecated mireds)
- `ColorMode` enums (not deprecated string constants)
- `async_load_platform` (not deprecated `load_platform`)

## Credits

- Original integration by CozyLife Team
- Light platform optimizations based on [imatrixcz fork](https://github.com/imatrixcz/hass_cozylife_local_pull)
- Energy storage support and network scanner by community contributors
- HA 2025.5+ compatibility fixes

## Feedback

- Submit issues: [GitHub Issues](https://github.com/inbatek/hass_cozylife_local_pull/issues)
- Original project: info@cozylife.app

## License

This is a community-maintained fork with additional features. Original integration by CozyLife Team.
