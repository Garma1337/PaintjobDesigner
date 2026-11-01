# coding: utf-8

from paintjob_designer.models import Wheel


class WheelWriter:
    def serialize(self, wheel: Wheel, indent: int = 2) -> str:
        return wheel.model_dump_json(indent=indent, by_alias=True)
