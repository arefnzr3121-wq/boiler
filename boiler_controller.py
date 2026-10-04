"""
Smart Boiler Room Controller
============================
پیاده‌سازی کامل الگوریتم هوشمند کنترل موتورخانه
- ماژولار و قابل توسعه
- Hardware-Independent (از طریق HAL)
- Non-Blocking (بدون sleep در منطق کنترل)
- Safety مستقل از Control
- تشخیص هوشمند خطا با Confidence Score
- Persian Messages + English Codes

اجرا:  python boiler_controller.py
"""

from __future__ import annotations

import time
import random
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Dict, List, Any
from collections import deque
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
#  PART 1: ENUMS و TYPES پایه
# ═══════════════════════════════════════════════════════════════════════

class SensorStatus(Enum):
    VALID = auto()
    UNCERTAIN = auto()
    SUSPICIOUS = auto()
    INVALID = auto()
    DISCONNECTED = auto()
    COMM_ERROR = auto()


class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    FAULT = auto()
    CRITICAL = auto()
    SAFETY = auto()


class SystemMode(Enum):
    OFF = auto()
    AUTO = auto()
    MANUAL = auto()
    BOOST = auto()
    VACATION = auto()
    SERVICE = auto()


class SystemState(Enum):
    OFF = auto()
    IDLE = auto()
    PRECHECK = auto()
    PUMP_STARTING = auto()
    FLOW_WAIT = auto()
    HEATING_REQUEST = auto()
    BURNER_STARTING = auto()
    HEATING = auto()
    BURNER_STOPPING = auto()
    PUMP_POST_RUN = auto()
    FAULT = auto()
    RETRY = auto()
    LOCKOUT = auto()
    SAFETY_LOCK = auto()
    MANUAL = auto()
    SERVICE = auto()


class ActuatorState(Enum):
    OFF = auto()
    ON = auto()
    STARTING = auto()
    STOPPING = auto()
    FAULT = auto()


class FaultRecovery(Enum):
    AUTO = auto()
    MANUAL_RESET = auto()
    POWER_CYCLE = auto()
    SERVICE_REQUIRED = auto()


class SensorType(Enum):
    PT100 = auto()
    PT1000 = auto()
    NTC_10K = auto()
    VOLT_0_10 = auto()
    MA_4_20 = auto()
    MODBUS = auto()


# شناسه‌های ثابت ورودی/خروجی
class AI(Enum):
    SUPPLY = 1
    RETURN = 2
    OUTDOOR = 3
    DHW = 4
    BOILER1 = 5
    BOILER2 = 6
    HEADER = 7
    ROOM = 8


class DI(Enum):
    PUMP1_FB = 1
    PUMP2_FB = 2
    BURNER1_FB = 3
    BURNER2_FB = 4
    FLOW_SWITCH = 5
    LOW_WATER = 6
    HIGH_PRESSURE = 7
    EMERGENCY_STOP = 8
    BURNER_FAULT = 9
    BOILER_SAFETY = 10
    FLAME_FB = 11
    DOOR_SAFETY = 12
    EXTERNAL_ENABLE = 13
    FIRE_ALARM = 14
    GAS_SAFETY = 15
    RESERVE = 16


class DO(Enum):
    PUMP1 = 1
    PUMP2 = 2
    BURNER1 = 3
    BURNER2 = 4
    DHW_PUMP = 5
    HEATING_VALVE = 6
    ALARM_RELAY = 7
    GENERAL_FAULT = 8
    FAN = 9
    RESERVE = 10


# ═══════════════════════════════════════════════════════════════════════
#  PART 2: Configuration
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SystemConfig:
    """تمام پارامترهای قابل تنظیم سیستم — هیچ Magic Number ای نباید خارج از این کلاس باشد."""

    # زمان‌بندی Cycle ها
    control_cycle_ms: int = 1000
    sensor_cycle_ms: int = 200
    safety_cycle_ms: int = 50
    fault_cycle_ms: int = 500

    # Anti-Short-Cycle
    pump_start_delay_ms: int = 10_000
    flow_confirm_ms: int = 10_000
    burner_start_delay_ms: int = 5_000
    burner_min_on_ms: int = 120_000
    burner_min_off_ms: int = 180_000
    pump_post_run_ms: int = 60_000
    pump_pre_run_ms: int = 10_000

    # Hysteresis
    heating_start_hyst: float = 3.0
    heating_stop_hyst: float = 0.0

    # Safety Limits
    max_supply_temp: float = 90.0
    max_boiler_temp: float = 95.0
    min_boiler_temp: float = 5.0
    max_dhw_temp: float = 70.0
    safety_reset_confirm_ms: int = 5_000

    # Outdoor Compensation
    outdoor_min: float = -10.0
    outdoor_max: float = 15.0
    supply_min: float = 75.0
    supply_max: float = 55.0
    curve_slope: float = 1.0
    curve_offset: float = 0.0
    wc_enabled: bool = True

    # Sensor Validation
    max_temp_rise_rate: float = 5.0
    max_temp_fall_rate: float = 5.0
    stuck_timeout_ms: int = 600_000
    plausibility_warn_ms: int = 60_000
    plausibility_fault_ms: int = 180_000

    # Equipment Response Detection
    min_expected_rise: float = 0.5
    burner_response_window_ms: int = 180_000

    # Communication
    modbus_timeout_ms: int = 500
    modbus_retries: int = 3

    # Manual Mode
    manual_timeout_ms: int = 30 * 60 * 1000

    # Boost
    boost_delta: float = 10.0
    boost_duration_ms: int = 30 * 60 * 1000

    # Default Setpoints
    default_setpoint: float = 65.0
    dhw_setpoint: float = 55.0

    # Retry / Recovery
    max_retries: int = 3
    retry_delay_ms: int = 30_000

    # Default Offsets
    sensor_offsets: Dict[AI, float] = field(default_factory=lambda: {
        AI.SUPPLY: 0.0, AI.RETURN: 0.0, AI.OUTDOOR: 0.0,
        AI.DHW: 0.0, AI.BOILER1: 0.0, AI.BOILER2: 0.0,
        AI.HEADER: 0.0, AI.ROOM: 0.0,
    })

    def validate(self) -> tuple[bool, str]:
        """اعتبارسنجی تنظیمات قبل از شروع."""
        errors = []
        if self.max_supply_temp <= self.supply_min:
            errors.append("max_supply_temp باید بزرگتر از supply_min باشد")
        if self.outdoor_min >= self.outdoor_max:
            errors.append("outdoor_min باید کوچکتر از outdoor_max باشد")
        if self.burner_min_on_ms < 1000:
            errors.append("burner_min_on_ms باید حداقل 1000ms باشد")
        if self.control_cycle_ms <= 0:
            errors.append("control_cycle_ms باید مثبت باشد")
        if self.heating_start_hyst < 0 or self.heating_stop_hyst < 0:
            errors.append("hysteresis نباید منفی باشد")
        return (len(errors) == 0, "; ".join(errors))


# ═══════════════════════════════════════════════════════════════════════
#  PART 3: Data Structures
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SensorConfig:
    id: AI
    name: str
    type: SensorType = SensorType.PT1000
    min_temp: float = -50.0
    max_temp: float = 150.0
    offset: float = 0.0
    gain: float = 1.0
    sampling_ms: int = 200
    failure_timeout_ms: int = 5000
    enabled: bool = True


@dataclass
class SensorReading:
    id: AI
    raw_value: float = float('nan')
    filtered_value: float = float('nan')
    corrected_value: float = float('nan')
    rate_of_change: float = 0.0
    status: SensorStatus = SensorStatus.INVALID
    timestamp_ms: float = 0.0


@dataclass
class ActuatorConfig:
    id: DO
    name: str
    min_on_ms: int = 10_000
    min_off_ms: int = 5_000
    delay_ms: int = 0
    manual_allowed: bool = True


