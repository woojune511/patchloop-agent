# Conan final-patch probe replay and recheck boundary

## Question and evidence

The live run passed the original oracle, but its failed public diagnostic was
not rerun after the second edit. This follow-up tests that exact diagnostic on
the exact final patch, without changing the original run or adding model calls.
This closes a specific evidence gap; it is not a new agent solve.

Copied the clean prepared base into a separate external Git checkout, applied the
saved submitted patch and verified the complete diff hash matches
3b31030232ab4f68b3e8fc7dfc0451eab4ac58fc45bbd0746542c6bf4f357aaa.
Reused the original run_probe question and python_source without edits, the same
prepared dependencies and DockerProbeSandbox profile. No hidden material or
reference patch entered this replay.

Both original diagnostic cases passed: a plain shared:INFO prefix and a prefix
that itself contains Emscripten. Both return emcc, 4.0.22, emcc. Exit 0,
13,271 ms, no timeout, cleanup confirmed. The original failed probe remains failed
in its immutable live journal. The successful result belongs only to this operator
replay; the agent did not perform it during the paid run.

Evidence root: C:\pt\analyses\conan-final-probe-20261001-v1.
Journal: runs/run_dev_conanfinalprobe.jsonl, with frozen original arguments, parent
action identity, patch hash, preflight identity and complete replay result.
Parent: run_dev_ffee311ba7aa4a11 under
C:\pt\runs\conan-original-live-20261001-v1.

## Why automatic recheck did not run

patchloop/dev/repair_recheck.py selects only unsuccessful registered run_check
results bound to the pre-edit diff. run_probe is explicitly excluded; the CLI
describes repair-recheck as rerunning a failed public check. On this saved journal,
select_repair_recheck returns None for the second edit: the registered public
check had passed. The read-only audit verified the original journal bytes remain
unchanged. Verification observations retain prior probe evidence, but do not make
it a submission gate.

This is a boundary of the current policy, not a broken automatic-check trigger.
The final replay closes the observed case. Retain the baseline: one successful
repair does not justify automatically replaying arbitrary model-authored probes,
which may have fixture assumptions or consume limited resources. Whether recurrent
unrechecked probe failures lead to incorrect submissions remains unresolved; use
such evidence before proposing a narrowly scoped policy change.

No runtime behavior changed, paid call, image pull/build, retry or resume occurred.
The allocation remains closed. The branch PR also includes earlier jsonschema task
admission and the live hidden-check requirement; its scope is broader than this
documentation-only follow-up.

Validation: 65 related recheck/task/adapter/documentation tests PASS, Ruff PASS,
diff whitespace checks PASS. The related test group exceeded the two-minute
focused-validation target; it is broader than this documentation change requires.
Documentation checks also passed separately after shortening current status.
No new full-suite result is claimed; cross-platform PR CI remains required.
