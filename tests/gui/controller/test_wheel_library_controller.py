# coding: utf-8

from unittest.mock import MagicMock

import pytest

from paintjob_designer.core import Slugifier
from paintjob_designer.gui.controller.wheel_library_controller import WheelLibraryController
from paintjob_designer.gui.util.library_writer import LibraryWriter
from paintjob_designer.gui.widget.wheel_library_sidebar import WheelLibrarySidebar
from paintjob_designer.models import (
    WHEEL_SLOT_NAMES,
    MetadataEdit,
    PsxColor,
    QuantizedTexture,
    SlotColors,
    Wheel,
)
from paintjob_designer.render.wheel_geometry import WheelGeometry
from paintjob_designer.wheel.reader import WheelReader
from paintjob_designer.wheel.writer import WheelWriter


@pytest.fixture
def fake_color_handler():
    handler = MagicMock()
    handler.default_slot_colors.return_value = [PsxColor(value=0x0421)] * 16
    handler.default_region_pixels.return_value = bytes(512)
    return handler


@pytest.fixture
def controller(qapp, fake_color_handler):
    message = MagicMock()
    message.confirm_destructive.return_value = True
    return WheelLibraryController(
        WheelLibrarySidebar(),
        WheelReader(),
        WheelWriter(),
        LibraryWriter(),
        MagicMock(),
        message,
        MagicMock(),
        Slugifier(),
        fake_color_handler,
        WheelGeometry(),
    )


def _frame(value: int) -> QuantizedTexture:
    return QuantizedTexture(width=32, height=32, pixels=bytes([value]) * 512, palette=[PsxColor(value=value)] * 16)


class TestWheelLibraryController:

    def test_new_wheel_without_an_iso_reports_instead_of_raising(self, controller, fake_color_handler):
        fake_color_handler.default_slot_colors.side_effect = FileNotFoundError("shared.vrm")

        controller.new()

        assert controller.library.count() == 0
        controller._message.error.assert_called_once()

    def test_new_wheel_seeds_every_frame_with_the_game_colors(self, controller):
        controller.new()

        wheel = controller.library.wheels[0]
        assert list(wheel.slots) == list(WHEEL_SLOT_NAMES)
        assert wheel.slots["frame16"].colors[0].value == 0x0421
        assert not any(slot.pixels for slot in wheel.slots.values())

    def test_apply_sheet_writes_pixels_at_each_frame_origin(self, controller):
        controller.new()
        reset = MagicMock()
        controller.library_reset.connect(reset)

        controller.apply_sheet(0, [_frame(i) for i in range(17)])

        wheel = controller.library.wheels[0]
        assert wheel.slots["frame05"].pixels[0].pixels == bytes([5]) * 512
        assert (wheel.slots["frame00"].pixels[0].vram_x, wheel.slots["frame00"].pixels[0].vram_y) == (448, 216)
        assert (wheel.slots["frame16"].pixels[0].vram_x, wheel.slots["frame16"].pixels[0].vram_y) == (320, 216)
        reset.assert_called_once()

    def test_frames_fall_back_to_the_game_tire(self, controller, fake_color_handler):
        wheel = Wheel(slots={"frame02": SlotColors(colors=[PsxColor(value=0x7C00)] * 16)})

        frames = controller.frames_of(wheel)

        assert len(frames) == 17
        assert frames[2][1][0].value == 0x7C00
        assert frames[3][1][0].value == 0x0421
        assert frames[2][0] == bytes(512)

    def test_apply_metadata_renames(self, controller):
        controller.new()

        controller.apply_metadata(0, MetadataEdit(name="Whitewalls", author="Garma", base_character_id=None))

        assert controller.library.wheels[0].name == "Whitewalls"
        assert controller.library.wheels[0].author == "Garma"
