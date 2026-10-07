# SQLFluff public repair: rule ownership and preserved behavior

Date: 2026-10-08. PatchLoop source baseline: `7775d60b`. Official=false.
The user authorized investigating a repair that preserves both the public CTE
example and existing regressions after the
[intermediate test](2026-10-07-intermediate-test.md). This is an operator-authored
public source diagnostic, not an autonomous solve or a new agent policy.

## Problem and competing explanations

The intermediate candidate passed the CTE test while failing an existing L036
fixture. Its final L036 revert passed 506 required tests but lost the CTE behavior.
The useful question was whether these requirements conflicted or whether the
repair changed the wrong responsibility. Another revalidation policy could detect
failure without supplying a revision that preserves both behaviors.

L036's existing fixture deliberately inserts newlines without copying indentation
from later targets. The intermediate patch copied that indentation to the first
target, adding two spaces where its fixture expected none. L003 adjusts physical
indentation, including paths that do not call `_coerce_indent_to`. L039 normalizes
inline whitespace but explicitly exempts indentation and space before comments.

Public source identified a narrower L039 defect: after seeing the first leading
whitespace segment it set `prev_newline=False`. A second leading whitespace
segment could then be treated as inline and reduced to one space. Zero-width meta
segments also passed through a branch that cleared leading-line state. Skipping
meta alone, as in an earlier agent candidate, leaves the whitespace reset intact.

The alternative was that L003's desired-indent arithmetic or multi-segment repair
was still necessary. We tested L039 alone on the public base so those earlier
L003/L036 edits could not explain the outcome. We did not instrument another fix
loop or claim that all possible indentation failures share this cause.

## Frozen change and comparison

Prepared two separate local clones at public SQLFluff base
`a1579a16b1d8913d9d7c7d12add374a290bcc78c`. Both received identical additive tests in
the existing `test/rules/std_L016_L36_combo.py`; existing tests were preserved and
the public additive-test/scope validators passed. The candidate changed only
`src/sqlfluff/rules/L039.py` among production files:

- Skip zero-width meta segments without changing whitespace state.
- Preserve leading-line state through whitespace until an actual token arrives.

L003 and L036 remained byte-identical to base. The complete candidate diff was
`sha256:bcc454228dd519ed44b4f4da5d5d44c9e718ac9a3ff9cb2e439903708bc2f78b`.
The standalone production patch is `C:/pt/sowner01/source-only.patch`; the complete
patch including additive tests is `C:/pt/sowner01/candidate.patch`.

Before execution, froze one candidate and at most three public launches: baseline
selected file, candidate same selected file, then candidate registered regression
only after selected PASS. Stop on unexpected control failure, candidate failure,
input drift or execution uncertainty. No tuning, retries or replacement launches.

## Results

| Phase | Result | Complete action time |
| --- | --- | ---: |
| Base plus identical tests | **2 FAIL / 5 PASS** | 15.107 s |
| L039 candidate, same selection | **7 PASS** | 15.332 s |
| Same candidate, required regressions | **506 PASS** | 31.739 s |

The baseline failures were the original full-default CTE assertion (nine spaces,
expected eight) and the split-indentation assertion. The other five tests passed.
The split test stopped at its first failing variant; later variants were not
executed in that baseline function. The candidate passed all five variants:
multiple whitespace segments, leading indent metadata, interleaved indent/dedent
metadata, and split whitespace at a segment's beginning. It also preserved plain
SELECT formatting, inline-space normalization, comment spacing and existing
L016/L036 controls. The unchanged required suite includes the L036 fixture that
the intermediate candidate had failed.

All three launches used the same already-installed pinned image and registered
commands. Requested/effective timeout was 300 seconds within each fresh operator
330-second deadline. Network was disabled, source/root were read-only, pull was
disabled, cleanup was confirmed, and all timeout/truncation/deadline/cleanup flags
were false. No image acquisition, daemon start, paid call or private evaluation
occurred. Pytest times were 0.59, 0.52 and 17.06 seconds respectively. Line-level
execution feedback remained unknown; this is assertion evidence, not measured
line or branch coverage.

## What the agent missed

The original final edit's public hypothesis at sequence 372 assumed that the
L003 helper correction made L036's indentation-copy change unnecessary for the
CTE. Its first premise, that L036's copy caused a regression, was supported by the
failure output. Its second premise, that the remaining L003 change preserved the
full behavior, was unverified and contradicted by the submitted result.

Relevant source was delivered. The actual sequence-367 request retained the
current L003 helper and separate indentation-creation branches, L036, and the
added CTE assertion. This does not establish that the model used every relevant
line, but it weakens a missing-source explanation for that final decision.

There was also a concrete investigation miss: searches at sequences 307 and 320
used the generated pytest ID
`L036_test_multiple_select_targets_some_newlines_missing_2` literally and returned
zero spans twice; the second response was cached. The YAML key omits the `L036_`
prefix. The agent did not reach its explanatory fixture comment through those
searches, although failure input and expected output remained available. This is
an observed ineffective query, not a demonstrated search-tool defect.

## Decision and limits

The tested public requirements are compatible. This L039-only candidate satisfies
both without copying indentation in L036 or changing L003. The comparison supports
the joint state-handling correction on these public cases; it does not isolate
each edit's contribution, prove a unique root cause, or establish hidden acceptance.

Keep the agent baseline and defer automatic revalidation. The next agent-level
question is how it identifies the responsible rule and tests the complete repair
premise when relevant public evidence is already available. A concrete lesson is
to distinguish helper-local normalization from the complete rule interaction and
to revise an unsuccessful generated-ID search using the underlying fixture name.
No prompt, memory feature, budget increase or paid comparison is adopted here.
This exposed-task operator repair is not counted as a fresh agent success.

## Evidence and validation

- Frozen plan: `C:/pt/sowner01/plan.json`, hash
  `sha256:b26fd5f1824a6826225881bdb6465c9b1a97b7a537aaaf3dfb2433dcc4e36ead`.
- Summary: `C:/pt/sowner01/summary.json`, hash
  `sha256:dd8e77d9f7b2d784a6b71442597210b0420fa535df126b5cf8cf94c9e6e4988e`.
- Each phase's result: `C:/pt/sowner01/executions/{baseline,candidate,regression}/result.json`.
- Source-only patch hash:
  `sha256:945afb6e25b2e02ee632b3a7a8a68725b1fcb435eb38799a28c58918715f80ab`.
- Public trace audit artifact hash:
  `sha256:69b61c6690aeb0c88bcdf336de35124f107c9acef58fe18f0bdb238e3fd60b7d`.
- Append-only journal: `C:/pt/sowner01/runs/run_dev_l039ownership.jsonl`.
- Independent reviewers verified the three outcomes, 158 file bindings, original
  and candidate workspace hashes, and journal chains. Historical bytes remained
  unchanged. PatchLoop runtime content stayed
  `sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.

Generated patches, diagnostic tests and check state remain outside PatchLoop's
repository. Only this report, current status and the history index change here.
Documentation layout/link checks passed 5/5 after trimming the current-status
byte budget; Ruff and whitespace checks passed. The broad PatchLoop suite and mock
smoke were not repeated because runtime code did not change. Initial and final
documentation check receipts remain in the diagnostic root.
