"""SQL backend — CRUD + time-series queries against the normalized SQLite
schema from Task 2 (stations / weather_conditions / holidays / traffic_records).

The API speaks a denormalized record shape, so this module is responsible for:
  * resolving weather_main/description -> weather_id (inserting new pairs),
  * upserting holidays and linking them by date,
  * joining the dimension tables back on read.
"""
import sqlite3
from datetime import datetime
from typing import List, Optional

from . import config
from .models import RecordIn, RecordOut

_DT_FMT = "%Y-%m-%d %H:%M:%S"

# One SELECT reused everywhere so every read returns the same denormalized shape.
_SELECT = """
SELECT t.record_id, t.station_id, t.date_time,
       w.weather_main, w.weather_description,
       t.temp_kelvin, t.rain_1h, t.snow_1h, t.clouds_all,
       t.traffic_volume, h.holiday_name
FROM traffic_records t
JOIN weather_conditions w ON t.weather_id = w.weather_id
LEFT JOIN holidays h      ON t.holiday_date = h.holiday_date
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_out(row: sqlite3.Row) -> RecordOut:
    return RecordOut(
        id=str(row["record_id"]),
        station_id=row["station_id"],
        date_time=datetime.strptime(row["date_time"], _DT_FMT),
        weather_main=row["weather_main"],
        weather_description=row["weather_description"],
        temp_kelvin=row["temp_kelvin"],
        rain_1h=row["rain_1h"],
        snow_1h=row["snow_1h"],
        clouds_all=row["clouds_all"],
        traffic_volume=row["traffic_volume"],
        holiday=row["holiday_name"],
    )


def _resolve_weather_id(cur: sqlite3.Cursor, main: str, description: str) -> int:
    """Find the weather_conditions row for this (main, description) pair, or
    create one with the next available id. Keeps the dimension table normalized."""
    cur.execute(
        "SELECT weather_id FROM weather_conditions WHERE weather_main=? AND weather_description=?",
        (main, description),
    )
    hit = cur.fetchone()
    if hit:
        return hit["weather_id"]
    cur.execute("SELECT COALESCE(MAX(weather_id), 0) + 1 AS nid FROM weather_conditions")
    new_id = cur.fetchone()["nid"]
    cur.execute(
        "INSERT INTO weather_conditions (weather_id, weather_main, weather_description) VALUES (?,?,?)",
        (new_id, main, description),
    )
    return new_id


def _link_holiday(cur: sqlite3.Cursor, dt: datetime, name: Optional[str]) -> Optional[str]:
    """If a holiday name is supplied, upsert it keyed on the record's date and
    return that date (the FK value). Otherwise return None."""
    if not name:
        return None
    holiday_date = dt.strftime("%Y-%m-%d")
    cur.execute(
        "INSERT INTO holidays (holiday_date, holiday_name) VALUES (?,?) "
        "ON CONFLICT(holiday_date) DO UPDATE SET holiday_name=excluded.holiday_name",
        (holiday_date, name),
    )
    return holiday_date


def create(rec: RecordIn) -> RecordOut:
    conn = _connect()
    try:
        cur = conn.cursor()
        weather_id = _resolve_weather_id(cur, rec.weather_main, rec.weather_description)
        holiday_date = _link_holiday(cur, rec.date_time, rec.holiday)
        cur.execute(
            """INSERT INTO traffic_records
               (station_id, date_time, weather_id, holiday_date,
                temp_kelvin, rain_1h, snow_1h, clouds_all, traffic_volume)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rec.station_id,
                rec.date_time.strftime(_DT_FMT),
                weather_id,
                holiday_date,
                rec.temp_kelvin,
                rec.rain_1h,
                rec.snow_1h,
                rec.clouds_all,
                rec.traffic_volume,
            ),
        )
        conn.commit()
        return get_by_id(str(cur.lastrowid))
    finally:
        conn.close()


def get_by_id(record_id: str) -> Optional[RecordOut]:
    conn = _connect()
    try:
        cur = conn.execute(_SELECT + " WHERE t.record_id = ?", (record_id,))
        row = cur.fetchone()
        return _row_to_out(row) if row else None
    finally:
        conn.close()


def get_latest() -> Optional[RecordOut]:
    conn = _connect()
    try:
        cur = conn.execute(_SELECT + " ORDER BY t.date_time DESC LIMIT 1")
        row = cur.fetchone()
        return _row_to_out(row) if row else None
    finally:
        conn.close()


def get_range(start: datetime, end: datetime, limit: int = 1000) -> List[RecordOut]:
    conn = _connect()
    try:
        cur = conn.execute(
            _SELECT + " WHERE t.date_time BETWEEN ? AND ? ORDER BY t.date_time ASC LIMIT ?",
            (start.strftime(_DT_FMT), end.strftime(_DT_FMT), limit),
        )
        return [_row_to_out(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update(record_id: str, rec: RecordIn) -> Optional[RecordOut]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM traffic_records WHERE record_id=?", (record_id,))
        if not cur.fetchone():
            return None
        weather_id = _resolve_weather_id(cur, rec.weather_main, rec.weather_description)
        holiday_date = _link_holiday(cur, rec.date_time, rec.holiday)
        cur.execute(
            """UPDATE traffic_records SET
                 station_id=?, date_time=?, weather_id=?, holiday_date=?,
                 temp_kelvin=?, rain_1h=?, snow_1h=?, clouds_all=?, traffic_volume=?
               WHERE record_id=?""",
            (
                rec.station_id,
                rec.date_time.strftime(_DT_FMT),
                weather_id,
                holiday_date,
                rec.temp_kelvin,
                rec.rain_1h,
                rec.snow_1h,
                rec.clouds_all,
                rec.traffic_volume,
                record_id,
            ),
        )
        conn.commit()
        return get_by_id(record_id)
    finally:
        conn.close()


def delete(record_id: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM traffic_records WHERE record_id=?", (record_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
