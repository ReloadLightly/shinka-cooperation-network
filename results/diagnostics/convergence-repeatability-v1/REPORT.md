# Step 3C: fixed-coefficient convergence repeatability

Status: **complete**. 9/9 new cells, plus the verified prior pilot. Zero refits or forecasts.

| Vector | Seed | Origin | max t: first 1000 | Overall: first 1000 | max t: all 3000 | Overall: all 3000 | Native valid |
|---|---:|---|---:|---:|---:|---:|---|
| attempt3 | 2009301 | reused pilot | 0.094229644 | 0.262082693 | 0.050915035 | 0.190819383 | True |
| attempt3 | 2009302 | new | 0.089690304 | 0.314649482 | 0.061539534 | 0.232484349 | True |
| attempt3 | 2009303 | new | 0.080374237 | 0.253379754 | 0.065415772 | 0.183766839 | True |
| attempt3 | 2009304 | new | 0.085431942 | 0.271836926 | 0.058876144 | 0.195148990 | True |
| attempt3 | 2009305 | new | 0.086252517 | 0.285003758 | 0.060945347 | 0.203812177 | True |
| attempt4 | 2009401 | new | 0.078654264 | 0.268093654 | 0.046468724 | 0.154661521 | True |
| attempt4 | 2009402 | new | 0.080443533 | 0.282949703 | 0.061573792 | 0.154774210 | True |
| attempt4 | 2009403 | new | 0.057986949 | 0.255834376 | 0.042639483 | 0.152855787 | True |
| attempt4 | 2009404 | new | 0.112250822 | 0.256447320 | 0.045648578 | 0.143698508 | True |
| attempt4 | 2009405 | new | 0.081691198 | 0.253294833 | 0.066699208 | 0.158261355 | True |

## Descriptive results

| Group | n | Overall first 1000: mean (SD) | Overall full 3000: mean (SD) | Joint cutoff pass counts: first/full |
|---|---:|---:|---:|---:|
| attempt3_new_only | 4 | 0.281217480 (0.025787390) | 0.203803089 (0.020808328) | 0/4 vs 4/4 |
| attempt3_including_seen_pilot | 5 | 0.277390523 (0.023915897) | 0.201206347 (0.018932913) | 0/5 vs 5/5 |
| attempt4_new_only | 5 | 0.263323977 (0.012368157) | 0.152850276 (0.005477609) | 0/5 vs 5/5 |

Conditional diagnostic repeatability for two fixed historical coefficient vectors. Five is a small sample; the seen pilot is excluded from attempt3_new_only. Prefix/full samples are nested. Counts are descriptive, not a validated pass probability or proof of production-policy suitability. No fitting variation, prediction quality, stronger identification or evolutionary improvement was measured.

All thresholds are unchanged: individual <0.1, overall <0.25. A threshold pass is distinct from full native validity. Historical accepted/rejected records remain unchanged.

See `cell_metrics.csv`, `summary.json`, each cell directory and `configs/convergence-repeatability-v1.json`. Every completed cell retains raw moment/score arrays and compact native covariance/derivative results, plus coefficient guards and source commitments. The prior 3B pilot is referenced, not duplicated or rerun.
