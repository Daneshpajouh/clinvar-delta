"""Compare two ClinVar releases by Variation ID.

Both inputs are `bcftools query` tables sorted numerically on the ID column, so the
comparison is a streaming merge join: memory stays flat whatever the release size.
Columns: ID CHROM POS REF ALT CLNSIG CLNREVSTAT GENEINFO.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from cvnf.clinvar import Group, classify, gene_symbols, review_stars

CHANGE_COLUMNS = (
    "variation_id",
    "change",
    "genes",
    "chrom",
    "pos",
    "ref",
    "alt",
    "old_clnsig",
    "new_clnsig",
    "old_group",
    "new_group",
    "old_stars",
    "new_stars",
)


@dataclass(frozen=True)
class Entry:
    vid: int
    chrom: str
    pos: str
    ref: str
    alt: str
    clnsig: str
    revstat: str
    genes: tuple[str, ...]

    @property
    def group(self) -> Group:
        return classify(self.clnsig).group

    @property
    def stars(self) -> int:
        return review_stars(self.revstat)


def parse_entries(lines: Iterable[str]) -> Iterator[Entry]:
    last = -1
    for raw in lines:
        cols = raw.rstrip("\n").split("\t")
        if len(cols) < 8 or not cols[0].isdigit():
            continue
        vid = int(cols[0])
        if vid < last:
            raise ValueError(f"input not sorted by Variation ID at {vid} after {last}")
        last = vid
        yield Entry(
            vid, cols[1], cols[2], cols[3], cols[4], cols[5], cols[6], tuple(gene_symbols(cols[7]))
        )


# Assertion changes come from submitters or expert panels and can change what a patient
# is told. Annotation changes come from ClinVar re-mapping or renaming (new coordinates,
# allele representation, gene symbols, status labels) while the classification and its
# review level stay the same.
ASSERTION_CHANGES = ("reclassified", "review_changed", "term_changed")
ANNOTATION_CHANGES = ("annotation_only",)


def classify_change(old: Entry | None, new: Entry | None) -> str:
    if old is None:
        return "added"
    if new is None:
        return "removed"
    if old.group is not new.group:
        return "reclassified"
    if old.stars != new.stars:
        return "review_changed"
    if old.clnsig != new.clnsig:
        return "term_changed"
    location_old = (old.chrom, old.pos, old.ref, old.alt, old.genes, old.revstat)
    location_new = (new.chrom, new.pos, new.ref, new.alt, new.genes, new.revstat)
    if location_old != location_new:
        return "annotation_only"
    return "unchanged"


def merge_join(
    old: Iterable[Entry], new: Iterable[Entry]
) -> Iterator[tuple[Entry | None, Entry | None]]:
    old_it, new_it = iter(old), iter(new)
    o = next(old_it, None)
    n = next(new_it, None)
    while o is not None or n is not None:
        if n is None or (o is not None and o.vid < n.vid):
            yield o, None
            o = next(old_it, None)
        elif o is None or n.vid < o.vid:
            yield None, n
            n = next(new_it, None)
        else:
            yield o, n
            o = next(old_it, None)
            n = next(new_it, None)


@dataclass
class DiffStats:
    changes: Counter[str] = field(default_factory=Counter)
    transitions: Counter[tuple[str, str]] = field(default_factory=Counter)
    reclassified_by_new_stars: Counter[int] = field(default_factory=Counter)
    reclassified_by_gene: Counter[str] = field(default_factory=Counter)
    plp_gained_by_gene: Counter[str] = field(default_factory=Counter)
    plp_lost_by_gene: Counter[str] = field(default_factory=Counter)

    def as_dict(self, top: int = 25) -> dict[str, object]:
        """JSON-ready summary; gene lists are ordered by count, then symbol."""

        def ranked(counter: Counter[str]) -> list[tuple[str, int]]:
            return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top]

        return {
            "changes": dict(sorted(self.changes.items())),
            "assertion_changes": sum(self.changes[c] for c in ASSERTION_CHANGES),
            "annotation_changes": sum(self.changes[c] for c in ANNOTATION_CHANGES),
            "transitions": [
                {"old": o, "new": n, "count": c}
                for (o, n), c in sorted(self.transitions.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            "reclassified_by_new_stars": {
                str(k): v for k, v in sorted(self.reclassified_by_new_stars.items())
            },
            "top_genes": [
                {
                    "gene": gene,
                    "reclassified": count,
                    "became_plp": self.plp_gained_by_gene[gene],
                    "left_plp": self.plp_lost_by_gene[gene],
                }
                for gene, count in ranked(self.reclassified_by_gene)
            ],
            "top_genes_became_plp": [
                {"gene": g, "count": c} for g, c in ranked(self.plp_gained_by_gene)
            ],
            "top_genes_left_plp": [
                {"gene": g, "count": c} for g, c in ranked(self.plp_lost_by_gene)
            ],
        }


def diff_releases(
    old: Iterable[Entry], new: Iterable[Entry], genes: set[str] | None = None
) -> Iterator[tuple[str, Entry | None, Entry | None]]:
    """Yield (change, old, new) for every Variation ID, optionally limited to genes."""
    for o, n in merge_join(old, new):
        ref = n if n is not None else o
        assert ref is not None
        if genes is not None and not genes.intersection(ref.genes):
            continue
        yield classify_change(o, n), o, n


def accumulate(stats: DiffStats, change: str, old: Entry | None, new: Entry | None) -> None:
    stats.changes[change] += 1
    if change != "reclassified" or old is None or new is None:
        return
    stats.transitions[(old.group.value, new.group.value)] += 1
    stats.reclassified_by_new_stars[new.stars] += 1
    for gene in new.genes or old.genes:
        stats.reclassified_by_gene[gene] += 1
        if new.group is Group.PLP:
            stats.plp_gained_by_gene[gene] += 1
        if old.group is Group.PLP:
            stats.plp_lost_by_gene[gene] += 1


def change_row(change: str, old: Entry | None, new: Entry | None) -> str:
    ref = new if new is not None else old
    assert ref is not None
    return "\t".join(
        [
            str(ref.vid),
            change,
            ",".join(ref.genes) or ".",
            ref.chrom,
            ref.pos,
            ref.ref,
            ref.alt,
            old.clnsig if old else ".",
            new.clnsig if new else ".",
            old.group.value if old else ".",
            new.group.value if new else ".",
            str(old.stars) if old else ".",
            str(new.stars) if new else ".",
        ]
    )
