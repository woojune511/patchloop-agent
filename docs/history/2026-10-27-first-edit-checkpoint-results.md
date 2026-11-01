# First-edit context A/B: accepted repair in A, failed hypothesis in B

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved execution, monitoring and public-evidence audit
- Origin Date: 2026-10-27
- Verification Status: LIVE EXECUTED; A isolated acceptance PASS; B FAIL
- Runtime implementation: `ed766efd`; execution checkout: `f61f8a04`
- Authority: [sealed plan](2026-10-27-first-edit-checkpoint-plan.md), explicitly approved
  manifest `sha256:6d226daa596dff15b612e28a7bc074d0d73d79adc1003d533620be827a1da19b`

## Question and executed boundary

The previous trial acquired public caller source and a useful helper observation,
then exhausted output before its first edit. This pair tested whether losslessly
representing duplicate public context changes that first-edit outcome. A retained
duplicates; B stored identical facts/source lines once and referenced them.

Both restored the same public post-helper checkpoint and saved candidate for
Astroid-1333, `dev-train/current-dev20/13`, official=false. Both used
`gpt-5.4-mini-2026-03-17`, xhigh, repository `.env`, fresh two ordinary responses,
one correction, two model tools and one new edit. No additional model helper or
original-selection requests were available. Input/output limits were 60K/40K;
correction output 25K, model/intermediate checks 600 seconds, final public/isolated
checks 390 seconds each. A then B, exactly once, under $1.20 each/$2.40 total.

Before dispatch, the manifest, script and input identities were revalidated and
the explicit approval was recorded. The collector exited zero. There were five
completed input counts, three started/settled generation calls, zero correction
calls and no count/transport/billing/execution uncertainty. No retries or extra
conditions ran. The new allocation is closed; earlier unknown charges remain
separate. Source/runtime stayed unchanged throughout execution.

## Results

| Outcome | A: duplicate context | B: lossless references |
|---|---:|---:|
| First input tokens | 56,199 | 36,887 |
| First output tokens | 25,417 | 24,870 |
| First generation seconds | 182.88 | 188.83 |
| Accepted new edits | 1 | 1 |
| Original F0010 | resolved | retained |
| Public cases | 5/5 PASS | 2/5 PASS |
| Public regression | PASS | PASS |
| Isolated task acceptance | PASS | FAIL |
| Isolated regression/scope/safety | all PASS | all PASS |
| Model terminal | INPUT_LIMIT | AGENT_STOPPED |
| Model/intermediate-check seconds | 208.56 | 314.39 |
| Model through final checks seconds | 328.91 | 436.39 |
| Settled cost | $0.15652575 | $0.25177050 |

Total settled cost: **$0.40829625**. No usage in this pair is unknown. Both
candidate hashes remained unchanged through final evaluation. A's accepted
candidate is `sha256:a249bfea69d7f903616db62e90fa6658bbf06a86879ae3b0d2132b70c4cb20ea`;
B's failed candidate is
`sha256:5d150b840fcdc0adf00a23dedd8efe17a45a760d07b2d2ba45167281861c760f`.
These are complete candidates including the restored seed, not just new edits.

## What the model changed and what verification established

A normalized explicitly supplied search paths in
`astroid/modutils.py::modpath_from_file_with_callback` using `_cache_normalize_path`.
Its public tool hypothesis connected relative `.` search roots to the observed
absolute-root helper result. The original failure disappeared with first-call
identity preserved, unchanged control output and no unexpected exception. Public
empty/import/syntax cases selected and attempted to parse child modules, guarding
against silent success from skipping the child. Direct/package controls and all
five public cases passed, followed by independent isolated task acceptance.

For A, second-call input identity was false while its control output stayed equal.
The existing comparison reports that separately because the first call can create
cache files inside the input tree. Do not describe both calls as having identical
inputs. First-call identity, public case controls and isolated acceptance provide
the separate positive evidence reported here.

