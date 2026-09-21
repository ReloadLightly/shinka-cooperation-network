# Step 4: one closure-specification comparison

Status: **complete**.

Reference: degPlus(1) + transTriads(0). Candidate: degPlus(1) + gwesp(69).
All original empirical controls and spending-equation structure retained; coefficients jointly estimated.
No Shinka proposals, decay search, reserved-year scores, or fit-seed replications.

| Metric (positive = candidate better) | Pooled 5,000 point | Approx. conditional MC interval |
|---|---:|---|
| pr_auc | -0.002670775 | [-0.005540049, 0.000198498] |
| brier | 0.000011270 | [0.000004590, 0.000017950] |
| spending_rmse | -0.000217121 | [-0.001393107, 0.000958864] |
| formation_pr_auc | -0.000986084 | [-0.002185112, 0.000212944] |
| dissolution_pr_auc | -0.006519415 | [-0.026995588, 0.013956759] |

The interval is a five-block jackknife approximation with t(4) scaling. It is fragile for PR-AUC ties and does not include fitting or historical sampling uncertainty. The independently repeated 1,000-endpoint contrasts are retained separately, not mistaken for pooled-endpoint scores.

This is a development comparison motivated in part by already inspected 2007 forecast misfit, not untouched confirmatory evidence. A favorable result does not prove a causal mechanism or a Shinka advantage; an unfavorable result does not invalidate the entire search grammar.
