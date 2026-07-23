"""Elapsed-time formatting with one audited boundary defect."""


def format_elapsed(seconds: int) -> str:
    """Format a non-negative elapsed duration as seconds or completed minutes."""

    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if seconds < 60:
        return f"{seconds}s"
    return f"{round(seconds / 60)}m"
