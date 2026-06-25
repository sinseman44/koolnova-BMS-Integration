# Constants for koolnova Modbus RTU BMS
# d'après la documentation officielle A52102 - Registre contrôle Modbus

from enum import Enum

DEFAULT_MODE = 'Modbus RTU'
DEFAULT_TCP_ADDR = '0.0.0.0'
DEFAULT_TCP_PORT = 502
DEFAULT_TCP_RETRIES = 3
DEFAULT_TCP_RECO_DELAY = 0.1
DEFAULT_TCP_RECO_DELAY_MAX = 300.0
# La couche physique est Modbus RTU sur RS485 à 9600, avec 8 bits de données, sans parité
# ou même parité et un bit d'arrêt. Par défaut: 9600 8E1
# L'adresse Modbus par défaut est 49
DEFAULT_ADDR = 49
DEFAULT_BAUDRATE = 9600
DEFAULT_PARITY = 'E'
DEFAULT_STOPBITS = 1
DEFAULT_BYTESIZE = 8

# Nombre de machines (AC1, AC2, AC3 et AC4)
NUM_OF_ENGINES = 4
# Nombre de registres par zone
NUM_REG_PER_ZONE = 4
# Nombre max de zone pour un systeme
NB_ZONE_MAX = 16

TABLE_VERSION_AUTO = "auto"
TABLE_VERSION_V1 = "v1"
TABLE_VERSION_V2 = "v2"
TABLE_VERSION_DEFAULT = TABLE_VERSION_V1
TABLE_VERSION_OPTIONS = (
    TABLE_VERSION_AUTO,
    TABLE_VERSION_V1,
    TABLE_VERSION_V2,
)

# Le registre logique 40073 est un bon candidat pour différencier les tables :
# - en v1.0, c'est la programmation du débit de la machine AC1, avec valeurs 1 à 4 ;
# - en v2.0, c'est le modèle et la version logiciel de l'unité de contrôle,
#   par exemple 0x4829.
REG_V2_MODEL_VERSION = 72
V1_FLOW_STATE_VALUES = (1, 2, 3, 4)

# Koolnova 2.0 advanced registers. Offsets are zero-based Modbus addresses
# matching the official logical addresses 40073 to 40092 and 40111 to 40126.
# 40074: paramètres système, sorties relais, efficacité/ECO/STOP/antigel/humidité.
REG_V2_PARAMETERS = 73
# 40075: MDA, modes système actifs ou cachés.
REG_V2_ACTIVE_MODES = 74
# 40076: LT3, limite chauffage maximale et limite refroidissement minimale.
REG_V2_TEMPERATURE_LIMITS = 75
# 40077: modes de changement automatique et contrôle humidité.
REG_V2_AUTO_CHANGEOVER_HUMIDITY = 76
# 40078: heure du système.
REG_V2_SYSTEM_TIME = 77
# 40079: INM, configuration des entrées externes DIN1 et DIN2.
REG_V2_EXTERNAL_INPUTS = 78
# 40080: APZ, angle d'ouverture des zones Z1 à Z8.
REG_V2_OPENING_ANGLE_Z1_Z8 = 79
# 40081: APZ, angle d'ouverture des zones Z9 à Z16.
REG_V2_OPENING_ANGLE_Z9_Z16 = 80
# 40082: WTE, NTC eau plancher chauffant.
REG_V2_FLOOR_WATER_TEMPERATURE = 81
# 40083: EXT, température ambiante extérieure.
REG_V2_OUTDOOR_TEMPERATURE = 82
# 40084: AUX, NTC auxiliaire.
REG_V2_AUX_TEMPERATURE = 83
# 40085: MKE, masque d'électrovannes.
REG_V2_VALVE_MASK = 84
# 40086: MKE, retard pompe et offset d'électrovannes.
REG_V2_PUMP_DELAY_VALVE_OFFSET = 85
# 40087: HET, résistance d'immersion.
REG_V2_IMMERSION_HEATER = 86
# 40088: BQ3, blocage de thermostats.
REG_V2_THERMOSTAT_BLOCK = 87
# 40089: MAU, mode automatique.
REG_V2_AUTO_MODE = 88
# 40090: CTH_LOW, températures ambiantes pour vanne mélangeuse.
REG_V2_MIXING_VALVE_AMBIENT_TEMPERATURES = 89
# 40091: CTH_HIGH, températures d'eau pour vanne mélangeuse.
REG_V2_MIXING_VALVE_WATER_TEMPERATURES = 90
# 40092: CTM, mode vanne mélangeuse et températures fixes froid/chaleur.
REG_V2_MIXING_VALVE_MODE_INFO = 91
# 40107: réservé.
REG_V2_RESERVED_40107 = 106
# 40111: nombre de thermostats qui demandent du chauffage au sol.
REG_V2_RADIANT_FLOOR_DEMAND_COUNT = 110
# 40112: nombre de thermostats qui demandent de l'air dans AC3.
REG_V2_AC3_AIR_DEMAND_COUNT = 111
# 40113: somme du volume des thermostats connectés pour AC1.
REG_V2_START_CONNECTED_VOLUME = 112
# 40113-40116: somme du volume des thermostats connectés pour AC1 à AC4.
NUM_REG_V2_CONNECTED_VOLUME = 4
# 40117: somme du volume des thermostats actifs en demande pour AC1.
REG_V2_START_ACTIVE_VOLUME = 116
# 40117-40120: somme du volume des thermostats actifs en demande pour AC1 à AC4.
NUM_REG_V2_ACTIVE_VOLUME = 4
# 40121: moyenne des températures de consigne demandées par AC1.
REG_V2_START_REQUESTED_TEMP_AVG = 120
# 40121-40123 et 40125: moyennes des températures de consigne pour AC1 à AC4.
NUM_REG_V2_REQUESTED_TEMP_AVG = 4
# 40126: MSB EFI, LSB vitesse AC3.
REG_V2_EFFICIENCY_AC3_SPEED = 125

