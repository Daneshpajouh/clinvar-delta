"""Command line entry point: `cvnf <command>`. Each pipeline step calls one command."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from cvnf import __version__
from cvnf.annotate import (
    CLINVAR_HEADER,
    FilterParams,
    clinvar_table,
    evaluate,
    gene_summary,
    read_table,
    stars_breakdown,
    to_json,
    write_table,
)
from cvnf.diff import (
    CHANGE_COLUMNS,
    DiffStats,
    accumulate,
    change_row,
    diff_releases,
    parse_entries,
)
from cvnf.panel import acmg_symbols, lookup_to_bed, pad_bed, read_lookup, request_body
from cvnf.profiling import (
    calibrated_config,
    fmt_bytes,
    fmt_pct,
    fmt_secs,
    parse_sacct,
    read_trace,
    slurm_job_rows,
    summarise,
)
from cvnf.report import render
from cvnf.vcf import header_contigs, open_text, read_vcf

log = logging.getLogger("cvnf")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so logs from many tasks can be concatenated and queried."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, sort_keys=True)


def setup_logging(command: str) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("cvnf")
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    root.propagate = False
    log.info("start", extra={"fields": {"command": command, "version": __version__}})


def info(event: str, **fields: object) -> None:
    log.info(event, extra={"fields": fields})


def read_lines(path: str) -> list[str]:
    with open_text(path) as handle:
        return [line.rstrip("\n") for line in handle if line.strip()]


def write_text(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


# --- commands ------------------------------------------------------------------------


def cmd_panel_symbols(args: argparse.Namespace) -> int:
    symbols = acmg_symbols(Path(args.html).read_text(encoding="utf-8", errors="replace"))
    write_text(args.out, "\n".join(symbols) + "\n")
    info("panel symbols", count=len(symbols))
    return 0


def cmd_panel_request_body(args: argparse.Namespace) -> int:
    sys.stdout.write(request_body(read_lines(args.symbols)))
    return 0


def cmd_panel_bed(args: argparse.Namespace) -> int:
    lines = lookup_to_bed(read_lookup(Path(args.lookup)), read_lines(args.symbols))
    write_text(args.out, "\n".join(lines) + "\n")
    info("panel bed", genes=len(lines))
    return 0


def cmd_panel_pad(args: argparse.Namespace) -> int:
    lines = pad_bed(read_lines(args.bed), args.pad)
    write_text(args.out, "\n".join(lines) + "\n")
    return 0


def cmd_clinvar_table(args: argparse.Namespace) -> int:
    count = 0
    with open_text(args.input) as src, open_text(args.out, "w") as dst:
        for line in clinvar_table(src):
            dst.write(line + "\n")
            count += 1
    write_text(args.header, CLINVAR_HEADER)
    info("clinvar table", rows=count)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Check contig naming between the sample VCF, reference and panel before any work."""
    fai = {line.split("\t")[0] for line in read_lines(args.fai)}
    problems: list[str] = []
    with open_text(args.vcf) as handle:
        vcf = read_vcf(handle)
        contigs = header_contigs(vcf.header)
        first = next(vcf.records, None)
    if len(vcf.samples) != 1:
        problems.append(f"expected one sample column, found {len(vcf.samples)}")
    used = {first.chrom} if first else set()
    if first is None:
        problems.append("VCF has no records")
    missing = sorted(c for c in used if c not in fai)
    if missing:
        problems.append(f"VCF contigs missing from reference: {', '.join(missing)}")
    panel_contigs = {line.split("\t")[0] for line in read_lines(args.panel)}
    if not panel_contigs <= fai:
        problems.append(
            f"panel contigs missing from reference: {', '.join(sorted(panel_contigs - fai))}"
        )
    result = {
        "sample": args.sample,
        "vcf_sample_name": vcf.samples[0] if vcf.samples else None,
        "header_contigs": len(contigs),
        "panel_contigs": sorted(panel_contigs),
        "problems": problems,
    }
    write_text(args.out, to_json(result))
    if problems:
        log.error("validation failed", extra={"fields": {"problems": problems}})
        return 1
    info("validation passed", sample=args.sample)
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    params = FilterParams(args.min_stars, args.max_af, not args.exclude_low_penetrance)
    rows = []
    with open_text(args.vcf) as handle:
        vcf = read_vcf(handle)
        for record in vcf.records:
            row = evaluate(record, args.sample, params)
            if row is not None:
                rows.append(row)
    with open_text(args.out, "w") as dst:
        write_table(rows, dst)
    reportable = sum(r.reportable for r in rows)
    info("filter", sample=args.sample, panel_variants=len(rows), reportable=reportable)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    with open_text(args.table) as handle:
        rows = read_table(handle)
    genes = [line.split("\t")[3] for line in read_lines(args.panel)]
    summary = gene_summary(rows, genes)
    stars = stars_breakdown(rows)
    reportable = [r for r in rows if r["reportable"] == "yes"]
    plp_all = [r for r in rows if r["group"] == "PLP"]
    keys = [
        "gene",
        "variants",
        "vus",
        "plp",
        "plp_stars_0",
        "plp_stars_1",
        "plp_stars_2",
        "plp_stars_3",
        "plp_stars_4",
        "reportable",
    ]
    with open_text(args.summary, "w") as dst:
        dst.write("\t".join(keys) + "\n")
        for item in summary:
            dst.write("\t".join(str(item[k]) for k in keys) + "\n")
    stats = {
        "sample": args.sample,
        "panel_genes": len(genes),
        "panel_variants": len(rows),
        "plp_any_review": len(plp_all),
        "reportable": len(reportable),
        "thresholds": {"min_stars": args.min_stars, "max_af": args.max_af},
        **stars,
    }
    write_text(args.json, to_json(stats))
    rep_cols = [
        "panel_gene",
        "chrom",
        "pos",
        "ref",
        "alt",
        "gt",
        "clnsig",
        "stars",
        "gnomad_af",
        "clinvar_id",
    ]
    plp_cols = [*rep_cols, "reason"]
    md, page = render(
        f"ClinVar panel report: {args.sample}",
        [
            f"Panel: {len(genes)} genes. Variants in panel regions: {len(rows)}. "
            f"P/LP in ClinVar (any review level): {len(plp_all)}. Reportable: {len(reportable)}.",
            f"Reportable means ClinVar P/LP, at least {args.min_stars} review star(s), gnomAD "
            f"allele frequency at most {args.max_af:g} (absent counts as 0), and a genotype "
            "carrying the alternate allele. This is a research summary, not a clinical report.",
        ],
        [
            (
                "Reportable variants",
                [] if reportable else ["None at these thresholds."],
                (rep_cols, [[r[c] for c in rep_cols] for r in reportable]) if reportable else None,
            ),
            (
                "All ClinVar P/LP variants in the panel",
                [],
                (plp_cols, [[r[c] for c in plp_cols] for r in plp_all]) if plp_all else None,
            ),
            (
                "P/LP variants by review stars",
                [],
                (
                    ["stars", "P/LP (any)", "reportable"],
                    [
                        [s, stars["plp_by_stars"][s], stars["reportable_by_stars"][s]]
                        for s in ["0", "1", "2", "3", "4"]
                    ],
                ),
            ),
            (
                "Per-gene summary (genes with variants)",
                [],
                (keys, [[item[k] for k in keys] for item in summary if item["variants"]]),
            ),
        ],
    )
    write_text(args.markdown, md)
    write_text(args.html, page)
    info("report", sample=args.sample, reportable=len(reportable))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    genes = set(read_lines(args.genes)) if args.genes else None
    stats = DiffStats()
    with open_text(args.old) as old, open_text(args.new) as new, open_text(args.out, "w") as dst:
        dst.write("\t".join(CHANGE_COLUMNS) + "\n")
        for change, o, n in diff_releases(parse_entries(old), parse_entries(new), genes):
            accumulate(stats, change, o, n)
            if change != "unchanged":
                dst.write(change_row(change, o, n) + "\n")
    data = {
        "old": args.old_label,
        "new": args.new_label,
        "gene_filter": len(genes) if genes else None,
        **stats.as_dict(),
    }
    write_text(args.json, to_json(data))
    info("diff", **dict(stats.changes))
    return 0


