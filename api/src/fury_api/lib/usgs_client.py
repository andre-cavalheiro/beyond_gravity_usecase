from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx

from fury_api.domain.earthquakes.models import Earthquake

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class USGSEarthquakeClient:
    def __init__(
        self,
        *,
        base_url: str = USGS_ENDPOINT,
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> "USGSEarthquakeClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("USGSEarthquakeClient must be used within an async context manager")
        return self._client

    async def fetch_earthquake_features(
        self,
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

        response = await self._http_client.get(self._base_url, params=params)
        response.raise_for_status()
        payload = response.json()

        features = payload.get("features", [])
        if not isinstance(features, list):
            return []
        return features

    async def fetch_ciim_geo_image_url(self, detail_url: Optional[str]) -> Optional[str]:
        if not detail_url:
            return None

        try:
            response = await self._http_client.get(detail_url)
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

    async def fetch_earthquakes(
        self,
        start_date: str,
        end_date: str,
        *,
        min_magnitude: float | None = None,
        limit: int | None = None,
        search_ciim_geo_image_url: bool = False,
    ) -> list[Earthquake]:
        features = await self.fetch_earthquake_features(
            start_date,
            end_date,
            min_magnitude=min_magnitude,
            limit=limit,
        )

        earthquakes: list[Earthquake] = []
        seen_ids: set[str | None] = set()
        for feature in features:
            earthquake = self.feature_to_earthquake(feature)
            if earthquake is None:
                continue
            if earthquake.external_id in seen_ids:
                continue
            seen_ids.add(earthquake.external_id)

            if search_ciim_geo_image_url:
                image_url = await self.fetch_ciim_geo_image_url(earthquake.detail_url)
                if image_url is not None:
                    earthquake.ciim_geo_image_url = image_url

            earthquakes.append(earthquake)

        return earthquakes

    @staticmethod
    def feature_to_earthquake(feature: dict[str, Any]) -> Earthquake | None:
        return _feature_to_earthquake(feature)


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


def _feature_to_earthquake(feature: dict[str, Any]) -> Earthquake | None:
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
        "external_updated_at": _parse_epoch_milliseconds(properties.get("updated")),
        "longitude": _to_float(coord_list[0]) if len(coord_list) > 0 else None,
        "latitude": _to_float(coord_list[1]) if len(coord_list) > 1 else None,
        "depth_km": _to_float(coord_list[2]) if len(coord_list) > 2 else None,
    }

    return Earthquake(**data)


def _to_str(value: Any, *, max_length: Optional[int] = None) -> Optional[str]:
    if value in (None, ""):
        return None
    stringified = str(value)
    if max_length is not None:
        return stringified[:max_length]
    return stringified


def _parse_epoch_milliseconds(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


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
