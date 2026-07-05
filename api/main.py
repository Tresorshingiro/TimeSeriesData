"""Task 3 — FastAPI application.

Exposes the same CRUD + time-series endpoints twice: once for the SQL backend
(prefix /sql) and once for the MongoDB backend (prefix /mongo). Both routers are
generated from one factory so the two backends are guaranteed to behave
identically at the API layer.

Run:  uvicorn api.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from datetime import datetime
from types import ModuleType
from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pymongo.errors import PyMongoError

from . import mongo_backend, sql_backend
from .models import RecordIn, RecordOut

app = FastAPI(
    title="Metro Traffic Volume API",
    description="Task 3 — CRUD and time-series query endpoints over SQL (SQLite) "
    "and MongoDB backends for the Metro Interstate Traffic Volume dataset.",
    version="1.0.0",
)


def _guard(fn, *args, **kwargs):
    """Run a backend call, translating a dead Mongo connection into a clean 503
    instead of a 500 stack trace."""
    try:
        return fn(*args, **kwargs)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


def make_router(backend: ModuleType, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.post("/records", response_model=RecordOut, status_code=201,
                 summary="Create a record")
    def create_record(rec: RecordIn) -> RecordOut:
        return _guard(backend.create, rec)

    @router.get("/records/latest", response_model=RecordOut,
                summary="Latest record (time-series query)")
    def latest_record() -> RecordOut:
        rec = _guard(backend.get_latest)
        if rec is None:
            raise HTTPException(status_code=404, detail="No records found")
        return rec

    @router.get("/records", response_model=List[RecordOut],
                summary="List / records by date range (time-series query)")
    def list_records(
        start: Optional[datetime] = Query(None, description="Range start (ISO 8601)"),
        end: Optional[datetime] = Query(None, description="Range end (ISO 8601)"),
        limit: int = Query(1000, ge=1, le=10000),
    ) -> List[RecordOut]:
        lo = start or datetime(1970, 1, 1)
        hi = end or datetime(2100, 1, 1)
        return _guard(backend.get_range, lo, hi, limit)

    @router.get("/records/{record_id}", response_model=RecordOut,
                summary="Get one record by id")
    def get_record(record_id: str) -> RecordOut:
        rec = _guard(backend.get_by_id, record_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return rec

    @router.put("/records/{record_id}", response_model=RecordOut,
                summary="Update a record")
    def update_record(record_id: str, rec: RecordIn) -> RecordOut:
        updated = _guard(backend.update, record_id, rec)
        if updated is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return updated

    @router.delete("/records/{record_id}", status_code=200,
                   summary="Delete a record")
    def delete_record(record_id: str) -> dict:
        if not _guard(backend.delete, record_id):
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": record_id}

    return router


@app.get("/", tags=["meta"], summary="Health check + endpoint index")
def root() -> dict:
    return {
        "service": "Metro Traffic Volume API",
        "backends": ["sql", "mongo"],
        "docs": "/docs",
        "endpoints": {
            "create": "POST   /{backend}/records",
            "latest": "GET    /{backend}/records/latest",
            "date_range": "GET /{backend}/records?start=&end=",
            "read": "GET    /{backend}/records/{id}",
            "update": "PUT    /{backend}/records/{id}",
            "delete": "DELETE /{backend}/records/{id}",
        },
    }


app.include_router(make_router(sql_backend, "/sql", "SQL (SQLite)"))
app.include_router(make_router(mongo_backend, "/mongo", "MongoDB"))
