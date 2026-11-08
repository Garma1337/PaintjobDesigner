# coding: utf-8

from unittest.mock import MagicMock

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.color.transform import ColorTransformer, TransformMode
from paintjob_designer.gui.dialog.vertex_transform_dialog import VertexTransformDialog
from paintjob_designer.models import Rgb888


def _dialog() -> VertexTransformDialog:
    converter = ColorConverter()
    dialog = VertexTransformDialog(ColorTransformer(converter), converter, MagicMock())
    dialog.set_colors([Rgb888(r=200, g=40, b=40)] * 5, skin_indices={0, 1, 2, 3}, shared_indices={1, 3})
    dialog._sections[TransformMode.INVERT].setChecked(True)
    return dialog


class TestVertexTransformScope:

    def test_colors_shared_with_the_kart_are_left_alone_by_default(self, qapp):
        dialog = _dialog()

        assert sorted(dialog._compute_overrides()) == [0, 2]
        assert "2 of 4" in dialog._intro.text()

    def test_shared_checkbox_is_hidden_when_nothing_is_shared(self, qapp):
        dialog = _dialog()
        assert not dialog._include_kart.isHidden()

        dialog.set_colors([Rgb888(r=200, g=40, b=40)] * 5, skin_indices={0, 1})

        assert dialog._include_kart.isHidden()
        assert sorted(dialog._compute_overrides()) == [0, 1]

    def test_shared_colors_can_be_included_but_kart_only_colors_never(self, qapp):
        dialog = _dialog()
        dialog._include_kart.setChecked(True)

        assert sorted(dialog._compute_overrides()) == [0, 1, 2, 3]
