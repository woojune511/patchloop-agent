"""Configuration helpers with one audited merge defect."""


def merge_config(
    base: dict[str, object], override: dict[str, object]
) -> dict[str, object]:
    """Return base values updated by every explicitly provided override."""

    result = dict(base)
    for key, value in override.items():
        result[key] = value or result.get(key)
    return result
