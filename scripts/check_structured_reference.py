#!/usr/bin/env python3
"""Opt-in forced new-adapter forecast from an accepted development fit; no refit."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import finalist_set as finalist
from scripts import multiobjective_evaluation as evaluator
from scripts.scientific_contract import scientific_identity
from scripts.resources import scientific_execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, choices=(2006, 2007, 2008, 2009), default=2006)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print('Dry run: --execute forces the structured adapter using an accepted development fit; no fitting or target scoring.')
        return 0
    with scientific_execution():
        settings, protocol = finalist.settings_and_protocol()
        spec, _ = evaluator.read_program(evaluator.REFERENCE)
        source = evaluator.saved_forecast_folder(spec, args.year, settings, protocol)
        finalist.validate_prediction(source, args.year, settings, args.year * 1000 + 1)
        identity = scientific_identity(ROOT)['sha256']
        destination = ROOT / 'results/verification/structured-reference' / identity / str(args.year)
        # This dedicated directory cannot return the original cached prediction.
        finalist.forecast(spec, args.year, settings, protocol, destination, fitted_source=source)
        evaluator.legacy.run_r([ROOT / 'R/compare_structured_predictions.R', source / 'predictions.rds',
                               destination / 'predictions.rds'], destination, 'compare_predictions', 300)
        evaluator.save_json(destination / 'verification.json', {
            'status': 'passed', 'year': args.year, 'scientific_fingerprint': identity,
            'training_refitted': False, 'target_outcomes_accessed': False,
            'native_structured_adapter_forced': True,
            'reference_prediction_sha256': evaluator.sha(source / 'predictions.rds'),
            'structured_prediction_sha256': evaluator.sha(destination / 'predictions.rds'),
            'comparison': 'identical fields in R/compare_structured_predictions.R; metadata-only additions allowed'})
        print(destination / 'verification.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
