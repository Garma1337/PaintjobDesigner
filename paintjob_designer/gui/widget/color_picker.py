# coding: utf-8

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QWidget

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.gui.util.disposed_after import DisposedAfter
from paintjob_designer.models import PsxColor, Rgb888


class PsxColorPicker:
    """Opens a standard color dialog and snaps the result to the PSX 15-bit grid."""

    def __init__(self, color_converter: ColorConverter) -> None:
        self._colors = color_converter

    def pick(
        self, initial: PsxColor, parent: QWidget | None = None, title: str = "Pick CLUT color",
    ) -> PsxColor | None:
        with DisposedAfter(QColorDialog(self._start_color(initial), parent)) as dialog:
            dialog.setWindowTitle(title)
            dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
            dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
            dialog.resize(1100, 640)

            if dialog.exec() != QColorDialog.DialogCode.Accepted:
                return None

            chosen = dialog.currentColor()

        if not chosen.isValid():
            return None

        return self._to_psx(chosen, initial)

    def _start_color(self, initial: PsxColor) -> QColor:
        rgb = self._colors.psx_to_rgb(initial)
        return QColor(rgb.r, rgb.g, rgb.b, 255)

    def _to_psx(self, chosen: QColor, initial: PsxColor) -> PsxColor:
        if chosen.alpha() < 128:
            return PsxColor(value=0)

        stp = 0 if initial.is_transparent else initial.stp
        return self._colors.rgb_to_psx(Rgb888(r=chosen.red(), g=chosen.green(), b=chosen.blue()), stp=stp)
