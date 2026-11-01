# coding: utf-8

import json

import pytest


from paintjob_designer.models import KartType
from paintjob_designer.profile.loader import ProfileLoader


def _profile_json(**overrides) -> str:
    doc = {
        "schema_version": 4,
        "characters": [
            {
                "id": "crash",
                "display_name": "Crash Bandicoot",
                "mesh_source": "bigfile/models/racers/hi/crash.ctr",
                "kart_type": "kart",
                "kart_slots": [
                    {"name": "front", "clut": {"x": 112, "y": 255}},
                    {"name": "back", "clut": {"x": 112, "y": 250}},
                ],
            }
        ],
    }

    doc.update(overrides)
    return json.dumps(doc)


class TestProfileReader:

    def test_reads_full_profile(self, profile_reader):
        profile = profile_reader.read(_profile_json())

        assert profile.schema_version == 4
        assert len(profile.characters) == 1

    def test_parses_character(self, profile_reader):
        profile = profile_reader.read(_profile_json())

        character = profile.characters[0]
        assert character.id == "crash"
        assert character.display_name == "Crash Bandicoot"
        assert character.mesh_source == "bigfile/models/racers/hi/crash.ctr"
        assert character.kart_type == KartType.KART
        assert len(character.kart_slots) == 2
        assert character.skin_slots == []

    def test_parses_slots_with_clut_coords(self, profile_reader):
        profile = profile_reader.read(_profile_json())

        front = profile.characters[0].kart_slots[0]
        assert front.name == "front"
        assert front.clut.x == 112
        assert front.clut.y == 255
        assert front.non_portable is False

    def test_parses_non_portable_flag(self, profile_reader):
        doc = _profile_json(characters=[{
            "id": "crash",
            "display_name": "Crash",
            "mesh_source": "x.ctr",
            "kart_type": "kart",
            "kart_slots": [
                {"name": "floor", "clut": {"x": 304, "y": 252}, "non_portable": True},
            ],
        }])

        profile = profile_reader.read(doc)
        floor = profile.characters[0].kart_slots[0]

        assert floor.non_portable is True

    def test_parses_hovercraft_kart_type(self, profile_reader):
        doc = _profile_json(characters=[{
            "id": "oxide",
            "display_name": "Nitros Oxide",
            "mesh_source": "oxide.ctr",
            "kart_type": "hovercraft",
            "kart_slots": [{"name": "hoverkart", "clut": {"x": 288, "y": 248}}],
        }])

        profile = profile_reader.read(doc)
        oxide = profile.characters[0]

        assert oxide.kart_type == KartType.HOVERCRAFT
        assert [s.name for s in oxide.kart_slots] == ["hoverkart"]

    def test_rejects_unknown_kart_type(self, profile_reader):
        doc = _profile_json(characters=[{
            "id": "x",
            "display_name": "x",
            "mesh_source": "x.ctr",
            "kart_type": "spaceship",
            "kart_slots": [],
        }])

        with pytest.raises(ValueError, match="Unknown kart_type"):
            profile_reader.read(doc)

    def test_kart_type_defaults_to_kart_when_missing(self, profile_reader):
        # Backward-compat for hand-authored / minimal profiles that don't
        # set kart_type explicitly.
        doc = _profile_json(characters=[{
            "id": "crash",
            "display_name": "Crash",
            "mesh_source": "x.ctr",
            "kart_slots": [],
        }])

        profile = profile_reader.read(doc)

        assert profile.characters[0].kart_type == KartType.KART

    def test_accepts_bytes_input(self, profile_reader):
        profile = profile_reader.read(_profile_json().encode("utf-8"))

        assert profile.characters[0].id == "crash"

    def test_rejects_non_object_root(self, profile_reader):
        with pytest.raises(ValueError, match="root must be a JSON object"):
            profile_reader.read("[]")

    def test_rejects_future_schema(self, profile_reader):
        with pytest.raises(ValueError, match="schema_version"):
            profile_reader.read(_profile_json(schema_version=999))

    def test_empty_character_list_when_missing(self, profile_reader):
        profile = profile_reader.read(json.dumps({"schema_version": 4}))

        assert profile.characters == []

    def test_bundled_profile_parses(self, profile_reader):
        profile = profile_reader.read(ProfileLoader.bundled_path().read_bytes())

        ids = [c.id for c in profile.characters]
        assert len(ids) == 16
        assert "oxide" in ids
        assert all(c.kart_slots and not c.skin_slots for c in profile.characters)
