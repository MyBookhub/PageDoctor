import ast
import importlib.util
import pkgutil
import sys
from pathlib import Path

import pagedoctor.domain

ALLOWED = set(sys.stdlib_module_names) | {"pydantic", "pagedoctor"}


def _domain_modules() -> list[str]:
    return [
        info.name
        for info in pkgutil.walk_packages(
            list(pagedoctor.domain.__path__), prefix="pagedoctor.domain."
        )
    ]


def _top_level_imports(module_name: str) -> set[str]:
    # find_spec avoids executing the module, so a forbidden import is caught statically.
    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin is not None
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            roots.add(node.module.split(".")[0])
    return roots


def test_domain_imports_only_stdlib_and_pydantic() -> None:
    modules = _domain_modules()
    assert modules, "no domain modules discovered"
    offenders = {
        name: external for name in modules if (external := _top_level_imports(name) - ALLOWED)
    }
    assert not offenders, f"domain modules import non-allowed packages: {offenders}"
