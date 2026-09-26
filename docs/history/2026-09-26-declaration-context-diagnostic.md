# Bounded declaration documentation in search results

Date: 2026-09-26. Optional implementation and offline validation, `official=false`.
Current priorities remain in [current status](../current-status.md).

## Problem, hypothesis and change

The first-interpretation audit found that successful PF asked whether existing profile
configuration was sufficient and read its documentation before editing. Failed PG only
received short declaration hits and implemented an overbroad condition. The source
question already differed before that read, and older failures sometimes received the
same documentation. Additional context is an unproven information intervention.

`diagnostics.declaration_context` adds a task-neutral, opt-in first-tool-batch gateway
for fresh `run_dev` diagnostics. A literal query matching an assigned Python data name
can extend its already-returned hit through the immediately following literal string.
Only module/class assignments are supported. No source imports, task-specific paths,
expected answer, successful patch, new plan instruction or schema is introduced.

The complete expanded span is bounded to 40 lines and stays within the original 20-hit/
24,000-character search limits. Original hits/lines remain available. Expansion happens
before normal evidence/fingerprint/cache/journal processing, so actual delivered lines
can authorize exact edits. Source mismatch fails normally; invalid/unsupported Python
keeps the original result. Later batches gain no new expansion. Omission uses the ordinary
runner. Policy/implementation identity is journaled; the wrapper forbids repeat/resume
and scopes its hook to one sequential process. Core runtime remains `4d2fc8ba`/v45.

## Offline results and limitations

The saved-source rehearsal executes only PG's four recorded public search actions in
each arm, against the verified prepared source. A matches the historical code ranges,
hashes and search metadata. B changes only the declaration query: it exposes profile
format documentation at lines 78–89, adding 12 unique lines and 1,012 returned content characters.
The other three results and all existing source lines are preserved. No model, candidate,
probe, Docker or evaluator execution occurs in this rehearsal.

Coverage accounting initially used `splitlines()` and incorrectly counted an already
observed terminal empty line 77 as new. `line-coverage.json` corrects the new-line count
to 12 using each span's inclusive line range; the initial output is retained. This also
corrects the prior first-interpretation record's 13 observed profile lines to 14. The
source bytes, actual input audit and semantic findings are unchanged.

Focused tests cover bounds, source identity, skipped contexts, public/private paths,
first-batch scope, replay/cache, mutation evidence and hook cleanup. A/B mocks under
append-v1 and segmented-v1 check equal prompts/schemas/normalized initial state, public
task/diff/check delivery and real source expansion, then reach isolated EVALUATOR_PASS.
These synthetic outcomes establish plumbing, not autonomous applicability judgment.
Validation totals and durations are recorded in the external validation packet.

The rehearsal is not a native-request fork or a hydrated historical checkpoint. The
fresh diagnostic seam alone does not implement the proposed fixed post-search comparison.
That collector still needs explicit binding of the old plan/opaque continuation and new
evidence/derived state. No live group, price allocation, quality result or default adoption
was made. The exact question/first-edit effect remains unmeasured.

## Evidence

- Contract: [declaration context](../../.agent/declaration-context.md).
- Source rehearsal: `C:\pt\analyses\declaration-context-preview-20260926-v1\result.md`.
- Local tests: `C:\pt\validation\declaration-context-20260926-v1\result.md`.
- Earlier causal limits: [first interpretation audit](2026-09-26-first-interpretation-audit.md).

Focused, related regression, documentation and Ruff results are recorded separately.
No full core regression is claimed for this optional diagnostic-only change. Historical
records and prepared source bytes remain unchanged; prior paid allocations remain closed.
