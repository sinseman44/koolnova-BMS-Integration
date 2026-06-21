""" for switch component """
# pylint: disable = too-few-public-methods
from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass
)

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

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    device = runtime_data["device"]
    coordinator = runtime_data["coordinator"]

    entities = [
        SystemStateSwitch(coordinator, device),
        DebugStateSwitch(device),
    ]
    if device.table_version == "v2":
        entities.extend(_build_v2_switch_entities(coordinator, device))
    else:
        _LOGGER.debug("Skip Koolnova v2 switches for table version %s", device.table_version)
    async_add_entities(entities)

def _build_v2_switch_entities(coordinator: KoolnovaCoordinator,
                                device: Koolnova,
                                ) -> list[SwitchEntity]:
    """Build switch entities that only exist for the Koolnova v2 Modbus table."""
    entities = []
    entities.append(V2ActiveModeSwitch(coordinator, device, "ventilation", "V2 ventilation mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "cooling", "V2 cooling mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "heating", "V2 heating mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "dehumidification", "V2 dehumidification mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "radiant_floor", "V2 radiant floor mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "radiant_floor_cooling", "V2 radiant floor cooling mode enabled"))
    entities.append(V2ActiveModeSwitch(coordinator, device, "radiant_floor_heating", "V2 radiant floor heating mode enabled"))

    for area in device.areas:
        entities.append(V2ZoneElectrovalveSwitch(coordinator, device, area.id_zone - 1))
    return entities

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
        self._attr_name = f"{self._device.name} Global HVAC State"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Global-HVAC-State-switch"
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

class V2ActiveModeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch component to enable or hide a Koolnova v2 global mode."""

    _attr_has_entity_name: bool = True
    _attr_device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH
    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator)
        self._device = device
        self._field = field
        self._attr_name = f"{self._device.name} {name}"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-40075-{self._field}-switch"

    def _register_value(self) -> dict:
        """Return the decoded active modes register."""
        coordinator_data = self.coordinator.data or {}
        return coordinator_data.get("v2_registers", {}).get(
            "40075_active_modes",
            self._device.v2_registers.get("40075_active_modes", {}),
        )

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._device.async_set_v2_active_modes(**{self._field: True})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._device.async_set_v2_active_modes(**{self._field: False})
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return bool(self._register_value().get(self._field))

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:tune-variant"

class V2ZoneElectrovalveSwitch(CoordinatorEntity, SwitchEntity):
    """Switch component for one Koolnova v2 zone electrovalve mask bit."""

    _attr_has_entity_name: bool = True
    _attr_device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH
    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    zone_index:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator)
        self._device = device
        self._zone_index = zone_index
        self._zone_name = self._zone_display_name()
        self._attr_name = f"{self._device.name} V2 {self._zone_name} electrovalve enabled"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-40085-z{self._zone_index + 1}-pump-switch"

    def _zone_display_name(self) -> str:
        """Return a user-facing zone label for this Modbus zone index."""
        zone_id = self._zone_index + 1
        for area in self._device.areas:
            if area.id_zone == zone_id and area.name:
                return f"Z{zone_id} - {area.name}"
        return f"Z{zone_id}"

    def _register_value(self) -> dict:
        """Return the decoded valve mask register."""
        coordinator_data = self.coordinator.data or {}
        return coordinator_data.get("v2_registers", {}).get(
            "40085_valve_mask",
            self._device.v2_registers.get("40085_valve_mask", {}),
        )

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._device.async_set_v2_zone_pump_enabled(self._zone_index, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._device.async_set_v2_zone_pump_enabled(self._zone_index, False)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        zone_pump_enabled = self._register_value().get("zone_pump_enabled", {})
        return bool(zone_pump_enabled.get(self._zone_index))

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:valve"

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
        self._attr_name = f"{self._device.name} Modbus Debug"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Modbus-Debug-switch"
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
