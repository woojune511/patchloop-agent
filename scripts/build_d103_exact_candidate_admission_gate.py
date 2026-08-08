"""Build or validate the exact D-103 candidate-admission gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d103_exact_candidate_admission as d103


def _build(repository: Path, output: Path) -> dict:
    payload = d103.build_d103_exact_admission_gate(repository=repository)
    content = d103.encode_d103_gate(payload)
    selected = output if output.is_absolute() else repository / output
    selected.parent.mkdir(parents=True, exist_ok=True)
    if selected.exists():
        if selected.read_bytes() != content:
            raise d103.D103ExactAdmissionError("D-103 gate exists with different exact bytes")
    else:
        selected.write_bytes(content)
    return d103.validate_d103_exact_admission_gate(
        selected,
        repository=repository,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "validate"])
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=d103.DEFAULT_GATE_PATH)
    args = parser.parse_args()
    repository = args.repository.resolve()
    result = (
        _build(repository, args.output)
        if args.command == "build"
        else d103.validate_d103_exact_admission_gate(
            args.output,
            repository=repository,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