# Chaque zone climatique est définie par 4 registres et il y a 16 zones possibles,
# donc le climat est défini par 64 registres
REG_START_ZONE = 0

# Commandes Modbus prises en charge sont le Read Holding Register (0x03)
# et le Write Single Register (0x06)

MODBUS_LOGICAL_ADDRESS_BASE = 40001

REG_LOCK_ZONE = 0 # 40001, 40005, 40009, etc ...
REG_STATE_AND_FLOW = 1 # 40002, 40006, 40010, etc ...

class ZoneState(Enum):
    STATE_OFF = 0
    STATE_ON = 1

    def __int__(self):
        return self.value

class ZoneRegister(Enum):
    REGISTER_OFF = 0
    REGISTER_ON = 1

    def __int__(self):
        return self.value

class ZoneFanMode(Enum):
    FAN_OFF = 0
    FAN_LOW = 1
    FAN_MEDIUM = 2
    FAN_HIGH = 3
    FAN_AUTO = 4

    def __int__(self):
        return self.value

class ZoneClimMode(Enum):
    OFF = 0
    COOL = 1 
    HEAT = 2
    HEATING_FLOOR = 4
    REFRESHING_FLOOR = 5 
    HEATING_FLOOR_2 = 6

    def __int__(self):
        return self.value

# Température de consigne = (data / 2) => delta: 15°C -> 35°C
REG_TEMP_ORDER = 2 # 40003, 40007, 40011, etc ...
# Température réelle = (data / 2) => delta: 0°C -> 50°C
REG_TEMP_REAL = 3 # 40004, 40008, 40012, etc ...

# Temperature maximale de consigne : 35°C
MAX_TEMP_ORDER = 35.0
# Temperature minimale de consigne : 15°C
MIN_TEMP_ORDER = 15.0
# Pas de la temperature de consigne : 0.5°C
STEP_TEMP_ORDER = 0.5

# Temperature maximale : 50°C
MAX_TEMP = 50.0
# Temperature minimale : 0°C
MIN_TEMP = 0.0
# Pas de la temperature : 0.5°C
STEP_TEMP = 0.5

# (4 registres: 64 -> 67) Debit des machines (0: arret -> 15: debit maximum)
NUM_REG_FLOG_ENGINE = 4
FLOW_ENGINE_VAL_MAX = 15
FLOW_ENGINE_VAL_MIN = 0

