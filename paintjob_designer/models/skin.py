# coding: utf-8

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from paintjob_designer.models.asset_library import AssetLibrary
from paintjob_designer.models.color import Rgb888
from paintjob_designer.models.paintjob import SlotColors


class Skin(BaseModel):
    """A character-bound recolor: skin-slot CLUT overrides + gouraud
    vertex color overrides.
    """

    model_config = ConfigDict(frozen=False)

    SCHEMA_VERSION: ClassVar[int] = 1

    schema_version: int = SCHEMA_VERSION
    name: str = ""
    author: str = ""
    character_id: str = ""
    slots: dict[str, SlotColors] = Field(default_factory=dict)
    vertex_overrides: dict[int, Rgb888] = Field(default_factory=dict)


class SkinLibrary(AssetLibrary[Skin]):
    skins: list[Skin] = Field(default_factory=list)

    def _items(self) -> list[Skin]:
        return self.skins

    def for_character(self, character_id: str) -> list[Skin]:
        """Return every skin in the library bound to `character_id`."""
        return [s for s in self.skins if s.character_id == character_id]
