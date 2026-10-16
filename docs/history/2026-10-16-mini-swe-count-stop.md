# mini-SWE-agent dev20 attempt: stopped before grading

Date: 2026-10-16. Allocation CLOSED_ON_COUNT_FAILURE; official=false and
claim-ineligible. This is an execution failure, not a 0/20 repair result.
The requested external-agent performance comparison remains unmeasured.

## Question, approval and frozen conditions

The user selected all 20 existing SWE-bench Lite development tasks to establish
an external-agent baseline against saved PatchLoop results. A simpler independent
agent could help distinguish PatchLoop-specific difficulties from shared task
difficulties, without presupposing a memory or prompt intervention. The comparison
was descriptive: tools, context management, edit policy and timeout accounting
would differ, so even completed outcomes would not identify a single causal feature.

After [preparation](2026-10-16-mini-swe-baseline-preparation.md), the user explicitly
approved the USD 24 cap and the experiment-only isolated-container bash exception.
The original no-retry, no-resume, no-replacement and stop-all conditions remained.

- Frozen checkout: `837e54750e2c4918c05782155cebd717a02d0408` at
  `C:/Users/geonj/.codex/worktrees/mini-swe-dev20/PatchLoop`.
- Execution implementation: `a6987993513a9f5bf38cc6b555db42bd37097b1b`.
- Canonical packet:
  `sha256:3e17672013e891246a91dd160650dbde81a758f7c5d53e3ab19986833b721132`.
- Preparation: `C:/pt/mini20prep04`; fresh live root: `C:/pt/mini20live01`.
- Agent: mini-SWE-agent v2.4.6,
  `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`, with the pinned upstream loop,
  SWE-bench prompts and Responses action/observation formatting.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output ceiling 25,000,
  default service tier, global OpenAI endpoint, exact primary-repository `.env`.
- Twenty tasks, one fresh attempt each, one worker; USD 1.20/task and USD 24 total,
  no transfer; 40 generations and 100 shell actions/task. Solver 1,470 seconds,
  separate native grading allowance 330 seconds with a 300-second test timeout.
- Existing digest-pinned images only. Offline container, read-only root, no host
  mounts or credentials, public source archive in tmpfs, synthetic one-commit Git.
  The agent received no private evaluator material or historical solution evidence.

The authorization was persisted and journaled before dispatch. Source/dependency,
task, archive, image, pricing and native-harness bindings passed before execution
and again during the read-only closeout. The frozen checkout remains unchanged.

## Execution outcome and accounting

Only row 1, `marshmallow-code__marshmallow-1343`, started. The first input-count
request succeeded; the first generation returned the exact model/default tier,
completed status and matching usage. One public file-inspection bash action ran.
The second input-count request then raised `BadRequestError`; no second generation
was dispatched. The driver stopped the whole panel and confirmed container removal.

| Axis | Observed result |
| --- | --- |
| Planned / started / not started | 20 / 1 / 19 |
| Count requests | 2: one success, one error |
| Generated responses / settled responses | 1 / 1 |
| Shell actions | 1 completed public inspection |
| Submissions / native evaluations | 0 / 0 |
| Native / registered / registered safety | NOT_RUN for all 20 |
| Model-token cost recorded | USD 0.002403 |
| First row including cleanup | 6.962199 seconds |
| Solver container cleanup | CONFIRMED; exact container absent on audit |
| Automatic retry, resume or next panel | None |

The recorded generation used 2,022 input tokens, zero cached input tokens and
197 output tokens. Recalculated cost is 2,403,000 nanodollars, below the
114,016,500-nanodollar dispatch reservation and the row cap. There is no unmatched
generation dispatch. The raw result conservatively has `billing_known=false`
because the adapter also marks count failures uncertain. That flag is preserved;
the audit separately establishes durable usage for the sole generation. It does
not claim provider-invoice reconciliation or convert the failed count into success.

The model journal runs from 2026-10-16 02:57:48.220583 to 02:57:54.084210 UTC;
container cleanup was confirmed at 02:57:54.296530 UTC. This brief stopped attempt
provides no useful runtime or cost-efficiency comparison with completed panels.

## Reproduced adapter defect and correction

The failed request retained the raw SDK response output as subsequent input.
OpenAI SDK 2.47.0 output serialization included `input[2].status=null` on a
reasoning item and `input[4].namespace=null` on a function call. The corresponding
SDK input types allow omission but reject null. Validating the exact saved objects
locally reproduces both schema errors; omitting null optional fields passes.

