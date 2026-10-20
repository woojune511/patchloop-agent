# Completion resource correction and context capacity review

Date: 2026-10-06. Provider-free implementation and public-source investigation.
Base: `53a48f9e113c95361c7b019d983c11ea822ac1de`.
Every run remains `official=false`; no claim-producing experiment was launched.

## Problem and decision

The [preceding diagnosis](2026-10-06-verification-context-budget-diagnosis.md)
identified an actionable accounting mismatch: automatic registered-check rechecks
consume a tool action but no model call, while the completion forecast charged both.
It also located previously observed source disappearing at a segment boundary before
SQLFluff-1733's unsuccessful edit. The user requested the accounting correction and
a comparison with other agents' context conventions.

The correction is adopted as a resource-contract fix. The context investigation
confirms that the 24,000-character retained-source pool is restrictive for this
observed multi-file task. It does not establish that increasing the pool improves
repairs. Keep the context defaults unchanged in this change; 48,000 characters is
an evidence-based availability candidate, not a measured quality improvement.

## Resource accounting change

`completion_budget.py` now forecasts model calls and tool actions separately.
Existing `minimum`/`protected` and public `*_calls` fields count model calls;
explicit tool-action fields carry the other resource. The runner uses each floor
for its corresponding resource in inspection, probes, tests, optional edits,
diagnostic checks, successor states, terminal diagnostics and completion-cost
forecasts. Automatic-recheck-off behavior and metadata shapes remain unchanged.
Saved-input reconstruction and diagnostic continuations also carry the same
automatic-recheck setting into policy forecasts. The first full test run exposed
a missed declaration-rebuild call site; enabled compaction/counterexample paths
and inherited correction/recovery paths were checked and aligned as well. Disabled
diagnostic branches retain their default-false behavior.

The shared `latest_repair_check` selection preserves the execution predicate:
latest result per registered check, exact current diff, succeeded execution,
behavioral failure, and no deadline or cleanup failure. It does not grant current
recheck credit for a historical result, a passing result, an unregistered check or
a failed execution. An accepted repair still invalidates earlier checks and may
automatically recheck only one eligible check. Other required checks retain their
slots; optional probes never gain required-check credit.

| Bounded path/state | Model calls | Tool actions |
| --- | ---: | ---: |
| Initial one-check protected path, automatic recheck off | 8 | 8 |
| Same path, automatic recheck on | 7 | 8 |
| Eligible current failure: accepted repair, automatic check, finish | 2 | 3 |
| All required checks passed: finish | 1 | 1 |

The protected path includes one rejected mutation attempt plus anchor read and
one future check failure with inspection/repair/recheck. This is a forecast for
those bounded outcomes, not a guarantee against arbitrary repeated failures.
Deadline, cleanup, mutation evidence, recovery identity, count/billing uncertainty
and invocation limits are unchanged. No additional provider or check retry is added.

Six saved public policy inputs were replayed against the new code. Disabling
automatic recheck exactly reproduces the old admission outputs. For row08/462,
eight remaining model calls and 58 tool actions now permit one further optional
model turn, including up to four parallel reads. Spending that turn closes the
same protected boundary. Eight remaining tool actions still forbid an optional
read because all eight are reserved. Row08/491 still has five optional turns after
PASS. The change does not prove the model would read the right code or test its
wrong hypothesis.

## What the context limits actually mean

The frozen runs used `gpt-5.4-mini-2026-03-17`. Four quantities must be distinguished:

- Each source read/search output has a 24,000-character source budget; a read also
  has a 400-line limit.
- The retained pool across prior observed sources has another 24,000-character
  budget. Latest native source is excluded from that pool to avoid duplication.
- The request also contains in-segment history, task, instructions, schemas,
  state and opaque continuation. None is accurately described by that source cap.
- The local segmented contract admits at most 60,000 counted input tokens,
  1,048,576 request bytes and a 262,144-byte largest encrypted item, with a separate
  25,000-token output ceiling. The provider's advertised window does not override
  those local limits.

