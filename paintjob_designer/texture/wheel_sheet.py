# coding: utf-8

from pathlib import Path

from PIL import Image

from paintjob_designer.models import WHEEL_FRAME_COUNT, WHEEL_FRAME_SIZE, PsxColor, QuantizedTexture
from paintjob_designer.texture.texture_exporter import TextureExporter
from paintjob_designer.texture.texture_quantizer import TextureQuantizer


class WheelSheet:
    """Converts a wheel's 17 frames to and from one sprite sheet.

    Frames are 32x32 cells read left to right, top to bottom; the exported
    sheet is a single 544x32 row. Each frame gets its own 16-color CLUT,
    like the game's.
    """

    def __init__(self, quantizer: TextureQuantizer, exporter: TextureExporter) -> None:
        self._quantizer = quantizer
        self._exporter = exporter

    def from_file(self, path: Path) -> list[QuantizedTexture]:
        with Image.open(path) as image:
            return self.from_image(image)

    def to_image(self, frames: list[tuple[bytes, list[PsxColor]]]) -> Image.Image:
        if len(frames) != WHEEL_FRAME_COUNT:
            raise ValueError(f"Expected {WHEEL_FRAME_COUNT} frames, got {len(frames)}")

        sheet = Image.new("RGBA", (WHEEL_FRAME_SIZE * WHEEL_FRAME_COUNT, WHEEL_FRAME_SIZE), (0, 0, 0, 0))
        for index, (pixels, clut) in enumerate(frames):
            frame = self._exporter.to_image(pixels, WHEEL_FRAME_SIZE, WHEEL_FRAME_SIZE, clut)
            sheet.paste(frame, (index * WHEEL_FRAME_SIZE, 0))

        return sheet

    def from_image(self, image: Image.Image) -> list[QuantizedTexture]:
        width, height = image.size
        columns = width // WHEEL_FRAME_SIZE
        rows = height // WHEEL_FRAME_SIZE
        if width % WHEEL_FRAME_SIZE or height % WHEEL_FRAME_SIZE or columns * rows < WHEEL_FRAME_COUNT:
            raise ValueError(
                f"A wheel sheet holds {WHEEL_FRAME_COUNT} frames of {WHEEL_FRAME_SIZE}x{WHEEL_FRAME_SIZE} "
                f"pixels (e.g. {WHEEL_FRAME_SIZE * WHEEL_FRAME_COUNT}x{WHEEL_FRAME_SIZE}); got {width}x{height}"
            )

        rgba = image.convert("RGBA")
        frames: list[QuantizedTexture] = []
        for index in range(WHEEL_FRAME_COUNT):
            x = (index % columns) * WHEEL_FRAME_SIZE
            y = (index // columns) * WHEEL_FRAME_SIZE
            cell = rgba.crop((x, y, x + WHEEL_FRAME_SIZE, y + WHEEL_FRAME_SIZE))
            frames.append(self._quantizer.quantize(cell, WHEEL_FRAME_SIZE, WHEEL_FRAME_SIZE))

        return frames
