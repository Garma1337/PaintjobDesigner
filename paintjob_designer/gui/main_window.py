# coding: utf-8

from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from paintjob_designer.color.converter import ColorConverter
from paintjob_designer.color.gradient import GradientGenerator
from paintjob_designer.color.transform import ColorTransformer
from paintjob_designer.config.iso_root_validator import IsoRootValidator
from paintjob_designer.config.store import AppConfig, ConfigStore
from paintjob_designer.core import Slugifier
from paintjob_designer.ctr.vertex_assembler import VertexAssembler
from paintjob_designer.gui.command.bulk_transform_command import BulkColorEdit, BulkTransformCommand
from paintjob_designer.gui.command.reset_slot_command import ResetSlotCommand
from paintjob_designer.gui.command.set_slot_color_command import SetSlotColorCommand
from paintjob_designer.gui.controller.animation_controller import AnimationController
from paintjob_designer.gui.controller.paintjob_library_controller import PaintjobLibraryController
from paintjob_designer.gui.controller.palette_library_controller import PaletteLibraryController
from paintjob_designer.gui.controller.profile_holder import ProfileHolder
from paintjob_designer.gui.controller.skin_library_controller import SkinLibraryController
from paintjob_designer.gui.controller.transform_panel_coordinator import TransformPanelCoordinator
from paintjob_designer.gui.controller.wheel_library_controller import WheelLibraryController
from paintjob_designer.gui.dialog.gradient_fill_dialog import GradientFillDialog
from paintjob_designer.gui.dialog.multi_region_texture_import_dialog import MultiRegionTextureImportDialog
from paintjob_designer.gui.dialog.palette_apply_dialog import PaletteApplyDialog
from paintjob_designer.gui.editor_mode import EditorMode
from paintjob_designer.gui.handler.character_handler import BroughtUpCharacter, CharacterHandler
from paintjob_designer.gui.handler.color_handler import ColorHandler
from paintjob_designer.gui.handler.project_handler import ProjectHandler
from paintjob_designer.gui.util.dialogs import FilePicker, MessageDialog
from paintjob_designer.gui.widget.collapsible_tab_widget import CollapsibleTabWidget
from paintjob_designer.gui.widget.color_picker import PsxColorPicker
from paintjob_designer.gui.widget.kart_viewer import KartViewer, NullKartViewer
from paintjob_designer.gui.widget.preview_sidebar import PreviewSidebar
from paintjob_designer.gui.widget.slot_editor import SlotEditor
from paintjob_designer.gui.widget.vertex_slot_editor import VertexSlotEditor
from paintjob_designer.models import (
    CharacterProfile,
    KartType,
    Paintjob,
    PaintjobLibrary,
    Palette,
    PaletteLibrary,
    Profile,
    SkippedCharacter,
    PsxColor,
    Rgb888,
    Skin,
    SkinLibrary,
    SlotColors,
    SlotRegionPixels,
    SlotRegions,
    WHEEL_FRAME_SIZE,
    WHEEL_SLOT_NAMES,
    Wheel,
    WheelLibrary,
)
from paintjob_designer.profile.loader import ProfileLoader
from paintjob_designer.render.atlas_renderer import AtlasRenderer
from paintjob_designer.render.atlas_uv_mapper import AtlasUvMapper
from paintjob_designer.render.blend_mode_grouper import BlendModeGrouper
from paintjob_designer.render.preview_image_writer import PreviewImageWriter
from paintjob_designer.render.ray_picker import RayTrianglePicker
from paintjob_designer.render.wheel_geometry import (
    SIDE_FRAME,
    TREAD_FRAME,
    WHEEL_CENTERS,
    WHEEL_HALF_SIZE,
    WheelGeometry,
)
from paintjob_designer.texture.multi_region_texture_importer import MultiRegionTextureImporter
from paintjob_designer.texture.single_region_texture_importer import (
    SingleRegionTextureImporter,
    SizeMismatchMode,
)
from paintjob_designer.texture.texture_exporter import TextureExporter
from paintjob_designer.texture.texture_rotator import TextureRotator

_PAINTJOB_EXT = ".json"
_PAINTJOB_FILTER = f"Paintjob (*{_PAINTJOB_EXT})"


