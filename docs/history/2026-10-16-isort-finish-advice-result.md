# isort I4: unchanged submission after finish-advice removal

Date: 2026-10-16, Asia/Seoul. One authorized I4 invocation completed,
official=false and claim-ineligible. The specified advice removal reached the
model, but its first response submitted the unchanged seed. U and public repair
failed; the isolated evaluator returned `EVALUATOR_FAIL`; safety passed.
Removing this recommendation was insufficient in this sample. Keep the baseline;
the allocation is closed with no wording change, replacement or follow-up run.

## Question, authorization and preserved conditions

The [I2/I3 input audit](2026-10-15-isort-first-response-audit.md) found different
first decisions under inputs differing only in displayed remaining time. That
left completion advice, inherited planning and response variation as plausible
influences. The [frozen I4 design](2026-10-15-isort-finish-advice-design.md) tested
one subtraction: remove the latest ready-state `finish_task` suggestion and its
matching message clause. The [bridge](2026-10-15-isort-finish-advice-bridge.md)
had passed its provider-free validation before this authorization.

The user approved exactly one execution of
`C:/pt/isortfinishready01/manifest.json`, hash
`sha256:0f436c49588fd821b867fe50f7773681fb680e98e1b903218a05fc04a6c1e381`.
The launch used commit `c8c6510ece8553598dd41fd70a1daae63b8f8327`,
`original-isort-2491` in dev-train, the original checkpoint through event 338,
`gpt-5.4-2026-03-05`, xhigh reasoning, default tier, fixed 25,000 output tokens,
and the bound repository `.env` credential path. The immutable preparation
manifest still says `paid_authorized=false`; new authorization is recorded in
separate launch and invocation journals.

Plans, diagnostic data, I3 retention, native continuation, system instructions,
tool availability, submission eligibility, source/mutation scope and assessments
remained fixed. No private result entered the solver. I3 was read as a historical
comparison, not executed again. Runtime and diagnostic implementation hashes
match the approved manifest; the unrelated user change to `AGENTS.md` is intact.

