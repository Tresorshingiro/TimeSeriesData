# Metro Interstate Traffic Volume — Time Series Analysis, Forecasting & Database Design

Course project analyzing the [Metro Interstate Traffic Volume dataset](https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume)
(hourly I-94 westbound traffic volume near Minneapolis/St. Paul, MN, with weather and
holiday features, Oct 2012–Sep 2018).

## Repo structure

```
.
├── notebooks/        # Task 1: EDA, analytical questions, model training/tuning
├── sql/               # Task 2: relational schema, sample data loader, query results
│   ├── schema.sql
│   ├── build_and_query.py
│   └── sample_query_results.txt
├── mongodb/           # Task 2: MongoDB collection design, sample documents, queries
│   └── mongodb_design.md
├── diagrams/          # ERD (Mermaid)
│   └── erd.mermaid
├── api/               # Task 3: CRUD + time-series query endpoints (SQL + MongoDB)
├── data/              # Raw/processed dataset (not committed if large — see below)
├── scripts/           # Task 4: end-to-end prediction/forecast script
└── docs/              # Report source + supporting docs
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Task summaries

- **Task 1 (EDA + modeling):** see `notebooks/`. Covers time range/frequency of the
  dataset, missing value handling, distributions, five+ analytical questions
  (including lag features and moving averages), and model training with a
  hyperparameter tuning experiment table.
- **Task 2 (Databases):** see `sql/` and `mongodb/`. Relational schema is normalized
  into 4 tables (stations, weather_conditions, holidays, traffic_records — see
  `diagrams/erd.mermaid`). MongoDB uses a single denormalized time-series collection.
  Both designs are validated against the same sample data and return matching
  aggregate results.
- **Task 3 (API):** see `api/`. CRUD endpoints for both the SQL and MongoDB backends,
  plus dedicated time-series endpoints (latest record, records by date range).
- **Task 4 (Prediction script):** see `scripts/`. Fetches a record from the API,
  applies the same preprocessing pipeline as Task 1, loads the trained model, and
  returns a forecast.

## Team

| Name  | Role / Main components |
| ----- | ---------------------- |
| _TBD_ | _TBD_                  |
| _TBD_ | _TBD_                  |
| _TBD_ | _TBD_                  |

## Report

The full PDF report (`docs/report.pdf`) details implementation choices for all four
tasks and each member's contribution. Source is in `docs/report.md`.