# (4 registres : 68 -> 71) Température de consigne de la machine.
# Valeur décimale de 30 à 60 = double de la temp de consigne des consignes AC1, AC2, AC3 et AC4
NUM_REG_ORDER_TEMP = 4

# (4 registres : 72 -> 75) Programmation des débit des machines du système
NUM_REG_FLOW_STATE_ENGINE = 4

class FlowEngine(Enum):
    MANUAL_MIN = 1
    MANUAL_MED = 2
    MANUAL_HIGH = 3
    AUTO = 4

    def __int__(self):
        return self.value

# Communication Modbus
# Point d'equilibre entre efficience/vitesse du système de zone
# chiffre élevé = meilleur efficience
# chiffre bas = temp réglée atteinte au plus tot
class Efficiency(Enum):
    LOWER_EFF = 1
    LOW_EFF = 2
    MED_EFF = 3
    HIGH_EFF = 4
    HIGHER_EFF = 5

    def __int__(self):
        return self.value

class SysState(Enum):
    SYS_STATE_OFF = 0
    SYS_STATE_ON = 1

    def __int__(self):
        return self.value

class GlobalMode(Enum):
    VENTILATION = 0
    COLD = 1
    HEAT = 2
    DEHUMIDIFICATION = 3
    HEATING_FLOOR = 4
    REFRESHING_FLOOR = 5
    HEATING_FLOOR_2 = 6

    def __int__(self):
        return self.value

REG_KEY_START_FLOW_ENGINE = "start_flow_engine"
REG_KEY_START_ORDER_TEMP = "start_order_temp"
REG_KEY_START_FLOW_STATE_ENGINE = "start_flow_state_engine"
REG_KEY_COMM = "comm"
REG_KEY_ADDR_MODBUS = "addr_modbus"
REG_KEY_EFFICIENCY = "efficiency"
REG_KEY_CLIM_ID = "clim_id"
REG_KEY_SYS_STATE = "sys_state"
REG_KEY_GLOBAL_MODE = "global_mode"

REGISTER_MAP_V1 = {
    REG_KEY_START_FLOW_ENGINE: 64,
    REG_KEY_START_ORDER_TEMP: 68,
    REG_KEY_START_FLOW_STATE_ENGINE: 72,
    REG_KEY_COMM: 76,
    REG_KEY_ADDR_MODBUS: 77,
    REG_KEY_EFFICIENCY: 78,
    REG_KEY_CLIM_ID: 79,
    REG_KEY_SYS_STATE: 80,
    REG_KEY_GLOBAL_MODE: 81,
}

REGISTER_MAP_V2 = {
    REG_KEY_START_FLOW_ENGINE: 92,
    REG_KEY_START_ORDER_TEMP: 96,
    REG_KEY_START_FLOW_STATE_ENGINE: 100,
    REG_KEY_COMM: 104,
    REG_KEY_ADDR_MODBUS: 105,
    REG_KEY_EFFICIENCY: None,
    REG_KEY_CLIM_ID: 107,
    REG_KEY_SYS_STATE: 108,
    REG_KEY_GLOBAL_MODE: 109,
}

REGISTER_MAPS = {
    TABLE_VERSION_V1: REGISTER_MAP_V1,
    TABLE_VERSION_V2: REGISTER_MAP_V2,
}

def normalize_table_version(table_version:str | None) -> str:
    """Normalize stored/user-facing table version values."""
    if table_version in TABLE_VERSION_OPTIONS:
        return table_version
    if table_version == "Koolnova 2.0":
        return TABLE_VERSION_V2
    if table_version == "Koolnova 1.0":
        return TABLE_VERSION_V1
    if table_version == "Auto detect":
        return TABLE_VERSION_AUTO
    return TABLE_VERSION_DEFAULT

def register_map_for_table_version(table_version:str | None) -> dict:
    """Return the register map for a normalized table version.

    Runtime setup should resolve auto-detection before constructing the device.
    Keep unresolved auto conservative by using v1.0, which preserves the
    previous integration behavior.
    """
    if table_version == TABLE_VERSION_AUTO:
        table_version = TABLE_VERSION_DEFAULT
    return REGISTER_MAPS[table_version or TABLE_VERSION_DEFAULT]
