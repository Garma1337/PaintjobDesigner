# coding: utf-8

import ast
import builtins
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent.parent / "paintjob_designer"
_IMPLICIT = set(dir(builtins)) | {"__file__"}


def _undefined_names(source: str) -> set[str]:
    """Names read but never bound anywhere in the module.

    Ignores scopes, so it only catches a name missing from the whole file:
    typically an import dropped while another code path still uses it, which
    Python reports only once that path runs.
    """
    tree = ast.parse(source)
    bound = set(_IMPLICIT)
    loaded = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bound |= {(alias.asname or alias.name).split(".")[0] for alias in node.names}
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.Name):
            (loaded if isinstance(node.ctx, ast.Load) else bound).add(node.id)

    return loaded - bound


class TestUndefinedNames:

    def test_package_reads_no_unbound_names(self):
        found = {
            str(path.relative_to(_PACKAGE)): names
            for path in _PACKAGE.rglob("*.py")
            if (names := _undefined_names(path.read_text(encoding="utf-8")))
        }

        assert found == {}

    def test_detects_a_dropped_import(self):
        source = "def f():" + chr(10) + "    return Image.open('x')" + chr(10)

        assert _undefined_names(source) == {"Image"}
