# Test data

Two kinds of files live here. Neither contains data about a real patient.

## Pipeline bundle (built by `scripts/make_test_data.py`)

Cut from the full downloads listed in `docs/data_sources.md` to three gene windows with
2 kb padding: BRCA2 (chr13:32315085-32400268), TP53 (chr17:7661778-7687546) and BRCA1
(chr17:43044291-43170245).

| File | Content |
|---|---|
| `HG002.subset.vcf.gz` | 155 real HG002 NISTv4.2.1 benchmark records in the windows |
| `clinvar_20251013.subset.vcf.gz`, `clinvar_20261011.subset.vcf.gz` | real ClinVar records in the windows, INFO cut to CLNSIG, CLNREVSTAT, GENEINFO, ALLELEID |
| `gnomad.subset.vcf.gz` | real gnomAD v4.1 genome sites in the windows (AC, AN, AF, nhomalt, AF_grpmax) |
| `reference.fa.gz` | chr13 and chr17 at full length: real hg38 sequence inside the windows, N elsewhere, so coordinates are real and the file is 0.8 MB |
| `panel.bed`, `panel_genes.txt` | the three genes |
| `SYNTH01.vcf.gz` | synthetic sample, 7 records, listed in `synthetic_records.txt` |

SYNTH01 exists because HG002 has no ClinVar P/LP variant in these genes. Its records:
three P/LP alleles with 2 or more stars (GT 0/1), one P/LP allele with 0 stars, one P/LP
allele with GT 0/0, a multiallelic site (T>A,C, GT 1/2; the C allele was picked as a base
not in the first ClinVar record and turned out to be ClinVar 51384), and ClinVar 51985
(13:32316463 GC>G) written one base to the right as CC>C so that normalisation has to
move it back before it matches.

## Hand-written mocks (`mock/`)

| File | What it tests |
|---|---|
| `multiallelic.vcf` | a 1/2 genotype at a two-ALT site; valid input for `cvnf validate` |
| `malformed.vcf` | line 4 has a non-numeric POS and too few columns; the reader must name the line |
| `empty.vcf` | zero bytes; the reader must refuse it |
| `no_chr_prefix.vcf` | contig `1` against a reference with `chr1`; validation must fail |
| `missing_clinvar_fields.vcf` | one record without CLNSIG, one without CLNSTARS, one complete P/LP |
| `reference.fa.fai`, `panel.bed` | a 1 kb `chr1` and one gene, GENE1 |
| `release_old.tsv`, `release_new.tsv` | two ClinVar "releases" as `bcftools query` tables sorted by Variation ID: ID 1 goes VUS to P/LP, ID 2 moves from position 150 to 151 with the same classification (annotation only), ID 3 is removed, ID 4 is added |
