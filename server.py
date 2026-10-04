"""
Web Bridge برای BoilerController
اجرا:  python server.py
سپس مرورگر را روی http://localhost:8000 باز کنید.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from boiler_controller import (
    BoilerController, SimulationHAL, SystemMode, DO, DI, AI, Severity
)

app = FastAPI(title="Boiler Controller HMI")

# ═══════════════════════════════════════════════════════════════════
# Global instances
# ═══════════════════════════════════════════════════════════════════
hal = SimulationHAL()
hal.set_time_scale(1.0)
ctrl = BoilerController(hal)
ctrl.start()

# History buffer for chart
from collections import deque
HISTORY = deque(maxlen=600)

# ═══════════════════════════════════════════════════════════════════
# Helper: Extract full state
# ═══════════════════════════════════════════════════════════════════
def build_full_state() -> dict:
    ctx = ctrl.ctx
    s = ctrl.get_status()

    # Sensors detail
    sensors = {}
    for sid, r in ctrl.sm.readings.items():
        sc = ctrl.sm.configs[sid]
        sensors[sid.value] = {
            "name": sc.name,
            "raw": r.raw_value,
            "filtered": r.filtered_value,
            "corrected": r.corrected_value,
            "offset": sc.offset,
            "roc": r.rate_of_change,
            "status": r.status.name,
            "enabled": sc.enabled,
        }

    # Actuators detail
    actuators = {}
    for do_id, rt in ctrl.actuators.runtime.items():
        actuators[do_id.value] = {
            "name": do_id.name,
            "state": rt.state.name,
            "command": rt.command,
            "feedback": rt.feedback,
            "manual": rt.manual_cmd,
            "runtime_ms": rt.total_runtime_ms,
            "start_count": rt.start_count,
        }

    # DI states
    di_states = {d.value: {
        "name": d.name,
        "value": hal.read_digital_input(d),
        "manual": hal.manual_feedback_override.get(d, False),
    } for d in DI}

    # Alarms
    alarms = []
    for a in ctrl.am.list_active():
        alarms.append({
            "code": a.code,
            "title": a.title,
            "description": a.description,
            "recommendation": a.recommendation,
            "severity": a.severity.name,
            "timestamp_ms": a.timestamp_ms,
            "source": a.source,
            "acknowledged": a.acknowledged,
            "latched": a.latched,
            "recovery": a.recovery.name,
            "confidence": a.confidence,
            "reason_code": a.reason_code,
        })

    # History of alarms
    alarm_history = [{
        "code": a.code, "title": a.title, "severity": a.severity.name,
        "timestamp_ms": a.timestamp_ms,
    } for a in ctrl.am.history[:50]]

    # Logs
    logs = [{
        "ts": l.timestamp_ms, "code": l.event_code,
        "desc": l.description, "value": l.value, "source": l.source,
    } for l in ctrl.logger.recent(100)]

    # Schedule
    schedule = [{
        "enabled": e.enabled, "days_mask": e.days_mask,
        "start_minutes": e.start_minutes, "end_minutes": e.end_minutes,
        "target_temp": e.target_temp, "priority": e.priority,
    } for e in ctrl.sched.entries]

    return {
        "timestamp": datetime.now().isoformat(),
        "sim_time_ms": hal.millis(),
        "time_scale": hal._scale,
        "mode": s["mode"],
        "state": s["state"],
        "safety_locked": s["safety_locked"],
        "heating_demand": s["heating_demand"],
        "setpoint": s["setpoint"],
        "setpoint_src": s["setpoint_src"],
        "error": s["error"],
        "reason_code": s["reason_code"],
        "temperatures": s["temperatures"],
        "flow_ok": s["flow_ok"],
        "pump1_on": s["pump1_on"],
        "burner1_on": s["burner1_on"],
        "sensors": sensors,
        "actuators": actuators,
        "di_states": di_states,
        "alarms": alarms,
        "alarm_history": alarm_history,
        "logs": logs,
        "schedule": schedule,
        "manual_setpoint": ctx.manual_setpoint,
        "retry_count": ctx.retry_count,
        "config": {
            "heating_start_hyst": ctrl.cfg.heating_start_hyst,
            "heating_stop_hyst": ctrl.cfg.heating_stop_hyst,
            "max_supply_temp": ctrl.cfg.max_supply_temp,
            "max_boiler_temp": ctrl.cfg.max_boiler_temp,
            "pump_start_delay_ms": ctrl.cfg.pump_start_delay_ms,
            "flow_confirm_ms": ctrl.cfg.flow_confirm_ms,
            "burner_start_delay_ms": ctrl.cfg.burner_start_delay_ms,
            "burner_min_on_ms": ctrl.cfg.burner_min_on_ms,
            "burner_min_off_ms": ctrl.cfg.burner_min_off_ms,
            "pump_post_run_ms": ctrl.cfg.pump_post_run_ms,
            "min_expected_rise": ctrl.cfg.min_expected_rise,
            "wc_enabled": ctrl.cfg.wc_enabled,
            "outdoor_min": ctrl.cfg.outdoor_min,
            "outdoor_max": ctrl.cfg.outdoor_max,
            "supply_min": ctrl.cfg.supply_min,
            "supply_max": ctrl.cfg.supply_max,
            "curve_slope": ctrl.cfg.curve_slope,
            "safety_reset_confirm_ms": ctrl.cfg.safety_reset_confirm_ms,
        },
    }

# ═══════════════════════════════════════════════════════════════════
# HTTP Endpoints
# ═══════════════════════════════════════════════════════════════════
@app.get("/")
async def root():
    html = Path(__file__).parent / "hmi.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>hmi.html not found</h1>")

@app.get("/api/state")
async def api_state():
    return build_full_state()

@app.get("/api/history")
async def api_history():
    return list(HISTORY)

# ═══════════════════════════════════════════════════════════════════
# WebSocket
# ═══════════════════════════════════════════════════════════════════
class ConnectionManager:
    def __init__(self):
        self.clients: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)
    async def broadcast(self, msg: dict):
        text = json.dumps(msg)
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

mgr = ConnectionManager()

async def state_broadcaster():
    """هر ۵۰۰ms وضعیت را برای همه کلاینت‌ها بفرستد."""
    while True:
        try:
            state = build_full_state()
            # اضافه به History
            HISTORY.append({
                "t": state["sim_time_ms"] / 1000.0,
                "supply": state["temperatures"].get("supply"),
                "return": state["temperatures"].get("return"),
                "boiler": state["temperatures"].get("boiler"),
                "outdoor": state["temperatures"].get("outdoor"),
                "setpoint": state["setpoint"],
            })
            await mgr.broadcast({"type": "state", "data": state})
        except Exception as e:
            print(f"[broadcaster] error: {e}")
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(state_broadcaster())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await mgr.connect(ws)
    try:
        # ارسال اولیه
        await ws.send_text(json.dumps({"type": "state",
                                       "data": build_full_state()}))
        while True:
            text = await ws.receive_text()
            msg = json.loads(text)
            await handle_command(msg)
    except WebSocketDisconnect:
        mgr.disconnect(ws)
    except Exception as e:
        print(f"[ws] error: {e}")
        mgr.disconnect(ws)

# ═══════════════════════════════════════════════════════════════════
# Command Handler
# ═══════════════════════════════════════════════════════════════════
async def handle_command(msg: dict):
    action = msg.get("action")

    # ---- Mode ----
    if action == "set_mode":
        mode_name = msg.get("mode", "AUTO")
        try:
            mode = SystemMode[mode_name]
            ctrl.set_mode(mode)
        except KeyError:
            pass

    # ---- Manual Setpoint ----
    elif action == "set_manual_setpoint":
        ctrl.set_manual_setpoint(float(msg.get("temp", 65)))

    # ---- Boost ----
    elif action == "boost":
        ctrl.start_boost()

    # ---- Master Reset ----
    elif action == "master_reset":
        ctrl.master_reset()

    # ---- Sensor Manual Override ----
    elif action == "set_sensor":
        sid = AI(int(msg["id"]))
        hal.manual_sensor_override[sid] = bool(msg.get("manual", False))
        if msg.get("manual"):
            hal.manual_sensor_values[sid] = float(msg.get("value", 0))

    elif action == "set_sensor_value":
        sid = AI(int(msg["id"]))
        hal.manual_sensor_values[sid] = float(msg["value"])

    elif action == "clear_sensor_override":
        sid = AI(int(msg["id"]))
        hal.manual_sensor_override[sid] = False

    # ---- DI Manual ----
    elif action == "set_di":
        di_id = DI(int(msg["id"]))
        hal.manual_feedback_override[di_id] = True
        hal.manual_feedback_values[di_id] = bool(msg["value"])

    elif action == "clear_di_override":
        di_id = DI(int(msg["id"]))
        hal.manual_feedback_override[di_id] = False

    # ---- Time Scale ----
    elif action == "set_time_scale":
        hal.set_time_scale(float(msg.get("scale", 1.0)))

    # ---- Actuator Manual ----
    elif action == "set_actuator_manual":
        do_id = DO(int(msg["id"]))
        val = msg.get("value")  # null = AUTO, true = ON, false = OFF
        ctrl.actuators.set_manual(do_id, val)

    # ---- Config ----
    elif action == "update_config":
        key = msg.get("key")
        value = msg.get("value")
        if hasattr(ctrl.cfg, key):
            setattr(ctrl.cfg, key, value)

    # ---- Schedule ----
    elif action == "add_schedule":
        from boiler_controller import ScheduleEntry
        e = ScheduleEntry(
            enabled=bool(msg.get("enabled", True)),
            days_mask=int(msg.get("days_mask", 127)),
            start_minutes=int(msg.get("start_minutes", 0)),
            end_minutes=int(msg.get("end_minutes", 1440)),
            target_temp=float(msg.get("target_temp", 65)),
            priority=int(msg.get("priority", 1)),
        )
        ctrl.sched.entries.append(e)

    elif action == "remove_schedule":
        idx = int(msg.get("index", -1))
        if 0 <= idx < len(ctrl.sched.entries):
            ctrl.sched.entries.pop(idx)

    # ---- Scenarios ----
    elif action == "scenario":
        await run_scenario(msg.get("name"), msg)

    # ---- Acknowledge Alarm ----
    elif action == "ack_alarm":
        ctrl.am.ack(msg.get("code", ""))

    elif action == "clear_alarm":
        ctrl.am.clear(msg.get("code", ""))


async def run_scenario(name: str, msg: dict):
    """اجرای سناریوهای آماده."""
    # ریست کامل
    ctrl.master_reset()
    # آزاد کردن همه overrideها
    for sid in AI:
        hal.manual_sensor_override[sid] = False
    for d in DI:
        hal.manual_feedback_override[d] = False
    for do_id in DO:
        ctrl.actuators.set_manual(do_id, None)

    # پیش‌فرض‌ها
    hal.set_time_scale(60.0)

    if name == "normal":
        hal.analog[AI.SUPPLY] = 45.0
        hal.analog[AI.BOILER1] = 50.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "setpoint_reached":
        hal.analog[AI.SUPPLY] = 55.0
        hal.analog[AI.BOILER1] = 60.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "pump_fail":
        hal.analog[AI.SUPPLY] = 45.0
        hal.manual_feedback_override[DI.PUMP1_FB] = True
        hal.manual_feedback_values[DI.PUMP1_FB] = False
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "flow_fail":
        hal.analog[AI.SUPPLY] = 45.0
        hal.manual_feedback_override[DI.PUMP1_FB] = True
        hal.manual_feedback_values[DI.PUMP1_FB] = True
        hal.manual_feedback_override[DI.FLOW_SWITCH] = True
        hal.manual_feedback_values[DI.FLOW_SWITCH] = False
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "burner_fail":
        hal.analog[AI.SUPPLY] = 45.0
        hal.manual_feedback_override[DI.PUMP1_FB] = True
        hal.manual_feedback_values[DI.PUMP1_FB] = True
        hal.manual_feedback_override[DI.FLOW_SWITCH] = True
        hal.manual_feedback_values[DI.FLOW_SWITCH] = True
        hal.manual_feedback_override[DI.BURNER1_FB] = True
        hal.manual_feedback_values[DI.BURNER1_FB] = False
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "no_response":
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 55.0
        hal.manual_sensor_override[AI.BOILER1] = True
        hal.manual_sensor_values[AI.BOILER1] = 56.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "sensor_stuck":
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 55.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "overtemp":
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 95.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "boiler_over":
        hal.manual_sensor_override[AI.BOILER1] = True
        hal.manual_sensor_values[AI.BOILER1] = 97.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "antifreeze":
        hal.analog[AI.SUPPLY] = 5.0
        hal.analog[AI.OUTDOOR] = -5.0
        hal.analog[AI.BOILER1] = 8.0
        ctrl.set_mode(SystemMode.AUTO)

    elif name == "estop":
        hal.manual_feedback_override[DI.EMERGENCY_STOP] = True
        hal.manual_feedback_values[DI.EMERGENCY_STOP] = True

    elif name == "outdoor_fail":
        hal.manual_sensor_override[AI.OUTDOOR] = True
        hal.manual_sensor_values[AI.OUTDOOR] = -100.0  # خارج از محدوده

    elif name == "sensor_invalid":
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 200.0

    elif name == "high_return":
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 45.0
        hal.manual_sensor_override[AI.RETURN] = True
        hal.manual_sensor_values[AI.RETURN] = 55.0


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("╔" + "═" * 68 + "╗")
    print("║   Boiler Controller HMI Server                                    ║")
    print("║   ►  http://localhost:8000                                        ║")
    print("╚" + "═" * 68 + "╝")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")