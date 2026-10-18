# Caller oracle target identity follow-up

Follow-up to the [preparation record](2026-10-18-caller-ready.md), before any new
paid solve or outcome exposure. The first whole-suite run on `3e32f89` was stopped
at about 18% when an additional synthetic positive-control review exposed a false
rejection in the new diagnostic oracle. Its interrupted log and nonzero exit are
preserved under `C:/pt/calleruptake18/validation/`; it is not passing full-suite evidence.

The observer can report the same child as `src/project/file.py`,
`./src/project/file.py` or an absolute path under the frozen cwd. The first parser
compared the path spelling literally, so an otherwise valid exit-0 observation of
that exact existing child was classified FAIL. This could obscure the study's repair
outcome independently of whether the model used caller evidence, and therefore had
to be corrected before freezing the packet.

The parser now resolves the observed path relative to the recorded cwd and requires
equality with the exact child, together with `path_exists=true`. Tests accept the
equivalent spellings and reject sibling, outside-root, escaping and nonexistent
targets. The real installed Pylint `get_ast` entry remains required. Exit, F0010,
source/caller origins, input layout, setup, cleanup and uncertainty checks are unchanged.
No program, candidate, source, environment, limit or successful-repair oracle was
tuned after observing new model outcomes. The frozen observer bytes and actual saved
calibration receipts are reused and regraded; no additional caller probe is necessary.

The final validation location is `C:/pt/calleruptake18/validation-v2/validation.json`,
with `preparation-complete-v2.json` and final request captures in `inputs-final-v2/`.
The executable packet remains `C:/pt/calleruptake18/packet/manifest.json`; it is created
only when the final-commit whole suite, focused tests, Ruff and mock smoke all pass.
The final commit/hash/counts belong to those immutable receipts, not the interrupted
earlier run. `final-receipt-v2.json` closes the validation and packet binding.

The absence of a real correct missing-input repair positive control remains explicit;
these synthetic parser cases do not establish a repair. Model uptake and repair-effect
measurement remain NOT_RUN. Transition rules, two references, all solver/probe/host
assessment limits and the USD 10.56 twelve-row allocation are unchanged. No paid
generation/counting or credential-content read is authorized by preparation.
