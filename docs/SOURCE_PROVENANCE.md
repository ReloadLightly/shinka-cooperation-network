# Primary-source provenance and reuse

Audit date: 2026-09-20. This records inspected sources and versions, not a claim
that their scientific results have been reproduced.

| Source | Inspected version and local evidence | Reuse statement |
|---|---|---|
| [Kinne and Kang, article](https://doi.org/10.1017/S0020818322000315) | *International Organization* 77, Spring 2023, pp. 405–439; 35-page `sources/reference/paper.pdf`, plus downloaded HTML/text | The article's first page explicitly declares CC BY-NC 4.0. This is distinct from the replication dataset's CC0 dedication. |
| [Online appendix](https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S0020818322000315/resource/name/S0020818322000315sup001.pdf) | 25-page `sources/reference/appendix.pdf`; PDF creation metadata 2022-08-30 | No independent reuse grant was identified in the appendix itself. Retain attribution and do not infer CC0 from the separate data archive. |
| [Replication dataset](https://doi.org/10.7910/DVN/S0ILRB) | Harvard Dataverse version 1.0, released 2022-08-29T20:26:49Z; saved API response `sources/metadata/dataverse.json` | Dataset metadata explicitly declares CC0 1.0; file is unrestricted and does not require an access request. |
| [IO_Final.zip file page](https://dataverse.harvard.edu/file.xhtml?fileId=6429192&version=1.0) | File ID 6429192, 7,978,306 bytes, archive retained at `sources/archive/IO_Final.zip`; [download endpoint](https://dataverse.harvard.edu/api/access/datafile/6429192) | The inspected dataset-level CC0 declaration accompanies this file. |
| [RSiena release](https://github.com/stocnet/rsiena/releases/tag/v1.3.10) | Version 1.3.10, dated 2022-04-28; tag commit `c13ddd4af204cdcfb743ebab6217a68fad333f5a`; `vendor/RSiena` and retained source archive | DESCRIPTION declares `GPL-2 | GPL-3 | file LICENSE`; source LICENSE contains GPLv3. |
| [ShinkaEvolve source](https://github.com/SakanaAI/ShinkaEvolve) and [documentation](https://sakanaai.github.io/ShinkaEvolve/) | Native source pinned to `9912af12d423504b8d580f4179fd15f5f88b8c50`, package 0.0.7; upstream archive and adapter patch recorded separately in `shinka/provenance.json` | Apache-2.0 per pinned source provenance; local modifications are explicitly recorded. |
| [PRROC documentation](https://cran.r-project.org/web/packages/PRROC/PRROC.pdf) | Requested live PDF now describes **1.4**, not this project's pinned **1.3.1**. Installed 1.3.1 help and executable fixtures were independently checked. | PRROC declares GPL-3. The live manual must not be represented as a version-pinned 1.3.1 artifact. |

The archive SHA256 is
`2f4c2c02e3969437976c505098848e0ef7333466aeba3cccd807b3b44ba75308`,
which exactly matches the previously inspected copy specified in the project
instruction. Its MD5 is `71ac60d68d541c14ac7186a74e4a3a50`, independently matching
the Dataverse API's checksum. All 27 extracted file members were byte-compared
with the preserved archive; none differed. The untouched tree is
`sources/original/IO_Final`. Per-file SHA256 values are in
[sources/manifest.json](../sources/manifest.json), including
`data/data_raw.RData`. Generated outputs and working copies belong elsewhere.

Additional retrieved artifact SHA256 values:

| Artifact | SHA256 |
|---|---|
| Article PDF | `84b709d3183e1092604d474e8d6f7438e5b489f1d28130e1df03d169cd575ce7` |
| Appendix PDF | `0ad37482e8ec54f6ca62a0198733f56d8567d467fbc3fcc9eff5cc49454ba602` |
| RSiena v1.3.10 source archive | `c7e0fc358f064e6b5d753ceb675a2eb00ea08cd6d58934ebabef31055302a1d5` |
| Retrieved live PRROC 1.4 manual | `dede522981b2d8ef9b8646e8eabfd45b7d2b4bc20bc246e169b54c8bc4d695e3` |

The article PDF contains Cambridge's retrieval timestamp, so another download
can have different bytes even when the underlying article is unchanged. PDF text
was inspected locally with pypdf 5.9.0; page numbers cited in the reproduction
audit are the appendix's printed page numbers, which match PDF page indices plus
one. Text extraction is an inspection aid, not a replacement for the source PDFs.

The archive README recommends R 4.2.1 and RSiena 1.3.10 on its reported Ubuntu
14.4 LTS system. Both requested language/package versions are installed exactly.
The current host, compiler, BLAS, dependency versions, binary-package build
warnings and isolated installation are documented in
[environment/README.md](../environment/README.md), with complete locks and
checksums. PRROC 1.3.1 is our declared pin; an original-author PRROC version was
not established from the replication README. Its help confirms positive scores
in `scores.class0`, negative scores in `scores.class1`, and the piecewise integral
in `auc.integral`. The verification fixture is preserved at
[environment/prroc-verification.json](../environment/prroc-verification.json).
