# SQLFluff contract identification: public reproduction and focused review

Date: 2026-10-30 KST. Status CLOSED: operator reproduction complete; approved model
diagnostic interrupted by its response-wait limit. Third-call billing remains
unknown. No retry, resume or replacement; runtime unchanged.

## Why this diagnosis

The [latest fresh run](2026-10-30-verification-scope-choice-results.md) checked one
additional whitespace input but still changed failure into partial success without
validating that success contract. Its independent FAIL does not identify a public
cause or establish model incapability. The user chose a small diagnosis before
further production changes. First confirm a real public defect in that exact patch;
then observe a focused model review without telling it the operator's case.

Frozen candidate:
`sha256:57aadee74f816fb44c764ef444ba797078194cbac2230174c1c3036c9a7821cf`,
from task16/SQLFluff1517, run `run_dev_55d4f4526e154a53`.
Runtime:
`sha256:ed9b23780500ed4d4f72fa7751156de34314d18be3a2a05a8fcd3830dca6f4b9`.
Production source, gates, tools and instructions were not modified for this diagnosis.

## Operator reproduction, completed without a model

Fresh external root: `C:/pt/scope16-public-diagnostic-20261030-v1`.
The original grammar and latest candidate received the same eight-case program,
including the identical added test file. Expected behavior was frozen from public
`Delimited` option definitions/guards, `MatchResult`, and public grammar tests
lines567-613. Truthiness and complete input preservation were observed separately.
Existing digest-pinned Python3.9.20 task image; one execution per condition, overall
120-second deadline,70-second condition ceilings. No network/image acquisition,
model, private evaluation, retry or mutation of historical artifacts.

| Public case | Original | Latest patch |
| --- | --- | --- |
| `bar..`, trailing forbidden | False; input lost | **True**; `bar.` matched; input preserved |
| `bar..`, minimum3, trailing allowed | False; input lost | **True**; `bar.` matched; input preserved |
| `bar.foo.`, trailing forbidden | False; input lost | **True**; `bar.` matched; input preserved |
| `bar.bar`, minimum2 | False; input lost | False; input still lost |
| Four normal/minimum/trailing controls | Expected behavior | Same expected behavior |

The three false-to-true changes reproduce success-condition regressions. Fixing
input conservation does not discharge minimum/trailing conditions. The separate
minimum-failure input-loss path remains unrepaired. These are public defects in the
exact patch; the specific private failing assertion remains unknown.

Both executions returned complete output and confirmed cleanup, without timeout
or truncation. Wall time52.41 seconds, model calls0. Diagnostic exit0 means the
observations were collected, not that the behavioral expectations passed.

Summary: `sha256:c8188b8fc9acef58a7fbb2fff498ac22356ba9a67cd8baf1d66d8f4600aeabfa`.
Interpretation: `sha256:11b43ae089125241da636398f1d2adcd011c53511781011d6277d8c179f90f82`.
Journal tail: `sha256:22f4a00b472c3e23a6111b561730cd8e9f791a1526426af9c1212c252c39945c`.

## Focused model diagnostic, frozen question and scope

One new review session on the fixed submitted candidate. This is not a fresh solve,
continuation of the closed paid run, candidate repair or independent evaluation.
Its initial input contains only the complete original public task, candidate diff,
probe environment and diagnostic limits. There is no inherited plan, action history,
check verdict, evaluator result, operator program/case/output or reasoning. Source
bodies are not preselected: the model discovers them through registered reads/searches.

Use the existing fixed-candidate diagnostic Session and counted dispatcher, current
model adapter/cost ledger/public gateway and bounded transport. External driver:
`C:/pt/scope16-review-diagnostic-20261030-v1/{prepare.py,run_review.py}`.
Result root: `C:/pt/scope16-review-run-20261030-v1`.
Only read_file/search_files/run_probe and the existing advisory report_discovery
terminal are offered. Normal finish_task and private evaluation never execute.
The candidate stays byte-identical throughout; report claims require human review.

