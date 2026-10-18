# Public caller uptake and repair: bounded comparison

Status: **LOCAL PREPARATION IMPLEMENTED; PAID NOT AUTHORIZED** (2026-10-18).
Readiness authority is the final-commit external packet and its validation receipts,
not this prose. See [preparation record](../../docs/history/2026-10-18-caller-ready.md).
Preparation uses public wheels and existing images without provider/count calls.
Old allocations are closed; neither their approvals nor unused balances transfer.

## Question and evidence

Does making the original public caller available lead the model to obtain and use
relevant failure-path evidence, and does that intervention improve actual repairs?
These are separate outcomes: access is not use, use is not correct interpretation,
and a supported interpretation or successful probe is not a repaired task.

The [local caller check](../../docs/history/2026-10-18-caller-check.md) ran installed
Pylint 2.12.2 against Astroid base and the saved E1J1 candidate. Both retained the
reported F0010; only the candidate passed its helper. The initializer-present
control passed in both. The [earlier repair panel](../../docs/history/2026-10-18-repair-mechanism-results.md)
did not acquire the caller link and showed no acceptance improvement from E/J.
This motivates an acquisition comparison, not another retention/prompt ablation.

Competing explanations are useful caller evidence was inaccessible; it becomes
available but is not used or is used with the wrong setup; it is acquired but lost
before a decision; it is delivered but overinterpreted; or the remaining repair
problem/resource limit persists despite appropriate use. A correct repair without
caller use would show the caller was unnecessary for that solve. A baseline which
already solves as often would weaken the intervention's practical benefit here.

Only the development-exposed Astroid-1333 task is selected, because it supplies
this demonstrated gap. Six repetitions per arm replace the previous three-task,
four-arm, one-repeat allocation: the same 12 rows and USD 10.56 ceiling. Repetition
measures local variability; it provides no cross-task or held-out generalization.
No production logic is specialized to Astroid, Pylint, a filename or an expected fix.

## Two fresh conditions on the same runtime

| Arm | Probe environment | Model-visible caller support |
| --- | --- | --- |
| A | Common Python/source/transitive packages; no Pylint distribution or source | Current caller-free tool description; no prepared-caller entry |
| B | Identical common environment plus pinned `pylint==2.12.2` | Existing prepared-caller metadata and generic `probe_callers.description` |

Both use the current product E/J behavior. Neither reuses an old ablation checkout,
saved patch, conversation, continuation, operator question, note or plan. The task
text is unchanged. B receives no diagnostic program, failing trace, path-normalization
hypothesis, answer, reference patch or extra evidence reference. The model chooses
whether and how to inspect/invoke the caller using existing registered tools.
No forced check, extra response, new gate or operator rescue occurs during a solve.

The treatment is the existing **availability plus generic disclosure** bundle.
This two-arm study cannot isolate installation from its description, prove an
individual repair's cause, or estimate judgment skill conditional on forced evidence.
The generic description's extra bytes are a treatment cost within unchanged bounds;
do not pad A or truncate B to manufacture equal prompt length.

Do not use the old Python 3.10/no-Pylint logs as A. Prepare both arms afresh with
`diagnostics.legacy_probe_metadata.prepare`, the same source root `astroid`,
`runtime_profile=python39-v1`, and the following identical operator supplements:

```text
isort==5.13.2
lazy-object-proxy==1.12.0
mccabe==0.6.1
platformdirs==4.4.0
setuptools==80.9.0
toml==0.10.2
typing-extensions==4.16.0
wrapt==1.13.3
```

B additionally sets `caller_requirements=["pylint==2.12.2"]`; A leaves it empty.
Pins come from the already checked public bundle, not future outcomes. Supplemental
roots remain operator declarations, separate from repository requirements. Ordinary
dependency checks stay enabled; B excludes only the source-supplied Astroid package.
This uses supported preparation inputs; never delete installed files or edit a
published descriptor to simulate A.

Before dispatch, compare wheel identities and every installed common file, including
workspace metadata. The only installed payload differences allowed are files owned
by the verified Pylint wheel and its declared console scripts. Bind that allowlist
from the wheel RECORD/entry-point metadata before running capabilities. Generated
lock/provenance/descriptor differences must correspond exactly to the caller input;
common source metadata, packages, import paths and executable bytes must match.
Compare actual initial requests: differences are limited to caller discovery/tool
description and their dependency identities. Normalize only declared row/run IDs
and temporary workspace paths, recording exact field replacements and original
payloads. Stop if other behavioral differences appear; do not silently expand the
allowlist after an outcome.

