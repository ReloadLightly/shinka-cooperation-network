# Fixed-fit forecast repeatability: GitHub execution

This is a measurement of forecast Monte Carlo variability conditional on the four
accepted Model 3 fits. It is not model fitting, model selection or an evolutionary
experiment. The frozen study uses development targets 2006–2009, offsets 101–105,
and 1,000 endpoints in each of 20 forecast batches.

## Completed measurement

**20/20 native forecast batches completed, with zero refits**, in GitHub Actions
run `35587860418`, using R 4.2.1 and RSiena 1.3.10. The sum of recorded native
forecast-stage times was **499.366 seconds (8.323 minutes)**; this is not total
setup, scoring or workflow wall time. The original fits and primary results are
unchanged. No candidate or evolutionary controller was launched.

| Metric (four-year average) | Mean of five fresh repetitions | Sample SD | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Overall PR-AUC | 0.922645998 | 0.001075374 | 0.921038956 | 0.923940088 |
| Brier | 0.004369965 | 0.000003595 | 0.004366027 | 0.004375172 |
| Spending RMSE | 0.391619896 | 0.000574493 | 0.391008501 | 0.392502364 |
| Formation PR-AUC | 0.023300652 | 0.000504128 | 0.022850642 | 0.024047392 |
| Dissolution PR-AUC | 0.044813174 | 0.005436338 | 0.039903246 | 0.050925197 |

| Target | SD: PR-AUC | SD: Brier | SD: spending RMSE | SD: formation PR-AUC | SD: dissolution PR-AUC |
|---:|---:|---:|---:|---:|---:|
| 2006 | 0.002750277 | 0.000006759 | 0.001131003 | 0.001097035 | 0.021627267 |
| 2007 | 0.002541011 | 0.000006017 | 0.001100060 | 0.001250824 | 0.001279947 |
| 2008 | 0.000766443 | 0.000008826 | 0.000886685 | 0.000820135 | 0.000836502 |
| 2009 | 0.003922615 | 0.000007993 | 0.001459477 | 0.000778365 | 0.001451448 |

The four-year PR-AUC averages range from 0.921038956 to 0.923940088 despite an
unchanged model and unchanged coefficients. Their sample SD is 0.001075374.
This measures a numerical scale against which small single-batch gains must be
interpreted; it does not establish the signal-to-noise ratio of an unevaluated
alternative specification. Dissolution ranking is notably variable in 2006
(SD 0.021627267); no objective or selection rule was changed in response.

Raw per-batch metrics: [batch_metrics.csv](batch_metrics.csv).
Unrounded summaries: [summary.json](summary.json).
Native execution: [execution.json](execution.json).
The per-year/per-offset directories retain endpoint simulations, predictions,
score artifacts, accepted-fit copies, coefficient audits and hash commitments.

## Input recovery

The eight development packets were recovered from the repository's source
archive and matched all pre-existing published SHA-256 hashes. A subsequent raw
reconstruction produced different past-packet hashes and was rejected. Its cause
was not established here, and no mismatching packet entered the study. The first
verified packet bundle is retained for exact restoration rather than relying on
another raw reconstruction. A local upload is not required.

The trusted preparation process deserialized the mixed-year replication archive,
then removed rows after 2009 before constructing packets. The forecasting and
scoring processes use only the separately verified development packets. No 2010
forecast, score, or finalist selection was performed. This is not a claim that
the mixed-year raw archive was never loaded.

## Guard repair

An initial attempt stopped before native simulation because an entirely empty
CSV interaction-name column was inferred as logical NA. The coefficient-checking
reader now explicitly preserves character columns. Its R regression reproduces
the old mismatch and verifies the fix; the coefficient equality test, fixed-fit
requirement and prohibition on estimation fallback remain intact. The same
predeclared seed was retained. The initial guard failure is not a model result.

## Interpretation

Sample standard deviations are computed across five fresh batches per year and
across the five complete four-year averages. The published +1 forecast is shown
as a fixed reference, not counted as a sixth replication. Differences from it
are same-model simulation differences, not candidate improvements. Five repeats
give only a rough estimate of variability, conditional on the specific accepted
fits; they do not measure refitting variation or historical generalization.

Every batch averages endpoints into probabilities before scoring. The mean of
five batch PR-AUCs is not the PR-AUC of pooled endpoint probabilities. There are
no altered convergence gates, new objective scales, additional candidates or
changes to the primary evolutionary fitness in this step.

## Verification and publication

All 20 batch commitments were independently checked from the downloaded native
artifacts. The summary was recomputed from the saved scores. Each accepted-fit
hash matches the pre-existing reference hash, and the five native coefficient
vectors are identical within each target year. The native call guards require
simulation-only execution, zero estimation subphases, all coefficients fixed and
1,000 returned endpoints.

The numerical measurement succeeded before an artifact-publication command failed
because the development bundle was ignored by Git. An explicit exception for that
one verified bundle repairs publication; the completed forecasts are restored
from the saved workflow artifact, not rerun. Earlier failed preparation/guard
attempts and the publication error remain separately recorded under
[prior-attempts](prior-attempts/).

The one-off research workflows are not installed as automatic main-branch
experiments. Step 3 (convergence-diagnostic precision) remains a separate task.
