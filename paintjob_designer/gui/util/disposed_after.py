# coding: utf-8

from typing import Generic, TypeVar

from PySide6.QtCore import QObject

TObject = TypeVar("TObject", bound=QObject)


class DisposedAfter(Generic[TObject]):
    """Deletes a short-lived modal dialog when the `with` block ends.

    A parented dialog otherwise lives until its parent does. `WA_DeleteOnClose`
    isn't an option: it can delete the dialog before `exec()` returns, while
    callers still have to read the result from it.
    """

    def __init__(self, qobject: TObject) -> None:
        self._qobject = qobject

    def __enter__(self) -> TObject:
        return self._qobject

    def __exit__(self, *_exc_info) -> None:
        self._qobject.deleteLater()
