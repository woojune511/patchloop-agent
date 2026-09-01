"""Capture a sanitized inventory from retained Harbor admission receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_harbor_admission import materialize_evidence_inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    binding = materialize_evidence_inventory(args.repository, args.source_root)
    print(json.dumps(binding.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
