from dataclasses import dataclass

from app.config.constants import (
    MAX_VALID_TEMPERATURE_C,
    MQ2_MAX_VALUE,
)


# ============================================================
# SAFETY RULE PRIORITIES
# ============================================================

SAFETY_PRIORITY_GAS = 0
SAFETY_PRIORITY_OVER_TEMPERATURE = 10
SAFETY_PRIORITY_SENSOR_FAILURE = 20
SAFETY_PRIORITY_INVALID_DATA = 30
SAFETY_PRIORITY_COMMUNICATION = 40


# ============================================================
# DEFAULT SAFETY LIMITS
# ============================================================

DEFAULT_MAX_BOILER_TEMPERATURE_C = 95.0

DEFAULT_MAX_COLLECTOR_TEMPERATURE_C = 120.0

DEFAULT_MQ2_GAS_THRESHOLD = 2500.0


# ============================================================
# SAFETY ACTIONS
# ============================================================

SAFETY_ACTION_SHUTDOWN = "shutdown"
SAFETY_ACTION_LOCKOUT = "lockout"
SAFETY_ACTION_WARNING = "warning"


# ============================================================
# SAFETY RULE
# ============================================================


@dataclass(frozen=True)
class SafetyRule:
    """
    یک قانون ایمنی.

    هر Rule مشخص می‌کند:
        چه چیزی خطرناک است؟
        چه اولویتی دارد؟
        چه اقدامی باید انجام شود؟
    """

    code: str

    description: str

    priority: int

    action: str

    enabled: bool = True


# ============================================================
# DEFAULT RULES
# ============================================================

GAS_DETECTION_RULE = SafetyRule(
    code="GAS_DETECTED",
    description=(
        "Gas concentration detected above safety threshold"
    ),
    priority=SAFETY_PRIORITY_GAS,
    action=SAFETY_ACTION_LOCKOUT,
)


BOILER_OVER_TEMPERATURE_RULE = SafetyRule(
    code="BOILER_OVER_TEMPERATURE",
    description=(
        "Boiler water temperature exceeded safety limit"
    ),
    priority=SAFETY_PRIORITY_OVER_TEMPERATURE,
    action=SAFETY_ACTION_SHUTDOWN,
)


COLLECTOR_OVER_TEMPERATURE_RULE = SafetyRule(
    code="COLLECTOR_OVER_TEMPERATURE",
    description=(
        "Collector temperature exceeded safety limit"
    ),
    priority=SAFETY_PRIORITY_OVER_TEMPERATURE,
    action=SAFETY_ACTION_SHUTDOWN,
)


SENSOR_FAILURE_RULE = SafetyRule(
    code="SENSOR_FAILURE",
    description=(
        "Required safety sensor is unavailable or invalid"
    ),
    priority=SAFETY_PRIORITY_SENSOR_FAILURE,
    action=SAFETY_ACTION_SHUTDOWN,
)


INVALID_DATA_RULE = SafetyRule(
    code="INVALID_DATA",
    description=(
        "Sensor data failed validation"
    ),
    priority=SAFETY_PRIORITY_INVALID_DATA,
    action=SAFETY_ACTION_SHUTDOWN,
)


COMMUNICATION_FAILURE_RULE = SafetyRule(
    code="COMMUNICATION_FAILURE",
    description=(
        "Communication with control system failed"
    ),
    priority=SAFETY_PRIORITY_COMMUNICATION,
    action=SAFETY_ACTION_SHUTDOWN,
)


# ============================================================
# SAFETY CONFIGURATION
# ============================================================


@dataclass(frozen=True)
class SafetyLimits:
    """
    محدودیت‌های ایمنی سیستم.
    """

    max_boiler_temperature_c: float = (
        DEFAULT_MAX_BOILER_TEMPERATURE_C
    )

    max_collector_temperature_c: float = (
        DEFAULT_MAX_COLLECTOR_TEMPERATURE_C
    )

    mq2_gas_threshold: float = (
        DEFAULT_MQ2_GAS_THRESHOLD
    )


DEFAULT_SAFETY_LIMITS = SafetyLimits()