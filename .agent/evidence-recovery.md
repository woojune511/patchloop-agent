# Source recovery and fixed reproduction scope

Implemented in dev-head; the [Astroid comparison](../docs/history/2026-10-20-recovery-schema-results.md)
exercised source recovery but established no repair-success improvement.
History search remains opt-in (`public-v1`), probes remain
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

## Bind a selected original-requirement probe in the same action

Every fresh `run_probe` selects `purpose`: `{"kind":"helper"}` for exploration,
or an object with `kind="original_requirement"`, a literal `requirement_quote`,
fully qualified Python `entrypoint`, `input_conditions`, `environment_conditions`
and bounded strict `expected_json`. Choosing original-requirement verification
therefore supplies its mapping and expectation in that same action. Missing or
invalid mapping fields fail before execution; no separate registration is needed.
Null is only for replay. The choice remains model-authored, not certified coverage.

For original-requirement probes, invoke the declared callable through injected
`call_target(args=[...], kwargs={...}, input_paths=[...], environment_keys=[...])`.
It resolves the public import path, including aliases and constructors, and calls
that target with the supplied arguments. It records arguments, cwd, sys.path,
Python/platform, selected environment value hashes and selected fixture-content
hashes immediately before the call. Select fixture roots, not implementation
files: a changed candidate must be allowed to produce a different result.
Empty selections do not certify that external inputs or environment are irrelevant.

Then call the injected `record_observation(value)` exactly once with the actual
JSON-compatible result, at most 2,048 UTF-8 bytes, after all selected target calls.
Print progress normally. Stdout/stderr are logs, not the predicate's input; the
recorded value travels with the bounded call-observation report. For example,
record `{"has_error": actual_has_error}` and let the host compare it to the frozen
expectation instead of asserting expected behavior before reporting anything.

Missing, duplicate, invalid or oversized observations cannot compare. A recorded
value remains visible if the process subsequently fails, but failed execution,
setup mismatch, timeout, truncation, uncertain cleanup or an unobserved declared
call cannot gain matched/mismatched credit. An observed bug can be recorded by a
healthy process as a mismatching value; process success is not task success.

The host binds the task, purpose, predicate, observation channel and authored
program hash before execution. New purpose/predicate/program means a distinct case.
Repeating an identical selection retains the original baseline identity.
New selections bind `invoke-declared-call-v1`. Existing `record-observation-v1`
and legacy stdout bindings retain their exact wrappers on replay; they do not
silently acquire the new linkage. Unadvertised legacy `reproduction` arguments
preserve prior action/recovery identities. Logs are never automatically converted
into declared cases, and old results are not regraded.

The provider-facing schema omits only the entrypoint regex. Strict mode, required
fields, nullability and length bounds remain; `Intent` still enforces the original
regex before any probe runs. The [single-call diagnostic](../docs/history/2026-10-20-b-pattern-results.md)
returned a healthy response with this projection. It did not establish repair
success or the provider's internal cause. The subsequent twelve-run comparison
completed with settled billing, but accepted repairs remained A/B 0/6.

The invocation adapter records at most four calls, four input roots and 16 selected
environment names per call. A snapshot covers at most 64 entries/1 MiB in total;
missing paths and directory contents are included. Symlinks, oversized/unsupported
arguments, deferred async/generator execution, absent calls or an observation
recorded before later calls prevent comparison. The report retains its 6,000-char
bound. Arbitrary object state, external effects and unselected inputs/environment
remain unverified; in-process feedback is not an attestation. The adapter and
authored program together must fit the unchanged 8,000-character source limit;
the larger adapter leaves less authoring space. Sandbox/output/deadline limits
remain unchanged. Completion-time replays below use the same public execution path.

Replay using the original `action_id`, with question/source/purpose null.
The existing replay path keeps the exact program and binding across edits and
restart. Receipts distinguish authored `source_hash` from the actual
`execution_source_hash`. A completed same-action retry returns its receipt rather
than executing again. Completion-time replay also reuses this identity contract.

## Separate observations from task acceptance

