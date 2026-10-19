import gzip
import json
from pathlib import Path

import pytest

from cvnf.cli import main
from cvnf.diff import (
    DiffStats,
    Entry,
    ParseCounts,
    accumulate,
    classify_change,
    diff_releases,
    parse_entries,
)

EXPERT = "reviewed_by_expert_panel"
SINGLE = "criteria_provided,_single_submitter"
MULTI = "criteria_provided,_multiple_submitters,_no_conflicts"
CONFLICT = "criteria_provided,_conflicting_classifications"


def entry(
    vid: int, clnsig: str, revstat: str = SINGLE, pos: str = "100", gene: str = "BRCA2"
) -> Entry:
    return Entry(vid, "13", pos, "A", "G", clnsig, revstat, (gene,))


def row(
    vid: int, clnsig: str, revstat: str = SINGLE, pos: str = "100", gene: str = "BRCA2:675"
) -> str:
    return f"{vid}\t13\t{pos}\tA\tG\t{clnsig}\t{revstat}\t{gene}\n"


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (None, entry(1, "Pathogenic"), "added"),
        (entry(1, "Pathogenic"), None, "removed"),
        (entry(1, "Uncertain_significance"), entry(1, "Likely_pathogenic"), "reclassified"),
        (
            entry(1, "Pathogenic"),
            entry(1, "Conflicting_classifications_of_pathogenicity", CONFLICT),
            "reclassified",
        ),
        (entry(1, "Pathogenic", SINGLE), entry(1, "Pathogenic", EXPERT), "review_changed"),
        (entry(1, "Pathogenic"), entry(1, "Pathogenic/Likely_pathogenic"), "term_changed"),
        (entry(1, "Pathogenic"), entry(1, "Pathogenic", pos="101"), "annotation_only"),
        (
            entry(1, "Pathogenic", gene="BRCA2"),
            entry(1, "Pathogenic", gene="ZAR1L"),
            "annotation_only",
        ),
        (entry(1, "Pathogenic"), entry(1, "Pathogenic"), "unchanged"),
    ],
)
def test_classify_change(old: Entry | None, new: Entry | None, expected: str) -> None:
    assert classify_change(old, new) == expected


def test_accession_continuity_across_gaps() -> None:
    old = list(
        parse_entries([row(1, "Pathogenic"), row(3, "Benign"), row(5, "Uncertain_significance")])
    )
    new = list(parse_entries([row(2, "Pathogenic"), row(3, "Benign"), row(5, "Likely_pathogenic")]))
    result = [(c, (o or n).vid) for c, o, n in diff_releases(old, new)]  # type: ignore[union-attr]
    assert result == [("removed", 1), ("added", 2), ("unchanged", 3), ("reclassified", 5)]


@pytest.mark.parametrize("ids", [(5, 4), (1, 1)], ids=["decreasing", "repeated"])
def test_unsorted_or_repeated_ids_are_rejected(ids: tuple[int, int]) -> None:
    rows = [row(ids[0], "Benign"), row(ids[1], "Benign")]
    with pytest.raises(ValueError, match=f"Variation ID {ids[1]} after {ids[0]}"):
        list(parse_entries(rows))


def test_gene_filter_uses_either_release() -> None:
    old = list(parse_entries([row(1, "Pathogenic", gene="TP53:7157")]))
    new = list(parse_entries([row(1, "Pathogenic", gene="TP53:7157|WRAP53:55135")]))
    assert [c for c, _, _ in diff_releases(old, new, {"WRAP53"})] == ["annotation_only"]
    assert list(diff_releases(old, new, {"BRCA1"})) == []


def test_gene_dropped_in_new_release_stays_in_panel_audit() -> None:
    old = list(parse_entries([row(1, "Pathogenic", gene="TP53:7157|WRAP53:55135")]))
    new = list(parse_entries([row(1, "Pathogenic", gene="TP53:7157")]))
    assert [c for c, _, _ in diff_releases(old, new, {"WRAP53"})] == ["annotation_only"]


