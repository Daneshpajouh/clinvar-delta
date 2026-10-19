# Code walk-through

A suggested reading order for a reviewer, about 30 minutes.

## 1. `main.nf` (108 lines)

Validates parameters with nf-schema, writes the parameters to a JSON file for the manifest,
dispatches on `--mode`, and writes `run_summary.json` from a `workflow.onComplete` handler
(an `onComplete:` section would need Nextflow 25.10). A single entry with a mode parameter, instead of `-entry`,
keeps one schema and one help text for both modes and lets nf-schema reject a wrong mode
before any work starts. `gitCommit()` reads `.git/HEAD` because `workflow.commitId` is only
set for pipelines pulled from a remote.

## 2. `workflows/annotate.nf`

The data flow, in order: pad the panel, validate each sample, prepare ClinVar, prefilter,
normalise, annotate, filter, report. Points to look at:

- Validation output is joined back to the samples, so a sample that fails validation
  never reaches bcftools.
- The prefilter uses the panel padded by 1 kb. An indel can move left during
  normalisation; filtering on the exact gene boundaries first would drop one that starts
  just outside and ends inside.
- `clinvar_annotation` ends in `.first()`. `combine` returns a queue channel, and without
  `.first()` only the first sample was annotated. The comment records why.

## 3. `modules/local/*/main.nf`

One process per directory, nf-core style: `tag`, a resource label, a tool label that picks
the container, a `versions.yml` output and a `stub:` block. Three choices worth discussing:

- `CLINVAR_PREPARE` renames ClinVar contigs (`1` to `chr1`, `MT` to `chrM`) from the
  reference index instead of a fixed list, so it works with any chr-style reference, and
  it normalises ClinVar with the same reference and bcftools version as the sample. A
  representation mismatch between the two would show up as a missed annotation, which is
  silent.
- `BCFTOOLS_ANNOTATE` runs the gnomAD pass first because bcftools 1.23 cannot pair a VCF
  annotation source with a streamed input (operations.md, failure 3).
- `CLINVAR_QUERY_SORTED` sorts by Variation ID with `LC_ALL=C sort -k1,1n` so the Python
  diff can be a streaming merge join.

## 4. `src/cvnf/clinvar.py`

The domain rules in one place: review status to stars (from the ClinVar documentation),
CLNSIG to group. Unknown review statuses raise, because a new ClinVar status scored as
0 stars would quietly hide variants. CLNSIG is split at `|` (the part after it holds
extra assertions such as `risk_factor`), then at `/`; risk-allele terms do not change the
group when another term is present.

## 5. `src/cvnf/diff.py`

The release audit, about 200 lines, no dependencies, usable without Nextflow
(`cvnf diff`). `merge_join` walks two ID-sorted streams; `classify_change` assigns one
label per Variation ID in a fixed order (group, then stars, then wording, then
annotation), so each ID is counted once and the labels do not overlap. `parse_entries`
rejects unsorted input rather than producing a wrong join. Output order follows the input,
so two runs produce identical bytes (tested).

## 6. `src/cvnf/annotate.py`, `report.py`

`clinvar_table` keeps one ClinVar record per allele (most stars, then lowest ID) so the
annotation does not depend on input order. `evaluate` returns a row for every panel
variant with the reason it is or is not reportable, which is what a reviewer asks when a
known variant is missing from a report. The report is plain Markdown and a self-contained
HTML page rendered from the same tables.

## 7. `src/cvnf/profiling.py`

Trace parsing, the per-process usage summary, `calibrated_config`, and the sacct parser.
Units follow the tools' own formats (`1.5 GB`, `1h 2m`, `[DD-]HH:MM:SS`, `812340K`, `4Gn`).

## 8. `conf/`

`base.config` has the labels and the retry rule (137 and 140 only). `slurm.config`
sets the executor, queue and submit rate. `calibrated.config` is generated. Test
profiles point at `tests/data`.

## 9. Tests

`tests/unit` for the Python, `tests/nf-test` for each process, `tests/pipeline` for
end-to-end, resume and stub runs. See testing.md.

## Trade-offs

- Python with no third-party dependencies: the tools image is the slim Python base plus
  `procps`, and the code runs anywhere Python 3.11 does. The cost is a hand-written VCF
  reader, which is fine for panel-sized files but would be slow for a whole genome; the
  bcftools steps carry the heavy work.
- bcftools over a VEP or SnpEff annotation: ClinVar and gnomAD matching needs exact allele
  matches, which `bcftools annotate` does after normalisation. Consequence annotation
  (HGVS, transcript) is not part of v1.0.
- Each tool has its own container, so bcftools can move to a new BioContainers build
  without rebuilding the Python image. There are two images to pin and publish instead
  of one.