Same pinned image in both arms:
`python@sha256:dad5b29e3506c35e0fd222736f4d4ef25d21b219acdd73f7bb41d59996ca8e0d`.
The prior check observed Python 3.9.25/Debian 13. Verify this again; it differs from
the issue's Python 3.9.1/OS. Astroid source is the task snapshot, not a released
distribution; its version compatibility remains explicitly unverified. Check each
selected distribution/origin individually, not a last-write-wins metadata dictionary.

## Fixed task, model, resources and order

- Task: `tasks/dev-train/current-dev20/13/public.yaml`,
  `swebench-lite-dev-pylint-dev-astroid-1333`, base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
  Prepared source: `C:/pt/ld20p01/s/13/prepared-source.json`; revalidate its identity.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens,
  standard/global Responses, `store=false`, zero SDK retries. Preserve the previous
  experiment's model; this does not change the general baseline model.
- Later credential file: `C:/Users/geonj/Documents/PatchLoop/.env`. No credential
  contents, provider availability check, input count or model request is read/sent
  during this specification work.
- Per row: **40 model calls, 100 actions, four accepted mutations, 1,800 seconds**,
  including the same **330-second evaluation reserve**. All other DevLimits stay
  unchanged. Source/test edits share the same mutation budget; no counter resets.
- **A: six fresh rows; B: six fresh rows. USD 0.88 per row, USD 5.28 per arm,
  USD 10.56 invocation-wide.** Every resolved request uses `repeat=1`, a separate
  state root/workspace and one fixed row allocation. No cap transfers, top-ups,
  replacement rows, manual retries, resumes, continuations or paid judges.
- `segmented-v1`, `result-or-size-v1`, `brief-v1`, current agent policy; probes on,
  probe-policy `none`, probe-recheck `none`, repair-recheck on, protected-v1
  inspection and per-call-v1 cost admission. Keep current evidence-selection and
  note/plan behavior; no additional active question or instruction is inserted.
- At most **two references**, one primary and one countercheck; identical validation,
  expiry, rebinding and diff-scope rules. Retained source **24,000 characters**,
  counted input **60,000 tokens**, request **1,048,576 bytes**, encrypted item
  **262,144 bytes**. Preserve 8,000 base/10,809 combined brief prompt characters and
  all existing schema/note bounds. Actual transition indices may differ as content
  grows; the algorithm and thresholds must be identical, not forcibly synchronized.
- Probe caps remain **30 seconds, one CPU, 512 MiB, eight PIDs, 8,000 source
  characters/32,000 source bytes, 12,000 output bytes**, offline/read-only/no child
  process. The caller gets no network, installation or unrestricted shell tool.

Use six serial blocks, settling billing, solver cleanup and the due registered
evaluation receipt before admitting the next row. Later native/caller assessments
remain pending until the public audit is sealed. The existing two-worker ceiling
is not increased; this design uses one worker. These are order blocks, not matched
random seeds or independent task samples.

| Block | First | Second |
| --- | --- | --- |
| 1 | A-r1-t13 | B-r1-t13 |
| 2 | B-r2-t13 | A-r2-t13 |
| 3 | A-r3-t13 | B-r3-t13 |
| 4 | B-r4-t13 | A-r4-t13 |
| 5 | A-r5-t13 | B-r5-t13 |
| 6 | B-r6-t13 | A-r6-t13 |

