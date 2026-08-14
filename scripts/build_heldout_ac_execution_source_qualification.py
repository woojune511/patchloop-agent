from __future__ import annotations

import json

from patchloop.evals.heldout_ac_execution_source_qualification import (
    run_heldout_ac_execution_source_qualification,
)


def main() -> None:
    print(json.dumps(run_heldout_ac_execution_source_qualification(), indent=2))


if __name__ == "__main__":
    main()
