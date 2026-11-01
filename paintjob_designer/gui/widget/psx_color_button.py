# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QWidget

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.gui.widget.color_picker import PsxColorPicker
from paintjob_designer.models import PsxColor


class PsxColorButton(QPushButton):
    """Push-button that shows a PSX color and opens the color picker on click."""

    color_picked = Signal(PsxColor)

    _SIZE = (120, 28)
    _OBJECT_NAME = "psxColorButton"

    def __init__(
        self,
        color_converter: ColorConverter,
        color_picker: PsxColorPicker,
        initial: PsxColor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(self._OBJECT_NAME)
        self._converter = color_converter
        self._picker = color_picker
        self._color = initial
        self.setFixedSize(*self._SIZE)
        self.clicked.connect(self._open_picker)
        self._refresh()

    def color(self) -> PsxColor:
        return self._color

    def set_color(self, color: PsxColor) -> None:
        self._color = color
        self._refresh()

    def _refresh(self) -> None:
        rgb = self._converter.psx_to_rgb(self._color)
        self.setText(self._converter.psx_to_u16_hex(self._color))
        # Light-on-dark or dark-on-light depending on perceived brightness
        # so the hex label stays readable across the picker's whole range.
        lum = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) // 1000
        fg = "#000" if lum > 140 else "#fff"

        self.setStyleSheet(
            f"QPushButton#{self._OBJECT_NAME} {{ "
            f"background-color: rgb({rgb.r},{rgb.g},{rgb.b}); "
            f"color: {fg}; border: 1px solid #222; }}"
        )

    def _open_picker(self) -> None:
        psx = self._picker.pick(self._color, parent=self, title="Pick color")
        if psx is None:
            return

        self.set_color(psx)
        self.color_picked.emit(psx)
