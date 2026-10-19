"""CLI behaviour on the hand-written files in tests/data/mock (see tests/data/README.md)."""

import csv
import json
from pathlib import Path

import pytest

from cvnf.cli import main
from cvnf.vcf import VcfFormatError, open_text, read_vcf

MOCK = Path(__file__).resolve().parents[1] / "data" / "mock"


def run(*args: str) -> int:
    return main(list(args))


@pytest.mark.parametrize(
    ("vcf", "status", "problem"),
    [
        ("multiallelic.vcf", 0, None),
        ("no_chr_prefix.vcf", 1, "VCF contigs missing from reference: 1"),
    ],
)
def test_validate(tmp_path: Path, vcf: str, status: int, problem: str | None) -> None:
    out = tmp_path / "v.json"
    code = run(
        "validate",
        "--sample",
        "S1",
        "--vcf",
        str(MOCK / vcf),
        "--fai",
        str(MOCK / "reference.fa.fai"),
        "--panel",
        str(MOCK / "panel.bed"),
        "--out",
        str(out),
    )
    assert code == status
    problems = json.loads(out.read_text())["problems"]
    assert problems == ([problem] if problem else [])


@pytest.mark.parametrize(
    ("vcf", "message"),
    [("empty.vcf", "empty file"), ("malformed.vcf", "line 4: expected 8+")],
)
def test_bad_vcf_raises_with_location(vcf: str, message: str) -> None:
    with open_text(MOCK / vcf) as handle, pytest.raises(VcfFormatError, match=message):
        list(read_vcf(handle).records)


def test_filter_handles_missing_clinvar_fields(tmp_path: Path) -> None:
    out = tmp_path / "t.tsv"
    assert (
        run(
            "filter",
            "--sample",
            "S1",
            "--vcf",
            str(MOCK / "missing_clinvar_fields.vcf"),
            "--out",
            str(out),
        )
        == 0
    )
    with out.open() as handle:
        rows = {r["clinvar_id"]: r for r in csv.DictReader(handle, delimiter="\t")}
    # No CLNSIG: treated as no germline classification, never reportable.
    assert rows["11"]["group"] == "NONE"
    assert rows["11"]["reportable"] == "no"
    # CLNSIG without CLNSTARS: zero stars, below the default minimum of one.
    assert rows["12"]["stars"] == "0"
    assert rows["12"]["reason"] == "stars 0 < 1"
    assert rows["13"]["reportable"] == "yes"


def test_report_on_mock_table(tmp_path: Path) -> None:
    table = tmp_path / "t.tsv"
    run(
        "filter",
        "--sample",
        "S1",
        "--vcf",
        str(MOCK / "missing_clinvar_fields.vcf"),
        "--out",
        str(table),
    )
    paths = {k: tmp_path / f"r.{k}" for k in ("tsv", "json", "md", "html")}
    assert (
        run(
            "report",
            "--sample",
            "S1",
            "--table",
            str(table),
            "--panel",
            str(MOCK / "panel.bed"),
            "--summary",
            str(paths["tsv"]),
            "--json",
            str(paths["json"]),
            "--markdown",
            str(paths["md"]),
            "--html",
            str(paths["html"]),
        )
        == 0
    )
    data = json.loads(paths["json"].read_text())
    assert data["reportable"] == 1
    assert data["plp_by_stars"] == {"0": 1, "1": 0, "2": 0, "3": 1, "4": 0}
    assert "| GENE1 | chr1 | 200 | G | A | 1/1 | Likely_pathogenic | 3 |" in paths["md"].read_text()
    assert paths["html"].read_text().startswith("<!doctype html>")


def test_diff_on_mock_releases(tmp_path: Path) -> None:
    out, js = tmp_path / "c.tsv", tmp_path / "c.json"
    assert (
        run(
            "diff",
            "--old",
            str(MOCK / "release_old.tsv"),
            "--new",
            str(MOCK / "release_new.tsv"),
            "--old-label",
            "old",
            "--new-label",
            "new",
            "--out",
            str(out),
            "--json",
            str(js),
        )
        == 0
    )
    with out.open() as handle:
        changes = {r["variation_id"]: r for r in csv.DictReader(handle, delimiter="\t")}
    assert changes["1"]["change"] == "reclassified"
    assert (changes["1"]["old_group"], changes["1"]["new_group"]) == ("VUS", "PLP")
    assert changes["2"]["change"] == "annotation_only"
    assert changes["3"]["change"] == "removed"
    assert changes["4"]["change"] == "added"
    data = json.loads(js.read_text())
    assert data["assertion_changes"] == 1
    assert data["annotation_changes"] == 1
