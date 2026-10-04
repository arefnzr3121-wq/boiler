from enum import Enum


# ============================================================
# SYSTEM
# ============================================================

SYSTEM_NAME = "Boiler Decision Engine"
SYSTEM_VERSION = "1.0.0"


# ============================================================
# SENSOR TYPES
# ============================================================

class SensorType(str, Enum):
    DS18B20 = "ds18b20"
    MQ2 = "mq2"


# ============================================================
# SENSOR STATUS
# ============================================================

class SensorStatus(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    OFFLINE = "offline"
    STALE = "stale"
    ERROR = "error"


# ============================================================
# DECISION STATES
# ============================================================

class DecisionState(str, Enum):
    OFF = "off"
    ON = "on"
    SAFETY_OFF = "safety_off"
    UNKNOWN = "unknown"


# ============================================================
# EQUIPMENT
# ============================================================

class EquipmentType(str, Enum):
    BOILER = "boiler"
    PUMP = "pump"
    BURNER = "burner"


# ============================================================
# SEASONS
# ============================================================

class Season(str, Enum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"


# ============================================================
# PRIORITY
# ============================================================

class DecisionPriority(int, Enum):
    """
    هرچه عدد کمتر باشد، اولویت تصمیم بالاتر است.
    """

    EMERGENCY = 0
    SAFETY = 10
    FAULT = 20
    MANUAL = 30
    SCHEDULE = 40
    COMFORT = 50
    ENERGY_OPTIMIZATION = 60
    DEFAULT = 100


# ============================================================
# TEMPERATURE LIMITS
# ============================================================

MIN_VALID_TEMPERATURE_C = -40.0
MAX_VALID_TEMPERATURE_C = 125.0


# ============================================================
# MQ-2
# ============================================================

MQ2_MIN_VALUE = 0.0
MQ2_MAX_VALUE = 4095.0


# ============================================================
# SENSOR TIMING
# ============================================================

DEFAULT_SENSOR_TIMEOUT_SECONDS = 10
DEFAULT_SENSOR_STALE_SECONDS = 30


# ============================================================
# CONTROL
# ============================================================

MINIMUM_BOILER_ON_TIME_SECONDS = 60
MINIMUM_BOILER_OFF_TIME_SECONDS = 60


# ============================================================
# DEFAULT COMFORT
# ============================================================

DEFAULT_COMFORT_TEMPERATURE_C = 21.0

DEFAULT_COMFORT_MIN_TEMPERATURE_C = 20.0
DEFAULT_COMFORT_MAX_TEMPERATURE_C = 22.0


# ============================================================
# HYSTERESIS
# ============================================================

DEFAULT_HYSTERESIS_C = 0.5


# ============================================================
# SAFETY
# ============================================================

SAFETY_SENSOR_FAILURE = "sensor_failure"
SAFETY_GAS_DETECTED = "gas_detected"
SAFETY_OVER_TEMPERATURE = "over_temperature"
SAFETY_INVALID_DATA = "invalid_data"
SAFETY_COMMUNICATION_FAILURE = "communication_failure"