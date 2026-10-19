# Testing

Four layers, each run by one command, plus a portability check. The test report for
v1.0.1 is in [test_report.md](test_report.md).

| Layer | Command | Tests | Run time | What it catches |
|---|---|---|---|---|
| Unit and CLI (pytest) | `make test-unit` | 90 | 0.3 s | classification and star mapping, diff categories, merge-join order, parsing of traces and sacct, report contents, bad inputs |
| Module (nf-test) | `make nf-test` | 11 module tests, 3 pipeline tests | 63 s | each process's command line, inputs and outputs, snapshots of outputs |
| Pipeline (pytest + Nextflow) | `make test-pipeline` | 9 | 26 s | channel wiring, both modes end to end, `-resume`, `-stub-run`, samplesheet validation |
| Validation (real data) | commands in results.md | 2 runs | 31 s and 80 s | counts that must add up, checksums of inputs, comparison with known values |

## Portability check

`scripts/test_linux.sh NXF_VER` (or `make test-linux NXF_VER=25.04.0`) builds a Debian 12
image with only Java 17, bcftools 1.16, tabix, procps and Python 3.11, installs the given
Nextflow release, and runs the `test` and `test_diff` profiles from an empty plugin cache
on the files git tracks. It catches what a developer machine hides: plugins served from a
local cache, syntax newer than the declared minimum Nextflow, missing system tools. It is
run for 25.04.0 (the declared minimum) and the current release.

## Unit and CLI layer

`tests/unit/`, pure Python, no network or external tools. Coverage of `src/cvnf` from
`pytest tests/unit --cov=cvnf` on 2026-10-19: 88% of 942 statements. By module: clinvar
100%, diff 99%, annotate 98%, profiling 94%, report 92%, vcf 92%, panel 85%, cli 73%
(the uncovered CLI lines are the panel and manifest commands, which the pipeline layer
runs).

Notable cases:

- every review status found in the two real ClinVar releases maps to the documented stars,
  and an unknown status raises instead of scoring 0;
- 16 CLNSIG forms, including `Pathogenic|risk_factor`, low penetrance, `VUS-high` and a
  P/B mix;
- the diff: accession continuity across gaps in Variation IDs, unsorted input rejected,
  gene filter matching either release, assertion and annotation changes counted apart,
  and byte-identical output, gzip included, from two runs on the same input;
- hand-written mocks in `tests/data/mock/` (see `tests/data/README.md`): a multiallelic
  site, a malformed line (the error names line 4), an empty file, a contig naming
  mismatch, records missing CLNSIG or CLNSTARS, and two tiny releases with one
  reclassification, one position-only change, one removal and one addition;
- a Nextflow trace recorded from a real Docker run, and sacct files in the documented
  `--parsable2` format for COMPLETED, OUT_OF_MEMORY, TIMEOUT and CANCELLED jobs.

## Module layer

`tests/nf-test/modules/` runs each process alone with Nextflow 26.10.2 and nf-test 0.9.5.
Snapshots (`*.nf.test.snap`) are committed; a changed output fails the test until the
snapshot is updated on purpose with `nf-test test --update-snapshot`. Covered: BCFTOOLS_NORM
(split and left-align), BCFTOOLS_PREFILTER, CLINVAR_PREPARE, CLINVAR_QUERY_SORTED,
CVNF_CLINVAR_TABLE, CVNF_DIFF, CVNF_FILTER, CVNF_PANEL_PAD, CVNF_VALIDATE (pass and fail),
TABIX_BGZIP. Not yet covered alone: BCFTOOLS_ANNOTATE, CVNF_REPORT, CVNF_DIFF_REPORT and
CVNF_MANIFEST, which run in the pipeline tests.

## Pipeline layer

`tests/pipeline/test_nextflow.py` (marker `pipeline`) and `tests/nf-test/pipeline/`:

- the synthetic sample gives 8 P/LP panel variants and 6 reportable ones, with stars
  0:1, 2:5, 3:2;
- ClinVar 51985 written one base to the right is left-aligned and matched;
- a multiallelic record becomes two records;
- HG002 gives 0 P/LP in the three test genes;
- every `pipeline_info` file exists and the manifest holds a SHA-256 for each input;
- `-resume` reuses all 15 analysis tasks (only the run manifest is rebuilt) and the report
  and table files are byte-identical;
- `-stub-run` completes with all 12 processes of a one-sample run;
- a samplesheet with a bad sample name and missing files is rejected by nf-schema;
- diff mode on the bundled subsets reports reclassifications.

This layer found a real bug on 2026-10-19: one of two samples was silently not annotated
(see operations.md).

## Validation layer

The real runs in results.md check what tests cannot: that the change counts add up to
both release totals (3,878,123 and 4,594,764), that every input matches its published
checksum, and that a whole-panel run on HG002 completes in the measured time and memory.
