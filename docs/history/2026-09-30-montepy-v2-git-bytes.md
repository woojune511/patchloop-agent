# MontePy v2 Git byte preservation

The first Linux CI for v2 (`36691405803`, head `e6259b79`) failed one test:
the copied evaluator asset's raw-byte hash did not match its declaration after
checkout. Other tests: 3,732 passed, 25 skipped. The local Windows task validation
had passed because its copied working files still held the original CRLF bytes.

The root cause was a missing `.gitattributes` exception for the new package path.
The three original pilot packages already disable Git text conversion because
their evaluator inventories bind raw bytes. The v2 path inherited the general
JSON/YAML LF conversion instead. This changed bytes while staging, not evaluator
meaning or the test's integer arithmetic.

Added the same `-text whitespace=cr-at-eol` rule for v2 and restaged its existing
working bytes. No original package, inventory digest or evaluator content was
changed. A regression test now compares Git-filtered and raw object hashes for
every declared v2 hidden asset. Local focused/package/documentation checks:
17 passed; Ruff and diff whitespace checks passed.

An independent export of the staged package validates and exactly matches the
previously calibrated package hash:
`sha256:e744e37bbef0a478328d5eb0b2e71bfa693ec17bf44a332cd1d7246f1c637b0b`.
Receipt: `C:\pt\analyses\montepy-v2-git-bytes-20260930-v1`, append-only journal
`run_dev_montepygitbytes`. Thus the earlier Docker calibration remains applicable
to the preserved bytes; it is not a rerun or a new agent-performance result.
Cross-platform CI on the corrected commit remains the merge gate.
