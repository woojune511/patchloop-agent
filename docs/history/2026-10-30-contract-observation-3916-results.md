# Contract-to-observation guidance: integrated tasks 3, 9 and 16

Date: 2026-10-30 KST. CLOSED. One fresh run per task; `official=false`,
`claim_eligible=false`. No unused allocation remains active.

## Question and conditions

The [preceding same-roster run](2026-10-30-evidence-reuse-3916-results.md)
retained source and probe output but still returned PASS/PASS/FAIL. A subsequent
public diagnosis found missed failure branches and a success-condition violation.
Its probe question named preservation that its program did not directly observe.
The [guidance change](2026-10-30-contract-observation-guidance.md) therefore connects
the current diff to a public contract, refuting setup, expected observation and
actual evidence or untested status in existing planning and repair instructions.

This integrated run asks whether the agent selects useful counterexamples, observes
the property it names, fixes discovered defects and completes correct repairs at
acceptable cost/time. Repeating the original example or setup-only checks weakens
the intervention. More plan text, case counts or successful probes alone are not
success criteria. The experiment is descriptive, not an isolated causal comparison.

- Execution commit: `556cbbbdcdc2b0b41be20404c5d82f683e8360d4`.
- Runtime: `sha256:c3c0a0debf6285da1202a51ebd0bef576aa1ee792e237fde72d6914452f82f75`.
- Baseline execution commit: `45ff269c65d296aa7a60635f5decbece8ed6f6b5`.
- Exact checked-in dev-train tasks: 3/pvlib1154, 9/pydicom1694, 16/SQLFluff1517.
- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired maximum output tokens.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; contents not logged.
- Once each from pristine prepared source, maximum two workers; USD4 per task,
  USD12 invocation cap. No allocation transfers, replacement, retry or resume.
- Per task: 40 model calls, 100 actions, 12 edits, 1,800 seconds including the
  330-second evaluation reserve. Existing isolated evaluation runs once at finish.
- Same current/brief-v1, segmented-v1/result-or-size-v1, ordinary probes,
  repair-recheck/protected-v1, public-checks-v1 and per-call cost settings as baseline.
  Task, source, dependency and probe-profile identities match the preceding run.
- No prior patch, plan, operator counterexample or other-agent output was supplied
  to the solver. Host load is not experimentally controlled.
- Exact pre-dispatch counts, zero SDK retries and shared admission stop on count,
  transport, billing, continuation or cleanup uncertainty. No image pull/build.