B instead changed `PKG_DIRECTORY` handling so a missing initializer returned a
`PY_NAMESPACE` classification. That hypothesis did not repair the original caller.
Direct/package controls passed, but empty/import/syntax cases retained F0010 and
did not select or parse the child. Public regression still passed, illustrating
again why regression alone cannot establish task repair. Isolated acceptance failed.

B's new lines 633-635 had no observed entry in the original-call instrumentation.
The public receipt was untruncated and complete, but its explicit coverage is
Python launch-thread line events across the original calls. This supports only
"no observed entry in the measured execution," not proof of global branch coverage
or absence in another thread. No extra tracing experiment was run.

## Post-edit feedback and the remaining implementation defect

A's next request counted 65,982 tokens, 9,783 above its first input and over 60K.
The completed edit exchange added 31,161 JSON characters, including 24,753 in
`revalidated_spans`; the edit's new text itself was only 308 characters. Fresh
original-call feedback added another 3,688 characters. The fixed initial evidence
was also still present.

The generic handoff attempt produced exactly the same counted request/hash, so
recounting again returned 65,982. The checkpoint request builder extracts completed
public exchanges and retains the fixed evidence; it does not consume the generic
handoff's replacement state. Thus a handoff was prepared but not committed. There
was no second generation and the model never received its successful original-call
result in a dispatched follow-up request. Host verification nevertheless evaluated
the actual edited candidate and established task acceptance. Accepted repair and
successful model completion flow are distinct outcomes here.

B's follow-up counted 46,645 tokens and was dispatched with exactly the fresh
failed original-call receipt. It returned `stop_task`, explicitly acknowledging
that the candidate still failed and no edit tool remained. This final response
used 17,157 output tokens and 102.21 seconds. It is evidence of failure-feedback
delivery and acknowledgement, not successful revision: the one-edit design did
not permit another repair. B's larger total cost includes this second response,
which A could not execute, so total cost is not a clean per-call compression effect.

## Decision and remaining question

Both conditions reached a first edit below the ordinary 40K output cap. A's success
shows that duplicate context did not necessarily prevent a repair. B reduced first
input by 34.4% and enabled feedback delivery, but did not improve repair correctness
in this pair. Lossless facts do not imply identical reading order, salience or
reference-following effort. With one fixed-order pair and stochastic responses,
the different repair hypotheses cannot be attributed confidently to representation.
This result does not justify adopting the reference representation as a repair
quality improvement or rejecting all context deduplication.

The demonstrated next implementation issue is narrower: repeated revalidated source
inflates post-edit input, and the generic handoff is ineffective for this checkpoint
builder. Preserve the successful candidate and address that delivery contract before
funding another broad repair search. No such implementation or further paid run is
included in this result. The 30-second correction floor was not exercised live;
its support remains the preceding local boundary tests.

A is a real model-authored accepted repair under saved public evidence, not a fresh
benchmark solve, held-out result, general success rate or proof that the newest
harness change caused repair. The known operator solution and private evaluation
details were excluded from model input. Historical failures remain intact.

## Evidence and audit

- Result: `C:/pt/first-edit-checkpoint-run-v1/result.json`
- Result hash: `sha256:4287b3b325e5dc23255b63f13273df1df7e7424b33a3bbdf0d4b4b5cd3ab4958`
- Approval: `C:/pt/first-edit-checkpoint-plan-v1/approval.json`
- Public analysis: `C:/pt/first-edit-checkpoint-analysis-v1/public-analysis.json`
- Candidate exports: `C:/pt/first-edit-checkpoint-analysis-v1/A-candidate.patch`
  and `B-candidate.patch`, each verified against the evaluated hash.

The public audit validates journal chains, call/count pairing, cost sums and
current-diff receipts. An independent read-only review confirmed the same outcome.
Analysis used public requests/tool/check records and top-level evaluation verdicts;
it did not read opaque provider responses or private evaluator artifacts. No
runtime code changed after preparation. Documentation validation passed five tests
in 0.12 seconds; manifest revalidation and whitespace checks passed. Full code tests
were not repeated for the documentation-only update.
