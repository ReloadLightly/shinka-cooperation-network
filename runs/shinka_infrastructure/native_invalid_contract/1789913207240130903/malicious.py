from pathlib import Path
Path('/home/roland/actir/shinka-cooperation-network/runs/shinka_infrastructure/native_invalid_contract/1789913207240130903/MUST_NOT_EXECUTE').write_text('UNSAFE EXECUTION')
def build_network_spec(allowed_schema):
    return {'schema_version': 1, 'network_effects': ['degPlus', 'transTriads']}
