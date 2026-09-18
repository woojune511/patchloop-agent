# Fixed-candidate counterexample discovery

## Question and boundary

Can the same model construct and execute a requirement-refuting input when explicitly
asked to review a fixed candidate? P11 supplied a useful public check at the outset;
that observation does not answer independent discovery. This diagnostic isolates that
question from patch repair and from voluntary verification during a solve.

`diagnostics.counterexample_discovery` implements `prepare`, `validate` and an offline
`rehearse`. `diagnostics.counterexample_discovery_rollout` now implements the bounded
collector, executable packet and read-only interrupted inspection. The first live sample
is **CLOSED / INFRASTRUCTURE_STOP**; the original design packet remains unchanged.
A separate authorized sample after the thread repair is now closed with a complete
probe and no model-supported counterexample; see the latest observation below.
Preparation never instantiates a provider client or reads credentials. All records are
external, immutable files with a `dev-run-v1` preparation/rehearsal journal; `official=false`.
The published packet is the final write. An incomplete directory cannot be reused.

## Frozen input

The exact input consists of:

- The original `pydantic-ai-synthetic-tool-reasoning` public task, including its two
  existing check definitions. No historical check verdicts are supplied.
- The exact P10 public patch, hash
  `sha256:9e7a8e144e1bf385aef59bb916461748bf9c4bfa46a8a8efa94fa54d6bd233f9`.
- A generic discovery instruction, original read/search/probe schemas with `brief-v1`
  annotations, prepared public dependency capability, and `report_discovery`.

The builder accepts no historical context argument. P10 plans, reasoning, trace,
outcomes, P11 task/check/case/patch, evaluator material and operator diagnoses are absent.
Local artifact paths and preparation identifiers are kept in the operator packet.
The model sees the neutral candidate name and public source/task identity only.

The same `gpt-5.4-2026-03-05` / `medium` model and 25,000 output ceiling are proposed.
One fresh sample, up to 40 model calls, 100 tools, 1,800 seconds and 60,000 input tokens;
total cap $1.20. The executable packet binds the exact repository `.env`, pricing reviewed
on its execution date, implementation/runtime identity and invocation cap. Preparation
does not consume a sample. Execution exclusively creates its bound result directory;
once created, that directory cannot be retried, resumed or replaced by this packet.

History starts fresh. Subsequent calls append only this diagnostic's native results and
opaque continuation; there is no inherited segmented handoff. This is a separately
elicited discovery task, not an unchanged-policy A/B arm. The candidate remains fixed;
only read/search/probe and the report terminal are offered. No mutation, registered-check
execution, patch submission or hidden evaluation occurs in the discovery loop.

## Collector and recovery

The collector reuses `fresh_state_rollout.dispatch`, `episode_requests.DiagnosticClient`,
`DevToolGateway`, `DevCostLedger`, and the active native exchange builder. It does not
restore a source solve. The exact frozen two-message request starts a new history;
only this run's tool calls, public results and encrypted continuation are appended.
Provider reasoning summaries are excluded. Each counted request is stored in CAS.

Count immediately before dispatch; zero SDK retries. Admission reserves the full
25,000 output ceiling and rejects input above 60,000 tokens. Count/response/client
cleanup waits are bounded by the existing 30/300/5-second transport contract and the
remaining run deadline. Preflight has a separate 180-second bound. Source and dependency
identities, fixed patch, tool grammar and probe image/profile are checked before use.
The candidate is cloned locally and each probe uses the prepared public source/dependency
snapshot. The collector does not start Docker or pull/build an image.

Usage, cleanup, continuation and action uncertainty stop the sole sample. Known usage
survives a late response, and no late tool action is admitted. `inspect` verifies the
journal chain, execution identity, CAS artifacts and any published result without a
client, credential, workspace creation or another action. Interrupted results remain
interrupted; inspection never resumes or repairs them. Action receipts retain the
existing `action_id + input_hash` replay contract.

