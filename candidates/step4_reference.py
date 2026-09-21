"""Frozen Step 4 specification; no learned coefficient or output edits."""

def build_network_spec(allowed_schema):
    return {'schema_version': 2, 'network_effects': [{'effect': 'degPlus', 'parameter': 1}, {'effect': 'transTriads', 'parameter': 0}]}
