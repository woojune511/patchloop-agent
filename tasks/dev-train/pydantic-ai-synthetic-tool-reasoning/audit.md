# Pydantic AI synthetic tool-turn reasoning, v1

Development-only registration; every run is `official=false`.

## Origin and contract

Original public issue: https://github.com/pydantic/pydantic-ai/issues/5829

The exact base is `5965db82c4e10012a8598c14716ea8a88fb411a9`, associated with
`pydantic__pydantic-ai-5842`. The existing image is pinned in `environment.yaml`.
Public source inspection and offline request capture establish missing reasoning
metadata on synthesized tool-search history after deferred capability loading.
Fixture reasoning from actual mocked replies remains present.

This task asks for a local wire-format repair: retain existing message content
and identities, add empty configured metadata only under the provider profile's
field-mode requirement, and preserve other profiles and explicit send modes.
An optional backwards-compatible profile setting is allowed. No exact setting
name, helper, minimum file count or patch shape is required.

All 39 previous current packages were excluded by base identity. Historical
metadata/admission records mention this problem, so it is not globally unseen.
Those archives, patches and evaluators remain immutable and are not imported.
This package's reference and oracle were independently authored from the public
requirements and exact source; no upstream gold/test patch was used.

## Visible and independent checks

The public contract has eight observations, including a real Agent loop with
fixed local HTTP replies. The unchanged base passes five and fails three.
All 18 selected existing provider/thinking tests pass on the unchanged base.
Both checks bind imports to the mounted source and use the image's existing
`/pydantic-ai/.venv/bin/python`. No dependency installation is required.

The independent oracle captures actual serialized requests across provider
profiles, copies/overrides, tool/text/thinking combinations and multiple
deferred capability loads. It compares message content, per-message reasoning
and tool identities/order against independently constructed expected data.
All response strings are fixtures; socket connections and Docker network are
disabled. It does not validate live DeepSeek acceptance or reproduce a real 400.

## Admission evidence

The reference passes three fresh isolated evaluations and the alternative passes
one. All nine semantic negative controls are rejected. A correct implementation
with a forbidden test edit passes behavior checks and fails scope. All 14 safety
verdicts pass. The oracle covers 84 wire combinations and eight requests across
the two complete flows. Global injection, ignored copied-profile send modes and
the wrong configured field pass public checks but fail the independent oracle.

The production isolated evaluator matrix and final validation are recorded at
`C:\pt\analyses\pydantic-ai-registration-20260917-v1`. The matrix binds task,
runtime, source, patches and operator bytes before evaluation. Its results are
task-admission evidence, not agent attempts or an official benchmark score.
Final outcomes are summarized in `result.md` and `completion.json` there.

The independently authored reference configures the provider/profile and maps
missing metadata during response assembly. The alternative performs that step
after assembly. Negative controls cover absent implementation, a configuration-only
change, global field injection, overwritten reasoning, ignored send modes, wrong
field names, dropped tool history, changed tool IDs and fabricated empty responses.
A forbidden-test edit checks scope separately from semantic acceptance.

## Workspace support found during registration

With Windows long-path policy disabled, a 266-character staging destination
failed Python copying although Git had created it. Cleanup then encountered a
read-only Git pack. The runtime now uses extended paths for workspace copying
and complete tree hashing, removes owned read-only Git files, and preserves the
original failure if cleanup fails. Ordinary envelope and Docker paths stay unchanged.
The published source was reused offline after that fix; the failed preparation
record and staging workspace remain preserved.

## Later observation

Registering this package does not start a paid run, reuse previous budget or
resume a closed group. A separate exact task/model/credential/repeat/cap must
be defined for a later observation. Private controls and reference patches never
enter coding-agent context. Default model, context, planning and tools stay fixed.
