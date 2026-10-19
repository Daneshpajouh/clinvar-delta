# Changelog

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
- Tests: 88 unit and CLI tests, 14 nf-test tests with snapshots, 9 pipeline tests
  including resume and stub runs.
