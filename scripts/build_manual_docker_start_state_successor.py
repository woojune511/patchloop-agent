from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals.manual_docker_start_state_successor import (
    MANUAL_START_CLAIM,
    load_contract,
    materialize_contract,
    qualify_source,
    record_manual_start_state,
    validate_manual_start_state,
    validate_source_qualification,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--validate-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate-source", action="store_true")
    mode.add_argument("--record-manual-start-state", action="store_true")
    mode.add_argument("--validate-state", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_contract()
    elif args.validate_contract:
        contract = load_contract()
        result = {
            "status": "OFFLINE_MANUAL_DOCKER_START_STATE_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_source_qualification()
    elif args.record_manual_start_state:
        result = record_manual_start_state(
            claim=MANUAL_START_CLAIM,
            recorded_at=datetime.now(UTC),
        )
    else:
        result = validate_manual_start_state()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
