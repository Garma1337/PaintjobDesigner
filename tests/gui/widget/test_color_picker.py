# coding: utf-8

from PySide6.QtGui import QColor

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.gui.widget.color_picker import PsxColorPicker
from paintjob_designer.models import PsxColor


class TestPsxColorPicker:

    def setup_method(self) -> None:
        self._converter = ColorConverter()
        self._picker = PsxColorPicker(self._converter)

    def test_dialog_starts_opaque_even_for_a_transparent_placeholder(self):
        assert self._picker._start_color(PsxColor(value=0x8000)).alpha() == 255
        assert self._picker._start_color(PsxColor(value=0x0000)).alpha() == 255

    def test_a_typed_color_does_not_inherit_the_placeholder_stp_bit(self):
        picked = self._picker._to_psx(QColor(255, 0, 0, 255), PsxColor(value=0x8000))

        assert picked.stp == 0
        assert picked.value == self._converter.rgb_to_psx(self._converter.psx_to_rgb(picked)).value

    def test_a_real_color_keeps_its_stp_bit(self):
        initial = PsxColor(value=0x8000 | 0x001F)

        picked = self._picker._to_psx(QColor(0, 255, 0, 255), initial)

        assert picked.stp == 1

    def test_low_alpha_is_the_transparent_sentinel(self):
        assert self._picker._to_psx(QColor(255, 0, 0, 10), PsxColor(value=0x001F)).value == 0