The official [token-counting guide](https://developers.openai.com/api/docs/guides/token-counting)
specifies the same input format as Responses. The local type check establishes a
request-shape defect, but the old adapter retained only the exception class, not
the provider error body/code/parameter. The exact server rejection field and any
additional incompatibility remain unconfirmed. No API replay was made to infer them.

The primary checkout's `diagnostics/mini_swe_runtime.py` now omits top-level null
item fields during history projection. It preserves every non-null field, item
order, encrypted reasoning, assistant phase, text, tool-call IDs, argument JSON
(including nested null data), and tool observations. Raw responses remain intact
in content-addressed storage. Count and generation still receive identical input.
Provider failure events now retain status/code/parameter when available without
copying bodies, headers or request contents. Stop rules and zero retries are unchanged.

The existing mock covered a minimal synthetic function call and did not contain
these realistic optional SDK fields. The new regression exercises two turns with
reasoning, assistant commentary and a function call, validates the second request
against SDK input types, and checks raw-history preservation. A second regression
covers diagnostic metadata and excludes a sensitive-body sentinel from the journal.
No solver prompt, tool policy, core PatchLoop runtime or task/evaluator changed.

## Historical comparison

All panels below use the selected mini snapshot/xhigh. Historical results remain
separate observations. No new PatchLoop solve or historical patch reevaluation ran.

| Panel | Native outcome | Registered outcome | Recorded USD |
| --- | --- | --- | ---: |
| Original registered dev20 | 10 PASS / 10 FAIL | 10 PASS / 10 FAIL | 5.01124395 |
| Portfolio full remeasurement | 9 PASS / 11 FAIL | 9 PASS / 11 FAIL | 3.46111455 |
| Previous partial current panel | 8 PASS / 9 FAIL / 3 NOT_RUN | 8 PASS / 8 FAIL / 1 ERROR / 3 NOT_RUN | 5.39413050 |
| Corrected current panel | 11 PASS / 7 FAIL / 2 NOT_RUN | 11 PASS / 7 FAIL / 2 NOT_RUN | 5.08206870 |
| Separate rows 18/20 supplement | 0 PASS / 2 FAIL | 0 PASS / 2 FAIL | 1.07327790 |
| This mini attempt | 20 NOT_RUN | 20 NOT_RUN | 0.00240300 |

The corrected panel's two NOT_RUN rows are not replaced by the later supplement.
The partial panel's registered ERROR/native FAIL is not an agreeing task failure.
Mini has zero matching graded pairs, so no success-rate delta, regression rate,
agent ranking or feature-effect conclusion follows.

Per-task native results are retained below. Every mini cell is NOT_RUN; row 1
stopped before submission and rows 2-20 never started. A dash in Supplement means
the task was not included in that separately authorized two-task run.

| # | Task | Original | Portfolio | Corrected | Supplement |
| ---: | --- | --- | --- | --- | --- |
| 1 | marshmallow-1343 | PASS | PASS | PASS | - |
| 2 | pvlib-1072 | PASS | PASS | PASS | - |
| 3 | pvlib-1154 | PASS | PASS | PASS | - |
| 4 | pvlib-1606 | PASS | PASS | PASS | - |
| 5 | pvlib-1707 | PASS | FAIL | PASS | - |
| 6 | pvlib-1854 | PASS | PASS | PASS | - |
| 7 | pydicom-1139 | FAIL | FAIL | FAIL | - |
| 8 | pydicom-1413 | FAIL | FAIL | PASS | - |
| 9 | pydicom-1694 | PASS | PASS | PASS | - |
| 10 | pydicom-901 | FAIL | FAIL | FAIL | - |
| 11 | astroid-1196 | PASS | PASS | PASS | - |
| 12 | astroid-1268 | FAIL | FAIL | FAIL | - |
| 13 | astroid-1333 | FAIL | FAIL | FAIL | - |
| 14 | astroid-1866 | FAIL | FAIL | PASS | - |
| 15 | pyvista-4315 | PASS | PASS | PASS | - |
| 16 | sqlfluff-1517 | FAIL | FAIL | FAIL | - |
| 17 | sqlfluff-1625 | FAIL | FAIL | FAIL | - |
| 18 | sqlfluff-1733 | FAIL | FAIL | NOT_RUN | FAIL |
| 19 | sqlfluff-1763 | FAIL | FAIL | FAIL | - |
| 20 | sqlfluff-2419 | PASS | PASS | NOT_RUN | FAIL |

## Validation, evidence and decision

- Adapter/documentation focused checks: 25 passed in 1.35 seconds. Broader focused
  usage/accounting/adapter/documentation regression group: 89 passed in 38.36
  seconds; Ruff passed. Documentation closeout has a separate validation receipt.
- Exact saved-request schema replay: both original violations reproduced; corrected
  input passes, original request unchanged, all non-null fields preserved, zero
  provider calls. Corrected request is retained for review, not dispatched.
- Actual pinned DefaultAgent plus real SDK response objects completed two mocked
  count/generation turns and submitted a harmless comment patch. Unchanged isolated
  native grading returned the expected FAIL, scope PASS, cleanup CONFIRMED. This is
  an operator negative control, not a mini task result. Real provider calls/cost: 0.
- Two preceding mock fixture construction failures are preserved: missing SDK item
  `type` and required usage `cache_write_tokens`. Both occurred locally before any
  real model or evaluator work. The corrected fixture is `mock_control03.py`.
- The preparation full suite remains 5,116 passed / 19 skipped. It predates this
  adapter correction and is not presented as a rerun; the focused group and upstream
  mock cover the delta. Core PatchLoop source and native grading are unchanged.

Closeout root: `C:/pt/mini20stop01`. `audit.py` and `audit.json` verify frozen
bindings, approval timing, journal chains, unique dispatch/usage, stop ordering,
all-20 dispositions and cleanup. `comparison.json` retains every task/panel axis,
source hashes and zero comparable pairs; saved historical comparison input hashes
were checked again. `schema-replay.json` binds the failed request and local schema
check. `mock-native-control03/smoke.json`, JUnit receipts and `closeout.json` bind
validation and the final commit. The live summary and all earlier preparation,
response, journal and historical artifacts remain unchanged.

The performance-baseline question remains open. This run changes the adapter
compatibility decision only: normalize absent optional values and test realistic
multi-turn response shapes before another live attempt. It supports no change to
PatchLoop repair strategy or defaults. The remaining empirical question is whether
the corrected request is accepted by the provider before a fresh baseline run.

No count retry, paid regeneration, resumed task, replacement task, fresh panel,
test300 run or publication is authorized by the unused allocation. Fresh execution
requires a new exact approved packet; this stopped attempt must remain visible.
