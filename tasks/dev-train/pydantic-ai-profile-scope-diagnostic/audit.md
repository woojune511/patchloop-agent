# Public profile-scope contrast diagnostic, v1

This is a separate assisted diagnostic task, always `official=false`. Do not pool
its results with `pydantic-ai-synthetic-tool-reasoning` or treat success as evidence
that an agent independently discovered a missing verification case.

## Single public intervention

Keep the parent issue, exact repository/base, edit constraints, two existing
checks, and pinned environment. Add `profile-scope-contrast` as the third required
public check. Its program is the existing `diagnostics/profile_scope_program.py`,
derived from the public requirement that the provider-supplied profile carries
the empty-field requirement while ordinary profiles retain their behavior.

Hold the OpenAI client/provider, synthetic model name, field mode/name and
tool-only response constant; vary ordinary versus provider-supplied profiles.
Repeat with the default and copied custom field names. The check compares complete
messages, verifies current workspace imports, blocks networking, and prints all
four actual/expected results. It prescribes no implementation marker or patch.

The new public task identity and additional check are the only model-visible
changes. Evaluation support is an opaque byte copy of the parent package with
only the private task identity relabeled. No private artifact, reference patch
content or hidden result was used to construct the public contrast.

## Local validation and interpretation

The fixed public program runs on fresh prepared-source base and exact P10 patch
workspaces. Base: ordinary profiles 2/2 PASS, supplied profiles 0/2. P10: ordinary
profiles 0/2, supplied profiles 2/2. Both executions complete with confirmed cleanup.
This newly reproduces P10's public regression without reopening its closed run.

Registration and serialization tests bind the exact extra check, unchanged
parent fields, opaque evaluation support, and public/private input separation.
The original package, earlier evidence and runtime policies remain unchanged.
Evidence: `C:\pt\analyses\profile-contrast-diagnostic-20260918-v1`.

A fresh one-run observation uses the same P10 model/settings and prepared public
dependencies with a new $1.20 total cap. The added check is available from the
first input. A correct first patch demonstrates solving with supplied cases;
repair after a failed check is claimed only if that sequence is actually observed.
Stop after one settled result or uncertainty; no retry/resume/replacement.
