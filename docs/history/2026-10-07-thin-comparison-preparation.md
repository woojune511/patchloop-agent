# Thin comparison preparation and SQLFluff-1733 A2 public replay

Date: 2026-10-07. Source baseline: `1532f8eda6b6a9c0404b95f0b73ed0d70137d6f3`.
Runtime hash: `sha256:3381660b5484eb474efe897157c711b32a8c26f54cbba05ab90ac1c9ec226522`.
User-authorized public replay and provider-free comparison preparation;
official=false, no live model or private evaluator execution. Runtime unchanged.
This follows the [thin adapter](2026-10-07-thin-policy.md) and the
[candidate matrix](2026-10-07-policy-candidate-prep.md); those records are immutable.

## Question and selected work

The candidate matrix could distinguish SQLFluff-2419 candidates, but lacked a
current public observation for the saved 1733 A2 patch. Its one-line indentation
change was plausible, not observed success. Closing this gap separates absence
of a viable candidate from failure to retain, verify or choose one. A public
example cannot settle full task acceptance or identify which agent mechanism
caused a later bad submission.

The subsequent question is whether the implemented thin policy bundle improves
fresh repair correctness against current under equal resources. Earlier repeated
prompt/context comparisons did not establish a gain. This preparation therefore
fixes bug and preservation observations, successful controls, repetition, and
correctness criteria before any new responses. No default changes or automatic
continuation follow from preparation.

## A2 replay and profile boundary

The actual saved submission is from `C:/pt/vcl06/06`,
`run_dev_34c6612b1eb647c4`. Its patch hash is
`sha256:d69d881c095ac356eb9587ada1a2a8d5ba539bfb3f85cca10b44a30fdad7622a`.
It changes the L003 expression from `comp_indent_num - this_indent_num` to
`comp_indent_num + indent_diff - this_indent_num`.

The first preflight in `C:/pt/a2pub01` stopped before any probe. Historical and
current probe profiles differed only in `line_trace_hash`, following the filename
alias correction. It would be inaccurate to claim identical historical/current
profiles. A separate matched pair in `C:/pt/a2pub02` therefore ran both base and
A2 under the current profile, with tracing disabled. No failed probe was retried.

The pair used the original public program, hash
`sha256:e958a374bd897eec3f0f1f1906d5b65611e048e506facfc5b727578c19a653b6`,
the registered public issue's full expected WITH output, and an ordinary SELECT
control. Same source base, dependencies and existing image; separate workspaces
in `C:/pt/a2pubw02`. Frozen ceiling: two probes, 30 seconds each, 300 seconds total;
actual pair duration 39.825 seconds. No image pull/build, provider or evaluator.

| Candidate | Exact public WITH output | Plain SELECT control | Scope |
| --- | --- | --- | --- |
| Base | FAIL; first field has nine leading spaces | PASS | SCOPED_FAIL |
| A2 | PASS; eight spaces and all output lines match | PASS | SCOPED_PASS |

Both receipts have passing supplied setup assertions, confirmed cleanup, and no
timeout, truncation or deadline uncertainty. Workspace patch identities remained
unchanged. Ten synthetic classifier cases passed. Independent read-only audit
passed 74 checks, including both journal chains, input hashes, actual submission
patch and complete output. It also checked two unknown-cleanup classifier cases.

Frozen replay packet:
`C:/pt/a2pub02/packet.json`,
`sha256:829c95dc0d6c4d54f8f20043a2bfeea13eba1d56ed8cb0fa35cb8de884dcebd8`.
Results are `observation-base.json`, `observation-A2.json`, and `result.json` there.
Independent audit: `audit.json`,
`sha256:24f2424ac27af43bb5dd02e4de0d212e08f52795bf64c1c253815a33f5355719`.
Append-only journal: `runs/run_dev_1733a2public02.jsonl`.

This establishes that an available saved candidate satisfies this public example
without breaking the checked SELECT control. It does not establish full task
correctness, reliable candidate selection, a thin-policy effect or a success rate.
Private acceptance was NOT_RUN. SQLFluff-1517's incomplete oracle is unchanged.

