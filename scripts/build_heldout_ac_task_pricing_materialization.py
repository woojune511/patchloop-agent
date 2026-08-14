from __future__ import annotations

import json

from patchloop.evals.heldout_ac_task_pricing_materialization import (
    run_heldout_ac_task_pricing_materialization,
)


def main() -> None:
    print(json.dumps(run_heldout_ac_task_pricing_materialization(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
