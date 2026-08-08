from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d108_provider_token_count_execution as d108


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare, preflight, or execute the one-use D-108 token-count gate."
    )
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.prepare_approval:
        result = d108.materialize_d108_approval_receipt(repository=args.repository)
        print(f"receipt_id={result['receipt_id']}")
        print(f"semantic_body_hash={result['semantic_body_hash']}")
        print(f"file_sha256={result['file_sha256']}")
        return 0

    if args.preflight:
        result = d108.preflight_d108_execution(repository=args.repository)
        print(f"ready={str(result['ready']).lower()}")
        print(f"provider_calls_made={result['provider_calls_made']}")
        print(f"generation_calls_made={result['generation_calls_made']}")
        return 0

    result = d108.execute_d108_provider_token_counts(repository=args.repository)
    for key in (
        "gate_id",
        "semantic_body_hash",
        "gate_file_sha256",
        "receipt_id",
        "receipt_file_sha256",
        "baseline_input_tokens",
        "with_memory_input_tokens",
        "memory_delta_tokens",
        "provider_input_token_count_calls_made",
        "provider_generation_calls_made",
        "automatic_retry_used",
        "provider_exact_budget_validated",
        "index_freeze_authorized",
        "retrieval_ready",
        "core_campaign_unlocked",
    ):
        print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
