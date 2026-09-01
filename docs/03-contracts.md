# Active contracts

## Turn grammar

One model response may request either:

- 1 to 4 parallel `search_files` and/or `read_file` calls; or
- exactly one `apply_patch`, `run_check`, or `finish_task` call.

Mixed and oversized batches receive one short correction. A repeated protocol or
incomplete-response violation terminates the row.

`run_check` is available from the first turn. `finish_task` is exposed only when
all visible checks passed against the exact current diff. The next context always
contains that full diff, so no `get_diff` tool exists.

## Mutation

Every `apply_patch` requires:

- `hypothesis`
- `expected_behavior`
- current `evidence_span_ids`
- `edit_anchor.path`, exact `old_text`, and occurrence
- a raw Git unified diff

The anchor and cited spans must still match current source, and the resulting diff
must satisfy `allowed_paths`, `forbidden_paths`, changed-file, and diff-line limits.

If one public failure signature repeats across two distinct diffs, the next
mutation must additionally include `falsified_prior_hypothesis` and
`alternative_mechanism`. This requirement does not create a plan turn.

## Context

Context is allowlist-built from the public task, current full diff, requested
source spans, recent visible-check results, bounded `last_successful_mutation`, and
the latest three attempt-result-next-question cards. Raw reasoning, private task
data, hidden tests, evaluator details, and reference patches are excluded.

## State and recovery

Each run has a unique ID and an append-only `dev-run-v1` JSONL stream outside the
repository. Every record has a sequence, previous hash, and event hash.
Mutation and check actions use `action_id + input_hash`: identical replay returns
the durable result; action-ID reuse with different input fails closed. A mutation
admitted before a crash is reconciled against the workspace rather than applied
twice. A provider start without durable usage completion is uncertain and is never
retried automatically.

## Limits

Defaults are 40 model calls, 100 tool actions, 4 accepted mutations, 1,800 seconds,
one protocol/incomplete recovery, and 4 parallel reads. `repeat` is 1 by default
and at most 6.
