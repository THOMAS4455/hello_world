#!/usr/bin/env python3
"""Report modules that nothing imports (dead-code audit).

Import resolution understands the project's two import roots: the repository
root and src/, which api/app_factory.py puts on sys.path.

Always exits 0 unless --strict is given, so it can run in CI as a
non-blocking signal.

Usage:
    python scripts/audit_imports.py [--report] [--strict] [--json PATH]
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Dict, List, Optional, Set

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "build",
    ".venv",
    "dsh-mobile-portal",
}
ALIAS_ROOTS = {
    "jobs": "src.jobs",
    "trading": "src.trading",
    "portfolio": "src.portfolio",
    "research": "src.research",
    "validation": "src.validation",
    "core": "src.core",
}

PRODUCTION_ROOTS = [
    "app",
    "api.app_factory",
    "api.services",
    "api.routes.admin",
    "api.routes.ai",
    "api.routes.auth",
    "api.routes.core",
    "api.routes.investment",
    "api.routes.predictions",
    "api.routes.stocks",
    "api.routes.system",
    "api.routes.tasks",
]


def _module_name(path: pathlib.Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _collect_files() -> Dict[str, pathlib.Path]:
    files: Dict[str, pathlib.Path] = {}
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files[_module_name(path)] = path
    return files


def _raw_imports(path: pathlib.Path) -> List[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                pkg = list(path.relative_to(ROOT).with_suffix("").parts[:-1])
                base = pkg[: len(pkg) - (node.level - 1)]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            if module:
                out.append(module)
                out.extend(module + "." + alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name in ("import_module", "__import__") and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    out.append(arg.value)
    return out


def _resolve(name: str, known: Set[str]) -> Optional[str]:
    if not name:
        return None
    candidates = [name]
    head = name.split(".")[0]
    if head in ALIAS_ROOTS:
        candidates.append(ALIAS_ROOTS[head] + name[len(head):])
    for cand in candidates:
        parts = cand.split(".")
        while parts:
            joined = ".".join(parts)
            if joined in known:
                return joined
            parts.pop()
    return None


def build_graph(files: Dict[str, pathlib.Path]) -> Dict[str, Set[str]]:
    known = set(files)
    graph: Dict[str, Set[str]] = {}
    for module, path in files.items():
        graph[module] = {
            resolved
            for resolved in (_resolve(imp, known) for imp in _raw_imports(path))
            if resolved
        }
    return graph


def reachable(graph: Dict[str, Set[str]], roots: List[str]) -> Set[str]:
    seen: Set[str] = set()
    stack = [root for root in roots if root in graph]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, ()))
    return seen


def _with_parents(modules: Set[str]) -> Set[str]:
    out = set(modules)
    for module in modules:
        parts = module.split(".")
        while len(parts) > 1:
            parts.pop()
            out.add(".".join(parts))
    return out


def audit() -> Dict[str, List[str]]:
    files = _collect_files()
    graph = build_graph(files)

    production = _with_parents(reachable(graph, PRODUCTION_ROOTS))
    scripts = _with_parents({m for m in graph if m.startswith("scripts.")})
    tests = _with_parents({m for m in graph if m.startswith("tests.")})
    if "tests.conftest" in graph:
        tests = tests | _with_parents(reachable(graph, ["tests.conftest"]))
    used = production | scripts | tests

    importers: Dict[str, int] = {module: 0 for module in graph}
    for module, deps in graph.items():
        for dep in deps:
            if dep in importers and dep != module:
                importers[dep] += 1

    # Package __init__ modules are addressed by their children, never directly.
    packages = {m for m, p in files.items() if p.name == "__init__.py"}
    orphans = sorted(
        module
        for module in graph
        if module not in used
        and module not in packages
        and importers.get(module, 0) == 0
    )
    return {
        "total_modules": sorted(graph),
        "production_reachable": sorted(production),
        "orphans": orphans,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="dead-code audit")
    parser.add_argument("--report", action="store_true", help="list every orphan")
    parser.add_argument("--strict", action="store_true", help="exit 1 when orphans exist")
    parser.add_argument("--json", help="write the full audit to this path")
    args = parser.parse_args(argv)

    result = audit()
    orphans = result["orphans"]

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(
        "modules=%d production_reachable=%d orphans=%d"
        % (len(result["total_modules"]), len(result["production_reachable"]), len(orphans))
    )
    if args.report or args.strict:
        for module in orphans:
            print("  ORPHAN  %s" % module)
    if args.strict and orphans:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
