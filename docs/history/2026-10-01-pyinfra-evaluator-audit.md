# Pyinfra evaluator expectation audit

## Question and boundary

The [public diagnosis](2026-10-01-pyinfra-public-diagnosis.md) observed correct
timeout argument flow despite two original hidden failures. This matters because
attributing evaluator artifacts to the agent could motivate an ineffective prompt
or code change. Audit whether the failures identify missing behavior or require
a particular internal implementation. This is an operator-only investigation:
private tests were inspected and replayed, never supplied to a solving agent.
No reference patch was needed. No model invocation occurred.

Saved run: `run_dev_710588e1c1a94d4f`, base
`185f7dbec96f8e1d5f7cfefe0f325f99ab73927a`, submitted patch SHA256
`b34362d8686ee9a0798e40e55eed651ce8fdc60080f9bece13dd6f8fa129c3ed`.
Original package, scoring, historical verdict and earlier records remain unchanged.

## Diagnostic and observations

Before execution, froze the question, programs, original oracle hash and stop
condition in an external hash-chained journal. Applied the saved patch to fresh
prepared source. Used the already-installed digest-pinned evaluator image from the
public diagnosis with DockerSandbox network isolation, read-only source/root and
a 120-second limit. Replayed the original test patch and command, changing only
traceback verbosity. It reproduced exactly 11 passes and two failures:

- `test_load_ssh_config_proxyjump`: the mock expects an explicit `timeout=None`
  keyword; the real call omits it. The submitted gateway has default timeout=None.
- `test_proxyjump_propagates_connecttimeout`: `kwargs["timeout"]` raises KeyError
  on the mocked jump SSHClient.connect call. That mock replaces the method which
  would parse the jump host's own SSH configuration and resolve its timeout.

A separate semantic diagnostic retained real SSHClient.connect, parse_config and
gateway, mocking the Paramiko connection and transport network boundaries. The
same timeout values as the hidden fixture (jump 7, target 5) reached Paramiko as
7 and 5, with channel-open timeout 5. Hostnames were synthetic diagnostic names;
this was a timeout-resolution comparison, not an exact fixture replay. Real SSHConfig
parsed the text, and the imported candidate module was asserted under /workspace/src.
Other issue-derived public cases retained their previous results.

Gateway calls with omitted timeout and explicit None bind to identical effective
arguments and both reach the fake transport with effective timeout=None. These
assertions passed. Both containers confirmed cleanup. The prior public diagnostic's
base and wrong-forwarding controls remain separate supporting evidence: base lacks
the channel timeout; forwarding the target timeout overrides a distinct hop value.

The driver then used a nonexistent read_events method for its final journal check.
This happened after both execution receipts and completion were persisted. A separate
follow-up validated all four events with DevJournal.events(), appended the diagnostic
bookkeeping error, and revalidated five events. Neither diagnostic was rerun, and the
original driver and error remain preserved.

## Decision and limits

Both reproduced failures impose internal call requirements stronger than the
public timeout interface requires. One distinguishes equivalent optional-argument
spellings; the other intercepts configuration resolution before its implementation
runs. They do not demonstrate the two corresponding behavioral failures in the
submitted patch. This changes the interpretation of the batch's pyinfra failure,
not its recorded score: original hidden FAIL, 1/3 bug cases and 10/10 regressions
remain intact. No replacement acceptance verdict was produced.

Keep the agent baseline unchanged. Do not modify the patch to satisfy these mock
shapes or introduce a shared verification rule from this case. A separate evaluator
revision could test effective connection/channel behavior while accepting equivalent
implementations, but must retain the original oracle and calibrate against base,
correct and incorrect timeout controls before issuing a new verdict. That revision
was not implemented or executed here.

Real network waiting, SSH banner handling, multi-hop behavior and overall task
correctness remain unproven. The evidence establishes two evaluator limitations,
not a general repair success or an explanation for other tasks' failures.

## Evidence and validation

External root: `C:\pt\analyses\pyinfra-evaluator-audit-20261001-v1`.
Journal: `runs/run_dev_pyinfraevaluatoraudit.jsonl`; content-addressed receipts
retain execution policy and outputs. Readable traces: `original-oracle-trace.txt`
and `semantic-boundaries.txt`. Driver: `C:\pt\pyinfra_evaluator_audit_20261001.py`.
Only current status and this new record changed in the repository. No paid calls,
runtime edits, package edits, image creation or historical rewrites occurred.
Documentation layout checks and whitespace validation passed.
