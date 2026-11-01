# coding: utf-8

from pathlib import Path

from PySide6.QtCore import QStandardPaths


class ConfigPathResolver:
    """Finds the persisted config blob in the platform's app-data folder.

    Must run after the QApplication exists: AppDataLocation includes the
    application name.
    """

    def default_path(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return Path(base) / "paintjob-designer" / "config.json"
