"""Materialize or replay the no-call Harbor admission sanitizer source gate."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.fresh_harbor_admission import materialize_source_qualification


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    binding = materialize_source_qualification(repository)
    print(json.dumps(binding.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
