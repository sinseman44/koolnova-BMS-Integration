""" for Climate integration. """
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import (
    ClimateEntity,
    ConfigEntry,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
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

from .coordinator import KoolnovaCoordinator

from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from .koolnova.device import Koolnova, Area
from .koolnova.const import (
    MIN_TEMP_ORDER,
    MAX_TEMP_ORDER,
    STEP_TEMP_ORDER,
    SysState,
    ZoneState,
    ZoneClimMode,
    ZoneFanMode,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback
                            ) -> None:
    """Setup switch entries"""

    entities = []
    coordinator = hass.data[DOMAIN]["coordinator"]
    device = hass.data[DOMAIN]["device"]

    for area in device.areas:
        entities.append(AreaClimateEntity(coordinator, device, area))
    async_add_entities(entities)

class AreaClimateEntity(CoordinatorEntity, ClimateEntity):
    """ Reperesentation of a climate entity """
    # pylint: disable = too-many-instance-attributes

    _attr_supported_features: int = SUPPORT_FLAGS
    _attr_temperature_unit: str = UnitOfTemperature.CELSIUS
    _attr_hvac_modes: list[HVACMode] = SUPPORTED_HVAC_MODES
    _attr_fan_modes: list[str] = SUPPORTED_FAN_MODES
    _attr_hvac_mode: HVACMode = HVACMode.OFF
    _attr_fan_mode: str = FAN_OFF
    _attr_min_temp: float = MIN_TEMP_ORDER
    _attr_max_temp: float = MAX_TEMP_ORDER
    _attr_precision: float = STEP_TEMP_ORDER
    _attr_target_temperature_high: float = MAX_TEMP_ORDER
    _attr_target_temperature_low: float = MIN_TEMP_ORDER
    _attr_target_temperature_step: float = STEP_TEMP_ORDER
    _enable_turn_on_off_backwards_compatibility: bool = False

    def __init__(self,
                coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                device: Koolnova, # pylint: disable=unused-argument
                area: Area, # pylint: disable=unused-argument
                ) -> None:
        """ Class constructor """
        super().__init__(coordinator)
        self._device = device
        self._area = area
        self._attr_name = f"{self._device.name} {self._area.name}"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{self._area.name}-area-climate"
        self._attr_current_temperature = self._area.real_temp
        self._attr_target_temperature = self._area.order_temp
        self._attr_fan_mode = FAN_TRANSLATION[int(self._area.fan_mode)]
        self._attr_hvac_mode = self._translate_to_hvac_mode()

    def _translate_to_hvac_mode(self) -> int:
        """ translate area state and clim mode to HA hvac mode """
        ret = 0
        if self._area.state == ZoneState.STATE_OFF:
            ret = HVACMode.OFF
        else:
            ret = HVAC_TRANSLATION[int(self._area.clim_mode)]

        return ret

    async def async_set_temperature(self,
                                    **kwargs,
                                    ) -> None:
        """ set new target temperature """
        _LOGGER.debug("[Climate {}] set target temp - kwargs: {}".format(self._area.id_zone, kwargs))
        if "temperature" in kwargs:
            target_temp = kwargs.get("temperature")
            ret = await self._device.async_set_area_target_temp(zone_id = self._area.id_zone, temp = target_temp)
            if not ret:
                _LOGGER.error("Error sending target temperature for area id {}".format(self._area.id_zone))
        else:
            _LOGGER.warning("Target temperature not defined for climate id {}".format(self._area.id_zone))
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self,
                                    fan_mode:str,
                                    ) -> None:
        """ set new target fan mode """
        _LOGGER.debug("[Climate {}] set new fan mode: {}".format(self._area.id_zone, fan_mode))
        for k,v in FAN_TRANSLATION.items():
            if v == fan_mode:
                opt = k
                break
        ret = await self._device.async_set_area_fan_mode(zone_id = self._area.id_zone,
                                                            mode = ZoneFanMode(opt))
        if not ret:
            _LOGGER.exception("Error setting new fan value for area id {}".format(self._area.id_zone))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self,
                                    hvac_mode:HVACMode,
                                    ) -> None:
        """ set new target hvac mode """
        _LOGGER.debug("[Climate {}] set new hvac mode: {}".format(self._area.id_zone, hvac_mode))
        opt = 0
        for k,v in HVAC_TRANSLATION.items():
            if v == hvac_mode:
                opt = k
                break
        ret = await self._device.async_set_area_clim_mode(zone_id = self._area.id_zone, 
                                                            mode = ZoneClimMode(opt))
        if not ret:
            _LOGGER.exception("Error setting new hvac value for area id {}".format(self._area.id_zone))
        await self.coordinator.async_request_refresh()
        
    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        _LOGGER.debug("[Climate {}] turn off".format(self._area.id_zone))
        ret = await self._device.async_set_area_off(zone_id = self._area.id_zone)
        if not ret:
            _LOGGER.exception("Error setting off HVAC for area id {}".format(self._area.id_zone))
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        _LOGGER.debug("[Climate {}] turn on".format(self._area.id_zone))
        ret = await self._device.async_set_area_on(zone_id = self._area.id_zone)
        if not ret:
            _LOGGER.exception("Error setting on HVAC for area id {}".format(self._area.id_zone))
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator """
        for _cur_area in self.coordinator.data['areas']:
            if _cur_area.id_zone == self._area.id_zone:
                _LOGGER.debug("[UPDATE] [Climate {}] temp:{} - target:{} - state: {} - hvac:{} - fan:{}".format(_cur_area.id_zone,
                                                                                                        _cur_area.real_temp,
                                                                                                        _cur_area.order_temp,
                                                                                                        _cur_area.state,
                                                                                                        _cur_area.clim_mode,
                                                                                                        _cur_area.fan_mode))
                self._area = _cur_area
                self._attr_current_temperature = _cur_area.real_temp
                self._attr_target_temperature = _cur_area.order_temp
                if _cur_area.state == ZoneState.STATE_OFF:
                    self._attr_hvac_mode = HVACMode.OFF
                else:
                    self._attr_hvac_mode = HVAC_TRANSLATION[int(_cur_area.clim_mode)]
                self._attr_fan_mode = FAN_TRANSLATION[int(_cur_area.fan_mode)]
        self.async_write_ha_state()
