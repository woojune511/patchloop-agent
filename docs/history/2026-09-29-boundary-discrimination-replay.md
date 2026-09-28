# Do the selected examples discriminate the repair condition?

Public-only replay of the [closed panel](2026-09-29-boundary-pair-panel-results.md)
confirmed a missing distinction in all four Pydantic patches and three HF patches.
The proposed PDM explanation did not reproduce a behavioral failure. This is an
operator diagnosis on saved code, not another agent experiment or acceptance score.

## Question and method

The panel's final public checks passed even for nine acceptance failures. We asked
whether those selected examples could expose the proposed wrong condition, using
only public requirements, public check source, public traces and saved final patches.
No hidden tests, reference patches or private failure assertions were inspected.

Before replay, an external hash-chained dev-run-v1 record fixed three diagnostics:

1. Pydantic: hold thinking-send mode and field name constant while changing whether
   the profile comes from the provider that carries the empty-field requirement.
   Existing thinking is a preservation control.
2. HF: compare an explicitly configured client with an endpoint-free client under
   an ambient custom endpoint, keeping a default-origin refresh route. A foreign
   refresh route is a preservation control.
3. PDM: ignore a valid or nonexistent active environment, then select another
   eligible environment or create one. Also check false-like flag reuse. Observe
   active PythonInfo construction without declaring every such read incorrect.

Each diagnostic ran on the clean base and all four saved final patches: 15 Docker
runs, 70 case observations (56 on final patches). Docker was already running; images
were present and pulls disabled. Containers used network=none, read-only root/source,
2 CPUs, 2 GiB memory, 256 PIDs and a 90-second host timeout. Every execution completed.
Source-only snapshots omit tests, private evaluators and reference patches. Images
provide the existing registered-check dependencies. P/H fixtures use local SDK/HTTP
mapping or mocked HEAD responses; PDM creates actual temporary venvs and controls
discovery/creation using the existing public fixture technique.

All 12 final source diffs matched their recorded submitted-patch hashes. Snapshot
contents matched original sources after execution. Original runs and task packages
were unchanged. Provider calls, credential loads and new private evaluations: zero.

## Results

| Diagnostic | Clean base | A1 | A2 | B1 | B2 |
| --- | --- | --- | --- | --- | --- |
| Pydantic, 3 cases | 2/3 | 2/3 | 2/3 | 2/3 | 2/3 |
| HF, 3 cases | 2/3 | 2/3 | 2/3 | 2/3 | 3/3 |
| PDM, 8 cases | 0/8 | 8/8 | 8/8 | 8/8 | 8/8 |

These totals conceal different failures; the per-case distinction is the result.

**Pydantic.** Base omits the required empty field for DeepSeek, but correctly omits
it for an independent OpenAI profile configured with the same field mode and
reasoning_content name. Every final patch fixes the former and breaks the latter:
it emits an empty field where omission must be preserved. Existing nonempty thinking
remains intact. The original public fixture's other-provider case uses a default
profile, so it does not hold mode/name constant. PB1 public decision event 19 calls
that fixture the highest-value evidence for the changed/preserved pair; event 21
then moves to upstream regression after PASS. The nearby selected cases cannot
separate the provider-carried requirement from generic field-mode configuration.

**HF.** Base preserves the default-origin route with no explicit client endpoint,
but fails to rebase for an explicit custom endpoint. HA1/HA2/HB1 fix explicit rebasing
and incorrectly rewrite the endpoint-free client's route to the ambient host.
HB2 passes all three cases, confirming its local explicitness improvement. The
existing public fixture checks endpoint-free access through the direct function;
client cases always construct HfApi with an explicit endpoint, including cases
running under an ambient endpoint. Thus the important cross-product is absent.
HB2's failure in the closed full evaluation remains unexplained by this diagnostic;
passing this boundary does not contradict that failure or establish a complete repair.

**PDM.** All final patches select the expected environment or creation fallback in
all eight cases, for both VIRTUAL_ENV and CONDA_PREFIX. DA1 constructs PythonInfo
for the ignored active path, including a nonexistent path; the others skip it.
That construction does not cause an exception or wrong selection in these cases.
The earlier candidate explanation is therefore unconfirmed, and the simple
missing-path variant is falsified as a reproducer. Do not inject an arbitrary
exception into PythonInfo just to make the hypothesis pass. Base failures are
consistent with its outer truthiness guard disabling the entire venv branch,
including for the nonempty false-like string. The original DA1 acceptance failure
still needs a concrete public reproducer; no cause is inferred from its FAIL alone.

## Implication and next question

The confirmed failure mechanism in Pydantic and three HF runs is a non-discriminating
preservation example: it changes more than the condition whose ownership matters,
or exercises a different entry path. A public-check PASS can consequently validate
the intended positive case while leaving the overbroad condition unchallenged.
This is a demonstrated check-scope/evidence-selection gap; it does not by itself
attribute the gap to model capability, prompt design or a missing harness feature.

The next useful experiment would measure whether an agent can choose an input that
holds the proposed guard constant while varying the requirement's distinguishing
condition. Define that outcome before adding another instruction or hard gate.
Separate choosing such an example from executing it and from repairing the result.
Use additional task families before claiming the mechanism generalizes. These newly
written task-specific counterexamples are operator diagnostics, not material to
silently inject into future agent inputs or reinterpret as benchmark tests.

No production change, public task-check expansion or paid follow-up was made.
This replay used registered-check images, not the agent run_probe dispatch path;
it proves these counterexamples can execute locally, not that the existing probe
service would admit and run every program unchanged. That capability question and
the remaining HF/PDM failure causes stay open.

Documentation layout/link/size tests passed (5 tests), and git diff --check passed.
Production code did not change, so no new runtime quality or full-suite claim is made.

## Evidence

External root: C:/pt/analyses/boundary-discrimination-20260929-v1.

- runs/run_dev_discrimination.jsonl: frozen questions, script hashes, execution
  receipts and integrity verification, in a hash chain.
- P.py, H.py, D.py: diagnostic programs; public-sources.json and copied public-check
  programs record the public fixture sources and dependency environments.
- run.py and verify.py: bounded execution and source/submission integrity checks.
- <label>-receipt.json: full observations, stderr and snapshot content hashes.
- summary.json: all 70 observations, including negative PDM evidence and base controls.
- Original public traces and final-check results remain at
  C:/pt/boundarypair0928b/public-review and its per-run journals. Original acceptance
  outcomes were not rerun and are not new observations in this investigation.
