from enum import Enum

from pydantic import BaseModel, Field


class BuildingType(str, Enum):
    RESIDENTIAL = "residential"
    OFFICE = "office"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED = "mixed"


class InsulationLevel(str, Enum):
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    EXCELLENT = "excellent"


class BuildingModelType(str, Enum):
    MODEL_A = "A"
    MODEL_B = "B"
    MODEL_C = "C"
    MODEL_D = "D"
    MODEL_E = "E"


class BuildingInfo(BaseModel):
    """
    مشخصات فیزیکی و پایه ساختمان.
    """

    building_id: str = Field(min_length=1)

    name: str = Field(min_length=1)

    building_type: BuildingType = BuildingType.RESIDENTIAL

    floor_count: int = Field(
        default=1,
        ge=1,
    )

    floor_area_m2: float = Field(
        default=100.0,
        gt=0.0,
    )

    occupancy_count: int = Field(
        default=1,
        ge=0,
    )

    insulation_level: InsulationLevel = (
        InsulationLevel.AVERAGE
    )

    model_type: BuildingModelType = (
        BuildingModelType.MODEL_A
    )

    design_indoor_temperature_c: float = Field(
        default=21.0,
        ge=5.0,
        le=35.0,
    )

    design_outdoor_temperature_c: float = Field(
        default=0.0,
        ge=-50.0,
        le=50.0,
    )