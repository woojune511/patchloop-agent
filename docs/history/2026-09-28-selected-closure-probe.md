# Independent review and execution of the selected closure probe

Date: 2026-09-28. `official=false`; provider-free operator diagnostic.
Follows [response comparison](2026-09-28-closure-policy-results.md). That comparison
executed no tools; the execution below is a separate follow-up, not a rewritten
solver trajectory or a new A/B outcome.

## Expectation and scope

B2 selected `rho = diag(0.5, 0.25, 0, 0.25)`, dimensions 2x2 and alpha=2.
The A-major basis gives joint distribution [[0.5, 0.25], [0, 0.25]] and B marginal
(0.5, 0.5). The state is mixed, correlated and fully classical. It reaches the
generic optimizer after shortcut removal, rather than the pure/product fallbacks.

For a diagonal reference on B with probabilities (q, 1-q), the alpha=2 objective
inside the logarithm is f(q)=1/(4q)+1/(8(1-q)). Its unique minimum has
q=sqrt(1/4)/(sqrt(1/4)+sqrt(1/8))=0.585786437626905. Hence:

- uparrow = -log2(min f) = 0.4568933936727761 bits;
- downarrow = -log2(f(1/2)) = 0.4150374992788438 bits;
- gap = 0.04185589439393228 bits.

This scalar calculation and a 99,999-point grid independently agree. Reduction to
diagonal references is justified by dephasing B: the state is unchanged and the
sandwiched divergence cannot increase under that channel at alpha=2. See
[data processing, Theorem 6](https://arxiv.org/html/1306.3142v4).
The classical Arimoto expression matches
[Definition 1, Eq. (5)](https://arxiv.org/html/2007.05049v2).
These citations and the reduction apply to this commuting example; they do not
validate a closed form for arbitrary noncommuting CQ states. In particular, the
second paper's general quantum expression is Petz-based, not an interchangeable
formula for the sandwiched task.

The selected probe's executable expectation is correct for this input. Its prose
says approximately 0.456009, an error of -0.0008843937 bits, but that number is not
used by its assertions. The assertion computes the correct formula. The simple
uparrow>=downarrow assertion alone is weak because the patch clamps with `max`;
the independent exact expectation adds discrimination. This example would not
expose the former shortcut's noncommuting error, since its formula agrees here.

## Exact selected probe execution

The unmodified model-authored program ran once in the existing prepared Python
3.12 DockerProbeSandbox, with no network, read-only candidate/dependency mounts,
and no image pull/build/startup. The candidate was cloned from the prepared base
and received the exact frozen final patch. Patch bytes verified before and after.

Setup checks passed. Downarrow returned 0.41503749927884404. Uparrow raised TypeError
at line 174 of `sandwiched_renyi_conditional_entropy.py`, during the optimizer's
objective call: `float(np.real_if_close(trace_term))`. It never reached the final
numeric assertions. Thus the failure does not depend on the prose typo or a
disputed expected-value tolerance. It is the same remaining objective-conversion
location identified in the prior independent public audit, now reached by a case
the model itself selected without receiving that operator case.

The probe exited 1; timed_out=false, deadline_exhausted=false, cleanup_failed=false,
cleanup_status=confirmed. No candidate repair or private evaluation occurred, and
this result was not delivered to the solver. Provider calls and new spending: zero.

## Evidence and next question

- `C:/pt/analyses/selected-closure-probe-20260928-v1/result.json`, journal
  `run_dev_selectedclosureprobe`, binds the selected sample, program, arithmetic,
  environment, patch, execution identity and receipt.
- Script: `C:/pt/review_selected_closure_probe_0928.py`.
- Program: `sha256:36c28444dfbf8540f043a4743f9b49ca9fc3b5c78940f85cf6f4615eb596f319`.
- Patch: `sha256:003d549bab52d602d4efb2c0c80b7002c4ab587da5c3fb086ea1a2977351bb50`.

The proposed probe is useful: it exposes a real current-patch failure. This advances
evidence from action selection to failure detection, not to repair or acceptance.
It does not cover the pure-state near-0.5 defect, establish generic optimizer
correctness, identify private failures or justify default policy adoption.
Next consider a bounded continuation from B2's actual response through ordinary
probe-result delivery, repair and same-case recheck. That needs separately prepared
continuation state and fresh paid approval; no further provider call is authorized.
