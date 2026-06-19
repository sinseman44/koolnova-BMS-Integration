""" for number components """
# pylint: disable = too-few-public-methods

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfTime,
)

from .const import (
    DOMAIN
)

from .coordinator import KoolnovaCoordinator

from .koolnova.device import (
    Koolnova,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback,
                            ):
    """ Setup number entries """

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    device = runtime_data["device"]
    coordinator = runtime_data["coordinator"]

    entities = []
    if device.table_version == "v2":
        entities.extend(_build_v2_number_entities(coordinator, device))
    else:
        _LOGGER.debug("Skip Koolnova v2 numbers for table version %s", device.table_version)

    async_add_entities(entities)

def _build_v2_number_entities(coordinator: KoolnovaCoordinator,
                                device: Koolnova,
                                ) -> list[NumberEntity]:
    """Build number entities that only exist for the Koolnova v2 Modbus table."""
    entities = []
    entities.append(V2TemperatureLimitNumber(coordinator, device,
                                                "max_heating_limit",
                                                "V2 maximum heating limit",
                                                0,
                                                255))
    entities.append(V2TemperatureLimitNumber(coordinator, device,
                                                "min_cooling_limit",
                                                "V2 minimum cooling limit",
                                                0,
                                                255))
    entities.append(V2PumpValveNumber(coordinator, device,
                                        "valve_origin_offset",
                                        "V2 valve origin offset",
                                        0,
                                        7,
                                        None))
    entities.append(V2PumpValveNumber(coordinator, device,
                                        "pump_delay_seconds",
                                        "V2 pump delay",
                                        60,
                                        255,
                                        UnitOfTime.SECONDS))
    entities.append(V2ImmersionHeaterNumber(coordinator, device,
                                            "activation_delay_minutes",
                                            "V2 immersion heater delay",
                                            0,
                                            255,
                                            UnitOfTime.MINUTES))
    entities.append(V2ImmersionHeaterNumber(coordinator, device,
                                            "activation_temperature_celsius",
                                            "V2 immersion heater activation temperature",
                                            -128,
                                            127,
                                            UnitOfTemperature.CELSIUS))
    entities.append(V2AutoModeNumber(coordinator, device,
                                        "cooling_water_threshold_celsius",
                                        "V2 auto cooling water threshold",
                                        0,
                                        255))
    entities.append(V2AutoModeNumber(coordinator, device,
                                        "heating_water_threshold_celsius",
                                        "V2 auto heating water threshold",
                                        0,
                                        255))
    entities.append(V2MixingValveAmbientNumber(coordinator, device,
                                                "upper_ambient_temperature_celsius",
                                                "V2 mixing valve upper ambient temperature",
                                                25,
                                                45))
    entities.append(V2MixingValveAmbientNumber(coordinator, device,
                                                "lower_ambient_temperature_celsius",
                                                "V2 mixing valve lower ambient temperature",
                                                -20,
                                                30))
    entities.append(V2MixingValveWaterNumber(coordinator, device,
                                                "upper_water_temperature_celsius",
                                                "V2 mixing valve upper water temperature",
                                                25,
                                                45))
    entities.append(V2MixingValveWaterNumber(coordinator, device,
                                                "lower_water_temperature_celsius",
                                                "V2 mixing valve lower water temperature",
                                                25,
                                                45))
    entities.append(V2MixingValveModeNumber(coordinator, device,
                                            "cooling_supply_temperature_celsius",
                                            "V2 mixing valve cooling supply temperature",
                                            10,
                                            22))
    entities.append(V2MixingValveModeNumber(coordinator, device,
                                            "heating_supply_temperature_celsius",
                                            "V2 mixing valve heating supply temperature",
                                            25,
                                            45))
    return entities

class V2RegisterNumber(CoordinatorEntity, NumberEntity):
    # pylint: disable = too-many-instance-attributes
    """Base number entity for a Koolnova v2 register field."""

    _attr_entity_category: EntityCategory = EntityCategory.CONFIG
    _attr_mode: NumberMode = NumberMode.BOX
    _attr_native_step: int = 1

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    register_key:str,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    unit:str | None = UnitOfTemperature.CELSIUS,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator)
        self._device = device
        self._register_key = register_key
        self._field = field
        self._attr_name = f"{self._device.name} {name}"
        self._attr_device_info = self._device.device_info
        self._attr_unique_id = f"{DOMAIN}-{self._device.name}-{self._register_key}-{self._field}-number"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_unit_of_measurement = unit

    def _register_value(self) -> dict:
        """Return the current decoded register value from coordinator data."""
        return self.coordinator.data.get("v2_registers", {}).get(
            self._register_key,
            self._device.v2_registers.get(self._register_key, {}),
        )

    def _value_from_registers(self,
                                registers: dict,
                                ):
        """Read this number value from a v2 register snapshot."""
        value = registers.get(self._register_key, {})
        if isinstance(value, dict):
            return value.get(self._field)
        return None

    @property
    def native_value(self):
        """Return the current number value."""
        return self._value_from_registers(
            self.coordinator.data.get("v2_registers", self._device.v2_registers)
        )

