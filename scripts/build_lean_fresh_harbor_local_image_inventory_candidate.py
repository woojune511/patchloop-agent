"""Materialize the execution-closed local-image inventory candidate."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.fresh_harbor_local_image_inventory import materialize_candidate


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    value = materialize_candidate(root)
    print(json.dumps(value.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
