from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config.constants import SensorStatus, SensorType
from app.models.sensor import SensorReading

from app.safety.safety_rules import (
    BOILER_OVER_TEMPERATURE_RULE,
    COLLECTOR_OVER_TEMPERATURE_RULE,
    GAS_DETECTION_RULE,
    INVALID_DATA_RULE,
    SENSOR_FAILURE_RULE,
    SafetyLimits,
    SafetyRule,
    DEFAULT_SAFETY_LIMITS,
)


# ============================================================
# SAFETY EVENT
# ============================================================


@dataclass
class SafetyEvent:
    """
    یک رویداد ایمنی.
    """

    rule: SafetyRule

    message: str

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    sensor_id: str | None = None

    value: float | None = None


# ============================================================
# SAFETY RESULT
# ============================================================


@dataclass
class SafetyResult:
    """
    نتیجه اجرای Safety Engine.
    """

    safe: bool

    shutdown_required: bool

    lockout_required: bool

    events: list[SafetyEvent] = field(
        default_factory=list
    )

    highest_priority: int | None = None

    reason: str | None = None


# ============================================================
# SAFETY ENGINE
# ============================================================


class SafetyEngine:
    """
    موتور ایمنی موتورخانه.

    این کلاس فقط Safety را بررسی می‌کند.
    تصمیم نهایی روشن/خاموش شدن تجهیزات
    در Decision Engine انجام خواهد شد.
    """

    def __init__(
        self,
        limits: SafetyLimits | None = None,
    ):
        self.limits = (
            limits
            or DEFAULT_SAFETY_LIMITS
        )

    # ========================================================
    # MAIN EVALUATION
    # ========================================================

    def evaluate(
        self,
        readings: list[SensorReading],
        data_valid: bool = True,
    ) -> SafetyResult:
        """
        اجرای تمام قوانین ایمنی.
        """

        events: list[SafetyEvent] = []

        # ----------------------------------------------------
        # INVALID DATA
        # ----------------------------------------------------

        if not data_valid:
            events.append(
                SafetyEvent(
                    rule=INVALID_DATA_RULE,
                    message=(
                        "Sensor data validation failed"
                    ),
                )
            )

        # ----------------------------------------------------
        # SENSOR STATUS
        # ----------------------------------------------------

        events.extend(
            self._check_sensor_status(readings)
        )

        # ----------------------------------------------------
        # GAS
        # ----------------------------------------------------

        events.extend(
            self._check_gas(readings)
        )

        # ----------------------------------------------------
        # TEMPERATURE
        # ----------------------------------------------------

        events.extend(
            self._check_temperature(readings)
        )

        # ----------------------------------------------------
        # BUILD RESULT
        # ----------------------------------------------------

        return self._build_result(events)

    # ========================================================
    # SENSOR STATUS
    # ========================================================

    def _check_sensor_status(
        self,
        readings: list[SensorReading],
    ) -> list[SafetyEvent]:

        events: list[SafetyEvent] = []

        for reading in readings:

            if reading.status in (
                SensorStatus.INVALID,
                SensorStatus.OFFLINE,
                SensorStatus.STALE,
                SensorStatus.ERROR,
            ):

                events.append(
                    SafetyEvent(
                        rule=SENSOR_FAILURE_RULE,
                        message=(
                            f"Sensor {reading.sensor_id} "
                            f"has status "
                            f"{reading.status.value}"
                        ),
                        sensor_id=reading.sensor_id,
                        value=reading.value,
                    )
                )

        return events

    # ========================================================
    # GAS CHECK
    # ========================================================

    def _check_gas(
        self,
        readings: list[SensorReading],
    ) -> list[SafetyEvent]:

        events: list[SafetyEvent] = []

        for reading in readings:

            if reading.sensor_type != SensorType.MQ2:
                continue

            if (
                reading.value
                >= self.limits.mq2_gas_threshold
            ):

                events.append(
                    SafetyEvent(
                        rule=GAS_DETECTION_RULE,
                        message=(
                            f"MQ-2 gas threshold exceeded: "
                            f"{reading.value}"
                        ),
                        sensor_id=reading.sensor_id,
                        value=reading.value,
                    )
                )

        return events

    # ========================================================
    # TEMPERATURE CHECK
    # ========================================================

    def _check_temperature(
        self,
        readings: list[SensorReading],
    ) -> list[SafetyEvent]:

        events: list[SafetyEvent] = []

        for reading in readings:

            if reading.sensor_type != SensorType.DS18B20:
                continue

            # ------------------------------------------------
            # Boiler temperature
            # ------------------------------------------------

            if (
                "boiler" in reading.sensor_id.lower()
                and reading.value
                >= self.limits.max_boiler_temperature_c
            ):

                events.append(
                    SafetyEvent(
                        rule=BOILER_OVER_TEMPERATURE_RULE,
                        message=(
                            f"Boiler temperature exceeded "
                            f"safety limit: "
                            f"{reading.value}°C"
                        ),
                        sensor_id=reading.sensor_id,
                        value=reading.value,
                    )
                )

            # ------------------------------------------------
            # Collector temperature
            # ------------------------------------------------

            if (
                "collector" in reading.sensor_id.lower()
                and reading.value
                >= self.limits.max_collector_temperature_c
            ):

                events.append(
                    SafetyEvent(
                        rule=COLLECTOR_OVER_TEMPERATURE_RULE,
                        message=(
                            f"Collector temperature exceeded "
                            f"safety limit: "
                            f"{reading.value}°C"
                        ),
                        sensor_id=reading.sensor_id,
                        value=reading.value,
                    )
                )

        return events

    # ========================================================
    # BUILD RESULT
    # ========================================================

    def _build_result(
        self,
        events: list[SafetyEvent],
    ) -> SafetyResult:

        if not events:

            return SafetyResult(
                safe=True,
                shutdown_required=False,
                lockout_required=False,
            )

        events.sort(
            key=lambda event: event.rule.priority
        )

        highest_priority = events[0].rule.priority

        shutdown_required = any(
            event.rule.action
            in (
                "shutdown",
                "lockout",
            )
            for event in events
        )

        lockout_required = any(
            event.rule.action == "lockout"
            for event in events
        )

        reason = events[0].message

        return SafetyResult(
            safe=False,
            shutdown_required=shutdown_required,
            lockout_required=lockout_required,
            events=events,
            highest_priority=highest_priority,
            reason=reason,
        )