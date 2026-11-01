# Diagnosis pilot: incompatible fields rejected before construction

Date: 2026-10-26. Follow-up to [host-built diagnosis requests](2026-10-26-diagnosis-request.md).

## Material Passport and selected question

- Origin: academic-research-suite / experiment-agent, run mode.
- Version: `diagnosis-request-live-v1`; `official=false`, `claim_eligible=false`.
- Verification: one live execution and saved public contract/receipt analysis.
  No independent repeat, corrected target replay or acceptance evaluation.
- Runtime commit: `f378b528c9b243d0ca20d44287f8725d28e5e19e`.
- Runtime hash: `sha256:34f859e75556d99fc59b61f599d8a530abdf2236a114f864fc6029b51d0c6e01`.

The [preceding pilot](2026-10-25-helper-correction-live.md) requested two call-path
diagnostics after an ineffective repair; both failed before execution because of
replay identity and function-line coordinates. The intervention moves those
coordinates into the host while retaining model choice of public functions/fields.
The question was whether this enables useful diagnosis, a revised repair hypothesis
and elimination of the original F0010 within unchanged resource limits.

Predeclared alternatives included no eligible diagnosis, wrong/absent focus,
irrelevant or incomplete observations, ineffective uptake, and resource/trajectory
limits. No historical repair, diagnostic source or private evaluator content was
seeded into the solver. Valid admission alone was not an adoption criterion.

## Frozen scope

The current user experiment request, within the continuing exact scope, authorized
one new invocation. Earlier allocations remained closed. Task:
`tasks/dev-train/current-dev20/13/public.yaml` (Astroid-1333); model
`gpt-5.4-mini-2026-03-17`, xhigh; credential file
`C:/Users/geonj/Documents/PatchLoop/.env`; repeat 1; invocation cap USD 1.20.

Normal output remained 40,000 tokens and protocol correction 25,000. Limits remained
40 model calls, 100 tool actions, four accepted edits and 1,800 active seconds,
with 1,920-second operator supervision. Context remained segmented-v1/result-or-size-v1,
planning brief-v1, probes enabled with policy none, repair-recheck, protected-v1
inspection, bounded-v1 acquisition and completion-recovery-v1 cost admission.
The run_probe recommendation remained enabled.

The request changed only state_root. Runtime changed as declared; the trusted probe
profile changed only call_path_trace_hash. Prepared source/dependencies, task hashes,
existing image identities and other policies stayed fixed. Two frozen public
post-submission checks retained their shared 120-second bound, conditional on a
submitted patch. No retries, resume, replacement solve or image acquisition occurred.

