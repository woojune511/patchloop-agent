# Limitations

- No authorized live row has validated the 30-minute target.
- The checked-in price registry currently supports only exact reviewed model IDs;
  an unknown model fails closed and requires a code change.
- Input counting and generation are two provider operations. A timeout after either
  boundary can make billing uncertain; the runtime stops instead of guessing.
- Docker policy records requested confinement and the preflight verifies a local
  digest. This is not a host-level attestation.
- Local mock evaluation uses fixture repositories and does not prove remote checkout,
  provider schema acceptance, model behavior, or production billing.
- The private evaluator currently records a literal safety PASS after constrained
  execution and static policies; therefore development results are not official
  claim evidence.
- Only recent bounded public evidence is projected. Long-horizon memory is disabled.
- Removing historical executables means old runs are not replayable from the current
  checkout without restoring Git history.
- A development PASS does not establish comparative quality, generalization,
  causality, or a memory benefit.
