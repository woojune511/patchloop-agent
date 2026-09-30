# Verification-selection comparison: proposed

Status: PREPARED / paid execution NOT_RUN / exact budget approval pending.
Every row is official=false and claim-ineligible. This note is not authorization.

## Question and fixed scope

Does replacing generic experiment advice with assumption-directed check selection
help the agent discover and repair a public correctness gap? This is a first
mechanism check on an exposed development task, not a general performance estimate.

| Order | Task | Guidance | Runtime source commit | Ceiling |
| --- | --- | --- | --- | --- |
| 1 / A | original-darts-3065 v1 | Previous generic advice | f900d72d351beb04ec5e8672aec2b396b13eff15 | USD 3 |
| 2 / B | original-darts-3065 v1 | Assumption-directed selection | 617bb7fb20e6754c133c46fd124e3fd987b3f604 | USD 3 |

Each is a fresh invocation with repeat=1. Total allocation is USD 6, enforced as
two nontransferable invocation-wide USD 3 caps. No replacement, retry, resume,
third row or automatic extension. B begins only after A's dispatch/accounting and
owned-process cleanup are settled. Count, transport, billing or cleanup uncertainty
stops the entire comparison, including B. Ordinary acceptance FAIL is an outcome,
not permission to change the scope. Unused funds do not authorize further work.

Both use the checked-in `tasks/dev-train/original-darts-3065/public.yaml`, original
source commit `6bfda77e4afc9c123740ab6cc52ca39a7ab92d84`, and model
`gpt-5.4-2026-03-05`, xhigh, desired output 25,000. Credential file:
`C:\Users\geonj\Documents\PatchLoop\.env`; inspect existence only during preparation.
Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled, probe-policy
none, repair-recheck, protected-v1 and per-call-v1. Per row: 40 model calls,
100 tools, four accepted edits, 1,800 seconds. Count immediately before dispatch;
zero SDK retries. Standard admission may lower the desired output ceiling.

The only changed runtime file is `patchloop/dev/model.py`; only its verification
paragraph differs. Run A from an isolated clean checkout and B from its pinned
runtime. Bind runtime/task/prompt/tool hashes before each dispatch. Do not inject
an old prompt into a differently labelled runtime or reuse an earlier live row.
Documentation-only descendant commits are allowed only with identical bound
runtime, task and prompt hashes. Preserve the original source in both runs.

## Inputs, environment and controls

Reuse verified local public preparation, without downloading or rebuilding:

- Source: `C:\pt\preparations\darts-next-repair-20260930-v1\prepared-source.json`.
- Dependencies: `C:\pt\preparations\darts-next-probes-20260930-v1\prepared-probe-dependencies.json`.
- Fresh state: `C:\pt\runs\verification-selection-ab-20260930-v1\row-1` and `row-2`.
- Preflight/proposal receipts: `C:\pt\preflights\verification-selection-20260930-v1`.

Confirm source/dependency contents, exact local evaluator/probe images, clean
runtime/task paths and both OS CI before paid admission. Never start Docker Desktop
or acquire images automatically. Source checkouts and agent context receive no
operator programs, prior patches, prior trajectories or evaluator feedback.

After both rows terminate, apply each exact submitted patch to separate copies
and run the already frozen public programs from
`C:\pt\reviews\probe-patches-20260930-v1\darts_cases.py`.
That program stays outside agent context and registered/private task evaluation.
Do not revise the cases after seeing the new runs. Original-source results and
earlier submitted patches remain immutable controls, not fresh A outcomes.

## Predeclared review and interpretation

First inspect actual agent inputs/actions: was the intended guidance delivered;
did a self-selected check test a repair assumption; was its expectation justified
by the public contract; did observed failure lead to a correct repair and recheck?
Distinguish invalid setup, invalid expectation, execution success, detected defect
and repaired defect. Probe count or a self-written explanation is not improvement.

Then report final public case outcomes, registered checks, isolated acceptance,
safety, completed/unfinished calls, cost and active time separately. Review cases
may overlap, so do not treat their pass fraction as an independent success rate.
A B-only valid counterexample followed by a correct repair, with no lost checked
behavior, is a promising observation requiring replication. Ties, non-use or
conflicting quality/cost outcomes are inconclusive; do not force a positive result.
No automatic default adoption or broader claim follows one pair. Darts is exposed
to the developers even though neither agent receives the operator counterexamples.

## Before asking to dispatch

Validate both request objects, runtime-only difference, prompt hashes and available
environment without invoking a provider. Save one external append-only dev-run-v1
proposal and read-only receipts. Present the exact two-run USD 6 scope for approval.
If a prerequisite fails, record it and leave the paid rows NOT_RUN.

## Completed preparation

Request validation, runtime-only difference, tracked-clean admission, prepared
source/dependency content checks and local evaluator/probe preflights passed with
HTTP provider requests blocked. Credential existence was checked without reading
its contents. A is checked out at
`C:\Users\geonj\.codex\worktrees\verification-control\PatchLoop`.
One checkout file's line endings were aligned to main after proving normalized
content equality; neither Git index content nor source logic changed. Runtime
hashes bind the actual bytes. No live row has run.

External proposal journal: `runs/run_dev_5ae2ba97983f404b.jsonl` under the preflight
root above. Final proposal hash:
`sha256:4b43f9e663a07ad89217c5f84e2c37f8e2e246eae36e9aa09482d975555c4aca`.
Both request templates, checkout paths, prompt/runtime/task/tool hashes, environment
receipts and the frozen operator-program hash are in that append-only record.
The earlier proposal event is superseded, not overwritten. Check current CI and
revalidate these identities immediately before an approved dispatch.
