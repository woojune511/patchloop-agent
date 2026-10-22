# Executable caller linkage OFF/ON on Astroid-1333

Status: implementation prepared, 2026-10-22. **No paid authorization.**
The executable packet is valid only with its final-commit qualification receipts and manifest hash.
This is a fresh proposed allocation; all prior allocations remain closed. This
document authorizes no provider/counting call, assessment or experiment resume.

## Question and evidence

Does executable linkage between a declared verification target and its actual
call/inputs/environment lead to faithful verification, fewer wrong completion
claims and more accepted repairs within the same resources?

The closed [role comparison](../../docs/history/2026-10-22-verification-role-results.md)
had accepted repairs A/B 0/3. B2 declared an original caller but executed helpers;
its receipt already reported zero observed declared calls and `not_compared`.
The final claim still overstated coverage. A's lower assigned claim-error count
was caused by one missing submission/claim, not better judgment.

The [new implementation](../../docs/history/2026-10-22-probe-call.md) directly
invokes the declared target, compares recorded conditions across edits, and retains
execution linkage in handoffs. It passed local controls and replayed 149 historical
inputs without changing old grades. These results do not establish model uptake.

Plausible remaining bottlenecks are nonselection despite an opportunity, selecting
the wrong caller/conditions, failing to construct an executable probe, ignoring
correctly delivered evidence, and insufficient repair ability/resources. Correct
use with unchanged repair outcomes would support the mechanism but not repair
improvement. Failure to use an offered feature is not proof of low reasoning ability.

## Treatment and common architecture

Both arms use **one repair conversation with the same mandatory verification phase**,
equivalent to the previous role controller's same-context mode. Hold that choice
fixed: the previous comparison provided no evidence to adopt an independent verifier.
Experiment arm B must not be passed through as role-controller mode B.

Use one final implementation derived from `1b7d53c713bb956234834779324c533cfd5a74e1`.
Build a diagnostic OFF adapter against the exact pre-change behavior at
`50b91b511d5a3d64d1365bacfa3203eda3a85aad`; do not compare whole repository revisions.

| Arm | Original-requirement execution | Comparison and current-state disclosure |
| --- | --- | --- |
| A: linkage OFF | Prior `record-observation-v1`: model writes the call; the legacy name observer records what it can observe. | Prior argument/cwd/sys.path pairing and prior review, without new execution links or replay-ID disclosure. |
| B: linkage ON | `invoke-declared-call-v1`: model uses `call_target`; the declared public callable is resolved and invoked with recorded inputs/selected environment. | New condition identity, bounded execution-link preview/hashes and replay ID. |

Both retain `purpose`, `record_observation`, verification-state separation ON,
legacy recovery support, helper probes, identical registered tools/argument schemas,
the same system/phase instructions and report schema. A can directly call the
original public caller and replay it. Its lack of B-only fields is not nonuse or
failure. Do not deliberately break or remove A's existing replay capability.

The treatment includes invocation guidance, execution/condition accounting and
handoff disclosure as one implemented change. It does not isolate their individual
effects. The larger observer and description consume existing limits; their cost,
source rejection and evidence displacement are treatment effects, not padded away.
No third condition, extra model, forced `call_target`, automatic reproduction,
new finish gate, test hint or task-specific runtime branch is included.

## Task, allocation and unchanged resources

