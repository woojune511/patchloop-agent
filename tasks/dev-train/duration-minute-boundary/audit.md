# Task audit: duration-minute-boundary

- Split: `dev-train`
- Failure pattern: rounding at a bucket boundary instead of counting completed units
- Expected source change: `mini_data_utils/timefmt.py`
- Base visible behavior: sub-minute seconds, exact minute boundaries and negative input remain valid
- Private acceptance: values immediately inside and near the end of minute buckets
- Leakage control: hidden values and reference patch are evaluator-only and must not enter memory text
- Independence rule: held-out tasks may reuse the boundary-checking pattern, but not this API or fix

Admission requires the no-op baseline to pass visible checks and fail hidden acceptance, the reference
patch to pass SCRR, and every known-bad patch to fail its predeclared boundary.
