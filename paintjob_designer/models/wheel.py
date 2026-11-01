# coding: utf-8

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

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


class WheelLibrary(BaseModel):
    """Ordered collection of wheels the session is working on."""

    model_config = ConfigDict(frozen=False)

    wheels: list[Wheel] = Field(default_factory=list)

    def count(self) -> int:
        return len(self.wheels)

    def add(self, wheel: Wheel) -> int:
        """Append `wheel` to the library and return its new index."""
        self.wheels.append(wheel)
        return len(self.wheels) - 1

    def remove(self, index: int) -> Wheel:
        """Pop the wheel at `index` and return it."""
        return self.wheels.pop(index)

    def move(self, from_index: int, to_index: int) -> None:
        """Reorder: move a wheel to a new position."""
        wheel = self.wheels.pop(from_index)
        to_index = max(0, min(to_index, len(self.wheels)))
        self.wheels.insert(to_index, wheel)
