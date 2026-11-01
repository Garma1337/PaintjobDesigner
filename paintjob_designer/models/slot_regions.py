# coding: utf-8

from collections.abc import Iterator
from dataclasses import dataclass, field

from paintjob_designer.models.ctr_mesh import BitDepth, BlendingMode
from paintjob_designer.models.profile import ClutCoord


_PIXELS_PER_VRAM_COLUMN_BY_BPP = {
    BitDepth.Bit4: 4,
    BitDepth.Bit8: 2,
    BitDepth.Bit16: 1,
    BitDepth.Bit24: 1,
}


@dataclass
class SlotRegion:
    """One rectangular texture region that samples through a paintjob slot's CLUT."""
    vram_x: int = 0
    vram_y: int = 0
    vram_width: int = 0
    vram_height: int = 0
    bpp: BitDepth = BitDepth.Bit4
    blending: BlendingMode = BlendingMode.Standard
    texture_layout_indices: list[int] = field(default_factory=list)

    @property
    def pixel_width(self) -> int:
        """Logical pixel width — VRAM columns × pixels-per-column for this bpp."""
        return self.vram_width * _PIXELS_PER_VRAM_COLUMN_BY_BPP.get(self.bpp, 1)

    @property
    def pixel_height(self) -> int:
        """Logical pixel height — same as VRAM row count (no vertical packing)."""
        return self.vram_height

    @property
    def pixel_dimensions(self) -> tuple[int, int]:
        return self.pixel_width, self.pixel_height


@dataclass
class SlotRegions:
    """All VRAM regions on one character's mesh that share a single paintjob slot."""
    slot_name: str = ""
    clut: ClutCoord = field(default_factory=ClutCoord)
    regions: list[SlotRegion] = field(default_factory=list)


@dataclass
class CharacterSlotRegions:
    character_id: str = ""
    slots: dict[str, SlotRegions] = field(default_factory=dict)

    def all_slots(self) -> Iterator[tuple[str, SlotRegions]]:
        yield from self.slots.items()

    def find_slot(self, slot_name: str) -> SlotRegions | None:
        return self.slots.get(slot_name)
