# Host-built original-call diagnosis requests

Date: 2026-10-26. Follow-up to the [closed pilot](2026-10-25-helper-correction-live.md).

## Material Passport

- Origin: academic-research-suite / experiment-agent, authorized implementation and
  bounded local code validation.
- Version: `diagnosis-request-local-v1`; `official=false`, `claim_eligible=false`.
- Verification: local mechanism tests and saved-request static comparison. No new
  provider call, Docker launch, target-task execution or actual-model pilot.
- Baseline commit: `14206d70caa4faace6546d3ec6539a68ac0399b0`.
- Changed runtime: `sha256:34f859e75556d99fc59b61f599d8a530abdf2236a114f864fc6029b51d0c6e01`.

## Problem, hypothesis and scope

The last pilot spent 28 source inspections before one ineffective mutation. The
original F0010 persisted with its changed branch unobserved. Two requested call-path
diagnostics never executed: call 31 used the failure replay's action ID instead of
the original root, and call 33 supplied lines outside selected functions. A nested
state also reported preparation available after its read/search tools disappeared.
This prevented the diagnostic mechanism from being tested at all.

The host already knew the original root, failing invocation and current source.
The intervention removes the model's redundant coordinate construction, while
retaining its choice of caller focus, watched public functions and scalar fields.
It does not prescribe the repair, increase budgets or add a new diagnostic attempt.
Wrong function selection, an absent focus or unhelpful observations remain plausible
failure causes. Admission success would not establish that they are solved.

## Implemented behavior

- Fresh `run_probe.call_path` accepts `focus` and `watches`; replay/source fields are
  null. `diagnosis_request.py` binds the pending original root and failing `call_id`.
  Public tracked/prepared membership remains enforced by the existing preflight.
- AST identifies a unique function; compile-only line tables select its own frame's
  lines, with unobserved changed lines first and a 32-line cap. Nested frame bodies
  and artificial locations are excluded. Selection reports omitted lines. Source
  is never imported or executed during construction.
- Durable admission stores candidate, canonical request, source hashes and selection
  policy. Raw action input hashes stay unchanged. Recovery uses that exact request,
  rejects source drift, reuses complete receipts and stops on uncertain execution.
  Interrupted rejected requests cannot turn into dispatches. Legacy admissions are
  still recoverable; their explicit coordinate shape is not freshly advertised.
- Both model-facing path projections distinguish an unused preparation allowance
  from an actually offered read/search. Minimum completion keeps the diagnostic,
  repair, fresh original replay, required checks and finish. Optional preparation is
  protected separately; an already reserved anchor/current-repair read is not doubled.
- The current replay-OFF comparison also removes and rejects symbolic call-path
  requests, since those now initiate replay without a raw replay ID. Its saved
  historical evidence is unchanged; the current B condition is unchanged.

The existing one-execution/two-rejected-request bounds, output/context/cost caps,
original program/arguments/oracles, and completion judgment are preserved. See the
[current contract](../../.agent/repair-path.md).

## Local evidence

Saved public source from `run_dev_ad2f36ee45664396` was read without executing it.
The same two requests still reject under their original coordinates. Removing only
the model-supplied replay/call/line coordinates lets the host construct both:

| Saved request | Baseline problem | Host construction |
| --- | --- | --- |
| Call 31 | Wrong root; also an out-of-function watch | Static admission PASS; watch sizes 15/27/28/32 |
| Call 33 | Out-of-function lines | Static admission PASS; watch sizes 9/12/27/28 |

Function/field choices and original-case binding remain the same. The first request's
long watch explicitly omits five eligible lines. Neither request was dispatched.

Core tests cover actual tiny local tracing, source hashes, raw-input immutability,
recovery before dispatch/after durable result, uncertain dispatch, durable rejection,
unknown observations, current-diff repair linkage, budget edges and projection
consistency. A scripted local sequence reaches diagnosis, causal revision, automatic
original recheck, checks, finish and isolated mock acceptance. It uses four probe
executions; finish reuses the completed original check. Mock safety remains NOT_RUN.

Review found a real Python 3.14 selector issue: artificial exception-table locations
from `dis.findlinestarts` can be `None`. The selector now excludes them; a try/except
and nested-function control covers the case. Initial test failures also exposed
invalid fixture assumptions, which were corrected and retained in external logs.
Native reviewers shared project context; this is not blinded effectiveness evidence.

- Focused: 79 PASS, 41.05 seconds pytest / 42.671 seconds command wall time.
- Ruff: PASS for runtime, tests and the changed diagnostic comparison module.
- Quick integration: 349 PASS, 77.72 seconds pytest / 79.522 seconds command wall
  time, including isolated mock evaluation and documentation checks.
- Full regression, Linux CI, actual target Python line-event correspondence and live
  model effectiveness: NOT_RUN.

Evidence root: `C:/pt/diagnosis-request-local-v1`. `plan.json`,
`saved-request-control.json`, validation logs/receipts and the final commit closeout
are linked through append-only, hash-chained `dev-run-v1` JSONL. Runtime hashes are
checked before and after validation. Old evidence and unrelated user changes remain.

## Decision and remaining question

Local evidence supports host-owned construction as a fix for the two observed
request failures and supports consistent preparation reporting. It does not show
that the chosen focus will run, that fields will contain useful values, or that a
model will use them to solve F0010. Host/compiler line tables can differ from the
target Python version; bounded line no-hit is not whole-function or branch proof.

The next empirical question is diagnostic uptake followed by successful original
repair on a fresh, exactly authorized pilot. No unused historical allocation is
carried forward and no live experiment was run as part of this implementation.
