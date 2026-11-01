# coding: utf-8

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from paintjob_designer.models.asset_library import AssetLibrary
from paintjob_designer.models.paintjob import SlotColors

WHEEL_FRAME_COUNT = 17
WHEEL_FRAME_SIZE = 32
WHEEL_SLOT_NAMES = tuple(f"frame{i:02d}" for i in range(WHEEL_FRAME_COUNT))


class Wheel(BaseModel):
    """A tire design: per-frame CLUT overrides + optional 32x32 4bpp pixels.

    Frames without an entry keep the game's colors and pixels.
    """

    model_config = ConfigDict(frozen=False)

    SCHEMA_VERSION: ClassVar[int] = 1

    schema_version: int = SCHEMA_VERSION
    name: str = ""
    author: str = ""
    slots: dict[str, SlotColors] = Field(default_factory=dict)


class WheelLibrary(AssetLibrary[Wheel]):
    wheels: list[Wheel] = Field(default_factory=list)

    def _items(self) -> list[Wheel]:
        return self.wheels
