"""End-to-end smoke test for the Task 3 API.

Exercises every endpoint (POST, GET one, GET latest, GET date-range, PUT, DELETE)
against BOTH the /sql and /mongo backends and prints a readable transcript. The
captured output doubles as evidence for the report.

Usage (server must be running):
    python -m api.smoke_test
"""
import json
import sys

import requests

BASE = "http://127.0.0.1:8000"

SAMPLE = {
    "date_time": "2018-09-30T23:00:00",
    "weather_main": "Clouds",
    "weather_description": "overcast clouds",
    "temp_kelvin": 283.84,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 90,
    "traffic_volume": 954,
    "station_id": "ATR-301",
    "holiday": None,
}


def show(label: str, resp: requests.Response) -> None:
    print(f"\n### {label}  ->  HTTP {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except ValueError:
        print(resp.text)


def run_backend(name: str) -> bool:
    p = f"{BASE}/{name}"
    print("\n" + "=" * 70)
    print(f"  BACKEND: {name.upper()}")
    print("=" * 70)

    # CREATE
    r = requests.post(f"{p}/records", json=SAMPLE)
    show("POST /records (create)", r)
    rec_id = r.json()["id"]

    # READ ONE
    show(f"GET /records/{rec_id} (read one)", requests.get(f"{p}/records/{rec_id}"))

    # LATEST (time-series) — should be the row we just inserted (2018-09-30)
    show("GET /records/latest (latest record)", requests.get(f"{p}/records/latest"))

    # DATE RANGE (time-series)
    show(
        "GET /records?start=2012-10-01&end=2012-10-31 (date range)",
        requests.get(f"{p}/records", params={"start": "2012-10-01", "end": "2012-10-31"}),
    )

    # UPDATE
    updated = {**SAMPLE, "traffic_volume": 1234, "weather_main": "Rain",
               "weather_description": "light rain"}
    show(f"PUT /records/{rec_id} (update volume->1234, weather->Rain)",
         requests.put(f"{p}/records/{rec_id}", json=updated))

    # DELETE
    show(f"DELETE /records/{rec_id} (delete)", requests.delete(f"{p}/records/{rec_id}"))

    # CONFIRM GONE
    r_gone = requests.get(f"{p}/records/{rec_id}")
    show(f"GET /records/{rec_id} after delete (expect 404)", r_gone)

    return r_gone.status_code == 404


def main() -> int:
    ok = True
    for backend in ("sql", "mongo"):
        try:
            ok &= run_backend(backend)
        except requests.RequestException as exc:
            print(f"\n[ERROR] {backend} backend request failed: {exc}")
            ok = False
    print("\n" + "=" * 70)
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
