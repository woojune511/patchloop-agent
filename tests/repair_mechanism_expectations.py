"""Expected experimental contract only; this variable never switches runtime behavior."""
import os

FROZEN_ARM = os.environ.get("PATCHLOOP_TEST_REPAIR_ARM")
ARM = "E1J1" if FROZEN_ARM is None else FROZEN_ARM
if ARM not in {"E0J0", "E1J0", "E0J1", "E1J1"}:
    raise ValueError("Unknown repair experiment test contract")
EVIDENCE = ARM[1] == "1"
JUDGMENT = ARM[3] == "1"
