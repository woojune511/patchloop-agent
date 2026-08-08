"""Build or validate the exact D-102 decision/candidate gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d102_maintainer_assisted_decisions as d102


def _build(repository: Path, output: Path) -> dict:
    payload = d102.build_d102_decision_candidate_gate(repository=repository)
    content = d102.encode_d102_gate(payload)
    selected = output if output.is_absolute() else repository / output
    selected.parent.mkdir(parents=True, exist_ok=True)
    if selected.exists():
        if selected.read_bytes() != content:
            raise d102.D102DecisionGateError("D-102 gate exists with different exact bytes")
    else:
        selected.write_bytes(content)
    return d102.validate_d102_decision_candidate_gate(
        selected,
        repository=repository,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "validate"])
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=d102.DEFAULT_GATE_PATH)
    args = parser.parse_args()
    repository = args.repository.resolve()
    result = (
        _build(repository, args.output)
        if args.command == "build"
        else d102.validate_d102_decision_candidate_gate(
            args.output,
            repository=repository,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
