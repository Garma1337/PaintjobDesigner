# coding: utf-8

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from paintjob_designer.config.store import ConfigStore
from paintjob_designer.gui.main_window import MainWindow
from paintjob_designer.gui.editor_mode import EditorMode
from paintjob_designer.models import AssembledMesh, CharacterProfile, GouraudColor, Paintjob, Profile, Rgb888, Skin
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


class TestVertexUsage:

    def test_profile_kart_vertices_leave_the_character_side(self, fresh_services):
        window = MainWindow(fresh_services)
        window._editor_mode = EditorMode.SKIN
        window._current_character = CharacterProfile(id="oxide", kart_vertex_slots=[1, 2])
        window._current_bundle = SimpleNamespace(mesh=SimpleNamespace(texture_layouts=[]))
        window._vertex_assembler = SimpleNamespace(assemble=lambda _mesh: SimpleNamespace(
            texture_layout_indices=[0],
            gouraud_color_indices=[(0, 1, 2)],
        ))

        assert window._vertex_usage() == ({0}, {1, 2})
        assert window._vertex_scope() == {"skin_indices": {0}, "shared_indices": set()}
        window._current_bundle = None
        window.deleteLater()


RED = Rgb888(r=255, g=0, b=0)
BLUE = Rgb888(r=0, g=0, b=255)


@pytest.fixture
def paint_window(fresh_services):
    """Paintjob mode on Oxide, with v1 and v2 assigned to the kart."""
    window = MainWindow(fresh_services)
    oxide = CharacterProfile(id="oxide", display_name="Nitros Oxide", kart_vertex_slots=[1, 2])
    crash = CharacterProfile(id="crash", display_name="Crash")
    window._profile = Profile(characters=[oxide, crash])
    window._kart_viewer = MagicMock()
    window._vertex_assembler = SimpleNamespace(assemble=lambda *_args, **_kwargs: AssembledMesh())
    window._current_bundle = SimpleNamespace(mesh=SimpleNamespace(
        gouraud_colors=[GouraudColor(r=9, g=9, b=9) for _ in range(4)], texture_layouts=[],
    ))
    window._current_character = oxide
    window._paintjob_controller._current = Paintjob(base_character_id="oxide")
    window._editor_mode = EditorMode.PAINTJOB

    yield window

    window._close_vertex_transform()
    window._current_bundle = None
    window.deleteLater()


class TestPaintjobVertexColors:

    def test_lists_only_the_kart_colors_and_edits_the_paintjob(self, paint_window):
        paint_window._populate_vertex_editor()
        paint_window._apply_vertex_override(1, RED)

        assert set(paint_window._vertex_editor._swatches) == {1, 2}
        assert paint_window._vertex_editor._enabled
        assert paint_window._vertex_editor._notice_label.isHidden()
        assert paint_window._current_paintjob.vertex_overrides == {1: RED}

    def test_read_only_and_baked_away_from_the_base_character(self, paint_window):
        paint_window._current_paintjob.vertex_overrides[1] = RED
        paint_window._current_paintjob.base_character_id = "crash"
        paint_window._populate_vertex_editor()

        assert not paint_window._vertex_editor._enabled
        assert paint_window._active_vertex_overrides() == {}
        assert "Crash" in paint_window._vertex_editor._notice_label.text()

        paint_window._apply_vertex_override(2, BLUE)
        assert paint_window._current_paintjob.vertex_overrides == {1: RED}

    def test_unbound_paintjob_says_to_set_a_base(self, paint_window):
        paint_window._current_paintjob.base_character_id = None
        paint_window._populate_vertex_editor()

        assert "no base character" in paint_window._vertex_editor._notice_label.text()

    def test_lists_colors_only_kart_faces_use(self, paint_window):
        kart_slot = SimpleNamespace(clut=SimpleNamespace(x=288, y=248))
        paint_window._current_character = CharacterProfile(id="crash", kart_slots=[kart_slot])
        paint_window._current_paintjob.base_character_id = "crash"
        paint_window._current_bundle.mesh.texture_layouts = [SimpleNamespace(palette_x=18, palette_y=248)]
        paint_window._vertex_assembler = SimpleNamespace(assemble=lambda _mesh: SimpleNamespace(
            texture_layout_indices=[1, 0],
            gouraud_color_indices=[(0, 1, 3), (1, 2, 2)],
        ))

        assert paint_window._visible_vertex_indices() == {0, 3}
        assert paint_window._vertex_tab_applies()

    def test_tab_is_hidden_without_kart_vertex_slots(self, paint_window):
        assert paint_window._vertex_tab_applies()

        paint_window._current_character = CharacterProfile(id="crash")

        assert not paint_window._vertex_tab_applies()

    def test_preview_layers_the_skin_over_the_paintjob(self, paint_window):
        paint_window._editor_mode = EditorMode.PREVIEW
        paint_window._preview_paintjob = Paintjob(base_character_id="oxide", vertex_overrides={1: RED, 2: RED})
        paint_window._preview_skin = Skin(character_id="oxide", vertex_overrides={2: BLUE})

        assert paint_window._active_vertex_overrides() == {1: RED, 2: BLUE}

        paint_window._preview_paintjob.base_character_id = "crash"
        assert paint_window._active_vertex_overrides() == {2: BLUE}

    def test_transform_scope_is_the_kart_colors(self, paint_window):
        assert paint_window._vertex_scope() == {"skin_indices": {1, 2}, "shared_indices": set()}


class TestBaseCharacterUndo:

    def test_undo_restores_the_base_and_its_vertex_overrides(self, paint_window):
        paintjob = paint_window._current_paintjob
        paintjob.vertex_overrides[1] = RED
        paint_window._library.add(paintjob)
        paint_window._paintjob_controller._message = SimpleNamespace(confirm_destructive=lambda *_args: True)

        paint_window._paintjob_controller.apply_metadata(0, SimpleNamespace(
            name="x", author="", base_character_id="crash",
        ))
        assert (paintjob.base_character_id, paintjob.vertex_overrides) == ("crash", {})

        paint_window._undo_stack.undo()
        assert (paintjob.base_character_id, paintjob.vertex_overrides) == ("oxide", {1: RED})

        paint_window._undo_stack.redo()
        assert (paintjob.base_character_id, paintjob.vertex_overrides) == ("crash", {})


class TestVertexTransformOwnership:

    def test_closing_restores_the_asset_it_was_opened_on_only(self, paint_window):
        first = paint_window._current_paintjob
        first.vertex_overrides[2] = BLUE
        paint_window._on_vertex_transform_requested()
        paint_window._on_vertex_transform_preview({1: RED})
        assert first.vertex_overrides == {1: RED, 2: BLUE}

        second = Paintjob(base_character_id="oxide", vertex_overrides={2: RED})
        paint_window._paintjob_controller._current = second
        paint_window._close_vertex_transform()

        assert first.vertex_overrides == {2: BLUE}
        assert second.vertex_overrides == {2: RED}

    def test_selecting_another_paintjob_reverts_the_preview(self, paint_window):
        paintjob = paint_window._current_paintjob
        paint_window._on_vertex_transform_requested()
        paint_window._on_vertex_transform_preview({1: RED})

        paint_window._on_paintjob_selection_changed(None)

        assert paintjob.vertex_overrides == {}
        assert not paint_window._vertex_transform_dialog.isVisible()


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
