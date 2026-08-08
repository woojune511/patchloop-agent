"""Build the D-116 public failure-class signal contract candidate and gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d116_public_failure_class_signal_contract as d116


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    result = d116.run_d116_contract_candidate(repository=args.repository)
    print(f"receipt_id={result['receipt_id']}")
    print(f"preflight_id={result['preflight_id']}")
    print(f"candidate_id={result['candidate_id']}")
    print(f"candidate_semantic_body_hash={result['candidate_semantic_body_hash']}")
    print(f"candidate_file_bytes={result['candidate_file_bytes']}")
    print(f"candidate_file_sha256={result['candidate_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['gate_semantic_body_hash']}")
    print(f"gate_file_bytes={result['gate_file_bytes']}")
    print(f"gate_file_sha256={result['gate_file_sha256']}")
    print(f"candidate_status={result['candidate_status']}")
    print(f"classifier_execution_count={result['classifier_execution_count']}")
    print(f"calibration_execution_count={result['calibration_execution_count']}")
    print(f"three_class_calibrated={result['three_class_calibrated']}")
    print(f"score_policy_correction_authorized={result['score_policy_correction_authorized']}")
    print(f"retrieval_ready={result['retrieval_ready']}")
    print(f"runtime_memory_injection_count={result['runtime_memory_injection_count']}")
    print(f"agent_runs={result['agent_runs']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
