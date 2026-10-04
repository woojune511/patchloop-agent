# C2 live1 completion cost: offline ledger and request audit

Date: 2026-10-04. Classification: consistent budget exhaustion; avoidance through
a different repair trajectory remains unestablished. No runtime change, new policy,
provider count, generation, sandbox execution or additional paid evaluation.

## Question and scope

The [feedback continuations](2026-10-04-c2-feedback-results.md) established public
autonomous repair in both candidates and original acceptance in live2. live1 repaired
the issue and passed all 506 public regressions but its final response was truncated
under cost admission. This audit asks whether actual spending, input growth and
the resulting admission match the execution contract. It does not reopen repair
ability or predict whether a larger final allowance would have completed the task.

Duplicate settlement, an unintended future reservation, a count/request mismatch,
or a missed required segment boundary would justify a focused correction. The
recorded arithmetic and boundary replay found none of those discrepancies.

Execution commit 89c1ff4ccb06ca30b2436fcbd8f48018b6a46528 is available locally.
Its cost, runner, segment and continuation-ledger files match the audited HEAD
a4c63ffeec34f447843ff90e23e3bee1f923c093 and unchanged working files. The runtime
hash still matches the execution manifest:
sha256:ca68a11874470d7887733422b5c715afb67a11e9b8d22d2a1c1de3e5b3b2b027.
The externally discussed abbreviated commit 4dc804b is not locally resolvable;
no equivalence to that version is claimed or needed for this execution audit.

## Actual spending, not reservation totals

The row cap is USD 3. Historical provider settlements sum to USD 2.415079,
leaving USD 0.584921 before the continuation. That sum matches the preserved
prefix and is carried once. The separately approved invocation cap is USD 1.3926595
of new spending; it never binds this first row. The active policy is per-call-v1,
so future-cost reservation is zero throughout. Model-call completion reserves
are a separate resource and must not be treated as reserved dollars.

Frozen rates per token: USD 0.0000025 uncached input, 0.00000025 cached input,
0.000015 output. Admission uses all input at the uncached rate, floors affordable
output and requires at least 128 tokens. Settlement uses actual cached input and
actual output. The replay uses both DevCostLedger and independent integer arithmetic.

All five dispatched requests desired 25,000 output tokens:

| New call / purpose | Input / cached tokens | Approved output | Actual output | Before USD | Reserved USD | Actual input USD | Actual output USD | Settled USD | After USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 / two searches | 28,857 / 0 | 25,000 | 902 | 0.5849210 | 0.4471425 | 0.0721425 | 0.0135300 | 0.0856725 | 0.4992485 |
| 2 / two searches | 29,887 / 0 | 25,000 | 910 | 0.4992485 | 0.4497175 | 0.0747175 | 0.0136500 | 0.0883675 | 0.4108810 |
| 3 / source read | 33,252 / 9,600 | 21,850 | 511 | 0.4108810 | 0.4108800 | 0.0615300 | 0.0076650 | 0.0691950 | 0.3416860 |
| 4 / fifth accepted edit | 34,633 / 11,648 | 17,006 | 9,984 | 0.3416860 | 0.3416725 | 0.0603745 | 0.1497600 | 0.2101345 | 0.1315515 |
| 5 / post-verification response | 51,273 / 0 | 224 | 224 | 0.1315515 | 0.1315425 | 0.1281825 | 0.0033600 | 0.1315425 | 0.0000090 |

The first three inspection decisions cost USD 0.243235. The patch-producing call
cost USD 0.2101345, including 9,984 output tokens (9,199 reported reasoning tokens).
Those two amounts leave USD 0.1315515. The mutation and automatic checks between
calls 4 and 5 consume actions/time but no additional model settlement. They change
what appears in the next input. Reservations above are not added to spent usage.

The desired 25,000-token ceiling first became unaffordable at call 3. This is
not the point at which completion became impossible: required completion output
length is unknown, and that call actually needed only 511 output tokens.

