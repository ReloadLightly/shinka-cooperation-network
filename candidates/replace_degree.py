"""Structural alternative: preferential attachment replaces total degree."""

# EVOLVE-BLOCK-START
def build_network_spec(allowed_schema):
    return {
        "schema_version": 1,
        "network_effects": ["inPop", "transTriads"],
    }
# EVOLVE-BLOCK-END