The question, selection, baseline, intervention, criteria and stops were recorded
in the external manifest before explicit approval of this new USD12 scope. Earlier
allocations remained closed. Preflight checked tracked clean inputs, credentials,
prepared sources/dependencies and existing local images without provider calls.
Official [model pricing](https://developers.openai.com/api/docs/models/gpt-5.4)
was rechecked: USD2.50 input, USD0.25 cached input and USD15 output per million
at this bounded short-context setting, matching runtime accounting.

## Results

| Task | Independent acceptance | Safety | Accepted edits | Calls | Task seconds | API cost USD |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 3 pvlib1154 | PASS | PASS | 1 | 11 | 317.999 | 0.511538 |
| 9 pydicom1694 | PASS | PASS | 1 | 12 | 360.560 | 0.757422 |
| 16 SQLFluff1517 | FAIL | PASS | 1 | 13 | 566.561 | 1.0609665 |

Total: **USD2.3299265**, **36 calls**, **57 actions**, two-worker elapsed
**886.668 seconds (14 min 47 s)**. All submissions are `unverified_delivery`;
none supplied a comparable bound unchanged-base reproduction. Independent
acceptance is separate from that delivery label and from public checks.

All 36 generation and exact-input-count starts/finishes and all 57 action pairs
match with no duplicate identities, replay, pending operation or uncertainty.
Exact token repricing equals the ledger; each reservation and row stays within its
cap. Runtime/task/request/source/dependency/profile identities and journal chains
validate. All three rows finished; allocation is CLOSED with no retries or cleanup
failure. Rejected pydicom edit177 is settled and preserves its prior diff.

The preceding run had the same acceptance/safety verdicts, USD2.221501, 33 calls
and 909.436 seconds. This attempt cost **4.9% more** and took **2.5% less** wall
time. SQLFluff itself took 566.561 vs 439.083 seconds; the shorter batch is not a
uniform task-speed gain. Provider dispatch occupied approximately 80.1%, 77.8%
and 81.7% of task time. One exposed attempt per condition establishes neither
causal benefit nor stable quality/cost/latency improvement.

## Public behavior review

Only public task/source, submitted diffs, public action/results, plans and accounting
metadata were reviewed, plus independent verdict summaries. No hidden checks,
reference patches, private evaluator artifacts, provider payloads or reasoning
transcripts were opened. Sequence numbers identify each task's public journal.

### pvlib: concrete values, narrower verification and a repeated subset

Run `run_dev_ab470b451bc34b11`. Edit88 uses masked division for zero GHI and adds
a regression expecting `[0, 27.9412, 104.1317, 34.1663]`. Plan101 connects the
contract to the zero/normal fixture and expected numeric values. This is more
than copying a plan heading. Check103 passes 99 tests; test147 passes two selected
tests from the same file on the same diff, adding no new input condition.

This is a subset recheck rather than the preceding run's second full-file check,
but redundant execution remains. No probe was used; the preceding run separately
examined array and scalar/return-type conditions. Changed-line tracking is unknown,
so file/test receipts must not be promoted to assertion-level coverage. The final
assessment distinguishes fixture evidence from the unverified original caller.
Plan revision2 still says the check is unexecuted after those checks have passed.

### pydicom: useful real-data observation, failed durable-test follow-through

Run `run_dev_4d72dd8b4c2b4c33`. Edit49 moves `self[key]` into the existing try
block and adds a mocked lookup TypeError regression. Check64 passes 27 tests.
After that PASS, plan78 keeps the actual failing conversion path and normal
control open rather than treating the suite as complete requirement coverage.

Probe116 uses invalid raw IS `b'2.0 '` under the default WARN setting. It exits
normally but prints no exception and retains the invalid tag: successful execution
does not establish the intended failure contract. The same configuration mistake
occurred in the preceding run. Probe164 deliberately changes to RAISE and observes
normal `[2]`, default ValueError for invalid input, omission of the invalid tag in
suppressed output and preservation of valid PN `Jane^Doe`. Its question and program
agree, and successful suppression and preservation are observed separately.
These are different configurations, not duplicate probes.

Replace176 then tries to add RawDataElement to a shared test import. Rejection177
correctly preserves the protected import and rolls back to the same diff; its
message explicitly permits importing inside a new test. The agent does not take
that route and submits at192. The durable regression remains a mock, weaker than
the preceding run's actual RawDataElement/strict-validation/whole-JSON test. This
is an agent follow-through gap, not evidence the correct import protection must
be removed. Existing checks/probes remain current because the edit was rejected.

### SQLFluff: broader patch and better observations, still narrow case selection

Run `run_dev_46be7e89743f4292`; submitted diff
`sha256:77030f900d6d24154cd2cb3bf279fa4f1b6515e50f1808802c24ab71b5e703d0`.
Edit147 changes several failure returns to retain the accumulated prefix, handles
an empty section after trimming non-code and adds allow_trailing/min_delimiters
guards. This is broader source coverage than the preceding one-branch patch;
source inspection alone does not prove these conditions are implemented correctly.

The new `test/core/parser/delimited_test.py` checks only normal `;` versus adjacent
`;;`, asserting full tree raw and the statement child. Check162 reports **167 PASS,
1 deselected** under the registered `not dbt` marker selection. Probe192/195 uses
the same two SQL inputs with both parse and lint. Unlike the preceding probe, it
directly prints/asserts full input preservation and equality of the statement child
with the normal control. Both return without runtime exception; doubled `;;` still
produces a SQLParseError/diagnostic. This establishes those particular observations,
not correctness of other grammar branches or option combinations.

Plan160 introduces the contract/case/observation wording but stays at revision1
through submission, including stale "visible check untested yet" text. The final
assessment207 explicitly acknowledges that other empty-element, terminator and
min_delimiters combinations were not directly probed. One edit and one helper
probe were followed by submission, not further selection of those open cases.

Independent acceptance is FAIL, safety PASS. The exact private failing condition
is unknown and was not inspected. No post-run public counterexample replay or
additional private evaluation was performed. The preceding operator's cases have
not been rerun against this new patch, so their old results are not current results.

## Decision and next question

The new guidance was delivered and some public work reflects it: pydicom keeps a
real-data obligation open after PASS, and SQLFluff aligns its probe with actual
preservation observations. This does **not** establish that the guidance caused
either behavior; acceptance stayed PASS/PASS/FAIL and meaningful coverage did not
expand consistently. In particular, broader SQLFluff edits were not paired with
tests of their additional failure paths or success conditions.

Keep the current implementation pending a concrete diagnosis rather than adding
more prompts, a required probe quota or another finish gate from this result alone.
The next unresolved question is which public boundary conditions still refute the
new SQLFluff patch and why those conditions were omitted from the plan/checks.
The pydicom rejection also provides a separate example of abandoning a permitted
test correction. These observations do not authorize another paid batch. No new
runtime change was made during execution or this result review.

## Evidence bindings

Preparation: `C:/pt/contractobs3916-20261030-v1`.
Results: `C:/pt/contractobs3916-run-20261030-v1`.

- Manifest: `sha256:b31a9359bb7d05fb3900f354c409ef68a3f03bfd481888f29d46e9e8ade6dd6a`.
- Approval: `sha256:ec14febc94df36eb38b5fb4baf8918ca3a792b45de221dfd7add6c87e140b523`.
- Result: `sha256:2aa42a21311e04c91aa1faf726933cc9d1b2a9fac1b5927b2d68c17d668ca751`.
- Summary: `sha256:5f8b66f9c03791cc6f922f8fc761309619af2c69bbe6bc4924df916b2b573157`.
- Public review: `sha256:a89a25cab65caf9b0cd5c75b3a65e189e5a80dd80fa64c326c5e3a0fd82e7abe`.
- Final batch event: `sha256:aea1bacef5ac1b140c65375d0ec40b5449df209179f25310dfac7b0df0f44c33`.

The execution source hash stayed fixed. Earlier implementation validation was
104 focused PASS and 1,256 quick PASS / 1 SKIP, including isolated mock evaluation.
These local checks are separate from the three live outcomes above.
Post-run documentation checks: 6 PASS, 0.21 seconds. HTML has 51 unique IDs,
71 valid links and unchanged scripts; visual rendering was not rerun for this
text-only update. `git diff --check` passes. Runtime code is unchanged; the full
runtime suite was not repeated for these documentation-only edits. Existing
historical records remain unchanged.
