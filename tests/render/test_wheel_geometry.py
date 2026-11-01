# coding: utf-8

import numpy as np
import pytest

from paintjob_designer.models import WHEEL_SLOT_NAMES, Vector3f
from paintjob_designer.render.wheel_geometry import (
    WHEEL_HALF_SIZE,
    FrameBounds,
    WheelGeometry,
)


@pytest.fixture
def geometry():
    return WheelGeometry()


class TestFrameLayout:

    def test_frames_follow_the_tire_icon_group(self, geometry):
        # tire00 texpage 7 u 0, tire04 texpage 7 u 128, tire08 texpage 6 u 0, tire16 texpage 5 u 0
        assert geometry.frame_origin(0) == (448, 216)
        assert geometry.frame_origin(4) == (480, 216)
        assert geometry.frame_origin(8) == (384, 216)
        assert geometry.frame_origin(15) == (440, 216)
        assert geometry.frame_origin(16) == (320, 216)

    def test_cluts_decode_the_icon_clut_words(self, geometry):
        # tire00 CLUT 0x40c0, tire16 CLUT 0x40d2
        assert (geometry.frame_clut(0).x, geometry.frame_clut(0).y) == (0, 259)
        assert (geometry.frame_clut(16).x, geometry.frame_clut(16).y) == (288, 259)

    def test_slot_regions_cover_every_frame_as_one_32x32_region(self, geometry):
        slots = geometry.wheel_slot_regions()

        assert list(slots) == list(WHEEL_SLOT_NAMES)
        for slot in slots.values():
            assert len(slot.regions) == 1
            assert slot.regions[0].pixel_dimensions == (32, 32)
            assert slot.regions[0].texture_layout_indices == []


class TestOpaqueBounds:

    def test_box_of_the_non_transparent_texels(self, geometry):
        alpha = np.zeros((32, 32), dtype=bool)
        alpha[2:30, 5:27] = True

        bounds = geometry.opaque_bounds(alpha)

        assert (bounds.left, bounds.top, bounds.right, bounds.bottom) == (5 / 32, 2 / 32, 27 / 32, 30 / 32)

    def test_records_each_rows_own_opaque_span(self, geometry):
        alpha = np.zeros((32, 32), dtype=bool)
        alpha[2, 8:24] = True
        alpha[3:30, 5:27] = True

        bounds = geometry.opaque_bounds(alpha)

        assert bounds.rows[0] is None
        assert bounds.rows[2] == (8 / 32, 24 / 32)
        assert bounds.rows[10] == (5 / 32, 27 / 32)

    def test_an_empty_frame_uses_the_whole_cell(self, geometry):
        bounds = geometry.opaque_bounds(np.zeros((32, 32), dtype=bool))

        assert (bounds.left, bounds.top, bounds.right, bounds.bottom) == (0.0, 0.0, 1.0, 1.0)


class TestWheelCylinder:
    _SIDE = FrameBounds(1 / 32, 1 / 32, 31 / 32, 31 / 32)
    _TREAD = FrameBounds(5 / 32, 2 / 32, 27 / 32, 30 / 32)

    def _cylinder(self, geometry, roll: float = 0.0):
        return geometry.wheel_cylinder(np.zeros(3), 1.0, self._SIDE, self._TREAD, roll)

    def test_two_side_caps_at_the_tread_width(self, geometry):
        caps = [q for q in self._cylinder(geometry) if q.frame == 16]

        assert len(caps) == 2
        assert sorted(float(q.corners[0][0]) for q in caps) == pytest.approx([-22 / 32, 22 / 32])
        assert all(np.allclose(q.corners[:, 0], q.corners[0][0]) for q in caps)

    def test_tread_band_wraps_the_axle_at_the_side_disc_radius(self, geometry):
        band = [q for q in self._cylinder(geometry) if q.frame == 0]

        assert len(band) == 32
        radii = [np.hypot(c[1], c[2]) for q in band for c in q.corners]
        assert radii == pytest.approx([30 / 32] * len(radii))

    def test_front_view_reproduces_the_tread_frame(self, geometry):
        band = [q for q in self._cylinder(geometry) if q.frame == 0]
        top = band[0]

        assert top.uvs[0] == pytest.approx((5 / 32, 2 / 32), abs=1e-3)
        assert top.uvs[1] == pytest.approx((27 / 32, 2 / 32), abs=1e-3)
        bottom_v = max(v for q in band for _, v in q.uvs)
        assert bottom_v == pytest.approx(30 / 32, abs=1e-3)

    def test_rounded_tread_shoulders_never_leave_transparent_texels_on_the_band(self, geometry):
        alpha = np.zeros((32, 32), dtype=bool)
        for row in range(2, 30):
            inset = max(0, 4 - min(row - 2, 29 - row))
            alpha[row, 5 + inset:27 - inset] = True

        band = [q for q in geometry.wheel_cylinder(np.zeros(3), 1.0, self._SIDE, geometry.opaque_bounds(alpha)) if q.frame == 0]

        for quad in band:
            (u0, va), (u1, _), _, (_, vb) = quad.uvs
            rows = range(int(min(va, vb) * 32), int(max(va, vb) * 32) + 1)
            columns = range(int(u0 * 32), int(np.ceil(u1 * 32)))
            assert all(alpha[r, c] for r in rows for c in columns)

    def test_rolling_turns_everything_around_the_axle_but_keeps_the_texture(self, geometry):
        still = self._cylinder(geometry)
        rolled = self._cylinder(geometry, np.pi / 2)

        assert np.allclose(rolled[0].corners[0], [still[0].corners[0][0], 1.0, 1.0])
        assert [q.uvs for q in rolled] == [q.uvs for q in still]
        assert np.allclose([c[0] for q in rolled for c in q.corners], [c[0] for q in still for c in q.corners])


class TestMeshSpace:

    def test_game_units_scale_by_1020_plus_the_frame_offset_correction(self, geometry):
        scale = Vector3f(x=0.5, y=0.5, z=0.5)
        offset = Vector3f(x=0.0, y=0.0, z=0.0)

        assert np.allclose(geometry.game_to_mesh_space((1020, 510, -1020), scale, offset), (1.0, 0.5, -1.0))

    def test_the_offset_shifts_like_the_vertex_assembler(self, geometry):
        scale = Vector3f(x=1.0, y=1.0, z=1.0)
        offset = Vector3f(x=-120 / 4096, y=0.0, z=0.0)

        # Assembler: (v / 255 + offset) * scale; game: (v + offset * 4096) * 4 * scale.
        v = 200
        game_x = (v + offset.x * 4096) * 4 * scale.x
        assembler_x = (v / 255 + offset.x) * scale.x

        assert geometry.game_to_mesh_space((game_x, 0, 0), scale, offset)[0] == pytest.approx(assembler_x)

    def test_half_size_is_the_default_wheel_size_over_64(self, geometry):
        assert WHEEL_HALF_SIZE == pytest.approx(0xCCC / 64)
