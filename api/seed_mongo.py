"""Seed the MongoDB collection from the Task 2 SQLite database.

Reading the sample rows straight out of sql/metro_traffic.db (rather than
re-typing them) guarantees the SQL and MongoDB backends start from *identical*
data, so cross-backend comparisons in the report are apples-to-apples.

Usage:
    python -m api.seed_mongo          # wipe + reseed the collection
"""
import sqlite3
from datetime import datetime

from pymongo import ASCENDING, MongoClient

from . import config

_DT_FMT = "%Y-%m-%d %H:%M:%S"

_SELECT = """
SELECT t.station_id, t.date_time,
       w.weather_main, w.weather_description,
       t.temp_kelvin, t.rain_1h, t.snow_1h, t.clouds_all,
       t.traffic_volume, h.holiday_name,
       s.station_name, s.road_name, s.direction
FROM traffic_records t
JOIN weather_conditions w ON t.weather_id = w.weather_id
JOIN stations s           ON t.station_id = s.station_id
LEFT JOIN holidays h      ON t.holiday_date = h.holiday_date
ORDER BY t.date_time ASC
"""


def _rows_from_sqlite():
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(_SELECT).fetchall()
    finally:
        conn.close()


def _to_doc(r: sqlite3.Row) -> dict:
    return {
        "date_time": datetime.strptime(r["date_time"], _DT_FMT),
        "metadata": {
            "station_id": r["station_id"],
            "station_name": r["station_name"],
            "road_name": r["road_name"],
            "direction": r["direction"],
        },
        "weather": {
            "main": r["weather_main"],
            "description": r["weather_description"],
            "temp_kelvin": r["temp_kelvin"],
            "rain_1h": r["rain_1h"],
            "snow_1h": r["snow_1h"],
            "clouds_all": r["clouds_all"],
        },
        "holiday": r["holiday_name"],
        "traffic_volume": r["traffic_volume"],
    }


def main() -> None:
    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
    coll = client[config.MONGO_DB][config.MONGO_COLLECTION]
    coll.drop()  # standard collection (see mongo_backend for why not time-series)
    docs = [_to_doc(r) for r in _rows_from_sqlite()]
    if docs:
        coll.insert_many(docs)
    coll.create_index([("date_time", ASCENDING)])
    coll.create_index([("metadata.station_id", ASCENDING), ("date_time", ASCENDING)])
    print(f"Seeded {coll.count_documents({})} documents into "
          f"{config.MONGO_DB}.{config.MONGO_COLLECTION}")


if __name__ == "__main__":
    main()
