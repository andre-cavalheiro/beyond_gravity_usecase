from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import ExitStack
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi_pagination.api import set_page, set_params

from fury_api.lib.factories import UnitOfWorkFactory
from fury_api.domain.earthquakes.models import Earthquake
from fury_api.domain.earthquakes.services import EarthquakesService
from fury_api.domain.image_transformations.services import ImageTransformationsService
from fury_api.lib.usgs_client import USGSEarthquakeClient
from fury_api.lib.model_filters import Filter, FilterOp, Sort
from fury_api.lib.pagination import CursorPage, CursorParams

DEFAULT_DELAY_SECONDS = 10.5


@dataclass
class IngestArgs:
    start_date: str
    end_date: str
    min_magnitude: Optional[float]
    limit: Optional[int]
    search_ciim_geo_image_url: bool


@dataclass
class TransformArgs:
    source: str
    output: Optional[str]
    gradient_blend: float
    delay_seconds: float


@dataclass
class ListArgs:
    limit: int
    after_id: Optional[int] = None


@dataclass
class GetArgs:
    earthquake_id: int


async def _handle_ingest(args: IngestArgs) -> int:
    async with USGSEarthquakeClient() as usgs_client:
        earthquakes = await usgs_client.fetch_earthquakes(
            args.start_date,
            args.end_date,
            min_magnitude=args.min_magnitude,
            limit=args.limit,
            search_ciim_geo_image_url=args.search_ciim_geo_image_url,
        )

    if not earthquakes:
        print(f"No earthquakes found for {args.start_date} -> {args.end_date}")
        return 0

    uow = UnitOfWorkFactory.get_uow()
    async with uow:
        service = EarthquakesService(uow, auth_user=None)
        await service.create_items(earthquakes)
        print(f"Ingested {len(earthquakes)} earthquake records for {args.start_date} -> {args.end_date}")
    return len(earthquakes)


async def _handle_transform(args: TransformArgs) -> Path:
    service = ImageTransformationsService()
    parsed = urlparse(args.source)
    is_url = parsed.scheme in {"http", "https"}

    if is_url:
        png_bytes = await service.generate_ciim_geo_heightmap_png(
            args.source,
            gradient_blend=args.gradient_blend,
        )
        source_name = Path(parsed.path or "remote_image").stem or "remote_image"
    else:
        png_bytes = await service.generate_ciim_geo_heightmap_png_from_path(
            args.source,
            gradient_blend=args.gradient_blend,
        )
        source_name = Path(args.source).stem or "image"

    delay = max(args.delay_seconds, 10.01)
    print(f"Simulating heavy processing for {delay:.1f}s...")
    await asyncio.sleep(delay)

    output_path = _resolve_output_path(args.output, source_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(png_bytes)
    print(f"Heightmap saved to {output_path}")
    return output_path


async def _handle_list(args: ListArgs) -> list[Earthquake]:
    limit = max(args.limit, 1)
    uow = UnitOfWorkFactory.get_uow(read_only=True)
    service = EarthquakesService(uow, auth_user=None)

    filters: list[Filter] = []
    if args.after_id is not None:
        filters.append(Filter(field="id", op=FilterOp.GT, value=args.after_id, field_type=int))

    sorts = [Sort(field="id", direction="asc")]

    with ExitStack() as stack:
        stack.enter_context(set_page(CursorPage))
        stack.enter_context(set_params(CursorParams(size=limit, cursor=None, include_total=False)))
        page = await service.get_items_paginated(model_filters=filters, model_sorts=sorts)

    earthquakes: list[Earthquake] = list(page.items)[:limit]

    if not earthquakes:
        print("No earthquakes found for the provided criteria.")
        return []

    header = f"{'ID':>6}  {'External ID':<16}  {'Title':<40}  Location"
    print(header)
    print("-" * len(header))
    for eq in earthquakes:
        external_id = (eq.external_id or "-")[:16]
        title = (eq.title or "-")[:40]
        location = _format_location(eq)
        print(f"{eq.id:>6}  {external_id:<16}  {title:<40}  {location}")

    if len(earthquakes) >= limit:
        last_id = earthquakes[-1].id
        print("\nHint: fetch the next page with --after-id", last_id)
    return earthquakes


async def _handle_get(args: GetArgs) -> Earthquake | None:
    uow = UnitOfWorkFactory.get_uow(read_only=True)
    service = EarthquakesService(uow, auth_user=None)
    earthquake = await service.get_item(args.earthquake_id)

    if earthquake is None:
        print(f"Earthquake with id {args.earthquake_id} not found.")
        return None

    data = _model_to_dict(earthquake)
    for key in sorted(data):
        print(f"{key}: {data[key]}")
    return earthquake


def _resolve_output_path(explicit: Optional[str], source_name: str) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name}_heightmap_{timestamp}.png"
    return Path(os.getcwd()) / filename