The [official standard pricing table](https://developers.openai.com/api/docs/pricing)
was fetched on 2026-10-18: per million tokens, USD 0.75 input, 0.075 cached input,
4.50 output for GPT-5.4 mini, matching the registered runtime rates. The maximum
60k-input/25k-output uncached reservation is USD 0.1575; USD 0.88 does not fund
40 such calls. Count immediately before dispatch, reserve uncached cost, settle
actual usage once, and record output-ceiling reductions/cached tokens. Revalidate
rates before any later authorized run; mismatch stops admission, not raises a cap.

## Public mechanism audit, sealed before outcome inspection

Audit only public task/source, actual requests, tool programs/results, explicit
decisions, plans/notes and submitted diffs. Do not inspect/decrypt reasoning or infer
hidden beliefs from silence. Keep records outside solver state; the audit has no
feedback channel. Seal all public annotations before opening fresh registered/native
grades or post-run caller checks. Execution can store sealed grades earlier; filter
grade-bearing terminal fields from the audit export. Arm/prior-result blinding is
not claimed; any accidental fresh-grade exposure must be recorded.

Record independent axes with YES, NO_OBSERVED, UNKNOWN and NOT_RUN as applicable.
Incomplete output is UNKNOWN, not evidence of non-use. A has caller absence by
design; that is not an acquisition attempt, model error or infra failure.

| Axis | Required public evidence; do not substitute |
| --- | --- |
| Availability/disclosure | Verified arm capability plus exact request containing its tool description/environment. Installation alone does not prove delivery. |
| Inspection | Model-authored action obtains real caller identity, entry/source or setup evidence. Naming Pylint in a plan, successful import or copied code alone does not establish path inspection. |
| Relevant caller execution | Executed installed entry or source-equivalent direct Run invocation on current source with the public directory argument, cwd, layout and relevant environment. A reduced helper or copied/mocked implementation does not qualify. |
| Failure/control evidence | Separately mark original failure reproduced, normal control executed, and current candidate tested. Bind observed exit/message/analysis target, not merely probe `passed` or an assertion about a helper. A successful first candidate can be verified without having reproduced base first. |
| Actual delivery/retention | Identify material source/output in the full request immediately preceding the decision, including native exchanges, observations and handoffs. Journal presence, citation or earlier-segment presence alone is insufficient. |
| Interpretation/action | Explicit conclusion respects the executed scope, distinguishes unsupported hypotheses, and takes a relevant next action or preserves an open gap. Link any revision, check, edit and eventual submitted diff. |

Relevant setup covers caller version/origin, workspace source origin, real entry,
arguments, cwd, import-path effects, configuration/environment and input layout.
For this issue: `src/__init__.py` exists, project init is absent, child may be empty,
and the relative directory argument is `src/project` from its root. Compare a normal
input through that same caller. Do not require the old failing internal branch
after a legitimate fix; review the model's program and observed entry/arguments.
A probe that never emits adequate setup/outcome evidence remains partial/unknown,
even if an operator can later supply missing facts. No prescribed probe sequence
or minimum check count is imposed on the solver; source-supported repairs are valid.

Define **source uptake U_source** as relevant real caller source/setup delivered
to a subsequent public decision and used in a supported, scope-correct inference
or action. Define **execution uptake U_exec** analogously for the result of a
qualifying caller execution. **U = U_source or U_exec**; record both components.
This credits useful caller-source reasoning without pretending it executed the
failure. Inspection alone, copied text or a plan mentioning the caller is not U.
Report reproduction, control and post-edit validation separately; U does not
require all of them. Classify the response as diagnosis, counterexample handling
or verification-only. Valid refusal to overclaim is uptake, not repair success.

For a counterexample-handling claim, require a real current-diff failure, its
material content in the next actual request, and a decision opportunity. Judge
whether the model revises an incompatible claim, tests a competing explanation,
changes the relevant source, or acknowledges the unresolved failure. A failed probe
followed immediately by a budget stop has **NO_DECISION_OPPORTUNITY**, not a judgment
failure. If an edit intervenes, record the version change; a stale failure cannot
by itself refute the new diff. Different decisions in one row are not independent
samples. Conditional uptake/decision subsets are descriptive, never the primary
treatment-effect denominator.

Inventory material evidence lost or displaced at every relevant actual handoff:
`(path, file_hash, lines)` and/or `(action_id, input_hash, diff_hash, output span)`.
Caller text obtained through a probe is a result body, not automatically a retained
repository source range. Classify NOT_ACQUIRED, ACQUISITION_FAILED, PRESENT,
LOST_AT_HANDOFF, STALE_AFTER_EDIT, TRUNCATED or UNCERTAIN, with exact request links.
A loss needs earlier delivery and later absence through every public delivery route.
Do not treat low citations or missing notes as loss. Record accompanying call/edit/
time/cost limits, displaced counterevidence and autonomous reference use; do not
change retention or insert a third reference to repair an observed trajectory.

The operator ledger binds row/arm, event/request/artifact hashes, action/input/diff
identities, probe program/outcome, environment, material evidence, explicit claim,
next action, confidence/uncertainty and reviewer rationale. Include independent
source-supported alternatives and unresolved purposes, not only self-declared plans.

## Repair outcome independent of model uptake

Keep all **12 intended rows**, six per arm. Record dispatched/submitted counts,
required public checks, registered acceptance, native acceptance/agreement, safety,
infrastructure/cleanup, actual cost/time and exhausted limits separately. Preserve
FAIL, ERROR and NOT_RUN; an unsubmitted/stopped row is not a graded failure, but
does not contribute an accepted repair to the intended-row denominator.

After public annotations are sealed, use both original registered and native
isolated evaluations of the immutable submitted patch. Additionally, apply the same
frozen public caller assessment to every submitted source-only patch from A and B,
regardless of caller use or model claims, in the common B environment. A gets that
caller only in post-run assessment, with no feedback to its solver.

The assessment reuses the missing/present programs from
`C:/pt/analyses/astroid-prepared-caller-20261018-v1/`, with SHA-256:

- `program-missing.py`: `6e8c94f7ba40b28dffdf22442d772678b23ce4a1ea1f87f02bed4625a0ee3278`.
- `program-present.py`: `8227ee2f9c9092341de61fefea2b310e9e4e638000eba7261e21ab0a78ef5f4b`.

Require clean execution/setup/cleanup, the installed entry/current-source origins,
intact frozen input conditions, Pylint exit 0, no F0010, and observed analysis of
`src/project/file.py` through Pylint `get_ast` on both inputs. Empty output alone
must not accept silently skipping the target. Do not require the historical
erroneous manager/builder branch; patches can change that route. The observer's
overflow/timeout/truncation is UNKNOWN/ERROR, never semantic FAIL or PASS. There is
no post-outcome program editing or rerun with weaker conditions.

Two post-run probes per submitted patch, at most 24, retain existing probe caps.
They and the native evaluation share the existing **600-second per-row host
assessment allowance**, with native test timeout at most **300 seconds**; do not
add a new 600-second allowance or extend the solver's 1,800 seconds. The registered
evaluation still uses its reserved time inside that 1,800 seconds. Submission and
source-only patch hashes, restored original tests and all assessment bytes are
bound separately. No private content enters caller probes or public audit inputs.

For arm X, report `S_X`: agreeing registered/native PASS out of six intended rows;
`T_X`: both common public caller inputs PASS out of six; and `Q_X`: the intersection
of S and T on the **same submitted diff**, out of six. Report safety independently
and flag any safety/scope failure; no favorable decision may conceal it. Primary
repair contrast is **Q_B - Q_A**, with **S_B - S_A** and control-regression counts
alongside it. Public-only success is not independent acceptance; acceptance with
an unresolved public failure is not a confirmed caller-path repair.

Report B's U count out of all six intended rows, plus eligible decision denominators
and UNKNOWN/NOT_RUN counts. Cross-tab U against Q for every row without discarding
non-users. Compare repair counts across the assigned arms, not successful users
versus non-users: usage is a post-treatment behavior, not randomized treatment.
Historical rows, saved-candidate probes and operator assessments never inflate U
or fresh solve denominators. Six repetitions of one exposed task support local
descriptions only, not statistical significance or a general repair-success claim.

| Observation | Permitted interpretation/next decision |
| --- | --- |
| B available, no qualifying use | Access works; autonomous acquisition remains unresolved. Do not blame evidence-present judgment. |
| Relevant evidence acquired then absent at decision | Observed delivery/retention gap; keep it separate from failure to acquire. |
| Adequate evidence delivered, incompatible explicit conclusion | Evidence-present interpretation failure, if a decision opportunity existed. |
| U improves, Q does not | Uptake demonstrated; repair gain not demonstrated. Inspect remaining source/verification/resource failure. |
| U_source and Q improve without U_exec | Caller-source reasoning has local support; execution-based failure-path validation is unestablished. |
| Q improves without qualifying U | Local outcome difference; the proposed evidence-use mechanism is unestablished. |
| Caller repair passes but acceptance fails, or vice versa | Scope mismatch remains; neither axis substitutes for the other. |
| U and Q improve with supporting trajectories | Mechanism-consistent local signal, not mediation proof or automatic adoption. |

A favorable local signal requires Q_B > Q_A, qualifying U in at least two B repairs
on independent fresh rows, complete agreeing grades for submitted patches, settled
cost/cleanup and no concealed normal-control or safety regression. An early stop,
missing assessment or unexpected environment difference blocks that conclusion.
Zero/negative quality contrast closes this allocation without another adjacent
prompt/context tweak, extra repetitions or spending the remainder. Any new study
needs a new evidence-based question. No result automatically changes defaults.

## Preparation gates and execution boundary

The design baseline is `96179c5e91316239a5a8395e8a0fd224f67f67e3`, runtime content
`20fb1541d4b2aa5c2f5af6e67f74546ae8762f74c4325988535dc7202075bf0a`.
The original design changed no runtime. The execution manifest must bind
the actual final source commit/runtime, protocol bytes, 12 requests/order/caps,
task/public/source identities, both complete dependency inventories, image digests,
tool/model hashes, all assessment programs/rubrics, driver/test receipts and pricing.
Hash private assets opaquely only through evaluator tooling; never inspect or copy
them into model/audit context. Preserve the existing uncommitted AGENTS edit.

Provider-free readiness gates, before requesting any paid authorization:

1. Build matched A/B descriptors at fresh external roots; verify file-level isolation
   and effective common package origins. A must not find/import Pylint; B must use
   the pinned package and current workspace source. No image acquisition.
2. Calibrate B's public assessment on unchanged base, the exact saved helper-only
   candidate and normal controls. Both wrong states must remain rejected despite
   helper PASS. Preserve the already recorded inputs/results. The earlier check has
   no successful missing-input repair control; record this limitation, and use
   synthetic parser fixtures for exit/message/target/UNKNOWN classification rather
   than importing a private reference patch or inventing a repair for calibration.
3. Validate first-request differences, hash bindings, fixed row/arm/global caps,
   stop propagation and audit/grade separation provider-free. Reuse supported
   preparation/panel paths; do not repurpose seeded `uptake_execution` as fresh
   solves or silently reuse the old E/J manifest. Any needed orchestration/collector
   adaptation is a separately testable preparation step, implemented in the operator
   modules listed below.
4. On the final implementation, run focused checks, Ruff, the full suite and mock
   smoke through isolated evaluation, binding their results to the manifest. No
   source/cap adjustment after seeing pilot trajectories; refresh exact bindings
   and authorization scope if readiness work changes the runtime.
5. Publish immutable external `dev-run-v1`/CAS preparation evidence with readiness,
   failures and NOT_RUN axes. Only then freeze a new execution packet with
   `paid_authorized=false`; this prose is not a runnable or authorized manifest.

Before each later dispatch recheck exact identities, tracked runtime/task/lock
cleanliness, available pinned images, current reviewed rates and the full settled
cost ledger. Stop all remaining admissions on count, transport, billing, encrypted
continuation, runtime/identity or cleanup uncertainty, or a missing/mismatched
receipt that is already due. Deferred native assessment is not a missing due
receipt. A disagreement discovered after the audit stops remaining assessments
and blocks a favorable conclusion; it cannot retroactively stop completed solves.
Keep known settled row-local budget/completion stops local, with original terminals
and no replacement; subsequent fixed rows may proceed.
No retries, automatic resume, provider-based judging or follow-up spending.

No paid execution occurs until the user authorizes that exact final packet, task,
model, credential path, repetition count and positive invocation-wide cap. This
follows the repository's live gate and the user's explicit no-paid instruction.

## Prepared operator path

`diagnostics/caller_uptake.py` constructs the twelve fresh requests, freezes a new
packet and revalidates exact identities. `caller_uptake_prepare.py` compares complete
common installed files and the wheel-derived caller additions, and intercepts real
initial request construction before counting. Its offline clock is fixed equally
for both captures to avoid host preparation jitter; only the exact generic caller
description and derived segment identity are normalized. Full source/context state,
tools, limits and model flags must otherwise agree. Final captures require normal
HEAD cleanliness; any earlier development capture is not readiness evidence.

`caller_uptake_execution.py` uses the existing coordinated worker for one row per
serial wave, with fixed invocation reservations and no transfers. Registered receipt
validation is due before the next row; its grade remains outside the public export.
The export binds the actual dispatched request (including any admitted output ceiling)
and public actions/decisions, while omitting evaluator/terminal records and replacing
opaque reasoning items with hashes. Public annotations must be sealed before the
common caller/native assessments can start. The latter share one 600-second allowance.

`caller_uptake_grading.py` handles frozen receipt parsing, annotation lineage and
intended-row S/T/Q/U accounting. Human interpretation remains necessary; a valid
annotation schema is not proof that a claim is correct. Local parser/stop fixtures and
saved-log exports are calibration, not fresh model-use or repair outcomes. The packet
binds the final commit, complete preparation/validation receipts and pricing evidence;
`paid_authorized=false` remains immutable. Separate exact human authorization is
required by `collect`, followed by a current official-price review. There is no paid
execution in `freeze`, `validate`, initial capture or the test suite.
