# coding: utf-8

from paintjob_designer.gui.command.undo_command_base import UndoCommandBase
from paintjob_designer.models import Paintjob, Rgb888


class ChangeBaseCharacterCommand(UndoCommandBase):
    """A paintjob's base character change, reversible along with the vertex
    overrides it dropped."""

    def __init__(
        self,
        main_window,
        paintjob: Paintjob,
        old_base: str | None,
        old_overrides: dict[int, Rgb888],
    ) -> None:
        super().__init__("Change base character")
        self._window = main_window
        self._paintjob = paintjob
        self._old_base = old_base
        self._old_overrides = dict(old_overrides)
        self._new_base = paintjob.base_character_id
        self._new_overrides = dict(paintjob.vertex_overrides)

    def _apply_redo(self) -> None:
        self._window.apply_base_character_from_command(self._paintjob, self._new_base, self._new_overrides)

    def undo(self) -> None:
        self._window.apply_base_character_from_command(self._paintjob, self._old_base, self._old_overrides)
