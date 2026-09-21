# Step 2: fixed-fit forecast repeatability

## Status

The bounded diagnostic is implemented. **No empirical repeatability estimate has
yet been produced.** A fresh published checkout contains all four accepted fits
and primary forecasts, but not the eight development-only `data/past` and
`data/targets` packets. Those directories are intentionally excluded from Git.
The input checker reports their exact expected hashes from the published
prediction/scoring provenance. Missing packets are an input-availability issue,
not a failed fit or evidence about the signal-to-noise ratio.

A pinned R 4.2.1 / RSiena 1.3.10 environment was installed in a branch-only GitHub
Actions job, and the saved native objects were inspected. The saved forecasts
contain unpacked forward-state objects, but those objects are not a substitute
for the original outcome packets required by the trusted scorer. The raw mixed-
year replication archive was **not opened** to regenerate packets. No 2010
outcomes, reference refits, candidate proposals or finalist selection are needed.

## Frozen bounded design

`configs/forecast-repeatability-v1.json` specifies targets 2006–2009 and five fresh
batches per target, with seeds `target * 1000 + offset` for offsets **101–105**.
These seeds are distinct from the original +1 forecast and the finalist reporting
+2 through +6 repetitions. Every batch contains exactly **1,000 native endpoints**.
There are **20 planned fresh batches**, not twenty fitted models. The default
invocation admits new work for at most one hour, then finishes the admitted batch
and pauses. A forecast has a 900-second process timeout; scoring has 300 seconds.
A smaller `--max-new-batches` bound permits stepwise execution.

The diagnostic repeats **the published reference's legacy native forecast path**
(`R/forecast.R`), using the same accepted fit, original observations and forecast
semantics. It does not claim to validate the expanded schema-v2 native adapter.
`R/forecast_repeatability.R` disables the estimation fallback, rejects missing
fits, guards the native call (`simOnly`, `nsub=0`, all included coefficients fixed),
checks its coefficients against the published forward-effect table and verifies
that the returned coefficients did not move. Accepted-fit bytes remain unchanged.
No convergence threshold, estimator setting or primary fitness is altered.

Each prediction is committed before its corresponding development outcome packet
is scored by the existing pinned PRROC scorer. Common dyad masks and spending
counts are checked. Completed batches have hash commitments and resume without
new calls. Missing/altered committed predictions cause refusal. An incomplete
started batch is retained and requires explicit review; no automatic replacement
seed, unbounded retry or fabricated result is permitted.

## Measurement and interpretation

For each year, report fresh-batch mean, sample standard deviation, minimum,
maximum and range for overall PR-AUC, Brier, spending RMSE, formation PR-AUC and
dissolution PR-AUC. For each seed offset, also average metrics over the four
years; report the variability of those five four-year means. Incomplete studies
remain explicitly partial; only complete four-year groups enter aggregate results.

The original published forecast is a fixed comparator, not one of the five fresh
replications. Signed same-model differences use the existing objective directions
but are **not evolutionary fitness or improvements**. The new artifact has no
`combined_score`, no successful-candidate record and no population admission.

Endpoints are averaged **before** calculating each batch's curve. A mean of five
batch PR-AUCs is not the PR-AUC of pooled endpoint probabilities. This initial
study estimates conditional forecast Monte Carlo variability at fixed accepted
coefficients. Five replications give a rough SD estimate, not a precise variance
characterization. It does not estimate fitting randomness, historical sampling
uncertainty, model-selection performance, generalization or a candidate SNR.
It must not be used to declare Shinka viable or futile without a changed-model
comparison. The study does not invoke `finalist_set.py` or close/freeze a campaign.

## Commands

Read-only availability/provenance check (exit 2 when packets are missing):

```bash
python3 scripts/forecast_repeatability.py check
```

On the existing local checkout with the original packets, export exactly the
eight permitted inputs. This command checks their hashes and never includes the
raw archive, 2010 packets, fitted models, credentials or runtime files:

```bash
python3 scripts/forecast_repeatability.py export-inputs --output /tmp/step2-inputs.zip
```

With the required packets and pinned native environment available:

```bash
# One bounded batch, then exit 75 with a resumable diagnostic checkpoint.
python3 scripts/forecast_repeatability.py run --execute --max-new-batches 1

# Complete the same finite study; completed batches are verified and reused.
python3 scripts/forecast_repeatability.py run --execute
```

Outputs are confined to `results/diagnostics/forecast-repeatability-v1/`.
Exporting packets does not run any forecasts. `run` without `--execute` is a dry
run. Do not regenerate all-year data with `R/audit_data.R` as part of this step.

## Verification scope

The new Python regression cases cover missing/changed inputs, exact eight-file
export, no reserved-packet reads, finite batches, prediction commitments, no-fit
fallback, failure preservation, bounded pause/resumption and summary arithmetic.
Workflow fixtures use synthetic bytes and a mocked native worker; they are not
research observations. `environment/run-r R/forecast_repeatability.R
--guard-self-test` checks the R call guards without simulation. Native forecast
execution and empirical variability remain unmeasured until the original
permitted packets are supplied.

Only new diagnostic code/configuration is added. Existing estimator, evaluator,
primary results and campaign contracts are unchanged; the diagnostic does not
rebind an existing evolutionary database.