The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
and [standard pricing](https://developers.openai.com/api/docs/pricing) were verified:
the snapshot supports xhigh, with input/cached-input/output rates of
$0.75/$0.075/$4.50 per million tokens. Same-commit local evidence was reverified and
reused: 79 focused PASS, 349 quick PASS including isolated mock evaluation, Ruff
PASS and five documentation checks. This reuse is not new live repair evidence.

## Observed result

Run `run_dev_df3cc57b3ef44b9a` ended `VERIFICATION_INCOMPLETE`.

| Measure | Result |
| --- | --- |
| Model / input-count / tool calls | 33 / 35 / 33 |
| Search / read / probe / mutation actions | 15 / 14 / 3 / 1 |
| Original baseline / candidate | F0010 present / still present; comparable |
| Actual probe executions | 2: baseline and automatic original replay |
| Path requests / host constructions / diagnostic executions | 1 / 0 / 0 |
| Path-linked later mutations / selected comparisons | 0 / 0 |
| Helper requests / corrections | 0 / 0; NOT_EXERCISED |
| Both path-preparation projections versus offered tools | PASS on calls 31-33 |
| Required checks / selected tests / submission | NOT_RUN / NOT_RUN / NOT_RUN |
| Frozen public checks / independent acceptance / safety | NOT_RUN / NOT_RUN / NOT_RUN |
| Settled cost / unused allocation | $1.059124500 / $0.140875500 |
| Process wall time | 861.201 seconds, about 14 minutes 21 seconds |

Call 1 reproduced F0010 for a package directory missing its initializer; the
control package with its initializer had no F0010. Host and authored judgments
agreed. After 29 source inspections, completion-horizon closure offered only
replace_text and stop_task at call 30.

The accepted mutation wrapped `astroid/modutils.py::file_info_from_modpath`'s
`_spec_from_modpath` call in an ImportError handler. For a modpath ending in
`__init__`, it retries the parent modpath. The predicted effect was to resolve a
missing-initializer directory as a namespace package.

Automatic replay used the same frozen program and comparable caller/input/environment
identities. It still returned `bug_has_error=true, control_has_error=false`, with
matching host/authored judgments. Changed line 402 was unobserved. This refutes the
predicted original-case effect; it does not prove the entire function never ran.
Candidate diff: `sha256:5e3fd1e57eaf363a25be5dd091c977fa22438d4663a70149da45fe1f1374c42a`.

## Rejected request and resource boundary

The pending path gate was reached, but no diagnostic executed:

| Model call | Funded output ceiling | Output tokens | Outcome |
| --- | --- | --- | --- |
| 30 | 40,000 | 32,854 | First mutation |
| 31 | 13,344 | 13,344 | Incomplete; no action |
| 32 | 25,000, reserved protocol correction | 18,007 | Symbolic diagnosis request rejected |
| 33 | 6,414 | 6,414 | Incomplete; no action |

Call 32 selected `AstroidManager.ast_from_module_name` as focus and watched manager,
resolver and builder functions. It supplied neither a call_id nor line coordinates;
replay_action_id and python_source were null. However, question and purpose were
non-null. The delivered run_probe prose explicitly required all four to be null
for this mode, while the common tool schema still allowed string questions and
original_requirement purpose objects. The model returned an incompatible mixture
of symbolic diagnosis and original-case declaration fields.

`diagnosis_request.prepare` rejects that mixture before source construction. Its
message was `symbolic diagnosis uses the pending original; leave replay/source null`.
The validation path was `/`, not `/question` or `/purpose`. Thus the feedback named
fields that were already null and omitted the fields causing rejection. This is
an observed contract/usability defect, not evidence that the selected focus/fields
would pass later validation or yield useful observations. No corrected request was
executed during analysis.

The next response exhausted 6,414 output tokens without an action. The one protocol
correction credit had already been consumed at call 32; its 25K allowance itself
was not exhausted. Calls 31 and 33 report all output tokens as reasoning metadata;
reasoning content was not inspected. Overall output was 123,353 tokens, including
109,032 reasoning tokens; those are not additive.

The terminal horizon reported cost as blocking: $0.140875500 remained, funding
three minimum calls at $0.045576 each when four were required. Seven model-call
slots and 67 tool actions remained. Therefore neither the invocation cap nor the
call-count limit was literally exhausted; the remaining completion sequence no
longer fit the configured reserve. A higher cap's effect is unmeasured.

Both delivered path-preparation states correctly showed an unused allowance but
no currently offered preparation read/search on calls 31-33. This supports the
specific projection fix. It does not claim that every budget hint is an offered
action or that a useful preparation read occurred.

## Decision, limits and evidence

Original-failure feedback and incomplete termination prevented the ineffective
candidate from being submitted. The host-construction path was requested but
blocked before admission, so construction/trace/repair effectiveness remain
NOT_EXERCISED. The separate state-projection check passed in this trajectory.

The next bounded question is how to make the pending-diagnosis mode constrain the
request shape and identify actual offending fields, before another paid repeat.
More prompt text or output capacity alone does not remove the expressible invalid
combination. This record does not implement a new fix or authorize another run.

This is one stochastic trajectory on an exposed development task. The historical
comparison is descriptive; changes in focus, first repair, cost or elapsed time do
not identify causal improvement. Local mechanism PASS, request admission, useful
diagnosis, original-case repair and independent acceptance remain separate claims.

Evidence roots and hashes:

- Preparation: `C:/pt/diagnosis-request-live-ready-v1`, request hash
  `sha256:b18fee8081041a10958c0f0955b60a4d916df9eef662083832a5157b82b77561`.
- Run: `C:/pt/diagnosis-request-live-v1`, collection hash
  `sha256:81f27fad02cfc5400b243f791ebc1630ac6480231249e9d3990261d1e16f4d39`.
- `public-analysis.json` hash
  `sha256:1e4aec7ce2edd9c9fce465c32966ab7aa1812e38e10fe44d2c22264922781706`.
- `request-analysis.json` hash
  `sha256:6e67f72d0b5b257426f2f31442141417a5952902187256a6c05f138796fe8321`.

Collection verified journals, action/input identities and 168 content-addressed
objects; final closeout includes subsequent audit records. Runtime/task/prepared
inputs remained fixed, cleanup was confirmed, and billing/counting settled. The
post-submission assessment and independent evaluator did not run because there was
no submission. Analysis added no provider or target execution and inspected no
private evaluator content or provider reasoning. The allocation is closed.

Closeout documentation validation: five checks PASS in 1.884 seconds command wall
time, and git diff whitespace validation PASS. No runtime change was made in this
experiment; same-commit focused/quick/Ruff/mock evidence was reused as stated above.
