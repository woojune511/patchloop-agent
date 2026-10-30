# Normal repair: mutation intent, verification choice and delivered evidence

Date: 2026-10-30 KST. Status CLOSED: offline audit and two bounded fixes validated.
No provider call, public probe or private task evaluation was run. Isolated mock
evaluation was exercised by local regression tests.

## Why revisit this point

The user requested tracing the normal repair loop before another experiment or
generic instruction. The short [deadline review](2026-10-30-sqlfluff-deadline-review.md)
used four calls, so its budget cannot explain the normal run with a 40-call cap. Reuse the
[earlier selection diagnosis](2026-10-30-verification-selection-diagnosis.md), but
verify the latest normal run rather than importing the earlier run's source inventory.

Target: `C:/pt/scope16-run-20261030-v1/16`, run `run_dev_55d4f4526e154a53`.
Execution commit `5f0eb78436b57b7af05e130019a9d1643ec45366`; inspected baseline
`f0bb672f`, runtime `sha256:ed9b23780500ed4d4f72fa7751156de34314d18be3a2a05a8fcd3830dca6f4b9`.
Only public source, actions, plans, assessments and selected public request fields
were reviewed. Provider reasoning, evaluator contents, hidden tests and reference
patches were not opened. Historical artifacts remain unchanged.

## First semantic gap: the changed success contract never entered the plan

The gap is not evidence of an authored contract disappearing. Sequence 89 explicitly
requests MatchResult semantics before changing failure returns to partial matches;
91 delivers truthiness and from_unmatched construction. At 120 the mutation contract
targets prefix preservation and no-crash/SQLParseError behavior for two inputs.
It does not formulate a check of the new truthy result against minimum/trailing
success conditions. The edit changes that meaning nevertheless.

Revision 2 at 134 says to narrow/revise on suite failure and submit on PASS. The suite
passes at 136. The agent voluntarily repeats its original helper at 151/154, then
assessment 168 uses the new observation accurately and names only exact CLI
reproduction as unfinished. The old plan's "not rerun" sentence is stale, but the
assessment demonstrates that the later observation was received and used.

Rejected revisions 34/51/70/87 also contain no minimum/trailing verification purpose.
They are not evidence that the host erased such a purpose. This chain locates a
gap between the semantic scope of the edit and its chosen verification target; it
does not establish whether the cause is ability, prioritization or another model choice.

## Delivery audit: plans arrived; source retention differed by mutation tool

| Actual request | Plan/review | Delimited source available |
| --- | --- | --- |
| 114, before edit | Compact repair omits plan by design; shared guidance present | Native read 1-251, 12,261 characters; option guards present |
| 129, after edit | Revision 1; mutation_result and handoff review | Edit arguments and first post-image preview; no old full-file read |
| 144, after public PASS | Revision 2; check_result/first-ready review | Current 141-147 only, 305 characters |
| 162, after helper | Revision 2; probe_result review, exact latest output | Same 141-147; no Delimited minimum/trailing guard bodies |

The final request still offers read/search/edit/probe. At request construction it has
31 calls, 80 actions, 11 edits, 1,058 solver seconds and USD 3.283226 left. Completion
guidance says eligibility is not correctness and gives no forced next action.
Plan/review loss, missing tools and hard budget exhaustion are not supported.

The source reduction is real. `file_edits.result` generated only a preview around
the first changed line of each file. `_accept_successful_mutation` then invalidated
all previously observed spans in those files. Unlike `replace_text`, `edit_files`
did not rebind already observed unchanged lines. Fresh context segments omitted
the old full-file read. This loss already existed in the gateway's source inventory;
the model projection did not drop a larger current body.

Before editing the agent had the relevant source, so later source loss does not
explain the initial omission. It can reduce the evidence available to reconsider
the choice. No causal repair-quality claim follows from restoring that evidence.

## Two bounded fixes

1. Reuse exact admitted file images and existing positional source rebinding for
   file transactions. Retain already observed unchanged lines and a bounded
   post-image across the changed interval, subject to existing source limits.
   Recovery and undo derive from the same saved images; no new state store,
   prompt, verification quota or submission gate is introduced.
2. Correct `finish_task`'s description for public-checks-v1. Actual request 162
   promised automatic original-case replay even though its completion guidance and
   execution policy explicitly did not replay. Only the policy-specific description
   changes; the default reproduction-gated wording and execution behavior remain.