Actual historical input counts were cross-checked against count, dispatch and
response usage records. No new token-count API was used.

| Public input | Actual input tokens | Unique visible source characters | Relevant arithmetic |
| --- | ---: | ---: | --- |
| Successful row06/336 edit decision | 56,160 | 60,024 | Present |
| Row08/393 before handoff | 50,260 | 42,859 | Present in older history |
| Row08/409 after handoff | 26,681 | 24,124 | Missing |
| Row08/462 edit decision | 33,805 | 37,758 | Missing |
| Row08/491 submission decision | 24,315 | 24,000 | Present again after edit |

The loss at handoff408 was `major_result_reviewed`, not token exhaustion. The
handoff discarded the old output even though the preceding request was below
60,000 tokens. This implicates retention/recency and result-driven segmentation,
not an exhausted provider window. Other handoffs really were token-triggered:
maximum candidate counts were 67,131/63,335 for rows06/08, while maximum dispatched
counts were 56,160/57,989. Larger retained source could reach the local limit sooner
elsewhere; the increased-cap requests were not token-counted or dispatched.

Six exact baseline selector replays and 150 grid projections, including 18 primary
projections, kept observations, source identities, priorities and latest
native spans fixed. They added no unread source.

| Retained source cap | Arithmetic at08/409 | Arithmetic at08/462 |
| --- | --- | --- |
| 24,000 characters | Missing | Missing |
| 32,000 characters | Missing | Missing |
| 48,000 characters | Present | Present |

At462, 48,000 retains lines431-733 beside the unchanged latest read330-430; it
still does not retain the whole function through785. The first successful tested
1,000-character increments were 39,000 at409 and 47,000 at462, not proven exact
minima. Larger caps can change tiny fragments selected by greedy complete-line
packing. At409/462, the48k projection displaced no24k retained range.

The previous same-cap priority intervention also preserved the arithmetic by
displacing other source; its file-recency shortcut failed. Thus capacity and
selection are alternative intervention points. Neither proves model attention,
verification choice or patch correctness. Arithmetic already reappeared before
the failed submission, when optional verification was available.

## Other agents: primary-source comparison

Sources were retrieved on 2026-10-06; implementation claims below use fixed commits.
Token, character, event, per-output and whole-window budgets are intentionally
kept separate. These are conventions, not comparative repair-quality evidence.

