-- ============================================================
-- Metro Interstate Traffic Volume — Relational Schema
-- Dialect: PostgreSQL (SERIAL/TIMESTAMP). For MySQL, swap
-- SERIAL -> INT AUTO_INCREMENT and TIMESTAMP stays the same.
-- ============================================================

-- 1. STATIONS
-- Dimension table for the monitoring station. The source dataset
-- only has one station (ATR 301), but modeling it as its own table
-- means the schema scales cleanly if more stations are added later.
CREATE TABLE stations (
    station_id          VARCHAR(20)   PRIMARY KEY,
    station_name        VARCHAR(100)  NOT NULL,
    road_name            VARCHAR(20)   NOT NULL,
    direction            VARCHAR(20)   NOT NULL,
    location_description VARCHAR(200)
);

-- 2. WEATHER_CONDITIONS
-- Dimension table for weather categories. Normalizing this out avoids
-- storing repeated text strings (weather_main / weather_description)
-- on every single hourly row.
CREATE TABLE weather_conditions (
    weather_id    INTEGER PRIMARY KEY,
    weather_main  VARCHAR(50) NOT NULL,
    weather_description VARCHAR(150) NOT NULL,
    UNIQUE (weather_main, weather_description)
);

-- 3. HOLIDAYS
-- Dimension table for US national + regional holidays (incl. MN State Fair).
-- Keyed by date since only one holiday can apply per calendar day.
CREATE TABLE holidays (
    holiday_date  DATE PRIMARY KEY,
    holiday_name  VARCHAR(100) NOT NULL
);

-- 4. TRAFFIC_RECORDS (fact table)
-- One row per hourly observation. FKs point into the dimension tables above.
-- UNIQUE(station_id, date_time) guards against the duplicate-timestamp
-- issue documented in EDA on this dataset.
CREATE TABLE traffic_records (
    record_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id     VARCHAR(20)  NOT NULL REFERENCES stations(station_id),
    date_time      TIMESTAMP    NOT NULL,
    weather_id     INTEGER      NOT NULL REFERENCES weather_conditions(weather_id),
    holiday_date   DATE         REFERENCES holidays(holiday_date),
    temp_kelvin    NUMERIC(6,2) NOT NULL,
    rain_1h        NUMERIC(6,2) NOT NULL DEFAULT 0,
    snow_1h        NUMERIC(6,2) NOT NULL DEFAULT 0,
    clouds_all     INTEGER      NOT NULL,
    traffic_volume INTEGER      NOT NULL,
    UNIQUE (station_id, date_time)
);

-- Indexes to support the time-series query patterns from Task 3
-- (latest record, date range lookups) and the analytical joins from Task 1.
CREATE INDEX idx_traffic_datetime ON traffic_records(date_time);
CREATE INDEX idx_traffic_weather  ON traffic_records(weather_id);
CREATE INDEX idx_traffic_holiday  ON traffic_records(holiday_date);
