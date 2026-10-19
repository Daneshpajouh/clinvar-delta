# clinvar-variant-nf

A Nextflow pipeline that does two things with ClinVar:

1. Panel report: takes a germline VCF, normalises it, adds ClinVar classifications,
   review stars and gnomAD allele frequencies, and lists the variants in a gene panel
   (here the 81 ACMG SF v3.2 genes) that ClinVar calls pathogenic or likely pathogenic.
2. Release audit: compares two ClinVar releases variant by variant and reports what
   changed: reclassifications (for example VUS to likely pathogenic), changes in review
   level, new and withdrawn records, and changes that are only re-annotation by ClinVar.

## Why the second part matters

ClinVar is updated every week. A variant reported as "uncertain" to a patient last year
may now be "likely pathogenic", and the reverse also happens. Between the 2025-10-13 and
2026-10-11 releases, 40,961 variants moved to a different classification group; in the
81 ACMG genes alone, 183 went from VUS to P/LP and 69 went from P/LP to VUS. A lab that
re-checks its past reports needs exactly this list, with the assertion changes separated
from ClinVar's own re-annotation. [docs/explainer.md](docs/explainer.md) covers the
background for readers who do not work with ClinVar.

## Quick start (about 2 minutes)

Needs Nextflow 25.04 or newer, Java 17+, and either Docker or local `bcftools` 1.23 and
Python 3.11+.

```bash
git clone https://github.com/Daneshpajouh/clinvar-variant-nf.git
cd clinvar-variant-nf
make image        # builds ghcr.io/daneshpajouh/clinvar-variant-nf:1.0.0 locally

# Annotate two bundled samples: real HG002 records in BRCA1, BRCA2 and TP53, and one synthetic sample
nextflow run . -profile test,docker --outdir results
# ...
# [SUCCESS] completed=18 failed=0 cached=0

# Compare the bundled cuts of two ClinVar releases
nextflow run . -profile test_diff,docker --outdir results_diff

ls results/report results_diff/clinvar_diff
```

Without Docker, use `-profile test`; `bin/cvnf` runs the Python tools from the checkout.

On the development machine (Apple M-series Mac, Docker Desktop, 2026-10-19) the two test
runs took 12.6 s and 8.8 s.

## Real-data results

From runs on 2026-10-19 (commands and full tables in [docs/results.md](docs/results.md)):

| | |
|---|---|
| HG002 (GIAB v4.2.1) variants in the 81 ACMG SF v3.2 genes | 9,807 |
| of which ClinVar P/LP, any review level | 0 |
| ClinVar 2026-10-11 records compared with 2025-10-13 | 4,594,764 against 3,878,123 |
| reclassified between groups / review level changed / annotation only | 40,961 / 164,786 / 4,427 |
| added / removed | 725,461 / 8,820 |
| wall time, panel annotation of HG002 / full release diff | 30.9 s / 1 min 20 s |

## Documentation

| Page | Content |
|---|---|
| [explainer](docs/explainer.md) | ClinVar, review stars and reclassification in plain language |
| [quick start and usage](docs/usage.md), [parameters](docs/parameters.md) | running on your data, profiles, outputs |
| [results](docs/results.md) | real HG002 and release-diff numbers with the exact commands |
| [profiling](docs/profiling.md) | before, during and after a run: trace report, calibrated requests, Slurm accounting |
| [testing](docs/testing.md), [test report](docs/test_report.md) | the four test layers and the v1.0.0 results |
| [code walk-through](docs/code_walkthrough.md) | a reviewer's tour of the code, with the design decisions |
| [maintenance SOP](docs/sop.md) | monthly ClinVar update, versioning, deprecations |
| [operations notes](docs/operations.md) | failures hit while building this, and their fixes |
| [data sources](docs/data_sources.md) | every downloaded file with URL, size, SHA-256 and terms |

## Layout

```
main.nf                 entry: --mode annotate | diff
workflows/              ANNOTATE and CLINVAR_DIFF
modules/local/          one process per directory, each with a stub block and versions.yml
conf/                   resource labels, Slurm, calibrated requests, test profiles
src/cvnf/               Python tools (diff, report, profiling), typed, no dependencies
bin/cvnf                runs src/cvnf from the checkout when the package is not installed
tests/                  pytest (unit, CLI, pipeline), nf-test, data and mocks
containers/             Dockerfile and Apptainer definition for the tools image
scripts/                data download and test-data builder
```

The Snakemake version of this kind of workflow lives in a separate repository; this one
is Nextflow only.

## Licence and citation

Apache-2.0. See [CITATION.cff](CITATION.cff). This is research software: the reports are
not clinical reports.
