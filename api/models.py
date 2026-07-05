"""Pydantic request/response models.

A single, denormalized record shape is used for BOTH backends so that the SQL
and MongoDB endpoints accept and return identical JSON. This makes the two
implementations directly comparable (a grading requirement) and keeps clients
backend-agnostic.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecordIn(BaseModel):
    """Body for POST (create) and PUT (full update)."""

    date_time: datetime = Field(
        ..., description="Observation timestamp (ISO 8601, e.g. 2013-06-16T08:00:00)"
    )
    weather_main: str = Field(..., examples=["Clouds"])
    weather_description: str = Field(..., examples=["scattered clouds"])
    temp_kelvin: float = Field(..., examples=[290.0])
    rain_1h: float = Field(0.0, ge=0)
    snow_1h: float = Field(0.0, ge=0)
    clouds_all: int = Field(..., ge=0, le=100)
    traffic_volume: int = Field(..., ge=0)
    station_id: str = Field("ATR-301")
    holiday: Optional[str] = Field(
        None, description="Holiday name if the day is a holiday, else null"
    )


class RecordOut(RecordIn):
    """Response shape: the input fields plus the backend-assigned id."""

    id: str = Field(..., description="Record id (integer for SQL, ObjectId hex for Mongo)")
