# Recovery A/B stopped with HTTP usage evidence

The newly authorized allocation is closed: A1 submitted, B1 stopped on its first
model response, and the other ten rows are NOT_RUN. A1 fails both registered/native
acceptance and the original missing-initializer caller; the initializer-present
control and safety pass. B took no action. This is not a completed A/B comparison
and establishes no recovery, reproduction or repair benefit.

The diagnostic improvement did answer a narrower question: B1's HTTP JSON already
contains zero usage counters, matching the SDK projection. The discrepancy was not
introduced by SDK parsing of those selected fields. The upstream cause and billed
amount remain unknown. No retry, replacement, continuation or further paid call
was made after the stop.

## Why this allocation and what was fixed

The [previous allocation](2026-10-20-evidence-recovery-results.md) ended before B
could act. The [A1 helper replay](2026-10-20-a1-helper-replay.md) then showed that
the old helper passed before and after its edit without reaching the edited branch.
That left the intended treatment question unanswered, rather than demonstrating
that B failed to use evidence. The [fresh specification](../../.agent/plans/recovery-http-comparison.md)
therefore retained the same three assigned changes and added identical operator
HTTP diagnostics to both runtimes. No caller hint or helper-replay result entered
either fresh solve.

- Manifest: `sha256:c4d29076f6068e17352535476e3e692c26e142ff665f01fd83f8de3adb8b3d09`.
- Packet: `C:/pt/evidence-comparison32/`; solver state:
  `C:/pt/evidence-comparison32-live/`.
- A: `dc03e120ec01a1592f4818fbcba5a50677deb890`; B:
  `52915883604f6fdafc2b1738b73c681870c8a333`. Preparation root: `b3303e86`.