## Frozen public observations

`C:/pt/thrub01/packet.json` binds exact programs, expected values, public issue
hashes, eight saved base/positive observations, classifier sources and 19 input
hashes. Packet hash:
`sha256:a9f88e43ed6a735a611871b0c74bd2f2f5cea56119165dc93634d36a8df414ab`.
The journal is `runs/run_dev_thinrubricfreeze.jsonl`. This freeze ran only pure
classifiers over saved receipts: zero new probes, providers or evaluators.

| Case | Public bug observation and preservation control | Saved calibration |
| --- | --- | --- |
| SQLFluff-1733 | Exact WITH output and plain SELECT | Current matched base FAIL / A2 PASS |
| SQLFluff-2419 | Exact IFNULL/NVL diagnostic text and COALESCE preservation | Historical base FAIL / single-quote candidate PASS |
| pvlib-1072 | Timezone-aware Fuentes result, naive values, index and name | Historical base FAIL / positive PASS |
| pydicom-1694 | Invalid raw IS conversion; suppression omits invalid data and keeps valid data; suppression off still raises | Historical base FAIL / positive PASS |

Original classifier output matches each saved assessment exactly. Each pair has
matching profile hashes, matching program bytes and confirmed cleanup. The
older pvlib/pydicom programs did not use supplied setup assertions; their explicit
output witnesses remain the scoped setup evidence. Their saved calibration does
not prove readiness of a future current environment. No program, expected value,
saved patch or operator verdict enters fresh solver context.

## Proposed comparison

Final design: `C:/pt/thplan01/plan-v4.json`, file hash
`sha256:e71788d6a39072988e7c6541c983bd100f3c17e286839e283b61fcdeea24febb`;
canonical JSON hash
`sha256:425aeed2247658c3a21d5289f798e77ff16109008e6a5aae06ffec3f0c373bf1`.
Readable design: `final-design-v2.md`; closeout: `validation-v4.json` there.
The exact request rows remain identical to the mock-tested v2 design. Later
versions add evidence links, explicit readiness limits and the current-document
update; earlier versions and receipts remain intact.

Sixteen fresh original-source solves: four tasks, two policies, two repetitions.
Use A=`current` + `brief-v1`, B=`thin` + `none`; this measures the interface/policy
bundle, not an individual removed field. Both keep probes, selected/additive tests,
repair recheck, 24,000 retained source characters, segmented/result-or-size context,
protected inspection and per-call cost admission. Automatic probe replay stays off.

| Row | Task | Selection reason |
| --- | --- | --- |
| 18 | SQLFluff-1733 | Recent registered/native FAIL; public discriminator now complete for the chosen example |
| 20 | SQLFluff-2419 | Recent registered/native FAIL despite earlier PASS; exact public message distinction |
| 2 | pvlib-1072 | Successful control in both previous complete and corrected dev20 evaluations |
| 9 | pydicom-1694 | Same successful-control history; both full-model repetitions also passed |

