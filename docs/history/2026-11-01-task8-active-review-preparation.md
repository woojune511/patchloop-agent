# Task 8: active post-mutation diagnostic preparation

Status: preparation complete, 2026-11-01; fresh exact-scope cap confirmation pending.
No new paid execution. This is a
separate follow-up; the [input171 diagnostic result](2026-10-31-execution-linked-task8-diagnostic-results.md)
and its allocation remain closed. All proposed work is `official=false` and
claim-ineligible.

## Reason for selecting a different checkpoint

The prior saved-input diagnostic accepted the new execution-reference review but
made no new case or execution. Inspection of its actual packet found that the
conditional `behavior_change` review was absent: it was already at a pre-submission
probe-result review. The latest message also requested an advisory report. That
result cannot establish what the active post-mutation review would do, or whether
the model lacks counterexample-construction ability.

The user now requests a small diagnostic at the actual active post-mutation point.
The question is whether the model uses that review to construct and execute a
materially unverified case from public requirements/source, without an operator
supplying the case. Correcting the checkpoint is warranted by observed delivery
state, not by unused budget or another generic prompt hypothesis. No production
runtime change is required for this preparation.

## Selected public state

Source run: `run_dev_3be40073fc4640bd`, task
`dev-train/current-dev20/8` (pydicom1413). Select model input **138**, the first
delivered current state after the accepted mutation. Actual gate:
`needs_visible_checks`. Review reasons: `context_handoff`, `mutation_result`;
the `behavior_change` payload contains the mutation action/input identities,
baseline/candidate diff hashes and guidance. The active trigger is verified before
any dispatch, not manufactured from a later finish point.

- Saved input artifact:
  `sha256:91123c7374f551d0bf51a0c097a1b18d5f462b65b4ab18c67aa1606fce3f1b37`.
- Source request hash:
  `sha256:af205ae9bde91d34be7a30eddb0749b5446b13ba583cef7fdff94830168c8e51`.
- Candidate:
  `sha256:be082f2721c12b34c2e8032d185297fb2e09379e45a46f5ce7fff1bd642862b9`.
- Runtime:
  `sha256:0963cb074795d1809310160f02dd3c2bc42efe892af302846c3a6454bf598e75`.

The saved public task, patch, source, old helper program/result and mutation facts
remain the input evidence. Only allowlisted public events strictly before138 are
available as references. The subsequent public check, helper replay, finish,
independent verdict and input171 diagnostic report are excluded. Imported actions
remain historical; they are neither newly executed nor rebilled. No raw/encrypted
provider reasoning, private evaluator body or reference patch enters the packet.

Current guidance and scope-review schema are overlaid explicitly. The historical
mutation facts stay fixed while its guidance field is brought to the current
runtime wording in both initial state and current-plan delivery. Old hardcoded
`ready_to_submit` projection/seed labels are replaced by the saved gate. Diagnostic
completion text states the remaining budget and available terminal neutrally; it
does not request an immediate summary. Reporting without a probe remains permitted.
The active review is consumed through the ordinary decision lifecycle, not reissued
as a fresh mutation after every action.

These are declared checkpoint, guidance and reporting-frame changes together.
The result would diagnose behavior under this corrected setup, not isolate which
change caused it. Registered reads/searches and inline probes are available;
ordinary checks, mutation and normal submission are not part of this fixed-patch
diagnostic. This is not an exact normal-run resumption.

## Outcome criteria and scope

Record separately whether the model (1) identifies a publicly supported unverified
case, (2) constructs its concrete input/caller and required observable, (3) executes
that program on the fixed candidate, and (4) interprets the observed outcome within
its actual scope. A discovered contradiction is stronger than successful execution
and is not required merely to establish case construction/execution.

At this earlier checkpoint, the old helper has not yet been rerun after mutation.
Such revalidation is legitimate but does not by itself count as new-case discovery.
A renamed program, populated scope review, old receipt citation or a claim of no
counterexample is likewise insufficient. A changed input must be material to the
public contract or changed branch, and the program must observe the named outcome.
One successful helper cannot certify every related member or the original caller.

If no new case is selected, distinguish an immediate report, useful old-case replay,
resource limit, construction error and execution uncertainty. No extra attempt is
made merely because the result is negative or budget remains. A positive result
would show fixed-patch diagnostic behavior, not repair gain or independent acceptance.
A negative result would not establish a general model capability ceiling.

