# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-142 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d142-d141-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914`;
  file `sha256:83fa6e83a3b5827a07e3383f9dea6318b748813742b501a4aaf7b41c726a1e80`,
  16,298 bytes; blob `a2fcfcf97e8cdc1c7b8357b334211efab4b2dbf2`.
- Source commit `1370cf43c08cefb550b158a5d4172a60ac172470`, tree
  `7f7e7e25c79899eee6180ae45767492435003096`, sole parent
  `6405be40eb52d71fc9376065b553a04164543a4b`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-141 chain and qualifies only the future one-use SDK successor contract.
Fully injected/mocked focused tests passed 170/170 and are reported separately from other checks. No D-142
receipt, attempt, marker, terminal or preservation artifact exists; preparation performed zero membership/value
or `.env` observation, credential mutation/provisioning, child launch, SDK inspection, endpoint/network or Docker
action.

## D-141 SDK no-call successor — BLOCKED and consumed

- Gate `reports/live-pilot/artifacts/d141-d140-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d141_51e825a474cc957f6fa20dea9ec5332c9b0defd7569dfe6f063f57f195636aab`; file
  `sha256:cc8de60111294a79ed5f29b24263d7e7fe303a8f9c0dd5c78858e63bc3caa642`, 16,056 bytes;
  blob `db596c40161e6cdf194e73ecff5f9afe1baa320f`; evidence commit
  `9b9ce197daa34db355274956fd5043ab3a0b3539`.
- Source commit `0ffe586760659542d7ecf7c94698a2f1e109e6b0`, tree
  `41d14e4d9778e52834e4e6636f1bcd35ce148876`, sole parent
  `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`; its diff is exactly four added paths.
- Receipt `reports/live-pilot/artifacts/d141-sdk-no-call-successor-activation-receipt.json`: ID/body
  `d141approval_e4f5bfc2324eb75194a84f45d42269910bc487101d7cd7b629289e60b7416c71`; file
  `sha256:77882d12949840b0768b445ec955e5bafb4da30d2929057c7ece230b7ab65711`, 9,720 bytes;
  blob `011fb464bf1a4102ddb2d440cd4506b1fff6267c`; commit
  `10fd04fb3528b4a059618e057ffb1b997cb66603`.
- Attempt `reports/live-pilot/artifacts/d141-sdk-no-call-successor-attempt-intent.json`: ID/body
  `d141sdkattempt_5df0f4f15f3e98deebbb77d59ace047102f2da75ef1378875311d1a6be66e588`; file
  `sha256:3ba4fad4a3a9d8690c0baeca00b8eaa1e3c8f97af43e99c7df6a310f49a9a32e`, 5,698 bytes;
  blob `1abe928d09e9f8c3a4d6a77d087385816c2262fe`; commit
  `d05af7f727517eaf36d37a80dab1a5735762ae75`.
- ACTION_STARTED `reports/live-pilot/artifacts/d141-sdk-no-call-successor-action-started.json`: ID/body
  `d141sdkstarted_549d1631211c3dfeb440989e9377cf6d697125eafd0309d68fe092f66ba61b57`; file
  `sha256:d41ec6aacb5f31de3df40fe2a405f35e56590ef7aa8971fee923f47663af4116`, 5,679 bytes;
  blob `c2dce1dc0c37e6af50a6cdf5c822b93a1fc28737`.
- BLOCKED terminal `reports/live-pilot/artifacts/d141-sdk-no-call-successor-terminal.json`: ID/body
  `d141sdk_c96ceb8eb274560b89e3688402a0c3576d6f09536c32d611600ac1386d4613ef`; file
  `sha256:38121d8498578cd495ec94a2ca4da47bdebfc87f358540892cff09c297793bcb`, 8,962 bytes;
  blob `809f513ec9a961bf998b822df08b5fd3e890dcda`.
- Exact STARTED+terminal commit `6405be40eb52d71fc9376065b553a04164543a4b`, tree
  `673f9dc639f1a9002d6aae63b99218141ebf7793`, sole parent
  `d05af7f727517eaf36d37a80dab1a5735762ae75`.

The terminal recorded the key and routing bits as false/false/false at the presence stage after three membership
checks. Credential/environment value and `.env` reads, child launch, SDK import/probe, transport/network and
provider/evaluator/agent calls were 0. D-141 is consumed and cannot be retried, resumed, repaired or backfilled.

## Earlier consumed evidence — compact index

- D-137 Docker transition `06e57c54b4fe09f3145b8b59e51a0e391108d52a` is READY after eight read-only
  commands and zero mutation. SDK transition `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` is BLOCKED after three
  membership checks found the key absent; value/`.env`/import/probe/dispatch/network counts were 0.
- D-138 SDK transition `9f31d330190aa83768077b17c3cde47eb86c639d` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-139 SDK transition `ba3af19a5cada8e49c29f514ad56c299639dc452` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-140 SDK transition `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2` is BLOCKED after false/false/false
  presence bits and three checks; value/`.env`/child/import/probe/dispatch/network/provider counts were 0.
- D-136 success commit `2378569536c2367a3186f575a7517e3de7282336` preserves one official public GET,
  HTTP 200, zero redirects and 3,735 replay bytes with provider/evaluator/agent and cost counts 0.
- D-132 has no canonical response evidence. D-133 marker commit
  `a10033b6abd7155ebaa5c66c13627ad3ea738566`, invalid D-134 gate commit
  `9dc450a747537634e89fe2ade824685f8b5a52d6` and D-135 procedural terminal commit
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786` preserve that consumed incident without reconstruction.
- D-129 remains terminal sequence-blocked; D-121 is deferred. Exact older artifacts and tuples remain in
  `reports/`, the archived ledger and Git history. None may be retried, resumed, repaired or backfilled.

## Next evidence boundary

Obtain a fresh exact D-142 activation quoting gate, source and evidence-commit tuples. It may create only a
receipt commit, then an SDK-attempt commit. The exact parent writes/fsyncs its marker before membership-only
checks; eligible SDK work runs only in the bounded `env={}` child with fixed placeholder, no ambient forwarding
and zero dispatch. Pre-bootstrap network absence is not claimed, and credential provisioning is a separate action
authorized by neither preparation nor activation; no credential value belongs in approval/chat. Commit
READY/BLOCKED terminal or, after failure, marker only; never retry. Any terminal requires a D-143 offline
successor and grants no provider/evaluator/agent, memory/retrieval, hash/candidate, cost or A/C authority.
