"""Markdown and HTML reports. The HTML is a direct rendering of the same tables."""

from __future__ import annotations

import html
from collections.abc import Sequence

Table = tuple[Sequence[str], Sequence[Sequence[object]]]


def md_table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def html_table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render(
    title: str,
    intro: Sequence[str],
    sections: Sequence[tuple[str, Sequence[str], Table | None]],
) -> tuple[str, str]:
    """Return (markdown, html) for a title, intro paragraphs and titled sections."""
    md = [f"# {title}", "", *[p + "\n" for p in intro]]
    body = [f"<h1>{html.escape(title)}</h1>", *[f"<p>{html.escape(p)}</p>" for p in intro]]
    for heading, paragraphs, table in sections:
        md += [f"## {heading}", ""]
        body.append(f"<h2>{html.escape(heading)}</h2>")
        for p in paragraphs:
            md += [p, ""]
            body.append(f"<p>{html.escape(p)}</p>")
        if table is not None:
            md += [md_table(*table), ""]
            body.append(html_table(*table))
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>"
        "body{font-family:system-ui,sans-serif;max-width:70rem;margin:2rem auto;padding:0 1rem;"
        "color:#1d2433;background:#fff}table{border-collapse:collapse;margin:1rem 0;"
        "font-size:.9rem}th,td{border:1px solid #c9ced8;padding:.3rem .6rem;text-align:left}"
        "th{background:#eef1f6}</style></head><body>" + "\n".join(body) + "</body></html>\n"
    )
    return "\n".join(md).rstrip() + "\n", page