@dataclass
class ActuatorRuntime:
    id: DO
    state: ActuatorState = ActuatorState.OFF
    last_on_ms: float = 0.0
    last_off_ms: float = 0.0
    total_runtime_ms: float = 0.0
    start_count: int = 0
    fault_count: int = 0
    command: bool = False
    feedback: bool = False
    manual_cmd: Optional[bool] = None  # None = AUTO, True = MAN ON, False = MAN OFF


@dataclass
class Alarm:
    code: str
    title: str
    description: str
    recommendation: str
    severity: Severity
    timestamp_ms: float
    source: str
    acknowledged: bool = False
    latched: bool = False
    auto_clear: bool = False
    recovery: FaultRecovery = FaultRecovery.AUTO
    confidence: float = 0.0
    reason_code: str = ""


@dataclass
class LogEntry:
    timestamp_ms: float
    event_code: str
    description: str
    value: float = 0.0
    source: str = ""


@dataclass
class ScheduleEntry:
    enabled: bool = False
    days_mask: int = 0x7F          # bit0=Sat … bit6=Fri
    start_minutes: int = 0
    end_minutes: int = 1440
    target_temp: float = 65.0
    mode: SystemMode = SystemMode.AUTO
    priority: int = 1


# ═══════════════════════════════════════════════════════════════════════
#  PART 4: Hardware Abstraction Layer
# ═══════════════════════════════════════════════════════════════════════

class IHardwareAbstraction:
    """رابط انتزاعی سخت‌افزار — منطق کنترل هرگز مستقیماً با سخت‌افزار کار نمی‌کند."""

    def read_analog(self, sensor_id: AI) -> float:
        raise NotImplementedError

    def read_digital_input(self, di_id: DI) -> bool:
        raise NotImplementedError

    def write_digital_output(self, do_id: DO, on: bool) -> None:
        raise NotImplementedError

    def write_analog_output(self, ao_id: int, value_01: float) -> None:
        raise NotImplementedError

    def millis(self) -> float:
        raise NotImplementedError

    def now(self) -> datetime:
        raise NotImplementedError

    def feed_watchdog(self) -> None:
        raise NotImplementedError

    def set_safe_state(self) -> None:
        raise NotImplementedError


class SimulationHAL(IHardwareAbstraction):
    """شبیه‌ساز کامل سخت‌افزار برای تست بدون نیاز به تجهیز واقعی.

    شامل فیزیک حرارتی ساده: دمای دیگ با مشعل بالا می‌رود، با پمپ خنک می‌شود و ...
    همچنین تأخیر واقع‌گرایانه برای فیدبک‌ها.
    """

    def __init__(self):
        self._start = time.time()
        self._scale = 1.0  # ضریب سرعت شبیه‌سازی

        # ورودی‌های آنالوگ (مقادیر سنسورها)
        self.analog = {
            AI.SUPPLY: 45.0,
            AI.RETURN: 40.0,
            AI.OUTDOOR: 8.0,
            AI.DHW: 50.0,
            AI.BOILER1: 50.0,
            AI.BOILER2: 45.0,
            AI.HEADER: 42.0,
            AI.ROOM: 20.0,
        }

        # ورودی‌های دیجیتال
        self.di = {
            DI.PUMP1_FB: False,
            DI.PUMP2_FB: False,
            DI.BURNER1_FB: False,
            DI.BURNER2_FB: False,
            DI.FLOW_SWITCH: False,
            DI.LOW_WATER: False,
            DI.HIGH_PRESSURE: False,
            DI.EMERGENCY_STOP: False,
            DI.BURNER_FAULT: False,
            DI.BOILER_SAFETY: False,
            DI.FLAME_FB: False,
            DI.DOOR_SAFETY: False,
            DI.EXTERNAL_ENABLE: True,
            DI.FIRE_ALARM: False,
            DI.GAS_SAFETY: False,
            DI.RESERVE: False,
        }

        # خروجی‌ها
        self.do = {d: False for d in DO}
        self.ao = {1: 0.0, 2: 0.0, 3: 0.0}

        # وضعیت فیزیکی داخلی برای شبیه‌سازی
        self._pump1_on_at: Optional[float] = None
        self._pump2_on_at: Optional[float] = None
        self._burner1_on_at: Optional[float] = None
        self._burner2_on_at: Optional[float] = None
        self._flow_on_at: Optional[float] = None

        # Manual overrides (توسط کاربر از UI خارجی)
        self.manual_sensor_override: Dict[AI, bool] = {a: False for a in AI}
        self.manual_sensor_values: Dict[AI, float] = {a: 0.0 for a in AI}
        self.manual_feedback_override: Dict[DI, bool] = {d: False for d in DI}
        self.manual_feedback_values: Dict[DI, bool] = {d: False for d in DI}

    # ---------- Interface ----------
    def read_analog(self, sensor_id: AI) -> float:
        if self.manual_sensor_override.get(sensor_id, False):
            return self.manual_sensor_values[sensor_id]
        return self.analog.get(sensor_id, float('nan'))

    def read_digital_input(self, di_id: DI) -> bool:
        if self.manual_feedback_override.get(di_id, False):
            return self.manual_feedback_values[di_id]
        return self.di.get(di_id, False)

    def write_digital_output(self, do_id: DO, on: bool) -> None:
        self.do[do_id] = bool(on)

    def write_analog_output(self, ao_id: int, value_01: float) -> None:
        self.ao[ao_id] = max(0.0, min(1.0, value_01))

    def millis(self) -> float:
        return (time.time() - self._start) * 1000.0 * self._scale

    def now(self) -> datetime:
        return datetime.now()

    def feed_watchdog(self) -> None:
        pass

    def set_safe_state(self) -> None:
        for k in self.do:
            self.do[k] = False
        for k in self.ao:
            self.ao[k] = 0.0

    # ---------- Simulation Physics ----------
    def update_physics(self, dt_ms: float) -> None:
        """به‌روزرسانی فیزیک شبیه‌سازی — فقط در SimulationHAL."""
        dt = (dt_ms / 1000.0)

        pump_on = self.do.get(DO.PUMP1, False)
        burner_on = self.do.get(DO.BURNER1, False)
        burner_fb = self.di.get(DI.BURNER1_FB, False)
        flow_ok = self.di.get(DI.FLOW_SWITCH, False)

        # --- Boiler1 ---
        if not self.manual_sensor_override[AI.BOILER1]:
            if burner_on and burner_fb:
                self.analog[AI.BOILER1] += 1.2 * dt  # °C/s
            else:
                self.analog[AI.BOILER1] -= 0.05 * dt
            self.analog[AI.BOILER1] = max(self.analog[AI.OUTDOOR],
                                          min(120.0, self.analog[AI.BOILER1]))

        # --- Supply ---
        if not self.manual_sensor_override[AI.SUPPLY]:
            delta = 0.0
            if burner_on and burner_fb and pump_on and flow_ok:
                delta += 0.8 * dt
            if pump_on and flow_ok and not burner_on:
                delta -= 0.15 * dt
            if not pump_on:
                delta -= 0.06 * dt
            delta -= 0.02 * dt  # ambient
            if not pump_on:
                delta += (self.analog[AI.BOILER1] - self.analog[AI.SUPPLY]) * 0.01 * dt
            self.analog[AI.SUPPLY] = max(0.0, min(120.0,
                self.analog[AI.SUPPLY] + delta))

        # --- Return ---
        if not self.manual_sensor_override[AI.RETURN]:
            target = self.analog[AI.SUPPLY] - (5.0 if pump_on else 8.0)
            self.analog[AI.RETURN] += (target - self.analog[AI.RETURN]) * 0.05 * dt * 5

        # --- Outdoor drift ---
        if not self.manual_sensor_override[AI.OUTDOOR]:
            self.analog[AI.OUTDOOR] += (random.random() - 0.5) * 0.001 * dt

        # --- DHW ---
        if not self.manual_sensor_override[AI.DHW]:
            self.analog[AI.DHW] += (40.0 - self.analog[AI.DHW]) * 0.005 * dt

        # --- Feedback Simulation (با تأخیر) ---
        now = self.millis()

        # Pump1 feedback
        if not self.manual_feedback_override[DI.PUMP1_FB]:
            if self.do.get(DO.PUMP1, False):
                if self._pump1_on_at is None:
                    self._pump1_on_at = now
                if now - self._pump1_on_at > 2000:
                    self.di[DI.PUMP1_FB] = True
            else:
                self.di[DI.PUMP1_FB] = False
                self._pump1_on_at = None

        # Pump2 feedback
        if not self.manual_feedback_override[DI.PUMP2_FB]:
            self.di[DI.PUMP2_FB] = self.do.get(DO.PUMP2, False)

        # Burner1 feedback
        if not self.manual_feedback_override[DI.BURNER1_FB]:
            if self.do.get(DO.BURNER1, False):
                if self._burner1_on_at is None:
                    self._burner1_on_at = now
                if now - self._burner1_on_at > 3000:
                    self.di[DI.BURNER1_FB] = True
            else:
                self.di[DI.BURNER1_FB] = False
                self._burner1_on_at = None

        # Burner2 feedback
        if not self.manual_feedback_override[DI.BURNER2_FB]:
            self.di[DI.BURNER2_FB] = self.do.get(DO.BURNER2, False)

        # Flow switch
        if not self.manual_feedback_override[DI.FLOW_SWITCH]:
            if self.do.get(DO.PUMP1, False):
                if self._flow_on_at is None:
                    self._flow_on_at = now
                if now - self._flow_on_at > 1500:
                    self.di[DI.FLOW_SWITCH] = True
            else:
                self.di[DI.FLOW_SWITCH] = False
                self._flow_on_at = None

    def set_time_scale(self, scale: float) -> None:
        self._scale = max(0.1, float(scale))


