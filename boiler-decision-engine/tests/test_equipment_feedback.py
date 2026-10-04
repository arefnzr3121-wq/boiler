from datetime import datetime, timezone

from app.equipment_feedback import EquipmentFeedbackParser


def test_equipment_feedback_parser_reads_states_and_faults():
    snapshot = EquipmentFeedbackParser().parse(
        {
            "equipment": {
                "boiler": {
                    "is_available": True,
                    "actual_state": "on",
                    "water_temperature_c": 72.0,
                },
                "burner": {
                    "is_available": True,
                    "actual_state": "on",
                    "flame_detected": True,
                },
                "pump": {
                    "is_available": True,
                    "actual_state": "on",
                    "flow_detected": True,
                    "speed_percent": 80,
                },
            }
        },
        timestamp=datetime.now(timezone.utc),
    )

    assert snapshot.boiler.actual_state.value == "on"
    assert snapshot.burner.flame_detected is True
    assert snapshot.pump.flow_detected is True
    assert snapshot.pump.speed_percent == 80
