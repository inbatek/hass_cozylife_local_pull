"""Example Load Platform integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType
import logging
import time
from .const import (
    DOMAIN,
    LANG
)
from .utils import get_pid_list
from .udp_discover import get_ip
from .tcp_client import tcp_client


_LOGGER = logging.getLogger(__name__)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:

    """
    Setup CozyLife integration.

    Supports two config formats:
    1. Legacy IP list: {'lang': 'en', 'ip': ['192.168.1.101', '192.168.1.102']}
    2. Device list: {'lang': 'en', 'devices': [{'serial_number': '...', 'alias': '...', 'ip': '...'}]}
    """
    ip = get_ip()

    # Support both legacy 'ip' list and new 'devices' list formats
    ip_from_config = config[DOMAIN].get('ip') if config[DOMAIN].get('ip') is not None else []
    devices_from_config = config[DOMAIN].get('devices') if config[DOMAIN].get('devices') is not None else []

    # Extract IPs from devices list format
    for device in devices_from_config:
        if 'ip' in device:
            ip_from_config.append(device['ip'])

    ip += ip_from_config
    ip_list = []
    [ip_list.append(i) for i in ip if i not in ip_list]

    # Build device alias mapping (IP -> alias)
    device_aliases = {}
    for device in devices_from_config:
        if 'ip' in device and 'alias' in device:
            device_aliases[device['ip']] = device['alias']

    if 0 == len(ip_list):
        _LOGGER.info('discover nothing')
        return True

    _LOGGER.info('try conncet ip_list:', ip_list)
    lang_from_config = (config[DOMAIN].get('lang') if config[DOMAIN].get('lang') is not None else LANG)
    get_pid_list(lang_from_config)

    hass.data[DOMAIN] = {
        'temperature': 24,
        'ip': ip_list,
        'tcp_client': [tcp_client(item) for item in ip_list],
        'device_aliases': device_aliases,
    }

    #wait for get device info from tcp conncetion
    #but it is bad
    time.sleep(3)
    # _LOGGER.info('setup', hass, config)
    hass.loop.call_soon_threadsafe(hass.async_create_task, async_load_platform(hass, 'light', DOMAIN, {}, config))
    hass.loop.call_soon_threadsafe(hass.async_create_task, async_load_platform(hass, 'switch', DOMAIN, {}, config))
    hass.loop.call_soon_threadsafe(hass.async_create_task, async_load_platform(hass, 'sensor', DOMAIN, {}, config))
    hass.loop.call_soon_threadsafe(hass.async_create_task, async_load_platform(hass, 'select', DOMAIN, {}, config))
    return True
