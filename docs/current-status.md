# Current status

Updated: 2026-09-28. This is a replaceable snapshot of current decisions, not an
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

AnyIO is calibration data, separate from original scores. The
[pilot](../.agent/original-input-pilot.md) fixed fresh attempts on toqito-1538,
MontePy-933_interface and darts-3065, excluding current task/ledger repositories.
This is development data. Image digests, environment controls, public checks and
four-file/1,000-line limits are in
[readiness](history/2026-09-27-original-pilot-readiness.md); pinned probe bundles in
[capacity results](history/2026-09-27-installed-probe-capacity.md).
Toqito excludes one obsolete public test contradicting the issue.
[Package validation](history/2026-09-27-original-pilot-packages.md).
See [calibration](history/2026-09-27-original-benchmark-calibration.md).
See [benchmark differences](history/2026-09-27-anyio-benchmark-differences.md).
The pilot is complete: MontePy and darts passed; toqito exhausted $1.20 before
checks/submission (NOT_RUN). Cost $2.0892005; funds closed. Preparation passed.
The user accepts more budget when needed; cost-policy work remains deferred. The
[public patch audit](history/2026-09-28-toqito-public-validation.md) found a semantic
error despite 14 passing base tests: the agent reversed conditioning in a probe's
expected value, blamed its optimizer, and generalized a CQ closed form incorrectly.
A feasible-state witness contradicts the patch by 0.18659 bits. Original NOT_RUN is
unchanged; this is separate public operator evidence. The
[mechanism audit](history/2026-09-28-general-failure-mechanism.md) confirms that full
outputs, expectation code and generic cautions were delivered before the wrong
attribution. A self-authored expectation became assumed truth; frequency and a fix
remain unproven. The [unhinted continuation](history/2026-09-28-post-edit-budget-results.md),
[scope cue](history/2026-09-28-verification-scope-results.md), and
[deferred cue](history/2026-09-28-deferred-scope-results.md) did not fix it.
[Advice removal](history/2026-09-28-completion-advice-results.md) prompted probes
and an edit but still failed. The [expectation review pair](history/2026-09-28-expectation-review-results.md)
changed B's first action to independent testing and eventually removed the wrong
CQ shortcut. Both final patches passed 14 public regressions; A failed the benchmark
and two operator public checks, while B passed those two checks but did not submit.
B's final call timed out with 4.499 seconds remaining: billing unknown,
acceptance/safety NOT_RUN. Recorded cost $2.9267315, final total unknown;
$6 authorization is closed. A separately approved [time extension](history/2026-09-28-time-extension-results.md)
added 60 minutes and a fresh $3 cap. One call ($0.094595) submitted the unchanged
patch: benchmark FAIL, safety PASS. No extra probe/edit; unused fresh funds closed.
The earlier unknown charge and B NOT_RUN remain. More time enabled submission but
not benchmark success. The [public requirements audit](history/2026-09-28-remaining-public-requirements.md)
reproduced pure-state underflow masked by the downarrow clamp and mixed-state
complex-to-float exceptions in both existing environments. A selected 15-case matrix
has 8 pass / 7 fail, not a benchmark score or hidden-failure attribution. Final
changed-path/input-range coverage was missing. The [closure audit](history/2026-09-28-verification-closure-process.md)
shows the CQ question survived: the model weakened its probe plan and closed it at
submission. All 17 verification lists were empty; later boundary cases were never
constructed. The [policy comparison](history/2026-09-28-closure-policy-results.md)
collected four responses: A finished twice; B finished once and proposed one probe.
Cost $0.446253; funds closed. No tools ran; quality improvement is unproven.
The [selected probe](history/2026-09-28-selected-closure-probe.md) has a valid
classical expectation and exposes the objective TypeError on the frozen patch.
The [funded continuation](history/2026-09-28-probe-followup-results.md) repaired that
failure and passed benchmark/safety checks: 5 calls, $0.685091; funds closed.
Its post-fix probe had a SyntaxError, which it left unresolved before submission
despite available probe/time/cost. Operator replay of the valid probe passed;
the fixed public matrix improved 8/15 to 14/15, with pure-state underflow remaining.
The [closure audit](history/2026-09-28-invalid-probe-closure.md) verified all five inputs:
the model acknowledged the invalid probe, replaced its question with check eligibility,
then cleared it. System optional-experiment advice returned after the one-input ablation.
The [A/B result](history/2026-09-28-invalid-probe-policy-results.md) was A: finish/probe,
B: finish/finish; $0.404483, funds closed. No improvement from advice removal was
observed. The sole probe stopped on floating-point setup equality and used a
refuted CQ expectation. The [construction audit](history/2026-09-28-probe-construction-analysis.md)
confirmed exact-equality misuse and reuse of a contradicted formula despite delivered
counterevidence. The [reconciliation result](history/2026-09-28-expectation-reconciliation-results.md)
found supported expectations A 0/2, B 1/2; no reliable effect. Cost $0.871760; funds
closed. Two probes stopped on float setup equality. Next: a generic tolerance
example for setup; oracle validity remains unresolved. No default cue adoption.

Earlier supplied-candidate repairs are not fresh solves. Planning OFF remains closed.

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
- Latest result: [AnyIO fresh solves](history/2026-09-27-anyio-fresh-solve.md);
  packet: `C:\pt\analyses\anyio-fresh-solve-20260927-v1`; live: `C:\pt\anyiofresh0927a`.
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