| Agent | Verified budget/convention | Implication for this project |
| --- | --- | --- |
| Codex | Official prompting guide recommends 10,000 tokens per tool response, with head/tail truncation. Configuration makes automatic compaction model-dependent. | A per-output limit is not a cap on all retained working source. [Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide), [configuration](https://learn.chatgpt.com/docs/config-file/config-reference). |
| Claude Code | Model-dependent compaction; afterward it rereads up to five previously read/edited files by modification recency, using path-only references for files above 5,000 tokens. | Active files receive separate restoration, although source can still be lost. [Official context documentation](https://code.claude.com/docs/en/context-window#what-survives-compaction). |
| Gemini CLI | Default compression trigger is 50% of the model token limit; older tool outputs use a 50,000 estimated-token truncation target. The recent 30% split uses serialized characters and safe message boundaries. | Overall context, old outputs and recent history have distinct budgets. [Fixed implementation](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/context/chatCompressionService.ts). |
| Aider | Conversation history threshold is model input/16, clamped 1,024-8,192 tokens. Editable/read-only file bodies enter the request separately. | A small summarized history budget can coexist with preserved active source. [History limit](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/models.py#L355-L358), [request assembly](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1278-L1283). |
| OpenHands SDK | Constructor/settings 240 events/keep first 2; default-agent factory 80/keep first 4; token-pressure limits also apply. | Entry point matters, and event counts are not token counts. [Condenser](https://github.com/OpenHands/software-agent-sdk/blob/6f8c38d00e0468ac138447be905f07a8a0cd7af8/openhands-sdk/openhands/sdk/context/condenser/llm_summarizing_condenser.py), [agent factory](https://github.com/OpenHands/software-agent-sdk/blob/6f8c38d00e0468ac138447be905f07a8a0cd7af8/openhands-tools/openhands/tools/preset/default.py). |

The [current GPT-5.4 mini documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
lists 400,000 context tokens. This does not make the local 60,000 input contract or
24,000-character retained pool necessary, optimal or directly comparable.
OpenAI's [compaction documentation](https://developers.openai.com/api/docs/guides/compaction)
also supports configurable thresholds; its 200,000-token example is not a universal
default. No provider compaction mechanism was introduced here.

## Validation and remaining question

The implementation's focused coverage includes 106 distinct tests: 105 passed in
58.91s, followed by the final 17-test resource file in 0.79s (16 overlap). An
independent executable-step oracle covers more than 3,000 multi-check states;
end-to-end tests cover enabled/disabled rechecks and durable recovery. Ruff and
five documentation tests passed. The explicit segmented/automatic-recheck mock
smoke reached isolated `EVALUATOR_PASS` in 14.814s; safety stayed `NOT_RUN`, with
zero billed cost. That smoke required no failed-check child; the focused end-to-end
tests exercise that path.

The full four-worker suite completed in 3,080.87s: 4,299 passed, five failed,
20 setup errors and 19 skipped. The five failures were old call-count expectations
in a deliberately greedy inspection fixture. They were updated to the independently
reproduced resource path, preserving isolation, private-data absence and durable
replay checks. All 29 tests in that file then passed in 88.70s. A five-case diagnostic
rerun under full-suite contention took 191.19s, exceeding the focused target; the
final file rerun was under two minutes.

The 20 setup errors shared one cause: declaration checkpoint reconstruction omitted
the automatic-recheck setting, so its action horizon disagreed with the saved
request. The flag propagation correction passed all 51 declaration tests in 37.64s.
The original full-suite result remains immutable; final closure combines it with
targeted reruns rather than describing the first run as green. Another 20 relevant
diagnostic execution/recovery cases passed in 61.22s. All 25 originally unsuccessful
nodes passed after the targeted corrections: combined coverage is 4,324 passed,
19 skipped, zero unresolved failures. Core runtime bytes stayed fixed throughout
the full run and reruns; diagnostic callers and test expectations were corrected
after the full run. Final Ruff and documentation checks passed. Linux CI, real
Docker safety and a paid repair-quality comparison were not run.

The next context question is whether a larger observed-source pool or preserving
the active function across handoff changes actual repair decisions within the
same call/cost limits. 48k has a concrete availability rationale; 32k does not address
this observed loss. A generic recency shortcut and automatic repetition of the
last probe have no new supporting evidence. No paid comparison, mandatory probe,
cross-run memory or context-default change was launched.

Evidence root: `C:/pt/analyses/resource-budget-context-20261006-v1`.
`context/evidence.json` binds six inputs and every range projection; file hash
`sha256:87cae0292266ce72f387b51609a39df8fa99c88fe82827c404bb20939ad16e1b`.
`research/evidence.json` binds 30 immutable upstream snapshots and scoped OpenAI
facts; file hash `sha256:d84185f840df0430aa7f53f532d34365d11006645a591519741aaf419ff334d9`.
Four fetched OpenAI Docs MCP responses and their hashes are separately preserved
in `openai-sources/`; that journal hash is
`sha256:64a2e60afb68deeb8d6ef5aa063cdf5ff1709ed8fbfdc8a4c2f1ac4095ab6f89`.
`replay-v2/result.json` binds six policy replays; file hash
`sha256:79d0b05647682d409319476adae8257d7ec8ce35b49716184e2b2d75a4d9120f`.
The first replay operator mistakenly selected a tool-batch event 475 instead of
prepared input 476 and failed its six-row count after five successful rows; it and
its failure receipt remain intact. The corrected operator was versioned separately.

Historical experiment bytes and the user's pre-existing `AGENTS.md` edit are
preserved. Local evidence does not establish live repair or generalization gains.
