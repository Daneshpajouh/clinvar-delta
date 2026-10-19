import pytest

from cvnf.annotate import FilterParams, clinvar_table, evaluate, gene_summary, stars_breakdown
from cvnf.report import md_table
from cvnf.vcf import VcfRecord

EXPERT = "reviewed_by_expert_panel"
SINGLE = "criteria_provided,_single_submitter"


def test_clinvar_table_keeps_best_reviewed_duplicate_and_drops_missing_alt() -> None:
    rows = [
        f"chr1\t100\tA\tG\t20\tPathogenic\t{SINGLE}\tG1:1\n",
        f"chr1\t100\tA\tG\t10\tLikely_pathogenic\t{EXPERT}\tG1:1\n",
        f"chr1\t100\tA\t.\t30\tPathogenic\t{SINGLE}\tG1:1\n",
        f"chr1\t200\tC\tT\t40\tBenign\t{SINGLE}\tG1:1\n",
    ]
    out = list(clinvar_table(rows))
    assert len(out) == 2
    assert out[0].split("\t")[4] == "10"
    assert out[0].split("\t")[7:9] == ["3", "PLP"]
    assert out[1].split("\t")[8] == "BLB"


def test_clinvar_table_is_deterministic_for_equal_stars() -> None:
    rows = [
        f"chr1\t100\tA\tG\t20\tPathogenic\t{SINGLE}\tG1:1\n",
        f"chr1\t100\tA\tG\t15\tPathogenic\t{SINGLE}\tG1:1\n",
    ]
    assert next(iter(clinvar_table(rows))).split("\t")[4] == "15"
    assert next(iter(clinvar_table(reversed(rows)))).split("\t")[4] == "15"


def record(info: dict[str, str], gt: str = "0/1") -> VcfRecord:
    return VcfRecord("chr13", 1000, ".", "A", "G", "50", "PASS", info, {"GT": gt})


BASE = {"PANEL_GENE": "BRCA2", "CLNSIG": "Pathogenic", "CLNSTARS": "2", "CLNVID": "5"}


def test_evaluate_reportable() -> None:
    row = evaluate(record(BASE), "S1", FilterParams())
    assert row is not None
    assert row.reportable
    assert row.gnomad_af is None


def test_evaluate_outside_panel_returns_none() -> None:
    assert evaluate(record({"CLNSIG": "Pathogenic"}), "S1", FilterParams()) is None


def test_evaluate_reasons() -> None:
    params = FilterParams(min_stars=2, max_af=0.01)
    low = evaluate(record({**BASE, "CLNSTARS": "1"}), "S1", params)
    common = evaluate(record({**BASE, "gnomAD_AF": "0.2"}), "S1", params)
    hom_ref = evaluate(record(BASE, gt="0/0"), "S1", params)
    assert low is not None
    assert low.reason == "stars 1 < 2"
    assert common is not None
    assert common.reason.startswith("gnomAD AF 0.2")
    assert hom_ref is not None
    assert hom_ref.reason == "genotype has no ALT allele"


def test_evaluate_low_penetrance_switch() -> None:
    info = {**BASE, "CLNSIG": "Pathogenic,_low_penetrance"}
    assert evaluate(record(info), "S1", FilterParams()).reportable  # type: ignore[union-attr]
    excluded = evaluate(record(info), "S1", FilterParams(include_low_penetrance=False))
    assert excluded is not None
    assert not excluded.reportable


def test_gene_summary_lists_every_panel_gene() -> None:
    rows = [{"panel_gene": "BRCA2", "group": "PLP", "stars": "2", "reportable": "yes"}]
    summary = gene_summary(rows, ["BRCA1", "BRCA2"])
    assert [s["gene"] for s in summary] == ["BRCA1", "BRCA2"]
    assert summary[0]["variants"] == 0
    assert summary[1]["plp_stars_2"] == 1
    assert stars_breakdown(rows)["reportable_by_stars"]["2"] == 1


def test_clinvar_table_rejects_short_rows_with_their_number() -> None:
    rows = [f"chr1\t100\tA\tG\t1\tBenign\t{SINGLE}\tG1:1\n", "chr1\t200\tC\n"]
    with pytest.raises(ValueError, match=r"<input>: line 2: expected 8 .* got 3"):
        list(clinvar_table(rows))


def test_clinvar_table_non_numeric_id_loses_ties() -> None:
    rows = [
        f"chr1\t100\tA\tG\tnot_an_id\tPathogenic\t{SINGLE}\tG1:1\n",
        f"chr1\t100\tA\tG\t99\tPathogenic\t{SINGLE}\tG1:1\n",
    ]
    assert next(iter(clinvar_table(rows))).split("\t")[4] == "99"


@pytest.mark.parametrize(
    "positions",
    [[("chr1", 100), ("chr1", 101), ("chr1", 100)], [("chr1", 5), ("chr2", 5), ("chr1", 9)]],
    ids=["position revisited", "chromosome revisited"],
)
def test_clinvar_table_rejects_unsorted_input(positions: list[tuple[str, int]]) -> None:
    rows = [f"{c}\t{p}\tA\tG\t{i}\tBenign\t{SINGLE}\tG1:1\n" for i, (c, p) in enumerate(positions)]
    with pytest.raises(ValueError, match=r"line 3: .* input must be sorted by position"):
        list(clinvar_table(rows))


@pytest.mark.parametrize(
    ("info", "stars"),
    [
        ({"CLNSTARS": "."}, 0),
        ({"CLNSTARS": ""}, 0),
        ({}, 0),
        ({"CLNSTARS": "1", "CLNREVSTAT": EXPERT}, 3),
        ({"CLNSTARS": "2"}, 2),
    ],
    ids=["dot", "empty", "absent", "revstat wins", "stars only"],
)
def test_stars_when_fields_are_missing(info: dict[str, str], stars: int) -> None:
    row = evaluate(
        record({"PANEL_GENE": "BRCA2", "CLNSIG": "Pathogenic", **info}), "S1", FilterParams()
    )
    assert row is not None
    assert row.stars == stars


@pytest.mark.parametrize(
    ("alt", "info"),
    [("G,T", {}), ("G", {"gnomAD_AF": "0.1,0.2"})],
    ids=["two ALT alleles", "vector AF"],
)
def test_unsplit_multiallelic_records_are_refused(alt: str, info: dict[str, str]) -> None:
    rec = VcfRecord("chr13", 1000, ".", "A", alt, "50", "PASS", {**BASE, **info}, {"GT": "0/1"})
    with pytest.raises(ValueError, match=r"chr13:1000:A:.*multiallelic record"):
        evaluate(rec, "S1", FilterParams())


def test_markdown_row_keeps_its_columns_when_clnsig_has_a_pipe() -> None:
    row = md_table(
        ["gene", "clnsig", "stars"], [["HFE", "Pathogenic|risk_factor", 2]]
    ).splitlines()[2]
    assert row == "| HFE | Pathogenic\\|risk_factor | 2 |"
    assert row.replace("\\|", "").count("|") == 4


@pytest.mark.parametrize(
    ("info", "reportable"),
    [
        ({"gnomAD_AF": "0.01"}, True),  # the report says "at most 0.01"
        ({"gnomAD_AF": "0.0101"}, False),
        ({"CLNSTARS": "1"}, True),  # min_stars 1 is met by one star
        ({"CLNSTARS": "0"}, False),
    ],
)
def test_thresholds_are_inclusive(info: dict[str, str], reportable: bool) -> None:
    row = evaluate(record({**BASE, **info}), "S1", FilterParams(min_stars=1, max_af=0.01))
    assert row is not None
    assert row.reportable is reportable
