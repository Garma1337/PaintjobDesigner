# coding: utf-8

from pathlib import Path

import numpy as np
from PIL import Image


class PreviewImageWriter:
    """Saves a captured RGBA viewer frame as PNG, JPEG or WebP.

    The format is picked from the target path's extension. JPEG
    has no alpha channel, so the frame is flattened onto
    `jpeg_background` first.
    """

    FORMATS: dict[str, str] = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".webp": "WEBP",
    }

    JPEG_QUALITY = 95
    WEBP_QUALITY = 95
    SPECK_WINDOW = 5
    SPECK_MIN_PIXELS = 5

    @staticmethod
    def visible_bounds(alpha: np.ndarray) -> tuple[int, int, int, int] | None:
        """(left, top, right, bottom) of the visible pixels, ignoring specks."""
        visible = alpha > 0
        if not visible.any():
            return None

        window = PreviewImageWriter.SPECK_WINDOW
        pad = window // 2
        padded = np.pad(visible.astype(np.int32), ((pad + 1, pad), (pad + 1, pad)))
        totals = padded.cumsum(axis=0).cumsum(axis=1)
        counts = (
            totals[window:, window:] - totals[:-window, window:]
            - totals[window:, :-window] + totals[:-window, :-window]
        )

        solid = visible & (counts >= PreviewImageWriter.SPECK_MIN_PIXELS)
        if not solid.any():
            solid = visible

        rows = np.flatnonzero(solid.any(axis=1))
        cols = np.flatnonzero(solid.any(axis=0))
        return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1

    def write(
        self,
        rgba: bytes,
        width: int,
        height: int,
        path: Path,
        jpeg_background: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Width/height must be positive, got {width}x{height}")

        image_format = self.FORMATS.get(path.suffix.lower())
        if image_format is None:
            raise ValueError(f"Unsupported image format: '{path.suffix}'")

        image = Image.frombytes("RGBA", (width, height), bytes(rgba))

        bounds = self.visible_bounds(np.asarray(image.getchannel("A")))
        if bounds is not None:
            image = image.crop(bounds)

        if image_format == "JPEG":
            flattened = Image.new("RGB", image.size, jpeg_background)
            flattened.paste(image, mask=image)
            flattened.save(path, image_format, quality=self.JPEG_QUALITY)
        elif image_format == "WEBP":
            image.save(path, image_format, quality=self.WEBP_QUALITY)
        else:
            image.save(path, image_format)