`report_discovery` binds its cited probe to the recorded program, candidate and receipt,
and records whether the requirement excerpt occurs in the public issue. A complete
receipt or zero exit does not prove a behavioral mismatch. `discovery_outcome` remains
null and `PUBLIC_REVIEW_REQUIRED` until the separate public-evidence review below.
Mock accounting is explicitly labeled simulated and reports zero live provider calls.

## Judgment

`report_discovery` can report a counterexample, no discovery, or a blockage. Reports are
claims to inspect, not an automatic verdict. A reproduced mismatch requires all of:

1. A literal public requirement and a justified expectation for the precise input.
2. A model-authored program bound to its recorded action, source and candidate hashes.
3. Execution of the current workspace implementation, with observations derived from
   that execution. Imports, printed assertions and line-entry hits alone are insufficient.
4. Complete actual/expected evidence of a behavioral contradiction. An import error,
   setup failure or nonzero exit alone is insufficient.
5. Complete receipts and confirmed cleanup, without unresolved execution uncertainty.

The public review checks those facts from recorded code and execution output. It does
not read hidden evaluator details, consult P11's case, run another candidate, or pay for
a judge. It records `REPRODUCED`, `NO_REPRODUCTION`, `CENSORED`, or `INFRASTRUCTURE_STOP`.
Call/probe counts and concise plans are secondary behavior evidence. Limits and setup
failures remain separate from a completed search without reproduction.

Success would justify inspecting why verification was not selected during earlier solves.
It would not prove that action selection is the unique cause: explicit instructions and
a fixed-candidate review change the task. Failure would leave requirement interpretation,
case design and execution obstacles to distinguish from the public trace. Neither result
changes runtime defaults or establishes general model capability from one selected patch.

## Optional expectation guidance

Preparation accepts `--review-guidance original|requirement-scope-v1` (default original).
The optional variant adds only a generic system-instruction paragraph. It asks the
model to derive expectations from the complete public requirement, including scope,
exceptions and preservation, then justify how the actual constructed input meets that
scope. When applicability depends on origin or construction, matching attributes alone
are insufficient. An unsupported expectation stays uncertain; the report must describe
what the program actually exercised. No task-specific input, expected answer or prior
diagnosis is supplied. This does not mechanically verify the model's interpretation.

Existing question, turn-decision and report fields carry concise public summaries.
There is no schema extension, compulsory extra action, new plan policy or semantic
parser. Tools, user context, model settings, limits, native continuation and stopping
rules are byte-identical between requests; only `input[0].content` differs. Default
request bytes remain identical to the previous closed observation.

The selected variant is bound in `packet.json`, `protocol.json` and the executable
plan. `fresh_request_unchanged` means the collector copies its selected design's request
without alteration; it does not mean a guided request equals the original prompt.
Validation reconstructs the selected guidance and rejects a removed/changed selection
or changed prompt before execution. The original form omits the optional metadata.
Frozen implementation identities still apply; never rewrite old packets for new code.
Read-only `inspect` continues to validate old closed journals without resuming them.

The provider-free record at
`C:\pt\analyses\counterexample-expectation-guidance-20260918-v1` contains fresh original
and guided design packets and their exact request comparison. Neither is a new paid
executable plan. The guided source/dependency rehearsal and scripted toy collector trace
pass. Focused 70 PASS/87.42s covers both request variants, selection/byte tampering,
unknown selection, CLI preparation, unchanged nullable reporting and native feedback.
Shared regressions 41 PASS/60.08s include both context policies' isolated mock evaluations
and actual task/diff/check delivery. Runtime-wide regression remains the unchanged
thread-compatibility receipt; it was not repeated for an instruction-only diagnostic.
At preparation, live model efficacy and independent discovery were NOT_RUN. The
separately authorized guided observation below is now closed without a supported discovery.

## Optional applicability contrast

`--review-guidance applicability-contrast-v1` extends preservation-case selection below.
The last observation selected a valid preservation case by switching off a candidate
condition, leaving behavior under the same condition but different public applicability
untested. The new generic instruction makes these two distinctions explicit in the probe
call. It does not supply a task-specific example, past counterexample or expected answer.

`case_selection.trigger_contrast` is null or an object with:

- `candidate_trigger`: the whole candidate condition, including each conjunct, derived
  from the inspected patch/source (1-300 characters).
