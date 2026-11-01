# coding: utf-8

from PySide6.QtWidgets import QListWidgetItem

from paintjob_designer.gui.widget.library_sidebar import (
    LibraryRowDelegate,
    LibrarySidebar,
)
from paintjob_designer.models import WheelLibrary


class WheelLibrarySidebar(LibrarySidebar):
    """Scrollable list of tire designs in the session library."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            new_tooltip="Create a new wheel from the game's tires.",
            delete_tooltip="Remove the selected wheel from the library.",
            export_tooltip="Export the entire wheel library to a directory of JSONs.",
            parent=parent,
        )

    def set_library(
        self,
        library: WheelLibrary,
        selected_index: int | None = None,
    ) -> None:
        self._list.blockSignals(True)
        self._list.clear()

        for index, wheel in enumerate(library.wheels):
            item = QListWidgetItem((wheel.name or "").strip() or f"Wheel {index + 1}")
            author = (wheel.author or "").strip()

            if author:
                item.setData(LibraryRowDelegate.SECONDARY_ROLE, author)

            self._list.addItem(item)

        self._list.blockSignals(False)

        self._apply_selection_after_rebuild(selected_index, library.count())
        self._refresh_button_state()
