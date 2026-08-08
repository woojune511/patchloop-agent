"""Preflight, materialize once, or validate the D-114 successor correction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d114_d112_validator_correction as d114


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--validate-sealed", action="store_true")
    mode.add_argument("--validate-current", action="store_true")
    mode.add_argument("--validate-evidence", action="store_true")
    args = parser.parse_args()

    if args.preflight:
        preflight = d114.preflight_d114_correction(repository=args.repository)
        result = {
            "candidate_id": preflight["authorization"]["candidate"]["candidate_id"],
            "authorized_action_hash": d114.EXPECTED_D113_ACTION_HASH,
            "protected_pre_state": preflight["protected_pre_state"],
            "correction_evidence_materializations": 0,
        }
    elif args.execute:
        result = d114.execute_d114_correction(repository=args.repository)
    elif args.validate_sealed:
        result = d114.validate_d112_history(
            repository=args.repository,
            mode=d114.ValidationMode.SEALED_HISTORICAL,
        )
    elif args.validate_current:
        result = d114.validate_d112_history(
            repository=args.repository,
            mode=d114.ValidationMode.CURRENT_INPUT,
        )
    else:
        result = d114.validate_d114_correction_evidence(repository=args.repository)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
