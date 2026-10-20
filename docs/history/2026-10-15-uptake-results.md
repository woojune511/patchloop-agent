# SQLFluff diagnostic uptake: fixed B1/B2 continuation results

Date: 2026-10-15. Closed paid invocation; official=false, claim-ineligible.
Follows the frozen [design](2026-10-15-uptake-design.md) and rehearsed
[execution bridge](2026-10-15-uptake-bridge.md). Those records remain unchanged.

## Question, authorization and decision

The earlier response-only comparison showed that the added B instruction could
select a diagnostic. It did not establish that the model would use the result
to revise its premise and repair SQLFluff-1733. Continue both saved proposals,
without selecting the cleaner sample, to test that missing step.

The user explicitly authorized the prepared manifest, B1 then B2 once each,
USD 7 total, twelve generations and twelve input counts, with no wording changes
or additional executions after observing results. Both rows submitted within
those limits. B1 failed public task repair and isolated acceptance; B2 passed
both. Actual final repair success is **1/2**.

Under the separate, predeclared explicit-linkage criterion, U is FAIL for B1 and
NOT_OBSERVABLE for B2. Therefore the fully observable D/U/P/I chain is **0/2**;
this does not turn B2's successful repair into a failed repair. No row was
unexposed, resource-stopped, replaced or omitted from the denominator.

Keep the runtime baseline. The observations support a successful conditional
repair in one seeded continuation and failure despite delivered counterevidence
in the other. They establish neither a causal gain over A nor general quality
improvement, and do not justify adopting the extra instruction. No prompt tuning,
retry, replacement, fresh A, native benchmark reevaluation or follow-up run was made.

## Frozen identity and accounting

- Manifest: `C:/pt/hypbridgeready01/manifest.json`,
  `sha256:5e093bab9215bcae8d6269257c18ef4a124929d7ba092e865d25b9d1e856b528`.
- Executing HEAD: `bd70d9c3c45da1945f8094898a33a39e931e3ed4`.
- Runtime hash:
  `sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
- Diagnostic implementation hash:
  `sha256:164ed8928443aea8cdb08ea18ecb823bd73d64cf02d9a8983f58b366b92653d1`.
- Task: `tasks/dev-train/current-dev20/18/public.yaml`,
  `swebench-lite-dev-sqlfluff-sqlfluff-1733`.
- Model: `gpt-5.4-2026-03-05`, xhigh, default/standard; exact credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`. No credential content is evidence.
- New evidence root: `C:/pt/hypfollowlive01`; collector summary `result.json`,
  reviewed summary `review-result.json`. Historical source/sample roots were not reopened.

