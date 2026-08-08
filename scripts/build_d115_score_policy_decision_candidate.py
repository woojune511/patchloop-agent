"""Build the D-115 offline score-policy decision candidate and source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d115_score_policy_decision as d115


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    result = d115.run_d115_offline_source_gate(repository=args.repository)
    print(f"preflight_id={result['preflight_id']}")
    print(f"candidate_id={result['candidate_id']}")
    print(f"candidate_semantic_body_hash={result['candidate_semantic_body_hash']}")
    print(f"candidate_file_bytes={result['candidate_file_bytes']}")
    print(f"candidate_file_sha256={result['candidate_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['gate_semantic_body_hash']}")
    print(f"gate_file_bytes={result['gate_file_bytes']}")
    print(f"gate_file_sha256={result['gate_file_sha256']}")
    print(f"recommended_disposition={result['recommended_disposition']}")
    print(f"corrected_policy_selected={result['corrected_policy_selected']}")
    print(f"score_policy_correction_authorized={result['score_policy_correction_authorized']}")
    print(f"retrieval_ready={result['retrieval_ready']}")
    print(f"runtime_memory_injection_count={result['runtime_memory_injection_count']}")
    print(f"agent_runs={result['agent_runs']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
