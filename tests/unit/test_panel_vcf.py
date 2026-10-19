import io

import pytest

from cvnf.panel import acmg_symbols, lookup_to_bed, pad_bed
from cvnf.vcf import carries_alt, header_contigs, parse_info, read_vcf

PAGE = """<table><tr><td>Hereditary breast cancer (<a>MIM 604370</a>)</td><td>MedGen C2676676</td>
<td><a>BRCA1</a> (MIM 113705)</td><td><a>ClinVar</a></td></tr>
<tr><td>x</td><td>MedGen C1</td><td><a>SDHD</a> (MIM 602690)</td><td>ClinVar</td></tr></table>"""


def test_acmg_symbols_from_table_rows() -> None:
    assert acmg_symbols(PAGE) == ["BRCA1", "SDHD"]


def test_lookup_to_bed_converts_to_zero_based_and_sorts() -> None:
    lookup: dict[str, dict[str, object]] = {
        "TP53": {"seq_region_name": "17", "start": 7661779, "end": 7687546},
        "SDHB": {"seq_region_name": "1", "start": 17018664, "end": 17054210},
    }
    assert lookup_to_bed(lookup, ["TP53", "SDHB"]) == [
        "chr1\t17018663\t17054210\tSDHB",
        "chr17\t7661778\t7687546\tTP53",
    ]


def test_lookup_missing_symbol_raises() -> None:
    with pytest.raises(ValueError, match="BRCA1"):
        lookup_to_bed({}, ["BRCA1"])


def test_pad_bed_clamps_at_zero() -> None:
    assert pad_bed(["chr1\t50\t100\tG"], 100) == ["chr1\t0\t200\tG"]


@pytest.mark.parametrize(
    ("gt", "alt"),
    [("0/1", True), ("1|1", True), ("0/0", False), ("./.", False), ("1", True), ("0|2", True)],
)
def test_carries_alt(gt: str, alt: bool) -> None:
    assert carries_alt(gt) is alt


def test_read_vcf_and_info() -> None:
    text = (
        "##fileformat=VCFv4.2\n##contig=<ID=chr1,length=10>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"
        "chr1\t5\t.\tA\tG\t50\tPASS\tDB;AF=0.1\tGT:DP\t0/1:20\n"
    )
    vcf = read_vcf(io.StringIO(text))
    rec = next(vcf.records)
    assert vcf.samples == ["S1"]
    assert header_contigs(vcf.header) == ["chr1"]
    assert rec.info == {"DB": "", "AF": "0.1"}
    assert rec.gt == "0/1"
    assert parse_info(".") == {}
