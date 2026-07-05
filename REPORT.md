# Metro Interstate Traffic Volume — Project Report

**Course:** _[course name]_
**Group members:** _[names]_
**Dataset:** Metro Interstate Traffic Volume (Kaggle / UCI), hourly I-94 westbound
traffic volume near Minneapolis–St. Paul, MN, Oct 2012–Sep 2018.

---

## 1. Introduction

_[1 paragraph: why this dataset, what the prediction target is (traffic_volume),
why it qualifies — clear timestamp, meaningful target, multiple variables over time.]_

---

## 2. Task 1 — Time-Series Preprocessing and Exploratory Analysis

### 2.1 Understanding the dataset

_[Time range, frequency/granularity, the known Aug 2014–Jun 2015 gap, missing value
handling and justification, distribution summaries.]_

### 2.2 Analytical questions

_[List your 5+ questions, each with a chart + interpretation. Confirm at least two
use lagged features/moving averages.]_

1. _[Question]_ — Finding: _[...]_
2. _[Question]_ — Finding: _[...]_
3. _[Question]_ — Finding: _[...]_
4. _[Question, lag/MA]_ — Finding: _[...]_
5. _[Question, lag/MA]_ — Finding: _[...]_

### 2.3 Model training

_[Model chosen, features used, hyperparameter tuning approach, experiment
comparison table (≥2 experiments: params, metric, notes).]_

| Experiment | Model | Key hyperparameters | Metric (e.g. RMSE) | Notes |
| ---------- | ----- | ------------------- | ------------------ | ----- |
| 1          |       |                     |                    |       |
| 2          |       |                     |                    |       |

---

## 3. Task 2 — Database Design (SQL and MongoDB)

### 3.1 Relational schema

The relational design normalizes the dataset into four tables to avoid redundant
storage of repeated categorical text and to enforce referential integrity:

- **stations** — the monitoring station (ATR-301). Modeled as its own table so the
  schema generalizes to multiple stations if extended.
- **weather_conditions** — normalizes `weather_main`/`weather_description` pairs out
  of the fact table.
- **holidays** — keyed by date; a holiday applies to at most one calendar day.
- **traffic_records** (fact table) — one row per hourly observation, with foreign
  keys into the three dimension tables above, and a `UNIQUE(station_id, date_time)`
  constraint that prevents the duplicate-timestamp issue documented during Task 1 EDA.

See `diagrams/erd.mermaid` for the ERD and `sql/schema.sql` for the full DDL.

**Queries performed** (full output in `sql/sample_query_results.txt`, produced by
running `sql/build_and_query.py` against sample data):

1. Latest record — `ORDER BY date_time DESC LIMIT 1`
2. Records by date range — `WHERE date_time BETWEEN ... AND ...`
3. Average traffic volume by weather condition — `GROUP BY weather_main`
4. Holiday vs. non-holiday average traffic volume — `GROUP BY` on a `CASE` expression

Result excerpt: average traffic volume was 5,932 vehicles/hour on non-holidays vs.
828 on holidays in the sample data, consistent with the well-documented holiday dip
in this dataset.

### 3.2 MongoDB design

The MongoDB design takes the opposite approach: a single collection with embedded
weather/holiday data, using MongoDB's native **time-series collection type**
(`timeseries: { timeField: "date_time", metaField: "metadata", granularity: "hours" }`),
purpose-built for regular measurements over time from a small number of sources.
Full design, sample documents, and query results are in `mongodb/mongodb_design.md`.

The same four queries were run against the MongoDB design and return matching
aggregate results to the SQL side, which we use as a cross-validation check between
the two implementations.

### 3.3 Relational vs. MongoDB — design tradeoffs

_[Summarize: normalization/integrity vs. denormalization/read-optimization; when
you'd pick one over the other for this workload.]_

---

## 4. Task 3 — CRUD and Time-Series Query Endpoints

The API is built with **FastAPI** (served by Uvicorn), which gives interactive
Swagger documentation at `/docs` for free. Full CRUD plus the two required
time-series queries are exposed for **both** backends. To guarantee the SQL and
MongoDB sides behave identically, both are generated from a single router factory
(`api/main.py`) parameterized by a backend module — so there is exactly one place
where route logic lives. Every endpoint below exists under both the `/sql` and
`/mongo` prefixes:

| Method | Endpoint               | Backend     | Description           |
| ------ | ---------------------- | ----------- | --------------------- |
| POST   | `/{backend}/records`             | SQL / Mongo | Create a record       |
| GET    | `/{backend}/records/latest`      | SQL / Mongo | **Latest record**     |
| GET    | `/{backend}/records?start=&end=` | SQL / Mongo | **Records by date range** |
| GET    | `/{backend}/records/{id}`        | SQL / Mongo | Get a record          |
| PUT    | `/{backend}/records/{id}`        | SQL / Mongo | Update a record       |
| DELETE | `/{backend}/records/{id}`        | SQL / Mongo | Delete a record       |

**Unified record shape.** Both backends accept and return the same denormalized
JSON, so clients are backend-agnostic. On the SQL side the API transparently maps
this shape onto the normalized Task 2 schema — resolving
`weather_main`/`weather_description` to a `weather_id` (inserting new pairs when
needed) and upserting holidays keyed by date — while MongoDB stores the embedded
`metadata`/`weather`/`holiday` document from the Task 2 design.

**Time-series endpoints.**
- *Latest record* — SQL runs `ORDER BY date_time DESC LIMIT 1`; MongoDB runs
  `find(sort=[("date_time", -1)]).limit(1)`.
- *Records by date range* — SQL uses `WHERE date_time BETWEEN ? AND ?`; MongoDB
  uses `{date_time: {$gte, $lte}}`. Both are backed by an index on `date_time`.

**MongoDB collection type.** Task 2's design uses a native *time-series*
collection for analytical storage, but that type rejects single-document updates
(`Cannot perform a non-multi update on a time-series collection`), which breaks a
REST `PUT`. The API therefore uses a standard collection with the identical
document shape and the same indexes, so full CRUD works while remaining faithful
to the Task 2 document model.

**Verification.** `api/smoke_test.py` drives the entire CRUD lifecycle plus both
time-series endpoints against both backends; the captured transcript is in
`api/sample_api_results.txt`. As a cross-check, the October-2012 date-range query
returns the same six traffic volumes (`5545, 4516, 4767, 5026, 6852, 6947`) on
both the SQL and MongoDB backends, and a record created via `POST` is immediately
reflected by the `latest` endpoint on both.

---

## 5. Task 4 — Prediction/Forecast Script

_[Describe the script: fetches a record from the Task 3 API, applies the same
preprocessing pipeline from Task 1, loads the trained model artifact, and returns
a forecast. Include a short example run.]_

---

## 6. Team Contributions

| Name       | Main components                                    | Details       |
| ---------- | -------------------------------------------------- | ------------- |
| _[Name 1]_ | _[e.g. Task 1 — EDA & analytical questions]_       | _[specifics]_ |
| _[Name 2]_ | _[e.g. Task 1 — modeling & tuning / Task 2 — SQL]_ | _[specifics]_ |
| _[Name 3]_ | _[e.g. Task 2 — MongoDB / Task 3 — API]_           | _[specifics]_ |
| _[Name 4]_ | _[e.g. Task 4 — prediction script / integration]_  | _[specifics]_ |

---

## 7. Conclusion

_[Summary of findings, model performance, and any limitations.]_