@pytest.mark.parametrize("panel", [{"TP53"}, {"WRAP53"}])
def test_gene_replaced_between_releases_is_audited_and_credited(panel: set[str]) -> None:
    old = list(parse_entries([row(1, "Pathogenic", gene="TP53:7157")]))
    new = list(parse_entries([row(1, "Uncertain_significance", gene="WRAP53:55135")]))
    stats = DiffStats()
    changes = []
    for change, o, n in diff_releases(old, new, panel):
        accumulate(stats, change, o, n)
        changes.append(change)
    assert changes == ["reclassified"]
    data = stats.as_dict()
    assert data["top_genes"] == [
        {"gene": "TP53", "reclassified": 1, "became_plp": 0, "left_plp": 1},
        {"gene": "WRAP53", "reclassified": 1, "became_plp": 0, "left_plp": 0},
    ]


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ("2\t13\t100\n", "rel.tsv: line 2: expected 8 tab-separated columns .* got 3"),
        ("x\t13\t1\tA\tG\tBenign\t.\tG:1\n", "rel.tsv: line 2: .* numeric Variation ID"),
    ],
    ids=["short row", "non-numeric ID"],
)
def test_malformed_rows_name_file_and_line(bad: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        list(parse_entries([row(1, "Benign"), bad], source="rel.tsv"))


def test_headers_and_blank_lines_are_skipped_and_rows_counted() -> None:
    counts = ParseCounts()
    lines = ["# header\n", "\n", row(1, "Benign"), row(2, "Benign")]
    assert [e.vid for e in parse_entries(lines, counts=counts)] == [1, 2]
    assert counts.rows == 2


def test_empty_releases() -> None:
    assert list(diff_releases([], [])) == []
    new = list(parse_entries([row(1, "Benign"), row(2, "Pathogenic")]))
    assert [c for c, _, _ in diff_releases([], new)] == ["added", "added"]


def test_group_change_wins_over_star_change() -> None:
    assert (
        classify_change(entry(1, "Uncertain_significance", SINGLE), entry(1, "Pathogenic", EXPERT))
        == "reclassified"
    )


def test_stats_track_movement_into_and_out_of_plp() -> None:
    stats = DiffStats()
    pairs = [
        (entry(1, "Uncertain_significance"), entry(1, "Pathogenic", MULTI)),
        (
            entry(2, "Pathogenic"),
            entry(2, "Conflicting_classifications_of_pathogenicity", CONFLICT),
        ),
    ]
    for old, new in pairs:
        accumulate(stats, classify_change(old, new), old, new)
    data = stats.as_dict()
    assert data["changes"] == {"reclassified": 2}
    assert data["top_genes"] == [
        {"gene": "BRCA2", "reclassified": 2, "became_plp": 1, "left_plp": 1}
    ]
    assert data["assertion_changes"] == 2
    assert data["annotation_changes"] == 0
    assert data["reclassified_by_new_stars"] == {"1": 1, "2": 1}


def test_cli_output_is_byte_identical_between_runs(tmp_path: Path) -> None:
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    old.write_text(row(1, "Pathogenic") + row(2, "Uncertain_significance") + row(4, "Benign"))
    new.write_text(row(1, "Pathogenic", EXPERT) + row(2, "Likely_pathogenic") + row(3, "Benign"))
    outputs = []
    for run in ("a", "b"):
        out = tmp_path / f"{run}.tsv"
        js = tmp_path / f"{run}.json"
        assert (
            main(
                [
                    "diff",
                    "--old",
                    str(old),
                    "--new",
                    str(new),
                    "--old-label",
                    "o",
                    "--new-label",
                    "n",
                    "--out",
                    str(out),
                    "--json",
                    str(js),
                ]
            )
            == 0
        )
        outputs.append((out.read_bytes(), js.read_bytes()))
    assert outputs[0] == outputs[1]
    data = json.loads(outputs[0][1])
    assert data["changes"] == {"added": 1, "reclassified": 1, "removed": 1, "review_changed": 1}


def test_gzip_output_is_byte_identical_and_holds_the_expected_rows(tmp_path: Path) -> None:
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    old.write_text(row(1, "Pathogenic") + row(2, "Benign"))
    new.write_text(row(1, "Likely_pathogenic", MULTI) + row(3, "Benign"))
    payloads = []
    for run in ("a", "b"):
        out = tmp_path / f"{run}.tsv.gz"
        js = tmp_path / f"{run}.json"
        main(
            [
                "diff",
                "--old",
                str(old),
                "--new",
                str(new),
                "--old-label",
                "o",
                "--new-label",
                "n",
                "--out",
                str(out),
                "--json",
                str(js),
            ]
        )
        payloads.append(out.read_bytes())
    assert payloads[0] == payloads[1]
    rows = gzip.decompress(payloads[0]).decode().splitlines()
    assert rows[0].split("\t")[:2] == ["variation_id", "change"]
    assert [r.split("\t")[:2] for r in rows[1:]] == [
        ["1", "review_changed"],
        ["2", "removed"],
        ["3", "added"],
    ]
    data = json.loads((tmp_path / "a.json").read_text())
    assert data["changes"] == {"added": 1, "removed": 1, "review_changed": 1}
    assert data["rows_read"] == {"old": 2, "new": 2}


def test_cli_fails_on_malformed_row_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    old.write_text(row(1, "Pathogenic") + "2\ttruncated\n")
    new.write_text(row(1, "Pathogenic"))
    code = main(
        [
            "diff",
            "--old",
            str(old),
            "--new",
            str(new),
            "--old-label",
            "o",
            "--new-label",
            "n",
            "--out",
            str(tmp_path / "d.tsv"),
            "--json",
            str(tmp_path / "d.json"),
        ]
    )
    assert code == 1
    error = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert error["error"].startswith(f"{old}: line 2: expected 8 tab-separated columns")


def test_empty_gene_list_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A panel file that lost its symbols would otherwise drop every record and report a
    # release with no changes.
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    genes = tmp_path / "genes.txt"
    old.write_text(row(1, "Pathogenic"))
    new.write_text(row(1, "Benign"))
    genes.write_text("\n\n")
    code = main(
        [
            "diff",
            "--old",
            str(old),
            "--new",
            str(new),
            "--old-label",
            "o",
            "--new-label",
            "n",
            "--genes",
            str(genes),
            "--out",
            str(tmp_path / "d.tsv"),
            "--json",
            str(tmp_path / "d.json"),
        ]
    )
    assert code == 1
    assert "gene list is empty" in capsys.readouterr().err
