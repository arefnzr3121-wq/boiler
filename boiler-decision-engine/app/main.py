import logging
from datetime import datetime, timezone
from typing import Any

from app.communication.message_handler import MessageHandler
from app.communication.mqtt_client import MQTTClient

from app.config.constants import DecisionState, Season
from app.config.settings import Settings, get_settings

from app.models.building import (
    BuildingInfo,
    BuildingModelType,
    BuildingType,
    InsulationLevel,
)
from app.models.comfort import ComfortSettings
from app.models.decision import DecisionResult
from app.models.schedule import (
    DailySchedule,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.models.sensor import SensorReading
from app.models.equipment import EquipmentSnapshot
from app.equipment_feedback import EquipmentFeedbackParser

from app.validation.data_validator import DataValidator
from app.safety.safety_engine import SafetyEngine, SafetyResult
from app.schedule.schedule_engine import ScheduleEngine
from app.comfort.comfort_engine import ComfortEngine, ComfortInput
from app.comfort.preheating import PreheatingConfig, PreheatingEngine
from app.building.building_engine import BuildingCalculationInput, BuildingEngine
from app.decision.decision_engine import DecisionEngine, DecisionInput

from app.models.output import OutputSnapshot
from app.models.actuator import ActuatorState
from app.output.output_engine import OutputEngine

from app.storage.history import HistoryService
from app.storage.repository import SQLiteRepository


logger = logging.getLogger(__name__)


class BoilerDecisionEngine:
    """
    هسته اصلی سیستم تصمیم‌گیری موتورخانه.

    Pipeline:

        MQTT
          ↓
        MessageHandler
          ↓
        Validation
          ↓
        Safety
          ↓
        Schedule
          ↓
        Comfort
          ↓
        Building
          ↓
        Decision
          ↓
        Output
          ↓
        History
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()

        # Communication
        self.message_handler = MessageHandler()
        self.equipment_feedback_parser = EquipmentFeedbackParser()

        # Validation
        self.data_validator = DataValidator()

        # Safety
        self.safety_engine = SafetyEngine()

        # Schedule
        self.schedule_engine = ScheduleEngine()

        # Comfort
        self.comfort_engine = ComfortEngine()
        self.preheating_engine = PreheatingEngine(
            PreheatingConfig(
                enabled=self.settings.preheating_enabled,
                max_preheat_minutes=self.settings.max_preheat_minutes,
            )
        )

        # Building
        self.building_engine = BuildingEngine()

        # Decision
        self.decision_engine = DecisionEngine()

        # Output
        self.output_engine = OutputEngine()

        # Storage
        self.repository = SQLiteRepository(
            database_path="data/boiler_engine.db"
        )

        self.history = HistoryService(
            repository=self.repository
        )

        # Configuration
        self.comfort_settings = ComfortSettings(
            target_temperature_c=self.settings.comfort_temperature_c,
            minimum_temperature_c=self.settings.comfort_min_temperature_c,
            maximum_temperature_c=self.settings.comfort_max_temperature_c,
            hysteresis_c=self.settings.hysteresis_c,
        )

        self.building = self._create_default_building()
        self.seasonal_schedule = self._create_default_schedule()

        # Runtime state
        self.previous_heating_state = False
        self.last_output: OutputSnapshot | None = None
        self.last_decision: DecisionResult | None = None
        self.last_sensor_readings: list[SensorReading] = []
        self.last_equipment_snapshot: EquipmentSnapshot | None = None

        # MQTT
        self.mqtt = MQTTClient(
            settings=self.settings,
            on_message=self._on_mqtt_message,
        )

    # ======================================================
    # DEFAULT CONFIGURATION
    # ======================================================

    def _create_default_building(self) -> BuildingInfo:
        return BuildingInfo(
            building_id="default-building",
            name="Default Building",
            building_type=BuildingType.RESIDENTIAL,
            floor_count=1,
            floor_area_m2=100.0,
            occupancy_count=4,
            insulation_level=InsulationLevel.AVERAGE,
            model_type=BuildingModelType.MODEL_A,
            design_indoor_temperature_c=21.0,
            design_outdoor_temperature_c=0.0,
        )

    def _create_default_schedule(self) -> SeasonalSchedule:
        weekday_windows = [
            ScheduleWindow(
                start_time=datetime.strptime(
                    "06:00",
                    "%H:%M",
                ).time(),
                end_time=datetime.strptime(
                    "17:00",
                    "%H:%M",
                ).time(),
            )
        ]

        days = []

        for day_of_week in range(5):
            days.append(
                DailySchedule(
                    day_of_week=day_of_week,
                    enabled=True,
                    windows=weekday_windows.copy(),
                )
            )

        for day_of_week in range(5, 7):
            days.append(
                DailySchedule(
                    day_of_week=day_of_week,
                    enabled=False,
                    windows=[],
                )
            )

        weekly_schedule = WeeklySchedule(
            enabled=True,
            days=days,
        )

        return SeasonalSchedule(
            season=Season.WINTER,
            enabled=True,
            weekly_schedule=weekly_schedule,
        )

    # ======================================================
    # MQTT LIFECYCLE
    # ======================================================

    def start(self) -> None:
        logger.info("Starting Boiler Decision Engine")

        if not self.settings.mqtt_enabled:
            logger.info("MQTT is disabled")
            return

        self.mqtt.connect()
        self.mqtt.start_background_loop()

        logger.info("Boiler Decision Engine started")

    def stop(self) -> None:
        logger.info("Stopping Boiler Decision Engine")

        self.mqtt.stop_loop()
        self.mqtt.disconnect()

        logger.info("Boiler Decision Engine stopped")

    # ======================================================
    # MQTT MESSAGE
    # ======================================================

    def _on_mqtt_message(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:

        logger.info(
            "MQTT message received: %s",
            topic,
        )

        if topic == self.settings.mqtt_equipment_topic:
            try:
                self.last_equipment_snapshot = self.equipment_feedback_parser.parse(payload)
                logger.info("Equipment feedback updated")
            except Exception:
                logger.exception("Invalid equipment feedback")
            return

        if topic != self.settings.mqtt_sensor_topic:
            logger.warning(
                "Ignoring unknown MQTT topic: %s",
                topic,
            )
            return

        try:
            self.process_sensor_payload(payload)

        except Exception:
            logger.exception(
                "Error while processing sensor payload"
            )

            self.history.record_event(
                event_type="SYSTEM_ERROR",
                severity="ERROR",
                message=(
                    "Unhandled exception while "
                    "processing sensor payload"
                ),
            )

    # ======================================================
    # MAIN PROCESSING PIPELINE
    # ======================================================

    def process_sensor_payload(
        self,
        payload: dict[str, Any],
    ) -> OutputSnapshot:

        # --------------------------------------------------
        # 1. Parse sensor message
        # --------------------------------------------------

        readings = self.message_handler.handle_sensor_message(
            payload
        )

        self.last_sensor_readings = readings

        # --------------------------------------------------
        # 2. Validation
        # --------------------------------------------------

        validation_result = self.data_validator.validate(
            readings
        )

        self.history.record_sensor_readings(
            readings
        )

        # --------------------------------------------------
        # 3. Safety
        # --------------------------------------------------

        safety_result = self.safety_engine.evaluate(
            readings=readings,
            data_valid=validation_result.valid,
        )

        self._record_safety_events(
            safety_result
        )

        # --------------------------------------------------
        # 4. Safety shutdown
        # --------------------------------------------------

        if safety_result.shutdown_required:

            decision = self.decision_engine.evaluate(
                DecisionInput(
                    safety_active=True,
                    safety_shutdown_required=True,
                    safety_lockout_required=(
                        safety_result.lockout_required
                    ),
                    safety_reason=safety_result.reason,
                )
            )

            self.last_decision = decision

            output = self.output_engine.evaluate(
                decision_state=decision.boiler,
                reason_code="SAFETY_SHUTDOWN",
                reason_message=safety_result.reason,
            )

            self.last_output = output

            self.history.record_decision(
                decision
            )

            self.history.record_output(
                output
            )

            self._publish_output(
                output
            )

            self._publish_state(
                decision=decision,
                output=output,
                safety=safety_result,
            )

            return output

        # --------------------------------------------------
        # 5. Extract temperatures
        # --------------------------------------------------

        indoor_temperature = self._get_sensor_value(
            readings,
            "indoor_temperature",
        )

        outdoor_temperature = self._get_sensor_value(
            readings,
            "outdoor_temperature",
        )

        # --------------------------------------------------
        # 6. Missing indoor temperature
        # --------------------------------------------------

        if indoor_temperature is None:

            self.history.record_event(
                event_type="MISSING_SENSOR",
                severity="ERROR",
                message="Indoor temperature sensor is required",
            )

            decision = self.decision_engine.evaluate(
                DecisionInput(
                    safety_shutdown_required=True,
                    safety_reason=(
                        "Indoor temperature sensor missing"
                    ),
                )
            )

            output = self.output_engine.evaluate(
                decision_state=decision.boiler,
                reason_code="MISSING_SENSOR",
                reason_message=(
                    "Indoor temperature sensor missing"
                ),
            )

            self.last_decision = decision
            self.last_output = output

            self.history.record_decision(
                decision
            )

            self.history.record_output(
                output
            )

            return output

        # --------------------------------------------------
        # 7. Schedule
        # --------------------------------------------------

        now = datetime.now(timezone.utc)

        schedule_state = self.schedule_engine.evaluate(
            seasonal_schedule=self.seasonal_schedule,
            current_datetime=now,
            timezone_name=self.settings.timezone,
        )

        # --------------------------------------------------
        # 8. Comfort
        # --------------------------------------------------

        preheating_active = False
        next_window_start = self.schedule_engine.get_next_window_start(
            seasonal_schedule=self.seasonal_schedule,
            current_datetime=now,
            timezone_name=self.settings.timezone,
        )
        if (
            not schedule_state.active
            and next_window_start is not None
            and indoor_temperature is not None
        ):
            preheating_active = self.preheating_engine.should_preheat(
                current_datetime=now.astimezone(next_window_start.tzinfo),
                schedule_start=next_window_start,
                indoor_temperature_c=indoor_temperature,
                target_temperature_c=self.comfort_settings.target_temperature_c,
                outdoor_temperature_c=outdoor_temperature,
            )

        offset_c = self._calculate_weather_offset(outdoor_temperature)

        comfort_input = ComfortInput(
            indoor_temperature_c=indoor_temperature,
            outdoor_temperature_c=outdoor_temperature,
            previous_heating_state=self.previous_heating_state,
            offset_c=offset_c,
            preheating_active=preheating_active,
        )

        comfort_snapshot = self.comfort_engine.evaluate(
            settings=self.comfort_settings,
            input_data=comfort_input,
        )

        # --------------------------------------------------
        # 9. Building model
        # --------------------------------------------------

        target_temperature = (
            comfort_snapshot
            .state
            .effective_target_temperature_c
        )

        if outdoor_temperature is None:
            outdoor_temperature = (
                self.building.design_outdoor_temperature_c
            )

        building_input = BuildingCalculationInput(
            indoor_temperature_c=indoor_temperature,
            outdoor_temperature_c=outdoor_temperature,
            target_temperature_c=target_temperature,
            design_load_w=self.settings.design_load_w,
            base_load_per_m2_w=self.settings.base_load_per_m2_w,
            thermal_resistance_k_per_w=self.settings.thermal_resistance_k_per_w,
            thermal_capacity_wh_per_k=self.settings.thermal_capacity_wh_per_k,
            time_step_hours=self.settings.time_step_hours,
        )

        building_result = self.building_engine.calculate(
            building=self.building,
            input_data=building_input,
        )

        # --------------------------------------------------
        # 10. Decision
        # --------------------------------------------------

        decision_input = DecisionInput(
            safety_active=False,
            safety_shutdown_required=False,
            safety_lockout_required=False,

            schedule_active=schedule_state.active,

            heating_required=(
                comfort_snapshot
                .state
                .heating_required
            ),

            comfort_satisfied=(
                comfort_snapshot
                .state
                .comfort_satisfied
            ),

            heating_demand=building_result.heating_demand,
            estimated_load_w=building_result.estimated_load_w,

            boiler_available=self._equipment_available("boiler"),
            burner_available=self._equipment_available("burner"),
            pump_available=self._equipment_available("pump"),

            boiler_fault=self._equipment_fault("boiler"),
            burner_fault=self._equipment_fault("burner"),
            pump_fault=self._equipment_fault("pump"),

            previous_boiler_state=self._get_output_state(
                "boiler"
            ),

            previous_burner_state=self._get_output_state(
                "burner"
            ),

            previous_pump_state=self._get_output_state(
                "pump"
            ),
        )

        decision = self.decision_engine.evaluate(
            decision_input
        )

        self.last_decision = decision

        # --------------------------------------------------
        # 11. Output
        # --------------------------------------------------

        output = self.output_engine.evaluate(
            decision_state=decision.boiler,
            burner_state=decision.burner,
            pump_state=decision.pump,
            reason_code=getattr(
                decision,
                "reason_code",
                "",
            ),
            reason_message=getattr(
                decision,
                "reason_message",
                "",
            ),
        )

        self.last_output = output

        # --------------------------------------------------
        # 12. Runtime state
        # --------------------------------------------------

        self.previous_heating_state = (
            output.boiler == ActuatorState.ON
        )

        # --------------------------------------------------
        # 13. History
        # --------------------------------------------------

        self.history.record_decision(
            decision
        )

        self.history.record_output(
            output
        )

        # --------------------------------------------------
        # 14. Publish output
        # --------------------------------------------------

        self._publish_output(
            output
        )

        # --------------------------------------------------
        # 15. Publish state
        # --------------------------------------------------

        self._publish_state(
            decision=decision,
            output=output,
            safety=safety_result,
        )

        return output

    # ======================================================
    # EQUIPMENT FEEDBACK HELPERS
    # ======================================================

    def _equipment_available(self, equipment_id: str) -> bool:
        snapshot = self.last_equipment_snapshot
        if snapshot is None:
            return not self.settings.equipment_feedback_required

        age = (
            datetime.now(timezone.utc) - snapshot.timestamp.astimezone(timezone.utc)
        ).total_seconds()
        if age > self.settings.equipment_feedback_timeout_seconds:
            return False

        state = getattr(snapshot, equipment_id)
        return state.is_available and not state.fault

    def _equipment_fault(self, equipment_id: str) -> bool:
        snapshot = self.last_equipment_snapshot
        if snapshot is None:
            return False

        return bool(getattr(snapshot, equipment_id).fault)

    def _calculate_weather_offset(self, outdoor_temperature: float | None) -> float:
        """Apply a small configurable weather-compensation offset."""
        if (
            not self.settings.weather_offset_enabled
            or outdoor_temperature is None
        ):
            return 0.0

        reference_temperature = 15.0
        offset = max(0.0, reference_temperature - outdoor_temperature)
        offset *= self.settings.weather_offset_slope_c_per_c
        return min(offset, self.settings.weather_offset_max_c)

    # ======================================================
    # SENSOR HELPERS
    # ======================================================

    def _get_sensor_value(
        self,
        readings: list[SensorReading],
        sensor_id: str,
    ) -> float | None:

        for reading in readings:
            if reading.sensor_id == sensor_id:
                return reading.value

        return None

    # ======================================================
    # OUTPUT HELPERS
    # ======================================================

    def _get_output_state(
        self,
        equipment_id: str,
    ) -> DecisionState:

        if self.last_output is None:
            return DecisionState.OFF

        if equipment_id == "boiler":
            return (
                DecisionState.ON
                if self.last_output.boiler == ActuatorState.ON
                else DecisionState.OFF
            )

        if equipment_id == "burner":
            return (
                DecisionState.ON
                if self.last_output.burner == ActuatorState.ON
                else DecisionState.OFF
            )

        if equipment_id == "pump":
            return (
                DecisionState.ON
                if self.last_output.pump == ActuatorState.ON
                else DecisionState.OFF
            )

        return DecisionState.OFF

    def _publish_output(
        self,
        output: OutputSnapshot,
    ) -> None:

        commands = []

        for command in output.commands:

            commands.append(
                {
                    "equipment": command.equipment.value,
                    "state": command.state.value,
                    "command": command.command,
                    "reason_code": command.reason_code,
                    "reason_message": command.reason_message,
                    "timestamp": command.timestamp.isoformat(),
                }
            )

        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "commands": commands,
        }

        self.mqtt.publish_command(
            payload
        )

    def _publish_state(
        self,
        decision: DecisionResult,
        output: OutputSnapshot,
        safety: SafetyResult,
    ) -> None:

        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "decision": {
                "boiler": decision.boiler.value,
                "burner": decision.burner.value,
                "pump": decision.pump.value,
                "priority": int(decision.priority),
                "safety_active": decision.safety_active,
                "schedule_active": decision.schedule_active,
                "heating_required": decision.heating_required,
            },

            "output": {
                "boiler": output.boiler.value,
                "burner": output.burner.value,
                "pump": output.pump.value,
                "commands": len(output.commands),
            },

            "safety": {
                "safe": safety.safe,
                "shutdown_required": safety.shutdown_required,
                "lockout_required": safety.lockout_required,
                "reason": safety.reason,
            },
        }

        self.mqtt.publish_state(
            payload
        )

    # ======================================================
    # SAFETY HISTORY
    # ======================================================

    def _record_safety_events(
        self,
        safety: SafetyResult,
    ) -> None:

        for event in safety.events:

            self.history.record_event(
                event_type=event.rule.code,
                severity=event.rule.action,
                message=event.message,
                data={
                    "sensor_id": event.sensor_id,
                    "value": event.value,
                    "priority": event.rule.priority,
                },
                timestamp=event.timestamp,
            )


def create_app() -> BoilerDecisionEngine:
    return BoilerDecisionEngine(
        settings=get_settings()
    )


def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    app = create_app()

    try:
        app.start()

        if app.settings.mqtt_enabled:
            import threading
            threading.Event().wait()

    except KeyboardInterrupt:
        logger.info(
            "Keyboard interrupt received"
        )

    finally:
        app.stop()


if __name__ == "__main__":
    main()


