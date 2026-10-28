# Required public checks

Task checks and explicitly host-registered public counterexamples use one effective
registry for status, `run_check`, repair recheck, resource forecasts and `finish_task`.
The original `PublicTask` and acquired original-call identity remain unchanged.
Model notes, plans, hypotheses and arbitrary helper output cannot register checks.

`RequiredPublicCheck` binds a registered definition to public program, interpretation,
environment and source-receipt identities. `public_checks_registered` freezes that
configuration in the run journal. Changing or removing it on recovery is rejected.
An existing complete failure on the current diff may be imported separately as
`public_check_imported`: it cites its observation identity and incurs no new action,
model call or execution charge. It is never fabricated as an `action_finished` event.

All required checks need PASS on the current diff. A known FAIL blocks successful
finish even with unused resources. An edit leaves missing checks NOT_RUN; a different
check's PASS, a prose assessment or a modified note cannot resolve the obligation.
The direct gateway enforces the same rule as the offered tool policy.

With repair-recheck enabled, a complete imported failure can select the same check
after an accepted edit, before the next model response. The child carries the prior
observation's identity/origin and uses ordinary `action_id + input_hash` recovery.
It spends one real tool action, not another model response. Current results and
definitions survive repair, diagnosis and completion context projections. Other
required checks still need their current receipts. Stop and resource-limit outcomes
retain unresolved check statuses rather than becoming successful completion.

Counts, output/cost reserves and nominal time use the effective registry. No extra
cap or retry is granted. Remaining budget chooses whether another repair/check is
possible; it never changes a FAIL or NOT_RUN into PASS.

The operator-assisted counterexample diagnostic registers its frozen public path
matrix through a prepared probe adapter. Host comparison of the 11 required cases
determines PASS, not the program's exit zero. The original baseline discrepancy is
excluded and reported separately. Incomplete output, changed environment and unknown
execution fail validation. Raw receipts remain artifacts, and bounded failures reach
the next model response. The former post-submission action/time reservation is removed;
the ordinary completion path now budgets each required execution, including check
timeout and standard overhead. Final reporting reads the current receipt without
executing the matrix again. Old sealed experiment manifests do not authorize this
changed diagnostic.
