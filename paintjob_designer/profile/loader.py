# coding: utf-8

import sys
from pathlib import Path

from paintjob_designer.ctr.reader import CtrModelReader
from paintjob_designer.models import ProfileLoadResult, SkippedCharacter
from paintjob_designer.profile.reader import ProfileReader
from paintjob_designer.profile.skin_slot_deriver import SkinSlotDeriver


class ProfileLoader:
    """Loads the bundled profile and completes it against an extracted ISO.

    The profile file only names the kart slots; every other CLUT a
    character's mesh samples becomes a skin slot. A legitimate NTSC-U ISO has
    every character, so one that can't be loaded points at a broken or
    modified ISO: it's left out and reported, and the rest still load.
    """

    def __init__(
        self,
        profile_reader: ProfileReader,
        model_reader: CtrModelReader,
        skin_slot_deriver: SkinSlotDeriver,
    ) -> None:
        self._reader = profile_reader
        self._model_reader = model_reader
        self._skin_slot_deriver = skin_slot_deriver

    def load(self, iso_root: str | Path) -> ProfileLoadResult:
        """Load every readable character; raises ValueError when none are."""
        profile = self._reader.read(self.bundled_path().read_bytes())
        loaded = []
        skipped = []

        for character in profile.characters:
            try:
                data = (Path(iso_root) / character.mesh_source).read_bytes()
                mesh = self._model_reader.read(data).meshes[0]
                character.skin_slots = self._skin_slot_deriver.derive(mesh, character.kart_slots)
            except FileNotFoundError:
                reason = "file is missing"
            except OSError as exc:
                reason = f"file can't be read ({exc.strerror or exc})"
            except (EOFError, IndexError, ValueError) as exc:
                reason = f"not a readable model ({exc})"
            else:
                loaded.append(character)
                continue

            skipped.append(SkippedCharacter(
                display_name=character.display_name or character.id,
                mesh_source=character.mesh_source,
                reason=reason,
            ))

        if not loaded:
            raise ValueError(f"No character models could be loaded from {iso_root}.")

        profile.characters = loaded
        return ProfileLoadResult(profile=profile, skipped=skipped)

    @staticmethod
    def bundled_path() -> Path:
        """Resolve `config/profile.json` from source or a PyInstaller one-file bundle."""
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "config" / "profile.json"

        return Path(__file__).parent.parent.parent / "config" / "profile.json"
