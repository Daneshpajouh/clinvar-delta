# Changelog

## Unreleased

- `cvnf diff --genes` refuses an empty gene list; it used to drop every record and write a
  JSON that read as an unfiltered release with no changes.
- Panel BEDs are read by one function: UCSC `track`, `browser` and `#` lines are skipped in
  validation and reporting as they already were in padding, and a line without a gene
  symbol in column 4 fails validation with its line number instead of crashing `report`.
- Markdown reports escape `|` in cells, so a CLNSIG such as `Pathogenic|risk_factor` stays
  in its column.
- `cvnf profile-sacct` multiplies a per-CPU `ReqMem` (`2000Mc`, Slurm before 21.08) by the
  allocated CPUs.
- `cvnf manifest` refuses an input that is not a readable file instead of leaving it out.
- Validation reads every contig that holds records (from the tabix index, else from all
  records), not only the first record's.
- `run_summary.json` lists output hashes only for a successful run; a failed rerun used to
  report the previous run's files.
- `software_versions.yml` lists each process once, not once per sample.
- `--mode diff` without `--diff_genes` stops with a message; ClinVar preparation stops when
  no ClinVar contig maps onto the reference instead of keeping nothing.
- The samplesheet needs at least one row and `--panel` a `.bed` file.
- `release.yml` runs CI on the tagged commit before it publishes the image and release.
- `scripts/fetch_data.sh` runs the checkout's `bin/cvnf` and accepts a relative DATA_DIR.
- Diff classes are described by the fields that changed; the report no longer says who
  made a change. An empty P/LP section in the panel report says "None.".
- `tests/data/synthetic_records.txt`: the second ALT at chr13:32316462 is ClinVar 51384,
  not a made-up allele.
- Docs: gene-list file name in the diff commands, samplesheet and prerequisites for the
  real-data runs, test counts and coverage, logging examples from a 1.0.1 run, CI status;
  the code walk-through is gone and its design notes are in the README.

## 1.0.1 (2026-10-19)

- Needs Nextflow 26.04.0 or newer; 1.0.0 declared 25.04.0. Releases 25.04 to 26.03 are no
  longer supported: 1.0.0's nf-schema 2.8.0 cannot be installed on 25.04 from an empty
  plugin cache (it is served only by the plugin registry, read from 25.10.0), and its
  manifest requires Nextflow 26.04.0.
- The run summary is a `workflow.onComplete` handler instead of an `onComplete:` section.
- `scripts/test_linux.sh NXF_VER` runs both test profiles in a clean Debian 12 image from
  an empty plugin cache. The README lists `procps` and `tabix`; data terms are recorded as
  read at source.
- Diff mode: the panel filter uses genes from both releases, so a gene renamed or dropped
  in the new release stays in the audit. P/LP losses are credited to the old release's
  genes and gains to the new release's genes. Malformed, repeated or out-of-order rows are
  refused with file and line instead of being skipped or reported as removed. The workflow
  checks it got exactly one pair of ClinVar tables.
- Review stars come from CLNREVSTAT when present; a `.` CLNSTARS no longer crashes.
- The VCF reader requires `#CHROM`, one sample and a fixed column count, and refuses
  unsplit multiallelic records; short ClinVar rows are refused; validation checks gnomAD
  contigs; MT maps to chrM in the panel BED.
- Python steps run the staged `src/cvnf` files, so `-resume` reruns them after a code
  change. The validation join is keyed on sample ID and fails on duplicates or mismatches,
  every input sample must reach the report, and `run_summary.json` lists hashes from this
  run's output channels.
- Renamed from clinvar-variant-nf to clinvar-delta. The Python package keeps the name `cvnf`.
- CI appends the docker profile to nf-test (`--profile +docker`), so each test keeps its own
  profile; the resume test reads task counts from `run_summary.json` instead of the console.
- The release image is tagged with the bare version (`1.0.1`), which `conf/base.config` pulls.

## 1.0.0 (2026-10-19)

First release.

- Annotate mode: prefilter to padded panel, `bcftools norm` split and left-align,
  annotation with ClinVar (with derived review stars and group), gnomAD AF and panel gene;
  per-variant reportability with reasons; per-gene summary; Markdown, HTML and JSON reports.
- Diff mode: Variation ID merge join of two ClinVar releases; labels reclassified,
  review_changed, term_changed, annotation_only, added, removed; whole-release and
  panel-gene reports.
- Profiling: trace, report, timeline and DAG on every run; `cvnf profile-usage`,
  `cvnf profile-calibrate`, `cvnf profile-sacct`; `conf/calibrated.config` from two real runs.
- Run manifest with input SHA-256, parameters, git commit and container images.
- Profiles: standard, docker, apptainer, slurm, calibrated, test, test_diff.
- Tests: 90 unit and CLI tests, 14 nf-test tests, 11 with snapshots, 9 pipeline tests
  including resume and stub runs.
