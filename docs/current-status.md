# Current status

Updated: 2026-09-29. This is a replaceable snapshot of current decisions, not an
append-only log. Source code owns runtime behavior; this page owns current priorities.
Read [history](history/README.md) only for a specific evidence question.

## Direction

Build an agent that understands public tasks, makes correct repairs, checks changed
and preserved behavior, and submits reliably within bounded cost and time. Start
with observed failures, diagnose causes, and select the smallest useful improvement.
Research questions can arise during diagnosis; reusable method claims follow evidence.
There is no commitment to demonstrate a memory effect or another preselected method.

Comparisons answer causal questions. Plumbing, note/probe use or submission alone
does not establish better task solving. Remove ineffective mechanisms when useful.

## Active runtime and working baseline

- `dev-head` is the sole active mutable runtime; every run is `official=false`.
- The chosen performance baseline is `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens.
  These selected settings are not a statement of CLI defaults.
- Baseline options: segmented-v1, result-or-size-v1 boundaries, brief-v1, probes
  enabled / probe-policy none, repair-recheck, protected-v1 inspection, and
  per-call-v1 completion-cost admission.
- Limits: 40 model calls, 100 tool actions, 4 accepted mutations, 1,800 seconds;
  paid work also needs an exact separately authorized invocation-wide cost cap.
- Cross-run memory, held-out tuning, and claim execution are disabled. Bounded
  run-local notes and public state remain available.
- Historical Rapid executables are absent. Existing history and evidence are immutable.

Keep the chosen baseline fixed while diagnosing a failure. Any proposed change
should identify the mechanism it tests; task-specific repair hints are excluded.
See [operations](operations.md) for commands and actual CLI defaults, and the
[implementation guide](../.agent/guide.md) for the relevant source and contracts.

## Current problem and next decision

The [basic/current comparison](history/2026-09-28-basic-current-baseline-comparison.md)
passed 4/6 versus 5/6 tasks, with only pyfakefs differing. Planning, probes and repair
recheck changed together; no feature has isolated credit. Keep Current as a working
baseline, not a proven default improvement. Detailed cost/time and safety evidence
remain in the closed result.

The [boundary-pair procedure panel](history/2026-09-29-boundary-pair-panel-results.md)
completed 24 fresh runs across Pydantic, HF Hub, Fromager, Loguru, PDM and pgmpy.
Current A passed 7/12; procedure B passed 8/12, with paired B wins / A wins / ties
1 / 0 / 11. Only PDM repetition one differed. All submitted, all safety PASS;
NOT_RUN and infrastructure failures were zero. Both known failure tasks failed all
four runs each. Actual cost $12.1553535; unused $35.8446465 is closed.
B cost 26.6% more and took 24.7% more active time. Do not adopt the instruction.

All 197 model inputs were verified; neither arm used run_probe. All final patches
passed public checks, including nine acceptance failures. More explicit pair prose
and selected-case PASS did not establish correct scope.

The [public discrimination replay](history/2026-09-29-boundary-discrimination-replay.md)
ran 15 local containers on base plus all Pydantic/HF/PDM final patches, without model
calls or private evaluation. Holding mode/name constant exposed overbroad behavior in
all four Pydantic patches; testing an endpoint-free client under an ambient endpoint
exposed three HF patches. HB2 preserves that boundary but its residual failure is open.
PDM's early active-interpreter construction did not cause failure with missing paths:
all four patches passed eight selection/fallback cases. That candidate cause remains
unconfirmed; do not force the explanation with an artificial exception.

Separate evidence selection, execution readiness and repair. Existing checks omit
the P/H distinctions; no default prompt or gate change is justified. These already
used tasks cannot establish generalization, and operator examples must not become
undisclosed agent hints.
The [selection diagnostic](history/2026-09-29-discriminating-case-selection-results.md)
completed 24 response-only samples from six fixed A1 candidates before their first
public check. Arm-masked review counted discriminating selections A 0/12, B 5/12:
B selected H's explicit-versus-ambient endpoint boundary twice and three F/G
control examples. P still misinterpreted provider-profile scope in both B responses.
B proposed eight probes; A only registered checks. This is selection evidence,
not five discovered bugs or better task acceptance. All dispatched inputs and source
bindings verified. Cost USD 2.455532; unused USD 10.544468 is closed.
The [registered probe replay](history/2026-09-29-selected-probe-execution-results.md)
executed all eight frozen programs unchanged, with no model calls. H reproduced
the public counterexample twice; F's two controls held; L exposed a diagnostic
scope question. P passed its unsupported expectation. G failed before behavior
on missing pandas/numpy despite delivered environment constraints. Separate
expectation validity, execution readiness and repair ability. No retries, source
changes or cleanup failures occurred. Keep the baseline unchanged; agent repair,
task acceptance and safety evaluation remain NOT_RUN. No further model run is
authorized by the closed allocation.
The [observation-to-repair comparison](history/2026-09-29-observation-repair-panel-design.md)
is prepared: H's fixed candidate and probe in both arms, actual observation withheld
versus supplied, A/B twice. Fresh seeded episodes permit normal repair/check/submit
and isolated evaluation. The proposed new USD 8 cap is not yet authorized; live repair
is NOT_RUN. Preparation passed source bindings, local Docker preflight and mock tests.
The [pre-edit comparison](history/2026-09-28-pre-edit-issue-focus-results.md) and
[plan audit](history/2026-09-28-plan-condition-audit.md) remain supporting evidence:
requirement-to-condition mapping failed despite faithful plan storage/delivery.
The [late check-definition diagnostic](history/2026-09-28-public-check-focus-results.md)
also did not justify adoption. All these allocations are closed.

Key closed evidence:

- [Basic/current comparison](history/2026-09-28-basic-current-baseline-comparison.md):
  12 fresh runs, 4/6 versus 5/6, 1 / 0 / 5 paired result, all safety PASS.
- [Original pilot](history/2026-09-28-original-pilot-results.md): MontePy/darts passed;
  toqito exhausted its cap before submission. Preparation passed for all three.
- [AnyIO fresh solves](history/2026-09-27-anyio-fresh-solve.md): one PASS, one resource
  NOT_RUN with corrected probe dependencies; calibration, not original benchmark score.
- [Toqito funded continuation](history/2026-09-28-probe-followup-results.md): supplied
  patch repair passed benchmark/safety; operator matrix 14/15, underflow remains.
  This is not an additional fresh solve.
- [Reconciliation result](history/2026-09-28-expectation-reconciliation-results.md):
  supported expectations A 0/2, B 1/2; no reliable effect. $0.871760, funds closed.
- [Earlier timeout](history/2026-09-28-expectation-review-results.md): billing of one
  interrupted call remains unknown, separately from later settled allocations.

All earlier allocations are closed. Seeded repairs, operator replays and response-only
samples remain separate from fresh solves. The working baseline is unchanged.

## Implemented and measured

The checkpoint collector has live provider acceptance, exact delivery and separate
cost-accounting evidence for the closed interventions. Accepted continuations are
not fresh solves. The earlier N1/N2 fresh solves used unmodified run_dev with corrected
dependencies. Reliable recovery, general improvement and default adoption remain
unestablished; earlier supplied-candidate repairs remain separate evidence.

The opt-in first-plan timing, declaration expansion and independent-candidate diagnostics
remain implemented, with no default adoption established by their closed comparisons.
The planning OFF comparison removes the explicit planning feature as a whole; bounded
working notes, internal reasoning and registered tools remain available.

Evidence for targeted lookup:

- Information comparison results: [outcomes and public audit](history/2026-09-27-caller-information-results.md);
  packet: `C:\pt\analyses\caller-information-results-20260927-v1`; live: `C:\pt\callerinfo0927a`.
- Information comparison preparation: [scope and validation](history/2026-09-27-caller-information.md);
  [contract](../.agent/caller-information.md);
  packet: `C:\pt\analyses\caller-information-comparison-20260927-v1`.
- Caller-state measurement: [observation and control](history/2026-09-27-anyio-caller-state.md);
  packet: `C:\pt\analyses\anyio-caller-state-20260927-v1`.
- Closed comparison: [checkpoint results](history/2026-09-27-checkpoint-live-results.md);
  packet: `C:\pt\analyses\checkpoint-live-results-20260927-v1`; live: `C:\pt\mutationlive0927a`.
- Live collector: [preparation and environment block](history/2026-09-27-checkpoint-live-preparation.md);
  [contract](../.agent/checkpoint-comparison.md);
  packet: `C:\pt\analyses\checkpoint-live-comparison-20260927-v1`.
- Offline continuation: [restoration and execution](history/2026-09-27-checkpoint-continuation.md);
  [contract](../.agent/checkpoint-continuation.md);
  packet: `C:\pt\analyses\checkpoint-continuation-20260927-v1`.
- Earlier baseline: [basic/current comparison](history/2026-09-28-basic-current-baseline-comparison.md);
  live state: `C:\pt\baseline-compare-20260928-v1`.
- Patch diagnostic: [AnyIO B1 branch deletion](history/2026-09-27-anyio-b1-branch-deletion.md);
  packet: `C:\pt\analyses\anyio-b1-branch-deletion-20260927-v1`.
- Audit: [AnyIO evidence/action links](history/2026-09-27-anyio-evidence-action-link.md);
  packet: `C:\pt\analyses\anyio-evidence-action-link-20260927-v2`.
- Replay: [AnyIO final probe scope](history/2026-09-27-anyio-final-probe-scope.md);
  packet: `C:\pt\analyses\anyio-final-probe-scope-20260927-v2`.
- Process analysis: [AnyIO process audit](history/2026-09-27-anyio-observation-process-audit.md);
  packet: `C:\pt\analyses\anyio-observation-process-audit-20260927-v1`.
- Closed result: [AnyIO observation repair comparison](history/2026-09-27-anyio-observation-repair-comparison.md).
- Results, public decision review and closure:
  `C:\pt\analyses\anyio-observation-repair-results-20260927-v1`; live state: `C:\pt\obsrepair0927a`.
- Preparation correction: [AnyIO probe readiness](history/2026-09-27-anyio-probe-readiness.md).
- New bundle and public reproduction: `C:\pt\analyses\anyio-probe-readiness-20260927-v1`;
  descriptor: `selected-pytest\prepared-probe-dependencies.json` within that packet.
- Protocol, metrics, public review, environment inventory and closure:
  `C:\pt\analyses\planning-off-regression-20260927-v1`.
- Earlier decisions and immutable records: [documentation history](history/README.md).

## Reading and updating this page

At task start, read this page and the relevant implementation/operation section.
Search history only when a named failure, decision, or evidence gap needs it; read
the matching passage rather than whole snapshots. Historical "current", "latest",
"next", commands, and approvals describe their original checkpoint only.

Replace stale status here. Record a significant completed investigation once in
`docs/history/`, then keep only its current implication and evidence link here.
Do not append run-by-run results, validation totals, or superseded plans to this page.
Documentation size limits are checked by `tests/test_documentation_layout.py`.
