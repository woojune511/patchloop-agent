"""Build or validate the offline evaluator-v2 A/C source qualification."""

from __future__ import annotations

import json

from patchloop.evals.evaluator_v2_source_qualification import (
    run_evaluator_v2_ac_source_qualification,
)


def main() -> None:
    print(
        json.dumps(
            run_evaluator_v2_ac_source_qualification(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
