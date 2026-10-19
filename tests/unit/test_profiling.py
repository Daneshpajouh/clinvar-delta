from pathlib import Path

import pytest

from cvnf.profiling import (
    calibrated_config,
    parse_duration,
    parse_sacct,
    parse_size,
    read_trace,
    slurm_bytes,
    slurm_job_rows,
    slurm_seconds,
    summarise,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize(
    ("text", "value"), [("1 GB", 1024**3), ("17.7 MB", 17.7 * 1024**2), ("-", None)]
)
def test_parse_size(text: str, value: float | None) -> None:
    assert parse_size(text) == value


@pytest.mark.parametrize(
    ("text", "value"), [("30m", 1800), ("1h 2m 3s", 3723), ("121ms", 0.121), ("-", None)]
)
def test_parse_duration(text: str, value: float | None) -> None:
    assert (
        parse_duration(text) == pytest.approx(value)
        if value is not None
        else parse_duration(text) is None
    )


def test_recorded_trace_summary() -> None:
    # Trace recorded from `nextflow run . -profile test,docker` on 2026-10-19.
    with (FIXTURES / "nextflow_trace_test_docker.txt").open() as handle:
        tasks = read_trace(handle)
    assert len(tasks) == 15
    summary = {s.process: s for s in summarise(tasks)}
    norm = summary["ANNOTATE:BCFTOOLS_NORM"]
    assert norm.tasks == 2
    assert norm.memory_requested == 4 * 1024**3
    assert norm.memory_used_fraction is not None
    assert norm.memory_used_fraction < 0.25
    assert "memory waste" in norm.flags


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("00:04:10", 250),
        ("1-00:00:12", 86412),
        ("00:12:29.512", 749.512),
        ("00:00.001", 0.001),
        ("UNLIMITED", None),
    ],
)
def test_slurm_seconds(text: str, seconds: float | None) -> None:
    assert slurm_seconds(text) == (pytest.approx(seconds) if seconds is not None else None)


@pytest.mark.parametrize(
    ("text", "value"),
    [("812340K", 812340 * 1024), ("4G", 4 * 1024**3), ("8000Mn", 8000 * 1024**2), ("", None)],
)
def test_slurm_bytes(text: str, value: float | None) -> None:
    assert slurm_bytes(text) == value


def test_sacct_fixture_rows() -> None:
    steps = parse_sacct((FIXTURES / "slurm" / "sacct_parsable2.txt").read_text())
    assert len(steps) == 9
    rows = {r["job"]: r for r in slurm_job_rows(steps)}
    assert rows["1001"]["state"] == "COMPLETED"
    assert rows["1001"]["memory_used"] == "19.4%"
    assert "memory waste" in rows["1001"]["flags"]
    assert rows["1002"]["flags"].startswith("out_of_memory")
    assert rows["1003"]["state"] == "TIMEOUT"
    assert rows["1003"]["time_used"] == "100.0%"


def test_sacct_wrong_field_count_raises() -> None:
    with pytest.raises(ValueError, match="expected 10 fields"):
        parse_sacct("1|2|3\n")


def test_calibrated_config_from_recorded_trace() -> None:
    with (FIXTURES / "nextflow_trace_test_docker.txt").open() as handle:
        summaries = summarise(read_trace(handle))
    config = calibrated_config(summaries, source="fixture")
    assert config.count("withName") == len(summaries)
    # Every recorded task here peaked far below 128 MB, so the floors apply.
    assert "memory = { 256.MB * task.attempt }" in config
    assert "time = { 10.min * task.attempt }" in config
    assert config.rstrip().endswith("}")


def test_per_cpu_memory_request_counts_every_cpu() -> None:
    # sacct from Slurm 20.11: 2000 MiB per CPU on 4 CPUs is an 8000 MiB request.
    line = "2001|nf-BCFTOOLS_NORM_HG002|COMPLETED|0:0|00:10:00|01:00:00|4|00:30:00|2000Mc|"
    (step,) = parse_sacct(line)
    assert step.req_mem == 8000 * 1024**2
