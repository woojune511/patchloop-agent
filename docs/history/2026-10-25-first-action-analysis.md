# First-action exhaustion: shared output budget and unchanged correction strategy

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate; frozen public requests, metadata and source analysis
- Origin Date: 2026-10-25
- Verification Status: ANALYZED; local control flow checked, live behavior not rerun
- Version Label: firstcall25-analysis-v1
- official=false; claim_eligible=false; new provider calls and target executions: 0

## Question and decision

The [feedback pilot](2026-10-25-original-feedback-live.md) used USD 0.235849950
of its 1.20 cap but executed no tool. The user asked why output was exhausted
before even the first action. This matters because original-call verification
and repair improvements cannot help a solve that never reaches tool execution.

The direct failure is established: both responses exhausted their full 25,000
output allowances, mostly in reasoning, and the adapter accepted no tool from
an incomplete response. The second response did contain a `function_call` item.
Its arguments and individual completion status were not retained, so absence of
an executed call must not be described as absence of any generated call item.

The leading structural hypothesis concerns broad first-action scope: initial
guidance favors a complex reproduction, and correction leaves that selection
problem unchanged under xhigh. The selected call name is unavailable, so choosing
run_probe in this run is not established. The hypothesis is consistent with the
observed inputs and earlier expensive first calls, but is not a proven account
of the model's internal reasoning. No private reasoning content was inspected.

Keep the original-feedback implementation unchanged. The next useful diagnostic
would hold model, xhigh, tools and token/cost limits fixed and change only the
first-action guidance to one small public-source search. Measure first valid
action, output/reasoning tokens and time separately from repair success. This is
a proposed comparison, not executed or authorized paid work. More invocation
budget alone does not target the observed per-response limit.

## Evidence and sequence

Source run: `run_dev_f203f76f3abb492a`; runtime commit `303e688e`.
Analysis checkout: `9d788047cf8f5be38c3c31a8fee8548755742b16`.
Frozen request hashes were checked against actual dispatch records, and source
journal hash chains were validated. The API's HTTP and SDK status/usage fields
matched; both HTTP statuses were 200 and both input-count deltas were zero.

| Response | Total output | Reasoning subset | Other output tokens | Provider item types | Accepted actions |
| --- | ---: | ---: | ---: | --- | ---: |
| Initial | 25,000 | 25,000 | 0 | reasoning | 0 |
| Correction | 25,000 | 23,648 | 1,352 | reasoning, function_call | 0 |

Reasoning accounted for 48,648 / 50,000 = **97.296%** of generated output.
Other output tokens include formatting; they are not a measurement of usable
tool-argument length. Both calls used `gpt-5.4-mini-2026-03-17`, xhigh,
`tool_choice=required`, and the full configured 25,000-token ceiling.

