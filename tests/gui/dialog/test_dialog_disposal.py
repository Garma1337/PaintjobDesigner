# coding: utf-8

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.gui.controller.character_picker import CharacterPicker
from paintjob_designer.gui.dialog.edit_metadata_dialog import EditMetadataDialog
from paintjob_designer.gui.util.disposed_after import DisposedAfter
from paintjob_designer.gui.widget.color_picker import PsxColorPicker
from paintjob_designer.models import CharacterProfile, Profile, PsxColor


def _flush_deletes() -> None:
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)


def _finish_modal(accept: bool) -> None:
    """Closes the dialog that `exec()` is about to block on."""

    def finish() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.accept() if accept else dialog.reject()

    QTimer.singleShot(0, finish)


@pytest.fixture
def parent(qapp):
    widget = QWidget()
    yield widget
    widget.deleteLater()
    _flush_deletes()


class TestDisposedAfter:

    def test_alive_inside_the_block_and_deleted_after(self, qapp):
        parent_object = QObject()

        with DisposedAfter(QObject(parent_object)) as child:
            _flush_deletes()
            assert child.parent() is parent_object

        _flush_deletes()
        assert parent_object.children() == []

    def test_an_exception_still_disposes(self, qapp):
        parent_object = QObject()

        with pytest.raises(RuntimeError):
            with DisposedAfter(QObject(parent_object)):
                raise RuntimeError

        _flush_deletes()
        assert parent_object.children() == []


class TestResultsSurviveUntilRead:
    """The dialog must still be alive when its result is read after `exec()`."""

    def test_color_picker_returns_the_accepted_color(self, parent):
        _finish_modal(accept=True)

        picked = PsxColorPicker(ColorConverter()).pick(PsxColor(value=0x1234), parent=parent)

        assert picked is not None
        assert picked.value == 0x1234

    def test_character_picker_returns_the_choice(self, parent):
        crash = CharacterProfile(id="crash", display_name="Crash")
        picker = CharacterPicker(lambda: Profile(characters=[crash]))

        _finish_modal(accept=True)

        assert picker.pick("Pick", parent=parent) is crash

    def test_metadata_values(self, parent):
        with DisposedAfter(EditMetadataDialog(parent, title="t", name="n", author="a")) as dialog:
            _finish_modal(accept=True)
            edit = dialog.exec_get()

        assert (edit.name, edit.author) == ("n", "a")
