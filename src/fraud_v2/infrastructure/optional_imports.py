from __future__ import annotations

import importlib
from types import ModuleType


def optional_module(name: str, extra: str) -> ModuleType:
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise RuntimeError(
            f"Optional dependency '{name}' is missing. Install with `uv sync --extra {extra}`."
        ) from exc
