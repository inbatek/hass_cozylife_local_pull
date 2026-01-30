"""Platform for switch integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from typing import Any
from .const import (
    DOMAIN,
    SWITCH_TYPE_CODE,
    ENERGY_STORAGE_TYPE_CODE,
    ENERGY_CONTROL,
    ENERGY_BIT_AC,
    ENERGY_BIT_LED,
    ENERGY_BIT_DC,
)
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches from a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data["client"]
    alias = entry_data.get("alias")

    entities = []

    if client.device_type_code == SWITCH_TYPE_CODE:
        # Regular switch/plug
        device_name = alias if alias else client.device_model_name
        entities.append(CozyLifeSwitch(client, device_name))

    elif client.device_type_code == ENERGY_STORAGE_TYPE_CODE:
        # Energy storage switches
        base_name = alias if alias else client.device_model_name
        entities.append(EnergyStorageACSwitch(client, base_name))
        entities.append(EnergyStorageLEDSwitch(client, base_name))
        entities.append(EnergyStorageDCSwitch(client, base_name))

    if entities:
        async_add_entities(entities)


class CozyLifeSwitch(SwitchEntity):
    _tcp_client = None
    _attr_is_on = True

    def __init__(self, tcp_client, alias: str | None = None) -> None:
        """Initialize the sensor."""
        _LOGGER.info('__init__')
        self._tcp_client = tcp_client
        self._unique_id = f"{tcp_client.device_id}_switch"  # Add suffix to avoid conflicts
        # Use alias from config if provided, otherwise use device model name from CozyLife app
        if alias:
            self._name = alias
        else:
            self._name = tcp_client.device_model_name
        self._refresh_state()
    
    def _refresh_state(self):
        self._state = self._tcp_client.query()
        self._attr_is_on = 0 != self._state['1']
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return True
    
    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        self._attr_is_on = True

        self._refresh_state()
        return self._attr_is_on
    
    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._tcp_client.device_id)},
            "name": self._name,
            "manufacturer": "CozyLife",
            "model": self._tcp_client.device_model_name,
        }

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        _LOGGER.info(f'turn_on:{kwargs}')
        self._tcp_client.control({'1': 255})
        return None
        raise NotImplementedError()
    
    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._attr_is_on = False
        _LOGGER.info('turn_off')
        self._tcp_client.control({'1': 0})
        return None

        raise NotImplementedError()


# Energy Storage Switches

class EnergyStorageBaseSwitch(SwitchEntity):
    """Base class for energy storage switches."""

    def __init__(self, tcp_client, base_name: str, bit_mask: int, switch_name: str) -> None:
        """Initialize the switch."""
        self._tcp_client = tcp_client
        self._bit_mask = bit_mask
        self._base_name = base_name  # Store base name for device_info
        self._unique_id = f"{tcp_client.device_id}_{switch_name.lower().replace(' ', '_')}"
        self._name = f"{base_name} {switch_name}"
        self._attr_is_on = False
        self._update_state()

    def _get_control_value(self) -> int:
        """Get current DPID 1 value."""
        state = self._tcp_client.query()
        return int(state.get(ENERGY_CONTROL, 0))

    def _update_state(self):
        """Update the switch state from device."""
        control_value = self._get_control_value()
        self._attr_is_on = (control_value & self._bit_mask) != 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        self._update_state()
        return self._attr_is_on

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

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        current = self._get_control_value()
        new_value = current | self._bit_mask
        self._tcp_client.control({ENERGY_CONTROL: new_value})
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        current = self._get_control_value()
        new_value = current & ~self._bit_mask
        self._tcp_client.control({ENERGY_CONTROL: new_value})
        self._attr_is_on = False


class EnergyStorageACSwitch(EnergyStorageBaseSwitch):
    """AC output switch for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_AC, "AC Output")


class EnergyStorageLEDSwitch(EnergyStorageBaseSwitch):
    """LED lamp switch for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_LED, "LED Lamp")


class EnergyStorageDCSwitch(EnergyStorageBaseSwitch):
    """DC 12V output switch for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_DC, "DC Output")