- `preserve_satisfies_trigger`: true/false/null for the model's hypothesis about whether
  the preservation input still satisfies that whole condition. Null means unknown.
- `applicability_difference`: the public requirement separating the inputs' applicability
  and how their construction differs (1-300 characters).

The strict schema requires these object properties; optional values are nullable.
Scripted calls may omit the annotation. Runtime binding checks only shape and bounds.
The model is asked to print relevant constructed values and observations per selected case.
A false relation yields public feedback that same-trigger preservation is unresolved,
suggesting a supported contrast or a reported limitation. A true relation remains a claim
to compare against actual construction and output. Unknown/missing/invalid records return
an unresolved question. A relation without a preservation case cannot support that claim.
No annotation gates a probe or report, and no relation is inferred from arbitrary programs.

Every result remains `model_authored_unverified`, `coverage_status=not_assessed`.
Raw annotations participate in shared action hashing; replay returns the saved feedback,
and changing the relation under the same action ID conflicts. No contrast carries into a
later omitted/null record. The gateway subclass applies only to this option. The default,
requirement-scope-v1 and preservation-cases-v1 initial request/prompt/protocol bytes remain
identical to sealed preparation records. Core runtime, available actions and limits remain
unchanged. Design and executable metadata bind the option and implementation hash.

Provider-free feature validation passes 24 tests in 13.36s; all three diagnostic files pass
117 in 129.77s with durations (combined suite exceeds two minutes). Shared regressions
pass 41/60.09s, including both context policies' isolated mock evaluation and public
task/diff/check delivery. Ruff, offline prepared-source rehearsal, scripted contrast
feedback and read-only inspection of the last closed run pass. Zero live provider/count,
credential or Docker operations. The unchanged core runtime reuses the prior resolved
2,776 PASS/12 SKIP full-regression receipt rather than rerunning it.
This confirms delivery, advisory behavior, identity and recovery, not better model
selection or discovery. No fresh
paid sample or executable real-task packet is included, and all older budgets remain closed.
Evidence: `C:\pt\analyses\counterexample-applicability-contrast-20260918-v1`.
The separate live observation below evaluates use of this option; it does not modify that
provider-free implementation record or reopen any earlier budget.

## Applicability-contrast live observation: 2026-09-19 KST

User continuation authorizes one new same-task/P10/GPT-5.4 medium observation under a
new $1.20 cap. Runtime/diagnostic commit `bd94da0e`; original public task, fresh independent
source clone/native history, existing dependency/image. No prior counterexample or finding
is injected. Plan hash:
`sha256:d211c7531c944be11388e605df1b5921d4988c530cf1e014eb6696250438844e`.
One planned/started/reported sample closes after seven counted model calls, six searches,
four reads, one probe and one report. No infrastructure or resource-limit stop.

The model first considers effective-profile lookup, reads the nested mapping context,
then chooses direct tool-only serialization with a reused DeepSeek profile and an intended
custom field. Its preservation input uses the default plain OpenAI profile. The annotation
sets preserve_satisfies_trigger=false. That same-trigger applicability boundary remains
untested; no follow-up probe occurs after the advisory feedback.

The recorded construction is a custom-field OpenAIModelProfile followed by
update(source_profile). Both printed source_profile and custom_profile contain
reasoning_content, and serialization outputs reasoning_content=''. The assertion expects
custom_reasoning='' and exits1. Default plain OpenAI serialization matches its expectation.
The public trace therefore shows an input setup mismatch, not a demonstrated failure to
honor the actual configured field. A read-only operator view of public ModelProfile.update
and the thinking-field default corroborates why the incoming source field overwrites the
custom value. Those supporting source excerpts were not model-delivered in this run;
the decisive actual-profile and output values were delivered. No new program was executed.

The next/final actual request contains the full receipt and the explicit same-trigger
warning. The model reports counterexample_reported, treating the assertion as a copied-field
requirement violation. Its limitation acknowledges the copy method might differ, but does
not verify the required renamed setup. Public review: **NO_REPRODUCTION**, supported
discoveries0/1; the reported counterexample is unsupported. This says nothing about overall
candidate correctness. The paraphrased/ellipsis excerpt fails literal binding as a separate
issue. All four added lines are observed in the launch thread; not per-case semantic coverage.

