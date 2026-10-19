# Roadmap

## 1.1: subsample calibration

As a pipeline maintainer sizing Slurm requests for a new kind of input, I want a
`--mode calibrate` run that executes each step on 1, 5 and 20 percent of the input and
fits time and peak memory against input size, so that `conf/calibrated.config` predicts
requests for the full input instead of copying one measured run.

Done when: the fit for HG002 genome-wide predicts the 100 percent run's peak RSS within
25 percent, and the prediction and the measurement are both in docs/profiling.md.

## 1.2: export shaped to the public IPR germline upload schema

As a lab that loads germline results into the open-source PORI IPR reporting system, I
want an optional JSON output shaped to match its public germline upload schema
(`app/schemas/germlineSmallMutation/upload.js` in the pori_ipr_api repository: top-level
project, version, source, rows; row fields such as gene, chromosome, position, reference,
alteration, zygosityGermline, clinvar, clinvarIds, gmaf), so that reportable variants load
without a conversion script.

Done when: the output validates against a JSON Schema transcribed from that file, with the
transcription date recorded.

## 1.3: condition-level changes

As a reviewer of past reports, I want changes to condition-specific (RCV) classifications,
which the VCF does not carry, so that a change for one condition is visible even when the
aggregate classification is unchanged. Needs the ClinVar XML or `variant_summary.txt`.

## 1.4: Slurm and Apptainer on a real cluster

Run the real-data commands with `-profile slurm,apptainer,calibrated` on an Alliance
Canada cluster, record sacct output, and replace the hand-written sacct fixtures with
recorded ones.
