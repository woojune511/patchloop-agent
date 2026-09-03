"""Deterministic verification."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from patchloop.verifier.core import EvaluationEngine

__all__ = ["EvaluationEngine"]


def __getattr__(name: str) -> Any:
    """Resolve the public evaluator without importing it during package initialization."""
    if name == "EvaluationEngine":
        from patchloop.verifier.core import EvaluationEngine

        globals()[name] = EvaluationEngine
        return EvaluationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
