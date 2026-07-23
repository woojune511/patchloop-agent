from __future__ import annotations

from patchloop.dataset import audit_dataset


def test_incomplete_dataset_is_reported_not_silently_accepted() -> None:
    result = audit_dataset("tasks")
    assert result["complete"] is False
    assert result["task_count"] == 4
    assert result["counts"] == {"dev-train": 1, "smoke": 3}
    assert "smoke" not in result["missing"]
    assert result["missing"]["dev-train"] == 5
    assert result["missing"]["cross-repo-heldout"] == 6
