"""Build the gene panel BED from the NCBI ACMG SF page and an Ensembl symbol lookup."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

# Rows on the NCBI page read "... MedGen C0000000 BRCA1 (MIM 113705) ClinVar ...".
_GENE_ROW = re.compile(r"([A-Z][A-Z0-9-]+) \(MIM \d+\) ClinVar")


def acmg_symbols(page_html: str) -> list[str]:
    text = re.sub(r"<script.*?</script>", " ", page_html, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)
    return sorted(set(_GENE_ROW.findall(text)))


def request_body(symbols: list[str]) -> str:
    return json.dumps({"symbols": symbols})


def lookup_to_bed(lookup: dict[str, dict[str, object]], symbols: list[str]) -> list[str]:
    """Return sorted BED lines (0-based start) for each symbol on a primary chromosome.

    Raises if any symbol is missing, so a renamed gene is caught when the panel is rebuilt.
    """
    missing = [s for s in symbols if s not in lookup]
    if missing:
        raise ValueError(f"Ensembl lookup has no entry for: {', '.join(missing)}")
    rows: list[tuple[str, int, int, str]] = []
    for symbol in symbols:
        entry = lookup[symbol]
        chrom = str(entry["seq_region_name"])
        start = int(str(entry["start"])) - 1
        end = int(str(entry["end"]))
        rows.append(("chrM" if chrom == "MT" else f"chr{chrom}", start, end, symbol))
    order = {f"chr{c}": i for i, c in enumerate([*map(str, range(1, 23)), "X", "Y", "M"])}
    rows.sort(key=lambda r: (order.get(r[0], 99), r[1], r[2]))
    return [f"{c}\t{s}\t{e}\t{g}" for c, s, e, g in rows]


def read_lookup(path: Path) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Ensembl lookup JSON must be an object keyed by symbol")
    return data


class BedFormatError(ValueError):
    pass


def bed_intervals(lines: Iterable[str], source: str = "<panel>") -> Iterator[list[str]]:
    """Yield the columns of each interval, skipping blank, '#', 'track' and 'browser' lines.

    Column 4 becomes PANEL_GENE, so a line without a gene symbol is refused here, before
    any work, instead of failing at the report step.
    """
    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.startswith(("#", "track", "browser")):
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 4 or not cols[1].isdigit() or not cols[2].isdigit() or not cols[3]:
            raise BedFormatError(
                f"{source}: line {number}: expected chrom, start, end and gene symbol "
                f"separated by tabs, got {line.rstrip()!r}"
            )
        yield cols


def pad_bed(lines: list[str], pad: int) -> list[str]:
    """Pad intervals; starts stop at 0.

    Ends are not capped at the contig length: bcftools treats the part of a region past
    the end of a contig as empty, so capping would need the .fai and change nothing.
    """
    out = []
    for chrom, start, end, *rest in bed_intervals(lines):
        new_start = max(0, int(start) - pad)
        out.append("\t".join([chrom, str(new_start), str(int(end) + pad), *rest]))
    return out
