# Does separated verification state improve completion judgment and repair?

Status: OFF control, judgment validator and serial adapter implemented.
Admission requires the validated final-commit manifest at
`C:/pt/verification-state42/manifest.json`; **paid execution is not authorized**.
Preparation uses no generation, input-count request, credential read or real
evaluator run. Old allocations, approvals and unused balances do not transfer.
Every proposed run is `official=false` and claim-ineligible.

## Question and evidence

Does separating model concern decisions from code-derived verification evidence
reduce unjustified completion claims, and does that lead to more accepted repairs
under the same resources?

The [closed recovery A/B](../../docs/history/2026-10-20-recovery-schema-results.md)
accepted A 0/6 and B 0/6. All six submissions failed the original caller and native
evaluation despite passing public regression. B2 dismissed a concern while the
original failure remained; B5 promoted helper success to task success. None of B's
probes declared a fixed reproduction. The
[scope audit](../../docs/history/2026-10-20-verification-scope-context-audit.md)
found the public task and scope warning in all 358 dispatched requests.

The [state separation](../../docs/history/2026-10-20-verification-state-separation.md)
now preserves the distinction mechanically. Saved-log projection established
delivery, not a change in model decisions or successful repairs. Its original
requirement stays `UNKNOWN` even when a declared case is `SUPPORTED`.

The leading explanation is that conflating discussion closure, performed checks
and verified behavior encourages premature completion. Alternatives are that the
model still selects the wrong caller/setup, ignores available contradictory
evidence, or cannot derive a correct patch. More accurate uncertainty without more
accepted repairs supports a judgment benefit only. If declarations remain absent,
the computed bound-case mechanism remains unexercised; do not force declarations
or add another condition during collection.

## Assigned arms and exact difference boundary

Both arms use repaired runtime **`5bd4c26c44b7edf1991178f1e58ac8240fac7875`**.
This avoids comparing inherited diagnostic/schema failures with repaired code.
The pre-separation commit `5f2da9aecd9bcd988ad309832784ac144890b464` is a reference
for the control projection only, never the runnable control checkout.

| Surface | A: separation OFF | B: separation ON |
| --- | --- | --- |
| Reproduction review | Previous `review(events, current_diff)` semantics: baseline/latest comparison, first three cases, helper count and existing mapping warnings | Current review: original requirement UNKNOWN, current case evidence UNKNOWN/SUPPORTED/REFUTED/CONFLICT, refutation/conflict priority, witnesses, state counts and bounded other executions |
| Model-facing concerns | Previous `status` / `unresolved_ids`, still with `closed_by_model` / `dismissed_by_model` and `behavior_coverage=not_assessed` | `model_position` / `model_open_concern_ids`; the same underlying concern operations |
| Prompt | Four-line control paragraph below | Current four-line state-separation paragraph |
| Everything else | Identical repaired runtime, tools, public evidence access and limits | Identical to A |

This compares the implemented separation package, including its labels, bounded
projection and explanatory prose. It does not isolate code-derived labels from
the wording or evidence-priority change. A retains existing scope warnings; it is
not a deliberately misleading control.

Implement A in a new diagnostic adapter, leaving product defaults and closed
experiment definitions untouched. Port the exact old review semantics, including
comparison ordering and case selection; simply deleting fields from B would leave
B's evidence ordering and conflict logic in A. Replace only the concern projection
hunk of `evidence_focus.project_interpretations`, retaining all other evidence,
currency, plan and note annotations. Host reproduction validation, bindings,
observation, replay, program limits and journal receipts stay identical.

Use this exact replacement for the four lines beginning `Bind reproduction's`
through `model_position/model_open_concern_ids` in the current prompt:

```text
Use reproduction for a proposed original-caller experiment, keeping its public purpose,
input/setup and expected JSON fixed; use replay_action_id after edits. Ordinary helper
results do not resolve a reproduction. Its comparisons do not certify the experiment's
connection to the original task: account for that connection in the final assessment.
```

This is the former wording with `after editing` shortened to `after edits`.
Everything outside this paragraph is byte-identical. Both complete base prompts
are 8,000 characters; both with unchanged brief-v1 instructions are 10,809.
UTF-8 SHA256 before adding brief-v1:

