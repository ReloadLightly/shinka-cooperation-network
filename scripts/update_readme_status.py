#!/usr/bin/env python3
"""Render current README coverage from published manifests, without R or data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- GENERATED-COVERAGE:START -->'
END = '<!-- GENERATED-COVERAGE:END -->'


def coverage(evolution, reproduction):
    years = evolution['baseline_years']
    accepted = [str(year) for year in (2006, 2007, 2008, 2009)
                if years.get(str(year), {}).get('accepted_training_fit_present') is True
                and (years[str(year)].get('forecast_audit') or {}).get('returned_simulations') == 1000
                and (years[str(year)].get('baseline_primary_metrics') or {}).get('pr_auc') is not None]
    complete = len(accepted) == 4
    evaluations = evolution.get('multiobjective_completed_evaluations', [])
    eq = reproduction.get('equilibrium_completed_settings', 0)
    fig = reproduction.get('figures_5_7_completed_settings', 0)
    lines = [START, '| Scientific milestone | Evidence in the published manifests |', '|---|---|',
        f'| Original equilibrium diagnostic | **{eq} / {reproduction.get("equilibrium_full_settings", 101)}** settings |',
        f'| Figures 5–7 simulation campaign | **{fig} / {reproduction.get("figures_5_7_full_settings", 564)}** settings |',
        f'| Temporal reference forecasts | **{len(accepted)} / 4 accepted and scored**' + (f'; {", ".join(accepted)}' if accepted else '') + ' |',
        '| Four-year reference forecast inputs | ' + ('**Complete**; cached forecasts supply the zero reference vector' if complete else '**Incomplete**; no partial-year fitness') + ' |',
        f'| Archived complete multiobjective evaluations | **{len(evaluations)}** canonical records; this count includes the reference when archived |',
        '| Native evolutionary improvement | Not inferred from reference completion or configured capabilities; inspect evaluated descendants |',
        '| Finalist sensitivity / reserved comparison | Tooling available; execution must be established by its own artifacts |', END]
    return '\n'.join(lines)


def updated(text, evolution, reproduction):
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError('README must contain exactly one generated coverage block')
    start, end = text.index(START), text.index(END) + len(END)
    return text[:start] + coverage(evolution, reproduction) + text[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'README.md'; before = path.read_text()
    after = updated(before, json.loads((ROOT / 'results/evolution_manifest.json').read_text()),
                    json.loads((ROOT / 'results/reproduction_manifest.json').read_text()))
    if args.check:
        if before != after:
            raise SystemExit('README coverage is stale; run python scripts/update_readme_status.py --write')
        print('README coverage matches the published manifests.')
    elif args.write:
        path.write_text(after)
    else:
        print(coverage(json.loads((ROOT / 'results/evolution_manifest.json').read_text()),
                       json.loads((ROOT / 'results/reproduction_manifest.json').read_text())))


if __name__ == '__main__':
    main()
