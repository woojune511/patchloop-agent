# Public profile-scope diagnostic

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
