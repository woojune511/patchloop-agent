"""Dataset completeness and split-leakage audit."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package

EXPECTED_COUNTS = {
    "smoke": 3,
    "dev-train": 6,
    "dev-validation": 2,
    "same-repo-heldout": 6,
    "cross-repo-heldout": 6,
}


def audit_dataset(tasks_root: str | Path | None = None) -> dict:
    root = Path(tasks_root) if tasks_root else repository_root() / "tasks"
    packages = []
    errors = []
    identities = set()
    for public_path in sorted(root.rglob("public.yaml")):
        try:
            package = load_task_package(public_path.parent)
        except ContractError as exc:
            errors.append({"path": str(public_path.parent), "error": str(exc)})
            continue
        identity = (package.public.task_id, package.public.task_version)
        if identity in identities:
            errors.append({"path": str(public_path.parent), "error": "duplicate task identity"})
        identities.add(identity)
        packages.append(package)
    counts = Counter(package.public.split for package in packages)
    missing = {
        split: expected - counts.get(split, 0)
        for split, expected in EXPECTED_COUNTS.items()
        if counts.get(split, 0) < expected
    }
    ledger_path = repository_root() / "data" / "oss-candidate-ledger.csv"
    ledger = (
        list(csv.DictReader(ledger_path.open(encoding="utf-8"))) if ledger_path.exists() else []
    )
    audited_oss = [row for row in ledger if row.get("status") == "selected"]
    complete = not errors and not missing and len(audited_oss) == 6
    return {
        "complete": complete,
        "task_count": len(packages),
        "counts": dict(counts),
        "expected_counts": EXPECTED_COUNTS,
        "missing": missing,
        "errors": errors,
        "oss_selected": len(audited_oss),
        "oss_required": 6,
    }
