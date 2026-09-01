# AnyIO public ordinary-failure preservation successor v5

This append-only successor preserves the AnyIO-v4 repository, issue, constraints, environment,
reference patch and hidden evaluator bytes. Public metadata advances to version 5 and adds the
independently qualified `public-ordinary-failure-preservation` check between the interrupt-specific
check and upstream regression. Private metadata changes only its task version.

The new check comes only from the public requirement to preserve normal pytest failures under a
shared async-generator fixture. Execution
`sha256:4269db56125f87e84e22a26299c9e2c58c55832e696f344068f6f09063544600` matched the local AnyIO
image and passed immutable base/reference trees. Base also passes, so this is a non-discriminating
regression guard, not evidence about the R14 hidden failure or a reference-derived solution.

This task version is not in the frozen dataset and creates no Rapid candidate, provider, evaluator,
paid or Docker authority. Any later runtime use requires its own source qualification and exact
candidate contract.
