# Saved 2009 training-fit numerical diagnosis

This focused analysis reads only completed attempts 1–3 for the original predictive specification fitted through 2008. It does not refit, simulate, score outcomes, change acceptance criteria, or modify the running fourth continuation. The saved fits remain unchanged. The final analysis took 2.54 seconds, with peak resident memory 253,668 KiB; its script, log, resource record, named tables and input provenance are retained here.

## Native diagnostic and numerical evidence

For this unconditional method-of-moments fit, RSiena 1.3.10 computes

\[
m=\operatorname{colMeans}(\mathrm{sf}),\quad
V=\operatorname{cov}(\mathrm{sf}),\quad
r_{\max}=\sqrt{m^\top V^{-1}m}.
\]

Fixed parameters would be removed; these fits have none. Each individual ratio is \(m_k/\sqrt{V_{kk}}\), using the simulation standard deviation, **not** the standard error of the simulation mean. The overall ratio is the maximum over linear combinations of the moments. Our reconstruction agrees with the stored ratios to floating-point precision and reproduces `msf` exactly. Source: `vendor/RSiena/R/phase3.r:153–212,463`.

| Attempt | Phase-3 draws | Largest absolute individual ratio | Overall ratio | Moment-correlation condition number | Standardized derivative condition number |
|---|---:|---:|---:|---:|---:|
| 1 | 1,000 | 0.112280530010 | 0.350944379747 | 102.05 | 98.53 |
| 2 | 1,000 | 0.096627317447 | 0.319073459000 | 115.37 | 99.75 |
| 3 | 1,000 | 0.075879323109 | 0.261344004799 | 126.79 | 99.99 |

The declared cutoffs remain maximum individual ratio `<0.1` and overall ratio `<0.25`. Attempt 3 fails the overall criterion. Native termination is `OK` in all three, but native success does not override the project's stricter convergence criteria. All three have empty native covariance-error messages, no divergence flags, no fixed parameters, and no newly fixed parameters. Reconstruction of the raw score-based derivatives finds no negative diagonal entries requiring the native correction.

## Monte Carlo contribution, with qualifications

There are 58 jointly assessed moments. At an exact moment root, an independent-draw heuristic for this norm is \(\sqrt{58/1000}=0.240832\), already close to the project's 0.25 cutoff. At 3,000 draws that heuristic is approximately 0.139044. These are noise-scale references, not replacement cutoffs, estimated true residuals, or tests of the empirical model.

We also centered and whitened the saved `sf` rows and computed Bartlett-weighted long-run variance traces using 10, 20 and 50 lags. This is deterministic matrix analysis of existing draws, not new simulation or resampling. For attempt 3 the resulting Monte Carlo ratio scales are respectively **0.239258, 0.236663 and 0.233161**. Their squared scales are 0.05724, 0.05601 and 0.05436, compared with the observed squared ratio 0.06830. This puts the sampling-noise benchmark at about 80–84% of the observed squared norm, but does **not** identify that proportion as noise: the covariance is estimated from the same draws, the true residual is unknown, and long-run variance estimates have uncertainty. Raw differences between squared norm and noise benchmark are retained without treating them as a corrected convergence score.

Attempt 3's median coordinate lag-one correlation is 0.001708 and its largest absolute value is 0.061694. This gives no conspicuous evidence of severe serial persistence, but is not a proof of independent draws. Its four 250-draw blocks have overall norms 0.4646, 0.5109, 0.5146 and 0.4517 using the full-sample covariance; smaller blocks naturally have more diagnostic noise. No formal significance claim is made for dependent dyads or across the dependent training fits.

The relevant native convergence calculation uses raw simulated-statistic deviations saved in `sf` (`phase3.r:717–723`). Dolby variance reduction affects other reported estimates and algorithm operations; the convergence formula here still uses raw `sf/msf` (`phase3.r:405–465`). Consequently, a variance-reduced `estMeans` diagnostic must not be silently substituted.

## Which combinations matter

