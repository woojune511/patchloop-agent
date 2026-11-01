# Fresh repair pilot: request correction executes, but caller verification and repair fail

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-24
- Verification Status: VERIFIED (execution and artifact integrity; repair failed)
- Version Label: repair24-live-v2

## Problem, question and frozen design

The [request pilot](2026-10-24-request-live.md) never executed an original probe
because host instrumentation exceeded the source limit. The [size split](2026-10-24-size.md)
removed that defect. The [operator oracle experiment](2026-10-24-oracle.md)
then showed that two corrected predicates distinguished the public failure from
ordinary lint warnings. Neither result established fresh-model uptake or repair.
This matters because passing regressions and submitting a patch have repeatedly
coexisted with failure of the original caller.

The prospective question was whether a fresh agent could now construct a faithful
original call, acquire its unchanged-base failure, repair it, replay the same
case and pass independent acceptance. Plausible remaining failures were wrong
arguments/observations, an incorrect repair, or insufficient completion resources.
Success required all stages, both frozen public caller checks and settled cost.
Independent acceptance and original-case verification remained separate criteria.

The user approved the prepared request with "docker 켰으니까 실험해줘". Docker
29.8.0 responded; the operator did not start Docker or acquire an image. Exact scope:
one fresh `tasks/dev-train/current-dev20/13/public.yaml` Astroid-1333 dev-train solve,
`gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output ceiling, repository `.env`, USD 0.88
invocation cap, 1,800 active seconds and 1,920 seconds outer supervision. At most
two frozen post-submission public checks shared 120 seconds. No prior solver
context, corrected program or operator repair hint entered the agent.

Runtime commit: `fe6014bab81b074dcebdb19ad6311585884f4936`.
Runtime hash: `sha256:bb00fed60196d995e8a303087350a9823461dc0cf968520038dd2f988f7829cd`.
The prepared public Astroid base, Python 3.9.25, pylint 2.12.2, offline dependencies,
probe profile and evaluator digests passed preflight. Policy settings were
segmented-v1, result-or-size-v1, brief-v1, probes with policy none, bounded-v1
acquisition, repair-recheck, protected-v1 and completion-recovery-v1. This is one
exposed-task sample with a historical reference; size handling and observation
guidance changed together. It is not a controlled estimate of either effect.

Executed from `C:/Users/geonj/Documents/PatchLoop`:

```powershell
uv run --locked --offline python C:/pt/repair24-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/repair24-live-ready-v1/assess_submission.py
```

## Results

Run: `run_dev_75cd3425d757450e`. Process status: completed, exit 0; task terminal:
`EVALUATOR_FAIL`. The solve took **432.812 seconds**; the two public assessments
took **17.131 seconds**. Cost was **USD 0.525472350**, fully settled. Twelve model
calls and twelve input counts produced twelve model-requested actions plus one
host completion replay. There were no incomplete responses or funded protocol
corrections. Output was 77,927 tokens, including 73,268 reasoning tokens; these
counts are not additive charges. Initial RSS was not collected; supervision used
process liveness, durable journal growth, frozen inputs and a hard timeout.

| Observation | Result |
| --- | --- |
| Fresh original requests / preflight rejections | 2 / 1 |
| Rejected request correction | `python_source=null` changed to 2,450 characters; `corrected` |
| Unchanged-base dispatches / returns | 1 / 1; two observed calls |
| Declared original failure acquired | No; failure comparison mismatched |
| Automatic candidate replay | 1 dispatch/return; same frozen source and binding |
| Helper dispatches | 0 |
| Reads / searches / accepted edits | 4 / 3 / 1 |
| Required check / finish | 1 / 1 |
| Public regression | 1,231 PASS, 69 SKIP, 15 XFAIL; pytest 9.28 seconds |
| Original evidence / delivery | unverified / `unverified_delivery` |
| Independent acceptance / safety | FAIL / PASS |
| Frozen public missing-init / control | FAIL / PASS |

All dispatched probes returned with confirmed cleanup. The first rejection was a
missing authored program, not the old combined-size defect. The next request
changed the actual invalid field and passed full preflight; a declaration of
correction alone did not supply that credit.

## What prevented a valid reproduction

The corrected request named `pylint.lint.Run` but used
`call_target(args=["src/project"], kwargs={"do_exit": False}, ...)`.
The host invokes `target(*args, **kwargs)`, so this passed a string where the
target expected its command-argument list. Both bug and control logs attempted
modules `s`, `r`, `c`, and other path characters, then reported F0010 for
`/__init__.py`. This was an actual call to the declared function, but not a faithful
execution of `pylint src/project`. The needed positional shape is a nested list;
this was diagnosed from saved public arguments and host source without a new run.

The program also searched `json.dumps(normalize(return_value))` for F0010 and
"Unable to load file". Pylint wrote diagnostics to stdout, while the returned
object representation did not contain them. It recorded both flags as false for
both fixtures despite visible errors. The exception handler could similarly turn
unrelated exceptions into dictionaries that the same predicate interpreted as
false. No counterfactual exception execution was performed here.

Consequently the unchanged base already matched the desired JSON and mismatched
the declared failure. The automatic post-edit replay preserved the program,
binding, caller arguments and fixture hashes, and again matched that unsound
desired JSON. Neither comparison proves repair. The host retained the missing
baseline failure and returned `unverified_delivery`; it did not promote the
expected-value matches or regression PASS to verified original evidence.
Acquisition ended with `investigation_action_limit`, not budget exhaustion.

## Submitted repair and public outcome

The patch changed `get_module_files` in `astroid/modutils.py`: a directory without
`__init__.py` was pruned only if it also contained no Python files. It added no
dedicated regression test. The exact submitted diff was used in both frozen
operator assessments, with scope/test-tampering checks and fresh public workspaces.

The missing-init assessment analyzed the child file but still produced F0010 and
caller exit 1. The init-present control analyzed the child without F0010 and exited
0. Independent task acceptance also failed; safety passed. No private test,
reference patch, evaluator program or detailed evaluator output was inspected or
returned to the agent.

## Decision and remaining question

The integrated repair criterion failed. Request correction, bounded execution,
post-edit replay and conservative completion labeling operated in this sample.
The new generic guidance did not produce a faithful caller/observation by itself.
This does not establish a general benefit or failure rate for that guidance.

The first unresolved stage is semantic construction of the call and its observable
result. The next smallest diagnostic should examine argument-shape guidance and
the distinction between returned values and emitted diagnostics, with negative
controls that cannot become a false/no-error result. A new prompt, tool or gate is
not selected by this record. More budget is not supported as the immediate remedy:
USD 0.354527650 remained, and check/finish had completed. Do not automatically rerun.

## Evidence and closeout

- Frozen plan, command, direct authorization and preflight: `C:/pt/repair24-live-ready-v1/`.
- Request hash: `sha256:41716929165863d6c2778e74a9483ce1552c73b8c5af2a6ac1da39371dfe8c56`.
- Process, public receipts, submitted patch and collection: `C:/pt/repair24-live-v2/`.
- Collection hash: `sha256:5976a96fe774b25a10d602f2d3d46b6f6cf726d1f3f6f1d4ab022350c4497208`.
- Submitted patch: `sha256:e4ce8ca45909ff3bf45f8e8b18346fb88492f8f181dd047be4ba16c91965e9d0`.

Three append-only hash-chained journals and 93 existing CAS objects passed integrity
checks before collection/closeout were appended. Action ID/input-hash pairs,
settled provider calls, submitted-diff identity and 109 frozen source/task files
were checked. Continuation blobs were hashed as opaque bytes, without reading
reasoning content. The empty preparation-only `repair24-live-v1` directory was
preserved; the actual solve used the fresh v2 root.

The allocation is closed, `official=false`, `claim_eligible=false`. No SDK retry,
resume, replacement sample, image acquisition, runtime edit or budget transfer
occurred. Historical records and unrelated working-tree changes were preserved.
Previous runtime tests were not repeated. The five documentation checks passed
in about two seconds; `git diff --check` passed for this closeout.
