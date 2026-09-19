# Direct construction references for diagnostic probes

`diagnostics.counterexample_discovery prepare --construction-evidence direct-links-v1`
adds optional syntax evidence to fixed-candidate discovery. It composes with the four
review-guidance modes, task-first-v1 and frozen-json-v1. Omission preserves all sixteen
existing request/protocol combinations. Core repair tools, defaults and task inputs
are unchanged; task-first's first task-only input is unchanged even when enabled.

## Failure and bounded response

The last closed model probe constructs a generic profile but calls it copied from a
provider. Its frozen expectation predicts the candidate's unwanted output, so exact
host comparison matches. The gap is between the claimed construction, actual program
and public applicability, not a lost receipt or an incorrect JSON comparator.

This option lets the model attach a claimed direct reference to a selected assignment.
The host returns that code alongside the actual probe result, so the model can review
its claim against concrete syntax. This is a small inspection aid, not an automatic
origin tracker or an oracle for the correct expected behavior. It adds no tool action,
planning round, case requirement or gate on probing/reporting.

## Contract

- `run_probe.construction_links` is a required nullable array under the strict tool
  schema. Null, omission or an empty array performs the ordinary probe with an omitted
  evidence receipt. There are at most four links. Each has required fields:
  `target` (simple ASCII variable name, at most80 characters), `source` (same or null),
  `line` (positive assignment start line or null), and `requirement_excerpt` (1–600
  characters). Nested objects disallow additional properties. This follows
  [OpenAI strict-mode rules](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).
- Complete arguments are frozen by the existing action_started/input_hash before
  dispatch. Only normal program/question/identity arguments reach the sandbox.
  The host parses the bounded Python source using AST; it never executes probe code.
- Selection considers Assign and valued AnnAssign nodes with a simple name target.
  Without a line, exactly one matching assignment must exist. Multiple matches are
  ambiguous; an absent assignment or wrong line is unknown. No last-write assumption
  or scope resolution is made. Destructuring and augmented assignment are unsupported.
- A receipt includes the exact selected statement (at most1,600 characters), its start
  and end lines, and sorted names loaded in the right-hand expression (at most32 names,
  each at most80 characters). `direct_reference` is true/false for membership of the
  asserted source name, or null when no source was supplied or analysis is unknown.
  Attributes, strings and comments are not mistaken for loaded variable names.
- Lambdas, comprehensions, generators and assignment expressions have local binding
  complications and remain unknown. Oversized evidence is unknown rather than a
  partial name list. Malformed annotations or unparseable source yield advisory
  invalid/unknown receipts. Existing probe validation and execution failures still
  apply independently; the annotation itself never gates a probe or report.
- The receipt binds the public task, program hash and candidate diff. Excerpt matching
  only checks a whitespace-normalized literal substring of the public issue. The
  receipt remains model-selected, with no semantic verdict and coverage not_assessed.
- Native feedback includes the receipt with ordinary execution, setup, selection and
  expected-output receipts. Replay returns the saved result without another probe;
  changing the annotation under the same action ID conflicts. Existing collector
  count, billing, continuation, cleanup and no-resume rules remain in force.

For example, `clone = supplied.copy()` directly references `supplied`, while
`fresh = Settings(mode="field")` does not. If `alias = supplied; clone = alias.copy()`,
the selected clone statement directly references only `alias`. A missing direct
reference does **not** exclude indirect derivation. A present name does **not** prove
copying, runtime identity or execution: a factory can ignore it, scopes can shadow
it, or the branch may never run. The model must inspect relevant links/source and
interpret the complete public requirement, or report the uncertainty.

Preparation binds the option and its implementation hash; the collector plan binds
the added module with its other implementation files. Longer optional schema/feedback
may increase counted input tokens. The existing invocation cap, output reservation,
call/time limits and zero-retry dispatcher still apply. No new journal lifecycle or
runtime version is introduced.

## Validation and evidence

Evidence: `C:\pt\analyses\construction-links-20260919-v1`.

Focused tests cover direct versus indirect references, misleading attributes/literals,
ambiguous selection, bounded/unsupported syntax, no host execution, strict schemas,
actual native feedback, composition, replay/conflict, advisory failures and packet
tampering. Both core context mocks exercise mutation, public check, submission and
isolated evaluation. An offline prepared-source rehearsal checks real input identities
and read recovery without executing the candidate. All sixteen prior request/protocol
variants are compared with their pre-edit snapshots, and closed evidence stays readable.

