# Profiling: before, during and after a run

Every run writes `execution_trace.txt`, `execution_report.html` and
`execution_timeline.html` to `results/pipeline_info/`. The trace has one row per task with
the request (`cpus`, `memory`, `time`) next to the measurement (`%cpu`, `peak_rss`,
`realtime`, `rchar`, `wchar`, `attempt`, `exit`).

On macOS without a container engine Nextflow cannot read task metrics (it warns "Task
runtime metrics are not reported"), so measured runs here use `-profile docker`.

## Before submission: size the requests from a measured run

```bash
cvnf profile-calibrate \
  --trace results/hg002_annotate/pipeline_info/execution_trace.txt \
  --trace results/clinvar_diff/pipeline_info/execution_trace.txt \
  --out conf/calibrated.config
nextflow run . -profile slurm,apptainer,calibrated ...
```

Requests are `max(256 MB, peak_rss x 2)` and `max(10 min, realtime x 4)`, both multiplied by
`task.attempt`. The committed `conf/calibrated.config` comes from the two real runs in
[results.md](results.md). Measured peaks from those runs:

| Process | Tasks | Peak RSS | Longest realtime | Requested by label | Memory used |
|---|---|---|---|---|---|
| CLINVAR_QUERY_SORTED | 2 | 611.9 MB | 45.0 s | 4 GB, 2 h | 14.9% |
| CLINVAR_PREPARE | 1 | 97.9 MB | 16.0 s | 4 GB, 2 h | 2.4% |
| BCFTOOLS_ANNOTATE | 1 | 63.1 MB | 3.0 s | 4 GB, 2 h | 1.5% |
| BCFTOOLS_PREFILTER | 1 | 47.3 MB | 1.0 s | 2 GB, 1 h | 2.3% |
| BCFTOOLS_NORM | 1 | 27.0 MB | 1.0 s | 4 GB, 2 h | 0.7% |
| CVNF_DIFF_ALL | 1 | 24.9 MB | 31.2 s | 2 GB, 1 h | 1.2% |
| CVNF_DIFF_PANEL | 1 | 24.4 MB | 15.8 s | 2 GB, 1 h | 1.2% |

The default labels ask for 7 to 150 times the memory these tasks use, which on a shared Slurm cluster delays scheduling and wastes allocation.
`CVNF_DIFF_ALL` reads 4.6 million plus 3.9 million records in 25 MB: the inputs are sorted
by Variation ID in `CLINVAR_QUERY_SORTED` (where `sort` spends the 612 MB) and the Python
step is a streaming merge join, so its memory does not grow with release size.

Calibrating from one input size assumes the next input is similar. For a different panel or
a whole-genome run, measure again: the planned subsample calibration (1, 5 and 20 percent
of the input, fitted against input size) is milestone 1.1 in ROADMAP.md.

## During the run

- `tail -f results/pipeline_info/execution_trace.txt` shows each task as it finishes,
  with its peak RSS and exit code.
- On Slurm, `squeue -u $USER -o '%i %j %T %M %l %m %C'` lists Nextflow's jobs (names start
  with `nf-` and the process name) with elapsed time, limit, memory and CPUs.
- For a running job, `sstat -j <jobid>.batch --format=JobID,MaxRSS,AveCPU` gives the live
  peak memory of the batch step.

## After the run

```bash
cvnf profile-usage --trace results/pipeline_info/execution_trace.txt \
  --markdown usage.md --html usage.html
```

Per process it reports requested CPUs and mean CPU efficiency, requested memory against the
largest peak RSS, requested time against the longest realtime, and flags: `memory waste`
(under 25% used), `memory near limit` or `time near limit` (over 90%), `low CPU use`,
`CPU above request` (over 110%: the task used more cores than it asked for, which cgroup
limits on a cluster would throttle), and counts of failed and retried tasks.

On the real annotate run every process was flagged `memory waste`, and
`BCFTOOLS_PREFILTER`, `BCFTOOLS_NORM` and `BCFTOOLS_ANNOTATE` were flagged `CPU above
request` (305%, 273% and 144% of their CPU request). These tasks ran for 1 to 3 seconds, so
the CPU figures are noisy; the memory figures are not.

For jobs on Slurm, the same comparison comes from accounting data:

```bash
sacct -j 1001,1002 --parsable2 --noheader \
  --format=JobID,JobName,State,ExitCode,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS > sacct.txt
cvnf profile-sacct --input sacct.txt
```

This reports memory and time used against the request, CPU efficiency
(TotalCPU / (Elapsed x AllocCPUS)) and flags OUT_OF_MEMORY, TIMEOUT, FAILED and CANCELLED
jobs. The parser is tested against hand-written files in the documented `--parsable2`
format (`tests/fixtures/slurm/`); it has not yet been run against a real cluster.

## Retries

`conf/base.config` retries a task twice, with memory and time multiplied by the attempt
number, only when it exits with 137 (killed, usually out of memory) or 140 (Slurm or SGE
time limit). Other exit codes stop the run, because retrying a real error wastes
allocation and hides the cause. `resourceLimits` caps every request at `--max_cpus`,
`--max_memory` and `--max_time`.
