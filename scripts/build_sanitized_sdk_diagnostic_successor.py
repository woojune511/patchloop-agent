from __future__ import annotations

import argparse
import json

from patchloop.evals.sanitized_sdk_diagnostic_successor import (
    load_contract,
    materialize_contract,
    qualify_source,
    validate_source_qualification,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--validate-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate-source", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_contract()
    elif args.validate_contract:
        contract = load_contract()
        result = {
            "status": "OFFLINE_SANITIZED_SDK_DIAGNOSTIC_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = qualify_source(source_commit=args.source_commit)
    else:
        result = validate_source_qualification()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
