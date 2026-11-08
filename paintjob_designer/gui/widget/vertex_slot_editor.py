# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from paintjob_designer.gui.widget.color_swatch import ColorSwatch
from paintjob_designer.models import Rgb888

_OVERRIDDEN_BORDER_CSS = (
    "QFrame#vertexRow { border: 1px solid #e0841e; border-radius: 3px; }"
)
_FOCUSED_BORDER_CSS = (
    "QFrame#vertexRow { border: 1px solid #4f9dff; border-radius: 3px; "
    "background-color: rgba(79, 157, 255, 30); }"
)
_DEFAULT_BORDER_CSS = (
    "QFrame#vertexRow { border: 1px solid transparent; border-radius: 3px; }"
)


class VertexSlotEditor(QWidget):
    """Per-vertex color editor for an asset's gouraud override table."""

    color_edit_requested = Signal(int)
    vertex_reset_requested = Signal(int)
    reset_all_requested = Signal()
    transform_requested = Signal()
    vertex_focus_changed = Signal(object)
    context_requested = Signal(int, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._colors: list[Rgb888] = []
        self._overridden: set[int] = set()
        self._enabled = False
        self._focused_index: int | None = None

        self._swatches: dict[int, ColorSwatch] = {}
        self._row_frames: dict[int, QFrame] = {}
        self._highlight_buttons: dict[int, QPushButton] = {}
        self._reset_buttons: dict[int, QPushButton] = {}

        self._empty_label = QLabel(
            "No character loaded — vertex slots appear here once a "
            "character is in preview.",
        )
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: #888; padding: 12px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        self._transform_button = QPushButton("Transform...")
        self._transform_button.setToolTip(
            "Apply Hue / Saturation / Brightness / RGB transforms to "
            "the vertex colors listed here.",
        )
        self._transform_button.clicked.connect(self.transform_requested)
        button_row.addWidget(self._transform_button)

        self._reset_all_button = QPushButton("Reset all")
        self._reset_all_button.setToolTip(
            "Drop every per-vertex override on the active paintjob or skin and "
            "revert to the character's baked gouraud colors.",
        )
        self._reset_all_button.clicked.connect(self.reset_all_requested)
        button_row.addWidget(self._reset_all_button)
        button_row.addStretch()
        outer.addLayout(button_row)

        self._notice_label = QLabel()
        self._notice_label.setWordWrap(True)
        self._notice_label.setStyleSheet("color: #e0841e; padding: 4px 0;")
        self._notice_label.hide()
        outer.addWidget(self._notice_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        self._content_layout.addWidget(self._empty_label)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

        self._sync_top_buttons()

    def set_colors(
        self,
        colors: list[Rgb888],
        overridden: set[int] | None = None,
        visible: set[int] | None = None,
    ) -> None:
        """(Re)build the per-vertex rows for a new character's gouraud table;
        `visible` limits the rows to those indices (all when None)."""
        self._clear_rows()
        self._colors = list(colors)
        self._overridden = set(overridden) if overridden is not None else set()
        self._focused_index = None

        indices = [i for i in range(len(self._colors)) if visible is None or i in visible]
        if not indices:
            self._empty_label.show()
            self._sync_top_buttons()
            return

        self._empty_label.hide()

        for i in indices:
            row = self._build_row(i, self._colors[i])
            # Insert above the trailing stretch so rows pack to the top.
            self._content_layout.insertWidget(self._content_layout.count() - 1, row)

        self._sync_enabled()
        self._sync_top_buttons()

    def update_color(
        self,
        index: int,
        color: Rgb888,
        is_overridden: bool = False,
    ) -> None:
        if index not in self._swatches:
            return

        self._colors[index] = color
        self._swatches[index].set_color(color.r, color.g, color.b, 0xFF)

        if is_overridden:
            self._overridden.add(index)
        else:
            self._overridden.discard(index)

        self._apply_row_style(index)

    def set_editable(self, editable: bool) -> None:
        self._enabled = editable
        self._sync_enabled()
        self._sync_top_buttons()

    def set_notice(self, text: str) -> None:
        """Explain why the rows are read-only; an empty `text` hides it."""
        self._notice_label.setText(text)
        self._notice_label.setVisible(bool(text))

    def focused_index(self) -> int | None:
        return self._focused_index

    def _build_row(self, index: int, color: Rgb888) -> QFrame:
        row = QFrame()
        row.setObjectName("vertexRow")
        row.setFrameShape(QFrame.Shape.NoFrame)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(6)

        label = QLabel(f"v{index}")
        label.setMinimumWidth(36)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(label)

        swatch = ColorSwatch()
        swatch.set_color(color.r, color.g, color.b, 0xFF)
        swatch.clicked.connect(self._emit_edit(index))
        swatch.right_clicked.connect(self._emit_context(index))
        row_layout.addWidget(swatch)

        highlight_button = QPushButton("Highlight")
        highlight_button.setCheckable(True)
        highlight_button.setToolTip(
            "Dim every kart triangle that doesn't sample this vertex color, "
            "so you can see exactly where it lands on the model.",
        )
        highlight_button.setFixedHeight(22)
        highlight_button.clicked.connect(self._emit_highlight_toggle(index))
        row_layout.addWidget(highlight_button)

        reset_button = QPushButton("Reset")
        reset_button.setToolTip("Drop this vertex's override and revert to the baked color.")
        reset_button.setFixedHeight(22)
        reset_button.clicked.connect(self._emit_reset(index))
        row_layout.addWidget(reset_button)

        row_layout.addStretch()

        self._swatches[index] = swatch
        self._row_frames[index] = row
        self._highlight_buttons[index] = highlight_button
        self._reset_buttons[index] = reset_button

        self._apply_row_style(index)
        return row

    def _apply_row_style(self, index: int) -> None:
        row = self._row_frames[index]
        if self._focused_index == index:
            row.setStyleSheet(_FOCUSED_BORDER_CSS)
        elif index in self._overridden:
            row.setStyleSheet(_OVERRIDDEN_BORDER_CSS)
        else:
            row.setStyleSheet(_DEFAULT_BORDER_CSS)

        self._reset_buttons[index].setEnabled(
            self._enabled and index in self._overridden,
        )

    def _clear_rows(self) -> None:
        for row in self._row_frames.values():
            self._content_layout.removeWidget(row)
            row.deleteLater()

        self._swatches.clear()
        self._row_frames.clear()
        self._highlight_buttons.clear()
        self._reset_buttons.clear()

    def _sync_enabled(self) -> None:
        for swatch in self._swatches.values():
            swatch.setEnabled(self._enabled)

        for btn in self._highlight_buttons.values():
            btn.setEnabled(bool(self._colors))

        for i in self._reset_buttons:
            self._apply_row_style(i)

    def _sync_top_buttons(self) -> None:
        active = self._enabled and bool(self._colors)
        self._transform_button.setEnabled(active)
        self._reset_all_button.setEnabled(active and bool(self._overridden))

    def _emit_edit(self, index: int):
        def handler():
            if not self._enabled:
                return

            self.color_edit_requested.emit(index)

        return handler

    def _emit_reset(self, index: int):
        def handler():
            if not self._enabled or index not in self._overridden:
                return

            self.vertex_reset_requested.emit(index)

        return handler

    def _emit_context(self, index: int):
        def handler():
            self.context_requested.emit(index, QCursor.pos())

        return handler

    def _emit_highlight_toggle(self, index: int):
        def handler():
            if self._focused_index == index:
                self._set_focus(None)
            else:
                self._set_focus(index)

        return handler

    def _set_focus(self, index: int | None) -> None:
        if index == self._focused_index:
            return

        previous = self._focused_index
        self._focused_index = index

        if previous in self._row_frames:
            self._highlight_buttons[previous].setChecked(False)
            self._apply_row_style(previous)

        if index in self._row_frames:
            self._highlight_buttons[index].setChecked(True)
            self._apply_row_style(index)

        self.vertex_focus_changed.emit(index)