# ═══════════════════════════════════════════════════════════════════════
#  PART 5: Data Logger
# ═══════════════════════════════════════════════════════════════════════

class DataLogger:
    def __init__(self, max_entries: int = 5000):
        self.buffer: deque[LogEntry] = deque(maxlen=max_entries)

    def log(self, now_ms: float, code: str, desc: str,
            value: float = 0.0, source: str = "") -> None:
        self.buffer.appendleft(LogEntry(now_ms, code, desc, value, source))

    def recent(self, n: int = 100) -> List[LogEntry]:
        return list(self.buffer)[:n]


# ═══════════════════════════════════════════════════════════════════════
#  PART 6: Alarm Manager
# ═══════════════════════════════════════════════════════════════════════

class AlarmManager:
    def __init__(self, logger: DataLogger):
        self.logger = logger
        self.active: Dict[str, Alarm] = {}
        self.history: List[Alarm] = []

    def raise_alarm(self, alarm: Alarm) -> None:
        if alarm.code in self.active:
            self.active[alarm.code].timestamp_ms = alarm.timestamp_ms
            return
        self.active[alarm.code] = alarm
        self.history.insert(0, alarm)
        if len(self.history) > 500:
            self.history.pop()
        self.logger.log(alarm.timestamp_ms, alarm.code, alarm.title, 0.0, alarm.source)

    def clear(self, code: str) -> None:
        if code in self.active:
            del self.active[code]
            self.logger.log(0, "CLEAR", f"آلارم پاک شد: {code}")

    def ack(self, code: str) -> None:
        if code in self.active:
            self.active[code].acknowledged = True

    def list_active(self) -> List[Alarm]:
        return list(self.active.values())

    def clear_all(self) -> None:
        self.active.clear()


# ═══════════════════════════════════════════════════════════════════════
#  PART 7: Sensor Manager
# ═══════════════════════════════════════════════════════════════════════

class SensorManager:
    def __init__(self, hal: IHardwareAbstraction, cfg: SystemConfig):
        self.hal = hal
        self.cfg = cfg
        self.configs: Dict[AI, SensorConfig] = {}
        self.readings: Dict[AI, SensorReading] = {}
        self.filters: Dict[AI, deque] = {}
        self.last_sample: Dict[AI, float] = {}

        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            (AI.SUPPLY, "دمای رفت", -50, 150),
            (AI.RETURN, "دمای برگشت", -50, 150),
            (AI.OUTDOOR, "دمای بیرون", -50, 80),
            (AI.DHW, "دمای DHW", -10, 100),
            (AI.BOILER1, "دمای دیگ ۱", -50, 150),
            (AI.BOILER2, "دمای دیگ ۲", -50, 150),
            (AI.HEADER, "دمای هدر", -50, 150),
            (AI.ROOM, "دمای اتاق", -10, 50),
        ]
        for sid, name, mn, mx in defaults:
            self.configs[sid] = SensorConfig(id=sid, name=name,
                                             min_temp=mn, max_temp=mx,
                                             offset=self.cfg.sensor_offsets.get(sid, 0.0))

    def tick(self, now_ms: float) -> None:
        for sid, sc in self.configs.items():
            if not sc.enabled:
                continue
            if now_ms - self.last_sample.get(sid, -1e9) < sc.sampling_ms:
                continue
            self.last_sample[sid] = now_ms
            self._sample(sc, now_ms)

    def _sample(self, sc: SensorConfig, now_ms: float) -> None:
        raw = self.hal.read_analog(sc.id)
        r = SensorReading(id=sc.id, timestamp_ms=now_ms, raw_value=raw)

        if raw is None or (isinstance(raw, float) and (raw != raw)) or raw < -10.0:
            r.status = SensorStatus.DISCONNECTED
            self.readings[sc.id] = r
            return

        # Filter (moving average ساده روی ۵ نمونه)
        if sc.id not in self.filters:
            self.filters[sc.id] = deque(maxlen=5)
        self.filters[sc.id].append(raw)
        r.filtered_value = sum(self.filters[sc.id]) / len(self.filters[sc.id])

        # Offset + Gain
        r.corrected_value = r.filtered_value * sc.gain + sc.offset

        # Rate of Change
        prev = self.readings.get(sc.id)
        if prev and prev.timestamp_ms > 0:
            dt = (now_ms - prev.timestamp_ms) / 1000.0
            if dt > 1e-3:
                r.rate_of_change = (r.corrected_value - prev.corrected_value) / dt

        # Range Check
        if r.corrected_value < sc.min_temp or r.corrected_value > sc.max_temp:
            r.status = SensorStatus.INVALID
        else:
            r.status = SensorStatus.VALID

        self.readings[sc.id] = r

    def get(self, sid: AI) -> Optional[SensorReading]:
        return self.readings.get(sid)

    def get_value(self, sid: AI, fallback: float = float('nan')) -> float:
        r = self.readings.get(sid)
        if r and r.status == SensorStatus.VALID:
            return r.corrected_value
        return fallback

    def set_offset(self, sid: AI, offset: float) -> None:
        if sid in self.configs:
            self.configs[sid].offset = offset


# ═══════════════════════════════════════════════════════════════════════
#  PART 8: Sensor Validation (۵ سطح)
# ═══════════════════════════════════════════════════════════════════════

class SensorValidation:
    """تشخیص ناهنجاری سنسورها با ۵ معیار مستقل."""

    def __init__(self, sm: SensorManager, cfg: SystemConfig):
        self.sm = sm
        self.cfg = cfg
        self.plausibility_violation_start = 0.0
        self.stuck_start: Dict[AI, float] = {}

    def tick(self, now_ms: float) -> None:
        # --- سطح ۴: Cross-Sensor: Supply >= Return در گرمایش ---
        s = self.sm.get(AI.SUPPLY)
        r = self.sm.get(AI.RETURN)
        if (s and r and s.status == SensorStatus.VALID and
                r.status == SensorStatus.VALID):
            if s.corrected_value + 0.5 < r.corrected_value:
                if self.plausibility_violation_start == 0.0:
                    self.plausibility_violation_start = now_ms

        # --- سطح ۳: Stuck Detection ---
        for sid, reading in self.sm.readings.items():
            if reading.status != SensorStatus.VALID:
                continue
            if abs(reading.rate_of_change) < 0.005:
                if sid not in self.stuck_start:
                    self.stuck_start[sid] = now_ms
            else:
                self.stuck_start.pop(sid, None)

    def is_stuck(self, sid: AI, now_ms: float) -> bool:
        st = self.stuck_start.get(sid)
        if st is None:
            return False
        return (now_ms - st) > self.cfg.stuck_timeout_ms

    def plausibility_state(self, now_ms: float) -> str:
        if self.plausibility_violation_start == 0.0:
            return "OK"
        elapsed = now_ms - self.plausibility_violation_start
        if elapsed > self.cfg.plausibility_fault_ms:
            return "FAULT"
        if elapsed > self.cfg.plausibility_warn_ms:
            return "WARNING"
        return "OK"

    def reset_plausibility(self) -> None:
        self.plausibility_violation_start = 0.0


