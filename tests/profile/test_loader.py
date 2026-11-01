# coding: utf-8

from pathlib import Path

import pytest

from paintjob_designer.ctr.animation import AnimationDecoder
from paintjob_designer.ctr.reader import CtrModelReader
from paintjob_designer.models import BitDepth, BlendingMode, CtrMesh, CtrModel, TextureLayout
from paintjob_designer.profile.loader import ProfileLoader
from paintjob_designer.profile.reader import ProfileReader
from paintjob_designer.profile.skin_slot_deriver import SkinSlotDeriver


def _layout(palette_x: int, palette_y: int) -> TextureLayout:
    return TextureLayout(
        uv0_u=0, uv0_v=0, uv1_u=0, uv1_v=0, uv2_u=0, uv2_v=0, uv3_u=0, uv3_v=0,
        palette_x=palette_x, palette_y=palette_y, page_x=0, page_y=0,
        blending=BlendingMode.Standard, bpp=BitDepth.Bit4,
    )


class _FakeModelReader:
    """Returns a mesh sampling Crash's `front` CLUT (112,255) plus one body CLUT (304,250)."""

    def __init__(self) -> None:
        self.read_count = 0

    def read(self, data: bytes) -> CtrModel:
        self.read_count += 1
        return CtrModel(meshes=[CtrMesh(texture_layouts=[_layout(7, 255), _layout(19, 250)])])


def _fake_iso(root: Path, without: tuple[str, ...] = ()) -> Path:
    profile = ProfileReader().read(ProfileLoader.bundled_path().read_bytes())
    for character in profile.characters:
        if character.id in without:
            continue

        path = root / character.mesh_source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")

    return root


class TestProfileLoader:

    def test_derives_skin_slots_from_each_mesh(self, tmp_path):
        model_reader = _FakeModelReader()
        loader = ProfileLoader(ProfileReader(), model_reader, SkinSlotDeriver())

        result = loader.load(_fake_iso(tmp_path))
        profile = result.profile

        crash = next(c for c in profile.characters if c.id == "crash")
        assert [s.name for s in crash.skin_slots] == ["extra_304_250"]
        assert result.skipped == []
        assert model_reader.read_count == len(profile.characters)

    def test_kart_slot_cluts_are_not_skin_slots(self, tmp_path):
        loader = ProfileLoader(ProfileReader(), _FakeModelReader(), SkinSlotDeriver())

        profile = loader.load(_fake_iso(tmp_path)).profile

        crash = next(c for c in profile.characters if c.id == "crash")
        assert "extra_112_255" not in [s.name for s in crash.skin_slots]

    def test_missing_mesh_is_skipped_and_reported(self, tmp_path):
        loader = ProfileLoader(ProfileReader(), _FakeModelReader(), SkinSlotDeriver())

        result = loader.load(_fake_iso(tmp_path, without=("crash",)))

        ids = [c.id for c in result.profile.characters]
        assert "crash" not in ids
        assert "cortex" in ids
        assert [s.reason for s in result.skipped] == ["file is missing"]
        assert result.skipped[0].display_name == "Crash Bandicoot"
        assert result.skipped[0].mesh_source.endswith("crash.ctr")

    def test_corrupt_mesh_is_skipped_and_the_rest_load(self, tmp_path):
        class _OneCorruptReader(_FakeModelReader):
            def read(self, data: bytes) -> CtrModel:
                if data == b"corrupt":
                    raise EOFError("read past end")

                return super().read(data)

        iso = _fake_iso(tmp_path)
        (iso / "bigfile/models/racers/hi/cortex.ctr").write_bytes(b"corrupt")
        loader = ProfileLoader(ProfileReader(), _OneCorruptReader(), SkinSlotDeriver())

        result = loader.load(iso)

        assert "cortex" not in [c.id for c in result.profile.characters]
        assert "crash" in [c.id for c in result.profile.characters]
        assert len(result.skipped) == 1
        assert "not a readable model" in result.skipped[0].reason

    def test_no_loadable_characters_raises(self, tmp_path):
        loader = ProfileLoader(ProfileReader(), _FakeModelReader(), SkinSlotDeriver())

        with pytest.raises(ValueError, match="No character models"):
            loader.load(tmp_path)

    def test_all_truncated_meshes_raise(self, tmp_path):
        loader = ProfileLoader(ProfileReader(), CtrModelReader(AnimationDecoder()), SkinSlotDeriver())

        with pytest.raises(ValueError, match="No character models"):
            loader.load(_fake_iso(tmp_path))
