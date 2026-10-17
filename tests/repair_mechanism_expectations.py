"""Expected experimental contract only; this variable never switches runtime behavior."""
import os

ARM = os.environ.get("PATCHLOOP_TEST_REPAIR_ARM", "E1J1")
if ARM not in {"E0J0", "E1J0", "E0J1", "E1J1"}:
    raise ValueError("Unknown repair experiment test contract")
EVIDENCE = ARM[1] == "1"
JUDGMENT = ARM[3] == "1"
