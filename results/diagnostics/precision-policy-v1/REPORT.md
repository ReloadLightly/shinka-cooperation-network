# Precision-before-continuation policy: implementation validation

Status: **implemented and validated as an opt-in fit-only policy**.
No Step 4 experiment or production fit has been executed under this policy.

The pinned R 4.2.1 / RSiena 1.3.10 validation passed **48 R checks**.
It replayed archived native and explicitly synthetic fixtures through the
policy state machine, testing short acceptance, one supplemental assessment,
successful rescue, failed-assessment continuation using original prevAns,
unchanged-vector seed reuse, partial-operation refusal and tampering refusal.
Both strict cutoffs and all existing native validity requirements remain.

Two **real native initializations** restored the saved third/fourth vectors
through the structured adapter at policy seed 52020091 and stopped before
phase 3. All coefficients remained identical, with zero simulator calls.
The test replay does not create empirical observations at that new seed.
The new generalized assessor's complete 3000-draw route was not rerun.

**170 Python tests** passed. Source/CLI tests, fixture replay and real stopped
initialization are distinct forms of evidence, not interchangeable claims.
Saved evidence is in execution.json, native-tests.json, native-tests.log,
python-tests.log and resources.txt; commitment.json binds those original files.
Documentation publication additionally binds the Python contract and runtime
launcher helpers in future request fingerprints; it does not alter the native
implementation that passed the R checks.

## Exact production behavior, when explicitly invoked

An eligible ratio-failing 1000-draw vector gets one fresh 3000-draw check.
Valid short fits remain accepted; this is a prespecified supplemental gate,
**not universal 3000-draw certification** or a guaranteed error probability.
A failed complete 3000-draw result gets no extra chance. Native-invalid
short fits do not bypass native validity. Seeds depend only on development
target and optimization attempt: 52000000 + 10 * year + attempt.
If an unchanged vector recurs within its bound fit, its assessment is reused.

Original optimizer checkpoints and any supplemental result remain separate.
Failed supplemental diagnostics never replace original warm-start matrices.
Acceptance records explicitly carry authoritative_n3, which can be 3000 on
an optimizer attempt whose scheduled n3 was 1000. Resumption cannot silently
change the request, overwrite evidence or retry an interrupted operation.

## Boundaries and Step 4

The interface is scripts/precision_fit.py, with the explicitly new profile
configs/precision-fit-v1.json. It is development-only and fit-only; no target
scores or evolution run. Historical entry points/settings/results remain
unchanged. Do not give the new settings to the old forecast adapter: Step 4
must explicitly consume the new acceptance receipt and declare its scoring
and uncertainty protocol. Automatic migration of historical accepted fits or
scores is not implemented. Any reuse must replay a reviewed policy-compatible
checkpoint history consistently for reference and candidate models.

Full design: ../../../docs/PRECISION_CONVERGENCE_POLICY.md.
Evidence motivating it: ../convergence-repeatability-v1/INTERPRETATION.md.
