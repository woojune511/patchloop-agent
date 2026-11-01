# Original-feedback live pilot: incomplete responses before action

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run, followed by public receipt analysis
- Origin Date: 2026-10-25
- Verification Status: ANALYZED; execution and integrity audited, repair not assessed
- Version Label: feedback25-live-v1
- official=false; claim_eligible=false; allocation CLOSED

## Question and decision

The [cap-only pilot](2026-10-25-budget-live.md) submitted a patch that retained
the original F0010 failure. Replay happened inside the final finish request,
leaving no model turn to use it, and host argv/environment drift prevented
comparable completion evidence. The [local implementation](2026-10-25-original-feedback.md)
introduced fresh invocation v4 and replay after accepted edits, before the next
model input. Local controls supported these mechanics, but could not show whether
a fresh model solve would use stable setup and the feedback to repair the caller.

This authorized single run stopped before its first executable tool response.
Both the initial response and the one allowed protocol-correction response hit
their full 25,000-token output ceilings. There was no inspection, original-call
attempt, edit, check or submission. The new execution/feedback mechanisms were
not reached, so their live effect remains unmeasured.

The allocation is closed. The evidence identifies output exhaustion before action,
not exhaustion of the invocation cost cap. It does not establish why the model
failed to produce a complete tool response, or that the new mechanisms caused it.
A new experiment would need to distinguish first-response formulation/output
allocation from tool or replay execution; unused budget alone is not a reason
to repeat or increase the cap. The local implementation is unchanged.

## Authorized scope and preparation

The user approved the prepared request with `실행해줘`. Authorization was bound
to the request and command hashes; prior allocations were not reopened.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, maximum 25,000 output tokens per call.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; contents not logged.
- One fresh solve, USD 1.20 invocation cap, 40 model calls, 100 tool actions,
  four accepted edits, 1,800 active seconds and 1,920-second outer supervision.
- Same segmented-v1, result-or-size-v1, brief-v1, probes/none, bounded-v1
  acquisition, repair-recheck/protected-v1 and completion-recovery-v1 policies.
- Same prepared task source, dependencies, existing local images, frozen public
  programs and grader as the closed cap-only pilot. No old model context, seeded
  probe, operator repair hint or private evaluator material entered the agent.
- At most two frozen public checks on the full submitted patch shared 120 seconds.
  They were eligible only after submission. Count, transport or billing uncertainty,
  cleanup failure and frozen-input drift were stop conditions.
- Zero SDK retries; no new solve, resume, replacement, model switch, image pull/build
  or budget increase. The existing one-per-run protocol correction was retained.

Preparation verified 111 source inputs, prepared source/dependency identities,
local image identities, prior validation of the current runtime, and a stubbed
CLI settings round trip. Runtime source stayed frozen during execution.

Dispatch commit: `303e688e7f11e70d3558b27177a77d8bde20480e`.
Runtime hash: `sha256:2d1a7111c4fb45675cbb415df884c96460fbc138eca2bec06c6a06f747fa5dce`.
Request hash: `sha256:27db722b1e9f96592f13a3e6699f76c3d9f879c096e7ca4fe3ac643c33c2738e`.
Authorization hash: `sha256:5dc48305d7e733ba0e64eb5c310816f832725c70901c187cd1096e8fa0da0386`.

Executed from `C:/Users/geonj/Documents/PatchLoop`:

```powershell
uv run --locked --offline python C:/pt/feedback25-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/feedback25-live-ready-v1/assess_submission.py
```

## Execution result

Run: `run_dev_f203f76f3abb492a`.
Start: 2026-10-25 04:54:20 KST; finish: 04:58:58 KST.
Elapsed: 278.707 seconds. Task terminal: `INCOMPLETE_RESPONSE`.
The supervisor exited zero after recording the task outcome; that is not repair
success. No hard timeout occurred. Billing and input counting are known.