def _format_location(eq: Earthquake) -> str:
    if eq.place:
        return eq.place

    lat = f"{eq.latitude:.3f}" if eq.latitude is not None else "?"
    lon = f"{eq.longitude:.3f}" if eq.longitude is not None else "?"
    return f"{lat}, {lon}"


def _model_to_dict(model: Earthquake) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


async def main(args: argparse.Namespace) -> int:
    if args.command == "ingest-earthquakes":
        ingest_args = IngestArgs(
            start_date=args.start_date,
            end_date=args.end_date,
            min_magnitude=args.min_magnitude,
            limit=args.limit,
            search_ciim_geo_image_url=args.search_ciim_geo_image_url,
        )
        await _handle_ingest(ingest_args)
        return 0

    if args.command == "transform-image":
        transform_args = TransformArgs(
            source=args.source,
            output=args.output,
            gradient_blend=args.gradient_blend,
            delay_seconds=args.delay_seconds,
        )
        await _handle_transform(transform_args)
        return 0

    if args.command == "list-earthquakes":
        list_args = ListArgs(
            limit=args.limit,
            after_id=args.after_id,
        )
        await _handle_list(list_args)
        return 0

    if args.command == "get-earthquake":
        get_args = GetArgs(
            earthquake_id=args.earthquake_id,
        )
        await _handle_get(get_args)
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FURY utility CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest-earthquakes",
        help="Fetch USGS earthquakes and persist them into the database",
    )
    ingest_parser.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    ingest_parser.add_argument("end_date", help="End date (YYYY-MM-DD)")
    ingest_parser.add_argument(
        "--min-magnitude",
        type=float,
        help="Optional minimum magnitude filter to apply to the USGS query",
    )
    ingest_parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit for number of events fetched from the USGS feed",
    )
    ingest_parser.add_argument(
        "--search-ciim-geo-image-url",
        action="store_true",
        help="Whether to search for the CIIM geo image URL for each earthquake",
    )

    transform_parser = subparsers.add_parser(
        "transform-image",
        help="Generate a 3D-ready heightmap PNG from an image path or URL",
    )
    transform_parser.add_argument(
        "source",
        help="Input image path or URL",
    )
    transform_parser.add_argument(
        "--output",
        "-o",
        help="Where to store the processed PNG (defaults to current directory with timestamped name)",
    )
    transform_parser.add_argument(
        "--gradient-blend",
        type=float,
        default=0.35,
        help="Blend ratio between gradients and base intensity (default: 0.35)",
    )
    transform_parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Artificial processing delay to satisfy CLI spec (minimum enforced at >10s)",
    )

    list_parser = subparsers.add_parser(
        "list-earthquakes",
        help="List earthquakes stored in the database",
    )

    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of records to display (default: 20)",
    )
    list_parser.add_argument(
        "--after-id",
        type=int,
        help="Fetch earthquakes with an internal id greater than the provided value",
    )

    get_parser = subparsers.add_parser(
        "get-earthquake",
        help="Show all details for a single earthquake",
    )
    get_parser.add_argument(
        "earthquake_id",
        type=int,
        help="Internal earthquake identifier",
    )

    return parser


if __name__ == "__main__":
    parser = build_parser()
    asyncio.run(main(parser.parse_args()))