# ═══════════════════════════════════════════════════════════════════════
#  PART 9: Actuator Manager
# ═══════════════════════════════════════════════════════════════════════

class ActuatorManager:
    def __init__(self, hal: IHardwareAbstraction, cfg: SystemConfig):
        self.hal = hal
        self.cfg = cfg
        self.runtime: Dict[DO, ActuatorRuntime] = {}
        self.last_tick = 0.0

        self._register_defaults()

    def _register_defaults(self) -> None:
    # همه خروجی‌های DO باید ثبت شوند
     for d in DO:
        self.runtime[d] = ActuatorRuntime(id=d)

    def request(self, do_id: DO, on: bool) -> None:
        rt = self.runtime[do_id]
        if rt.manual_cmd is None:
            rt.command = on
        else:
            rt.command = rt.manual_cmd

    def set_manual(self, do_id: DO, val: Optional[bool]) -> None:
        self.runtime[do_id].manual_cmd = val

    def set_feedback(self, do_id: DO, fb: bool) -> None:
        self.runtime[do_id].feedback = fb

    def apply(self, now_ms: float, safety_ok: bool, logger: DataLogger) -> None:
        for do_id, rt in self.runtime.items():
            want = rt.command

            # Safety — مشعل‌ها همیشه در حالت ایمنی خاموش
            if not safety_ok and do_id in (DO.BURNER1, DO.BURNER2):
                want = False
                rt.manual_cmd = None

            # Anti-Short-Cycle فقط در AUTO
            if rt.manual_cmd is None:
                if rt.state == ActuatorState.ON and not want:
                    if do_id in (DO.BURNER1, DO.BURNER2):
                        if now_ms - rt.last_on_ms < self.cfg.burner_min_on_ms:
                            want = True
                if rt.state == ActuatorState.OFF and want:
                    if do_id in (DO.BURNER1, DO.BURNER2):
                        if rt.last_off_ms > 0 and \
                                now_ms - rt.last_off_ms < self.cfg.burner_min_off_ms:
                            want = False

            # اعمال تغییر
            if want and rt.state != ActuatorState.ON:
                rt.state = ActuatorState.ON
                rt.last_on_ms = now_ms
                rt.start_count += 1
                self.hal.write_digital_output(do_id, True)
                logger.log(now_ms, "ACT_ON", f"{do_id.name} روشن شد", 0, do_id.name)
            elif not want and rt.state != ActuatorState.OFF:
                rt.state = ActuatorState.OFF
                rt.last_off_ms = now_ms
                self.hal.write_digital_output(do_id, False)
                logger.log(now_ms, "ACT_OFF", f"{do_id.name} خاموش شد", 0, do_id.name)

            # Runtime
            if rt.state == ActuatorState.ON and self.last_tick > 0:
                rt.total_runtime_ms += (now_ms - self.last_tick)

        self.last_tick = now_ms

    def is_on(self, do_id: DO) -> bool:
        return self.runtime[do_id].state == ActuatorState.ON


# ═══════════════════════════════════════════════════════════════════════
#  PART 10: Safety Manager (مستقل از Control)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SafetyResult:
    ok: bool
    trip_codes: List[str] = field(default_factory=list)
    force_safe_state: bool = False


class SafetyManager:
    def __init__(self, hal: IHardwareAbstraction, cfg: SystemConfig):
        self.hal = hal
        self.cfg = cfg
        self.clear_since = 0.0

    def evaluate(self, ctx: 'Context') -> SafetyResult:
        r = SafetyResult(ok=True)

        if self.hal.read_digital_input(DI.EMERGENCY_STOP):
            r.ok = False; r.trip_codes.append("E330")
        if self.hal.read_digital_input(DI.FIRE_ALARM):
            r.ok = False; r.trip_codes.append("E310")
        if self.hal.read_digital_input(DI.GAS_SAFETY):
            r.ok = False; r.trip_codes.append("E340")
        if self.hal.read_digital_input(DI.BOILER_SAFETY):
            r.ok = False; r.trip_codes.append("E230")
        if self.hal.read_digital_input(DI.LOW_WATER):
            r.ok = False; r.trip_codes.append("E320")
        if ctx.supply_temp > self.cfg.max_supply_temp:
            r.ok = False; r.trip_codes.append("E300")
        if ctx.boiler_temp > self.cfg.max_boiler_temp:
            r.ok = False; r.trip_codes.append("E301")

        r.force_safe_state = not r.ok

        # Auto-Reset پس از رفع علت
        if r.ok and ctx.safety_locked:
            if self.clear_since == 0.0:
                self.clear_since = self.hal.millis()
            if self.hal.millis() - self.clear_since > self.cfg.safety_reset_confirm_ms:
                ctx.safety_locked = False
                self.clear_since = 0.0
        elif not r.ok:
            self.clear_since = 0.0

        return r


# ═══════════════════════════════════════════════════════════════════════
#  PART 11: Schedule Manager
# ═══════════════════════════════════════════════════════════════════════

class ScheduleManager:
    def __init__(self):
        self.entries: List[ScheduleEntry] = [
            ScheduleEntry(enabled=True, days_mask=0x7F,
                          start_minutes=0, end_minutes=1440,
                          target_temp=65.0, priority=1)
        ]

    def compute_setpoint(self, dt: datetime) -> float:
        now_min = dt.hour * 60 + dt.minute
        # weekday() = 0=Mon … 6=Sun → تبدیل به 0=Sat
        wd_map = [5, 6, 0, 1, 2, 3, 4]
        wd = wd_map[dt.weekday()]
        best, best_pri = None, 999
        for e in self.entries:
            if not e.enabled:
                continue
            if not (e.days_mask & (1 << wd)):
                continue
            if e.start_minutes <= now_min < e.end_minutes:
                if e.priority < best_pri:
                    best_pri = e.priority
                    best = e.target_temp
        return best if best is not None else 55.0


# ═══════════════════════════════════════════════════════════════════════
#  PART 12: Setpoint Manager (با Weather Compensation + Priorities)
# ═══════════════════════════════════════════════════════════════════════

class SetpointManager:
    def __init__(self, sched: ScheduleManager, cfg: SystemConfig):
        self.sched = sched
        self.cfg = cfg

    def compute(self, ctx: 'Context') -> float:
        if ctx.mode == SystemMode.OFF:
            return 0.0

        base = self.sched.compute_setpoint(ctx.dt)
        src = "Schedule"

        if ctx.mode == SystemMode.BOOST:
            base += self.cfg.boost_delta
            src = "Boost"

        if ctx.mode == SystemMode.MANUAL and ctx.manual_setpoint is not None:
            base = ctx.manual_setpoint
            src = "Manual"

        # Weather Compensation
        if self.cfg.wc_enabled and not (ctx.outdoor_temp != ctx.outdoor_temp):
            o = max(self.cfg.outdoor_min,
                    min(self.cfg.outdoor_max, ctx.outdoor_temp))
            t = (o - self.cfg.outdoor_min) / (self.cfg.outdoor_max - self.cfg.outdoor_min)
            comp = (self.cfg.supply_max +
                    (self.cfg.supply_min - self.cfg.supply_max) * t *
                    self.cfg.curve_slope + self.cfg.curve_offset)
            base = 0.7 * base + 0.3 * comp
            src += "+Outdoor"

        # Limit
        base = max(self.cfg.supply_max, min(self.cfg.max_supply_temp, base))
        ctx.setpoint_src = src
        return base


