# Constants for koolnova Modbus RTU BMS
# d'après la documentation officielle A52102 - Registre contrôle Modbus

from enum import Enum

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

# Chaque zone climatique est définie par 4 registres et il y a 16 zones possibles,
# donc le climat est défini par 64 registres
REG_START_ZONE = 0

# Commandes Modbus prises en charge sont le Read Holding Register (0x03) 
# et le Write Single Register (0x06)

REG_LOCK_ZONE = 0 # 40001, 40005, 40009, etc ...
REG_STATE_AND_FLOW = 1 # 40002, 40006, 40010, etc ...

class ZoneState(Enum):
    STATE_OFF = 0
    STATE_ON = 1

class ZoneRegister(Enum):
    REGISTER_OFF = 0
    REGISTER_ON = 1

class ZoneFanMode(Enum):
    FAN_OFF = 0
    FAN_LOW = 1
    FAN_MEDIUM = 2
    FAN_HIGH = 3
    FAN_AUTO = 4

class ZoneClimMode(Enum):
    COLD = 1 
    HOT = 2
    HEATING_FLOOR = 4
    REFRESHING_FLOOR = 5 
    HEATING_FLOOR_2 = 6

# Température de consigne = (data / 2) => delta: 15°C -> 35°C
REG_TEMP_ORDER = 2 # 40003, 40007, 40011, etc ...
# Température réelle = (data / 2) => delta: 0°C -> 50°C
REG_TEMP_REAL = 3 # 40004, 40008, 40012, etc ...

# Temperature maximale de consigne : 35°C
MAX_TEMP_ORDER = 35.0
# Temperature minimale de consigne : 15°C
MIN_TEMP_ORDER = 15.0

# (4 registres: 64 -> 67) Debit des machines (0: arret -> 15: debit maximum)
REG_START_FLOW_ENGINE = 64
NUM_REG_FLOG_ENGINE = 4
FLOW_ENGINE_VAL_MAX = 15
FLOW_ENGINE_VAL_MIN = 0

# (4 registres : 68 -> 71) Température de consigne de la machine.
# Valeur décimale de 30 à 60 = double de la temp de consigne des consignes AC1, AC2, AC3 et AC4
REG_START_ORDER_TEMP = 68
NUM_REG_ORDER_TEMP = 4

# (4 registres : 72 -> 75) Programmation des débit des machines du système
REG_START_FLOW_STATE_ENGINE = 72
NUM_REG_FLOW_STATE_ENGINE = 4

class FlowEngine(Enum):
    MANUAL_MIN = 1
    MANUAL_MED = 2
    MANUAL_HIGH = 3
    AUTO = 4

# Communication Modbus
REG_COMM = 76

REG_ADDR_MODBUS = 77 # dispo (1 - 127)
REG_EFFICIENCY = 78

# Point d'equilibre entre efficience/vitesse du système de zone
# chiffre élevé = meilleur efficience
# chiffre bas = temp réglée atteinte au plus tot
class Efficiency(Enum):
    LOWER_EFF = 1
    LOW_EFF = 2
    MED_EFF = 3
    HIGH_EFF = 4
    HIGHER_EFF = 5

REG_CLIM_ID = 79
REG_SYS_STATE = 80

class SysState(Enum):
    SYS_STATE_OFF = 0
    SYS_STATE_ON = 1

REG_GLOBAL_MODE = 81

class GlobalMode(Enum):
    COLD = 1
    HEAT = 2
    HEATING_FLOOR = 4
    REFRESHING_FLOOR = 5
    HEATING_FLOOR_2 = 6