The false replay promise is a contract defect, not proof of why the model stopped.
Assessment 168 acknowledges that the exact CLI case was not replayed. The fix does
not make optional checks compulsory or certify the candidate's correctness.

## Evidence

Audit root: `C:/pt/scope16-plan-action-audit-20261030-v1`.
- Public chain: `public-chain/public-chain.json`, CAS
  `sha256:7358b69ab422bf027d96afaef52c73817b7a25fc6b76c7c7c97788d1ea723c02`.
- Delivery: `delivery/findings.json`, file
  `sha256:ac322b552f66109958edde5b26c6d96dd83cf5b01d7189b048a1c5079c595cdb`.
- Final prepared request:
  `sha256:58d3f1c2a749a0f33b0af0ffd3ff0521832e338315c173da179876681925436e`.
- Final public context:
  `sha256:8f698c372f1a021859f8a5bd05aaae66eaf972947713dec0ede9ba4a401e943a`.

## Local validation and exact public edit replay

Before the source fix, two distant-edit cases (LF and CRLF) fail: a 19-line observed
file retains only lines 2-8 after changes at 5 and 15. Baseline log:
`sha256:8ea6e9fcbfad344ceed119d3e1daa4e1fe943376a53dab6380db9fbebf2e5742`.
After the fix, 5 new and 11 existing source-rebinding tests pass in 67.496 seconds.
They cover distant changes, raw newline identity, current edit authority, bounded
large post-images, unread tails, global eight-fragment bounds, multiple files, undo,
and crash/replay with identical evidence. Artifact:
`sha256:7070cfbcc72f6a6c22eb6998cb458da8a2bbe5a2677f6ff4f3927316ca392f03`.
Durable observed source may still be omitted by the 24k model-context selection;
retention does not promise all known source in every request.

Policy-focused 7 tests pass in 33.73 seconds, including actual mock finish through
isolated evaluation, optional public replay and strict replay/failure blocking.
The two broader policy owner files pass 31 tests but take over two minutes; these
are separate from the focused selection. Ruff passes. Execution rules did not change.

The actual saved 16 public inspections and 1 edit were then replayed against a fresh
public source snapshot, with no model, probe, public check or private evaluator.
The resulting patch remains
`sha256:57aadee74f816fb44c764ef444ba797078194cbac2230174c1c3036c9a7821cf`.
Current projected Delimited source is now 1-255 / 12,401 characters, compared with the
historical final 141-147 / 305. All option-guard lines are present and match the current
file; total retained source is 24,000 characters. This proves the delivery change on
the exact saved edit, not that a model will use it or produce a correct repair.

Replay root: `C:/pt/scope16-plan-action-audit-20261030-v1/replay`, result artifact
`sha256:2a198b266897c9c382f287ed80d9f38a7e27c105e260ce01003313c1f9ff0951`.
Final summary writing initially used the wrong ArtifactStore root; safe rejection
was recorded and the existing result was finalized without repeating any action.
Validated runtime:
`sha256:c70488eef7bf533d471d47396d213edec62783d754016c4fadc1115de2a7b728`.

Quick regression: 1,265 PASS, 1 SKIP in 301.938 seconds, with four workers and
unchanged runtime. It includes the isolated mock evaluation path. No extra mock
smoke or paid call was needed. Log artifact:
`sha256:b2ad4f10ecbc9d66351d1e367d9fb5b8b4ace12d7c3b0b480351f8f1100ab6d3`.
Validation root: `C:/pt/scope16-plan-action-audit-20261030-v1/quick-validation`.
Repository-wide Ruff, diff whitespace, local HTML links, unique HTML IDs and the
12k current-status bound pass; HTML scripts are unchanged.
Final checks artifact:
`sha256:996c5c95a8a66f8972df2fa2fc256ae193414eef9b1648740a81e3de720af52f`.

Decision: retain the existing scope-choice guidance and repair these demonstrated
source/contract defects, without adding a semantic gate or another planning layer.
The unresolved question is whether a normal live run uses the restored evidence
to identify and test changed success conditions. No live repair benefit or causal
explanation of the independent failure is established. Existing paid allocations
stay closed, including the separate unresolved earlier provider call.
