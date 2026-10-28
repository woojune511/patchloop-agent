# Public counterexample revision: preparation

Material Passport: implementation and provider-free preparation; live execution
NOT_RUN, official=false, claim-ineligible. Fresh funding is pending. This is an
operator-assisted continuation of a saved candidate, not a clean-start solve or
a controlled estimate of repair improvement.

## Question and evidence

The [caller/completion run](2026-10-28-caller-completion-repair-results.md) passed
the original caller, positive processing witness and public regression, then
failed isolated task acceptance. Its allocation is closed. A separate
[public comparison](2026-10-28-caller-path-contract-results.md) found three
candidate-only path-contract regressions. That public defect, rather than any
private evaluator detail, motivates this follow-up.

Can the model revise the saved candidate using these counterexamples while
preserving the original caller behavior and public library contract? The leading
hypothesis is that supplying observable counterevidence helps it distinguish a
caller workaround from a library repair. Plausible alternatives are that it
ignores the additional evidence, cannot derive a repair within the remaining
budget, or produces a different incomplete workaround. A normal finish alone
does not support the hypothesis. Success on these supplied examples would not
establish clean-start ability or generalization.

## Fixed checkpoint and information boundary

- Task: Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`.
- Source: `C:/pt/caller-completion-repair-run-v1/repair`, run
  `run_dev_3e21775752a54cae`, prepared-request cut 212, excluding the cut.
- Candidate: `sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
- The prefix includes successful original replay and public regression, but no
  finish, submission or isolated evaluator result. Historical opaque model state
  is excluded at the restored boundary; new native conversation then continues.
- `operator_public_counterexamples` supplies the frozen public program, fixture
  inputs, expected/base/candidate outcomes and measured/current diff identities.
  It excludes host paths, operator diagnosis, suggested repairs, reference patches
  and private evaluator information. A changed diff makes the supplied outcomes
  historical. The task, ordinary tools and host verification gates are unchanged.
- `dependency:pylint` remains a registered read-only source. No target patch or
  previously successful operator repair is injected.

The three newly failing cases are `namespace_leaf_explicit`,
`split_leaf_forward` and `split_leaf_reverse`. All eleven baseline-correct cases
must remain correct. `namespace_root_empty` already disagreed on the base and is
reported separately; fixing it is not a newly imposed requirement.

## Resources and observation sequence

One run: `gpt-5.4-2026-03-05`, `xhigh`, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`. Context 60K, ordinary output 40K,
protocol correction output 25K. Zero SDK retries and no automatic restart.

The checkpoint has spent USD1.11921130, 12 model responses, 26 actions and one edit.
The proposed fresh invocation cap is **USD3.38078870**: together with that inherited
spend it retains the original USD4.50 ceiling. Previously unused allocations are
closed, not reopened. Remaining responses are eight including at most one protocol
correction, and remaining accepted edits are two.

Reserve one of the 14 remaining actions and 35 seconds for the final public matrix.
The ordinary runner therefore has 13 actions, approximately 1,353.349 solver
seconds and the unchanged 390-second evaluation reservation. Its global limits
are 39 actions and 2,365 seconds; the added observation keeps combined limits at
40 actions and 2,400 seconds. Responses, edits and money are not reset or raised.
Every normal dispatch still uses fresh input counting and cost admission.

The model may read, search, probe, edit, finish or stop using ordinary admission.
Each edit retains the ordinary original-call replay and current public-check
obligations. There is no new gate forcing a revision. After settled submission
and ordinary completion, one host execution reruns the frozen 12-case public
matrix against that exact submitted diff. It is **not** an automatic check after
each edit and its final output is **not** returned for another model revision.
Skip it without settled submission or after execution/billing uncertainty.

Record independently: model evidence uptake and changes, original-call equality
and processing, public regression, normal finish/submission, final public matrix,
isolated acceptance, safety, cost and time. Any count, transport, billing,
execution or cleanup uncertainty stops the invocation. No retry, image pull or
build is authorized.

## Implementation and local validation

`diagnostics/counterexample_packet.py` checks the frozen public comparison and raw
receipts; `counterexample_repair.py` overlays its public projection at both
canonical context and actual counted/dispatched input. The existing observation
fork now supports an explicit action/time reservation with zero-default behavior.
Ordinary resume and original obligations are not relaxed.

Preparation commits `67366522`, `777cb9c4` and `08e2a815` added the bounded
continuation and stronger delivery checks. Local validation initially passed 39
focused tests in 20.744 seconds, including ordinary-resume controls and isolated
mock evaluation; the expanded final-check driver passed seven in 0.909 seconds.
These are mechanism tests, not live-model repair evidence.

Offline preparation exposed two audit defects: the first audit mistook new native
history for old opaque state; the second scripted read omitted nullable
`memory_update`, so it exercised protocol correction rather than a successful
read. Both were corrected, and their external preparation directories are kept.
A successful read then exposed a real delivery defect: completion projection
discarded its source body when the next input started a fresh compact segment.
Commit `f385692d` preserves only latest successful current-diff read/search
outputs, including dependency provenance, while leaving old bodies omitted.
Existing native deduplication still sends a source body once. The final preparation
verified successful read execution, zero protocol corrections, exact bound source
spans in the following actual request and retained counterexamples. This additional
delivery repair is part of the tested
configuration, so the trial cannot isolate the effect of counterexample feedback.

Final focused validation passed **37 tests in 22.619 seconds**, including source
projection, actual source delivery with/without native history, finalization and
recovery, the final matrix collector and isolated mock evaluation. Ruff and
`git diff --check` passed. Source delivery unit controls also passed 24 in 0.791s;
these overlap the 37 and are not an additional independent sample.

## Sealed execution package

Final preparation: `C:/pt/public-counterexample-repair-plan-v4`.
Status `READY_PENDING_FRESH_CAP`: frozen runtime, task, public source, existing
images and dependency identities passed preflight. First request count/dispatch
parity and successful read-to-follow-up delivery passed with finite offline
clients. Preparation used **zero provider calls and zero target executions**.
Simulated token/cost counters in the rehearsals are not charges.

- Manifest:
  `sha256:aa4f9cc0390ed63ed98bc111af507cebbc4b26cfc281090399fd66eba001c1ba`
- Public packet:
  `sha256:7d8166d7cfb6d9fa2f6a46364d16ba0534a4031a2c18cfeeaa7362960af31372`
- First normalized request:
  `sha256:20fce5d2c7758ee55634bc1ba83e7a3265357036a67250dabe4643138fe51186`
- Preflight report:
  `sha256:5f96f397b7e775a800f2ff9a093ee7f21601c1c285990397d9d2b2d525620a91`
- `run.ps1`:
  `sha256:ea17ee01e0754940ac33f6e53056460831716fa3a0d02c906368cda5ae69a11a`
- Preparation runtime commit: `f385692d7256d97c7db83a1ff858e881b519a89c`.
- Intended result root: `C:/pt/public-counterexample-repair-run-v1` (not created).

After explicit approval of the new invocation cap, execute exactly:

```powershell
& 'C:/pt/public-counterexample-repair-plan-v4/run.ps1'
```

The old v1-v3 external preparations remain preserved. v1 and v3 did not produce
a final manifest; v2's delivery claim is superseded by the successful-read checks
above and its implementation binding no longer matches current code. None ran a
paid collector. Local preparation does not establish model adoption or repair.