class V2TemperatureLimitNumber(V2RegisterNumber):
    """Number entity for v2 temperature limits."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40076_temperature_limits", field,
                            name, min_value, max_value, UnitOfTemperature.CELSIUS)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        max_heating_limit = register["max_heating_limit"]
        min_cooling_limit = register["min_cooling_limit"]
        if self._field == "max_heating_limit":
            max_heating_limit = int(value)
        else:
            min_cooling_limit = int(value)
        await self._device.async_set_v2_temperature_limits(max_heating_limit, min_cooling_limit)
        await self.coordinator.async_request_refresh()

class V2PumpValveNumber(V2RegisterNumber):
    """Number entity for v2 pump delay and valve offset."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    unit:str | None,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40086_pump_delay_valve_offset", field,
                            name, min_value, max_value, unit)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        valve_origin_offset = register["valve_origin_offset"]
        pump_delay_seconds = register["pump_delay_seconds"]
        if self._field == "valve_origin_offset":
            valve_origin_offset = int(value)
        else:
            pump_delay_seconds = int(value)
        await self._device.async_set_v2_pump_delay_valve_offset(valve_origin_offset, pump_delay_seconds)
        await self.coordinator.async_request_refresh()

class V2ImmersionHeaterNumber(V2RegisterNumber):
    """Number entity for v2 immersion heater settings."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    unit:str | None,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40087_immersion_heater", field,
                            name, min_value, max_value, unit)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        activation_delay_minutes = register["activation_delay_minutes"]
        activation_temperature_celsius = register["activation_temperature_celsius"]
        if self._field == "activation_delay_minutes":
            activation_delay_minutes = int(value)
        else:
            activation_temperature_celsius = int(value)
        await self._device.async_set_v2_immersion_heater(
            activation_delay_minutes,
            activation_temperature_celsius,
        )
        await self.coordinator.async_request_refresh()

class V2AutoModeNumber(V2RegisterNumber):
    """Number entity for v2 automatic mode water thresholds."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40089_auto_mode", field,
                            name, min_value, max_value, UnitOfTemperature.CELSIUS)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        cooling_water_threshold_celsius = register["cooling_water_threshold_celsius"]
        heating_water_threshold_celsius = register["heating_water_threshold_celsius"]
        if self._field == "cooling_water_threshold_celsius":
            cooling_water_threshold_celsius = int(value)
        else:
            heating_water_threshold_celsius = int(value)
        await self._device.async_set_v2_auto_mode(
            cooling_water_threshold_celsius,
            heating_water_threshold_celsius,
        )
        await self.coordinator.async_request_refresh()

class V2MixingValveAmbientNumber(V2RegisterNumber):
    """Number entity for v2 mixing valve ambient temperatures."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40090_mixing_valve_ambient_temperatures",
                            field, name, min_value, max_value, UnitOfTemperature.CELSIUS)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        upper_ambient_temperature_celsius = register["upper_ambient_temperature_celsius"]
        lower_ambient_temperature_celsius = register["lower_ambient_temperature_celsius"]
        if self._field == "upper_ambient_temperature_celsius":
            upper_ambient_temperature_celsius = int(value)
        else:
            lower_ambient_temperature_celsius = int(value)
        await self._device.async_set_v2_mixing_valve_ambient_temperatures(
            upper_ambient_temperature_celsius,
            lower_ambient_temperature_celsius,
        )
        await self.coordinator.async_request_refresh()

class V2MixingValveWaterNumber(V2RegisterNumber):
    """Number entity for v2 mixing valve water temperatures."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40091_mixing_valve_water_temperatures",
                            field, name, min_value, max_value, UnitOfTemperature.CELSIUS)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        upper_water_temperature_celsius = register["upper_water_temperature_celsius"]
        lower_water_temperature_celsius = register["lower_water_temperature_celsius"]
        if self._field == "upper_water_temperature_celsius":
            upper_water_temperature_celsius = int(value)
        else:
            lower_water_temperature_celsius = int(value)
        await self._device.async_set_v2_mixing_valve_water_temperatures(
            upper_water_temperature_celsius,
            lower_water_temperature_celsius,
        )
        await self.coordinator.async_request_refresh()

class V2MixingValveModeNumber(V2RegisterNumber):
    """Number entity for v2 mixing valve mode temperatures."""

    def __init__(self,
                    coordinator: KoolnovaCoordinator,
                    device: Koolnova,
                    field:str,
                    name:str,
                    min_value:int,
                    max_value:int,
                    ) -> None:
        """Class constructor."""
        super().__init__(coordinator, device, "40092_mixing_valve_mode_info",
                            field, name, min_value, max_value, UnitOfTemperature.CELSIUS)

    async def async_set_native_value(self,
                                        value: float,
                                        ) -> None:
        """Set the number value."""
        register = self._register_value()
        cooling_supply_temperature_celsius = register["cooling_supply_temperature_celsius"]
        heating_supply_temperature_celsius = register["heating_supply_temperature_celsius"]
        if self._field == "cooling_supply_temperature_celsius":
            cooling_supply_temperature_celsius = int(value)
        else:
            heating_supply_temperature_celsius = int(value)
        await self._device.async_set_v2_mixing_valve_mode_info(
            register["safety_factor_code"],
            register["mode"],
            cooling_supply_temperature_celsius,
            heating_supply_temperature_celsius,
        )
        await self.coordinator.async_request_refresh()
