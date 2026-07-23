from __future__ import annotations

from patchloop.dataset import audit_dataset


def test_incomplete_dataset_is_reported_not_silently_accepted() -> None:
    result = audit_dataset("tasks")
    assert result["complete"] is False
    assert result["task_count"] == 3
    assert result["counts"] == {"smoke": 3}
    assert "smoke" not in result["missing"]
    assert result["missing"]["cross-repo-heldout"] == 6
