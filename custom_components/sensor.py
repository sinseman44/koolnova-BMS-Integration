""" Implementation du composant sensors """
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
from  homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)
from .const import (
    DOMAIN
)
from homeassistant.const import UnitOfTime
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
    _LOGGER.debug("Calling async_setup_entry - datas: {}".format(entry.data))
    _LOGGER.debug("HASS data: {}".format(hass.data[DOMAIN]))
    for device in hass.data[DOMAIN]:
        _LOGGER.debug("Device: {}".format(device))
        entities = [
            DiagnosticsSensor(device, "Device", entry.data),
            DiagnosticsSensor(device, "Address", entry.data),
            DiagModbusSensor(device, entry.data),
        ]
        for engine in device.engines:
            _LOGGER.debug("Engine: {}".format(engine))
            entities.append(DiagEngineSensor(device, engine))
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
        self._attr_name = f"{device.name} {name}"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{name}-sensor"
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
        self._attr_name = f"{device.name} Modbus RTU"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-Modbus-RTU-sensor"
        self._attr_native_value = "{} {}{}{}".format(entry_infos.get("Baudrate"),
                                                        entry_infos.get("Sizebyte"),
                                                        entry_infos.get("Parity")[0],
                                                        entry_infos.get("Stopbits"))

    @property
    def icon(self) -> str | None:
        return "mdi:monitor"

    @property
    def should_poll(self) -> bool:
        """ Do not poll for those entities """
        return False

class DiagEngineSensor(SensorEntity):
    # pylint: disable = too-many-instance-attributes
    """ Representation of a Sensor """

    _attr_entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    device: Koolnova, # pylint: disable=unused-argument
                    engine: Engine, # pylint: disable=unused-argument
                    ) -> None:
        """ Class constructor """
        self._device = device
        self._engine = engine
        self._attr_name = f"{device.name} Engine AC{engine.engine_id} Throughput"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-Engine-AC{engine.engine_id}-throughput-sensor"
        self._attr_native_value = f"TEST"

    @property
    def icon(self) -> str | None:
        return "mdi:monitor"

    @property
    def should_poll(self) -> bool:
        """ Do not poll for those entities """
        return False
