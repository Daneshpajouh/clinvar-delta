"""Job profiling: Nextflow trace usage report and Slurm sacct parsing.

Nextflow writes requested resources (cpus, memory, time) and measured usage (%cpu,
peak_rss, realtime) per task into the trace file. The usage report compares the two
per process and flags waste and failures. The sacct parser reads `--parsable2` output so
the same comparison can be made for jobs submitted by any tool.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO

_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
_SLURM_UNITS = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}


def parse_size(value: str) -> float | None:
    """Parse Nextflow sizes such as '1.5 GB' or '200 MB' into bytes."""
    value = value.strip()
    if value in {"", "-"}:
        return None
    match = re.fullmatch(r"([\d.]+)\s*([KMGT]?B)", value)
    if not match:
        return None
    return float(match.group(1)) * _UNITS[match.group(2)]


def parse_duration(value: str) -> float | None:
    """Parse Nextflow durations such as '1h 2m 3s', '450ms' or '2.5s' into seconds."""
    value = value.strip()
    if value in {"", "-"}:
        return None
    total = 0.0
    for number, unit in re.findall(r"([\d.]+)\s*(ms|s|m|h|d)", value):
        total += float(number) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return total


def parse_percent(value: str) -> float | None:
    value = value.strip().rstrip("%")
    return None if value in {"", "-"} else float(value)


@dataclass
class TaskUsage:
    process: str
    name: str
    status: str
    exit: str
    attempt: int
    cpus: float | None
    cpu_percent: float | None
    memory: float | None
    peak_rss: float | None
    time: float | None
    realtime: float | None


def read_trace(handle: TextIO) -> list[TaskUsage]:
    tasks = []
    for row in csv.DictReader(handle, delimiter="\t"):
        tasks.append(
            TaskUsage(
                process=row.get("process") or row.get("name", "?").split(" (")[0],
                name=row.get("name", ""),
                status=row.get("status", ""),
                exit=row.get("exit", ""),
                attempt=int(row.get("attempt") or 1),
                cpus=float(row["cpus"]) if row.get("cpus", "-") not in {"", "-"} else None,
                cpu_percent=parse_percent(row.get("%cpu", "-")),
                memory=parse_size(row.get("memory", "-")),
                peak_rss=parse_size(row.get("peak_rss", "-")),
                time=parse_duration(row.get("time", "-")),
                realtime=parse_duration(row.get("realtime", "-")),
            )
        )
    return tasks


@dataclass
class ProcessSummary:
    process: str
    tasks: int
    failed: int
    retried: int
    cpus_requested: float | None
    cpu_efficiency: float | None
    memory_requested: float | None
    peak_rss_max: float | None
    memory_used_fraction: float | None
    time_requested: float | None
    realtime_max: float | None
    time_used_fraction: float | None
    flags: list[str]


def _ratio(used: float | None, requested: float | None) -> float | None:
    if used is None or not requested:
        return None
    return used / requested


def summarise(
    tasks: Iterable[TaskUsage], waste_below: float = 0.25, near_above: float = 0.9
) -> list[ProcessSummary]:
    """Summarise tasks per process.

    Flags: 'memory waste' when the largest task used less than `waste_below` of its
    request, 'memory near limit' above `near_above`, the same for time, 'low CPU use'
    when mean CPU efficiency is below `waste_below`, and failures or retries.
    """
    groups: dict[str, list[TaskUsage]] = defaultdict(list)
    for task in tasks:
        groups[task.process].append(task)
    out = []
    for process, items in sorted(groups.items()):
        done = [t for t in items if t.status in {"COMPLETED", "CACHED"}]
        failed = sum(1 for t in items if t.status == "FAILED")
        retried = sum(1 for t in items if t.attempt > 1)
        ref = done or items
        cpus = max((t.cpus for t in ref if t.cpus), default=None)
        effs = [t.cpu_percent / 100 / t.cpus for t in done if t.cpu_percent is not None and t.cpus]
        mem_req = max((t.memory for t in ref if t.memory), default=None)
        rss = max((t.peak_rss for t in done if t.peak_rss is not None), default=None)
        time_req = max((t.time for t in ref if t.time), default=None)
        real = max((t.realtime for t in done if t.realtime is not None), default=None)
        mem_frac = _ratio(rss, mem_req)
        time_frac = _ratio(real, time_req)
        cpu_eff = sum(effs) / len(effs) if effs else None
        flags = []
        if mem_frac is not None and mem_frac < waste_below:
            flags.append("memory waste")
        if mem_frac is not None and mem_frac > near_above:
            flags.append("memory near limit")
        if time_frac is not None and time_frac > near_above:
            flags.append("time near limit")
        if cpu_eff is not None and cpu_eff < waste_below and (cpus or 1) > 1:
            flags.append("low CPU use")
        if failed:
            flags.append(f"{failed} failed")
        if retried:
            flags.append(f"{retried} retried")
        out.append(
            ProcessSummary(
                process,
                len(items),
                failed,
                retried,
                cpus,
                cpu_eff,
                mem_req,
                rss,
                mem_frac,
                time_req,
                real,
                time_frac,
                flags,
            )
        )
    return out


def fmt_bytes(value: float | None) -> str:
    if value is None:
        return "-"
    for unit in ("GB", "MB", "KB"):
        if value >= _UNITS[unit]:
            return f"{value / _UNITS[unit]:.1f} {unit}"
    return f"{value:.0f} B"


def fmt_pct(value: float | None) -> str:
    return "-" if value is None else f"{100 * value:.1f}%"


def fmt_secs(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}s"


# --- Slurm -----------------------------------------------------------------------------

SACCT_FIELDS = (
    "JobID",
    "JobName",
    "State",
    "ExitCode",
    "Elapsed",
    "Timelimit",
    "AllocCPUS",
    "TotalCPU",
    "ReqMem",
    "MaxRSS",
)


def slurm_seconds(value: str) -> float | None:
    """Parse Slurm times: [DD-][HH:]MM:SS[.mmm]; 'UNLIMITED' and empty give None."""
    value = value.strip()
    if not value or value in {"UNLIMITED", "Partition_Limit", "INVALID"}:
        return None
    days = 0
    if "-" in value:
        d, value = value.split("-", 1)
        days = int(d)
    parts = [float(p) for p in value.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return days * 86400 + h * 3600 + m * 60 + s


def slurm_bytes(value: str) -> float | None:
    """Parse Slurm memory such as '1234K', '4G' or older '4000Mn' / '2Gc' ReqMem forms."""
    value = value.strip()
    if not value:
        return None
    match = re.fullmatch(r"([\d.]+)([KMGT]?)([nc]?)", value)
    if not match:
        return None
    number, unit, _scope = match.groups()
    return float(number) * (_SLURM_UNITS[unit] if unit else 1)


@dataclass
class SlurmStep:
    job_id: str
    name: str
    state: str
    exit_code: str
    elapsed: float | None
    timelimit: float | None
    alloc_cpus: int
    total_cpu: float | None
    req_mem: float | None
    max_rss: float | None

    @property
    def cpu_efficiency(self) -> float | None:
        if not self.elapsed or not self.alloc_cpus or self.total_cpu is None:
            return None
        return self.total_cpu / (self.elapsed * self.alloc_cpus)


def parse_sacct(text: str) -> list[SlurmStep]:
    """Parse `sacct --parsable2 --noheader --format=<SACCT_FIELDS>` output."""
    steps = []
    for line in text.splitlines():
        if not line.strip():
            continue
        cols = line.split("|")
        if len(cols) != len(SACCT_FIELDS):
            raise ValueError(f"expected {len(SACCT_FIELDS)} fields, got {len(cols)}: {line!r}")
        rec = dict(zip(SACCT_FIELDS, cols, strict=True))
        steps.append(
            SlurmStep(
                job_id=rec["JobID"],
                name=rec["JobName"],
                state=rec["State"].split(" ")[0],
                exit_code=rec["ExitCode"],
                elapsed=slurm_seconds(rec["Elapsed"]),
                timelimit=slurm_seconds(rec["Timelimit"]),
                alloc_cpus=int(rec["AllocCPUS"] or 0),
                total_cpu=slurm_seconds(rec["TotalCPU"]),
                req_mem=slurm_bytes(rec["ReqMem"]),
                max_rss=slurm_bytes(rec["MaxRSS"]),
            )
        )
    return steps


def slurm_job_rows(steps: list[SlurmStep]) -> list[dict[str, str]]:
    """One row per job: requested values from the allocation line, peak RSS from steps."""
    jobs: dict[str, dict[str, object]] = {}
    for step in steps:
        base = step.job_id.split(".")[0]
        job = jobs.setdefault(
            base,
            {
                "job": base,
                "name": step.name,
                "state": step.state,
                "elapsed": step.elapsed,
                "timelimit": step.timelimit,
                "req_mem": step.req_mem,
                "max_rss": None,
                "cpu_eff": step.cpu_efficiency,
            },
        )
        if "." not in step.job_id:
            job.update(
                name=step.name,
                state=step.state,
                elapsed=step.elapsed,
                timelimit=step.timelimit,
                req_mem=step.req_mem,
            )
        if step.max_rss is not None:
            prev = job["max_rss"]
            job["max_rss"] = step.max_rss if prev is None else max(float(str(prev)), step.max_rss)
        if step.job_id.endswith(".batch") and step.cpu_efficiency is not None:
            job["cpu_eff"] = step.cpu_efficiency
    rows = []
    for job in jobs.values():
        req = job["req_mem"]
        rss = job["max_rss"]
        mem_frac = None if req is None or rss is None else float(str(rss)) / float(str(req))
        el, tl = job["elapsed"], job["timelimit"]
        time_frac = None if el is None or tl is None else float(str(el)) / float(str(tl))
        flags = []
        if job["state"] in {"OUT_OF_MEMORY", "TIMEOUT", "FAILED", "NODE_FAIL", "CANCELLED"}:
            flags.append(str(job["state"]).lower())
        if mem_frac is not None and mem_frac < 0.25:
            flags.append("memory waste")
        rows.append(
            {
                "job": str(job["job"]),
                "name": str(job["name"]),
                "state": str(job["state"]),
                "memory_used": fmt_pct(mem_frac),
                "time_used": fmt_pct(time_frac),
                "cpu_efficiency": fmt_pct(
                    job["cpu_eff"] if isinstance(job["cpu_eff"], float) else None
                ),
                "flags": ", ".join(flags) or "-",
            }
        )
    return rows
