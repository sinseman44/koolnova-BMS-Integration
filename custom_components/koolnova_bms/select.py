""" for select component """
# pylint: disable = too-few-public-methods

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN,
    GLOBAL_MODES,
    GLOBAL_MODES_V2,
    GLOBAL_MODE_TRANSLATION,
    EFF_MODES,
    EFF_TRANSLATION,
    ENGINE_FLOW_MODES,
    ENGINE_FLOW_TRANSLATION,
)

from .coordinator import KoolnovaCoordinator

from .koolnova.device import (
    Koolnova,
    Engine,
    Area,
)

from .koolnova.const import (
    GlobalMode,
    Efficiency,
    FlowEngine,
)

_LOGGER = logging.getLogger(__name__)

V2_GLOBAL_MODE_ACTIVE_FIELD = {
    int(GlobalMode.VENTILATION): "ventilation",
    int(GlobalMode.COLD): "cooling",
    int(GlobalMode.HEAT): "heating",
    int(GlobalMode.DEHUMIDIFICATION): "dehumidification",
    int(GlobalMode.HEATING_FLOOR): "radiant_floor_heating",
    int(GlobalMode.REFRESHING_FLOOR): "radiant_floor_cooling",
    int(GlobalMode.HEATING_FLOOR_2): "radiant_floor",
}

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback,
                            ):
    """ Setup select entries """

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    device = runtime_data["device"]
    coordinator = runtime_data["coordinator"]

    entities = [
        GlobalModeSelect(coordinator, device),
    ]
    if device.supports_efficiency:
        entities.append(EfficiencySelect(coordinator, device))

    for engine in device.engines:
        entities.append(EngineStateSelect(coordinator, device, engine))
    if device.table_version == "v2":
        entities.extend(_build_v2_select_entities(coordinator, device))
    else:
        _LOGGER.debug("Skip Koolnova v2 selects for table version %s", device.table_version)
    async_add_entities(entities)

def _build_v2_select_entities(coordinator: KoolnovaCoordinator,
                                device: Koolnova,
                                ) -> list[SelectEntity]:
    """Build select entities that only exist for the Koolnova v2 Modbus table."""
    entities = [
        V2EfiSelect(coordinator, device),
        V2AutoChangeoverModeSelect(
            coordinator,
            device,
            "mode_when_water_above_threshold",
            "V2 auto changeover mode above heating water threshold",
            {
                "radiant_floor_heating": 0x04,
                "radiant_floor_heating_and_heating": 0x06,
                "heating": 0x02,
            },
        ),
        V2AutoChangeoverModeSelect(
            coordinator,
            device,
            "mode_when_water_below_threshold",
            "V2 auto changeover mode below cooling water threshold",
            {
                "cooling": 0x01,
                "radiant_floor_cooling_and_cooling": 0x05,
            },
        ),
        V2ExternalInputSelect(coordinator, device, "din1_function", "V2 DIN1 function"),
        V2ExternalInputSelect(coordinator, device, "din2_function", "V2 DIN2 function"),
    ]
    for area in device.areas:
        if area.id_zone < 1 or area.id_zone > 16:
            continue
        entities.append(V2OpeningAngleAreaSelect(coordinator, device, area))

    entities.extend([
        V2ThermostatBlockSelect(coordinator, device),
        V2MixingValveSafetyFactorSelect(coordinator, device),
        V2MixingValveModeSelect(coordinator, device, "cooling_mode", "V2 mixing valve cooling mode"),
        V2MixingValveModeSelect(coordinator, device, "heating_mode", "V2 mixing valve heating mode"),
    ])
    return entities

