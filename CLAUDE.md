# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom component integration for CozyLife smart home devices (lights, switches, plugs, energy storage) using local network communication. The integration uses UDP broadcast for device discovery and TCP for device control.

**Note**: Energy storage (Type 02) support is a custom addition not present in the original CozyLife integration. Light platform optimizations are based on community improvements (imatrixcz fork).

## Installation & Configuration

This is a Home Assistant custom component that must be cloned to the `custom_components` directory. Configuration is done via `configuration.yaml`:

```yaml
hass_cozylife_local_pull:
   lang: en
   ip:
     - "192.168.1.99"
```

The `lang` parameter supports: zh, en, es, pt, ja, ru, nl, ko, fr, de.
The `ip` parameter is optional and allows manually specifying device IPs in addition to auto-discovered devices.

## Architecture

### Device Discovery & Connection Flow

1. **UDP Discovery** (`udp_discover.py`): Broadcasts UDP packets on port 6095 to discover CozyLife devices on the local network
2. **TCP Connection** (`tcp_client.py`): Establishes persistent TCP connections on port 5555 to each discovered device
3. **Device Info Retrieval**: Queries device metadata (device ID, product ID, device type) via TCP
4. **Product Lookup** (`utils.py`): Fetches product models from CozyLife API (`api-us.doiting.com`) to map PIDs to device capabilities
5. **Platform Setup** (`__init__.py`): Creates light and switch entities based on device types

### Communication Protocol

The integration uses a JSON-based protocol over TCP with three command types:
- `CMD_INFO (0)`: Get device information (device ID, PID, MAC, IP, firmware version)
- `CMD_QUERY (2)`: Query device state (switch status, brightness, color, temperature)
- `CMD_SET (3)`: Control device (turn on/off, set brightness, color, etc.)

All messages include:
- `cmd`: Command type
- `pv`: Protocol version (0)
- `sn`: Serial number (timestamp in milliseconds)
- `msg`: Message payload with `attr` (attribute IDs) and `data` (attribute values)

### Device Types & Data Points (DPID)

Devices are categorized by type code:
- `00`: Switch/Plug
- `01`: Light (RGBCW, CW, etc.)
- `02`: Energy Storage (power stations with AC/DC outputs, LED lamp, battery)

#### Switch/Plug (Type 00) - DPIDs:
- `1`: Switch (on/off)

#### Light (Type 01) - DPIDs:
- `1`: Switch (on/off)
- `2`: Work mode
- `3`: Color temperature (0-1000)
- `4`: Brightness (0-1000)
- `5`: Hue (0-65535)
- `6`: Saturation (0-65535)

#### Energy Storage (Type 02) - DPIDs:
- `1`: **Control bitmask** (bit 0=AC output, bit 1=LED lamp, bit 2=DC 12V output)
  - Bit 0 (value & 1): AC output on/off
  - Bit 1 (value & 2): LED lamp on/off
  - Bit 2 (value & 4): DC 12V output on/off
  - Examples: 0=all off, 1=AC only, 3=AC+LED, 5=AC+DC, 7=all on
- `3`: Battery percentage (0-100, read-only sensor)
- `4`: Output power (Watts, read-only sensor)
- `30`: Time remaining (minutes until battery empty, read-only sensor)
- `21`: Input power (Watts, read-only sensor, 0 when not charging)
- `33`: LED mode control (only applicable when LED is on via DPID 1)
  - 0 = Steady low brightness
  - 1 = Steady high brightness
  - 5 = SOS blinking pattern
  - 8 = Auto/standby (set automatically when LED turns off)
- `40`: Max output (constant value, likely max current in amps - 30A)
- `41`: Battery capacity (constant value in Wh, e.g., 300Wh)

### Threading & Connection Management

- TCP connections are established in background threads with automatic reconnection (tcp_client.py:61-77)
- Failed connections retry every 60 seconds
- The main setup uses `time.sleep(3)` to wait for device info before loading platforms (__init__.py:50)
- Platforms are loaded asynchronously via `async_load_platform` with `call_soon_threadsafe`

### Entity Implementation

**Light entities** (`light.py`):
- **Optimized for high-frequency updates** (e.g., Ambilight/HyperHDR)
- Uses async/await and optimistic updates (`_attr_should_poll = False`)
- No polling - state updates are immediate and assumed successful
- **Critical fix**: Always uses DPID 2 = 0 (not a mode switch, but effects control)
- Modern ColorMode API with Kelvin color temperature
- Support ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS based on device capabilities
- Convert between HA ranges and device ranges (brightness 0-255 → 0-1000, hue/saturation scaling)
- Trade-off: Won't detect state changes made from outside Home Assistant (e.g., CozyLife app)

**Switch entities** (`switch.py`):
- Simple on/off control via DPID 1
- Query state on each access

**Energy storage entities** (`energy_storage.py`):
- Three independent switches (AC output, LED lamp, DC 12V output)
- Uses bitwise operations on DPID 1 to control each output independently
- Turn on: `current_value | bit_mask` (sets bit)
- Turn off: `current_value & ~bit_mask` (clears bit)
- LED mode select (Low/High/SOS) - controls DPID 33, only available when LED is on
- Five sensors: output power, input power, battery percentage, time remaining, battery capacity
- Hardware limitation: When AC is off (battery mode), LED and DC cannot both be on simultaneously

