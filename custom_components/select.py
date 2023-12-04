""" for select component """
# pylint: disable = too-few-public-methods

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.select import SelectEntity
from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    GLOBAL_MODES,
    GLOBAL_MODE_TRANSLATION,
    EFF_MODES,
    EFF_TRANSLATION,
)
from homeassistant.const import UnitOfTime
from .koolnova.device import Koolnova
from .koolnova.const import (
    GlobalMode,
    Efficiency,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    """Setup select entries"""

    for device in hass.data[DOMAIN]:
        _LOGGER.debug("Device: {}".format(device))
        entities = [
            GlobalModeSelect(device),
            EfficiencySelect(device),
        ]
        async_add_entities(entities)

class GlobalModeSelect(SelectEntity):
    """Select component to set Global Mode """

    def __init__(self, 
                    device: Koolnova,
                ) -> None:
        super().__init__()
        self._attr_options = GLOBAL_MODES
        self._device = device
        self._attr_name = f"{device.name} Global Mode"
        self._attr_device_info = device.device_info
        self._attr_icon = "mdi:cog-clockwise"
        self._attr_unique_id = f"{DOMAIN}-GlobalMode-select"
        self.select_option(
            GLOBAL_MODE_TRANSLATION[int(self._device.global_mode)]
        )

    def _update_state(self) -> None:
        """ update global mode """
        _LOGGER.debug("[GLOBAL MODE] _update_state")
        self.select_option(
            GLOBAL_MODE_TRANSLATION[int(self._device.global_mode)]
        )

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug("[GLOBAL MODE] select_option: {}".format(option))
        self._attr_current_option = option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug("[GLOBAL_MODE] async_select_option: {}".format(option))
        opt = 0
        for k,v in GLOBAL_MODE_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.set_global_mode(GlobalMode(opt))
        self.select_option(option)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.debug("[GLOBAL MODE] async_update")
        #await self._device.update()
        self._update_state()

class EfficiencySelect(SelectEntity):
    """Select component to set Efficiency """

    def __init__(self, 
                    device: Koolnova,
                ) -> None:
        super().__init__()
        self._attr_options = EFF_MODES
        self._device = device
        self._attr_name = f"{device.name} Efficiency"
        self._attr_device_info = device.device_info
        self._attr_icon = "mdi:wind-power-outline"
        self._attr_unique_id = f"{DOMAIN}-Efficiency-select"
        self.select_option(
            EFF_TRANSLATION[int(self._device.efficiency)]
        )

    def _update_state(self) -> None:
        """ update efficiency """
        _LOGGER.debug("[EFF] _update_state")
        self.select_option(
            EFF_TRANSLATION[int(self._device.efficiency)]
        )

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug("[EFF] select_option: {}".format(option))
        self._attr_current_option = option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug("[EFF] async_select_option: {}".format(option))
        opt = 0
        for k,v in EFF_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.set_efficiency(Efficiency(opt))
        self.select_option(option)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.debug("[EFF] async_update")
        #await self._device.update()
        self._update_state()