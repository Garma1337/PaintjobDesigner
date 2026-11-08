# coding: utf-8

"""JSON field-name constants for the on-disk paintjob/skin/profile formats.

Centralized so a typo in `raw.get("schema_version", ...)` becomes an
`AttributeError` at import time instead of silently returning the
default. Pydantic models use these same names as their attribute names,
so model serialization stays in sync without further wiring.

Grouped by document type. Keys shared across documents (e.g. `name`,
`schema_version`) live on `CommonKey`.
"""


class CommonKey:
    SCHEMA_VERSION = "schema_version"
    NAME = "name"
    AUTHOR = "author"
    ID = "id"
    DISPLAY_NAME = "display_name"


class ProfileKey:
    CHARACTERS = "characters"
    MESH_SOURCE = "mesh_source"
    KART_TYPE = "kart_type"
    KART_SLOTS = "kart_slots"
    KART_VERTEX_SLOTS = "kart_vertex_slots"
    CLUT = "clut"
    CLUT_X = "x"
    CLUT_Y = "y"
    NON_PORTABLE = "non_portable"


class PaintjobKey:
    SLOTS = "slots"
    COLORS = "colors"
    BASE_CHARACTER_ID = "base_character_id"
    VERTEX_OVERRIDES = "vertex_overrides"


class SkinKey:
    SLOTS = "slots"
    COLORS = "colors"
    CHARACTER_ID = "character_id"
    VERTEX_OVERRIDES = "vertex_overrides"


class WheelKey:
    SLOTS = "slots"
    COLORS = "colors"
