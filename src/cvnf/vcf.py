"""A small streaming VCF reader for single-sample, already normalised files.

bcftools does the heavy lifting in the pipeline; this reader only walks the final
panel-sized VCF, so it favours plain code over speed. BGZF files are valid gzip
streams, so the standard gzip module reads them.
"""

from __future__ import annotations

import gzip
import io
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO, cast


@contextmanager
def open_text(path: str | Path, mode: str = "r") -> Iterator[TextIO]:
    """Open plain, gzip or BGZF text; '-' means stdin or stdout."""
    name = str(path)
    if name == "-":
        yield sys.stdin if "r" in mode else sys.stdout
        return
    if name.endswith((".gz", ".bgz")):
        with gzip.open(name, mode + "t", encoding="utf-8", newline="") as handle:
            yield cast(TextIO, handle)
        return
    with open(name, mode, encoding="utf-8", newline="") as handle:
        yield cast(TextIO, handle)


def parse_info(info: str) -> dict[str, str]:
    if info in {"", "."}:
        return {}
    out: dict[str, str] = {}
    for item in info.split(";"):
        key, sep, value = item.partition("=")
        out[key] = value if sep else ""
    return out


@dataclass
class VcfRecord:
    chrom: str
    pos: int
    vid: str
    ref: str
    alt: str
    qual: str
    filter: str
    info: dict[str, str]
    sample: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}"

    @property
    def gt(self) -> str:
        return self.sample.get("GT", ".")


def carries_alt(gt: str) -> bool:
    """True when any called allele in GT is non-reference ('0/1', '1|1', '1')."""
    alleles = gt.replace("|", "/").split("/")
    return any(a not in {"0", "."} for a in alleles)


@dataclass
class VcfFile:
    header: list[str]
    samples: list[str]
    records: Iterator[VcfRecord]


class VcfFormatError(ValueError):
    pass


def _records(lines: Iterator[str], n_samples: int, offset: int) -> Iterator[VcfRecord]:
    for number, line in enumerate(lines, start=offset + 1):
        if not line.strip():
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 8 or not cols[1].isdigit():
            raise VcfFormatError(
                f"line {number}: expected 8+ tab-separated columns with a numeric POS"
            )
        sample: dict[str, str] = {}
        if n_samples and len(cols) > 9:
            sample = dict(zip(cols[8].split(":"), cols[9].split(":"), strict=False))
        yield VcfRecord(
            chrom=cols[0],
            pos=int(cols[1]),
            vid=cols[2],
            ref=cols[3],
            alt=cols[4],
            qual=cols[5],
            filter=cols[6],
            info=parse_info(cols[7]),
            sample=sample,
        )


def read_vcf(handle: TextIO) -> VcfFile:
    """Read the header eagerly and return a lazy record iterator."""
    header: list[str] = []
    samples: list[str] = []
    for line in handle:
        if not line.startswith("#"):
            raise VcfFormatError("no #CHROM header line before the first record")
        if line.startswith("##"):
            header.append(line.rstrip("\n"))
            continue
        if line.startswith("#CHROM"):
            header.append(line.rstrip("\n"))
            samples = line.rstrip("\n").split("\t")[9:]
            break
    if not header:
        raise VcfFormatError("empty file: no VCF header")
    records = _records(iter(handle), len(samples), offset=len(header))
    return VcfFile(header=header, samples=samples, records=records)


def header_contigs(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        if line.startswith("##contig=<"):
            body = line[len("##contig=<") : -1]
            for part in body.split(","):
                key, _, value = part.partition("=")
                if key == "ID":
                    out.append(value)
    return out


def text_stream(data: str) -> TextIO:
    """Wrap a string as a text handle; used by tests and small fixtures."""
    return io.StringIO(data)
