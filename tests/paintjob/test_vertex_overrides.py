# coding: utf-8

import json

import pytest

from paintjob_designer.models import Paintjob, Rgb888

RED = Rgb888(r=255, g=0, b=0)


class TestPaintjobVertexOverrides:

    def test_apply_only_on_the_base_character(self):
        paintjob = Paintjob(base_character_id="oxide", vertex_overrides={51: RED})

        assert paintjob.vertex_overrides_for("oxide") == {51: RED}
        assert paintjob.vertex_overrides_for("crash") == {}

    def test_unbound_paintjob_applies_nowhere(self):
        paintjob = Paintjob(vertex_overrides={51: RED})

        assert paintjob.vertex_overrides_for("oxide") == {}

    def test_changing_the_base_drops_them(self):
        paintjob = Paintjob(base_character_id="oxide", vertex_overrides={51: RED})

        paintjob.set_base_character("crash")

        assert paintjob.base_character_id == "crash"
        assert paintjob.vertex_overrides == {}

    def test_setting_the_same_base_keeps_them(self):
        paintjob = Paintjob(base_character_id="oxide", vertex_overrides={51: RED})

        paintjob.set_base_character("oxide")

        assert paintjob.vertex_overrides == {51: RED}

    def test_existing_files_without_the_field_still_load(self, paintjob_reader):
        assert paintjob_reader.read(json.dumps({"name": "old"})).vertex_overrides == {}

    def test_rejects_non_object(self, paintjob_reader):
        with pytest.raises(ValueError, match="vertex_overrides"):
            paintjob_reader.read(json.dumps({"vertex_overrides": []}))
