# Live request correction and original-caller acquisition

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-24
- Verification Status: VERIFIED (execution and artifact integrity; repair failed)
- Version Label: request24-live-v1

## Question and frozen conditions

The [previous pilot](2026-10-23-oracle-live.md) repeated identical invalid quote
arguments and never executed the original caller. The [request implementation](2026-10-23-requests.md)
removed model-authored quotation and classified corrections from actual arguments.
The selected question was whether this removes the request bottleneck and permits
faithful unchanged-base caller acquisition before repair. A valid request could
still target the wrong caller, fail setup, or encode an unrelated oracle; useful
correction and actual acquisition were separate criteria.

The user approved the prepared exact scope with "실행해줘": one fresh Astroid-1333
dev-train solve, `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output ceiling, repository
`.env`, USD 0.88 invocation cap and 1,800 active seconds. At most two frozen
post-submission public checks shared 120 seconds. No seeded reproduction, forced
error, prior solver context or operator repair hint entered the agent.

Runtime commit: `608bd9c0306a355be9ed6cb6777969bfbca7db2e`.
Runtime hash: `sha256:eed50e6ae199c2c376afcb188109358218063be34385829c7c33e760195746cd`.
The public task, prepared source, pylint 2.12.2, offline Python 3.9 dependencies and
probe/evaluator image digests matched the historical pilot. Host Python/security
dependencies changed since that pilot. This is one exposed-task diagnostic with a
historical reference, not a controlled effect-size or generalization estimate.
Acquisition release, replay scheduling and cost policies were unchanged.

## Results

Run: `run_dev_a38aa7435b7f4712`. The solve took 807.198 seconds; the two separate
public assessments took 17.913 seconds. Cost was USD **0.876006900**, fully settled.
There were 29 model calls, 31 input counts and 30 tool actions. The output total was
105,478 tokens, including 92,223 reasoning tokens; these are not additive charges.

| Observation | Result |
| --- | --- |
| Original requests / preflight rejections | 2 / 2 |
| Actual original dispatches / returns | 0 / 0 |
| Original setup failures | 0; neither request reached execution |
| Helper dispatch / return | 1 / 1; execution failed with NameError |
| Reads / searches | 11 / 13 |
| Accepted edits / required checks / finish | 1 / 1 / 1 |
| Public regression | 1,231 PASS, 69 SKIP, 15 XFAIL; pytest 8.49 seconds |
| Delivery | `unverified_delivery`, zero bound original cases |
| Independent acceptance / safety | FAIL / PASS |
| Frozen public missing-init / normal control | FAIL / PASS |

The first request named `pylint.lint.Run` and distinct failure/desired values.
It passed the quotation-free binding but failed the combined execution-source
length check. The next request changed `/python_source`, reducing authored source
from 2,807 to 2,475 characters; it still exceeded the limit. The receipt correctly
reported `invalid`, with `changed_error_fields=["/python_source"]`, rather than
`unchanged` or `corrected`. Thus real argument editing was observed, but no valid
original correction or acquisition was achieved.

After two rejected requests, acquisition was released with `request_error_limit`.
The later helper request was recorded as `different_purpose`, without correction
credit. It invoked module-resolution helpers but ended at `record_observation`,
which is unavailable to helper-purpose programs. A completed tool return therefore
did not establish a successful diagnostic, much less original-caller reproduction.

The agent added two lines in `astroid/modutils.py`: a package directory for which
`_has_init()` returns None is reclassified as `PY_NAMESPACE`. It added no dedicated
regression test. The public suite passed and the patch was submitted, but the
frozen original caller still emitted F0010 and did not analyze the child module;
the control did analyze it without F0010. Independent acceptance also failed.
No private evaluator program, test, reference patch or detailed output was read
or returned to the agent.

Completion funding reached edit/check/finish. One output-only incomplete response
at 7,370 output tokens consumed the existing funded protocol correction, whose
successor produced the edit. That is separate from correcting probe arguments.
The unused USD 0.003993100 does not authorize another attempt.

## Deterministic request-size diagnosis

Reconstructing only the host's program string from the saved public requests
explains both rejections; no model, container or additional probe ran for this audit.

| Request | Authored chars | Serialized source chars | Full execution chars |
| --- | ---: | ---: | ---: |
| First | 2,807 | 2,886 | 8,889 |
| Revised | 2,475 | 2,539 | 8,542 |

For these bindings, host instrumentation and fixed fields occupy 6,003 characters.
The 8,000-character total limit leaves only 1,997 for the serialized source, which
includes quoting and escaped newlines. The revised request remained 542 characters
over the bound. The error names `/python_source` and the combined limit but does
not provide the generated size, overhead or exact remaining allowance. This is a
host/request budget mismatch; it does not show that every original probe is too
large or that merely increasing the sandbox limit would produce a correct repair.

## Decision and remaining question

The runtime correctly distinguished an actual but insufficient argument change
and a switch to helper purpose. It also retained `unverified_delivery` despite
regression PASS. These are observed accounting/completion behaviors, not repair
quality gains. Original acquisition and the integrated repair criterion failed.

The next local design question is to separate the model-authored source budget
from trusted observer overhead, or expose the exact remaining serialized allowance
before another request. Preserve bounded source, output and execution resources.
Then reassess caller acquisition before attributing failure to later repair/replay
policy. Merely increasing attempts or adding another prompt is not supported by
this result. Helper API misuse and acquisition release remain separate concerns.
No runtime fix or further paid execution is included in this record.

## Evidence and closeout

- Plan, exact command and approval: `C:/pt/request24-live-ready-v1/`.
- Plan hash: `sha256:d34ddff03e5cd8002af276f07b67efddecc2de51c387739a7869300f4f0a13af`.
- Process, public assessments, size audit and collection: `C:/pt/request24-live-v1/`.
- Collection hash: `sha256:347f4b9315494a2844b52d47def3fbb1e71107f3c391b2ddbdbc567813bf8f87`.
- Submitted patch: `sha256:e73e2d9bdfa457556b72058ee12c39b213c6c957affa9f0cc0363e2fbfdbe2e8`.
- Append-only `dev-run-v1` journals and 154 existing content-addressed objects
  passed integrity checks at collection. Continuation blobs were hashed as opaque
  bytes; private reasoning was not inspected.

Code and frozen inputs remained unchanged throughout execution. No SDK retry,
resume, replacement sample, image acquisition or Docker startup occurred. The
allocation is closed, `official=false`, `claim_eligible=false`. Local implementation
tests were not repeated; only changed-document checks are part of this closeout.
Existing unrelated `AGENTS.md` changes and the temporary directory were preserved.
