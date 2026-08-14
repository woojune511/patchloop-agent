from __future__ import annotations

import json

from patchloop.evals.heldout_ac_binding_source_qualification import (
    run_heldout_ac_binding_source_qualification,
)


def main() -> None:
    print(
        json.dumps(
            run_heldout_ac_binding_source_qualification(),
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
