"""ClinVar annotation table, panel filtering and per-gene summary."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from typing import TextIO

from cvnf.clinvar import Group, classify, review_stars
from cvnf.vcf import VcfRecord, carries_alt

CLINVAR_HEADER = """\
##INFO=<ID=CLNVID,Number=1,Type=Integer,Description="ClinVar Variation ID">
##INFO=<ID=CLNSIG,Number=.,Type=String,Description="ClinVar aggregate germline classification">
##INFO=<ID=CLNREVSTAT,Number=.,Type=String,Description="ClinVar review status">
##INFO=<ID=CLNSTARS,Number=1,Type=Integer,Description="Review stars (0 to 4) from CLNREVSTAT">
##INFO=<ID=CLNGROUP,Number=1,Type=String,Description="Classification group derived from CLNSIG">
##INFO=<ID=CLNGENE,Number=1,Type=String,Description="ClinVar GENEINFO">
"""

TABLE_COLUMNS = (
    "sample",
    "chrom",
    "pos",
    "ref",
    "alt",
    "gt",
    "panel_gene",
    "clinvar_id",
    "clnsig",
    "group",
    "stars",
    "revstat",
    "gnomad_af",
    "low_penetrance",
    "reportable",
    "reason",
)


def clinvar_table(rows: Iterable[str]) -> Iterator[str]:
    """Turn `bcftools query` rows into a bcftools annotate table.

    Input columns: CHROM POS REF ALT ID CLNSIG CLNREVSTAT GENEINFO, sorted by position.
    When two ClinVar records describe the same allele after normalisation, the one with
    more review stars wins (then the lower Variation ID), so annotation is deterministic.
    """
    pending: dict[tuple[str, str, str, str], tuple[int, int, str]] = {}
    current: tuple[str, str] | None = None

    def flush() -> Iterator[str]:
        for key in sorted(pending):
            yield pending[key][2]
        pending.clear()

    for number, raw in enumerate(rows, start=1):
        cols = raw.rstrip("\n").split("\t")
        if len(cols) < 8:
            raise ValueError(f"row {number}: expected 8 tab-separated columns, got {len(cols)}")
        chrom, pos, ref, alt, vid, clnsig, revstat, geneinfo = cols[:8]
        if alt in {".", "*"}:
            continue
        if current != (chrom, pos):
            yield from flush()
            current = (chrom, pos)
        stars = review_stars(revstat)
        group = classify(clnsig).group
        line = "\t".join([chrom, pos, ref, alt, vid, clnsig, revstat, str(stars), group, geneinfo])
        key = (chrom, pos, ref, alt)
        # A non-numeric ID sorts after every real one instead of winning ties.
        rank = (-stars, int(vid) if vid.isdigit() else sys.maxsize)
        best = pending.get(key)
        if best is None or rank < (best[0], best[1]):
            pending[key] = (rank[0], rank[1], line)
    yield from flush()


@dataclass
class PanelVariant:
    sample: str
    chrom: str
    pos: int
    ref: str
    alt: str
    gt: str
    panel_gene: str
    clinvar_id: str
    clnsig: str
    group: str
    stars: int
    revstat: str
    gnomad_af: float | None
    low_penetrance: bool
    reportable: bool
    reason: str

    def as_row(self) -> str:
        values = asdict(self)
        af = values["gnomad_af"]
        values["gnomad_af"] = "." if af is None else f"{af:.6g}"
        values["low_penetrance"] = "yes" if self.low_penetrance else "no"
        values["reportable"] = "yes" if self.reportable else "no"
        return "\t".join(str(values[c]) for c in TABLE_COLUMNS)


@dataclass(frozen=True)
class FilterParams:
    min_stars: int = 1
    max_af: float = 0.01
    include_low_penetrance: bool = True


def _float_or_none(value: str | None) -> float | None:
    if value in {None, "", "."}:
        return None
    return float(str(value).split(",")[0])


def evaluate(record: VcfRecord, sample: str, params: FilterParams) -> PanelVariant | None:
    """Return the panel row for a record, or None when it lies outside the panel."""
    panel_gene = record.info.get("PANEL_GENE")
    if not panel_gene:
        return None
    clnsig = record.info.get("CLNSIG", ".")
    cls = classify(clnsig)
    stars = int(record.info["CLNSTARS"]) if "CLNSTARS" in record.info else 0
    af = _float_or_none(record.info.get("gnomAD_AF"))
    reasons = []
    if cls.group is not Group.PLP:
        reasons.append("not PLP")
    if not carries_alt(record.gt):
        reasons.append("genotype has no ALT allele")
    if cls.group is Group.PLP and stars < params.min_stars:
        reasons.append(f"stars {stars} < {params.min_stars}")
    if cls.group is Group.PLP and af is not None and af > params.max_af:
        reasons.append(f"gnomAD AF {af:.4g} > {params.max_af:g}")
    if cls.low_penetrance and not params.include_low_penetrance:
        reasons.append("low penetrance excluded")
    return PanelVariant(
        sample=sample,
        chrom=record.chrom,
        pos=record.pos,
        ref=record.ref,
        alt=record.alt,
        gt=record.gt,
        panel_gene=panel_gene.replace("|", ","),
        clinvar_id=record.info.get("CLNVID", "."),
        clnsig=clnsig,
        group=cls.group.value,
        stars=stars,
        revstat=record.info.get("CLNREVSTAT", "."),
        gnomad_af=af,
        low_penetrance=cls.low_penetrance,
        reportable=not reasons,
        reason="; ".join(reasons) if reasons else "P/LP, review and frequency thresholds met",
    )


def write_table(rows: Iterable[PanelVariant], handle: TextIO) -> None:
    handle.write("\t".join(TABLE_COLUMNS) + "\n")
    for row in rows:
        handle.write(row.as_row() + "\n")


def read_table(handle: TextIO) -> list[dict[str, str]]:
    lines = [line.rstrip("\n") for line in handle if line.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=True)) for line in lines[1:]]


def gene_summary(rows: list[dict[str, str]], panel_genes: list[str]) -> list[dict[str, object]]:
    """Per-gene counts; every panel gene appears, including genes with no variants."""
    by_gene: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for gene in row["panel_gene"].split(","):
            counts = by_gene[gene]
            counts["variants"] += 1
            if row["group"] == Group.PLP.value:
                counts["plp"] += 1
                counts[f"plp_stars_{row['stars']}"] += 1
            if row["group"] == Group.VUS.value:
                counts["vus"] += 1
            if row["reportable"] == "yes":
                counts["reportable"] += 1
    out: list[dict[str, object]] = []
    for gene in sorted(set(panel_genes) | set(by_gene)):
        c = by_gene.get(gene, Counter())
        out.append(
            {
                "gene": gene,
                "variants": c["variants"],
                "vus": c["vus"],
                "plp": c["plp"],
                **{f"plp_stars_{s}": c[f"plp_stars_{s}"] for s in range(5)},
                "reportable": c["reportable"],
            }
        )
    return out


def stars_breakdown(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """Counts of P/LP rows (any genotype) and reportable rows by review stars."""
    plp = Counter(r["stars"] for r in rows if r["group"] == Group.PLP.value)
    rep = Counter(r["stars"] for r in rows if r["reportable"] == "yes")
    return {
        "plp_by_stars": {str(s): plp.get(str(s), 0) for s in range(5)},
        "reportable_by_stars": {str(s): rep.get(str(s), 0) for s in range(5)},
    }


def to_json(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"
