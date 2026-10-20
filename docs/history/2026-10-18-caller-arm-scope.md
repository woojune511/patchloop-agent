# Caller preparation: frozen-arm test scope

Follow-up to the [target-path correction](2026-10-18-caller-target.md), before any
paid solve. The whole suite on `2f3b03a` completed with 5,330 passed, 20 skipped and
one failure. Its result remains immutable under
`C:/pt/calleruptake18/validation-v2/full-retain-failures/`.

The failure reproduced independently without the temporary-retention setting. It
was an applicability error in the old E/J experiment test, not a timeout or a new
repair outcome. The default development checkout was required to match all five
source files frozen at `168765b` byte-for-byte. The existing public-caller import
and description in `patchloop/dev/tools.py` legitimately differ from that snapshot;
those two additions already preceded this preparation work.

The default development suite still tests E1J1 selection, authority labels, prompt
bounds, transitions and two-reference/resource limits directly. Selecting any
`PATCHLOOP_TEST_REPAIR_ARM` value explicitly still requires exact historical source
bytes, including E1J1. The frozen replay shares that strict validator. The original
base, transforms, manifests, checkouts, histories and grades remain unchanged.

Four unconditional fixture cases verify each exact frozen arm and reject every
other arm label plus an unrelated source-byte change. Explicit E1J1 and E0J0
negative runs reject the current development checkout; the environment cannot
relabel it as a frozen experiment. No assertion, timeout, resource limit or runtime
behavior is removed to obtain a pass. The agent runtime content hash is unchanged.

Final readiness now comes from `C:/pt/calleruptake18/validation-v3/validation.json`,
`preparation-complete-v3.json`, `inputs-final-v3/` and `final-receipt-v3.json`.
The packet path remains `C:/pt/calleruptake18/packet/manifest.json` and is created
only after the final-commit full suite, focused tests, Ruff and isolated mock smoke
pass. Failed and interrupted earlier runs do not count as passing validation.

Source acquisition/use and real repair outcomes remain NOT_RUN. All solver,
transition, two-reference, probe and cost bounds remain fixed. The previously
recorded lack of a real correct missing-input repair positive control remains a
limitation; this test-scope correction supplies no repair-quality evidence.