All seven requests/public-result deliveries, complete output and cleanup pass. Cost
$0.1730905; cache-neutral$0.3772825; max input28,104; active142.649s/wall248.831s.
Generation usage is recorded; invoice/count-endpoint billing remains unverified. The one
slot and unused$1.0269095 are closed. No retry/resume/replacement, extra candidate/baseline
execution, paid judge or hidden evaluation. Task acceptance NOT_ASSESSED; official=false.

Do not connect the diagnostic option to repair defaults based on this observation.
Next priority is checking actual probe construction before classifying a failed assertion
as candidate behavior. This record authorizes no further prompt variant or paid sample.
Current implementation tests are reused unchanged (117 diagnostic,41 shared,3 docs,Ruff,
both isolated mocks; unchanged runtime full regression). Only the new documentation is
checked again after this observation. Evidence:
`C:\pt\analyses\counterexample-discovery-applicability-20260919-v1`;
raw state: `C:\pt\pl-discovery-contrast-live-0919a`.

## Optional preservation-case selection

`--review-guidance preservation-cases-v1` extends the scope guidance with a concrete
case-selection step inside the existing probe call. Where the public task supports a
preservation boundary, the model selects a nearby input sharing the proposed code trigger
outside the change scope and preferably exercises it in the first probe. The model derives
the input from public requirements/source; the harness supplies no task-specific case.

The diagnostic's `run_probe.case_selection` is null or an object with
`change={setup,expected}`, `preserve={setup,expected}|null`, `scope_basis`, and
`selected=change|preserve|both`. It reuses the existing behavior-case shape and 300-character
string limits. `selected` describes what the program intends to exercise. Unsupported
preservation scope stays null with an explanation. The strict schema requires the nullable
field; the collector also accepts omission for existing scripted calls. Null, omission and
malformed annotations produce advisory diagnostics without blocking the probe/report.
Selecting a missing preservation case produces a diagnostic, not a fabricated case.

A diagnostic-only gateway wrapper binds the annotation to the public-task hash and returns
it beside the probe's source/diff hashes and actual output. Native feedback asks the model
to compare the selected setup with actual construction and observations, then investigate
remaining useful cases or report the limits. Every receipt retains
`model_authored_unverified` and `coverage_status=not_assessed`, including wrong expectations,
normal exits, failed assertions and missing cases. The gateway never interprets the program
or upgrades selection to execution/coverage proof. Reports retain the same public-review
requirement. No extra tool, compulsory probe, planning policy or report gate is added.

Raw arguments, including the annotation, remain in shared `action_id + input_hash` admission
and journal records. Completed replay returns the original receipt without another probe;
changing a selection under the same action ID conflicts. Later null/omitted annotations
cannot inherit earlier cases. The wrapper applies only to this diagnostic option; runtime
and dev-loop defaults are unchanged. The original and requirement-scope-v1 request, prompt
and protocol bytes remain unchanged. For the new mode, only generic system guidance and the
nullable probe schema differ initially; the new feedback is linked to the selected request.
Design/executable metadata bind the mode and implementation. Older closed journals remain
read-only inspectable; their samples and budgets are closed.

Provider-free evidence is recorded at
`C:\pt\analyses\counterexample-preservation-cases-20260918-v1`.
The feature-focused tests pass 11/8.02s; all three discovery files pass 93/147.28s,
exceeding the two-minute target for the combined diagnostic suite. Shared paths pass
41/67.42s, including both context policies' isolated mock evaluation and actual public
task/diff/check delivery. Ruff, the real offline source rehearsal, and scripted toy
case-selection feedback pass. Old original/scope request bytes and closed-journal
inspection are verified. The unchanged runtime retains the prior full-regression
receipt; it was not rerun for this diagnostic-only change.
The provider-free implementation record does not establish live case selection or efficacy.
The separately authorized live observation below assesses its use; no default is adopted.

## Preservation-case live observation

