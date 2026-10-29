# Runtime usability, contract repair and local overhead

Date: 2026-10-29. Starting HEAD: `87c06386`. Local implementation and validation;
no provider invocation, Docker execution, private feedback or quality claim.

## Problem and decision

The architecture discussion identified stale contract tests, unclear action-specific
budget consequences, overly small edit quotas, constrained file access, and repeated
state processing. The user requested these engineering changes before another task
list. They matter because a valid edit can disappear after exploration while money,
time and mutation slots remain, and multiple small related changes consume scarce
responses/edits. A blanket prompt, context or monetary increase is not the intervention.

The preceding audit reproduced 11 failures among 28 focused tests: ten assertions
still expected retired public mutation annotations, and one expected a fixed context
without `repair_stage`. Following that smoke farther exposed a production defect:
phase projection replaced already deduplicated state with raw context, restoring
duplicate tool results. Fixing tests alone would have hidden that defect.

## Changes

- Fresh mutation schema tests cover the six execution/intent fields separately from
  legacy absent/null/value preservation. Current phase context is explicitly checked.
  Annotation tests now distinguish durable rejected updates from what the compact
  repair view actually delivers. The observer fixture supplies the same v11 validator
  as the real launcher; historical wrapper bytes are unchanged.
- An action-specific forecast explains ordinary versus reserved correction responses,
  read/search batch sizes, probes and single/paired tests, and the subsequent successful
  edit/check/finish minimum. Actual exclusion reasons distinguish response, action,
  monetary and time constraints. Forecasts add no gate/reserve and assume unchanged
  obligations/current anchors; they cannot promise a correct future edit.
  A mandatory selected-test comparison exposes only its two-execution variant.
- Fresh dev/repair defaults permit 12 accepted edits instead of four. Historical
  explicit three/four-edit settings and total call/action/time/cost caps are preserved.
  Twelve is an engineering allowance, not an empirically optimal value.
- Fresh reads no longer have a separate 400-line rejection; 24,000-character
  complete-line pagination still bounds delivery. Legacy range-only reads retain
  their wire contract. `occurrence="all"` applies all exact matches in one tracked
  file in one mutation; every anchor must be observed, with ordinary full-diff scope,
  test preservation and offset/hash-bound crash recovery.
- Phase projection now precedes native result deduplication, source referencing and
  compaction, so there is one common delivery path. Native results remain available.
- The current segmented-input audit reconstructs diagnosis/repair/completion and
  thin views before strict equality checking. It no longer rejects valid compact
  deliveries by comparing them to the general notes/plan view. Native binding,
  public authority and state-tamper checks remain in place.
- Journal reads retain a validated byte prefix and decoded events. Every read still
  reads the file and compares bytes; only identical prefixes skip decoding/hash work.
  New suffixes are validated, changed prefixes are fully revalidated, and returned
  objects are deep copies. No mtime shortcut, journal rewrite or weaker fsync contract.

## Local performance question and result

Question: can repeated journal decoding/hash validation be avoided without losing
corruption, torn-tail, external-append or caller-mutation detection? Baseline: old
`DevJournal.events()` at starting HEAD; intervention: verified-prefix reuse only.
Selection: largest of the 20 saved dev20 public journals, chosen by byte length,
`C:/pt/repair-dev20-run-v2/18/runs/run_dev_6bcac837b62a4354.jsonl` (787,336 bytes,
275 events). Same host/interpreter and unchanged journal; five blocks of 20 reads,
median block time. No model, tokens or dollars. Retain only with a meaningful local
reduction and all integrity tests passing; stop if semantics differ. This is a local
component comparison, not an end-to-end agent speed or repair-quality experiment.

Baseline median: 0.239162 seconds per 20 reads. After: 0.114471 seconds, about 52%
less time in this microbenchmark. Existing state tests plus new integrity tests
passed (25). The cache retains one raw journal and its decoded events per object;
memory and copy costs remain, and long-run end-to-end latency was not measured.

The earlier dev20 read-only timing audit found 4,368.414 seconds in 223 provider
calls, 148.644 seconds in 223 input counts, and 518.911 seconds from solver finish
to evaluation finish for 19 submissions. Total active time was 6,117.366 seconds;
batch wall time 7,158.386. Provider-call intervals are about 71% of active time and
include transport/service waiting, not just reasoning. Local journal speed cannot
be extrapolated to a 52% end-to-end improvement.

## Validation

