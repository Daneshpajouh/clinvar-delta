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
    [("empty.vcf", "empty file"), ("malformed.vcf", "line 4: expected 10 tab-separated columns")],
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


def test_malformed_input_is_named_in_the_error_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = MOCK / "malformed.vcf"
    assert run("filter", "--sample", "S1", "--vcf", str(bad), "--out", str(tmp_path / "t.tsv")) == 1
    error = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert error["level"] == "error"
    assert "line 4" in error["error"]
    assert str(bad) in error["inputs"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("##fileformat=VCFv4.2\n##contig=<ID=chr1>\n", "no #CHROM header line"),
        (
            "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB\n",
            "2 samples; one sample per VCF expected",
        ),
        (
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\n"
            "chr1\t5\t.\tA\tG\t.\t.\t.\tGT\t0/1\textra\n",
            "line 2: expected 10 .* got 11",
        ),
    ],
    ids=["metadata only", "two samples", "extra column"],
)
def test_vcf_structure_errors_name_the_file(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "in.vcf"
    path.write_text(text)
    with open_text(path) as handle, pytest.raises(VcfFormatError, match=f"{path}: {message}"):
        list(read_vcf(handle, str(path)).records)


HEAD = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
SITES = HEAD + "\n{c}\t100\t.\tA\tG\t.\t.\tAF=0.1\n"
SAMPLE = HEAD + "\tFORMAT\tS1\n{c}\t100\t.\tA\tG\t.\t.\t.\tGT\t0/1\n"


@pytest.mark.parametrize(
    ("ref", "vcf", "panel", "gnomad", "problem"),
    [
        ("chr1", "chr1", "chr1", "chr1", None),
        ("1", "1", "1", "1", None),
        ("chr1", "1", "chr1", "chr1", "VCF contigs missing from reference: 1"),
        ("chr1", "chr1", "1", "chr1", "panel contigs missing from reference: 1"),
        ("chr1", "chr1", "chr1", "1", "gnomAD contigs missing from reference: 1"),
        ("1", "chr1", "1", "1", "VCF contigs missing from reference: chr1"),
    ],
    ids=[
        "all chr",
        "all bare",
        "bare VCF",
        "bare panel",
        "bare gnomAD",
        "chr VCF on bare reference",
    ],
)
def test_validate_contig_style_of_every_input(  # noqa: PLR0917 (one parametrize row per case)
    tmp_path: Path, ref: str, vcf: str, panel: str, gnomad: str, problem: str | None
) -> None:
    (tmp_path / "ref.fai").write_text(f"{ref}\t1000\t0\t60\t61\n")
    (tmp_path / "s.vcf").write_text(SAMPLE.format(c=vcf))
    (tmp_path / "p.bed").write_text(f"{panel}\t50\t300\tGENE1\n")
    (tmp_path / "g.vcf").write_text(SITES.format(c=gnomad))
    out = tmp_path / "v.json"
    code = run(
        "validate",
        "--sample",
        "S1",
        "--vcf",
        str(tmp_path / "s.vcf"),
        "--fai",
        str(tmp_path / "ref.fai"),
        "--panel",
        str(tmp_path / "p.bed"),
        "--gnomad",
        str(tmp_path / "g.vcf"),
        "--out",
        str(out),
    )
    assert json.loads(out.read_text())["problems"] == ([problem] if problem else [])
    assert code == (1 if problem else 0)


def validate_with_panel(tmp_path: Path, panel_text: str) -> tuple[int, dict[str, object]]:
    panel = tmp_path / "panel.bed"
    panel.write_text(panel_text)
    out = tmp_path / "v.json"
    code = run(
        "validate",
        "--sample",
        "S1",
        "--vcf",
        str(MOCK / "multiallelic.vcf"),
        "--fai",
        str(MOCK / "reference.fa.fai"),
        "--panel",
        str(panel),
        "--out",
        str(out),
    )
    return code, json.loads(out.read_text())


def test_validate_skips_ucsc_header_lines_in_the_panel(tmp_path: Path) -> None:
    code, result = validate_with_panel(
        tmp_path, 'track name="ACMG SF"\n# chrom start end gene\nchr1\t50\t300\tGENE1\n'
    )
    assert code == 0
    assert result["panel_contigs"] == ["chr1"]


def test_validate_refuses_a_panel_without_gene_symbols(tmp_path: Path) -> None:
    code, result = validate_with_panel(tmp_path, "chr1\t50\t300\n")
    assert code == 1
    assert result["problems"] == [
        f"{tmp_path / 'panel.bed'}: line 1: expected chrom, start, end and gene symbol "
        "separated by tabs, got 'chr1\\t50\\t300'"
    ]


def test_report_reads_gene_names_past_a_track_line(tmp_path: Path) -> None:
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
    panel = tmp_path / "panel.bed"
    panel.write_text("track name=panel\n" + (MOCK / "panel.bed").read_text())
    paths = {k: tmp_path / f"r.{k}" for k in ("tsv", "json", "md", "html")}
    code = run(
        "report",
        "--sample",
        "S1",
        "--table",
        str(table),
        "--panel",
        str(panel),
        "--summary",
        str(paths["tsv"]),
        "--json",
        str(paths["json"]),
        "--markdown",
        str(paths["md"]),
        "--html",
        str(paths["html"]),
    )
    assert code == 0
    assert json.loads(paths["json"].read_text())["panel_genes"] == 1


def test_manifest_hashes_each_input_and_refuses_a_missing_one(tmp_path: Path) -> None:
    bed = tmp_path / "brca1.bed"
    bed.write_text("chr17\t43044294\t43125483\tBRCA1\n")
    out = tmp_path / "m.json"
    assert run("manifest", "--engine", "nextflow 24.10.4", "--out", str(out), str(bed)) == 0
    # Digest taken with `shasum -a 256` on the same 30 bytes.
    assert json.loads(out.read_text())["inputs"] == {
        "brca1.bed": {
            "sha256": "b5e0b25d6769ca8ef877452dc9e54f6019299a37c8ea0990b298e9651d973de0",
            "bytes": 30,
        }
    }
    missing = tmp_path / "gone.vcf.gz"
    assert (
        run("manifest", "--engine", "nextflow 24.10.4", "--out", str(out), str(bed), str(missing))
        == 1
    )
