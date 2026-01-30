"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfEnergy, UnitOfTime, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data["client"]
    alias = entry_data.get("alias")

    entities = []

    if client.device_type_code == ENERGY_STORAGE_TYPE_CODE:
        # Energy storage sensors
        base_name = alias if alias else client.device_model_name
        entities.append(EnergyStorageOutputPowerSensor(client, base_name))
        entities.append(EnergyStorageInputPowerSensor(client, base_name))
        entities.append(EnergyStorageBatteryPercentSensor(client, base_name))
        entities.append(EnergyStorageTimeRemainingSensor(client, base_name))
        entities.append(EnergyStorageCapacitySensor(client, base_name))

    if entities:
        async_add_entities(entities)


class EnergyStorageBaseSensor(SensorEntity):
    """Base class for energy storage sensors."""

    def __init__(self, tcp_client, base_name: str, sensor_name: str, dpid: str) -> None:
        """Initialize the sensor."""
        self._tcp_client = tcp_client
        self._dpid = dpid
        self._base_name = base_name  # Store base name for device_info
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
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._tcp_client.device_id)},
            "name": self._base_name,  # Use stored base name
            "manufacturer": "CozyLife",
            "model": self._tcp_client.device_model_name,
        }

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
