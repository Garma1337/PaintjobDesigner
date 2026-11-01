# coding: utf-8

import pytest
from PIL import Image

from paintjob_designer.render.preview_image_writer import PreviewImageWriter


@pytest.fixture
def writer():
    return PreviewImageWriter()


def _red_frame(width: int, height: int) -> bytes:
    return bytes([255, 0, 0, 255]) * (width * height)


class TestFormats:

    @pytest.mark.parametrize("suffix, expected", [
        (".png", "PNG"),
        (".jpg", "JPEG"),
        (".jpeg", "JPEG"),
        (".webp", "WEBP"),
        (".PNG", "PNG"),
    ])
    def test_format_follows_extension(self, writer, tmp_path, suffix, expected):
        path = tmp_path / f"preview{suffix}"

        writer.write(_red_frame(4, 3), 4, 3, path)

        with Image.open(path) as image:
            assert image.format == expected
            assert image.size == (4, 3)

    def test_png_keeps_pixels_exact(self, writer, tmp_path):
        path = tmp_path / "preview.png"

        writer.write(_red_frame(2, 2), 2, 2, path)

        with Image.open(path) as image:
            assert image.convert("RGBA").getpixel((1, 1)) == (255, 0, 0, 255)

    @pytest.mark.parametrize("suffix", [".png", ".webp"])
    def test_transparency_is_kept(self, writer, tmp_path, suffix):
        path = tmp_path / f"preview{suffix}"
        transparent = bytes([0, 0, 0, 0]) * 4

        writer.write(transparent, 2, 2, path)

        with Image.open(path) as image:
            assert image.convert("RGBA").getpixel((0, 0))[3] == 0

    def test_jpeg_flattens_transparency_onto_background(self, writer, tmp_path):
        path = tmp_path / "preview.jpg"
        transparent = bytes([0, 0, 0, 0]) * 64

        writer.write(transparent, 8, 8, path, jpeg_background=(38, 41, 46))

        with Image.open(path) as image:
            r, g, b = image.getpixel((4, 4))
            assert abs(r - 38) <= 2 and abs(g - 41) <= 2 and abs(b - 46) <= 2

    def test_jpeg_is_flattened_to_rgb(self, writer, tmp_path):
        path = tmp_path / "preview.jpg"

        writer.write(_red_frame(8, 8), 8, 8, path)

        with Image.open(path) as image:
            assert image.mode == "RGB"


class TestCrop:

    @staticmethod
    def _frame_with_opaque_block() -> bytes:
        # 6x5 transparent frame with an opaque 2x2 block at (3, 1)..(4, 2).
        image = Image.new("RGBA", (6, 5), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (3, 1, 5, 3))
        return image.tobytes()

    @pytest.mark.parametrize("suffix", [".png", ".jpg", ".webp"])
    def test_crops_to_visible_pixels(self, writer, tmp_path, suffix):
        path = tmp_path / f"preview{suffix}"

        writer.write(self._frame_with_opaque_block(), 6, 5, path)

        with Image.open(path) as image:
            assert image.size == (2, 2)

    def test_partially_transparent_pixels_count_as_visible(self, writer, tmp_path):
        path = tmp_path / "preview.png"
        image = Image.new("RGBA", (4, 1), (0, 0, 0, 0))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((2, 0), (255, 0, 0, 40))

        writer.write(image.tobytes(), 4, 1, path)

        with Image.open(path) as written:
            assert written.size == (3, 1)

    def test_floating_specks_do_not_widen_the_crop(self, writer, tmp_path):
        path = tmp_path / "preview.png"
        image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (10, 10, 20, 20))
        for x, y in [(30, 30), (31, 29), (35, 36), (2, 2)]:
            image.putpixel((x, y), (34, 0, 0, 127))

        writer.write(image.tobytes(), 40, 40, path)

        with Image.open(path) as written:
            assert written.size == (10, 10)

    def test_pointed_tip_is_kept(self, writer, tmp_path):
        # Triangle widening by one pixel per row, like a kart's ear tip.
        path = tmp_path / "preview.png"
        image = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
        for row in range(10):
            image.paste((255, 0, 0, 255), (10, 5 + row, 11 + row, 6 + row))

        writer.write(image.tobytes(), 30, 30, path)

        with Image.open(path) as written:
            assert written.height >= 9

    def test_separate_small_part_is_kept(self, writer, tmp_path):
        path = tmp_path / "preview.png"
        image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (5, 5, 15, 15))
        image.paste((255, 0, 0, 255), (30, 30, 33, 33))

        writer.write(image.tobytes(), 40, 40, path)

        with Image.open(path) as written:
            assert written.size == (28, 28)

    def test_fully_transparent_frame_keeps_its_size(self, writer, tmp_path):
        path = tmp_path / "preview.png"

        writer.write(bytes(4 * 12), 4, 3, path)

        with Image.open(path) as image:
            assert image.size == (4, 3)


class TestValidation:

    def test_unknown_extension_rejected(self, writer, tmp_path):
        with pytest.raises(ValueError):
            writer.write(_red_frame(1, 1), 1, 1, tmp_path / "preview.bmp")

    def test_zero_dims_rejected(self, writer, tmp_path):
        with pytest.raises(ValueError):
            writer.write(b"", 0, 0, tmp_path / "preview.png")
