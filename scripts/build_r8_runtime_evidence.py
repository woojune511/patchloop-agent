"""Build or validate the append-only R8 runtime evidence correction."""

from __future__ import annotations

import json

from patchloop.evals.r8_completion_correction import run_r8_runtime_evidence


def main() -> None:
    print(json.dumps(run_r8_runtime_evidence(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