def cmd_diff_report(args: argparse.Namespace) -> int:
    sections: list[tuple[str, list[str], tuple[list[str], list[list[object]]] | None]] = []
    intro = []
    for label, path in (("All records", args.all_json), ("Panel genes", args.panel_json)):
        if not path:
            continue
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        intro = [f"ClinVar {data['old']} compared with {data['new']}, matched on Variation ID."]
        changes = data["changes"]
        sections.append(
            (
                f"{label}: changes",
                [
                    "Assertion changes (reclassified, review_changed, term_changed) come from "
                    "submitters or expert panels. annotation_only means ClinVar changed the "
                    "location, allele, gene or status wording while the classification and stars "
                    "stayed the same."
                ],
                (["change", "variation IDs"], [[k, v] for k, v in changes.items()]),
            )
        )
        sections.append(
            (
                f"{label}: reclassifications between groups",
                [],
                (
                    ["old group", "new group", "count"],
                    [[t["old"], t["new"], t["count"]] for t in data["transitions"]],
                ),
            )
        )
        sections.append(
            (
                f"{label}: reclassified, by review stars in the new release",
                [],
                (
                    ["stars", "count"],
                    [[k, v] for k, v in data["reclassified_by_new_stars"].items()],
                ),
            )
        )
        sections.append(
            (
                f"{label}: genes with most reclassifications",
                ["A variant listed under two genes counts once for each."],
                (
                    ["gene", "reclassified", "became P/LP", "left P/LP"],
                    [
                        [g["gene"], g["reclassified"], g["became_plp"], g["left_plp"]]
                        for g in data["top_genes"]
                    ],
                ),
            )
        )
        sections.append(
            (
                f"{label}: assertion versus annotation changes",
                [],
                (
                    ["kind", "variation IDs"],
                    [
                        [
                            "assertion (reclassified, review_changed, term_changed)",
                            data["assertion_changes"],
                        ],
                        ["annotation only", data["annotation_changes"]],
                    ],
                ),
            )
        )
    md, page = render("ClinVar release comparison", intro, sections)
    write_text(args.markdown, md)
    write_text(args.html, page)
    return 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cmd_manifest(args: argparse.Namespace) -> int:
    files = {}
    for item in args.inputs:
        path = Path(item)
        if path.is_file():
            files[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "pipeline": "clinvar-variant-nf",
        "version": __version__,
        "run_started": args.started,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": args.engine,
        "git_commit": args.git_commit,
        "params": json.loads(Path(args.params).read_text(encoding="utf-8")) if args.params else {},
        "containers": json.loads(args.containers) if args.containers else {},
        "inputs": files,
        "python": platform.python_version(),
    }
    write_text(args.out, to_json(manifest))
    return 0


