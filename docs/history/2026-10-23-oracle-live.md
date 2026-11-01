# Oracle and correction funding live pilot

Date: 2026-10-23. One authorized fresh dev-train solve; official=false,
claim-ineligible. Allocation closed; repair failed.

## Question and fixed scope

The [preceding pilot](2026-10-23-repro-live.md) observed the reported failure but
declared it as the desired result, then ended without an edit or submission. The
[implementation](2026-10-23-oracles.md) separated failure/desired values and reserved
one full response correction. This pilot asks whether those mechanisms acquire a
faithful original failure and reach verified repair within the same USD 0.88 cap.

Registration: `C:/pt/oracle-recovery23-live-ready/request.json`, SHA-256
`6bf94f4fc0b279af04cf2158ac78c5cd8227d167b5620acd0875436d2f0512f1`.
Its proposal remains immutable; a separate authorization receipt binds the user's
approval. The exact command is in that root's `command.ps1`. Conditions:

- Astroid-1333: `tasks/dev-train/current-dev20/13/public.yaml`, one fresh solve,
  `gpt-5.4-mini-2026-03-17`, xhigh, requested output ceiling 25,000, repository `.env`.
- Runtime commit `0e0def9271b3faaa3929c770c9e94a6c92a04510`, content hash
  `sha256:9fba6972d78cc32a204a54c75194a5fe06902b8316c06a922ff8b8f1e9840154`.
- 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  outer supervisor limit 1,920 seconds. No retry/resume, replacement or cap increase.
- Segmented-v1, result-or-size-v1, brief-v1, probes/none, repair-recheck,
  protected-v1, bounded-v1 acquisition and completion-recovery-v1.
- Same prepared source/dependencies, local images, model and cap as the preceding
  pilot. Two bundled changes and a historical reference, not a matched control.
  No seeded case, prior solver context, operator hint or injected response error.
- At most two frozen post-submission public checks, missing/present initializer,
  sharing 120 seconds and zero model calls, on the entire submitted patch.

The positive criterion requires a faithful baseline failure, comparable candidate
support, required check/submission, both public checks PASS and independent acceptance
PASS. Submission alone does not meet it. Count/transport/billing or cleanup uncertainty
stops subsequent work. Existing images only; no image pull/build or Docker startup.

## Observations

Run `run_dev_f2b136229bb4489e` ran from 16:58:37 to 17:10:31 KST, 714.31 wall seconds.
All billing and input counting settled. No hard timeout or automatic retry occurred.

| Measurement | Result |
| --- | --- |
| Model calls / input counts / actions | 35 / 36 / 37 |
| Cost / cap | USD 0.864747450 / 0.88 |
| Input / cached input / output tokens | 1,296,393 / 763,776 / 90,667 |
| Reasoning output tokens, usage metadata only | 79,514 |
| Reproduction requests rejected / dispatched / returned / setup failures | 2 / 0 / 0 / 0 |
| Read / search / accepted edit | 13 / 19 / 1 |
| Required base-regression | PASS: 1,231 passed, 69 skipped, 15 xfailed |
| Submission / original evidence | submitted / unverified_delivery; no bound case |
| Post-submission missing / present public condition | FAIL / PASS |
| Independent task acceptance / safety | FAIL / PASS |
| Integrated positive criterion | not met |

The first response consumed all 25,000 output tokens, entirely reasoning according
to usage metadata, and returned no action (`incomplete`, `max_output_tokens`). The
funded correction received the full 25,000 allowance and returned a schema-valid
`run_probe` call after 22,243 output tokens. Its credit was consumed once and never
renewed. Protocol shape recovered; the reproduction request itself was rejected.

Both requests declared F0010 as failure and no F0010 as the desired value, so they
did not repeat the previous inversion. Both used the same non-verbatim
`requirement_quote` and failed with `reproduction requirement_quote must occur in
the public issue`. The second purpose and program were unchanged. The first error
was present in the next model input; the separate note update also had an
`unobserved_tool_result` rejection. This is not evidence of a missing primary error.
After two request errors, acquisition became `request_blocked`/released, with zero
actual caller attempts and zero completion cases. Original evidence stayed unverified.
Oracle meaning was declared, but its execution and caller mapping were not validated.

