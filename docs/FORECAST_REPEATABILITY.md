# Step 2: fixed-fit forecast repeatability

## Status — completed

**All 20 native forecast batches completed with zero refits**, using R 4.2.1 /
RSiena 1.3.10 in GitHub Actions run `35587860418`. The four-year average PR-AUC
has fresh-batch sample SD **0.001075374**, across five prespecified repetitions.
The full [measurement report](../results/diagnostics/forecast-repeatability-v1/REPORT.md),
[unrounded summary](../results/diagnostics/forecast-repeatability-v1/summary.json)
and per-batch native artifacts are retained. This is conditional forecast Monte
Carlo variability, not a measured candidate SNR or an evolutionary improvement.

The earlier [availability record](../results/diagnostics/forecast-repeatability-v1/availability.json)
is preserved as historical evidence of the missing-input checkpoint, not current
status. The exact eight development packets were subsequently recovered from
GitHub and verified against all pre-existing published SHA-256 hashes. The
verified bundle is now stored at `sources/archive/step2-development-inputs.zip`;
no manual WSL-to-Windows upload is needed.

The trusted recovery process did deserialize the mixed-year raw archive, then
removed rows after 2009 before constructing packets. No 2010 forecast or score
was produced, and no 2010 result was used for model selection. A subsequent raw
reconstruction failed the past-packet byte hashes and was rejected; its cause
was not established. The successful first bundle was reused without relaxing
checks. Standard restoration now uses that development-only bundle and does not
open the raw archive.

An initial forecast attempt failed before simulation because CSV type inference
turned empty interaction-name fields into logical NA. The diagnostic reader now
preserves those fields as character strings; an R regression reproduces the old
failure and verifies the repair. All coefficient equality checks remain intact.

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

Restore exactly the eight verified packets from the repository bundle:

```bash
python3 scripts/recover_repeatability_inputs.py --execute
```

Restoration validates every member before writing, rejects unexpected paths or
hash mismatches, and never overwrites conflicting local inputs. It starts no R
process and performs no fitting, forecasting or scoring. The optional
`--from-raw` route preserves the historical trusted-preparation implementation;
it is not the routine restoration path and does not promise byte-identical
reconstruction on another host. Existing recovery records are never overwritten.

Export from a checkout with verified packets remains available, but is no longer
required for this handoff:

```bash
python3 scripts/forecast_repeatability.py export-inputs --output /tmp/step2-inputs.zip
```

The existing runner remains available. With the published completed artifacts,
it verifies and reuses all 20 batches; it does not start new forecasts. Native R
is needed only when running a separately authorized incomplete study:

```bash
# For an incomplete, separately authorized study: admit at most one new batch.
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
research observations. The R `--guard-self-test` checks call guards without
simulation. Native execution is now documented by the 20 completed batch
artifacts, separately from the synthetic regression cases. The publication verification restores real
inputs and checks all completed commitments and coefficient vectors from a fresh
checkout without installing the native runtime or rerunning forecasts.

The only changed R file is the diagnostic wrapper, not the original model or
scorer. Existing estimator, evaluator, primary results and campaign contracts
are unchanged; the diagnostic does not
rebind an existing evolutionary database.

The [fresh-checkout publication verification](../results/diagnostics/forecast-repeatability-v1/publication_verification.json)
records 101 passing Python tests, restoration of all eight real packets and
verification of all twenty completed native batches without new simulation.
