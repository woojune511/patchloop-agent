"""Materialize the exact execution-closed 144-row admission runner candidate."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.fresh_harbor_partial_runner import materialize_candidate


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    binding = materialize_candidate(repository)
    print(json.dumps(binding.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
