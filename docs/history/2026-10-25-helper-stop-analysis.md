# Helper failure, exploration closure and no first mutation

Date: 2026-10-25. Completed offline follow-up to the
[call-path pilot](2026-10-25-callpath-live.md). Runtime unchanged; no new provider,
Docker, target or evaluator execution. `official=false`, `claim_eligible=false`.

## Material Passport

- Origin: academic-research-suite / experiment-agent / validate.
- Verification: ANALYZED from immutable public receipts, actual dispatched inputs,
  source and pure policy recalculation. Model reasoning content was not inspected.
- Version: `callpath-stop-analysis-v1`.

## Question and competing explanations

Why did the model leave its helper's NameError unfixed, continue inspecting source,
then exhaust 40K normal and 25K correction output without a first mutation?
This matters because the new post-mutation path diagnostic was never reached:
its effectiveness cannot be evaluated from this trajectory.

The audit distinguishes lost feedback, unavailable retry capacity, misleading
success status, absent execution-error recovery, physical versus monetary limits,
annotation failures and unresolved repair reasoning. It covers all 31 dispatched
inputs and focuses on calls 25-31. One trajectory cannot identify the model's
internal cause or estimate the repair benefit of a counterfactual policy.

## 1. A helper used an original-case-only API

Call 25 selected `purpose={kind: helper}`. Its source executed
`root = Path(reproduction_workspace())` before creating fixtures or invoking the
resolver functions named in its question. The saved execution source is exactly
the authored source: helper mode has no reproduction binding and therefore no
original-call wrapper. `reproduction_workspace` was undefined and raised NameError
at authored line 8. No resolver outputs were produced; setup checks had not run.

Source bindings:

- `reproduction.py:187` returns no binding for helper purpose.
- `tools.py:3816` returns authored source unchanged without that binding.
- `probe_call_capture.py:134` defines the workspace helper inside the original-case
  observer. `docker/probe_runner.py:229` separately injects the common `check_setup`.
- The actual call-25 tool schema discusses helper probes and common setup helpers,
  then describes original-requirement observation and `reproduction_workspace` in
  the same long description. It scopes the observer with “For original_requirement”
  but provides no separate helper-mode namespace list or local template.

The observed defect is use of an unavailable harness name, not evidence of an
Astroid resolver defect. The mixed description is a plausible contributor to API
overgeneralization, not a measured prompt effect. A helper can create a scratch
fixture directly; correcting that harness error still would not prove task repair.

The proposed helper also inserted the fixture's `src` into `sys.path` and called
Astroid resolvers directly. It did not invoke the original `pylint.lint.Run` call.
Even a successful corrected helper would require a separate mapping to the original
call's actual arguments/search roots before it could support a repair hypothesis.

## 2. The model saw the failure and chose a different investigation

The exact NameError remained visible in every dispatched input from calls 26
through 31, including public developer archives. The failed probe also remained
in public state. Call 26's public plan explicitly acknowledged that the helper
failed before observing target behavior, and chose source inspection next.
This weakens a context-loss explanation and a claim that outer tool success made
the model believe the diagnostic had succeeded.

The actual sequence was:

| Call | Selected action | Public decision or result |
| --- | --- | --- |
| 25 | helper probe | Separate namespace handling from directory/file loading; fails in fixture construction |
| 26 | search | Replace the failed helper investigation with inspection of modpath callback conditions |
| 27 | read | Reconsider `_spec_from_modpath` and a possible `PY_SOURCE`/missing-location conversion |
| 28 | search | Find the `Unable to load file` raise site |
| 29 | read | Inspect the presumed path-building helper before choosing a fix |
| 30 | no tool call | Exploration closed; 40K output exhausted |
| 31 | no tool call | Same allowed actions; 25K correction output exhausted |

`run_probe` remained available at calls 26-29. The four inspections consumed all
four remaining exploration opportunities. They added no uncovered public source
lines, and the no-new-coverage counter reached four. That counter does not prove
no information was learned: rereading can resolve uncertainty. Here, however, no
new execution tested the competing paths, and the final open question still asked
which helper constructed the missing init-file path. The no-gain signal is advisory
(`runner.py:1438`), so it did not require a concrete diagnostic or a changed method.

Model-authored source notes moved among plausible branches; they did not establish
which branch the failing caller reached. `ready_to_attempt` meant current editable
source anchors were delivered (`tools.py:2303`), not that the repair was understood.

## 3. No recovery state connected this execution failure to its correction

The action had `status=succeeded`, but its nested execution was `status=failed`,
`exit_code=1`, with the traceback intact. The outer status means a durable tool
return; it is not a behavioral PASS. The public observation also said execution
failed, and the model acknowledged that fact.

Nevertheless, three existing recovery mechanisms did not cover this situation:

1. `probe-request-correction-v1` tracks rejected preflight fields. This request was
   accepted with no invalid fields. Its successful preflight closes that correction
   chain even if execution fails later (`probe_requests.py:47`). A returned NameError
   is not a preflight correction event.
2. The existing original-failure diagnostic credit requires a nonempty changed diff
   with a comparable failure (`completion_reproduction.py:221`). The diff was empty.
3. The new call-path diagnostic requires an accepted implementation mutation and
   unobserved changed lines (`repair_path.py:79`). No mutation existed.

Thus the failed helper was preserved as evidence but did not become a bounded
pending repair task with a reserved corrected execution. The model could correct
it through ordinary probe capacity, but could also spend that capacity on reads.
Once exploration closed, neither diagnosis mechanism supplied an exception.

