from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory.d100_group_admission import (
    DEFAULT_SOURCE_GATE_PATH,
    build_d100_source_gate,
    encode_d100_source_gate,
)
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the deterministic D-100 group-admission mechanism source gate."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_SOURCE_GATE_PATH)
    args = parser.parse_args()

    root = repository_root()
    output = args.output if args.output.is_absolute() else root / args.output
    payload = build_d100_source_gate(repository=root)
    encoded = encode_d100_source_gate(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    print(output)
    print(f"bytes={len(encoded)}")
    print(f"sha256={sha256_bytes(encoded)}")


if __name__ == "__main__":
    main()
