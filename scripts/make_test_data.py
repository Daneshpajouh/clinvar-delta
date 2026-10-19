#!/usr/bin/env python3
"""Build the bundled test data in tests/data from the full downloads.

Real records: HG002 v4.2.1, ClinVar 2025-10-13 and 2026-10-11, and gnomAD v4.1 genomes,
all cut to three gene windows (BRCA1, TP53 on chr17; BRCA2 on chr13). The reference keeps
real hg38 sequence inside the windows and N elsewhere, so coordinates stay real while the
bgzipped FASTA stays small. SYNTH01 is a synthetic sample built from ClinVar alleles to
exercise the paths HG002 does not reach (see tests/data/README.md).

Usage: scripts/make_test_data.py DATA_DIR OUT_DIR
"""

from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path

GENES = [
    ("chr13", 32315085, 32400268, "BRCA2"),
    ("chr17", 7661778, 7687546, "TP53"),
    ("chr17", 43044291, 43170245, "BRCA1"),
]
PAD = 2000
WRAP = 60


def run(cmd: list[str], **kwargs: object) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)  # type: ignore[call-overload]
    return str(result.stdout)


def windows() -> list[tuple[str, int, int]]:
    return [(c, s - PAD, e + PAD) for c, s, e, _ in GENES]


def subset_vcf(src: Path, dest: Path, regions: str, extra: list[str] | None = None) -> None:
    cmd = ["bcftools", "view", "--no-version", "-r", regions, "-Oz", "-o", str(dest), str(src)]
    if extra:
        cmd = [
            "bash",
            "-c",
            f"bcftools view --no-version -r {regions} -Ou {src} | "
            f"bcftools annotate --no-version {' '.join(extra)} -Oz -o {dest}",
        ]
    run(cmd)
    run(["bcftools", "index", "-t", "-f", str(dest)])


def masked_reference(fasta: Path, dest: Path) -> None:
    lengths = {}
    for line in Path(f"{fasta}.fai").read_text().splitlines():
        name, length, *_ = line.split("\t")
        lengths[name] = int(length)
    plain = dest.with_suffix("")
    with plain.open("w") as out:
        for chrom in sorted({c for c, _, _ in windows()}, key=lambda c: int(c[3:])):
            seq = bytearray(b"N" * lengths[chrom])
            for c, start, end in windows():
                if c != chrom:
                    continue
                region = run(["samtools", "faidx", str(fasta), f"{c}:{start}-{end}"])
                bases = "".join(region.splitlines()[1:]).encode()
                seq[start - 1 : start - 1 + len(bases)] = bases
            out.write(f">{chrom}\n")
            for i in range(0, len(seq), WRAP):
                out.write(seq[i : i + WRAP].decode() + "\n")
    run(["bgzip", "-f", str(plain)])
    run(["samtools", "faidx", str(dest)])


def clinvar_rows(vcf: Path) -> list[list[str]]:
    out = run(
        [
            "bcftools",
            "query",
            "-f",
            "%CHROM\t%POS\t%ID\t%REF\t%ALT\t%INFO/CLNSIG\t%INFO/CLNREVSTAT\t%INFO/GENEINFO\n",
            str(vcf),
        ]
    )
    return [line.split("\t") for line in out.splitlines()]


def ref_base(fasta: Path, chrom: str, start: int, end: int) -> str:
    return "".join(
        run(["samtools", "faidx", str(fasta), f"{chrom}:{start}-{end}"]).splitlines()[1:]
    ).upper()


