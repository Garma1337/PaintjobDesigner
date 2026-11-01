# coding: utf-8

from paintjob_designer.models import (
    BitDepth,
    CharacterProfile,
    CharacterSlotRegions,
    ClutCoord,
    CtrMesh,
    SlotRegion,
    SlotRegions,
    TextureLayout,
)


# In 4bpp mode, a single VRAM u16 stores 4 texture pixels (low-nibble first).
# In 8bpp, 2 texture pixels. In 16/24bpp, a u16 is a full pixel (no stretch).
_STRETCH_BY_BPP = {
    BitDepth.Bit4: 4,
    BitDepth.Bit8: 2,
    BitDepth.Bit16: 1,
    BitDepth.Bit24: 1,
}

# VRAM page dimensions in 16bpp coordinates.
_PAGE_WIDTH_VRAM = 64
_PAGE_HEIGHT = 256


class SlotRegionDeriver:
    """Groups a `CtrMesh`'s `TextureLayout`s by CLUT coordinate and matches each
    group to a `SlotProfile`, producing the VRAM rectangles a slot owns.

    The profile's skin slots are derived from the same mesh, so every
    sampled CLUT belongs to a slot.
    """

    def derive(
        self,
        mesh: CtrMesh,
        character: CharacterProfile,
    ) -> CharacterSlotRegions:
        groups = self._group_layouts(mesh)
        slots_by_clut = {(s.clut.x, s.clut.y): s for s in character.slots}

        result = CharacterSlotRegions(character_id=character.id)

        for (palette_x, palette_y, page_x, page_y, bpp), layouts in groups.items():
            clut_x = palette_x * 16
            clut_y = palette_y
            slot = slots_by_clut.get((clut_x, clut_y))
            if slot is None:
                raise ValueError(
                    f"{character.id}: mesh samples CLUT ({clut_x},{clut_y}) "
                    f"that no slot covers"
                )

            entry = result.slots.setdefault(
                slot.name,
                SlotRegions(slot_name=slot.name, clut=ClutCoord(x=clut_x, y=clut_y)),
            )

            entry.regions.append(self._compute_region(layouts, page_x, page_y, bpp))

        # Kart slots whose shared CLUT this mesh doesn't sample stay editable
        # (other characters' karts use them); empty `regions` = orphan slot.
        for slot in character.slots:
            if slot.name in result.slots:
                continue

            result.slots[slot.name] = SlotRegions(
                slot_name=slot.name,
                clut=ClutCoord(x=slot.clut.x, y=slot.clut.y),
            )

        return result

    def _group_layouts(
        self, mesh: CtrMesh,
    ) -> dict[tuple[int, int, int, int, BitDepth], list[tuple[int, TextureLayout]]]:
        groups: dict[tuple[int, int, int, int, BitDepth], list[tuple[int, TextureLayout]]] = {}
        for index, tl in enumerate(mesh.texture_layouts):
            key = (tl.palette_x, tl.palette_y, tl.page_x, tl.page_y, tl.bpp)
            groups.setdefault(key, []).append((index, tl))
        return groups

    def _compute_region(
        self,
        layouts: list[tuple[int, TextureLayout]],
        page_x: int,
        page_y: int,
        bpp: BitDepth,
    ) -> SlotRegion:
        us: list[int] = []
        vs: list[int] = []
        for _, tl in layouts:
            # Skip uv[3] — CTR faces are triangles; the 4th UV is garbage
            # (ctr-tools overwrites it with uv[2] before Combine).
            us.extend((tl.uv0_u, tl.uv1_u, tl.uv2_u))
            vs.extend((tl.uv0_v, tl.uv1_v, tl.uv2_v))

        min_u, max_u = min(us), max(us)
        min_v, max_v = min(vs), max(vs)
        stretch = _STRETCH_BY_BPP[bpp]

        vram_x = page_x * _PAGE_WIDTH_VRAM + min_u // stretch
        vram_y = page_y * _PAGE_HEIGHT + min_v
        vram_width = (max_u - min_u) // stretch + 1
        vram_height = max_v - min_v + 1

        return SlotRegion(
            vram_x=vram_x,
            vram_y=vram_y,
            vram_width=vram_width,
            vram_height=vram_height,
            bpp=bpp,
            blending=layouts[0][1].blending,
            texture_layout_indices=[i for i, _ in layouts],
        )
