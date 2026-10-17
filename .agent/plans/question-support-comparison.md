# Evidence retention and judgment support: bounded repair comparison

Date: 2026-10-17. Revised proposal; paid execution is **NOT_AUTHORIZED**.
This replaces the unexecuted call-support A/B design, not any closed allocation.
Experiment-only ablations passed all four full suites and offline factor-isolation replay;
see the [validation record](../../docs/history/2026-10-17-repair-mechanism-isolation.md). The live execution manifest remains
**NOT_READY**. No old approval or unused allowance transfers.

## Question, evidence and scope

Do focused evidence retention (E) and explicit judgment support (J) improve actual
repairs, separately or together, within the same limits? Distinguish a missing body
at a handoff from an unsupported conclusion despite relevant delivered evidence.

The [saved-input audit](../../docs/history/2026-10-17-question-call-support.md)
restored caller conditions and local exclusions while displacing 59 line versions,
including nine useful indirect counterevidence lines. Its active references were
operator-authored: delivery improved in those inputs, not yet in autonomous solves.
The [plan comparison](../../docs/history/2026-10-16-plan-grounds.md) preserved reasons
and reviews but achieved 0/8 independent acceptances in each arm. The
[Astroid closure audit](../../docs/history/2026-10-16-astroid-plan-closure.md) found
unsupported closure despite available evidence; the later purpose-guidance arm was
[not executed](../../docs/history/2026-10-16-output-stop.md). These observations
motivate separate factors; they are not fresh controls or proof of either cause.

Alternatives: the solver may not declare usable references; recency may already
retain sufficient evidence; extra support may displace a necessary branch; explicit
labels/reasons may merely justify the same wrong patch. Even better judgments can
fail to produce a repair within four edits. Delivery, checks, longer notes, public
PASS and submission alone establish no repair gain.

## Four arms on one common implementation

Use base `168765b55b7d5c26cdfc7ce50c0d70cf729e39b8`, including the timeout-fixture
and settled-INCOMPLETE_RESPONSE batch fixes in every arm. Base runtime content hash:
`sha256:2f0d160691daa1df55f1a9a671b7ff09881b53932559380eae6fc8abac7684d9`.
Build isolated experiment-only ablations from that base; do not run old commits as
controls or change dev-head's default behavior. Arm labels are not runtime versions.

| Arm | Focused retention E | Judgment support J | Comparison role |
| --- | --- | --- | --- |
| E0J0 | Off | Off | Common-contract control |
| E1J0 | On | Off | Added retention with baseline judgment presentation |
| E0J1 | Off | On | Added judgment support with baseline retention |
| E1J1 | On | On | Current combined behavior |

### E: which already-observed evidence reaches the request

E1 uses the current atomic priority: mutation anchors/postimages, eligible current
countercheck, primary, observed immediate call-support bundle, then ordinary recency.
It also permits the existing bounded replay of question-cited check/test/probe
call/result bodies, subject to the current deterministic size fallback.

E0 uses the same observed candidate pool, native latest-result delivery, anchor
protection, line accounting, staleness and fallback rules. It passes no priority
references to `context.project_observed_sources` and adds no optional question-cited
exchanges via `evidence_focus.optional_exchanges`. Ordinary recency can still retain
the same evidence; evidence is not deliberately deleted to create failure.
Question binding, stored bodies, validation and the two-reference interface stay on.

Implementation seams: `dev/context.py`, projection callers in `dev/tools.py`, and
optional-exchange selection in `dev/runner.py`. Do not disable annotation binding,
mutation admission, recovery, native result delivery or actual count/cap guards.
Only the selection-specific help sentence in `DEV_SYSTEM_PROMPT` may differ with E:
E1 describes its priority; E0 states that references do not receive extra priority.
The request to cite minimal observed primary/countercheck units remains common.
This estimates the focused-retention package, not call support alone or the benefit
of merely introducing a reference schema.

### J: observations, interpretations and unfinished purposes