Proposed exact live scope:

- Task 8, fixed input138/candidate above, one attempt.
- `gpt-5.4-2026-03-05`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- New invocation-wide cap **USD2**, four model calls, 12 actions including report,
  two probes, 600 seconds total, 40,000 counted input tokens per call and 25,000
  maximum output tokens. Waits are clipped to the remaining total deadline.
- Registered read/search, public inline probe and diagnostic report only; no patch
  mutation, normal finish or independent evaluation.
- Exact predispatch counting, zero SDK retries, stop on count, transport, billing,
  cleanup or recovery uncertainty; no retry, resume or automatic additional sample.

The [official pricing page](https://developers.openai.com/api/docs/pricing) was
fetched on 2026-11-01 through OpenAI Docs: standard short-context GPT-5.4 remains
USD2.50 input / USD0.25 cached input / USD15 output per million tokens. Four calls
at the stated input/output ceilings reserve at most USD1.90 in uncached generation
usage; the invocation cap remains USD2. Count-endpoint billing and invoice
reconciliation are not established by the generation ledger.

## Preparation and validation

The new external preparation root is `C:/pt/active8-review-20261101-v1/`; the
separate proposed result root is `C:/pt/active8-review-run-20261101-v1/` and must
remain absent before launch. The prior consumed root is never reused. Driver
origins, exact packet, local validation and frozen plan are retained externally.
Image inspection uses the already installed identity; Docker Desktop is not
started and no image is pulled or built automatically.

The external driver passed **24 mocked tests in 55.17 seconds** and Ruff. Coverage
includes actual first-dispatch active guidance, admitted mutation identity, consumed
trigger on the second request, rejecting an inactive checkpoint, future-evidence
exclusion, stale-diff references, immediate report without a probe, bounds and
uncertainty stops. A code review found that the old developer state could retain
the first active label after a new decision; the diagnostic now refreshes that
working-plan projection and removes old diagnostic budget overlays. Original
checkpoint/source/program archives remain immutable. Initial allocation and latest
remaining diagnostic budget are distinct fields, as documented in the test receipt.

An independent offline audit constructed the first request from the **real input138**
packet through `ReviewSession.prepare_request`, without provider/counting or target
execution. Both current-plan representations contain the same active mutation
request and current guidance. It verified unchanged issue, complete patch,
referenced public exchanges, selected source, old probe and check facts; **38 public
records end at134**, strictly before138. The source-receipt index contains eight
metadata entries. This supports transport/mechanism readiness, not live model uptake.

Evidence:

- [External driver validation](C:/pt/active8-review-20261101-v1/local-validation.json):
  `sha256:5611b74dd3814aede3db19e31454e5c03a224082006b7554debfa4ec0f872260`;
  exact code bindings, command/log/XML and zero-provider/target/evaluator boundary.
- [Prepared checkpoint](C:/pt/active8-review-20261101-v1/checkpoint.json):
  `sha256:91672c7d253a0d8281af8a976321e97d1a1b52bed00e5320c014624711ff3bd8`.
- [Prepared request](C:/pt/active8-review-20261101-v1/request.json), canonical request
  hash `sha256:d53817fb14b009a8812d2895b643484857f61f3f3adbd81ce1da4eeedb280727`.
- [Actual first-request audit](C:/pt/active8-local-20261101-v1/packet-audit.json).
- [Driver origins](C:/pt/active8-review-20261101-v1/origin-bindings.json) preserve
  the four prior driver hashes; original files are unchanged.
- [Credential-shape preflight](C:/pt/active8-local-20261101-v1/credential-preflight.json)
  records only validity/untracked status, never the secret.

The plan will be sealed against the clean documentation commit before the cap question;
its exact HEAD and command binding will be recorded in
`C:/pt/active8-review-20261101-v1/plan.json`.
Documentation checks/integrity receipts are under `C:/pt/active8-local-20261101-v1/`.
Prior local runtime validation remains in the implementation record; this preparation
changes external diagnostic code and documentation only. No paid provider/counting
call, real target program or independent evaluator has been executed by preparation.
No new acceptance, repair-gain or generalization claim is supported.
