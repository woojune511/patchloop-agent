# One-row B time extension: completed without repair improvement

## Question and bounded intervention

Following the [timing diagnosis](2026-10-02-review-timing-diagnosis.md), the user
approved one fresh OpenSandbox B execution with a 360-second reviewer allowance
and an additional USD 2 cap. The question was whether B could reach report and
repair completion with more time. This was not an equal-resource comparison with
earlier A/C rows. The 360-second value was a bounded diagnostic choice, not an
estimated sufficient deadline.

Implementation commit 51cf1703 adds a separate review-time-extension-v1 manifest
with exactly original-opensandbox-816 B, repeat one, and retains 180 seconds for
the original twelve-row schema. SharedBudget, request horizon and actual deadline
use the same selected allowance. Source candidates and scoring are unchanged.
The remaining limits stay fixed: gpt-5.4-2026-03-05, xhigh, 25,000 maximum output,
four reviewer calls, twelve reviewer actions, 900 total seconds, sixteen total
calls, 48 actions, two new accepted edits, and USD 2 shared review/repair cost.
Credential path remains C:/Users/geonj/Documents/PatchLoop/.env.

## Preparation and verification

- Focused suite: 112 passed in 43.29 seconds; Ruff passed.
- Full suite: 3,954 passed, 16 skipped in 707.69 seconds; JUnit:
  C:/pt/tmp/reviewextensionfull01-results.xml.
- Mock run run_dev_5b7a3a3479f24c7a reached isolated EVALUATOR_PASS, safety NOT_RUN,
  zero provider cost; C:/pt/runs/review-extension-mock-20261002-v1.
- Fake-clock checks distinguish rejection after 180 seconds from a valid report
  after a 200-second response under the 360-second allowance. Provider timeout,
  displayed horizon and post-response admission use the same selected value.
- Single-row orchestration preflights and executes only the selected task. Frozen
  manifest controls reject expanded time, duplicate rows and additional calls.
- Original source, scoring and other controls matched the preceding manifest.
  Existing environment admission passed before credentials and again at execution.
- The unrelated user's AGENTS.md edit was preserved, not included in the commits.

Manifest: C:/pt/analyses/review-extension-ready-20261002-v1/manifest.json

Manifest hash: sha256:feccbdab7406bef0130ecf2da1be583dfa9594d626862b21adc598e70855f8fd

Preparation driver: C:/pt/review_extension_prepare_20261002.py. Preparation itself
made no provider calls or credential reads. The user's approval covered this exact
one-row scope and additional cap; the collector consumed the frozen manifest hash.

## Live result

One row completed, with no retry, timeout or replacement. B used four review calls,
performed four read/search actions and one public probe, and returned the bounded
report on the fourth call with finish_review forced. This exercises the reserved
final-call report behavior that earlier live attempts did not reach.

The probe tested native Unix symlink rejection plus preservation of a Windows-style
allowlisted path on Unix. The symlink path was rejected and the Windows-style path
was accepted. The report explicitly said no concrete defect was established and
limited its scope: native Windows/reparse points, other path variants and
post-validation races were not covered. A passing probe here confirms those
observations, not task completeness or a newly discovered counterexample.

The reviewer finished 116.589617 seconds after its admission event (about 117
seconds including initial admission overhead). It did not consume the extra
180 seconds. Its requests, outputs and timing differed from the earlier failed
attempt; this is not evidence that raising the limit caused completion or that
the prior attempt would have succeeded with a longer timeout.

The repair continuation submitted the original candidate unchanged:
sha256:5295695164a555a65c6373515dfdf9ecf3c1deadafebc617044fe9ba00896493.
Public matrix: 5/8, hidden acceptance FAIL, safety PASS, official=false. The
inherited accepted-mutation counter is not a new edit. No observed repair-quality
improvement or fresh-context advantage was established.

New settled cost: USD 0.1576275, comprising review USD 0.1118725 and repair
USD 0.045755. billing_known=true from returned usage; no invoice reconciliation.
The previous allocation's unknown timeout charge remains separate and unresolved.

## Evidence and decision

- Result: C:/pt/runs/review-extension-20261002-v1/result.json
- Result hash: sha256:04d4a616b0a62b55549128d499910d312c2f870859ce104693c25d5ec3c726b0
- Audit: C:/pt/analyses/review-extension-audit-20261002-v1/summary.json
- Audit driver: C:/pt/review_extension_audit_20261002.py

The read-only audit verified hash-chained journals, one completed row, unchanged
candidate, forced final report, probe receipt, evaluation and cost. It made zero
provider/probe calls and preserved result bytes. Documentation checks passed.

Close the one-row allocation. Keep the baseline; no further time increase, paid
run or prompt tuning is queued. Completion is now observed, but the review selected
behavior the patch already handled and did not produce a repair. That is a scoped
observation about this task/run, not a general rejection of review. Any further
investigation needs a distinct evidence-based question rather than unused budget.
