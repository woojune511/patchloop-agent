# Cross-task evidence to action audit

Date: 2026-09-29. Provider-free, read-only trace analysis; no new task execution,
private evaluator inspection, runtime change or general-performance claim.

## Scope and method

Inventory 45 completed journals across nine task identities: boundary-pair panel
24, basic/current panel 12, AnyIO seeded observation repair four, toqito funded
follow-up one, HF observation repair four. The toqito journal includes its inherited
history; it is one continued trajectory, not additional independent episodes.
The 36 panel solves cover seven tasks. Named follow-ups extend mechanism coverage;
this is a purposive sample, not all historical runs or a randomized channel comparison.

Read all action outcomes in these journals. Extract nonzero/failed registered
checks and probes, every later public decision and action through termination.
Distinguish delivered evidence from operator replays made only after termination.
An evaluator FAIL is not a public counterexample the model could have acted on.
A next-step choice alone is not proof of eventual abandonment.

## Findings

| Evidence channel | Observed sequence | Interpretation |
| --- | --- | --- |
| Registered check FAIL | 11 events in eight trajectories, three task identities; each followed by edits and eventual PASS of the same check | Repair from concrete failure is available; submission gates require these checks to pass |
| HF external current-diff observation | Treated seeded B1 investigates/repairs; B2 checks and submits unchanged | Correct delivery does not guarantee use; no robust treatment effect |
| toqito failed probe | Several earlier failures prompt inspection/new probes; final syntax-invalid probe is acknowledged, then base-regression PASS and submission | An unanswered verification question can be left behind without verification capacity being exhausted |
| Post-run operator discoveries | Pydantic/HF failures and toqito residual numerical case discovered outside the episode | Do not count as agent ignoring known evidence |

The 11 registered failures consist of HF six events in three trajectories,
pyfakefs one event in one trajectory, AnyIO four events in four trajectories.
All 11 next active inputs were reconstructed and contain the triggering action ID;
public next decisions explicitly address the failures. No delivery error was found.
This checks event delivery, not semantic correctness of every interpretation.

Examples:

- HF boundary HB2: failing cases 72 -> 72 -> 48 -> PASS. The model traced retained
  endpoint state, HfApi forwarding and file_download forwarding, editing each path.
  Same-check recovery did not imply full acceptance; its evaluator still failed.
- pyfakefs Current: parent-traversal check PASS, upstream regression FAIL on broken
  symlink parents, next action narrows an exception catch to FileExistsError, then
  same-check and task-check PASS. Isolated acceptance subsequently passed.
- AnyIO: all four seeded trajectories see explicit-cancel lifecycle failure, inspect
  runner ownership, repair and pass that check. Both observation arms receive this
  later registered failure, so these traces do not isolate the initial external cue.

No failed registered check/probe action was found in 32 of the 36 fresh panel
journals. Thus most cannot test response to a delivered failure at all. Passing
public checks alongside evaluator failure supports a coverage/interpretation gap,
not an ignored-counterexample count. The eight successful registered-check recovery
trajectories are also selected completed runs under a blocking submission rule;
they cannot prove that making all diagnostics mandatory would improve quality.

## Strongest unresolved-verification example

The toqito journal contains six failed probes: two numerical assertion mismatches,
two TypeErrors during candidate execution, one setup mismatch and one syntax error.
These are different evidence classes. Numerical disagreement can implicate an
incorrect expectation; setup/compile failure establishes no candidate behavior.
The first five provoke further inquiry in the public trace. This is not a blanket
inability or unwillingness to react to optional evidence.

After the last syntax error, the model correctly says repository behavior was not
tested, but switches to base-regression and then finish_task. No later probe occurs.
At the next actual input it still has nine calls, 57 tool actions, 3418 seconds,
USD 2.520385 and offered run_probe. No accepted mutations remain. Lack of edit
capacity does not make the pending verification impossible; the model explicitly
uses mutation exhaustion and submission eligibility to justify closure.
The terminal outcome is acceptance PASS, but that does not validate the unexecuted
probe. An operator later ran the valid program successfully; that result was never
agent verification evidence. No claim of a remaining defect follows from syntax
failure alone.

Five inherited toqito next-input reconstructions fail through the current loader
with _ProviderContinuationError; their action/decision links are journal evidence
only in this audit. The final syntax-error successor reconstructs successfully.
Do not describe all six historical deliveries as freshly verified. The earlier
closed toqito audit remains separate supporting evidence.

## State mechanism and competing explanations

Actual final inputs for toqito and both treated HF episodes have empty
working_notes.verification.items/unresolved_ids. Their open_question focuses on the
remaining registered check. The existing concern feature cannot preserve a question
the model never records. A focus change can therefore leave no structured record
of the earlier discrepancy even though its raw observation is still available.
This is narrower than lost context and different from lack of repair ability.

The common weak point suggested by HF B2 and toqito is maintaining the status of
non-blocking evidence/questions through unrelated checks and submission. The
[latest-recommendation ablation](2026-09-29-completion-recommendation-ablation-results.md)
showed no immediate selection gain, so another completion-wording change is not
supported. Neither record proves a single universal cause: evidence authority,
expectation validity, model variation and task-specific remaining resources differ.

A better next design target is explicit question lifecycle: candidate mismatch,
invalid/unfinished experiment, and supported resolution/dismissal must remain
separate. Reuse existing concerns rather than add another freeform memory channel.
Before any live intervention, test provider-free that changing focus, unrelated
PASS and invalid probe output do not silently imply resolution, while edits mark
old observations historical and supported dismissals remain possible. The observed
failure is missing registration/use as well as persistence, so simply making an
unused list durable is insufficient. Any automatic registration would need provenance
and must not promote arbitrary failed model assertions into trusted bugs. No new
hard submission gate, runtime change or paid comparison is authorized by this audit.

## Evidence and validation

External immutable extraction and source journal hashes:
C:/pt/analyses/cross-task-evidence-action-20260929-v1/audit.json;
reproduction script audit.py; hash-bound dev-run-v1 audit journal.
Roots: C:/pt/boundarypair0928b; C:/pt/baseline-compare-20260928-v1;
C:/pt/obsrepair0927a; C:/pt/probefollowup0928a;
C:/pt/analyses/observation-repair-panel-20260929-v1/state.

Relevant prior records: [baseline](2026-09-28-basic-current-baseline-comparison.md),
[AnyIO](2026-09-27-anyio-observation-repair-comparison.md),
[toqito](2026-09-28-probe-followup-results.md),
[HF decision audit](2026-09-29-observation-decision-audit.md).
No old artifacts or closed reports rewritten. Zero provider cost. Documentation
layout and diff checks run for this documentation-only change. No fresh accuracy,
safety or task-acceptance measurement is produced.
