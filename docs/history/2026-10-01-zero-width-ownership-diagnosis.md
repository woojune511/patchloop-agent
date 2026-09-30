# Zero-width inverse ownership diagnosis

Complete provider-free diagnosis on the two saved Darts guidance-comparison
patches. No product patch, model call, task-check change or private evaluation.

## Question and controls

The [priority review](2026-10-01-failure-priority-review.md) selected silent
column loss after a zero-width categorical feature. Distinguish loss of decoder
information from loss of column ownership during Darts reconstruction. Use only
the existing ordinary drop=first control and frozen constant+variable case,
on fresh public-source copies with hash-verified A/B submitted patches.

The diagnostic inspects fitted implementation metadata from public source,
executes the fitted sklearn decoder directly, and compares its values with
Darts' full inverse output. No hidden test or reference patch was used. The
operator has access to public implementation internals; this is not an agent
probe-capability or fresh-solve result.

## Executed observations

Both patches produced identical results for these cases. The ordinary control
round-tripped correctly. For constant=['k','k','k','k'] and variable=['a','b','c','d']:

| Stage | Observed value |
| --- | --- |
| Forward map | constant: []; variable: [variable_b, variable_c, variable_d] |
| Inverse map | Each surviving variable_* column maps to variable; no constant entry |
| Encoder categories / dropped indices | [k], [a,b,c,d] / [0,0] |
| Direct encoder inverse | [[k,a], [k,b], [k,c], [k,d]] |
| Darts inverse columns | [variable] |
| Darts inverse values | [[k], [k], [k], [k]] |
| Decoder values named by forward-map keys | Exact original DataFrame restored |

The last assertion includes original order, values, index and column-axis name.
It demonstrates metadata sufficiency for this all-categorical case, not a general
repair for mixed numeric, untouched or entirely zero-width inputs.

## Mechanism and changed interpretation

In `_create_category_mappings`, omitting the dropped sole category leaves
`constant: []` in the forward map but creates no inverse-map entry. This is the
first omission from the inverse representation, not destruction of all fitted
information. `categories_` still retains k and the forward map retains original
column names and order.

`_transform_static_covs` successfully decodes both original columns. Its existing
width check compares three encoded input columns with three inverse-map keys;
that check passes but does not validate reconstructed ownership.

`_add_back_static_covs` iterates surviving encoded columns and the inverse map.
The first encountered name is variable; it consumes decoded column zero (k).
Later encoded columns repeat variable and are skipped. No iteration emits constant
or consumes decoded column one. This precisely explains the missing column and
wrong values without blaming sklearn or unavailable dependencies.

The earlier description of information loss is therefore narrowed: the inverse
representation loses ownership, while enough metadata remains elsewhere for the
selected input. A task-local correction should reconstruct against original
schema/order instead of inferring that schema solely from surviving encoded
columns. New persistent agent memory or another prompt reminder does not follow
from this finding.

## Diagnostic failure and evidence

The first diagnostic stopped on its ordinary control: the operator-created
DataFrame omitted the column-axis name static_covariates. This was an assertion
setup error, not a product failure. Confirmed cleanup permitted a separate v2
diagnostic with that metadata restored; v1 was preserved unchanged.

- Scripts: `C:\pt\darts-zero-width-investigate-20261001.py` and its `-v2.py` sibling.
- v1 root: `C:\pt\analyses\darts-zero-width-20261001-v1`;
  journal `runs\run_dev_3ce36990eac048a5.jsonl` (failed diagnostic retained).
- v2 root: `C:\pt\analyses\darts-zero-width-20261001-v2`;
  journal `runs\run_dev_ef300a18bfd2445b.jsonl` (six events verified).
- A patch: `sha256:d5e6681a111d3b012cf7cacfe747634e6c4e30b186028e4f4655523ed220007a`.
- B patch: `sha256:42983459343a910a7a04e567d57f36145e37de6e3175848570ee8b1b5ad7a6b8`.

Each journal binds the program and source/patch identities and full sandbox
receipts. Three container executions total, all with confirmed cleanup; the two
v2 executions succeeded. Existing pinned image, no network, read-only source/root.
No image acquisition, provider calls, original artifact changes or runtime changes.

## Decision and limits

The task-level defect mechanism is now established for the frozen case; another
reproduction or wording comparison is unnecessary. Keep this as a regression
example of an incomplete repair. The separate agent-level question remains why
verification omitted this boundary. Successful read receipts do not prove attention
or explain input selection. No claim of a general model improvement follows.

A later task-local repair would need to preserve mixed-column ordering and consider
the entirely zero-output path before being called complete. Such a repair is not
implemented here and should not be presented as an improvement to PatchLoop itself.
