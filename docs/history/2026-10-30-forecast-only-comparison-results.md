# Forecast-only comparison: no repair, contrasting public diagnoses

Date: 2026-10-30 KST. Status: **CLOSED**. Both authorized branches completed;
all new provider usage is settled at **USD0.5311435** of the USD6.636999 cap.
Unused allowance does not authorize another run. No repetitions or extensions.

## Question, controls and execution

The [frozen plan](2026-10-30-forecast-only-comparison-plan.md) asked whether an
action-specific budget forecast preserves the edit/check/finish route at a
public failure boundary. The user confirmed Astroid dev-train row13,
`gpt-5.4-2026-03-05`/xhigh, repository `.env`, OFF/ON once each, and the exact new
row/group caps. Both branches restored the same B cut258 and naturally selected
source; no operator repair or additional source was injected.

Execution HEAD: `cf9ed68e1868a6f609e69cbbe40a40b83369bc03`.
Agent runtime: `sha256:45e1bfe96a20897102c6903cc14a19e261f82bb5d4a0887a8f63e579707acb7c`.
Manifest: `C:/pt/forecast-live-preparation-20261030-v2/manifest.json`,
`sha256:b5e65b220bbd11913acaf0f934da24435be418f8fb838ea0da7f475786227704`.
External launcher: `sha256:25cccdb38288517562f504cb384fe6256164fd49d911236173fb1fc2aa336061`.
The narrow continuation-error stop guard passed five synthetic controls before
execution; the agent runtime was unchanged. Older prepared manifests were not used.

An independent audit of the actual first paid requests verified:

- Prepared, freshly counted and dispatched request identities match in each arm.
- After the declared elapsed-time normalization, only
  `action_horizon.action_budget` differs. Actual solver-time displays differ by one second.
- Both requests contain the same current `astroid/modutils.py:261–470` helper
  source and exclude the operator's proposed replacement.
- Initial token counts are OFF25,289 and ON25,528, a 239-token forecast difference.

Request audit: `C:/pt/forecast-live-request-audit-20261030-v1/runs/run_dev_forecastliveinputaudit.jsonl`;
report `sha256:a0b53a5c662960d3a14500c8aab56c1d4b03fe9f91bc5ec146ba0bda6bfaf48f`.
Actual first request hashes are OFF
`sha256:8fc3c950fbf1e54d76e7cd9bf983871117bc5ceeae55e3d063becd8a3dcbfc3d`
and ON `sha256:8d3c7b57b2e23769e39cdacbf73446478d16d500cff9dd53490edbfb77715739`.

## Observed outcomes

| Outcome | OFF1 | ON1 |
|---|---|---|
| First action | run_probe | run_probe |
| Next action | finish_task | stop_task |
| New accepted mutations | 0 | 0 |
| New public checks | 0 | 0 |
| Current required public check | Inherited PASS on unchanged diff | Inherited PASS on unchanged diff |
| Submitted | Same inherited patch | No submission |
| Independent task acceptance | FAIL | NOT_RUN |
| Independent safety | PASS | NOT_RUN |
| New counts / model dispatches | 2 / 2 | 2 / 2 |
| New API cost | USD0.260345 | USD0.2707985 |
| Fork receipt to terminal | 128.366 seconds | 167.155 seconds |
| Provider dispatch-to-return time | 85.505 seconds | 147.540 seconds |

Both retain the same candidate:
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.
Terminal `accepted_mutations=1` includes the inherited edit; it is not a new repair.
The public-check PASS is still valid regression evidence for that unchanged diff,
but does not establish that the reported failure was repaired.

OFF's probe `call_lkuEkoOwNRJ1RCDeglEiyGyI` changes the temporary fixture's import
search path by adding its absolute root. It observes no F0010 and W0611 on file.py,
then submits the saved patch. Its assessment mentions missing baseline verification
but treats the reported failure as absent on the patch. This conclusion does not
preserve the public caller's conditions.

