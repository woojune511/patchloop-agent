# Connect repair contracts to cases and actual observations

Date: 2026-10-30 KST. Local implementation; no provider execution in this change.
Baseline HEAD: `9363d5d9a10a2eaa77650c4da26525993596df51`.
Baseline runtime: `sha256:e8098f8b558a6bd8a5310e0cb07f70deacc3fe86c41fe3a7dab6bd00368d05d9`.

## Problem and decision

The [latest SQLFluff public replay](2026-10-30-latest-sqlfluff-public-counterexamples.md)
confirmed missed sibling failures and a minimum-condition regression despite 167
public PASS. The [preceding live run](2026-10-30-evidence-reuse-3916-results.md)
already delivered relevant source and retained probe observations. Repeating source
retrieval or adding storage does not address the demonstrated gap.

Public task16 run `run_dev_52faf580f57d463b` records a narrower decision path:

- Sequence123, plan revision2: after the edit, required-check PASS would make the
  candidate ready to submit; other failure paths/options were not named as checks.
- Sequence140, revision3: only normal `;` and adjacent `;;` remained as probe inputs.
- Sequence141, probe question: preserve previously matched content and leave the
  extra delimiter unmatched. Its program printed parse violations/unparsable counts
  and checked tree existence, but did not directly compare raw or matched/unmatched
  content. The question named a stronger property than the program observed.
- Sequence174, submission assessment: cited those inputs and treated exact CLI
  replay as its remaining gap. This does not reveal the model's internal reasoning.

The existing shared guidance already requested related paths/options, and planning
already warned against replacing verification with suite PASS. The selected change
makes their expected public work product more concrete: contract -> refuting setup
-> expected observation -> actual evidence or untested. It reuses the existing
edit-assumption idea in the active brief plan's review rather than adding another
policy, tool, gate or review call. This is a hypothesis about selection/judgment,
not an established repair-quality improvement.

If the model continues to choose only the original example, maps a question to the
wrong observation, or merely fills the wording without finding defects, that weakens
this intervention. Local delivery tests cannot settle that question. Cases must
come from public requirements/callers/tests rather than operator solutions or
private evaluator knowledge.

## Implementation

`patchloop/dev/working_plan.py` replaces the generic result-review portion of the
existing brief instructions. At the existing mutation review it asks for:

1. A changed return/condition in the **current diff**, grounded in observed source.
   This distinguishes applied code from a rejected proposal.
2. The applicable public contract, a refuting input/setup and a value to compare.
   Sibling failure paths and guards bypassed by early success are selection cues.
3. Expected observation linked to actual current evidence, or explicitly untested.
   Required state preservation and success eligibility remain separate obligations.
4. A next useful check that observes the property in its question, grouping related
   cases with a normal control and reusing adequate current-diff evidence.

This remains the existing bounded `plan_update` string. Null, invalid annotations,
review timing, journal/replay, budgets and finish authority are unchanged. Plans are
model-authored and unverified. No parser validates headings, counts assertions or
certifies semantic completeness. The prior opt-in formats remain available; no new
planning policy or runtime version is introduced.

`patchloop/dev/repair_guidance.py` replaces the shared guidance with the same
contract/case/observation connection for general current/thin, compact repair and
completion. It explicitly separates setup checks from the behavior asked about.
The `run_probe` schema/description already supports printing or asserting expected
observations, so those interfaces were not changed. No particular assertion syntax,
probe count, extra model turn or new finish prerequisite is required.

The ordinary current system prompt grows from 7,950 to 7,987 characters; base plan
instructions shrink from 2,807 to 2,804 by compressing repeated guidance. Their
combined prompt is 10,793, within the existing 10,809-character bound. Character
counts are not API token/cost measurements. No task-specific counterexamples,
SQLFluff code, hidden expectations or source patches were added to agent guidance.

## Verification boundaries and compatibility

The added integration test uses authored generic contract statements. Through the
actual runner's append and segmented paths it checks post-mutation brief guidance,
then retains an untested contract after suite PASS and a setup-only successful probe.
A fresh completion handoff retains both the plan and the actual observation without
upgrading either to verified behavior. Offered tools/budgets remain unchanged; a
null-plan finish passes annotation/batch validation, without proving the whole
gateway submission path. Existing policy/stage tests cover shared guidance once.

