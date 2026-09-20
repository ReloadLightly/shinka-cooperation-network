"""Kinne and Kang's predictive Model 3, expressed in the native schema-v2 grammar.

Network degree activity/popularity uses the empirical raw-degree parameter 1.
The trusted R adapter preserves density, empirical controls and spending-objective
structure, while jointly estimating every included coefficient from past data.
"""

# EVOLVE-BLOCK-START
def build_network_spec(allowed_schema):
    return {
        "schema_version": 2,
        "network_effects": [
            {"effect": "degPlus", "parameter": 1},
            {"effect": "transTriads", "parameter": 0},
        ],
    }
# EVOLVE-BLOCK-END
