"""Materialize or replay the execution-closed all-cross successor artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.fresh_all_cross_successor import materialize_all_cross_successor


def main() -> None:
    bindings = materialize_all_cross_successor(Path.cwd())
    print(
        json.dumps(
            [binding.model_dump(mode="json") for binding in bindings],
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
