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
