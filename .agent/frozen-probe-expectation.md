# Frozen expectations for diagnostic probes

`diagnostics.counterexample_discovery prepare --probe-expectation frozen-json-v1`
adds an optional host-side JSON comparison to fixed-candidate discovery. It composes
with all four review-guidance modes and `--case-design task-first-v1`. Omission
preserves their request and protocol bytes. Core dev tools, repair defaults, task
inputs, planning policies and public checks are unchanged.

## Why this seam

The closed task-first probe derived its displayed expected count and tool names
from observed messages, and asserted only that selected fields were strings. The
subsequent offline fixture accepted ten synthetic corruptions under that predicate.
An expectation written before execution and compared outside the program removes
that opportunity to replace the expected value during this probe. It does not choose
the right applicability boundary or ensure the model writes a useful expectation.

## Contract

- The existing `run_probe` schema gains `expected_json`: a required nullable string
  in strict mode, following [OpenAI's strict-mode contract](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).
  Null/omission leaves an ordinary probe; the string `"null"` expects JSON null.
- A supplied value must encode one JSON value, at most 2,048 UTF-8 bytes both before
  and after canonicalization. Duplicate keys, nonfinite numbers, invalid Unicode,
  oversized or malformed JSON fail before sandbox execution through the existing
  failed-action path. There is no automatic retry or repair.
- The existing `action_started` stores the complete raw arguments and `input_hash`
  before probe dispatch. The host parses the expectation before running the program;
  it passes only the normal question/source/execution identity to the sandbox.
- The program prints exactly one JSON observation. The host reuses the core JSON
  observation parser and compares complete canonical values. Object key order is
  ignored; array order, values and types are preserved. Extra/missing fields differ.
- `expectation_comparison` records `matched`, `mismatched` or `not_compared`, bounded
  canonical expected/observed strings and hashes, reason, source hash and diff hash.
  Unhealthy, incomplete or invalid output is `not_compared`, never a behavior verdict.
  Existing cleanup, identity, deadline and accounting stops still apply.
- Native feedback carries the comparison together with existing setup and case
  selection receipts. Replay returns the durable result without another execution;
  changing an expectation under the same action ID conflicts. Interrupted diagnostics
  remain inspect-only. Reports require no positive comparison or additional probe.

The tool description asks the model to derive concrete expected contents from the
public requirement and compute actual observations from current project code. The
host does not verify that reasoning, prior-observation independence, program truth,
field selection or coverage. A model can still choose a weak boolean, copy an earlier
observation, print constants, or make a semantically wrong prediction. Every receipt
is `model_authored_unverified`, with no semantic verdict and coverage `not_assessed`.
No task-specific contrast, expected answer or historical observation is supplied.

## Preparation, cost and evidence

The option and its implementation hash are frozen in the design; the executable plan
binds the option and all diagnostic implementation files. Staged preparation retains
the exact task-only first request; the new schema becomes visible after the proposal.
There is no new tool, model round trip, execution action or case requirement. The
longer probe schema/feedback can change counted tokens if a future run is authorized.
The same invocation cap, output reservation, limits and zero-retry dispatcher apply.

Implementation evidence is provider-free: local JSON adversarial cases, actual native
mock feedback, replay/conflict/interruption checks, packet tamper rejection, existing
diagnostic regression and both context-policy mocks through isolated evaluation.
An offline prepared-source rehearsal and eight-mode request/protocol byte comparison
cover real frozen inputs without executing a candidate probe. Closed historical
inspection remains readable. Evidence is outside the repository at
`C:\pt\analyses\frozen-probe-expectation-20260919-v1`.

Validation: focused56 PASS in40.41s, diagnostic/setup regression190 PASS in179.49s
(`--durations`), documentation3 PASS and Ruff PASS; 249 distinct tests. Both core mock
contexts reach mutation, public check, submission and isolated evaluation. The broader
core suite is not rerun: the preserved unchanged-runtime receipt has 2,878 PASS/16 SKIP
and six schema snapshot failures, followed by 11 passing correction checks covering
all six. That receipt is not a clean full rerun. All1,661 prior entries are preserved;
provider/count/credential/Docker operations and model cost are zero for this change.

This implements comparison mechanics only. No new paid sample, acceptance result,
discovery improvement, default adoption or completed A/B comparison follows. Earlier
sample budgets stay closed; concrete scope selection and semantic expectation quality
remain open research questions.

## Closed live observation

One separately authorized sample at implementation commit `dc962a56` keeps the exact
task/P10/GPT-5.4 medium/task-first/applicability-contrast settings and adds only this
option. The task-only first request is byte-identical to the preceding sample. New
cap$1.20/repeat1, fresh source workspace and history; no earlier findings are supplied.

The model proposes four cases, searches/reads source, then supplies a literal JSON
expectation on turn5. Its program imports `check_setup` from a nonexistent project
module and exits1 before behavior checks. Host status is not_compared. Turn6 removes
only that import and uses the sandbox-provided helper; its unchanged expected JSON
exactly matches healthy stdout. Five setup rows pass (four paths and final `done`).
Both expectations were recorded before execution and their full receipts reach the
following requests. The final report says no_counterexample_found.

Manual public review separates this report from the actual construction. Program
lines35-37 instantiate OpenAIModelProfile with field mode and field name `reasoning`,
then pass it to OpenAIProvider under `fixture-other`. No DeepSeek profile is obtained
or copied. The public preservation clause and supplied P10 diff entail no new empty
field for this ordinary profile, yet the model's expected object and actual result both
contain `reasoning: ""`. Its report incorrectly calls the profile copied. Thus the
model executed the known applicability defect and expected its wrong result.

Supported autonomous discoveries remain **0/1**. The external review's REPRODUCED
classification is explicitly attributed to operator analysis of existing model trace
(one observed public mismatch), not to a model finding or another candidate execution.
Original host matched and model no-counterexample records stay unchanged. No hidden
evaluation or acceptance result is inferred. This failure is wrong applicability/expected
semantics despite a predeclared literal, not observed-value copying within these probes.

Three direct mappings have appropriate matching expectations; the fourth is the wrong
ordinary-profile expectation above. Deferred history has a fixed expected three-name
order and a string-field boolean, so expected names are no longer taken from actual
output. Exact empty/original thinking values, full arguments/IDs/returns and multiple
loads or separate-run replay remain unverified. The explicit preserve annotation still
disables the candidate trigger, and setup checks never establish profile origin.

Seven model/count calls, eleven actions, two probes, first probe turn5. Recorded cost
$0.2858285, cache-neutral $0.5113325, maximum input39,280; active254.228s/wall381.356s.
All7 request deliveries, source/diff identities and both containers' cleanup pass; no
infrastructure/resource stop. All1,687 prior evidence entries are preserved. Existing
249-test implementation validation is reused unchanged; documentation3 checks are new.
Sample and unused $0.9141715 close without retry/resume/replacement/extra program.

This confirms live use and setup-error correction, not autonomous discovery benefit.
Do not adopt into repair defaults or automatically run another paid variant. Grounding
expectations in actual object construction and the complete public scope remains open.
Evidence: `C:\pt\analyses\counterexample-discovery-frozen-json-20260919-v1`;
raw: `C:\pt\pl-discovery-exp-live-0919a`.