def cmd_profile_usage(args: argparse.Namespace) -> int:
    with open_text(args.trace) as handle:
        tasks = read_trace(handle)
    summary = summarise(tasks)
    header = [
        "process",
        "tasks",
        "cpus req",
        "CPU eff",
        "mem req",
        "peak RSS",
        "mem used",
        "time req",
        "max realtime",
        "time used",
        "flags",
    ]
    rows: list[list[object]] = [
        [
            s.process,
            s.tasks,
            s.cpus_requested or "-",
            fmt_pct(s.cpu_efficiency),
            fmt_bytes(s.memory_requested),
            fmt_bytes(s.peak_rss_max),
            fmt_pct(s.memory_used_fraction),
            fmt_secs(s.time_requested),
            fmt_secs(s.realtime_max),
            fmt_pct(s.time_used_fraction),
            ", ".join(s.flags) or "-",
        ]
        for s in summary
    ]
    md, page = render(
        "Requested versus used resources",
        [
            f"Trace: {Path(args.trace).name}. {len(tasks)} tasks in {len(summary)} processes.",
            "mem used = peak RSS of the largest task / requested memory; time used = longest "
            "realtime / requested time; CPU eff = %cpu / (100 x cpus), averaged over tasks.",
        ],
        [("Per process", [], (header, rows))],
    )
    write_text(args.markdown, md)
    if args.html:
        write_text(args.html, page)
    flagged = sum(1 for s in summary if s.flags)
    info("usage report", processes=len(summary), flagged=flagged)
    return 0


def cmd_profile_calibrate(args: argparse.Namespace) -> int:
    tasks = []
    for trace in args.trace:
        with open_text(trace) as handle:
            tasks += read_trace(handle)
    config = calibrated_config(
        summarise(tasks),
        source=", ".join(f"{Path(t).parent.parent.name}/{Path(t).name}" for t in args.trace),
        memory_headroom=args.memory_headroom,
        time_headroom=args.time_headroom,
    )
    write_text(args.out, config)
    info("calibrated config", processes=config.count("withName"), out=args.out)
    return 0