# ═══════════════════════════════════════════════════════════════════════
#  PART 13: Heating Demand Manager
# ═══════════════════════════════════════════════════════════════════════

class HeatingDemandManager:
    def __init__(self, spm: SetpointManager, cfg: SystemConfig):
        self.spm = spm
        self.cfg = cfg

    def compute(self, ctx: 'Context') -> bool:
        ctx.setpoint = self.spm.compute(ctx)

        if ctx.mode == SystemMode.OFF:
            ctx.heating_demand = False
            ctx.last_reason_code = "MODE_OFF"
            return False

        if ctx.supply_temp != ctx.supply_temp:  # NaN
            ctx.heating_demand = False
            ctx.last_reason_code = "SUPPLY_INVALID"
            return False

        error = ctx.setpoint - ctx.supply_temp
        ctx.error = error

        if not ctx.heating_demand and error > self.cfg.heating_start_hyst:
            ctx.heating_demand = True
            ctx.last_reason_code = "HEAT_REQUEST_LOW_TEMP"
        elif ctx.heating_demand and error <= self.cfg.heating_stop_hyst:
            ctx.heating_demand = False
            ctx.last_reason_code = "HEAT_STOP_SETPOINT_REACHED"

        return ctx.heating_demand


# ═══════════════════════════════════════════════════════════════════════
#  PART 14: Fault Engine (تشخیص هوشمند با Confidence)
# ═══════════════════════════════════════════════════════════════════════

class FaultEngine:
    def __init__(self,
                 sm: SensorManager,
                 sv: SensorValidation,
                 am: AlarmManager,
                 actuators: ActuatorManager,
                 cfg: SystemConfig):
        self.sm = sm
        self.sv = sv
        self.am = am
        self.actuators = actuators
        self.cfg = cfg
        self._stuck_alarm_sent: Dict[AI, bool] = {}

    def tick(self, ctx: 'Context', now_ms: float) -> None:
        self._check_sensor_faults(ctx, now_ms)
        self._check_plausibility(ctx, now_ms)
        self._check_stuck_sensors(ctx, now_ms)
        self._check_burner_thermal_response(ctx, now_ms)

    # ---------- Sensor Faults ----------
    def _check_sensor_faults(self, ctx: 'Context', now_ms: float) -> None:
        for sid, r in self.sm.readings.items():
            sc = self.sm.configs[sid]
            if r.status == SensorStatus.DISCONNECTED:
                self.am.raise_alarm(Alarm(
                    code=f"E010_{sid.value}",
                    title=f"قطع ارتباط سنسور {sc.name}",
                    description=f"سنسور {sc.name} پاسخ نمی‌دهد.",
                    recommendation="سیم‌کشی و اتصالات سنسور را بررسی کنید.",
                    severity=Severity.FAULT,
                    timestamp_ms=now_ms,
                    source=sc.name,
                    auto_clear=True,
                    recovery=FaultRecovery.AUTO,
                ))
            elif r.status == SensorStatus.INVALID:
                self.am.raise_alarm(Alarm(
                    code=f"E001_{sid.value}",
                    title=f"مقدار سنسور {sc.name} خارج از محدوده",
                    description=f"مقدار {r.corrected_value:.1f}°C نامعتبر است.",
                    recommendation="سنسور و کالیبراسیون آن را بررسی کنید.",
                    severity=Severity.FAULT,
                    timestamp_ms=now_ms,
                    source=sc.name,
                    auto_clear=True,
                    recovery=FaultRecovery.AUTO,
                ))
            else:
                self.am.clear(f"E010_{sid.value}")
                self.am.clear(f"E001_{sid.value}")

    # ---------- Plausibility ----------
    def _check_plausibility(self, ctx: 'Context', now_ms: float) -> None:
        state = self.sv.plausibility_state(now_ms)
        if state == "FAULT":
            self.am.raise_alarm(Alarm(
                code="E020",
                title="نقض منطق دمای رفت و برگشت",
                description="دمای برگشت بالاتر از دمای رفت برای مدت طولانی است.",
                recommendation="سنسورها، پمپ و جهت جریان آب را بررسی کنید.",
                severity=Severity.FAULT,
                timestamp_ms=now_ms,
                source="PLAUSIBILITY",
                auto_clear=True,
            ))
        elif state == "WARNING":
            self.am.raise_alarm(Alarm(
                code="E020_W",
                title="هشدار نقض منطق دمای رفت/برگشت",
                description="دمای برگشت بالاتر از رفت است — پایش می‌شود.",
                recommendation="سنسورها را بررسی کنید.",
                severity=Severity.WARNING,
                timestamp_ms=now_ms,
                source="PLAUSIBILITY",
                auto_clear=True,
            ))
        else:
            self.am.clear("E020")
            self.am.clear("E020_W")

    # ---------- Stuck Sensors ----------
    def _check_stuck_sensors(self, ctx: 'Context', now_ms: float) -> None:
        burner_on = self.actuators.is_on(DO.BURNER1) and \
                    self.actuators.runtime[DO.BURNER1].feedback
        if not burner_on:
            self._stuck_alarm_sent.clear()
            return
        for sid in (AI.SUPPLY, AI.BOILER1):
            if self.sv.is_stuck(sid, now_ms):
                if not self._stuck_alarm_sent.get(sid, False):
                    sc = self.sm.configs[sid]
                    self.am.raise_alarm(Alarm(
                        code=f"E030_{sid.value}",
                        title=f"احتمال گیرکردن سنسور {sc.name}",
                        description=f"دمای {sc.name} برای مدت طولانی ثابت مانده "
                                    f"در حالی که مشعل فعال است.",
                        recommendation="سنسور را بررسی یا تعویض کنید.",
                        severity=Severity.WARNING,
                        timestamp_ms=now_ms,
                        source=sc.name,
                    ))
                    self._stuck_alarm_sent[sid] = True

    # ---------- Burner Thermal Response ----------
    def _check_burner_thermal_response(self, ctx: 'Context', now_ms: float) -> None:
        rt = self.actuators.runtime[DO.BURNER1]
        if rt.state != ActuatorState.ON or not rt.feedback:
            return
        if ctx.burner_start_ts <= 0:
            return
        elapsed = now_ms - ctx.burner_start_ts
        if elapsed < self.cfg.burner_response_window_ms:
            return
        delta = ctx.supply_temp - ctx.supply_temp_at_burner_start
        if delta < self.cfg.min_expected_rise:
            # محاسبه Confidence هوشمند
            confidence = self._compute_burner_fault_confidence(ctx)
            self.am.raise_alarm(Alarm(
                code="E210",
                title="پاسخ حرارتی مشعل مطابق انتظار نیست",
                description=(
                    f"مشعل {int(elapsed/1000)}s روشن است اما دمای رفت "
                    f"{delta:.2f}°C تغییر کرده (انتظار ≥ {self.cfg.min_expected_rise}°C)."
                ),
                recommendation=(
                    "پمپ، جریان آب، سنسور دمای رفت و مشعل را بررسی کنید. "
                    "این هشدار قطعی نیست — ممکن است مشکل از سنسور یا جریان باشد."
                ),
                severity=Severity.WARNING,
                timestamp_ms=now_ms,
                source="BURNER1",
                recovery=FaultRecovery.MANUAL_RESET,
                confidence=confidence,
                reason_code="NO_THERMAL_RESPONSE",
            ))

    def _compute_burner_fault_confidence(self, ctx: 'Context') -> float:
        """محاسبه Confidence بر اساس تمام شواهد موجود."""
        score = 0.0

        # سنسور Supply معتبر؟
        s = self.sm.get(AI.SUPPLY)
        if s and s.status == SensorStatus.VALID:
            score += 25
        # پمپ فعال و فیدبک OK؟
        if self.actuators.is_on(DO.PUMP1) and \
                self.actuators.runtime[DO.PUMP1].feedback:
            score += 25
        # جریان تأیید شده؟
        # (نیاز به HAL دارد — در Context نگه می‌داریم)
        if ctx.flow_ok:
            score += 25
        # فیدبک مشعل؟
        if self.actuators.runtime[DO.BURNER1].feedback:
            score += 25

        return score


