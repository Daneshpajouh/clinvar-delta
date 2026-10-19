# Logging

Examples are from `nextflow run . -profile test -ansi-log false --outdir results_test2`
on 2026-10-19.

## Run manifest

`pipeline_info/run_manifest.json` is written by the first task to start (CVNF_MANIFEST
needs only the input list): SHA-256 and size of every input, all parameters, the git
commit, the Nextflow version, the run start time and the container image per tool label
(the bcftools image is pinned by digest).

```json
"engine": "nextflow 26.10.2",
"run_started": "2026-10-19T11:59:39.367056-07:00",
"inputs": {"clinvar_20261011.subset.vcf.gz": {"bytes": 644594, "sha256": "..."}}
```

## Task logs and progress

- `-ansi-log false` prints one line per task as it is submitted, for example
  `[PROCESS 27/339e47] ANNOTATE:CVNF_REPORT (SYNTH01)`.
- `pipeline_info/execution_trace.txt` gains a row as each task finishes (status, exit,
  attempt, realtime, peak RSS); `tail -f` it to follow a long run.
- Each task directory keeps `.command.sh`, `.command.log`, `.command.err` and
  `.command.trace`. The `cvnf` steps log JSON lines with a UTC timestamp and level:

```json
{"command": "filter", "event": "start", "level": "info", "ts": "2026-10-19T18:21:25Z", "version": "1.0.0"}
{"event": "filter", "level": "info", "panel_variants": 8, "reportable": 6, "sample": "SYNTH01", "ts": "..."}
```

  A failing step logs the error and the files it was given:

```json
{"command": "filter", "error": "line 4: expected 8+ tab-separated columns with a numeric POS", "event": "failed", "inputs": ["tests/data/mock/malformed.vcf", ...], "level": "error", ...}
```

## Run summary

The workflow's `onComplete` handler writes `pipeline_info/run_summary.json` after success
and after failure: status, start and end time, duration, task counts (succeeded, cached,
failed, retried), the error message, and every published file with its SHA-256.

```json
{"status": "success", "duration_ms": 3955, "nextflow": "26.10.2",
 "tasks": {"succeeded": 18, "cached": 0, "failed": 0, "ignored": 0, "retried": 0},
 "error": null,
 "outputs": {"bcftools_annotate/HG002.annotated.vcf.gz": "46243989a07c...", "...": "..."}}
```

Nextflow also writes `execution_report.html`, `execution_timeline.html` and
`pipeline_dag.html`, and keeps `.nextflow.log` in the launch directory. The per-process
resource table comes from `cvnf profile-usage` (profiling.md).
