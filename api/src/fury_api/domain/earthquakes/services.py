from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import cv2
import numpy as np
import requests

from .models import Earthquake
from fury_api.lib.service import SqlService, with_uow
from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.domain.users.models import User
from fury_api.lib.model_filters import Filter, Sort
from fury_api.lib.pagination import CursorPage

if TYPE_CHECKING:
    pass

__all__ = ["EarthquakesService"]

class EarthquakesService(SqlService[Earthquake]):
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        auth_user: User | None = None,
        **kwargs,
    ):
        super().__init__(Earthquake, uow, auth_user=auth_user, **kwargs)
