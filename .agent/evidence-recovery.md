# Source recovery and fixed reproduction scope

Implemented in dev-head; local evidence only. No repair-success improvement has
been established. History search remains opt-in (`public-v1`), probes remain
opt-in, and existing transition rules, two question references, source/input,
action, wall-time and spending limits are unchanged.

## Recover missing source at an ordinary search hit

With history enabled, `search_files` can expand a hit using an earlier `read_file`
range actually dispatched to this run's model. Candidates must overlap the hit,
contain the literal query and match its current path/file hash. The smallest
complete matching read is preferred; no task names or predefined caller paths.
Existing native source visibility suppresses redundant restoration.

The union preserves both the complete earlier read and the current hit's edges.
Other search hits are retained. All source text shares the existing 24,000-character
search limit; if the union cannot fit, return the original hit with a labelled
range and history record ID. Old file versions are pointers only: read current
source for edits, or fetch the historical record explicitly for comparison.
The recovered range is observed text, not necessarily a whole function.

The index is derived from dispatched input artifacts, not arbitrary action logs,
plans, encrypted reasoning or private evaluation. Pending/current and future
deliveries cannot enter it. The existing process lock protects parallel reads.
Expanded results are durable receipts but are not cached as ordinary search
answers: new actions recompute visibility, while an identical action ID/input
replays its original receipt. No additional action or question reference is used.
Larger results still consume context and can affect later size transitions; no
claim is made that the rest of a future request will remain unchanged.

## Bind a proposed original-task reproduction before execution

`run_probe.reproduction` is nullable in the ordinary probe surface. Null means a
helper or unbound diagnostic. A declaration includes a literal public issue
quote, a fully qualified Python entrypoint, input/environment descriptions and
bounded strict `expected_json`. The program must print one JSON value computed
from its actual observation. The host binds task, purpose, predicate and authored
program hash before execution; new purpose/predicate/program means a distinct case.
Repeating an identical declaration retains the original baseline identity.

For declared reproductions only, an in-process observer records up to four calls
to the named Python entrypoint, bounded primitive arguments, cwd and sys.path.
Unsupported/truncated arguments or absent calls prevent comparison. Receiver
object state, arbitrary external effects and all environment variables are not
certified. This is diagnostic feedback, not an attestation. The observer and
authored program together must fit the unchanged 8,000-character source limit;
the existing sandbox/output/deadline limits still apply.

Replay using the original `action_id`, with question/source/reproduction null.
The existing replay path keeps the exact program and binding across edits and
restart. Receipts distinguish authored `source_hash` from the actual
`execution_source_hash`. A completed same-action retry returns its receipt rather
than executing again. No automatic probe or extra finish gate is added.

## Separate observations from task acceptance

`reproduction_review` is rebuilt from durable public results, projected into the
current state across handoffs, and included with `finish_task`. It retains the
first three declared case identities, their baseline/latest result and an omission
count. Helpers, visible check PASS and free-form assessment cannot resolve these
comparisons. Only a current-diff replay with the same observed arguments/setup can
show `mismatch_to_match`; later edits make it historical. Fresh scratch cwd paths
are normalized while preserving their relative relationships.

Even `mismatch_to_match` means only that declared experiment changed as expected.
The issue-to-entrypoint mapping and expected value are model-authored, and a
baseline JSON mismatch need not reproduce the reported bug. `repair_success`
remains `not_assessed`; private acceptance stays outside agent context. Declaration
fields are excluded from evidence ranking and labelled as annotations in returned
originals. The current review is mutable state, not an archived observation.

Focused checks: `tests/test_evidence_recovery.py`. Source replay and validation:
[implementation record](../docs/history/2026-10-20-evidence-recovery.md).
