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
completed 12 fresh runs across six `dev-train` tasks. Basic passed 4/6 and Current
passed 5/6; paired Current wins / Basic wins / ties were 1 / 0 / 5. All safety states
passed. Current cost $3.338190 versus Basic $2.777399 (+20.2%) and used 1,431.504
versus 1,159.543 active seconds (+23.5%). The total actual cost was $6.115589.

This is a single-repeat three-feature bundle comparison, not a causal estimate or
general success-rate claim. The only discordant task was pyfakefs: Basic passed both
registered public checks but failed evaluation, while Current followed a two-mutation
path through a visible regression and successful repair. Planning, probes, and repair
recheck changed together, so none has isolated credit. Keep the selected Current
configuration as a working baseline, not a proven default improvement.

The [boundary-pair procedure panel](history/2026-09-29-boundary-pair-panel-results.md)
completed 24 fresh runs across Pydantic, HF Hub, Fromager, Loguru, PDM and pgmpy.
Current A passed 7/12; procedure B passed 8/12, with paired B wins / A wins / ties
1 / 0 / 11. Only PDM repetition one differed. All submitted, all safety PASS;
NOT_RUN and infrastructure failures were zero. Both known failure tasks failed all
four runs each. Actual cost $12.1553535; unused $35.8446465 is closed.
B cost 26.6% more and took 24.7% more active time. Do not adopt the instruction.

Arm-masked public review was frozen before outcome mapping; 197 actual model inputs
were verified. B made selected pairs more explicit, but neither arm used run_probe.
Every final patch passed public checks, including nine acceptance failures. Pydantic
still used an overbroad field-mode guard. One HF B run preserved raw explicit endpoint
context but still failed acceptance. PDM's sole discordance has a source-level candidate
cause (active interpreter construction before the ignore guard), not a verified public
failing-input diagnosis. Valid pair prose and selected-case PASS do not prove full scope.

The active question is whether selected evidence can falsify the proposed condition.
Use saved public traces/patches to distinguish non-discriminating examples from missing
verification capability before another paid comparison. Keep the baseline fixed;
no new prompt fields, gates or default behavior change is justified by this panel.
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

All allocations, including the basic/current panel, are closed. Earlier
supplied-candidate repairs, operator replays and response-only samples remain
separate from fresh solves. Planning
comparisons are closed; the selected working baseline above is unchanged.

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