The separately authorized one-sample preservation-cases-v1 observation is closed at
implementation commit `8e0fed11`. Original task/P10/GPT-5.4 medium, new $1.20 cap,
fresh prepared workspace and native history; no prior case, result or solution input.
Eight model/count calls, nine source inspections, two probes and one report finish normally.
Public review is NO_REPRODUCTION, supported model discoveries 0/planned1.

The model first chooses copied/reused DeepSeek field and auto profiles with an alternate
field name, two deferred capability loads and later history replay. Its initial
`base.update(OpenAIModelProfile(...))` does not apply the default-valued auto override,
leaving field mode. The apparent preservation mismatch is a setup error, not a candidate
counterexample. After two searches and a read of ModelProfile.update, it uses
dataclasses.replace and prints the actual modes. The second probe observes the expected
synthetic empty fields in field mode and their absence in auto mode, while preserving
the existing fixture values. The final report accurately limits its no-counterexample result.

Both probes use selected=both, and their annotation/actual-output feedback is delivered.
Concrete case selection, execution and correction of setup are supported observations.
Auto mode disables the candidate's field-mode guard. Ordinary profiles that retain the
same field/nonempty-name/tool-call trigger without the requiring provider profile are
not exercised. Selecting that applicability contrast remains open; one selected result
does not establish an improvement or justify adoption. The combined/reordered requirement
excerpt fails literal source binding. Some 300-character expectation text ends mid-phrase;
programs and complete outputs are the review evidence, not those labels alone.

Both receipts have complete output and confirmed cleanup; exact owned containers are absent.
All eight actual inputs preserve the frozen request and preceding public results. All four
added lines are observed in each probe's launch thread, not per-case branch/semantic coverage.
Recorded cost $0.3083795, cache-neutral $0.6139475, max input37,139; active331.857s/wall460.933s.
Sample and unused $0.8916205 are closed; no retry, resume, replacement or additional candidate
execution. official=false, task acceptance NOT_ASSESSED, hidden evaluation NOT_RUN.
Evidence: `C:\pt\analyses\counterexample-discovery-preservation-20260918-v1`;
raw run: `C:\pt\pl-discovery-preserve-live-0918a`.

## Preparation and validation

The external record is `C:\pt\analyses\counterexample-discovery-20260918-v1`.
`packet/request.json` contains the actual initial request bytes. `packet/protocol.json`
contains the predeclared judgment and stopping rules; `packet/packet.json` binds both.
Use `python -B -m diagnostics.counterexample_discovery validate --root <packet>` for
read-only reconstruction. `rehearse --root <packet> --output <fresh-external-root>` checks
dependency contents, clones prepared source independently, applies the exact candidate,
reads its hunk through `DevToolGateway`, and verifies idempotent read recovery. This does
not execute a model-authored probe or establish model capability.

Focused tests prohibit network/provider/Docker access and private sibling reads. They
cover input provenance, tampering, interrupted publication, exact independent workspaces,
dependency corruption and read recovery. Existing probe/dependency tests exercise mocked
execution, action identity, current-source delivery and isolated evaluation separately.
Runtime/default/task bytes stay unchanged; full-suite evidence belongs to that unchanged
runtime and is not a newly executed full regression.

Executable evidence is `C:\pt\analyses\counterexample-discovery-executable-20260918-v1`.
`packet/plan.json` binds the untouched initial request and one fresh result directory.
The module's `prepare`/`validate` commands prepare and inspect that packet; `run` requires
both `--plan-root` and the exact `--plan-hash`. `inspect --root <result>` is read-only.
The frozen price review must match the UTC execution date. The live result directory was
consumed by the 2026-09-18 observation below; it cannot be reused.

Collector tests: 45 PASS/85.79s, covering native public feedback, terminal reporting,
full output reservation, call/tool/time/input bounds, invalid tools, source/packet/CAS
identity, uncertainty, cleanup and interrupted inspection. Shared regressions: 56 PASS/
75.72s, including the real response parser and both mock isolated evaluations. A durable
toy smoke records read -> simulated probe -> report with actual follow-up request bytes.
It proves collector plumbing only; it is not live discovery or real probe evidence.

