""" for select component """
# pylint: disable = too-few-public-methods

import logging

from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.select import SelectEntity
from homeassistant.util import Throttle
from homeassistant.const import UnitOfTime
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    GLOBAL_MODES,
    GLOBAL_MODE_TRANSLATION,
    EFF_MODES,
    EFF_TRANSLATION,
)

from .coordinator import KoolnovaCoordinator

from .koolnova.device import Koolnova
from .koolnova.const import (
    GlobalMode,
    Efficiency,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback,
                            ):
    """ Setup select entries """

    device = hass.data[DOMAIN]["device"]
    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = [
        GlobalModeSelect(coordinator, device),
        EfficiencySelect(coordinator, device),
    ]
    async_add_entities(entities)

class GlobalModeSelect(CoordinatorEntity, SelectEntity):
    """ Select component to set global HVAC mode """

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__(coordinator)
        self._attr_options = GLOBAL_MODES
        self._device = device
        self._attr_name = f"{device.name} Global HVAC Mode"
        self._attr_device_info = device.device_info
        self._attr_icon = "mdi:cog-clockwise"
        self._attr_unique_id = f"{DOMAIN}-Global-HVACMode-select"
        self.select_option(
            GLOBAL_MODE_TRANSLATION[int(self._device.global_mode)]
        )

    def select_option(self, option: str) -> None:
        """ Change the selected option. """
        self._attr_current_option = option

    async def async_select_option(self, option: str) -> None:
        """ Change the selected option. """
        opt = 0
        for k,v in GLOBAL_MODE_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.set_global_mode(GlobalMode(opt))
        self.select_option(option)

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator 
            Retrieve latest state of global mode """
        self.select_option(
            GLOBAL_MODE_TRANSLATION[int(self.coordinator.data['glob'])]
        )

class EfficiencySelect(CoordinatorEntity, SelectEntity):
    """Select component to set global efficiency """

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__(coordinator)
        self._attr_options = EFF_MODES
        self._device = device
        self._attr_name = f"{device.name} Global HVAC Efficiency"
        self._attr_device_info = device.device_info
        self._attr_icon = "mdi:wind-power-outline"
        self._attr_unique_id = f"{DOMAIN}-Global-HVACEff-select"
        self.select_option(
            EFF_TRANSLATION[int(self._device.efficiency)]
        )

    def select_option(self,
                        option: str,
                        ) -> None:
        """ Change the selected option. """
        self._attr_current_option = option

    async def async_select_option(self,
                                    option: str,
                                    ) -> None:
        """ Change the selected option. """
        _LOGGER.debug("[EFF] async_select_option: {}".format(option))
        opt = 0
        for k,v in EFF_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.set_efficiency(Efficiency(opt))
        self.select_option(option)

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator
            Retrieve latest state of global efficiency """
        self.select_option(
            EFF_TRANSLATION[int(self.coordinator.data['eff'])]
        )