from __future__ import annotations

from pathlib import Path

from patchloop.agent.completion_loop_successor_qualification import (
    QUALIFICATION_PATH,
    build_ordered_correction_qualification,
    qualification_bytes,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    qualification = build_ordered_correction_qualification(root)
    output = root / QUALIFICATION_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(qualification_bytes(qualification))
    print(output.as_posix())


if __name__ == "__main__":
    main()
