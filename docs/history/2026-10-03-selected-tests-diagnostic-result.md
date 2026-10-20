# Seeded selected-test diagnostic: provider stop

Date: 2026-10-03. official=false, claim-ineligible. Allocation closed.
Follow-up to [preparation](2026-10-03-selected-tests-diagnostic-preparation.md) and
the [frozen design](../../.agent/selected-tests-diagnostic.md).

## Question and authorized execution

The diagnostic asks whether an agent with optional `run_tests` independently
exposes and repairs the saved A1 CLI regression while preserving two public TSQL
examples. B1 is a preservation control for those checks. This is a seeded diagnostic,
not a fresh-solve or causal tool-effect comparison. Public calibration had passed;
autonomous selection, interpretation and repair remained unresolved.

The user approved the exact two-run proposal with `진행해줘`: A1 then B1, each once,
`gpt-5.4-2026-03-05` xhigh, desired output ceiling 25,000 tokens, USD 3 per row /
USD 6 invocation, 40 calls / 100 actions / 1,800 seconds per row, three new edits
after seed installation, repository `.env`, no retry/resume/expansion.

Execution commit: `43d97f81b83b2c20d4945fe5f97465c69f68667e`.
Packet: `sha256:ec81e0a94e5210c2948cd521f97af1890859b2d407ebe614734ca95511327e06`.
External root: `C:/pt/analyses/selected-tests-diagnostic-20261003-v2`.
The immutable `authorization.json` and hash-chained authorization event bind this
approval to the original packet. The frozen packet's pending-approval field remains
its preparation-time record; it was not rewritten.

## Observed result

| Row | Provider execution | Agent actions / new edits | Submission / final checks |
| --- | --- | --- | --- |
| A1 | First generation dispatch failed with `RateLimitError` | 0 / 0 | NOT_RUN |
| B1 | NOT_RUN after stop-all | 0 / 0 | NOT_RUN |

A1 run: `run_dev_4daeb0d826594696`, state `C:/pt/stlive01/A1`.
One input-count request succeeded with 10,465 tokens. Its exact request hash matched
the following generation dispatch, which reserved USD 0.4011625 for the selected
25,000 output ceiling. The reservation is not billed usage. Solver wall time was
10.390 seconds; there were no solver tools, edits, submission or isolated evaluation.

Terminal: `PROVIDER_TIMEOUT_OR_UNKNOWN`. The only retained error detail is
`provider dispatch failed: RateLimitError`; no response/usage receipt was recorded.
The evidence does not distinguish the underlying provider limit or quota cause.
Recorded cost is zero, **billing is UNKNOWN**, and total actual cost is not established.
Do not report this as a free run or a confirmed zero-cost response.

The driver observed unsettled usage and stopped before B1. No retry, resume, extra
provider request or post-run assessment was performed. Original private acceptance,
safety and final public behavior are all NOT_RUN. This is an execution failure,
not an agent selection/repair failure or a task-acceptance verdict.

## Verification and decision

Read-only audit validated the frozen packet before documentation changes, journal
hash chains, one counted request and one generation dispatch, absent usage receipts,
unresolved provider dispatch, and no unresolved input count. The actual first model
input contained the public suite and seed notice, no operator CLI target, no old
review/source snapshot, and three remaining mutation slots. The solver worktree
still exactly matches A1's seed; both historical A1/B1 workspaces remain unchanged.

Evidence at the external root: `result.json`, `execution-audit.json`,
`runs/run_dev_testdiagnostic.jsonl`, plus the A1 run journal under its state root.
Result file hash: `sha256:8842b5793a907cbb3790aeb4d1737a4f93301cef245058ff0a667a74d6819e61`.
The audit was appended after allocation closure without new provider calls.
Documentation layout/link tests and `git diff --check` passed. Runtime and frozen
driver/contract were unchanged; no full suite or new mock smoke was needed for
this documentation-only close-out.

The stop-all rule behaved as intended under provider uncertainty. There is no new
evidence about autonomous verification selection, patch correctness or quality
improvement. Keep the baseline and the original calibration conclusions. Resolve
the provider failure before proposing any separately authorized future execution;
the unattempted B1 suffix and remaining budget do not authorize continuation.
