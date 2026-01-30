"""CozyLife Local integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, LANG
from .tcp_client import tcp_client
from .utils import get_pid_list
from .udp_discover import get_ip

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.LIGHT, Platform.SWITCH, Platform.SENSOR, Platform.SELECT]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the CozyLife Local component from YAML."""

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    # Get language setting
    lang = conf.get('lang', LANG)
    await hass.async_add_executor_job(get_pid_list, lang)

    # Import devices from YAML into config entries
    devices_from_config = conf.get('devices', [])
    ip_list = conf.get('ip', [])

    # Handle new device list format
    for device in devices_from_config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=device,
            )
        )

    # Handle legacy IP list format
    for ip in ip_list:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={"ip": ip},
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CozyLife Local from a config entry."""

    _LOGGER.info(f"Setting up CozyLife device from config entry: {entry.title}")

    ip = entry.data["ip"]
    alias = entry.data.get("alias")

    # Create TCP client for this device
    client = await hass.async_add_executor_job(tcp_client, ip)

    # Wait for connection (non-blocking)
    _LOGGER.info(f"Waiting for device {ip} to connect...")
    for i in range(30):  # 15 seconds max (30 x 0.5s)
        await asyncio.sleep(0.5)
        if client.device_id:
            break

    if not client.device_id:
        _LOGGER.error(f"Failed to connect to device at {ip}")
        return False

    _LOGGER.info(f"Connected to device: {client.device_id} at {ip}")

    # Update config entry unique ID to use device ID
    if entry.unique_id != client.device_id and "serial_number" in entry.data:
        # Already has correct unique ID from YAML import
        pass
    else:
        # Update unique ID to device ID
        hass.config_entries.async_update_entry(
            entry, unique_id=client.device_id
        )

    # Register device in device registry
    device_name = alias if alias else client.device_model_name
    device_reg = dr.async_get(hass)
    device_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, client.device_id)},
        name=device_name,
        manufacturer="CozyLife",
        model=client.device_model_name,
    )

    # Store client in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "alias": alias,
    }

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(f"Successfully set up CozyLife device: {device_name}")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.info(f"Unloading CozyLife device: {entry.title}")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up stored data
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data and "client" in entry_data:
            # Close TCP connection
            client = entry_data["client"]
            await hass.async_add_executor_job(client._close_connection)

    return unload_ok