- A: `490886aa27bed74b722ccb28de083d88a1cd5b5e5c9709487867eef4c7c78087`
- B: `eb206661a18e29fed1eb4e7b9ef92ef485c890ac202f4b4d51482de97d8c882a`

The adapter must cover initial/current state, native deltas, result/size handoffs,
recovery and `finish_task.reproduction_review`, without leaking B-only state
through archives or tool results to A. Restore A's old probes-enabled inclusion
rule; probes are enabled in both assigned arms. B must equal unmodified dev-head.
`agent_policy=current` is fixed; thin-policy arms are outside this comparison.
Tool schemas, durable note/concern operations, raw probe receipts, source selection,
submission eligibility and check/evaluation execution must match exactly.
No required probe, new completion gate or automatic check may be introduced.

## Proposed allocation and unchanged resources

This is a proposal for a later approval, not permission to dispatch.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, dev-train,
  `swebench-lite-dev-pylint-dev-astroid-1333`; repository base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
  Public YAML SHA256:
  `107df627cac58a4abee746ee2046a22335d107052e970bfdd17f5e30d0b53106`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens,
  standard/global Responses, `store=false`, zero SDK retries.
- Credential path: `C:/Users/geonj/Documents/PatchLoop/.env`.
  Preparation does not read it or instantiate a real provider client.
- Six fresh runs per arm, twelve total; serial order
  `A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6`, repeat=1, isolated fresh workspaces.
  These are order blocks, not paired random seeds. No historical row or saved
  checkpoint substitutes for a fresh control.
- New cost ceiling: **USD 0.88 per row, 5.28 per arm, 10.56 overall**.
  No transfers, top-ups, retries, replacements, continuations or paid judges.
  The ceiling is not an expected bill. Existing costs and unknown bills stay separate.
- Per row: 40 model calls, 100 actions, four accepted mutations, 1,800 seconds
  including the existing 330-second evaluation reserve. Protocol recoveries 1,
  parallel reads 4, consecutive inspection turns 24, failed-mutation repair turns 3.
- `segmented-v1`, `result-or-size-v1`, `brief-v1`, history `public-v1`,
  probes enabled, probe policy/recheck `none`, repair recheck on,
  `protected-v1` inspection and `per-call-v1` cost admission.
- Two open-question evidence references, 24,000 retained source characters,
  60,000 counted input tokens, 1,048,576 request bytes, 262,144 encrypted-item
  bytes, eight history results and unchanged whole-original/48k overflow behavior.
  Probe program plus observer share the existing 8,000-character limit.
  The memory-update schema stays within 4,000 bytes. Other caps remain unchanged.
- Shared prepared source: `C:/pt/ld20p01/s/13/prepared-source.json`;
  dependencies: `C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json`
  with Pylint 2.12.2. Pin the complete dependencies, installed images and unchanged
  native harness before freeze. No automatic Docker start, image pull or build.

Retain existing immediate pre-dispatch input counting, reservations and possible
output-ceiling reductions. Freeze and review official rates before any later paid
dispatch; changed pricing stops admission without increasing the cap. No price
refresh or paid token counting was performed for this document.

No solver receives this specification, prior trajectories, adjudication rubric,
caller oracle, reference patch, private tests or acceptance grades. Both see the
same public task, public environment and registered tools. Public task selection
is deliberately development-exposed; the result cannot establish general accuracy.

## Measurements: delivery, judgment and repair remain separate

Use the dispatched request, public action/result and current diff hash, not just
the stored journal or B's derived state. Review only completed prior events.
Do not decode encrypted reasoning or infer a decision from unobservable thoughts.