`reproduction_review` is rebuilt from durable public results, projected into the
current state across handoffs even without probes, and included with `finish_task`.
`required` points to the unchanged public issue and task hash. Its status remains
`UNKNOWN`: this runtime does not certify the issue-to-test mapping. Cases retain
their fixed program/predicate identity and baseline/latest result. Their separate
`evidence.status` is computed over current-diff results with the baseline's observed
arguments/setup: matched gives `SUPPORTED`, mismatched gives `REFUTED`, both give
`CONFLICT`, and no comparable result gives `UNKNOWN`. A later success on the same
snapshot cannot erase a failure; unrelated checks or changed inputs cannot close it.
Edits make earlier observations historical. New-channel pairs also require the
same selected fixture contents/environment and host execution profile/dependencies.
Fresh scratch and selected input roots are normalized while preserving relative
relationships; argument types stay distinct. Return/exception changes are outcomes,
not input drift. A matched value with changed conditions stays unpaired/UNKNOWN.

The bounded view shows three cases, prioritizing conflict/refutation, plus counts
for all case states and omitted cases. At most two witness action IDs per case
identify the success/failure results. Each case keeps a replay action ID and
baseline/latest execution linkage. New receipts expose a bounded concrete-condition
preview, condition hash and environment hash; omitted preview characters are counted.
Legacy receipts expose only their weaker name-trace status/count.
`other_executions` shows the latest three
unbound diagnostics/checks with actual execution flags, scope and an omission count;
zero exit and suite PASS do not acquire original-requirement coverage. Existing
recent probe bodies and the unsuccessful-observation catalog remain separate.

Concern `model_position` and `model_open_concern_ids` in the model view describe
discussion only. Resolve/dismiss and plan edits never write computed evidence
state. Durable concern operations and receipts retain their original schema for
recovery. These model-authored concerns do not gate completion.

`reproduction_review.completion` separately retains every first case binding from
the full journal. A healthy invocation-bound root is mechanically replayable;
this is not certification that it reproduces the reported bug. At finish, stale
cases (including matched baseline controls) run through ordinary budgeted probe
actions. A helper/new case cannot close an older one. Same-case current mismatch
or conflict rejects finish; absent cases and incomplete/unavailable observations
remain explicitly unverified. The gateway also checks this state, so a direct or
recovered finish cannot bypass it. Deterministic child IDs bind run/case/root/diff;
a finished or durably skipped attempt is not retried on that diff. Another edit
invalidates its currency. Child start/finish receipts restore action accounting.
The public view shows three cases plus counts; execution uses the complete set.
`submission_verification` accompanies the free-text assessment without replacing
the separate private evaluation or certifying semantic requirement coverage.

Even `mismatch_to_match` means only that declared experiment changed as expected.
The issue-to-entrypoint mapping and expected value are model-authored, and a
baseline JSON mismatch need not reproduce the reported bug. `repair_success`
remains `not_assessed`; private acceptance stays outside agent context. Declaration
fields are excluded from evidence ranking and labelled as annotations in returned
originals. The current review is mutable state, not an archived observation.

Focused checks: `tests/test_probe_invocation.py`, `tests/test_probe_purpose.py`,
`tests/test_evidence_recovery.py`, `tests/test_verification_scope_state.py`.
[Executable caller binding](../docs/history/2026-10-22-probe-call.md).
[Purpose and observation channel](../docs/history/2026-10-21-probe-purpose.md).
[State separation and saved-log replay](../docs/history/2026-10-20-verification-state-separation.md).
Diagnostic probe overrides must forward the host-bound `reproduction_binding`,
including null, to ordinary execution. Inline-only projections remove both replay
descriptions together with the replay input, retaining reproduction validation.
Quick checks cover these adapter paths, OFF disclosure and the original 8,000-character
prompt / 4,000-byte memory-schema ceilings; see the
[regression repair](../docs/history/2026-10-20-regression-contract-repair.md).
The [verification-state comparison](plans/verification-state-comparison.md) supplies
a diagnostic-only OFF control and an independent public-judgment validator.
Its frozen packet binds local validation; no paid allocation is authorized.
Source replay and validation:
[implementation record](../docs/history/2026-10-20-evidence-recovery.md).