Annotations show a secondary semantic mismatch. At call 26, concern `v1` linked
the helper's execution failure to text about a suspected Astroid loader defect.
Calls 27 and 29 tried to relink it to the successful-exit original reproduction
and a search result; both were rejected as `unobserved_verification_observation`.
That concern API accepts unsuccessful executions, not a successful execution whose
original-behavior comparison is refuted. The original-failure obligation remained
separately preserved. Annotation errors did not reject the actual read/search or
consume the protocol correction; they are not the demonstrated terminal cause.
Their effect on model attention is unmeasured.

## 4. Physical call reservations closed exploration before money ran out

An independent static audit and the saved-state recalculation agree:

| Before call | Physical model slots | Protocol slot reserved | Usable slots | Protected completion | Remaining USD | Probe offered |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 26 | 15 | 1 | 14 | 10 | 0.604150800 | Yes |
| 27 | 14 | 1 | 13 | 10 | 0.578116800 | Yes |
| 28 | 13 | 1 | 12 | 10 | 0.546079050 | Yes |
| 29 | 12 | 1 | 11 | 10 | 0.512491800 | Yes |
| 30 | 11 | 1 | 10 | 10 | 0.488399550 | No |
| 31 | 10 | 0 | 10 | 10 | 0.278964300 | No |

The pure `completion_budget` calculation returns minimum 3 / protected 10 model
calls, and minimum 4 / protected 14 tool actions. Minimum completion is edit,
registered check and finish; original replay is an automatic physical tool action.
The largest protected path adds mutation-request recovery 2, registered-check
failure recovery 2 and original-failure feedback recovery 3. The protocol
correction slot is reserved separately. Early replay/reuse is already reflected:
the feedback recovery does not reserve another failed finish call.

At call 30, `10 usable - 1 prospective probe < 10 protected`, so reads and probes
were removed. The cost calculation still funded seven minimum-size model calls,
enough for a probe plus its minimum successor. Cost and tool-action slots did not
cause this closure. `protected_completion_possible=true` in this policy does not
promise money for every protected failure path: physical reservations and monetary
minimum-successor admission are distinct (`runner.py:823, 1059, 1123`).

The reserve is conservative about future failures, but it did not prevent correction
immediately after the helper failed. Four available attempts were instead consumed
by inspection. Simply reducing a reserve or adding one call could reopen a tool;
this audit does not show that the model would select it or repair F0010.

## 5. The final correction repeated the same unresolved decision

Calls 30 and 31 offered only `replace_text` and `stop_task`; `needs_mutation`
guidance recommended an evidence-backed edit. The current question still lacked
an observed original path. The 25K reserve was for recovering an incomplete model
response into a valid tool-call shape, not for fixing the helper program. Its
message repeated the edit-or-stop choices and did not reopen diagnostic execution.

The normal response received its entire 40,000-token ceiling and the correction
received its entire 25,000. Both responses contained only provider-classified
reasoning items, no tool call, and ended `max_output_tokens`. Input counts were
39,247 and 26,321 against the unchanged 60K input limit. This was not input-window
overflow, reduced output admission, provider transport failure or a rejected patch.

The supported interpretation is an unresolved diagnosis reaching an execution-only
decision, followed by two unsuccessful response generations. Internal deliberation
and the causal contribution of the restricted choices are unknown. A larger output
ceiling might change a stochastic result, but the existing 65K allowance did not
produce an action; the record gives no reason to treat cap growth as the first fix.

## Decision implications and limits

Prioritize the transition before the first mutation: make helper fixture APIs
unambiguous; distinguish a confirmed pre-target harness failure from target behavior;
and preserve one bounded corrected diagnostic opportunity tied to that failure and
question. The opportunity should have an explicit success/abandonment outcome under
the existing cap, rather than allowing unrelated reads to silently consume it.
If diagnosis remains unavailable, a truthful incomplete stop is preferable to a
forced speculative repair. Do not force every nonzero probe into a retry: an
intentional assertion or target exception may be useful evidence, and uncertain
external execution still must not be redispatched.

No runtime change was made here. A corrected helper is not original-call evidence
unless its conditions and path are linked; newly reserved capacity is not repair
success. The post-mutation call-path mechanism remains locally tested and unexercised
in this live trajectory.

## Verification and evidence

- Source run: `run_dev_b727d95fec6b4f93`, runtime `ab1fc8ef`, analysis HEAD `bad813cb`.
- External plan/script/journal: `C:/pt/callpath-stop-analysis-v1`.
- Analysis: `sha256:798f5476003530995756e409f33f46772e599f0cc6b89b740b8f2a4fa262eaf3`.
- Hash checks bound the previous closeout, public analyses and all 31 dispatched
  input artifacts. Pure forecast assertions match the saved 3/10 model and 4/14
  tool counts, the six monetary rows and tool availability. The actual call-25
  tool schema was read from the prepared request; opaque reasoning was not inspected.
- A separate native agent reviewed static policy and independently recomputed the
  same reservations. It shared project context; this is not a blind model study.
- New paid calls / containers / target executions: 0 / 0 / 0. No historical
  records were rewritten. Documentation checks and commit are in the closeout.

Statistical tests/effect estimates are not applicable to this single saved trace.
Fallacy scan: 11/11 checked. Simpson, ecological, Berkson, collider, base-rate and
regression-to-mean claims are not made. Survivorship is limited by retaining the
failed helper and both incomplete responses; look-elsewhere and forking-path risks
are disclosed as retrospective analysis. Temporal order supports the sequence,
while correlation/causation and reverse-causality checks prevent treating a host
policy or a public plan as proof of the model's hidden cause or general repair gain.
