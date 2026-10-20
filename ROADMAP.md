# Roadmap

## 1.1: subsample calibration

A `--mode calibrate` run executes each step on 1, 5 and 20 percent of the input, fits
wall time and peak memory against input size, and writes `conf/calibrated.config` from the
fit instead of from one measured run.

Done when the fit for HG002 genome-wide predicts the peak RSS of the full run within 25
percent, with both numbers in docs/profiling.md.

## 1.2: IPR-compatible export

An optional JSON output shaped to match the public germline upload schema of the
open-source PORI IPR reporting system (pori_ipr_api: top-level project, version, source
and rows in `app/schemas/germlineSmallMutation/upload.js`; row fields such as gene,
chromosome, position, reference, alteration, zygosityGermline, clinvar, clinvarIds and
gmaf in `app/models/germlineSmallMutation/variants.js`).

Done when the output validates against a JSON Schema transcribed from that file, with the
transcription date recorded.

## 1.3: condition-level changes

Changes to condition-specific (RCV) classifications, which the VCF does not carry, read
from the ClinVar XML or `variant_summary.txt`, so that a change for one condition shows
even when the aggregate classification is unchanged.

Done when the diff report lists RCV-level changes for the panel genes between the two
releases in docs/results.md.

## 1.4: Slurm and Apptainer on a cluster

The real-data commands run with `-profile slurm,apptainer,calibrated` on an Alliance
Canada cluster.

Done when recorded sacct output replaces the hand-written fixtures in
`tests/fixtures/slurm/`.