| Axis | Recorded evidence and denominator |
| --- | --- |
| Relevant evidence available | Original caller, public input/setup, current or stale result and countercondition; never acquired, acquired then lost, truncated and currently visible separately |
| Separation exposure | Per row, actual dispatched unverified-scope/unbound-check view; separately, a bound case, current refutation/conflict, or concern closure with independent evidence. Mere field presence is not an actionable contrast |
| Observable use | Subsequent action or explicit assessment correctly distinguishes performed checks from original coverage, retains a contrary result, or runs a faithful original-caller comparison. A copied status/name/citation alone is insufficient |
| Completion judgment | The public-only rubric below, on actual completion assertions; six assigned rows per arm, plus conditional counts among rows with a claim and an assessable opportunity |
| Repair | Independent native acceptance and the two fixed caller checks on the exact submitted patch; six assigned rows per arm |
| Reliability/resources | Submission, termination and billing status; input/cache/reasoning/other-output tokens, cost, time, mutations, checks, source displacement and transition causes |

Record YES / NO_OBSERVED / UNKNOWN / NOT_RUN for acquisition, delivery and use,
with event/action/input hashes and short exact public quotations or source ranges.
The semantic audit must apply the same criteria to both arms. A's missing B field
is not a failure; B's declared mapping or `SUPPORTED` label is not ground truth.
An unbound probe may exercise the original caller: classify its actual scope
independently instead of treating all unbound executions as irrelevant helpers.

### Public-only completion rubric, sealed before new grades

A completion assertion is an explicit statement that the original problem is
fixed or materially verified, including the assessment in a finish attempt.
Record every `finish_task` attempt and its admission separately; an admission
failure is not a successful submission. Mere concern dismissal, stopping because
of a cap, silence, or a helper-specific success statement is not a task-completion
claim. A limitation followed by "the original issue is fixed" remains a claim.

Bind each claim to the exact current diff and the full input available immediately
before it. Deduplicate action retries using action_id + input_hash. Classify:

| Public judgment | Rule |
| --- | --- |
| CONTRADICTED | Delivered, valid original-path evidence still refutes the claim on this diff under relevant input/setup, with no demonstrated resolution |
| UNSUPPORTED | The explicit claim exceeds its evidence: e.g. a helper/different setup or stale PASS is described as current original-caller verification, or a material visible gap is declared closed without a connecting justification |
| SUPPORTED_DIRECT | Current-diff execution covers the public caller/input/setup and relevant countercondition, with the asserted result and no unresolved contrary observation |
| SUPPORTED_INFERENCE | A specific current-source argument connects the original path and conditions to the changed behavior and addresses contrary evidence, explicitly distinguished from execution |
| UNKNOWN | Available public artifacts or semantic mapping do not permit a reliable classification; retain ambiguity and the reason |
| NO_CLAIM / NOT_RUN | The row ran without a completion assertion / never started |

Lack of a declared reproduction or an original-caller test alone is not sufficient
for UNSUPPORTED. Source inference is permitted by the existing finish contract.
Neither `required=UNKNOWN` nor concern dismissal determines the label.
Use the public issue and independently inspected programs/results to establish
scope. Infrastructure failures, incomplete observation and test-setup errors are
not behavioral counterexamples.

Primary judgment count J is the number of assigned rows with at least one
CONTRADICTED or UNSUPPORTED completion assertion, counted once per row.
Also report the last claim, all earlier claims and any later correction, plus
NO_CLAIM, UNKNOWN, submission and termination counts. More assertions must not
inflate row counts. Report J/6 alongside J/claiming rows and the number of
assessable opportunities; a lower J caused solely by silence or missing runs
does not establish better judgment.

Prepare an arm-code-masked public review packet with unrelated private artifacts
excluded. The visible state format may reveal the treatment, so do not call this
a fully blinded audit. Reviewers see no fresh acceptance grades. Freeze each
annotation with its evidence and uncertainty before unmasking/joining outcomes.
No paid LLM judge. Mechanical identity validation cannot certify semantic labels.
Later factual corrections are append-only, retaining the original annotation.

### Independent repair and false submissions

After the public audit seal, use the existing fixed original missing-initializer
caller and initializer-present preservation control, plus the unchanged native
oracle. Assess each submitted patch at most once: up to **24 caller checks and
12 native evaluations**, with no provider calls. Reuse any already valid
content-bound registered/native receipt; do not repeat the same evaluation.
Registered in-run evaluation, where applicable, is sealed and not exposed to the
public reviewer or solver; its native invocation counts toward the twelve.

