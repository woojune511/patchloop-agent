# Failed-eight public audit, test discovery and expectation grounding

Date: 2026-11-01. Local implementation and public-log analysis. No new provider
call, benchmark solve, saved-patch execution or independent evaluation.

## Why this work

The latest [full dev20](2026-11-01-pre-edit-dev20-results.md) still had eight
independent failures: **7, 8, 10, 12, 13, 16, 17, 19**. All submitted after required
public checks passed. The [fresh task18](2026-11-01-repair-continuity-task18-results.md)
passed independently but created `test/rules/std_L003_L036_combo.py`, which
matches neither pytest's default patterns nor its public `tox.ini` pattern
`*_test.py`. The prepared public tree also has `pytest.ini`, which takes precedence
and does not override `python_files`; the filename check therefore reports defaults,
not the lower-priority tox.ini setting. Explicit selection ran that regression;
ordinary directory discovery did not include it. This repeated an earlier new-test
omission and makes future regression checks incomplete.

The user selected a common-failure audit and discovery fix before another paid
panel. The question was whether the failures support a common intervention rather
than more blanket probes, higher limits or task-specific repair hints.

## Evidence and limits

Base checkout: `a142620559510bdaded89e6207d870e864e243c1`.
Full20 ran at `f994a2b6` with runtime implementation `e6374d6f`; the latest task18
used `21793a4b`. This follow-up does not rewrite any prior patch or evaluation.

External evidence: `C:/pt/failed8-public-20261101-v1/`:

- `audit.json` and `task<N>.json`: public tasks, actually dispatched public inputs,
  public actions/results and submitted patches. All eight original JSONL chains,
  final hashes and patch hashes validate. Current public specs equal those in
  the saved initial dispatched requests; no guessed current projection replaces
  old inputs. Reasoning payloads and private evaluator bodies were not read/exported.
- `findings.json`: observations, limits, public task hashes and exact event refs.
  Its CAS hash is `sha256:808bedd5deeee667c8b4ae8b365b9a1e19866667d4008a142989396ce83de215`.
- `task18-filename-check.json`: the same filename validation against the real public
  suite and prepared tracked configuration rejects the submitted name and accepts
  a `_test.py` name. This is read-only admission analysis, not target execution.
- `runs/run_dev_failed8publicaudit.jsonl`: append-only hash-chained audit and
  subsequent local-validation receipts. Local synthetic tests are not benchmark runs.

| Task | Public evidence | Remaining question / interpretation |
| --- | --- | --- |
| 7 · pydicom1139 | Added iteration/containment, tested `Dataset.PatientName`, substring/negative/iteration controls; required check passed. | The shown public example is supported. No missing length/indexing requirement is inferred from independent FAIL. Exact private failure remains unknown. |
| 8 · pydicom1413 | Ordinary I-array bytes did not reproduce the report. Later array/bytearray inputs failed and the patch repaired that helper path; selected tests passed. | Reported H-array-to-bytes input was replaced. The observed helper exception did not explain how the report's already-bytes value became MultiValue. This is a concrete target-selection gap, not exhausted edit budget. |
| 10 · pydicom901 | Import leaves preconfigured handlers and level intact. The edit also promises preserved explicit `config.debug()` behavior. | Added test and probe only check import configuration. No explicit debug call validates that side of the promised compatibility contract. This is a gap, not proof of the exact private failing assertion. |
| 12 · astroid1268 | `Unknown().as_string()` no longer crashes. Added test/probe require `"Unknown"` because that is `node.name`. | The issue gives no exact required string. Observed empty-node visitors use empty text. Choosing a representation needs a public contract; self-authored equality does not settle the ambiguity. |
| 13 · astroid1333 | Before/after `pylint.expand_modules` comparison fixes a bogus initializer target; regular-package control passes. | Constructed `src/project` fixtures omit the report's `src/__init__.py`. Same caller is useful evidence but does not establish that omitted condition or full CLI behavior is immaterial. |
| 16 · SQLFluff1517 | Original double-semicolon crash becomes a parse violation. Broader grammar probes cover whitespace/invalid/empty middle cases and preserve raw input. | Their expected matched prefixes follow the new behavior. Raw preservation and reaching changed branches do not prove success eligibility under the grammar's other options. Two earlier probes lacked fixtures; a lint control also incorrectly assumed no style errors. |
| 17 · SQLFluff1625 | Reported single-table alias, no-alias control and joined-alias control pass. Rejected YAML edit was replaced by a valid Python test before submission. | Guard combines one table with used alias references. Other no-join shapes and the pre-existing documented alias policy are not settled by those examples. The earlier edit rejection is not the terminal cause. |
| 19 · SQLFluff1763 | Encoding-error helper previously emptied the file; after the edit it preserves bytes. Added CLI test asserts failure reporting and original content. | Supports the report's minimum preservation request. Full dbt/noqa setup and broader filesystem/OSError semantics remain unverified. A universal claim that these failures lack useful caller evidence is contradicted here. |

