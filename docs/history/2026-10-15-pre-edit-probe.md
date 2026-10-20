# Public execution of the pre-edit diagnostic

Date: 2026-10-15. One operator-authored public probe executed; runtime unchanged.
Source HEAD: `51e2d7aaf09f037e8fed9f5a443de9227ffe7dfa`.
Every result is `official=false` and claim-ineligible. Model A/B, provider calls,
token-count calls and new private evaluations: **zero**.

## Question and result

The [prepared diagnostic](2026-10-15-pre-edit-diagnostic-design.md) had only passed
static checks. This execution tests whether its imports, temporary method
substitution and observations work in the actual public probe environment. The
question matters because [rerunning the unchanged candidate](2026-10-07-intermediate-test.md)
passes the selected task test and cannot test the contemplated removal of L036.

The frozen program **distinguishes the two states on the public CTE case**:

| Observation within the single probe | `my_id` indentation | Matches public expected output |
| --- | --- | --- |
| Third-edit candidate, current L036 method | Eight spaces | Yes |
| Same process, with the earlier L036 addition temporarily removed | Five spaces | No |

The second output differs from the expected output only in those three missing
spaces. The probe restored the original method in `finally`. All five supplied
setup comparisons matched: source hash, unique replacement anchor, temporary
method installation, original method restoration and unchanged L036 file bytes.
Independent host checks also found all 1,807 tracked files unchanged in each of
the original and reconstructed workspaces, with all 36 bound inputs unchanged.

One `run_probe` action completed in 12.125 seconds through `DevToolGateway`.
The raw receipt has `output.status=passed`, exit code zero, no timeout, deadline
exhaustion, truncation or cleanup failure, and confirmed container cleanup.
This status means the diagnostic program completed; the hypothetical task
observation is a failure. The receipt retains a package deprecation warning and
an L003 repeated-fix warning; neither prevented either observation.

## Controlled state and execution boundary

The original SQLFluff-1733 run is `run_dev_c6cdf266d5a34ded`. A separate local
clone was reconstructed from base `a1579a16b1d8913d9d7c7d12add374a290bcc78c`, applying
only the recorded replacements at sequences 255, 267 and 356. Each preimage,
postimage and intermediate full diff matched the original journal. The resulting
candidate equals the earlier independently reconstructed third-edit workspace:
`sha256:59679012118d519810c25430eb177c6fe0fb5480b986b452b6c2e8bd676d2987`.

The program is the unchanged 2,580-byte `reference_probe_safe_trace.py` frozen
before this request, hash
`sha256:cfbd10c277d2f58b00b9ade34fee0de7f4685c27f3001742d111720752d11b11`.
It calls default `sqlfluff.fix` twice on the same public SQL input. Only the
L036 method is replaced in process; L003 and other source remain fixed. Applying
its replacement to the full L036 file exactly reproduces the original fourth-edit
file. The original final and third-edit workspaces differ only in that file.
The trial function uses a synthetic filename, preserving the distinction between
hypothetical execution and line feedback for the current source.

The existing Python 3.12 public image was reused at digest
`sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Prepared public dependencies came from
`C:/pt/cd20p06c/dependencies/18/prepared-probe-dependencies.json`; both its identity
and installed content matched the original run. The complete probe profile also
matched the original hash:
`sha256:017d711b962db34da9a80840af0d6af10228c3eea4c99b427b90fe3542a9226d`.
The ordinary 30-second, one-CPU, 512-MB, read-only, network-disabled probe contract
was used, with a fresh 120-second operator deadline. No new tool or allowance was
introduced. The public snapshot contains source roots and prepared dependencies;
the diagnostic does not mount evaluator material or execute the pytest suite.

Initially, preflight stopped because the Docker Desktop Linux engine pipe was
unavailable. No action or container had started. The user explicitly authorized
starting Docker Desktop and executing once. After read-only readiness inspection,
the same frozen plan dispatched exactly one probe, without an image pull/build,
diagnostic retry or replay. The preflight failure remains in the journal.

## Decision and limits

For this checkpoint and public input, the assumption that removing the L036
addition preserves the successful CTE behavior is contradicted. This operator
diagnostic could reveal that consequence before consuming a file edit. The
existing public tool can express and execute this comparison, so this result
does not justify another tool, larger tool budget or an additional runtime gate.

Keep the runtime baseline. This result closes the prepared program's execution
feasibility question; it does not show that an LLM will select the diagnostic,
construct it correctly, use its result or find a complete repair in the one edit
remaining. The selected case does not make the third-edit candidate correct: its
previously observed regression failure remains. The regression suite and private
evaluation were not rerun. No solver received this result or earned check credit.

The [proposed model A/B](2026-10-15-pre-edit-diagnostic-design.md) remains prepared,
unexecuted and unauthorized. Its requests and grading material retain their
original bytes. There is no autonomous repair gain or generalization claim.

## Evidence and validation

External root: `C:/pt/hyprun01`.

- `run_once.py`, `plan.json`, `reconstruction.json`: bounded execution and exact
  candidate/input bindings. Frozen plan hash:
  `sha256:b98dba05d5990b3cefb5de496acb87d00df9c8f99da9e32862f2e846444dcb2e`.
- `docker-readiness.json`: installed-image inspection after authorized startup.
- `receipt.json`: authoritative full public action result, hash
  `sha256:082748b5f8cd9bc1cae5789c1f01c67839e68ae941210ccc0d84ab233ba885f6`.
- `result.json`, `analyze_result.py`, `interpretation.json`: observed outputs,
  source equivalence, one-action count and integrity checks. The summary's
  `probe_status` is null because its writer queried an absent key; the separate
  interpretation records the authoritative `receipt.output.status=passed`.
  Neither the summary nor the completed execution was overwritten or repeated.
- `runs/run_dev_counterfactualprobe.jsonl` and
  `probe/runs/run_dev_counterfactualaction.jsonl`: hash-chained preparation and
  action journals, including the durable `action_id + input_hash` pair.
- `validation.json`, `closeout.json`: documentation checks and final commit binding.

The setup helper's generic `selection=model_authored` metadata is not authorship
evidence: this was the frozen operator reference, without any model sampling.
Setup comparisons and line observations are diagnostic evidence, not independent
task acceptance. Documentation layout/link, Ruff and whitespace checks passed.
No production code changed, so the broad runtime suite and mock smoke were not
repeated. Original histories, journals and the user's AGENTS.md edit were preserved.