Before dispatch, the fetched [official pricing page](https://developers.openai.com/api/docs/pricing)
confirmed standard short-context input/cached-input/output prices of USD
2.50/0.25/15.00 per million tokens. The
[model page](https://developers.openai.com/api/docs/models/gpt-5.4) confirmed the
snapshot and xhigh support. Read-only task/source/image/dependency readiness
passed, then one metadata request confirmed access to the exact model. The
collector used the fixed global endpoint, zero SDK retries, and no automatic
Docker start, image pull or build.

## Actual delivered input and response

Event numbers refer to the I4 row after inherited event 338. The first request
was prepared at **344**, counted at **346/347** and dispatched at **350/351**.
It had 53,268 input tokens and request hash
`sha256:4d58699283f282a70950f1cc9a4ef12f02d6d6ddfa2b912587aad391e4293ad5`.
The normalized frozen-preview comparison passed at **352**.

A separate read-only comparison of the actual I3 and I4 requests found exactly
three changed fields in the latest `harness_current_state`:

- `completion_guidance.next_action`: `{"tool":"finish_task"}` became `null`.
- `completion_guidance.message`: the exact recommendation clause was removed.
- `remaining_budget.active_wall_time_seconds`: 267 became 268.

All other request content, including native/opaque history, the inherited plan,
the complete four-case diagnostic, system text and tools, matched. Real deadlines
were enforced; displayed time was not forced to the historical value. The
recommendation was therefore removed as designed, with only the allowed clock
difference. No second request existed on which to exercise later delivery.

At **353/354**, the model returned `finish_task`. It cited the inherited
`base-regression` PASS, the repaired original `type_opening` case and preserved
`plain_item` case. Unlike I3's public explanation, it explicitly acknowledged
that `type_item` moves an existing item comment to the opening line. It then
called that a derived, untested control whose placement was not established as
a requirement by the public task or visible checks. The plan update at **356**
said no further publicly supported repair remained. Finish succeeded at **358**;
**362** recorded the unchanged seed patch:
`sha256:6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.

The packet actually contained executed observations with checked settings;
calling this control untested does not match that execution evidence. The
separate question of whether a derived control expresses a task requirement
remained part of the model's public scope judgment. Its response did not address
the other contrary row, `plain_opening`. These are observable explanation and
action differences, not access to encrypted reasoning or proof of attention to
every input. No new read, probe, source edit or regression check occurred.

## Grades sealed before final assessments

The public-only review was recorded at **364** with
`terminal_assessments_present=false`. U used public events **354, 356, 357, 358,
362**. Advice/delivery/first-action grades were sealed at **365**, U at **366**,
and C/R at **367**, before the terminal public oracle at **368** and isolated
evaluation completion at **369**. No grade was changed after seeing a verdict.

U is FAIL under the unchanged clause that submitting the unchanged seed as
sufficient is failure. Acknowledging a counterexample does not establish the
required evidence-to-hypothesis-revision-to-accepted-edit link. This is an
affirmative submission judgment, not a failure inferred from silence or cutoff.

| Measure | Historical I3 | I4 |
| --- | --- | --- |
| Advice removal A | Not an I3 treatment | PASS |
| Diagnostic delivery D | PASS | PASS |
| First executed decision | Immediate unchanged submission | Immediate unchanged submission |
| U: evidence-linked revision and edit | FAIL | FAIL |
| C: qualifying later-context exposure | NOT_EXERCISED | NOT_EXERCISED |
| R: fewer same-case probes plus a new edit | NOT_OBSERVABLE | NOT_OBSERVABLE |
| New accepted edits / model probes | 0 / 0 | 0 / 0 |
| Public final repair P | FAIL | FAIL |
| Isolated acceptance I | FAIL | FAIL |
| Safety | PASS | PASS |
| Generations / input counts | 1 / 1 | 1 / 1 |
| Known usage cost, USD | 0.2108375 | 0.177165 |

Zero probes without a new edit cannot satisfy R. The original
`D/C/R/U/P/I/safety` conjunction also remains unsuccessful for both rows; making
C/R secondary in I4 does not upgrade the old I3 result. The I4 primary
`A/D/U/P/I/safety` target failed despite valid treatment exposure.

The single terminal public program completed with correct settings and confirmed
cleanup; exit zero did not imply behavioral success. Comment text/count and
import AST were preserved, but two positions failed, exactly as in I3:

| Case | Expected position | Final position | Result |
| --- | --- | --- | --- |
| `type_opening` | opening | opening | PASS; exact original output preserved |
| `type_item` | item | opening | FAIL |
| `plain_opening` | opening | item | FAIL |
| `plain_item` | item | item | PASS |

P also lacked a new accepted source change and a fresh final-diff regression
execution. The inherited regression PASS still permitted submission. The one
existing isolated evaluation independently returned acceptance FAIL and safety
PASS. Neither assessment was reinjected into model context.

## Resource and boundary audit

All values below are new-invocation usage, excluding inherited work.

| Resource | Used | Fixed ceiling |
| --- | --- | --- |
| Known provider usage cost | USD 0.177165 | USD 3.50 |
| Generation / input count / metadata | 1 / 1 / 1 | 6 / 6 / 1 |
| Solver tool actions / accepted edits | 1 / 0 | 18 / 2 |
| Solver through last batch, including preparation | 66.832 s | 281 s |
| Approval event to invocation close | 145.180 s | 720 s total |
| Terminal public oracle | 1; receipt duration 2.689 s | 1; 30 s phase |
| Isolated evaluation | 1; finished 7.137 s after oracle record | 1; 330 s phase |

The public review occupied 69.324 s inside the total deadline. Input usage was
53,268 tokens, cached input zero, output 2,933 including 2,677 reasoning tokens.
Input counting matched actual usage. The admission reservation was USD 0.508170;
it is not the consumed amount. The USD 0.177165 figure is settled usage multiplied
by verified rates, not an observed invoice. No unresolved count, transport,
billing or cleanup uncertainty remained. Lower cost than I3 is not an efficiency
gain claim: both made one unsuccessful submission, with different output lengths.

Retries, response retrieval, resume, paid compaction/judges, protocol correction,
seed-diagnostic reruns, extra samples and new control rows remained zero. The
solver finished voluntarily with resource headroom. Its cumulative terminal
counters include inherited work and must not be reported as I4 consumption.

## Decision and evidence limits

Keep the default structure and completion guidance. This single subtraction
did not produce hypothesis revision or a correct final repair. It weakens the
explanation that the removed latest-state recommendation was necessary for this
unchanged submission; it does not prove that advice never affects behavior or
that the entire architecture is correct. Historical n=1 comparison cannot
separate response variation, inherited-plan influence and remaining completion
language into causal effects.

The sharper observed bottleneck is requirement scope in the final decision:
I4 acknowledges a contrary observation but treats it as insufficiently relevant
to justify another edit. The inherited plan and other completion instructions
were deliberately held fixed, so their effects remain unresolved. This is not
grounds to launch another adjacent prompt experiment automatically. The current
allocation is closed, no runtime change is adopted, and no additional execution
is queued. Future work needs a separately justified question grounded in this
evidence rather than unused budget.

## Evidence and verification

- Launch approval/prices/script: `C:/pt/isortfinishlaunch01`, journal
  `runs/run_dev_isortfinishlaunch.jsonl`.
- Invocation: `C:/pt/isortfinishlive01/result.json`; full result artifact
  `sha256:afe9e1a59794c5385c5563f3a6739fe12a2a656e1241d27537e5a73e1ffb91e1`.
- Row: `C:/pt/isortfinishlive01/I4/runs/run_dev_49397fa9568d4b80.jsonl`.
- Pre-assessment review:
  `sha256:3ecf03bd79792cdafdd7d14b19bd813c4515e746b376423b38cbc8aa34be0a53`;
  `public-grade.json` hash
  `sha256:36af66a120f50007335009d0cd42bf6f7ed813b194a7f8a95d8949e06475f232`.
- Read-only audit: `C:/pt/isortfinishaudit01/audit.json`, file hash
  `sha256:c8ba00d92f2e4bcfb24a78f8f2a9928d7df96db0c01aa2faa21237614f3fd01e`;
  canonical artifact hash
  `sha256:6fbba59e3be6a04f038c775d6ecc70267df09f56ee5e0dee3137e916069ab03e`.
  It verifies 28 file bindings, journal chains, actual request parity, grade order,
  counters, cost, time and preserved historical bytes without target execution.
- Historical comparison: [closed I3 result](2026-10-15-isort-retention-result.md)
  and `C:/pt/isortretainlive01`; original result and row hashes remain unchanged.

The approved bridge's frozen free tests remain its implementation evidence.
This follow-up changes documentation only; documentation-layout checks and
`git diff --check` validate the record. No extra model, diagnostic or evaluator
execution was used to prepare the audit or documentation.
