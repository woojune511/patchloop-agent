"""Path matching helpers with one audited boundary defect."""


def is_path_within(path: str, root: str) -> bool:
    """Return whether path is root itself or one of its descendants."""

    normalized_path = path.replace("\\", "/").rstrip("/")
    normalized_root = root.replace("\\", "/").rstrip("/")
    return normalized_path.startswith(normalized_root)