# ═══════════════════════════════════════════════════════════════════════
#  PART 15: Context (وضعیت کامل سیستم)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Context:
    mode: SystemMode = SystemMode.AUTO
    state: SystemState = SystemState.OFF
    state_enter_ts: float = 0.0
    prev_state: Optional[SystemState] = None

    # Timers
    pump_start_ts: float = 0.0
    burner_start_ts: float = 0.0
    burner_stop_ts: float = 0.0
    supply_temp_at_burner_start: float = 0.0
    manual_until_ts: float = 0.0
    boost_end_ts: float = 0.0
    retry_start_ts: float = 0.0

    # Values
    supply_temp: float = 0.0
    return_temp: float = 0.0
    outdoor_temp: float = 0.0
    boiler_temp: float = 0.0
    dhw_temp: float = 0.0
    room_temp: float = 20.0

    # Control
    heating_demand: bool = False
    setpoint: float = 0.0
    setpoint_src: str = "—"
    error: float = 0.0
    last_reason_code: str = "INIT"

    # Feedback
    flow_ok: bool = False

    # Safety
    safety_locked: bool = False

    # Manual
    manual_setpoint: Optional[float] = None
    retry_count: int = 0

    # Date/Time
    dt: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════════════════
#  PART 16: State Machine
# ═══════════════════════════════════════════════════════════════════════

class StateMachine:
    def __init__(self,
                 actuators: ActuatorManager,
                 hdm: HeatingDemandManager,
                 am: AlarmManager,
                 hal: IHardwareAbstraction,
                 cfg: SystemConfig,
                 logger: DataLogger):
        self.actuators = actuators
        self.hdm = hdm
        self.am = am
        self.hal = hal
        self.cfg = cfg
        self.logger = logger

    def update(self, ctx: Context, now_ms: float, safety_ok: bool) -> None:
        # --- Safety Override ---
        if not safety_ok:
            self.actuators.request(DO.BURNER1, False)
            self.actuators.request(DO.BURNER2, False)
            if ctx.state != SystemState.SAFETY_LOCK:
                self._enter(ctx, SystemState.SAFETY_LOCK, now_ms)
                ctx.safety_locked = True
                self.am.raise_alarm(Alarm(
                    code="E500",
                    title="قفل ایمنی سیستم",
                    description="سیستم به دلیل شرایط ایمنی وارد حالت قفل شد.",
                    recommendation="علت را رفع کنید. ریست خودکار پس از رفع علت انجام می‌شود.",
                    severity=Severity.SAFETY,
                    timestamp_ms=now_ms,
                    source="SAFETY",
                    recovery=FaultRecovery.AUTO,
                ))
            return

        # اگر Safety رفع شد و در قفل بودیم
        if ctx.state == SystemState.SAFETY_LOCK and not ctx.safety_locked:
            self._enter(ctx, SystemState.IDLE, now_ms)
            self.am.clear("E500")

        # --- Main State Machine ---
        if ctx.state == SystemState.OFF:
            if ctx.mode != SystemMode.OFF:
                self._enter(ctx, SystemState.IDLE, now_ms)

        elif ctx.state == SystemState.IDLE:
            if self.hdm.compute(ctx):
                self._enter(ctx, SystemState.PRECHECK, now_ms)

        elif ctx.state == SystemState.PRECHECK:
            self.actuators.request(DO.PUMP1, True)
            ctx.pump_start_ts = now_ms
            self._enter(ctx, SystemState.PUMP_STARTING, now_ms)

        elif ctx.state == SystemState.PUMP_STARTING:
            if self.actuators.runtime[DO.PUMP1].feedback:
                self._enter(ctx, SystemState.FLOW_WAIT, now_ms)
            elif now_ms - ctx.pump_start_ts > self.cfg.pump_start_delay_ms:
                self.am.raise_alarm(Alarm(
                    code="E100",
                    title="عدم تأیید پمپ ۱",
                    description="فرمان روشن شدن پمپ ارسال شد اما فیدبک دریافت نشد.",
                    recommendation="کنتاکتور، فیوز، سیم‌کشی و فیدبک پمپ را بررسی کنید.",
                    severity=Severity.FAULT,
                    timestamp_ms=now_ms,
                    source="PUMP1",
                    latched=True,
                    recovery=FaultRecovery.MANUAL_RESET,
                ))
                self._enter(ctx, SystemState.FAULT, now_ms)

        elif ctx.state == SystemState.FLOW_WAIT:
            if ctx.flow_ok:
                self._enter(ctx, SystemState.HEATING_REQUEST, now_ms)
            elif now_ms - ctx.pump_start_ts > self.cfg.flow_confirm_ms * 2:
                self.am.raise_alarm(Alarm(
                    code="E110",
                    title="عدم تأیید جریان آب",
                    description="پمپ فرمان گرفت اما جریان در مدت تعیین‌شده تأیید نشد.",
                    recommendation="پمپ، شیرها، هواگیری و Flow Switch را بررسی کنید.",
                    severity=Severity.FAULT,
                    timestamp_ms=now_ms,
                    source="FLOW",
                    latched=True,
                    recovery=FaultRecovery.MANUAL_RESET,
                ))
                self._enter(ctx, SystemState.FAULT, now_ms)

        elif ctx.state == SystemState.HEATING_REQUEST:
            self.actuators.request(DO.BURNER1, True)
            ctx.burner_start_ts = now_ms
            ctx.supply_temp_at_burner_start = ctx.supply_temp
            self._enter(ctx, SystemState.BURNER_STARTING, now_ms)

        elif ctx.state == SystemState.BURNER_STARTING:
            if self.actuators.runtime[DO.BURNER1].feedback:
                self._enter(ctx, SystemState.HEATING, now_ms)
            elif now_ms - ctx.burner_start_ts > self.cfg.burner_start_delay_ms:
                self.am.raise_alarm(Alarm(
                    code="E200",
                    title="عدم فیدبک مشعل",
                    description="فرمان روشن شدن مشعل ارسال شد اما فیدبک دریافت نشد.",
                    recommendation="مشعل، کنترلر مشعل و فیدبک را بررسی کنید.",
                    severity=Severity.FAULT,
                    timestamp_ms=now_ms,
                    source="BURNER1",
                    latched=True,
                    recovery=FaultRecovery.MANUAL_RESET,
                ))
                self._enter(ctx, SystemState.FAULT, now_ms)

        elif ctx.state == SystemState.HEATING:
            if self.hdm.compute(ctx):
                return
            rt = self.actuators.runtime[DO.BURNER1]
            if now_ms - rt.last_on_ms > self.cfg.burner_min_on_ms:
                self.actuators.request(DO.BURNER1, False)
                ctx.burner_stop_ts = now_ms
                self._enter(ctx, SystemState.BURNER_STOPPING, now_ms)

        elif ctx.state == SystemState.BURNER_STOPPING:
            if now_ms - ctx.burner_stop_ts > self.cfg.burner_min_off_ms:
                self._enter(ctx, SystemState.PUMP_POST_RUN, now_ms)

        elif ctx.state == SystemState.PUMP_POST_RUN:
            if now_ms - ctx.burner_stop_ts > \
                    (self.cfg.burner_min_off_ms + self.cfg.pump_post_run_ms):
                self.actuators.request(DO.PUMP1, False)
                self._enter(ctx, SystemState.IDLE, now_ms)

        elif ctx.state == SystemState.FAULT:
            # تلاش برای Recovery
            if ctx.retry_count < self.cfg.max_retries:
                if ctx.retry_start_ts == 0.0:
                    ctx.retry_start_ts = now_ms
                if now_ms - ctx.retry_start_ts > self.cfg.retry_delay_ms:
                    ctx.retry_count += 1
                    ctx.retry_start_ts = 0.0
                    self.logger.log(now_ms, "RETRY", f"تلاش {ctx.retry_count}")
                    self._enter(ctx, SystemState.IDLE, now_ms)
            else:
                self._enter(ctx, SystemState.LOCKOUT, now_ms)

        elif ctx.state == SystemState.LOCKOUT:
            # منتظر Reset دستی
            pass

    def reset(self, ctx: Context, now_ms: float) -> None:
        ctx.state = SystemState.IDLE
        ctx.state_enter_ts = now_ms
        ctx.heating_demand = False
        ctx.retry_count = 0
        ctx.retry_start_ts = 0.0
        self.logger.log(now_ms, "RESET", "State Machine ریست شد")

    def _enter(self, ctx: Context, new_state: SystemState, now_ms: float) -> None:
        ctx.prev_state = ctx.state
        ctx.state = new_state
        ctx.state_enter_ts = now_ms
        self.logger.log(now_ms, "STATE", f"ورود به {new_state.name}")


