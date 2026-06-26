""" consts for koolnova BMS """

from homeassistant.const import Platform
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    FAN_AUTO,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from .koolnova.const import (
    GlobalMode,
    Efficiency,
    FlowEngine,
    ZoneClimMode,
    ZoneFanMode,
    ZoneState,
)

DOMAIN = "koolnova_bms"
PLATFORMS: list[Platform] = [Platform.SENSOR,
                                Platform.NUMBER,
                                Platform.SELECT,
                                Platform.SWITCH,
                                Platform.CLIMATE]

SERVICE_SET_V2_OPENING_ANGLE = "set_v2_opening_angle"
SERVICE_GET_V2_LAST_OPENING_ANGLE = "get_v2_last_opening_angle"

SERVICE_FIELD_ENTRY_ID = "entry_id"
SERVICE_FIELD_ZONE_ID = "zone_id"
SERVICE_FIELD_ANGLE = "angle"

CONF_NAME = "koolnova-BMS-Integration"
CONF_DEVICE_ID = "device_id"

DEVICE_MANUFACTURER = "koolnova"

CONF_UPDATE_INTERVAL = "Update_interval"
DEFAULT_UPDATE_INTERVAL = 30

#MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

GLOBAL_MODE_POS_1 = "cold"
GLOBAL_MODE_POS_2 = "heat"
GLOBAL_MODE_POS_3 = "heating floor"
GLOBAL_MODE_POS_4 = "refreshing floor"
GLOBAL_MODE_POS_5 = "heating floor 2"
GLOBAL_MODE_POS_6 = "ventilation"
GLOBAL_MODE_POS_7 = "dehumidification"

GLOBAL_MODE_TRANSLATION = {
    int(GlobalMode.VENTILATION): GLOBAL_MODE_POS_6,
    int(GlobalMode.COLD): GLOBAL_MODE_POS_1,
    int(GlobalMode.HEAT): GLOBAL_MODE_POS_2,
    int(GlobalMode.DEHUMIDIFICATION): GLOBAL_MODE_POS_7,
    int(GlobalMode.HEATING_FLOOR): GLOBAL_MODE_POS_3,
    int(GlobalMode.REFRESHING_FLOOR): GLOBAL_MODE_POS_4,
    int(GlobalMode.HEATING_FLOOR_2): GLOBAL_MODE_POS_5,
}

GLOBAL_MODES = [
    GLOBAL_MODE_POS_1,
    GLOBAL_MODE_POS_2,
    GLOBAL_MODE_POS_3,
    GLOBAL_MODE_POS_4,
    GLOBAL_MODE_POS_5,
]

GLOBAL_MODES_V2 = [
    GLOBAL_MODE_POS_6,
    GLOBAL_MODE_POS_1,
    GLOBAL_MODE_POS_2,
    GLOBAL_MODE_POS_7,
    GLOBAL_MODE_POS_3,
    GLOBAL_MODE_POS_4,
    GLOBAL_MODE_POS_5,
]

EFF_POS_1 = "lower"
EFF_POS_2 = "low"
EFF_POS_3 = "Medium"
EFF_POS_4 = "High"
EFF_POS_5 = "Higher"

EFF_TRANSLATION = {
    int(Efficiency.LOWER_EFF): EFF_POS_1,
    int(Efficiency.LOW_EFF): EFF_POS_2,
    int(Efficiency.MED_EFF): EFF_POS_3,
    int(Efficiency.HIGH_EFF): EFF_POS_4,
    int(Efficiency.HIGHER_EFF): EFF_POS_5,
}

EFF_MODES = [
    EFF_POS_1,
    EFF_POS_2,
    EFF_POS_3,
    EFF_POS_4,
    EFF_POS_5,
]

ENGINE_FLOW_POS_1 = "Manual minimum"
ENGINE_FLOW_POS_2 = "Manual medium"
ENGINE_FLOW_POS_3 = "Manual High"
ENGINE_FLOW_POS_4 = "Auto"

ENGINE_FLOW_TRANSLATION = {
    int(FlowEngine.MANUAL_MIN): ENGINE_FLOW_POS_1,
    int(FlowEngine.MANUAL_MED): ENGINE_FLOW_POS_2,
    int(FlowEngine.MANUAL_HIGH): ENGINE_FLOW_POS_3,
    int(FlowEngine.AUTO): ENGINE_FLOW_POS_4,
}

ENGINE_FLOW_MODES = [
    ENGINE_FLOW_POS_1,
    ENGINE_FLOW_POS_2,
    ENGINE_FLOW_POS_3,
    ENGINE_FLOW_POS_4,
]

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)

SUPPORTED_HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.HEAT,
]

HVAC_TRANSLATION = {
    int(ZoneState.STATE_OFF): HVACMode.OFF,
    int(ZoneClimMode.COOL): HVACMode.COOL,
    int(ZoneClimMode.HEAT): HVACMode.HEAT,
    int(ZoneClimMode.HEATING_FLOOR): HVACMode.HEAT,
    int(ZoneClimMode.REFRESHING_FLOOR): HVACMode.COOL,
    int(ZoneClimMode.HEATING_FLOOR_2): HVACMode.HEAT,
}

#FAN_MODE_1 = "1 Off"
#FAN_MODE_2 = "2 Low"
#FAN_MODE_3 = "3 Medium"
#FAN_MODE_4 = "4 High"

FAN_TRANSLATION = {
    int(ZoneFanMode.FAN_AUTO): FAN_AUTO,
    int(ZoneFanMode.FAN_OFF): FAN_OFF,
    int(ZoneFanMode.FAN_LOW): FAN_LOW,
    int(ZoneFanMode.FAN_MEDIUM): FAN_MEDIUM,
    int(ZoneFanMode.FAN_HIGH): FAN_HIGH,
}

SUPPORTED_FAN_MODES = [
    FAN_AUTO,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
]
