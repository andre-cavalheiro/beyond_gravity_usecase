from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime
from typing import Optional

from sqlmodel import Field
from fury_api.lib.db.base import BaseSQLModel, BigIntIDModel

__all__ = ["Earthquake", "EarthquakeCreate", "EarthquakeRead", "IngestPayload", "IngestResponse"]

class EarthquakeBase(BaseSQLModel):
    external_id: Optional[str] = Field(
        default=None,
        sa_type=sa.String(length=32),
        index=True,
        unique=True,
        description="Provider-specific identifier, e.g. 'us6000rhpf'.",
    )
    magnitude: Optional[float] = Field(default=None, sa_type=sa.Float)
    magnitude_type: Optional[str] = Field(default=None, sa_type=sa.String(length=16))
    place: Optional[str] = Field(default=None, sa_type=sa.String(length=255))
    status: Optional[str] = Field(default=None, sa_type=sa.String(length=32))
    event_type: Optional[str] = Field(
        default=None,
        sa_type=sa.String(length=32),
        description="USGS event type, e.g. 'earthquake'.",
    )
    title: str = Field(sa_type=sa.String(length=255))
    detail_url: Optional[str] = Field(default=None, sa_type=sa.String(length=512))
    info_url: Optional[str] = Field(default=None, sa_type=sa.String(length=512))
    ciim_geo_image_url: Optional[str] = Field(default=None, sa_type=sa.String(length=1024))
    
    significance: Optional[int] = Field(default=None, sa_type=sa.Integer)
    tsunami: Optional[bool] = Field(default=None, sa_type=sa.Boolean)
    felt_reports: Optional[int] = Field(default=None, sa_type=sa.Integer)
    cdi: Optional[float] = Field(default=None, sa_type=sa.Float)
    mmi: Optional[float] = Field(default=None, sa_type=sa.Float)
    alert: Optional[str] = Field(default=None, sa_type=sa.String(length=16))
    station_count: Optional[int] = Field(default=None, sa_type=sa.Integer, description="Number of stations (NST).")
    minimum_distance: Optional[float] = Field(default=None, sa_type=sa.Float, description="Minimum distance (dmin).")
    rms: Optional[float] = Field(default=None, sa_type=sa.Float)
    gap: Optional[float] = Field(default=None, sa_type=sa.Float)
    occurred_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True)),
        description="Event origin time.",
    )
    external_updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True)),
        description="Last provider update timestamp.",
    )
    latitude: Optional[float] = Field(default=None, sa_type=sa.Float)
    longitude: Optional[float] = Field(default=None, sa_type=sa.Float)
    depth_km: Optional[float] = Field(default=None, sa_type=sa.Float)


class Earthquake(EarthquakeBase, BigIntIDModel, table=True):
    __tablename__: str = "earthquake"
    __id_attr__ = "id"

    id: int = Field(primary_key=True, sa_type=sa.BigInteger, sa_column_kwargs={"autoincrement": True})

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class EarthquakeRead(EarthquakeBase):
    class Config:
        """
        Ignore extra fields.
        Allows us to use EarthquakeRead as a response model and using Earthquake as model in the controller.
        """

        extra = "ignore"

    id: int
# Pydantic picks remaining fields from EarthquakeBase.


class EarthquakeCreate(EarthquakeBase):
    title: str = Field()

class IngestPayload(BaseSQLModel):
    start_date: str
    end_date: str
    min_magnitude: Optional[float] = None
    limit: Optional[int] = None
    search_ciim_geo_image_url: bool = False
    enforce_ciim_geo_image_url: bool = True

class IngestResponse(BaseSQLModel):
    count: int
    
    