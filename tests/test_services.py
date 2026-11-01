# coding: utf-8

import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from paintjob_designer.config.store import ConfigStore
from paintjob_designer.gui.main_window import MainWindow
from paintjob_designer.services import container

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _modules_after(statement: str) -> set[str]:
    """`sys.modules` of a fresh interpreter that ran `statement`."""
    result = subprocess.run(
        [sys.executable, "-c", f"import sys; {statement}; print(*sys.modules)"],
        capture_output=True, text=True, check=True, cwd=_REPO_ROOT,
    )

    return set(result.stdout.split())


@pytest.fixture
def fresh_services(qapp, tmp_path):
    """The real wiring with nothing built yet and the config in a temp folder."""
    instances = container._instances
    config_factory = container._factories["config_store"]
    container._instances = {}
    container.register("config_store", lambda c: ConfigStore(tmp_path / "config.json"))

    yield container

    container._factories["config_store"] = config_factory
    container._instances = instances


class TestWiring:

    def test_every_service_can_be_built(self, fresh_services):
        for name in fresh_services.registered_names():
            assert fresh_services.resolve(name) is not None, name

    def test_main_window_builds_from_the_container(self, fresh_services):
        window = MainWindow(fresh_services)

        window.deleteLater()

    def test_context_menu_does_not_stay_behind(self, fresh_services):
        """Unlike a QDialog, a QMenu stays alive as long as its parent does."""
        window = MainWindow(fresh_services)

        for _ in range(3):
            QTimer.singleShot(0, lambda: QApplication.activePopupWidget().close())
            window._on_viewer_context_menu(QPoint(0, 0))

        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)

        assert window.findChildren(QMenu, options=Qt.FindChildOption.FindDirectChildrenOnly) == []
        window.deleteLater()


class TestImportPrompt:

    def test_file_lost_during_the_size_prompt_reports_instead_of_raising(
        self, fresh_services, monkeypatch,
    ):
        window = MainWindow(fresh_services)
        errors = []
        monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[2]))

        class Importer:
            def import_from_path(self, *_args, mode=None):
                raise OSError("gone") if mode else ValueError("wrong size")

        window._single_region_texture_importer = Importer

        def choose_scale():
            prompt = QApplication.activeModalWidget()
            next(b for b in prompt.buttons() if b.text() == "Scale").click()

        QTimer.singleShot(0, choose_scale)

        assert window._import_png_with_prompt(Path("x.png"), 4, 4) is None
        assert errors == ["gone"]
        window.deleteLater()


class TestLazyImports:

    def test_importing_the_services_loads_no_service(self):
        modules = _modules_after("import paintjob_designer.services")

        assert not {"numpy", "PIL", "pydantic", "OpenGL", "PySide6"} & modules
        assert not [m for m in modules if m.startswith("paintjob_designer.gui")]

    def test_pillow_waits_for_the_first_image_operation(self):
        statement = (
            "from PySide6.QtWidgets import QApplication; "
            "app = QApplication(['t', '-platform', 'offscreen']); "
            "from paintjob_designer.gui.main_window import MainWindow; "
            "from paintjob_designer.services import container; "
            "from paintjob_designer.config.store import ConfigStore; "
            "from pathlib import Path; import tempfile; "
            "container.register('config_store', "
            "lambda c: ConfigStore(Path(tempfile.mkdtemp()) / 'config.json')); "
            "window = MainWindow(container)"
        )

        assert "PIL" not in _modules_after(statement)
