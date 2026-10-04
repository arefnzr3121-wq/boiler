from datetime import datetime, timezone
from typing import Any

from app.models.equipment import (
    BoilerState,
    BurnerState,
    EquipmentSnapshot,
    PumpState,
)


class EquipmentFeedbackParser:
    """Parse equipment feedback received from MQTT."""

    def parse(
        self,
        payload: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> EquipmentSnapshot:
        raw = payload.get("equipment", payload)
        if not isinstance(raw, dict):
            raise ValueError("equipment feedback must be an object")

        now = timestamp or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        return EquipmentSnapshot(
            timestamp=now,
            boiler=self._boiler(raw.get("boiler", {})),
            burner=self._burner(raw.get("burner", {})),
            pump=self._pump(raw.get("pump", {})),
        )

    def _common(self, data: dict[str, Any], equipment_id: str) -> dict[str, Any]:
        if not isinstance(data, dict):
            data = {}

        actual = str(data.get("actual_state", "off")).lower()
        requested = str(data.get("requested_state", "off")).lower()

        return {
            "equipment_id": equipment_id,
            "is_available": bool(data.get("is_available", True)),
            "is_running": bool(data.get("is_running", actual == "on")),
            "requested_state": requested,
            "actual_state": actual,
            "fault": bool(data.get("fault", False)),
            "fault_code": data.get("fault_code"),
            "runtime_seconds": max(0.0, float(data.get("runtime_seconds", 0.0))),
        }

    def _boiler(self, data: dict[str, Any]) -> BoilerState:
        common = self._common(data, "boiler")
        common["water_temperature_c"] = data.get("water_temperature_c")
        common["target_temperature_c"] = data.get("target_temperature_c")
        return BoilerState(**common)

    def _burner(self, data: dict[str, Any]) -> BurnerState:
        common = self._common(data, "burner")
        common["flame_detected"] = bool(data.get("flame_detected", False))
        common["ignition_attempts"] = max(0, int(data.get("ignition_attempts", 0)))
        return BurnerState(**common)

    def _pump(self, data: dict[str, Any]) -> PumpState:
        common = self._common(data, "pump")
        common["flow_detected"] = data.get("flow_detected")
        common["speed_percent"] = float(data.get("speed_percent", 100.0))
        return PumpState(**common)
