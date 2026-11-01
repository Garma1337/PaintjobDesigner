# coding: utf-8

import json

from pydantic import ValidationError

from paintjob_designer.models import WHEEL_FRAME_SIZE, WHEEL_SLOT_NAMES, SlotColors, Wheel
from paintjob_designer.schema_keys import CommonKey, WheelKey


class WheelReader:
    """Parses a wheel JSON file into a `Wheel`."""

    def read(self, data: str | bytes) -> Wheel:
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        raw = json.loads(data)
        self._validate_shape(raw)
        raw[CommonKey.SCHEMA_VERSION] = Wheel.SCHEMA_VERSION

        try:
            wheel = Wheel.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"Wheel is not valid: {exc}") from exc

        for slot_name, slot in wheel.slots.items():
            for region in slot.pixels:
                if region.width != WHEEL_FRAME_SIZE or region.height != WHEEL_FRAME_SIZE:
                    raise ValueError(
                        f"Frame {slot_name!r} pixels must be "
                        f"{WHEEL_FRAME_SIZE}x{WHEEL_FRAME_SIZE}, got {region.width}x{region.height}"
                    )

        return wheel

    def _validate_shape(self, raw: object) -> None:
        if not isinstance(raw, dict):
            raise ValueError("Wheel root must be a JSON object")

        schema_version = int(raw.get(CommonKey.SCHEMA_VERSION, Wheel.SCHEMA_VERSION))
        if schema_version > Wheel.SCHEMA_VERSION:
            raise ValueError(
                f"Wheel schema_version {schema_version} is newer than this "
                f"tool supports (max {Wheel.SCHEMA_VERSION}). "
                "Upgrade Paintjob Designer to open this file."
            )

        slots_raw = raw.get(WheelKey.SLOTS, {})
        if not isinstance(slots_raw, dict):
            raise ValueError("Wheel 'slots' must be an object")

        for slot_name, slot_raw in slots_raw.items():
            if slot_name not in WHEEL_SLOT_NAMES:
                raise ValueError(
                    f"Unknown wheel frame {slot_name!r} (expected frame00..frame{len(WHEEL_SLOT_NAMES) - 1:02d})"
                )

            if not isinstance(slot_raw, dict):
                raise ValueError(
                    f"Frame {slot_name!r} must be an object with 'colors' "
                    f"(and optional 'pixels')"
                )

            colors_raw = slot_raw.get(WheelKey.COLORS)
            if colors_raw is None or len(colors_raw) != SlotColors.SIZE:
                raise ValueError(
                    f"Frame {slot_name!r} must have exactly {SlotColors.SIZE} "
                    f"colors, got {len(colors_raw) if colors_raw is not None else 0}"
                )
