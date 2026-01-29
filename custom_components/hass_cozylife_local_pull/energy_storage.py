"""Platform for energy storage integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.select import SelectEntity
from homeassistant.const import UnitOfPower, UnitOfEnergy, UnitOfTime, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from typing import Any
import logging

from .const import (
    DOMAIN,
    ENERGY_STORAGE_TYPE_CODE,
    ENERGY_CONTROL,
    ENERGY_BATTERY_PERCENT,
    ENERGY_OUTPUT_POWER,
    ENERGY_TIME_REMAINING,
    ENERGY_INPUT_POWER,
    ENERGY_LED_MODE,
    ENERGY_CAPACITY,
    ENERGY_BIT_AC,
    ENERGY_BIT_LED,
    ENERGY_BIT_DC,
    ENERGY_LED_MODE_LOW,
    ENERGY_LED_MODE_HIGH,
    ENERGY_LED_MODE_SOS,
    ENERGY_LED_MODE_AUTO,
)
from .tcp_client import tcp_client

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the energy storage platform."""
    _LOGGER.info('Energy storage setup_platform')

    if discovery_info is None:
        return

    entities = []
    for item in hass.data[DOMAIN]['tcp_client']:
        if ENERGY_STORAGE_TYPE_CODE == item.device_type_code:
            base_name = item.device_model_name + ' ' + item.device_id[-4:]

            # Add switches
            entities.append(EnergyStorageACSwitch(item, base_name))
            entities.append(EnergyStorageLEDSwitch(item, base_name))
            entities.append(EnergyStorageDCSwitch(item, base_name))

            # Add select entities
            entities.append(EnergyStorageLEDModeSelect(item, base_name))

            # Add sensors
            entities.append(EnergyStorageOutputPowerSensor(item, base_name))
            entities.append(EnergyStorageInputPowerSensor(item, base_name))
            entities.append(EnergyStorageBatteryPercentSensor(item, base_name))
            entities.append(EnergyStorageTimeRemainingSensor(item, base_name))
            entities.append(EnergyStorageCapacitySensor(item, base_name))

    add_entities(entities)


class EnergyStorageBaseSwitch(SwitchEntity):
    """Base class for energy storage switches."""

    def __init__(self, tcp_client: tcp_client, base_name: str, bit_mask: int, switch_name: str) -> None:
        """Initialize the switch."""
        self._tcp_client = tcp_client
        self._bit_mask = bit_mask
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

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_AC, "AC Output")


class EnergyStorageLEDSwitch(EnergyStorageBaseSwitch):
    """LED lamp switch for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_LED, "LED Lamp")


class EnergyStorageDCSwitch(EnergyStorageBaseSwitch):
    """DC 12V output switch for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, ENERGY_BIT_DC, "DC Output")


class EnergyStorageBaseSensor(SensorEntity):
    """Base class for energy storage sensors."""

    def __init__(self, tcp_client: tcp_client, base_name: str, sensor_name: str, dpid: str) -> None:
        """Initialize the sensor."""
        self._tcp_client = tcp_client
        self._dpid = dpid
        self._unique_id = f"{tcp_client.device_id}_{sensor_name.lower().replace(' ', '_')}"
        self._name = f"{base_name} {sensor_name}"
        self._attr_native_value = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return True

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._unique_id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        state = self._tcp_client.query()
        return self._process_value(state.get(self._dpid, 0))

    def _process_value(self, value):
        """Process the raw value. Override in subclasses if needed."""
        return value


class EnergyStorageOutputPowerSensor(EnergyStorageBaseSensor):
    """Output power sensor for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Output Power", ENERGY_OUTPUT_POWER)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageInputPowerSensor(EnergyStorageBaseSensor):
    """Input power sensor for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Input Power", ENERGY_INPUT_POWER)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageBatteryPercentSensor(EnergyStorageBaseSensor):
    """Battery percentage sensor for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Battery", ENERGY_BATTERY_PERCENT)
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageTimeRemainingSensor(EnergyStorageBaseSensor):
    """Time remaining sensor for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Time Remaining", ENERGY_TIME_REMAINING)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageCapacitySensor(EnergyStorageBaseSensor):
    """Battery capacity sensor for energy storage device."""

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Battery Capacity", ENERGY_CAPACITY)
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_state_class = SensorStateClass.MEASUREMENT


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

    def __init__(self, tcp_client: tcp_client, base_name: str) -> None:
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
