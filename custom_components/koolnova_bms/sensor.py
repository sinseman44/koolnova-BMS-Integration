""" for sensors components """
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.const import (
    UnitOfTemperature
)

from .const import (
    DOMAIN
)

from .coordinator import KoolnovaCoordinator

from .koolnova.device import (
    Koolnova, 
    Engine,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    """ Configuration des entités sensor à partir de la configuration
        ConfigEntry passée en argument
    """
    entities = []
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    device = runtime_data["device"]
    coordinator = runtime_data["coordinator"]
    if entry.data.get("Mode") == "Modbus RTU":
        entities.append(DiagnosticsSensor(device, "Device", entry.data))
        entities.append(DiagnosticsSensor(device, "Address", entry.data))
        entities.append(DiagModbusSensor(device, entry.data))
    elif entry.data.get("Mode") == "Modbus TCP":
        entities.append(DiagModbusSensor(device, entry.data))
    else:
        _LOGGER.error("Mode unknown")

    if device.table_version == "v2":
        entities.extend(_build_v2_sensor_entities(coordinator, device))
    else:
        _LOGGER.debug("Skip Koolnova v2 sensors for table version %s", device.table_version)

    for engine in device.engines:
        entities.append(DiagEngineThroughputSensor(coordinator, device, engine))
        entities.append(DiagEngineTempOrderSensor(coordinator, device, engine))
    async_add_entities(entities)

def _build_v2_sensor_entities(coordinator: KoolnovaCoordinator,
                                device: Koolnova,
                                ) -> list[SensorEntity]:
    """Build sensors that only exist for the Koolnova v2 Modbus table."""
    entities = []
    entities.append(V2RegisterSensor(coordinator, device, "40073_model_version", "V2 model version", "mdi:chip"))
    entities.append(V2RegisterFieldSensor(coordinator, device, "40078_system_time", "day_name", "V2 system day", "mdi:calendar", enabled_default=False))
    entities.append(V2RegisterFieldSensor(coordinator, device, "40078_system_time", "hour", "V2 system hour", "mdi:clock-time-four-outline", enabled_default=False))
    entities.append(V2RegisterFieldSensor(coordinator, device, "40078_system_time", "minute", "V2 system minute", "mdi:clock-time-four-outline", enabled_default=False))
    entities.append(V2TemperatureSensor(coordinator, device, "40082_floor_water_temperature", "V2 floor water temperature", "mdi:thermometer-water"))
    entities.append(V2TemperatureSensor(coordinator, device, "40083_outdoor_temperature", "V2 outdoor temperature", "mdi:thermometer"))
    entities.append(V2TemperatureSensor(coordinator, device, "40084_aux_temperature", "V2 auxiliary temperature", "mdi:thermometer-probe"))
    entities.append(V2RegisterSensor(coordinator, device, "40107_reserved", "V2 reserved 40107", "mdi:counter", enabled_default=False))
    entities.append(V2RegisterSensor(coordinator, device, "40111_radiant_floor_demand_count", "V2 radiant floor demand count", "mdi:counter"))
    entities.append(V2RegisterSensor(coordinator, device, "40112_ac3_air_demand_count", "V2 AC3 air demand count", "mdi:counter"))

    for engine, register in zip(device.engines, (40113, 40114, 40115, 40116)):
        entities.append(V2EngineRegisterSensor(coordinator, device, engine,
                                                "{}_connected_volume_ac{}".format(register, engine.engine_id),
                                                "V2 AC{} connected volume".format(engine.engine_id),
                                                "mdi:gauge",
                                                enabled_default=False))

    for engine, register in zip(device.engines, (40117, 40118, 40119, 40120)):
        entities.append(V2EngineRegisterSensor(coordinator, device, engine,
                                                "{}_active_volume_ac{}".format(register, engine.engine_id),
                                                "V2 AC{} active volume".format(engine.engine_id),
                                                "mdi:gauge",
                                                enabled_default=False))

    for engine, register in zip(device.engines, (40121, 40122, 40123, 40125)):
        entities.append(V2EngineTemperatureSensor(coordinator, device, engine,
                                                    "{}_requested_temp_avg_ac{}".format(register, engine.engine_id),
                                                    "V2 AC{} requested temperature average".format(engine.engine_id),
                                                    "mdi:thermometer-lines",
                                                    enabled_default=False))

    entities.append(V2RegisterSensor(coordinator, device, "40126_efficiency_ac3_speed", "V2 efficiency AC3 speed", "mdi:counter"))
    return entities

class V2RegisterSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """Diagnostic sensor for a Koolnova v2 register snapshot value."""

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    key:str,
                    name:str,
                    icon:str,
                    enabled_default: bool = True,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator)
        self._device = device
        self._key = key
        self._attr_name = f"{self._device.name} {name}"
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{self._key}-sensor"
        self._attr_icon = icon
        self._attr_native_value = self._value_from_registers(self._device.v2_registers)

    def _value_from_registers(self,
                                registers: dict,
                                ):
        """Read this sensor value from a v2 register snapshot."""
        value = registers.get(self._key)
        if isinstance(value, dict):
            return value.get("raw")
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        coordinator_data = self.coordinator.data or {}
        self._attr_native_value = self._value_from_registers(
            coordinator_data.get("v2_registers", self._device.v2_registers)
        )
        self.async_write_ha_state()

