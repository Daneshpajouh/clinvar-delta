# Changelog

## 1.0.1 (2026-10-19)

- Needs Nextflow 26.04.0 or newer; 1.0.0 declared 25.04.0. Releases 25.04 to 26.03 are no
  longer supported: 1.0.0's nf-schema 2.8.0 cannot be installed on 25.04 from an empty
  plugin cache (it is served only by the plugin registry, read from 25.10.0), and its
  manifest requires Nextflow 26.04.0. A pin to 2.5.1, tried during this release, made
  numeric options such as `--max_cpus 8` fail validation on 26.10 as strings.
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
- Tests: 90 unit and CLI tests, 14 nf-test tests with snapshots, 9 pipeline tests
  including resume and stub runs.
