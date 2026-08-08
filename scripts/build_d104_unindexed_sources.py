"""Materialize or validate the exact D-104 unindexed memory sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d104_unindexed_sources as d104


def _build(repository: Path, output: Path) -> dict:
    materialized = d104.materialize_d104_sources(
        repository=repository,
    )
    payload = d104.build_d104_source_gate(
        repository=repository,
    )
    content = d104.encode_d104_gate(payload)
    selected = output if output.is_absolute() else repository / output
    write = d104.write_d104_new_exact(selected, content, repository=repository)
    validation = d104.validate_d104_source_gate(selected, repository=repository)
    return {"source_writes": materialized["writes"], "gate_write": write, **validation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "validate"])
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=d104.DEFAULT_GATE_PATH)
    args = parser.parse_args()
    repository = args.repository.absolute()
    result = (
        _build(repository, args.output)
        if args.command == "build"
        else d104.validate_d104_source_gate(args.output, repository=repository)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
