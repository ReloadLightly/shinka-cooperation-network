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


# Potential Recommendations
The following are potential recommendations for the next program generation:

SYNTHETIC META CHECK: preserve controls.
You MUST respond using an edit name, description, and the exact SEARCH/REPLACE diff format shown below to indicate changes:

<NAME>
A shortened name summarizing the edit you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the edit you are proposing.
</DESCRIPTION>

<DIFF>
<<<<<<< SEARCH
# Original code to find and replace (must match exactly including indentation)
=======
# New replacement code
>>>>>>> REPLACE

</DIFF>


Example of a valid diff format:
<DIFF>
<<<<<<< SEARCH
for i in range(m):
    for j in range(p):
        for k in range(n):
            C[i, j] += A[i, k] * B[k, j]
=======
# Reorder loops for better memory access pattern
for i in range(m):
    for k in range(n):
        for j in range(p):
            C[i, j] += A[i, k] * B[k, j]
>>>>>>> REPLACE

</DIFF>

* You may only modify text that lies below a line containing "EVOLVE-BLOCK-START" and above the next "EVOLVE-BLOCK-END". Everything outside those markers is read-only.
* Do not repeat the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the SEARCH/REPLACE blocks.  
* Every block’s SEARCH section must be copied **verbatim** from the current file, including indentation.
* You can propose multiple independent edits. SEARCH/REPLACE blocks follow one after another. DO NOT ADD ANY OTHER TEXT BETWEEN THESE BLOCKS.
* Make sure the file still runs after your changes.

Here are the performance metrics of a set of previously implemented programs:

# Prior programs

```python
"""Structural alternative: preferential attachment replaces total degree."""

# EVOLVE-BLOCK-START
def build_network_spec(allowed_schema):
    return {
        "schema_version": 1,
        "network_effects": ["inPop", "transTriads"],
    }
# EVOLVE-BLOCK-END

```

Performance metrics:
Combined score to maximize: 1.0

Text feedback:
SYNTHETIC INSPIRATION ONLY; no empirical score.


# Current program

Here is the current program we are trying to improve (you will need to propose a modification to it below):

```python
"""Original predictive network objective: empirical Model 3.

Only endogenous network statistics are mutable. The trusted adapter retains
density, all empirical controls, and the full spending objective, and estimates
every coefficient from training observations.
"""

# EVOLVE-BLOCK-START
def build_network_spec(allowed_schema):
    return {
        "schema_version": 1,
        "network_effects": ["degPlus", "transTriads"],
    }
# EVOLVE-BLOCK-END

```

Here are the performance metrics of the program:

Combined score to maximize: 1.00
raw_F: 0.00

Here is additional text feedback about the current program:

SYNTHETIC CONTRACT CHECK ONLY: F=+0.000000000000; no fitted score.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.