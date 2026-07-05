# Task 3 — CRUD & Time-Series API (SQL + MongoDB)

A [FastAPI](https://fastapi.tiangolo.com/) service exposing full CRUD plus the two
required time-series queries (**latest record**, **records by date range**) over
**both** backends built in Task 2:

- **SQL** — the normalized SQLite database `sql/metro_traffic.db`
  (`stations` / `weather_conditions` / `holidays` / `traffic_records`).
- **MongoDB** — a collection using the denormalized document shape from
  `mongodb/mongodb_design.md`.

Both backends are served by one router factory (`api/main.py`), so they behave
identically at the API layer and can be compared directly.

## Endpoints

Each is available under **both** `/sql` and `/mongo`:

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/{backend}/records` | Create a record |
| `GET` | `/{backend}/records/latest` | **Latest record** (time-series) |
| `GET` | `/{backend}/records?start=&end=&limit=` | **Records by date range** (time-series) |
| `GET` | `/{backend}/records/{id}` | Read one record |
| `PUT` | `/{backend}/records/{id}` | Update a record |
| `DELETE` | `/{backend}/records/{id}` | Delete a record |
| `GET` | `/` | Health check + endpoint index |
| `GET` | `/docs` | Interactive Swagger UI |

`{backend}` is `sql` or `mongo`. `id` is the integer `record_id` for SQL and the
`ObjectId` hex string for MongoDB.

### Unified record shape

Both backends accept and return the same denormalized JSON, so clients don't need
to know which database is behind the endpoint:

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

On the SQL side the API transparently resolves `weather_main`/`weather_description`
to a `weather_id` (inserting new pairs) and upserts holidays, keeping the
normalized schema intact.

## Running it

```bash
# 1. Install deps (from repo root)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Build the SQL database (Task 2 loader)
python sql/build_and_query.py

# 3. Start MongoDB, then seed it from the same SQLite data
mongod --dbpath /path/to/data --port 27017 &
python -m api.seed_mongo

# 4. Launch the API
uvicorn api.main:app --reload
# -> http://127.0.0.1:8000/docs
```

> **Note on the MongoDB collection type.** Task 2's design uses a native
> *time-series* collection for analytical storage. That collection type
> intentionally rejects single-document updates
> (`Cannot perform a non-multi update on a time-series collection`), which is
> incompatible with a REST `PUT`. The API therefore uses a **standard**
> collection with the identical document shape and the same indexes
> (`date_time`, `metadata.station_id + date_time`), so full CRUD works while
> staying faithful to the Task 2 document model.

## Example requests

```bash
# Latest record (SQL)
curl "http://127.0.0.1:8000/sql/records/latest"

# Records in a date range (MongoDB)
curl "http://127.0.0.1:8000/mongo/records?start=2012-10-01&end=2012-10-31"

# Create (SQL)
curl -X POST "http://127.0.0.1:8000/sql/records" -H "Content-Type: application/json" -d '{
  "date_time": "2018-09-30T23:00:00", "weather_main": "Clouds",
  "weather_description": "overcast clouds", "temp_kelvin": 283.84,
  "clouds_all": 90, "traffic_volume": 954, "station_id": "ATR-301"}'

# Update / Delete
curl -X PUT    "http://127.0.0.1:8000/mongo/records/<id>" -H "Content-Type: application/json" -d '{...}'
curl -X DELETE "http://127.0.0.1:8000/sql/records/<id>"
```

## Verifying everything works

With the server running:

```bash
python -m api.smoke_test
```

This drives the full CRUD lifecycle plus both time-series endpoints against
**both** backends and prints a transcript. A captured run is saved in
[`sample_api_results.txt`](sample_api_results.txt). Both backends return
identical data (e.g. the Oct-2012 date-range query yields the same six volumes
`5545, 4516, 4767, 5026, 6852, 6947` on each), cross-validating the two
implementations.

## Files

| File | Purpose |
| ---- | ------- |
| `main.py` | FastAPI app; router factory shared by both backends |
| `models.py` | Pydantic request/response schemas (unified record shape) |
| `sql_backend.py` | CRUD + time-series against SQLite |
| `mongo_backend.py` | CRUD + time-series against MongoDB |
| `config.py` | Env-overridable paths / connection settings |
| `seed_mongo.py` | Seeds MongoDB from the Task 2 SQLite data |
| `smoke_test.py` | End-to-end endpoint test / evidence generator |
| `sample_api_results.txt` | Captured smoke-test transcript |
