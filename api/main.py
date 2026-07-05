"""
Task 3 - FastAPI Application (SQL & MongoDB Backends)
Task 4 - Machine Learning Prediction Endpoint Integration with Time-Series Features
"""

from datetime import datetime
from typing import List, Optional
import joblib

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo.errors import PyMongoError

# Import backend clients and models from your project structure
from .import mongo_backend, sql_backend
from .models import RecordIn, RecordOut

app = FastAPI(
    title="Metro Traffic Volume API",
    description="Task 3 & 4: CRUD and time-series query endpoints over SQL/MongoDB + ML Traffic Volume Predictions.",
    version="2.1.0",
)


# ==========================================
# TASK 4: ML MODEL INPUT SCHEMAS & ROUTER
# ==========================================
class PredictionInput(BaseModel):
    # Core weather metrics
    temp: float
    rain_1h: float
    snow_1h: float
    clouds_all: int
    is_holiday: int  # 0 or 1
    
    # DateTime components
    hour: int
    dayofweek: int  # 0 (Monday) to 6 (Sunday)
    month: int      # 1 to 12
    
    # Time-series engineered features
    lag_1: float
    lag_24: float
    lag_168: float
    roll_mean_24: float
    
    # One-hot encoded weather types (0 or 1 for each)
    weather_main_Clouds: int = 0
    weather_main_Drizzle: int = 0
    weather_main_Fog: int = 0
    weather_main_Haze: int = 0
    weather_main_Mist: int = 0
    weather_main_Rain: int = 0
    weather_main_Smoke: int = 0
    weather_main_Snow: int = 0
    weather_main_Squall: int = 0
    weather_main_Thunderstorm: int = 0


predict_router = APIRouter(prefix="/predict", tags=["Prediction"])

# Safely load the pre-trained ML model dictionary bundle from the project root
try:
    model_bundle = joblib.load("traffic_model.joblib")
    # Extract the underlying trained model object out of the dictionary
    traffic_model = model_bundle["model"]
except Exception as e:
    print(f"⚠️ Error loading traffic_model.joblib bundle: {e}")
    traffic_model = None


@predict_router.post("/", summary="Predict traffic volume using ML model")
def predict_traffic(payload: PredictionInput):
    """
    Accepts full time-series and weather attributes and returns a predicted traffic volume metric.
    """
    if traffic_model is None:
        raise HTTPException(
            status_code=500, 
            detail="Machine Learning model pipeline failed to load on server start."
        )
    
    try:
        # Structure the payload values into the exact 22-column order the model expects
        features = [[
            payload.temp, payload.rain_1h, payload.snow_1h, payload.clouds_all, payload.is_holiday,
            payload.hour, payload.dayofweek, payload.month,
            payload.lag_1, payload.lag_24, payload.lag_168, payload.roll_mean_24,
            payload.weather_main_Clouds, payload.weather_main_Drizzle, payload.weather_main_Fog,
            payload.weather_main_Haze, payload.weather_main_Mist, payload.weather_main_Rain,
            payload.weather_main_Smoke, payload.weather_main_Snow, payload.weather_main_Squall,
            payload.weather_main_Thunderstorm
        ]]
        
        # Execute the model inference step using the unpacked model object
        prediction = traffic_model.predict(features)[0]
        
        return {"predicted_traffic_volume": float(prediction)}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Inference pipeline execution error: {str(e)}")


# ==========================================
# TASK 3: REFACTOR FACTORY LOGIC FOR CRUD
# ==========================================
def _guard(fn, *args, **kwargs):
    """
    Wraps a backend call, translating a dead Mongo connection into a clean 503
    instead of a raw stack trace.
    """
    try:
        return fn(*args, **kwargs)
    except PyMongoError as err:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {err}")


def make_router(backend, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.post("/records", response_model=RecordOut, status_code=201, summary="Create a record")
    def create_record(res: RecordIn) -> RecordOut:
        return _guard(backend.create, res)

    @router.get("/records/latest", response_model=RecordOut, summary="Latest record (time-series query)")
    def latest_record() -> RecordOut:
        rec = _guard(backend.get_latest)
        if rec is None:
            raise HTTPException(status_code=404, detail="No records found")
        return rec

    @router.get("/records", response_model=List[RecordOut], summary="List / records by date range (time-series query)")
    def list_records(
        start: Optional[datetime] = Query(None, description="Range start (ISO 8601)"),
        end: Optional[datetime] = Query(None, description="Range end (ISO 8601)"),
        limit: int = Query(1000, ge=1, le=10000),
    ) -> List[RecordOut]:
        lo = start or datetime(1970, 1, 1)
        hi = end or datetime(2100, 1, 1)
        return _guard(backend.get_range, lo, hi, limit)

    @router.get("/records/{record_id}", response_model=RecordOut, summary="Get one record by id")
    def get_record(record_id: str) -> RecordOut:
        rec = _guard(backend.get_by_id, record_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return rec

    @router.put("/records/{record_id}", response_model=RecordOut, summary="Update a record")
    def update_record(record_id: str, res: RecordIn) -> RecordOut:
        updated = _guard(backend.update, record_id, res)
        if updated is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return updated

    @router.delete("/records/{record_id}", status_code=200, summary="Delete a record")
    def delete_record(record_id: str):
        if not _guard(backend.delete, record_id):
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": record_id}

    return router


@app.get("/", tags=["meta"], summary="Health check + endpoint index")
def root():
    return {
        "service": "Metro Traffic Volume API",
        "backends": ["sql", "mongo"],
        "docs": "/docs",
        "endpoints": {
            "create": "POST /{backend}/records",
            "latest": "GET /{backend}/records/latest",
            "date_range": "GET /{backend}/records?start=...&end=...",
            "read": "GET /{backend}/records/{id}",
            "update": "PUT /{backend}/records/{id}",
            "delete": "DELETE /{backend}/records/{id}",
            "predict": "POST /predict/"
        }
    }


# Include your generated routing tables
app.include_router(make_router(sql_backend, "/sql", "SQL (SQLite)"))
app.include_router(make_router(mongo_backend, "/mongo", "MongoDB"))

# Include your updated Task 4 machine learning prediction router
app.include_router(predict_router)