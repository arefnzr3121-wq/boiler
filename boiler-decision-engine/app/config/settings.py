from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.constants import (
    DEFAULT_COMFORT_MAX_TEMPERATURE_C,
    DEFAULT_COMFORT_MIN_TEMPERATURE_C,
    DEFAULT_COMFORT_TEMPERATURE_C,
    DEFAULT_HYSTERESIS_C,
    DEFAULT_SENSOR_STALE_SECONDS,
    DEFAULT_SENSOR_TIMEOUT_SECONDS,
    MAX_VALID_TEMPERATURE_C,
    MIN_VALID_TEMPERATURE_C,
    MQ2_MAX_VALUE,
    MQ2_MIN_VALUE,
)


class Settings(BaseSettings):
    """
    تنظیمات اصلی Boiler Decision Engine.

    مقادیر می‌توانند از فایل .env یا Environment Variable
    دریافت شوند.
    """

    # ========================================================
    # APPLICATION
    # ========================================================

    app_name: str = "Boiler Decision Engine"

    environment: str = "development"

    debug: bool = False

    # ========================================================
    # MQTT
    # ========================================================

    mqtt_enabled: bool = True

    mqtt_host: str = "localhost"

    mqtt_port: int = 1883

    mqtt_username: str | None = None

    mqtt_password: str | None = None

    mqtt_client_id: str = "boiler-decision-engine"

    mqtt_keepalive: int = 60

    mqtt_sensor_topic: str = "boiler/sensors"

    mqtt_command_topic: str = "boiler/commands"

    mqtt_state_topic: str = "boiler/state"

    # ========================================================
    # SENSOR VALIDATION
    # ========================================================

    sensor_timeout_seconds: int = Field(
        default=DEFAULT_SENSOR_TIMEOUT_SECONDS,
        ge=1,
    )

    sensor_stale_seconds: int = Field(
        default=DEFAULT_SENSOR_STALE_SECONDS,
        ge=1,
    )

    min_valid_temperature_c: float = (
        MIN_VALID_TEMPERATURE_C
    )

    max_valid_temperature_c: float = (
        MAX_VALID_TEMPERATURE_C
    )

    mq2_min_value: float = MQ2_MIN_VALUE

    mq2_max_value: float = MQ2_MAX_VALUE

    # ========================================================
    # COMFORT
    # ========================================================

    comfort_temperature_c: float = (
        DEFAULT_COMFORT_TEMPERATURE_C
    )

    comfort_min_temperature_c: float = (
        DEFAULT_COMFORT_MIN_TEMPERATURE_C
    )

    comfort_max_temperature_c: float = (
        DEFAULT_COMFORT_MAX_TEMPERATURE_C
    )

    hysteresis_c: float = Field(
        default=DEFAULT_HYSTERESIS_C,
        ge=0.0,
    )

    # ========================================================
    # SAFETY
    # ========================================================

    gas_detection_enabled: bool = True

    temperature_safety_enabled: bool = True

    sensor_failure_safety_enabled: bool = True

    # ========================================================
    # DECISION ENGINE
    # ========================================================

    decision_loop_interval_seconds: float = Field(
        default=1.0,
        gt=0.0,
    )

    # ========================================================
    # RUNTIME / TIMEZONE
    # ========================================================

    # Timezone of the physical building. Schedule calculations in the
    # application layer must use this timezone, not the server timezone.
    timezone: str = "Asia/Tehran"

    # ========================================================
    # EQUIPMENT FEEDBACK
    # ========================================================

    # When enabled, a missing equipment feedback snapshot is treated as
    # unavailable (fail-safe). Keep false only for simulation/bench tests.
    equipment_feedback_required: bool = False

    equipment_feedback_timeout_seconds: int = Field(
        default=15,
        ge=1,
    )

    # ========================================================
    # BUILDING MODEL
    # ========================================================

    building_model: str = "A"

    design_load_w: float = Field(default=10000.0, gt=0.0)
    base_load_per_m2_w: float = Field(default=100.0, gt=0.0)
    thermal_resistance_k_per_w: float = Field(default=0.01, gt=0.0)
    thermal_capacity_wh_per_k: float = Field(default=10000.0, gt=0.0)
    time_step_hours: float = Field(default=1.0, gt=0.0)

    # ========================================================
    # PYDANTIC SETTINGS
    # ========================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Singleton-like access to application settings.

    با این روش در کل پروژه یک نمونه Settings استفاده می‌شود.
    """

    return Settings()