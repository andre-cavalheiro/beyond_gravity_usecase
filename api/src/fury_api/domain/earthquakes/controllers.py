import asyncio
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status

from fury_api.domain import paths
from fury_api.domain.users.models import User
from fury_api.core.dependencies import (
    FiltersAndSortsParser,
    ServiceType,
    get_models_filters_parser_factory,
    get_service,
    get_uow_any_tenant,
    get_uow_tenant,
    get_uow_tenant_ro,
    get_usgs_client,
)
from . import exceptions
from .models import (
    Earthquake,
    EarthquakeCreate,
    EarthquakeRead,
    IngestPayload,
    IngestResponse,
)
from fury_api.core.security import get_current_user
from fury_api.lib.db.base import Identifier
from fury_api.lib.pagination import CursorPage
from .services import EarthquakesService
from fury_api.lib.model_filters import ModelFilterAndSortDefinition, get_default_ops_for_type
from fury_api.domain.image_transformations.services import ImageTransformationsService
from fury_api.lib.usgs_client import USGSEarthquakeClient

earthquake_router = APIRouter()

EARTHQUAKES_FILTERS_DEFINITION = ModelFilterAndSortDefinition(
    model=Earthquake,
    allowed_filters={
        "id": get_default_ops_for_type(Identifier),
        "title": get_default_ops_for_type(str),
        "external_id": get_default_ops_for_type(str),
        "magnitude": get_default_ops_for_type(float),
        "magnitude_type": get_default_ops_for_type(str),
        "place": get_default_ops_for_type(str),
        "status": get_default_ops_for_type(str),
        "event_type": get_default_ops_for_type(str),
        "detail_url": get_default_ops_for_type(str),
        "info_url": get_default_ops_for_type(str),
        "significance": get_default_ops_for_type(int),
        "tsunami": get_default_ops_for_type(bool),
        "felt_reports": get_default_ops_for_type(int),
        "cdi": get_default_ops_for_type(float),
        "mmi": get_default_ops_for_type(float),
        "alert": get_default_ops_for_type(str),
        "station_count": get_default_ops_for_type(int),
        "minimum_distance": get_default_ops_for_type(float),
        "rms": get_default_ops_for_type(float),
        "gap": get_default_ops_for_type(float),
        "occurred_at": get_default_ops_for_type(datetime),
        "external_updated_at": get_default_ops_for_type(datetime),
        "latitude": get_default_ops_for_type(float),
        "longitude": get_default_ops_for_type(float),
        "depth_km": get_default_ops_for_type(float),
        "created_at": get_default_ops_for_type(datetime),
        "last_updated_at": get_default_ops_for_type(datetime),
    },
    allowed_sorts={
        "id",
        "title",
        "external_id",
        "magnitude",
        "magnitude_type",
        "place",
        "status",
        "event_type",
        "significance",
        "tsunami",
        "felt_reports",
        "cdi",
        "mmi",
        "alert",
        "station_count",
        "minimum_distance",
        "rms",
        "gap",
        "occurred_at",
        "external_updated_at",
        "latitude",
        "longitude",
        "depth_km",
        "created_at",
        "last_updated_at",
    },
)

@earthquake_router.get(paths.EARTHQUAKES, response_model=CursorPage[EarthquakeRead])
async def get_items(
    earthquake_service: Annotated[EarthquakesService, Depends(get_service(ServiceType.EARTHQUAKES, read_only=True, uow=Depends(get_uow_any_tenant)))],
    filters_parser: Annotated[FiltersAndSortsParser, Depends(get_models_filters_parser_factory(EARTHQUAKES_FILTERS_DEFINITION))],
) -> CursorPage[EarthquakeRead]:
    return await earthquake_service.get_items_paginated(
        model_filters=filters_parser.filters, model_sorts=filters_parser.sorts
    )


@earthquake_router.get(paths.EARTHQUAKES_ID, response_model=EarthquakeRead)
async def get_item(
    id_: int,
    earthquake_service: Annotated[
        EarthquakesService,
        Depends(get_service(ServiceType.EARTHQUAKES, read_only=True, uow=Depends(get_uow_any_tenant))),
    ],
) -> EarthquakeRead:
    earthquake = await earthquake_service.get_item(id_)
    if not earthquake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Earthquake not found")
    return earthquake

@earthquake_router.get(paths.EARTHQUAKES_ID_IMAGE, response_model=bytes)
async def get_ciim_geo_3d_image(
    id_: int,
    earthquake_service: Annotated[EarthquakesService, Depends(get_service(ServiceType.EARTHQUAKES, read_only=True, uow=Depends(get_uow_any_tenant)))],
    image_transformation_service: Annotated[ImageTransformationsService, Depends(get_service(ServiceType.IMAGE_TRANSFORMATIONS, uow=Depends(get_uow_any_tenant)))],
    min_delay: Optional[float] = 10,
) -> bytes:
    earthquake = await earthquake_service.get_item(id_)
    if not earthquake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Earthquake not found")

    if not earthquake.ciim_geo_image_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIIM geo image not found")

    try:
        png_bytes = await image_transformation_service.generate_ciim_geo_heightmap_png(
            earthquake.ciim_geo_image_url
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if min_delay and min_delay > 0:
        await asyncio.sleep(min_delay)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@earthquake_router.post(paths.EARTHQUAKES_INGEST, response_model=IngestResponse)
async def ingest_earthquakes_from_usgs(
    ingest_payload: IngestPayload,
    earthquake_service: Annotated[EarthquakesService, Depends(get_service(ServiceType.EARTHQUAKES, read_only=False, uow=Depends(get_uow_any_tenant)))],
    usgs_client: Annotated[USGSEarthquakeClient, Depends(get_usgs_client)],
) -> IngestResponse:
    async with usgs_client:
        earthquakes = await usgs_client.fetch_earthquakes(
            ingest_payload.start_date,
            ingest_payload.end_date,
            min_magnitude=ingest_payload.min_magnitude,
            limit=ingest_payload.limit,
            search_ciim_geo_image_url=ingest_payload.search_ciim_geo_image_url,
            enforce_ciim_geo_image_url=ingest_payload.enforce_ciim_geo_image_url,
        )
    
    if not earthquakes:
        return IngestResponse(count=0)
    
    await earthquake_service.create_items(earthquakes)
    return IngestResponse(count=len(earthquakes))

