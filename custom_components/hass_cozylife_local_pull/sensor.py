"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfEnergy, UnitOfTime, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import logging

from .const import (
    DOMAIN,
    ENERGY_STORAGE_TYPE_CODE,
    ENERGY_BATTERY_PERCENT,
    ENERGY_OUTPUT_POWER,
    ENERGY_TIME_REMAINING,
    ENERGY_INPUT_POWER,
    ENERGY_CAPACITY,
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info('Sensor setup_platform')

    if discovery_info is None:
        return

    sensors = []
    device_aliases = hass.data[DOMAIN].get('device_aliases', {})

    for item in hass.data[DOMAIN]['tcp_client']:
        if ENERGY_STORAGE_TYPE_CODE == item.device_type_code:
            # Use alias if configured, otherwise use model name + device ID
            if item.ip in device_aliases:
                base_name = device_aliases[item.ip]
            else:
                base_name = item.device_model_name + ' ' + item.device_id[-4:]

            # Add sensors
            sensors.append(EnergyStorageOutputPowerSensor(item, base_name))
            sensors.append(EnergyStorageInputPowerSensor(item, base_name))
            sensors.append(EnergyStorageBatteryPercentSensor(item, base_name))
            sensors.append(EnergyStorageTimeRemainingSensor(item, base_name))
            sensors.append(EnergyStorageCapacitySensor(item, base_name))

    add_entities(sensors)


class EnergyStorageBaseSensor(SensorEntity):
    """Base class for energy storage sensors."""

    def __init__(self, tcp_client, base_name: str, sensor_name: str, dpid: str) -> None:
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

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Output Power", ENERGY_OUTPUT_POWER)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageInputPowerSensor(EnergyStorageBaseSensor):
    """Input power sensor for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Input Power", ENERGY_INPUT_POWER)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageBatteryPercentSensor(EnergyStorageBaseSensor):
    """Battery percentage sensor for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Battery", ENERGY_BATTERY_PERCENT)
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageTimeRemainingSensor(EnergyStorageBaseSensor):
    """Time remaining sensor for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Time Remaining", ENERGY_TIME_REMAINING)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyStorageCapacitySensor(EnergyStorageBaseSensor):
    """Battery capacity sensor for energy storage device."""

    def __init__(self, tcp_client, base_name: str) -> None:
        super().__init__(tcp_client, base_name, "Battery Capacity", ENERGY_CAPACITY)
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL  # Total capacity, not measurement
