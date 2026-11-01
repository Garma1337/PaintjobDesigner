# coding: utf-8

from PySide6.QtWidgets import QTabWidget, QWidget


class CollapsibleTabWidget(QTabWidget):
    """Tab widget whose pages can be hidden when they don't apply.

    Hiding the open page moves to a neighbor, as Qt does. When that page comes
    back it reopens, so hiding a tab for a moment (the editors clear and refill
    on every asset switch) doesn't throw the user off it. Clicking another tab
    while it's hidden cancels that.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_to_reopen: QWidget | None = None
        self.tabBarClicked.connect(self._forget_page_to_reopen)

    def set_page_visible(self, page: QWidget, visible: bool) -> None:
        index = self.indexOf(page)
        if self.isTabVisible(index) == visible:
            return

        if not visible and self.currentWidget() is page:
            self._page_to_reopen = page

        self.setTabVisible(index, visible)

        if visible and self._page_to_reopen is page:
            self.setCurrentWidget(page)
            self._page_to_reopen = None

    def _forget_page_to_reopen(self, _index: int) -> None:
        self._page_to_reopen = None
