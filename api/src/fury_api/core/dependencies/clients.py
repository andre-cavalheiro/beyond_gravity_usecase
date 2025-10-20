from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Request

from fury_api.lib.usgs_client import USGSEarthquakeClient

from fury_api.core.factories.clients_factory import ClientsFactory

async def get_usgs_client(request: Request) -> AsyncGenerator[USGSEarthquakeClient, None]:
    """Get a new usgs client."""
    yield ClientsFactory.get_usgs_client()
