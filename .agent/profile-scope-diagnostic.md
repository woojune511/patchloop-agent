# Public profile-scope diagnostic

The fixed operator command below retains its original behavior. A separate assisted
task now registers its exact public program as a third visible check:
`tasks/dev-train/pydantic-ai-profile-scope-diagnostic`. Its P11 outcome and the
post-run operator audit correction are recorded in that task's `audit.md` and
`C:\pt\analyses\profile-contrast-diagnostic-20260918-v1\result.md`. Parent task bytes
and earlier diagnostic records remain unchanged.

`diagnostics/profile_scope_check.py` runs one fixed public Python program on a clean
base and one supplied patch in two independent prepared-source workspaces. It is
an operator diagnostic, not a coding-agent tool, new task version or evaluation.

The public Pydantic AI issue requires empty thinking metadata for profiles supplied
by DeepSeek and preserves ordinary profiles. `profile_scope_program.py` keeps the
OpenAI client/provider, synthetic model name, field mode, configured field name and
tool-only message fixed. It varies ordinary versus DeepSeek-supplied profiles, using
both `reasoning_content` and a copied profile's `scope_reasoning` name. Expectations
come from the public issue, not hidden tests or an implementation-specific setting.

The program imports the actual workspace modules and checks their origins. It uses
the existing registered check's interpreter and dependency environment, with local
HTTP fixtures and blocked network connections. It reports all four comparisons even
when one fails. A mismatch is an observed public behavior result; missing/malformed
output, timeout, truncation, cleanup uncertainty and abnormal exit stop the pair.

Run from the repository using an existing prepared source, a previously supplied
patch and a fresh external output directory:

```powershell
.venv\Scripts\python.exe -B -m diagnostics.profile_scope_check `
  --prepared-source C:\pt\sources\prepared-source.json `
  --candidate-patch C:\pt\results\candidate.diff `
  --output C:\pt\analyses\new-profile-scope-check
```

The exact task image must already exist and Docker must already run. There is no
pull/build/start, remote fetch fallback, provider call, retry or resume. Existing
output directories are rejected. The immutable manifest binds source, patch,
program, runtime, public task and command/environment; `dev-run-v1` events link
each receipt. The task package's private files are never loaded by this diagnostic.

The project image is used only for the fixed operator-owned registered check. It
is never made available to arbitrary model-authored `run_probe` source. Agent probe
dependencies, public checks, task bytes, prompts, policies and finish gates remain
unchanged. This operator route does not establish that the model can choose or run
the contrast autonomously in its current stdlib-only probe environment.

## Executed observation

Evidence: `C:\pt\analyses\profile-scope-verification-20260918-v1`.
Two Docker checks, four comparisons each, no model generation, official=false.
The unchanged base preserves ordinary profiles but misses both provider-supplied
cases. The exact P9 patch passes both provider-supplied cases and fails both ordinary
preservation cases, inserting an unwanted empty field. No correction candidate or
private evaluation was run; P9's original acceptance result and closed cap stay exact.

This demonstrates a public overbroad condition, not the private evaluator's cause
or an agent-quality improvement. Next focus: a public dependency environment where
the coding agent can author and execute such contrasts against current project code.
That requires its own public-only source/dependency boundary; do not use this
operator diagnostic as authority to expose the evaluator image to `run_probe`.

## P10 input and expectation characterization: 2026-09-19 KST

An authorized offline follow-up runs this same program/operator unchanged on the
exact base and fixed P10, once each, using fresh independent prepared-source clones.
Public task, registered checks, prompts and model input are unchanged. No corrected
candidate, new task, provider/count call, credential read or private evaluation occurs.
The daemon and exact project image already exist; no start/pull/build is performed.

For both reasoning_content and scope_reasoning, the base preserves the ordinary profile
and misses the supplied-profile requirement. P10 meets the supplied-profile requirement
but inserts an unwanted empty field for the ordinary profile. The field mode/name,
OpenAI client/provider, model name and tool-only input are held fixed. Thus changing
to default auto mode or adding ThinkingPart would remove the distinguishing input.
Both checks return complete four-row output with expected exit1 and confirmed cleanup.
The result is a public scope violation, not an acceptance or hidden-failure verdict.
It does not change the prior task-first model-discovery score of0/1.

The same follow-up separately characterizes the closed model probe's replay assertion.
It verifies the recorded program hash and exact AST of the reviewed final projection,
then applies an equivalent locally authored predicate to a synthetic fixed message
fixture. No model-authored source or candidate program is executed for this check.
The fixture IDs/return strings are unit-test data, not captured Pydantic wire expectations.

Ten corruptions retain apparent success: missing one/all assistant tool messages,
reordered message pairs, invented synthetic thinking, overwritten real thinking,
wrong tool name/arguments/ID, and missing/changed returns. Expected count and names
are copied from actual output; only field types are asserted, including vacuous
success for all([]). Fixed fixture expectations independent of observations reject
all ten. The unchanged control passes; missing/non-string fields fail both predicates.
These13 checks establish a narrow assertion weakness, not ten real defects or semantic
coverage. The original complete raw histories were not captured, so their exact field
values/returns cannot be retrospectively certified from a boolean summary.

Operator tests29 PASS with durations; documentation3, Ruff and read-only evidence audit
PASS. All1,634 prior evidence entries, user AGENTS.md and historical trees are preserved.
Runtime and full-regression/mock evidence remain unchanged and are reused. Model cost$0;
task acceptance NOT_ASSESSED; all prior paid budgets remain closed. This work changes
no runtime guidance, agent schema, probe API, task or repair default. Future work must
keep supplied input/oracle assistance distinct from autonomous selection and discovery.

Evidence: `C:\pt\analyses\public-input-oracle-characterization-20260919-v1`.
Raw public pair: `C:\pt\pl-oracle-base-p10-0919a`.