J1 keeps `evidence_focus.project_interpretations`: proposed remaining work,
`model_interpretation`, separate evidence currency/delivery and missing ranges,
`closed_by_model` / `dismissed_by_model`, and coverage `not_assessed`. It keeps current
plan/note guidance and purpose-preserving completion instructions: account for the
original input/path/outcome, distinguish execution from source inference, and do not
substitute an unrelated PASS or make verification conditional on failure.

J0 omits only that final interpretation projection from `dev/model_state.py`.
Use the earlier, still explicitly unverified note/concern view: `statement`,
`status`, existing `model_authored_unverified`, model-decision basis and warning that
current evidence is not proof of the prose. Keep the same source/result bodies.
Restore `working_plan.INSTRUCTIONS` and the completion paragraph from
`fcfa496dfb57f7e0d79616e5389fac034cfbc6b2` (before `5fbce0c` purpose guidance), not its
runtime. In the current notes paragraph, replace help for renamed J1-only fields
with their J0 equivalents; retain minimal-reference help and honest unverified-data
warnings. Freeze the exact resulting strings before any execution.

Shared in all arms: original concern/progress separation, concern persistence, plan
predecessor/revision-reason retention and validation, final diff-bound review,
annotation bounds, original check verdicts and current-diff finish requirements.
J never certifies an assertion or requires an extra check. This tests the incremental
presentation/purpose-guidance bundle; it does **not** re-estimate earlier plan-history
or concern-persistence contracts, or isolate individual sentences.

### Isolation contract

Freeze each arm's patch, source/import hash, rendered prompt and common schemas.
Verify factor instructions and required shared guidance in the rendered prompt, not
just source strings. Preserve the existing 8,000-character base prompt and 10,809-character
combined brief-v1 prompt as maximum comparison sizes; no truncation or added capacity.
E and J transformations must commute. E0J1/E1J1 share J rules; E1J0/E1J1 share the
evidence selector. On an identical saved public state, toggling J must leave source
line versions and tool call/result bodies equal before final size admission.
J may change metadata and request size; record resulting fallback/body loss as a
delivery-mediated interaction, not judgment-only evidence. E1J1 must match the base.
No task-ID/path special cases, forced references, new tools, historical-answer hints
or extra model calls are allowed.

## Fixed tasks, model and resources

Retain the previous proposal's three tasks; do not replace them after seeing exposure
or grades. Astroid supplies observed examples of both mechanisms; the other two test
public call/exception behavior and regressions, not known judgment failures.

| Index | Registered public input | Public selection reason |
| --- | --- | --- |
| 13 | `tasks/dev-train/current-dev20/13/public.yaml` (Astroid-1333) | Directory/file dispatch evidence loss and separately observed unsupported purpose closure. |
| 1 | `tasks/dev-train/current-dev20/1/public.yaml` (Marshmallow-1343) | Nested deserialization/validator chain; missing data and error propagation. |
| 9 | `tasks/dev-train/current-dev20/9/public.yaml` (Pydicom-1694) | Lookup/value-conversion traceback; caller scope of exception suppression. |

All are development-exposed. Historical FAIL/PASS/PASS discloses selection only;
historical runs are not pooled into fresh denominators. No private spec, hidden test,
reference patch or evaluator detail informs task annotations or solver context.
Private assets may be hashed opaquely and used only by isolated evaluation.

- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens,
  standard/global Responses, `store=false`, zero SDK retries. This preserves the
  saved panel's model, not a change to the general baseline model.
- Later credential path: `C:/Users/geonj/Documents/PatchLoop/.env`; preparation
  does not read its contents. No availability or token-count API call is permitted.
- Preserve `segmented-v1`, `result-or-size-v1`, `brief-v1`, current agent policy,
  probes enabled, probe-policy/recheck none, repair-recheck true, protected-v1
  inspection and per-call-v1 cost admission, except the two specified ablations.
- Keep at most **two** question references, one primary and one countercheck, and
  existing validity, expiry, rebinding and diff-scope rules. Fresh solves receive no
  operator question, note, plan, citation, patch, saved conversation or continuation.
