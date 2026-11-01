# coding: utf-8

from dataclasses import dataclass

import numpy as np

from paintjob_designer.models import (
    WHEEL_FRAME_COUNT,
    WHEEL_FRAME_SIZE,
    WHEEL_SLOT_NAMES,
    BitDepth,
    BlendingMode,
    ClutCoord,
    SlotRegion,
    SlotRegions,
    Vector3f,
)

_FRAME_Y = 216
_TEXPAGE_WIDTH = 64
_FRAME_HALFWORDS = WHEEL_FRAME_SIZE // 4
_FRAME_TEXPAGES = (7,) * 8 + (6,) * 8 + (5,)
_FRAME_CLUTS = (
    0x40C0, 0x4001, 0x4041, 0x4081, 0x40C1, 0x4002, 0x4042, 0x4082,
    0x40C2, 0x4003, 0x4043, 0x4083, 0x40C3, 0x4012, 0x4052, 0x4092, 0x40D2,
)

WHEEL_CENTERS = ((144, 64, 199), (-144, 64, 199), (144, 64, -96), (-144, 64, -96))
WHEEL_HALF_SIZE = 0xCCC / 64

SIDE_FRAME = WHEEL_FRAME_COUNT - 1
TREAD_FRAME = 0
_TREAD_SEGMENTS = 32


@dataclass
class WheelQuad:
    """One textured tire quad: corners TL, TR, BR, BL and their UVs within the frame (0..1)."""
    corners: np.ndarray
    frame: int
    uvs: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))


@dataclass
class FrameBounds:
    """Opaque texel box of a frame, as fractions of the 32x32 cell (right/bottom exclusive).

    `rows` holds each texel row's own opaque (left, right) span, None for an
    empty row; without it every row spans the whole box.
    """
    left: float = 0.0
    top: float = 0.0
    right: float = 1.0
    bottom: float = 1.0
    rows: tuple[tuple[float, float] | None, ...] = ()

    def inner_span(self, v0: float, v1: float) -> tuple[float, float]:
        """Widest (left, right) that is opaque in every texel row between `v0` and `v1` (0..1)."""
        if not self.rows:
            return self.left, self.right

        last = len(self.rows) - 1
        first_row = min(max(int(min(v0, v1) * len(self.rows)), 0), last)
        last_row = min(max(int(max(v0, v1) * len(self.rows)), 0), last)
        left, right = self.left, self.right
        for span in self.rows[first_row:last_row + 1]:
            if span is not None:
                left, right = max(left, span[0]), min(right, span[1])

        return (left, right) if left < right else (self.left, self.right)


class WheelGeometry:
    """VRAM layout of the wheel frames and the 3D tire built from them."""

    def frame_origin(self, frame: int) -> tuple[int, int]:
        """VRAM halfword origin of a frame's 32x32 texel block."""
        u = (frame % 8) * WHEEL_FRAME_SIZE if frame < 16 else 0
        return _FRAME_TEXPAGES[frame] * _TEXPAGE_WIDTH + u // 4, _FRAME_Y

    def frame_clut(self, frame: int) -> ClutCoord:
        clut = _FRAME_CLUTS[frame]
        return ClutCoord(x=(clut & 0x3F) * 16, y=clut >> 6)

    def wheel_slot_regions(self) -> dict[str, SlotRegions]:
        """The 17 frames as editable slots, keyed by `WHEEL_SLOT_NAMES`."""
        slots: dict[str, SlotRegions] = {}
        for frame, name in enumerate(WHEEL_SLOT_NAMES):
            x, y = self.frame_origin(frame)
            region = SlotRegion(
                vram_x=x,
                vram_y=y,
                vram_width=_FRAME_HALFWORDS,
                vram_height=WHEEL_FRAME_SIZE,
                bpp=BitDepth.Bit4,
                blending=BlendingMode.Translucent,
            )
            slots[name] = SlotRegions(slot_name=name, clut=self.frame_clut(frame), regions=[region])

        return slots

    def game_to_mesh_space(self, point, scale: Vector3f, offset: Vector3f) -> np.ndarray:
        """Map a kart-local game-unit point into the space `VertexAssembler` emits.

        The game decodes a vertex as `(v + offset) * 4 * scale` with the frame
        offset in vertex units; the assembler uses `(v / 255 + offset / 4096) * scale`.
        """
        factor = 1.0 - 4096.0 / 255.0
        return np.array([
            point[0] / 1020.0 + offset.x * scale.x * factor,
            point[1] / 1020.0 + offset.y * scale.y * factor,
            point[2] / 1020.0 + offset.z * scale.z * factor,
        ])

    def opaque_bounds(self, alpha: np.ndarray) -> FrameBounds:
        """Bounding box of the non-transparent texels of a 32x32 alpha mask."""
        columns = np.flatnonzero(alpha.any(axis=0))
        rows = np.flatnonzero(alpha.any(axis=1))
        if columns.size == 0:
            return FrameBounds()

        size = float(WHEEL_FRAME_SIZE)
        spans: list[tuple[float, float] | None] = []
        for row in alpha:
            opaque = np.flatnonzero(row)
            spans.append((opaque[0] / size, (opaque[-1] + 1) / size) if opaque.size else None)

        return FrameBounds(
            columns[0] / size, rows[0] / size, (columns[-1] + 1) / size, (rows[-1] + 1) / size, tuple(spans),
        )

    def wheel_cylinder(
        self, center: np.ndarray, half_size: float, side: FrameBounds, tread: FrameBounds, roll: float = 0.0,
    ) -> list[WheelQuad]:
        """Side-face caps plus a tread band around the axle (x), sized from the frames' opaque texels."""
        radius = half_size * (side.bottom - side.top)
        width = half_size * 2.0 * (tread.right - tread.left)
        up = half_size * np.array([0.0, np.cos(roll), np.sin(roll)])
        forward = half_size * np.array([0.0, -np.sin(roll), np.cos(roll)])
        quads: list[WheelQuad] = []

        for x in (-width / 2.0, width / 2.0):
            cap = center + np.array([x, 0.0, 0.0])
            quads.append(WheelQuad(
                corners=np.array([cap - forward + up, cap + forward + up, cap + forward - up, cap - forward - up]),
                frame=SIDE_FRAME,
            ))

        def rim(angle: float) -> tuple[np.ndarray, float]:
            point = center + np.array([0.0, radius * np.cos(angle + roll), radius * np.sin(angle + roll)])
            t = (1.0 - np.cos(angle)) / 2.0
            v = tread.top + (tread.bottom - tread.top) * (0.001 + 0.998 * t)
            return point, v

        left = np.array([-width / 2.0, 0.0, 0.0])
        right = np.array([width / 2.0, 0.0, 0.0])
        for segment in range(_TREAD_SEGMENTS):
            a, va = rim(2.0 * np.pi * segment / _TREAD_SEGMENTS)
            b, vb = rim(2.0 * np.pi * (segment + 1) / _TREAD_SEGMENTS)
            u0, u1 = tread.inner_span(va, vb)
            quads.append(WheelQuad(
                corners=np.array([a + left, a + right, b + right, b + left]),
                frame=TREAD_FRAME,
                uvs=((u0, va), (u1, va), (u1, vb), (u0, vb)),
            ))

        return quads