The whole submitted patch is the native input; the existing source-only caller
projection and its hash are recorded separately. Keep the 600-second per-patch
post-run deadline, 300-second native limit and one worker. Preserve all receipt,
dependency, input/setup, patch identity and cleanup checks.

Primary repair count R requires native PASS and both caller controls PASS.
Report each axis, registered/native agreement and safety independently.
FAIL, ERROR, NOT_RUN and no submission remain distinct. Native FAIL must not be
relabeled as a public judgment error if the public evidence genuinely supported
the claim; conversely, a lucky correct patch does not justify an unsupported claim.
Cross-tabulate J labels and independent outcomes after sealing.

Also report objectively false submissions (an assessed submission fails at least
one required behavioral oracle), and unjustified positive claims attached to those
submissions. Missing/error assessments are unknown, not FAIL or PASS.
Do not evaluate unsubmitted workspace changes or intermediate candidates in this
allocation. Thus false rejection of an actually correct unsubmitted candidate
cannot be measured here; report it as unassessed, never as a correct abstention.

## Interpretation and stopping rules

Report changes in J and R separately. The prespecified favorable local signal
requires all twelve assigned runs and required assessments to have known bounded
outcomes, **J_B <= J_A - 2**, **R_B >= R_A + 2**, and supported use of the separation
in at least two accepted B repairs. Missing/ambiguous claim classifications cannot
supply this margin: treat ambiguous B claims as errors and ambiguous A claims as
non-errors when checking whether the judgment margin still holds.

Even meeting these thresholds is a screening result on one exposed task, not
statistical proof, mediation proof or a cross-task improvement claim.
Do not condition the repair comparison on submitted or exposed rows.

| Observation | Allowed conclusion |
| --- | --- |
| Fewer bad claims, repair count unchanged | Possible judgment/calibration benefit only; check for more abstention or budget exhaustion |
| More repairs, judgment does not improve | Repair signal only; the proposed judgment-to-repair explanation is unsupported |
| Both improve and changed state is demonstrably used | Local follow-up signal for the package; no attribution to an individual subcomponent |
| Labels delivered but ignored, or use without more accepted repairs | Locate the remaining selection/interpretation/patch failure; no repair-gain claim |
| No relevant contrast or no bound cases | Report the corresponding mechanism as unexercised; no automatic extra run |
| Partial allocation or uncertain infrastructure/billing | Preserve assigned-row denominators and unresolved outcomes; no positive comparative claim |

Complete the fixed order regardless of intermediate task grades unless an existing
hard stop fires. Known row budget exhaustion closes that row without transferring
its balance. Count/transport/billing uncertainty, invalid provenance, unexpected
wire differences or unconfirmed cleanup close the allocation with no retry or
replacement. Assessment ERROR or uncertain cleanup stops remaining assessments.
No automatic resumption, relaxed validator, new prompt or further paid allocation
follows a negative or inconclusive result.

## Required provider-free preparation before an execution freeze

1. Implement the diagnostic OFF adapter and judgment-record validator; pin them
   and the common repaired runtime. Keep future changes within the allowed seams;
   any required common runtime fix changes the binding and needs a fresh freeze.
2. Capture complete first requests and synthetic post-action, delta, handoff,
   recovery and finish inputs for both arms. B equals current runtime; A equals
   the specified control projection. Bind an exact field/path difference allowlist,
   not just hashes. Schemas, public task, plan/source/diff/check/probe/budget fields
   and limits match; only derived segment IDs follow the pinned derivation.
   Do not normalize clock/budget differences away; record deterministic captures
   and justify any actual preparation-time difference before dispatch.
3. Use a compact local fixture set: helper/suite success, current original failure
   despite dismissal, same-diff conflict, changed setup, stale-after-edit evidence,
   valid fixed replay, three-case overflow, and a verified positive finish.
   Exercise real local probe binding as well as fabricated receipts. Both arms
   retain validators, idempotency, submission eligibility and negative paths.
4. Validate the public rubric on fixed historical B2/B5 contrasts and a previously
   accepted public trajectory, with prior outcomes identified as known. Include
   source inference, no claim, unknown scope, rejected finish and setup error.
   Assert that wrong patch/receipt hashes and missing evidence fail validation.
   Historical semantic labels are calibration, not fresh accuracy evidence.
