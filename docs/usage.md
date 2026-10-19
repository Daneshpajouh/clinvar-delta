# Usage

## Inputs for annotate mode

| Input | Format |
|---|---|
| `--input` | CSV with `sample,vcf,tbi`; one single-sample bgzipped VCF per row, GRCh38, chr-prefixed contigs |
| `--fasta` | bgzipped GRCh38 FASTA with `.fai` and `.gzi` beside it; must contain every contig in the VCFs and the panel |
| `--clinvar` | `clinvar_YYYYMMDD.vcf.gz` from `ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/`, with `.tbi` |
| `--gnomad` | gnomAD sites VCF with `INFO/AF`, bgzipped and indexed; panel regions are enough |
| `--panel` | BED with chrom, start, end, gene symbol |

`scripts/fetch_data.sh DATA_DIR giab clinvar reference panel gnomad` downloads all of
these for HG002 and the ACMG SF v3.2 panel (1.51 GB) and records provenance.

```bash
D=/path/to/data
nextflow run . -profile docker \
  --input samplesheet.csv \
  --fasta $D/reference/hg38_selected.fa.gz \
  --clinvar $D/clinvar/clinvar_20261011.vcf.gz \
  --gnomad $D/gnomad/gnomad.genomes.v4.1.acmg_sf_panel.vcf.gz \
  --panel $D/panel/acmg_sf_v3.2.grch38.bed \
  --outdir results
```

## Diff mode

```bash
nextflow run . -profile docker --mode diff \
  --clinvar_old $D/clinvar/clinvar_20251013.vcf.gz --clinvar_old_label clinvar_20251013 \
  --clinvar_new $D/clinvar/clinvar_20261011.vcf.gz --clinvar_new_label clinvar_20261011 \
  --diff_genes $D/panel/acmg_sf_v3.2.genes.txt --outdir results_diff
```

Records are matched on ClinVar Variation ID (the VCF ID column), so a variant whose
position or allele representation changed is still followed. Each ID gets one label:

| Label | Meaning |
|---|---|
| `reclassified` | classification group changed (P/LP, VUS, B/LB, conflicting, risk allele, other, none) |
| `review_changed` | same group, different number of review stars |
| `term_changed` | same group and stars, different wording, for example Pathogenic to Pathogenic/Likely_pathogenic |
| `annotation_only` | same classification and stars; position, allele, gene list or status wording changed |
| `added`, `removed` | ID only in the new or only in the old release |
| `unchanged` | identical in the fields compared |

The VCF carries ClinVar's aggregate (VCV-level) germline classification only. Changes to
condition-specific (RCV) classifications and to individual submissions are not visible in
it; see ROADMAP.md.

## Profiles

| Profile | Use |
|---|---|
| `standard` | local executor, tools from PATH (bcftools 1.23, Python 3.11+), up to 8 CPUs |
| `docker` | BioContainers bcftools 1.23.1 pinned by digest; tools image `ghcr.io/daneshpajouh/clinvar-variant-nf:1.0.0`, pinned by tag until the first release publishes it (build it locally with `make image`) |
| `apptainer` | same images through Apptainer (definition in `containers/apptainer.def`; not run in this release) |
| `slurm` | Slurm executor; set `--slurm_queue` and `--slurm_cluster_options` |
| `calibrated` | per-process requests from measured runs (`conf/calibrated.config`) |
| `test`, `test_diff` | bundled data, under two minutes |

Profiles combine: `-profile slurm,apptainer,calibrated`.

## Outputs

```
results/
  report/              <sample>.report.{md,html,json}, <sample>.gene_summary.tsv
  cvnf_filter/         <sample>.panel_variants.tsv: every panel variant with its reason
  bcftools_annotate/   <sample>.annotated.vcf.gz (+ .tbi), <sample>.panel.vcf.gz
  bcftools_norm/       normalised VCF and the bcftools norm summary line
  clinvar_prepare/     ClinVar table used for annotation and normalisation warnings
  cvnf_validate/       input checks per sample
  clinvar_diff/        diff.{all,panel}.json, diff.*.changes.tsv.gz, clinvar_diff.report.{md,html}
  pipeline_info/       execution_trace.txt, execution_report.html, execution_timeline.html,
                       pipeline_dag.html, software_versions.yml, run_manifest.json
```

`run_manifest.json` holds the SHA-256 of every input, all parameters, the git commit and
the container image for each process. Every `cvnf` step logs JSON lines to stderr
(`.command.err` in the task directory), for example
`{"event": "filter", "panel_variants": 9807, "reportable": 0, "sample": "HG002", ...}`.

## Reportable variants

A panel variant is reportable when all of these hold: ClinVar group P/LP, at least
`--min_stars` stars (default 1), gnomAD AF at most `--max_af` (default 0.01; absent from
gnomAD counts as 0), and a genotype with an ALT allele. Low-penetrance P/LP terms are
included unless `--include_low_penetrance false`. Every non-reportable panel variant keeps
its reason in `<sample>.panel_variants.tsv`.
