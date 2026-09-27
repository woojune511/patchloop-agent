# Original-input pilot probe readiness and no-dispatch draft

## Question and boundary

Can the three original-input packages use the selected baseline's isolated public
probes before requesting paid fresh solves? Evaluator calibration alone cannot
answer this because evaluation uses Python 3.13 and probes use clean Python 3.12.
No model, token-count request, evaluator image acquisition or image build ran here.
Original task packages and runtime source are unchanged.

## Preparation evidence

Fresh clean sources were published under `C:/pt/prepared/` with names
`original-toqito-1538-0927-v1`, `original-montepy-933-0927-v1`, and
`original-darts-3065-0927-v1`. Each contains `prepared-source.json` bound to the
package repository/base. Only public project metadata selected dependencies.

- Toqito: `original-toqito-1538-probe-0927-v1/resolve.json` reports that required
  `picos>=2.6.2` has no usable wheel. The current binary-only resolver rejects it;
  no dependency descriptor was published. This is a preparation limitation, not
  an agent failure. No runtime dependency was silently omitted.
- Darts: `original-darts-3065-probe-0927-v1/install.json` reports successful offline
  installation, but inventory is 574,281,919 bytes against the 268,435,456-byte cap.
  Largest directories are llvmlite (179,441,907), scipy (80,486,547) and statsmodels
  (41,619,577). No usable descriptor was published and no cap was increased.
- MontePy: initial dependency preparation succeeded, but the operator selected
  source root `.`. The snapshot filter selects directory prefixes literally, so
  nested package files were absent and the actual probe raised ModuleNotFoundError.
  The original receipt remains intact. A separate v2 preparation selects `montepy`;
  it retains the same public runtime requirements and uses a fresh output directory.
  With source included, OpenBLAS attempts 16 threads and fails at thread 7 against
  the probe PID limit of eight. This is an executed resource mismatch, not a missing
  NumPy wheel. A third canary changes only OPENBLAS_NUM_THREADS to 1 before import:
  PASS, exit 0, public /workspace/montepy/__init__.py imported and Cell constructed,
  without timeout or cleanup failure. This conditional success does not change the
  default profile or establish unrestricted probe readiness.

Probe receipts and the no-dispatch manifest are in
`C:/pt/analyses/original-pilot-readiness-20260927-v1`, journal
`run_dev_originalpilotreadiness`. The draft is `execution-draft.json`, canonical
artifact SHA-256 `c146f9663eb679ee52ecc337696c16d2ced90659b96d85eb90fb66986ef1fd35`.
It binds runtime, tool surface, task/issue/source hashes and the available MontePy
dependency descriptor. Every row is dispatch_ready=false; missing descriptors are
explicit nulls, not a fallback to probes without dependencies. The canary imports public source and constructs a
base Cell; it does not check the requested repair or use hidden evaluation data.

## Proposed invocation and next decision

The draft fixes the existing three-task order, one fresh solve each, model
`gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens, and existing baseline
policies. Proposed caps remain $1.20 per task and $3.60 total, without transfers,
retries or automatic replenishment. Limits remain 40 model calls, 100 tool actions,
four accepted mutations and 1,800 seconds per task. The credential path is
`C:/Users/geonj/Documents/PatchLoop/.env`; only file existence was checked, not its
contents or provider validity. This draft is not authorization or a runnable grant.

Do not dispatch the fixed pilot while probe preparation is incomplete, silently
turn probes off, omit dependencies, or replace tasks. The next engineering decision
is public dependency preparation support: first align numerical-library thread
defaults with the existing sandbox budget, then review an isolated build path for a
source-only package and an explicit resource policy for larger dependency bundles.
Keep these environment changes separate from agent quality and original scoring.

## Validation

Documentation layout/link tests: five passed. Runtime/task bytes are unchanged;
no implementation suite or mock smoke was repeated for this documentation-only
change. Canary receipts establish environment behavior only, not task correctness.
The three preparation journals and all failed canaries are retained unchanged.
