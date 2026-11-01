# Verification or narrower repair: an existing-decision revision

Date: 2026-10-30 KST. Implementation and local validation; live experiment pending.
This is an exposed development investigation, official=false and claim-ineligible.

## Problem and decision

The [selection diagnosis](2026-10-30-verification-selection-diagnosis.md) found that
task16 changed general failure/success behavior while testing only the reported
example and a normal control. It acknowledged other untested behavior and stopped
with source, tools and resources available. This matters because a passing example
does not exercise the new assumptions introduced by a broader repair.

The leading hypothesis is a mismatch between the scope of changed behavior and the
criterion used to stop. Difficulty constructing a useful case, or low expected
value assigned to testing, remain alternatives. The unknown independent failure
cannot be attributed to any particular branch. Existing guidance already asks for
counterexamples; repeating that request or enforcing a probe count is not justified.

The user chose implementation plus a small integrated experiment. Replace existing
shared repair and brief-plan instructions, rather than add a workflow stage:

- Ground required behavior in public requirements, callers or tests and separate
  behavior chosen by the repair. Preserve existing success/failure meaning when
  sufficient; a chosen implementation does not establish a stronger requirement.
- Test a material new assumption, narrow/remove an unnecessary change, or explain
  why the uncertainty cannot affect required behavior. Listing unknowns alone is
  not a reason to stop. Prefer observations that could change the patch/submission
  decision over repeating a supported example.
- Retain direct question/property observation, normal controls, same-diff evidence
  reuse and the distinction between state preservation and success eligibility.

Only `repair_guidance.INSTRUCTIONS` and `working_plan.INSTRUCTIONS` change in
production. Existing mutation intents, decisions, plans and receipt undo suffice.
No tool/schema/state change, mandatory probe, extra model round or semantic finish
gate is introduced. Plans and reasons remain unverified authored data. A smaller
patch is not automatically better and removing changes does not certify the
remaining required behavior. Current-diff required checks still apply.

## Local evidence

Baseline: `53a7e75f35444ca7cfa19c3ded3afd04d04a9651`, runtime
`sha256:c3c0a0debf6285da1202a51ebd0bef576aa1ee792e237fde72d6914452f82f75`.
External evidence: `C:/pt/scope-choice-20261030-v1`, journal `run_dev_scopechoice`.
Current runtime:
`sha256:ed9b23780500ed4d4f72fa7751156de34314d18be3a2a05a8fcd3830dca6f4b9`.

- Focused: **111 PASS**, 33.73 seconds pytest / 35.539 wall. Covers actual
  general/repair/completion requests, append/segmented delivery, current/thin and
  both verification policies, exact recovery boundaries and isolated mock finish.
  The first pass found only two documentation byte-limit violations; current
  wording was shortened and the new history entry moved into the daily index.
- Quick: **1258 PASS / 1 skip**, 331.97 seconds pytest / 333.587 wall, including
  isolated mock evaluation. Ruff on `patchloop tests` and `git diff --check` PASS.
- AST audit: only the two instruction assignments changed in production; ordered
  tool schemas across all planning policies remain equal. Current system 7,979
  characters and combined brief 10,808 remain within 8,000 / 10,809 limits.
  Current identity fixtures updated; frozen historical identities preserved.
- HTML: 51 unique IDs, 73 static links resolve and scripts unchanged. Visual
  rendering was not rerun. Prior evidence records and historical bytes unchanged.

Focused report:
`sha256:24de3f375c67d8f2603149390c162bd8a67f80804ab34bf6b3029acfc3f96ec0`.
Quick report:
`sha256:53d391de9017cda122ff21f34a5132645e9958847b8bd05c330a80d6ec6f7f46`.
Contract audit:
`sha256:bbae9c2ee2c0eefca426ba98238bacb79289ba3f2bf2ae4c170b5f09db585773`.
Local audit:
`sha256:77f394f0a836ff56baf564849155bbc84e2770cf62a7dc012d9d8debd9150b29`.

The authored narrowing regression proves that the previous assumption, removal
reason and still-untested original requirement survive delivery on the new diff;
it does not establish whether a live model will choose a correct narrowing. Actual
undo and fresh-check behavior use existing gateway coverage. These tests concern
instruction delivery and unchanged authority, not repair quality. Provider calls: 0.

## Small experiment specification

One fresh dev-train task16 (SQLFluff1517), selected because it exhibited this
decision failure. No previous patch, plan, operator counterexample or other-agent
output enters solver context. The preceding run used execution commit
`556cbbbdcdc2b0b41be20404c5d82f683e8360d4`, same baseline runtime above,
`C:/pt/contractobs3916-run-20261030-v1/16`: acceptance FAIL, safety PASS, public
checks PASS, one accepted edit, 13 calls, 25 actions, 566.561 seconds, USD1.0609665.

Proposed unchanged task conditions: gpt-5.4-2026-03-05/xhigh, 25,000 output tokens,
current/brief-v1, segmented-v1/result-or-size-v1, probes enabled/policy none,
repair-recheck, protected-v1, per-call-v1 and public-checks-v1. One repeat, one
worker, 40 model calls, 100 actions, 12 edits, 1,800 seconds with 330 seconds reserved
for evaluation, positive invocation-wide USD4 cap. Credential file:
`C:/Users/geonj/Documents/PatchLoop/.env`. Same pristine prepared source/dependencies.
[Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4)
was checked on this date: input/cached/output USD2.50/0.25/15.00 per million tokens.
Fresh preparation/result roots: `C:/pt/scope16-20261030-v1` and
`C:/pt/scope16-run-20261030-v1`. Final commit, runtime and all input hashes will bind
the prepared manifest. This specification does not authorize provider calls.

Question: does the revised choice lead to a useful falsification of newly changed
behavior or a justified narrower repair, and does the delivered candidate satisfy
independent acceptance? Review public input/action evidence, concrete assertion
outcomes, responses to failures, acceptance, regressions, cost and time together.
More prose, more probes, smaller diffs or successful submission alone are not gains.
A repeated example-only patch/verification mismatch weakens this intervention.
Even acceptance PASS once supports only this attempt; no causal or general gain.
If the same mechanism persists, diagnose the resulting contract/case choice before
adding more instruction. There is no automatic repeat or unused-budget continuation.

Use the existing bounded scheduler and isolated run evaluation once. Count before
dispatch, zero SDK retries; count, transport, billing, continuation or cleanup
uncertainty stops admission. Never start Docker Desktop or pull/build images.
Prior allocations remain closed; fresh exact approval follows completed local
validation and preflight.
