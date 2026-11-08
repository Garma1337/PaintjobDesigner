# coding: utf-8

import json

from paintjob_designer.models import (
    CharacterProfile,
    ClutCoord,
    KartType,
    Profile,
    SlotProfile,
)
from paintjob_designer.schema_keys import CommonKey, ProfileKey


class ProfileReader:
    """Parses the bundled profile JSON into a `Profile` (kart slots only)."""

    def read(self, data: str | bytes) -> Profile:
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        return self._parse(json.loads(data))

    def _parse(self, raw: dict) -> Profile:
        if not isinstance(raw, dict):
            raise ValueError("Profile root must be a JSON object")

        schema_version = int(
            raw.get(CommonKey.SCHEMA_VERSION, Profile.SCHEMA_VERSION),
        )

        if schema_version != Profile.SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported profile schema_version {schema_version} "
                f"(expected {Profile.SCHEMA_VERSION})"
            )

        characters = [
            self._parse_character(c) for c in raw.get(ProfileKey.CHARACTERS, [])
        ]

        return Profile(schema_version=schema_version, characters=characters)

    def _parse_character(self, raw: dict) -> CharacterProfile:
        kart_type_raw = str(raw.get(ProfileKey.KART_TYPE, KartType.KART.value))

        try:
            kart_type = KartType(kart_type_raw)
        except ValueError as exc:
            raise ValueError(
                f"Unknown kart_type {kart_type_raw!r} for character "
                f"{raw.get(CommonKey.ID, '?')!r}"
            ) from exc

        return CharacterProfile(
            id=str(raw.get(CommonKey.ID, "")),
            display_name=str(raw.get(CommonKey.DISPLAY_NAME, "")),
            mesh_source=str(raw.get(ProfileKey.MESH_SOURCE, "")),
            kart_type=kart_type,
            kart_slots=[
                self._parse_slot(s) for s in raw.get(ProfileKey.KART_SLOTS, [])
            ],
            kart_vertex_slots=[int(i) for i in raw.get(ProfileKey.KART_VERTEX_SLOTS, [])],
        )

    def _parse_slot(self, raw: dict) -> SlotProfile:
        clut_raw = raw.get(ProfileKey.CLUT) or {}

        return SlotProfile(
            name=str(raw.get(CommonKey.NAME, "")),
            clut=ClutCoord(
                x=int(clut_raw.get(ProfileKey.CLUT_X, 0)),
                y=int(clut_raw.get(ProfileKey.CLUT_Y, 0)),
            ),
            non_portable=bool(raw.get(ProfileKey.NON_PORTABLE, False)),
        )
