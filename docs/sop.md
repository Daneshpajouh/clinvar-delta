# Maintenance SOP

## Versioning

Semantic versioning. MAJOR: an output column, file name or parameter is removed or changes
meaning. MINOR: a new output, parameter or mode. PATCH: bug fixes and dependency pins that
do not change outputs on the test data. Every release updates CHANGELOG.md, the version in
`nextflow.config`, `pyproject.toml`, `src/cvnf/__init__.py`, `CITATION.cff` and the tools
image tag in `conf/base.config`. Tagging `vX.Y.Z` runs `.github/workflows/release.yml`,
which pushes the tools image to ghcr.io and prints its digest in the release notes; the
next commit replaces the tag in `conf/base.config` with that digest, so that both images
are pinned by digest from then on.

## Monthly ClinVar update

ClinVar publishes a release in `vcf_GRCh38/` weekly and keeps them under `archive_2.0/`.

1. Fetch the new release with `CLINVAR_NEW=clinvar_YYYYMMDD scripts/fetch_data.sh DATA_DIR clinvar`.
   The script checks the NCBI `.md5` file and records size and SHA-256 in `provenance.tsv`.
2. List the review statuses and compare with `REVIEW_STARS` in `src/cvnf/clinvar.py`:
   `bcftools query -f '%INFO/CLNREVSTAT\n' clinvar_YYYYMMDD.vcf.gz | sort | uniq -c`.
   An unknown status makes `cvnf clinvar-table` fail on purpose; add it with its stars from
   the ClinVar review status page and a test.
3. Do the same for CLNSIG terms (`classify` sends unknown terms to OTHER; check the new
   ones belong there).
4. Run diff mode against the previous release used for reporting and file the panel-gene
   report with the release.
5. Re-run affected samples. Variants in `diff.panel.changes.tsv.gz` with `reclassified`
   into or out of P/LP are the ones to re-check in past reports.
6. Record the release name and the diff summary numbers in the run log.

## Updating the gene panel

Rebuild the BED with `scripts/fetch_data.sh DATA_DIR panel`. `cvnf panel-bed` stops if any
symbol is missing from the Ensembl lookup, which is how a renamed gene is noticed. Commit
the new gene list and note the ACMG SF version and Ensembl release in the changelog.

## Tool and container updates

1. Pick the new BioContainers tag and its digest from quay.io; change the `withLabel:
   'bcftools'` line in `conf/base.config`.
2. Run `make test` and `make nf-test`. Snapshot changes must be explained in the pull
   request before `nf-test test --update-snapshot` is committed.
3. Run the real-data commands in results.md and compare the counts.

## Deprecations

A parameter is deprecated for one MINOR release before removal: it keeps working, the
schema description starts with "Deprecated", and the changelog names the replacement.
Removal is a MAJOR release.