The [official price table](https://developers.openai.com/api/docs/pricing) was
fetched again before dispatch on 2026-10-15: USD 2.50/0.25/15.00 per million
input/cached-input/output tokens. Exact-model availability passed one metadata
read. The already-installed source, dependencies and pinned images passed the
read-only preflight; no image build/pull or Docker Desktop start was performed.

| Resource | B1 | B2 | Total / invocation cap |
| --- | --- | --- | --- |
| New generations | 4 | 4 | 8 / 12 |
| New input counts | 4 | 4 | 8 / 12 |
| New usage cost, USD | 0.69823200 | 0.52038550 | 1.21861750 / 7.00 |
| New tool actions, including saved probe and automatic check | 9 | 8 | 17 / 36 |
| New accepted edits | 1 | 1 | 2 / 2 |
| Largest counted input | 54,234 | 54,416 | per-request cap 60,000 |
| Largest output | 10,634 | 12,099 | fixed ceiling 25,000 |

Costs use settled provider-reported usage and the reviewed prices, not an invoice
reconciliation. Historical samples and parent costs are excluded. The two saved
probe executions, one subsequent model-selected probe per row, one final public
oracle and one existing isolated evaluation per submitted row were all within
the frozen design. Metadata reads: 1; SDK retries, protocol correction calls,
paid judges and paid compaction calls: 0. Both rows ended at finish, not a cap.

## Public trace grading, frozen before private verdict review

| Row | D: delivered counterexample | U: explicit uptake | P: public repair | I: isolated acceptance | Safety |
| --- | --- | --- | --- | --- | --- |
| B1 | PASS | FAIL | FAIL | FAIL | PASS |
| B2 | PASS | NOT_OBSERVABLE | PASS | PASS | PASS |

Both unchanged saved probes showed the hypothetical L036 reversion produces
five spaces before `my_id,`, against the public issue's expected eight.
Setup and cleanup were confirmed, necessary output was complete, and exact
receipts reached each first continuation with its saved call ID and opaque
continuation items. No opaque reasoning was inspected. B1's CTE assertion failed
at line 60; its unrelated later YAML assertion was not reached and was not used
as a veto. B2 printed the disconfirming full CTE output with exit code zero.

### B1: a tested alternative was abandoned in the final edit

Public journal sequences: seed receipt 374, exposure gate 377, first input 378,
conditional probe decision/result 384/387, source investigation 398,
pre-edit input 411, edit/acceptance 418/421, regression 426, finish 435,
final public oracle 447. The journal is
`B1/runs/run_dev_c6cdf266d5a34ded.jsonl` under the evidence root.

The next probe copied indentation only when the second target originally began
on a later line. Its CTE equality passed, but its all-rules YAML output failed
an expectation written for L036-only behavior. The model then read two files and
made two searches. Its accepted edit nevertheless removed the L036 whitespace
copying entirely. Its hypothesis said the CTE was more likely addressed by L003
and L036 should return to newline-only creation; its expected behavior still
claimed L003 would normalize the CTE indentation. That explicitly preserves the
premise contradicted by the saved probe: U FAIL, not merely unobservable uptake.

The unchanged final-diff registered regression passed **506 tests**, but the
frozen public CTE oracle again produced five spaces and failed. Isolated task
acceptance also failed, with safety PASS. The final patch retained the inherited
L003 change and added test but removed the L036 change; no test was weakened.

Patch: `sha256:94b0aeeb58bbec9cd30180cf3d3275c00a779be8fad9817f5cac9290efff25f3`.

### B2: correct conditional repair; explicit uptake remains unobservable

Public journal sequences: seed receipt 374, exposure gate 377, first input 378,
rule-comparison decision/result 384/387, source investigation 398,
pre-edit input 409, edit/acceptance 416/419, regression 424, finish 433,
final public oracle 445. The journal is
`B2/runs/run_dev_c6cdf266d5a34ded.jsonl` under the evidence root.

B2 compared current all-rules, L036-only and L003-only output for the flat SELECT
and CTE cases. It then read L036 and searched the failing regression and whitespace
field. Its final edit retained copying only when the first and second targets
originally occupied different lines. This changes the repair strategy from
unconditional reversion and preserves CTE indentation while removing the flat
L036-only regression. Registered regression passed **506 tests**, the final public
CTE output exactly matched the frozen expectation, and isolated acceptance and
safety both passed. No test or task constraint was weakened.

The public hypothesis explains the incorrectly indented flat target and the
conditional fix. However, its `causal_revision.falsified_prior_hypothesis` names
the **always-copy-whitespace** premise, not the **simple-revert-preserves-CTE**
premise. No public field connects the seed CTE failure to rejection or
qualification of that earlier preservation claim; all new `memory_update`
fields are null. The frozen rubric explicitly requires that link and distinguishes
correct behavior without it as NOT_OBSERVABLE. No particular words, numeric
value or action ID were required. U was frozen on this basis before opening I;
the successful patch and private PASS were not used to infer the missing linkage.
This is a limit on observing uptake, not a claim that B2 ignored the diagnosis.

Patch: `sha256:6e4375e0b664c685b6a82aa831853adada4929e92e3bcfd849d88335cecaabfe`.

## What the actual inputs narrow down

Both first requests delivered the original saved call and real diagnostic output.
Later result handoffs reduced the requests, but the relevant seed stdout and
subsequent probe output remained in each input immediately preceding the edit.
For B1 that request is
`sha256:ce206fb279a199eb216b88fcbe35fe16128c1f2d4b3e893b980dad102f45c039`;
for B2 it is
`sha256:2b95863dd8859a3d96f24853a9b078dea607c93ef9b272a752c3e5c604cbad69`.
Thus omission of this counterevidence during compaction is not an observed
explanation for B1's final choice. Null note updates do not prove forgetting.

Both final-edit inputs exposed only `replace_text` and `stop_task` because the
unchanged completion horizon reserved four calls and five actions. This is an
actual condition of the experiment, not evidence that the restriction caused
the difference. The one-edit restriction remained intact. B2 demonstrates that
a passing repair was reachable under it in this run; the design does not identify
why B1 chose otherwise or what it would have done with more exploration.

The B1 ancillary expectation mismatch and the different follow-up probes are
plausible contributors to divergent interpretation. This is an inference, not a
controlled explanation. The result does not justify adding memory, changing
pruning, tightening a finish gate or increasing budgets automatically. The
remaining question is how a delivered contradiction is incorporated into a final
decision; any new intervention needs separate evidence and authorization.

## Evidence closure and validation

Public source-grounded grading was recorded before private verdict review;
there was no paid judge or independent-blinding claim. The public-grading artifact
is `sha256:609941bfff498be4274d16353f5b844b4520221c7c44e4192305aaf3ad12ec71`.
Review summary: `sha256:55cdd8f5ae7f2582c4ace93e1cbad945f708649c79f2d779f14534a673e56594`.
Audit: `sha256:480c846b073b51e10117ec1cd0fdfac869a396d128c330abcbbc160f2e878ebd`.

The audit verified all eight count/dispatch hash bindings, full output ceilings,
cost arithmetic, both single-use seeds, accepted-edit/action limits, one oracle
and isolated evaluation per row, and no model call after terminal assessment.
All 74 historical bindings, approved manifest, runtime and diagnostic hashes
remained unchanged. Journal heads:

- Collection `run_dev_uptakecollection`:
  `sha256:ce5dec940237c1132105a0249de7113c775a6ef842941acbd9a0bafb04b25161`.
- Public grading/private review `run_dev_uptakereview`:
  `sha256:b7e3da4118bb17022c18269b0697bc53d83a7aa823a90dea8fe7a980ed03822c`.

Runtime and diagnostic implementation were not edited. The user's existing
AGENTS.md change was preserved separately. This follow-up changes only the
result record and current navigation/status. The earlier bridge's full suite
and mock smoke remain its preparation evidence; they are not reexecuted task
results. Closeout validation passed: five documentation layout/link tests,
Ruff over `patchloop tests diagnostics`, and the scoped Git diff check. The
full suite and mock smoke were not repeated for this documentation-only change.
No new test was added for the documentation update.