class GlobalModeSelect(CoordinatorEntity, SelectEntity):
    """ Select component to set global HVAC mode """

    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_options = self.__global_mode_options()
        self._attr_name = f"{self._device.name} global HVAC mode"
        self._attr_device_info = device.device_info
        self._attr_icon = "mdi:cog-clockwise"
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Global-HVACMode-select"
        self.__select_option(
            GLOBAL_MODE_TRANSLATION.get(int(self._device.global_mode), GLOBAL_MODES[0])
        )

    def __select_option(self, option: str) -> None:
        """ Change the selected option. """
        self._attr_options = self.__global_mode_options()
        self._attr_current_option = option

    def __global_mode_options(self) -> list[str]:
        """Return global mode options enabled by register 40075 for v2 tables."""
        if self._device.table_version != "v2":
            return GLOBAL_MODES

        coordinator_data = self.coordinator.data or {}
        active_modes = coordinator_data.get("v2_registers", {}).get(
            "40075_active_modes",
            self._device.v2_registers.get("40075_active_modes", {}),
        )
        if not active_modes:
            return GLOBAL_MODES_V2

        return [
            mode_name
            for mode_value, mode_name in GLOBAL_MODE_TRANSLATION.items()
            if active_modes.get(V2_GLOBAL_MODE_ACTIVE_FIELD.get(mode_value), False)
        ]

    async def async_select_option(self, option: str) -> None:
        """ Change the selected option. """
        if option not in self.options:
            raise ValueError(f"Invalid global mode option: {option}")
        opt = 0
        for k,v in GLOBAL_MODE_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.async_set_global_mode(GlobalMode(opt))
        self.__select_option(option)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator 
            Retrieve latest state of global mode """
        _LOGGER.debug("[UPDATE] Global Mode: {}".format(self.coordinator.data['glob']))
        self.__select_option(
            GLOBAL_MODE_TRANSLATION.get(int(self.coordinator.data['glob']), GLOBAL_MODES[0])
        )
        self.async_write_ha_state()

class V2RegisterSelect(CoordinatorEntity, SelectEntity):
    """Base select component backed by a decoded Koolnova v2 register."""

    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    register_key:str,
                    name:str,
                    unique_suffix:str,
                    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._register_key = register_key
        self._attr_name = f"{self._device.name} {name}"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{unique_suffix}-select"

    def _register_value(self) -> dict:
        """Return the decoded register value from the latest coordinator snapshot."""
        coordinator_data = self.coordinator.data or {}
        return coordinator_data.get("v2_registers", {}).get(
            self._register_key,
            self._device.v2_registers.get(self._register_key, {}),
        )

    def _required_register_value(self, field:str) -> int:
        """Return one register field or fail before writing an incomplete register."""
        value = self._register_value().get(field)
        if value is None:
            raise ValueError(f"Missing {field} in {self._register_key}")
        return int(value)

class V2EfiSelect(V2RegisterSelect):
    """Select component for the EFI field in register 40074."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40074_parameters",
            "V2 EFI",
            "40074-efi",
        )
        self._attr_options = [str(value) for value in range(8)]
        self._attr_icon = "mdi:fan-speed-3"

    @property
    def current_option(self) -> str | None:
        """Return the selected EFI code."""
        value = self._register_value().get("efi")
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Change the selected EFI code."""
        if option not in self.options:
            raise ValueError(f"Invalid EFI option: {option}")
        await self._device.async_set_v2_parameters(efi=int(option))
        await self.coordinator.async_request_refresh()

class V2AutoChangeoverModeSelect(V2RegisterSelect):
    """Select component for one mode nibble in register 40077."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    options:dict[str, int],
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40077_auto_changeover_humidity",
            name,
            f"40077-{field}",
        )
        self._field = field
        self._options_by_name = options
        self._names_by_option = {value: key for key, value in options.items()}
        self._attr_options = list(options)
        self._attr_icon = "mdi:swap-horizontal"

    @property
    def current_option(self) -> str | None:
        """Return the selected automatic changeover mode."""
        value = self._register_value().get(self._field)
        return self._names_by_option.get(value)

    async def async_select_option(self, option: str) -> None:
        """Change one automatic changeover mode."""
        if option not in self._options_by_name:
            raise ValueError(f"Invalid automatic changeover option: {option}")
        mode_when_above = self._required_register_value("mode_when_water_above_threshold")
        mode_when_below = self._required_register_value("mode_when_water_below_threshold")
        if self._field == "mode_when_water_above_threshold":
            mode_when_above = self._options_by_name[option]
        else:
            mode_when_below = self._options_by_name[option]
        await self._device.async_set_v2_auto_changeover_humidity(
            mode_when_above,
            mode_when_below,
            self._required_register_value("humidity_relay_threshold"),
        )
        await self.coordinator.async_request_refresh()