These tests establish delivery and authority preservation, not that a real model
selects useful contracts, writes correct probes or fixes the resulting failures.
Planning instruction hashes bind the updated identity; changed runtime/identity
does not authorize replay of an old paid run under new code. Existing ordered tool
schemas remain exact; historical `FROZEN_ARM` expectation branches are preserved.

Before production edits, two focused current-contract tests already failed on stale
hash expectations. An initial attempt also hit the host's default pytest temp-directory
permission issue; a fresh short external basetemp removed that environment error and
left the two hash failures. Related current planning/probe fixtures were normalized,
including the old assumption that annotation-free mutation tools carry `turn_decision`.
Historical expected values were retained. Two existing identity tests are now in
the quick manifest so those current fixtures cannot silently fall out of quick coverage.

The first expanded focused run had 98 PASS / 4 FAIL. Those four fixtures also assumed
every stage carried a plan and every mutation carried annotations. Current compact
repair deliberately omits the plan and small mutations omit annotations. Tests now
assert those omissions, then verify exact post-edit/completion review reasons and
stage prompts. Three simulated crash boundaries still require POST_EDIT revision2,
four dispatches/counts, one mutation admission, unique durable receipts and a no-op
terminal resume. No production recovery or context behavior was changed to satisfy them.

The first quick run had 1,251 PASS / 5 FAIL / 1 SKIP. Two closed-comparison tests
restored the historical system prompt but inherited current plan instructions;
their shared fixture now restores both from the same historical commit. Another
test retained an old current-guidance digest. The other failures exposed the
existing document and combined-prompt size bounds: guidance was condensed to fit
those unchanged limits. Historical diagnostics and size limits were not relaxed.

The shared-fixture audit additionally ran 33 legacy comparison tests: 27 PASS /
6 FAIL. The six failures concern old `Intent.requirement_quote` requests and
four-edit comparison limits. All six recur with the HEAD version of the helper
loaded only in the test process; five messages are byte-identical, and the sixth
differs only by run ID. These are not regressions from fixing prompt isolation and
were not repaired here. This is not a clean full-suite result. Evidence:
`C:/pt/contract-guidance-compat-sharedfreeze-head-20261030-v1/failure-equivalence.json`.

## Decision and remaining question

Keep the small guidance change if delivery and ordinary regression remain sound;
its live behavior still needs observation. Use the normal integrated development
loop and judge independently accepted repairs, newly discovered public defects,
regressions, cost and time. More plan text, case counts or completed probes are not
success criteria. Do not feed the operator's SQLFluff cases to a fresh solver as
hidden hints. No paid invocation or additional evaluation was started here.

External evidence: `C:/pt/contract-probe-guidance-20261030-v1`.
Append-only journal: `runs/run_dev_contractprobeguidance.jsonl`.
`baseline.json` binds original instructions/identities/schema hashes. Validation
reports and immutable logs are under `validation/`, with content-addressed copies.

## Local validation

- Final focused set: **104 PASS**, pytest28.72 s / total30.249 s, under two minutes.
  It includes current brief native delivery, shared stage delivery, exact recovery,
  instruction identity, unchanged schemas and completion context.
- Final quick suite: **1,256 PASS / 1 SKIP**, pytest249.23 s / total250.814 s,
  four file-grouped workers. The selected isolated mock evaluation tests passed.
- Changed-file Ruff and `git diff --check`: PASS.
- Contract audit: outside the two `INSTRUCTIONS` assignments the production AST is
  unchanged. Ordered schemas for all five planning settings exactly match baseline;
  task-specific diagnostic strings are absent from the revised instructions.
- Documentation: 51 unique HTML IDs and 70 links checked, inline scripts unchanged;
  changed Markdown links resolve. Current guidance remains within existing byte
  bounds. Visual rendering was not rerun for this content-only edit.
- Runtime: `sha256:c3c0a0debf6285da1202a51ebd0bef576aa1ee792e237fde72d6914452f82f75`.
- Contract audit: `sha256:cdb9f1c16d13645224fba34c12abbcc7b08a1f189088b2ea4a508b98ef5c52f9`.
- Focused report: `sha256:7e73b159663a1a03fed04f0f1854ab858ee6bbe580eb7a925af1eb3ffddc36eb`.
- Quick report: `sha256:69b8b91a99aaf0691d02b8d3b1afc6cd434f403641e29c3c1eb8075ce6ec49d3`.

Full regression, Linux execution and live-model quality/cost/latency effects are
not established by this local change.