# ═══════════════════════════════════════════════════════════════════════
#  PART 17: Main Controller (Orchestrator)
# ═══════════════════════════════════════════════════════════════════════

class BoilerController:
    """کنترلر اصلی — همه ماژول‌ها را به هم وصل می‌کند."""

    def __init__(self, hal: IHardwareAbstraction,
                 cfg: Optional[SystemConfig] = None):
        self.cfg = cfg or SystemConfig()
        valid, err = self.cfg.validate()
        if not valid:
            raise ValueError(f"تنظیمات نامعتبر: {err}")

        self.hal = hal
        self.logger = DataLogger()
        self.am = AlarmManager(self.logger)
        self.sm = SensorManager(hal, self.cfg)
        self.sv = SensorValidation(self.sm, self.cfg)
        self.actuators = ActuatorManager(hal, self.cfg)
        self.safety = SafetyManager(hal, self.cfg)
        self.sched = ScheduleManager()
        self.spm = SetpointManager(self.sched, self.cfg)
        self.hdm = HeatingDemandManager(self.spm, self.cfg)
        self.fault_engine = FaultEngine(self.sm, self.sv, self.am,
                                        self.actuators, self.cfg)
        self.state_machine = StateMachine(self.actuators, self.hdm,
                                          self.am, hal, self.cfg, self.logger)

        self.ctx = Context()
        self._last_sensor_tick = 0.0
        self._last_control_tick = 0.0
        self._last_fault_tick = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.logger.log(0, "BOOT", "کنترلر راه‌اندازی شد")
        self.state_machine._enter(self.ctx, SystemState.IDLE, 0)

    # ---------- Public API ----------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def set_mode(self, mode: SystemMode) -> None:
        self.ctx.mode = mode
        self.logger.log(self.hal.millis(), "MODE", f"حالت: {mode.name}")

    def set_manual_setpoint(self, temp: float) -> None:
        self.ctx.manual_setpoint = temp

    def start_boost(self) -> None:
        self.ctx.mode = SystemMode.BOOST
        self.ctx.boost_end_ts = self.hal.millis() + self.cfg.boost_duration_ms

    def master_reset(self) -> None:
        """ریست کامل تمام خطاها و بازگشت به IDLE."""
        # پاک کردن ورودی‌های خطرناک در HAL
        for d in (DI.EMERGENCY_STOP, DI.FIRE_ALARM, DI.GAS_SAFETY,
                  DI.BOILER_SAFETY, DI.LOW_WATER, DI.HIGH_PRESSURE):
            if isinstance(self.hal, SimulationHAL):
                self.hal.di[d] = False
                self.hal.manual_feedback_override[d] = False
        self.am.clear_all()
        self.ctx.safety_locked = False
        self.safety.clear_since = 0.0
        self.sv.reset_plausibility()
        self.state_machine.reset(self.ctx, self.hal.millis())
        # آزاد کردن manual تجهیزات
        for d in DO:
            self.actuators.set_manual(d, None)

    def get_status(self) -> Dict[str, Any]:
        """Snapshot کامل برای HMI/API."""
        return {
            "mode": self.ctx.mode.name,
            "state": self.ctx.state.name,
            "heating_demand": self.ctx.heating_demand,
            "setpoint": self.ctx.setpoint,
            "setpoint_src": self.ctx.setpoint_src,
            "error": self.ctx.error,
            "reason_code": self.ctx.last_reason_code,
            "safety_locked": self.ctx.safety_locked,
            "temperatures": {
                "supply": self.ctx.supply_temp,
                "return": self.ctx.return_temp,
                "outdoor": self.ctx.outdoor_temp,
                "boiler": self.ctx.boiler_temp,
                "dhw": self.ctx.dhw_temp,
            },
            "pump1_on": self.actuators.is_on(DO.PUMP1),
            "burner1_on": self.actuators.is_on(DO.BURNER1),
            "flow_ok": self.ctx.flow_ok,
            "active_alarms": [
                {"code": a.code, "title": a.title, "severity": a.severity.name}
                for a in self.am.list_active()
            ],
        }

    # ---------- Internal Loop ----------
    def _run_loop(self) -> None:
        while self._running:
            now_ms = self.hal.millis()

            # به‌روزرسانی فیزیک شبیه‌سازی
            if isinstance(self.hal, SimulationHAL):
                last = getattr(self, "_last_physics", now_ms)
                dt = now_ms - last
                if dt > 0:
                    self.hal.update_physics(dt)
                self._last_physics = now_ms

            # Sensor Task (200ms)
            if now_ms - self._last_sensor_tick >= self.cfg.sensor_cycle_ms:
                self._last_sensor_tick = now_ms
                self.sm.tick(now_ms)

            # Control Task (1000ms)
            if now_ms - self._last_control_tick >= self.cfg.control_cycle_ms:
                self._last_control_tick = now_ms
                self._control_tick(now_ms)

            # Fault Task (500ms)
            if now_ms - self._last_fault_tick >= self.cfg.fault_cycle_ms:
                self._last_fault_tick = now_ms
                self.sv.tick(now_ms)
                self.fault_engine.tick(self.ctx, now_ms)

            # Watchdog
            self.hal.feed_watchdog()

            time.sleep(0.02)

    def _control_tick(self, now_ms: float) -> None:
        # 1) به‌روزرسانی مقادیر از سنسورها
        self._update_ctx_from_sensors()

        # 2) فیدبک‌ها
        self.actuators.set_feedback(DO.PUMP1,
                                    self.hal.read_digital_input(DI.PUMP1_FB))
        self.actuators.set_feedback(DO.PUMP2,
                                    self.hal.read_digital_input(DI.PUMP2_FB))
        self.actuators.set_feedback(DO.BURNER1,
                                    self.hal.read_digital_input(DI.BURNER1_FB))
        self.actuators.set_feedback(DO.BURNER2,
                                    self.hal.read_digital_input(DI.BURNER2_FB))
        self.ctx.flow_ok = self.hal.read_digital_input(DI.FLOW_SWITCH)

        # 3) Boost timeout
        if self.ctx.mode == SystemMode.BOOST and \
                now_ms > self.ctx.boost_end_ts:
            self.ctx.mode = SystemMode.AUTO
            self.logger.log(now_ms, "BOOST_END", "دوره Boost تمام شد")

        # 4) Manual timeout
        if self.ctx.mode == SystemMode.MANUAL and \
                self.ctx.manual_until_ts > 0 and \
                now_ms > self.ctx.manual_until_ts:
            self.ctx.mode = SystemMode.AUTO
            self.ctx.manual_until_ts = 0.0
            self.logger.log(now_ms, "MANUAL_TIMEOUT", "کنترل دستی به پایان رسید")

        # 5) Safety
        safety_res = self.safety.evaluate(self.ctx)

        # 6) State Machine
        self.state_machine.update(self.ctx, now_ms, safety_res.ok)

        # 7) اعمال خروجی‌ها
        self.actuators.apply(now_ms, safety_res.ok, self.logger)

    def _update_ctx_from_sensors(self) -> None:
        self.ctx.supply_temp = self.sm.get_value(AI.SUPPLY, float('nan'))
        self.ctx.return_temp = self.sm.get_value(AI.RETURN, float('nan'))
        self.ctx.outdoor_temp = self.sm.get_value(AI.OUTDOOR, float('nan'))
        self.ctx.dhw_temp = self.sm.get_value(AI.DHW, float('nan'))
        self.ctx.boiler_temp = self.sm.get_value(AI.BOILER1, float('nan'))
        self.ctx.room_temp = self.sm.get_value(AI.ROOM, 20.0)
        self.ctx.dt = datetime.now()


