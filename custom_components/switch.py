""" for switch component """
# pylint: disable = too-few-public-methods
from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity
from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
)
from homeassistant.const import UnitOfTime
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

    for device in hass.data[DOMAIN]:
        _LOGGER.debug("Device: {}".format(device))
        entities = [
            SystemStateSwitch(device),
        ]
        async_add_entities(entities)

class SystemStateSwitch(SwitchEntity):
    """Select component to set system state """
    _attr_has_entity_name = True

    def __init__(self,
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__()
        self._device = device
        self._attr_name = f"{device.name} Global HVAC State"
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}-Global-HVACState-switch"
        self._is_on = bool(int(self._device.sys_state))

    async def async_turn_on(self, **kwargs):
        """ Turn the entity on. """
        self._is_on = True
        await self._device.set_sys_state(SysState.SYS_STATE_ON)

    async def async_turn_off(self, **kwargs):
        """ Turn the entity off. """
        self._is_on = False
        await self._device.set_sys_state(SysState.SYS_STATE_OFF)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """ Retrieve latest state. """
        self._is_on = bool(int(self._device.sys_state))

    @property
    def is_on(self):
        """ If the switch is currently on or off. """
        return self._is_on

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:power"
    
    @property
    def should_poll(self) -> bool:
        """ Do not poll for this entity """
        return False