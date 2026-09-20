You are modifying an interpretable statistical model specification for the
Kinne–Kang defense cooperation network. You are not optimizing countries'
strategies, national security, or policy. The countries' network objective is
f_i^net(x,z)=sum_k beta_k s_ik(x,z), with continuous-time RSiena stochastic
actor-oriented dynamics and partner confirmation. Only the supported endogenous
network statistics s_ik may change; beta_k are statistically estimated using
training observations, not supplied by you. The defense-spending objective and
original empirical controls are immutable.

Return a Python program containing build_network_spec(allowed_schema) with a
literal return dictionary: {"schema_version": 1, "network_effects": [...]}. The
trusted evaluator AST-interprets that literal and never executes candidate Python.
Imports, calls, external files, coefficient values, evaluator changes, data access,
and arbitrary Python utilities are unsupported. The catalog and limit in the
allowed schema are authoritative. Initial endogenous mechanisms are degPlus and
transTriads. At most three supported endogenous structural effects are allowed.
Keep EVOLVE-BLOCK markers intact. Explain each structural change in code comments.

Fixed scientific fitness (never redefine it): for each development target
t in {2006,2007,2008,2009}, coefficients are fitted only on 1990..t-1; an
unconditional annual RSiena forecast starts from the observed t-1 state. For
S=1000 endpoint networks, p_C(i,j,t)=sum_s A_C,s(i,j,t)/S. Binary ties are averaged
before scoring. Eligible undirected dyads are scored once, i<j, using the pinned
R PRROC integral. B_t is the original empirical predictive specification refitted
on the identical training observations/settings. delta_t=PR_AUC(C,t)-PR_AUC(B_t,t).
F(C)=(delta_2006+delta_2007+delta_2008+delta_2009)/4. Shinka combined_score=1+F
solely avoids the pinned engine's exact-zero sorting bug; raw F is reported.
There is no complexity reward, runtime reward, spending reward, or LLM judgment
in this fitness. Negative improvements remain negative. A failed fit, incomplete
year set, nonfinite result, invalid forecast, or timeout is invalid execution,
not a scientific loss. Uncertainty and the same fixed random schedule matter.

Use parent, executable archive/top-performing inspirations, detailed development
feedback, and native meta-recommendations to propose mathematically meaningful
structural changes. Cosmetic source changes are not new mathematical models;
canonical model novelty is independently tracked. Source-code embedding novelty
is a heuristic, never a guarantee of model novelty. No final-year results or
outcomes may enter mutation, novelty, prompt evolution, inspirations, or selection.
Do not access files or use tools: all authorized task context is in this prompt.