- Task: Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`, base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000;
  credential path: project `.env`.
- Human approval: “새 12회·$10.56 상한으로 승인”, bound in `authorization.json`
  and `run_dev_recoveryhttpapproval32`. Six assigned rows per arm, serial order
  `A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6`; USD 0.88/row, 5.28/arm, 10.56 overall.
- Transitions, two references, 24,000 retained characters, 60,000 input tokens,
  request/item ceilings, 40 calls, 100 actions, four edits and 1,800 seconds
  including the 330-second evaluation reserve remained unchanged. Source,
  Pylint 2.12.2 dependencies and installed image identities were pinned.

The complete assigned runtime diff matched the original A/B diff. Both normalized
initial requests matched their historical arm, with the same six allowed A/B
differences. Shared diagnostic files/tests were identical. Selected preparation
checks passed: A 161, B 173, adapter/audit 11, documentation 5 and Ruff; both arms'
quick selection included isolated mock evaluation. These are selected checks, not
a full-suite pass; four older timing failures remain unresolved.

## Execution, acceptance and cost

The public audit was sealed before any fresh acceptance grade was opened. Then
exactly two caller checks and one native assessment ran on the single saved patch,
with zero additional provider calls. The same whole patch was used for native
evaluation; no additive tests existed to remove from the caller projection.
All A1 assessment cleanups were confirmed, and registered/native results agreed.

| New row | Execution | Public base regression | Registered / native | Original missing / present caller | Safety | Billing |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Submitted | PASS: 1,231 passed, 69 skipped, 15 xfailed | FAIL / FAIL | FAIL / PASS | PASS | USD 0.48778785 settled |
| B1 | ERROR before any action | NOT_RUN | NOT_RUN / NOT_RUN | NOT_RUN / NOT_RUN | NOT_RUN | UNKNOWN |
| Other ten | NOT_RUN after stop | NOT_RUN | NOT_RUN / NOT_RUN | NOT_RUN / NOT_RUN | NOT_RUN | No dispatch |

There are zero accepted repairs among the six assigned rows in each arm, but five
rows per arm were never attempted and B1 never produced an action. Reporting this
as a measured 0/6 versus 0/6 repair rate would obscure the failed comparison.
`outcomes_complete=false`, `favorable_local_signal=false`, `official=false` and
`claim_eligible=false`. The prespecified two-repair/two-supported-use criterion
cannot be evaluated from these interrupted assignments.

A1 made 28 generation calls and 28 actions: 14 source searches, 11 reads, one edit,
one public check and finish. It consumed 1,041,165 total input tokens, including
707,328 cached tokens, and 40,969 output tokens, including 30,458 reasoning tokens.
Largest dispatched input: 59,228 tokens. No output ceiling was reduced. Its last
active receipt was at 322.594 seconds; the separate saved-patch assessment took
41.504 seconds.

| A1 settled component | USD |
| --- | ---: |
| Uncached input: 333,837 tokens | 0.25037775 |
| Cached input: 707,328 tokens | 0.05304960 |
| Reasoning output: 30,458 tokens | 0.13706100 |
| Other output: 10,511 tokens | 0.04729950 |
| Total | 0.48778785 |

The new total is **USD 0.48778785 plus UNKNOWN B1 billing**, not USD 0.48778785
with a free B1. Its USD 0.122916 conservative reservation is not a bill. The previous
allocation's USD 0.75890505 and its separate UNKNOWN B1 remain separate; neither
was transferred or retroactively resolved by this run. Prices were checked against
the official standard/global table on 2026-10-20 before dispatch.

## Evidence acquisition, delivery and interpretation

This section concerns **new A1**, not the old helper-test A1. It added eight lines
to `check_modpath_has_init` in `astroid/modutils.py`, consulting `spec.find_spec`
when the existing namespace predicate returned false. Submitted/source/native
patch hash: `sha256:e3f2cdb6db4e45dc8ff0ac18ea23b3c141de457a16713855ab482e401b747c36`.

**Acquisition was partial.** The public failure's directory layout, Pylint command,
environment and test command were in the initial input. Reads delivered
`builder.file_build`, the edited predicate and import spec finders. The actual
Pylint caller and `manager.ast_from_file` body were not acquired. Sequence 325
searched for `def ast_from_file` only in `astroid/astroid_manager.py`; result 329
had no spans, and the agent did not locate the actual defining file afterward.
It also did not execute a public caller probe or a before-edit failure.

**Delivered source did not establish the chosen causal path.** Input 362, immediately
before edit decision 364, retained `builder.py:90-180`, `modutils.py:259-520,598-674`
and `spec.py:100-369`. The edit was explicitly justified as the most plausible
failure path, without observing the original caller or a failing baseline. Thus
the evidence supports an incomplete caller investigation and speculative edit;
it does not support source loss as the sole cause of that edit.

**The final scope assertion was unsupported.** Public check 381 passed the general
pytest suite. Finish decision 393 asserted that this was the exact public behavior
and that the missing-initializer scenario no longer failed. No trace tied that
suite to execution of the reported Pylint invocation. The later independent
missing-initializer assessment still observed F0010 and no child analysis; the
initializer-present control passed. This confirms that the regression PASS did
not establish repair of the original failure. Native and registered acceptance
also failed. No inference from opaque reasoning was used.

**Recovery was not exercised.** Neither row called history search or a probe.
A's 14 ordinary searches yielded zero eligible lost-body restorations under the
unchanged automatic-recovery predicate. B exposed its initial schema but returned
no tool call; there was no opportunity to observe its source restoration or fixed
before/after comparison. This is not evidence that the treatment was offered at
a relevant decision and ignored.

## Context displacement

The size handoff from input 250 to 269 lost no source lines and gained 65 newly
read lines. Source retention did not narrow the relevant bodies before the edit.
After the edit and regression check, the result handoff from 375 to 391 removed
456 versioned lines:

| Removed range | Lines | Interpretation |
| --- | ---: | --- |
| Old `modutils.py:259-520,598-674` | 339 | Superseded version; updated source remained |
| `builder.py:90-121,127-180` | 86 | Current loading context lost; error wrapper 122-126 remained |
| `spec.py:29-33` | 5 | Enum context lost; finder bodies remained |
| Scoped nodes 756-769,775-786 | 26 | Current neighboring name-resolution context lost |

The 456 lines are not 456 missing current counterexamples. There were no probe
programs/results to displace. The later loss of builder context may matter to
the final review, but happened after the speculative edit and does not establish
its cause. With no actual recovery input, recovery-caused displacement is NOT_RUN.

## What the new HTTP evidence establishes

B1 counted 13,888 input tokens immediately before dispatch. Count and generation
used the same request hash:
`sha256:798774be66fbda662db93dd8cf95f077528e722e5f38a482644b197906e0f9d8`.
The desired/admitted output ceiling was 25,000. After 1,358 ms, the client received:

- HTTP 200, buffered JSON body of 113,739 bytes; no raw body was persisted.
- `status=incomplete`, reason `max_output_tokens`, and zero SDK output items.
- All five selected raw usage counters were explicit integer zero, including
  input, output, cached input, reasoning output and total tokens.
- The selected HTTP and SDK metadata/usage fields matched exactly:
  `comparison=matched_selected_fields`, `changed_fields=[]`.
- Request ID `req_5b7b460db98f44c2badd2aa2fbd10967` and response ID
  `resp_0a64486adc2404e4016ad6edff70dc87d099d4dfa239df52c5`.

Therefore this new mismatch predates SDK parsing; it is not an omitted usage
object that the SDK filled with zero. Nor does the record establish ordinary
consumption of 25,000 output tokens: the reported counters contradict that
interpretation. The diagnostics do not expose internal provider processing or
prove zero work/zero charge. A B-request-shape interaction remains possible, but
the responsible field and upstream cause are unestablished. The previous B1's
HTTP body was never captured, so this finding does not retroactively locate its
failure layer.

## Decision and evidence custody

Keep the accounting/count guards and no-retry stop. The comparison is closed and
cannot resume; no default adoption or new paid experiment follows. The next
unresolved operational question is why the initial B request receives this HTTP
usage response. Resolve that boundary before another repair-quality panel. The
separate agent-quality finding is that general regression success was promoted
to original-caller repair without reproducing that caller; this run cannot tell
whether B's intended intervention would prevent it.

Key files under the packet root are `collection.json`, `usage.json`,
`http-usage-diagnosis.json`, `audit-public/`, `review/`, `annotations.json`,
`public-review-summary.json`, `result.json`, `assessments/A-r1-t13/` and
`closeout-verification.json`. Journals hash-chain collection, public export,
semantic audit/seal, assessments and closeout. A1 native used the whole submitted
patch; caller/native hashes happen to be equal because no tests were added.

Final `execute.validate` passed after all assessments and before current guidance
was updated. Exact bound status/specification bytes were copied to
`frozen-guidance/` and hash-checked; the original manifest remains unchanged.
Post-closeout current-status drift is deliberate and is not permission to reuse
the closed collector. Historical allocations, reports and raw logs were not
rewritten. The pre-existing root `AGENTS.md` edit is outside this change.

Runtime code was unchanged during collection/analysis. The local preparation,
live interruption, public-only mechanism audit and independent local evaluations
are separate evidence. No statistical or cross-task quality claim follows.

Closeout documentation checks passed 5/5; Ruff and `git diff --check` passed. The
first documentation run caught the history index exceeding its unchanged 6,000-byte
limit by 36 bytes. Replacing its prior top-level helper entry with this result
entry restored the bound; this report still links the preserved helper record.
The initial failure and successful rerun are both retained. No runtime suite was
rerun for this documentation-only closeout.