5. Reconstruct both projections over the saved 358 Astroid inputs and ten accepted
   task-1 inputs. Hash the inputs before/after; never invent declarations.
   Check the exact allowed state differences, actual serialized input bytes,
   recovered/missing source and probe bodies, and the two-reference bound.
   A projection replay cannot predict future actions, handoffs or token cost.
6. In prospective live inputs, inventory newly absent current source ranges,
   original caller/setup/countercondition evidence and probe programs at every
   decision and transition. Compare chronological inputs within each run.
   For matched saved prefixes also compare A/B projection. New runtime branches
   make cross-run displacement descriptive, not a paired eviction experiment.
   Actual token, cache, reasoning and cost effects wait for an authorized run.
7. Run focused adapter/grader checks under two minutes, Ruff, both-arm quick/mock
   checks and the full suite at the final implementation commit. Do not loosen
   old assertions or add skips. Keep the current baseline's **5,463 passed,
   20 skipped** at `5bd4c26c` distinct from the adapter's future validation.
   Baseline receipts: `C:/pt/regression-contract40/validation.json`.
8. Freeze a new external manifest with commit/tree/content hashes, this spec,
   all twelve resolved requests, order/caps, prompt/schema hashes, environment
   identities, caller/native inputs and grading code, full wire differences,
   replay/fixture/test receipts and annotation schema. Use a fresh state root
   and append-only hash-chained `dev-run-v1` journals outside the repository.
   Keep execution authorization false; exact human approval is a later record.

## Implemented preparation and execution interface

The diagnostic-only implementation is
[`verification_state_off.py`](../../diagnostics/verification_state_off.py),
[`verification_state_grading.py`](../../diagnostics/verification_state_grading.py),
[`verification_state_panel.py`](../../diagnostics/verification_state_panel.py) and
[`verification_state_execution.py`](../../diagnostics/verification_state_execution.py).
The product runtime remains byte-identical to the common repaired base.
The OFF adapter is process-local and restored after local use; spawned paid workers
receive the assigned initializer. A and B share the existing serial cost ledger,
due-receipt validation, caller grader and whole-patch native assessor.

The public grader validates dispatched-input/action/diff/receipt bindings and
literal evidence, requires every finish attempt and observable decision to be
reviewed, deduplicates action identities, and keeps semantic review explicit.
Awarding mechanism use requires an actionable contrast and a subsequent action
bound to the same request. It cannot prove semantic correctness from a valid
annotation. Three selected historical decisions calibrate discussion-only B2,
helper-to-task B5 and an accepted source-inference example; these are neither
fresh blinded predictions nor whole-row completion scores.

Current local evidence lives in `C:/pt/verification-state42/`; the earlier
specification-only receipt remains at `C:/pt/verification-state-spec41/`.
`validation.json` binds focused checks, Ruff, both quick selections, mock evaluation,
initial captures, 368 public input reconstructions, historical grading calibration
and the final-commit full suite. The full suite runs the product defaults and
includes the new A/B tests. A's additional quick selection covers 45 common
contract/state/cost/mock cases under the actual OFF initializer; B's quick
selection keeps the existing product expectations, plus the new comparison tests.
No existing assertion, test skip, timeout or budget is relaxed.

Initial requests may differ only in the system paragraph, reproduction review,
empty concern ID field name and verified derived segment IDs. The complete tool
schemas match. Saved-log reconstruction compares public bytes with encrypted
reasoning still redacted: it measures neither full billed input size nor token
cost and does not rerun the source selector or predict future transitions.
Historical input files remain immutable. The final replay and capture receipts,
rather than an earlier intermediate script, are bound by the manifest.

Use `python -m diagnostics.verification_state_panel validate --root
C:/pt/verification-state42 --hash <manifest-hash>` to recheck the frozen packet.
The separate `diagnostics.verification_state_execution` CLI supports `collect`,
`export`, `seal`, and `assess` with the same root/hash. `collect` additionally
requires exact new human authorization and a fresh official pricing review.
`export` masks arm codes; `seal` validates all twelve public annotations before
`assess` can open acceptance results. Preparation never creates an authorization.
