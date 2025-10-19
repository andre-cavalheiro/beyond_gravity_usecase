import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx

from fury_api.core.factories import UnitOfWorkFactory
from fury_api.domain.earthquakes.models import Earthquake
from fury_api.domain.earthquakes.services import EarthquakesService

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def _parse_epoch_milliseconds(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _to_str(value: Any, *, max_length: Optional[int] = None) -> Optional[str]:
    if value in (None, ""):
        return None
    stringified = str(value)
    if max_length is not None:
        return stringified[:max_length]
    return stringified


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    try:
        numeric = int(float(value))
        return bool(numeric)
    except (TypeError, ValueError):
        return None


async def fetch_earthquake_features(
    start_date: str,
    end_date: str,
    *,
    min_magnitude: float | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
    }
    if min_magnitude is not None:
        params["minmagnitude"] = str(min_magnitude)
    if limit is not None:
        params["limit"] = str(limit)

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.get(USGS_ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json()

    features = payload.get("features", [])
    if not isinstance(features, list):
        return []
    return features


def _extract_ciim_geo_image_url(detail_payload: dict[str, Any]) -> Optional[str]:
    properties = detail_payload.get("properties")
    if not isinstance(properties, dict):
        return None

    products = properties.get("products")
    if not isinstance(products, dict):
        return None

    dyfi_products = products.get("dyfi")
    if not isinstance(dyfi_products, list):
        return None

    fallback_url: Optional[str] = None
    for dyfi_product in dyfi_products:
        if not isinstance(dyfi_product, dict):
            continue

        contents = dyfi_product.get("contents")
        if not isinstance(contents, dict):
            continue

        for key, value in contents.items():
            if not isinstance(key, str):
                continue

            key_lower = key.lower()
            if not key_lower.endswith(".jpg"):
                continue

            if not isinstance(value, dict):
                continue

            url_str = _to_str(value.get("url"), max_length=1024)
            if url_str is None:
                continue

            if key_lower.endswith("ciim_geo.jpg"):
                return url_str

            if fallback_url is None:
                fallback_url = url_str

    return fallback_url


async def fetch_ciim_geo_image_url(
    client: httpx.AsyncClient,
    detail_url: Optional[str],
) -> Optional[str]:
    if not detail_url:
        return None

    try:
        response = await client.get(detail_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    return _extract_ciim_geo_image_url(payload)


def feature_to_model(feature: dict[str, Any]) -> Earthquake | None:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates: Iterable[Any] = geometry.get("coordinates") or []
    coord_list = list(coordinates)

    title = properties.get("title")
    if title in (None, ""):
        return None

    data: dict[str, Any] = {
        "external_id": _to_str(feature.get("id"), max_length=32),
        "magnitude": _to_float(properties.get("mag")),
        "magnitude_type": _to_str(properties.get("magType"), max_length=16),
        "place": _to_str(properties.get("place"), max_length=255),
        "status": _to_str(properties.get("status"), max_length=32),
        "event_type": _to_str(properties.get("type"), max_length=32),
        "title": _to_str(title, max_length=255),
        "detail_url": _to_str(properties.get("detail"), max_length=512),
        "info_url": _to_str(properties.get("url"), max_length=512),
        "significance": _to_int(properties.get("sig")),
        "tsunami": _to_bool(properties.get("tsunami")),
        "felt_reports": _to_int(properties.get("felt")),
        "cdi": _to_float(properties.get("cdi")),
        "mmi": _to_float(properties.get("mmi")),
        "alert": _to_str(properties.get("alert"), max_length=16),
        "station_count": _to_int(properties.get("nst")),
        "minimum_distance": _to_float(properties.get("dmin")),
        "rms": _to_float(properties.get("rms")),
        "gap": _to_float(properties.get("gap")),
        "occurred_at": _parse_epoch_milliseconds(properties.get("time")),
        "ecternal_updated_at": _parse_epoch_milliseconds(properties.get("updated")),
        "longitude": _to_float(coord_list[0]) if len(coord_list) > 0 else None,
        "latitude": _to_float(coord_list[1]) if len(coord_list) > 1 else None,
        "depth_km": _to_float(coord_list[2]) if len(coord_list) > 2 else None,
    }

    return Earthquake(**data)


async def persist_earthquakes(
    earthquakes: list[Earthquake],
    *,
    organization_id: int | None = None,
) -> int:
    if not earthquakes:
        return 0

    uow = UnitOfWorkFactory.get_uow(organization_id=organization_id)
    async with uow:
        service = EarthquakesService(uow, auth_user=None)
        await service.create_items(earthquakes)
    return len(earthquakes)


async def run_ingestion(
    start_date: str,
    end_date: str,
    *,
    organization_id: int | None = None,
    min_magnitude: float | None = None,
    limit: int | None = None,
) -> int:
    features = await fetch_earthquake_features(
        start_date,
        end_date,
        min_magnitude=min_magnitude,
        limit=limit,
    )

    seen_ids: set[str | None] = set()
    earthquakes: list[Earthquake] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as detail_client:
        for feature in features:
            earthquake = feature_to_model(feature)
            if earthquake is None:
                continue
            if earthquake.external_id in seen_ids:
                continue

            seen_ids.add(earthquake.external_id)

            image_url = await fetch_ciim_geo_image_url(detail_client, earthquake.detail_url)
            if image_url is not None:
                earthquake.ciim_geo_image_url = image_url

            earthquakes.append(earthquake)

    return await persist_earthquakes(
        earthquakes,
        organization_id=organization_id,
    )


async def main(args: argparse.Namespace) -> None:
    created = await run_ingestion(
        args.start_date,
        args.end_date,
        organization_id=args.organization_id,
        min_magnitude=args.min_magnitude,
        limit=args.limit,
    )
    print(f"Ingested {created} earthquake records for {args.start_date} -> {args.end_date}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch USGS earthquakes and persist them into the database")
    parser.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("end_date", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--organization-id",
        type=int,
        help="Optional tenant/organization identifier",
    )
    parser.add_argument(
        "--min-magnitude",
        type=float,
        help="Optional minimum magnitude filter to apply to the USGS query",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit for number of events fetched from the USGS feed",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    asyncio.run(main(parser.parse_args()))
