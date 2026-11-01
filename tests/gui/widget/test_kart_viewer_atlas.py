# coding: utf-8

import numpy as np

from paintjob_designer.gui.widget.kart_viewer import KartViewer
from paintjob_designer.render.atlas_uv_mapper import AtlasUvMapper
from paintjob_designer.render.blend_mode_grouper import BlendModeGrouper
from paintjob_designer.render.ray_picker import RayTrianglePicker
from paintjob_designer.render.wheel_geometry import WheelGeometry


class TestRollTimer:

    @staticmethod
    def _viewer() -> KartViewer:
        return KartViewer(AtlasUvMapper(), RayTrianglePicker(), BlendModeGrouper(), WheelGeometry())

    def test_runs_only_while_rolling_with_wheels_on_screen(self, qapp):
        viewer = self._viewer()

        viewer.set_wheels_rolling(True)
        assert not viewer._roll_timer.isActive()

        viewer.set_wheels(np.zeros((4, 3), dtype=np.float32), 1.0)
        assert viewer._roll_timer.isActive()

        viewer.set_wheels_rolling(False)
        assert not viewer._roll_timer.isActive()

    def test_stops_when_the_wheels_go_away_and_resumes_when_they_return(self, qapp):
        viewer = self._viewer()
        viewer.set_wheels(np.zeros((4, 3), dtype=np.float32), 1.0)
        viewer.set_wheels_rolling(True)

        viewer.set_wheels(None)
        assert not viewer._roll_timer.isActive()

        viewer.set_wheels(np.zeros((4, 3), dtype=np.float32), 1.0)
        assert viewer._roll_timer.isActive()

        viewer.clear()
        assert not viewer._roll_timer.isActive()


class TestSurfaceFormat:

    def test_requests_an_alpha_buffer_for_transparent_captures(self, qapp):
        viewer = KartViewer(AtlasUvMapper(), RayTrianglePicker(), BlendModeGrouper(), WheelGeometry())

        assert viewer.format().alphaBufferSize() == 8


class TestAtlasRegionUploads:

    def test_regions_queued_before_a_paint_grow_into_one_rect(self, qapp):
        viewer = KartViewer(AtlasUvMapper(), RayTrianglePicker(), BlendModeGrouper(), WheelGeometry())
        viewer._texture = 1
        rgba = bytes(16 * 16 * 4)

        viewer.set_atlas_region(rgba, 16, 16, 2, 3, 4, 5)
        viewer.set_atlas_region(rgba, 16, 16, 10, 1, 2, 2)

        assert viewer._pending_atlas_region[3:] == (2, 1, 10, 7)