| Binding | Proposed value; not authorization |
| --- | --- |
| Task | `tasks/dev-train/current-dev20/13/public.yaml`; `swebench-lite-dev-pylint-dev-astroid-1333`, dev-train |
| Repository base | `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a` |
| Model | `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 |
| Credential file | `C:/Users/geonj/Documents/PatchLoop/.env`; never copy its contents into evidence |
| Repeats/order | A 3, B 3; six fresh isolated rows, repeat=1; serial A1 B1 B2 A2 A3 B3 |
| Spending ceilings | USD 0.88/row, 2.64/arm, **5.28 for the entire new allocation** |
| Local post-collection assessment | At most twelve caller checks and six native evaluations, one worker |
| Proposed future packet/live roots | `C:/pt/probe-invocation53`, `C:/pt/probe-invocation53-live`; must be fresh at freeze |

Fresh controls are required; prior A runs are context, not new controls. Repetition
IDs are not paired random seeds. Run-local notes, patches, responses and feedback
are never shared across rows. Cache behavior is measured, not assumed equal.

Reuse the existing same-context phase schedule and safe-point triggers exactly:

| Phase | Model calls | Actions | Accepted edits | USD |
| --- | ---: | ---: | ---: | ---: |
| Initial repair | 28 | 60 | 3 | 0.48 |
| Verification, frozen candidate | 6 | 20 | 0 | 0.20 |
| Repair after feedback / submission | 6 | 20 | 1 | 0.20 |
| Row total | 40 | 100 | 4 | 0.88 |

The [existing schedule](verification-role-comparison.md#schedule-within-one-row)
owns entry, masks and return: enter at the first safely reconciled finish-eligible
candidate or initial-envelope exhaustion; no candidate remains explicitly recorded.
Verification ends with the same bounded report or exhausted envelope. Unused
initial/verification resources flow only to final repair in the same row. No early
phase may borrow later reserves; no phase switch resets global counters or time.
All calls, corrections, reports, checks and replays consume that row's resources.

Keep the 1,800-second global deadline including the 330-second evaluation reserve,
one consecutive correction, four parallel reads, 24 consecutive inspections and
three failed-mutation repair turns. Keep `segmented-v1`, `result-or-size-v1`,
`brief-v1`, history `public-v1`, probes enabled with policy/recheck `none`,
repair-recheck, `protected-v1` inspection and `per-call-v1` cost admission.
Keep two open-question references, 24,000 retained source characters, 60,000 counted
input tokens, 1,048,576 request bytes, 262,144 encrypted-item bytes, eight history
results and the current whole-original/48k overflow behavior. Keep the 1,500-character
verification report. Receipt IDs/hashes do not create extra source-body slots.

Probe plus observer remains within 8,000 characters, observation JSON within 2,048
UTF-8 bytes, call report within 6,000 characters and probe output within 12,000 bytes;
probe time/memory remain 30 seconds/512 MiB. B retains its implemented four-call,
four-input-root, 16-environment-name, 64-entry/1-MiB-per-call snapshot bounds. Do not
raise caps to admit a failing program. Record authored and wrapped lengths separately.

Shared prepared source: `C:/pt/ld20p01/s/13/prepared-source.json`.
Shared dependencies: `C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json`,
including Pylint 2.12.2. Pin complete task/source/dependency/installed-image identities
at freeze; record differences from the public issue's stated environment. No Docker
start, image pull/build or dependency change is automatic. Prices are not refreshed
by this document; verify official rates at freeze and before later paid dispatch,
preserving the cap and current output-ceiling reductions.

## Opportunity, actual use and interpretation

Audit only public task/source, actual dispatched inputs, authored programs and
completed receipts. Never inspect encrypted reasoning. A model-authored declaration,
expected value, `SUPPORTED` status or mention of `call_target` is not ground truth.

For every selected probe and relevant following decision, retain row/phase,
request hash, decision sequence, action_id + input_hash, case/channel/program hash,
candidate diff, observed/declared target, arguments, fixture/environment identities,
observation/predicate, flags and delivered result. Bind all evidence to completed
prior events, deduplicate recovery, and use short public quotes/source ranges.

| Measure | Required evidence; report assigned and opportunity denominators |
| --- | --- |
| E: exposure/opportunity | Actual dispatched tool guidance/state, allowed probe/replay, prepared environment and remaining time/action/cost/source allowance. Split offered, feasible, unavailable and uncertain; never infer opportunity from journal existence alone. |
| U_attempt: selection | B-authored `call_target` invocation attempt in a proposed original-requirement probe, including invalid/rejected programs; separate name-only prose/comments. For A record direct original-caller probe/replay attempts; B-API adoption is N/A for A. |
| U_bound: executable linkage | B receipt with actual target invocation and usable condition capture; distinguish resolution/setup/type/size failures, missing calls and incomplete reports. This is structural feature use, not proof of the right target. |
| V_original: faithful verification | Independent public audit confirms actual original caller, issue-relevant arguments/fixture/environment and behavior, plus relevant countercondition. Apply the same semantic criterion to A and B, including valid unbound probes. |
| P_pair: before/after | Completed failing baseline and later edited candidate use the same program/purpose/expectation and comparable observed conditions; current result addresses that failure. Record paired-still-failing and paired-improved separately. |
| D: delivery/retention | Exact useful result and concrete scope were delivered before the next decision and remained available at return/final claim; distinguish absent, truncated, dropped, restored and stale evidence. |
| U_applied: judgment/action | Subsequent public assessment or action correctly uses the observed result/condition difference: revises the hypothesis, runs a relevant countercheck, makes a targeted repair/replay, or explicitly maintains justified uncertainty. Mere repetition of a label/hash is insufficient. |

Use YES / NO_OBSERVED / UNKNOWN / NOT_RUN with reason and evidence; use N/A for
B-only feature metrics in A. Summarize /3 assigned per arm and /exposed-feasible
rows, then the conditional attempt-to-execution, execution-to-delivery and
delivery-to-application counts. Do not equate the arms' different telemetry.
A's legacy observer can miss aliases/constructors; use actual public programs,
execution feedback and outputs to assess scope. Insufficient evidence stays
UNKNOWN, not automatically wrong. Calibrate this asymmetry before freeze.
Declared cases must retain the frozen `expected_json`. An unbound direct comparison
needs equally explicit, unchanged expectations and executed program/setup provenance;
otherwise its pair is UNKNOWN. Neither arm needs B's fields to earn semantic credit.

A baseline is measured before the edit it is compared with; it need not be the
untouched repository, but its exact diff must be retained. A first observation
after an edit is only current-candidate verification. Do not invent its before
result, rewind a candidate automatically, or add a free pre-patch probe. Model
selection of an early baseline and a subsequent replay is itself measured. Missing
baseline/pair opportunities and phase starvation remain separate from incorrect use.
Changing program, expected value, fixture or environment creates a different case;
repeated current-diff contradictions cannot be erased by a later PASS.

## Wrong completion and independent repair outcomes

Seal public annotations before opening fresh private acceptance grades. Mask row
labels where possible, acknowledging that the API reveals treatment. No solver
receives this specification, prior runs, grading rubric, caller assessment program,
reference patch, private test or acceptance grade. The public issue is unchanged;
the operator's caller/countercondition audit is not an added agent hint.

Use the [public completion rubric](verification-state-comparison.md#public-only-completion-rubric-sealed-before-new-grades):
CONTRADICTED, UNSUPPORTED, SUPPORTED_DIRECT, SUPPORTED_INFERENCE, UNKNOWN,
NO_CLAIM and NOT_RUN. Review every completion assertion/finish attempt, not just
successful submissions. Respect correct, explicitly labelled source inference;
no declared probe or `required=UNKNOWN` alone establishes a judgment error.

| Outcome | Definition |
| --- | --- |
| J_final, primary judgment | Rows whose final repair completion claim is CONTRADICTED or UNSUPPORTED; /3 assigned and /assessable final claims. Absence/UNKNOWN/unreached final phase are separate. |
| J_any | Rows with any wrong completion claim in any phase; preserve earlier errors and later corrections, count each row once. Verification reports have their own verdict labels. |
| R, primary repair | Exact submitted patch passes native acceptance **and both** fixed missing/present-initializer caller controls; /3 assigned, plus each PASS/FAIL/ERROR/NOT_RUN component. |
| Resources/reliability | Submission, phase reach, stop cause, counts, total/phase cost/time, input/cache/reasoning/output usage, output ceilings, source rejection, incomplete traces and segment causes. |

An unsubmitted row is unassessed, not an observed behavioral FAIL. Existing valid
native receipts count once toward the six-evaluation cap. Caller assessment uses
at most two checks per submitted patch; post-collection host/native time bounds stay
600/300 seconds per patch. No assessment can feed more solver work. Failed caller
behavior and infrastructure ERROR remain distinct. Judge scope from public evidence
before grades; a lucky repair does not retroactively support an unsupported claim.

Report each row as E -> attempt -> actual caller/conditions -> before/after pair
-> delivery -> application -> J_final/J_any -> R. Cross-tabulate application with
judgment and repair, retaining no-claim/unknown/unassessed cells. Fewer wrong claims
caused only by silence or earlier failure are not improved judgment. Faithful
verification without accepted repair is a verification result, not a repair gain.

Classify the earliest observed break and any later break: not exposed; exposed but
not selected despite opportunity; attempted but rejected/failed; executed wrong
mapping/changed conditions; no comparable baseline; evidence not delivered; valid
evidence delivered but ignored/misinterpreted; evidence applied but repair failed.
Statements about what the model knew or felt require explicit public evidence;
otherwise report observable behavior and the remaining alternative explanations.

## Predeclared interpretation and stopping

Mechanism evidence requires faithful B linkage and supported subsequent use in at
least two of three rows, not just API calls. Report faithful verification/pairs in
A alongside it. A favorable combined exploratory screen additionally requires:
all six trajectories and submitted-patch assessments resolved; at least two
assessable final claims per arm; J_final_B <= J_final_A - 2 and a lower conditional
claim-error rate; R_B >= R_A + 2; and at least two accepted B repairs with supported
linkage use. Ambiguous B claims count against a judgment margin and ambiguous A
claims in its favor. Missingness cannot manufacture a favorable result.

Otherwise report the separate stages without claiming adoption or general benefit.
Three runs per arm on this repeatedly exposed development task are an exploratory
screen, not statistical or held-out accuracy evidence. No automatic extension,
new arm or second paid comparison follows from unused budget or a negative result.

Keep immediate pre-dispatch counting, one shared nanodollar ledger and zero SDK
retries. Stop all remaining rows on count, transport, billing, continuation/action
or cleanup uncertainty, manifest drift or changed required environment. Known
row/phase cap exhaustion follows the existing schedule; record NOT_RUN rows.
Assessment ERROR stops remaining assessments. No retries, resumes, replacements,
top-ups, paid judge or additional generation are included. Prior settled costs and
UNKNOWN bills stay separate from this proposed new allocation.

## Provider-free implementation and freeze gates

The diagnostic adapter, same-context controller composition and public grader are
implemented. The old role executor remains a different experiment. Packet freeze
requires all of the following evidence at the final implementation commit:

1. Implement the minimal diagnostic adapter: A restores the pinned description,
   fresh observation channel and exact prior review; B uses the current implementation.
   Both explicitly select same-context role mode. Preserve durable action identities,
   legacy wrapper bytes, actual behavior and state separation; do not emulate A by
   merely hiding B's receipt fields while retaining its execution semantics.
2. Capture initial and shared-checkpoint A/B requests with provider/counting blocked.
   Prove differences are limited to invocation guidance, channel/execution handling,
   new review fields and derived identities. At common states, schemas, system/phase
   prompts, masks, task, budgets and original evidence agree. Future trajectories
   may diverge; no matched-seed causal claim follows from equal repeat IDs.
3. Replay role51's immutable six public audits/149 inputs and the known declared-but-
   unobserved receipt without executing saved programs or changing grades. Add small
   public synthetic controls for aliases/constructors, helper substitution, wrong
   mapping, changed argument types/files/environment, missing baseline, stale/conflicting
   results, correct source inference and unsupported final claims. Validate both
   false acceptance and false rejection; new fields alone must not decide a label.
4. At entry, transitions, return and final claim, enumerate exact caller/input/setup
   and contrary/other-function evidence gained, lost, truncated or restored. Check
   new previews do not silently become extra reference slots or full-body storage.
   Measure description, state and wrapped-source overhead. Prior replay's no-eviction
   result applies only to its old fixed trajectories, not new live probes.
5. Check a meaningful generic original-caller/countercondition program fits the same
   8,000-character limit and report bounds. Verify the earliest feasible baseline,
   post-edit replay, report and finish path within the unchanged phase/global caps.
   Use captured sizes, saved counts and conservative offline bounds; no paid count.
   Missing minimum-path funding or source capacity blocks freeze. Record that floor
   feasibility does not guarantee useful reasoning or that a model will choose it.
6. Run concise focused controls under two minutes, Ruff, quick suite with both-arm
   isolated mock evaluation, then full regression at the final implementation commit.
   Preserve assertions/skip policies. Bind source, control, prompts, schemas, grader,
   phase/invariant hashes, input/displacement/resource evidence, six row requests,
   order/caps, environment, operator-only assessment identities and validation receipts.

The final implementation commit, adapter/grader hashes and all validation receipts
are bound by `C:/pt/probe-invocation53/manifest.json`. A missing or rejected packet
is not qualified. Schema `probe-invocation-comparison-v1` cannot accept an old role
or state allocation. Generated state stays in external hash-chained journals.

Implemented interfaces (repository virtualenv Python; all preparation is offline):

- `python -m diagnostics.probe_invocation_panel capture --root <packet> --arm A|B`
- `python -m diagnostics.probe_invocation_qualification --manifest <role51-manifest>`
  `--audit <role51-audit-public> --annotations <sealed-public-annotations>`
  `--output <fresh-output> --tokenizer-package <local> --tokenizer-cache <local>`
- `python -m diagnostics.probe_invocation_panel freeze --root <packet>`
  `--live C:/pt/probe-invocation53-live --validation <validation.json> --repeat-per-arm 3`
- `python -m diagnostics.probe_invocation_panel validate --root <packet> --hash <digest>`
- The separate `diagnostics.probe_invocation_execution` interface has `collect`,
  `export`, `seal`, `assess`. Collect requires a new exact human authorization and
  fresh price review. It is NOT_RUN in this preparation.

Public annotations retain the existing role report/claim rubric and add an
`invocation` block: assigned arm; exact `opportunities()` and `inventory()` values;
resource feasibility for every offer; semantic `original_scope` with caller,
arguments, inputs, environment, countercondition and expectation; optional measured
pairs; subsequent action/application quotes and scope; ordered causal breaks.
`U_attempt` counts attempted original verification including rejected selections;
`invocation_expression` separately records a parsed `call_target` call, not a string.
`U_bound` is B-only mechanical execution, never a semantic scope verdict.
`delivery_inventory()` distinguishes missing, body, summary, stale and restored
receipts even when the model does not use them. Empty application/pair lists mean
no observed supported use/pair; they cannot manufacture a favorable screen.

The additional 91 local-token guidance overhead can trigger an existing size
handoff near 60k. Replay records both the unchanged-input contrast and a separate
bounded size-transition sensitivity, with lost/gained line ranges and receipts.
It does not force a transition before the live counter actually reaches the limit.
Saved-count anchored estimates use the cached tokenizer and an empirical margin;
they are not provider counts or a guarantee of model behavior. Only exact dispatch
counting enforces the unchanged live limit. See the
[qualification follow-up](../../docs/history/2026-10-22-probe-invocation-qualification.md).
Only after packet freeze/revalidation would exact paid approval be requested.
