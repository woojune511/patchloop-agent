"""Build the D-113 offline D-112 validator-correction authorization candidate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d113_validator_correction_authorization as d113


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    result = d113.run_d113_offline_source_gate(repository=args.repository)
    print(f"preflight_id={result['preflight_id']}")
    print(f"candidate_id={result['candidate_id']}")
    print(f"candidate_semantic_body_hash={result['candidate_semantic_body_hash']}")
    print(f"candidate_file_bytes={result['candidate_file_bytes']}")
    print(f"candidate_file_sha256={result['candidate_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['semantic_body_hash']}")
    print(f"gate_file_sha256={result['file_sha256']}")
    print(f"gap_ids={','.join(result['gap_ids'])}")
    print(f"protected_fingerprints_equal={result['protected_fingerprints_equal']}")
    print(f"validator_correction_authorized={result['validator_correction_authorized']}")
    print(f"validator_correction_implemented={result['validator_correction_implemented']}")
    print(f"retrieval_calls={result['retrieval_calls']}")
    print(f"provider_calls_made={result['provider_calls_made']}")
    print(f"evaluator_calls_made={result['evaluator_calls_made']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