## Latest closed observation: requirement-scope guidance, 2026-09-18

One new same-task/P10/GPT-5.4 medium sample with its own $1.20 cap is closed.
`C:\pt\analyses\counterexample-discovery-guided-20260918-v1` binds the already sealed
guided design to a new executable packet; raw state is
`C:\pt\pl-discovery-guided-live-0918a`. Plan hash:
`sha256:78ee481f0367c3bf5df1b99ff73f97e772edeeb15a6b037a9999c95efbbad0f4`.
Only the system instruction differs from the original request. All 849 prior evidence
files pass preservation verification; fresh source/dependency/read rehearsal passes.
Runtime and collector validation are reused from unchanged committed code.

Nine counted model responses finish normally: three reads/five searches, one probe
at turn8, then the terminal report. Some inspection summaries discuss supplied-profile
reuse and alternate field names; the executed program uses only DeepSeek's supplied
default profile. Two deferred capabilities, two agent runs with explicit history reuse
and six offline SDK requests complete. The later body contains six assistant tool-call
messages, each with string reasoning_content; two synthesized search_tools messages
have the empty string and the four fixture-origin values are retained. Source imports
resolve to current workspace code. All four added lines receive launch-thread events.
Full feedback reaches turn9 before no_counterexample_found; cleanup is confirmed.

Public review: NO_REPRODUCTION / independent discovery NOT_ESTABLISHED, 0/1. The
executed expectation and actual setup are supported, but this is an in-scope case.
Ordinary-profile preservation, supplied-profile reuse/copy and other replay modes are
not tested. The final report explicitly limits its coverage. Do not infer that the
earlier wrong expectation was corrected on its ordinary-profile input: the program
chooses a different case. Do not infer a causal improvement from one observation per
instruction condition. The report paraphrases its requirement excerpt, so literal
binding is false; the full task still supports this executed case's expectation.

Recorded cost $0.220049; cache-neutral $0.448145; max input 29,665; active 183.705s,
wall 306.243s. All usage is recorded; invoice/count-endpoint billing remains unverified.
No infrastructure or resource-limit exit. Task acceptance/hidden evaluation remain
NOT_ASSESSED/NOT_RUN. The one slot and unused $0.979951 close with this report.
No retry, resume, replacement, extra candidate/baseline execution or default adoption.
Next diagnosis: selection of a concrete input testing preservation outside the change
scope. The current generic guidance has not established improved discovery.

## Earlier closed observation: bounded-thread profile, 2026-09-18

User continuation authorized one new same-model/medium diagnostic with its own $1.20
cap. `C:\pt\analyses\counterexample-discovery-thread-20260918-v1` holds the new design,
executable packet, admission and public review; raw state is
`C:\pt\pl-discovery-thread-live-0918a`. Plan hash:
`sha256:916b79cbbf9f42159885587db2ba9d894222315efdd1d39ff4ac9d1eb8d7d167`.
Initial request bytes remain identical to the prior diagnostic. Only the design's
runtime hash and probe profile change. Fresh independent source/dependency rehearsal
passes before dispatch, using existing Docker/image only. No prior findings are injected.

Five counted model responses complete: search/search -> read/search -> read -> probe ->
report. The single program calls current workspace code, performs four offline SDK
requests, two deferred loads and final history replay, and exits0 with complete output
and confirmed cleanup. All four added source lines receive launch-thread events. Exact
probe feedback reaches the last actual input; all five requests pass the public audit.

The model reports `no_counterexample_found`. It builds a fresh ordinary
`OpenAIModelProfile(field, alt_reasoning)` and `OpenAIProvider`, with no supplied DeepSeek
profile. It expects the direct tool-only response to contain `alt_reasoning=''`, observes
that insertion and accepts it. The report describes a copied profile; the recorded program
constructs a new one and does not exercise supplied-profile reuse or copying.

