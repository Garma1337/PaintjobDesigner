# coding: utf-8

import gc
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QPushButton

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.color.gradient import GradientGenerator
from paintjob_designer.gui.dialog.edit_metadata_dialog import EditMetadataDialog
from paintjob_designer.gui.dialog.gradient_fill_dialog import GradientFillDialog
from paintjob_designer.gui.dialog.multi_region_texture_import_dialog import MultiRegionTextureImportDialog
from paintjob_designer.gui.dialog.palette_apply_dialog import PaletteApplyDialog
from paintjob_designer.gui.dialog.palette_edit_dialog import PaletteEditDialog
from paintjob_designer.gui.dialog.pick_character_dialog import PickCharacterDialog
from paintjob_designer.gui.widget.color_picker import PsxColorPicker
from paintjob_designer.models import CharacterProfile, Palette, PsxColor


def _palette_dialog() -> PaletteEditDialog:
    converter = ColorConverter()
    colors = [PsxColor(value=1), PsxColor(value=2), PsxColor(value=3)]
    return PaletteEditDialog(Palette(name="p", colors=colors), converter, PsxColorPicker(converter))


def _gradient_dialog() -> GradientFillDialog:
    converter = ColorConverter()
    return GradientFillDialog(
        "slot", [PsxColor(value=1)] * 16, converter, GradientGenerator(converter), PsxColorPicker(converter),
    )


def _palette_apply_dialog() -> PaletteApplyDialog:
    palette = Palette(name="p", colors=[PsxColor(value=1), PsxColor(value=2)])
    return PaletteApplyDialog(
        palette=palette, paintjob_name="a", slot_name="s", color_converter=ColorConverter(),
    )


def _multi_region_dialog(files=None) -> MultiRegionTextureImportDialog:
    return MultiRegionTextureImportDialog(
        None, slot_name="s", region_specs=[(4, 4), (8, 8)], files=files or MagicMock(),
    )


def _metadata_dialog() -> EditMetadataDialog:
    return EditMetadataDialog(None, title="t", name="n", author="a")


def _character_dialog() -> PickCharacterDialog:
    return PickCharacterDialog([CharacterProfile(id="crash")], title="t")


class TestLifetime:
    """A lambda capturing the dialog keeps it alive forever: Qt holds the lambda,
    and the lambda holds the dialog."""

    @pytest.mark.parametrize("factory", [
        _palette_dialog,
        _gradient_dialog,
        _palette_apply_dialog,
        _multi_region_dialog,
        _metadata_dialog,
        _character_dialog,
    ])
    def test_dropping_a_dialog_frees_it(self, qapp, factory):
        dialog = factory()
        ref = weakref.ref(dialog)

        del dialog
        gc.collect()

        assert ref() is None


class TestMultiRegionPickButtons:

    def test_each_button_fills_its_own_region(self, qapp):
        files = MagicMock()
        files.pick_open_path.side_effect = [Path("second.png"), Path("first.png")]
        dialog = _multi_region_dialog(files)
        buttons = {
            button.property("regionIndex"): button
            for button in dialog.findChildren(QPushButton)
            if button.property("regionIndex") is not None
        }

        buttons[1].click()
        buttons[0].click()

        assert dialog.chosen_paths() == [Path("first.png"), Path("second.png")]


class TestPaletteRowButtons:

    @staticmethod
    def _click(dialog: PaletteEditDialog, text: str, row: int) -> None:
        buttons = [b for b in dialog.findChildren(QPushButton) if b.text() == text]
        by_index = {b.property("colorIndex"): b for b in buttons}
        by_index[row].click()

    @staticmethod
    def _values(dialog: PaletteEditDialog) -> list[int]:
        return [color.value for color in dialog._colors]

    def test_up_moves_that_row(self, qapp):
        dialog = _palette_dialog()

        self._click(dialog, "▲", 1)

        assert self._values(dialog) == [2, 1, 3]

    def test_down_moves_that_row(self, qapp):
        dialog = _palette_dialog()

        self._click(dialog, "▼", 1)

        assert self._values(dialog) == [1, 3, 2]

    def test_remove_drops_that_row(self, qapp):
        dialog = _palette_dialog()

        self._click(dialog, "✕", 0)

        assert self._values(dialog) == [2, 3]

    def test_picking_a_color_writes_that_row(self, qapp):
        dialog = _palette_dialog()
        button = next(b for b in dialog.findChildren(QPushButton) if hasattr(b, "color_picked") and b.property("colorIndex") == 2)

        button.color_picked.emit(PsxColor(value=9))

        assert self._values(dialog) == [1, 2, 9]