- Final quick manifest plus mock isolated-evaluator smoke: **1,022 passed in
  176.23 seconds**, four file-grouped workers. JUnit: `C:/pt/tmp/uq5.xml`.
  Command: `.venv/Scripts/python.exe -m pytest @tests/quick.txt
  tests/test_dev_runner.py::test_mock_end_to_end_isolated_evaluator_and_public_context
  -n 4 --dist loadfile --max-worker-restart=0 --basetemp C:/pt/tmp/uq5
  -o "addopts=-p no:cacheprovider" -q --tb=short --junitxml=C:/pt/tmp/uq5.xml`.
- Focused checks include all-match recovery/scope/CLI, byte-prefix integrity,
  action-budget consequences and compact annotation delivery. The latter two
  groups passed 11 and 9 tests respectively; state/prefix checks passed 25.
  Historical caller fixture/assessment and documentation checks passed 20 in
  13.92 seconds. The updated segmented audit and saved checkpoint tests passed 39;
  historical-cap and current-drift checks passed four in 27.56 seconds.
  The previously blocked caller-evidence execution file then passed all nine tests
  in 32.06 seconds (`C:/pt/tmp/ufinal-caller.xml`). Final documentation checks passed
  six in 0.19 seconds. No total duration was retained for the 39-test audit group.
- Ruff and `git diff --check` passed. HTML static validation found 51 unique IDs,
  54 valid local/fragment links and unchanged scripts. Visual browser QA was not
  completed: the browser tool's URL policy rejected local `file://` navigation.
- The full suite was attempted with bounded failure stopping, **not completed**.
  Before follow-up fixes, `C:/pt/tmp/uf4.txt` recorded 231 passed, 9 failed and
  7 setup errors. A clean worktree at `87c06386072e6651e35258a832a243126f2d8afe`
  reproduced six annotation failures, the observer fixture failure, boundary-panel B
  treatment loss, and a representative segmented-audit setup error. The new default
  also exposed one historical caller fixture's implicit four-edit assumption; its
  configuration is now explicit. Baseline selection, output and provenance are in
  `C:/pt/tmp/uf4-baseline-args.txt`, `uf4-baseline-result.txt` and
  `uf4-baseline-provenance.json`. The temporary baseline worktree was archived.
- The historical boundary-panel B treatment-delivery assertion remains unresolved:
  that driver patches planning instructions, but compact phase prompts do not consume
  them. The assertion is a useful incompatibility detector; it was not removed and
  its treatment was not added to general prompts. This driver must not be interpreted
  as a valid current A/B comparison. Remaining full-suite tests are unverified.

During verification, blank entries in the quick argument manifest accidentally
selected the repository root. Collection generated bytecode caches in task/fixture
trees and temporarily changed snapshot hashes. Those contaminated runs are excluded
from the results above. After checking exact paths and creation times, only the newly
created cache directories were removed; the original smoke snapshot hash was restored
to `sha256:ea86e87d65632d2cadc0a65066bdd1fcdfb66ef3799ff4fed85ea1c2626a3d67`.
The manifest now has no blank selectors and a layout test prevents recurrence.
Final tests used external temporary state. Existing user changes remain untouched.

## Follow-up questions from the discussion

1. Does the explicit action forecast change model choices when one probe would
   consume the last edit route? Reconstruct the public checkpoint first; any live
   comparison needs a new exact task/model/repetition/cap authorization.
2. Does a larger edit allowance help tasks that actually exhausted edits, without
   increasing regressions or pointless revisions? Keep task/model/other limits fixed;
   score correctness as well as time, cost and submission. Do not pool historical scores.
3. Which real tasks require new files, atomic multi-file edits or explicit undo?
   Their path admission, diff generation, rollback, evaluation and recovery must form
   one coherent contract. Existing-file all-match replacement does not supply them.
4. Why does the agent sometimes finish after observing the original bug remains?
   Separate task interpretation, expectation grounding, failure use and resource loss;
   do not automatically add another global reproduction gate.
5. Which optional diagnostic/context layers provide useful decisions? Remove redundant
   projections first, preserve legacy receipt reading, and compare behavior before
   deleting deeper paths. Retire or explicitly isolate obsolete comparison drivers,
   starting with boundary-panel B, before reusing their labels on current prompts.
   More notes or hypothesis fields are not a default remedy.
6. Can redundant model turns and repeated exploration be reduced? Measure per-stage
   wall time and accuracy before changing reasoning effort or call admission. Mandatory
   pre-dispatch counting and independent evaluation remain necessary boundaries.
