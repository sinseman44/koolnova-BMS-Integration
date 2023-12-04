""" for Climate integration. """
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import (
    ClimateEntity,
    ConfigEntry,
)

from homeassistant.components.climate.const import (
    HVACMode,
    FAN_AUTO,
    FAN_OFF,
)

from .const import (
    DOMAIN,
    SUPPORT_FLAGS,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
    FAN_TRANSLATION,
    HVAC_TRANSLATION,
)

from homeassistant.const import (
    TEMP_CELSIUS,
    ATTR_TEMPERATURE,
)

from .koolnova.device import Koolnova, Area
from .koolnova.const import (
    MIN_TEMP,
    MAX_TEMP,
    STEP_TEMP,
    MIN_TEMP_ORDER,
    MAX_TEMP_ORDER,
    STEP_TEMP_ORDER,
    SysState,
    ZoneState,
    ZoneClimMode,
    ZoneFanMode,
)

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    """Setup switch entries"""

    entities = []
    for device in hass.data[DOMAIN]:
        for area in device.areas:
            _LOGGER.debug("Device: {} - Area: {}".format(device, area))
            entities.append(AreaClimateEntity(device, area))
        async_add_entities(entities)

class AreaClimateEntity(ClimateEntity):
    """ Reperesentation of a climate entity """
    # pylint: disable = too-many-instance-attributes

    _attr_supported_features: int = SUPPORT_FLAGS
    _attr_temperature_unit: str = TEMP_CELSIUS
    _attr_hvac_modes: list[HVACMode] = SUPPORTED_HVAC_MODES
    _attr_fan_modes: list[str] = SUPPORTED_FAN_MODES
    _attr_hvac_mode: HVACMode = HVACMode.OFF
    _attr_fan_mode: str = FAN_OFF
    _attr_min_temp: float = MIN_TEMP
    _attr_max_temp: float = MAX_TEMP
    _attr_precision: float = STEP_TEMP
    _attr_target_temperature_high: float = MAX_TEMP_ORDER
    _attr_target_temperature_low: float = MIN_TEMP_ORDER
    _attr_target_temperature_step: float = STEP_TEMP_ORDER

    def __init__(self, 
                device: Koolnova, # pylint: disable=unused-argument
                area: Area, # pylint: disable=unused-argument
                ) -> None:
        """ Class constructor """
        self._device = device
        self._area = area
        self._attr_name = f"{device.name} {area.name} area"
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}-{area.name}-area-climate"
        self._attr_current_temperature = area.real_temp
        self._attr_target_temperature = area.order_temp
        _LOGGER.debug("[Climate {}] {} - {}".format(self._area.id_zone, self._area.fan_mode, FAN_TRANSLATION[int(self._area.fan_mode)]))
        self._attr_fan_mode = FAN_TRANSLATION[int(self._area.fan_mode)]
        _LOGGER.debug("[Climate {}] {} - {}".format(self._area.id_zone, self._area.clim_mode, self._translate_to_hvac_mode()))
        self._attr_hvac_mode = self._translate_to_hvac_mode()

    def _translate_to_hvac_mode(self) -> int:
        """ translate area state and clim mode to HA hvac mode """
        ret = 0
        if self._area.state == ZoneState.STATE_OFF:
            ret = HVACMode.OFF
        else:
            ret = HVAC_TRANSLATION[int(self._area.clim_mode)]

        return ret

    async def async_set_temperature(self, **kwargs) -> None:
        """ set new target temperature """
        _LOGGER.debug("[Climate {}] set target temp - kwargs: {}".format(self._area.id_zone, kwargs))
        if "temperature" in kwargs:
            target_temp = kwargs.get("temperature")
            ret = await self._device.set_area_target_temp(zone_id = self._area.id_zone, temp = target_temp)
            if not ret:
                _LOGGER.error("Error sending target temperature for area id {}".format(self._area.id_zone))
        else:
            _LOGGER.warning("Target temperature not defined for climate id {}".format(self._area.id_zone))

    async def async_set_fan_mode(self, fan_mode:str) -> None:
        """ set new target fan mode """
        _LOGGER.debug("[Climate {}] set new fan mode: {}".format(self._area.id_zone, fan_mode))
        for k,v in FAN_TRANSLATION.items():
            if v == fan_mode:
                opt = k
                break
        ret = await self._device.set_area_fan_mode(zone_id = self._area.id_zone,
                                                    mode = ZoneFanMode(opt))
        await self._update_state()

    async def async_set_hvac_mode(self, hvac_mode:HVACMode) -> None:
        """ set new target hvac mode """
        _LOGGER.debug("[Climate {}] set new hvac mode: {}".format(self._area.id_zone, hvac_mode))
        opt = 0
        for k,v in HVAC_TRANSLATION.items():
            if v == hvac_mode:
                opt = k
                break
        ret = await self._device.set_area_clim_mode(zone_id = self._area.id_zone, 
                                                    mode = ZoneClimMode(opt))
        await self._update_state()

    async def async_turn_on(self) -> None:
        """ turn the entity on """
        _LOGGER.debug("[Climate {}] turn on the entity".format(self._area.id_zone))
        #await self._update_state()

    async def async_turn_off(self) -> None:
        """ turn the entity off """
        _LOGGER.debug("[Climate {}] turn off the entity".format(self._area.id_zone))
        #await self._update_state()

    async def _update_state(self) -> None:
        """ Private update attributes """
        _LOGGER.debug("[Climate {}] _update_state".format(self._area.id_zone))
        # retreive current temperature from specific area
        ret, up_area = await self._device.update_area(self._area.id_zone)
        if not ret:
            _LOGGER.error("[Climate {}] Cannot update area values")
            return
        self._area = up_area
        _LOGGER.debug("[Climate {}] temp:{} - target:{} - state: {} - hvac:{} - fan:{}".format(self._area.id_zone,
                                                                                                self._area.real_temp,
                                                                                                self._area.order_temp,
                                                                                                self._area.state,
                                                                                                self._area.clim_mode,
                                                                                                self._area.fan_mode))
        self._attr_current_temperature = self._area.real_temp
        self._attr_target_temperature = self._area.order_temp
        self._attr_hvac_mode = self._translate_to_hvac_mode()
        self._attr_fan_mode = FAN_TRANSLATION[int(self._area.fan_mode)]

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """ Retreive latest values """
        await self._update_state()