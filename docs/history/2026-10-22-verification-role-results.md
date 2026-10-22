# Verification role comparison: scope gaps survived correct feedback delivery

## Decision

The six-row allocation is closed. Independent verification did not improve the
measured completion judgments or repairs in this comparison. A submitted two
patches; B submitted three. All five failed both the original missing-initializer
caller assessment and native acceptance, while all init-present controls passed.
A1 exhausted cost admission without submitting and remains behaviorally unassessed.

Public judgments were sealed before fresh private grades were opened. Final
unsupported-completion counts were A **2/3 assigned, 2/2 assessable claims** and B
**3/3 assigned, 3/3 assessable claims**. Accepted repairs were **0/3 each**.
A's lower assigned error count reflects a missing claim/submission, not improved
judgment. The exploratory adoption criterion failed; do not adopt independent
verification or extend this allocation on these results.

The question was selected because prior agents repeatedly substituted helper or
regression success for the original caller requirement. A separate context could
challenge that substitution. Instead, both roles described the missing original
verification, and the final repair decisions still treated it as optional.
This weakens context separation alone as the remedy under these conditions. It
does not establish that multiple agents never help, or isolate model capability
from the shared instructions, evidence selection and verification procedure.

## Frozen execution and reconciliation

- [Specification](../../.agent/plans/verification-role-comparison.md): A is a
  mandatory verification phase in the repair context; B is an independent context
  using the same model, tools and bounded public packet. Both share one total
  budget. This does not compare mandatory verification against no verification.
- Frozen implementation HEAD: `4714399314fd3397069f3e429f5abbfa68506f0a`.
  Runtime: `sha256:08f48f832e57bd30440a0d82707e6e396ea697f363fa30466c149047d2f862ac`.
- Manifest: `sha256:e38cac4f947585f337f93bb8c5da75b2a4e0f41c1f8e251ba2785b2831a824c6`.
  Packet `C:/pt/verification-role51`; run state `C:/pt/verification-role51-live`.
- Task `tasks/dev-train/current-dev20/13/public.yaml`, dev-train Astroid-1333;
  `gpt-5.4-mini-2026-03-17`, xhigh, project `.env`. Exact new approval is recorded
  separately in `authorization.json`; the immutable preparation's
  `paid_authorized=false` was not rewritten.
- A1 B1 B2 A2 A3 B3 ran serially, three per arm, with USD 0.88/row,
  2.64/arm and **5.28 total**. All six settled; no unknown bills, allocation stop,
  paid retry, replacement, extension or additional condition.
