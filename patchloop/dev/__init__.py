"""Mutable, unofficial PatchLoop development runtime."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from patchloop.dev.runner import run_dev

__all__ = ["run_dev"]


def __getattr__(name: str) -> Any:
    """Resolve the public runner without importing it during package initialization."""
    if name == "run_dev":
        from patchloop.dev.runner import run_dev

        globals()[name] = run_dev
        return run_dev
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