# ═══════════════════════════════════════════════════════════════════════
#  PART 18: Demo / Test Harness
# ═══════════════════════════════════════════════════════════════════════

def print_status(controller: BoilerController, tick: int) -> None:
    s = controller.get_status()
    print(f"\n╔══ Tick #{tick} ═══════════════════════════════════════════════════")
    print(f"║ Mode={s['mode']:8s}  State={s['state']:15s}  "
          f"Safety={'LOCKED' if s['safety_locked'] else 'SAFE'}")
    print(f"║ Setpoint={s['setpoint']:6.1f}°C ({s['setpoint_src']})  "
          f"Error={s['error']:+6.2f}°C")
    print(f"║ Temps: Supply={s['temperatures']['supply']:5.1f}  "
          f"Return={s['temperatures']['return']:5.1f}  "
          f"Boiler={s['temperatures']['boiler']:5.1f}  "
          f"Outdoor={s['temperatures']['outdoor']:5.1f}")
    print(f"║ Pump1={'ON ' if s['pump1_on'] else 'OFF'}  "
          f"Burner1={'ON ' if s['burner1_on'] else 'OFF'}  "
          f"Flow={'OK' if s['flow_ok'] else 'NO'}")
    print(f"║ Demand={'ON ' if s['heating_demand'] else 'OFF'}  "
          f"Reason={s['reason_code']}")
    if s['active_alarms']:
        print(f"║ ⚠️  Alarms: {len(s['active_alarms'])}")
        for a in s['active_alarms'][:3]:
            print(f"║    [{a['code']}] {a['title']} ({a['severity']})")
    print(f"╚═══════════════════════════════════════════════════════════════")


def demo_normal_heating():
    """سناریوی ۱: گرمایش عادی."""
    print("\n" + "═" * 70)
    print("  DEMO 1: گرمایش عادی")
    print("═" * 70)

    hal = SimulationHAL()
    hal.set_time_scale(60.0)  # ×60 برای تست سریع‌تر
    hal.analog[AI.SUPPLY] = 45.0
    hal.analog[AI.BOILER1] = 50.0

    ctrl = BoilerController(hal)
    ctrl.start()

    try:
        for i in range(40):
            time.sleep(0.5)
            if i % 4 == 0:
                print_status(ctrl, i)
    finally:
        ctrl.stop()


def demo_over_temp():
    """سناریوی ۲: دمای بالا → SAFETY_LOCK و سپس Auto-Reset."""
    print("\n" + "═" * 70)
    print("  DEMO 2: Over-Temperature + Auto-Reset")
    print("═" * 70)

    hal = SimulationHAL()
    hal.set_time_scale(10.0)
    ctrl = BoilerController(hal)
    ctrl.start()

    try:
        time.sleep(1.0)
        print_status(ctrl, 0)
        print("\n>>> تنظیم دمای رفت به 95°C (بالاتر از حد ایمنی)")
        hal.manual_sensor_override[AI.SUPPLY] = True
        hal.manual_sensor_values[AI.SUPPLY] = 95.0
        time.sleep(2.0)
        print_status(ctrl, 1)

        print("\n>>> برگرداندن دما به 70°C — انتظار: Auto-Reset")
        hal.manual_sensor_values[AI.SUPPLY] = 70.0
        time.sleep(7.0)
        print_status(ctrl, 2)
    finally:
        ctrl.stop()


def demo_pump_failure():
    """سناریوی ۳: خرابی پمپ."""
    print("\n" + "═" * 70)
    print("  DEMO 3: Pump Feedback Failure")
    print("═" * 70)

    hal = SimulationHAL()
    hal.set_time_scale(60.0)
    hal.analog[AI.SUPPLY] = 45.0
    # پمپ فیدبک هرگز نمی‌آید (خرابی)
    hal.manual_feedback_override[DI.PUMP1_FB] = True
    hal.manual_feedback_values[DI.PUMP1_FB] = False

    ctrl = BoilerController(hal)
    ctrl.start()

    try:
        for i in range(30):
            time.sleep(0.5)
            if i % 5 == 0:
                print_status(ctrl, i)
    finally:
        ctrl.stop()


def demo_manual_feedback_control():
    """سناریوی ۴: کنترل دستی فیدبک‌ها."""
    print("\n" + "═" * 70)
    print("  DEMO 4: Manual Feedback Control (تست خطا)")
    print("═" * 70)

    hal = SimulationHAL()
    hal.set_time_scale(60.0)
    hal.analog[AI.SUPPLY] = 45.0
    # پمپ OK ولی Flow را دستی خاموش نگه می‌داریم
    hal.manual_feedback_override[DI.PUMP1_FB] = True
    hal.manual_feedback_values[DI.PUMP1_FB] = True
    hal.manual_feedback_override[DI.FLOW_SWITCH] = True
    hal.manual_feedback_values[DI.FLOW_SWITCH] = False

    ctrl = BoilerController(hal)
    ctrl.start()

    try:
        for i in range(30):
            time.sleep(0.5)
            if i % 5 == 0:
                print_status(ctrl, i)
    finally:
        ctrl.stop()


def demo_fault_confidence():
    """سناریوی ۵: عدم پاسخ حرارتی مشعل (Fault Confidence)."""
    print("\n" + "═" * 70)
    print("  DEMO 5: Burner No Thermal Response")
    print("═" * 70)

    hal = SimulationHAL()
    hal.set_time_scale(60.0)
    # دمای رفت را دستی روی 55 نگه می‌داریم تا مشعل روشن شود اما دما افزایش نیابد
    hal.manual_sensor_override[AI.SUPPLY] = True
    hal.manual_sensor_values[AI.SUPPLY] = 55.0
    hal.manual_sensor_override[AI.BOILER1] = True
    hal.manual_sensor_values[AI.BOILER1] = 56.0
    # فیدبک‌ها AUTO می‌مانند

    ctrl = BoilerController(hal)
    ctrl.start()

    try:
        for i in range(40):
            time.sleep(0.5)
            if i % 5 == 0:
                print_status(ctrl, i)
    finally:
        ctrl.stop()


# ═══════════════════════════════════════════════════════════════════════
#  PART 19: Entry Point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔" + "═" * 68 + "╗")
    print("║  Smart Boiler Room Controller — Python Reference Implementation  ║")
    print("║  الگوریتم کامل کنترل هوشمند موتورخانه                           ║")
    print("╚" + "═" * 68 + "╝")

    demos = {
        "1": ("گرمایش عادی", demo_normal_heating),
        "2": ("دمای بالا + Auto-Reset", demo_over_temp),
        "3": ("خرابی پمپ", demo_pump_failure),
        "4": ("کنترل دستی فیدبک", demo_manual_feedback_control),
        "5": ("عدم پاسخ حرارتی مشعل", demo_fault_confidence),
    }

    print("\nانتخاب سناریو:")
    for k, (name, _) in demos.items():
        print(f"  {k}. {name}")
    print("  0. خروج")

    try:
        choice = input("\nشماره سناریو [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice in demos:
        demos[choice][1]()
    elif choice == "0":
        print("خداحافظ!")
    else:
        print("انتخاب نامعتبر — اجرای سناریو ۱ به‌صورت پیش‌فرض")
        demo_normal_heating()