def synthetic_sample(clinvar: Path, fasta: Path, dest: Path) -> list[str]:
    rows = clinvar_rows(clinvar)
    plp = [
        r
        for r in rows
        if r[5] in {"Pathogenic", "Likely_pathogenic", "Pathogenic/Likely_pathogenic"}
    ]
    picked: list[tuple[str, int, str, str, str, str]] = []
    notes = []

    def snv(r: list[str]) -> bool:
        return len(r[3]) == 1 and len(r[4]) == 1

    starred = [
        r
        for r in plp
        if snv(r)
        and r[6]
        in {"criteria_provided,_multiple_submitters,_no_conflicts", "reviewed_by_expert_panel"}
    ]
    for r in starred[:3]:
        picked.append((f"chr{r[0]}", int(r[1]), r[3], r[4], "0/1", f"ClinVar {r[2]} {r[5]}"))
        notes.append(f"chr{r[0]}:{r[1]} {r[3]}>{r[4]} ClinVar {r[2]}, P/LP with 2+ stars, GT 0/1")
    zero = next(r for r in plp if snv(r) and r[6] == "no_assertion_criteria_provided")
    picked.append((f"chr{zero[0]}", int(zero[1]), zero[3], zero[4], "0/1", "0 stars"))
    notes.append(f"chr{zero[0]}:{zero[1]} ClinVar {zero[2]}, P/LP with 0 stars, GT 0/1")
    hom_ref = starred[3]
    picked.append((f"chr{hom_ref[0]}", int(hom_ref[1]), hom_ref[3], hom_ref[4], "0/0", "no ALT"))
    notes.append(f"chr{hom_ref[0]}:{hom_ref[1]} ClinVar {hom_ref[2]}, P/LP but GT 0/0")
    multi = starred[4]
    other = next(b for b in "ACGT" if b not in {multi[3], multi[4]})
    picked.append(
        (f"chr{multi[0]}", int(multi[1]), multi[3], f"{multi[4]},{other}", "1/2", "multiallelic")
    )
    # The second ALT is the first base not already used at the site; say whether ClinVar
    # has it, since that decides how many P/LP rows the split record gives.
    second = next(
        (r for r in rows if r[:2] == multi[:2] and r[3] == multi[3] and r[4] == other), None
    )
    second_note = (
        f"second ALT {other} is ClinVar {second[2]} {second[5]}"
        if second
        else f"second ALT {other} is not in ClinVar"
    )
    notes.append(
        f"chr{multi[0]}:{multi[1]} multiallelic {multi[3]}>{multi[4]},{other} (ClinVar {multi[2]}; "
        f"{second_note}), GT 1/2"
    )
    # A one-base deletion inside a homopolymer, written one base to the right of where
    # ClinVar (left-aligned) puts it; bcftools norm must move it back to match.
    for r in plp:
        if (
            len(r[3]) != 2
            or len(r[4]) != 1
            or r[6]
            not in {
                "criteria_provided,_multiple_submitters,_no_conflicts",
                "reviewed_by_expert_panel",
                "criteria_provided,_single_submitter",
            }
        ):
            continue
        pos = int(r[1])
        context = ref_base(fasta, f"chr{r[0]}", pos, pos + 3)
        if context[1] == context[2]:
            shifted_ref = context[1:3]
            picked.append(
                (f"chr{r[0]}", pos + 1, shifted_ref, context[1], "0/1", "right-shifted deletion")
            )
            notes.append(
                f"chr{r[0]}:{pos + 1} {shifted_ref}>{context[1]} is ClinVar {r[2]} "
                f"({r[0]}:{pos} {r[3]}>{r[4]}) shifted right by one base"
            )
            break
    picked.sort(key=lambda p: (int(p[0][3:]), p[1]))
    header = [
        "##fileformat=VCFv4.2",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        "##contig=<ID=chr13,length=114364328>",
        "##contig=<ID=chr17,length=83257441>",
        "##comment=Synthetic test sample built from ClinVar alleles; not a real person",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSYNTH01",
    ]
    body = [f"{c}\t{p}\t.\t{ref}\t{alt}\t50\tPASS\t.\tGT\t{gt}" for c, p, ref, alt, gt, _ in picked]
    plain = dest.with_suffix("")
    plain.write_text("\n".join(header + body) + "\n")
    run(["bgzip", "-f", str(plain)])
    run(["bcftools", "index", "-t", "-f", str(dest)])
    return notes


def main(data_dir: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    regions_chr = ",".join(f"{c}:{s}-{e}" for c, s, e in windows())
    regions_bare = ",".join(f"{c[3:]}:{s}-{e}" for c, s, e in windows())
    keep = ["-x", "'^INFO/CLNSIG,INFO/CLNREVSTAT,INFO/GENEINFO,INFO/ALLELEID'"]
    subset_vcf(
        data_dir / "giab/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz",
        out / "HG002.subset.vcf.gz",
        regions_chr,
    )
    for release in ("clinvar_20251013", "clinvar_20261011"):
        subset_vcf(
            data_dir / f"clinvar/{release}.vcf.gz",
            out / f"{release}.subset.vcf.gz",
            regions_bare,
            keep,
        )
    subset_vcf(
        data_dir / "gnomad/gnomad.genomes.v4.1.acmg_sf_panel.vcf.gz",
        out / "gnomad.subset.vcf.gz",
        regions_chr,
    )
    fasta = data_dir / "reference/hg38_selected.fa.gz"
    masked_reference(fasta, out / "reference.fa.gz")
    notes = synthetic_sample(out / "clinvar_20261011.subset.vcf.gz", fasta, out / "SYNTH01.vcf.gz")
    (out / "panel.bed").write_text("".join(f"{c}\t{s}\t{e}\t{g}\n" for c, s, e, g in GENES))
    (out / "panel_genes.txt").write_text("".join(f"{g}\n" for *_, g in GENES))
    (out / "samplesheet.csv").write_text(
        "sample,vcf,tbi\n"
        "HG002,tests/data/HG002.subset.vcf.gz,tests/data/HG002.subset.vcf.gz.tbi\n"
        "SYNTH01,tests/data/SYNTH01.vcf.gz,tests/data/SYNTH01.vcf.gz.tbi\n"
    )
    (out / "synthetic_records.txt").write_text("\n".join(notes) + "\n")
    with gzip.open(out / "HG002.subset.vcf.gz", "rt") as handle:
        count = sum(1 for line in handle if not line.startswith("#"))
    print(f"HG002 records in windows: {count}")
    print("\n".join(notes))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
