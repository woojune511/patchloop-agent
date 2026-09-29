# Current status

Updated: 2026-09-30. This is a replaceable snapshot of current decisions, not an
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

The [boundary-pair panel](history/2026-09-29-boundary-pair-panel-results.md)
completed 24 fresh runs on six tasks: A 7/12, B 8/12; paired wins 1/0/11. All final
public checks passed, including nine acceptance failures. Neither arm used probes.
Keep the baseline; no procedure adoption. Cost USD 12.1553535; remaining funds closed.

The [public discrimination replay](history/2026-09-29-boundary-discrimination-replay.md)
ran 15 local containers on base plus all Pydantic/HF/PDM final patches, without model
calls or private evaluation. Holding mode/name constant exposed overbroad behavior in
all four Pydantic patches; testing an endpoint-free client under an ambient endpoint
exposed three HF patches. HB2 preserves that boundary but its residual failure is open.
PDM's missing-path replay did not confirm the suspected interpreter-construction failure.

Separate evidence selection, execution readiness and repair. Existing checks omit
the P/H distinctions; no default prompt or gate change is justified. These already
used tasks cannot establish generalization, and operator examples must not become
undisclosed agent hints.
The [selection diagnostic](history/2026-09-29-discriminating-case-selection-results.md)
and [registered replay](history/2026-09-29-selected-probe-execution-results.md)
separate case selection, expectation validity and execution readiness; neither
established task-acceptance improvement. Their allocations are closed.
The [observation-to-repair comparison](history/2026-09-29-observation-repair-panel-results.md)
completed four seeded H episodes: frozen public counterexample repaired A 0/2,
B 1/2; benchmark acceptance 0/4, safety PASS 4/4. All 23 actual inputs retained
correct feedback and candidate currency. B1 inspected and repaired the observed
boundary; B2 submitted unchanged after public PASS despite receiving the same
counterexample. The [decision audit](history/2026-09-29-observation-decision-audit.md)
rules out delivery, hard budget exhaustion and tool closure for B2. External evidence
does not enter computed failure/submit state; guidance causality is unproven. The
[fixed-input ablation](history/2026-09-29-completion-recommendation-ablation-results.md)
completed six responses: targeted counterexample investigation A 1/3, B 1/3;
paired wins 1/1/1. Removing the latest recommendation showed no advantage.
The [stricter audit](history/2026-09-30-retained-counterexample-audit.md) rechecked
95 journals: HF B2 is the confirmed delivered counterexample left in the final patch.
Tox responded with a targeted repair; 11 registered failures reached same-check PASS.
The [judgment/action audit](history/2026-09-30-public-judgment-action-audit.md)
localizes B2 to unsupported closure; A3 does not prove abandonment.
The [disposition diagnostic](history/2026-09-30-evidence-disposition-results.md)
completed 12 responses: joint A 1/2, B 0/2; B claimed unsupported resolution 2/2.
Do not adopt; USD 0.689213 settled, allocation closed.
[Context preparation](history/2026-09-30-evidence-context-preparation.md) freezes
four evidence-matched reviewer pairs across HF/AnyIO/tox. Live NOT_RUN; no collector.
The [lifecycle audit](history/2026-09-29-verification-concern-lifecycle-audit.md)
found HF/toqito questions were never registered. [Observation linking](history/2026-09-29-verification-observation-linking.md)
now retains registered unsuccessful executions and provenance; local tests/mock passed.
It certifies neither bugs nor semantic resolution and adds no submission gate.
Operator feedback stays separate; live benefit remains unestablished.
[Restoration](history/2026-09-29-optional-probe-restoration.md) confirmed tox's seeded
regression. [Request parity](history/2026-09-29-observation-request-parity.md) passed
for AnyIO/pyfakefs; direct resume fails runtime identity. The current-runtime
[offline fork](history/2026-09-29-observation-fork-rehearsal.md) preserves that guard.
The [live comparison](history/2026-09-29-observation-comparison-results.md)
ran three conditions, then stopped on a local recount guard; three remain NOT_RUN.
The complete pair tied on target handling; original N1 evaluations errored.
Provider-free [boundary fixes](history/2026-09-29-observation-boundary-fixes.md)
separate recount admission and receipt lineage. [Saved N1 patch evaluation](history/2026-09-30-observation-n1-saved-patch-evaluation.md)
passed task v3 for both arms. Both repaired the competing lifecycle failure while
leaving the target probe setup unresolved. Establish target relevance before another
comparison; no retention benefit is established and prior allocations remain closed.
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
  [contract](../.agent/caller-information.md).
- Closed comparison: [checkpoint results](history/2026-09-27-checkpoint-live-results.md);
  packet: `C:\pt\analyses\checkpoint-live-results-20260927-v1`; live: `C:\pt\mutationlive0927a`.
- Live collector: [preparation and environment block](history/2026-09-27-checkpoint-live-preparation.md);
  [contract](../.agent/checkpoint-comparison.md);
  packet: `C:\pt\analyses\checkpoint-live-comparison-20260927-v1`.
- Offline continuation: [restoration and execution](history/2026-09-27-checkpoint-continuation.md).
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

Read this page and relevant implementation guidance first. Consult history only for
a named evidence question; historical commands and approvals do not carry forward.
Replace stale decisions here and link completed investigations in `docs/history/`.
Keep this snapshot within the limit checked by `tests/test_documentation_layout.py`.
