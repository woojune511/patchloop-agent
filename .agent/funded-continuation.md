# Separately funded interrupted-state continuation

`diagnostics/funded_continuation.py` supports an explicit new allocation after a
closed interrupted batch. It is not ordinary `--resume`, a fresh solve, or authority
to reopen historical funds. Normal resume still requires the exact old envelope.
The external launcher binds exact tasks, parent hashes, new caps, cumulative limits,
credential path, model, implementation and first reconstructed requests before
obtaining new paid authorization. It uses the existing parallel admission lock.

The selected parent must be unevaluated. The last prepared input follows completed
public actions. No received generation, action or submission after that boundary
may be discarded. All counts must be settled. A single lost generation may be
excluded from the new branch only as an explicit recorded UNKNOWN parent tail;
its call/request identity and conservative reservation remain bound to the entire
immutable parent journal. It is not retransmitted, fabricated as zero usage, or
reclassified as a success. The next generation is a newly funded decision from
the confirmed state. New uncertainty still stops all new admissions in that batch.

Restoration verifies exact file transaction pre/post bytes and diff identity,
preserves successful `replace_text`/`edit_files` effects and ignores rejected edits.
Public observations, plans, notes and opaque native continuation stay within the
settled prefix. No operator diagnosis or private evaluator output is appended.

An opt-in larger total wall limit creates a new envelope. Full-parent consumed
active time is retained, including time after the cut. Excluded generation attempts
consume model slots: a parent with 27 attempts/26 receipts under a 40-call limit
has a child limit of 39 and 26 inherited calls, leaving 13. Report the separate
historical excluded call alongside child counts when reporting cumulative use.
Actions, edits, evaluation reserve and all other policies stay unchanged, including
`rate_limit_policy`. The current operator panel freezes a 3,600-second total limit.

Each row reserves only its new allowance from the new batch. Its internal ledger
retains settled parent usage, but that history is subtracted from new settlements;
unsettled usage remains unknown. The outer manifest hash is checked again inside
each worker before restoration. Each state root and allocation is single-use.

Offline rehearsal uses a finite scripted client and an inert managed transport;
it cannot construct the real HTTP client, execute remote mutations/checks, or
submit. A separate mocked transport test exercises actual 429 policy wiring.
Preparation checks establish restoration/accounting, not autonomous repair gain.