class V2ExternalInputSelect(V2RegisterSelect):
    """Select component for one external input function in register 40079."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40079_external_inputs",
            name,
            f"40079-{field}",
        )
        self._field = field
        self._attr_options = [str(value) for value in range(16)]
        self._attr_icon = "mdi:electric-switch"

    @property
    def current_option(self) -> str | None:
        """Return the selected input function code."""
        value = self._register_value().get(self._field)
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Change one external input function code."""
        if option not in self.options:
            raise ValueError(f"Invalid external input option: {option}")
        din2_function = self._required_register_value("din2_function")
        din1_function = self._required_register_value("din1_function")
        if self._field == "din2_function":
            din2_function = int(option)
        else:
            din1_function = int(option)
        await self._device.async_set_v2_external_inputs(
            din2_function,
            din1_function,
        )
        await self.coordinator.async_request_refresh()

class V2OpeningAngleZoneSelect(V2RegisterSelect):
    """Select component for the target area field in registers 40080 and 40081."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    register_key:str,
                    name:str,
                    zone_indexes:range,
                    setter,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            register_key,
            name,
            f"{register_key}-zone-index",
        )
        self._setter = setter
        self._options_by_zone_index = self._area_options_by_zone_index(
            device.areas,
            zone_indexes,
        )
        self._zone_index_by_option = {
            option: zone_index
            for zone_index, option in self._options_by_zone_index.items()
        }
        self._attr_options = list(self._options_by_zone_index.values())
        self._attr_icon = "mdi:map-marker-radius"

    @staticmethod
    def _area_options_by_zone_index(areas:list[Area],
                                    zone_indexes:range,
                                    ) -> dict[int, str]:
        """Return Home Assistant options keyed by the Modbus zone index."""
        areas_by_zone_id = {
            area.id_zone: area
            for area in areas
        }
        options = {}
        for zone_index in zone_indexes:
            zone_id = zone_index + 1
            area = areas_by_zone_id.get(zone_id)
            if area is None or not area.name:
                options[zone_index] = f"Z{zone_id}"
            else:
                options[zone_index] = f"Z{zone_id} - {area.name}"
        return options

    @property
    def current_option(self) -> str | None:
        """Return the selected target area."""
        value = self._register_value().get("zone_index")
        return self._options_by_zone_index.get(value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected target area."""
        if option not in self._zone_index_by_option:
            raise ValueError(f"Invalid target area option: {option}")
        await self._setter(
            self._required_register_value("angle_code"),
            self._zone_index_by_option[option],
        )
        await self.coordinator.async_request_refresh()

