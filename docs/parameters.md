# Parameters

Matches `nextflow_schema.json`; nf-schema validates every run against it.

## Mode

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--mode` | string | `annotate` | annotate: report panel variants for samples. diff: compare two ClinVar releases. |

## Annotate inputs

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--input` | string |  | Samplesheet CSV with columns sample,vcf,tbi. |
| `--fasta` | string |  | bgzipped GRCh38 FASTA with .fai and .gzi next to it, chr-prefixed contigs. |
| `--clinvar` | string |  | ClinVar GRCh38 VCF (vcf_GRCh38/clinvar_YYYYMMDD.vcf.gz) with .tbi. |
| `--gnomad` | string |  | gnomAD sites VCF with INFO/AF, bgzipped and indexed; panel regions are enough. |
| `--panel` | string |  | Gene panel BED: chrom, start, end, gene symbol. |
| `--prefilter_panel` | boolean | `True` | Restrict sample and ClinVar records to the padded panel before normalisation. |
| `--panel_padding` | integer | `1000` | Bases added to each side of panel intervals for the prefilter. |
| `--min_stars` | integer | `1` | Minimum ClinVar review stars for a reportable P/LP variant. |
| `--max_af` | number | `0.01` | Maximum gnomAD allele frequency for a reportable variant; absent counts as 0. |
| `--include_low_penetrance` | boolean | `True` | Report P/LP classifications marked low penetrance. |

## Diff inputs

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--clinvar_old` | string |  | Older ClinVar GRCh38 VCF with .tbi. |
| `--clinvar_new` | string |  | Newer ClinVar GRCh38 VCF with .tbi. |
| `--clinvar_old_label` | string | `old` | Label for the older release, for example clinvar_20251013. |
| `--clinvar_new_label` | string | `new` | Label for the newer release. |
| `--diff_genes` | string |  | Text file with one gene symbol per line for the panel-level comparison. |

## Output

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--outdir` | string | `results` | Output directory. |
| `--publish_dir_mode` | string | `copy` | How results are published. |

## Resources and scheduler

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--max_cpus` | integer | `8` | Upper bound for any task's CPUs, retries included. |
| `--max_memory` | string | `16.GB` | Upper bound for any task's memory. |
| `--max_time` | string | `24.h` | Upper bound for any task's wall time. |
| `--slurm_queue` | string |  | Slurm partition for the slurm profile. |
| `--slurm_cluster_options` | string |  | Extra sbatch options, for example --account=def-xyz. |
