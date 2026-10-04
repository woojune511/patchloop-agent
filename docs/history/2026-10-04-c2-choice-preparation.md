# C2 fourth-edit choice: offline preparation

Date: 2026-10-04. Provider-free restoration verified; no live continuation executed.
The [regression investigation](2026-10-04-sqlfluff-c2-regression.md) remains closed.
The current [evaluation scope](../../.agent/c2-choice-evaluation.md) adds no policy.

## Selected question and decision

The operator identified a within-four-edit path satisfying the issue and public
regression. That establishes existence, not autonomous choice. The user requested
preparation of an evaluation from edit 3 with the historical remaining resources.
Starting after edit 4 with extra edits would measure a different question; injecting
the operator solution or later failures would invalidate this earlier checkpoint.

This preparation tests state fidelity, not mismatch recognition or repair quality.
A request mismatch, lost receipt/anchor, changed policy or reset budget would prevent
attributing a continuation outcome to the intended original decision state.

## Restored boundary

Source run: C:/pt/prlive01/1733C2, run_dev_8ae27bd1b3464578.
The prefix ends at model_input_prepared sequence 238, after the third automatic
probe and its native segment boundary. Target input count/dispatch and every later
decision are excluded. The prepared boundary hash is:
sha256:070e999e9e932b4f816e9051b393b06c9d73c4a0c693b056bb4056f0b68529ec.
Candidate diff:
sha256:1aeb6873c007f9d407817b9fd81399ee5ba786340cf18aef57e53495a34c4f9b.
Request hash:
sha256:d27f40e0782fab9c89fe3ea9cb4b213aa1da83d4f89e6f5d8ffc127dcc1b8b1b.

Restoration verified source journal/envelope hashes and the existing runtime hash,
recursively copied prefix-referenced CAS bytes including encrypted continuation,
and replayed only the three recorded text replacements into a fresh local prepared
source. Every replacement verifies preimage, postimage and cumulative diff hashes.
Original journals, candidates and user AGENTS.md bytes remain unchanged.

Historical usage is 14 model calls, 27 actions, three accepted edits and
USD 1.5654975. At the prepared boundary active elapsed is 829,490 ms, leaving
970,510 ms of the original 1,800 seconds. The earlier probe receipt's 829,476 ms
is not used as the boundary. Remaining resources are 26 calls, 73 actions, one
edit and USD 1.4345025; ordinary completion reserves still apply.

The original C guidance and saved-program-v1 setting were retained. Existing generic
continuation restoration predates automatic probes and omits that request option,
so its restore entrypoint was not used unchanged. A bounded external preparation
script reuses its CAS resolver, first-request verifier and scripted runner rehearsal,
plus the existing candidate-restoration and C-policy helpers. Production runtime
and ordinary resume contracts were not changed.

## Offline validation and limits

Four fresh external branches exercised scripted stop, count timeout, transport
timeout and missing usage through the existing runner and adapter. Each rebuilt
request matched the frozen request except for the allowed active-time comparison;
every dispatched synthetic request then exactly matched the frozen request. The
stop path ended AGENT_STOPPED; all uncertainty paths stopped remaining work with
their distinct terminal results. No new probe/check/mutation ran. Restored counters,
candidate identity and inherited receipts remained intact, without double actions.

Read-only preflight verified the registered task, existing prepared source and
dependencies, evaluator/probe image identities, C model-policy hash and credential
path/existence. It did not read the credential, start containers, pull/build images,
count input remotely or contact a provider. Model acceptance, live repair, original
acceptance and Docker safety remain NOT_RUN. Actual new model cost is USD 0.

Evidence root: C:/pt/analyses/c2-choice-prep-20261004-v1. prepare.py records the exact
single-case procedure; packet.json freezes source, request, resources and proposed
two-repeat scope. stop.json, count.json, transport.json and usage.json retain the
scripted receipts; preflight.json records environment checks. collect.py composes
the existing continuation collector/ledger and public pair checker; manifest.json
will bind its exact execution commit and scope before approval. A hash-chained
dev-run-v1 preparation journal binds these records. Fork workspaces/journals live
under C:/pt/c2cp01. Failed attempts, if any, are retained rather than overwritten.

The four restoration rehearsals completed in 38.9 seconds. An additional synthetic
two-row collector audit delivered the exact C2 request on both branches and charged
only new simulated usage to the shared ledger. Its public pair was stubbed and is
explicitly NOT_RUN; it adds no behavioral evidence. collector-audit.json retains
that result. No real authorization file or live allocation was created.

Repository changes are documentation only. Sixteen documentation and existing
collector/ledger tests passed in 19.1 seconds; the latter include a synthetic fixture
submission reaching isolated local evaluation and stop-all uncertainty checks.
Ruff and diff checks passed. No production runtime change calls for rerunning the
full fast suite or separate mock evaluator smoke. The actual-task stop rehearsals
do not reach isolated evaluation and are not reported as evaluation successes.

The decision is that this checkpoint can be restored faithfully for a newly approved
bounded continuation. It does not establish that the model will choose the narrower
patch, that more edits help, or that any harness improvement has occurred.
