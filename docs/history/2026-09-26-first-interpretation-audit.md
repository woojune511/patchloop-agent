# First interpretation, source questions and applicability

Date: 2026-09-26. Read-only retrospective audit, `official=false`.
Current decisions remain in [current status](../current-status.md).

## Question and method

Compare the successful fresh Pydantic PF run from the 2026-09-25 v2 model comparison
with PG, the failed fresh generation in the independent-candidate experiment. Locate
the public requirement, question, source observation and first mutation that distinguish
them. Revisit earlier case-design and information-supplement attempts before proposing
another generic instruction. No provider calls, candidate executions or hidden evaluator
details were needed; coarse recorded acceptance remains PASS and FAIL respectively.

Both use `gpt-5.4-2026-03-05` xhigh, original Pydantic v1, the same exact base/prepared
source, dependency identity, runtime `4d2fc8ba`/v45, tool/prompt settings and $1.20 cap.
The actual initial requests match after removing only measured remaining wall time and
the derived segment ID. Model equality is checked separately from the existing normalizer.
All 20 dispatched inputs, count/dispatch identities, source closure hashes and public
journal chains were reverified. The first mutations both occur at call 6 before a segment
transition. This selected pair is not a randomized experiment or a new quality sample.

## Findings

| Stage | Successful PF | Failed PG |
| --- | --- | --- |
| Initial plan | Mentions DeepSeek-style profiles and a shared serializer; no complete explicit discriminator yet. | Treats field mode as sufficient, while still mentioning ordinary-provider preservation. |
| Question | Call 2 explicitly asks whether existing configuration suffices or an optional profile setting is needed. | Initial profile search asks how field/tags/auto/disabled and field name are configured. |
| Received profile source before editing | OpenAI profile 1–260, DeepSeek provider 1–101, including format semantics and construction. | OpenAI profile 13 unique search lines and provider 7; no full format documentation or construction function. |
| Mutation | Call 6 adds default-false opt-in, 7 enables it on provider profile, 8 checks it in shared serializer. | Call 6 changes serializer using field mode/name, tool calls and absent thinking only. |
| Verification | Two registered checks PASS, no distinguishing probe, acceptance PASS. | Same two checks PASS, no distinguishing probe, acceptance FAIL. |

The successful source question predates the fuller source response. The read cannot be
credited with originating that question. Its role in the later design remains plausible,
not isolated. Both runs located the shared serialization/replay owner, so location alone
did not determine applicability. The failed run retained relevant preservation prose;
this was not complete disappearance of the requirement from public working state.

This refines the earlier first-plan diagnosis: an underspecified first plan can still be
followed by the correct design. Inspect how a source question tests the adequacy of an
existing setting, rather than treating initial-plan wording as a sufficient predictor.
The successful run also supplies no evidence of superior discriminating-test selection.

## Earlier attempts and decision

The closed factorized case-design run still changed field mode in its preservation
case. Frozen expectations matched the wrong profile interpretation. Source-relation
supplementation produced supported detection A 0/2 and B 0/2 in a selected mini review.
The earlier missing-observation audit recorded that five of six failed Pydantic runs
already received field-format documentation. These old audits were consulted as records,
not re-executed or pooled with this pair. More source or more declarations is not an
established remedy; adding another common planning instruction is not justified here.

The next candidate for consideration is a source-only contrast at PG's first post-search
decision, using a generic rule to expose a matched Python declaration and adjacent
documentation. Preserve its original prompt and first plan; provide no successful patch,
known contrast input, answer condition or task-specific selector. Measure the selected
question, resulting source use and actual first edit, not whether a flag is mentioned.
This tests whether that interpretation is recoverable with different declaration context;
it does not test why the first plan formed. It is an unimplemented, unrun diagnostic
candidate in the same information-supplement family as an earlier negative comparison.
No new paid allocation, common tool expansion or default adoption follows from this audit.

## Evidence and validation

`C:\pt\analyses\pydantic-first-interpretation-audit-20260926-v1\result.md` contains the
detailed account. `comparison.json`, per-run public decisions, delivered state and
observed-source maps preserve the exact audit links. Eighty consumed source files were
checked against their prior closure where applicable and verified unchanged afterward.
The first local audit attempt encountered differing Windows path separators in old
closure manifests; normalization fixed the reader without changing historical bytes.

Source provenance: PF `run_dev_7a72ecd7402d4e83` under `C:\pt\xsolve-live-0925b\PF`;
PG `run_dev_0ca1f93057454146` under `C:\pt\indcandidate0926a\PG`.
Ruff, focused documentation checks and final preservation hashes are recorded in the new
packet's validation and closure files. Runtime, prompts, tools, task and defaults did not
change; full runtime regression and mock smoke were not rerun for this documentation audit.