| Response | Admitted output ceiling | Output tokens | Reasoning tokens included in output | Cost, USD | Incomplete reason |
| --- | ---: | ---: | ---: | ---: | --- |
| Initial | 25,000 | 25,000 | 25,000 | 0.120383700 | max_output_tokens |
| Protocol correction | 25,000 | 25,000 | 23,648 | 0.115466250 | max_output_tokens |

Two generation calls and two input-count requests were recorded. Total input was
23,913 tokens, including 10,496 cached input tokens; total output was 50,000,
including 48,648 reasoning tokens. Reasoning counts are metadata, not additional
output to charge again; private reasoning content was not inspected.

Settled cost: USD **0.235849950**, leaving **0.964150050** under the cap. Both
calls received the full configured output ceiling, so monetary admission did
not truncate these responses. The protocol correction requested a valid tool
response at the `needs_original_reproduction` gate. Neither response produced
an executed tool action, and the second incomplete response terminated the run.

| Stage or judgment | Observation |
| --- | --- |
| Source inspections / executed tool actions | 0 / 0 |
| Original acquisition | not_attempted; 0 actual attempts |
| Accepted edits / submitted patch | 0 / absent |
| Stable original-call identity and early replay | NOT_RUN |
| Feedback uptake / repair success | NOT_ASSESSED |
| Public regression / submission verification | NOT_RUN |
| Frozen public missing/present checks | NOT_RUN / NOT_RUN, reason no_submission |
| Independent acceptance / safety | NOT_RUN / NOT_RUN |

The tracked workspace diff is empty. Pure completion projection remains
`unverified`, with zero original cases and `repair_success=not_assessed`.
The post-submission assessment entry point ran and recorded ineligibility; it
executed no checks or model calls. No missing result is relabeled as PASS or FAIL.

## Interpretation and limits

The prior cap-only sample used the same model, output ceiling and monetary cap,
and reached edits/submission without an incomplete response. The current sample
failed at an earlier stage. That contrast is descriptive: one stochastic sample
per implementation on an exposed dev-train task cannot attribute the difference
to the implementation or establish a general regression.

The immediate observed failure is an unfinished response at the output ceiling.
Prompt/tool formulation and model generation behavior remain possible contributors;
neither is isolated here. Runtime replay, caller argument construction, repair
semantics and independent acceptance were not exercised. Prior local evidence
remains local; this run adds no live evidence for feedback adoption or repair gain.

## Evidence and collection

- Preparation: `C:/pt/feedback25-live-ready-v1`, including frozen `plan.md`,
  `request.json`, `preflight.json`, `authorization.json` and preparation journal.
- Run: `C:/pt/feedback25-live-v1`, including process receipts, CLI result, public
  assessment, collection, public analysis and append-only `dev-run-v1` journals.
- Collection: `sha256:d82d0be3f9236b6d230941827c137d39eeee0d32337bc810ee6821e6ff3fea5f`.
- Public analysis: `sha256:5adac47736ef6421fd6724868f826a185c257191ff9e360af9fbcc3f6b2f223f`.
- Public collector: `sha256:98027628429a2a090cb6596a1e462a849771db099b7925a5ff76c716e87d03c8`.
- Analysis code: `sha256:0626f96b7fcc93c99f9c364a83dac4a5ba5f2e5c17def6c424361c52f396b187`.

Collection verified the three journal chains, 27 content-addressed objects,
frozen source/configuration identities and complete dispatch/count/billing pairs.
There were no mutation/check actions to recover. Provider continuation bytes were
hashed opaquely; private evaluator content and reference patches were not read.
The collection and separate public analysis were stored by content hash, and
allocation closure was recorded in both operator and preparation journals.

This follow-up changes documentation only. The implementation's local validation
remains recorded in its separate history entry; long runtime tests were not repeated.
Documentation layout validation passed all five tests; its receipt is
`C:/pt/feedback25-live-v1/docs-tests.xml`. The final documentation commit is recorded
separately under the run root. Historical experiment files and user-owned edits
are preserved.
