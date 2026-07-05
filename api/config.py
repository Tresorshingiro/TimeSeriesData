"""Central configuration for the API.

All values can be overridden with environment variables so the same code runs
against a grader's local setup, a Docker container, or CI without edits.
"""
import os
from pathlib import Path

# Repo root = one level up from this file's directory (api/).
REPO_ROOT = Path(__file__).resolve().parent.parent

# --- SQL (SQLite) backend ---------------------------------------------------
# Reuses the exact database built in Task 2 by sql/build_and_query.py.
SQLITE_PATH = os.getenv("SQLITE_PATH", str(REPO_ROOT / "sql" / "metro_traffic.db"))

# Every record belongs to a station; the dataset has exactly one (ATR-301).
DEFAULT_STATION_ID = os.getenv("DEFAULT_STATION_ID", "ATR-301")

# --- MongoDB backend --------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "metro_traffic")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "traffic_records")
