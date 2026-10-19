"""End-to-end runs of the Nextflow pipeline on the bundled test data.

Run with `pytest -m pipeline`. Uses the local tools (bcftools, python3 >= 3.11) unless
CVNF_NF_PROFILE adds a container profile, for example CVNF_NF_PROFILE=test,docker.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = os.environ.get("CVNF_NF_PROFILE", "test")

pytestmark = [
    pytest.mark.pipeline,
    pytest.mark.skipif(shutil.which("nextflow") is None, reason="nextflow not on PATH"),
]


def nextflow(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = ["nextflow", "run", str(ROOT / "main.nf"), *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"{' '.join(cmd)} failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"
        )
    return result


def samplesheet(tmp: Path) -> Path:
    # Absolute paths, so the run does not depend on the launch directory.
    sheet = tmp / "samplesheet.csv"
    data = ROOT / "tests" / "data"
    sheet.write_text(
        "sample,vcf,tbi\n"
        f"HG002,{data}/HG002.subset.vcf.gz,{data}/HG002.subset.vcf.gz.tbi\n"
        f"SYNTH01,{data}/SYNTH01.vcf.gz,{data}/SYNTH01.vcf.gz.tbi\n"
    )
    return sheet


def digests(outdir: Path) -> dict[str, str]:
    files = sorted((outdir / "report").glob("*")) + sorted((outdir / "cvnf_filter").glob("*"))
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


@pytest.fixture(scope="module")
def annotate_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("nf_annotate")
    nextflow("-profile", PROFILE, "--input", str(samplesheet(tmp)), "--outdir", "results", cwd=tmp)
    return tmp


def test_synthetic_sample_results(annotate_run: Path) -> None:
    report = json.loads((annotate_run / "results/report/SYNTH01.report.json").read_text())
    assert report["panel_variants"] == 8
    assert report["plp_any_review"] == 8
    assert report["reportable"] == 6
    assert report["plp_by_stars"] == {"0": 1, "1": 0, "2": 5, "3": 2, "4": 0}


def test_right_shifted_deletion_is_left_aligned_and_matched(annotate_run: Path) -> None:
    with (annotate_run / "results/cvnf_filter/SYNTH01.panel_variants.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    deletion = [r for r in rows if r["ref"] == "GC" and r["alt"] == "G"]
    assert len(deletion) == 1
    assert deletion[0]["pos"] == "32316463"
    assert deletion[0]["clinvar_id"] == "51985"


def test_multiallelic_record_is_split(annotate_run: Path) -> None:
    with (annotate_run / "results/cvnf_filter/SYNTH01.panel_variants.tsv").open() as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t") if r["pos"] == "32316462"]
    assert sorted(r["alt"] for r in rows) == ["A", "C"]


def test_hg002_subset_has_no_plp(annotate_run: Path) -> None:
    report = json.loads((annotate_run / "results/report/HG002.report.json").read_text())
    assert report["plp_any_review"] == 0
    assert report["panel_variants"] > 0


def test_pipeline_info_written(annotate_run: Path) -> None:
    info = annotate_run / "results/pipeline_info"
    for name in (
        "execution_trace.txt",
        "execution_report.html",
        "execution_timeline.html",
        "software_versions.yml",
        "run_manifest.json",
    ):
        assert (info / name).is_file(), name
    manifest = json.loads((info / "run_manifest.json").read_text())
    assert manifest["params"]["min_stars"] == 1
    assert all(len(v["sha256"]) == 64 for v in manifest["inputs"].values())


def test_resume_reuses_every_task_and_outputs_are_unchanged(annotate_run: Path) -> None:
    before = digests(annotate_run / "results")
    result = nextflow(
        "-profile",
        PROFILE,
        "--input",
        str(annotate_run / "samplesheet.csv"),
        "--outdir",
        "results",
        "-resume",
        cwd=annotate_run,
    )
    match = re.search(r"completed=(\d+) failed=0 cached=(\d+)", result.stdout)
    assert match is not None
    # Only the run manifest is rebuilt: it records this run's time and params file.
    assert int(match.group(1)) == 1
    assert int(match.group(2)) >= 15
    assert digests(annotate_run / "results") == before


def test_stub_run(tmp_path: Path) -> None:
    result = nextflow(
        "-profile",
        PROFILE,
        "-stub-run",
        "--input",
        str(samplesheet(tmp_path)),
        "--outdir",
        "results",
        cwd=tmp_path,
    )
    assert "SUCCESS" in result.stdout or "Succeeded" in result.stdout or result.returncode == 0


def test_diff_profile(tmp_path: Path) -> None:
    diff_profile = PROFILE.replace("test", "test_diff")
    nextflow("-profile", diff_profile, "--outdir", "results", cwd=tmp_path)
    data = json.loads((tmp_path / "results/clinvar_diff/diff.panel.json").read_text())
    assert data["changes"]["reclassified"] > 0
    assert data["assertion_changes"] >= data["changes"]["reclassified"]


def test_invalid_samplesheet_is_rejected(tmp_path: Path) -> None:
    sheet = tmp_path / "bad.csv"
    sheet.write_text("sample,vcf\nbad name,missing.vcf.gz\n")
    cmd = [
        "nextflow",
        "run",
        str(ROOT / "main.nf"),
        "-profile",
        PROFILE,
        "--input",
        str(sheet),
        "--outdir",
        "results",
    ]
    result = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "sample may contain letters" in result.stdout + result.stderr
