import sqlite3
import os

DB_PATH = "./metro_traffic.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")
cur = conn.cursor()

with open("./schema.sql") as f:
    cur.executescript(f.read())

# --- Dimension data ---
cur.execute("INSERT INTO stations VALUES (?,?,?,?,?)",
            ("ATR-301", "MN DoT ATR Station 301", "I-94", "Westbound",
             "Roughly midway between Minneapolis and St Paul, MN"))

weather_rows = [
    (1, "Clouds", "scattered clouds"),
    (2, "Clear",  "sky is clear"),
    (3, "Rain",   "light rain"),
    (4, "Snow",   "light snow"),
    (5, "Mist",   "mist"),
    (6, "Clouds", "overcast clouds"),
]
cur.executemany("INSERT INTO weather_conditions VALUES (?,?,?)", weather_rows)

holiday_rows = [
    ("2012-12-25", "Christmas Day"),
    ("2013-01-01", "New Years Day"),
    ("2012-09-01", "Labor Day"),
]
cur.executemany("INSERT INTO holidays VALUES (?,?)", holiday_rows)

# --- Fact data: representative hourly rows spanning a few days,
#     including a holiday and a range of weather conditions ---
traffic_rows = [
    # station, date_time,            weather_id, holiday,      temp_K, rain, snow, clouds, volume
    ("ATR-301", "2012-10-02 09:00:00", 1,
     None,          288.28, 0.0, 0.0, 40, 5545),
    ("ATR-301", "2012-10-02 10:00:00", 2,
     None,          289.36, 0.0, 0.0,  1, 4516),
    ("ATR-301", "2012-10-02 11:00:00", 3,
     None,          289.58, 0.25, 0.0, 75, 4767),
    ("ATR-301", "2012-10-02 12:00:00", 6,
     None,          290.13, 0.0, 0.0, 90, 5026),
    ("ATR-301", "2012-10-03 07:00:00", 2,
     None,          284.32, 0.0, 0.0,  0, 6852),
    ("ATR-301", "2012-10-03 08:00:00", 1,
     None,          285.10, 0.0, 0.0, 20, 6947),
    ("ATR-301", "2012-12-25 00:00:00", 4,
     "2012-12-25",  263.15, 0.0, 1.2, 90,  680),
    ("ATR-301", "2012-12-25 01:00:00", 4,
     "2012-12-25",  262.90, 0.0, 0.8, 90,  502),
    ("ATR-301", "2012-12-25 09:00:00", 4,
     "2012-12-25",  264.00, 0.0, 0.5, 88, 1240),
    ("ATR-301", "2013-01-01 00:00:00", 5,
     "2013-01-01",  270.11, 0.0, 0.0, 65,  890),
    ("ATR-301", "2013-01-02 08:00:00", 2,
     None,          268.44, 0.0, 0.0,  5, 6210),
    ("ATR-301", "2013-01-02 17:00:00", 1,
     None,          271.02, 0.0, 0.0, 55, 6688),
    ("ATR-301", "2013-06-15 08:00:00", 2,
     None,          295.20, 0.0, 0.0,  2, 6790),
    ("ATR-301", "2013-06-15 17:00:00", 3,
     None,          296.70, 1.5, 0.0, 80, 5980),
]
cur.executemany("""INSERT INTO traffic_records
    (station_id, date_time, weather_id, holiday_date, temp_kelvin, rain_1h, snow_1h, clouds_all, traffic_volume)
    VALUES (?,?,?,?,?,?,?,?,?)""", traffic_rows)

conn.commit()


def run(label, query):
    print(f"\n--- {label} ---")
    print(query.strip())
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall():
        print(" | ".join(str(v) for v in row))


# Query 1: Latest record (needed for Task 3 endpoint too)
run("Query 1: Latest record", """
SELECT t.date_time, t.traffic_volume, w.weather_main, s.station_name
FROM traffic_records t
JOIN weather_conditions w ON t.weather_id = w.weather_id
JOIN stations s ON t.station_id = s.station_id
ORDER BY t.date_time DESC
LIMIT 1;
""")

# Query 2: Records by date range (needed for Task 3 endpoint too)
run("Query 2: Records in date range 2012-10-01 to 2012-10-31", """
SELECT date_time, traffic_volume, temp_kelvin
FROM traffic_records
WHERE date_time BETWEEN '2012-10-01' AND '2012-10-31 23:59:59'
ORDER BY date_time;
""")

# Query 3: Average traffic volume by weather condition (analytical)
run("Query 3: Avg traffic volume by weather_main", """
SELECT w.weather_main, ROUND(AVG(t.traffic_volume),1) AS avg_volume, COUNT(*) AS n_obs
FROM traffic_records t
JOIN weather_conditions w ON t.weather_id = w.weather_id
GROUP BY w.weather_main
ORDER BY avg_volume DESC;
""")

# Query 4: Holiday vs non-holiday average traffic volume (analytical)
run("Query 4: Holiday vs non-holiday avg traffic volume", """
SELECT CASE WHEN holiday_date IS NULL THEN 'Non-holiday' ELSE 'Holiday' END AS day_type,
       ROUND(AVG(traffic_volume),1) AS avg_volume,
       COUNT(*) AS n_obs
FROM traffic_records
GROUP BY day_type;
""")

conn.close()
print("\nDB written to:", DB_PATH)
