"""Materialize the hash-only deterministic partial-admission preregistration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_harbor_partial_admission import materialize_preregistration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Trusted retained admission root; patch bodies are never printed or persisted.",
    )
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    binding = materialize_preregistration(repository, arguments.source_root)
    print(json.dumps(binding.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