def cmd_profile_sacct(args: argparse.Namespace) -> int:
    steps = parse_sacct(Path(args.input).read_text(encoding="utf-8"))
    rows = slurm_job_rows(steps)
    keys = ["job", "name", "state", "memory_used", "time_used", "cpu_efficiency", "flags"]
    sys.stdout.write("\t".join(keys) + "\n")
    for row in rows:
        sys.stdout.write("\t".join(row[k] for k in keys) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cvnf", description=__doc__)
    parser.add_argument("--version", action="version", version=f"cvnf {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("panel-symbols", help="gene symbols from the saved NCBI ACMG SF page")
    p.add_argument("--html", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_panel_symbols)

    p = sub.add_parser("panel-request-body", help="JSON body for the Ensembl symbol lookup")
    p.add_argument("--symbols", required=True)
    p.set_defaults(func=cmd_panel_request_body)

    p = sub.add_parser("panel-bed", help="BED from an Ensembl lookup response")
    p.add_argument("--lookup", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_panel_bed)

    p = sub.add_parser("panel-pad", help="pad BED intervals on both sides")
    p.add_argument("--bed", required=True)
    p.add_argument("--pad", type=int, required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_panel_pad)

    p = sub.add_parser("clinvar-table", help="bcftools annotate table with review stars")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--header", required=True)
    p.set_defaults(func=cmd_clinvar_table)

    p = sub.add_parser("validate", help="check sample VCF, reference and panel agree")
    p.add_argument("--sample", required=True)
    p.add_argument("--vcf", required=True)
    p.add_argument("--fai", required=True)
    p.add_argument("--panel", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_validate)

    for name, func in (("filter", cmd_filter), ("report", cmd_report)):
        p = sub.add_parser(name)
        p.add_argument("--sample", required=True)
        p.add_argument("--min-stars", type=int, default=1)
        p.add_argument("--max-af", type=float, default=0.01)
        p.set_defaults(func=func)
        if name == "filter":
            p.add_argument("--vcf", required=True)
            p.add_argument("--out", required=True)
            p.add_argument("--exclude-low-penetrance", action="store_true")
        else:
            p.add_argument("--table", required=True)
            p.add_argument("--panel", required=True)
            p.add_argument("--summary", required=True)
            p.add_argument("--json", required=True)
            p.add_argument("--markdown", required=True)
            p.add_argument("--html", required=True)

    p = sub.add_parser("diff", help="compare two ClinVar releases sorted by Variation ID")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--old-label", required=True)
    p.add_argument("--new-label", required=True)
    p.add_argument("--genes")
    p.add_argument("--out", required=True)
    p.add_argument("--json", required=True)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("diff-report")
    p.add_argument("--all-json", required=True)
    p.add_argument("--panel-json")
    p.add_argument("--markdown", required=True)
    p.add_argument("--html", required=True)
    p.set_defaults(func=cmd_diff_report)

    p = sub.add_parser("manifest", help="run manifest with input SHA-256")
    p.add_argument("--engine", required=True)
    p.add_argument("--git-commit", default="unknown")
    p.add_argument("--params")
    p.add_argument("--containers")
    p.add_argument("--started", default="unknown")
    p.add_argument("--out", required=True)
    p.add_argument("inputs", nargs="*")
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("profile-usage", help="requested versus used resources from a trace")
    p.add_argument("--trace", required=True)
    p.add_argument("--markdown", required=True)
    p.add_argument("--html")
    p.set_defaults(func=cmd_profile_usage)

    p = sub.add_parser("profile-calibrate", help="per-process requests from measured traces")
    p.add_argument("--trace", required=True, action="append")
    p.add_argument("--memory-headroom", type=float, default=2.0)
    p.add_argument("--time-headroom", type=float, default=4.0)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_profile_calibrate)

    p = sub.add_parser("profile-sacct", help="summarise sacct --parsable2 output")
    p.add_argument("--input", required=True)
    p.set_defaults(func=cmd_profile_sacct)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.command)
    try:
        result: int = args.func(args)
    except (OSError, ValueError) as exc:
        # Name the files this command was given, so the failing input is in the task log.
        inputs = sorted(
            str(v)
            for k, v in vars(args).items()
            if k not in {"func", "command"} and isinstance(v, str)
        )
        log.error(
            "failed",
            extra={"fields": {"command": args.command, "error": str(exc), "inputs": inputs}},
        )
        return 1
    return result