## Energy Storage Device Implementation Details

### Independent Control via Bitmask

Energy storage devices (type 02) use DPID 1 as a 3-bit bitmask for independent control of three outputs:

```python
ENERGY_BIT_AC = 1   # Bit 0: AC output
ENERGY_BIT_LED = 2  # Bit 1: LED lamp
ENERGY_BIT_DC = 4   # Bit 2: DC 12V output
```

**Control Pattern:**
1. Query current state: `current = tcp_client.query()[ENERGY_CONTROL]`
2. Set bit to turn on: `new_value = current | bit_mask`
3. Clear bit to turn off: `new_value = current & ~bit_mask`
4. Send control: `tcp_client.control({ENERGY_CONTROL: new_value})`

**Valid State Combinations:**
- `0` (000): All off
- `1` (001): AC only
- `2` (010): LED only (battery mode)
- `3` (011): AC + LED
- `4` (100): DC only (battery mode)
- `5` (101): AC + DC
- `6` (110): LED only (DC bit ignored when AC off)
- `7` (111): All on (AC plugged in)

### LED Mode Control

The LED has three modes controlled via DPID 33:
- **Low** (DPID 33 = 0): Steady low brightness - default when LED turns on
- **High** (DPID 33 = 1): Steady high brightness
- **SOS** (DPID 33 = 5): SOS blinking pattern

When the LED is turned off (DPID 1 bit 1 cleared), DPID 33 automatically reverts to 8 (auto/standby state).
When the LED is turned back on, DPID 33 defaults to 0 (low brightness).

The LED mode select entity is only available/visible when the LED is on.

### Sensor Updates

Energy storage sensors query DPID values on each state access:
- **Battery percentage** (DPID 3): 0-100 range
- **Output power** (DPID 4): Updated every 2-4 seconds by device via CMD 10 push messages
- **Time remaining** (DPID 30): Minutes until battery empty at current load, fluctuates based on power consumption
- **Input power** (DPID 32): 0 when not charging, >0 when AC input connected
- **Battery capacity** (DPID 41): Constant value showing battery capacity in Wh (e.g., 300Wh)

### Hardware Constraints

When running on battery (AC bit = 0), the device prevents both LED and DC from being on simultaneously. If both bits are set while AC is off, only the LED will activate. This is a power-saving measure enforced by the device firmware.

## Key Files

- `__init__.py`: Integration entry point, handles setup, device discovery coordination, platform loading
- `tcp_client.py`: TCP client class managing device connections, protocol implementation, reconnection logic
- `udp_discover.py`: UDP broadcast-based device discovery
- `utils.py`: API client for fetching product models, timestamp generation
- `light.py`: Light entity platform with color/brightness/temperature support
- `switch.py`: Switch entity platform
- `energy_storage.py`: Energy storage platform with independent AC/LED/DC switches and power/battery sensors
- `const.py`: Domain constants, device type codes, DPID definitions, API domain, energy storage bitmasks
- `manifest.json`: Integration metadata for Home Assistant

## Home Assistant Compatibility

**✅ HA 2026.1+ Ready**: This integration is fully compatible with Home Assistant 2026.1 and later:

- **Color temperature**: Uses modern kelvin-based attributes (`_attr_color_temp_kelvin`, `_attr_min_color_temp_kelvin`, `_attr_max_color_temp_kelvin`) instead of deprecated mireds
- **ColorMode enum**: Uses `ColorMode.HS`, `ColorMode.COLOR_TEMP`, `ColorMode.BRIGHTNESS`, `ColorMode.ONOFF` instead of deprecated `COLOR_MODE_*` string constants
- **Platform loading**: Uses `async_load_platform` instead of deprecated `load_platform` (HA 2025.5+)

These improvements were inherited from the imatrixcz fork optimizations, ensuring compatibility with current and future Home Assistant versions.

## Performance Optimizations

The light platform has been optimized based on community improvements (credit: imatrixcz fork):
- **Optimistic updates**: Lights respond instantly without waiting for device confirmation
- **No polling**: Eliminates constant state queries, reducing network traffic
- **Async operations**: All commands run asynchronously via executor jobs
- **High-frequency ready**: Suitable for Ambilight/HyperHDR and other rapid update scenarios

**Important caveat**: With optimistic mode enabled, Home Assistant won't detect if you control lights via the CozyLife mobile app or other means. The HA state will be out of sync until you control it through HA again.

## Common Issues

- **Network isolation**: Router network isolation can prevent UDP broadcast discovery
- **Connection stability**: TCP reconnection is automatic but can take 60 seconds between retries
- **Light color control**: DPID 2 must always be 0 for standard operation (not a mode selector)
- **Platform loading timing**: Recent HA versions (2025.5+) require using `async_load_platform` instead of deprecated `load_platform`
- **Weak WiFi signal**: CozyLife devices often have weak antennas; ensure strong 2.4 GHz signal
