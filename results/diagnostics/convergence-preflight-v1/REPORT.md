# Step 3A — saved-fit and native-initialization verification

**Completed without new simulations. Step 3B has not started.**

The exact third Model 3 training-fit attempt associated with the 2009 forecast
was loaded under R 4.2.1 / RSiena 1.3.10. Only its hash-verified 1990–2008 training
packet was decompressed from the preserved development bundle. No outcome packet
or raw replication archive was read.

## Verified findings

| Check | Result |
|---|---|
| Training scope | 161 actors; 19 observed waves, 1990–2008; 18 intervals |
| Parameters | 58: 18 network rates, 18 behavior rates, 11 network-objective and 11 behavior-objective coefficients |
| Coefficient binding | All 58 final theta values matched at actual native initialization; complete identities include period and group |
| Native effect ordering and fixed flags | Identical to the saved fit; all 58 coordinates retained for diagnosis |
| Observed targets | Aggregate and per-period statistics exactly equal; both maximum differences 0 |
| Old moment matrix | 1,000 rows × 58 columns |
| Old maximum individual convergence ratio | 0.07587932310910743; reconstruction error 0 |
| Old overall convergence ratio | 0.2613440047985899; reconstruction error below 4e-16 |
| Old moment covariance | Reproduced with maximum elementwise error 0 |
| Source verification | Nine loaded native function bodies/formals match the pinned source; thirteen source/help/package files hash-checked |
| Numerical activity | Zero new simulations, estimation iterations, refits, forecasts or scores |

The native controller was exercised through initialization and stopped by a
specific expected condition at the entrance to `phase3()`, before its body.
Optimization functions and simulator entry points were separately guarded.
This is a real initialization test, not a mock simulation or a completed
3,000-draw diagnostic. The original failed overall convergence decision remains
failed; these are reconstructed **old** statistics, not new evidence of acceptance.

## Implementation lessons retained for Step 3B

The saved fit contains external pointers, not reusable training data. Rebuild
from the exact packet instead of restoring pointer state. Map `fit$theta`, not
old initial values, using period-aware identities. Keep original free-parameter
flags: marking all parameters fixed would remove the coordinates used by the
overall convergence diagnostic. The proposed no-estimation route is `nsub=0`,
`simOnly=FALSE`, preserving the remaining original scientific settings.

## Tests and resources

All **117 Python tests** and **11 deterministic R checks** passed. The Python
fixtures/source checks are distinct from the real native initialization test.
The latter completed in **8.86 seconds**, with maximum RSS **442,740 KiB**.
These costs exclude runtime installation and are not a pilot-runtime estimate.

The native verification in workflow `35594291946` completed successfully before
a publication helper failed to parse the end of the merged unittest log.
The completed evidence was recovered from artifact `10635713620`, its
commitments verified, and publication repaired without another native run.
[Execution record](execution.json) retains that distinction.

## Evidence and next operation

[Verification JSON](verification.json), [input fingerprints](inputs.json),
[parameter map](parameter-map.csv), [saved covariance](saved-moment-covariance.csv),
[saved means](saved-moment-means.csv), [native log](native.log),
[native initialization report](stopped-initialization.txt),
[resource record](resources.txt), [Python test log](python-tests.log), and
[artifact commitments](commitment.json) are retained here.

Detailed implementation and reproduction instructions:
[CONVERGENCE_PREFLIGHT.md](../../../docs/CONVERGENCE_PREFLIGHT.md).

The separately proposed Step 3B is one 3,000-draw pilot with seed **2009301**,
unchanged saved theta, `nsub=0`, `simOnly=FALSE`, original fixed flags and serial
execution. Required inputs are present. Actual phase-3 coefficient invariance,
completion, warnings, convergence diagnostics and resource cost remain untested.
No thresholds, fitness definitions, original results or evolutionary campaigns
were changed in Step 3A.
