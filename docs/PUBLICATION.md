# Scientific artifact publication

The publication inventory is [results/publication/inventory.json](../results/publication/inventory.json). It lists each scientific artifact's relative path, byte count, SHA256, category, and whether Git ignored it when inspected. Failed fits and interrupted attempts are evidence and are included. The inventory is a file-level snapshot, not proof of successful reproduction or predictive improvement.

The initial audit on 20 September 2026 identified **259 artifacts totaling 39,518,882 bytes**, including the 7,978,306-byte CC0 replication archive. The largest generated scientific artifact was a 4,456,130-byte fitted-model snapshot. The present results fit ordinary Git; every artifact is below GitHub's 50 MiB warning threshold and 100 MiB hard limit. No large-file storage service is necessary for this snapshot. [GitHub's large-file documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) was checked on 20 September 2026. Byte-identical historical fit snapshots remain at their original provenance paths; Git can reuse their content blobs.

| Evidence category | Files | Bytes at initial audit |
| --- | ---: | ---: |
| Empirical fit caches and diagnostics | 46 | 22,612,415 |
| Environment and source provenance, including archive | 22 | 8,387,298 |
| Original ABM checkpoints | 7 | 2,487,416 |
| Copies of generated original-source logs | 6 | 1,529,349 |
| Native engine and adapter evidence | 61 | 267,949 |
| Other scientific results and execution logs | 117 | 4,234,455 |

Refresh before committing a later snapshot:

```bash
python3 scripts/publication_inventory.py
```

This command uses Python's standard library. It does not run R, stage files, contact GitHub, inspect user-home credentials, deserialize outcome packets, or read/hash `data/targets/2010.rds`. It checks file size and modification time around reads and rejects a file that repeatedly changes. Finish or checkpoint active scientific jobs before publishing if an across-file stationary snapshot is required.

## Generated outputs rescued from ignored work directories

Original source work directories contain redundant input data as well as generated output. The inventory command copies only generated `output/`, `figures_tables_main/`, `figures_tables_appendix/`, and `cluster.out` into the corresponding run's `source_outputs/`. Each run's `source_outputs/provenance.json` records the original relative source path, copied path, size, SHA256, source modification time, and snapshot time.

The current preserved files include the complete original `ABM_sims.txt` and `equilibriaModels.txt` logs, plus both cluster logs. Their work-directory originals remain untouched. The same command preserves the otherwise ignored `data/preparation_audit.json` at [results/audits/data_preparation.json](../results/audits/data_preparation.json), with provenance. Inspection of `R/audit_data.R` confirms that this audit reports training-only coverage, missingness, and composition; it does not contain target labels or target tie counts.

## Inclusion and exclusion rules

The publication configuration removes these former broad exclusions from `.gitignore`, so caches and native result objects are included:

```gitignore
results/cache/
results/**/*.rds
results/**/*.RDS
results/**/*.RData
results/**/*.csv.gz
```

Source work directories and prepared input packets remain ignored. Only the canonical archive is included from its directory:

```gitignore
sources/archive/*
!sources/archive/IO_Final.zip
```

Machine environments, regenerated data, private sessions, and ephemeral process locks remain excluded:

```gitignore
results/**/work/
data/
sources/original/
**/evaluation.lock
results/r-execution.lock
runs/**/campaign_supervisor.lock
runs/**/home/
runs/**/auth.json
*.sqlite-wal
*.sqlite-shm
```

Existing exclusions for installed R/Python environments, vendor checkouts, compiler/package caches, downloaded tooling, model weights, and `node_modules` should remain. These are reconstructible dependencies, not scientific results. Original article/appendix PDFs have separate reuse terms and are not included in this artifact inventory; source provenance and download instructions remain available.

The canonical replication archive is already publicly available under the recorded dataset terms. Publishing that archive does not authorize candidate access to raw data. Mutation subprocesses must retain their restricted filesystem interface, and 2010 outcomes remain excluded from selection, feedback, and prompts. The inventory excludes any incomplete `results/final_test/` tree; final outputs belong in a later publication snapshot only after the completed comparison exists. It never traverses private `home/`, `.codex/`, or `.claude/` directories.

For future campaigns that generate substantially larger simulation archives, retain compact predictions, diagnostics, manifests, and checksums in Git, and publish bulky immutable archives as [versioned release assets](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github#distributing-large-binaries) or through an archival repository. Do not replace fitted coefficients, eligibility masks, failed-fit diagnostics, or the evidence needed to reconstruct reported scores with unexplained external files.

## Credential and session audit

[results/publication/credential_scan.json](../results/publication/credential_scan.json) records filename-only findings from the current publishable tree and the scientific artifacts that were still ignored. The initial expanded scan inspected 308 textual/SQLite files and found **no high-confidence API-token, JWT, private-key, bearer-token, credential-assignment, or credential-URL pattern matches**. Auth/session references occurred only in ignore rules and the sandbox/publication implementation:

- `.gitignore`
- `scripts/publication_inventory.py`
- `scripts/run_shinka.py`
- `shinka/check_network_isolation.py`
- `shinka/headless_isolated.py`

These references are expected policy/code paths; no authentication or conversation-session payload was identified in the generated scientific outputs. The audit does not decode compressed R objects, archives, PDFs, or images for secrets; those files are inventoried by hash and provenance. This is a bounded publication check, not a claim that pattern matching proves the absence of every possible secret.

No remote operation, visibility change, or Git staging is performed by this workflow. The GitHub publication preserves the repository’s existing private visibility.
