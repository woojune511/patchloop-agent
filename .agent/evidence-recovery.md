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
or an object with `kind="original_requirement"`, fully qualified Python `entrypoint`,
`input_conditions`, `environment_conditions`,
`reported_failure_json` and `expected_json`. Both values are bounded strict JSON:
the former describes the reported buggy result, the latter the desired result after
repair. Their canonical values must differ. The same action binds both values and
the mapping; neither value certifies semantic requirement coverage. Missing or
invalid mapping fields fail before execution; no separate registration is needed.
Null is only for replay. The choice remains model-authored, not certified coverage.

Fresh original purposes omit `requirement_quote`. The host binds the full current
public task hash and an `issue` reference with the exact issue-content hash; the
already supplied public task owns the source text. No selected quotation or fuzzy
text match gates execution. Admitted legacy quotation-bearing definitions retain
their exact identity and program on recovery/replay.

Fresh request admission stores `probe_request.validation` and returns the same
`request_validation` receipt with the primary result. `invalid_fields` identifies
the failing paths and constraints. The latest rejected fresh request in the same
task is compared using actual argument values, excluding action IDs and decisions.
`unchanged` means identical arguments; `invalid` means changed arguments still fail
preflight; `corrected` requires a changed error field and full preflight success.
Switching from original purpose to helper is `different_purpose`, not correction.
An accepted request closes that chain even if execution later fails. Replay and
uncertain recovery are excluded. The admission receipt survives crashes unchanged;
completed action recovery still uses `action_id + input_hash` without redispatch.
Correction is request validity only, never execution or requirement verification.
Existing request/attempt limits, acquisition release and completion policy remain.

Authored `python_source` retains its 8,000-character allowance for both purposes.
Host reproduction instrumentation (including fixed headers) has a separate
8,000-character / 32,000-byte bound. Exceeding that bound reports a host observer
error, not a request to shorten `/python_source`. Serialized execution allows
88,002 characters / 112,002 UTF-8 bytes: `repr(source)` can expand each character
to ten ASCII characters plus two quotes, followed by the bounded observer.
The gateway checks authored input; the sandbox and standalone reader bound the
composed program. The v3 probe profile records all limits. Observer/program bytes
and saved binding hashes remain unchanged; existing manifests cannot silently
switch runtime/profile identities. Local size admission is not target execution
or original-requirement acquisition; see the [size repair](../docs/history/2026-10-24-size.md).

For original-requirement probes, create the injected
`target = observed_target(input_paths=[...], environment_keys=[...])`, then call
it with ordinary Python arguments, for example `call = target(["src/project"],
do_exit=False)`. There is no extra adapter argument container. It resolves the
public path, including aliases and constructors, and binds an inspectable
signature before invoking the callable. Binding checks Python argument placement;
it cannot certify argument types or correspondence to the issue.

Fresh v4 calls record raw arguments, bound parameter names, actual sys.argv, cwd,
sys.path, Python/platform, selected environment value hashes and fixture-content
hashes before execution. Select fixture roots, not implementation files. Empty
selections do not certify external inputs or environment coverage. Set sys.argv
before a CLI callable that reads it; changed argv prevents comparison. Raw inputs
define comparison identity; bound parameter names and result fields do not.

V4 initializes target-visible `sys.argv` to `["<patchloop-reproduction>"]` before
authored code, preventing host timeout/line-tracing parameters from leaking into
the callable. Explicit authored argv still takes effect and remains compared.
`reproduction_workspace()` exclusively creates `patchloop-case` under the fresh
sandbox's initial cwd (`/tmp/patchloop-case` in Docker). Repeated helper calls in
one execution return that newly created path; an occupied path raises without
deleting or reusing it. Put fixture roots there and explicitly set HOME/cache
environment variables when needed. The helper does not rewrite environment
values: arbitrary random HOME/PYLINTHOME still produces a real identity mismatch.

Each call returns `.value`, `.stdout`, `.stderr`, `.outcome`, `.capture_status`,
`.exception`, `.exit_code` and `.call_id`. Capture isolates that call's Python
streams from probe progress and other calls. Direct file-descriptor writes,
subprocess output and streams retained before the call remain unobserved. The
shared capture budget is 4,096 UTF-8 bytes across all calls and both streams.
Truncation, stream replacement and deferred execution remain incomplete.
SystemExit is an observed outcome; a nonzero code can be the reported bug.
`outcome="returned"` describes execution, not task success. `exit_code=null`
means no SystemExit code was observed, not zero. Choose the diagnostic channel
from public behavior and inspect both captured streams; do not assume stderr.
Unexpected exceptions prevent comparison. An intended exception observation may
declare exact classes, e.g. `expected_exceptions=(ValueError,)` when creating the
adapter; declaring a base class does not allow arbitrary subclass failures.

Then call the injected `record_observation(value)` exactly once with the actual
JSON-compatible result, at most 2,048 UTF-8 bytes, after all selected target calls.
Print progress normally. Whole-probe logs are not automatically parsed; explicitly
derive the value from the target's return, captured diagnostics or intended
exception. Keep raw logs, exception metadata and execution outcome in the separate
call receipt unless they are part of the required behavior. Use one extractor for
the failing input and a normal-input control before and after repair. Prefer a
small stable value, for example failure `{"bug_has_error":true,"control_has_error":false}`
and desired `{"bug_has_error":false,"control_has_error":false}`, recording those
same keys from the actual calls. `comparison` describes the desired result;
`declared_failure_comparison` describes the authored failure value.

