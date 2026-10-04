from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config.constants import DecisionState
from app.config.settings import Settings
from app.main import BoilerDecisionEngine


# ============================================================
# API TEST ENGINE
# ============================================================

settings = Settings(
    mqtt_enabled=False,
    environment="test",
)

engine = BoilerDecisionEngine(
    settings=settings
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Boiler Decision Engine Test API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class SensorInput(BaseModel):
    indoor_temperature: float = Field(default=20.0)
    outdoor_temperature: float = Field(default=10.0)
    boiler_temperature: float = Field(default=60.0)
    gas_raw: float = Field(default=300.0)

    target_temperature: float = Field(default=21.0)
    offset: float = Field(default=0.0)

    schedule_active: bool = Field(default=True)
    preheating_active: bool = Field(default=False)

    boiler_available: bool = Field(default=True)
    burner_available: bool = Field(default=True)
    pump_available: bool = Field(default=True)


class EvaluateRequest(BaseModel):
    mode: str = Field(default="AUTO")
    action: str = Field(default="RUN")

    sensors: SensorInput = Field(
        default_factory=SensorInput
    )

    fault_sensor: bool = False
    fault_communication: bool = False
    fault_boiler: bool = False


# ============================================================
# HELPERS
# ============================================================

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_sensor_payload(
    data: SensorInput,
    fault_sensor: bool = False,
    fault_communication: bool = False,
) -> dict[str, Any]:

    now = _timestamp()

    if fault_sensor:
        indoor_status = "invalid"
    else:
        indoor_status = "ok"

    payload = {
        "timestamp": now,
        "sensors": [
            {
                "sensor_id": "indoor_temperature",
                "sensor_type": "ds18b20",
                "value": data.indoor_temperature,
                "unit": "°C",
                "status": indoor_status,
                "timestamp": now,
            },
            {
                "sensor_id": "outdoor_temperature",
                "sensor_type": "ds18b20",
                "value": data.outdoor_temperature,
                "unit": "°C",
                "status": "ok",
                "timestamp": now,
            },
            {
                "sensor_id": "boiler_temperature",
                "sensor_type": "ds18b20",
                "value": data.boiler_temperature,
                "unit": "°C",
                "status": "ok",
                "timestamp": now,
            },
            {
                "sensor_id": "gas_sensor",
                "sensor_type": "mq2",
                "value": data.gas_raw,
                "unit": "raw",
                "status": "ok",
                "timestamp": now,
            },
        ],
    }

    if fault_communication:
        payload["communication_fault"] = True

    return payload


def _decision_response(
    output,
    action: str = "RUN",
) -> dict[str, Any]:

    decision = engine.last_decision

    if decision is None:
        decision_name = "UNKNOWN"
        reason_code = ""
        reason_message = ""
        safety_active = False
    else:
        decision_name = decision.boiler.value

        if decision.reasons:
            reason = decision.reasons[0]
            reason_code = reason.code
            reason_message = reason.message
        else:
            reason_code = ""
            reason_message = ""

        safety_active = decision.safety_active

    return {
        "timestamp": _timestamp(),
        "action": action,
        "decision": decision_name,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "safety_active": safety_active,
        "actuators": {
            "boiler": output.boiler.value,
            "burner": output.burner.value,
            "pump": output.pump.value,
        },
        "commands": [
            {
                "equipment": command.equipment.value,
                "state": command.state.value,
                "command": command.command,
                "reason_code": command.reason_code,
                "reason_message": command.reason_message,
                "timestamp": command.timestamp.isoformat(),
            }
            for command in output.commands
        ],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/test/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "boiler-decision-engine",
        "timestamp": _timestamp(),
    }


# ============================================================
# STATE
# ============================================================

@app.get("/api/test/state")
def state() -> dict[str, Any]:

    decision = engine.last_decision
    output = engine.last_output

    return {
        "timestamp": _timestamp(),
        "decision": (
            decision.boiler.value
            if decision is not None
            else "UNKNOWN"
        ),
        "safety_active": (
            decision.safety_active
            if decision is not None
            else False
        ),
        "actuators": (
            {
                "boiler": output.boiler.value,
                "burner": output.burner.value,
                "pump": output.pump.value,
            }
            if output is not None
            else {
                "boiler": "OFF",
                "burner": "OFF",
                "pump": "OFF",
            }
        ),
    }


# ============================================================
# EVALUATE
# ============================================================

@app.post("/api/test/evaluate")
def evaluate(request: EvaluateRequest):

    mode = request.mode.upper()
    action = request.action.upper()

    if mode not in {"AUTO", "MANUAL"}:
        raise HTTPException(
            status_code=400,
            detail="mode must be AUTO or MANUAL",
        )

    if action == "STOP":
        output = engine.output_engine.evaluate(
            decision_state=DecisionState.OFF,
            reason_code="TEST_STOP",
            reason_message="Test panel requested STOP",
        )

        engine.last_output = output

        return _decision_response(
            output,
            action="STOP",
        )

    if action == "SAFETY":
        output = engine.output_engine.evaluate(
            decision_state=DecisionState.SAFETY_OFF,
            reason_code="TEST_SAFETY",
            reason_message="Test panel requested safety shutdown",
        )

        engine.last_output = output

        return _decision_response(
            output,
            action="SAFETY",
        )

    payload = _build_sensor_payload(
        request.sensors,
        fault_sensor=request.fault_sensor,
        fault_communication=request.fault_communication,
    )

    output = engine.process_sensor_payload(
        payload
    )

    return _decision_response(
        output,
        action=action,
    )


# ============================================================
# SAFETY
# ============================================================

@app.post("/api/test/safety")
def safety():

    output = engine.output_engine.evaluate(
        decision_state=DecisionState.SAFETY_OFF,
        reason_code="TEST_SAFETY",
        reason_message="Manual test safety shutdown",
    )

    engine.last_output = output

    return _decision_response(
        output,
        action="SAFETY",
    )


# ============================================================
# RESET SAFETY
# ============================================================

@app.post("/api/test/reset-safety")
def reset_safety():

    engine.safety_engine = type(
        engine.safety_engine
    )()

    engine.last_output = None
    engine.last_decision = None
    engine.last_sensor_readings = []
    engine.previous_heating_state = False

    return {
        "status": "ok",
        "message": "Safety test state reset",
        "timestamp": _timestamp(),
    }
