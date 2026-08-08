"""Build the D-107 portable-index and token-count no-call source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d107_portable_index_freeze_readiness as d107


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()

    result = d107.run_d107_offline_source_gate(repository=args.repository)
    print(f"portable_validation_id={result['portable_validation_id']}")
    print(f"token_plan_id={result['token_plan_id']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['gate_semantic_body_hash']}")
    print(f"gate_file_sha256={result['gate_file_sha256']}")
    print(f"request_artifact_count={result['request_artifact_count']}")
    print(f"provider_calls_made={result['provider_calls_made']}")
    print(f"memory_index_frozen={result['memory_index_frozen']}")
    print(f"retrieval_ready={result['retrieval_ready']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