Proposed model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens, existing
repository `.env`. Its contents were not read. Historical selection traces mostly
used mini; both new arms use the same full model. This is not a direct reproduction
of mini behavior. The snapshot and rates were verified against official
[model documentation](https://developers.openai.com/api/docs/models/gpt-5.4) and
[pricing](https://developers.openai.com/api/docs/pricing) on 2026-10-07.

Proposed caps: USD 4 per row, USD 64 invocation-wide, nontransferable. At the
verified standard short-context rates, the old 1733 mini trace's USD 0.91865010
would cost USD 3.062167 at identical token usage on full. USD 3 could censor that
observed path; USD 4 matches the token allowance of the old USD 1.20 mini ceiling.
This is a cap rationale, not a spending or completion forecast. Each row permits
40 model calls, 100 actions, four accepted edits and 1,800 active seconds including
330 seconds of evaluation reserve. The separate native grading operational limit
is 600 seconds. Fresh state roots are proposed under `C:/pt/thlive01`, not created.

At most two distinct task workers run concurrently. Each wave must settle before
the next starts. Queue order is fixed; actual runtimes determine overlap.

| Wave | Ordered task-arm-repeat rows |
| --- | --- |
| 1 | 18-A-1, 2-B-1, 20-B-1, 9-A-1 |
| 2 | 9-B-1, 20-A-1, 2-A-1, 18-B-1 |
| 3 | 20-A-2, 9-B-2, 18-B-2, 2-A-2 |
| 4 | 2-B-2, 18-A-2, 9-A-2, 20-B-2 |

Each task has ABBA or BAAB order and occupies each queue position once. No prior
patch, working history, probe result or operator program is seeded. Count,
transport, billing, identity, cleanup or assessment uncertainty blocks subsequent
admission and later waves; already admitted operations settle. No retries,
replacement runs, resume, cap transfer or automatic follow-up. Settled resource
limits remain separate from global uncertainty.

Registered/native agreement, public behavior, submission, safety, billing and
infrastructure must be reported separately. To make thin a candidate for further
validation, all four thin successful-control attempts must pass, no paired
current-PASS/thin-FAIL regression may occur, and at least one failure task must
improve current-FAIL to thin-PASS in both repetitions with matching public behavior.
No safety/integrity regression is allowed. Missing or resource-censored verdicts
are inconclusive. Token savings alone are insufficient. If both policies repeat
the same repair failures, preserve current and investigate repair capability or
candidate generation instead of another adjacent wording variant. This small,
development-exposed panel cannot establish generalization.

## Orchestration checks and remaining work

The external mock-only harness `C:/pt/thplan01/mock_wave_validation_v2.py` uses the
existing spawned process pool, shared admission lock and stop latch. Five tests
passed in 11.157 seconds, including seven malformed-scope subcases. Synthetic
receipts exercise all 16 forwarded requests, four waves, at most two workers,
request-bound full-model report labels, one nontransferable USD 64 reservation,
separate row artifacts and no restart/resume. Count, billing and assessment
uncertainty each stop later waves while admitted peers settle and later
count/generation admissions reject. Result: `mock02/validation.json`.
Harness hash:
`sha256:663992ca69ab3b204da65d3e1a268c936ac894f3c71348ed9a170c8284668a90`.
The original harness passed five tests but failed Ruff style checks. Its script
and `mock01` receipt are preserved; the formatted v2 copy passed Ruff and the
fresh mock02 run. These mocks do not exercise real SDK settlement or prove all
task-local deadline classifications.

These are orchestration checks, not live model or isolated task evaluation.
Provider, Docker and evaluator calls in the mock were zero. Runtime and relevant
drivers remained unchanged. Previous current/thin CLI smoke reaching isolated
evaluation is recorded in the linked implementation report, not rerun here.

The design remains NOT_READY for live execution. The generic batch driver rejects
repeated task paths in a flat batch; the existing wave wrapper hardcodes a different
eight-row comparison; native assessment labels predictions with a fixed mini model.
A live adapter must bind this schedule and rubric packet, preserve the mock-tested
allocation/stop behavior, report `req.model`, and freeze its exact environment and
evaluation identities. Existing-image preflight and a concrete executable manifest
remain unexecuted. Only then can exact new task/model/credential/repeat/cap approval
be requested under AGENTS.md gate 5. No historical allocation has been reopened.

Current decision: retain the default policy. The A2 public gap is closed; the next
implementation boundary is the live comparison adapter, followed by preflight and
new paid authorization. No model-quality result has been produced by this work.

Repository checks: five documentation layout/size/link tests passed, new record's
four Markdown links resolved, and `git diff --check` passed. Replay/rubric scripts
passed Ruff (E402 excepted for the explicit import bootstrap); the final mock
harness passed the same check. No runtime edit required another full suite or
mock solve. Runtime hash and the user's pre-existing AGENTS.md bytes were preserved.