Attempt 3's largest individual deviations are the network rate for period 17 (+0.07588), the spending rate for period 3 (−0.07346), and the spending rate for period 7 (+0.05573). The largest network-objective deviation is absolute ideal-point distance (−0.04810). All are within the individual cutoff.

Marginal overall ratios for the four blocks are network rates 0.14388, network objective 0.09969, spending rates 0.14180, and spending objective 0.08538. These correlated blocks do not form an additive decomposition of the overall ratio. The optimal full combination and its signed coordinate contributions are saved in `attempt-3-named-moments.csv`; prominent terms include spending rate period 3, network rate period 17, distance, network rates periods 5–6, and spending rate period 7. Signed contributions describe one correlated linear combination, not causal importance.

The largest covariance eigendirection accounts for 15.95% of attempt 3's squared ratio and is mainly a mixture of spending/network rates; its eigenvalue is 0.9416, so it is not a nearly zero-variance direction. A second direction accounts for 9.70% and mixes national capabilities (+0.641 loading), trade (−0.577), density (−0.308), and distance (−0.308), with eigenvalue 0.1105. The five leading directions and named loadings are retained for every attempt.

## Conditioning and derivative uncertainty

Raw condition numbers reflect radically different units: in attempt 3 they are approximately 48.4 million for the moment covariance and 7.32 million for the derivative. Interpreting those as identification failures would be misleading. After converting covariance to a correlation matrix, its condition number is 126.79, with minimum eigenvalue 0.04281. After scaling derivative rows by moment standard deviation and parameter columns to unit Euclidean norm, its condition number is 99.99 and smallest singular value 0.02937. Scaling parameter columns by fitted standard errors instead gives condition number 57.85. Parameter-correlation minimum eigenvalue is 0.04211. These matrices are numerically full rank; this does not establish strong identification of every combination.

The weakest standardized derivative direction chiefly trades off the spending objective's degree effect (+0.804) against its dense-triads effect (−0.567), with a smaller linear-shape component (−0.145). Another weak direction mixes network density (−0.751) and degree activity plus popularity (+0.578). Their signs are arbitrary eigenvector conventions. They flag correlated estimation directions, not grounds to remove protected effects or declare failure automatically.

The score-based derivative is reconstructed from saved per-period score/statistic arrays using the native formula (`phase1.r:543–580`), with standardized relative error below \(7\times10^{-15}\). Reconstructing the two 500-draw halves of attempt 3 gives about 6.8% deviation of each from the full derivative and 13.58% difference between halves, measured in the same moment-SD/parameter-SE scaling. This demonstrates finite-draw derivative uncertainty without implying singularity. Standardized unit-column derivatives differ by 10.25% and 11.11% between consecutive attempts. The stored `dfra1` is the incoming derivative used in phase 2, which can come from a previous fit; it is not necessarily a newly estimated phase-1 matrix on a continuation.

## Interpretation and the running continuation

Together with small coefficient movements reported separately, these results are consistent with a near-solution and substantial diagnostic Monte Carlo noise. They do not show large coefficient oscillation, catastrophic singularity, or a native identification warning. Residual mismatch is not excluded: attempt 3 remains above the prespecified overall threshold, and a single noisy diagnostic cannot establish the exact underlying moment root.

`nsub` controls stochastic-approximation subphases in phase 2; increasing it can move the coefficient estimate (`phase2.r:62–82`). `n3` controls phase-3 draws used to assess convergence, covariance and derivatives. Native phase 3 calculates a possible Newton step but calls it with `MakeStep=FALSE` (`phase3.r:90–95,478–575`); increasing `n3` alone is therefore not a substitute for further parameter adjustment. The pinned help says 1,000 draws often suffice for routine method-of-moments use and advises at least 3,000 for publication/maximum likelihood (`man/sienaAlgorithmCreate.Rd:63–68`).

The already-running continuation changes both `nsub` and `n3` under the declared policy. It must finish and be assessed under the unchanged criteria before any remedy is selected. This diagnosis supplies no held-out prediction or evolutionary result.
