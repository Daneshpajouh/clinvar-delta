# Logging

Examples are from `nextflow run . -profile test,docker -ansi-log false` on 2026-10-19 at
17:05 Pacific (cvnf 1.0.1, Nextflow 26.10.2).

## Run manifest

`pipeline_info/run_manifest.json` is written by the first task to start (CVNF_MANIFEST
needs only the input list): SHA-256 and size of every input, all parameters, the git
commit, the Nextflow version, the run start time and the container image per tool label
(the bcftools image is pinned by digest).

```json
"engine": "nextflow 26.10.2",
"run_started": "2026-10-19T17:05:25.272398-07:00",
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
{"command": "filter", "event": "start", "level": "info", "ts": "2026-10-20T00:05:38Z", "version": "1.0.1"}
{"event": "filter", "level": "info", "panel_variants": 145, "reportable": 0, "sample": "HG002", "ts": "2026-10-20T00:05:38Z"}
```

  A failing step logs the error and the files it was given:

```json
{"command": "filter", "error": "tests/data/mock/malformed.vcf: line 4: expected 10 tab-separated columns with a numeric POS, got 4", "event": "failed", "inputs": [...], "level": "error", ...}
```

## Run summary

The workflow's `onComplete` handler writes `pipeline_info/run_summary.json` after success
and after failure: status, start and end time, duration, task counts (succeeded, cached,
failed, retried), the error message, and the SHA-256 and size of each file this run
produced. The list comes from `pipeline_info/outputs.sha256.json`, written by
CVNF_OUTPUT_HASHES from the output channels, so files left in the output directory by
earlier runs are not included. After a failure the list is empty, because the file in the
output directory would be the previous run's.

```json
{"status": "success", "duration_ms": 17192, "nextflow": "26.10.2",
 "tasks": {"succeeded": 19, "cached": 0, "failed": 0, "ignored": 0, "retried": 0},
 "error": null,
 "outputs": {"HG002.annotated.vcf.gz": {"bytes": "...", "sha256": "..."}, "...": "..."}}
```

Nextflow also writes `execution_report.html`, `execution_timeline.html` and
`pipeline_dag.html`, and keeps `.nextflow.log` in the launch directory. The per-process
resource table comes from `cvnf profile-usage` (profiling.md).
