# coding: utf-8

import json
from pathlib import Path

from paintjob_designer.models import Wheel


_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "schema"
    / "wheels_library_schema.json"
)


class TestWheelJsonSchema:
    """The committed `schema/wheels_library_schema.json` must stay in lockstep
    with the pydantic Wheel model. If you change a field, regenerate the schema
    by running `tools/dump_schema.py` and commit the result.
    """

    def test_committed_schema_matches_model(self) -> None:
        generated = Wheel.model_json_schema(by_alias=True)
        committed = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

        assert generated == committed, (
            "Committed schema/wheels_library_schema.json is out of sync with "
            "the pydantic Wheel model. Regenerate with "
            "`python tools/dump_schema.py`."
        )

    def test_slots_present(self) -> None:
        schema = Wheel.model_json_schema(by_alias=True)
        assert "slots" in schema["properties"]