- Retained source **24,000 characters**, counted input **60,000 tokens**, request
  **1,048,576 bytes**, encrypted item **262,144 bytes**. The existing base instruction
  is **8,000 characters**; brief-v1 appends 2,807 plus two separators, totaling **10,809**.
  The previous wording incorrectly called 8,000 the whole system-prompt ceiling;
  runtime has no such truncation. Preserve these existing sizes as comparison maxima,
  and all note/schema bounds and request admission limits unchanged.
- Per row: **40 model calls, 100 actions, four accepted edits, 1,800 seconds**,
  including the **330-second** registered-evaluation reserve. Counters do not reset.
  Transition algorithm/thresholds are identical; realized size transitions can differ
  with content and must be reported, not forced to the same action index.
- **3 tasks x 4 arms x 1 repetition = 12 fresh solves**; each resolved request has
  `repeat=1`, a unique state root and **USD 0.88**. Total invocation cap stays
  **USD 10.56**: USD 2.64 per arm, USD 3.52 per task. No transfers, replacements,
  retries, resume, continuation, paid judges or automatic expansion.
- The previous A/B's two repeats per cell become one to fund factor separation.
  There is no within-cell variance estimate, seed matching, statistical significance
  or generalization claim. Low exposure does not authorize additional repetitions.
- Registered pricing carried from the 2026-10-17 packet: USD 0.75 uncached input,
  USD 0.075 cached input, USD 4.50 output per million tokens. This revision does not
  recheck prices. Reserve uncached cost immediately before dispatch; settle usage
  and record output-ceiling reductions. A 60k-input/25k-output call reserves USD
  0.1575; USD 0.88 does not guarantee 40 maximum-size calls. Revalidate rates before
  later approved dispatch; a mismatch needs a revised frozen packet.
- Keep the same prepared source/dependency descriptors and pinned images, verified
  anew before execution. Registered and native grading stay separate; native host
  allowance 600 seconds and test timeout 300 seconds. No image pull/build, dependency
  resolution or task registration is included.

Use this fixed order, reading each round left to right. Each cell is one settled,
single-row wave of the existing scheduler with its arm's own interpreter. This
interleaves arms without importing multiple arms into one process. The existing
two-worker ceiling is preserved but these waves use one worker; no launcher extension
is required. Order varies by task but cannot remove time effects or stochastic noise.

| Round | First: task 13 | Second: task 1 | Third: task 9 |
| --- | --- | --- | --- |
| 1 | E0J0 | E1J0 | E0J1 |
| 2 | E1J0 | E0J1 | E1J1 |
| 3 | E0J1 | E1J1 | E0J0 |
| 4 | E1J1 | E0J0 | E1J0 |

## Public-only mechanism audit

Freeze the rubric before dispatch. Seal public annotations before unblinding final
acceptance grades; record unavoidable grade exposure. Arm blinding is not claimed.
Keep an operator-only ledger linked to journal/request hash and event sequence;
never send that ledger or evaluator output to the solver. No paid judging is included.

For every material public question/purpose, record original input/path/outcome,
supporting observations, competing branch/counterevidence, versions, actual delivery,
explicit claim/disposition, next action, candidate diff and remaining call/edit/time
budget. Include requirements omitted from plans; no concern/question is not proof
of correct judgment.

1. **Opportunity and exposure.** Count transitions, autonomous references, eligibility,
   priority/support admission and actual request changes. Distinguish NO_TRANSITION,
   NO_DECLARATION, INELIGIBLE, ALREADY_RETAINED, BUDGET_REJECTED and DELIVERED_CHANGE.
   J instruction exposure alone is not an eligible decision: identify an interpretation,
   purpose closure or finish judgment with relevant evidence. Report denominators.
2. **Retention and displacement.** Replay E0/E1 on identical saved public state,
   references, diff, native results and observed text without new reads/provider calls.
   Audit both J presentations for size effects. Inventory every gained/lost
   `(path, file_hash, line)` and result `(action_id, input_hash, diff_hash)` with text,
   roles and omissions. Judge minimum sufficient evidence by public conditions and
   branches, not line totals or citation completeness. Label direct support,
   countercheck, caller gate, indirect counterevidence, mutation anchor, unrelated and
   uncertain; allow mixed roles. Include uncited and newly displaced evidence.
   Separate original output truncation from delivery.
   A loss claim requires a material unit in an actual earlier request and absent
   after the handoff. Distinguish NOT_ACQUIRED (never observed), STALE_AFTER_EDIT,
   LOST_AT_HANDOFF, PRESENT and UNCERTAIN; failed acquisition is not retention loss.
