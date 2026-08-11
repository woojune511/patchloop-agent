"""Materialize or validate the versioned no-call preflight source boundary."""

from __future__ import annotations

import argparse
import json

from patchloop.evals.versioned_no_call_preflight import (
    materialize_versioned_no_call_preflight_contract,
    run_versioned_no_call_preflight_source_qualification,
    validate_versioned_no_call_preflight_source_qualification,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_versioned_no_call_preflight_contract()
    elif args.qualify_source:
        result = run_versioned_no_call_preflight_source_qualification(
            source_commit=args.source_commit
        )
    else:
        result = validate_versioned_no_call_preflight_source_qualification()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
