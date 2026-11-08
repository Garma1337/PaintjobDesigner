# coding: utf-8

from dataclasses import dataclass, field
from enum import Enum


class KartType(str, Enum):
    """The kind of vehicle a character drives."""

    KART = "kart"
    HOVERCRAFT = "hovercraft"


@dataclass
class ClutCoord:
    x: int = 0
    y: int = 0


@dataclass
class SlotProfile:
    """One paintable CLUT on one character."""

    name: str = ""
    clut: ClutCoord = field(default_factory=ClutCoord)
    non_portable: bool = False


@dataclass
class CharacterProfile:
    """One character + the CLUTs that paintjobs and skins can edit.

    `kart_slots` come from the bundled profile; `skin_slots` are derived
    from the character's mesh when the ISO loads.

    `kart_vertex_slots` lists the gouraud indices that belong to the kart even
    though untextured faces use them. Those faces have no CLUT, so the mesh
    can't tell kart from character.
    """

    id: str = ""
    display_name: str = ""
    mesh_source: str = ""
    kart_type: KartType = KartType.KART
    kart_slots: list[SlotProfile] = field(default_factory=list)
    kart_vertex_slots: list[int] = field(default_factory=list)
    skin_slots: list[SlotProfile] = field(default_factory=list)

    @property
    def slots(self) -> list[SlotProfile]:
        return self.kart_slots + self.skin_slots


@dataclass
class Profile:
    SCHEMA_VERSION = 4

    schema_version: int = SCHEMA_VERSION
    characters: list[CharacterProfile] = field(default_factory=list)


@dataclass
class SkippedCharacter:
    """A profile character whose mesh could not be loaded from the ISO."""

    display_name: str = ""
    mesh_source: str = ""
    reason: str = ""


@dataclass
class ProfileLoadResult:
    """A profile holding only the loadable characters, plus the ones left out."""

    profile: Profile = field(default_factory=Profile)
    skipped: list[SkippedCharacter] = field(default_factory=list)
