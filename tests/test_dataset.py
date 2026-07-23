from __future__ import annotations

from patchloop.dataset import audit_dataset


def test_incomplete_dataset_is_reported_not_silently_accepted() -> None:
    result = audit_dataset("tasks")
    assert result["complete"] is False
    assert result["counts"] == {"smoke": 1}
    assert result["missing"]["cross-repo-heldout"] == 6