Select observable properties that distinguish the public failure from the desired
behavior, including any control. A clean exit or absence of every diagnostic is
part of the oracle only when the public requirement calls for it. Preserve other
diagnostics in logs. Derive values from completed, interpretable target results;
missing output and unexpected invocation/setup/parse failures must leave the
observation incomplete, never become a false/no-error value. The v54 tool guidance
describes this choice. Healthy v3/v4 receipts include `comparison_feedback` for
`desired` and, when declared, `declared_failure`. Each lists missing/extra/type/value
differences at JSON Pointer paths (empty path means the root), at most eight rows,
160 characters per path and 2,048 UTF-8 bytes per declaration. Truncated paths and
omitted rows are explicit. Values remain in `binding.definition` and `observed_json`.
Feedback is absent when comparison is unavailable. Legacy v1/v2 receipts and all
observer bytes remain unchanged; durable old results are not recomputed.

The host still uses exact frozen JSON equality, including scalar types, and does
not certify the selected channel, control or semantic mapping. There is no new
same-shape admission gate: some legitimate failures change shape after repair.
Correcting a predicate creates a new case; prior mismatches retain their verdict.
A desired match from an empty wrong channel cannot acquire a differing declared
original failure. Field feedback does not infer the right channel or repair it.

Missing, duplicate, invalid or oversized observations cannot compare. A recorded
value remains visible if the process subsequently fails, but failed execution,
setup mismatch, timeout, truncation, uncertain cleanup or an unobserved declared
call cannot gain matched/mismatched credit. An observed bug can be recorded by a
healthy process as a mismatching value; process success is not task success.

The host binds the task, purpose, predicate, observation channel and authored
program hash before execution. New purpose/predicate/program means a distinct case.
Repeating an identical selection retains the original baseline identity.
New selections bind `invoke-declared-call-v4`. Existing invocation v1/v2/v3,
`record-observation-v1` and legacy stdout bindings retain their exact wrappers
and APIs on replay; they do not
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
recorded before later calls prevent comparison. The v3 report is bounded to 10,000
UTF-8 bytes; v1/v2 retain their 6,000-character bound. Arbitrary object state,
external effects and unselected inputs/environment remain unverified; in-process
feedback is not an attestation. Authored source and host observer retain separate
8,000-character allowances. Only fixed host indentation is compacted; authored
and legacy bytes stay intact. Sandbox/output/deadline limits remain unchanged.
See the [local four-condition result](../docs/history/2026-10-24-capture.md).
Completion-time replays below use the same public execution path.

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

`reproduction_review.completion` separately retains every admitted first case binding
from the full journal. Known preflight rejections stay in request/recovery accounting
but cannot create completion cases. Accepted uncertain and legacy unknown requests
remain unverified. A healthy invocation-bound root is mechanically replayable;
this is not certification that it reproduces the reported bug. After an accepted
edit, acquired original failures replay before the next model input. Selection
uses all baseline-failure IDs, never the latest helper/saved program or the three
displayed cases. Early replay is reserved completion work: no extra model call,
and new work is deferred if the minimum check/return budget cannot fit. Already
started children reconcile even if new admission closes. At finish, remaining stale
cases (including matched baseline controls) run through ordinary budgeted probe
actions. A helper/new case cannot close an older one. Same-case current mismatch
or conflict rejects finish; absent cases and incomplete/unavailable observations
remain explicitly unverified. The gateway also checks this state, so a direct or
recovered finish cannot bypass it. Deterministic child IDs bind run/case/root/diff;
a finished or durably skipped attempt is not retried on that diff. Another edit
invalidates its currency. Child start/finish receipts restore action accounting.
The public view shows three cases plus counts; execution uses the complete set.
Each displayed case retains bounded current `observed_json` and execution status
separately from comparability (`same`, `changed`, `unavailable`). Changed conditions
list bounded JSON Pointer differences without exposing raw environment values.
A bug-like observed value with changed conditions remains UNKNOWN; same-condition
mismatch remains REFUTED. Native tool outputs contain only model-requested results;
host child feedback comes from the journal projection. Protected tool forecasts
include acquired-original replay costs on each accepted future repair, while
monetary minimum admission still does not guarantee semantic failure recovery.
`submission_verification` accompanies the free-text assessment without replacing
the separate private evaluation or certifying semantic requirement coverage.

`completion.original_obligation` binds the full public task independently of case
selection and plan replacement. Opt-in `--reproduction-acquisition bounded-v1`
records its immutable root before investigation, with at most two original attempts
or six read/search/probe actions. Rejected edits and replayed action IDs do not
consume that allowance. A fresh paired case acquires a failure only when a healthy
unchanged-base execution matches the declared failure and mismatches the desired
result. A third value or an already-correct result remains `not_reproduced`.
Legacy bindings retain their original acquisition rules. Missing/invalid observations
are `setup_blocked`, without attributing the failure to infrastructure. No attempt
is `not_attempted`. The stage releases at its bound or when probes/protected budget
are unavailable; this does not discharge the obligation. Direct mutation/finish
cannot bypass a pending stage, and pending actions recover before the next turn.

Finish returns `cases_verified_delivery` only with that baseline failure and all
selected current cases supported. Missing/incomplete evidence returns the patch as
`unverified_delivery`, with `original_verification` and `submission_verification`.
The durable finish determines this outcome on recovery; independent evaluator PASS
cannot upgrade it. The acquisition flag defaults to `none` for bounded comparisons.
Its 2/6 limits are provisional resource bounds, not measured optimal settings.

Even `mismatch_to_match` means only that declared experiment changed as expected.
The issue-to-entrypoint mapping and both comparison values are model-authored; even
a declared failure match does not certify the reported bug. `repair_success`
remains `not_assessed`; private acceptance stays outside agent context. Declaration
fields are excluded from evidence ranking and labelled as annotations in returned
originals. The current review is mutable state, not an archived observation.

Focused checks: `tests/test_reproduction_oracles.py`,
`tests/test_probe_invocation.py`, `tests/test_probe_purpose.py`,
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