Generic instructions ask for a concrete input that could violate a contract grounded
in the issue or public source/callers/tests. The model records the proposed input,
expected observation and basis before probe execution, then prints actual properties.
No specific branch, option, input or expected answer from the operator reproduction
enters the request. A defect is not asserted as guaranteed. No probe quota is required.
The model may report no counterexample; reaching a limit is a censored observation.

Approved exact scope: dev-train current-dev20 task16, fixed candidate above,
gpt-5.4-2026-03-05/xhigh, credential `C:/Users/geonj/Documents/PatchLoop/.env`,
one session, **USD2 total cap,4 model calls,12 actions including report,2 probes,
600 seconds**, plus bounded cleanup. Input ceiling40,000 tokens per request and
full output ceiling25,000. No extra reporting call is reserved. Four maximum calls
reserve at most USD1.90 at the reviewed standard rates; actual input is counted
immediately before each dispatch. Zero SDK retries; unknown counting, transport,
billing, continuation or cleanup stops all new work without retry/resume/replacement.

[Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4)
was rechecked on this date: input/cached/output USD2.50/0.25/15.00 per million tokens.
Prepared request hash:
`sha256:459ae3d734c6a91a5b50448f1613706018383f8bb3054974ecb9e8b04805e8d0`.
Exact source/patch/dependency/request/implementation identities and final HEAD bind
the sealed plan before approval. Earlier allocations remain closed.

Local driver validation:8 PASS in36.99 seconds using the actual Session/dispatcher
with synthetic provider/probe substitutes. Count uncertainty/40K overflow dispatch
no model; billing uncertainty executes no tools or successor; forbidden edits and
a third probe are rejected before execution; call/action limits hold; read, two
probes and advisory reporting complete. Real network, credentials and Docker were
blocked in these mocks. Two earlier rehearsal failures were fixture placement and
expected terminal labels, corrected without changing the driver; all logs remain.
External script Ruff and repository documentation tests6 PASS. Production tests
were not rerun because production code did not change.

Mock evidence: `C:/pt/scope16-review-validation-20261030-v3`, result artifact
`sha256:cd233e9c1914528ba212e4575c6cb9c8fda987896e4edecb38bc11b72cebc988`.
Packet audit: `sha256:3a1000d764f15497ed9723723f86aa7fd1f4ab3609fba8e845994a7c1627e2cb`.
Documentation validation: `sha256:9b45210762b146e00a7e003bdf4747906aae8d0d0b3a75089577b602e73fb2e8`.
These establish local mechanism and boundary behavior, not model discovery ability.

## Interpretation and next decision

Review the first unsupported step in public evidence: contract identification,
input construction, execution setup, result interpretation, or subsequent decision.
A valid discovery needs a supported expectation, real candidate-code execution,
complete current-diff observations and a contradiction, not merely exception/exit
status or a model-authored report. Source-backed contracts count even if an advisory
report excerpt does not appear verbatim in the issue text. A different valid public
counterexample is acceptable; matching the operator's exact case is unnecessary.

If the model constructs and observes a valid case, this establishes ability under
focused review conditions only. It does not isolate why the original repair stopped
early or justify adding an automatic reviewer. If it fails, name the observed step
and resource limits; do not claim a general capability ceiling. No automatic second
sample, production intervention or paid follow-up follows from this one session.

The operator used the task's Python3.9 image; the model was offered the same prepared
Python3.12 probe environment as the preceding solver. No model probe ran, so this
environment difference did not produce an observed behavioral or setup result.

## Paid execution and observed limit

The user approved the exact prepared scope with "이 범위로 실행". Preparation code:
`a37973c9336547f158a60584da3000bf02cdfa66`; runtime hash above unchanged.
Sealed plan:
`sha256:56c6b5e1e566dab98db43720437bfd86258cc43884b1f2df6c44b9dba95cebf4`.
Approval receipt: `C:/pt/scope16-review-diagnostic-20261030-v1/approval.json`.
Run: `run_dev_b306fd8919744575`, immutable result at
`C:/pt/scope16-review-run-20261030-v1/result.json`.

