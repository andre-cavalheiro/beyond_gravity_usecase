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
from fury_api.core.service import SqlService, with_uow
from fury_api.core.unit_of_work import UnitOfWork
from fury_api.domain.users.models import User
from fury_api.lib.model_filters import Filter, Sort
from fury_api.lib.pagination import CursorPage

if TYPE_CHECKING:
    pass

__all__ = ["EarthquakesService"]

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class EarthquakesService(SqlService[Earthquake]):
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        auth_user: User | None = None,
        **kwargs,
    ):
        super().__init__(Earthquake, uow, auth_user=auth_user, **kwargs)

    async def generate_ciim_geo_heightmap_png(
        self,
        image_url: str,
        *,
        gradient_blend: float = 0.35,
    ) -> bytes:
        return await asyncio.to_thread(
            transform_url_to_heightmap_png_bytes,
            image_url,
            gradient_blend=gradient_blend,
        )


def _cache_path_for(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.bin"


def fetch_bytes(url: str, timeout: int = 30, *, use_cache: bool = True) -> bytes:
    """
    Download the raw bytes from a URL with a few safety checks.
    """
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {scheme}")

    cache_path = _cache_path_for(url) if use_cache else None
    if cache_path and cache_path.exists():
        return cache_path.read_bytes()

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Failed to download image: {exc}") from exc

    ctype = resp.headers.get("Content-Type", "").lower()
    if "image" not in ctype and "octet-stream" not in ctype:
        raise ValueError(f"Unexpected content type: {ctype}")

    max_bytes = 15 * 1024 * 1024
    content = resp.content
    if len(content) > max_bytes:
        raise ValueError(f"File too large: {len(content)} bytes")

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(content)
    return content


def decode_image_gray(image_bytes: bytes) -> np.ndarray:
    """
    Decode bytes -> grayscale image (uint8 HxW).
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def sobel_heightmap_uint8(gray: np.ndarray, *, gradient_blend: float = 0.35) -> np.ndarray:
    """
    Generate a displacement-friendly heightmap by mixing Sobel gradients with base intensity.
    """
    if not 0.0 <= gradient_blend <= 1.0:
        raise ValueError("gradient_blend must be between 0.0 and 1.0")

    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.0)
    grad_x = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)

    mag_norm = cv2.normalize(magnitude, None, 0.0, 1.0, cv2.NORM_MINMAX)
    base_norm = blurred.astype(np.float32) / 255.0

    height_map = ((1.0 - gradient_blend) * mag_norm) + (gradient_blend * base_norm)
    height_uint8 = cv2.normalize(height_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return cv2.GaussianBlur(height_uint8, (0, 0), sigmaX=0.5)


def encode_png_bytes(img_uint8: np.ndarray) -> bytes:
    """
    Encode uint8 image -> PNG bytes.
    """
    ok, buf = cv2.imencode(".png", img_uint8)
    if not ok:
        raise ValueError("PNG encoding failed")
    return buf.tobytes()


def transform_url_to_heightmap_png_bytes(url: str, *, gradient_blend: float = 0.35) -> bytes:
    """
    Full pipeline:
      URL -> bytes -> grayscale -> Sobel-based heightmap (uint8) -> PNG bytes
    """
    raw = fetch_bytes(url)
    gray = decode_image_gray(raw)
    height_img = sobel_heightmap_uint8(gray, gradient_blend=gradient_blend)
    return encode_png_bytes(height_img)