3. **Judgment and subsequent action.** Reconstruct the complete actual request just
   before the decision across all delivery routes. Journal presence, a citation or an
   earlier segment does not prove current delivery. Classify executed support
   (matching input/assertion/result/current diff), explicit supported source inference,
   acknowledged open gap, unsupported closure, or UNASSESSABLE. An unrelated PASS,
   silently dropped purpose, conditional weakening, or explicit assertion contradicted
   by supplied source is unsupported. Do not infer hidden beliefs from silence or
   inspect/decrypt raw reasoning.
4. **Behavior and repair.** Link evidence to revised public claims, discriminating
   checks, re-reads, accepted corrective edits and submitted diff. Record whether the
   relevant code changed after the observation; repeated checks or accurate caveats
   with the same wrong patch are not repairs. Source inference may justify finishing
   without another check; there is no check quota.

Use independent labels, not one inferred root-cause bucket. A row can have both loss
and unsupported judgment at different decisions. At one decision, a missing material
unit makes evidence-adequate judgment NOT_ASSESSABLE; do not assign that failure to J.
With complete relevant support/counterevidence in the request, an unsupported public
conclusion is an evidence-present judgment failure. Complete citations alone do not
establish sufficiency. Preserve reviewer uncertainty and mismatched task scope.
Even confirmed loss plus a later failure is an association; the fresh arm contrasts,
not the chronological coincidence, supply the repair-outcome comparison.

Historical replay establishes selection differences only. Its operator-authored active
references cannot demonstrate autonomous use or counterfactual repair success.
Same-state replay of a new trajectory is also an input diagnostic, not an unexecuted
solve outcome. Exposed post-treatment subsets are not the primary causal comparison.

## Primary repair outcome and conditional comparisons

Retain all 12 intended rows, including stopped/unsubmitted ones. Record separately:
submission, required public checks, registered acceptance, native acceptance/agreement,
safety, infrastructure/cleanup, settled cost/time and exhausted limits. Acceptance FAIL,
ERROR and NOT_RUN stay distinct; public PASS is not correctness.

Report accepted repairs per task/arm out of **one intended row**, and per-arm totals
out of **three**. Let `S_ej` count registered/native agreeing PASS results in that arm.
This counts accepted repairs, not graded failures inferred from unsubmitted rows.
Keep ERROR/NOT_RUN visible; never drop, replace or label them acceptance FAIL.

| Prespecified contrast | What it can distinguish |
| --- | --- |
| `S_10 - S_00` and `S_11 - S_01` | Retention contribution with J off and on |
| `S_01 - S_00` and `S_11 - S_10` | Judgment-support contribution with E off and on |
| `(S_11 - S_01) - (S_10 - S_00)` | Descriptive interaction: dependence on the other factor |
| `S_11 - S_00` | Combined outcome only; cannot assign a gain to either factor |

Report all cells, task-level contrasts and unfavorable results. A favorable
**conditional pilot signal** requires eligible exposure of that factor, more accepted
repairs in its on arm, no per-task acceptance decrease, complete agreeing grades for
submitted patches, settled accounting, and no infrastructure/missing-assessment
uncertainty in the contrasted rows. Known local resource stops remain non-successes
for bounded repair throughput and are separate from graded FAIL; the mechanism can
still be unassessable.

A factor-wide signal additionally requires no aggregate/task regression in its other
conditional contrast. A zero/unexposed contrast is not independent confirmation.
Opposite signs are an interaction/tradeoff, not one main-effect gain. Three one-shot
tasks cannot establish an individual repair's cause or a statistically reliable effect;
traces provide only a mechanism-consistent account.

