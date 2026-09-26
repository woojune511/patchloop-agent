# First-batch declaration context diagnostic

`diagnostics.declaration_context.run(request, policy="python-declaration-doc-v1",
experiment_hash=...)` uses the ordinary dev runner with an opt-in search gateway.
Omitting the policy takes the original runner path. No CLI default, public tool
schema, plan instruction, completion gate or evaluation contract changes.

## Source selection

Only uncached `search_files` results in the first tool batch can gain new context.
The original registered search still determines files, literal matches, order and
all returned hits. For a `.py` file, a generic AST rule selects a module/class
`Assign` or `AnnAssign` whose assigned name contains the literal query and whose
name line is already in a returned span. Its immediately following literal string
is treated as attribute documentation. Comments/blank lines between the two are
allowed; intervening statements are not.

Expand one hit per declaration to include that complete declaration and string,
preserving all originally returned lines. Function-local variables, arbitrary uses,
tuple unpacking, nonliteral strings and unsupported/syntactically invalid Python
receive ordinary search results. No imports or project code execute. There are no
task names, desired conditions, known counterexamples or semantic annotations in
the selector or result.

The expanded span is at most 40 lines; all hits share the existing 20-span and
24,000-content-character limits. A whole block that would exceed a limit is omitted
from the expansion, keeping the original hit unchanged. Other hits are never dropped
to make room. A changed source hash or inconsistent span fails through the normal
tool error path. Existing tracked/public path admission and source-size bounds apply.

## Evidence and lifecycle

Expansion happens before normal source observation, fingerprints, mutation evidence,
cache and action-result journaling. Span IDs bind the actual new ranges and bytes.
Only delivered lines become editable evidence. Replayed action IDs and same-diff
search-cache hits retain the recorded result; later batches do not gain new expansion,
but already observed expanded content may still be returned from the normal cache.

The policy event binds its implementation, limits and external experiment hash.
An observation event records original/expanded output hashes and omitted blocks.
Those operator receipts are not new model instructions. Gateway reconstruction
requires the same binding; a policy cannot be attached after an ordinary episode
has begun. Normal fresh requests still receive the same initial public input.

The wrapper requires a fresh external state root, repeat=1 and no resume. Run it in
a dedicated sequential process because the scoped gateway hook is process-local.
The normal runner owns workspace isolation, cost admission, transport uncertainty,
idempotency, completion and isolated evaluation. This diagnostic does not provide a
new paid allocation or normal-CLI recovery of diagnostic runs. The separate
[checkpoint sampler](declaration-checkpoint.md) compares frozen next decisions.

## Validation and interpretation

Focused tests cover exact source bounds, ignored contexts, limits, hash mismatch,
private paths, replay/cache, mutation from newly delivered lines and hook restoration.
A/B mocks in both context policies compare actual schemas, prompts and normalized
initial states, then reach search/read/edit/check/submit/isolated evaluation. They
test plumbing and delivery, not autonomous condition reasoning.

The external saved-search preview replays only the first public search batch from
a closed run and compares code ranges. It is not a hydrated historical checkpoint,
does not preserve or dispatch that run's entire native request, and measures no model
effect. The separate checkpoint sampler binds the prior plan, native continuation,
changed search evidence and derived state. A fresh run through this wrapper alone
is not that fixed-checkpoint comparison; use the sampler's frozen request contract.
