from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import cv2
import numpy as np
import requests

from fury_api.lib.service import GenericService
from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.domain.users.models import User

if TYPE_CHECKING:
    pass

__all__ = ["ImageTransformationsService"]


class ImageTransformationsService(GenericService):
    def __init__(
        self,
        uow: UnitOfWork | None = None,
        *,
        auth_user: User | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.uow = uow
        self.auth_user = auth_user

    async def generate_ciim_geo_heightmap_png(
        self,
        image_url: str,
        *,
        gradient_blend: float = 0.35,
    ) -> bytes:
        return await asyncio.to_thread(
            self._transform_url_to_heightmap_png_bytes,
            image_url,
            gradient_blend=gradient_blend,
        )

    async def generate_ciim_geo_heightmap_png_from_path(
        self,
        image_path: str | Path,
        *,
        gradient_blend: float = 0.35,
    ) -> bytes:
        """
        Local-path variant useful for CLI tooling/tests.
        """
        return await asyncio.to_thread(
            self._transform_path_to_heightmap_png_bytes,
            image_path,
            gradient_blend=gradient_blend,
        )

    def _fetch_bytes(self, url: str, timeout: int = 30) -> bytes:
        """
        Download the raw bytes from a URL with a few safety checks.
        No caching - always fetch fresh.
        """
        scheme = urlparse(url).scheme.lower()
        if scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme: {scheme}")

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

        return content


    def _decode_image_gray(self, image_bytes: bytes) -> np.ndarray:
        """
        Decode bytes -> grayscale image (uint8 HxW).
        """
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Could not decode image bytes")
        return img


    def _sobel_heightmap_uint8(self, gray: np.ndarray, *, gradient_blend: float = 0.35) -> np.ndarray:
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


    def _encode_png_bytes(self, img_uint8: np.ndarray) -> bytes:
        """
        Encode uint8 image -> PNG bytes.
        """
        ok, buf = cv2.imencode(".png", img_uint8)
        if not ok:
            raise ValueError("PNG encoding failed")
        return buf.tobytes()


    def _transform_url_to_heightmap_png_bytes(self, url: str, *, gradient_blend: float = 0.35) -> bytes:
        """
        Full pipeline:
        URL -> bytes -> grayscale -> Sobel-based heightmap (uint8) -> PNG bytes
        """
        raw = self._fetch_bytes(url)
        return self._raw_bytes_to_heightmap_png_bytes(raw, gradient_blend=gradient_blend)

    def _transform_path_to_heightmap_png_bytes(
        self,
        image_path: str | Path,
        *,
        gradient_blend: float = 0.35,
    ) -> bytes:
        path = Path(image_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f"Image path not found: {path}")

        max_bytes = 15 * 1024 * 1024
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise ValueError(f"File too large: {len(raw)} bytes")

        return self._raw_bytes_to_heightmap_png_bytes(raw, gradient_blend=gradient_blend)

    def _raw_bytes_to_heightmap_png_bytes(self, raw: bytes, *, gradient_blend: float) -> bytes:
        gray = self._decode_image_gray(raw)
        height_img = self._sobel_heightmap_uint8(gray, gradient_blend=gradient_blend)
        return self._encode_png_bytes(height_img)
