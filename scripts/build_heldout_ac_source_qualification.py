"""Build or validate the offline held-out A/C contract source qualification."""

from __future__ import annotations

import json

from patchloop.evals.heldout_ac_source_qualification import (
    run_heldout_ac_source_qualification,
)


def main() -> None:
    print(
        json.dumps(
            run_heldout_ac_source_qualification(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
