"""fraud-v2 local fraud decision platform."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

__all__ = ["__version__"]


def _package_version() -> str:
    try:
        return version("fraud-v2")
    except PackageNotFoundError:
        version_path = Path(__file__).resolve().parents[2] / "VERSION"
        if version_path.exists():
            return version_path.read_text(encoding="utf-8").strip()
        return "0.0.0"


__version__ = _package_version()