Terminal: **PROVIDER_TIMEOUT_OR_UNKNOWN**, elapsed **459.093 seconds**. Three input
counts completed and three provider calls started; two returned and settled. Four
gateway actions completed: three reads and one search. No probe, report, edit,
normal submission or independent evaluation ran. Candidate identity was rechecked.
The recorded known spend is **USD0.1377155**; usage/billing for the third call is
unknown, not zero. The USD2 allocation is closed to further dispatch. Invoice and
input-count endpoint billing remain unverified.

The third call reached the collector's **300-second per-response wait**, with
`RequestWaitExpired`, phase `provider_response_wait`, elapsed300017ms and
`response_received=false`. This is the local whole-response timer, not evidence of
an SDK I/O timeout or a provider-side failure reason. The overall600-second limit,
four-call limit, twelve-action limit and two-probe limit were not exhausted.
Closing the client does not prove remote cancellation or settled billing. No
automatic request followed the timeout.

There was a positive intermediate observation. The first response requested the
completeness helper, MatchResult semantics and full patched Delimited implementation.
After those reads, the second response's public search action (journal sequence32)
explicitly stated that the changed failure paths omit min_delimiters checks and
that partial-prefix returns could violate an existing contract. It searched
`min_delimiters=` to find public grammar/test use. This risk was not supplied by the
operator. It is a public action explanation, not an inference from private reasoning.

Thus **contract-risk identification occurred under focused review**. The review
did not produce a concrete input, expected observation, executed probe or terminal
report. It cannot establish whether the agent can complete that next step, or why
the original repair loop did not choose it. This interruption neither validates
the patch nor establishes an inability to find counterexamples. The operator's
three success regressions and remaining input-loss path remain valid separate
public evidence.

Decision: preserve the current production instructions and gates. Adding another
semantic warning, reviewer or required probe is not supported by this interrupted
review. A future diagnostic would first need an explicit response-wait budget
consistent with its total deadline and fresh paid scope. More waiting might allow
an observation, but does not guarantee one. No new experiment is authorized here.

## Closing evidence and validation

- Result bytes: `sha256:eb2c9fee4752da13da75aef8676adbbbbda102d99e2597b3cfa2d2bc72281918`.
- Execution journal bytes: `sha256:20b75bd02072861cd24da4a94c99e040018a59df896b8eee386ab40359d7abd8`.
- Independent scope/accounting audit: `C:/pt/scope16-review-audit-20261030-v1/audit.json`,
  `sha256:c433e9cd03cdcc9dbcad6308b1fd62586418dfd6d713982348f5a347cee96c53`.
  All44 event hashes and28 audit checks pass: exact approval/input/implementation
  identities, paired counts/actions, fixed final patch, and no dispatch after failure.
  Third-call reserve USD0.4141275 plus known spend gives a conditional response-cost
  exposure bound of USD0.551843 under the bound model/rates/ceilings. This is neither
  settled spend nor an invoice estimate; unknown billing stays unresolved.
- Public-action review: `C:/pt/scope16-review-public-audit-20261030-v1/public-review.json`,
  CAS `sha256:88c33d189e17a512c3ff9de54dbf481ec9a9b3be16b16ebd75ad2ca4b46e4ff9`.
  Reads/search succeeded without truncation. The helper, MatchResult and complete
  Delimited body were returned, followed by grammar_test.py605-609 option references.
  It records the identified minimum-delimiter risk separately from an executed case.
- Documentation validation:6 PASS, local HTML links/unique IDs valid, embedded
  scripts and production runtime unchanged; no new production tests were needed.
  Artifact `sha256:d6da1334674e3d5bae00beae85344c64cdea994d4dd882de9f814f3f03424652`
  under `C:/pt/scope16-review-docs-20261030-v1`. Closed earlier histories are untouched.

These audits are read-only reviews of the completed execution. They make no new
provider/probe calls and do not settle the interrupted provider request.
