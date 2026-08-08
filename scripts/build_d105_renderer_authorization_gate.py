"""Materialize and validate the deterministic D-105 renderer source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d105_renderer_authorization as d105


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--gate",
        type=Path,
        default=d105.DEFAULT_GATE_PATH,
    )
    args = parser.parse_args()

    repository = args.repository.resolve()
    gate_path = args.gate if args.gate.is_absolute() else repository / args.gate
    gate = d105.preflight_d105_publication(gate_path, repository=repository)
    content = d105.encode_d105_gate(gate)
    materialized = d105.materialize_d105_renders(repository=repository)
    write = d105.write_d105_new_exact(gate_path, content, repository=repository)
    validated = d105.validate_d105_gate(gate_path, repository=repository)

    print(f"rendered_memory_count={materialized['rendered_memory_count']}")
    print(f"gate_id={validated['gate_id']}")
    print(f"semantic_body_hash={validated['semantic_body_hash']}")
    print(f"gate_file_bytes={validated['gate_file_bytes']}")
    print(f"gate_file_sha256={validated['gate_file_sha256']}")
    print(f"created={write['created']}")
    print(f"idempotent_retry={write['idempotent_retry']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
