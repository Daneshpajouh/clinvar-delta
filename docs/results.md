# Results on real data

All numbers on this page come from two v1.0.0 runs on 2026-10-19 (Pacific time 11:31 to 11:43) on
an Apple M-series Mac with Docker Desktop. `run_manifest.json` records commit `000f3b9` for
the annotate run and `3496b41` for the diff run, and the bcftools image digest
`sha256:8cf74dd0...3869`. Data are listed in [data_sources.md](data_sources.md).

## HG002 against the ACMG SF v3.2 panel

```bash
D=$DATA_DIR   # the directory given to scripts/fetch_data.sh
nice -n 10 nextflow run main.nf -profile docker --max_cpus 8 \
  --input $D/runs/samplesheet_hg002.csv --fasta $D/reference/hg38_selected.fa.gz \
  --clinvar $D/clinvar/clinvar_20261011.vcf.gz \
  --gnomad $D/gnomad/gnomad.genomes.v4.1.acmg_sf_panel.vcf.gz \
  --panel $D/panel/acmg_sf_v3.2.grch38.bed --outdir $D/runs/hg002_annotate -work-dir $D/runs/work
```

Wall time 30.9 s, 12 tasks.

| Step | Count |
|---|---|
| HG002 benchmark records, whole file | 4,048,342 |
| records in the panel prefilter (genes plus 1 kb) | 9,906 |
| multiallelic records split by `bcftools norm` | 120 |
| indels re-left-aligned by `bcftools norm` | 77 |
| ClinVar records in the padded panel regions | 337,967 (0 re-aligned) |
| HG002 variants inside the 81 panel genes | 9,807 |
| with a gnomAD v4.1 AF | 9,792 |

ClinVar groups for the 9,807 panel variants:

| Group | Variants |
|---|---|
| no ClinVar record | 8,308 |
| benign or likely benign | 1,442 |
| other (drug response, risk factor and similar) | 42 |
| conflicting | 10 |
| uncertain significance | 5 |
| pathogenic or likely pathogenic | 0 |

P/LP by review stars, any genotype: 0 at every level (0, 1, 2, 3 and 4 stars), so nothing
is reportable for HG002 with this panel and release. The synthetic test sample exercises
the same code path with positive results (6 reportable of 8 P/LP, see testing.md).

The NISTv4.2.1 benchmark covers chr1 to chr22 only, so GLA and OTC (chrX) cannot have
HG002 variants here.

## ClinVar 2025-10-13 against 2026-10-11

```bash
nice -n 10 nextflow run main.nf -profile docker --max_cpus 8 --mode diff \
  --clinvar_old $D/clinvar/clinvar_20251013.vcf.gz --clinvar_new $D/clinvar/clinvar_20261011.vcf.gz \
  --clinvar_old_label clinvar_20251013 --clinvar_new_label clinvar_20261011 \
  --diff_genes $D/panel/acmg_sf_v3.2.genes.txt --outdir $D/runs/clinvar_diff -work-dir $D/runs/work
```

Wall time 1 min 20 s. Records: 3,878,123 (old) and 4,594,764 (new). The counts below add
up to both totals.

| Change | All records | ACMG SF v3.2 genes |
|---|---|---|
| reclassified (group changed) | 40,961 | 5,672 |
| review_changed (stars changed) | 164,786 | 13,662 |
| term_changed (wording within group) | 16,180 | 1,284 |
| annotation_only | 4,427 | 27 |
| added | 725,461 | 28,586 |
| removed | 8,820 | 1,071 |
| unchanged | 3,642,949 | 287,395 |

Selected transitions between groups:

| From | To | All records | ACMG genes |
|---|---|---|---|
| VUS | conflicting | 19,907 | 2,862 |
| P/LP | conflicting | 3,955 | 496 |
| VUS | B/LB | 2,035 | 195 |
| VUS | P/LP | 1,350 | 183 |
| conflicting | P/LP | 1,227 | 297 |
| P/LP | VUS | 685 | 69 |
| P/LP | B/LB | 17 | 0 |

Reclassified records by review stars in the new release, all records: 0 stars 143,
1 star 36,687, 2 stars 3,196, 3 stars 935. Panel genes: 10, 4,873, 527 and 262.

Panel genes with the most reclassifications (a record listed under two genes counts for
each, which is why TTN-AS1 appears beside TTN):

| Gene | Reclassified | Became P/LP | Left P/LP |
|---|---|---|---|
| TTN | 616 | 6 | 48 |
| TTN-AS1 | 290 | 2 | 21 |
| TSC2 | 242 | 37 | 2 |
| BRCA2 | 241 | 33 | 8 |
| BRCA1 | 203 | 30 | 6 |
| MSH2 | 187 | 18 | 6 |
| RYR1 | 157 | 29 | 37 |
| MSH6 | 146 | 5 | 6 |

The new release also has 242,896 records with no germline classification (CLNSIG `.`),
against 4,559 a year earlier. The header defines separate somatic fields (ONC, SCI) for
such records; this pipeline reads only the germline fields.
