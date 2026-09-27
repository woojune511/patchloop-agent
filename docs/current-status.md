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

Comparisons answer concrete causal questions when needed. Successful plumbing,
note/probe use, or submission alone does not establish better task solving.
Simplifying an ineffective mechanism is a valid next step.

## Active runtime and working baseline

- `dev-head` is the sole active mutable runtime; every run is `official=false`.
- The chosen performance baseline is `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens.
  The latest information comparison used collector checkpoint `0cf07b81`.
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

The cleanup-information comparison is closed; it established neither benefit nor
equivalence. See [results](history/2026-09-27-cleanup-information-results.md).

The waiting-caller stall also occurs at base and lacks a public support requirement;
it does not invalidate acceptance. See
[caller support scope](history/2026-09-27-caller-support-scope.md).

AnyIO is development/calibration data; its adapted-task acceptance is separate from
original scores. See the linked benchmark audit.
The [original-input pilot](../.agent/original-input-pilot.md) fixes three fresh attempts:
toqito-1538, MontePy-933_interface and darts-3065. Deterministic selection excludes
current task/ledger repositories; this is a development pilot, not proven held-out.
All three images were acquired with explicit approval and their digests fixed.
Packages passed isolated reference evaluation and environment controls. Public tests
run in temporary copies; toqito excludes one obsolete test contradicting the issue.
Pre-run limits were fixed at four files/1,000 lines with API changes allowed.
Pinned probe bundles and public canaries are documented in
[capacity results](history/2026-09-27-installed-probe-capacity.md).
See [readiness](history/2026-09-27-original-pilot-readiness.md) for earlier preparation evidence.
[Package validation](history/2026-09-27-original-pilot-packages.md).
See [calibration](history/2026-09-27-original-benchmark-calibration.md).
See [benchmark differences](history/2026-09-27-anyio-benchmark-differences.md).
The fixed pilot is complete: MontePy and darts passed original evaluation; toqito
made one edit but exhausted its $1.20 allowance before checks/submission (NOT_RUN).
Resolved/submitted is 2/2; resolved/planned is 2/3. Total cost was $2.0892005 / $3.60;
remaining funds are closed. All three passed environment preparation. The user accepts
more budget when necessary; $1.20 is not a product constraint. Cost-policy work is
deferred (no runtime policy changed). The
[public patch audit](history/2026-09-28-toqito-public-validation.md) found a semantic
error despite 14 passing base tests: the agent reversed conditioning in a probe's
expected value, blamed its optimizer, and generalized a CQ closed form incorrectly.
A feasible-state witness contradicts the patch by 0.18659 bits. Original NOT_RUN is
unchanged; this is separate public operator evidence. The
[mechanism audit](history/2026-09-28-general-failure-mechanism.md) confirms that full
outputs, expectation code and generic cautions were delivered before the wrong
attribution. A self-authored expectation became assumed truth; frequency and a fix
remain unproven. The [unhinted continuation](history/2026-09-28-post-edit-budget-results.md)
used $0.2168265 in two new calls: old regression PASS, then unchanged submission and
benchmark FAIL (safety PASS). With ample resources, the agent treated downarrow-only
regression results as validation of new uparrow behavior. It did not revisit the
comparator or correct the patch. A [generic scope cue](history/2026-09-28-verification-scope-preparation.md)
is prepared at the same checkpoint; only one input field changes. A proposed $3,
one-run continuation awaits exact authorization. Prior allocations remain closed;
no default policy change is authorized.
See [pilot results and process audit](history/2026-09-28-original-pilot-results.md).

Earlier supplied-candidate A/B repairs remain separate 2/2 acceptance per arm,
with no observed information advantage. They are not fresh-solve controls;
earlier NOT_RUN outcomes remain unchanged.
Use the selected pytest dependency bundle for further AnyIO diagnostics. The
planning OFF comparisons remain closed without automatic adoption or baseline change.

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

- Cleanup information: [results](history/2026-09-27-cleanup-information-results.md);
  packet: `C:\pt\analyses\cleanup-information-results-20260927-v1`.

- Cleanup mechanism: [trace and one-line removal](history/2026-09-27-anyio-cleanup-cancellation.md);
  packet: `C:\pt\analyses\anyio-cleanup-analysis-20260927-v1`.
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
- Original input pair: [mutation advice checkpoint](history/2026-09-27-mutation-advice-checkpoint.md);
  [contract](../.agent/mutation-advice-checkpoint.md);
  packet: `C:\pt\analyses\mutation-advice-checkpoint-20260927-v1`.
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
- Prior preparation: [AnyIO failure observation](history/2026-09-27-anyio-failure-observation.md).
- Frozen reproduction/comparison: `C:\pt\analyses\anyio-observation-repair-20260927-v1`.
- Preparation correction: [AnyIO probe readiness](history/2026-09-27-anyio-probe-readiness.md).
- New bundle and public reproduction: `C:\pt\analyses\anyio-probe-readiness-20260927-v1`;
  descriptor: `selected-pytest\prepared-probe-dependencies.json` within that packet.
- Separate prior model result: [planning OFF regression](history/2026-09-27-planning-off-regression.md).
- Protocol, metrics, public review, environment inventory and closure:
  `C:\pt\analyses\planning-off-regression-20260927-v1`.
- Separate prior result: [planning ON/OFF comparison](history/2026-09-26-planning-off-comparison.md).
- Separate timing result: [first-plan timing comparison](history/2026-09-27-after-source-planning-comparison.md).
- Current implementation: [first plan after source](history/2026-09-26-after-source-planning.md).
- Existing contract: [brief planning](../.agent/planning-experiment.md).
- Prior next-question result: [declaration checkpoint comparison](history/2026-09-26-declaration-checkpoint-comparison.md).
- Prior interpretation audit: [first interpretation and source questions](history/2026-09-26-first-interpretation-audit.md).
- Prior candidate result: [independent candidate comparison](history/2026-09-26-independent-candidate-comparison.md).
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