class MainWindow(QMainWindow):
    """Top-level window. Owns the editor surface and orchestrates the
    library / palette / skin / preview controllers."""

    def __init__(
        self,
        config_store: ConfigStore,
        iso_root_validator: IsoRootValidator,
        profile_loader: ProfileLoader,
        character_handler: CharacterHandler,
        color_handler: ColorHandler,
        project_handler: ProjectHandler,
        color_converter: ColorConverter,
        color_picker: PsxColorPicker,
        vertex_assembler: VertexAssembler,
        atlas_uv_mapper: AtlasUvMapper,
        color_transformer: ColorTransformer,
        gradient_generator: GradientGenerator,
        ray_picker: RayTrianglePicker,
        blend_mode_grouper: BlendModeGrouper,
        slugifier: Slugifier,
        single_region_texture_importer: SingleRegionTextureImporter,
        multi_region_texture_importer: MultiRegionTextureImporter,
        texture_rotator: TextureRotator,
        texture_exporter: TextureExporter,
        preview_image_writer: PreviewImageWriter,
        wheel_geometry: WheelGeometry,
        skin_writer,
        message: MessageDialog,
        files: FilePicker,
        profile_holder: ProfileHolder,
        paintjob_library_controller: PaintjobLibraryController,
        skin_library_controller: SkinLibraryController,
        wheel_library_controller: WheelLibraryController,
        palette_library_controller: PaletteLibraryController,
        preview_sidebar: PreviewSidebar,
        slot_editor: SlotEditor,
        orphan_slot_editor: SlotEditor,
        vertex_slot_editor: VertexSlotEditor,
        kart_viewer: KartViewer,
    ) -> None:
        super().__init__()
        self._config_store = config_store
        self._validator = iso_root_validator
        self._profile_loader = profile_loader
        self._character_handler = character_handler
        self._color_handler = color_handler
        self._project_handler = project_handler
        self._color_converter = color_converter
        self._color_picker = color_picker
        self._vertex_assembler = vertex_assembler
        self._atlas_uv_mapper = atlas_uv_mapper
        self._color_transformer = color_transformer
        self._gradient_generator = gradient_generator
        self._ray_picker = ray_picker
        self._blend_mode_grouper = blend_mode_grouper
        self._slugifier = slugifier
        self._single_region_texture_importer = single_region_texture_importer
        self._multi_region_texture_importer = multi_region_texture_importer
        self._texture_rotator = texture_rotator
        self._texture_exporter = texture_exporter
        self._preview_image_writer = preview_image_writer
        self._wheel_geometry = wheel_geometry
        self._skin_writer = skin_writer
        self._message = message
        self._files = files
        self._profile_holder = profile_holder

        self._paintjob_controller = paintjob_library_controller
        self._skin_controller = skin_library_controller
        self._wheel_controller = wheel_library_controller
        self._palette_controller = palette_library_controller

        self._preview_sidebar = preview_sidebar
        self._slot_editor = slot_editor
        self._orphan_slot_editor = orphan_slot_editor
        self._vertex_editor = vertex_slot_editor
        self._kart_viewer = kart_viewer
        # Both editors fan out the same per-slot updates — `update_color` /
        # `set_slot_colors` are no-ops when a slot isn't owned by that editor.
        self._slot_editors: tuple[SlotEditor, ...] = (slot_editor, orphan_slot_editor)

        # Make sidebars discoverable via short aliases — most editor
        # logic still asks for them by name. Controllers own the actual
        # sidebar widgets and wire their internal signals.
        self._sidebar = self._paintjob_controller._sidebar
        self._skin_sidebar = self._skin_controller._sidebar
        self._wheel_sidebar = self._wheel_controller._sidebar
        self._palette_sidebar = self._palette_controller._sidebar

        # Sidebar row labels resolve raw character ids to display names
        # via the profile holder. Installed once here; the holder is a
        # mutable cell so the resolver picks up new profiles without
        # being re-wired.
        self._sidebar.set_character_resolver(self._profile_holder.display_name_for)
        self._skin_sidebar.set_character_resolver(self._profile_holder.display_name_for)

        self._config: AppConfig = self._config_store.load()
        self._profile: Profile | None = None

        # Hydrate library state from the persisted config and hand it
        # to the controllers — they own all read/write access from here
        # on.
        self._paintjob_controller.replace_library(
            self.restore_library(self._config.library, PaintjobLibrary),
        )
        self._skin_controller.replace_library(
            self.restore_library(self._config.skins, SkinLibrary),
        )
        self._wheel_controller.replace_library(
            self.restore_library(self._config.wheels, WheelLibrary),
        )
        self._palette_controller.replace_library(
            self._restore_palette_library_from_config(),
        )

        self._editor_mode: EditorMode = EditorMode.PAINTJOB
        self._preview_paintjob: Paintjob | None = None
        self._preview_skin: Skin | None = None
        self._preview_wheel: Wheel | None = None

        self._wire_controller_signals()

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(500)
        self._autosave_timer.timeout.connect(self._flush_autosave)

        # `_current_character` is the PREVIEW character — the mesh the 3D
        # viewer shows and the VRAM we sample defaults from. It's driven by
        # the preview-character combo at the top of the viewer pane, NOT
        # the sidebar (which lists assets).
        self._current_character: CharacterProfile | None = None
        self._current_bundle: BroughtUpCharacter | None = None

        # Per-tab preview-character memory: keyed by editor mode, value is
        # the last character_id the user picked while that tab was active. On tab change we restore that
        # character if it's still in the new combo's list, falling back
        # to the first compatible character when not.
        self._remembered_character_id: dict[EditorMode, str] = {}

        # Slot / vertex → triangle indices for the focus-highlight overlay.
        # Vertex mask treats a triangle as affected if any of its 3 vertices
        # samples the selected gouraud index.
        self._slot_triangle_mask: dict[str, list[int]] = {}
        self._vertex_triangle_mask: dict[int, list[int]] = {}
        self._vertex_usage_cache: tuple[BroughtUpCharacter, tuple[set[int], set[int]]] | None = None

        # Lazy-created on first open and reused so slider state survives
        # Apply→Apply→Close cycles.
        self._vertex_transform_dialog = None
        self._vertex_transform_snapshot: dict | None = None
        self._vertex_transform_dirty: set[int] = set()

        # One undo stack for the whole session. Clicking between characters
        # doesn't clear it — Ctrl+Z still unwinds edits across character
        # boundaries, which matches what users expect from a single-editor app.
        self._undo_stack = QUndoStack(self)

        # Every undo-routed edit (color set, reset, bulk transform, palette
        # apply) advances the stack index. Hook that for autosave so the
        # color-edit path doesn't need an explicit `_schedule_autosave()`
        # at each mutation site.
        self._undo_stack.indexChanged.connect(self._schedule_autosave)

        self._transform = TransformPanelCoordinator(
            color_transformer=self._color_transformer,
            color_converter=self._color_converter,
            color_handler=self._color_handler,
            slot_editor_provider=lambda: self._slot_editor,
            kart_viewer_provider=lambda: self._kart_viewer,
            bundle_provider=lambda: self._current_bundle,
            asset_provider=self._active_asset,
            character_provider=lambda: self._current_character,
            editor_mode_provider=lambda: self._editor_mode,
            iso_root_provider=lambda: self._config.iso_root,
            undo_stack=self._undo_stack,
            color_picker=self._color_picker,
            parent_widget=self,
        )

        self._animation = AnimationController(
            vertex_assembler=self._vertex_assembler,
            bundle_provider=lambda: self._current_bundle,
            on_positions=lambda pos: self._kart_viewer.set_frame_positions(pos),
            on_wheels_rolling=lambda rolling: self._kart_viewer.set_wheels_rolling(rolling),
            parent=self,
        )

        self.resize(1440, 900)
        self.setAcceptDrops(True)
        self.setWindowTitle("Paintjob Designer")

        self._build_menu_bar()
        self._build_ui()
        self._palette_controller.show_initial()
        self._bootstrap()

    @property
    def _library(self) -> PaintjobLibrary:
        return self._paintjob_controller.library

    @property
    def _skin_library(self) -> SkinLibrary:
        return self._skin_controller.library

    @property
    def _wheel_library(self) -> WheelLibrary:
        return self._wheel_controller.library

    @property
    def _palette_library(self) -> PaletteLibrary:
        return self._palette_controller.library

    @property
    def _current_paintjob(self) -> Paintjob | None:
        return self._paintjob_controller.current

    @property
    def _current_skin(self) -> Skin | None:
        return self._skin_controller.current

    @property
    def _current_wheel(self) -> Wheel | None:
        return self._wheel_controller.current

    def _wire_controller_signals(self) -> None:
        """Forward controller events to the editor-side handlers."""
        pjc = self._paintjob_controller
        pjc.selection_changed.connect(self._on_paintjob_selection_changed)
        pjc.library_changed.connect(self._on_library_changed)
        pjc.library_reset.connect(self._invalidate_undo)
        pjc.mutated.connect(self._schedule_autosave)

        skc = self._skin_controller
        skc.selection_changed.connect(self._on_skin_selection_changed)
        skc.library_changed.connect(self._on_library_changed)
        skc.library_reset.connect(self._invalidate_undo)
        skc.mutated.connect(self._schedule_autosave)

        whc = self._wheel_controller
        whc.selection_changed.connect(self._on_wheel_selection_changed)
        whc.library_changed.connect(self._on_library_changed)
        whc.library_reset.connect(self._invalidate_undo)
        whc.mutated.connect(self._schedule_autosave)

        plc = self._palette_controller
        plc.save_from_slot_requested.connect(self._on_save_palette_from_slot)
        plc.mutated.connect(self._schedule_autosave)

    def _invalidate_undo(self) -> None:
        """Drop the undo history: its commands hold refs to the replaced SlotColors."""
        if hasattr(self, "_undo_stack"):
            self._undo_stack.clear()

    def _on_library_changed(self) -> None:
        if hasattr(self, "_preview_sidebar"):
            self._sync_preview_sidebar_sources()

    def dragEnterEvent(self, event) -> None:
        if self._drop_path(event) is not None:
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if self._drop_path(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = self._drop_path(event)
        if path is None:
            return

        event.acceptProposedAction()

        self._paintjob_controller.import_file(path)

    def _drop_path(self, event) -> Path | None:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None

        urls = [u for u in mime.urls() if u.isLocalFile()]
        if len(urls) != 1:
            return None

        path = Path(urls[0].toLocalFile())
        if not path.name.lower().endswith(_PAINTJOB_EXT):
            return None

        return path

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_action(
            file_menu, "&Load ISO...", self._on_load_iso,
            shortcut=QKeySequence("Ctrl+L"),
        )

        file_menu.addSeparator()
        self._add_action(
            file_menu, "Export Paintjob &Library As...",
            self._paintjob_controller.export_library,
            shortcut=QKeySequence("Ctrl+Shift+S"),
        )
        self._add_action(
            file_menu, "&Import Paintjobs...",
            lambda: self._paintjob_controller.import_files(
                self._config.iso_root or None,
            ),
            shortcut=QKeySequence("Ctrl+O"),
        )

        file_menu.addSeparator()
        self._add_action(
            file_menu, "Export &Skin Library As...",
            self._skin_controller.export_library,
        )
        self._add_action(
            file_menu, "Import S&kins...",
            lambda: self._skin_controller.import_files(
                self._config.iso_root or None,
            ),
        )

        file_menu.addSeparator()
        self._add_action(
            file_menu, "Export &Wheel Library As...",
            self._wheel_controller.export_library,
        )
        self._add_action(
            file_menu, "Import W&heels...",
            lambda: self._wheel_controller.import_files(
                self._config.iso_root or None,
            ),
        )

        file_menu.addSeparator()
        self._export_preview_action = self._add_action(
            file_menu, "Export Preview as &Image...", self._on_export_preview_image,
            shortcut=QKeySequence("Ctrl+E"),
        )

        file_menu.addSeparator()
        self._add_action(
            file_menu, "E&xit", self.close,
            shortcut=QKeySequence.StandardKey.Quit,
        )

        edit_menu = menubar.addMenu("&Edit")
        undo_action = self._undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        redo_action = self._undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)

        view_menu = menubar.addMenu("&View")
        self._reset_camera_action = self._add_action(
            view_menu, "Reset &Camera", self._on_reset_camera,
            shortcut=QKeySequence("R"),
        )

    def _add_action(
        self,
        menu: QMenu,
        text: str,
        slot,
        shortcut: QKeySequence | None = None,
    ) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)

        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)

        self._preview_sidebar.composition_changed.connect(
            self._on_preview_composition_changed,
        )

        # Palettes are paintjob-only (vertex/skin slots don't draw from
        # them), so they live nested inside the Paintjobs tab as a second
        # vertically-stacked section rather than as their own top-level
        # tab. Splitter so the artist can grow the palette area when
        # they're palette-heavy and shrink it otherwise.
        paintjobs_tab = QWidget()
        paintjobs_tab_layout = QVBoxLayout(paintjobs_tab)
        paintjobs_tab_layout.setContentsMargins(0, 0, 0, 0)
        paintjobs_tab_layout.setSpacing(4)

        paintjobs_inner_split = QSplitter(Qt.Orientation.Vertical)
        paintjobs_inner_split.addWidget(self._sidebar)

        palette_section = QWidget()
        palette_section_layout = QVBoxLayout(palette_section)
        palette_section_layout.setContentsMargins(0, 0, 0, 0)
        palette_section_layout.setSpacing(2)
        palette_header = QLabel("Color Palettes")
        palette_header.setStyleSheet("color: #aaa; padding: 2px 4px;")
        palette_section_layout.addWidget(palette_header)
        palette_section_layout.addWidget(self._palette_sidebar, 1)
        paintjobs_inner_split.addWidget(palette_section)

        paintjobs_inner_split.setStretchFactor(0, 3)
        paintjobs_inner_split.setStretchFactor(1, 2)
        paintjobs_tab_layout.addWidget(paintjobs_inner_split, 1)

        self._sidebar_tabs = QTabWidget()
        self._sidebar_tabs.addTab(paintjobs_tab, "Paintjobs")
        self._sidebar_tabs.addTab(self._skin_sidebar, "Skins")
        self._sidebar_tabs.addTab(self._wheel_sidebar, "Wheels")
        self._sidebar_tabs.addTab(self._preview_sidebar, "Preview")
        self._sidebar_tabs.currentChanged.connect(self._on_sidebar_tab_changed)
        sidebar_layout.addWidget(self._sidebar_tabs, 1)
        sidebar_layout.addWidget(self._animation.panel)

        # Stash for tab-change identity checks: the tab's root widget wraps
        # the paintjob list, so the list itself can't identify the tab.
        self._paintjobs_tab = paintjobs_tab
        self._preview_tab = self._preview_sidebar

        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)

        # Picks which mesh and VRAM defaults the active asset previews on.
        # Hidden in Preview mode, where the sidebar's own combo drives.
        self._preview_strip = QWidget()
        preview_strip_layout = QHBoxLayout(self._preview_strip)
        preview_strip_layout.setContentsMargins(8, 4, 8, 4)
        preview_strip_layout.addWidget(QLabel("Preview on:"))
        self._preview_character_combo = QComboBox()
        self._preview_character_combo.setPlaceholderText("Pick a character to preview…")
        self._preview_character_combo.currentIndexChanged.connect(
            self._on_preview_character_changed,
        )
        preview_strip_layout.addWidget(self._preview_character_combo, 1)
        viewer_layout.addWidget(self._preview_strip)

        self._kart_viewer.gl_init_failed.connect(self._on_gl_init_failed)
        self._kart_viewer.eyedropper_picked.connect(self._on_eyedropper_picked)
        self._kart_viewer.empty_space_context_requested.connect(
            self._on_viewer_context_menu,
        )
        viewer_layout.addWidget(self._kart_viewer, 1)

        for editor in self._slot_editors:
            editor.color_edit_requested.connect(self._on_color_edit_requested)
            editor.slot_reset_requested.connect(self._on_slot_reset_requested)
            editor.slot_focus_changed.connect(self._on_slot_focus_changed)
            editor.context_requested.connect(self._on_slot_editor_context)
            editor.transform_requested.connect(self._on_slot_transform_requested)
            editor.reset_all_requested.connect(self._on_slot_reset_all_requested)

        # Vertex-color editor for the gouraud table; only meaningful in
        # skin mode (paintjobs don't carry vertex overrides). Lives next
        # to the CLUT slot editor in a tab widget so the right pane stays
        # one column wide regardless of which mode is active.
        self._vertex_editor.color_edit_requested.connect(
            self._on_vertex_color_edit_requested,
        )
        self._vertex_editor.vertex_reset_requested.connect(
            self._on_vertex_reset_requested,
        )
        self._vertex_editor.reset_all_requested.connect(
            self._on_vertex_reset_all_requested,
        )
        self._vertex_editor.vertex_focus_changed.connect(
            self._on_vertex_focus_changed,
        )
        self._vertex_editor.context_requested.connect(self._on_vertex_editor_context)
        self._vertex_editor.transform_requested.connect(
            self._on_vertex_transform_requested,
        )

        self._right_tabs = CollapsibleTabWidget()
        self._right_tabs.addTab(self._slot_editor, "CLUT slots")
        self._right_tabs.addTab(self._vertex_editor, "Vertex slots")
        self._right_tabs.addTab(self._orphan_slot_editor, "Orphan Slots")
        self._right_tabs.set_page_visible(self._orphan_slot_editor, False)

        splitter.addWidget(sidebar_container)
        splitter.addWidget(viewer_container)
        splitter.addWidget(self._right_tabs)

        # Stored so `_on_gl_init_failed` can swap the viewer for a placeholder.
        self._splitter = splitter
        self._viewer_container = viewer_container
        self._viewer_container_layout = viewer_layout
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([240, 600, 600])

        self.setCentralWidget(splitter)
        self.setWindowTitle("Paintjob Designer")

        self.statusBar().showMessage("Ready.")

    def _bootstrap(self) -> None:
        if self._validator.validate(self._config.iso_root).ok:
            self._load_profile()
            return

        self.statusBar().showMessage(
            "No ISO loaded — use File → Load ISO... to pick your extracted CTR directory.",
        )

    def _load_profile(self) -> bool:
        """Load the profile for the configured ISO; False when it can't be read."""
        self._paintjob_controller.set_iso_root(self._config.iso_root)
        self._skin_controller.set_iso_root(self._config.iso_root)
        self._wheel_controller.set_iso_root(self._config.iso_root)

        try:
            result = self._profile_loader.load(self._config.iso_root)
        except (OSError, ValueError) as exc:
            self._profile = None
            self._profile_holder.set(None)
            self._clear_preview_render()
            self._populate_preview_character_combo([])
            self._message.error(self, "Could not load characters", str(exc))
            return False

        self._profile = result.profile

        # Push the active profile into the shared holder so the new-asset
        # flows can pick characters and seed slots.
        self._profile_holder.set(self._profile)

        # Fresh profile = fresh context. Drop any per-tab memory from
        # the previous profile (character ids may differ).
        self._remembered_character_id.clear()
        self._clear_preview_render()
        self._populate_preview_character_combo([])
        if hasattr(self, "_preview_sidebar"):
            self._sync_preview_sidebar_sources()

        # Saved libraries are restored before the profile loads, so any
        # rows rendered earlier still show raw character ids. Re-render
        # now that the resolver works.
        self._skin_controller.refresh_sidebar_labels()

        # Auto-select the first paintjob in the active tab (Paintjobs is
        # the default). The selection_changed handler will populate the
        # combo and auto-pick a preview character. The skin controller
        # waits — its first item only auto-selects when the user
        # actually switches to the Skins tab.
        self._paintjob_controller.show_initial_selection()

        if result.skipped:
            self._warn_skipped_characters(result.skipped)

        return True

    def _warn_skipped_characters(self, skipped: list[SkippedCharacter]) -> None:
        details = "\n".join(
            f"  • {c.display_name} — {c.mesh_source}: {c.reason}" for c in skipped
        )
        self._message.warn(
            self, "Some characters could not be loaded",
            "A legitimate NTSC-U copy of the game contains every character, "
            "so this ISO may be broken or modified. Everything else has "
            f"loaded normally.\n\nNot loaded:\n{details}",
        )

    def _populate_preview_character_combo(
        self,
        characters: list[CharacterProfile],
    ) -> None:
        self._preview_character_combo.blockSignals(True)
        self._preview_character_combo.clear()

        for character in characters:
            self._preview_character_combo.addItem(
                character.display_name or character.id, character.id,
            )

        # Force "no selection" — without this Qt sets currentIndex to 0
        # automatically as items are added.
        self._preview_character_combo.setCurrentIndex(-1)
        self._preview_character_combo.blockSignals(False)
        self._preview_character_combo.setEnabled(bool(characters))

    def _clear_preview_render(self) -> None:
        self._current_character = None
        self._current_bundle = None
        self._slot_triangle_mask = {}
        self._vertex_triangle_mask = {}
        for editor in self._slot_editors:
            editor.set_slots([])
        self._right_tabs.set_page_visible(self._orphan_slot_editor, False)
        self._vertex_editor.set_colors([])
        self._kart_viewer.clear()

    def _restore_preview_character(
        self, characters: list[CharacterProfile],
    ) -> None:
        if not characters:
            return

        target_index = 0
        remembered = self._remembered_character_id.get(self._editor_mode)
        if remembered:
            for i in range(self._preview_character_combo.count()):
                if self._preview_character_combo.itemData(i) == remembered:
                    target_index = i
                    break

        # Combo is at -1 from `_populate_preview_character_combo`; setting
        # to a valid index always emits and triggers `_reload_preview`.
        self._preview_character_combo.setCurrentIndex(target_index)

    def _is_iso_ready(self) -> bool:
        return self._validator.validate(self._config.iso_root).ok and self._profile is not None

    def _require_active_paintjob(self) -> bool:
        """Gate for actions that need a selected paintjob in the library."""
        if self._current_paintjob is not None:
            return True

        QMessageBox.information(
            self, "No paintjob selected",
            "Create a paintjob (sidebar → New) or import one from JSON "
            "before performing this action.",
        )

        return False

    def _require_active_asset(self) -> bool:
        """Gate for actions that edit whatever the active mode exposes."""
        if self._editor_mode == EditorMode.PREVIEW:
            QMessageBox.information(
                self, "Preview mode is read-only",
                "The Preview tab combines existing paintjobs and skins to "
                "show how they look together — it can't be edited. Switch "
                "to the Paintjobs or Skins tab to make changes.",
            )

            return False

        if self._active_asset() is not None:
            return True

        if self._editor_mode == EditorMode.SKIN:
            QMessageBox.information(
                self, "No skin selected",
                "Create a skin (Skins tab → New) or pick one from the list "
                "before performing this action.",
            )
        elif self._editor_mode == EditorMode.WHEEL:
            QMessageBox.information(
                self, "No wheel selected",
                "Create a wheel (Wheels tab → New) or pick one from the list "
                "before performing this action.",
            )
        else:
            QMessageBox.information(
                self, "No paintjob selected",
                "Create a paintjob (sidebar → New) or import one from JSON "
                "before performing this action.",
            )

        return False

    def _on_load_iso(self) -> None:
        chosen = self._files.pick_directory(
            self, "Select extracted CTR ISO root",
            self._config.iso_root or None,
        )

        if chosen is None:
            return

        chosen = str(chosen)

        result = self._validator.validate(chosen)
        if not result.ok:
            QMessageBox.warning(
                self, "Not a valid CTR ISO",
                "The selected directory is missing required files:\n\n"
                + "\n".join(f"  • {p}" for p in result.missing),
            )

            return

        self._config.iso_root = chosen
        self._config_store.save(self._config)
        self._character_handler.invalidate_vram_cache()

        # A fresh ISO invalidates every in-flight asset (character IDs may
        # change between profiles). Reset all three libraries via their
        # controllers — undo history clears via the library_reset signal.
        self._paintjob_controller.replace_library(PaintjobLibrary())
        self._skin_controller.replace_library(SkinLibrary())
        self._wheel_controller.replace_library(WheelLibrary())
        self._current_character = None
        self._current_bundle = None
        self._schedule_autosave()

        if self._load_profile():
            self.statusBar().showMessage(
                "ISO loaded. Create a paintjob (sidebar → New) or import one to begin.",
            )

    @staticmethod
    def restore_library(raw, library_type):
        """Rehydrate a persisted library blob, or an empty one if it's unusable."""
        if not isinstance(raw, dict):
            return library_type()

        try:
            return library_type.model_validate(raw)
        except Exception:
            return library_type()

    def _restore_palette_library_from_config(self) -> PaletteLibrary:
        """Rehydrate the persisted palette library from the config list."""
        raw = self._config.palettes
        if not isinstance(raw, list):
            return PaletteLibrary()

        palettes: list[Palette] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue

            try:
                palettes.append(Palette.model_validate(entry))
            except Exception:
                continue

        return PaletteLibrary(palettes=palettes)

    def _schedule_autosave(self) -> None:
        """Kick the debounced autosave; coalesces bursty mutation sequences."""
        self._autosave_timer.start()

    def _flush_autosave(self) -> None:
        """Serialize the current library + palette library + skin library
        into the config."""
        try:
            self._config.library = self._library.model_dump(by_alias=True)
            self._config.palettes = [
                p.model_dump() for p in self._palette_library.palettes
            ]
            self._config.skins = self._skin_library.model_dump(by_alias=True)
            self._config.wheels = self._wheel_library.model_dump(by_alias=True)
            self._config_store.save(self._config)
        except OSError:
            self.statusBar().showMessage(
                "Autosave failed — check disk space / permissions.", 4000,
            )

    def closeEvent(self, event) -> None:
        """Confirm on close, then flush a final autosave before exiting."""
        confirm = QMessageBox.question(
            self, "Exit Paintjob Designer?",
            "Exit Paintjob Designer?\n\n"
            "Your library is autosaved and will reopen the way you left it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        # Rewind any live transform preview so the autosaved state is the
        # last committed one, not the in-flight slider preview.
        self._transform.close_pending_preview()

        self._autosave_timer.stop()
        self._flush_autosave()

        event.accept()

    def _on_save_palette_from_slot(self) -> None:
        """Capture the focused slot's 16 colors and hand them to the palette controller."""
        if self._current_bundle is None or self._current_paintjob is None:
            self._message.info(
                self, "No slot to capture",
                "Select a paintjob and highlight a slot row first — the "
                "palette captures that slot's 16 colors.",
            )

            return

        slot_name = next(
            (e.focused_slot() for e in self._slot_editors if e.focused_slot()),
            None,
        )
        if slot_name is None:
            self._message.info(
                self, "No focused slot",
                "Click a slot row in the editor to highlight it; the "
                "palette captures the highlighted slot's colors.",
            )

            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        colors = [
            PsxColor(value=self._current_color(slot, i).value)
            for i in range(SlotColors.SIZE)
        ]

        self._palette_controller.add_from_colors(colors, f"{slot_name} palette")

    def _on_apply_palette_to_slot(self, palette_index: int, slot_name: str) -> None:
        """Open the mapping dialog for `palette_index` targeting `slot_name`."""
        if palette_index < 0 or palette_index >= len(self._palette_library.palettes):
            return

        if self._current_bundle is None or not self._require_active_asset():
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        palette = self._palette_library.palettes[palette_index]
        asset = self._active_asset()

        dialog = PaletteApplyDialog(
            palette=palette,
            paintjob_name=asset.name,
            slot_name=slot_name,
            color_converter=self._color_converter,
            parent=self,
        )

        if dialog.exec() != PaletteApplyDialog.DialogCode.Accepted:
            return

        ordered = dialog.ordered_colors()
        if not ordered:
            return

        edits: list[BulkColorEdit] = []
        for color_index, new_color in enumerate(ordered[:SlotColors.SIZE]):
            old = PsxColor(value=self._current_color(slot, color_index).value)

            if old.value == new_color.value:
                continue

            edits.append(BulkColorEdit(
                asset=asset,
                slot=slot,
                color_index=color_index,
                old_color=old,
                new_color=PsxColor(value=new_color.value),
            ))

        if not edits:
            self.statusBar().showMessage(
                f"Palette '{palette.name}' already matches {slot_name}.",
            )

            return

        self.apply_bulk_edits_from_command(
            [(e.asset, e.slot, e.color_index, e.new_color) for e in edits],
        )

        label = f"Apply palette '{palette.name or '(unnamed)'}' to {slot_name}"
        self._undo_stack.push(BulkTransformCommand(self, label, edits))

    def _on_reset_camera(self) -> None:
        self._kart_viewer.reset_camera()

    def _on_viewer_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction(self._reset_camera_action)
        menu.addAction(self._export_preview_action)
        menu.exec(global_pos)

    def _on_export_preview_image(self) -> None:
        """Save the 3D viewer's current frame as a PNG / JPEG / WebP image."""
        capture = self._kart_viewer.capture_rgba()
        if capture is None:
            self._message.info(
                self, "Nothing to export",
                "Pick a character to preview before exporting an image.",
            )

            return

        character_id = self._current_character.id if self._current_character else "preview"
        default_path = Path(self._config.iso_root or Path.home()) / f"{character_id}_preview.png"
        save_path = self._files.pick_save_path(
            self, "Export preview image", default_path,
            "PNG images (*.png);;JPEG images (*.jpg *.jpeg);;WebP images (*.webp)",
        )

        if save_path is None:
            return

        if save_path.suffix.lower() not in PreviewImageWriter.FORMATS:
            save_path = save_path.with_name(f"{save_path.name}.png")

        rgba, width, height = capture
        try:
            self._preview_image_writer.write(
                rgba, width, height, save_path,
                jpeg_background=self._kart_viewer.background_rgb(),
            )
        except (OSError, ValueError) as exc:
            self._message.error(self, "Export failed", str(exc))

            return

        self.statusBar().showMessage(f"Exported preview → {save_path}")

    def _on_gl_init_failed(self, reason: str) -> None:
        """Replace the 3D viewer with a placeholder when the GL context fails."""
        placeholder = QLabel(
            "3D preview unavailable.\n\n"
            "Your system's OpenGL support is insufficient for the kart viewer "
            "(requires OpenGL 3.3 core profile). You can still edit and export "
            "paintjobs — only the live 3D render is disabled.\n\n"
            f"Details: {reason}"
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("QLabel { background: #1f2024; color: #cccccc; padding: 24px; }")

        # The viewer is wrapped in a container that also holds the preview-
        # character combo above it. Replace just the viewer, not the whole
        # container, so the combo stays visible and functional.
        self._viewer_container_layout.replaceWidget(self._kart_viewer, placeholder)
        self._kart_viewer.deleteLater()

        # Later calls (highlight, set_atlas, ...) would crash on the deleted
        # viewer; this no-op stand-in absorbs them so the rest of the loading
        # path doesn't need to know.
        self._kart_viewer = NullKartViewer()
        self.statusBar().showMessage("3D preview disabled (GL init failed).")

    def _on_preview_character_changed(self, index: int) -> None:
        """Driven by the preview-character combo above the 3D viewer."""
        if self._profile is None or index < 0:
            return

        character_id = self._preview_character_combo.itemData(index)
        character = next(
            (c for c in self._profile.characters if c.id == character_id),
            None,
        )

        if character is None:
            return

        # Revert any in-flight transform preview — it was built against
        # the old character's candidates and would misapply otherwise.
        self._transform.close_pending_preview()

        self._current_character = character
        # Per-tab memory: this is now the character to restore next time
        # the user comes back to this tab.
        if self._editor_mode in (EditorMode.PAINTJOB, EditorMode.SKIN, EditorMode.WHEEL):
            self._remembered_character_id[self._editor_mode] = character.id

        self._reload_preview()

        if self._transform.is_visible():
            self._transform._take_snapshot()
            self._transform.refresh()

    def _reload_preview(self) -> None:
        """Re-render the current preview character with the active asset."""
        if self._current_character is None:
            return

        active = self._active_asset()
        render_asset = active if active is not None else Paintjob()
        try:
            bundle = self._character_handler.load_character(
                self._config.iso_root, self._current_character, render_asset,
            )
        except (OSError, ValueError, EOFError) as exc:
            # ValueError: the mesh changed on disk and samples a CLUT the
            # profile's derived slots don't cover. Picking again won't help
            # until the ISO is reloaded, so say so instead of dying in a slot.
            self.statusBar().showMessage(f"Load failed: {exc}. Reload the ISO if it changed on disk.")
            return

        self._current_bundle = bundle

        self._kart_viewer.set_atlas(
            bundle.atlas_rgba, AtlasRenderer.ATLAS_WIDTH, AtlasRenderer.ATLAS_HEIGHT,
        )

        assembled = self._vertex_assembler.assemble(
            bundle.mesh, vertex_overrides=self._active_vertex_overrides(),
        )
        self._kart_viewer.set_mesh(assembled, bundle.mesh.texture_layouts)
        self._push_wheels_to_viewer(bundle)

        self._slot_triangle_mask = self._build_slot_triangle_mask(assembled, bundle)
        self._vertex_triangle_mask = self._build_vertex_triangle_mask(assembled)

        self._animation.reload()
        self._populate_slot_editor()
        self._populate_vertex_editor()
        self.statusBar().showMessage(
            f"{self._current_character.display_name}: "
            f"{len(bundle.slot_regions.slots)} slots, "
            f"{assembled.triangle_count} triangles",
        )

    def _push_wheels_to_viewer(self, bundle: BroughtUpCharacter) -> None:
        """Place the four wheels; hovercraft characters have none."""
        if self._current_character is None or self._current_character.kart_type != KartType.KART:
            self._kart_viewer.set_wheels(None)
            return

        mesh = bundle.mesh
        centers = np.array([
            self._wheel_geometry.game_to_mesh_space(center, mesh.scale, mesh.frame.offset)
            for center in WHEEL_CENTERS
        ], dtype=np.float32)

        uvs = []
        for frame in range(len(WHEEL_SLOT_NAMES)):
            x, y = self._wheel_geometry.frame_origin(frame)
            u0 = x * 4 / AtlasRenderer.ATLAS_WIDTH
            v0 = y / AtlasRenderer.ATLAS_HEIGHT
            uvs.append((
                u0, v0,
                u0 + WHEEL_FRAME_SIZE / AtlasRenderer.ATLAS_WIDTH,
                v0 + WHEEL_FRAME_SIZE / AtlasRenderer.ATLAS_HEIGHT,
            ))

        atlas = np.frombuffer(bundle.atlas_rgba, dtype=np.uint8).reshape(
            AtlasRenderer.ATLAS_HEIGHT, AtlasRenderer.ATLAS_WIDTH, AtlasRenderer.BYTES_PER_PIXEL,
        )

        def bounds(frame: int):
            x, y = self._wheel_geometry.frame_origin(frame)
            alpha = atlas[y:y + WHEEL_FRAME_SIZE, x * 4:x * 4 + WHEEL_FRAME_SIZE, 3]
            return self._wheel_geometry.opaque_bounds(alpha > 0)

        self._kart_viewer.set_wheels(
            centers, WHEEL_HALF_SIZE / 1020.0, uvs,
            side=bounds(SIDE_FRAME), tread=bounds(TREAD_FRAME),
        )

    def _on_paintjob_selection_changed(self, paintjob: Paintjob | None) -> None:
        """Active paintjob changed — repopulate the combo, restore character.

        The combo is filtered to characters whose `kart_type` matches the
        paintjob. The preview character defaults to whichever character
        the user last viewed paintjobs on (per-tab memory) or the first
        compatible one if that character isn't in the new list.
        """
        self._transform.close_pending_preview()
        self._clear_preview_render()

        if paintjob is None:
            self._populate_preview_character_combo([])
            return

        characters = self._characters_matching_kart_type(paintjob.kart_type)
        self._populate_preview_character_combo(characters)
        self._restore_preview_character(characters)

    def _characters_matching_kart_type(
        self, kart_type: KartType,
    ) -> list[CharacterProfile]:
        if self._profile is None:
            return []

        return [c for c in self._profile.characters if c.kart_type == kart_type]

    def _active_asset(self) -> Paintjob | Skin | Wheel | None:
        """The asset the viewer is currently rendering. Preview mode returns
        a synthesized Paintjob merging the chosen paintjob + skin + wheel slots."""
        if self._editor_mode == EditorMode.PREVIEW:
            return self._build_preview_composite()

        if self._editor_mode == EditorMode.SKIN:
            return self._current_skin

        if self._editor_mode == EditorMode.WHEEL:
            return self._current_wheel

        return self._current_paintjob

    def _build_preview_composite(self) -> Paintjob | None:
        paintjob = self._preview_paintjob
        skin = self._preview_skin
        wheel = self._preview_wheel
        if paintjob is None and skin is None and wheel is None:
            return None

        merged: dict[str, SlotColors] = {}
        if paintjob is not None:
            merged.update(paintjob.slots)

        if skin is not None:
            merged.update(skin.slots)

        if wheel is not None:
            merged.update(wheel.slots)

        return Paintjob(
            name="(preview composite)",
            kart_type=paintjob.kart_type if paintjob is not None else KartType.KART,
            slots=merged,
        )

    def _active_slot_names(self) -> set[str]:
        if self._current_character is None:
            return set()

        if self._editor_mode == EditorMode.PREVIEW:
            return (
                {s.name for s in self._current_character.kart_slots}
                | {s.name for s in self._current_character.skin_slots}
            )

        if self._editor_mode == EditorMode.SKIN:
            return {s.name for s in self._current_character.skin_slots}

        if self._editor_mode == EditorMode.WHEEL:
            return set(WHEEL_SLOT_NAMES)

        return {s.name for s in self._current_character.kart_slots}

    def _active_vertex_overrides(self) -> dict[int, Rgb888]:
        if self._editor_mode == EditorMode.PREVIEW and self._preview_skin is not None:
            return self._preview_skin.vertex_overrides

        if self._editor_mode == EditorMode.SKIN and self._current_skin is not None:
            return self._current_skin.vertex_overrides

        return {}

    def _vertex_tab_applies(self) -> bool:
        """Only skins carry vertex colors; the preview shows them read-only."""
        return self._editor_mode in (EditorMode.SKIN, EditorMode.PREVIEW)

    def _refresh_vertex_tab(self) -> None:
        self._right_tabs.set_page_visible(self._vertex_editor, self._vertex_tab_applies())

    def _populate_vertex_editor(self) -> None:
        self._refresh_vertex_tab()

        if self._current_bundle is None or not self._vertex_tab_applies():
            self._vertex_editor.set_colors([])
            return

        overrides = self._active_vertex_overrides()
        effective: list[Rgb888] = []
        overridden: set[int] = set()
        for i, base in enumerate(self._current_bundle.mesh.gouraud_colors):
            override = overrides.get(i)

            if override is not None:
                effective.append(Rgb888(r=override.r, g=override.g, b=override.b))
                overridden.add(i)
            else:
                effective.append(Rgb888(r=base.r, g=base.g, b=base.b))

        self._vertex_editor.set_colors(effective, overridden=overridden, visible=self._vertex_usage()[0])
        self._vertex_editor.set_editable(
            self._editor_mode == EditorMode.SKIN and self._current_skin is not None,
        )

    def _on_sidebar_tab_changed(self, index: int) -> None:
        """Switch editor mode and restore that tab's preview state.

        Each editing tab keeps its own (asset, preview character) pair.
        Coming back to a tab restores what you were last looking at;
        if you've never visited the tab (or the asset wasn't selected
        yet), the first asset auto-selects and renders on the first
        compatible character.
        """
        widget = self._sidebar_tabs.widget(index)

        if widget is self._paintjobs_tab:
            new_mode = EditorMode.PAINTJOB
        elif widget is self._skin_sidebar:
            new_mode = EditorMode.SKIN
        elif widget is self._wheel_sidebar:
            new_mode = EditorMode.WHEEL
        elif widget is getattr(self, "_preview_tab", None):
            new_mode = EditorMode.PREVIEW
        else:
            return

        if new_mode == self._editor_mode:
            return

        self._editor_mode = new_mode
        self._transform.close_pending_preview()
        self._update_editors_for_mode()
        self._clear_preview_render()

        if new_mode == EditorMode.PREVIEW:
            # Preview tab drives composition from its own combos; the top
            # "Preview on:" strip is redundant there.
            self._preview_strip.setVisible(False)
            self._sync_preview_sidebar_sources()
            return

        self._preview_strip.setVisible(True)
        controller = {
            EditorMode.PAINTJOB: self._paintjob_controller,
            EditorMode.SKIN: self._skin_controller,
            EditorMode.WHEEL: self._wheel_controller,
        }[new_mode]

        if controller.current is None:
            # First entry into this tab — let the controller pick the
            # first item; its selection_changed signal feeds back into
            # `_on_paintjob/_on_skin_selection_changed` which populates
            # the combo and restores the per-tab preview character.
            controller.show_initial_selection()
            return

        # Asset already selected for this tab — repopulate the combo for
        # it and restore the remembered preview character.
        asset = controller.current
        if new_mode == EditorMode.PAINTJOB:
            characters = self._characters_matching_kart_type(asset.kart_type)
        elif new_mode == EditorMode.WHEEL:
            characters = self._characters_matching_kart_type(KartType.KART)
        else:
            characters = self._characters_for_skin(asset)

        self._populate_preview_character_combo(characters)
        self._restore_preview_character(characters)

    def _update_editors_for_mode(self) -> None:
        """Enable or disable the right-pane editor tabs based on current mode."""
        editable = self._editor_mode in (EditorMode.PAINTJOB, EditorMode.SKIN, EditorMode.WHEEL)

        for editor in self._slot_editors:
            editor.setEnabled(editable)

        self._vertex_editor.setEnabled(editable and self._editor_mode == EditorMode.SKIN)
        self._refresh_vertex_tab()
        self._refresh_slot_button_strip()

    def _refresh_slot_button_strip(self) -> None:
        editable = self._editor_mode in (EditorMode.PAINTJOB, EditorMode.SKIN, EditorMode.WHEEL)
        enabled = editable and self._active_asset() is not None

        for editor in self._slot_editors:
            editor.set_button_strip_enabled(enabled)

    def _sync_preview_sidebar_sources(self) -> None:
        """Push current characters + libraries into the Preview sidebar."""
        if self._profile is None:
            return

        self._preview_sidebar.set_sources(
            self._profile.characters, self._library, self._skin_library, self._wheel_library,
        )

    def _on_preview_composition_changed(
        self, character_id: str, paintjob_index: int, skin_index: int, wheel_index: int,
    ) -> None:
        """Sidebar combos changed — rebuild the preview composite + reload."""
        if self._profile is None:
            return

        character = next(
            (c for c in self._profile.characters if c.id == character_id), None,
        )

        if 0 <= paintjob_index < self._library.count():
            self._preview_paintjob = self._library.paintjobs[paintjob_index]
        else:
            self._preview_paintjob = None

        if 0 <= skin_index < self._skin_library.count():
            self._preview_skin = self._skin_library.skins[skin_index]
        else:
            self._preview_skin = None

        if 0 <= wheel_index < self._wheel_library.count():
            self._preview_wheel = self._wheel_library.wheels[wheel_index]
        else:
            self._preview_wheel = None

        if self._editor_mode != EditorMode.PREVIEW:
            return

        if character is None:
            return

        self._current_character = character
        self._reload_preview()

    def _characters_for_skin(self, skin: Skin) -> list[CharacterProfile]:
        """The single bound character a skin can be previewed on (or empty
        when the saved skin references a character missing from the
        active profile)."""
        if self._profile is None:
            return []

        return [
            c for c in self._profile.characters if c.id == skin.character_id
        ]

    def _on_skin_selection_changed(self, skin: Skin | None) -> None:
        """Active skin changed — repopulate the combo and render."""
        self._transform.close_pending_preview()
        self._clear_preview_render()

        if skin is None:
            self._populate_preview_character_combo([])
            return

        characters = self._characters_for_skin(skin)
        self._populate_preview_character_combo(characters)
        self._restore_preview_character(characters)

    def _on_wheel_selection_changed(self, wheel: Wheel | None) -> None:
        """Active wheel changed — wheels fit every kart character."""
        self._transform.close_pending_preview()
        self._clear_preview_render()

        if wheel is None:
            self._populate_preview_character_combo([])
            return

        characters = self._characters_matching_kart_type(KartType.KART)
        self._populate_preview_character_combo(characters)
        self._restore_preview_character(characters)

    def _build_slot_triangle_mask(
        self, assembled, bundle: BroughtUpCharacter,
    ) -> dict[str, list[int]]:
        """Group triangles by the slot they belong to for highlight focus."""
        layout_to_slot: dict[int, str] = {}
        for slot_name, regions in bundle.slot_regions.all_slots():
            for region in regions.regions:
                for layout_idx in region.texture_layout_indices:
                    layout_to_slot[layout_idx] = slot_name

        mask: dict[str, list[int]] = {}
        for tri_idx, one_based in enumerate(assembled.texture_layout_indices):
            if one_based == 0:
                continue   # Untextured triangle — no slot ownership.

            slot = layout_to_slot.get(one_based - 1)
            if slot is not None:
                mask.setdefault(slot, []).append(tri_idx)

        return mask

    def _build_vertex_triangle_mask(self, assembled) -> dict[int, list[int]]:
        # A triangle appears under every distinct gouraud index its 3 vertices sample.
        mask: dict[int, list[int]] = {}
        for tri_idx, indices in enumerate(assembled.gouraud_color_indices):
            for color_index in set(indices):
                mask.setdefault(color_index, []).append(tri_idx)

        return mask

    def _on_slot_focus_changed(self, slot_name) -> None:
        if slot_name is None:
            self._kart_viewer.set_highlighted_triangles(None)
        else:
            self._kart_viewer.set_highlighted_triangles(
                self._slot_triangle_mask.get(slot_name, []),
            )

        # Focus changes pick which slot "This slot" scope targets in the
        # transform panel, so re-push candidates whenever it shifts.
        if self._transform.is_visible():
            self._transform.refresh()

    def _populate_slot_editor(self) -> None:
        """Refresh both slot-editor tabs (mesh-mapped + orphan) for the active asset + preview."""
        if self._current_bundle is None:
            for editor in self._slot_editors:
                editor.set_slots([])

            self._right_tabs.set_page_visible(self._orphan_slot_editor, False)
            return

        mode_slots = self._active_slot_names()
        mesh_mapped: dict[str, SlotRegions] = {}
        orphan: dict[str, SlotRegions] = {}

        for name, regions in self._current_bundle.slot_regions.slots.items():
            if name not in mode_slots:
                continue

            if regions.regions:
                mesh_mapped[name] = regions
            else:
                orphan[name] = regions

        self._populate_one_slot_editor(self._slot_editor, mesh_mapped)
        self._populate_one_slot_editor(self._orphan_slot_editor, orphan)
        self._right_tabs.set_page_visible(self._orphan_slot_editor, bool(orphan))
        self._refresh_slot_button_strip()

    def _populate_one_slot_editor(
        self, editor: SlotEditor, slots: dict[str, SlotRegions],
    ) -> None:
        slot_names = self._ordered_slot_names(slots.keys())
        dimensions = {
            name: self._slot_dimension_hint(slots[name])
            for name in slot_names
        }

        editor.set_slots(slot_names, dimensions=dimensions)

        active = self._active_asset()
        for slot_name, slot in slots.items():
            if active is not None and slot_name in active.slots:
                colors = list(active.slots[slot_name].colors)
            else:
                colors = self._color_handler.default_slot_colors(
                    self._config.iso_root, slot,
                )

            editor.set_slot_colors(slot_name, colors)

    def _slot_dimension_hint(self, slot_regions) -> str:
        """Pixel-space size hint shown next to a slot label in the editor."""
        if not slot_regions.regions:
            return ""

        sizes: list[str] = []
        for region in slot_regions.regions:
            pixel_w, pixel_h = region.pixel_dimensions
            sizes.append(f"{pixel_w}x{pixel_h}")

        return " + ".join(sizes)

    def _ordered_slot_names(self, names) -> list[str]:
        """Sort slot names by the current character's profile order."""
        name_set = set(names)
        if self._current_character is None:
            return sorted(name_set)

        profile_order = [s.name for s in self._current_character.slots]
        ordered = [n for n in profile_order if n in name_set]
        extras = sorted(name_set - set(profile_order))
        return ordered + extras

    def _defaults_by_slot_for_current(self) -> dict[str, list[PsxColor]]:
        """VRAM-default CLUT for every slot the current character owns."""
        if self._current_bundle is None:
            return {}

        return {
            slot_name: self._color_handler.default_slot_colors(
                self._config.iso_root, slot,
            )
            for slot_name, slot in self._current_bundle.slot_regions.all_slots()
        }

    def _on_color_edit_requested(self, slot_name: str, color_index: int) -> None:
        if self._current_bundle is None or not self._require_active_asset():
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        old_color = self._current_color(slot, color_index)
        new_color = self._color_picker.pick(old_color, parent=self)
        if new_color is None or new_color.value == old_color.value:
            return

        # Apply immediately so the user sees the change, then push a
        # command that represents the same operation so it can be reversed.
        # SetSlotColorCommand's first redo is a no-op. Routes through the
        # active asset — every asset type has the same `.slots` shape so
        # the apply path duck-types on it.
        asset = self._active_asset()
        self.apply_color_edit_from_command(asset, slot, color_index, new_color)
        self._undo_stack.push(SetSlotColorCommand(
            self, asset, slot, color_index, old_color, new_color,
        ))

    def _on_vertex_transform_requested(self) -> None:
        """Open the modeless vertex transform panel.

        Mirrors the slot transform panel's UX: live preview as sliders
        move, Apply commits + resets sliders for the next pass, Close
        reverts any in-flight preview.
        """
        if (
            self._editor_mode != EditorMode.SKIN
            or self._current_skin is None
            or self._current_bundle is None
        ):
            return

        self._ensure_vertex_transform_dialog()
        self._vertex_transform_dialog.set_colors(
            self._current_vertex_effective_colors(),
            **self._vertex_scope(),
        )

        if not self._vertex_transform_dialog.isVisible():
            self._vertex_transform_snapshot = dict(
                self._current_skin.vertex_overrides,
            )
            self._vertex_transform_dirty = set()
            self._vertex_transform_dialog.show()
        else:
            self._vertex_transform_dialog.raise_()
            self._vertex_transform_dialog.activateWindow()

    def _vertex_usage(self) -> tuple[set[int], set[int]]:
        """(character, kart) gouraud indices. Kart triangles are the ones
        textured with a kart-slot CLUT; every other triangle, untextured ones
        included, belongs to the character. The two share one color table."""
        if self._current_bundle is None or self._current_character is None:
            return set(), set()

        cached = self._vertex_usage_cache
        if cached is not None and cached[0] is self._current_bundle:
            return cached[1]

        mesh = self._current_bundle.mesh
        kart_cluts = {(s.clut.x, s.clut.y) for s in self._current_character.kart_slots}
        assembled = self._vertex_assembler.assemble(mesh)
        character: set[int] = set()
        kart: set[int] = set()
        for layout_index, indices in zip(assembled.texture_layout_indices, assembled.gouraud_color_indices):
            layout = mesh.texture_layouts[layout_index - 1] if layout_index != 0 else None
            if layout is not None and (layout.palette_x * 16, layout.palette_y) in kart_cluts:
                kart.update(indices)
            else:
                character.update(indices)

        self._vertex_usage_cache = (self._current_bundle, (character, kart))
        return character, kart

    def _vertex_scope(self) -> dict[str, set[int]]:
        character, kart = self._vertex_usage()
        return {"skin_indices": character, "shared_indices": character & kart}

    def _ensure_vertex_transform_dialog(self) -> None:
        if self._vertex_transform_dialog is not None:
            return

        from paintjob_designer.gui.dialog.vertex_transform_dialog import (
            VertexTransformDialog,
        )

        dialog = VertexTransformDialog(
            color_transformer=self._color_transformer,
            color_converter=self._color_converter,
            color_picker=self._color_picker,
            parent=self,
        )
        dialog.preview_changed.connect(self._on_vertex_transform_preview)
        dialog.commit_requested.connect(self._on_vertex_transform_commit)
        dialog.closing.connect(self._on_vertex_transform_closing)
        self._vertex_transform_dialog = dialog

    def _current_vertex_effective_colors(self) -> list[Rgb888]:
        if self._current_skin is None or self._current_bundle is None:
            return []

        overrides = self._current_skin.vertex_overrides
        result: list[Rgb888] = []

        for i, base in enumerate(self._current_bundle.mesh.gouraud_colors):
            override = overrides.get(i)
            if override is not None:
                result.append(Rgb888(r=override.r, g=override.g, b=override.b))
            else:
                result.append(Rgb888(r=base.r, g=base.g, b=base.b))

        return result

    def _on_vertex_transform_preview(self, preview_overrides) -> None:
        """Reverts to the open-time snapshot first so cross-pass drift cleans
        up (e.g. a slider that previously dirtied v17 is now back to zero —
        v17 must drop back to its snapshot value).
        """
        if (
            self._current_skin is None
            or self._current_bundle is None
            or self._vertex_transform_snapshot is None
        ):
            return

        self._current_skin.vertex_overrides.clear()
        self._current_skin.vertex_overrides.update(self._vertex_transform_snapshot)

        for index, color in preview_overrides.items():
            base = self._current_bundle.mesh.gouraud_colors[index]
            if (color.r, color.g, color.b) == (base.r, base.g, base.b):
                self._current_skin.vertex_overrides.pop(index, None)
            else:
                self._current_skin.vertex_overrides[index] = color

        new_dirty = set(preview_overrides.keys())
        # Refresh union of old + new dirty so vertices touched last pass
        # but not this one revert to the snapshot value.
        self._sync_vertex_view(list(self._vertex_transform_dirty | new_dirty))
        self._vertex_transform_dirty = new_dirty

    def _on_vertex_transform_commit(self, overrides) -> None:
        if (
            self._current_skin is None
            or self._current_bundle is None
            or self._vertex_transform_dialog is None
        ):
            return

        # Preview already wrote the final state, so persistence is just
        # snapshot-advance + autosave.
        self._vertex_transform_snapshot = dict(
            self._current_skin.vertex_overrides,
        )
        self._vertex_transform_dirty = set()

        self._vertex_transform_dialog.set_colors(
            self._current_vertex_effective_colors(),
            **self._vertex_scope(),
        )
        self._vertex_transform_dialog.commit_finished()

        self._schedule_autosave()
        self.statusBar().showMessage(
            f"Applied vertex transform: {len(overrides)} colors changed.",
        )

    def _on_vertex_transform_closing(self) -> None:
        if (
            self._current_skin is None
            or self._current_bundle is None
            or self._vertex_transform_snapshot is None
        ):
            return

        self._current_skin.vertex_overrides.clear()
        self._current_skin.vertex_overrides.update(self._vertex_transform_snapshot)

        if self._vertex_transform_dirty:
            self._sync_vertex_view(list(self._vertex_transform_dirty))

        self._vertex_transform_snapshot = None
        self._vertex_transform_dirty = set()

    def _on_vertex_color_edit_requested(self, index: int) -> None:
        if (
            self._editor_mode != EditorMode.SKIN
            or self._current_skin is None
            or self._current_bundle is None
        ):
            return

        if not (0 <= index < len(self._current_bundle.mesh.gouraud_colors)):
            return

        current = self._current_skin.vertex_overrides.get(index)
        if current is None:
            base = self._current_bundle.mesh.gouraud_colors[index]
            current = Rgb888(r=base.r, g=base.g, b=base.b)

        chosen = QColorDialog.getColor(
            QColor(current.r, current.g, current.b),
            self,
            f"Pick color for v{index}",
            QColorDialog.ColorDialogOption.DontUseNativeDialog,
        )

        if not chosen.isValid():
            return

        new_color = Rgb888(r=chosen.red(), g=chosen.green(), b=chosen.blue())
        if (new_color.r, new_color.g, new_color.b) == (current.r, current.g, current.b):
            return

        self._apply_vertex_override(index, new_color)

    def _on_vertex_reset_requested(self, index: int) -> None:
        if (
            self._editor_mode != EditorMode.SKIN
            or self._current_skin is None
            or self._current_bundle is None
        ):
            return

        if index not in self._current_skin.vertex_overrides:
            return

        self._current_skin.vertex_overrides.pop(index, None)
        self._refresh_vertex_after_override_change(touched_indices=[index])

    def _on_vertex_reset_all_requested(self) -> None:
        if (
            self._editor_mode != EditorMode.SKIN
            or self._current_skin is None
            or self._current_bundle is None
            or not self._current_skin.vertex_overrides
        ):
            return

        touched = list(self._current_skin.vertex_overrides.keys())
        self._current_skin.vertex_overrides.clear()
        self._refresh_vertex_after_override_change(touched_indices=touched)

    def _on_vertex_focus_changed(self, index) -> None:
        if index is None:
            self._kart_viewer.set_highlighted_triangles(None)
        else:
            self._kart_viewer.set_highlighted_triangles(
                self._vertex_triangle_mask.get(index, []),
            )

    def _on_vertex_editor_context(self, index: int, global_pos) -> None:
        if self._editor_mode != EditorMode.SKIN or self._current_skin is None:
            return

        menu = QMenu(self)

        reset_action = menu.addAction("Reset to baked color")
        reset_action.setEnabled(index in self._current_skin.vertex_overrides)
        reset_action.triggered.connect(
            lambda: self._on_vertex_reset_requested(index),
        )

        menu.exec(global_pos)

    def _apply_vertex_override(self, index: int, color: Rgb888) -> None:
        if self._current_skin is None or self._current_bundle is None:
            return

        base = self._current_bundle.mesh.gouraud_colors[index]
        if (color.r, color.g, color.b) == (base.r, base.g, base.b):
            self._current_skin.vertex_overrides.pop(index, None)
        else:
            self._current_skin.vertex_overrides[index] = color

        self._refresh_vertex_after_override_change(touched_indices=[index])

    def _refresh_vertex_after_override_change(
        self, touched_indices: list[int],
    ) -> None:
        self._sync_vertex_view(touched_indices)
        self._schedule_autosave()

    def _sync_vertex_view(self, touched_indices) -> None:
        if self._current_skin is None or self._current_bundle is None:
            return

        overrides = self._current_skin.vertex_overrides
        for index in touched_indices:
            base = self._current_bundle.mesh.gouraud_colors[index]
            override = overrides.get(index)

            if override is not None:
                self._vertex_editor.update_color(
                    index, Rgb888(r=override.r, g=override.g, b=override.b),
                    is_overridden=True,
                )
            else:
                self._vertex_editor.update_color(
                    index, Rgb888(r=base.r, g=base.g, b=base.b),
                    is_overridden=False,
                )

        self._vertex_editor.set_editable(True)

        assembled = self._vertex_assembler.assemble(
            self._current_bundle.mesh, vertex_overrides=overrides,
        )

        self._kart_viewer.set_mesh(
            assembled, self._current_bundle.mesh.texture_layouts,
        )

    def _on_slot_reset_requested(self, slot_name: str) -> None:
        if self._current_bundle is None or not self._require_active_asset():
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        asset = self._active_asset()
        old_colors = self._snapshot_slot_colors(asset, slot.slot_name)
        self.apply_slot_reset_from_command(asset, slot)
        self._undo_stack.push(ResetSlotCommand(self, asset, slot, old_colors))

    def _on_slot_transform_requested(self) -> None:
        if self._current_bundle is None or not self._require_active_asset():
            return

        self._transform.show()

    def _on_slot_reset_all_requested(self) -> None:
        """Bundled into a single undo macro so one Ctrl+Z reverses the whole
        Reset all, not just the last slot.
        """
        if self._current_bundle is None or not self._require_active_asset():
            return

        asset = self._active_asset()
        mode_slots = self._active_slot_names()

        slots = [
            slot for name, slot in self._current_bundle.slot_regions.slots.items()
            if name in mode_slots
        ]

        if not slots:
            return

        self._undo_stack.beginMacro(f"Reset all ({len(slots)} slots)")

        try:
            for slot in slots:
                old_colors = self._snapshot_slot_colors(asset, slot.slot_name)
                self.apply_slot_reset_from_command(asset, slot)
                self._undo_stack.push(
                    ResetSlotCommand(self, asset, slot, old_colors),
                )
        finally:
            self._undo_stack.endMacro()

        self.statusBar().showMessage(f"Reset {len(slots)} slot(s) to defaults.")

    def _on_eyedropper_picked(
        self, tex_layout_index: int, byte_u: float, byte_v: float,
    ) -> None:
        """Resolve a right-click 3D pick to a (slot, color_index) and reveal it."""
        if self._current_bundle is None or self._current_character is None:
            return

        mesh = self._current_bundle.mesh
        layout_index = tex_layout_index - 1
        if layout_index < 0 or layout_index >= len(mesh.texture_layouts):
            return

        slot_name = self._find_slot_for_texture_layout(layout_index)
        if slot_name is None:
            self.statusBar().showMessage(
                "Eyedropper: this face isn't assigned to a paintjob slot "
                "(shared asset, wheel, or other non-editable region).",
                4000,
            )

            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        tl = mesh.texture_layouts[layout_index]
        atlas_x = int(round(tl.page_x * 256 + byte_u))
        atlas_y = int(round(tl.page_y * 256 + byte_v))
        atlas_w = AtlasRenderer.ATLAS_WIDTH
        atlas_h = AtlasRenderer.ATLAS_HEIGHT
        if not (0 <= atlas_x < atlas_w and 0 <= atlas_y < atlas_h):
            return

        offset = (atlas_y * atlas_w + atlas_x) * 4
        if offset + 4 > len(self._current_bundle.atlas_rgba):
            return

        hit_r = self._current_bundle.atlas_rgba[offset + 0]
        hit_g = self._current_bundle.atlas_rgba[offset + 1]
        hit_b = self._current_bundle.atlas_rgba[offset + 2]
        hit_a = self._current_bundle.atlas_rgba[offset + 3]

        color_index = self._match_atlas_pixel_to_slot_color(
            slot, hit_r, hit_g, hit_b, hit_a,
        )

        if color_index is None:
            self.statusBar().showMessage(
                f"Eyedropper: sampled ({hit_r},{hit_g},{hit_b}) in "
                f"slot '{slot_name}' but couldn't match it to any of the 16 CLUT entries.",
                4000,
            )

            return

        hex_text = self._color_converter.psx_to_u16_hex(
            self._current_color(slot, color_index),
        )

        self.statusBar().showMessage(
            f"Eyedropper: {slot_name}[{color_index}] = {hex_text}. "
            f"Opening color picker — Cancel to leave unchanged.",
            5000,
        )

        # Pop the color picker pre-loaded with the picked color. If the user
        # changes it, that's a normal slot edit (goes through the regular
        # undo path); Cancel leaves everything alone.
        self._edit_color_at(slot, color_index)

    def _edit_color_at(self, slot, color_index: int) -> None:
        """Programmatic equivalent of the user clicking that slot's swatch."""
        if self._current_bundle is None or not self._require_active_asset():
            return

        old_color = self._current_color(slot, color_index)
        new_color = self._color_picker.pick(old_color, parent=self)
        if new_color is None or new_color.value == old_color.value:
            return

        asset = self._active_asset()
        self.apply_color_edit_from_command(asset, slot, color_index, new_color)
        self._undo_stack.push(SetSlotColorCommand(
            self, asset, slot, color_index, old_color, new_color,
        ))

    def _find_slot_for_texture_layout(self, layout_index: int) -> str | None:
        """Reverse-lookup: which paintjob slot owns this 0-based texture layout?"""
        if self._current_bundle is None:
            return None

        for slot_name, slot in self._current_bundle.slot_regions.all_slots():
            for region in slot.regions:
                if layout_index in region.texture_layout_indices:
                    return slot_name

        return None

    def _match_atlas_pixel_to_slot_color(
        self, slot, r: int, g: int, b: int, a: int,
    ) -> int | None:
        """Find which of a slot's 16 CLUT entries was sampled at the hit pixel."""
        for i in range(SlotColors.SIZE):
            color = self._current_color(slot, i)
            if color.value == 0:
                if a == 0:
                    return i

                continue

            rgb = self._color_converter.psx_to_rgb(color)
            if rgb.r == r and rgb.g == g and rgb.b == b:
                return i

        return None

    def _on_slot_editor_context(self, slot_name: str, color_index: int, global_pos) -> None:
        """Right-click on a swatch (color_index >= 0) or slot-row chrome (color_index == -1)."""
        if self._current_bundle is None or self._current_character is None:
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        # Bulk operations are available in every edit mode; each writes
        # to the active asset. Preview mode is read-only — no menu.
        if self._editor_mode not in (EditorMode.PAINTJOB, EditorMode.SKIN, EditorMode.WHEEL):
            return

        menu = QMenu(self)
        menu.addAction(
            "Transform colors...",
            lambda: self._transform.show(slot_override=slot_name),
        )

        # Gradient fill / palette apply / texture import only make sense
        # on a whole slot — offered from the row-chrome menu, not the
        # per-swatch one.
        if color_index < 0:
            menu.addAction(
                "Gradient fill...",
                lambda: self._open_gradient_fill_dialog(slot_name),
            )

            self._add_apply_palette_submenu(menu, slot_name)

            if slot.regions:
                menu.addSeparator()

                if not self._slot_is_non_portable(slot_name):
                    menu.addAction(
                        "Import texture...",
                        lambda: self._on_import_slot_texture(slot_name),
                    )

                menu.addAction(
                    "Export texture...",
                    lambda: self._on_export_slot_texture(slot_name),
                )

                asset = self._active_asset()
                if (
                    asset is not None
                    and asset.slots.get(slot_name) is not None
                    and asset.slots[slot_name].pixels
                ):
                    self._add_rotate_texture_submenu(menu, slot_name)
                    menu.addAction(
                        "Remove imported texture",
                        lambda: self._on_remove_slot_texture(slot_name),
                    )

        menu.exec(global_pos)

    def _add_apply_palette_submenu(self, menu: QMenu, slot_name: str) -> None:
        """Append an "Apply Color Palette" submenu listing every saved palette."""
        submenu = menu.addMenu("Apply Color Palette")
        palettes = self._palette_library.palettes

        if not palettes:
            hint = submenu.addAction(
                "(no palettes saved — create one in the Color Palettes tab)",
            )
            hint.setEnabled(False)
            return

        for i, palette in enumerate(palettes):
            label = palette.name.strip() or f"Palette {i + 1}"
            submenu.addAction(
                label,
                lambda _=False, pi=i, sn=slot_name: self._on_apply_palette_to_slot(pi, sn),
            )

    def _open_gradient_fill_dialog(self, slot_name: str) -> None:
        if self._current_bundle is None or not self._require_active_asset():
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None:
            return

        current_colors = [
            self._current_color(slot, i) for i in range(SlotColors.SIZE)
        ]

        dialog = GradientFillDialog(
            slot_name=slot_name,
            current_colors=current_colors,
            color_converter=self._color_converter,
            gradient_generator=self._gradient_generator,
            color_picker=self._color_picker,
            parent=self,
        )

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        replacements = dialog.resulting_replacements()
        if not replacements:
            return

        asset = self._active_asset()
        edits = [
            BulkColorEdit(
                asset=asset,
                slot=slot,
                color_index=ci,
                old_color=current_colors[ci],
                new_color=new_color,
            )
            for ci, new_color in replacements
        ]

        self.apply_bulk_edits_from_command(
            [(e.asset, e.slot, e.color_index, e.new_color) for e in edits],
        )

        lo = replacements[0][0]
        hi = replacements[-1][0]
        label = f"Gradient fill {slot_name}[{lo}..{hi}]"
        self._undo_stack.push(BulkTransformCommand(self, label, edits))

    def _slot_is_non_portable(self, slot_name: str) -> bool:
        """True if the slot's `non_portable` flag is set in the current character's profile."""
        if self._current_character is None:
            return False

        for slot in self._current_character.slots:
            if slot.name == slot_name:
                return slot.non_portable
        
        return False

    def _on_import_slot_texture(self, slot_name: str) -> None:
        """Import a PNG as the slot's 4bpp pixel + CLUT payload.

        Targets the active asset — every asset type stores pixel payloads
        on `SlotColors.pixels`, so the same path works for all of them.
        """
        if (
            self._current_bundle is None
            or self._current_character is None
            or not self._require_active_asset()
        ):
            return

        if self._slot_is_non_portable(slot_name):
            QMessageBox.information(
                self, "Slot not textureable",
                f"'{slot_name}' has different VRAM rect dimensions per character "
                f"(e.g. 8x8 on Crash, 16x8 on Cortex, 4x8 on Tiny), so an imported "
                f"texture can't upload cleanly across all characters. Edit its "
                f"CLUT colors instead — those stay portable.",
            )

            return

        slot_regions = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot_regions is None or not slot_regions.regions:
            return

        if len(slot_regions.regions) == 1:
            self._import_single_region_texture(slot_name, slot_regions.regions[0])
        else:
            self._import_multi_region_texture(slot_name, slot_regions.regions)

    def _import_single_region_texture(self, slot_name: str, region) -> None:
        width, height = region.pixel_dimensions

        path = self._files.pick_open_path(
            self, f"Import texture for {slot_name} ({width}x{height})",
            self._config.iso_root or None,
            "PNG images (*.png);;All files (*)",
        )

        if path is None:
            return

        path = Path(str(path))
        texture = self._import_png_with_prompt(path, width, height)
        if texture is None:
            return

        asset = self._active_asset()
        asset.slots[slot_name] = SlotColors(
            colors=list(texture.palette),
            pixels=[
                SlotRegionPixels(
                    vram_x=region.vram_x,
                    vram_y=region.vram_y,
                    width=texture.width,
                    height=texture.height,
                    pixels=texture.pixels,
                ),
            ],
        )

        self._after_texture_import(slot_name, path.name)

    def _import_multi_region_texture(self, slot_name: str, regions) -> None:
        region_specs = [r.pixel_dimensions for r in regions]

        dialog = MultiRegionTextureImportDialog(
            self,
            slot_name=slot_name,
            region_specs=region_specs,
            files=self._files,
            default_dir=self._config.iso_root or None,
        )

        if dialog.exec() != MultiRegionTextureImportDialog.DialogCode.Accepted:
            return

        paths = dialog.chosen_paths()
        try:
            images = [Image.open(p).copy() for p in paths]
        except OSError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        try:
            result = self._multi_region_texture_importer.import_for_regions(
                images, region_specs,
            )
        except ValueError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        asset = self._active_asset()
        asset.slots[slot_name] = SlotColors(
            colors=list(result.palette),
            pixels=[
                SlotRegionPixels(
                    vram_x=region.vram_x,
                    vram_y=region.vram_y,
                    width=region_import.width,
                    height=region_import.height,
                    pixels=region_import.pixels,
                )
                for region, region_import in zip(regions, result.regions)
            ],
        )

        self._after_texture_import(
            slot_name, f"{len(paths)} regions",
        )

    def _on_export_slot_texture(self, slot_name: str) -> None:
        """Save the slot's pixel data as PNG(s) using the current CLUT.

        Single-region slots write one file at the chosen path. Multi-region
        slots write one file per region with `_<index>` suffixed before the
        extension so the regions stay grouped on disk.
        """
        if self._current_bundle is None or self._current_character is None:
            return

        slot = self._current_bundle.slot_regions.find_slot(slot_name)
        if slot is None or not slot.regions:
            return

        default_name = f"{self._current_character.id}_{slot_name}.png"
        default_path = Path(self._config.iso_root or Path.home()) / default_name
        save_path = self._files.pick_save_path(
            self, f"Export texture for {slot_name}",
            default_path, "PNG images (*.png)",
        )

        if save_path is None:
            return

        save_path = save_path.with_suffix(".png")
        clut = self._current_clut_for_slot(slot)

        try:
            paths_written = self._write_slot_textures(slot, clut, save_path)
        except (OSError, ValueError) as exc:
            self._message.error(
                self, "Export failed", str(exc),
            )

            return

        self.statusBar().showMessage(
            f"Exported {slot_name} → {len(paths_written)} file(s)",
        )

    def _current_clut_for_slot(self, slot: SlotRegions) -> list[PsxColor]:
        """Resolve the 16 colors currently displayed for this slot — asset
        override if present, otherwise the live VRAM defaults."""
        asset = self._active_asset()
        if asset is not None and slot.slot_name in asset.slots:
            return list(asset.slots[slot.slot_name].colors)

        return self._color_handler.default_slot_colors(self._config.iso_root, slot)

    def _write_slot_textures(
        self, slot: SlotRegions, clut: list[PsxColor], base_path: Path,
    ) -> list[Path]:
        asset = self._active_asset()
        imported_pixels = (
            asset.slots[slot.slot_name].pixels
            if asset is not None and slot.slot_name in asset.slots
            else []
        )

        imported_by_coord = {
            (rp.vram_x, rp.vram_y): rp for rp in imported_pixels
        }

        written: list[Path] = []
        multi = len(slot.regions) > 1
        for index, region in enumerate(slot.regions):
            override = imported_by_coord.get((region.vram_x, region.vram_y))
            if override is not None:
                pixel_bytes = bytes(override.pixels)
                width, height = override.width, override.height
            else:
                pixel_bytes = self._color_handler.default_region_pixels(
                    self._config.iso_root, region,
                )
                width, height = region.pixel_dimensions

            image = self._texture_exporter.to_image(
                pixel_bytes, width, height, clut,
            )

            if multi:
                target = base_path.with_name(
                    f"{base_path.stem}_{index}{base_path.suffix}",
                )
            else:
                target = base_path

            image.save(target)
            written.append(target)

        return written

    def _after_texture_import(self, slot_name: str, source_label: str) -> None:
        self._invalidate_undo()
        self._populate_slot_editor()
        self._reload_preview()
        self._schedule_autosave()
        self.statusBar().showMessage(f"Imported {source_label} → {slot_name}")

    def _import_png_with_prompt(self, path: Path, width: int, height: int):
        """Try REJECT mode first; on size mismatch, ask the artist whether to scale/crop."""
        try:
            return self._single_region_texture_importer.import_from_path(path, width, height)
        except ValueError as exc:
            # Size mismatch — offer Scale / Crop / Cancel.
            msg = QMessageBox(self)
            msg.setWindowTitle("Size mismatch")
            msg.setText(str(exc))
            msg.setInformativeText(
                "Choose how to fit the source image into the slot:",
            )
            scale = msg.addButton("Scale", QMessageBox.ButtonRole.AcceptRole)
            crop = msg.addButton("Center crop", QMessageBox.ButtonRole.AcceptRole)
            msg.addButton(QMessageBox.StandardButton.Cancel)
            msg.exec()

            chosen = msg.clickedButton()

            if chosen is scale:
                mode = SizeMismatchMode.SCALE
            elif chosen is crop:
                mode = SizeMismatchMode.CENTER_CROP
            else:
                return None

            try:
                return self._single_region_texture_importer.import_from_path(
                    path, width, height, mode=mode,
                )
            except ValueError as exc2:
                QMessageBox.critical(self, "Import failed", str(exc2))
                return None
        except OSError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return None

    def _on_remove_slot_texture(self, slot_name: str) -> None:
        """Drop a slot's pixel payload; CLUT colors stay as-is."""
        if not self._require_active_asset():
            return

        asset = self._active_asset()
        slot = asset.slots.get(slot_name)
        if slot is None or not slot.pixels:
            return

        asset.slots[slot_name] = SlotColors(colors=list(slot.colors), pixels=[])

        self._invalidate_undo()
        self._populate_slot_editor()
        self._reload_preview()
        self._schedule_autosave()
        self.statusBar().showMessage(f"Removed imported texture on {slot_name}")

    def _add_rotate_texture_submenu(self, menu: QMenu, slot_name: str) -> None:
        asset = self._active_asset()
        if asset is None:
            return

        slot = asset.slots.get(slot_name)
        if slot is None or not slot.pixels:
            return

        # Multi-region textures aren't rotatable as a unit — bail out
        # silently so the menu just doesn't grow the submenu.
        if len(slot.pixels) != 1:
            return

        region = slot.pixels[0]
        square = region.width == region.height

        submenu = menu.addMenu("Rotate texture")
        for degrees, label in ((90, "90° clockwise"), (180, "180°"), (270, "270° clockwise")):
            action = submenu.addAction(
                label,
                lambda _=False, d=degrees: self._on_rotate_slot_texture(slot_name, d),
            )

            # 90 / 270 swap dimensions; only valid when the texture is square.
            if degrees != 180 and not square:
                action.setEnabled(False)
                action.setToolTip(
                    "Only available for square textures — 90 / 270° would "
                    "swap width and height.",
                )

    def _on_rotate_slot_texture(self, slot_name: str, degrees: int) -> None:
        if not self._require_active_asset():
            return

        asset = self._active_asset()
        slot = asset.slots.get(slot_name)
        if slot is None or len(slot.pixels) != 1:
            return

        region = slot.pixels[0]
        try:
            rotated = self._texture_rotator.rotate(
                region.pixels, region.width, region.height, degrees,
            )
        except ValueError as exc:
            QMessageBox.critical(self, "Rotate failed", str(exc))
            return

        asset.slots[slot_name] = SlotColors(
            colors=list(slot.colors),
            pixels=[
                SlotRegionPixels(
                    vram_x=region.vram_x,
                    vram_y=region.vram_y,
                    width=rotated.width,
                    height=rotated.height,
                    pixels=rotated.pixels,
                ),
            ],
        )

        self._invalidate_undo()
        self._populate_slot_editor()
        self._reload_preview()
        self._schedule_autosave()
        self.statusBar().showMessage(f"Rotated {slot_name} by {degrees}°")

    def apply_bulk_edits_from_command(
        self,
        operations: list[tuple[object, object, int, PsxColor]],
    ) -> None:
        """Apply N `(asset, slot, color_index, color)` changes in one batch.

        `asset` is a Paintjob OR Skin — both have the same `.slots[name]`
        shape so the color-handler path duck-types on it.
        """
        if self._current_bundle is None or not operations:
            return

        # If every edit targets a single asset that isn't the currently-
        # selected one, switch selection so Ctrl+Z doesn't silently mutate
        # an asset the user isn't looking at.
        assets = {id(op[0]) for op in operations}
        if len(assets) == 1:
            self._switch_to_asset_if_needed(operations[0][0])

        by_slot: dict[tuple[int, str], list[tuple[int, PsxColor]]] = {}
        slot_for_key: dict[tuple[int, str], object] = {}
        asset_for_key: dict[tuple[int, str], object] = {}
        for asset, slot, color_index, color in operations:
            key = (id(asset), slot.slot_name)
            by_slot.setdefault(key, []).append((color_index, color))
            slot_for_key[key] = slot
            asset_for_key[key] = asset

        for key, slot_ops in by_slot.items():
            slot = slot_for_key[key]
            asset = asset_for_key[key]
            self._color_handler.apply_edits(
                self._config.iso_root,
                self._current_bundle.atlas_rgba,
                asset,
                slot,
                slot_ops,
            )

            if asset is self._active_asset():
                for color_index, new_color in slot_ops:
                    for editor in self._slot_editors:
                        editor.update_color(
                            slot.slot_name, color_index, new_color,
                        )

        self._kart_viewer.set_atlas(
            self._current_bundle.atlas_rgba,
            AtlasRenderer.ATLAS_WIDTH,
            AtlasRenderer.ATLAS_HEIGHT,
        )

    def _switch_to_asset_if_needed(self, asset: Paintjob | Skin | Wheel) -> None:
        """Select `asset` in its sidebar so an undo visibly reverts the edit."""
        if isinstance(asset, Wheel):
            if self._current_wheel is asset:
                return

            try:
                index = self._wheel_library.wheels.index(asset)
            except ValueError:
                return

            self._editor_mode = EditorMode.WHEEL
            self._wheel_controller.select_index(index)
            self._reload_preview()
            return

        if isinstance(asset, Skin):
            if self._current_skin is asset:
                return

            try:
                index = self._skin_library.skins.index(asset)
            except ValueError:
                return

            self._editor_mode = EditorMode.SKIN
            self._skin_controller.select_index(index)
            self._reload_preview()
            return

        if self._current_paintjob is asset:
            return

        try:
            self._library.paintjobs.index(asset)
        except ValueError:
            # Asset isn't in the library anymore (deletion should have
            # cleared undo, so this is a rare safety net).
            return

        self._editor_mode = EditorMode.PAINTJOB
        self._paintjob_controller.select_paintjob(asset)
        self._reload_preview()

    def apply_color_edit_from_command(
        self,
        asset: Paintjob | Skin,
        slot,
        color_index: int,
        new_color: PsxColor,
    ) -> None:
        """Apply a color change without going through the undo stack."""
        if self._current_bundle is None:
            return

        self._switch_to_asset_if_needed(asset)

        self._color_handler.apply_edit(
            self._config.iso_root,
            self._current_bundle.atlas_rgba,
            asset,
            slot,
            color_index,
            new_color,
        )

        self._push_slot_region_to_viewer(slot)
        for editor in self._slot_editors:
            editor.update_color(slot.slot_name, color_index, new_color)

    def apply_slot_reset_from_command(
        self, asset: Paintjob | Skin, slot,
    ) -> None:
        if self._current_bundle is None:
            return

        self._switch_to_asset_if_needed(asset)

        # Reset pulls colors from the asset's base character — for
        # paintjobs that's `base_character_id` (wildcard-capable), for
        # skins it's the bound `character_id` (character-locked).
        base_x, base_y = self._base_clut_coord_for(asset, slot.slot_name)

        defaults = self._color_handler.reset_slot(
            self._config.iso_root,
            self._current_bundle.atlas_rgba,
            asset,
            slot,
            base_x,
            base_y,
        )

        self._push_slot_region_to_viewer(slot)
        for editor in self._slot_editors:
            editor.set_slot_colors(slot.slot_name, defaults)

    def _base_clut_coord_for(
        self, asset: Paintjob | Skin, slot_name: str,
    ) -> tuple[int, int]:
        """Resolve the asset's base-character CLUT coords for a given slot."""
        if isinstance(asset, Wheel):
            clut = self._wheel_geometry.frame_clut(WHEEL_SLOT_NAMES.index(slot_name))
            return clut.x, clut.y

        base_id = (
            asset.character_id if isinstance(asset, Skin)
            else asset.base_character_id
        )

        base_char = self._find_character(base_id) or self._current_character
        if base_char is None:
            return 0, 0

        for slot_profile in base_char.slots:
            if slot_profile.name == slot_name:
                return slot_profile.clut.x, slot_profile.clut.y

        return 0, 0

    def _find_character(self, character_id: str | None):
        """Profile-character lookup by id. Returns `None` when not found or id is None."""
        if character_id is None or self._profile is None:
            return None
        
        for character in self._profile.characters:
            if character.id == character_id:
                return character

        return None

    def apply_slot_restore_from_command(
        self,
        asset: Paintjob | Skin,
        slot,
        old_colors: SlotColors | None,
    ) -> None:
        if self._current_bundle is None:
            return

        self._switch_to_asset_if_needed(asset)

        colors = self._color_handler.restore_slot(
            self._config.iso_root,
            self._current_bundle.atlas_rgba,
            asset,
            slot,
            old_colors,
        )

        self._push_slot_region_to_viewer(slot)
        for editor in self._slot_editors:
            editor.set_slot_colors(slot.slot_name, colors)

    def _push_slot_region_to_viewer(self, slot) -> None:
        """Upload just the dirty rectangle of the atlas after a slot edit."""
        if self._current_bundle is None:
            return

        atlas_w = AtlasRenderer.ATLAS_WIDTH
        atlas_h = AtlasRenderer.ATLAS_HEIGHT
        bbox = self._atlas_bbox_for_slot(slot)

        if bbox is None:
            self._kart_viewer.set_atlas(
                self._current_bundle.atlas_rgba, atlas_w, atlas_h,
            )
            return

        x, y, w, h = bbox
        self._kart_viewer.set_atlas_region(
            self._current_bundle.atlas_rgba, atlas_w, atlas_h, x, y, w, h,
        )

    def _atlas_bbox_for_slot(self, slot) -> tuple[int, int, int, int] | None:
        """Atlas-pixel bounding box enclosing every VRAM region of `slot`."""
        if not slot.regions:
            return None

        # AtlasRenderer stretches VRAM X by 4 for 4bpp texel visibility.
        stretch_x = 4
        min_x = min_y = None
        max_x = max_y = None

        for region in slot.regions:
            ax = region.vram_x * stretch_x
            ay = region.vram_y
            aw = region.vram_width * stretch_x
            ah = region.vram_height

            if min_x is None:
                min_x, min_y = ax, ay
                max_x, max_y = ax + aw, ay + ah
            else:
                min_x = min(min_x, ax)
                min_y = min(min_y, ay)
                max_x = max(max_x, ax + aw)
                max_y = max(max_y, ay + ah)

        return min_x, min_y, max_x - min_x, max_y - min_y

    def _snapshot_slot_colors(
        self, asset: Paintjob | Skin, slot_name: str,
    ) -> SlotColors | None:
        """Deep-copy a slot's entire state (colors + imported pixels)."""
        slot = asset.slots.get(slot_name)
        if slot is None:
            return None

        return SlotColors(
            colors=[PsxColor(value=c.value) for c in slot.colors],
            pixels=list(slot.pixels),
        )

    def _current_color(self, slot, color_index: int) -> PsxColor:
        """Effective color for `(slot, color_index)` in the editor right now."""
        active = self._active_asset()
        if active is not None and slot.slot_name in active.slots:
            return active.slots[slot.slot_name].colors[color_index]

        defaults = self._color_handler.default_slot_colors(self._config.iso_root, slot)
        return defaults[color_index]