class V2TemperatureSensor(V2RegisterSensor):
    # pylint: disable = too-many-instance-attributes
    """Diagnostic temperature sensor for a Koolnova v2 register."""

    _attr_device_class: SensorDeviceClass = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement: str = UnitOfTemperature.CELSIUS

class V2RegisterFieldSensor(V2RegisterSensor):
    # pylint: disable = too-many-instance-attributes
    """Diagnostic sensor for one field of a Koolnova v2 register snapshot."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    key:str,
                    field:str,
                    name:str,
                    icon:str,
                    enabled_default: bool = True,
                    ) -> None:
        """Class constructor."""
        self._field = field
        super().__init__(coordinator, device, key, name, icon, enabled_default)
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{self._key}-{self._field}-sensor"

    def _value_from_registers(self,
                                registers: dict,
                                ):
        """Read this sensor field from a v2 register snapshot."""
        value = registers.get(self._key, {})
        if isinstance(value, dict):
            return value.get(self._field)
        return None

class V2EngineRegisterSensor(V2RegisterSensor):
    # pylint: disable = too-many-instance-attributes
    """Diagnostic sensor for a Koolnova v2 register tied to an engine."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    engine: Engine,
                    key:str,
                    name:str,
                    icon:str,
                    enabled_default: bool = True,
                    ) -> None:
        """Class constructor."""
        self._engine = engine
        super().__init__(coordinator, device, key, name, icon, enabled_default)
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Engine-AC{self._engine.engine_id}-{self._key}-sensor"

class V2EngineTemperatureSensor(V2EngineRegisterSensor):
    # pylint: disable = too-many-instance-attributes
    """Diagnostic temperature sensor for a Koolnova v2 engine register."""

    _attr_device_class: SensorDeviceClass = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement: str = UnitOfTemperature.CELSIUS

class DiagnosticsSensor(SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """ Representation of a Sensor """

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    device: Koolnova, # pylint: disable=unused-argument,
                    name:str, # pylint: disable=unused-argument
                    entry_infos, # pylint: disable=unused-argument
                    ) -> None:
        """ Class constructor """
        self._device = device
        self._attr_name = f"{self._device.name} {name}"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{name}-sensor"
        self._attr_native_value = entry_infos.get(name)

    @property
    def icon(self) -> str | None:
        return "mdi:monitor"

    @property
    def should_poll(self) -> bool:
        """ Do not poll for those entities """
        return False

class DiagModbusSensor(SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """ Representation of a Sensor """

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    device: Koolnova, # pylint: disable=unused-argument,
                    entry_infos, # pylint: disable=unused-argument
                    ) -> None:
        """ Class constructor """
        self._device = device
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Modbus-RTU-sensor"
        if entry_infos.get("Mode") == 'Modbus RTU':
            self._attr_name = f"{self._device.name} {self._device.name} Modbus RTU"
            self._attr_native_value = "{} {}{}{}".format(entry_infos.get("Baudrate"),
                                                        entry_infos.get("Sizebyte"),
                                                        entry_infos.get("Parity")[0],
                                                        entry_infos.get("Stopbits"))
        elif entry_infos.get("Mode") == 'Modbus TCP':
            self._attr_name = f"{self._device.name} {self._device.name} Modbus TCP"
            self._attr_native_value = "{}:{}".format(entry_infos.get("Address"),
                                                        entry_infos.get("Port"))

    @property
    def icon(self) -> str | None:
        return "mdi:monitor"

    @property
    def should_poll(self) -> bool:
        """ Do not poll for those entities """
        return False

class DiagEngineThroughputSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """ Representation of a Sensor """

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument
                    engine: Engine, # pylint: disable=unused-argument
                    ) -> None:
        """ Class constructor """
        super().__init__(coordinator)
        self._device = device
        self._engine = engine
        self._attr_name = f"{self._device.name} Engine AC{self._engine.engine_id} throughput"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Engine-AC{self._engine.engine_id}-throughput-sensor"
        self._attr_native_value = "{}".format(self._engine.throughput)

    @property
    def icon(self) -> str | None:
        return "mdi:thermostat-cog"

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator """
        for _cur_engine in self.coordinator.data['engines']:
            if self._engine.engine_id == _cur_engine.engine_id:
                _LOGGER.debug("[UPDATE] [ENGINE AC{}] Troughput: {}".format(_cur_engine.engine_id, _cur_engine.throughput))
                self._attr_native_value = "{}".format(_cur_engine.throughput)
        self.async_write_ha_state()

class DiagEngineTempOrderSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """ Representation of a Sensor """

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement: str = UnitOfTemperature.CELSIUS

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument
                    engine: Engine, # pylint: disable=unused-argument
                    ) -> None:
        """ Class constructor """
        super().__init__(coordinator)
        self._device = device
        self._engine = engine
        self._attr_name = f"{self._device.name} Engine AC{self._engine.engine_id} temperature order"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Engine-AC{self._engine.engine_id}-temp-order-sensor"
        self._attr_native_value = "{}".format(self._engine.order_temp)

    @property
    def icon(self) -> str | None:
        return "mdi:thermometer-lines"

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator """
        for _cur_engine in self.coordinator.data['engines']:
            if self._engine.engine_id == _cur_engine.engine_id:
                _LOGGER.debug("[UPDATE] [ENGINE AC{}] Order temp: {}".format(_cur_engine.engine_id, _cur_engine.order_temp))
                self._attr_native_value = "{}".format(_cur_engine.order_temp)
        self.async_write_ha_state()
