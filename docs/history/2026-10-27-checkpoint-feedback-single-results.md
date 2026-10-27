# Single-A result: original feedback delivered, later regression blocks acceptance

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved execution and public-artifact audit
- Origin Date: 2026-10-27
- Verification Status: LIVE_EXECUTED / CLOSED; delivery PASS, full repair incomplete
- Runtime/delivery source: `054dfc7b`; selected invocation: `dc6b9ebc`; plan: `51eb70e6`

The [sealed trial](2026-10-27-checkpoint-feedback-single-plan.md) executed A exactly
once with the user's exact manifest approval and $1.20 cap. It asked whether the
post-edit source projection lets a real model receive its current original-call
verification and stop accurately. The prior A repaired the task but failed this
delivery step at 65,982 input tokens. First-request content and row limits stayed
fixed; the new model selected a different edit, so this is a live integration
trial against a historical baseline, not a controlled repair-quality comparison.

## Observed outcomes

| Outcome | Result |
|---|---|
| Initial request | Same hash as prior A; 56,199 input tokens |
| Accepted source edit | One; `_get_relative_base_path` normalizes the search root |
| Original verification | supported; first call retains identity and F0010 resolves |
| Next actual request | 59,142 input tokens; exact current-diff verification delivered |
| Model response | Successful `stop_task`; accurately recognizes original-call success |
| Final public cases | 5/5 PASS, child selected and parsed; no F0010 |
| Public regression | 1 failed, 1,230 passed, 69 skipped, 15 xfailed |
| Isolated evaluation | NOT_RUN_PUBLIC_CHECKS; zero evaluator dispatches |
| Cost and closure | $0.19439055, all usage known; allocation closed |

Two input counts and two generation calls completed. Ordinary/correction/tool/edit
counts were 2/0/2/1. Both source references expanded exactly to the durable edit
result, with changed mutation evidence preserved. The counted and dispatched
second request had identical content/hash and its `current_trial_original_recheck`
exactly equaled the fresh journal feedback for the candidate diff. No handoff was
needed, so the rebuilt-handoff path remains locally tested, not live exercised here.
The input margin was only 858 tokens; this does not prove every future edit fits.

The first response used 26,027 output tokens in 117.88s and cost $0.12142755;
56,064 of its 56,199 input tokens were cached. The second used 6,357 output tokens
in 27.24s and cost $0.07296300, with no cached input. Cost differences from prior A
therefore cannot be attributed only to delivery changes. Model plus intermediate
verification took 175.42s; through final checks and closure, 307.75s. No correction,
automatic retry, additional trial, billing uncertainty or execution abort occurred.

The original first call had the same inputs and its control output was unchanged.
The second original call's input identity differed because cache output inside
the input root can affect later call inputs; that limitation remains recorded.
Do not claim both calls retained identical input conditions.

## What the later failure means

The model replaced `os.path.normcase(path_to_check)` with `_normalize_path(path_to_check)`
in `_get_relative_base_path`. This fixed relative-root matching for the observed
namespace case, but the public regression test
`test_load_from_module_symlink_on_symlinked_paths_in_syspath` raised `ImportError`.
The log is complete, not truncated or timed out: 1 failure in 12.25s.

The source and public failure explain a likely mechanism: `_normalize_path` resolves
symlinks. The search root `/tmp/path_to_include` becomes `/tmp/deployment`, whereas
the linked file is considered as `/tmp/path_to_include/secret.py` or its final real
target `/tmp/secret.py`. Neither starts with `/tmp/deployment`, losing the previous
raw-path match. This is a source/log diagnosis; no extra counterfactual execution
or operator patch was added to this one-run allocation.

The last model response preceded public regression. Its statement that the original
F0010 resolved was supported by the evidence it received; it did not claim final
regression or isolated acceptance. The later regression failure was never sent
back to the model. Thus original-feedback delivery and accurate diagnostic stop
passed, while full repair and acceptance did not. This trial also does not exercise
the product's complete `finish_task` submission flow.

Decision: retain the exact source-reference delivery fix on its local and now live
flow evidence. No context-limit increase is justified by this run. The next question
is how to include final public regression in model-visible completion feedback and
fund a bounded response or repair after that result. Preserve raw/symlink matching
when evaluating the new repair hypothesis. Do not automatically execute another
trial or promote this saved-evidence result to general repair-quality evidence.

## Evidence

- Manifest: `C:/pt/checkpoint-feedback-single-plan-v1/manifest.json`,
  SHA-256 `e3bc2fd08b1808c7e5b8e024bf71aa2a266c7607e2f8dbbc49195c5b465f660e`.
- Direct approval: `C:/pt/checkpoint-feedback-single-plan-v1/approval.json`.
- Executed command: `& 'C:/pt/checkpoint-feedback-single-plan-v1/run.ps1'`; exit 0.
- Result: `C:/pt/checkpoint-feedback-single-run-v1/result.json`,
  SHA-256 `65dd13cee44620d449f873418b8217038790f327671689c4afdde008a48bfed6`.
- Public analysis: `C:/pt/checkpoint-feedback-single-analysis-v1/public-analysis.json`,
  SHA-256 `96637bdb9d4361311c61e3df968b708a300cb3f8a7ba361439308c822079c9cd`.
- Independent public delivery audit: same folder, `delivery-audit.json`,
  SHA-256 `8681865c6f223826984d6c6f77f8fda13eb824ec7d3271722e054bc28b74c5f1`.
- Candidate patch: same folder, `candidate.patch`,
  SHA-256 `f9998e3e5ea9bd927ae3aa5658138ed04b73254307b110e83380ae5f1968a5cc`.
- Public regression receipt SHA-256:
  `bf5c885a06a0b84a0d930b9a32d5d571c61a8597959452a3b215d281abfce8fb`.

Audit used public actions/requests/checks and scalar isolated-evaluation status.
Opaque model reasoning, hidden tests and reference fixes were not inspected or
projected into model context. Public journals and the analysis journal validate
their hash chains. Source code did not change during this approved execution.
