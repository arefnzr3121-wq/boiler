from pydantic import BaseModel, Field, model_validator


class ComfortSettings(BaseModel):
    """
    تنظیمات آسایش حرارتی ساختمان.
    """

    target_temperature_c: float = Field(
        default=21.0,
        ge=5.0,
        le=35.0,
    )

    minimum_temperature_c: float = Field(
        default=20.0,
        ge=5.0,
        le=35.0,
    )

    maximum_temperature_c: float = Field(
        default=22.0,
        ge=5.0,
        le=35.0,
    )

    hysteresis_c: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
    )

    offset_c: float = Field(
        default=0.0,
        ge=-10.0,
        le=10.0,
    )

    @model_validator(mode="after")
    def validate_temperature_range(self):
        if self.minimum_temperature_c > self.target_temperature_c:
            raise ValueError(
                "Minimum temperature cannot be greater "
                "than target temperature"
            )

        if self.target_temperature_c > self.maximum_temperature_c:
            raise ValueError(
                "Target temperature cannot be greater "
                "than maximum temperature"
            )

        return self


class ComfortState(BaseModel):
    """
    وضعیت لحظه‌ای آسایش.
    """

    indoor_temperature_c: float

    outdoor_temperature_c: float | None = None

    effective_target_temperature_c: float

    comfort_minimum_c: float

    comfort_maximum_c: float

    heating_required: bool = False

    comfort_satisfied: bool = False


class ComfortSnapshot(BaseModel):
    """
    snapshot کامل اطلاعات آسایش در یک لحظه.
    """

    settings: ComfortSettings

    state: ComfortState