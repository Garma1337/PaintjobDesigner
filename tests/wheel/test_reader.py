# coding: utf-8

import base64
import json
import re
from pathlib import Path

import pytest

from paintjob_designer.models import WHEEL_SLOT_NAMES, SlotColors, Wheel
from paintjob_designer.wheel.reader import WheelReader
from paintjob_designer.wheel.writer import WheelWriter

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schema" / "wheels_library_schema.json"


def _frame(width: int = 32, height: int = 32) -> dict:
    return {
        "colors": ["#7fff"] * SlotColors.SIZE,
        "pixels": [{
            "vram_x": 448, "vram_y": 216, "width": width, "height": height,
            "data": base64.b64encode(bytes(width * height // 2)).decode("ascii"),
        }],
    }


def _wheel_json(**overrides) -> str:
    doc = {"schema_version": 1, "name": "Whitewalls", "author": "Garma", "slots": {"frame00": _frame()}}
    doc.update(overrides)
    return json.dumps(doc)


class TestWheelReader:

    def test_reads_metadata_and_frames(self):
        wheel = WheelReader().read(_wheel_json())

        assert wheel.name == "Whitewalls"
        assert wheel.author == "Garma"
        assert len(wheel.slots["frame00"].pixels[0].pixels) == 512

    def test_rejects_unknown_frame_names(self):
        with pytest.raises(ValueError, match="frame17"):
            WheelReader().read(_wheel_json(slots={"frame17": _frame()}))

    def test_rejects_frames_that_are_not_32x32(self):
        with pytest.raises(ValueError, match="32x32"):
            WheelReader().read(_wheel_json(slots={"frame03": _frame(16, 16)}))

    def test_rejects_wrong_color_count(self):
        frame = _frame()
        frame["colors"] = frame["colors"][:4]

        with pytest.raises(ValueError, match="16"):
            WheelReader().read(_wheel_json(slots={"frame00": frame}))

    def test_rejects_newer_schema(self):
        with pytest.raises(ValueError, match="newer"):
            WheelReader().read(_wheel_json(schema_version=99))

    def test_round_trips_through_the_writer(self):
        wheel = WheelReader().read(_wheel_json())

        again = WheelReader().read(WheelWriter().serialize(wheel))

        assert again == wheel


class TestWheelSlotNames:

    def test_seventeen_zero_padded_frames(self):
        assert len(WHEEL_SLOT_NAMES) == 17
        assert all(re.fullmatch(r"frame\d\d", name) for name in WHEEL_SLOT_NAMES)
        assert WHEEL_SLOT_NAMES[-1] == "frame16"


class TestWheelJsonSchema:

    def test_committed_schema_matches_model(self):
        committed = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

        assert Wheel.model_json_schema(by_alias=True) == committed, (
            "Regenerate schema/wheels_library_schema.json with `python tools/dump_schema.py`."
        )
