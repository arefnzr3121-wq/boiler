import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteRepository:
    """
    Ù„Ø§ÛŒÙ‡ Ø¯Ø³ØªØ±Ø³ÛŒ Ø¨Ù‡ SQLite.

    Ù…Ø³Ø¦ÙˆÙ„:
    - Ø§ÛŒØ¬Ø§Ø¯ Database
    - Ø§ÛŒØ¬Ø§Ø¯ TableÙ‡Ø§
    - Ø°Ø®ÛŒØ±Ù‡ Sensor Reading
    - Ø°Ø®ÛŒØ±Ù‡ Decision
    - Ø°Ø®ÛŒØ±Ù‡ Output
    - Ø°Ø®ÛŒØ±Ù‡ Event
    """

    def __init__(
        self,
        database_path: str = "data/boiler_engine.db",
    ):
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    boiler_state TEXT NOT NULL,
                    burner_state TEXT NOT NULL,
                    pump_state TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    safety_active INTEGER NOT NULL,
                    schedule_active INTEGER NOT NULL,
                    heating_required INTEGER NOT NULL,
                    energy_optimization_active INTEGER NOT NULL,
                    reasons_json TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    equipment_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    accepted INTEGER NOT NULL,
                    reason TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data_json TEXT
                )
                """
            )

            connection.commit()

    def save_sensor_reading(
        self,
        sensor_id: str,
        sensor_type: str,
        value: float,
        unit: str | None,
        status: str,
        timestamp: datetime,
    ) -> int:

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO sensor_readings (
                    sensor_id,
                    sensor_type,
                    value,
                    unit,
                    status,
                    timestamp,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sensor_id,
                    sensor_type,
                    value,
                    unit,
                    status,
                    timestamp.isoformat(),
                    created_at,
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def save_decision(
        self,
        decision: Any,
    ) -> int:

        reasons = []

        for reason in decision.reasons:
            reasons.append(
                reason.model_dump(mode="json")
            )

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO decisions (
                    timestamp,
                    boiler_state,
                    burner_state,
                    pump_state,
                    priority,
                    safety_active,
                    schedule_active,
                    heating_required,
                    energy_optimization_active,
                    reasons_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.timestamp.isoformat(),
                    decision.boiler.value,
                    decision.burner.value,
                    decision.pump.value,
                    int(decision.priority),
                    int(decision.safety_active),
                    int(decision.schedule_active),
                    int(decision.heating_required),
                    int(
                        decision.energy_optimization_active
                    ),
                    json.dumps(
                        reasons,
                        ensure_ascii=False,
                    ),
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def save_output(
        self,
        output: Any,
    ) -> int:

        first_id: int | None = None

        with self._connect() as connection:
            cursor = connection.cursor()

            for command in output.commands:
                cursor.execute(
                    """
                    INSERT INTO outputs (
                        timestamp,
                        equipment_id,
                        state,
                        accepted,
                        reason
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        command.timestamp.isoformat(),
                        command.equipment.value,
                        command.state.value,
                        1,
                        (f"{command.reason_code}: {command.reason_message}" if command.reason_code else command.reason_message),
                    ),
                )

                if first_id is None:
                    first_id = cursor.lastrowid

            connection.commit()

        return first_id or 0

    def save_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        data: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> int:

        timestamp = timestamp or datetime.now(
            timezone.utc
        )

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO events (
                    timestamp,
                    event_type,
                    severity,
                    message,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp.isoformat(),
                    event_type,
                    severity,
                    message,
                    json.dumps(
                        data or {},
                        ensure_ascii=False,
                    ),
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def get_recent_sensor_readings(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM sensor_readings
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_recent_decisions(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM decisions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_recent_events(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]