- Actual new cost **USD 3.19329735**: A 1.65112800, B 1.54216935.
  Prior allocations and bills remain separate. Provider prices matched the
  [official standard rates](https://developers.openai.com/api/docs/pricing)
  checked on 2026-10-22: input/cached/output USD 0.75/0.075/4.50 per million.
- Segmented-v1, result-or-size-v1, brief-v1, two reference slots, 24k retained
  source characters, 60k counted input tokens, 1 MiB requests, 40 model calls,
  100 actions, four edits and 1,800 seconds per row were unchanged. Phase envelopes
  remained initial 28 calls/60 actions/3 edits/USD 0.48, verify 6/20/0/0.20,
  final 6/20/1/0.20 with only unused earlier resources carried into final repair.
- The frozen implementation had **5,541 passed, 20 skipped, zero failed** at its
  final commit, with the skip set preserved. Post-execution packet validation
  passed at the same HEAD before this documentation-only result commit.

The public audit is `annotations.json`, with quote/input/diff/receipt identities
validated in `public-audit-validation.json`. `audit-public/` contains masked public
events; stream layout can still reveal treatment, so this is not fully blind.
`result.json` joins the sealed audit to separate local outcomes. Ten caller checks
and five native evaluations completed within the approved 12/6 ceilings, without
assessment ERROR, retry or acceptance disagreement. Caller checks used the source
projection; native assessment used each exact full submitted patch, including any
submitted tests. No assessment result was returned to an agent for more repair.

All runs are official=false and claim-ineligible. Generated evidence and journals
remain external. Earlier histories, the frozen specification and runtime were not
edited. The existing user change to `AGENTS.md` was preserved.

## Judgment and actual repair

| Row | Termination | Public final judgment | Missing-init caller | Init-present control | Native | New USD |
| --- | --- | --- | --- | --- | --- | ---: |
| A1 | COST_CAP_REACHED, no submission | NO_CLAIM | NOT_RUN | NOT_RUN | NOT_RUN | 0.85779060 |
| B1 | EVALUATOR_FAIL | UNSUPPORTED | FAIL | PASS | FAIL | 0.83882190 |
| B2 | EVALUATOR_FAIL | UNSUPPORTED | FAIL | PASS | FAIL | 0.43039665 |
| A2 | EVALUATOR_FAIL | UNSUPPORTED | FAIL | PASS | FAIL | 0.39989220 |
| A3 | EVALUATOR_FAIL | UNSUPPORTED | FAIL | PASS | FAIL | 0.39344520 |
| B3 | EVALUATOR_FAIL | UNSUPPORTED | FAIL | PASS | FAIL | 0.27295080 |

All five assessed missing-init cases retained F0010 and did not analyze the child
file; all present-init controls analyzed it. Native FAIL agreed with the registered
isolated acceptance receipt in every submitted row. The agent-visible regression
checks passed in all six rows; those checks are distinct from native acceptance.

J_any equals J_final here: A 2, B 3. A1's final plan said completion would follow
if the pending check passed; there was no later model decision or submission.
That conditional plan was not counted as an actual completed-task assertion.
Unsubmitted A1 was not scored as an observed repair failure or a correct abstention.
`outcomes_complete=true` includes its known unassessed termination;
`favorable_local_signal=false`.

The five claims were UNSUPPORTED rather than CONTRADICTED: current helper/suite
results and plausible edits did not establish the actual Pylint call-to-branch
connection. B1's original-path failure preceded its edit, so it was historical
counterevidence requiring a rerun, not a current-patch refutation. The later
independent FAIL results did not determine or retroactively change these labels.
Source inference is allowed by the rubric; these traces lacked the concrete
caller, arguments/setup and countercondition mapping needed to support it.

Verifier reports correctly distinguished observed scope from original-call
certainty: five uncertain reports and one report of B1's still-failing baseline.
V_wrong is zero for this public scope review. This credits their explicit gap
detection, not their speculative repair diagnoses. Several reports described
original verification as a check to do only if more certainty were needed; A3
also hedged that no further fix appeared necessary. Such permissive framing is
not evidence that the candidate is correct or that verification was strong.

## Acquisition, feedback and application

All six reached verification; two per arm had a candidate at entry. Every report
was delivered in full in every final-phase request. No row obtained the Pylint
caller source, no verifier ran an original-caller probe, and no row reran Pylint
after its patch. None acquired a complete before/after original caller plus
present-initializer control pair during agent execution.

| Row | New actions inside verification, excluding report | Subsequent repair behavior |
| --- | --- | --- |
| A1 | One source read; no candidate | More source inspection, helper edit/test, suite PASS; cost admission then prevents submission |
| A2 | None | Immediately submits the source normalization edit despite the exact-caller gap |
| A3 | None | Immediately submits importlib namespace edit and helper test despite the gap |
| B1 | One source read and baseline regression check; no candidate | Makes modutils namespace edit and helper test; suite PASS, no Pylint rerun |
| B2 | None | Adds a declared original-requirement probe that actually executes helpers; then submits |
| B3 | One focused modutils test run | Immediately submits directory callback edit despite the gap |

The public evidence supports three distinct limits:

1. **Acquisition/selection:** B1 alone invoked `pylint.lint.Run` before editing
   (public decision 333, receipt 337), observing the reported F0010. It used an
   absolute directory argument rather than changing to the issue's project root
   and did not run the init-present control. Other probes tested Astroid helpers.
   Merely restating the public issue's command did not supply the caller connection.
2. **Delivery:** B1's report at 395 contrasted that failure with the passing
   baseline suite. Its complete text reached the repair stage. All other reports'
   original-path caveats also survived. Complete feedback loss therefore does not
   explain the final five claims, although some source bodies were displaced.
3. **Application/interpretation:** B2 responded to report 313 with probe 332,
   declaring `entrypoint=pylint.lint.Run`. The actual program only invoked
   `modpath_from_file` and `AstroidManager.ast_from_module_name` after adding both
   `src` and its parent to `sys.path`. It never called Pylint. Receipt 337 reported
   successful helper results; finish 349 claimed the same original failure was
   addressed even while the host retained unverified requirement mapping.

B2 is credited with observable, partial response to current feedback, not faithful
original-requirement closure or a proven causal effect of independence. Its repair
failed. B1's later patch overlaps its pre-verification plan at decision 319, so a
matching recommendation alone does not establish new report-induced repair.
A2, A3 and B3 dismissed the disclosed gap without a new applicable observation.

Thus this run demonstrates a delivered warning followed by unsupported completion,
and, in B2, interface use followed by a wrong scope inference. It does not support
the explanation that the main remaining problem is simply missing report context.

## Retained and displaced material

`public-delivery-inventory.json` records actual boundary inputs and exchange IDs;
`public-displacement-detail.json` records file/version/range differences. Counts
below are versioned source-line identities, not counts of necessary facts. Lines
from an older file version can disappear while the same text remains elsewhere
in the current file. Live rows are not matched stochastic seeds or same-snapshot
A/B eviction comparisons.

| Row | Source identities before -> after verification entry | Lost identities | Of those, same file/text still present | Source identities lost on return |
| --- | ---: | ---: | ---: | ---: |
| A1 | 870 -> 870 | 0 | 0 | 0 |
| B1 | 930 -> 659 | 271 | 48 | 0 |
| B2 | 1202 -> 665 | 537 | 398 | 0 |
| A2 | 1022 -> 679 | 343 | 20 | 0 |
| A3 | 897 -> 645 | 252 | 58 | 0 |
| B3 | 701 -> 510 | 191 | 190 | 0 |

B1 entry lost builder 80-152 and modutils 347-520 among other spans; the verifier
read modutils again. Return restored 96 source identities and the earlier Pylint
probe, while its new read/check exchanges were not retained as raw exchanges.
Their report summaries survived. B2 lost old modutils and builder spans, much of
the former also present as current text. A2 lost builder 1-248 and test 116-210;
A3 lost parts of manager file fallback and modutils resolution. Such internal
branches can matter to diagnosis, but their eviction's effect is not isolated by
these divergent live trajectories. B3's 191 lost identities were almost entirely
old-version text still present in its current modutils view.

On return, B3's focused-test raw exchange and A3's base-check raw exchange dropped
out, while their results remained in the reports. No source identities were lost
at the measured return boundaries. B report reference counts were B1 2, B2 2,
B3 0; A counts were A1 0, A2 2, A3 0. No report selected a new verifier probe
receipt, so the locally tested two-new-probe return path was not exercised live.
Missing external caller source was never acquired; it was not removed at handoff.

## Resources and remaining uncertainty

`resource-analysis.json` reconciles all receipts: **149 generation calls,
160 input counts, 166 executed actions**, 5,605,103 input tokens including
3,588,608 cached tokens, and 313,729 output tokens including 266,865 reasoning
tokens. Reasoning tokens are counted once within output cost; no reasoning
content was inspected. Summed active row time was 2,605.653 seconds (43m26s),
excluding operator audit and separate local assessments.

| Row | Model calls initial / verify / final | USD initial / verify / final |
| --- | --- | --- |
| A1 | 26 / 2 / 8 | 0.46348950 / 0.08923920 / 0.30506190 |
| B1 | 23 / 3 / 6 | 0.46341045 / 0.11942790 / 0.25598355 |
| B2 | 20 / 1 / 2 | 0.36490995 / 0.01545435 / 0.05003235 |
| A2 | 18 / 1 / 1 | 0.36737505 / 0.01585860 / 0.01665855 |
| A3 | 17 / 1 / 1 | 0.34458030 / 0.03233835 / 0.01652655 |
| B3 | 16 / 2 / 1 | 0.21824730 / 0.03145695 / 0.02324655 |

A1 and B1 reached the initial cost envelope without an edit; their verifier
reviewed the baseline. A1 later reached total cost admission after a passing
helper regression. Final calls above the nominal six in A1 used unused earlier
allowance within the same total cap. This is a real repair-opportunity cost to
report, but the experiment does not isolate the alternative unsplit trajectory.

No verification phase exhausted its envelope. A2, A3 and B2 reported immediately
with the full six-call, USD 0.20 verification allowance still available; probes
were offered in all verification inputs. B3 chose a helper test, and B1 reran the
baseline suite. Nonselection of original-caller verification therefore cannot be
explained solely by an unavailable probe tool or exhausted verifier resources.
Available allowance does not guarantee a successful reproduction or useful output.

Fourteen requests had reduced output ceilings. One B1 initial response exhausted
its 3,460-token output allowance using reasoning tokens and returned no tool call;
usage was known and settled. This is an output-limit event, not a transport or
billing uncertainty. No retry or replenishment was added. Maximum dispatched
input was 59,912 tokens. The 32 recorded segment starts comprise nine initial
starts (six repair streams plus three independent verifier streams), eight size
transitions and fifteen ordinary result transitions; no new forced repair
transition was introduced.

The next unresolved question is whether verification can execute and compare the
actual public caller/arguments/setup on the candidate, rather than accepting a
declared entrypoint or helper result as coverage. A small follow-up should test
that connection and its application before spending on more independent roles.
No such implementation or paid follow-up is authorized by this report. Three
repetitions per arm on this repeatedly exposed development task cannot support
statistical superiority, general repair accuracy or universal architecture claims.
