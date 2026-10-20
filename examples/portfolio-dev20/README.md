# Frozen dev20 measurement

Saved results, not a live demo or an executable authorization. The current runtime
resolved **9/20**, versus historical **10/20**, on the same development-exposed
roster. Both registered and pinned native evaluations completed and agreed for all
twenty original submissions. No task was retried or replaced.

- [Results](results.json): ordered task outcomes, original patch hashes, exact
  base/task/image identities, public-check receipt summaries, costs and timing.
- [Provenance](provenance.json): source hashes and export transformations.
- [File hashes](files.sha256.json): integrity inventory for this saved export.
- [Measurement record](../../docs/history/2026-10-06-portfolio-dev20-results.md):
  execution configuration, full result table and local original-artifact locations.
- [Public repair example](../saved-repair/README.md): inspectable request, original
  patch and verifier JSON; this is a separate closed usage example.

The model was `gpt-5.4-mini-2026-03-17`, xhigh, desired output limit 25,000,
40 calls / 100 actions / 4 edits / 1,800 seconds per task. Maximum spend was
USD 1.20 per task / 24 total; recorded spend was **USD 3.46111455**.
The panel took 6,138.868835 seconds. Solver invocation time (5,587.366 seconds)
includes registered evaluation; native evaluation added 466.989 seconds.
The remaining wall time includes between-row identity checks and orchestration.

PASS->PASS: 9; FAIL->PASS: 0; PASS->FAIL: 1 (pvlib #1707); FAIL->FAIL: 10.
All twenty submitted patches passed the configured public check on that diff;
only nine passed independent acceptance. Public check success is not acceptance.
No non-submissions, evaluation errors, unexecuted tasks or unknown billing remain.

Eight historical environment corrections and two public-check projections remain
part of this panel's construction. SQLFluff-1625 uses a byte-exact copy of its old
registered package. Runtime behavior is current; this is not a paired rerun of the
old runtime and does not isolate a feature's effect. The 11/20 expenditure threshold
was not met: test300 was not prepared or executed. These are self-evaluated dev
results, not a Lite test score, leaderboard entry or training-non-exposure claim.

To verify the saved export locally (no model calls or evaluation):

```powershell
python -c "import hashlib,json,pathlib; p=pathlib.Path('examples/portfolio-dev20'); m=json.loads((p/'files.sha256.json').read_text()); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in m.items()); print('hashes match')"
```

The closed state must not be rerun. A new measurement would require a new approved
scope and fresh state using `diagnostics.portfolio_dev20`; its preparation depends
on the separately preserved local task/source/image inputs. This export contains
receipt summaries, not a self-contained reconstruction of those environments.
Original patches and raw public logs remain in the external evidence root; their
hashes here permit exact comparison without exposing provider state or private
evaluation material. No human patch approval is inferred from benchmark acceptance.