Final admission, in integer nanodollars:

```text
remaining                         131,551,500
uncached input = 51,273 * 2,500  -128,182,500
future reserve                            0
available for output                3,369,000
floor(3,369,000 / 15,000)                  224 tokens
reservation = input + 224 * 15,000 131,542,500
```

225 tokens would require 6,000 nanodollars more than the remaining row allowance.
Thus a larger ceiling was not admissible for this identical request and budget.
The response used all 224 output tokens for reasoning and emitted no tool call.
Usage was known and settled, leaving 9,000 nanodollars. The one protocol-correction
request was counted at 50,957 input tokens, requiring at least 129,312,500
nanodollars for input plus the 128-token minimum. It was denied before dispatch.
No duplicate cost or unbilled provider generation was found.

## Input growth and segment handling

Between the edit-producing call and the post-check request, counted input grows
by 16,640 tokens, from 34,633 to 51,273. Uncached input admission consequently
grows by USD 0.0416000, from 0.0865825 to 0.1281825. Cached settlement discounts
from earlier calls do not reduce the conservative input admission for the next
call. The last response reported zero cached input.

The same transition grows serialized request size from 157,522 to 260,963 bytes:

| Serialized component | Byte change |
| --- | ---: |
| Opaque reasoning continuation item and metadata | +67,033 |
| replace_text tool response | +21,544 |
| Historical public-source evidence message | +15,603 |
| replace_text function call | +4,619 |
| Current-state message | -3,884 |
| Schemas and serialization overhead | -1,474 |
| Total | +103,441 |

The encrypted payload itself is 66,916 bytes; its contents were not decrypted or
interpreted. The mutation response includes revalidated source spans. The extra
historical evidence retains source observations. Current state contains updated
regression/probe receipts but shrinks overall. Thus it would be inaccurate to
attribute the entire input increase to the regression report. These are serialized
byte contributions, not token counts or causal token-price allocations per field.
No new provider count or local token estimate was substituted for the recorded count.

The final request is below all configured limits: 60,000 input tokens, 1,048,576
request bytes and 262,144 bytes per encrypted item. The existing result-or-size-v1
contract waits for a major result to be reviewed by the next valid decision and
completed batch before a result-driven handoff. The successful post-edit checks
had just arrived; that review decision had not yet occurred. Replaying boundary_reason
at each recorded request yields no missing boundary. Segment starts at sequences
324 and 344 both record major_result_reviewed; there is no later required rollover
before the final request. A premature handoff would be a policy change, not repair
of a missed existing trigger.

## Decision, limits and evidence

Classify this as consistent exhaustion under the existing cost contract. No runtime
correction is justified by this audit. The fifth-edit feedback result remains
2/2 public repair, with acceptance 1 PASS and 1 NOT_RUN. Keep baseline and closed
allocations; add no completion reservation or automatic submission behavior.

The records identify where money was spent and why only 224 tokens were admissible.
They do not identify a known minimum budget for a successful finish. Shortening
earlier exploration/output, changing context retention or funding a larger cap
could arithmetically leave more allowance, but the same repair and successful
submission under those changes are untested. Earlier spending is not classified
as waste merely because a different allocation could produce a larger ceiling.

External immutable procedure and evidence:
C:/pt/analyses/c2-completion-cost-audit-20261004-v1/audit.py and audit.json,
bound by run_dev_c2completionaudit JSONL. The script validates the original row and
allocation journals, envelope, actual counted/dispatched request artifacts,
settled usage and execution runtime. It reads no credential or reasoning content
and makes zero external calls. Source journal and allocation hashes remain those
in the completed live audit; raw requests are not copied into repository docs.

The offline replay passed. Existing focused cost/segment tests and documentation
layout/link tests, Ruff and diff checks passed. No new implementation tests were
added. Full fast suite and standalone mock smoke were not rerun for this
documentation-only change; no fresh solve or additional acceptance was executed.
