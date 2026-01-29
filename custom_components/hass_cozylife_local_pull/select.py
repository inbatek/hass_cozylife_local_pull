"""Platform for select integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import logging

from .const import (
    DOMAIN,
    ENERGY_STORAGE_TYPE_CODE,
    ENERGY_CONTROL,
    ENERGY_LED_MODE,
    ENERGY_BIT_LED,
    ENERGY_LED_MODE_LOW,
    ENERGY_LED_MODE_HIGH,
    ENERGY_LED_MODE_SOS,
    ENERGY_LED_MODE_AUTO,
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the select platform."""
    _LOGGER.info('Select setup_platform')

    if discovery_info is None:
        return

    selects = []
    device_aliases = hass.data[DOMAIN].get('device_aliases', {})

    for item in hass.data[DOMAIN]['tcp_client']:
        if ENERGY_STORAGE_TYPE_CODE == item.device_type_code:
            # Use alias if configured, otherwise use model name + device ID
            if item.ip in device_aliases:
                base_name = device_aliases[item.ip]
            else:
                base_name = item.device_model_name + ' ' + item.device_id[-4:]

            # Add LED mode select
            selects.append(EnergyStorageLEDModeSelect(item, base_name))

    add_entities(selects)


class EnergyStorageLEDModeSelect(SelectEntity):
    """LED mode select for energy storage device."""

    # Mode mapping: display name -> DPID 33 value
    MODE_MAP = {
        "Low": ENERGY_LED_MODE_LOW,
        "High": ENERGY_LED_MODE_HIGH,
        "SOS": ENERGY_LED_MODE_SOS,
    }

    # Reverse mapping: DPID 33 value -> display name
    MODE_REVERSE_MAP = {v: k for k, v in MODE_MAP.items()}

    def __init__(self, tcp_client, base_name: str) -> None:
        """Initialize the select."""
        self._tcp_client = tcp_client
        self._unique_id = f"{tcp_client.device_id}_led_mode"
        self._name = f"{base_name} LED Mode"
        self._attr_options = list(self.MODE_MAP.keys())
        self._attr_current_option = None

    def _get_control_value(self) -> int:
        """Get current DPID 1 value."""
        state = self._tcp_client.query()
        return int(state.get(ENERGY_CONTROL, 0))

    def _is_led_on(self) -> bool:
        """Check if LED is currently on."""
        control_value = self._get_control_value()
        return (control_value & ENERGY_BIT_LED) != 0

    def _get_led_mode(self) -> int:
        """Get current LED mode from DPID 33."""
        state = self._tcp_client.query()
        return int(state.get(ENERGY_LED_MODE, ENERGY_LED_MODE_AUTO))

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        """Return if the select is available (LED must be on)."""
        return self._is_led_on()

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._unique_id

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if not self._is_led_on():
            return None

        mode_value = self._get_led_mode()
        return self.MODE_REVERSE_MAP.get(mode_value, "Low")

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self._is_led_on():
            _LOGGER.warning("Cannot set LED mode when LED is off")
            return

        if option not in self.MODE_MAP:
            _LOGGER.error(f"Invalid LED mode: {option}")
            return

        mode_value = self.MODE_MAP[option]
        self._tcp_client.control({ENERGY_LED_MODE: mode_value})