A retrospective AST-only check uses **operator-supplied** links on the saved last
probe. Its `renamed_profile` assignment loads only OpenAIModelProfile and does not
directly reference deepseek; the subsequent model assignment references renamed_profile.
This receipt is separate from the immutable model trace. It is not an autonomous
discovery, a new candidate execution or future model input.

Validation: focused48 PASS/24.91s (both isolated mocks included), diagnostic/setup
regression239 PASS/211.35s with durations, documentation3 PASS and Ruff PASS; 290 distinct
tests. The initial attempt hit denied Windows default-temp permissions (5 PASS/43
fixture errors); a fresh explicit external temp path passed all48 without production
changes. All1,750 prior evidence entries are preserved. The broader unchanged core
receipt is reused: 2,878 PASS/16 SKIP/six schema snapshot failures followed by11 passing
correction checks covering all six, not a clean full rerun. Zero provider/count calls,
credential reads, Docker operations and model cost. Details are in the completion receipt.

No paid sample, acceptance result or model-behavior improvement is established by these
mechanical checks. Prior samples and unused budgets remain closed. A fresh observation,
if later authorized with exact live parameters, must let the model choose its own links
and assess whether it actually corrects a mistaken applicability claim; existing traces
cannot answer that question.

## Closed live observation

One separately authorized observation at implementation commit09abf40e retains the
original public dev-train task, P10, GPT-5.4 medium, task-first-v1,
applicability-contrast-v1 and frozen-json-v1; only direct-links-v1 is added. New
cap$1.20/repeat1, fresh source/history, same task-only initial request. The review
schema differs only in its new nullable property, required key and description suffix.
Existing Docker/image are reused. No prior cases, outcomes or answers are supplied.

Four initial cases are proposed. The preservation boundary is described as outside
field mode. Turn4's program obtains a DeepSeek provider profile but tries to override
its thinking field using update(keyword=...), which raises before setup/behavior
checks. The model reads the profile dataclass on turn5, then uses dataclasses.replace
on turn6. That program finishes with four passing setup comparisons. Its copied
provider profile, reused on OpenAIProvider with custom_reasoning, receives an empty
field; the default plain-profile control receives none. Both direct message objects
match the inline literal expectations.

Both calls send **construction_links=null and expected_json=null**. All six review
requests contain the new schema. Both omitted construction receipts, not_compared
expectation receipts and complete setup/scope/stdout/stderr reach subsequent native
inputs. No exact selected statement/reference receipt is produced. The program's
actual supplied-profile origin is already present before any such feedback, so it
does not demonstrate correction caused by the new mechanism.

Deferred history prints four reasoning values [fixture-1, empty, fixture-2, fixture-3]
and tool names [load_capability, search_tools, search_tools, roll_dice]. The program's
inline expected list has three tool names and no exact expected reasoning sequence.
The final report acknowledges the additional search_tools and treats the history
shape as implementation-specific. The expected three-name list is not established
by the public requirement, so that difference is not credited as a counterexample.
Exact argument/ID/return/grouping preservation, multiple deferred capabilities and
a separate subsequent Agent.run remain unverified.

The preservation annotation explicitly says its case does not retain the full
candidate trigger. No ordinary profile with the same field-mode settings is created.
Complete same-trigger feedback is delivered, but the model ends with
no_counterexample_found. Public review is **NO_REPRODUCTION, supported discoveries0/1**;
task acceptance is NOT_ASSESSED. Two of four initial excerpts bind literally; the
final excerpt combines clauses with ellipses and does not bind as one literal excerpt.

Metrics: seven model/count calls,13 actions, two probes, first probe turn4; recorded
model-rate cost$0.2706935, cache-neutral$0.4731575, maximum input34,863, active239.603s,
wall345.128s. Both cleanups are confirmed, owned containers absent and all seven input
deliveries verified. No infrastructure/resource-limit stop. Current runtime/source
hashes are unchanged; the prior290-test/Ruff/mock receipt is reused and three document
checks newly pass. All1,775 previous evidence entries are preserved.

The sole sample and remaining$0.9293065 are closed. No retry, resume, replacement,
extra candidate/baseline execution, hidden evaluation or default change. The observation
shows optional-feature non-use and the unresolved case-selection gap; it neither
establishes nor refutes a benefit from selected construction feedback. Future decisions
should distinguish whether evidence is selected from whether it is interpreted well.
Evidence: `C:\pt\analyses\counterexample-discovery-links-20260919-v1`;
raw: `C:\pt\pl-discovery-links-live-0919a`.
