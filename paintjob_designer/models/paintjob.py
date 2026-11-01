# coding: utf-8

import base64
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

from paintjob_designer.constants import CLUT_PALETTE_SIZE
from paintjob_designer.models.asset_library import AssetLibrary
from paintjob_designer.models.color import PsxColor
from paintjob_designer.models.profile import KartType

"""Canonical paintjob slot names for `KartType.KART` characters."""
KART_SLOT_NAMES = (
    "front", "back", "floor", "brown", "motorside", "motortop", "bridge", "exhaust",
    "rearbase", "seattop", "exhaustholes", "seatside", "exhaustmount",
    "underfloor", "steering",
)


class SlotRegionPixels(BaseModel):
    """4bpp pixel payload for one VRAM region of a slot."""

    model_config = ConfigDict(frozen=False, populate_by_name=True)

    vram_x: int = 0
    vram_y: int = 0
    width: int = 0
    height: int = 0
    pixels: "_Base64Bytes" = Field(
        default=b"",
        alias="data",
        serialization_alias="data",
        json_schema_extra={"contentEncoding": "base64"},
    )

    @staticmethod
    def decode_base64(value: Any) -> bytes:
        """Accept raw bytes or a base64 string on input."""
        if isinstance(value, bytes):
            return value

        if isinstance(value, str):
            return base64.b64decode(value, validate=True)

        raise TypeError(
            f"Expected bytes or base64 string, got {type(value).__name__}",
        )

    @staticmethod
    def encode_base64(value: bytes) -> str:
        """Serialize raw bytes back to a base64 ASCII string for JSON."""
        return base64.b64encode(value).decode("ascii")


_Base64Bytes = Annotated[
    bytes,
    BeforeValidator(SlotRegionPixels.decode_base64),
    PlainSerializer(SlotRegionPixels.encode_base64, return_type=str),
]

SlotRegionPixels.model_rebuild(_types_namespace={"_Base64Bytes": _Base64Bytes})


class SlotColors(BaseModel):
    """One CLUT slot on a paintjob: 16 colors + optional per-region pixels."""

    model_config = ConfigDict(frozen=False)

    SIZE: ClassVar[int] = CLUT_PALETTE_SIZE

    colors: list[PsxColor] = Field(default_factory=list)
    pixels: list[SlotRegionPixels] = Field(default_factory=list)


class Paintjob(BaseModel):
    """A single kart paintjob: one entry per kart slot, each 16 colors,
    optionally with custom textures.
    """

    model_config = ConfigDict(frozen=False)

    SCHEMA_VERSION: ClassVar[int] = 2

    schema_version: int = SCHEMA_VERSION
    name: str = ""
    author: str = ""
    kart_type: KartType = KartType.KART
    base_character_id: str | None = None
    slots: dict[str, SlotColors] = Field(default_factory=dict)

    def has_any_pixels(self) -> bool:
        """True when any slot carries imported pixel data."""
        return any(slot.pixels for slot in self.slots.values())


class PaintjobLibrary(AssetLibrary[Paintjob]):
    paintjobs: list[Paintjob] = Field(default_factory=list)

    def _items(self) -> list[Paintjob]:
        return self.paintjobs

    def find_by_base_character(self, character_id: str) -> Paintjob | None:
        """Return the paintjob whose `base_character_id` matches, or None."""
        for pj in self.paintjobs:
            if pj.base_character_id == character_id:
                return pj

        return None