After 32 reads/searches, the cost horizon restricted call 33 to edit/stop, call 34
to required check/stop, and call 35 to finish/stop. Output ceilings were respectively
10,435, 8,154 and 11,194, with two/one/zero minimum successor calls reserved. The
model edited `astroid/manager.py`, passed the registered suite and submitted. Its
planned new regression test was not added. Changed-line execution feedback was
unknown (`unsupported_python_options`), not evidence of an unexecuted line.

The submission retained `unverified_delivery`, `request_error_limit`, zero original
attempts and `no_bound_reproduction`. Independent evaluation did not upgrade that
state. Remaining USD 0.015252550 is not a new execution allocation.

## Why the submitted patch did not fix the public failure

Submitted full patch hash:
`sha256:bb3fca8bc6184b6a306d2385e9ccf2171a7a9de5f7697377c2c9cfa80f7e9ce9`.
It changed `source = True` after a successful `get_source_file` call into an `else`
branch assigning `source = os.path.isfile(filepath)`. Its stated hypothesis was
that a directory input was incorrectly treated as a source file.

The frozen public checks ran on that exact full patch in a separate worktree,
completed in 18.429 seconds, and confirmed container cleanup. The missing case still
returned F0010, exit 1, without analyzing the child file. The present control returned
exit 0 and analyzed it. These are operator observations after submission, not evidence
the solver acquired or used during its run.

The missing-case public call trace passes `src/project/__init__.py`, which does not
exist, to `ast_from_file` with `source=True`, then to `file_build`. Source inspection
shows `get_source_file` raises `NoSourceFile` for that missing path. The patch changes
only the successful lookup branch; the exception branch still preserves the incoming
`source=True`. Thus the saved trace and source explain why this patch leaves the
reported path unchanged. This does not establish behavior for every directory case.

## Decision and remaining question

Supported: a naturally triggered correction received its reserved full allowance;
the credit did not renew; the completion horizon retained edit/check/finish; rejected
requests created no verified case; missing evidence survived submission. These are
mechanism observations in one execution, not causal improvement or general accuracy.

Not supported: useful original reproduction recovery, faithful executed oracle
binding, correct repair or the integrated positive criterion. The correction solved
response formatting but not request validity. Larger output alone is not established
as a remedy: the first failure occurred with the full allowance, before budget pressure.

The next diagnostic question is why the agent repeated an unchanged rejected request
despite seeing its exact error, then chose a repair for an unobserved input path.
Request-construction friction and failure to use feedback remain plausible; this run
does not distinguish them. An offline inspection or bounded request-construction
control should precede another paid solve. No additional rule, default adoption,
follow-up implementation or paid run is selected by this result.

## Evidence and integrity

State root: `C:/pt/oracle-recovery23-live`. `collection.json` has SHA-256
`f44b0e6a4dc194a9ef4370991ef8b33a9a93096d118dc03449bca7a5d1a7fe93`.
`process-result.json`, `public-assessment.json`, immutable CAS and the solver/operator
`dev-run-v1` journals preserve outcomes and the complete funding timeline. All 106
frozen runtime/task/grader files stayed unchanged; the ready/live journal chains and
7/174 existing CAS objects passed integrity checks before collection. The exact full
solver diff matched the submitted and assessed patch. CLI stderr was empty.

`feedback-audit.json` (SHA-256
`cda56505e893a9e5f005aa514c59fd78a4f310eae41beb7dfc362fac0000eb3d`) clarifies one
collector limitation without rewriting its sealed output: `native_probe_feedback`
is empty because it searched native function outputs; segment restarts delivered
the error receipts in developer messages. Both receipts were verified there.

The initial preparation-only path-comparison failure and corrected normalization
remain in `C:/pt/oracle-recovery23-preflight-audit`; no live call occurred in either
preparation attempt. Credentials were not printed. Provider reasoning contents,
private evaluator details/tests/spec and reference patches were not inspected or
fed back to the solver. The allocation is closed; no remaining balance was reused.

Only reporting documents change in the product repository. Documentation validation
is recorded separately in the operator journal; prior runtime regression/mock results
remain in the implementation report. This run adds no Linux CI or generalization claim.

Material passport: academic-research-suite / experiment-agent; standalone run;
2026-10-23; oracle-recovery-pilot-v1. Verification status UNVERIFIED for successful
repair and generalization; the negative live outcome and artifact checks are recorded.