## Decision and alternatives

There is no demonstrated single cause of all eight independent failures. The
recurring actionable problem is the transition from a public requirement to the
test's conditions and expected value: helpers can change the premise (8/13),
new test values can restate the implementation (12/16), and compatibility can be
reduced to an unspecified suite PASS (10/17/19). Publicly supported examples in
7 and 19, and underspecified public oracles, limit that explanation.

Existing guidance already requested public grounding and scope review. Repeating
"test more" would not address why a larger test set can confirm the wrong premise.
The smallest selected change refines the existing review representation, with no
new planner, critic call, semantic validator, mandatory experiment or finish gate.
Model reasoning/selection may still fail despite it. If a future run supplies a
sound public oracle and matching conditions yet fails, this intervention has not
explained that failure; inspect the remaining actual public behavior instead.

## Implemented changes

1. New pytest modules in a registered additive test root are checked before the
   atomic file transaction. A known filename mismatch is rejected with the path,
   public configuration/hash and `python_files` patterns. The model can choose a
   matching name or extend an existing collected module. Other files in the same
   rejected batch remain untouched, and no accepted-edit slot is consumed.
   Ordinary pytest INI settings in pytest.ini, .pytest.ini, tox.ini, setup.cfg and
   pyproject.toml are read without importing project code; default patterns apply
   when no applicable config exists. Reads are tracked/public, at most 64 KiB.
   Unsupported commands, CLI/environment overrides, changed/nested configs and native TOML
   settings remain unknown rather than causing a guessed rejection. A filename
   match alone is not collection, function/marker execution or correctness proof.
2. `scope_review.cases[].expected_observation` now separates `outcome` (300 chars)
   and `public_basis` (200 chars, nullable). It retains the former 500-character
   text budget. The basis names a public issue clause or observed pre-existing
   contract, not the new patch/test or its successful execution. Unspecified
   values remain explicitly unknown. Old string records still parse and replay.
3. Existing post-edit review compares literal public input/setup with the actual
   reduced case and asks for a relevant compatibility/control case that could
   distinguish a narrow repair from an overbroad change. Existing adequate
   evidence is reused. Check PASS is not itself the behavior assertion or oracle.

The host validates receipt identity and annotation shape, not semantic truth.
Null annotations, prior review retention, current/historical labels and original
public-check submission eligibility remain unchanged. Tool/contract fingerprints
bind both changes. No benchmark-specific condition or private expectation enters
the runtime. Independent grading is unchanged.

## Local validation

Final focused: **88 PASS in 20.65 seconds**, including real pytest proof that direct
selection executes a misnamed test while directory discovery omits it; rejection
and corrected-name discovery; atomicity/idempotent replay; known/unknown configs;
legacy and new expectation records; invalid annotation retention; and actual
append/segmented completion input delivery with unchanged model/tool counts.
Changing configuration within the same transaction does not wrongly apply the
old naming rule. Initial focused validation had 81 PASS in 20.99 seconds.

Quick completed with **1,487 PASS, 6 FAIL, one Windows symlink host skip** in
371.17 seconds. Five failures pinned the previous current-runtime contract/schema
hashes; the sixth was the prompt-size bound. Only current identity expectations
were updated; frozen experiment identities remain unchanged. Guidance was shortened
to 11,132 characters, below the existing 11,164 cap, instead of raising it. All six
failed cases and the final changed-owner selection pass in the 88-case focused run.
The added configuration-transition test also passes. Thus the updated quick
selection resolves to **1,494 PASS/one host skip across these executions**, not a
claim that the first quick invocation passed. Previously passed tests were not
repeated without a new reason. Four isolated mock planning modes passed in quick;
the focused actual-input tests also reached isolated acceptance in both contexts.

Ruff, documentation bounds/links and diff checking pass. The separate selected
follow-up probe transport plus documentation run had 7 PASS in 7.09 seconds.
Logs, runtime hashes and source/test bindings are retained in `validation.json`
and CAS with a journal receipt. No test or record changes private grading.

Runtime hash at the start of validation:
`sha256:d0cc5f1f72dbf0754c913c2b9995edcb506f380b6f538596f9b9c40da46a86c5`.
Final runtime after shortening guidance and the configuration-transition control:
`sha256:268b9abb488f62a08bb7c6c7c754080c8893831fe68327caa467cf33085c4792`.

## Next question

The implementation fixes a known filename omission and makes expectation premises
reviewable. It does not prove the eight tasks are now repaired or that model
reasoning, cost or time improved. A future authorized integrated failed-task panel
with passing controls can test target/oracle choices and independent acceptance;
another condition-by-condition diagnosis is not a prerequisite. All prior paid
allocations remain closed. Residual semantic probe duplication is not addressed
by this change.
