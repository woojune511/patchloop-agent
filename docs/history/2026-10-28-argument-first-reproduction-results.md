# First original call entered and F0010 reproduced

Status: B/full executed once; usage settled; allocation CLOSED. Official=false.
The public failure was reproduced. Argument correction was NOT_EXERCISED.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-28
- Verification Status: VERIFIED execution/accounting and captured public-fixture failure
- Version Label: argument_first_reproduction_result_v1

## Question and authorized scope

The [sealed plan](2026-10-28-argument-first-reproduction-plan.md) tests actual
callable-signature guidance and the [bounded correction implementation](2026-10-28-original-argument-correction.md).
The prior helper trial failed before target entry by supplying an extra positional
list to a zero-parameter CLI. The same public checkpoint, full model and limits
were retained. Only the initial description's call paragraph changed; fresh v9
and a conditional one-correction diagnostic endpoint apply. No prior generated
program, result, patch or private evaluator information was injected.

The user approved manifest
`sha256:4224bb0d22dd283f8d9508b71a68b9613aab13b6d326bd1a8a5b9072e3697016`,
Astroid-1333 dev-train/current-dev20/13, gpt-5.4-2026-03-05 xhigh, repository `.env`,
one run and USD 4.41415320 invocation-wide. Input/ordinary/protocol output limits
were 60K/40K/25K; remaining model/tool slots were 16/34, solver time 1,903s and
evaluation reservation 390s. A first eligible pre-target binding error could receive
one ordinary model correction; a normal first invocation ends immediately.
Repair, public regression, finish and isolated evaluation were outside this scope.

## Observed outcome

| Measure | Result |
| --- | --- |
| New input counts / model responses / probe processes | 1 / 1 / 1 |
| Input / cached input tokens | 20,025 / 0 |
| Output / reasoning output tokens | 15,445 / 14,254 |
| Applied ordinary output ceiling | 40,000 |
| Target invocations / actual entries | 2 / 2 |
| Signature / Python arguments, both calls | `()` / no positional or keyword arguments |
| Capture completeness / argument binding errors | complete, both calls / none |
| Original directory call | F0010 present, W0611 absent, exit 1 |
| Normal package control | F0010 absent, W0611 present, exit 20 |
| Declared failure / desired result comparison | matched / mismatched |
| Argument correction / protocol correction | NOT_EXERCISED / unused |
| Provider active / new active / group wall | 163.151s / 175.875s / 184.048903s |
| Probe duration | 7.943s |
| New cost | USD 0.2817375 |

Requested and actual response models agree and the response completed normally.
Context/output limits were not exhausted. New cost equals USD 0.0500625 input plus
USD 0.231675 output under the registered pricing. Provider, branch, group and result
ledgers agree; historical USD 0.0858468 is excluded. All count/provider/action/probe
starts are settled. Cleanup is confirmed with no timeout, truncation or uncertainty.

The outer probe process passed because it successfully recorded the expected
failing behavior. This is not a repair PASS. The host acquired one baseline case;
the original obligation remains `refuted` against the desired behavior on the
unchanged base. There were no source edits or subsequent model/tool calls.

## Public behavior and signature use

The authored program creates `src/__init__.py` and `src/project/file.py` containing
`import os`, while omitting `src/project/__init__.py`. It changes cwd to that fixture
root and sets `sys.argv = ['pylint', 'src/project']`. This corresponds to the public
issue's corrected reproduction steps. The control is a separate regular package
with an `__init__.py` and the same `import os` file.

The model invokes `target.signature()` at program line 41, then uses `target()` at
line 54 after setting argv. Both host call rows record signature `()`, empty Python
arguments, `target_started=true` and `binding_error=false`. The old extra-list error
did not recur. However, `_ = target.signature()` discards the returned value;
there is no branch or assertion using it. This shows API invocation and correct
arguments, not adaptive argument selection based on the returned signature.

The first call's own complete capture contains:

```text
src/project/__init__.py:1:0: F0010: error while code parsing: Unable to load file src/project/__init__.py:
[Errno 2] No such file or directory: 'src/project/__init__.py' (parse-error)
```

The second call's own capture contains W0611 for unused `os` in the normal package.
This confirms public failure/control behavior within these fixtures. The model's
declared failing JSON exactly matches those captures. Its desired JSON requires
F0010 absence AND W0611 presence from the original directory call itself, as well
as the control. Control output cannot substitute for original-call processing.
The failing baseline has no positive processing witness; that remains desired
behavior for a future repaired candidate, not a condition satisfied in this run.

`diagnostic_rules` is null. The nested booleans are computed by the authored
`has_code` substring helper at lines 65-67 and recorded at lines 74-83. Independent
review and bounded token extraction agree with every boolean for these captures,
but this is not the host's canonical diagnostic-rule path. Future candidate output
still needs scrutiny. W0611 is an added processing check beyond the public issue's
explicit error-absence requirement. No broader semantic or benchmark acceptance
claim follows from that added condition.

## Decision and unresolved questions

The previous pre-target argument obstacle did not recur, and the original F0010
now has an executed public baseline. Keep this evidence for the next repair
question rather than increase context/output limits based on the earlier failure.
One stochastic run with host/API/endpoint changes cannot isolate which change
caused the better first request or establish reliability across tasks.

No binding error occurred, so the feedback window never opened. The experiment
does not establish live-model error correction; only its preceding local controls
exercise that path. No extra run was added to manufacture an error.

The next unresolved product question is whether the actual model can use this
reproduction evidence to repair the source and pass the same original call,
processing requirement and public regressions before submission. This diagnostic
does not authorize that continuation. Repair, candidate replay, public-check PASS,
isolated acceptance, clean-start completion and generalization remain unverified.
The unused USD 4.1324157 allowance is closed, not a new execution authorization.

## Evidence and closeout

- Executing commit: `3d173010`; runtime implementation baseline `1f69d90d`.
- Runtime: `sha256:321e6bc99e4cd3ef014e5d9bc7947c5f3369dedddc39c1be520a21b6142d47b3`.
- Diagnostic implementation: `sha256:7310c1f03d493abb038bcdab491b769739121175fe05a39fa8e4af21ee96b301`.
- Result root: `C:/pt/argument-first-reproduction-run-v1`.
- `result.json`: `sha256:09b657af297ff561310e3a22a1e90c52d41e00f8886648fc5e52d2fb33d79b54`.
- `analysis.json`: `sha256:7f7dd66511996c058a61bb7420a21320bb94a7ea2acb11204222504c2f681b21`.
- `B-probe.py`: `sha256:3a1c39fc32cb99a61159ceb623602c7dab4dd7d4eea70dda31b1e4fb365a3a66`.
- Independent shared-context metadata audit PASS and public behavior review with
  the limitations above are saved in `metadata-audit.json` and `public-behavior-review.json`.
- Sealed/prepared/count/dispatch identity, actual model, usage, source preservation,
  inherited 64-event prefix, unchanged runtime/diagnostic/host hashes and no post-probe
  activity were checked. No opaque reasoning or hidden evaluator content was opened.
- Analysis binds the group prefix through sequence 8 and branch through sequence 86.
  Later analysis/audit/closure events extend the group journal; the result is unchanged.
- No retry, manual target replay, image pull/build, Docker startup, source mutation,
  public checks, finish or isolated evaluation occurred. The next allocation is unset.
