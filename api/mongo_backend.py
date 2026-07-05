"""MongoDB backend — CRUD + time-series queries.

Document shape matches Task 2's MongoDB design (denormalized: embedded
`metadata`, `weather`, and a flat `holiday`). Task 2's design uses a native
*time-series* collection for analytical storage; that collection type
intentionally forbids single-document updates ("Cannot perform a non-multi
update on a time-series collection"), which is incompatible with a REST PUT.
The API therefore uses a *standard* collection with the identical shape and the
same indexes, so full CRUD works while staying faithful to the document model.
"""
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, MongoClient

from . import config
from .models import RecordIn, RecordOut

# Station dimension is embedded per-document; the dataset has one station.
_STATION_META = {
    "ATR-301": {
        "station_id": "ATR-301",
        "station_name": "MN DoT ATR Station 301",
        "road_name": "I-94",
        "direction": "Westbound",
    }
}

_client: Optional[MongoClient] = None


def _collection():
    """Lazily connect and ensure the two time-series indexes exist."""
    global _client
    if _client is None:
        _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
    coll = _client[config.MONGO_DB][config.MONGO_COLLECTION]
    coll.create_index([("date_time", ASCENDING)])
    coll.create_index([("metadata.station_id", ASCENDING), ("date_time", ASCENDING)])
    return coll


def _to_doc(rec: RecordIn) -> dict:
    return {
        "date_time": rec.date_time,
        "metadata": _STATION_META.get(rec.station_id, {"station_id": rec.station_id}),
        "weather": {
            "main": rec.weather_main,
            "description": rec.weather_description,
            "temp_kelvin": rec.temp_kelvin,
            "rain_1h": rec.rain_1h,
            "snow_1h": rec.snow_1h,
            "clouds_all": rec.clouds_all,
        },
        "holiday": rec.holiday,
        "traffic_volume": rec.traffic_volume,
    }


def _doc_to_out(doc: dict) -> RecordOut:
    w = doc.get("weather", {})
    return RecordOut(
        id=str(doc["_id"]),
        station_id=doc.get("metadata", {}).get("station_id", config.DEFAULT_STATION_ID),
        date_time=doc["date_time"],
        weather_main=w.get("main"),
        weather_description=w.get("description"),
        temp_kelvin=w.get("temp_kelvin"),
        rain_1h=w.get("rain_1h", 0.0),
        snow_1h=w.get("snow_1h", 0.0),
        clouds_all=w.get("clouds_all"),
        traffic_volume=doc["traffic_volume"],
        holiday=doc.get("holiday"),
    )


def _oid(record_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(record_id)
    except (InvalidId, TypeError):
        return None


def create(rec: RecordIn) -> RecordOut:
    doc = _to_doc(rec)
    res = _collection().insert_one(doc)
    doc["_id"] = res.inserted_id
    return _doc_to_out(doc)


def get_by_id(record_id: str) -> Optional[RecordOut]:
    oid = _oid(record_id)
    if oid is None:
        return None
    doc = _collection().find_one({"_id": oid})
    return _doc_to_out(doc) if doc else None


def get_latest() -> Optional[RecordOut]:
    doc = _collection().find_one(sort=[("date_time", DESCENDING)])
    return _doc_to_out(doc) if doc else None


def get_range(start: datetime, end: datetime, limit: int = 1000) -> List[RecordOut]:
    cursor = (
        _collection()
        .find({"date_time": {"$gte": start, "$lte": end}})
        .sort("date_time", ASCENDING)
        .limit(limit)
    )
    return [_doc_to_out(d) for d in cursor]


def update(record_id: str, rec: RecordIn) -> Optional[RecordOut]:
    oid = _oid(record_id)
    if oid is None:
        return None
    res = _collection().replace_one({"_id": oid}, _to_doc(rec))
    if res.matched_count == 0:
        return None
    return get_by_id(record_id)


def delete(record_id: str) -> bool:
    oid = _oid(record_id)
    if oid is None:
        return False
    return _collection().delete_one({"_id": oid}).deleted_count > 0
