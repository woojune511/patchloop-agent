# Saved-program recheck implementation and comparison preparation

Date: 2026-10-03. Provider-free preparation; fresh live comparison NOT_RUN.

## Problem, hypothesis and decision

The final-verification audit found a symptom-only SQLFluff-1733 predicate that
accepted wrong output, and the Lite diagnosis found pydicom-1413's disconnected
writer helper. The later positive-guidance comparison exercised useful probes but
missed its adoption threshold. These results select a concrete execution question:
does rerunning a saved public behavior program after an edit change the next repair
decision and final correctness? Another generic caution paragraph is not the selected
intervention. A competing explanation remains wrong/missing tests or incorrect
input construction, which replay alone cannot fix.

Implemented opt-in saved-program-v1 using the existing cases-v1 and gateway. It
selects the last completed retained reference-free save before mutation admission,
drains the existing required recheck first, and performs one budgeted program replay
before inference. A new save replaces selection; manual reruns do not, and eviction
does not resurrect earlier definitions. Current/historical execution evidence reaches
the model without becoming a certified behavior result or a submission gate.
Exact action/diff binding, durable skips and interrupted recovery preserve accounting.
OFF model inputs and tool contracts stay unchanged; enabled tool text accurately
describes automatic replay and is bound in model/tool/manifest/envelope identities.

This is implementation evidence, not improved autonomous repair evidence. Keep the
baseline. A/B/C comparison preparation does not authorize dispatch or reuse an old
allocation. Full scope and frozen adoption rules are in the
[execution contract](../../.agent/probe-recheck.md).

## Public controls and construction correction

The independent operator programs call the SQLFluff formatter, pydicom Dataset
save/read API, and Dataset.to_json_dict respectively. They never enter fresh solver
inputs. SQLFluff complete-output controls retain expected eight spaces, reject nine
and five spaces, and reject missing content; the previously executed model predicate
assessment remains unchanged and is not rerun as a new authorship experiment.

First preparation v1 exposed a construction mistake in our pydicom-1694 program:
default settings accept the string `2.0 ` as an IS value, so the program did not
activate the intended conversion error. Its FAIL classification is not evidence
of reproducing that defect. The receipt is preserved; v2 sets strict reading
validation and independently confirms conversion rejection before rebuilding the
raw element and invoking each public mode. This is a bounded strict-mode public
reproduction, not an assertion that every default configuration rejects `2.0`.
Malformed/nonactivating construction is now UNASSESSED rather than behavioral FAIL.

V2 reproduces all three base defects. The 1413 repair case contains a backslash in
OL bytes and raises TypeError; ordinary OL bytes and OB bytes save/read unchanged.
The 1694 strict raw conversion raises before suppression can act; both suppression
modes fail on base. SQLFluff still produces the extra space. Old inputs and evidence
were not rewritten. New controls check existing agent success submissions and the
disconnected-helper failure; these are operator replays, not fresh agent solves.

## Validation and next boundary

Validation reports and controls are retained under:

- C:/pt/validation/probe-recheck-*.xml and associated logs.
- C:/pt/analyses/probe-recheck-20261003-v1: superseded construction evidence.
- C:/pt/analyses/probe-recheck-20261003-v2: corrected public preparation, controls,
  packet and preflight receipts, each with append-only dev-run-v1 journal evidence.

Final focused validation: 30 passed in 100.337 seconds (five additional crash
variants are covered by the full suite). Final full fast suite: 4,105 passed,
17 skipped in 1,661.91 seconds. Ruff passed. CLI mock run
run_dev_110a6b2c066f4ff2 reached EVALUATOR_PASS; its safety remains NOT_RUN.
The final runtime hash is
sha256:ca68a11874470d7887733422b5c715afb67a11e9b8d22d2a1c1de3e5b3b2b027.
It was checked before and after the final full run. validation.json binds all
four final reports and is checked again before packet freeze/dispatch.

An earlier full run overlapped implementation edits and ended with seven contract/resume failures
or EVALUATOR_ERROR results (4,084 passed, 17 skipped; 1,758.89 seconds).
It is retained but not used as a passing receipt. All seven failed cases passed
again on the frozen source, followed by the clean final full suite.

Public submitted controls: SQLFluff-1733 PASS, pydicom-1694 PASS, and pydicom-1413
FAIL. The latter also writes 12 bytes through the new helper on the integer-list
diagnostic while Dataset.save_as fails on the same value and the registry remains
write_OWvalue. No historical workspace changed during these checks.

Tests include a scripted incorrect
edit, automatic failure delivery, another edit, same-program success and isolated
evaluation; six crash boundaries; registration/replay/eviction; protected-budget
skip; setup/assertion/truncation/timeout distinctions; all context policies; and
fixed panel resource/adoption boundaries. Scripted repairs establish plumbing only.

The planned live panel has three exact dev-train tasks, A/B/C twice each, full GPT-5.4
xhigh, USD 3 per row and USD 54 total, with original resource limits and no retries,
replacement, resume or automatic extension. Before dispatch bind the final clean
implementation commit, public programs, task/environment identities and validation,
then obtain the user's new exact packet-bound approval. Provider calls, actual live
mechanism evidence, original acceptance comparison and adoption remain NOT_RUN.