The API output ceiling includes reasoning, visible output and formatting tokens.
An incomplete response can therefore occur before visible output; a 25,000-token
allowance is not a guarantee of a tool response. This is documented in the
[official reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#controlling-costs).

After response 1, the encrypted continuation measured **345,164 bytes**, exceeding
the segmented-v1 per-item bound of **262,144 bytes**. The journal records a new
segment with reason `encrypted_item_bytes`. The actual second request contains
no native reasoning item; it retains public task/state and the correction.
The prior hidden computation was not delivered as continuation to response 2.
This is a consequence of the first exhaustion and a possible recovery amplifier,
not an explanation of why the first response exhausted its allowance.

Response 2 kept the same model, reasoning effort, output ceiling, system prompt,
task, user instruction and four tool schemas. The final state message grew by
677 characters; counted input increased from 11,894 to 12,019 tokens. The
correction requested a valid tool-call shape and listed inspection, probe and
stop options. It did not narrow the first action or change the generation budget
split. With no prior tool action, there was no new source/probe result to use.

The adapter first classifies any incomplete response as `incomplete_response`
([model.py](../../patchloop/agent/model.py), line 224). It then skips function-call
argument parsing when an error exists (line 274), and returns an empty accepted
call list (line 293). The function-call payload is not retained; response shape,
status/usage metadata and opaque continuation remain. Thus response 2 is neither
a demonstrated malformed request
nor a demonstrated valid call discarded by mistake: its individual call validity
cannot be recovered from the retained metadata. Executing an uncertain partial
call is not the proposed remedy.

The existing single correction was consumed; the next incomplete response ended
the run ([runner.py](../../patchloop/dev/runner.py), line 5533). Billing, action
limits, Docker execution and target exceptions did not trigger this termination.

## Initial action burden and counterevidence

The initial public state recommends `run_probe` at the
`needs_original_reproduction` stage (runner.py, line 611). Its guidance asks for
the original caller, actual arguments, cwd, fixtures and environment before
editing. The probe description combines setup checks, failure/control extraction,
call observation, identity selection and stable workspace requirements. This can
make the first chosen action much larger than a short source inspection.

However, `read_file` and `search_files` are explicitly offered, alongside
`run_probe` and `stop_task`. The system prompt permits reads/searches, says offered
tools are callable, and permits null note updates. There is no demonstrated
"must finish reproduction before any tool is callable" deadlock. A separate
read-only source audit confirmed this distinction; it was a shared-context
single-family review, not an independent live experiment.

Comparing the actual first requests with the cap-only baseline shows:

- System prompt, public task and user instruction are byte-identical strings.
- The public state differs only in its segment ID.
- All tool parameter schemas are unchanged. Only the `run_probe` description
  changed, from 8,086 to 8,618 characters: stable workspace and argv guidance.
- Counted input increased **92 tokens**, from 11,802 to 11,894 (about 0.78%).
- The system message is 13,332 characters and the run_probe schema serializes to
  15,770 characters in the analysis format; character counts are not token counts.
- The post-edit replay implementation is not executed before an accepted edit;
  there were no acquired original cases or edits in this run.

The small input difference does not prove harmlessness, but it does not support
a claim that new replay execution blocked the first call. Earlier frozen runs
also show the failure predates this change:

| Historical trajectory | Initial response | Following response |
| --- | --- | --- |
| Observation pilot, run_dev_3f0132d090d04653 | 25,000 reasoning/output; incomplete; no call | After size handoff, 17,789 output / 16,834 reasoning; accepted run_probe |
| Cap-only pilot, run_dev_8302ca202b3544e6 | 20,353 output / 19,164 reasoning; accepted run_probe | Accepted search_files |
| Current feedback pilot | 25,000 reasoning/output; incomplete; no call | After size handoff, incomplete with a function_call item; no accepted action |

The observation pilot had a different total cost cap and six fewer initial input
tokens than the cap-only pilot. These are selected historical trajectories, not
matched randomized repetitions. They weaken claims that the new guidance alone
introduced the failure or that a segment handoff necessarily prevents recovery.
They do not estimate the causal contribution of xhigh, prompt complexity or
discarded continuation, nor show that lowering effort would preserve repair quality.

## Validation, interpretation and limits

Three existing local tests passed in 7.32 seconds: typed incomplete metadata,
oversized-incomplete handoff with correction retention, and repeated-incomplete
termination without resetting the correction budget. They use fake providers;
the segment tests prohibit HTTP transport. These checks reproduce host control
flow, not the live model's reasoning or first-action failure. No product code,
runtime configuration or frozen experiment artifact was changed.

Statistical fallacy coverage: **11/11 checked**, with no inferential statistics
or success-rate claim. Simpson's paradox and collider adjustment are inapplicable
to this descriptive event sequence. Ecological inference is avoided by not
inferring hidden thought from aggregate tokens. Selection/Berkson and base-rate
concerns prevent generalizing from exposed failure-selected runs. Regression to
the mean cautions against treating a future successful retry as improvement.
Survivorship is addressed by retaining failed trajectories. Look-elsewhere and
forking-path concerns are bounded by labeling this an exploratory analysis and
preserving inputs. Correlation is not causal attribution; reverse causality is
avoided by placing the size handoff after the first exhaustion.

The most concrete gaps are an exhaustion-specific action strategy and retained
public metadata about rejected function-call items. The first should be tested
by a narrow first-action comparison; the second would allow a future audit to
distinguish a partial call, invalid JSON and an individually complete call.
Neither change has been implemented here. Original-call comparability, feedback
uptake, task repair and generalization remain outside this run's evidence.

## Reproducible analysis artifacts

External root: `C:/pt/firstcall25-analysis-v1`.
Journal: `run_dev_firstcall25analysis`, append-only `dev-run-v1` with CAS artifacts.
`analyze.py` validates frozen request hashes and compares only public inputs,
response metadata and opaque continuation sizes. `public-requests.json` redacts
native reasoning items. `summary.json` contains the quantitative audit;
its hash is `sha256:722d0f3b449e0cd7598cbbf219a35327572aab871c1c33d7c555f5497cef03f5`.
`mechanism-tests.xml` records the three local checks. Documentation layout checks
also passed all five tests (`docs-tests.xml`). The final commit receipt is stored
separately in that root.

The earlier [execution record](2026-10-25-original-feedback-live.md) and closed
historical records are preserved; this follow-up refines the interpretation of
generated versus accepted calls without rewriting the experiment outcome.
