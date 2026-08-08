"""Build the D-109 offline index-freeze authorization candidate and gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d109_index_freeze_authorization as d109


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    result = d109.run_d109_offline_source_gate(repository=args.repository)
    print(f"runtime_preflight_id={result['runtime_preflight_id']}")
    print(f"candidate_id={result['candidate_id']}")
    print(f"candidate_semantic_body_hash={result['candidate_semantic_body_hash']}")
    print(f"candidate_file_sha256={result['candidate_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['gate_semantic_body_hash']}")
    print(f"gate_file_sha256={result['gate_file_sha256']}")
    print(f"runtime_index_written={result['runtime_index_written']}")
    print(f"frozen_marker_created={result['frozen_marker_created']}")
    print(f"index_freeze_authorized={result['index_freeze_authorized']}")
    print(f"memory_index_frozen={result['memory_index_frozen']}")
    print(f"retrieval_ready={result['retrieval_ready']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    print(f"provider_calls_made={result['provider_calls_made']}")
    print(f"evaluator_calls_made={result['evaluator_calls_made']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
