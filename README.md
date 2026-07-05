# Metro Interstate Traffic Volume — Time Series Analysis, Forecasting & Database Design

Group course project analyzing the [Metro Interstate Traffic Volume dataset](https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume)
(Kaggle / UCI): six years of **hourly westbound traffic counts on I-94** near
Minneapolis–St Paul, MN (Oct 2012 – Sep 2018), with weather and holiday features.

The dataset meets all assignment requirements: a clear timestamp column
(`date_time`, hourly), a meaningful forecasting target (`traffic_volume`,
vehicles/hour), and multiple measurable variables over time (temperature,
rain, snow, cloud cover, weather category, holidays).

## Repo structure

```
.
├── EDA_Model.ipynb                     # Task 1: EDA, 5 analytical questions, model training/tuning
├── Metro_Interstate_Traffic_Volume.csv # Raw dataset (48,204 hourly rows)
├── traffic_model.joblib                # Trained model bundle (Task 1 → served by Task 4)
├── sql/                                # Task 2: relational design (SQLite)
│   ├── schema.sql                      #   DDL — 4 normalized tables
│   ├── build_and_query.py              #   builds metro_traffic.db + runs the 4 sample queries
│   ├── metro_traffic.db                #   the built database
│   └── sample_query_results.txt        #   captured query output
├── mongodb/
│   └── mongodb_design.md               # Task 2: MongoDB collection design, sample docs, queries + results
├── diagrams/
│   └── erd.mermaid                     # ERD for the relational schema
├── api/                                # Tasks 3 & 4: FastAPI app
│   ├── main.py                         #   CRUD + time-series routers (SQL & Mongo) + /predict ML endpoint
│   ├── README.md                       #   full endpoint docs & examples
│   └── smoke_test.py                   #   end-to-end verification (transcript in sample_api_results.txt)
└── docs/
    └── report.docx                     # Project report (export to PDF for submission)
```

## Setup

Requires Python 3.10+ and (for the MongoDB backend) a local MongoDB server.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## How to run each task

### Task 1 — EDA & modeling

```bash
jupyter notebook EDA_Model.ipynb
```

Covers the dataset's time range and hourly granularity, missing-value handling
(duplicate timestamps, disguised sentinels like 0 K temperatures, the 2014–15
sensor outage), distributions, and **five analytical questions** — including
lag-feature and moving-average analyses. Trains and compares **4 experiments**
(Linear Regression baseline + 3 tuned Random Forests) on a chronological
80/20 split; the best deployable model (test RMSE ≈ 235 veh/h, R² ≈ 0.986) is
saved to `traffic_model.joblib` together with its feature list and
preprocessing constants.

### Task 2 — Databases

```bash
cd sql && python build_and_query.py   # rebuilds metro_traffic.db, prints the 4 queries + results
```

- **Relational (SQLite):** normalized into 4 tables — `stations`,
  `weather_conditions`, `holidays`, `traffic_records` — with a
  `UNIQUE(station_id, date_time)` guard against the duplicate-timestamp issue
  found in Task 1. ERD in `diagrams/erd.mermaid`.
- **MongoDB:** a single denormalized time-series collection with embedded
  weather/station metadata — see `mongodb/mongodb_design.md`.
- Both designs run the same 4 queries against the same sample data and return
  **identical results**, cross-validating the two implementations.

### Task 3 — CRUD & time-series API

```bash
(cd sql && python build_and_query.py)  # 1. build the SQL database
python -m api.seed_mongo               # 2. seed MongoDB from it (MongoDB must be running)
uvicorn api.main:app --reload          # 3. launch → http://127.0.0.1:8000/docs
```

Full CRUD (POST/GET/PUT/DELETE) plus the two required time-series queries —
**latest record** and **records by date range** — exposed identically under
both `/sql` and `/mongo` prefixes from a single router factory. Verify
everything end-to-end with `python -m api.smoke_test` (transcript in
`api/sample_api_results.txt`). Details in [`api/README.md`](api/README.md).

### Task 4 — Traffic volume prediction

The trained Task 1 model is served by the same API as a prediction endpoint:

```bash
uvicorn api.main:app --reload   # run from the repo root so traffic_model.joblib is found
```

`POST /predict/` accepts the model's 22 features — weather metrics, calendar
components (`hour`, `dayofweek`, `month`, `is_holiday`), the time-series
features from Task 1 (`lag_1`, `lag_24`, `lag_168`, `roll_mean_24`), and the
one-hot weather category — and returns `predicted_traffic_volume`:

```bash
curl -X POST "http://127.0.0.1:8000/predict/" -H "Content-Type: application/json" -d '{
  "temp": 10.5, "rain_1h": 0.0, "snow_1h": 0.0, "clouds_all": 40, "is_holiday": 0,
  "hour": 17, "dayofweek": 2, "month": 6,
  "lag_1": 5200, "lag_24": 5400, "lag_168": 5500, "roll_mean_24": 3300,
  "weather_main_Clouds": 1}'
```

The lag features come straight from the Task 3 time-series endpoints (e.g.
`GET /sql/records/latest` and the date-range query), consolidating all
previous tasks: fetch recent records from the API → build the Task 1 feature
pipeline → model inference → forecast.

## Team

| Name  | Role / Main components |
| ----- | ---------------------- |
| _TBD_ | _TBD_                  |
| _TBD_ | _TBD_                  |
| _TBD_ | _TBD_                  |

## Report

`docs/report.docx` details the implementation of all four tasks and each
member's contribution; the final submission is its PDF export plus this repo's
link.
