"""Draw the old-group by new-group reclassification counts of a diff report as an SVG.

Reads the "<scope>: reclassifications between groups" table of clinvar_diff.report.md, so
the figure in the README comes straight from a committed run's output. Standard library
only, like the rest of the tools.

Usage: python3 scripts/plot_transitions.py REPORT.md "Panel genes" OUT.svg TITLE
"""

from __future__ import annotations

import html
import math
import sys
from pathlib import Path

ROWS = ["PLP", "VUS", "CONFLICTING", "BLB", "OTHER", "NONE"]
COLS = ["PLP", "VUS", "CONFLICTING", "BLB", "OTHER", "NONE", "RISK_ALLELE"]
LABELS = {
    "CONFLICTING": "Conflicting",
    "RISK_ALLELE": "Risk allele",
    "OTHER": "Other",
    "NONE": "None",
}


def read_transitions(report: str, scope: str) -> dict[tuple[str, str], int]:
    heading = f"## {scope}: reclassifications between groups"
    lines = report.splitlines()
    start = lines.index(heading)
    counts: dict[tuple[str, str], int] = {}
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 3 and cells[2].isdigit():
            counts[(cells[0], cells[1])] = int(cells[2])
    if not counts:
        raise SystemExit(f"no transition rows under {heading!r}")
    missing = {g for pair in counts for g in pair} - set(ROWS) - set(COLS)
    if missing:
        raise SystemExit(f"groups not in the layout: {sorted(missing)}")
    return counts


def svg(counts: dict[tuple[str, str], int], title: str) -> str:
    cell, left, top = 74, 120, 92
    width, height = left + cell * len(COLS) + 20, top + cell * len(ROWS) + 40
    peak = math.log10(max(counts.values()) + 1)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        'font-family="Helvetica, Arial, sans-serif" font-size="13">',
        f"<title>{html.escape(title)}</title>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="22" font-size="14" font-weight="bold">{html.escape(title)}</text>',
        f'<text x="{left + cell * len(COLS) / 2}" y="48" text-anchor="middle">new group</text>',
        f'<text x="18" y="{top + cell * len(ROWS) / 2}" text-anchor="middle" '
        f'transform="rotate(-90 18 {top + cell * len(ROWS) / 2})">old group</text>',
    ]
    for j, col in enumerate(COLS):
        x = left + j * cell + cell / 2
        out.append(
            f'<text x="{x}" y="{top - 10}" text-anchor="middle">{LABELS.get(col, col)}</text>'
        )
    for i, row in enumerate(ROWS):
        y = top + i * cell
        out.append(
            f'<text x="{left - 8}" y="{y + cell / 2 + 4}" text-anchor="end">'
            f"{LABELS.get(row, row)}</text>"
        )
        for j, col in enumerate(COLS):
            x = left + j * cell
            n = counts.get((row, col), 0)
            if row == col:
                fill = "#eeeeee"
            elif n:
                # Log scale: the counts run from 1 to thousands.
                shade = math.log10(n + 1) / peak
                red, green, blue = (int(255 - k * shade) for k in (200, 140, 60))
                fill = f"rgb({red},{green},{blue})"
            else:
                fill = "#ffffff"
            out.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" '
                'stroke="#c9ced8"/>'
            )
            if n:
                color = "#ffffff" if math.log10(n + 1) / peak > 0.6 else "#1d2433"
                out.append(
                    f'<text x="{x + cell / 2}" y="{y + cell / 2 + 5}" text-anchor="middle" '
                    f'fill="{color}">{n:,}</text>'
                )
    total = sum(counts.values())
    out.append(
        f'<text x="{left}" y="{height - 12}" fill="#4a5163">{total:,} variants changed group; '
        "grey cells are the same group in both releases</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> None:
    report, scope, out, title = argv
    counts = read_transitions(Path(report).read_text(encoding="utf-8"), scope)
    Path(out).write_text(svg(counts, title), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
