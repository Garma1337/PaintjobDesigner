# coding: utf-8

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Per-user settings persisted between sessions."""
    iso_root: str = ""
    library: dict | None = None
    palettes: list[dict] = field(default_factory=list)
    skins: dict | None = None
    wheels: dict | None = None
    shading: bool = True


class ConfigStore:
    """Loads and saves `AppConfig` as JSON at a caller-supplied path."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppConfig:
        """Return the stored config, or a default if nothing has been saved yet."""
        if not self._path.exists():
            return AppConfig()

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return AppConfig()

        return AppConfig(
            iso_root=str(raw.get("iso_root", "")),
            library=self.coerce_library(raw.get("library")),
            palettes=self.coerce_palettes(raw.get("palettes")),
            skins=self.coerce_library(raw.get("skins")),
            wheels=self.coerce_library(raw.get("wheels")),
            shading=raw.get("shading", True) is not False,
        )

    def save(self, config: AppConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "iso_root": config.iso_root,
            "palettes": list(config.palettes),
            "shading": config.shading,
        }

        if config.library is not None:
            data["library"] = config.library

        if config.skins is not None:
            data["skins"] = config.skins

        if config.wheels is not None:
            data["wheels"] = config.wheels

        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def coerce_library(value: Any) -> dict | None:
        if isinstance(value, dict):
            return value

        return None

    @staticmethod
    def coerce_palettes(value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []

        return [entry for entry in value if isinstance(entry, dict)]
