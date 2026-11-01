# coding: utf-8

import pytest
from PIL import Image

from paintjob_designer.models import PsxColor
from paintjob_designer.texture.four_bpp_codec import FourBppCodec
from paintjob_designer.texture.texture_exporter import TextureExporter
from paintjob_designer.texture.texture_quantizer import TextureQuantizer
from paintjob_designer.texture.wheel_sheet import WheelSheet


@pytest.fixture
def sheet(color_converter):
    return WheelSheet(TextureQuantizer(color_converter), TextureExporter(color_converter, FourBppCodec()))


def _solid_frames(count: int = 17):
    clut = [PsxColor(value=0)] + [PsxColor(value=0x001F)] * 15
    return [(bytes([0x11]) * 512, clut) for _ in range(count)]


class TestWheelSheet:

    def test_exports_one_row_of_17_frames(self, sheet):
        image = sheet.to_image(_solid_frames())

        assert image.size == (544, 32)
        assert image.getpixel((0, 0))[3] == 255
        assert image.getpixel((543, 31))[3] == 255

    def test_rejects_the_wrong_frame_count(self, sheet):
        with pytest.raises(ValueError, match="17"):
            sheet.to_image(_solid_frames(16))

    def test_round_trips_through_quantization(self, sheet):
        frames = sheet.from_image(sheet.to_image(_solid_frames()))

        assert len(frames) == 17
        assert all(f.width == 32 and f.height == 32 and len(f.pixels) == 512 for f in frames)

    def test_reads_frames_from_a_grid_row_major(self, sheet):
        grid = Image.new("RGBA", (32 * 5, 32 * 4), (0, 0, 0, 0))
        grid.paste((255, 0, 0, 255), (32 * 2, 0, 32 * 3, 32))

        frames = sheet.from_image(grid)

        assert any(c.value != 0 for c in frames[2].palette[1:])
        assert set(frames[0].pixels) == {0}

    def test_rejects_sheets_without_room_for_every_frame(self, sheet):
        with pytest.raises(ValueError, match="17 frames"):
            sheet.from_image(Image.new("RGBA", (32 * 4, 32 * 4)))

        with pytest.raises(ValueError, match="17 frames"):
            sheet.from_image(Image.new("RGBA", (545, 32)))
