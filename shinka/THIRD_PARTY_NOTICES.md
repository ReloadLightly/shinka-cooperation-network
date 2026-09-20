# Third-party notices for published patches

This directory publishes project compatibility patches containing limited source
context from the following Apache-2.0 components. The exact upstream license texts
are included, with their original copyright notices preserved.

| Component | Pinned source | Copyright notice | Included license |
|---|---|---|---|
| ShinkaEvolve 0.0.7 | [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50), commit `9912af12d423504b8d580f4179fd15f5f88b8c50` | Copyright 2025 Sakana AI | [ShinkaEvolve Apache-2.0](licenses/ShinkaEvolve-Apache-2.0.txt) |
| Headless 0.6.1 | [RobertTLange/headless-cli](https://github.com/RobertTLange/headless-cli), npm `@roberttlange/headless@0.6.1` | Copyright 2026 Robert Lange | [Headless Apache-2.0](licenses/Headless-Apache-2.0.txt) |

Project modifications, recorded 2026-09-20:

- `patches/astra-ultra-and-no-web.patch` extends the Shinka and Headless reasoning
  effort parsers to accept `max` and `ultra`, disables Headless's default web search
  and shell tool for this read-only route, and binds the native WebUI to loopback.
- `patches/local-evaluation-process-tree.patch` changes native local evaluator
  cleanup to terminate owned descendants, including children in separate sessions.

The patch files identify their modified source paths and retain surrounding source
context. These are project changes, not claims of upstream functionality. The
inspected upstream distributions contain no separate `NOTICE` file. Installed
vendor trees, npm dependencies, embedding weights and executable runtimes are not
part of these published patch contexts. Their acquisition, version and local
artifact hashes remain recorded in [provenance.json](provenance.json).

This notice documents the third-party material above; it does not assign a license
to unrelated project code, scientific data, papers or figures.
