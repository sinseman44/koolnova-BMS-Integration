""" for switch component """
# pylint: disable = too-few-public-methods
from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity
from homeassistant.util import Throttle
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
)

from .coordinator import KoolnovaCoordinator

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

    device = hass.data[DOMAIN]["device"]
    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = [
        SystemStateSwitch(coordinator, device),
    ]
    async_add_entities(entities)

class SystemStateSwitch(CoordinatorEntity, SwitchEntity):
    """Select component to set system state """
    _attr_has_entity_name = True

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_name = f"{device.name} Global HVAC State"
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}-Global-HVACState-switch"
        self._is_on = bool(int(self._device.sys_state))

    async def async_turn_on(self, **kwargs):
        """ Turn the entity on. """
        _LOGGER.debug("Turn on system")
        await self._device.set_sys_state(SysState.SYS_STATE_ON)
        self._is_on = True

    async def async_turn_off(self, **kwargs):
        """ Turn the entity off. """
        _LOGGER.debug("Turn off system")
        await self._device.set_sys_state(SysState.SYS_STATE_OFF)
        self._is_on = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator """
        self._is_on = bool(int(self.coordinator.data['sys']))

    @property
    def is_on(self):
        """ If the switch is currently on or off. """
        return self._is_on

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:power"