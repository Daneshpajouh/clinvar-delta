"""A small streaming VCF reader for single-sample, already normalised files.

bcftools normalises and annotates the records; this reader only walks the final
panel-sized VCF, so it favours plain code over speed. BGZF files are valid gzip
streams, so the standard gzip module reads them.
"""

from __future__ import annotations

import gzip
import io
import struct
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
    if name.endswith((".gz", ".bgz")) and "w" in mode:
        # No file name and mtime=0 in the gzip header, so equal content gives equal bytes.
        with (
            open(name, "wb") as dest,
            gzip.GzipFile(filename="", mode="wb", fileobj=dest, mtime=0) as raw,
            io.TextIOWrapper(raw, encoding="utf-8", newline="") as handle,
        ):
            yield cast(TextIO, handle)
        return
    if name.endswith((".gz", ".bgz")):
        with gzip.open(name, "rt", encoding="utf-8", newline="") as handle:
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


def _records(lines: Iterator[str], n_samples: int, offset: int, source: str) -> Iterator[VcfRecord]:
    expected = 10 if n_samples else 8
    for number, line in enumerate(lines, start=offset + 1):
        if not line.strip():
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) != expected or not cols[1].isdigit():
            raise VcfFormatError(
                f"{source}: line {number}: expected {expected} tab-separated columns "
                f"with a numeric POS, got {len(cols)}"
            )
        sample: dict[str, str] = {}
        if n_samples:
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


def read_vcf(handle: TextIO, source: str = "<input>") -> VcfFile:
    """Read the header eagerly and return a lazy record iterator.

    The pipeline is single-sample by design, so a VCF with more than one sample column is
    refused here rather than having its later samples ignored.
    """
    header: list[str] = []
    samples: list[str] | None = None
    for line in handle:
        if not line.startswith("#"):
            break
        header.append(line.rstrip("\n"))
        if line.startswith("#CHROM"):
            samples = line.rstrip("\n").split("\t")[9:]
            break
    if not header:
        raise VcfFormatError(f"{source}: empty file, no VCF header")
    if samples is None:
        raise VcfFormatError(f"{source}: no #CHROM header line")
    if len(samples) > 1:
        raise VcfFormatError(f"{source}: {len(samples)} samples; one sample per VCF expected")
    records = _records(iter(handle), len(samples), offset=len(header), source=source)
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


def tabix_names(path: str | Path) -> list[str]:
    """Contig names in a tabix (.tbi) index: every contig that holds a record."""
    with gzip.open(path, "rb") as handle:
        # magic, then n_ref, format, col_seq, col_beg, col_end, meta, skip, l_nm (int32 each)
        head = handle.read(36)
        if len(head) < 36 or head[:4] != b"TBI\x01":
            raise VcfFormatError(f"{path}: not a tabix index")
        (names_length,) = struct.unpack("<i", head[32:36])
        names = handle.read(names_length)
    return [name.decode() for name in names.split(b"\0") if name]
