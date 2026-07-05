# Task 3 — CRUD & Time-Series Query Endpoints

**Contributor:** Enock Mugisha
**Component:** REST API layer over both databases (SQL + MongoDB)

## 1. Overview

For Task 3 I built a single REST API, using **FastAPI** (served by Uvicorn), that
exposes full CRUD operations (**POST, GET, PUT, DELETE**) plus the two required
time-series queries (**latest record** and **records by date range**) over
**both** databases designed in Task 2:

- **SQL** — the normalized SQLite database `sql/metro_traffic.db`
  (`stations` / `weather_conditions` / `holidays` / `traffic_records`).
- **MongoDB** — a collection using the embedded document shape from
  `mongodb/mongodb_design.md`.

FastAPI was chosen because it gives request/response validation (via Pydantic) and
interactive Swagger documentation at `/docs` out of the box, which made the API
easy to test and demonstrate.

## 2. Design decision — one router, two backends

Rather than write two separate sets of endpoints, I generated both from a **single
router factory** (`make_router` in `api/main.py`) parameterized by a backend
module. This means the route logic lives in exactly one place, and the SQL and
MongoDB sides are *guaranteed* to behave identically at the API layer. Every
endpoint therefore exists under both a `/sql` and a `/mongo` prefix.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/{backend}/records` | Create a record |
| GET | `/{backend}/records/latest` | **Latest record** (time-series query) |
| GET | `/{backend}/records?start=&end=&limit=` | **Records by date range** (time-series query) |
| GET | `/{backend}/records/{id}` | Read one record |
| PUT | `/{backend}/records/{id}` | Update a record |
| DELETE | `/{backend}/records/{id}` | Delete a record |
| GET | `/` | Health check + endpoint index |
| GET | `/docs` | Interactive Swagger UI |

`{backend}` is either `sql` or `mongo`. `id` is the integer `record_id` for SQL and
the `ObjectId` hex string for MongoDB.

## 3. Unified record shape (backend-agnostic clients)

Both backends accept and return the **same** denormalized JSON (defined in
`api/models.py` as the `RecordIn` / `RecordOut` Pydantic models), so a client does
not need to know which database is behind the endpoint:

```json
{
  "id": "12",
  "station_id": "ATR-301",
  "date_time": "2013-06-15T17:00:00",
  "weather_main": "Rain",
  "weather_description": "light rain",
  "temp_kelvin": 296.7,
  "rain_1h": 1.5,
  "snow_1h": 0.0,
  "clouds_all": 80,
  "traffic_volume": 5980,
  "holiday": null
}
```

The interesting part is bridging this flat shape onto Task 2's **normalized** SQL
schema. On writes, the SQL backend (`api/sql_backend.py`) transparently:

- resolves the `weather_main` / `weather_description` pair to a `weather_id`,
  inserting a new row in `weather_conditions` if the pair is new;
- upserts holidays keyed by date and links them by foreign key;
- joins the three dimension tables back on every read so the response matches the
  unified shape.

The MongoDB backend (`api/mongo_backend.py`) instead stores the embedded
`metadata` / `weather` / `holiday` document directly, as per the Task 2 design.

## 4. Time-series endpoints

- **Latest record** — SQL runs `ORDER BY date_time DESC LIMIT 1`; MongoDB runs
  `find(sort=[("date_time", -1)]).limit(1)`.
- **Records by date range** — SQL uses `WHERE date_time BETWEEN ? AND ?`; MongoDB
  uses `{date_time: {$gte, $lte}}`. Both are backed by an index on `date_time`
  (MongoDB also indexes `metadata.station_id + date_time`), so range scans stay
  efficient.

## 5. Robustness

- **Validation** — Pydantic enforces field types and constraints (e.g.
  `clouds_all` in 0–100, non-negative `rain_1h` / `snow_1h` / `traffic_volume`)
  and rejects malformed requests with a clear 422 before they reach the database.
- **Correct HTTP status codes** — `201` on create, `404` when a record id does not
  exist (read/update/delete), `200` on success.
- **Graceful failure** — a `_guard` helper wraps every backend call and converts a
  dead MongoDB connection into a clean `503 Database unavailable` instead of a raw
  500 stack trace.
- **MongoDB collection-type note** — Task 2's design uses a native *time-series*
  collection for analytical storage, but that collection type rejects
  single-document updates (`Cannot perform a non-multi update on a time-series
  collection`), which is incompatible with a REST `PUT`. The API therefore uses a
  **standard** collection with the identical document shape and the same indexes,
  so full CRUD works while staying faithful to the Task 2 document model.

## 6. Verification / evidence

I wrote an end-to-end test, `api/smoke_test.py`, that drives the full CRUD
lifecycle plus both time-series endpoints against **both** backends and prints a
transcript. The captured run is saved in `api/sample_api_results.txt` and ends with
`ALL CHECKS PASSED`. Highlights:

- **CRUD lifecycle** (per backend): `POST` a new record → `GET` it by id → `PUT`
  updates its volume to `1234` and weather to `Rain` → `DELETE` it → a follow-up
  `GET` correctly returns `404 Record not found`.
- **Latest record** — immediately after the `POST`, the `latest` endpoint returns
  the just-created 2018-09-30 record on both backends, confirming the write is
  reflected.
- **Cross-validation** — the October-2012 date-range query returns the **same six
  traffic volumes** (`5545, 4516, 4767, 5026, 6852, 6947`) on both the SQL and
  MongoDB backends, proving the two independent implementations agree.

## 7. How to run

```bash
# from repo root
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python sql/build_and_query.py          # build the SQL database (Task 2 loader)
mongod --dbpath /path/to/data &        # start MongoDB
python -m api.seed_mongo               # seed Mongo from the same data

uvicorn api.main:app --reload          # -> http://127.0.0.1:8000/docs
python -m api.smoke_test               # end-to-end verification transcript
```

## 8. Files I authored

| File | Purpose |
| ---- | ------- |
| `api/main.py` | FastAPI app; shared router factory for both backends |
| `api/models.py` | Pydantic request/response schemas (unified record shape) |
| `api/sql_backend.py` | CRUD + time-series against SQLite (normalized schema) |
| `api/mongo_backend.py` | CRUD + time-series against MongoDB |
| `api/config.py` | Env-overridable paths / connection settings |
| `api/seed_mongo.py` | Seeds MongoDB from the Task 2 SQLite data |
| `api/smoke_test.py` | End-to-end endpoint test / evidence generator |
| `api/sample_api_results.txt` | Captured smoke-test transcript |
| `api/README.md` | API documentation |
