# Why the agent stopped with narrow verification

Date: 2026-10-30 KST. Public-record and source analysis only; no provider call,
sandbox execution, patch change or private evaluation. User question: why does
the agent fail to widen verification, and can that yield a general improvement?

## Observations that distinguish explanations

The [latest run](2026-10-30-contract-observation-3916-results.md) ended SQLFluff
task16 with public PASS and independent FAIL. This analysis examines its choice
of verification, not the unknown private failing case. Source journal:
`C:/pt/contractobs3916-run-20261030-v1/16/runs/run_dev_46be7e89743f4292.jsonl`.

1. **No hard resource closure.** At final turn201, 28 model calls, 76 actions,
   11 edits, 969 solver seconds and USD3.0334745 remained. Read/search, edits,
   probe/tests and finish were all offered; exploration was open, closure null.
   The one-call completion minimum is a reserve, not the remaining call count.
2. **Relevant information was available.** The agent reread Delimited at177.
   Final public input retained current source lines1-284, current diff and the
   shared sibling-failure/bypassed-guard guidance. The model could see the changed
   minimum/trailing conditions. This does not prove it understood them.
3. **The selected checks remained anchored to the reported example.** Edit147
   changed several returns and option guards. Plan160 instead links the contract
   to normal `;`, adjacent `;;` and the suite. Probe192/195 checks those two inputs
   with real tree/statement assertions. It does not select a refuting option case.
4. **Other gaps were acknowledged, then left open.** Assessment207 names untested
   empty-element, terminator and min_delimiters combinations. Public decision204
   says: "No further available action is needed to complete the scoped candidate".
   Recognition of an untested area did not become a concrete next action. This
   is observable authored justification, not access to internal reasoning.
5. **Review requests were not lost.** Check/first-ready signals arrived at170,
   and probe-result review at201. Null updates at176/191/206 preserve revision1,
   including stale "visible check untested yet" text. The host requests review
   without interpreting plan prose or rejecting an otherwise valid action.

The completion instructions already distinguish eligibility from correctness and
say to continue when an action could resolve a material gap. Submission is not
forced. Pydicom in the same batch continued after public PASS and tested actual
RawDataElement behavior, so a universal "PASS immediately stops the loop" account
is contradicted. Merely repeating the existing warning is weakly motivated.

## Leading explanation and limits

The strongest current hypothesis is a mismatch between **changed behavior** and
the **criterion used to stop**. The patch alters general matching behavior, but
the agent treats repairing the reported input as enough for this candidate.
Additional changed conditions remain caveats in assessment rather than work that
could change the repair. This explains the visible choices better than a missing
tool, lost source or hard budget exhaustion.

Two alternatives remain: the model may not know how to construct a useful public
counterexample from those conditions, or it may know but judge its value too low.
The current run does not distinguish them. Soft sensitivity to latency/cost also
cannot be ruled out by unused hard limits. Stale plans may be a symptom of that
decision, not its cause. There is no evidence that forcing a plan rewrite alone
would improve repairs or that broader verification would fix the hidden failure.

A related hypothesis concerns scope selection before validation. The public issue
leaves open whether doubled semicolons should be ignored or diagnosed. Mutation146
adds the stronger expectation that the first parsed statement remains preserved,
then implements partial-success handling and guards for additional options. Plan160
is the first non-null plan, after that design has already been applied. The added
tree-shape requirement may be reasonable, but its necessity is not established by
the issue alone. Distinguish a required input-conservation invariant from a chosen
parse-tree shape; neither a smaller repair nor the stronger behavior has been
independently compared here.

## General improvement candidate

The target is **selection of the next useful action**, not total test count.

- Before editing, distinguish requirements supported by public callers/tests from
  behavior introduced by the chosen repair. Prefer preserving existing success/
  failure meaning when that is sufficient; do not invent a stronger contract.
- At existing post-edit/review decisions, focus on an important unverified change
  to behavior. Either obtain an observation capable of refuting it, narrow/remove
  an unnecessary change, or explain why the uncertainty is immaterial. Writing
  "untested" is an honest report, not evidence that further work lacks value.
- A new check should be selected because its result could change the patch or
  submission decision. Rechecking an already supported example is not equivalent.

These can use existing mutation hypothesis/expected_behavior, plan and decision
fields. No new tool, stored checklist, mandatory number of probes or semantic
finish gate follows from this analysis. The host cannot certify an arbitrary
contract from model prose. This is a proposed policy intervention, not implemented
or validated behavior; the previous generic guidance already overlaps with it.

Before extending that guidance again, identify which public boundary cases actually
refute the latest patch. Then examine whether the solver can construct such a
discriminating case without receiving the operator's solution. Successful case
construction followed by voluntary finish would support a stopping-priority issue;
inability to construct a valid case would point to source/contract/setup reasoning.
Use the ordinary integrated development loop unless a specific unresolved decision
requires a bounded comparison. No paid continuation or extra evaluation is approved
by this analysis.

## Evidence and verification

Current source: `patchloop/dev/runner.py` completion guidance,
`patchloop/dev/completion_context.py`, `patchloop/dev/working_plan.py` and
`patchloop/dev/repair_guidance.py`. Public task: current-dev20/16/public.yaml.
Audit root: `C:/pt/verification-selection-audit-20261030-v1`.
`diagnosis.json` points to immutable selected public evidence; its append-only
journal records the analysis. Provider payloads/reasoning, hidden tests, reference
patches and private evaluation artifacts were not opened.

Audit report: `sha256:7e88544dda13b313071f3066d72ce626494201d58f2e54ab1a06c9861d5c6acb`.
Documentation tests: 6 PASS, 0.10 seconds; HTML has 51 unique IDs, 72 valid links
and unchanged scripts. Visual rendering was not rerun for this content-only edit.
`git diff --check` passes. Runtime remains
`sha256:c3c0a0debf6285da1202a51ebd0bef576aa1ee792e237fde72d6914452f82f75`;
no implementation or model-quality test was performed.