class V2OpeningAngleValueSelect(V2RegisterSelect):
    """Select component for the opening angle field in registers 40080 and 40081."""

    _ANGLE_CODES = {
        "45": 0x00,
        "60": 0x01,
        "75": 0x02,
        "90": 0x03,
    }
    _ANGLE_BY_CODE = {value: key for key, value in _ANGLE_CODES.items()}

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    register_key:str,
                    name:str,
                    setter,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            register_key,
            name,
            f"{register_key}-angle",
        )
        self._setter = setter
        self._attr_options = list(self._ANGLE_CODES)
        self._attr_icon = "mdi:angle-acute"

    @property
    def current_option(self) -> str | None:
        """Return the selected opening angle."""
        value = self._register_value().get("angle_code")
        return self._ANGLE_BY_CODE.get(value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected opening angle."""
        if option not in self._ANGLE_CODES:
            raise ValueError(f"Invalid opening angle option: {option}")
        await self._setter(
            self._ANGLE_CODES[option],
            self._required_register_value("zone_index"),
        )
        await self.coordinator.async_request_refresh()

class V2OpeningAngleAreaSelect(V2RegisterSelect):
    """Select component to set one configured zone opening angle directly."""

    _ANGLE_CODES = V2OpeningAngleValueSelect._ANGLE_CODES
    _ANGLE_BY_CODE = V2OpeningAngleValueSelect._ANGLE_BY_CODE

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    area: Area,
                    ) -> None:
        self._area = area
        self._zone_index = area.id_zone - 1
        self._setter = (
            device.async_set_v2_opening_angle_z1_z8
            if self._zone_index < 8
            else device.async_set_v2_opening_angle_z9_z16
        )
        register_key = (
            "40080_opening_angle_z1_z8"
            if self._zone_index < 8
            else "40081_opening_angle_z9_z16"
        )
        super().__init__(
            coordinator,
            device,
            register_key,
            f"V2 {self._area_label()} opening angle",
            f"{register_key}-z{area.id_zone}-angle",
        )
        self._attr_options = list(self._ANGLE_CODES)
        self._attr_icon = "mdi:angle-acute"

    def _area_label(self) -> str:
        """Return a user-facing zone label."""
        if self._area.name:
            return f"Z{self._area.id_zone} - {self._area.name}"
        return f"Z{self._area.id_zone}"

    @property
    def current_option(self) -> str | None:
        """Return the selected angle when the shared register targets this zone."""
        register_value = self._register_value()
        if register_value.get("zone_index") != self._zone_index:
            return None
        return self._ANGLE_BY_CODE.get(register_value.get("angle_code"))

    async def async_select_option(self, option: str) -> None:
        """Change this configured zone opening angle."""
        if option not in self._ANGLE_CODES:
            raise ValueError(f"Invalid opening angle option: {option}")
        await self._setter(
            self._ANGLE_CODES[option],
            self._zone_index,
        )
        await self.coordinator.async_request_refresh()

class V2ThermostatBlockSelect(V2RegisterSelect):
    """Select component for the thermostat block level in register 40088."""

    _BLOCK_OPTIONS = [
        "0 no block",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15 total block",
    ]

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40088_thermostat_block",
            "V2 thermostat block",
            "40088-block-level",
        )
        self._attr_options = self._BLOCK_OPTIONS
        self._attr_icon = "mdi:lock-outline"

    @property
    def current_option(self) -> str | None:
        """Return the selected thermostat block level."""
        value = self._register_value().get("block_level")
        if value is None or value < 0 or value >= len(self._BLOCK_OPTIONS):
            return None
        return self._BLOCK_OPTIONS[value]

    async def async_select_option(self, option: str) -> None:
        """Change the selected thermostat block level."""
        if option not in self._BLOCK_OPTIONS:
            raise ValueError(f"Invalid thermostat block option: {option}")
        await self._device.async_set_v2_thermostat_block(
            self._BLOCK_OPTIONS.index(option)
        )
        await self.coordinator.async_request_refresh()

class V2MixingValveSafetyFactorSelect(V2RegisterSelect):
    """Select component for the safety factor field in register 40092."""

    _SAFETY_FACTOR_CODES = {
        "0": 0x00,
        "2": 0x01,
        "-2": 0x02,
    }
    _SAFETY_FACTOR_BY_CODE = {value: key for key, value in _SAFETY_FACTOR_CODES.items()}

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40092_mixing_valve_mode_info",
            "V2 mixing valve safety factor",
            "40092-safety-factor",
        )
        self._attr_options = list(self._SAFETY_FACTOR_CODES)
        self._attr_icon = "mdi:shield-half-full"

    @property
    def current_option(self) -> str | None:
        """Return the selected mixing valve safety factor."""
        value = self._register_value().get("safety_factor_code")
        return self._SAFETY_FACTOR_BY_CODE.get(value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected mixing valve safety factor."""
        if option not in self._SAFETY_FACTOR_CODES:
            raise ValueError(f"Invalid safety factor option: {option}")
        await self._device.async_set_v2_mixing_valve_mode_info(
            self._SAFETY_FACTOR_CODES[option],
            self._required_register_value("mode"),
            self._required_register_value("cooling_supply_temperature_celsius"),
            self._required_register_value("heating_supply_temperature_celsius"),
        )
        await self.coordinator.async_request_refresh()

class V2MixingValveModeSelect(V2RegisterSelect):
    """Select component for one mode bit in register 40092."""

    _COOLING_MODE_OPTIONS = ["fixed", "dew_point"]
    _HEATING_MODE_OPTIONS = ["fixed", "curve"]

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    ) -> None:
        super().__init__(
            coordinator,
            device,
            "40092_mixing_valve_mode_info",
            name,
            f"40092-{field}",
        )
        self._field = field
        self._attr_options = (
            self._COOLING_MODE_OPTIONS
            if field == "cooling_mode"
            else self._HEATING_MODE_OPTIONS
        )
        self._attr_icon = "mdi:valve"

    @property
    def current_option(self) -> str | None:
        """Return the selected mixing valve mode."""
        value = self._register_value().get(self._field)
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Change one mixing valve mode bit."""
        if option not in self.options:
            raise ValueError(f"Invalid mixing valve mode option: {option}")
        mode = self._required_register_value("mode")
        if self._field == "cooling_mode":
            mode = (mode | 0x02) if option == "dew_point" else (mode & ~0x02)
        else:
            mode = (mode | 0x01) if option == "curve" else (mode & ~0x01)
        await self._device.async_set_v2_mixing_valve_mode_info(
            self._required_register_value("safety_factor_code"),
            mode,
            self._required_register_value("cooling_supply_temperature_celsius"),
            self._required_register_value("heating_supply_temperature_celsius"),
        )
        await self.coordinator.async_request_refresh()

class EfficiencySelect(CoordinatorEntity, SelectEntity):
    """Select component to set global efficiency """

    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                ) -> None:
        super().__init__(coordinator)
        self._attr_options = EFF_MODES
        self._device = device
        self._attr_name = f"{self._device.name} global HVAC efficiency"
        self._attr_device_info = self._device.device_info
        self._attr_icon = "mdi:wind-power-outline"
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Global-HVACEff-select"
        self.__select_option(
            EFF_TRANSLATION[int(self._device.efficiency)]
        )

    def __select_option(self,
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
        await self._device.async_set_efficiency(Efficiency(opt))
        self.__select_option(option)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator
            Retrieve latest state of global efficiency """
        _LOGGER.debug("[UPDATE] Efficiency: {}".format(self.coordinator.data['eff']))
        self.__select_option(
            EFF_TRANSLATION[int(self.coordinator.data['eff'])]
        )
        self.async_write_ha_state()

