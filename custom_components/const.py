""" Les constantes pour l'intégration TestVBE_4 """

from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    FAN_AUTO,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
)
from .koolnova.const import (
    GlobalMode,
    Efficiency,
    ZoneClimMode,
    ZoneFanMode,
    ZoneState,
)

DOMAIN = "testVBE_4"
PLATFORMS: list[Platform] = [Platform.SENSOR,
                                Platform.SELECT, 
                                Platform.SWITCH, 
                                Platform.CLIMATE]

CONF_NAME = "koolnova_test_HA"
CONF_DEVICE_ID = "device_id"

DEVICE_MANUFACTURER = "koolnova"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

GLOBAL_MODE_POS_1 = "cold"
GLOBAL_MODE_POS_2 = "heat"
GLOBAL_MODE_POS_3 = "heating floor"
GLOBAL_MODE_POS_4 = "refreshing floor"
GLOBAL_MODE_POS_5 = "heating floor 2"

GLOBAL_MODE_TRANSLATION = {
    int(GlobalMode.COLD): GLOBAL_MODE_POS_1,
    int(GlobalMode.HEAT): GLOBAL_MODE_POS_2,
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

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
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