""" for sensors components """
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from  homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTime,
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
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    """ Configuration des entités sensor à partir de la configuration
        ConfigEntry passée en argument
    """
    entities = []
    device = hass.data[DOMAIN]["device"]
    coordinator = hass.data[DOMAIN]["coordinator"]
    if entry.data.get("Mode") == "Modbus RTU":
        entities.append(DiagnosticsSensor(device, "Device", entry.data))
        entities.append(DiagnosticsSensor(device, "Address", entry.data))
        entities.append(DiagModbusSensor(device, entry.data))
    elif entry.data.get("Mode") == "Modbus TCP":
        entities.append(DiagModbusSensor(device, entry.data))
    else:
        _LOGGER.error("Mode unknown")

    for engine in device.engines:
        entities.append(DiagEngineThroughputSensor(coordinator, device, engine))
        entities.append(DiagEngineTempOrderSensor(coordinator, device, engine))
    async_add_entities(entities)

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