class EngineStateSelect(CoordinatorEntity, SelectEntity):
    """Select component to set flow engine """

    _attr_entity_category: EntityCategory = EntityCategory.CONFIG

    def __init__(self,
                    coordinator: KoolnovaCoordinator, # pylint: disable=unused-argument
                    device: Koolnova, # pylint: disable=unused-argument,
                    engine: Engine, # pylint: disable=unused-argument
                ) -> None:
        super().__init__(coordinator)
        self._attr_options = ENGINE_FLOW_MODES
        self._device = device
        self._engine = engine
        self._attr_name = f"{self._device.name} engine AC{self._engine.engine_id} state"
        self._attr_device_info = self._device.device_info
        self._attr_icon = "mdi:turbine"
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-Engine-AC{self._engine.engine_id}-State-select"
        self.__select_option(
            ENGINE_FLOW_TRANSLATION[int(self._engine.state)]
        )

    def __select_option(self,
                        option: str,
                        ) -> None:
        """ Change the selected option. """
        self._attr_current_option = option

    async def async_select_option(self,
                                    option: str,
                                    ) -> None:
        """ Change the selected option. """
        _LOGGER.debug("[ENGINE FLOW] async_select_option: {}".format(option))
        opt = 0
        for k,v in ENGINE_FLOW_TRANSLATION.items():
            if v == option:
                opt = k
                break
        await self._device.async_set_engine_state(FlowEngine(opt), self._engine.engine_id)
        self.__select_option(option)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """ Handle updated data from the coordinator
            Retrieve latest state of global efficiency """
        for _cur_engine in self.coordinator.data['engines']:
            if self._engine.engine_id == _cur_engine.engine_id:
                _LOGGER.debug("[UPDATE] [ENGINE AC{}] Order temp: {}".format(_cur_engine.engine_id, _cur_engine.state))
                self.__select_option(
                    ENGINE_FLOW_TRANSLATION[int(_cur_engine.state)]
                )
                break
        self.async_write_ha_state()
