"""Materialize the no-call Harbor partial-runner source qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_harbor_partial_runner import materialize_source_qualification


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harbor-source", type=Path, required=True)
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    binding = materialize_source_qualification(repository, arguments.harbor_source)
    print(json.dumps(binding.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