ON's probe `call_PjKTk9FN2kXhXIrqT6DOEH6Y` instead observes F0010, a missing
initializer reference and no file.py processing. It stops with
`no_safe_scoped_mutation`, accurately reporting that the patch still fails and
mutation tools are no longer offered. Both arms used the optional probe despite
the three-ordinary-call edit/check/finish route; after it, only two ordinary calls
remain. This describes choices and availability, not internal model motives.

The arms' probe programs differ beyond import paths, so their contrasting
observations alone cannot identify the cause. Independent acceptance is reported
separately and was not used to construct model input or the public diagnosis.

## Controlled public follow-up

After both live branches ended, two bounded public-sandbox dispatches reused
the exact OFF program and candidate. The second removed only
`sys.path.insert(0, str(root))`; no source patch or model call was added.

| Condition | Directory F0010 | Directory file.py W0611 | Direct-file control |
|---|---|---|---|
| OFF program with absolute root | Absent | Present | No F0010, W0611 present |
| Only that insertion removed | Present | Absent | No F0010, W0611 present |

The paired calls retain the same cwd, argv, arguments, input hash, environment,
snapshot and sandbox profile. Captured sys.path differs by the one inserted root;
the removal arm has no absolute fixture cwd, empty-string or dot entry. Original
workspace/source hashes remain unchanged. These are four pylint calls in two
operator probe dispatches, with zero additional model calls.

Thus, under this public fixture, OFF's apparent success depends on the altered
search path. It is not evidence of source repair. The direct-file control remains
working while the issue's directory invocation fails.

Journal: `C:/pt/forecast-public-path-control-20261030-v2/runs/run_dev_forecastpublicpathcontrol.jsonl`;
report `sha256:48cc68ca0bbffe64346cb5e9aa55d50eae6ea1bca4ab84bfd079ba847b386ba4`.
The v1 preparation error, a missing purpose wire adapter, is retained separately
with zero target dispatches; v2 uses the existing registered selection adapter.

## Decision and remaining question

The forecast did not preserve a repair route or produce a repair in this pair.
ON's more accurate diagnosis and refusal to submit are observed differences;
one stochastic pair cannot attribute them to the forecast. Neither general gain
nor universal ineffectiveness is established. Timings differ in output length,
cache use and terminal work, so they do not establish a speed effect.

Keep the accurate resource description and repaired source-delivery contract.
Do not add another prompt, gate or quota change from this result. The actionable
correctness issue is preservation of public reproduction conditions: a successful
helper invocation can hide the reported failure by changing import resolution.
ON demonstrates that the existing public tools can reproduce the failure; no
new execution capability is shown necessary. A next intervention needs a focused
reason to improve this condition fidelity, not more available budget.

The selected 12-edit default, file operations and bounded notes remain unchanged.
This checkpoint comparison does not measure their fresh-solve effect. Full-suite
completion, broader repair improvement and held-out generalization remain unverified.
The runtime's previous frozen 1,101-test quick PASS and Ruff result still apply;
this turn changed no agent runtime code. Documentation/link checks were rerun.
Final documentation tests: 6 passed in 0.18 seconds. HTML static validation:
51 unique IDs, 58 valid links, unchanged JavaScript with Node syntax PASS; visual
browser QA NOT_RUN. Group, both branch and public-control journal chains validate.
The runtime hash remains fixed and no running Docker container remained after
the completed comparison and public controls.

## Durable result

- Run root: `C:/pt/forecast-live-20261030-v1`.
- Result JSON hash: `sha256:e915f6092b80751d3b802f318e982cc7388307f312f8083cda3a8dc92475d48a`.
- Group journal: `runs/run_dev_forecastlivecomparison.jsonl`; final accounting
  follow-up hash `sha256:61c08cad900712614e219f87df7fd5ba1f221b1d2d423d7130981dd56c8dacd0`.
- OFF journal final hash: `sha256:820965e27ce398b56c838dc2f2bcf9adcf815b4b83cec8ec21ce88df14055614`.
- ON journal final hash: `sha256:a2bfa4754e6d5806327f69b41437c797bb2bf49f988a52b3bb9cc544489b09a7`.
- All new API usage settled. The allocation is closed, with no automatic retry,
  resume, extra repetition or new paid experiment authorized.
