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


def test_gene_renamed_in_new_release_stays_in_panel_audit() -> None:
    old = list(parse_entries([row(1, "Pathogenic", gene="OLDNAME:1")]))
    new = list(parse_entries([row(1, "Uncertain_significance", gene="NEWNAME:1")]))
    assert [c for c, _, _ in diff_releases(old, new, {"OLDNAME"})] == ["reclassified"]


def test_malformed_rows_are_counted() -> None:
    counts = ParseCounts()
    rows = [row(1, "Benign"), "2\t13\t100\n", "x\t13\t1\tA\tG\tBenign\t.\tG:1\n", "\n"]
    assert [e.vid for e in parse_entries(rows, counts)] == [1]
    assert (counts.rows, counts.skipped) == (3, 2)


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


def test_gzip_output_is_byte_identical_between_runs(tmp_path: Path) -> None:
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    old.write_text(row(1, "Pathogenic") + row(2, "Benign"))
    new.write_text(row(1, "Likely_pathogenic") + row(3, "Benign"))
    digests = []
    for run in ("a", "b"):
        out = tmp_path / f"{run}.tsv.gz"
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
                str(tmp_path / f"{run}.json"),
            ]
        )
        digests.append(out.read_bytes())
    assert digests[0] == digests[1]


def test_cli_fails_and_reports_skipped_rows(tmp_path: Path) -> None:
    old = tmp_path / "old.tsv"
    new = tmp_path / "new.tsv"
    old.write_text(row(1, "Pathogenic") + "2\ttruncated\n")
    new.write_text(row(1, "Pathogenic"))
    js = tmp_path / "d.json"
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
            str(js),
        ]
    )
    assert code == 1
    assert json.loads(js.read_text())["rows_skipped"] == {"old": 1, "new": 0}
