# coding: utf-8

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMenu, QWidget

from paintjob_designer.core import Slugifier
from paintjob_designer.gui.controller.library_controller import LibraryController
from paintjob_designer.gui.handler.color_handler import ColorHandler
from paintjob_designer.gui.util.dialogs import FilePicker, MessageDialog
from paintjob_designer.gui.util.disposed_after import DisposedAfter
from paintjob_designer.gui.util.library_writer import LibraryWriter
from paintjob_designer.gui.widget.wheel_library_sidebar import WheelLibrarySidebar
from paintjob_designer.models import (
    WHEEL_FRAME_SIZE,
    WHEEL_SLOT_NAMES,
    SlotColors,
    SlotRegionPixels,
    Wheel,
    WheelLibrary,
)
from paintjob_designer.render.wheel_geometry import WheelGeometry
from paintjob_designer.wheel.reader import WheelReader
from paintjob_designer.wheel.writer import WheelWriter

if TYPE_CHECKING:
    from paintjob_designer.texture.wheel_sheet import WheelSheet

_WHEEL_EXT = ".json"
_WHEEL_FILTER = f"Wheel (*{_WHEEL_EXT})"
_SHEET_FILTER = "PNG images (*.png)"


class WheelLibraryController(LibraryController[Wheel, WheelLibrary]):
    """Owns the wheel library + sidebar + wheel CRUD and sprite-sheet round trips."""

    def __init__(
        self,
        sidebar: WheelLibrarySidebar,
        wheel_reader: WheelReader,
        wheel_writer: WheelWriter,
        library_writer: LibraryWriter,
        wheel_sheet_provider: Callable[[], "WheelSheet"],
        message: MessageDialog,
        files: FilePicker,
        slugifier: Slugifier,
        color_handler: ColorHandler,
        wheel_geometry: WheelGeometry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(message, parent)
        self._sidebar = sidebar
        self._wheel_reader = wheel_reader
        self._wheel_writer = wheel_writer
        self._library_writer = library_writer
        self._wheel_sheet = wheel_sheet_provider
        self._files = files
        self._slugifier = slugifier
        self._color_handler = color_handler
        self._wheel_geometry = wheel_geometry
        self._iso_root: str = ""

        self._sidebar.item_selected.connect(self._on_sidebar_selected)
        self._sidebar.context_requested.connect(self._on_context_menu)
        self._sidebar.new_requested.connect(self.new)
        self._sidebar.delete_requested.connect(self.delete)
        self._sidebar.export_requested.connect(self.export_library)

    def set_iso_root(self, iso_root: str) -> None:
        self._iso_root = iso_root

    def _make_empty_library(self) -> WheelLibrary:
        return WheelLibrary()

    def _items(self) -> list[Wheel]:
        return self._library.wheels

    def _item_label(self, item: Wheel, index: int) -> str:
        return item.name.strip() or f"Wheel {index + 1}"

    def _item_kind(self) -> str:
        return "wheel"

    def _refresh_sidebar(self, selected_index: int | None) -> None:
        self._sidebar.set_library(self._library, selected_index=selected_index)

    def _remove_at(self, index: int) -> Wheel:
        return self._library.remove(index)

    def _set_sidebar_selection(self, index: int) -> None:
        self._sidebar.set_selected_index(index)

    def new(self) -> None:
        try:
            slots = self._seed_slots()
        except OSError as exc:
            self._message.error(
                self._parent_widget, "Could not create wheel",
                f"New wheels start from the game's tires, so load an ISO first.\n\n{exc}",
            )

            return

        wheel = Wheel(name=f"Wheel {self._library.count() + 1}", slots=slots)
        index = self._library.add(wheel)
        self._refresh_sidebar(index)
        self._after_mutation()

    def import_files(self, default_dir: str | None = None) -> None:
        for path in self._files.pick_open_paths(
            self._parent_widget, "Import wheels",
            default_dir, f"{_WHEEL_FILTER};;All files (*)",
        ):
            self.import_file(path)

    def import_file(self, path: Path) -> None:
        try:
            loaded = self._wheel_reader.read(path.read_bytes())
        except (OSError, ValueError) as exc:
            self._message.error(self._parent_widget, "Import failed", str(exc))
            return

        index = self._library.add(loaded)
        self.library_reset.emit()
        self._refresh_sidebar(index)
        self._after_mutation()

    def replace_from_file(self, index: int) -> None:
        if not (0 <= index < self._library.count()):
            return

        path = self._files.pick_open_path(
            self._parent_widget, "Replace wheel from JSON",
            None, f"{_WHEEL_FILTER};;All files (*)",
        )

        if path is None:
            return

        try:
            loaded = self._wheel_reader.read(path.read_bytes())
        except (OSError, ValueError) as exc:
            self._message.error(self._parent_widget, "Import failed", str(exc))
            return

        self._library.wheels[index] = loaded
        self._replaced(index)

    def export_one(self, wheel: Wheel) -> None:
        try:
            index = self._library.wheels.index(wheel)
        except ValueError:
            return

        path = self._files.pick_save_path(
            self._parent_widget, "Export wheel as JSON",
            self._slug(wheel, index) + _WHEEL_EXT, _WHEEL_FILTER,
        )

        if path is None:
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._wheel_writer.serialize(wheel), encoding="utf-8")
        except OSError as exc:
            self._message.error(self._parent_widget, "Export failed", str(exc))

    def export_library(self) -> None:
        if self._library.count() == 0:
            self._message.info(
                self._parent_widget, "Nothing to save",
                "The wheel library is empty — create at least one wheel "
                "before saving.",
            )

            return

        directory = self._files.pick_directory(self._parent_widget, "Save wheel library")
        if directory is None:
            return

        try:
            self._library_writer.write(
                directory, self._library.wheels,
                filename_for=lambda wheel, index: f"{index:02d}_{self._slug(wheel, index)}{_WHEEL_EXT}",
                serialize=self._wheel_writer.serialize,
            )
        except OSError as exc:
            self._message.error(self._parent_widget, "Save wheel library failed", str(exc))

    def import_sheet(self, index: int) -> None:
        if not (0 <= index < self._library.count()):
            return

        path = self._files.pick_open_path(
            self._parent_widget, "Import wheel sprite sheet",
            None, f"{_SHEET_FILTER};;All files (*)",
        )

        if path is None:
            return

        try:
            frames = self._wheel_sheet().from_file(path)
        except (OSError, ValueError) as exc:
            self._message.error(self._parent_widget, "Import failed", str(exc))
            return

        self.apply_sheet(index, frames)

    def apply_sheet(self, index: int, frames) -> None:
        """Replace every frame of the wheel at `index` with quantized sheet cells."""
        if not (0 <= index < self._library.count()):
            return

        regions = self._wheel_geometry.wheel_slot_regions()
        wheel = self._library.wheels[index]
        for name, frame in zip(WHEEL_SLOT_NAMES, frames):
            region = regions[name].regions[0]
            wheel.slots[name] = SlotColors(
                colors=list(frame.palette),
                pixels=[SlotRegionPixels(
                    vram_x=region.vram_x,
                    vram_y=region.vram_y,
                    width=WHEEL_FRAME_SIZE,
                    height=WHEEL_FRAME_SIZE,
                    pixels=frame.pixels,
                )],
            )

        self._replaced(index)

    def export_sheet(self, index: int) -> None:
        if not (0 <= index < self._library.count()):
            return

        wheel = self._library.wheels[index]
        path = self._files.pick_save_path(
            self._parent_widget, "Export wheel sprite sheet",
            self._slug(wheel, index) + ".png", _SHEET_FILTER,
        )

        if path is None:
            return

        if path.suffix.lower() != ".png":
            path = path.with_name(f"{path.name}.png")

        try:
            self._wheel_sheet().to_image(self.frames_of(wheel)).save(path)
        except (OSError, ValueError) as exc:
            self._message.error(self._parent_widget, "Export failed", str(exc))

    def frames_of(self, wheel: Wheel) -> list:
        """(pixels, CLUT) of every frame, falling back to the game's tires."""
        frames = []
        for name, slot in self._wheel_geometry.wheel_slot_regions().items():
            region = slot.regions[0]
            design = wheel.slots.get(name)
            if design is not None and design.colors:
                clut = list(design.colors)
            else:
                clut = self._color_handler.default_slot_colors(self._iso_root, slot)

            if design is not None and design.pixels:
                pixels = bytes(design.pixels[0].pixels)
            else:
                pixels = self._color_handler.default_region_pixels(self._iso_root, region)

            frames.append((pixels, clut))

        return frames

    def _on_context_menu(self, index: int, global_pos: QPoint) -> None:
        if not (0 <= index < self._library.count()):
            return

        wheel = self._library.wheels[index]
        menu = QMenu(self._parent_widget)
        menu.addAction("Edit metadata...", lambda: self.edit_metadata(index))
        menu.addSeparator()
        menu.addAction("Import sprite sheet...", lambda: self.import_sheet(index))
        menu.addAction("Export sprite sheet...", lambda: self.export_sheet(index))
        menu.addSeparator()
        menu.addAction("Export as JSON...", lambda: self.export_one(wheel))
        menu.addAction("Replace from JSON...", lambda: self.replace_from_file(index))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self.delete(index))
        menu.exec(global_pos)
        menu.deleteLater()

    def edit_metadata(self, index: int) -> None:
        from paintjob_designer.gui.dialog.edit_metadata_dialog import EditMetadataDialog

        if not (0 <= index < self._library.count()):
            return

        wheel = self._library.wheels[index]
        with DisposedAfter(EditMetadataDialog(
            self._parent_widget,
            title="Edit wheel metadata",
            name=wheel.name or "",
            author=wheel.author or "",
            base_character_options=None,
        )) as dialog:
            edit = dialog.exec_get()

        if edit is None:
            return

        self.apply_metadata(index, edit)

    def apply_metadata(self, index: int, edit) -> None:
        if not (0 <= index < self._library.count()):
            return

        wheel = self._library.wheels[index]
        wheel.name = edit.name
        wheel.author = edit.author

        self._refresh_sidebar(index)
        self._after_mutation()

    def _replaced(self, index: int) -> None:
        self.library_reset.emit()
        self._current = self._library.wheels[index]
        self._refresh_sidebar(index)
        self._after_mutation()
        self.selection_changed.emit(self._current)

    def _seed_slots(self) -> dict[str, SlotColors]:
        return {
            name: SlotColors(colors=list(self._color_handler.default_slot_colors(self._iso_root, slot)))
            for name, slot in self._wheel_geometry.wheel_slot_regions().items()
        }

    def _slug(self, wheel: Wheel, index: int) -> str:
        return self._slugifier.slugify(wheel.name) or f"wheel_{index:02d}"