Public review records `NO_REPRODUCTION` / independent model discovery NOT_ESTABLISHED.
This does **not** mean no violating behavior was observed: the task preserves ordinary
profiles and the supplied diff introduces the unconditional field-mode insertion.
The recorded direct response therefore exposes that preservation violation. The operator
derives the correct expectation (omit the empty field) from the public task/diff, without
executing another baseline or candidate. The model's own expected/actual pair matches;
it does not identify or justify the mismatch. Keep operator recognition separate from
model-discovery credit. An executed case and complete line coverage do not validate its
expected behavior.

No resource-limit exit or infrastructure stop. Cost$0.1471595, cache-neutral$0.2266475,
max input18756, active148.389s/wall263.851s; 5 inspections/1 probe/1 report. Known count
and provider usage; invoice/count-endpoint billing remains unverified. Acceptance and
hidden evaluation NOT_ASSESSED/NOT_RUN. The new slot and unused budget are closed, with
no retry, replacement or resume. Prior closed records and the runtime remain unchanged.

Next diagnosis should test how the agent derives expected behavior from the complete
public requirement and verifies the probe setup's claimed origin. Do not change default
planning/context policies or supply the known contrast automatically from this single
observation. Runtime regression, both isolated mocks and real Docker thread coverage
are reused from the unchanged `4b2a58c8` compatibility receipt; the live result is new.

## Earlier closed live observation: 2026-09-18

User continuation authorized the exact one-sample/$1.20 packet. The original input and
all150 executable evidence files were verified before dispatch. Existing Docker/image
only; no startup, pull or build. Execution at runtime/collector commit `1dfa42e7` ends
with `REPORT_RECORDED` after 7 model/count calls, 11 reads/searches, 1 probe, 1 report.
The model reports `blocked`; public review records `INFRASTRUCTURE_STOP`, not a successful
discovery or a completed negative capability result. Task acceptance stays NOT_ASSESSED.

The first probe follows five inspection responses. It prints current `/workspace` module
paths and directly calls `_map_model_response`, then runs a deferred capability scenario
using `httpx.MockTransport`. SDK2.29.0 calls `asyncify(get_platform)` before transport;
the asyncio implementation uses `asyncio.to_thread`. Traceback reaches thread creation
and reports `RuntimeError: can't start new thread`. Probe code denies clone/clone3 and
uses pids_limit=2; the trace does not isolate which kernel restriction failed first.
The traceback exceeds 12,000 captured bytes (13,008 observed), yielding output_limit,
truncated=true and exit=null. Cleanup is confirmed; elapsed/container timeout flags are
false. The changed-line report is unavailable. None of this establishes a task defect.

Independently, the model's expected behavior is too broad. Its program creates a fresh
ordinary `OpenAIModelProfile` in field mode with `alt_reasoning`, without a supplied
DeepSeek profile, and expects an empty field. The original public task preserves ordinary
profiles unless given the requiring provider profile. The supplied patch itself shows
this unconditional field-mode insertion was newly added. The direct output matches the
model's unsupported expectation; its final report calls that behavior correct. Public
review records this expectation error without importing P11's check or rerunning a case.
The partial direct output cannot satisfy the frozen complete-receipt discovery criteria.

Recorded generation cost $0.2577015; cache-neutral $0.4425975; maximum input33355;
active loop183.065s/wall289.636s. Count/billing known for all7 responses; invoice/count
endpoint billing remains unverified. No global cost/input/call/time limit exit. Native
history is fresh append-only with no segment transitions. All7 actual requests and prior
public results pass the read-only delivery audit; exact candidate remains fixed, no
untracked files, no owned probe containers. No hidden evaluator read or execution.

Observation/public review: `C:\pt\analyses\counterexample-discovery-observation-20260918-v1`.
Raw execution: `C:\pt\analyses\counterexample-discovery-live-20260918-v1`.
The one sample and all unused funds are closed. Next work is provider-free
characterization and correction of SDK local initialization versus probe isolation;
retain the expectation error separately. This observation permits no automatic extra
candidate, paid judge, retry, resume, new prompt policy or runtime default adoption.

The report schema follows [OpenAI Docs strict function schemas](https://developers.openai.com/api/docs/guides/function-calling#strict-mode):
object properties are required, optional values are nullable, and extra properties are
forbidden. Schema preparation is not proof of live provider admission.