| Observed chain | Allowed conclusion |
| --- | --- |
| Better delivery, same acceptance | Retention worked; repair gain not demonstrated |
| Fewer unsupported closures, same acceptance | Judgment changed; repair gain not demonstrated |
| More acceptances without exposure/traceable mechanism | Outcome signal; intended explanation unresolved |
| E1J0 gains; J adds no gain | Retention signal in this panel; no added J quality signal |
| E0J1 gains with adequate delivered evidence | Judgment-support signal under baseline retention |
| Only E1J1 gains with both mechanisms exposed | Possible complementarity; neither alone shown sufficient |
| Useful counterevidence displaced and task acceptance drops | Selection tradeoff/regression despite more cited lines |
| No opportunity, ambiguous sufficiency or missing assessment | Corresponding mechanism/quality question unresolved |

Close after the fixed rows. No automatic adoption, rollback, exposed-case tuning,
extra repetitions or follow-up spending follows any result.

## Freeze, validation and stops

New preparation record: `C:/pt/analyses/repair-mechanisms-spec-20261017-v1`.
Reserved, uncreated live root: `C:/pt/repairmechanisms17live01`.
The old `C:/pt/analyses/question-support-experiment-20261017-v1` packet, its
`qcscompare17live01` reservation and readiness/failure receipts remain immutable;
they neither authorize nor describe this four-arm experiment.

The [offline builder](../../diagnostics/repair_mechanisms.py) applies three experiment-only
patches to clean separate checkouts; it cannot patch the calling product checkout or
dispatch a solver. [Replay](../../diagnostics/repair_mechanisms_replay.py) uses frozen
public snapshots, actual source-selection/presentation code and the runner's pure
optional-exchange selection expression. It does not replay provider continuation or
exact token admission; the fake-provider recovery tests cover count/fallback/commit.
Before live readiness, freeze exact strings, factor patch hashes and source/import identities;
bind all 12 resolved requests, descriptors/images, common schemas, transition/limit
hashes, registered prices, native harness, rubric and protocol hash. Hash private
assets opaquely. Check actual effective fields, not just CLI arguments.

Provider-free gates and remaining live prerequisites:

- Same-state public fixtures must prove E/J isolation, E1J1/base parity, unchanged
  transition algorithm/thresholds, two-reference bounds and every admission limit.
  Cover no-focus, stale/oversized refs, native overlap, result truncation, displaced
  counterevidence and J-induced size fallback. Preserve failed receipts.
- Each exact arm must pass relevant regression tests and Ruff, the full suite, and
  mock isolated evaluation, with source bytes frozen before/after. Expected ablation
  differences must be explicit; no blanket skips or weakened production expectations.
  Verify that each interpreter imports only its pinned arm.
- Fresh public import/operation/selected-test canaries and image identities remain
  required. Missing prerequisites are NOT_RUN/BLOCKED, never PASS.
- The base's exact-commit 5,215-pass / 19-skip receipt at
  `C:/pt/analyses/batch-stop-fix-20261017-v1` establishes the common fix only; it does
  not substitute for arm validation. All four committed arms now have separate
  5,225-pass / 19-skip receipts; the 10 added tests cover isolation and fixed caps.

Arm validation and replay isolation passed in
`C:/pt/analyses/repair-mechanisms-20261017-v1`; final arm identities, complete
displacement inventories and size interactions are recorded there. Fresh environment
canaries and a resolved execution manifest remain NOT_RUN. No repair-quality experiment ran.
Preparation provides no dispatch entry point. A later execution request must approve
the exact new packet, tasks, model, credential, repeats and USD 10.56 cap; no
availability/count/model call is allowed before that authorization.

Stop all pending admissions on source/request drift, private-context exposure,
changed limits/transitions, missing mandatory evidence, count/transport/billing
uncertainty, unconfirmed cleanup or grader disagreement. Already admitted work must
settle with usage preserved. The common fixed scheduler keeps known row caps and
fully accounted, cleanup-confirmed INCOMPLETE_RESPONSE local; the latter is unsubmitted
with acceptance NOT_RUN, never a repair PASS. Ordinary acceptance FAIL does not stop
other rows or trigger retry. Every run is `official=false`, `claim_eligible=false`;
cross-run memory, held-out tuning and claim execution remain disabled.
