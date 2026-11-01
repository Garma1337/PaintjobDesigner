# coding: utf-8

import json

import pytest

from paintjob_designer.models import (
    Paintjob,
    PaintjobLibrary,
    Skin,
    SkinLibrary,
    Wheel,
    WheelLibrary,
)

_LIBRARIES = [
    (PaintjobLibrary, Paintjob, "paintjobs"),
    (SkinLibrary, Skin, "skins"),
    (WheelLibrary, Wheel, "wheels"),
]


@pytest.mark.parametrize("library_type, asset_type, field", _LIBRARIES)
class TestAssetLibrary:

    def _filled(self, library_type, asset_type):
        library = library_type()
        for name in ("a", "b", "c"):
            library.add(asset_type(name=name))

        return library

    def _names(self, library, field):
        return [asset.name for asset in getattr(library, field)]

    def test_add_returns_the_new_index(self, library_type, asset_type, field):
        library = library_type()

        assert library.add(asset_type(name="a")) == 0
        assert library.add(asset_type(name="b")) == 1
        assert library.count() == 2

    def test_remove_returns_the_asset(self, library_type, asset_type, field):
        library = self._filled(library_type, asset_type)

        assert library.remove(1).name == "b"
        assert self._names(library, field) == ["a", "c"]

    @pytest.mark.parametrize("to_index, expected", [
        (0, ["c", "a", "b"]),
        (1, ["a", "c", "b"]),
        (99, ["a", "b", "c"]),
        (-5, ["c", "a", "b"]),
    ])
    def test_move_clamps_the_target(self, library_type, asset_type, field, to_index, expected):
        library = self._filled(library_type, asset_type)

        library.move(2, to_index)

        assert self._names(library, field) == expected

    def test_instances_do_not_share_their_list(self, library_type, asset_type, field):
        first = library_type()
        first.add(asset_type(name="a"))

        assert library_type().count() == 0

    def test_saved_json_keeps_only_the_list_field(self, library_type, asset_type, field):
        library = self._filled(library_type, asset_type)

        dumped = json.loads(library.model_dump_json(by_alias=True))

        assert list(dumped) == [field]
        assert [item["name"] for item in dumped[field]] == ["a", "b", "c"]

    def test_round_trips_through_saved_json(self, library_type, asset_type, field):
        library = self._filled(library_type, asset_type)

        restored = library_type.model_validate(library.model_dump(by_alias=True))

        assert self._names(restored, field) == ["a", "b", "c"]
        assert restored.count() == 3
