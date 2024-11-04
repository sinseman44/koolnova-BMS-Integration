""" for switch component """
# pylint: disable = too-few-public-methods
from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass
)

from homeassistant.util import Throttle
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN
)

from .coordinator import KoolnovaCoordinator

from homeassistant.const import (
    STATE_OFF,
    STATE_ON
)

from .koolnova.device import Koolnova
from .koolnova.const import (
    SysState,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback,
                            ):
    """ Setup switch entries """

    device = hass.data[DOMAIN]["device"]
    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = [
        SystemStateSwitch(coordinator, device),
        DebugStateSwitch(device),
    ]
    async_add_entities(entities)

class SystemStateSwitch(CoordinatorEntity, SwitchEntity):
    """Select component to set system state """
    _attr_has_entity_name: bool = True
    _attr_device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH
    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument
                ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_name = f"{device.name} Global HVAC State"
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}-Global-HVAC-State-switch"
        self._attr_is_on = bool(int(self._device.sys_state))
        if bool(int(self._device.sys_state)):
            self._attr_state = STATE_ON
        else:
            self._attr_state = STATE_OFF

    async def async_turn_on(self, **kwargs):
        """ Turn the entity on. """
        _LOGGER.debug("Turn on system")
        await self._device.async_set_sys_state(SysState.SYS_STATE_ON)
        self._attr_is_on = True
        self._attr_state = STATE_ON
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """ Turn the entity off. """
        _LOGGER.debug("Turn off system")
        await self._device.async_set_sys_state(SysState.SYS_STATE_OFF)
        self._attr_is_on = False
        self._attr_state = STATE_OFF
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator """
        self._attr_is_on = bool(int(self.coordinator.data['sys']))
        _LOGGER.debug("[UPDATE] Switch State: {}".format(bool(int(self.coordinator.data['sys']))))
        if bool(int(self.coordinator.data['sys'])):
            self._attr_state = STATE_ON
        else:
            self._attr_state = STATE_OFF
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return bool(int(self._device.sys_state))

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:power"

class DebugStateSwitch(SwitchEntity):
    """Select component to set system state """
    _attr_has_entity_name: bool = True
    _attr_device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH
    _attr_entity_category: EntityCategory = EntityCategory.DIAGNOSTIC

    def __init__(self,
                    device: Koolnova, # pylint: disable=unused-argument
                ) -> None:
        super().__init__()
        self._device = device
        self._attr_name = f"Modbus Debug"
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}-Modbus-Debug-switch"
        self._attr_is_on = bool(int(self._device.debug))
        if bool(int(self._device.debug)):
            self._attr_state = STATE_ON
        else:
            self._attr_state = STATE_OFF

    async def async_turn_on(self, **kwargs):
        """ Turn the entity on. """
        _LOGGER.debug("Turn on Debug")
        await self._device.async_set_debug(True)
        self._attr_is_on = True
        self._attr_state = STATE_ON

    async def async_turn_off(self, **kwargs):
        """ Turn the entity off. """
        _LOGGER.debug("Turn off Debug")
        await self._device.async_set_debug(False)
        self._attr_is_on = False
        self._attr_state = STATE_OFF

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._device.debug

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:bug"