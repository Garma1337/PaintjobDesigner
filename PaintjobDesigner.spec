# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_submodules

sys.path.insert(0, SPECPATH)

KEEP_QT_MODULES = {
    "Core",
    "Gui",
    "Widgets",
    "OpenGL",
    "OpenGLWidgets",
    "DBus",
}

PYSIDE6_PYTHON_EXCLUDES = [
    "PySide6.QtAsyncio",
    "PySide6.QtConcurrent",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQmlCore",
    "PySide6.QtQmlWorkerScript",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickTest",
    "PySide6.QtQuickWidgets",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtUiTools",
    "PySide6.QtXml",
]

MISC_EXCLUDES = [
    "tkinter",
    "unittest",
    "test",
    "tests",
    "pytest",
    "setuptools",
    "pip",
    "doctest",
    "pdb",
    "ssl",
    "_ssl",
    "_hashlib",
    "PIL._avif",
    "PIL.AvifImagePlugin",
    "PIL._imagingcms",
    "PIL.ImageCms",
    "PIL._imagingtk",
    "PIL.ImageTk",
    "PIL._imagingmath",
    "PIL.ImageMath",
]

_UNUSED_PATHS = (
    "pyside6/translations/",
    "pyside6/plugins/iconengines/",
    "opengl/dlls/",
)
_KEPT_PLUGINS = {
    "pyside6/plugins/imageformats/": ("qico",),
    "pyside6/plugins/platforms/": ("qwindows", "libqxcb", "libqwayland"),
}
_UNUSED_FILES = {"msvcr100.dll"}


def _path_modules(dest: str) -> set[str]:
    lowered = dest.replace("\\", "/").lower()
    found: set[str] = set()

    prefixes = ("libqt6", "libqt", "qt6", "qt")
    separators = ".-_"

    for part in lowered.split("/"):
        for prefix in prefixes:
            if not part.startswith(prefix):
                continue

            tail = part[len(prefix):]
            cut = min(
                (tail.find(s) for s in separators if s in tail),
                default=len(tail),
            )
            candidate = tail[:cut]

            if candidate:
                found.add(candidate)

            break

    return found


def _is_excluded(dest: str) -> bool:
    modules = _path_modules(dest)
    if not modules:
        return False

    keep_lower = {m.lower() for m in KEEP_QT_MODULES}
    return all(m not in keep_lower for m in modules)


def _is_unused(dest: str) -> bool:
    path = dest.replace("\\", "/").lower()

    if path in _UNUSED_FILES or path.startswith(_UNUSED_PATHS):
        return True

    for folder, kept in _KEPT_PLUGINS.items():
        if path.startswith(folder):
            return not path[len(folder):].startswith(kept)

    return False


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("config/profile.json", "config"),
        ("paintjob_designer/gui/widget/shaders", "paintjob_designer/gui/widget/shaders"),
        ("app.ico", "."),
    ],
    hiddenimports=collect_submodules("paintjob_designer"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=PYSIDE6_PYTHON_EXCLUDES + MISC_EXCLUDES,
    noarchive=False,
    optimize=2,
)

_before_binaries = len(a.binaries)
_before_datas = len(a.datas)

a.binaries = [b for b in a.binaries if not _is_excluded(b[0]) and not _is_unused(b[0])]
a.datas = [d for d in a.datas if not _is_excluded(d[0]) and not _is_unused(d[0])]

print(
    f"[paintjob_designer.spec] Dropped "
    f"{_before_binaries - len(a.binaries)} binaries and "
    f"{_before_datas - len(a.datas)} data files "
    f"for excluded Qt modules and unused files."
)


pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaintjobDesigner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="app.ico",
    disable_windowed_traceback=False,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PaintjobDesigner",
)
