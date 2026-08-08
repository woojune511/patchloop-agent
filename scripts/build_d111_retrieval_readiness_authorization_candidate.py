"""Build the D-111 offline retrieval-readiness candidate and source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d111_retrieval_readiness_authorization as d111


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    result = d111.run_d111_offline_source_gate(repository=args.repository)
    print(f"preflight_id={result['preflight_id']}")
    print(f"candidate_id={result['candidate_id']}")
    print(f"candidate_semantic_body_hash={result['candidate_semantic_body_hash']}")
    print(f"candidate_file_bytes={result['candidate_file_bytes']}")
    print(f"candidate_file_sha256={result['candidate_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['semantic_body_hash']}")
    print(f"gate_file_sha256={result['file_sha256']}")
    print(f"retrieval_probe_authorized={result['retrieval_probe_authorized']}")
    print(f"retrieval_called={result['retrieval_called']}")
    print(f"query_embedding_encoded={result['query_embedding_encoded']}")
    print(f"runtime_memory_injection_count={result['runtime_memory_injection_count']}")
    print(f"provider_calls_made={result['provider_calls_made']}")
    print(f"evaluator_calls_made={result['evaluator_calls_made']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
