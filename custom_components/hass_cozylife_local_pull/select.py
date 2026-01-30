"""Platform for select integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data["client"]
    alias = entry_data.get("alias")

    entities = []

    if client.device_type_code == ENERGY_STORAGE_TYPE_CODE:
        # Energy storage LED mode select
        base_name = alias if alias else client.device_model_name
        entities.append(EnergyStorageLEDModeSelect(client, base_name))

    if entities:
        async_add_entities(entities)


class EnergyStorageLEDModeSelect(SelectEntity):
    """LED mode select for energy storage device."""

    # Mode mapping: display name -> DPID 33 value
    MODE_MAP = {
        "Off": None,  # Special case - turns off LED
        "Low": ENERGY_LED_MODE_LOW,
        "High": ENERGY_LED_MODE_HIGH,
        "SOS": ENERGY_LED_MODE_SOS,
    }

    # Reverse mapping: DPID 33 value -> display name
    MODE_REVERSE_MAP = {v: k for k, v in MODE_MAP.items() if v is not None}

    def __init__(self, tcp_client, base_name: str) -> None:
        """Initialize the select."""
        self._tcp_client = tcp_client
        self._base_name = base_name  # Store base name for device_info
        self._unique_id = f"{tcp_client.device_id}_led_mode"
        self._name = f"{base_name} LED Mode"
        self._attr_options = list(self.MODE_MAP.keys())
        self._attr_current_option = "Off"  # Default to Off

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
        """Return if the select is available (always available now)."""
        return True

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._tcp_client.device_id)},
            "name": self._base_name,  # Use stored base name
            "manufacturer": "CozyLife",
            "model": self._tcp_client.device_model_name,
        }

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if not self._is_led_on():
            return "Off"

        mode_value = self._get_led_mode()
        return self.MODE_REVERSE_MAP.get(mode_value, "Low")

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.MODE_MAP:
            _LOGGER.error(f"Invalid LED mode: {option}")
            return

        if option == "Off":
            # Turn off LED by clearing bit 1 in DPID 1
            current = self._get_control_value()
            new_value = current & ~ENERGY_BIT_LED  # Clear LED bit
            self._tcp_client.control({ENERGY_CONTROL: new_value})
            _LOGGER.info(f"Turning LED off for {self._tcp_client.device_id}")
        else:
            # Turn on LED (if not already on) and set mode
            current = self._get_control_value()
            if not (current & ENERGY_BIT_LED):
                # LED is off, turn it on
                new_value = current | ENERGY_BIT_LED  # Set LED bit
                self._tcp_client.control({ENERGY_CONTROL: new_value})
                _LOGGER.info(f"Turning LED on for {self._tcp_client.device_id}")

            # Set the LED mode
            mode_value = self.MODE_MAP[option]
            self._tcp_client.control({ENERGY_LED_MODE: mode_value})
            _LOGGER.info(f"Setting LED mode to {option} ({mode_value}) for {self._tcp_client.device_id}")
