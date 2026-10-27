# Helper follow-up: configuration passed, target argument binding failed

Status: B/full executed once; all usage settled; allocation CLOSED. Official=false.
The diagnostic completed, but original target execution and reproduction did not.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-28
- Verification Status: VERIFIED execution/accounting; original reproduction NOT_RUN
- Version Label: helper_first_reproduction_result_v1

## Question and fixed conditions

The [sealed plan](2026-10-28-helper-first-reproduction-plan.md) follows the prior
full model's SystemExit helper-configuration failure. Fresh v8 permits the option
and documents its semantics. The same public checkpoint, full model, long
description except that paragraph, schemas and resource limits were retained.
Neither prior authored code nor repair/private evaluation information was injected.

The user approved manifest
`sha256:eb979db8aa9020c72b211ded93eb0a2ede59a538af86b928e13ddb5a3e258ba8`,
Astroid-1333 dev-train/current-dev20/13, gpt-5.4-2026-03-05 xhigh, repository `.env`,
B only once and USD 4.41415320 invocation-wide. Input/output/correction limits were
60K/40K/25K, remaining response/tool slots 16/34, solver time 1,903s and evaluation
reservation 390s. First settled probe ends the diagnostic, including a rejection
or pre-target error. No execution-feedback continuation or repair was authorized.

## Observed result

| Measure | Result |
| --- | --- |
| New input counts / model responses | 1 / 1 |
| Input / cached input tokens | 19,997 / 0 |
| Output / reasoning output tokens | 9,111 / 8,172 |
| Applied output ceiling | 40,000 |
| Model active / new active seconds | 98.194 / 106.270 |
| Group wall / probe seconds | 119.835 / 3.411 |
| Request admission / probe processes | accepted / 1 |
| Public setup comparisons | 3 PASS |
| Helper construction | passed |
| Recorded invocation attempts / actual target entries | 1 / 0 |
| Original F0010 / same-call processing | NOT_RUN / NOT_RUN |
| New cost | USD 0.1866575 |

The actual response model matches the requested snapshot and completed normally.
Output and context ceilings were not exhausted. Cost is 19,997 input tokens at
USD 2.50/M plus 9,111 output tokens at USD 15/M; it agrees across provider, branch
and group ledgers. Historical USD 0.0858468 is excluded. All calls are settled;
cleanup is confirmed, without truncation, timeout or execution uncertainty.

The outer `run_probe` action succeeded in returning a result, but its nested probe
failed with exit code 1. The call row records `target_started=false`, incomplete
capture, `bound_parameters=null`, and TypeError: `too many positional arguments`.
Both reproduction comparisons are `not_compared`; `observed_json` is null. No
target output exists, and the direct-file control was never reached.

## Concrete failure mechanism

The model found the correct installed console entrypoint and set CLI arguments:

```python
def invoke(arg):
    sys.argv = ["pylint", arg]
    return target([arg])
```

The pinned public dependency source defines `run_pylint()` with no parameters;
inside, it invokes `PylintRun(sys.argv[1:])`. Passing `[arg]` additionally as a Python
positional argument is invalid. The observer's `inspect.signature(target).bind(...)`
therefore rejects the call before target entry. Calling `target()` after setting
`sys.argv` matches that source signature, but this manual correction was not run.

Authored code lines 29-35 and the complete trace agree. The inspected source is
`C:/pt/calleruptake18/preparation-v2/B/site-packages/pylint/__init__.py`, lines 20-25;
its hash matches the prepared dependency manifest:
`sha256:e164a915e056963a9f9e31fe1c5066c72f9bb6b27455ba8f38784c59e049e061`.
This is static public-source confirmation, not another target execution.

The prior SystemExit settings error did not recur. However, this fresh model omitted
`expected_exceptions`, so it did not exercise the newly accepted explicit option.
Helper construction passed, but this trajectory alone cannot attribute that to
the new validator rather than a changed authored request. Local option-equivalence
tests remain the direct evidence for that narrow implementation change.

The desired observation now requires `buggy_has_w0611=true` from the same directory
call as `buggy_has_f0010=false`, plus a direct-file control. This addresses the prior
control-only positive-witness omission at the design level. Nothing reached these
extractions, so semantic processing and reproduction remain unverified.

## Decision and remaining question

The current obstacle is callable-signature adaptation, not insufficient output
budget. The preserved long description gives a generic `target(['path'])` example
but also says to inspect the supported signature and set CLI argv. That example
may be a contributor; one generated program cannot establish why it was chosen.

A useful next question is whether exposing the resolved public callable signature
before invocation and allowing one bounded correction of a pre-target binding
error can reach target execution. Do not silently coerce arbitrary arguments or
weaken original-reproduction obligations. This diagnostic deliberately provided no
post-probe model turn, so it cannot show that the model could not correct the error.
No further run is funded by its unused allowance. Repair, submission, public
regression, isolated acceptance and generalization are all outside this result.

## Evidence and closeout

- Executing commit: `c113b271d05e21dab21ae71ffe60a827f6d1bdec`.
- Runtime: `sha256:8deec9e3573e699515c346aabcfcb5267c78f4cb85752262d8db3e99f7c3e60d`.
- Diagnostic implementation: `sha256:74564874e4f84c935486fbda6bda2e8f28f1c54ae7e5cd52a95d3cf7e33311da`.
- External result root: `C:/pt/helper-first-reproduction-run-v1`; `result.json`,
  `analysis.json`, `B-probe.py`, and separate branch/group hash-chained journals.
- Analysis hash: `sha256:9855fa932930d3b087e8446f69042e2e801581fca2b886944881f692b49b93ee`.
- Public program hash: `sha256:53d412057555891e4268f462633622bbb8442996c6af09365c10fa23d440f7da`.
- Independent metadata audit PASS: sealed/prepared/count/dispatch request identity,
  actual model, costs, all start/finish pairs, unchanged source records and zero
  post-probe calls. No opaque reasoning artifacts were opened for analysis.
- The analysis records the group prefix through comparison completion; later
  analysis/audit/closure events extend that chain. The original result is unchanged.
- No retry, manual target replay, image pull/build, Docker startup, modification,
  visible regression, submission or isolated evaluation was performed.
