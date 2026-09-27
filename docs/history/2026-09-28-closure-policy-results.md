# Closure-policy response comparison result

Date: 2026-09-28. `official=false`; four live responses, no returned tool execution.
Follows [collector validation](2026-09-28-closure-policy-collector.md) and the linked
design. The user approved $4 total, $1 per response, A1/B1/B2/A2, the exact
original-toqito-1538 dev-train checkpoint, gpt-5.4-2026-03-05 xhigh and repository
`.env`, with a 30-minute invocation deadline and no retry.

## Result

| Sample | Next action | New cost USD | Output tokens |
| --- | --- | ---: | ---: |
| A1: unchanged | finish_task | 0.019523 | 722 |
| B1: two sentences removed | finish_task | 0.1955065 | 8,004 |
| B2: two sentences removed | run_probe | 0.2116255 | 13,533 |
| A2: unchanged | finish_task | 0.019598 | 727 |

All responses completed with known billing. Total $0.446253; elapsed 208.750
seconds. Unused $3.553747 is closed. There is no continuation/retry authorization.
Output counts are provider usage, not a measure of reasoning quality.

Anonymous public decisions were reviewed and journaled before revealing arm mapping.
All three finish responses explicitly clear the open question and treat the passed
registered regression/no observed current failure as sufficient to submit. One
describes further probing as optional numerical risk because it changes no required
gate. B1 still finishes despite producing substantially more output than either A.

B2 distinguishes passing regression from coverage of the changed mixed-CQ branch.
It proposes a current-diff alpha=2 correlated classical 2x2 state, an Arimoto-form
expectation, a separate downarrow expectation and an uparrow/downarrow inequality.
It keeps the verification question open and makes submission conditional on the
probe. The expected formula is asserted as known in the response; it was not
independently established by this collection. No probe was executed, and no edit,
submission, benchmark or safety evaluation occurred. All those outcomes are NOT_RUN.

## Interpretation

The observed split is A: two finish choices; B: one finish and one probe choice.
This is an exploratory signal of current-input decision sensitivity, not a reliable
effect estimate, proof of causal mechanism, or evidence of better repairs. There
are only two samples per arm, prior policy exposure remains shared, and the saved
plan had already weakened. Three of four responses still close verification.
The treatment's larger token usage did not consistently produce verification.

Do not adopt the deletion as a default from this result. The smallest next diagnostic
is a provider-free review of B2's proposed probe: whether its expectation is justified,
whether it actually discriminates the changed behavior, and, if separately authorized,
what it observes on the frozen patch. Selecting a probe alone cannot answer that.

## Evidence and boundaries

- Live root: `C:/pt/closurepolicy0928a`; journal `run_dev_sample_6a5bd904d1934142`.
- Review/audit: `C:/pt/analyses/closure-policy-results-20260928-v1`, journal
  `run_dev_closurepolicyresults`. `anonymous-review.json` precedes arm decoding;
  `audit.json` binds delivery identities, per-response settlements and source hash.
- Four counted requests and dispatched identities match the frozen cells exactly.
  A input count 33,314; B 33,289. No tools ran and no response was chained into another.
- [Official model pricing](https://developers.openai.com/api/docs/models/gpt-5.4)
  reviewed on 2026-09-27 UTC (2026-09-28 KST): $2.50 uncached input, $0.25 cached
  input and $15 output per million tokens. The frozen short-context rates matched.
- Price/admission review and grant:
  `C:/pt/analyses/closure-policy-price-review-20260928-v1`.
- Production runtime and historical records remain unchanged. Prior unknown billing
  remains separate from this fully settled invocation. Documentation checks passed;
  earlier full-suite incompleteness remains as recorded in collector validation.
